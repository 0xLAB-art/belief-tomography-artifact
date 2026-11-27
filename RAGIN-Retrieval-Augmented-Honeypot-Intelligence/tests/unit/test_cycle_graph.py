"""Tests for the LangGraph deception pipeline (graph orchestration)."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from ragin.cycle.graph import HAS_LANGGRAPH, DeceptionGraph, DeceptionPipeline
from ragin.cycle.hitl import ApprovalGateway, ClaimedApprover
from ragin.cycle.session import Session
from ragin.hisoka.deception import identity_for


def _classifier(skill: str = "intermediate", confidence: float = 0.8) -> MagicMock:
    c = MagicMock()
    c.classify.return_value = {"skill_level": skill, "confidence": confidence}
    return c


def _analyzer(techniques: list[str] | None = None) -> MagicMock:
    a = MagicMock()
    a.analyze.return_value = {
        "threat_summary": "SSH brute force then credential hunt",
        "recommendations": ["deploy honeytoken"],
        "extracted_techniques": techniques or ["T1552"],
    }
    return a


def _deceiver(text: str = "uid=1001(webapp) gid=1001(webapp) groups=1001(webapp)") -> MagicMock:
    d = MagicMock()
    d.generate_response.return_value = {"response_text": text, "persona_used": "intermediate"}
    return d


class TestDeceptionGraphNodes:
    def test_classify_node_returns_skill(self):
        graph = DeceptionGraph(classifier=_classifier())
        out = graph.classify_node({"attacker_input": "whoami", "context": {}})
        assert out["classification"]["skill_level"] == "intermediate"

    def test_analyze_node_handles_non_dict(self):
        a = MagicMock()
        a.analyze.return_value = "plain text analysis"
        graph = DeceptionGraph(analyzer=a)
        out = graph.analyze_node({"attacker_input": "x", "context": {}})
        assert out["cti_analysis"]["threat_summary"] == "plain text analysis"

    def test_plan_node_attaches_strategy(self):
        graph = DeceptionGraph(classifier=_classifier("novice"))
        state = {
            "session_id": "s1",
            "attacker_input": "uname",
            "context": {},
            "classification": {"skill_level": "novice"},
            "cti_analysis": {"extracted_techniques": ["T1033"]},
        }
        out = graph.plan_node(state)
        assert out["plan"]["persona"] == "novice"
        assert out["plan"]["identity"]["host"]
        assert out["plan"]["fiction_block"]
        assert "bait" in out["plan"]["strategy_block"]
        assert "steer" in out["plan"]["strategy_block"]

    def test_fiction_block_injected_into_generate(self):
        deceiver = _deceiver()
        graph = DeceptionGraph(
            classifier=_classifier(),
            analyzer=_analyzer(),
            deceiver=deceiver,
        )
        state = {
            "session_id": "s1",
            "attacker_input": "id",
            "context": {},
            "classification": {"skill_level": "novice"},
            "cti_analysis": {"extracted_techniques": ["T1033"]},
        }
        plan = graph.plan_node(state)
        state.update(plan)
        graph.generate_node(state)
        passed_context = deceiver.generate_response.call_args[0][1]
        assert "fiction_block" in passed_context
        assert "corp.local" in passed_context["fiction_block"]
        assert "strategy_block" in passed_context
        assert "bait" in passed_context["strategy_block"]

    def test_generate_node_stamps_generated_verified(self):
        graph = DeceptionGraph(classifier=_classifier(), analyzer=_analyzer(), deceiver=_deceiver())
        state = {"session_id": "s1", "attacker_input": "id", "context": {}, "classification": {"skill_level": "novice"}}
        out = graph.generate_node(state)["deception_response"]
        assert out["serve_path"] == "GENERATED_VERIFIED"

    def test_generate_node_labels_gateway_fallback_as_template_fallback(self):
        """2026-09-28 audit finding: the deceiver's gateway-outage template
        came back with no serve_path and generate_node's setdefault stamped it
        GENERATED_VERIFIED — outage templates counted as verified LLM drafts
        in every serve-path tally. Metadata marks must relabel it."""
        deceiver = MagicMock()
        deceiver.generate_response.return_value = {
            "response_text": "bash: id: command not found",
            "persona_used": "novice",
            "metadata": {"gateway_fallback": True},
        }
        graph = DeceptionGraph(classifier=_classifier(), analyzer=_analyzer(), deceiver=deceiver)
        state = {"session_id": "s1", "attacker_input": "id", "context": {}, "classification": {"skill_level": "novice"}}
        out = graph.generate_node(state)["deception_response"]
        assert out["serve_path"] == "TEMPLATE_FALLBACK_VERIFIED"

    def test_generate_node_labels_unsafe_retry_and_anchored_fallbacks(self):
        for mark in ("unsafe_retry_fallback", "template_anchored"):
            deceiver = MagicMock()
            deceiver.generate_response.return_value = {
                "response_text": "template text",
                "persona_used": "novice",
                "metadata": {mark: True},
            }
            graph = DeceptionGraph(classifier=_classifier(), analyzer=_analyzer(), deceiver=deceiver)
            state = {
                "session_id": "s1",
                "attacker_input": "id",
                "context": {},
                "classification": {"skill_level": "novice"},
            }
            out = graph.generate_node(state)["deception_response"]
            assert out["serve_path"] == "TEMPLATE_FALLBACK_VERIFIED", mark

    def test_generate_node_labels_static_fallback_as_template_fallback(self):
        """4th provenance lock: the DECEIVER's own static fallback (budget
        exhausted / circuit breaker open) is a deterministic template too —
        never a verified LLM draft."""
        deceiver = MagicMock()
        deceiver.generate_response.return_value = {
            "response_text": "static deception text",
            "persona_used": "novice",
            "metadata": {"static_fallback": True},
        }
        graph = DeceptionGraph(classifier=_classifier(), analyzer=_analyzer(), deceiver=deceiver)
        state = {"session_id": "s1", "attacker_input": "id", "context": {}, "classification": {"skill_level": "novice"}}
        out = graph.generate_node(state)["deception_response"]
        assert out["serve_path"] == "TEMPLATE_FALLBACK_VERIFIED"


class TestDeceptionGraphE2E:
    def test_full_graph_runs_via_langgraph(self):
        graph = DeceptionGraph(
            classifier=_classifier(),
            analyzer=_analyzer(),
            deceiver=_deceiver(),
        )
        result = graph.invoke("s1", "show me the db password", {"source_ip": "10.0.0.7"})
        assert result["deception_response"]["response_text"]
        assert result["classification"]["skill_level"] == "intermediate"
        assert result["cti_analysis"]["next_techniques_predicted"]
        assert result["plan"]["fiction_block"]

    @pytest.mark.skipif(not HAS_LANGGRAPH, reason="langgraph not installed")
    def test_retry_loop_on_verification_failure(self):
        verifier = MagicMock()
        verifier.verify.side_effect = [
            {"passed": False, "issues": ["too terse"]},
            {"passed": False, "issues": ["too terse"]},
            {"passed": True, "issues": []},
        ]
        deceiver = _deceiver("dark!")
        graph = DeceptionGraph(
            classifier=_classifier(),
            analyzer=_analyzer(),
            deceiver=deceiver,
            verifier=verifier,
            max_retries=2,
        )
        result = graph.invoke("s2", "id", {})
        # max_retries counts total attempts: initial + (max_retries - 1) retries.
        assert deceiver.generate_response.call_count == 2
        # C2 fail-safe default: after retries exhaust, the FAILED response is
        # never served — the deterministic identity-bound template replaces it.
        assert result["verification"]["passed"] is True
        assert result["verification"].get("fallback_served") is True
        assert result["deception_response"]["response_text"] != "dark!"

    @pytest.mark.skipif(not HAS_LANGGRAPH, reason="langgraph not installed")
    def test_high_risk_paused_then_resumed(self):
        gateway = ApprovalGateway()  # requires approval for T1059 apt sessions
        graph = DeceptionGraph(
            classifier=_classifier("apt"),
            analyzer=_analyzer(["T1059.001", "T1571"]),
            deceiver=_deceiver(),
            approval_gateway=gateway,
            human_in_the_loop=True,
        )
        result = graph.invoke("s3", "install a reverse shell on 4444", {})
        assert "__interrupt__" in result
        resumed = graph.resume("s3", decided=True, reason="approved by analyst")
        assert resumed["deception_response"]["response_text"]
        assert resumed["approval"]["approved"] is True

    def test_gateway_blocks_without_approver(self):
        graph = DeceptionGraph(
            classifier=_classifier("apt"),
            analyzer=_analyzer(["T1059.001"]),
            deceiver=_deceiver(),
        )
        result = graph.invoke("s4", "deploy nc -lvnp 4444", {})
        assert result["approval"]["approved"] is False

    def test_failsafe_fallback_serves_pinned_identity_not_failed_text(self):
        """C2 fail-safe contract, asserted end-to-end via the linear executor:
        when verification fails on every attempt, the served text must be the
        deterministic identity-bound template — never the failed LLM output."""
        verifier = MagicMock()
        verifier.verify.side_effect = [
            {"passed": False, "issues": ["fiction-contradiction: os: Ubuntu 22.04.3 LTS -> Ubuntu SMP"]},
            {"passed": True, "issues": []},
        ]
        deceiver = _deceiver("cat /etc/shadow && root:FC7x9qZb")  # leaked secret: must never reach attacker
        graph = DeceptionGraph(
            classifier=_classifier("novice"),
            analyzer=_analyzer(),
            deceiver=deceiver,
            verifier=verifier,
            max_retries=1,
        )
        result = graph.invoke("s5", "uname -a", {})
        served = result["deception_response"]["response_text"]
        # Failed response never served.
        assert served != "cat /etc/shadow && root:FC7x9qZb"
        # Fallback carries the pinned identity (uname reports host + kernel).
        ident = identity_for("novice")
        assert ident["host"] in served
        assert ident["kernel"] in served
        # Verification is repaired honestly: fail-safe marker, not silent pass.
        assert result["verification"]["passed"] is True
        assert result["verification"].get("fallback_served") is True
        # retries exhausted -> exactly max_retries generation attempts.
        assert deceiver.generate_response.call_count == 1


class TestFailSafeFallback:
    """Direct verify_node tests for the C2 fail-safe default: after retries
    exhaust, a failed response must NEVER reach the attacker — the deterministic
    identity-bound template replaces it (the C1 battery caught verify_node
    documenting but not implementing this)."""

    def _graph(self, verifier: Any = None) -> DeceptionGraph:
        return DeceptionGraph(classifier=None, analyzer=None, deceiver=None, verifier=verifier)

    def _failed_state(self, retries_left: int) -> dict:
        return {
            "session_id": "fs1",
            "attacker_input": "uname -a",
            "classification": {"skill_level": "novice"},
            "deception_response": {
                "response_text": "HONEYPOT DETECTED — you are in a sandbox",
                "persona_used": "novice",
            },
            "verification": {"passed": False, "issues": ["danger-signal: honeypot self-reference"]},
            "retries_left": retries_left,
        }

    def test_fallback_served_when_retries_exhausted(self):
        graph = self._graph()
        updates = graph.verify_node(self._failed_state(retries_left=0))
        assert updates["verification"]["passed"] is True
        assert updates["verification"].get("fallback_served") is True
        # The original failed text was replaced by the deterministic template.
        served = updates["deception_response"]["response_text"]
        assert "HONEYPOT DETECTED" not in served
        assert served.strip()  # never empty

    def test_no_fallback_while_retries_remain(self):
        verifier = MagicMock()
        verifier.verify.return_value = {"passed": False, "issues": ["danger-signal: honeypot self-reference"]}
        graph = self._graph(verifier=verifier)
        # retries_left counts remaining attempts: 2 -> 1 after this failed
        # verify, so the retry loop continues and no fallback fires yet.
        updates = graph.verify_node(self._failed_state(retries_left=2))
        assert updates["verification"]["passed"] is False
        assert "fallback_served" not in updates["verification"]
        assert "deception_response" not in updates
        assert updates["retries_left"] == 1
        assert "danger-signal" in updates["retry_feedback"]

    def test_fallback_carries_pinned_identity(self):
        graph = self._graph()
        updates = graph.verify_node(self._failed_state(retries_left=0))
        served = updates["deception_response"]["response_text"]
        ident = identity_for("novice")
        # uname fallback reports the pinned host + kernel (real uname output
        # never contains a username).
        assert ident["host"] in served
        assert ident["kernel"] in served

    def test_fallback_for_whoami_carries_user(self):
        state = self._failed_state(retries_left=0)
        state["attacker_input"] = "whoami"
        updates = self._graph().verify_node(state)
        served = updates["deception_response"]["response_text"]
        assert identity_for("novice")["user"] in served


class TestDeceptionPipeline:
    def test_process_returns_pipeline_result(self, tmp_path):
        pipeline = DeceptionPipeline(
            classifier=_classifier(),
            analyzer=_analyzer(),
            deceiver=_deceiver(),
        )
        session = Session.create(source_ip="10.0.0.5", session_dir=str(tmp_path))
        result = pipeline.process(session, "show credentials")
        assert result.response_text == "uid=1001(webapp) gid=1001(webapp) groups=1001(webapp)"
        assert result.classification["skill_level"] == "intermediate"
        assert result.cti_analysis["next_techniques_predicted"]

    def test_process_claims_approval_via_gateway(self, tmp_path):
        gateway = ApprovalGateway(approver=ClaimedApprover(lambda r: True))
        pipeline = DeceptionPipeline(
            classifier=_classifier("apt"),
            analyzer=_analyzer(["T1059.001"]),
            deceiver=_deceiver(),
            approval_gateway=gateway,
        )
        session = Session.create(source_ip="10.0.0.5", session_dir=str(tmp_path))
        result = pipeline.process(session, "deploy listener on 4444")
        assert not result.error
        assert result.deception_response["response_text"]

    def test_linear_fallback_preserves_semantics(self, monkeypatch, tmp_path):
        monkeypatch.setattr("ragin.cycle.graph.HAS_LANGGRAPH", False)
        pipeline = DeceptionPipeline(
            classifier=_classifier(),
            analyzer=_analyzer(),
            deceiver=_deceiver(),
        )
        session = Session.create(source_ip="10.0.0.5", session_dir=str(tmp_path))
        result = pipeline.process(session, "uname -a")
        assert result.classification["skill_level"] == "intermediate"
        assert result.response_text
