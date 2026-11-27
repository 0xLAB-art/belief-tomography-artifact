from __future__ import annotations

from tempfile import TemporaryDirectory

from ragin.cycle.adapters import SubstantiveStrategyAdapter
from ragin.cycle.harness import Harness
from ragin.cycle.hitl import ApprovalGateway, ApprovalLevel, ClaimedApprover
from ragin.cycle.session import Session
from ragin.decision_fusion_v4.benchmark import EvidenceQualityGate
from ragin.decision_fusion_v4.runtime_mode import decision_arm_for_runtime

STRATEGY_COMMANDS = {
    "maximize_recon_surface": ("ls -la", "ls -la", "ls -la"),
    "fake_success_and_return_visits": ("deploy fictional-app", "status operation", "status operation"),
    "steer_to_honeytoken_credentials": ("credentials", "credentials", "credentials"),
    "expose_decoy_internal_topology": ("ss -tlnp", "ss -tlnp", "ss -tlnp"),
    "contain_in_fiction_and_instrument": ("apply change", "apply change", "apply change"),
    "low_intensity_administration": ("status service", "status service", "status service"),
}


class SyntheticClassifier:
    def classify(self, attacker_input, session_context):
        return {"skill_level": "novice", "confidence": 1.0, "features_used": [], "feature_values": {}}


class SyntheticDon:
    def __init__(self, bundle):
        self._bundle = bundle

    def analyze(self, attacker_input, session_context):
        return {"evidence_bundle": self._bundle}


class RequestedStrategySelector:
    def __init__(self, strategy):
        self.strategy = strategy
        self.gate = EvidenceQualityGate()

    def select(self, bundle):
        gate = self.gate.evaluate(bundle)
        return {
            "gate_state": gate["gate_state"],
            "valid_doc_ids": gate["valid_doc_ids"],
            "selected_response_strategy": self.strategy,
            "supporting_evidence_refs": gate["valid_doc_ids"][:1],
            "policy_reason_code": "synthetic_fixture_strategy",
        }

    def fallback_decision(self, bundle, gate):
        return {
            "gate_state": gate["gate_state"],
            "valid_doc_ids": gate["valid_doc_ids"],
            "selected_response_strategy": "baseline",
            "supporting_evidence_refs": [],
            "policy_reason_code": "fixture_fallback",
        }


class RejectingVerifier:
    def verify(self, response, context):
        return {"passed": False, "issues": ["synthetic_rejection"], "deterministic": True}


def valid_bundle(strategy):
    tactic, ttp = {
        "maximize_recon_surface": ("TA0043", "T1046"),
        "fake_success_and_return_visits": ("TA0003", "T1053.003"),
        "steer_to_honeytoken_credentials": ("TA0006", "T1003"),
        "expose_decoy_internal_topology": ("TA0043", "T1046"),
        "contain_in_fiction_and_instrument": ("TA0001", "T1190"),
        "low_intensity_administration": (None, None),
    }[strategy]
    classification = "benign" if strategy == "low_intensity_administration" else "malicious"
    severity = "info" if strategy == "low_intensity_administration" else "high"
    return {
        "schema": "ragin.don.evidence_bundle.v4",
        "session": {"session_id": "synthetic", "current_input": "synthetic"},
        "chrollo": {"skill_level": "novice", "confidence": 1.0, "features_used": [], "feature_values": {}},
        "don_analysis": {
            "classification": classification,
            "severity": severity,
            "confidence": 1.0,
            "tactics": [{"id": tactic, "name": "synthetic", "confidence": 1.0}] if tactic else [],
            "ttps_seen": [ttp] if ttp else [],
            "iocs": [],
        },
        "retrieval": {
            "retrieval_status": "SUCCESS",
            "backend": "synthetic",
            "query": "synthetic",
            "sub_queries": ["synthetic"],
            "retrieved_count": 1,
            "relevant_count": 1,
            "relevant_doc_ids": ["synthetic-doc-1"],
            "query_coverage": {"complete": True},
            "documents": [{
                "doc_id": "synthetic-doc-1",
                "title": "Synthetic evidence",
                "content": "synthetic evidence",
                "source": "synthetic-fixture",
                "provenance_status": "VALID",
                "sanitization_status": "SANITIZED",
                "conflict_status": "NONE",
            }],
            "trace_summary": {"usable_successful_retrieval": True},
        },
    }


def make_harness(strategy, *, verifier=None, approval_gateway=None):
    adapter = SubstantiveStrategyAdapter("RAGIN_V4_SUBSTANTIVE_DETERMINISTIC")
    harness = Harness(
        classifier=SyntheticClassifier(),
        cti_engine=SyntheticDon(valid_bundle(strategy)),
        deceiver=adapter,
        verifier=verifier,
        mandatory_verification=True,
        max_retries=0,
        approval_gateway=approval_gateway,
        decision_arm=decision_arm_for_runtime("RAGIN_V4_SUBSTANTIVE_DETERMINISTIC"),
    )
    harness._policy_selector = RequestedStrategySelector(strategy)
    return harness, adapter


