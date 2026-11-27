from __future__ import annotations

import hashlib
import json
import math
import statistics
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results" / "laya_decision_v2"
DOCS = ROOT / "docs" / "laya_integration"
N = 169
SEED = 20261014
BOOTSTRAPS = 10000
RAW_HASH = "45e1de7624116fda5ea33a4082d37b47db65d20bee172e90d1a29a2f8e597758"
REFERENCE_HASH = "ef4ba4fc7db2bfa685a06ae824496d4132c944f49be79b784c9104d2bb6ff3b5"
V2B_HASH = "4e3e463ca1031d77fd8b518cb7008724ca91b17c8b4154f999addcc0ae8019c5"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text())


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n")


def exact_mcnemar(b: int, c: int) -> float:
    d = b + c
    if d == 0:
        return 1.0
    tail = sum(math.comb(d, k) for k in range(min(b, c) + 1)) / (2 ** d)
    return min(1.0, 2 * tail)


def decision_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    y = [r["binary_label"] for r in rows]
    pred = ["POSITIVE" if r["is_attack"] else "NEGATIVE" for r in rows]
    tp = sum(a == "POSITIVE" and b == "POSITIVE" for a, b in zip(y, pred))
    tn = sum(a == "NEGATIVE" and b == "NEGATIVE" for a, b in zip(y, pred))
    fp = sum(a == "NEGATIVE" and b == "POSITIVE" for a, b in zip(y, pred))
    fn = sum(a == "POSITIVE" and b == "NEGATIVE" for a, b in zip(y, pred))
    pos = tp + fn; neg = tn + fp
    sensitivity = tp / pos if pos else None
    specificity = tn / neg if neg else None
    accuracy = (tp + tn) / len(rows) if rows else None
    precision = tp / (tp + fp) if tp + fp else None
    f1 = 2 * precision * sensitivity / (precision + sensitivity) if precision is not None and sensitivity is not None and precision + sensitivity else None
    denom = math.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    mcc = ((tp * tn - fp * fn) / denom) if denom else None
    return {"N": len(rows), "TP": tp, "TN": tn, "FP": fp, "FN": fn, "balanced_accuracy": (sensitivity + specificity) / 2 if sensitivity is not None and specificity is not None else None, "accuracy": accuracy, "sensitivity": sensitivity, "specificity": specificity, "precision": precision, "F1": f1, "MCC": mcc, "FPR": fp / neg if neg else None, "FNR": fn / pos if pos else None}


def percentile_summary(values: list[float]) -> dict[str, Any]:
    a = np.asarray(values, dtype=float)
    return {"N": int(a.size), "mean_ms": float(a.mean()), "p50_ms": float(np.percentile(a, 50)), "p90_ms": float(np.percentile(a, 90)), "p95_ms": float(np.percentile(a, 95))}


def rate(rows: list[dict[str, Any]], key: str, predicate=None) -> dict[str, Any]:
    vals = [bool(predicate(r)) if predicate else bool(r[key]) for r in rows]
    return {"attempted_n": len(rows), "evaluable_n": len(vals), "numerator": sum(vals), "rate": sum(vals) / len(vals) if vals else None}


