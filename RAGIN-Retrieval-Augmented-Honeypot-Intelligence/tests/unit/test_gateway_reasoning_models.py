"""Tests for reasoning-model handling in GatewayClient and the Don graph.

Covers the Azure AI Foundry qwen3 reasoning deployments (vLLM-served):
short structured calls (grading, decomposition, rewrites) must run at
reasoning_effort=low, extra_body passthrough must reach the wire, and a
400 on optional extension fields must degrade to a plain OpenAI payload
instead of failing the caller.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests

from ragin.don.graph import BATCH_GRADE_MAX_TOKENS, GRAPH_LLM_MAX_TOKENS, DonRAGGraph
from ragin.gateway.client import GatewayClient

pytestmark = pytest.mark.unit


def _ok_response(content: str = "relevant") -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = {
        "choices": [{"message": {"role": "assistant", "content": content}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }
    return resp


def _post_args(mock_post: MagicMock, call_index: int = 0) -> dict:
    return mock_post.call_args_list[call_index][1]["json"]


class TestReasoningModelDetection:
    @pytest.mark.parametrize(
        ("model", "expected"),
        [
            ("qwen--qwen38-27b", True),
            ("qwen3-max", True),
            ("QwQ-32B", True),
            ("deepseek-r1", True),
            ("o4-mini", True),
            ("openai/gpt-4o-mini", False),
            ("moonshotai/kimi-k3-free", False),
        ],
    )
    def test_detection(self, model: str, expected: bool):
        assert GatewayClient._is_reasoning_model(model) is expected


class TestReasoningEffortTuning:
    def test_short_call_gets_low_effort_for_reasoning_model(self):
        with patch("requests.post") as mock_post:
            mock_post.return_value = _ok_response()
            client = GatewayClient(gateway_url="http://fake:8080", api_key="k")
            client.generate(
                messages=[{"role": "user", "content": "grade this"}],
                model="qwen--qwen38-27b",
                max_tokens=512,
            )
            payload = _post_args(mock_post)
            assert payload["reasoning_effort"] == "low"

    def test_long_call_skips_low_effort(self):
        with patch("requests.post") as mock_post:
            mock_post.return_value = _ok_response()
            client = GatewayClient(gateway_url="http://fake:8080", api_key="k")
            client.generate(
                messages=[{"role": "user", "content": "write a report"}],
                model="qwen--qwen38-27b",
                max_tokens=4096,
            )
            assert "reasoning_effort" not in _post_args(mock_post)

    def test_non_reasoning_model_skips_effort(self):
        with patch("requests.post") as mock_post:
            mock_post.return_value = _ok_response()
            client = GatewayClient(gateway_url="http://fake:8080", api_key="k")
            client.generate(
                messages=[{"role": "user", "content": "hello"}],
                model="openai/gpt-4o-mini",
                max_tokens=64,
            )
            assert "reasoning_effort" not in _post_args(mock_post)

    def test_explicit_extra_body_wins(self):
        with patch("requests.post") as mock_post:
            mock_post.return_value = _ok_response()
            client = GatewayClient(
                gateway_url="http://fake:8080",
                api_key="k",
                extra_body={"reasoning_effort": "high"},
            )
            client.generate(
                messages=[{"role": "user", "content": "think hard"}],
                model="qwen--qwen38-27b",
                max_tokens=512,
            )
            assert _post_args(mock_post)["reasoning_effort"] == "high"


class TestExtraBodyPassthrough:
    def test_client_level_extra_body_reaches_wire(self):
        with patch("requests.post") as mock_post:
            mock_post.return_value = _ok_response()
            client = GatewayClient(
                gateway_url="http://fake:8080",
                api_key="k",
                extra_body={"top_k": 20},
            )
            client.generate(messages=[{"role": "user", "content": "hi"}], max_tokens=64)
            assert _post_args(mock_post)["top_k"] == 20

    def test_call_level_overrides_client_level(self):
        with patch("requests.post") as mock_post:
            mock_post.return_value = _ok_response()
            client = GatewayClient(
                gateway_url="http://fake:8080",
                api_key="k",
                extra_body={"top_k": 20},
            )
            client.generate(
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=64,
                extra_body={"top_k": 5},
            )
            assert _post_args(mock_post)["top_k"] == 5


class TestBadRequestFallback:
    def test_400_on_extra_fields_degrades_to_plain_payload(self):
        """Strict OpenAI frontends reject reasoning_effort — the client must
        retry once without the extensions instead of failing the caller."""
        bad = MagicMock()
        bad.status_code = 400
        bad.reason = "Bad Request"
        mock_post = MagicMock(side_effect=[requests.HTTPError("400", response=bad), _ok_response()])

        with patch("requests.post", mock_post):
            client = GatewayClient(gateway_url="http://fake:8080", api_key="k")
            content, _ = client.generate(
                messages=[{"role": "user", "content": "hi"}],
                model="qwen--qwen38-27b",
                max_tokens=512,
            )

        assert content == "relevant"
        assert len(mock_post.call_args_list) == 2
        plain = _post_args(mock_post, 1)
        assert "reasoning_effort" not in plain
        assert plain["model"] == "qwen--qwen38-27b"

    def test_400_without_extra_fields_raises(self):
        bad = MagicMock()
        bad.status_code = 400
        bad.reason = "Bad Request"
        with patch("requests.post", MagicMock(side_effect=requests.HTTPError("400", response=bad))):
            client = GatewayClient(gateway_url="http://fake:8080", api_key="k")
            with pytest.raises(requests.HTTPError):
                client.generate(
                    messages=[{"role": "user", "content": "hi"}],
                    model="openai/gpt-4o-mini",
                    max_tokens=64,
                )


class TestGraphShortCallBudget:
    def test_graph_llm_budget_is_short_call(self):
        """Grade/decompose/rewrite calls must stay within the short-call
        threshold so reasoning deployments run them at low effort."""
        assert GRAPH_LLM_MAX_TOKENS <= 1024

    def test_graph_llm_call_uses_bounded_max_tokens(self):
        engine = MagicMock()
        engine._api_key = "k"
        engine._model = "qwen--qwen38-27b"
        engine._circuit_breaker.allow.return_value = True
        engine._cost_tracker.check_budget.return_value = True
        engine._call_gateway.return_value = "relevant"

        g = DonRAGGraph(engine)
        assert g._ask_llm("sys", "user") == "relevant"

        request = engine._call_gateway.call_args[0][0]
        assert request.max_tokens == GRAPH_LLM_MAX_TOKENS


class TestBatchGrading:
    """_llm_grade_batch grades a whole candidate slice in one LLM call."""

    def _engine(self, gateway_output: str | None) -> MagicMock:
        engine = MagicMock()
        engine._api_key = "k"
        engine._model = "qwen--qwen38-27b"
        engine._circuit_breaker.allow.return_value = True
        engine._cost_tracker.check_budget.return_value = True
        engine._call_gateway.return_value = gateway_output
        return engine

    def test_parses_all_verdict_lines(self):
        out = "\n"
        out += "lightrag-00001: relevant\nlightrag-00002: irrelevant\n"
        out += "[lightrag-00003]: relevant\nlightrag-00004 : irrelevant"
        scores = DonRAGGraph(self._engine(out))._llm_grade_batch(
            "q", [{"doc_id": f"lightrag-{i:05d}", "title": "t", "content": "c"} for i in (1, 2, 3, 4)]
        )
        assert scores == {
            "lightrag-00001": 1.0,
            "lightrag-00002": 0.0,
            "lightrag-00003": 1.0,
            "lightrag-00004": 0.0,
        }

    def test_tolerates_markdown_and_reasoning_noise(self):
        out = "Let me check each doc.\n**lightrag-00001**: relevant\n- lightrag-00002: irrelevant"
        scores = DonRAGGraph(self._engine(out))._llm_grade_batch(
            "q", [{"doc_id": f"lightrag-{i:05d}", "title": "t", "content": "c"} for i in (1, 2)]
        )
        assert scores == {"lightrag-00001": 1.0, "lightrag-00002": 0.0}

    def test_unparseable_output_returns_none(self):
        assert (
            DonRAGGraph(self._engine("I cannot grade these."))._llm_grade_batch(
                "q", [{"doc_id": "d1", "title": "t", "content": "c"}]
            )
            is None
        )

    def test_gateway_failure_returns_none(self):
        engine = self._engine(None)
        assert DonRAGGraph(engine)._llm_grade_batch("q", [{"doc_id": "d1"}]) is None

    def test_empty_doc_slice(self):
        assert DonRAGGraph(self._engine("x"))._llm_grade_batch("q", []) == {}

    def test_batch_call_uses_batch_token_budget(self):
        engine = self._engine("d1: relevant")
        DonRAGGraph(engine)._llm_grade_batch("q", [{"doc_id": "d1", "title": "t", "content": "c"}])
        request = engine._call_gateway.call_args[0][0]
        assert request.max_tokens == BATCH_GRADE_MAX_TOKENS

    def test_grade_node_batches_per_sub_query(self):
        """The grade node must issue one LLM call per sub-query, not one per
        (doc, sub-query) pair — that is the fix for ~5 min/query graphs."""
        engine = MagicMock()
        engine._api_key = "k"
        engine._model = "qwen--qwen38-27b"
        engine._circuit_breaker.allow.return_value = True
        engine._cost_tracker.check_budget.return_value = True
        engine._call_gateway.side_effect = [
            "ssh brute force\nnmap scan",  # decompose
            "d1: relevant\nd2: irrelevant",  # batch grade sq1
            "d1: irrelevant\nd2: relevant",  # batch grade sq2
        ]
        engine.hybrid_search.return_value = [
            {"doc_id": "d1", "title": "ssh brute force", "content": "ssh brute force " + "x" * 60},
            {"doc_id": "d2", "title": "pancakes", "content": "pancakes recipe " + "y" * 60},
        ]

        res = DonRAGGraph(engine).invoke("ssh brute force and nmap scan")

        n_grade_calls = sum(
            1 for c in engine._call_gateway.call_args_list if c[0][0].messages[0].content.startswith("You grade")
        )
        assert n_grade_calls == len(res.sub_queries)
        assert res.trace[-1]["node"] == "compose"
