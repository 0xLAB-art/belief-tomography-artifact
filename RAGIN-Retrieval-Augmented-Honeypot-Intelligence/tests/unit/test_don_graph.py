"""Tests for the Don LangGraph corrective-RAG orchestration."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from ragin.don.graph import DonRAGGraph


class FakeEngine:
    """Minimal ThreatRAGEngine stand-in: deterministic retriever, no LLM."""

    def __init__(self, docs_by_query: dict[str, list[dict[str, Any]]] | None = None, api_key: str = "") -> None:
        self.docs_by_query = docs_by_query or {}
        self._api_key = api_key
        self._model = "test-model"
        self.calls: list[str] = []

    def hybrid_search(self, query: str, alpha: float = 0.7) -> list[dict[str, Any]]:
        self.calls.append(query)
        return self.docs_by_query.get(query, []) + self.docs_by_query.get("*", [])

    # Guard hooks consulted by _llm_available()
    class _NoCB:
        def allow(self):
            return True

    _circuit_breaker = _NoCB()
    _cost_tracker = None


def _doc(i: int, terms: str) -> dict[str, Any]:
    return {"doc_id": f"d{i}", "title": f"Doc {i}", "content": f"{terms} " + "x" * 50}


@pytest.fixture
def engine() -> FakeEngine:
    return FakeEngine(
        docs_by_query={
            "*": [
                _doc(1, "ssh brute force lateral movement"),
                _doc(2, "apt persistence crontab"),
                _doc(3, "nmap scan reconnaissance"),
                _doc(4, "unrelated recipe pancakes"),
            ],
        }
    )


class TestGraphStructure:
    def test_invoke_returns_result(self, engine):
        res = DonRAGGraph(engine).invoke("ssh brute force")
        assert res.context
        assert res.sub_queries
        assert res.rounds == 0
        assert res.trace[-1]["node"] == "compose"

    def test_decomposition_bounded(self, engine):
        res = DonRAGGraph(engine).invoke(" ".join(["word"] * 30))
        assert 1 <= len(res.sub_queries) <= 4

    def test_documents_fused_and_deduped(self, engine):
        res = DonRAGGraph(engine).invoke("ssh brute force and nmap scan")
        doc_ids = [d["doc_id"] for d in res.relevant_docs]
        assert len(doc_ids) == len(set(doc_ids))

    def test_grading_filters_irrelevant(self, engine):
        res = DonRAGGraph(engine).invoke("ssh brute force")
        assert all("pancakes" not in d["content"] for d in res.relevant_docs)

    def test_no_llm_degraded_flag_false(self, engine):
        # Without an API key the graph runs fully heuristic — that is the
        # designed degraded path, not an error.
        res = DonRAGGraph(engine).invoke("apt persistence")
        assert res.context
        assert any(t["node"] == "grade" for t in res.trace)

    def test_retriever_errors_swallowed(self):
        class Broken(FakeEngine):
            def hybrid_search(self, query, alpha=0.7):
                raise RuntimeError("vector store down")

        res = DonRAGGraph(Broken()).invoke("anything")
        assert res.context == ""
        assert res.relevant_docs == []


class TestRewriteLoop:
    def test_insufficient_triggers_rewrite_then_terminates(self):
        # Two sub-queries but the corpus only covers one of them: the
        # 'weather' information-need stays at zero coverage, so the
        # sufficiency check must trigger the bounded rewrite loop.
        docs = {"*": [_doc(1, "ssh brute force"), _doc(2, "ssh hardened ciphers")]}
        engine = FakeEngine(docs_by_query=docs, api_key="")  # heuristic rewrite
        res = DonRAGGraph(engine).invoke("ssh brute force and weather")
        assert res.rounds >= 1
        assert res.rounds <= 2
        # Retries actually hit the retriever again with rewritten queries.
        assert len(engine.calls) > len(res.sub_queries)
        # Loop terminates in compose regardless.
        assert res.trace[-1]["node"] == "compose"

    def test_loop_terminates_within_bound(self):
        engine = FakeEngine(docs_by_query={})  # nothing ever found
        res = DonRAGGraph(engine).invoke(" ".join(["term"] * 20))
        assert res.rounds <= 2
        assert res.trace[-1]["node"] == "compose"


class TestLLMPath:
    def test_llm_available_requires_key(self, engine):
        g = DonRAGGraph(engine)
        assert g._llm_available() is False
        engine._api_key = "k"
        assert g._llm_available() is True

    def test_failing_llm_falls_back_to_heuristics(self, engine):
        engine._api_key = "k"

        def boom(*a, **k):
            raise RuntimeError("gateway down")

        engine._call_gateway = boom
        res = DonRAGGraph(engine).invoke("ssh brute force and nmap scan")
        assert res.context  # heuristics carried the graph
        assert res.degraded or all(not t.get("degraded") for t in res.trace)


class TestRelevantDocRanking:
    """relevant_docs must be ranked (grade, fused score, coverage) so the
    caller's top-5 slice is the best evidence, not raw retrieval order."""

    def test_core_grounding_leads_within_graded_cohort(self):
        # d3 shares every core term of the original query; d1/d2 only some.
        # All grade 1.0 and FakeEngine docs carry no hybrid score, so the
        # fused core-term term decides — d3 first.
        docs = {
            "ssh brute force": [
                _doc(1, "ssh brute force exploitation"),
                _doc(3, "ssh brute force nmap scan port scanning"),
            ],
            "nmap scan": [
                _doc(2, "nmap scan discovery"),
                _doc(3, "ssh brute force nmap scan port scanning"),
            ],
        }
        res = DonRAGGraph(FakeEngine(docs_by_query=docs)).invoke("ssh brute force and nmap scan")
        assert res.rounds == 0
        assert res.relevant_docs[0]["doc_id"] == "d3"

    def test_core_doc_outranks_higher_scored_drift_doc(self):
        """Regression: crontab query P@5 0.8 -> 0.0. A drifted sub-query's
        high-scored doc must not outrank the original query's canonical doc."""
        engine = MagicMock()
        engine._api_key = "k"
        engine._model = "qwen--qwen38-27b"
        engine._circuit_breaker.allow.return_value = True
        engine._cost_tracker.check_budget.return_value = True

        def fake_gateway(req):
            if req.messages[0].content.startswith("You decompose"):
                return "scheduled task crontab persistence\nmalware families crontab"
            return "ddrift: relevant\ndcore: relevant"

        engine._call_gateway.side_effect = fake_gateway
        engine.hybrid_search.return_value = [
            {
                "doc_id": "ddrift",
                "title": "Malware families overview",
                "content": "malware families and tooling " + "y" * 60,
                "graph_score": 0.95,
            },
            {
                "doc_id": "dcore",
                "title": "Scheduled Task crontab persistence",
                "content": "scheduled task crontab persistence via systemd timers " + "x" * 60,
                "graph_score": 0.80,
            },
        ]

        res = DonRAGGraph(engine).invoke("scheduled task persistence via crontab")
        assert res.relevant_docs[0]["doc_id"] == "dcore"

    def test_full_ties_keep_retrieval_order(self):
        docs = {
            "*": [
                _doc(1, "ssh brute force tools"),
                _doc(2, "ssh brute force tooling"),
                _doc(3, "ssh brute force suites"),
            ]
        }
        res = DonRAGGraph(FakeEngine(docs_by_query=docs)).invoke("ssh brute force")
        assert [d["doc_id"] for d in res.relevant_docs] == ["d1", "d2", "d3"]

    def test_grade_beats_retrieval_score_on_graded_path(self):
        """On the LLM-graded path, a relevant verdict must outrank a higher
        retrieval score that the grader judged irrelevant."""
        engine = MagicMock()
        engine._api_key = "k"
        engine._model = "qwen--qwen38-27b"
        engine._circuit_breaker.allow.return_value = True
        engine._cost_tracker.check_budget.return_value = True

        def fake_gateway(req):
            if req.messages[0].content.startswith("You decompose"):
                return "ssh brute force"
            return "dlow: relevant\ndhigh: irrelevant"

        engine._call_gateway.side_effect = fake_gateway
        engine.hybrid_search.return_value = [
            {
                "doc_id": "dhigh",
                "title": "High score mismatch",
                "content": "weather report " + "y" * 60,
                "graph_score": 0.95,
            },
            {
                "doc_id": "dlow",
                "title": "ssh brute force",
                "content": "ssh brute force attempts " + "x" * 60,
                "graph_score": 0.90,
            },
        ]

        res = DonRAGGraph(engine).invoke("ssh brute force")
        assert [d["doc_id"] for d in res.relevant_docs] == ["dlow"]