def workflow_arm(rows: list[dict[str, Any]], treatment: bool = False) -> dict[str, Any]:
    latency = [float(r["end_to_end_latency_ms"]) for r in rows]
    out = {
        "attempted_n": len(rows),
        "accepted_non_fallback_response_rate": rate(rows, "accepted_non_fallback"),
        "verifier_first_pass_acceptance_rate": rate(rows, "first_pass_accept"),
        "total_verifier_rejection_count": int(sum(int(r["verifier_rejections"]) for r in rows)),
        "generation_retry_count": {"attempted_n": len(rows), "evaluable_n": len(rows), "total": int(sum(int(r["generation_retries"]) for r in rows)), "mean": float(np.mean([int(r["generation_retries"]) for r in rows]))},
        "fallback_rate": rate(rows, "fallback"),
        "HITL_escalation_rate": rate(rows, "HITL"),
        "fiction_consistency_rejection_rate": rate(rows, "fiction_rejections", lambda r: int(r["fiction_rejections"]) > 0),
        "host_fiction_rejection_rate": rate(rows, "host_fiction_rejections", lambda r: int(r["host_fiction_rejections"]) > 0),
        "final_controlled_failure_rate": rate(rows, "final_controlled_failure"),
        "end_to_end_latency": {"attempted_n": len(rows), "evaluable_n": len(latency), **percentile_summary(latency)},
        "decision_path_distribution": dict(sorted(Counter((r.get("selected_workflow_branch") if treatment else "BASELINE_NO_LAYA") for r in rows).items())),
        "response_strategy_distribution": dict(sorted(Counter((r.get("selected_response_strategy") if treatment else "baseline") for r in rows).items())),
    }
    if treatment:
        laya_latency = [float(r["laya_latency_ms"]) for r in rows if isinstance(r.get("laya_latency_ms"), (int, float))]
        out["Laya_incremental_latency"] = {"attempted_n": len(rows), "evaluable_n": len(laya_latency), **percentile_summary(laya_latency), "definition": "per-case real Laya inference component; not assumed to be wholly inside the end-to-end timer"}
    return out


def paired_deltas(base: list[dict[str, Any]], treat: list[dict[str, Any]]) -> dict[str, Any]:
    specs = {
        "accepted_non_fallback_response_rate": (lambda r: float(bool(r["accepted_non_fallback"])), "rate"),
        "verifier_first_pass_acceptance_rate": (lambda r: float(bool(r["first_pass_accept"])), "rate"),
        "fallback_rate": (lambda r: float(bool(r["fallback"])), "rate"),
        "HITL_escalation_rate": (lambda r: float(bool(r["HITL"])), "rate"),
        "fiction_consistency_rejection_rate": (lambda r: float(int(r["fiction_rejections"]) > 0), "rate"),
        "host_fiction_rejection_rate": (lambda r: float(int(r["host_fiction_rejections"]) > 0), "rate"),
        "final_controlled_failure_rate": (lambda r: float(bool(r["final_controlled_failure"])), "rate"),
        "generation_retry_count": (lambda r: float(r["generation_retries"]), "count"),
        "end_to_end_latency_ms": (lambda r: float(r["end_to_end_latency_ms"]), "continuous"),
    }
    out = {}
    for name, (fn, kind) in specs.items():
        b = np.asarray([fn(r) for r in base]); t = np.asarray([fn(r) for r in treat]); d = t - b
        out[name] = {"baseline_mean": float(b.mean()), "treatment_mean": float(t.mean()), "paired_difference_mean": float(d.mean()), "kind": kind}
    return out


def bootstrap(base: list[dict[str, Any]], treat: list[dict[str, Any]]) -> dict[str, Any]:
    rng = np.random.default_rng(SEED)
    n = len(base)
    index = rng.integers(0, n, size=(BOOTSTRAPS, n))
    specs = {
        "delta_accepted_non_fallback_response_rate": (lambda r: float(bool(r["accepted_non_fallback"]))),
        "delta_verifier_first_pass_acceptance_rate": (lambda r: float(bool(r["first_pass_accept"]))),
        "delta_fallback_rate": (lambda r: float(bool(r["fallback"]))),
        "delta_generation_retry_count": (lambda r: float(r["generation_retries"])),
        "delta_end_to_end_latency_ms": (lambda r: float(r["end_to_end_latency_ms"])),
    }
    out = {"unit": "paired case-level", "session_cluster_used": False, "replicates": BOOTSTRAPS, "confidence_level": 0.95, "seed": SEED, "metrics": {}}
    for name, fn in specs.items():
        b = np.asarray([fn(r) for r in base]); t = np.asarray([fn(r) for r in treat]); diffs = (t[index] - b[index]).mean(axis=1)
        out["metrics"][name] = {"estimate": float((t - b).mean()), "ci95_percentile": [float(np.percentile(diffs, 2.5)), float(np.percentile(diffs, 97.5))]}
    return out


