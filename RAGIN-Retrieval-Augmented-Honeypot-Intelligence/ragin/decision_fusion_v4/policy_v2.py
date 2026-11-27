from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Mapping
from typing import Any

from .benchmark import ALLOWED_STRATEGIES, EvidenceQualityGate
from .evidence_export import freeze_bundle, sha256_json, thaw

POLICY_ENGINE_ID = "evidence_grounded_deterministic_v2"
POLICY_VERSION = "EVIDENCE_GROUNDED_DETERMINISTIC_V2"
POLICY_SCHEMA = "ragin.decision_fusion_v4.policy_decision.v2"

def _decision(bundle: Mapping[str, Any], gate: Mapping[str, Any], strategy: str, reason: str, rule_id: str, predicate: Mapping[str, Any], refs: list[str], started: int, abstention: str | None = None) -> dict[str, Any]:
    frozen = freeze_bundle(bundle)
    digest = sha256_json(frozen)
    return {
        "schema": POLICY_SCHEMA,
        "policy_engine_id": POLICY_ENGINE_ID,
        "policy_version": POLICY_VERSION,
        "policy_hash": hashlib.sha256(f"{POLICY_ENGINE_ID}:{POLICY_VERSION}".encode()).hexdigest(),
        "selected_response_strategy": strategy,
        "supporting_evidence_refs": list(refs),
        "valid_doc_ids": list(gate.get("valid_doc_ids", [])),
        "gate_state": gate.get("gate_state"),
        "evidence_gate_state": gate.get("gate_state"),
        "evidence_gate_reason": gate.get("reason_code"),
        "policy_reason_code": reason,
        "rule_id": rule_id,
        "rule_predicate": dict(predicate),
        "predicate_match": strategy != "baseline" and abstention is None,
        "abstention_reason": abstention,
        "input_digest": digest,
        "policy_input_sha256": digest,
        "evidence_bundle_sha256": digest,
        "policy_latency_ms": (time.perf_counter_ns() - started) / 1_000_000,
        "supporting_evidence_count": len(refs),
    }

class EvidenceGroundedDeterministicPolicyV2:
    gate = EvidenceQualityGate()

    def select(self, evidence_bundle: Mapping[str, Any]) -> dict[str, Any]:
        started = time.perf_counter_ns()
        frozen = thaw(freeze_bundle(evidence_bundle))
        gate = self.gate.evaluate(frozen)
        if gate["gate_state"] != "VALID_EVIDENCE":
            return _decision(frozen, gate, "baseline", "abstain_invalid_evidence", "ABSTAIN_INVALID_EVIDENCE", {}, [], started, gate.get("reason_code", "invalid_evidence"))
        return self._select_valid(frozen, gate, started)

    def fallback_decision(self, evidence_bundle: Mapping[str, Any], gate_result: Mapping[str, Any]) -> dict[str, Any]:
        return _decision(evidence_bundle, gate_result, "baseline", "abstain_invalid_evidence", "ABSTAIN_INVALID_EVIDENCE", {}, [], time.perf_counter_ns(), str(gate_result.get("reason_code", "invalid_evidence")))

    def _select_valid(self, bundle: Mapping[str, Any], gate: Mapping[str, Any], started: int) -> dict[str, Any]:
        retrieval = bundle["retrieval"]
        projection = (retrieval.get("trace_summary") or {}).get("context_projection") or {}
        features = projection.get("features") or {}
        docs = retrieval.get("documents") or []
        valid_ids = set(str(x) for x in gate.get("valid_doc_ids", []))
        grounded = [doc for doc in docs if str(doc.get("doc_id")) in valid_ids and doc.get("relevance_grade") == "command_grounded"]
        if not grounded:
            return _decision(bundle, gate, "baseline", "abstain_without_command_grounding", "ABSTAIN_NO_COMMAND_GROUNDING", {"grounded_document_count": 0}, [], started, "no_command_grounded_document")
        techniques = {str(t) for doc in grounded for t in doc.get("techniques", [])}
        behaviors = {str(t) for doc in grounded for t in doc.get("behavior_tags", [])}
        indicators = set(str(t) for t in features.get("behavior_indicators", []))
        ambiguity = str(features.get("ambiguity", "none"))
        base = {"techniques": sorted(techniques), "behavior_tags": sorted(behaviors), "behavior_indicators": sorted(indicators), "ambiguity": ambiguity, "grounded_document_count": len(grounded)}
        refs = [str(doc["doc_id"]) for doc in grounded]
        if ambiguity != "none":
            return _decision(bundle, gate, "baseline", "abstain_ambiguous_context", "ABSTAIN_AMBIGUOUS_CONTEXT", base, refs, started, "ambiguous_command_context")
        if "T1105" in techniques and features.get("download_execution_relationship") is True:
            return _decision(bundle, gate, "contain_in_fiction_and_instrument", "transfer_with_execution_relationship", "DONV2_T1105_EXECUTION_RELATIONSHIP", base, refs, started)
        if ("T1003" in techniques or "T1552.001" in techniques) and ("credential_access_indicator" in indicators or "credentials" in features.get("path_categories", [])):
            return _decision(bundle, gate, "steer_to_honeytoken_credentials", "credential_behavior_with_context", "DONV2_CREDENTIAL_CONTEXT", base, refs, started)
        if "T1053.003" in techniques and "persistence_indicator" in indicators:
            return _decision(bundle, gate, "fake_success_and_return_visits", "persistence_behavior_with_context", "DONV2_CRON_PERSISTENCE", base, refs, started)
        if "T1016" in techniques and "network" in features.get("path_categories", []):
            return _decision(bundle, gate, "expose_decoy_internal_topology", "network_discovery_with_context", "DONV2_NETWORK_TOPOLOGY", base, refs, started)
        if techniques.intersection({"T1007", "T1082", "T1083"}) and "environment_discovery" in indicators:
            return _decision(bundle, gate, "maximize_recon_surface", "system_or_file_discovery_with_context", "DONV2_DISCOVERY_SURFACE", base, refs, started)
        if bundle.get("don_analysis", {}).get("classification") == "benign" and bundle.get("don_analysis", {}).get("severity") == "info" and not indicators.intersection({"credential_access_indicator", "persistence_indicator", "download_indicator", "execution_indicator"}):
            return _decision(bundle, gate, "low_intensity_administration", "explicit_benign_administration", "DONV2_BENIGN_ADMINISTRATION", base, refs, started)
        return _decision(bundle, gate, "baseline", "abstain_unsupported_or_insufficient_behavior", "ABSTAIN_UNSUPPORTED_BEHAVIOR", base, refs, started, "no_supported_strategy_predicate")

def build_policy_v2() -> EvidenceGroundedDeterministicPolicyV2:
    return EvidenceGroundedDeterministicPolicyV2()
