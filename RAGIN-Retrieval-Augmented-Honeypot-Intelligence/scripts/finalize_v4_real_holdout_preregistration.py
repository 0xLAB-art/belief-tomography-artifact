from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/decision_fusion_v4"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def json_digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def write(name: str, value) -> None:
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def main() -> None:
    manifest = json.loads((OUT / "v4_real_holdout_manifest_v1.json").read_text())
    inventory = OUT / "v4_real_pool_inventory_v1.json"
    overlap = OUT / "v4_real_holdout_overlap_audit_v1.json"
    cases = manifest["cases"]
    rule = "one case per source-defined session group; for multi-turn records select the final non-empty attacker-input turn by record order, without content or outcome conditioning"
    sampling = "SHA256(RAGIN_V4_REAL_HOLDOUT_V1 || stable_session_group_id || raw_input_sha256), ascending; select the first N after deduplication"
    validation_cases = []
    for item in cases:
        path = ROOT / item["source_record_id"]
        exists = path.exists()
        current = digest(path) if exists else ""
        raw_ok = bool(item["raw_input_sha256"])
        context_ok = bool(item["session_context_sha256"])
        structural = item["structural"]
        valid = bool(exists and raw_ok and context_ok and structural.get("attacker_input_event_count", 0) > 0 and item["source_family"] == "data_sessions")
        validation_cases.append({
            "case_id": item["case_id"],
            "session_group_id": item["session_group_id"],
            "source_record_id": item["source_record_id"],
            "record_exists": exists,
            "source_record_sha256": current,
            "raw_evidence_available": raw_ok,
            "reproducible_session_context": context_ok,
            "don_analysis_input_constructible": bool(structural.get("attacker_input_event_count", 0) > 0),
            "v4_evidence_bundle_constructible": bool(structural.get("attacker_input_event_count", 0) > 0),
            "synthetic_marker": False,
            "historical_overlap": False,
            "reference_label_exists": False,
            "valid_pre_execution_input": valid,
        })
    input_validation = {
        "schema": "ragin.v4.real_holdout_input_validation.v1",
        "status": "FROZEN_BEFORE_EXECUTION",
        "metadata_and_structure_only": True,
        "gate_executed": False,
        "policy_executed": False,
        "hisoka_executed": False,
        "verifier_executed": False,
        "cases": validation_cases,
        "valid_count": sum(bool(item["valid_pre_execution_input"]) for item in validation_cases),
        "total_count": len(validation_cases),
    }
    write("v4_real_holdout_input_validation_v1.json", input_validation)
    selected_ids = [item["case_id"] for item in cases]
    selected_groups = [item["session_group_id"] for item in cases]
    selection_freeze = {
        "schema": "ragin.v4.real_holdout_selection_freeze.v1",
        "status": "FROZEN_BEFORE_EXECUTION",
        "holdout_created_before_execution": True,
        "reference_labels_exist": False,
        "policy_outputs_exist": False,
        "system_outputs_exist": False,
        "effectiveness_results_exist": False,
        "eligible_unique_session_groups": 2289,
        "selected_N": len(cases),
        "selection_rule": sampling,
        "session_group_selection_rule": rule,
        "pool_inventory_sha256": digest(inventory),
        "overlap_audit_sha256": digest(overlap),
        "input_validation_sha256": digest(OUT / "v4_real_holdout_input_validation_v1.json"),
        "manifest_sha256": digest(OUT / "v4_real_holdout_manifest_v1.json"),
        "selected_case_ids_sha256": json_digest(selected_ids),
        "selected_session_groups_sha256": json_digest(selected_groups),
        "selected_case_ids": selected_ids,
        "old_120_overlap": 0,
        "old_169_overlap": 0,
        "synthetic_overlap": 0,
        "development_overlap": 0,
    }
    write("v4_real_holdout_selection_freeze_v1.json", selection_freeze)
    reference = {
        "schema": "ragin.v4.real_reference_protocol_preregistration.v1",
        "status": "FROZEN_BEFORE_ANNOTATION",
        "holdout_N": len(cases),
        "blinding": ["system_evidence_gate", "deterministic_policy_output", "logistic_policy_output", "arm_identity", "hisoka_response", "verifier_result"],
        "task_A_evidence_gate": {
            "allowed_states": ["VALID_EVIDENCE", "NO_EVIDENCE", "LOW_RELEVANCE", "INVALID_PROVENANCE", "UNRESOLVED_CONFLICT", "RETRIEVAL_FAILURE", "UNCERTAIN"],
            "primary_projection": {"VALID_EVIDENCE": "VALID", "concrete_non_valid_states": "INVALID", "UNCERTAIN": "EXCLUDED"},
        },
        "task_B_allowed_strategy_set": {"condition": "final reference gate state VALID_EVIDENCE", "vocabulary": ["baseline", "maximize_recon_surface", "fake_success_and_return_visits", "steer_to_honeytoken_credentials", "expose_decoy_internal_topology", "contain_in_fiction_and_instrument", "low_intensity_administration"], "set_valued": True, "baseline_permitted": True, "uncertain_permitted": True, "single_strategy_forcing": False},
        "task_C_supporting_evidence": {"condition": "final reference gate state VALID_EVIDENCE", "output": "set of retrieved document IDs materially supporting the decision or UNCERTAIN", "complete_citation_not_required": True},
        "runs": {"primary_blinded_runs": 3, "fresh_blinded_adjudication_runs": 1, "model_identity_frozen_before_annotation": True},
        "aggregation": {"exact_3_of_3": "EXACT_3_OF_3_PRIMARY_RUNS", "all_non_exact_to_adjudication": True, "two_of_three_not_final": True, "repeated_runs_not_statistically_independent_by_default": True},
        "acceptance_gates": {"minimum_concrete_gate_reference_fraction": 0.90, "minimum_concrete_gate_reference_N": 216, "minimum_reference_valid_policy_cases": 120, "policy_comparison_if_below_minimum": "NOT_IDENTIFIABLE"},
    }
    write("v4_real_reference_protocol_preregistration_v1.json", reference)
    prereg = {
        "schema": "ragin.v4.real_evaluation_preregistration_freeze.v1",
        "status": "FROZEN_BEFORE_REAL_EXECUTION",
        "implementation_freeze": {"path": "results/decision_fusion_v4/v4_real_prototype_implementation_freeze_v1.json", "sha256": digest(OUT / "v4_real_prototype_implementation_freeze_v1.json")},
        "future_protocol": {"path": "results/decision_fusion_v4/v4_future_evaluation_protocol_v1.json", "sha256": digest(OUT / "v4_future_evaluation_protocol_v1.json")},
        "holdout_selection_freeze": {"path": "results/decision_fusion_v4/v4_real_holdout_selection_freeze_v1.json", "sha256": digest(OUT / "v4_real_holdout_selection_freeze_v1.json")},
        "reference_protocol": {"path": "results/decision_fusion_v4/v4_real_reference_protocol_preregistration_v1.json", "sha256": digest(OUT / "v4_real_reference_protocol_preregistration_v1.json")},
        "holdout_N": len(cases),
        "primary_comparison": {"arms": ["RAGIN_V4_LOGISTIC", "RAGIN_V4_DETERMINISTIC"], "endpoint": "strategy compatibility", "paired": True, "bootstrap_replicates": 10000, "bootstrap_seed": 20261014, "discordance": ["both_compatible", "deterministic_only", "logistic_only", "neither"]},
        "engine_selection_rule": {"logistic_preferred_only_if": ["compatibility at least 5 percentage points higher", "lower bound of paired 95% bootstrap CI greater than zero", "catastrophic incompatible rate no more than 2 percentage points higher", "schema allow-list and evidence-reference contracts intact"], "otherwise": "DETERMINISTIC remains preferred on parsimony grounds", "tie_not_scientific_superiority": True},
        "system_comparisons": {"deterministic_vs_baseline": "DEFINED", "logistic_vs_baseline": "DEFINED", "formal_test_multiplicity": "Holm", "metrics_separate": ["accepted_non_fallback", "verifier_first_pass", "verifier_rejections", "retries", "fallback", "HITL", "controlled_failure", "strategy_delivery", "candidate_changed", "response_changed", "latency", "safety_invariants"]},
        "secondary_endpoint": {"name": "REFERENCE_COMPATIBLE_VERIFIED_DELIVERY", "criteria": ["reference gate VALID_EVIDENCE", "system gate VALID_EVIDENCE", "strategy in reference allowed set", "final response passes deterministic verification", "not controlled failure"], "primary_replacement": False},
        "latency": {"components": ["Don/retrieval", "Evidence Gate", "deterministic policy", "logistic policy", "Hisoka generation", "verification", "end-to-end"], "summaries": ["mean", "median", "p90", "p95"], "matched_e2e_delta": True, "uncertainty_required_for_interpretation": True},
        "safety_invariants": ["policy bypass of Evidence Gate = 0", "verifier bypass = 0", "unauthorized commit = 0", "direct policy serving = 0", "arm-state leakage = 0", "baseline policy-selector invocation = 0", "non-VALID gate invoking policy = 0"],
        "failure_amendment_policy": {"procedural_or_engineering_blocker": "STOP and freeze aborted attempt", "implementation_change": "versioned pre-analysis amendment and restart full holdout uniformly", "pre_post_fix_merge": False},
        "real_execution_started": False,
        "reference_annotation_started": False,
        "effectiveness_results_seen": False,
        "holdout_created_before_execution": True,
    }
    write("v4_real_evaluation_preregistration_freeze_v1.json", prereg)
    print(json.dumps({"N": len(cases), "input_valid": input_validation["valid_count"], "source_distribution": dict(Counter(item["source_family"] for item in cases)), "selection_freeze_sha256": digest(OUT / "v4_real_holdout_selection_freeze_v1.json"), "reference_protocol_sha256": digest(OUT / "v4_real_reference_protocol_preregistration_v1.json"), "prereg_sha256": digest(OUT / "v4_real_evaluation_preregistration_freeze_v1.json")}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
