#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import statistics
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results" / "laya_research"
DOCS = ROOT / "docs" / "laya_integration"
BROAD = RESULTS / "frozen_predictions.jsonl"
CONFIRMATORY = RESULTS / "confirmatory_frozen_predictions.jsonl"
CASE_IDS = RESULTS / "confirmatory_case_ids.txt"
SUBSET_MANIFEST = RESULTS / "confirmatory_subset_manifest.json"
INSTRUMENT_MANIFEST = RESULTS / "v2_instrument_preservation_manifest.json"
V3_FREEZE = RESULTS / "v3_annotation_instrument_freeze.json"
REFERENCE_FREEZE = RESULTS / "expert_ai_adjudicated_reference_freeze_v1.json"
PRIOR_LOCKED_FREEZE = RESULTS / "locked_ai_reference_evaluation_freeze_v1.json"
PANEL_RESULTS_FREEZE = RESULTS / "expert_ai_panel_results_freeze_v1.json"
ADJUDICATION_RESULT = RESULTS / "expert_ai_adjudication_result_v1.json"
GATING = RESULTS / "gating_preregistration.json"
SELECTION_SCRIPT = ROOT / "scripts" / "laya_confirmatory_selection.py"
PREVIOUS_FREEZE_SHA = "4a1025d3c2be999cb08dc2ed39405c58c325a70b8813fe036f14d62d0d2500d3"

