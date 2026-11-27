from __future__ import annotations

import hashlib
import json
import pathlib
import random
from collections import Counter, defaultdict


ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE = ROOT / "results" / "evidence_judge_real_data_ablation_v1"
WORK = BASE / "ai_reference_v2_2"
PAIRED = ROOT / "results" / "evidence_judge_real_data_final_paired_audit_v1"
REFERENCE = WORK / "reference_freeze_v2_2.json"
REFERENCE_MANIFEST = WORK / "reference_freeze_manifest_v2_2.json"
ARMS = BASE / "matched_arm_results.json"
CASE_COMPARISON = PAIRED / "case_level_comparison.json"
EXPECTED = {
    str(ARMS.relative_to(ROOT)): "d67449c247741824c56d11548e39aca23e7ddaa9e578ce84706e7a7c84d0a572",
    str(CASE_COMPARISON.relative_to(ROOT)): "853d4295030ec04f22beee8c6342e71ccba35c586e8a3ec2f51555fcadc524f9",
}


def sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: pathlib.Path):
    return json.loads(path.read_text(encoding="utf-8"))


def ratio(a: int, b: int) -> float | None:
    return a / b if b else None


def cluster_interval(groups: dict[str, tuple[int, int]], seed: int = 20261014, reps: int = 10000) -> dict:
    keys = sorted(groups)
    if not keys:
        return {"estimate": None, "ci95": None, "clusters": 0, "bootstrap_replicates": reps}
    numerator = sum(groups[key][0] for key in keys)
    denominator = sum(groups[key][1] for key in keys)
    estimate = ratio(numerator, denominator)
    rng = random.Random(seed)
    values = []
    for _ in range(reps):
        selected = [keys[rng.randrange(len(keys))] for _ in keys]
        den = sum(groups[key][1] for key in selected)
        num = sum(groups[key][0] for key in selected)
        if den:
            values.append(num / den)
    values.sort()
    if not values:
        interval = None
    else:
        interval = [values[int(0.025 * (len(values) - 1))], values[int(0.975 * (len(values) - 1))]]
    return {"estimate": estimate, "ci95": interval, "clusters": len(keys), "bootstrap_replicates": reps, "seed": seed, "unit": "case_id"}


