from __future__ import annotations

from tempfile import TemporaryDirectory

from ragin.cycle.session import EventType, Session
from tests.integration.test_substantive_runtime_integration_v1 import (
    RejectingVerifier,
    SyntheticClassifier,
    SyntheticDon,
    RequestedStrategySelector,
    make_harness,
    valid_bundle,
)
from ragin.cycle.adapters import SubstantiveStrategyAdapter
from ragin.cycle.harness import Harness


def test_policy_contract_preserves_true_ttp_semantics_and_rule_outcomes():
    expected = {
        "maximize_recon_surface": ("TA0043", "T1046"),
        "fake_success_and_return_visits": ("TA0003", "T1053.003"),
        "steer_to_honeytoken_credentials": ("TA0006", "T1003"),
        "expose_decoy_internal_topology": ("TA0043", "T1046"),
        "contain_in_fiction_and_instrument": ("TA0001", "T1190"),
        "low_intensity_administration": (None, None),
    }
    for strategy, (tactic, ttp) in expected.items():
        bundle = valid_bundle(strategy)
        observed = bundle["don_analysis"]
        assert observed["tactics"][0]["id"] == tactic if tactic else observed["tactics"] == []
        assert observed["ttps_seen"] == [ttp] if ttp else observed["ttps_seen"] == []
        harness, _ = make_harness(strategy)
        assert harness._policy_selector.select(bundle)["selected_response_strategy"] == strategy


def test_nonbaseline_serving_trace_is_complete_on_synthetic_success():
    harness, _ = make_harness("maximize_recon_surface")
    with TemporaryDirectory() as directory:
        session = Session.create(source_ip="synthetic", session_dir=directory)
        result = harness.process(session, "ls -la")
        trace = result.deception_response["metadata"]
        assert trace["serving_outcome"] == "STRATEGY_CONSUMED_AND_SERVED"
        assert trace["strategy_consumed_by_template"] is True
        assert trace["actual_generator_invocation"] is True
        assert trace["candidate_response_sha256"]
        assert trace["served_response_sha256"]
        assert trace["fictional_state_before_hash"]
        assert trace["fictional_state_proposed_hash"]
        assert trace["fictional_state_after_hash"]
        assert trace["serving_attempts"][0]["verifier_verdict"]["passed"] is True
        assert trace["serving_attempts"][0]["hitl_result"]["approved"] is True
        assert trace["serving_attempts"][0]["commit_event"] == "accepted"


def test_rejected_candidate_trace_is_emitted_without_state_commit():
    harness, adapter = make_harness("maximize_recon_surface", verifier=RejectingVerifier())
    with TemporaryDirectory() as directory:
        session = Session.create(source_ip="synthetic", session_dir=directory)
        result = harness.process(session, "ls -la")
        traces = [event.data["serving_trace"] for event in session.replay() if event.event_type == EventType.RESPONSE_GENERATE]
        assert result.error == "verified_serve_unavailable"
        assert traces[0]["outcome"] == "STRATEGY_CONSUMED_BUT_REJECTED"
        assert traces[0]["strategy_consumed_by_template"] is True
        assert traces[0]["verifier_verdict"]["passed"] is False
        assert traces[-1]["strategy_consumed_by_template"] is False
        assert adapter._generators[session.session_id].state.visits == 0
        assert not adapter._pending


def test_invalid_evidence_has_explicit_safe_fallback_trace():
    adapter = SubstantiveStrategyAdapter("RAGIN_V4_SUBSTANTIVE_DETERMINISTIC")
    harness = Harness(
        classifier=SyntheticClassifier(),
        cti_engine=SyntheticDon({"malformed": True}),
        deceiver=adapter,
        mandatory_verification=True,
        max_retries=0,
        decision_arm="RAGIN_V4_DETERMINISTIC",
    )
    with TemporaryDirectory() as directory:
        session = Session.create(source_ip="synthetic", session_dir=directory)
        result = harness.process(session, "whoami")
        metadata = result.deception_response["metadata"]
        assert metadata["serving_outcome"] == "GENERATION_NOT_APPLICABLE"
        assert metadata["strategy_runtime_fallback"] == "invalid_evidence_gate"
        assert metadata["strategy_consumed_by_template"] is False
        assert metadata["serving_attempts"][-1]["fallback_reason"] == "invalid_evidence_gate"