class TestCorrectiveLoopSemantics:
    """The rewrite loop must fire when the decomposition drifts off the
    original query's core terms — even when peripheral sub-queries are
    generously covered (the old per-sub-query sufficiency missed this)."""

    def _llm_engine(self, decompose_outputs: list[str], grade_output: str) -> MagicMock:
        engine = MagicMock()
        engine._api_key = "k"
        engine._model = "qwen--qwen38-27b"
        engine._circuit_breaker.allow.return_value = True
        engine._cost_tracker.check_budget.return_value = True
        calls = {"n": 0}

        def fake_gateway(req):
            if req.messages[0].content.startswith("You decompose"):
                out = decompose_outputs[min(calls["n"], len(decompose_outputs) - 1)]
                calls["n"] += 1
                return out
            if req.messages[0].content.startswith("You grade"):
                return grade_output
            return "mimikatz lsass credential dumping"  # rewrite

        engine._call_gateway.side_effect = fake_gateway
        engine.hybrid_search.return_value = [
            {"doc_id": "d1", "title": "Generic doc", "content": "generic content " + "x" * 60},
        ]
        return engine

    def test_drifted_decomposition_triggers_rewrite(self):
        # Both sub-queries covered => old logic called this sufficient.
        # Neither shares a core term with the original query => must rewrite.
        engine = self._llm_engine(
            ["evasion techniques\nedr telemetry gaps"],
            "d1: relevant",
        )
        res = DonRAGGraph(engine).invoke("mimikatz lsass credential dumping")
        assert any(t["node"] == "rewrite" and t.get("core_ok") is False for t in res.trace)
        assert res.rounds >= 1

    def test_core_grounding_suffices_without_full_coverage(self):
        # Only the core-grounded sub-query yields relevant docs; a majority
        # of sub-queries (1 of 2) is covered and the core need is satisfied.
        engine = self._llm_engine(
            ["mimikatz lsass credential dumping\nevasion techniques"],
            "d1: relevant",
        )
        res = DonRAGGraph(engine).invoke("mimikatz lsass credential dumping")
        assert res.trace[-1]["node"] == "compose"
        assert all(t["node"] != "rewrite" for t in res.trace)


class TestErrorPlaceholderGuard:
    def test_gateway_error_placeholder_needly_becomes_none(self):
        """_call_gateway returns '[Report generation failed: ...]' strings on
        failure; _ask_llm must convert them to None so callers fall back to
        heuristics instead of misreading the placeholder as model output."""
        engine = FakeEngine(docs_by_query={"*": [_doc(1, "ssh brute force")]})
        engine._api_key = "k"
        engine._call_gateway = lambda req: "[Report generation failed: 401 Unauthorized]"
        g = DonRAGGraph(engine)
        assert g._ask_llm("sys", "user") is None

    def test_placeholder_context_still_grades_via_heuristic(self):
        engine = FakeEngine(docs_by_query={"*": [_doc(1, "ssh brute force lateral movement")]})
        engine._api_key = "k"
        engine._call_gateway = lambda req: "[Report generation failed: 401 Unauthorized]"
        res = DonRAGGraph(engine).invoke("ssh brute force")
        # Grading fell back to lexical overlap -> doc still found relevant.
        assert len(res.relevant_docs) == 1
        assert res.context