def main() -> int:
    if not REFERENCE.exists() or not REFERENCE_MANIFEST.exists():
        raise SystemExit("BLOCKED_REFERENCE_NOT_FROZEN")
    reference_manifest = load(REFERENCE_MANIFEST)
    reference = load(REFERENCE)
    if sha(REFERENCE) != reference_manifest.get("reference_sha256"):
        raise SystemExit("BLOCKED_REFERENCE_HASH_MISMATCH")
    if reference.get("status") != "AI_DERIVED_REFERENCE_FROZEN" or reference.get("human_ground_truth") is not False:
        raise SystemExit("BLOCKED_REFERENCE_TYPE_MISMATCH")
    hashes = {}
    for rel, expected in EXPECTED.items():
        path = ROOT / rel
        actual = sha(path)
        hashes[rel] = {"expected_sha256": expected, "actual_sha256": actual, "matches": actual == expected}
        if actual != expected:
            raise SystemExit("BLOCKED_FROZEN_ARM_HASH_MISMATCH: " + rel)
    arm_doc = load(ARMS)
    case_doc = load(CASE_COMPARISON)
    arm_rows = {row["case_id"]: row for row in arm_doc["results"]}
    comparison_rows = {row["case_id"]: row for row in case_doc["cases"]}
    reference_rows = {row["case_id"]: row for row in reference["cases"]}
    if not (len(arm_rows) == len(comparison_rows) == len(reference_rows) == 120):
        raise SystemExit("BLOCKED_CASE_COVERAGE_MISMATCH")
    candidate_matrix = Counter()
    binary_matrix = Counter()
    bundle_matrix = Counter()
    invalid_ids = []
    candidate_rows = 0
    candidate_unknown = 0
    unsupported_admissions = Counter()
    missed_direct_support = Counter()
    exact_groups = defaultdict(lambda: [0, 0])
    unsupported_groups = defaultdict(lambda: [0, 0])
    missed_groups = defaultdict(lambda: [0, 0])
    direct_recall_groups = defaultdict(lambda: [0, 0])
    specificity_groups = defaultdict(lambda: [0, 0])
    precision_groups = defaultdict(lambda: [0, 0])
    binary_accuracy_groups = defaultdict(lambda: [0, 0])
    bundle_exact_groups = defaultdict(lambda: [0, 0])
    bundle_binary_groups = defaultdict(lambda: [0, 0])
    case_reference_counts = Counter()

    for case_id, ref_case in reference_rows.items():
        result = arm_rows[case_id]
        comp = comparison_rows[case_id]
        judge = result["arm_b"].get("judge", {})
        judge_candidates = {row["doc_id"]: row["label"] for row in judge.get("candidate_judgments", [])}
        ref_candidates = {row["doc_id"]: row for row in ref_case["candidate_reviews"]}
        if set(judge_candidates) != set(ref_candidates):
            invalid_ids.append(case_id)
        for doc_id, ref in ref_candidates.items():
            candidate_rows += 1
            truth = ref["label"]
            predicted = judge_candidates.get(doc_id, "MISSING")
            case_reference_counts[truth] += 1
            if truth == "UNKNOWN":
                candidate_unknown += 1
                continue
            direct = truth == "DIRECT_SUPPORT"
            admitted = predicted == "SUPPORTED"
            binary_matrix[("DIRECT_SUPPORT" if direct else "NON_DIRECT_SUPPORT", "SUPPORTED" if admitted else "NOT_SUPPORTED")] += 1
            binary_accuracy_groups[case_id][1] += 1
            binary_accuracy_groups[case_id][0] += direct == admitted
            exact_truth = truth
            exact_prediction = {"SUPPORTED": "DIRECT_SUPPORT", "PARTIAL": "PARTIAL", "IRRELEVANT": "IRRELEVANT"}.get(predicted, predicted)
            candidate_matrix[(exact_truth, exact_prediction)] += 1
            exact_groups[case_id][1] += 1
            exact_groups[case_id][0] += exact_truth == exact_prediction
            if truth in {"PARTIAL", "IRRELEVANT", "CONTRADICTORY"}:
                unsupported_groups[case_id][1] += 1
                unsupported_groups[case_id][0] += admitted
                specificity_groups[case_id][1] += 1
                specificity_groups[case_id][0] += not admitted
                unsupported_admissions[truth] += admitted
            if admitted:
                precision_groups[case_id][1] += 1
                precision_groups[case_id][0] += direct
            if direct:
                missed_groups[case_id][1] += 1
                missed_groups[case_id][0] += not admitted
                direct_recall_groups[case_id][1] += 1
                direct_recall_groups[case_id][0] += admitted
                missed_direct_support[predicted] += not admitted

        system_bundle = comp["bundle_sufficiency"]
        ai_bundle = ref_case["bundle_review"]["label"]
        if ai_bundle != "UNKNOWN":
            bundle_exact_groups[case_id][1] += 1
            bundle_exact_groups[case_id][0] += system_bundle == ai_bundle
            ai_sufficient = ai_bundle == "SUFFICIENT"
            system_sufficient = system_bundle == "SUFFICIENT"
            bundle_matrix[("SUFFICIENT" if ai_sufficient else "NOT_SUFFICIENT", "SUFFICIENT" if system_sufficient else "NOT_SUFFICIENT")] += 1
            bundle_binary_groups[case_id][1] += 1
            bundle_binary_groups[case_id][0] += ai_sufficient == system_sufficient

    candidate_evaluable = sum(case_reference_counts.values()) - candidate_unknown
    bundle_unknown = reference["bundle_label_counts"].get("UNKNOWN", 0)
    gate_pairs = Counter((row["arm_a_gate_state"], row["arm_b_gate_state"]) for row in case_doc["cases"])
    retained_equal = sum(row["arm_a_candidate_ids_retained"] == row["arm_b_candidate_ids_retained"] for row in case_doc["cases"])
    arm_a_retained = sum(len(row["arm_a_candidate_ids_retained"]) for row in case_doc["cases"])
    arm_b_retained = sum(len(row["arm_b_candidate_ids_retained"]) for row in case_doc["cases"])
    run_manifest = load(WORK / "run_manifest_v2_2.json")
    call_errors = sum(len(row.get("validation_errors", [])) for row in run_manifest["calls"])
    call_coverage = {"scheduled_batches": 6, "recorded_calls": len(run_manifest["calls"]), "schema_valid_calls": sum(bool(row.get("json_valid")) for row in run_manifest["calls"]), "fully_valid_calls": sum(bool(row.get("json_valid")) and not row.get("validation_errors") for row in run_manifest["calls"]), "field_validation_errors": call_errors}
    report = {
        "schema": "ragin.locked_evidence_support_evaluation.v2.2",
        "status": "LOCKED_DESCRIPTIVE_ANALYSIS",
        "reference_type": reference["reference_type"],
        "human_ground_truth": False,
        "single_model_dependence_warning": "All evidence-support labels are from one fixed Codex reviewer; metrics are descriptive and are not independent adjudication.",
        "reference_sha256": sha(REFERENCE),
        "reference_manifest_sha256": sha(REFERENCE_MANIFEST),
        "analysis_script_sha256": sha(pathlib.Path(__file__)),
        "supersedes_preliminary_analysis_sha256": sha(WORK / "locked_evaluation_v2_2.json") if (WORK / "locked_evaluation_v2_2.json").exists() else None,
        "matched_arm_and_case_comparison_hashes": hashes,
        "matched_arm_source_sha256": case_doc["source_matched_results_sha256"],
        "case_count": len(reference_rows),
        "candidate_slots": candidate_rows,
        "candidate_unknown_excluded": candidate_unknown,
        "candidate_evaluable": candidate_evaluable,
        "reference_candidate_label_counts": dict(sorted(case_reference_counts.items())),
        "ai_reviewer_call_coverage": call_coverage,
        "candidate_crosswalk": "SUPPORTED maps to DIRECT_SUPPORT; PARTIAL and IRRELEVANT map to matching labels; contradictory evidence has no distinct Judge output.",
        "candidate_reference_by_judge_confusion": {"rows": sorted({k[0] for k in candidate_matrix}), "columns": sorted({k[1] for k in candidate_matrix}), "counts": {f"{a}|{b}": n for (a, b), n in sorted(candidate_matrix.items())}},
        "direct_support_binary_confusion": {"positive": "AI DIRECT_SUPPORT / Judge SUPPORTED", "counts": {f"{a}|{b}": n for (a, b), n in sorted(binary_matrix.items())}},
        "candidate_metrics": {
            "direct_support_recall": {"numerator": sum(value[0] for value in direct_recall_groups.values()), "denominator": sum(value[1] for value in direct_recall_groups.values()), "value": ratio(sum(value[0] for value in direct_recall_groups.values()), sum(value[1] for value in direct_recall_groups.values())), "case_cluster_bootstrap": cluster_interval({key: tuple(value) for key, value in direct_recall_groups.items()})},
            "direct_support_precision": {"numerator": sum(value[0] for value in precision_groups.values()), "denominator": sum(value[1] for value in precision_groups.values()), "value": ratio(sum(value[0] for value in precision_groups.values()), sum(value[1] for value in precision_groups.values())), "case_cluster_bootstrap": cluster_interval({key: tuple(value) for key, value in precision_groups.items()})},
            "non_direct_specificity": {"numerator": sum(value[0] for value in specificity_groups.values()), "denominator": sum(value[1] for value in specificity_groups.values()), "value": ratio(sum(value[0] for value in specificity_groups.values()), sum(value[1] for value in specificity_groups.values())), "case_cluster_bootstrap": cluster_interval({key: tuple(value) for key, value in specificity_groups.items()})},
            "binary_accuracy": {"numerator": sum(value[0] for value in binary_accuracy_groups.values()), "denominator": sum(value[1] for value in binary_accuracy_groups.values()), "value": ratio(sum(value[0] for value in binary_accuracy_groups.values()), sum(value[1] for value in binary_accuracy_groups.values())), "case_cluster_bootstrap": cluster_interval({key: tuple(value) for key, value in binary_accuracy_groups.items()})},
            "unsupported_direct_admissions_by_reference_label": dict(unsupported_admissions),
            "false_rejection_of_direct_support_by_judge_label": dict(missed_direct_support),
            "unsupported_admission_rate_over_non_direct_evaluable": {"numerator": sum(unsupported_admissions.values()), "denominator": sum(v[1] for k, v in unsupported_groups.items()), "value": ratio(sum(unsupported_admissions.values()), sum(v[1] for v in unsupported_groups.values())), "case_cluster_bootstrap": cluster_interval({key: tuple(value) for key, value in unsupported_groups.items()})},
            "false_rejection_rate_over_direct_support": {"numerator": sum(missed_direct_support.values()), "denominator": sum(v[1] for v in missed_groups.values()), "value": ratio(sum(missed_direct_support.values()), sum(v[1] for v in missed_groups.values())), "case_cluster_bootstrap": cluster_interval({key: tuple(value) for key, value in missed_groups.items()})},
            "crosswalk_exact_agreement": {"numerator": sum(v[0] for v in exact_groups.values()), "denominator": sum(v[1] for v in exact_groups.values()), "value": ratio(sum(v[0] for v in exact_groups.values()), sum(v[1] for v in exact_groups.values())), "case_cluster_bootstrap": cluster_interval({key: tuple(value) for key, value in exact_groups.items()})},
        },
        "bundle_evaluable": 120 - bundle_unknown,
        "bundle_unknown_excluded": bundle_unknown,
        "bundle_reference_label_counts": reference["bundle_label_counts"],
        "bundle_confusion": {f"{a}|{b}": n for (a, b), n in sorted(bundle_matrix.items())},
        "bundle_exact_agreement": {"numerator": sum(v[0] for v in bundle_exact_groups.values()), "denominator": sum(v[1] for v in bundle_exact_groups.values()), "value": ratio(sum(v[0] for v in bundle_exact_groups.values()), sum(v[1] for v in bundle_exact_groups.values())), "case_cluster_bootstrap": cluster_interval({key: tuple(value) for key, value in bundle_exact_groups.items()})},
        "bundle_binary_accuracy": {"numerator": sum(v[0] for v in bundle_binary_groups.values()), "denominator": sum(v[1] for v in bundle_binary_groups.values()), "value": ratio(sum(v[0] for v in bundle_binary_groups.values()), sum(v[1] for v in bundle_binary_groups.values())), "case_cluster_bootstrap": cluster_interval({key: tuple(value) for key, value in bundle_binary_groups.items()})},
        "paired_arm_descriptives": {"gate_state_pairs": {f"{a}|{b}": n for (a, b), n in sorted(gate_pairs.items())}, "retained_candidate_sets_equal": retained_equal, "case_total": 120, "retained_candidate_total_arm_a": arm_a_retained, "retained_candidate_total_arm_b": arm_b_retained},
        "missing_or_misaligned_candidate_cases": sorted(invalid_ids),
        "inference_limit": "All 120 cases originate from one HF-2024 source family; case-cluster intervals condition on that source family and do not estimate between-source-family uncertainty.",
    }
    output = WORK / "locked_evaluation_addendum_v2_2_01.json"
    if output.exists():
        raise SystemExit("BLOCKED_OUTPUT_ALREADY_EXISTS")
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output.relative_to(ROOT)), "sha256": sha(output), "candidate_evaluable": candidate_evaluable, "bundle_evaluable": 120 - bundle_unknown, "candidate_crosswalk_agreement": report["candidate_metrics"]["crosswalk_exact_agreement"]["value"], "bundle_exact_agreement": report["bundle_exact_agreement"]["value"]}, indent=2))


if __name__ == "__main__":
    main()