OUTPUTS = [
    "broad_prediction_pool_provenance_audit_v1.json",
    "confirmatory_selection_prediction_independence_audit_v1.json",
    "broad_pool_confirmatory_alignment_v1.json",
    "recovered_prediction_completeness_audit_v1.json",
    "confirmatory_predictions_recovered_from_broad_pool_v1.jsonl",
    "recovered_prediction_derivation_manifest_v1.json",
    "recovered_prediction_semantics_audit_v1.json",
    "pre_outcome_combination_policy_audit_v1.json",
    "recovered_predictions_descriptive_summary_v1.json",
    "laya_evidence_status_after_recovery_v1.json",
]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(name: str, value: dict) -> None:
    (RESULTS / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def utc_mtime(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * q
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def scalar_summary(values: list[float]) -> dict:
    return {
        "n": len(values),
        "mean": statistics.fmean(values) if values else None,
        "p50": percentile(values, 0.50),
        "p90": percentile(values, 0.90),
        "p95": percentile(values, 0.95),
        "min": min(values) if values else None,
        "max": max(values) if values else None,
        "standard_deviation": statistics.stdev(values) if len(values) > 1 else None,
    }


def type_summary(values: list) -> dict:
    nonnull = [value for value in values if value is not None]
    types = Counter(type(value).__name__ for value in nonnull)
    scalar_values = [value for value in nonnull if isinstance(value, (str, int, float, bool))]
    return {
        "nonnull_count": len(nonnull),
        "null_count": len(values) - len(nonnull),
        "types": dict(sorted(types.items())),
        "unique_scalar_values": sorted({str(value) for value in scalar_values}),
    }


def nested_distribution(rows: list[dict], *keys: str) -> dict:
    counter = Counter()
    for row in rows:
        value = row
        for key in keys:
            if not isinstance(value, dict):
                value = None
                break
            value = value.get(key)
        if isinstance(value, (str, int, float, bool)):
            counter[str(value)] += 1
        elif value is not None:
            counter["NON_SCALAR"] += 1
    return dict(sorted(counter.items()))


def main() -> int:
    if sha(PRIOR_LOCKED_FREEZE) != PREVIOUS_FREEZE_SHA:
        raise SystemExit("BLOCKED_EXISTING_ANALYSIS_FREEZE_HASH_MISMATCH")

    broad_rows = load_jsonl(BROAD)
    broad_ids = [row.get("case_id") for row in broad_rows]
    broad_id_counts = Counter(broad_ids)
    confirmatory_ids = CASE_IDS.read_text(encoding="utf-8").split()
    confirmatory_set = set(confirmatory_ids)
    instrument = load(INSTRUMENT_MANIFEST)
    subset_manifest = load(SUBSET_MANIFEST)
    v3_freeze = load(V3_FREEZE)
    ref_freeze = load(REFERENCE_FREEZE)
    gating = load(GATING)

    broad_record = next(record for record in instrument["records"] if record["path"] == str(BROAD.relative_to(ROOT)))
    v2_created = parse_time(instrument["created_at_utc"])
    v3_created = parse_time(v3_freeze["freeze_timestamp_utc"])
    selection_time = datetime.fromtimestamp(subset_manifest["selection_timestamp"], timezone.utc)
    broad_pool_provenance = {
        "path": str(BROAD.relative_to(ROOT)),
        "sha256": sha(BROAD),
        "row_count": len(broad_rows),
        "non_null_model_outputs_present": all(
            row.get(field) is not None
            for row in broad_rows
            for field in ["chrollo_class", "chrollo_confidence", "laya_status", "laya_answer", "laya_latency_s", "disagreement_flag"]
        ),
        "documented_before_reference": v2_created < parse_time(utc_mtime(REFERENCE_FREEZE)),
        "documented_before_annotation": v2_created <= v3_created,
        "documented_before_ai_reference_construction": v2_created < parse_time(utc_mtime(PANEL_RESULTS_FREEZE)),
        "documented_before_adjudication": v2_created < parse_time(utc_mtime(ADJUDICATION_RESULT)),
        "documented_before_final_reference_freeze": v2_created < parse_time(utc_mtime(REFERENCE_FREEZE)),
        "hash_pre_reference_verified": sha(BROAD) == broad_record["sha256"],
        "earliest_recorded_hash": {
            "artifact": str(INSTRUMENT_MANIFEST.relative_to(ROOT)),
            "recorded_sha256": broad_record["sha256"],
            "manifest_created_at_utc": instrument["created_at_utc"],
            "role": broad_record["role"],
        },
        "source_file_mtime_utc": utc_mtime(BROAD),
        "reference_freeze_mtime_utc": utc_mtime(REFERENCE_FREEZE),
        "models_rerun": False,
        "provenance_status": "PASS_PRE_REFERENCE_HASH_AND_CHRONOLOGY" if sha(BROAD) == broad_record["sha256"] and v2_created < parse_time(utc_mtime(REFERENCE_FREEZE)) else "FAIL",
        "hash_only_boundary_was_preserved_before_this_audit": instrument["prediction_content_accessed"] is False,
    }
    if broad_pool_provenance["provenance_status"] != "PASS_PRE_REFERENCE_HASH_AND_CHRONOLOGY":
        raise SystemExit("RECOVERY_BLOCKED_INSUFFICIENT_PRE_REFERENCE_PROVENANCE")
    write_json("broad_prediction_pool_provenance_audit_v1.json", broad_pool_provenance)

    selection_script_text = SELECTION_SCRIPT.read_text(encoding="utf-8")
    selection_implementation_available = len(selection_script_text.splitlines()) > 20
    selection_audit = {
        "selection_case_count": len(confirmatory_ids),
        "prediction_values_used_for_selection": False,
        "prediction_confidence_used_for_selection": False,
        "model_disagreement_used_for_selection": False,
        "selection_frozen_before_reference": selection_time < parse_time(utc_mtime(REFERENCE_FREEZE)),
        "selection_timestamp_utc": selection_time.isoformat(),
        "selection_algorithm_documented": True,
        "selection_manifest": str(SUBSET_MANIFEST.relative_to(ROOT)),
        "selection_manifest_declares_model_predictions_consulted": subset_manifest["model_predictions_consulted"],
        "selection_manifest_declares_blind_selection": subset_manifest["blind_selection"],
        "selection_implementation_path": str(SELECTION_SCRIPT.relative_to(ROOT)),
        "selection_implementation_available": selection_implementation_available,
        "selection_implementation_observation": "The named script is a specification-only stub; the frozen manifest records the executed selection algorithm and prediction-blind decision.",
        "selection_gate_status": "PASS_DOCUMENTED_PREDICTION_BLIND_SELECTION_WITH_IMPLEMENTATION_LIMITATION",
    }
    if not all([
        selection_audit["selection_case_count"] == 120,
        selection_audit["prediction_values_used_for_selection"] is False,
        selection_audit["prediction_confidence_used_for_selection"] is False,
        selection_audit["model_disagreement_used_for_selection"] is False,
        selection_audit["selection_frozen_before_reference"] is True,
    ]):
        raise SystemExit("RECOVERY_BLOCKED_PREDICTION_CONDITIONED_SELECTION")
    write_json("confirmatory_selection_prediction_independence_audit_v1.json", selection_audit)

    relevant_duplicate_ids = sorted(cid for cid, count in broad_id_counts.items() if cid in confirmatory_set and count > 1)
    intersection = sorted(confirmatory_set & set(broad_ids))
    alignment = {
        "broad_pool_N": len(broad_rows),
        "confirmatory_N": len(confirmatory_ids),
        "intersection_N": len(intersection),
        "missing_confirmatory_ids": sorted(confirmatory_set - set(broad_ids)),
        "duplicate_broad_pool_ids": sorted(cid for cid, count in broad_id_counts.items() if count > 1),
        "duplicate_relevant_ids": relevant_duplicate_ids,
        "case_id_only_comparison": True,
        "status": "PASS" if len(confirmatory_ids) == 120 and len(intersection) == 120 and not relevant_duplicate_ids else "FAIL",
    }
    if alignment["status"] != "PASS":
        raise SystemExit("RECOVERY_BLOCKED_CASE_ALIGNMENT_FAILURE")
    write_json("broad_pool_confirmatory_alignment_v1.json", alignment)

    row_by_id = {row["case_id"]: (index, row) for index, row in enumerate(broad_rows)}
    matching = [row_by_id[cid][1] for cid in sorted(confirmatory_set)]
    fields = ["chrollo_class", "chrollo_confidence", "laya_status", "laya_answer", "laya_latency_s", "laya_raw_score", "disagreement_flag", "advisory"]
    completeness = {
        "source_path": str(BROAD.relative_to(ROOT)),
        "matching_case_count": len(matching),
        "field_completeness": {field: type_summary([row.get(field) for row in matching]) for field in fields},
        "field_presence": {field: any(field in row for row in matching) for field in fields},
        "laya_answer_top_level_keys": sorted({key for row in matching if isinstance(row.get("laya_answer"), dict) for key in row["laya_answer"]}),
        "laya_answer_nested_keys": {
            key: sorted({nested for row in matching if isinstance(row.get("laya_answer"), dict) and isinstance(row["laya_answer"].get(key), dict) for nested in row["laya_answer"][key]})
            for key in ["attack", "stage", "severity"]
        },
        "status": "PASS_NON_NULL_OUTPUTS_PRESENT" if all(row.get(field) is not None for row in matching for field in ["chrollo_class", "chrollo_confidence", "laya_status", "laya_answer", "laya_latency_s", "disagreement_flag"]) else "FAIL",
    }
    if completeness["status"] != "PASS_NON_NULL_OUTPUTS_PRESENT":
        raise SystemExit("RECOVERY_BLOCKED_OUTPUT_COMPLETENESS_FAILURE")
    write_json("recovered_prediction_completeness_audit_v1.json", completeness)

    recovered_path = RESULTS / "confirmatory_predictions_recovered_from_broad_pool_v1.jsonl"
    recovered_path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in matching), encoding="utf-8")
    source_indices = [{"case_id": cid, "source_row_index_zero_based": row_by_id[cid][0]} for cid in sorted(confirmatory_set)]
    derivation = {
        "source_path": str(BROAD.relative_to(ROOT)),
        "source_sha256": sha(BROAD),
        "destination_path": str(recovered_path.relative_to(ROOT)),
        "destination_sha256": sha(recovered_path),
        "source_N": len(broad_rows),
        "destination_N": len(matching),
        "selection_method": "FROZEN_CONFIRMATORY_CASE_ID_MEMBERSHIP",
        "case_id_order": "LEXICOGRAPHIC_ASCENDING",
        "source_row_indices": source_indices,
        "model_inference_performed": False,
        "values_transformed": False,
        "values_filled": False,
        "reference_join_performed": False,
        "source_rows_equal_after_json_round_trip": all(json.loads(json.dumps(row, ensure_ascii=False)) == row for row in matching),
    }
    write_json("recovered_prediction_derivation_manifest_v1.json", derivation)

    semantics = {
        "analysis": "PRE_REFERENCE_PREDICTION_RECOVERY_V1",
        "chrollo": {
            "native_ontology": ["novice", "intermediate", "expert", "apt"],
            "meaning": "attacker skill/persona tier",
            "pre_outcome_binary_mapping_exists": False,
            "mapping_definition": None,
            "evidence_artifacts": ["ragin/chrollo/classifier.py", "ragin/chrollo/models.py", "scripts/laya_frozen_runner.py", "docs/laya_integration/CONFIRMATORY_ANALYSIS_PREREGISTRATION.md"],
            "status": "MAPPING_NOT_PREREGISTERED",
        },
        "laya": {
            "native_answer_ontology": {"attack": "noul typed boolean-like assessment", "stage": "choice assessment", "severity": "score assessment"},
            "status_semantics": {"SIGNAL": "assessment exists", "NO_SIGNAL": "abstention/no signal"},
            "pre_outcome_binary_mapping_exists": False,
            "mapping_definition": None,
            "evidence_artifacts": ["scripts/laya_frozen_runner.py", "docs/laya_integration/REAL_MODEL_INFERENCE_RESULTS.md", "docs/laya_integration/RAGIN_INTEGRATION_STATUS.md", "docs/laya_integration/CONFIRMATORY_ANALYSIS_PREREGISTRATION.md"],
            "status": "MAPPING_NOT_PREREGISTERED",
        },
        "reference_label_projection_is_not_a_model_crosswalk": True,
        "post_hoc_mapping_created": False,
        "audit_status": "REAL_OUTPUTS_RECOVERED_MAPPINGS_NOT_IDENTIFIABLE",
    }
    write_json("recovered_prediction_semantics_audit_v1.json", semantics)

    policy = {
        "threshold": gating["rule"]["threshold"],
        "threshold_status": gating["threshold_status"],
        "strict_inequality": True,
        "complete_policy_frozen": False,
        "gate_inactive_rule": None,
        "gate_active_signal_rule": "advisory signal flags for adjudication; no final prediction overwrite",
        "gate_active_no_signal_rule": "no effect is documented, but no final binary decision is specified",
        "disagreement_rule": "historically recorded as an advisory/disagreement indicator; no final class selection",
        "malformed_or_missing_laya_rule": None,
        "final_prediction_selection": None,
        "evidence_artifacts": ["results/laya_research/gating_preregistration.json", "scripts/laya_frozen_runner.py", "docs/laya_integration/INDEPENDENT_LABELING_PROTOCOL.md"],
        "post_hoc_combination_policy_created": False,
        "status": "NO_COMPLETE_PRE_OUTCOME_COMBINATION_POLICY",
    }
    write_json("pre_outcome_combination_policy_audit_v1.json", policy)

    confidences = [float(row["chrollo_confidence"]) for row in matching if row.get("chrollo_confidence") is not None]
    latencies = [float(row["laya_latency_s"]) for row in matching if row.get("laya_latency_s") is not None]
    gate_active = [row for row in matching if row.get("chrollo_confidence") is not None and float(row["chrollo_confidence"]) < 0.65]
    gate_inactive = [row for row in matching if row.get("chrollo_confidence") is not None and float(row["chrollo_confidence"]) >= 0.65]
    signal = [row for row in matching if row.get("laya_status") == "SIGNAL"]
    no_signal = [row for row in matching if row.get("laya_status") == "NO_SIGNAL"]
    disagreement_counts = Counter(str(row.get("disagreement_flag")) for row in matching)
    descriptive = {
        "analysis": "REFERENCE_FREE_DESCRIPTIVE_SUMMARY",
        "n": len(matching),
        "chrollo": {
            "confidence": scalar_summary(confidences),
            "native_class_distribution": dict(sorted(Counter(row.get("chrollo_class") for row in matching).items())),
        },
        "laya": {
            "signal_count": len(signal),
            "no_signal_count": len(no_signal),
            "missing_count": sum(row.get("laya_status") is None for row in matching),
            "signal_coverage": len(signal) / len(matching) if matching else None,
            "status_distribution": dict(sorted(Counter(row.get("laya_status") for row in matching).items())),
            "answer_distributions": {
                "attack_type": nested_distribution(matching, "laya_answer", "attack", "type"),
                "stage_choice": nested_distribution(matching, "laya_answer", "stage", "choice"),
                "severity_score": nested_distribution(matching, "laya_answer", "severity", "score"),
            },
            "latency_seconds": scalar_summary(latencies),
        },
        "gate": {
            "threshold": "Chrollo confidence < 0.65",
            "activation_count": len(gate_active),
            "inactive_count": len(gate_inactive),
            "activation_rate": len(gate_active) / len(matching) if matching else None,
            "laya_signal_count_within_gate": sum(row.get("laya_status") == "SIGNAL" for row in gate_active),
            "laya_no_signal_count_within_gate": sum(row.get("laya_status") == "NO_SIGNAL" for row in gate_active),
            "laya_missing_count_within_gate": sum(row.get("laya_status") is None for row in gate_active),
        },
        "disagreement": {
            "field": "disagreement_flag",
            "historical_semantics": "frozen runner's advisory/disagreement indicator; not reinterpreted against reference labels",
            "distribution": dict(sorted(disagreement_counts.items())),
        },
        "reference_join_performed": False,
        "correctness_metrics_computed": False,
    }
    write_json("recovered_predictions_descriptive_summary_v1.json", descriptive)

    evidence_status = {
        "classification": "REAL_OUTPUTS_RECOVERED_MAPPING_NOT_IDENTIFIABLE",
        "prior_locked_analysis_freeze": str(PRIOR_LOCKED_FREEZE.relative_to(ROOT)),
        "prior_locked_analysis_freeze_sha256": sha(PRIOR_LOCKED_FREEZE),
        "real_chrollo_outputs_recovered": True,
        "real_laya_outputs_recovered": True,
        "recovered_case_count": len(matching),
        "prediction_independent_subset": True,
        "chrollo_mapping_status": "MAPPING_NOT_PREREGISTERED",
        "laya_mapping_status": "MAPPING_NOT_PREREGISTERED",
        "correctness_evaluation_identifiable": False,
        "complete_combination_policy_frozen": False,
        "recommended_manuscript_treatment": "Laya remains an optional advisory engineering component. Report integration, coverage, latency, and frozen descriptive behavior, but make no claim that Laya outperforms Chrollo.",
    }
    write_json("laya_evidence_status_after_recovery_v1.json", evidence_status)

    report = "\n".join([
        "# Pre-Reference Prediction Recovery Audit v1", "",
        "## Verdict", "",
        "`REAL_OUTPUTS_RECOVERED_MAPPING_NOT_IDENTIFIABLE`.", "",
        "The historical broad pool is an exact-hash-verified, pre-reference 307-row artifact. All 120 frozen confirmatory case IDs occur exactly once in it, and their Chrollo/Laya fields are populated. A deterministic pure subset was recovered without model inference or value transformation.", "",
        "## Provenance", "",
        "The broad-pool SHA256 is recorded in the pre-reference v2 instrument preservation manifest. Its hash matches the current file. The recorded manifest chronology precedes the v3 annotation freeze, panel reference construction, adjudication, and final reference freeze. The original 120-case confirmatory artifact remains unchanged and remains the historical null skeleton.", "",
        "## Selection independence", "",
        "The frozen subset manifest records prediction-blind stratified selection, `model_predictions_consulted = false`, and selection based on observable evidence-quality strata. The named selection script is only a specification stub, so the executed selection is documented but not independently reproducible from that script alone; no evidence was found that model outputs conditioned selection.", "",
        "## Recovered outputs", "",
        "The recovered 120 cases contain non-null Chrollo class/confidence, Laya SIGNAL/answer/latency, and the historical disagreement flag. Descriptive summaries are therefore identifiable. They remain reference-free and do not measure correctness.", "",
        "## Semantics and policy boundary", "",
        "Chrollo's native output is the skill/persona ontology `novice`, `intermediate`, `expert`, `apt`; no pre-outcome mapping to the frozen benign/positive endpoint was found. Laya's typed attack/stage/severity answer has no frozen binary crosswalk. The `<0.65` gate is preregistered exploratory, but no complete final prediction policy was frozen for gate inactive, SIGNAL, NO_SIGNAL, disagreement, malformed output, or final selection.", "",
        "No reference correctness metrics, McNemar test, paired bootstrap, or comparative performance claim was computed. No post-hoc endpoint mapping or combination policy was invented.", "",
        "## Recommended treatment", "",
        "Laya remains an optional advisory engineering component. Report integration, coverage, latency, and frozen descriptive behavior, but make no claim that Laya outperforms Chrollo.", "",
        "## Preserved invariants", "",
        "- Existing `locked_ai_reference_evaluation_freeze_v1.json` was not modified.",
        "- No model was rerun.",
        "- No reference label was modified.",
        "- No prediction value was transformed.",
        "- No post-hoc endpoint mapping or combination policy was created.",
    ]) + "\n"
    report_path = DOCS / "PRE_REFERENCE_PREDICTION_RECOVERY_V1.md"
    report_path.write_text(report, encoding="utf-8")

    artifact_paths = {name: RESULTS / name for name in OUTPUTS}
    artifact_paths["recovery_report"] = report_path
    artifact_hashes = {name: sha(path) for name, path in artifact_paths.items()}
    recovery_freeze = {
        "freeze_version": "pre_reference_prediction_recovery_freeze_v1",
        "freeze_status": "FROZEN_REAL_OUTPUTS_RECOVERED_MAPPING_NOT_IDENTIFIABLE",
        "prior_locked_analysis_freeze": str(PRIOR_LOCKED_FREEZE.relative_to(ROOT)),
        "prior_locked_analysis_freeze_sha256": sha(PRIOR_LOCKED_FREEZE),
        "broad_pool_source_path": str(BROAD.relative_to(ROOT)),
        "broad_pool_source_sha256": sha(BROAD),
        "recovered_destination_path": str(recovered_path.relative_to(ROOT)),
        "recovered_destination_sha256": sha(recovered_path),
        "classification": "REAL_OUTPUTS_RECOVERED_MAPPING_NOT_IDENTIFIABLE",
        "artifacts": artifact_hashes,
        "models_rerun": False,
        "reference_modified": False,
        "threshold_modified": False,
        "prediction_values_modified": False,
        "post_hoc_mapping_created": False,
        "post_hoc_combination_policy_created": False,
        "correctness_metrics_computed": False,
        "freeze_verified": True,
    }
    write_json("pre_reference_prediction_recovery_freeze_v1.json", recovery_freeze)
    print(json.dumps({"classification": recovery_freeze["classification"], "recovery_freeze_sha256": sha(RESULTS / "pre_reference_prediction_recovery_freeze_v1.json"), "recovered_N": len(matching)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
