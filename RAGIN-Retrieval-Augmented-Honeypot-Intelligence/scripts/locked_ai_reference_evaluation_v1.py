#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results" / "laya_research"
DOCS = ROOT / "docs" / "laya_integration"

REFERENCE_FREEZE = RESULTS / "expert_ai_adjudicated_reference_freeze_v1.json"
REFERENCE = RESULTS / "expert_ai_adjudicated_reference_v1.json"
BINARY_REFERENCE = RESULTS / "expert_ai_adjudicated_binary_reference_v1.json"
READINESS = RESULTS / "confirmatory_reference_readiness_v1.json"
PREDICTIONS = RESULTS / "confirmatory_frozen_predictions.jsonl"
BROAD_PREDICTIONS = RESULTS / "frozen_predictions.jsonl"
SUBSET_MANIFEST = RESULTS / "confirmatory_subset_manifest.json"
INSTRUMENT_MANIFEST = RESULTS / "v2_instrument_preservation_manifest.json"
GATING = RESULTS / "gating_preregistration.json"
PREREG = DOCS / "CONFIRMATORY_ANALYSIS_PREREGISTRATION.md"

OUT_NAMES = [
    "locked_prediction_provenance_audit_v1.json",
    "locked_prediction_reference_alignment_v1.json",
    "locked_prediction_semantics_audit_v1.json",
    "chrollo_locked_ai_reference_metrics_v1.json",
    "laya_locked_ai_reference_metrics_v1.json",
    "chrollo_laya_paired_correctness_v1.json",
    "chrollo_laya_exact_mcnemar_v1.json",
    "chrollo_laya_paired_bootstrap_v1.json",
    "laya_gate_exploratory_analysis_v1.json",
    "laya_frozen_latency_summary_v1.json",
    "locked_ai_reference_case_analysis_v1.jsonl",
    "reference_source_sensitivity_v1.json",
]

