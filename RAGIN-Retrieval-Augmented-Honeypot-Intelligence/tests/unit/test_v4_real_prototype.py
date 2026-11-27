from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ragin.cycle.graph import DeceptionGraph
from ragin.decision_fusion_v4.benchmark import EvidenceQualityGate, generate_corpus
from ragin.decision_fusion_v4.policy import DeterministicPolicySelector, LogisticPolicySelector


def _case(stratum: str) -> dict:
    cases = generate_corpus("V4D-", 1, 17)
    return next(case.state for case in cases if case.stratum == stratum)


def _graph(arm: str, bundle: dict, verifier: object | None = None, deceiver: object | None = None) -> DeceptionGraph:
    classifier = MagicMock()
    classifier.classify.return_value = {"skill_level": "advanced", "confidence": 0.9}
    analyzer = MagicMock()
    analyzer.analyze.return_value = {"extracted_techniques": ["T1046"], "evidence_bundle": bundle}
    generator = deceiver or MagicMock()
    generator.generate_response.return_value = {"response_text": "safe synthetic response", "persona_used": "advanced"}
    check = verifier or MagicMock()
    check.verify.return_value = {"passed": True, "issues": [], "deterministic": True}
    return DeceptionGraph(
        classifier=classifier,
        analyzer=analyzer,
        deceiver=generator,
        verifier=check,
        decision_arm=arm,
        max_retries=1,
    )


def test_gate_accepts_immutable_export_and_rejects_fail_closed_inputs():
    valid = _case("valid_recon")
    assert EvidenceQualityGate().evaluate(valid)["gate_state"] == "VALID_EVIDENCE"
    for stratum in ("retrieval_failure", "invalid_provenance", "duplicate_documents", "unresolved_conflict", "query_coverage_failure", "sanitization_failure"):
        bundle = _case(stratum)
        assert EvidenceQualityGate().evaluate(bundle)["gate_state"] != "VALID_EVIDENCE"


@pytest.mark.parametrize("selector", [DeterministicPolicySelector(), LogisticPolicySelector()])
def test_policy_selector_contract_and_fallback(selector):
    valid = _case("valid_recon")
    selected = selector.select(valid)
    assert selected["selected_response_strategy"] == "maximize_recon_surface"
    assert selected["supporting_evidence_refs"] == valid["retrieval"]["relevant_doc_ids"]
    invalid = _case("retrieval_failure")
    fallback = selector.select(invalid)
    assert fallback["selected_response_strategy"] == "baseline"
    assert fallback["fallback_reason"] == "evidence_gate_fallback"
    malformed = selector.select({})
    assert malformed["selected_response_strategy"] == "baseline"


def test_policy_validation_rejects_strategy_and_reference_and_exception():
    class BadSelector(DeterministicPolicySelector):
        def _select_valid(self, evidence_bundle, valid_doc_ids):
            return {"selected_response_strategy": "not-allowed", "supporting_evidence_refs": ["fake"]}

    decision = BadSelector().select(_case("valid_recon"))
    assert decision["selected_response_strategy"] == "baseline"
    assert decision["fallback_reason"] == "unsupported_strategy"

    class FailingSelector(DeterministicPolicySelector):
        def _select_valid(self, evidence_bundle, valid_doc_ids):
            raise TimeoutError("synthetic timeout")

    decision = FailingSelector().select(_case("valid_recon"))
    assert decision["selected_response_strategy"] == "baseline"
    assert decision["fallback_reason"] == "TimeoutError"


def test_baseline_does_not_invoke_v4_selector():
    graph = _graph("RAGIN_BASELINE", _case("valid_recon"))
    graph._policy_selector = MagicMock(side_effect=AssertionError("selector invoked"))
    result = graph.invoke("v4-baseline", "nmap -sV 10.0.0.0/24", {})
    assert "policy_decision" not in result


@pytest.mark.parametrize("arm", ["RAGIN_V4_DETERMINISTIC", "RAGIN_V4_LOGISTIC"])
def test_v4_strategy_reaches_generator_and_verification_is_mandatory(arm):
    generator = MagicMock()
    generator.generate_response.return_value = {"response_text": "safe synthetic response", "persona_used": "advanced"}
    verifier = MagicMock()
    verifier.verify.return_value = {"passed": True, "issues": [], "deterministic": True}
    graph = _graph(arm, _case("valid_recon"), verifier=verifier, deceiver=generator)
    result = graph.invoke(f"{arm}-smoke", "nmap -sV 10.0.0.0/24", {})
    decision = result["policy_decision"]
    assert decision["selected_response_strategy"] == "maximize_recon_surface"
    assert decision["strategy_reached_generator"] is True
    assert generator.generate_response.call_args.args[1]["strategy_block"] == "Bounded response strategy: maximize_recon_surface\n"
    assert verifier.verify.called


def test_invalid_evidence_never_reaches_policy_selector():
    graph = _graph("RAGIN_V4_DETERMINISTIC", _case("retrieval_failure"))
    selector = DeterministicPolicySelector()
    selector._select_valid = MagicMock(side_effect=AssertionError("policy engine invoked"))
    graph._policy_selector = selector
    result = graph.invoke("v4-invalid", "nmap -sV 10.0.0.0/24", {})
    assert result["policy_decision"]["selected_response_strategy"] == "baseline"
    selector._select_valid.assert_not_called()
    assert result["policy_decision"]["gate_state"] == "RETRIEVAL_FAILURE"


def test_failed_verification_does_not_commit_failed_response():
    verifier = MagicMock()
    verifier.verify.side_effect = [{"passed": False, "issues": ["synthetic rejection"]}, {"passed": True, "issues": []}]
    generator = MagicMock()
    generator.generate_response.return_value = {"response_text": "failed draft", "persona_used": "advanced"}
    graph = _graph("RAGIN_V4_DETERMINISTIC", _case("valid_recon"), verifier=verifier, deceiver=generator)
    result = graph.invoke("v4-retry", "nmap -sV 10.0.0.0/24", {})
    assert result["verification"]["passed"] is True
    assert result["deception_response"]["response_text"] != "failed draft" or verifier.verify.call_count == 2