def test_server_runtime_mode_maps_to_existing_v4_policy_arms():
    assert decision_arm_for_runtime("RAGIN_BASELINE") == "RAGIN_BASELINE"
    assert decision_arm_for_runtime("RAGIN_V4_SUBSTANTIVE_DETERMINISTIC") == "RAGIN_V4_DETERMINISTIC"
    assert decision_arm_for_runtime("RAGIN_V4_SUBSTANTIVE_LOGISTIC") == "RAGIN_V4_LOGISTIC"


def test_all_six_strategies_run_three_verified_turns_with_state_traces():
    for strategy, commands in STRATEGY_COMMANDS.items():
        with TemporaryDirectory() as directory:
            harness, adapter = make_harness(strategy)
            session = Session.create(source_ip="synthetic", session_dir=directory)
            results = [harness.process(session, command) for command in commands]
            assert all(result.error is None for result in results)
            assert all(result.verification.get("passed") is True for result in results)
            assert all(result.approval.get("approved") is True for result in results)
            assert all(result.deception_response["metadata"]["generator_version"] == "V1_SUBSTANTIVE_STRATEGY_GENERATOR" for result in results)
            assert all(result.deception_response["metadata"]["selected_strategy"] == strategy for result in results)
            assert all(result.deception_response["metadata"]["evidence_ids"] == ["synthetic-doc-1"] for result in results)
            assert all(result.deception_response["metadata"].get("fictional_commit_event") == "accepted" for result in results)
            before = [result.deception_response["metadata"]["fictional_state_before_hash"] for result in results]
            after = [result.deception_response["metadata"]["fictional_state_after_hash"] for result in results]
            assert before[0] != after[0]
            assert after[0] == before[1]
            assert after[1] == before[2]
            assert len({result.response_text for result in results}) >= 1
            assert all("service discovery: internal endpoints available" not in result.response_text for result in results)
            assert adapter._generators[session.session_id].state.visits == 3


def test_strategy_semantics_differ_after_decorative_markers_are_removed():
    responses = {}
    states = {}
    for strategy, commands in STRATEGY_COMMANDS.items():
        with TemporaryDirectory() as directory:
            harness, adapter = make_harness(strategy)
            session = Session.create(source_ip="synthetic", session_dir=directory)
            result = harness.process(session, commands[0])
            assert result.error is None
            assert result.verification.get("passed") is True
            responses[strategy] = "\n".join(result.response_text.splitlines()[1:])
            states[strategy] = repr(adapter._generators[session.session_id].state)
    assert len(set(responses.values())) == 6
    assert len(set(states.values())) == 6
    assert "/srv/fictional-app" in responses["maximize_recon_surface"]
    assert "status: SUCCESS" in responses["fake_success_and_return_visits"]
    assert "access_ref=svc-ref-" in responses["steer_to_honeytoken_credentials"]
    assert "db-fictional-01" in responses["expose_decoy_internal_topology"]
    assert "contained_resource=" in responses["contain_in_fiction_and_instrument"]
    assert "administration: no change" in responses["low_intensity_administration"]


def test_rejected_candidate_does_not_commit_fictional_state():
    with TemporaryDirectory() as directory:
        harness, adapter = make_harness("maximize_recon_surface", verifier=RejectingVerifier())
        session = Session.create(source_ip="synthetic", session_dir=directory)
        result = harness.process(session, "ls -la")
        assert result.error == "verified_serve_unavailable"
        assert adapter._generators[session.session_id].state.visits == 0
        assert not adapter._pending


def test_hitl_rejection_does_not_commit_fictional_state():
    gateway = ApprovalGateway(policy=lambda state: ApprovalLevel.REQUIRE, approver=ClaimedApprover(lambda request: False))
    with TemporaryDirectory() as directory:
        harness, adapter = make_harness("steer_to_honeytoken_credentials", approval_gateway=gateway)
        session = Session.create(source_ip="synthetic", session_dir=directory)
        result = harness.process(session, "show credentials")
        assert result.error == "verified_serve_unavailable"
        assert adapter._generators[session.session_id].state.visits == 0
        assert not adapter._pending


def test_invalid_evidence_uses_verified_baseline_fallback_without_strategy_state():
    with TemporaryDirectory() as directory:
        adapter = SubstantiveStrategyAdapter("RAGIN_V4_SUBSTANTIVE_DETERMINISTIC")
        harness = Harness(
            classifier=SyntheticClassifier(),
            cti_engine=SyntheticDon({"malformed": True}),
            deceiver=adapter,
            mandatory_verification=True,
            max_retries=0,
            decision_arm="RAGIN_V4_DETERMINISTIC",
        )
        session = Session.create(source_ip="synthetic", session_dir=directory)
        result = harness.process(session, "whoami")
        assert result.error is None
        assert result.verification.get("passed") is True
        assert result.deception_response["metadata"]["strategy_runtime_fallback"] == "invalid_evidence_gate"
        assert session.session_id not in adapter._generators
