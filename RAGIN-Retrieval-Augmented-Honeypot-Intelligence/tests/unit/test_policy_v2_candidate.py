from __future__ import annotations

from tempfile import TemporaryDirectory

from ragin.cycle.adapters import SubstantiveStrategyAdapter
from ragin.cycle.harness import Harness
from ragin.cycle.session import Session
from ragin.decision_fusion_v4.policy_v2 import build_policy_v2


class SyntheticClassifier:
    def classify(self, attacker_input, session_context):
        return {"skill_level": "novice", "confidence": 1.0, "features_used": [], "feature_values": {}}


class SyntheticDon:
    def __init__(self, bundle):
        self.bundle = bundle

    def analyze(self, attacker_input, session_context):
        return {"evidence_bundle": self.bundle}


class RejectingVerifier:
    def verify(self, response, context):
        return {"passed": False, "issues": ["synthetic_rejection"], "deterministic": True}


def bundle(technique, tags, indicators, *, command="synthetic", classification="malicious", severity="high", relationship=False, ambiguity="none", provenance="VALID", path_categories=None):
    document = {
        "doc_id": f"synthetic-{technique or 'benign'}",
        "title": "Synthetic command-grounded evidence",
        "content": "synthetic command-grounded evidence",
        "source": "synthetic-policy-v2",
        "provenance_status": provenance,
        "sanitization_status": "SANITIZED",
        "conflict_status": "NONE",
        "relevance_grade": "command_grounded",
        "techniques": [technique] if technique else [],
        "behavior_tags": tags,
        "command_patterns": [command.split()[0]],
    }
    return {
        "schema": "ragin.don.evidence_bundle.v4",
        "session": {"session_id": "synthetic-policy-v2", "current_input": command},
        "chrollo": {"skill_level": "novice", "confidence": 1.0, "features_used": [], "feature_values": {}},
        "don_analysis": {"classification": classification, "severity": severity, "confidence": 1.0, "tactics": [], "ttps_seen": [], "iocs": []},
        "retrieval": {
            "retrieval_status": "SUCCESS",
            "backend": "command_aware_v2",
            "query": command,
            "sub_queries": [command],
            "retrieved_count": 1,
            "relevant_count": 1,
            "relevant_doc_ids": [document["doc_id"]],
            "query_coverage": {"complete": True, "required_terms": [command.split()[0]], "covered_terms": [command.split()[0]]},
            "documents": [document],
            "trace_summary": {"usable_successful_retrieval": True, "context_projection": {"features": {"behavior_indicators": indicators, "path_categories": path_categories or [], "download_execution_relationship": relationship, "ambiguity": ambiguity}}},
        },
    }


def cases():
    return {
        "maximize_recon_surface": bundle("T1083", ["file_discovery", "discovery"], ["environment_discovery"], command="find /home"),
        "fake_success_and_return_visits": bundle("T1053.003", ["persistence"], ["persistence_indicator"], command="deploy fictional-app"),
        "steer_to_honeytoken_credentials": bundle("T1552.001", ["credentials"], ["credential_access_indicator"], command="cat /etc/passwd"),
        "expose_decoy_internal_topology": bundle("T1016", ["network_discovery", "discovery"], ["environment_discovery"], command="ip addr", path_categories=["network"]),
        "contain_in_fiction_and_instrument": bundle("T1105", ["download"], ["download_indicator", "execution_indicator"], command="apply change", relationship=True),
        "low_intensity_administration": bundle(None, ["benign_administration"], [], command="systemctl status ssh", classification="benign", severity="info"),
    }


def test_policy_v2_maps_only_supported_observed_evidence():
    selector = build_policy_v2()
    expected = {strategy: strategy for strategy in cases()}
    for strategy, fixture in cases().items():
        decision = selector.select(fixture)
        assert decision["selected_response_strategy"] == expected[strategy]
        assert decision["predicate_match"] is True
        assert decision["supporting_evidence_refs"] == fixture["retrieval"]["relevant_doc_ids"]
        assert decision["rule_id"]
        assert decision["abstention_reason"] is None


def test_policy_v2_abstains_on_ambiguous_transfer_only_and_unsupported_shell():
    selector = build_policy_v2()
    transfer_only = selector.select(bundle("T1105", ["download"], ["download_indicator"], command="wget https://example.invalid/x"))
    shell_only = selector.select(bundle("T1059.004", ["shell", "execution"], ["execution_indicator"], command="bash script.sh"))
    assert transfer_only["selected_response_strategy"] == "baseline"
    assert transfer_only["abstention_reason"] == "no_supported_strategy_predicate"
    assert shell_only["selected_response_strategy"] == "baseline"
    assert shell_only["abstention_reason"] == "no_supported_strategy_predicate"


def test_policy_v2_rejects_conflicting_and_missing_provenance():
    selector = build_policy_v2()
    conflicting = bundle("T1083", ["file_discovery"], ["environment_discovery"])
    conflicting["retrieval"]["documents"][0]["conflict_status"] = "UNRESOLVED"
    invalid = selector.select(conflicting)
    missing = selector.select(bundle("T1083", ["file_discovery"], ["environment_discovery"], provenance="UNKNOWN"))
    assert invalid["selected_response_strategy"] == "baseline"
    assert invalid["abstention_reason"] == "unresolved_document_conflict"
    assert missing["selected_response_strategy"] == "baseline"
    assert missing["abstention_reason"] == "invalid_or_unknown_provenance"


def test_policy_v2_pipeline_consumes_all_six_strategies():
    for strategy, fixture in cases().items():
        adapter = SubstantiveStrategyAdapter("RAGIN_V4_SUBSTANTIVE_DETERMINISTIC")
        harness = Harness(classifier=SyntheticClassifier(), cti_engine=SyntheticDon(fixture), deceiver=adapter, mandatory_verification=True, max_retries=0, decision_arm="RAGIN_V4_DETERMINISTIC")
        harness._policy_selector = build_policy_v2()
        with TemporaryDirectory() as directory:
            session = Session.create(source_ip="synthetic", session_dir=directory)
            result = harness.process(session, fixture["session"]["current_input"])
        metadata = result.deception_response["metadata"]
        assert result.error is None
        assert result.verification["passed"] is True
        assert result.approval["approved"] is True
        assert metadata["selected_strategy"] == strategy
        assert metadata["strategy_consumed_by_template"] is True
        assert metadata["serving_outcome"] == "STRATEGY_CONSUMED_AND_SERVED"
        assert metadata["fictional_commit_event"] == "accepted"


def test_policy_v2_rejected_candidate_rolls_back_and_trace_is_explicit():
    fixture = cases()["maximize_recon_surface"]
    adapter = SubstantiveStrategyAdapter("RAGIN_V4_SUBSTANTIVE_DETERMINISTIC")
    harness = Harness(classifier=SyntheticClassifier(), cti_engine=SyntheticDon(fixture), deceiver=adapter, verifier=RejectingVerifier(), mandatory_verification=True, max_retries=0, decision_arm="RAGIN_V4_DETERMINISTIC")
    harness._policy_selector = build_policy_v2()
    with TemporaryDirectory() as directory:
        session = Session.create(source_ip="synthetic", session_dir=directory)
        result = harness.process(session, fixture["session"]["current_input"])
        traces = [event.data["serving_trace"] for event in session.replay() if event.event_type.value == "response_generate"]
    assert result.error == "verified_serve_unavailable"
    assert traces[0]["outcome"] == "STRATEGY_CONSUMED_BUT_REJECTED"
    assert traces[0]["verifier_verdict"]["passed"] is False
    assert adapter._generators[session.session_id].state.visits == 0
    assert not adapter._pending