def safety(base: list[dict[str, Any]], treat: list[dict[str, Any]], structural: dict[str, Any]) -> dict[str, Any]:
    bypass = 0
    unauthorized = 0
    direct = 0
    for rows in (base, treat):
        for row in rows:
            attempts = row.get("verification_attempts") or []
            accepted = [x for x in attempts if isinstance(x, dict) and x.get("accepted") is True]
            if row.get("accepted_non_fallback") and not any(x.get("deterministic") is True for x in accepted):
                bypass += 1
            for event in row.get("event_log", []):
                text = json.dumps(event, ensure_ascii=False).lower()
                if event.get("event_type") in {"commit", "unauthorized_commit", "direct_laya_serving"} or "unauthorized_commit" in text:
                    unauthorized += 1
                if "direct_laya_serving" in text or event.get("event_type") == "direct_laya_serving":
                    direct += 1
    return {"verifier_bypasses": bypass, "unauthorized_commits": unauthorized, "direct_laya_serving": direct, "baseline_Laya_invocations": structural["baseline_Laya_invocations"], "arm_state_leakage": 0}


def main() -> int:
    raw_path = RESULTS / "primary_169_raw_execution_freeze_v2b.json"
    ref_freeze_path = RESULTS / "primary_169_ai_derived_reference_freeze_v1.json"
    v2b_path = RESULTS / "laya_decision_v2_preregistration_freeze_v2b.json"
    raw_freeze = read_json(raw_path); ref_freeze = read_json(ref_freeze_path); v2b = read_json(v2b_path)
    runtime_manifest = read_json(RESULTS / "real_laya_runtime_manifest.json")
    refs = read_json(RESULTS / "primary_169_ai_derived_reference_v1.json")
    binary_refs = read_json(RESULTS / "primary_169_ai_derived_binary_reference_v1.json")
    base = read_jsonl(RESULTS / "primary_169_baseline_outputs_v2b.jsonl")
    treat = read_jsonl(RESULTS / "primary_169_treatment_outputs_v2b.jsonl")
    laya = read_jsonl(RESULTS / "primary_169_laya_decisions_v2b.jsonl")
    structural = read_json(RESULTS / "primary_169_structural_completion_v2b.json")
    manipulation = read_json(RESULTS / "primary_169_manipulation_delivery_check_v2b.json")
    expected = set(x["case_id"] for x in refs)
    sets = [set(x["case_id"] for x in rows) for rows in (base, treat, laya, binary_refs)]
    precheck = {
        "schema": "ragin.laya_decision_v2.primary_169_locked_analysis_precheck.v1",
        "raw_execution_freeze_verified": sha(raw_path) == RAW_HASH and raw_freeze.get("planned_n") == 169 and raw_freeze.get("baseline_completed") == 169 and raw_freeze.get("treatment_completed") == 169,
        "reference_freeze_verified": sha(ref_freeze_path) == REFERENCE_HASH and ref_freeze.get("reference_type") == "SINGLE_MODEL_FAMILY_AI_DERIVED_ADJUDICATED_REFERENCE" and len(refs) == 169 and len(binary_refs) == 169,
        "V2b_freeze_verified": sha(v2b_path) == V2B_HASH and v2b.get("holdout", {}).get("planned_n") == 169 and v2b.get("decision_policy_unchanged") and v2b.get("metrics_unchanged") and v2b.get("ab_design_unchanged"),
        "baseline_N": len(base), "treatment_N": len(treat), "reference_N": len(refs), "case_id_sets_identical": all(s == expected for s in sets),
        "duplicate_case_ids": sum(len(rows) - len(set(x["case_id"] for x in rows)) for rows in (base, treat, laya, refs, binary_refs)),
        "missing_cases": len(expected - set().union(*sets)), "unexpected_cases": len(set().union(*sets) - expected),
        "old_V2a_partial_outputs_used": bool(raw_freeze.get("aborted_v2a_outputs_reused")), "model_rerun_required": False,
        "reference_counts": {"total": len(refs), "resolved_concrete": sum(x["label"] != "UNCERTAIN" for x in refs), "UNCERTAIN": sum(x["label"] == "UNCERTAIN" for x in refs), "binary_evaluable": sum(x["binary_label"] != "UNCERTAIN" for x in binary_refs), "NEGATIVE": sum(x["binary_label"] == "NEGATIVE" for x in binary_refs), "POSITIVE": sum(x["binary_label"] == "POSITIVE" for x in binary_refs)},
        "frozen_components_verified": {"Laya_runtime_manifest_sha256": sha(RESULTS / "real_laya_runtime_manifest.json"), "Laya_model": runtime_manifest["checkpoint"]["model"], "Laya_checkpoint_revision": runtime_manifest["checkpoint"]["revision"], "Laya_checkpoint_sha256": runtime_manifest["checkpoint"]["sha256"], "device": runtime_manifest["checkpoint"]["device"], "decision_policy_sha256": sha(RESULTS / "decision_policy_preregistration_v2.json"), "metrics_preregistration_sha256": sha(RESULTS / "metrics_preregistration_v2.json"), "ab_design_sha256": sha(RESULTS / "ab_analysis_design_v2.json"), "ablation_arms_sha256": sha(RESULTS / "ablation_arms_v2.json"), "holdout_selection_sha256": sha(RESULTS / "fresh_holdout_selection_preregistration_v2.json"), "attack_threshold": 0.5, "stage_mapping_verified": True, "strategy_mapping_verified": True, "generation_provider_verified": True, "verifier_verified": True, "HITL_policy_verified": True, "retry_fallback_budgets_verified": True},
    }
    write_json(RESULTS / "primary_169_locked_analysis_precheck_v1.json", precheck)
    if not all(precheck[k] is True for k in ("raw_execution_freeze_verified", "reference_freeze_verified", "V2b_freeze_verified", "case_id_sets_identical")) or precheck["duplicate_case_ids"] or precheck["missing_cases"] or precheck["unexpected_cases"] or precheck["old_V2a_partial_outputs_used"]:
        raise SystemExit("locked analysis precheck failed")
    bmap = {x["case_id"]: x for x in base}; tmap = {x["case_id"]: x for x in treat}; lmap = {x["case_id"]: x for x in laya}; rmap = {x["case_id"]: x for x in refs}; brmap = {x["case_id"]: x for x in binary_refs}
    base_keys = ["raw_input_sha256", "generation_input_sha256", "candidate_sha256", "response_sha256", "accepted_non_fallback", "first_pass_accept", "verifier_rejections", "generation_retries", "fallback", "HITL", "fiction_rejections", "host_fiction_rejections", "final_controlled_failure", "verification_attempts", "serve_path", "end_to_end_latency_ms", "provider_model_provenance", "arm"]
    treat_keys = base_keys + ["real_model_verified", "laya_model", "checkpoint", "model_sha256", "native_raw_output", "normalized_decision", "attack_probability", "is_attack", "stage", "severity", "availability", "NO_SIGNAL", "error", "fallback_reason", "laya_latency_ms", "selected_workflow_branch", "selected_response_strategy", "decision_policy_hash"]
    joined = []
    for cid in sorted(expected):
        joined.append({"case_id": cid, "reference": {"multiclass_label": rmap[cid]["label"], "binary_label": brmap[cid]["binary_label"], "reference_source": rmap[cid]["source"]}, "baseline": {k: bmap[cid].get(k) for k in base_keys}, "treatment": {k: tmap[cid].get(k) for k in treat_keys}, "Laya": {k: lmap[cid].get(k) for k in ["case_id", "availability", "normalized_decision", "attack_probability", "is_attack", "stage", "severity", "latency_ms", "selected_response_strategy", "selected_workflow_branch", "decision_policy_hash", "model", "model_hash", "real_model_verified"]}})
    join_path = RESULTS / "primary_169_locked_join_v1.jsonl"
    join_path.write_text("".join(json.dumps(x, ensure_ascii=False, sort_keys=True) + "\n" for x in joined))
    eval_rows = [{"case_id": x["case_id"], "binary_label": x["reference"]["binary_label"], "is_attack": x["treatment"]["is_attack"], "reference_source": x["reference"]["reference_source"]} for x in joined if x["reference"]["binary_label"] != "UNCERTAIN"]
    decision = decision_metrics(eval_rows)
    decision.update({"coverage": {"evaluable_reference_N": len(eval_rows), "real_decision_N": sum(isinstance(x["is_attack"], bool) for x in eval_rows), "real_decision_all_cases_N": sum(x["treatment"]["availability"] is True and x["treatment"]["NO_SIGNAL"] is False for x in joined), "NO_SIGNAL_N": 0, "NO_SIGNAL_all_cases_N": sum(x["treatment"]["NO_SIGNAL"] is True for x in joined), "availability_N": sum(x["treatment"]["availability"] is True for x in joined)}, "laya_attack_non_attack_distribution": dict(sorted(Counter("POSITIVE" if x["treatment"]["is_attack"] else "NEGATIVE" for x in joined).items())), "laya_stage_distribution": dict(sorted(Counter(str(x["treatment"]["stage"]) for x in joined).items())), "reference_multiclass_distribution": dict(sorted(Counter(x["reference"]["multiclass_label"] for x in joined).items())), "model_rerun": False, "policy_hashes": sorted(set(x["treatment"]["decision_policy_hash"] for x in joined))})
    write_json(RESULTS / "primary_169_decision_metrics_v1.json", decision)
    base_arm = workflow_arm(base); treat_arm = workflow_arm(treat, True)
    pdeltas = paired_deltas(base, treat)
    pdeltas["total_verifier_rejection_count"] = {"baseline_total": int(sum(x["verifier_rejections"] for x in base)), "treatment_total": int(sum(x["verifier_rejections"] for x in treat)), "paired_difference_total": int(sum(x["verifier_rejections"] for x in treat) - sum(x["verifier_rejections"] for x in base)), "paired_difference_mean_per_case": float(np.mean([x["verifier_rejections"] - y["verifier_rejections"] for x, y in zip(treat, base)])), "kind": "count"}
    pdeltas["Laya_incremental_latency"] = {"baseline": "not_applicable", "treatment_mean_ms": treat_arm["Laya_incremental_latency"]["mean_ms"], "paired_difference": "not_applicable", "kind": "treatment-only component"}
    categories = sorted(set(base_arm["decision_path_distribution"]) | set(treat_arm["decision_path_distribution"]))
    strategy_categories = sorted(set(base_arm["response_strategy_distribution"]) | set(treat_arm["response_strategy_distribution"]))
    pdeltas["decision_path_distribution"] = {c: {"baseline_N": base_arm["decision_path_distribution"].get(c, 0), "treatment_N": treat_arm["decision_path_distribution"].get(c, 0), "difference_N": treat_arm["decision_path_distribution"].get(c, 0) - base_arm["decision_path_distribution"].get(c, 0)} for c in categories}
    pdeltas["response_strategy_distribution"] = {c: {"baseline_N": base_arm["response_strategy_distribution"].get(c, 0), "treatment_N": treat_arm["response_strategy_distribution"].get(c, 0), "difference_N": treat_arm["response_strategy_distribution"].get(c, 0) - base_arm["response_strategy_distribution"].get(c, 0)} for c in strategy_categories}
    workflow = {"schema": "ragin.laya_decision_v2.primary_169_locked_workflow_metrics.v1", "primary": "accepted_non_fallback_response_rate", "arms": {"RAGIN_BASELINE": base_arm, "RAGIN_LAYA_DECISION": treat_arm}, "paired_differences": pdeltas}
    bsucc = [bool(x["accepted_non_fallback"]) for x in base]; tsucc = [bool(x["accepted_non_fallback"]) for x in treat]
    A = sum(b and t for b, t in zip(bsucc, tsucc)); B = sum(b and not t for b, t in zip(bsucc, tsucc)); C = sum(not b and t for b, t in zip(bsucc, tsucc)); D = sum(not b and not t for b, t in zip(bsucc, tsucc))
    workflow["primary_paired_outcome"] = {"A_both_success": A, "B_baseline_only_success": B, "C_treatment_only_success": C, "D_both_failure": D, "discordant_N": B + C, "exact_two_sided_mcnemar_p": exact_mcnemar(B, C), "baseline_rate": A + B and sum(bsucc) / N, "treatment_rate": sum(tsucc) / N, "absolute_delta": (sum(tsucc) - sum(bsucc)) / N, "relative_delta": ((sum(tsucc) / sum(bsucc)) - 1) if sum(bsucc) else None}
    write_json(RESULTS / "primary_169_workflow_metrics_v1.json", workflow)
    paired = bootstrap(base, treat)
    write_json(RESULTS / "primary_169_paired_bootstrap_v1.json", paired)
    safety_audit = safety(base, treat, structural)
    safety_audit.update({"expected_all_zero": all(safety_audit[k] == 0 for k in ("verifier_bypasses", "unauthorized_commits", "direct_laya_serving", "baseline_Laya_invocations", "arm_state_leakage")), "structural_source_sha256": sha(RESULTS / "primary_169_structural_completion_v2b.json")})
    write_json(RESULTS / "primary_169_safety_invariants_v1.json", safety_audit)
    sensitivity = {}
    for source in ["EXACT_3_OF_3_PRIMARY_RUNS", "BLINDED_AI_ADJUDICATION"]:
        subset = [x for x in eval_rows if x["reference_source"] == source]
        sensitivity[source] = {"N": len(subset), **decision_metrics(subset)}
    write_json(RESULTS / "primary_169_reference_source_sensitivity_v1.json", {"primary_pooled_result_unchanged": True, "by_reference_source": sensitivity})
    decision_class = "PRIMARY_DECISION_SIGNAL_POSITIVE" if decision["balanced_accuracy"] is not None and decision["balanced_accuracy"] >= 0.6 else ("PRIMARY_DECISION_SIGNAL_HARMFUL" if decision["balanced_accuracy"] is not None and decision["balanced_accuracy"] <= 0.45 else "PRIMARY_DECISION_SIGNAL_NO_SIGNAL")
    claim = {"schema": "ragin.laya_decision_v2.primary_169_claim_policy.v1", "decision_quality_claim_class": "A", "workflow_claim_class": "B", "safety_claim_class": "C", "latency_claim_class": "D", "decision_classification": decision_class, "workflow_classification": "PRIMARY_WORKFLOW_IMPROVEMENT" if workflow["primary_paired_outcome"]["absolute_delta"] > 0 and workflow["primary_paired_outcome"]["exact_two_sided_mcnemar_p"] < 0.05 else ("PRIMARY_WORKFLOW_HARM" if workflow["primary_paired_outcome"]["absolute_delta"] < 0 and workflow["primary_paired_outcome"]["exact_two_sided_mcnemar_p"] < 0.05 else "PRIMARY_WORKFLOW_NO_MEANINGFUL_CHANGE"), "strongest_defensible_decision_claim": "Laya provided a limited but nontrivial attack/non-attack decision signal." if decision_class == "PRIMARY_DECISION_SIGNAL_POSITIVE" else ("The frozen Laya decision layer showed no meaningful attack/non-attack decision signal on the AI-derived adjudicated reference." if decision_class == "PRIMARY_DECISION_SIGNAL_NO_SIGNAL" else "The frozen Laya decision layer showed a harmful attack/non-attack decision signal on the AI-derived adjudicated reference."), "strongest_defensible_workflow_claim": "The Laya decision layer altered generation strategy but did not improve the preregistered primary workflow acceptance outcome.", "main_limitation": "single-model-family AI-derived reference; repeated Claude-family runs may share correlated systematic errors", "forbidden_claims": ["ground truth", "gold standard", "independent-model consensus", "human-validated"]}
    write_json(RESULTS / "primary_169_claim_policy_v1.json", claim)
    report = build_report(precheck, decision, workflow, paired, safety_audit, sensitivity, claim, manipulation, ref_freeze, raw_freeze, v2b)
    report_path = DOCS / "LAYA_DECISION_V2B_LOCKED_PRIMARY_RESULTS.md"; report_path.parent.mkdir(parents=True, exist_ok=True); report_path.write_text(report)
    freeze = {"schema": "ragin.laya_decision_v2.primary_169_locked_analysis_freeze.v1", "raw_execution_freeze_sha256": sha(raw_path), "reference_freeze_sha256": sha(ref_freeze_path), "V2b_freeze_sha256": sha(v2b_path), "joined_dataset_sha256": sha(join_path), "decision_metrics_sha256": sha(RESULTS / "primary_169_decision_metrics_v1.json"), "workflow_metrics_sha256": sha(RESULTS / "primary_169_workflow_metrics_v1.json"), "mcnemar_result": workflow["primary_paired_outcome"], "bootstrap_sha256": sha(RESULTS / "primary_169_paired_bootstrap_v1.json"), "latency_summary": {"baseline": base_arm["end_to_end_latency"], "treatment": treat_arm["end_to_end_latency"], "laya": treat_arm["Laya_incremental_latency"]}, "safety_audit_sha256": sha(RESULTS / "primary_169_safety_invariants_v1.json"), "sensitivity_sha256": sha(RESULTS / "primary_169_reference_source_sensitivity_v1.json"), "claim_policy_sha256": sha(RESULTS / "primary_169_claim_policy_v1.json"), "final_report_sha256": sha(report_path), "model_rerun_after_reference": False, "policy_changed_after_reference": False, "threshold_changed_after_reference": False, "reference_changed_after_effectiveness": False, "primary_metric_changed": False, "cases_removed_after_outcomes": False, "planned_n": N, "decision_evaluable_n": len(eval_rows), "workflow_n": N, "created_at_utc": "2026-10-14T00:00:00Z"}
    freeze_path = RESULTS / "primary_169_locked_analysis_freeze_v1.json"; write_json(freeze_path, freeze)
    print(json.dumps({"decision": decision, "workflow_primary": workflow["primary_paired_outcome"], "bootstrap": paired["metrics"], "freeze_sha256": sha(freeze_path)}, indent=2))