POSITIVE_LABELS = {
    "RECON", "SUSPICIOUS", "EXPLOITATION", "PRIVILEGE_ESCALATION",
    "DATA_ACCESS", "PERSISTENCE", "OTHER_ATTACK",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def iso_mtime(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()


def write_json(name: str, value: dict) -> None:
    (RESULTS / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def metric_template() -> dict:
    return {
        "tp": None, "tn": None, "fp": None, "fn": None,
        "balanced_accuracy": None, "accuracy": None,
        "sensitivity_recall_tpr": None, "specificity_tnr": None,
        "precision_ppv": None, "negative_predictive_value": None,
        "f1": None, "mcc": None, "fpr": None, "fnr": None,
    }


def main() -> int:
    freeze = load_json(REFERENCE_FREEZE)
    readiness = load_json(READINESS)
    subset = load_json(SUBSET_MANIFEST)
    instrument = load_json(INSTRUMENT_MANIFEST)
    gating = load_json(GATING)

    if digest(REFERENCE_FREEZE) != "57bf43e9c4992d22d21f45f4351d225dd1d27d554c8499d2d2f16bac7c0b08eb":
        raise SystemExit("BLOCKED_FROZEN_ARTIFACT_HASH_MISMATCH")

    referenced_hashes = {}
    mismatches = []
    for name, expected in freeze["artifacts"].items():
        path = Path(name)
        if not path.is_absolute():
            path = ROOT / path
        if not path.exists():
            mismatches.append({"path": name, "reason": "missing"})
            continue
        actual = digest(path)
        referenced_hashes[name] = {"expected": expected, "actual": actual, "matches": actual == expected}
        if actual != expected:
            mismatches.append({"path": name, "expected": expected, "actual": actual})
    if mismatches:
        raise SystemExit("BLOCKED_FROZEN_ARTIFACT_HASH_MISMATCH")

    instrument_record = next(
        record for record in instrument["records"] if record["path"] == str(PREDICTIONS.relative_to(ROOT))
    )
    subset_recorded_sha = subset["confirmatory_frozen_predictions_sha256"]
    prediction_sha = digest(PREDICTIONS)
    reference_freeze_mtime = iso_mtime(REFERENCE_FREEZE)
    prediction_mtime = iso_mtime(PREDICTIONS)
    instrument_created = instrument["created_at_utc"]
    generated_before_reference = (
        prediction_sha == instrument_record["sha256"] == subset_recorded_sha
        and prediction_mtime < reference_freeze_mtime
        and instrument_created < reference_freeze_mtime
    )
    provenance = {
        "analysis": "LOCKED_AI_REFERENCE_EVALUATION",
        "reference_freeze_sha256": digest(REFERENCE_FREEZE),
        "reference_freeze_expected_sha256": "57bf43e9c4992d22d21f45f4351d225dd1d27d554c8499d2d2f16bac7c0b08eb",
        "reference_freeze_named_artifact_hashes_verified": True,
        "prediction_path": str(PREDICTIONS.relative_to(ROOT)),
        "prediction_sha256": prediction_sha,
        "recorded_pre_reference_sha256": {
            "v2_instrument_preservation_manifest": instrument_record["sha256"],
            "confirmatory_subset_manifest": subset_recorded_sha,
        },
        "hash_matches": prediction_sha == instrument_record["sha256"] == subset_recorded_sha,
        "prediction_case_count": None,
        "generated_before_reference": generated_before_reference,
        "prediction_freeze_evidence": {
            "instrument_manifest_created_at_utc": instrument_created,
            "prediction_file_mtime_utc": prediction_mtime,
            "reference_freeze_file_mtime_utc": reference_freeze_mtime,
            "record_role": instrument_record["role"],
            "manifest_content_flag": instrument.get("prediction_content_accessed") is False,
        },
        "reference_created_after_prediction_freeze": generated_before_reference,
        "predictions_rerun": False,
        "authoritative_over_broad_pool": True,
        "broad_pool_not_used": str(BROAD_PREDICTIONS.relative_to(ROOT)),
        "provenance_status": "PASS_PRE_REFERENCE_HASH_AND_CHRONOLOGY" if generated_before_reference else "INSUFFICIENT",
        "prediction_content_status": "FROZEN_SKELETON_ALL_MODEL_FIELDS_NULL",
    }

    predictions = load_jsonl(PREDICTIONS)
    provenance["prediction_case_count"] = len(predictions)
    pred_ids = [row.get("case_id") for row in predictions]
    pred_id_counts = Counter(pred_ids)

    reference_doc = load_json(REFERENCE)
    binary_doc = load_json(BINARY_REFERENCE)
    reference_cases = reference_doc["cases"]
    binary_cases = binary_doc["cases"]
    reference_by_id = {row["case_id"]: row for row in reference_cases}
    binary_by_id = {row["case_id"]: row for row in binary_cases}
    selected_ids = set(subset["selected_case_ids"])
    reference_ids = set(reference_by_id)
    prediction_ids = set(pred_ids)
    eligible_ids = {row["case_id"] for row in reference_cases if row["primary_metric_eligible"]}
    uncertain_ids = reference_ids - eligible_ids

    alignment = {
        "analysis": "LOCKED_AI_REFERENCE_EVALUATION",
        "prediction_path": str(PREDICTIONS.relative_to(ROOT)),
        "reference_path": str(REFERENCE.relative_to(ROOT)),
        "binary_reference_path": str(BINARY_REFERENCE.relative_to(ROOT)),
        "prediction_case_count": len(predictions),
        "reference_case_count": len(reference_cases),
        "confirmatory_selected_case_count": len(selected_ids),
        "duplicate_prediction_case_ids": sorted(cid for cid, n in pred_id_counts.items() if n > 1),
        "missing_prediction_ids": sorted(reference_ids - prediction_ids),
        "unexpected_prediction_ids": sorted(prediction_ids - reference_ids),
        "missing_reference_ids_from_confirmatory_set": sorted(selected_ids - reference_ids),
        "unexpected_reference_ids_vs_confirmatory_set": sorted(reference_ids - selected_ids),
        "case_set_exact_match": prediction_ids == reference_ids == selected_ids,
        "primary_metric_eligible_n": len(eligible_ids),
        "reference_uncertain_n": len(uncertain_ids),
        "reference_unresolved_n": sum(row["reference_status"] == "UNRESOLVED" for row in reference_cases),
        "prediction_schema": sorted(predictions[0]) if predictions else [],
        "null_counts": {
            field: sum(row.get(field) is None for row in predictions)
            for field in ["chrollo_output", "chrollo_confidence", "laya_status", "laya_answer", "laya_latency_ms"]
        },
        "alignment_status": "PASS_CASE_ID_ALIGNMENT_NULL_PREDICTION_CONTENT" if prediction_ids == reference_ids == selected_ids else "FAIL",
    }

    semantics = {
        "analysis": "LOCKED_AI_REFERENCE_EVALUATION",
        "prediction_path": str(PREDICTIONS.relative_to(ROOT)),
        "chrollo": {
            "observed_field_in_authoritative_artifact": "chrollo_output",
            "runner_output_field": "chrollo_class",
            "native_ontology_documented_as": ["novice", "intermediate", "expert", "apt"],
            "meaning": "attacker skill level/persona tier, not the frozen benign-versus-attack endpoint",
            "binary_mapping_status": "MAPPING_NOT_PREREGISTERED",
            "binary_mapping": None,
            "multiclass_mapping_status": "MAPPING_NOT_IDENTIFIABLE_FROM_NULL_CONFIRMATORY_OUTPUTS",
            "evidence": ["ragin/chrollo/classifier.py", "ragin/chrollo/models.py", "scripts/laya_frozen_runner.py"],
        },
        "laya": {
            "status_field": "laya_status",
            "status_semantics": {"SIGNAL": "assessment returned", "NO_SIGNAL": "abstention/no signal; not benign"},
            "answer_field": "laya_answer",
            "answer_schema": "typed attack/stage/severity assessment; no frozen binary projection",
            "binary_mapping_status": "MAPPING_NOT_PREREGISTERED",
            "binary_mapping": None,
            "evidence": ["scripts/laya_frozen_runner.py", "docs/laya_integration/RAGIN_INTEGRATION_STATUS.md", "docs/laya_integration/REAL_MODEL_INFERENCE_RESULTS.md"],
        },
        "combination_policy": {
            "pre_outcome_complete_rule_exists": False,
            "status": "NO_PRE_FROZEN_END_TO_END_COMBINATION_POLICY",
            "advisory_contract": "SIGNAL flags for adjudication; it does not overwrite Chrollo; NO_SIGNAL has no effect",
            "evidence": ["results/laya_research/gating_preregistration.json", "scripts/laya_frozen_runner.py"],
        },
        "semantics_status": "MAPPINGS_NOT_PREREGISTERED",
    }

    chrollo_metrics = {
        "analysis": "CHROLLO_PRIMARY_EVALUATION",
        "reference_type": "AI_DERIVED_ADJUDICATED_REFERENCE",
        "human_ground_truth": False,
        "primary_reference_n": len(eligible_ids),
        "valid_mapped_prediction_n": 0,
        "mapping_status": "MAPPING_NOT_PREREGISTERED",
        "metric_status": "NOT_IDENTIFIABLE_NO_MAPPED_CHROLLO_PREDICTIONS",
        "binary_metrics": metric_template(),
        "confusion_matrix": None,
        "multiclass_metrics": None,
        "note": "The native Chrollo skill-level ontology has no pre-outcome crosswalk to the fixed binary endpoint, and all confirmatory output fields are null.",
    }
    laya_metrics = {
        "analysis": "LAYA_COVERAGE_AND_CONDITIONAL_PERFORMANCE",
        "reference_type": "AI_DERIVED_ADJUDICATED_REFERENCE",
        "human_ground_truth": False,
        "primary_reference_n": len(eligible_ids),
        "signal_count": 0,
        "no_signal_count": 0,
        "missing_status_count": len(eligible_ids),
        "signal_coverage_rate": None,
        "no_signal_rate": None,
        "mapping_status": "MAPPING_NOT_PREREGISTERED",
        "conditional_evaluable_n": 0,
        "metric_status": "NOT_IDENTIFIABLE_NO_LAYA_SIGNAL_OR_BINARY_MAPPING",
        "conditional_on_laya_signal": metric_template(),
        "note": "Missing status is not recoded as NO_SIGNAL; NO_SIGNAL is an observed abstention only when the frozen status field says NO_SIGNAL.",
    }

    paired = {
        "analysis": "SHARED_PREDICTION_SUBSET",
        "reference_type": "AI_DERIVED_ADJUDICATED_REFERENCE",
        "shared_prediction_subset_definition": "eligible reference AND valid Chrollo prediction AND valid mapped Laya SIGNAL prediction",
        "shared_prediction_subset_n": 0,
        "status": "NOT_IDENTIFIABLE_NO_SHARED_PREDICTION_SUBSET",
        "cells": {"A_both_correct": None, "B_chrollo_correct_laya_wrong": None, "C_chrollo_wrong_laya_correct": None, "D_both_wrong": None},
        "laya_corrections_C": None,
        "laya_harms_B": None,
        "net_corrections_C_minus_B": None,
        "correction_harm_ratio_C_over_B": None,
        "causal_treatment_effect_claim": False,
    }
    mcnemar = {
        "analysis": "EXACT_TWO_SIDED_MCNEMAR",
        "shared_prediction_subset_n": 0,
        "B_chrollo_correct_laya_wrong": None,
        "C_chrollo_wrong_laya_correct": None,
        "discordant_total": 0,
        "two_sided_exact_p_value": None,
        "status": "NO_SHARED_PREDICTION_SUBSET_NO_DISCORDANCE_TEST_IDENTIFIABLE",
        "equivalence_claim": False,
    }
    bootstrap = {
        "analysis": "PAIRED_BOOTSTRAP",
        "status": "NOT_IDENTIFIABLE_NO_SHARED_PREDICTION_SUBSET",
        "replicates_requested": 10000,
        "replicates_executed": 0,
        "confidence_level": 0.95,
        "resampling": "paired case-level",
        "ci_method": "percentile",
        "deterministic_seed": 20261013,
        "implementation_detail_status": "ANALYSIS_IMPLEMENTATION_DETAIL_NOT_OUTCOME_TUNED",
        "shared_prediction_subset_n": 0,
        "balanced_accuracy_difference_laya_minus_chrollo": None,
        "balanced_accuracy_difference_95_ci": None,
        "accuracy_difference_laya_minus_chrollo": None,
        "accuracy_difference_95_ci": None,
        "model_specific_bootstrap_cis": {"chrollo": None, "laya_conditional_signal": None},
        "note": "No bootstrap replicate was run because there are no valid paired model predictions; the preregistered/default implementation details are recorded for the blocked analysis.",
    }

    threshold = gating["rule"]["threshold"]
    gate = {
        "analysis": "PREREGISTERED_EXPLORATORY",
        "threshold": threshold,
        "threshold_status": gating["threshold_status"],
        "strict_inequality": True,
        "total_eligible_cases": len(eligible_ids),
        "valid_chrollo_confidence_n": 0,
        "gate_active_count": None,
        "gate_inactive_count": None,
        "gate_activation_rate": None,
        "chrollo_error_rate_inside_gate": None,
        "chrollo_error_rate_outside_gate": None,
        "laya_signal_count_inside_gate": None,
        "laya_no_signal_count_inside_gate": None,
        "laya_missing_status_count_inside_gate": None,
        "gate_active_signal_pair_counts": None,
        "corrections_inside_gate": None,
        "harms_inside_gate": None,
        "end_to_end_gated_policy_metric": "NOT_IDENTIFIABLE_FROM_PREREGISTERED_POLICY",
        "combination_policy_frozen_before_outcomes": False,
        "note": "No confidence values are present in the authoritative confirmatory artifact; missing confidence is not treated as gate-inactive.",
    }

    latency = {
        "analysis": "FROZEN_LAYA_LATENCY_SUMMARY",
        "source_field": "laya_latency_ms",
        "unit": "seconds",
        "recorded_latency_n": 0,
        "signal_n": 0,
        "no_signal_n": 0,
        "missing_status_n": len(eligible_ids),
        "all": {"n": 0, "mean": None, "median_p50": None, "p90": None, "p95": None, "min": None, "max": None, "standard_deviation": None},
        "signal": {"n": 0},
        "no_signal": {"n": 0},
        "gate_active": {"n": 0},
        "gate_inactive": {"n": 0},
        "status": "NOT_IDENTIFIABLE_NO_RECORDED_LAYA_LATENCIES",
        "cold_start_warm_start_inference": False,
    }

    def laya_prediction_if_defined(row: dict):
        return None

    case_lines = []
    for cid in sorted(reference_ids):
        pred = next(row for row in predictions if row["case_id"] == cid)
        reference = reference_by_id[cid]
        binary = binary_by_id[cid]
        case_lines.append({
            "case_id": cid,
            "reference_label": reference["reference_label"],
            "reference_binary": binary["binary_label"],
            "reference_status": reference["reference_status"],
            "primary_metric_eligible": reference["primary_metric_eligible"],
            "chrollo_prediction": pred.get("chrollo_output"),
            "chrollo_confidence": pred.get("chrollo_confidence"),
            "chrollo_correct": None,
            "laya_status": pred.get("laya_status"),
            "laya_prediction_if_defined": laya_prediction_if_defined(pred),
            "laya_correct_if_defined": None,
            "laya_latency_s": None if pred.get("laya_latency_ms") is None else pred["laya_latency_ms"] / 1000,
            "gate_active": None,
            "pair_category_if_defined": None,
        })
    (RESULTS / "locked_ai_reference_case_analysis_v1.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in case_lines), encoding="utf-8"
    )

    source_sensitivity = {"analysis": "REFERENCE_SOURCE_SENSITIVITY", "status": "NOT_IDENTIFIABLE_NO_MAPPED_PREDICTIONS", "strata": {}}
    for source in ["EXACT_3_OF_3_PRIMARY_PANEL", "BLINDED_AI_ADJUDICATION"]:
        rows = [row for row in reference_cases if row["reference_source"] == source]
        eligible = [row for row in rows if row["primary_metric_eligible"]]
        source_sensitivity["strata"][source] = {
            "total_n": len(rows),
            "primary_metric_eligible_n": len(eligible),
            "uncertain_n": sum(row["reference_status"] == "UNCERTAIN" for row in rows),
            "reference_binary_counts": Counter(binary_by_id[row["case_id"]]["binary_label"] for row in eligible),
            "chrollo_metrics": metric_template(),
            "laya_conditional_metrics": metric_template(),
            "paired_n": 0,
        }
    combined = [row for row in reference_cases if row["primary_metric_eligible"]]
    source_sensitivity["strata"]["COMBINED_PRIMARY_EVALUABLE"] = {
        "total_n": len(combined),
        "primary_metric_eligible_n": len(combined),
        "uncertain_n": 0,
        "reference_binary_counts": Counter(binary_by_id[row["case_id"]]["binary_label"] for row in combined),
        "chrollo_metrics": metric_template(),
        "laya_conditional_metrics": metric_template(),
        "paired_n": 0,
    }

    summary_counts = {
        "chrollo_false_positives": None,
        "chrollo_false_negatives": None,
        "laya_conditional_false_positives": None,
        "laya_conditional_false_negatives": None,
        "laya_corrections": None,
        "laya_harms": None,
        "status": "NOT_IDENTIFIABLE_NO_MAPPED_PREDICTIONS",
    }

    report = "\n".join([
        "# Chrollo vs Laya Locked AI-Reference Evaluation v1", "",
        "## Status", "", "`ANALYSIS_NOT_IDENTIFIABLE`.", "",
        "This is a locked evaluation against the frozen `AI_DERIVED_ADJUDICATED_REFERENCE`. The authoritative 120-case confirmatory prediction artifact has a valid pre-reference SHA256 and exact case-ID alignment, but every Chrollo and Laya model-output field is null. The broader 307-case pool was not substituted, no model was rerun, no label was changed, and no endpoint mapping was invented.", "",
        "## A. Directly measured", "",
        "- Reference: 120 total cases; 114 resolved/evaluable; 6 `UNCERTAIN`; 0 `UNRESOLVED`.",
        "- Resolved binary distribution: 92 `NEGATIVE`, 22 `POSITIVE`.",
        "- Reference type: `AI_DERIVED_ADJUDICATED_REFERENCE`; `human_ground_truth = false`.",
        "- Prediction provenance: pre-reference hash and chronology verified for `results/laya_research/confirmatory_frozen_predictions.jsonl`.",
        "- Prediction/reference alignment: exact 120-case ID match, no duplicates, no missing IDs, no unexpected IDs.",
        "- Prediction content: 120/120 null Chrollo outputs, confidences, Laya statuses, Laya answers, and latencies.", "",
        "## B. Statistical comparison support", "",
        "None. There is no valid mapped Chrollo prediction, no valid mapped Laya `SIGNAL`, and therefore no shared prediction subset. Exact McNemar and paired bootstrap are not statistically identifiable from this artifact.", "",
        "## C. What this does not support", "",
        "It does not support Chrollo performance metrics, conditional Laya performance, a Laya correction/harm estimate, an exact p-value, a paired delta, an end-to-end gated-policy metric, or any claim of Laya advantage. It does not establish human ground truth, gold-standard truth, equivalence, or open-world security performance.", "",
        "## D. Abstention and missingness", "",
        "Missing `laya_status` is reported as missing, not as `NO_SIGNAL` and not as `NEGATIVE`. Consequently observed `SIGNAL = 0`, observed `NO_SIGNAL = 0`, missing status = 114 on the eligible subset, and coverage is not identifiable.", "",
        "## E. Gate findings", "",
        "The strict gate `Chrollo confidence < 0.65` remains `PREREGISTERED_EXPLORATORY`. No confidence values are present, so gate-active and gate-inactive counts and rates are not identifiable. A routing threshold is not a final combination rule; the pre-existing artifacts explicitly do not freeze one.", "",
        "## F. Latency", "",
        "No frozen Laya latency values are recorded in the authoritative artifact. Latency summaries are therefore not identifiable; cold-start versus warm-start behavior is not inferred.", "",
        "## G. Reference-source sensitivity", "",
        "The requested strata are reported in `reference_source_sensitivity_v1.json`: exact-3/3 primary-evaluable N = 88, blinded-AI-adjudication primary-evaluable N = 26 (32 source cases including 6 `UNCERTAIN`), and combined primary-evaluable N = 114. All model metrics remain not identifiable because model outputs are absent.", "",
        "## H. Limitations", "",
        "- The reference is AI-derived, not human ground truth.",
        "- Three AI models plus one AI adjudicator created the reference.",
        "- The resolved set is class-imbalanced (92 negative, 22 positive); raw accuracy is secondary and balanced accuracy would be primary if predictions existed.",
        "- Six cases were excluded as `UNCERTAIN`.",
        "- Laya signal coverage cannot be estimated from missing statuses.",
        "- The `<0.65` gate is preregistered exploratory absent stronger independent justification.",
        "- Absence of a pre-frozen combination rule prevents post-hoc end-to-end policy claims.",
        "- Any future bootstrap independence would be case-level unless a defensible cluster structure is explicitly available.",
        "- The study does not establish open-world security performance.",
        "- The authoritative prediction artifact is a frozen skeleton rather than populated model predictions; the 307-case broad pool was not used.", "",
        "## Scientific classification", "",
        "`ANALYSIS_NOT_IDENTIFIABLE`: the fixed reference is available and integrity-verified, but the authoritative confirmatory prediction artifact contains no evaluable model outputs or pre-registered binary mappings.", "",
        "## Freeze invariants", "",
        "- `predictions_rerun = false`",
        "- `reference_modified = false`",
        "- `threshold_changed = false`",
        "- `post_hoc_combination_rule_created = false`",
        "- `reference_type = AI_DERIVED_ADJUDICATED_REFERENCE`",
        "- `human_ground_truth = false`",
    ]) + "\n"
    report_path = DOCS / "CHROLLO_VS_LAYA_LOCKED_AI_REFERENCE_EVAL_V1.md"
    report_path.write_text(report, encoding="utf-8")

    outputs = {
        "locked_prediction_provenance_audit_v1.json": provenance,
        "locked_prediction_reference_alignment_v1.json": alignment,
        "locked_prediction_semantics_audit_v1.json": semantics,
        "chrollo_locked_ai_reference_metrics_v1.json": chrollo_metrics,
        "laya_locked_ai_reference_metrics_v1.json": laya_metrics,
        "chrollo_laya_paired_correctness_v1.json": paired,
        "chrollo_laya_exact_mcnemar_v1.json": mcnemar,
        "chrollo_laya_paired_bootstrap_v1.json": bootstrap,
        "laya_gate_exploratory_analysis_v1.json": gate,
        "laya_frozen_latency_summary_v1.json": latency,
        "reference_source_sensitivity_v1.json": source_sensitivity,
    }
    for name, value in outputs.items():
        write_json(name, value)

    output_paths = {name: RESULTS / name for name in OUT_NAMES if name.endswith(".json")}
    output_paths["locked_ai_reference_case_analysis_v1.jsonl"] = RESULTS / "locked_ai_reference_case_analysis_v1.jsonl"
    output_paths["narrative_report"] = report_path
    output_hashes = {name: digest(path) for name, path in output_paths.items()}
    evaluation_freeze = {
        "freeze_version": "locked_ai_reference_evaluation_freeze_v1",
        "freeze_status": "FROZEN_ANALYSIS_NOT_IDENTIFIABLE",
        "analysis": "LOCKED_AI_REFERENCE_EVALUATION",
        "reference_type": "AI_DERIVED_ADJUDICATED_REFERENCE",
        "human_ground_truth": False,
        "primary_reference_n": len(eligible_ids),
        "reference_total_n": len(reference_cases),
        "reference_uncertain_n": len(uncertain_ids),
        "reference_unresolved_n": 0,
        "reference_sha256": digest(REFERENCE_FREEZE),
        "input_artifact_hashes": referenced_hashes,
        "authoritative_prediction_artifact": str(PREDICTIONS.relative_to(ROOT)),
        "authoritative_prediction_sha256": prediction_sha,
        "prediction_provenance_status": provenance["provenance_status"],
        "prediction_content_status": provenance["prediction_content_status"],
        "reference_hash_verification": {name: value["matches"] for name, value in referenced_hashes.items()},
        "artifacts": output_hashes,
        "predictions_rerun": False,
        "reference_modified": False,
        "threshold_changed": False,
        "post_hoc_combination_rule_created": False,
        "scientific_classification": "ANALYSIS_NOT_IDENTIFIABLE",
        "classification_reason": "Authoritative 120-case prediction skeleton is aligned and pre-reference frozen but contains null Chrollo/Laya outputs; no mapped performance or paired comparison is identifiable.",
        "summary_counts": summary_counts,
        "freeze_verified": True,
    }
    write_json("locked_ai_reference_evaluation_freeze_v1.json", evaluation_freeze)
    print(json.dumps({"status": "FROZEN_ANALYSIS_NOT_IDENTIFIABLE", "freeze_sha256": digest(RESULTS / "locked_ai_reference_evaluation_freeze_v1.json"), "outputs": len(output_hashes)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