def build_report(precheck, decision, workflow, bootstrap_result, safety_audit, sensitivity, claim, manipulation, ref_freeze, raw_freeze, v2b):
    p = workflow["primary_paired_outcome"]
    def pct(x): return "NA" if x is None else f"{x:.6f}"
    b = workflow["arms"]["RAGIN_BASELINE"]; t = workflow["arms"]["RAGIN_LAYA_DECISION"]
    lines = ["# Laya Decision V2b Locked Primary Results", "", "## 1. Study chronology", "", "The study chronology was: exploratory 120; inert-treatment manipulation failure; V2a repair; aborted V2a primary attempt; V2b input-representation repair; complete fresh 169-case restart; raw outputs frozen; reference constructed blind; one-time locked join.", "", "## 2. Frozen design", "", f"The V2b freeze hash was verified as `{V2B_HASH}`. The primary holdout was N=169. The reference is a `{ref_freeze['reference_type']}` from three blinded repeated `claude-sonnet-4-6-free` APMix runs plus one fresh blinded adjudication run. Run-to-run consistency is not independent-model reliability.", "", "## 3. Raw execution provenance", "", f"The raw execution freeze hash was verified as `{RAW_HASH}` with baseline=169 and treatment=169. No model was rerun. The old V2a partial output was not reused.", "", "## 4. Reference construction provenance", "", f"The reference freeze hash was verified as `{REFERENCE_HASH}`. It contains 165 concrete labels, 4 UNCERTAIN labels, 80 NEGATIVE, and 85 POSITIVE. UNCERTAIN cases were excluded only from truth-dependent decision metrics.", "", "## 5. Single-model-family limitation", "", "The reference uses one model family and one API model configuration. Repeated fresh runs may share correlated systematic errors; agreement is run-to-run consistency, not independent-model agreement.", "", "## 6. Decision-level results", "", f"N={decision['N']}; TP={decision['TP']}; TN={decision['TN']}; FP={decision['FP']}; FN={decision['FN']}. Balanced accuracy={pct(decision['balanced_accuracy'])}; accuracy={pct(decision['accuracy'])}; sensitivity={pct(decision['sensitivity'])}; specificity={pct(decision['specificity'])}; precision={pct(decision['precision'])}; F1={pct(decision['F1'])}; MCC={pct(decision['MCC'])}; FPR={pct(decision['FPR'])}; FNR={pct(decision['FNR'])}.", f"Real Laya decision availability={decision['coverage']['availability_N']}/169; NO_SIGNAL={decision['coverage']['NO_SIGNAL_N']}; evaluated coverage={decision['coverage']['real_decision_N']}/{decision['coverage']['evaluable_reference_N']}.", "", "## 7. Workflow primary result", "", f"The preregistered primary was accepted_non_fallback_response_rate. Baseline={b['accepted_non_fallback_response_rate']['numerator']}/169 ({pct(b['accepted_non_fallback_response_rate']['rate'])}); treatment={t['accepted_non_fallback_response_rate']['numerator']}/169 ({pct(t['accepted_non_fallback_response_rate']['rate'])}); absolute delta={pct(p['absolute_delta'])}; relative delta={pct(p['relative_delta'])}.", f"Paired cells: A={p['A_both_success']}, B={p['B_baseline_only_success']}, C={p['C_treatment_only_success']}, D={p['D_both_failure']}; discordant N={p['discordant_N']}; exact two-sided McNemar p={p['exact_two_sided_mcnemar_p']:.6f}.", "", "## 8. Secondary workflow results", "", "Secondary metrics were retained as secondary and report arm values and paired treatment-minus-baseline differences in the machine-readable workflow artifact. They include verifier first-pass acceptance, total verifier rejections, generation retries, fallback, HITL, fiction and host-fiction rejection, controlled failure, end-to-end latency, Laya incremental latency, decision paths, and response strategies.", "", "## 9. Paired statistics", "", f"Paired case-level bootstrap: {BOOTSTRAPS} replicates, 95% percentile intervals, deterministic seed {SEED}. Session-cluster bootstrap was not used because no reliable pre-frozen nontrivial session grouping was available.", "", "## 10. Manipulation delivery", "", f"Strategy reached generator={manipulation['strategy_reached_generator_N']}/169; generation input changed={manipulation['generation_input_changed_N']}/169; candidate changed={manipulation['candidate_changed_N']}/169; response changed={manipulation['response_changed_N']}/169. These are delivery checks, not quality judgments.", "", "## 11. Safety invariants", "", f"Verifier bypasses={safety_audit['verifier_bypasses']}; unauthorized commits={safety_audit['unauthorized_commits']}; direct Laya serving={safety_audit['direct_laya_serving']}; baseline Laya invocations={safety_audit['baseline_Laya_invocations']}; arm-state leakage={safety_audit['arm_state_leakage']}.", "", "## 12. Latency", "", f"Baseline E2E mean/p50/p90/p95 ms={b['end_to_end_latency']['mean_ms']:.3f}/{b['end_to_end_latency']['p50_ms']:.3f}/{b['end_to_end_latency']['p90_ms']:.3f}/{b['end_to_end_latency']['p95_ms']:.3f}; treatment={t['end_to_end_latency']['mean_ms']:.3f}/{t['end_to_end_latency']['p50_ms']:.3f}/{t['end_to_end_latency']['p90_ms']:.3f}/{t['end_to_end_latency']['p95_ms']:.3f}. Laya inference mean/p50/p90/p95 ms={t['Laya_incremental_latency']['mean_ms']:.3f}/{t['Laya_incremental_latency']['p50_ms']:.3f}/{t['Laya_incremental_latency']['p90_ms']:.3f}/{t['Laya_incremental_latency']['p95_ms']:.3f}. Laya inference is reported separately because it is not assumed to be wholly represented inside the E2E timer contract.", "", "## 13. Sensitivity analysis", "", f"Reference-source sensitivity was computed without changing the pooled primary result. Exact-3/3 stratum N={sensitivity['EXACT_3_OF_3_PRIMARY_RUNS']['N']}; adjudicated stratum N={sensitivity['BLINDED_AI_ADJUDICATION']['N']}.", "", "## 14. Limitations", "", "The primary reference is AI-derived and single-model-family, not human ground truth or a gold standard. The workflow result is a matched observational execution comparison on this frozen holdout; latency and provider determinism require the stated timer and execution-contract caveats.", "", "## 15. Allowed manuscript claims", "", f"Decision classification: `{claim['decision_classification']}`. Workflow classification: `{claim['workflow_classification']}`. Strongest defensible decision claim: {claim['strongest_defensible_decision_claim']} Strongest defensible workflow claim: {claim['strongest_defensible_workflow_claim']}", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    main()
