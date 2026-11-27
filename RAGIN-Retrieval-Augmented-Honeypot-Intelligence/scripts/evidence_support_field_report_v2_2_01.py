from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
from collections import Counter

import evidence_support_ai_reference_v2 as base
import evidence_support_codex_reference_v2_2 as v22


WORK = base.BASE / "ai_reference_v2_2"
SOURCE_BATCHES = base.BASE / "ai_reference_v2_1" / "primary_inputs"
MANIFEST = WORK / "run_manifest_v2_2.json"
REFERENCE = WORK / "reference_freeze_v2_2.json"
REFERENCE_MANIFEST = WORK / "reference_freeze_manifest_v2_2.json"
INPUT_FREEZE = WORK / "input_freeze_v2_2.json"
ADDENDUM = WORK / "locked_evaluation_addendum_v2_2_01.json"
REPORT = WORK / "field_level_error_report_v2_2_02.json"
SUPERSEDES = WORK / "field_level_error_report_v2_2_01.json"
FILLER_RATIONALE = "Review unavailable or invalid."


def sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: pathlib.Path):
    return json.loads(path.read_text(encoding="utf-8"))


def error_key(error: str) -> tuple[str, str | None]:
    if error.startswith("invalid candidate review: "):
        return "invalid_candidate_review", error.split(": ", 1)[1]
    if error.startswith("candidate review coverage incomplete: "):
        return "candidate_coverage_incomplete", error.split(": ", 1)[1]
    if error.startswith("duplicate candidate index: "):
        return "duplicate_candidate_index", error.split(": ", 1)[1]
    if error.startswith("invalid bundle review: "):
        return "invalid_bundle_review", error.split(": ", 1)[1]
    if error.startswith("bundle_review missing: "):
        return "bundle_review_missing", error.split(": ", 1)[1]
    if error.startswith("case omitted: "):
        return "case_omitted", error.split(": ", 1)[1]
    if error.startswith("candidate_reviews missing: "):
        return "candidate_reviews_missing", error.split(": ", 1)[1]
    return "unclassified", error


def load_batch_inputs() -> dict[str, dict]:
    freeze = v22.verify_freeze()
    batches = {}
    for batch in freeze["batches"]:
        batch_id = pathlib.Path(batch["path"]).stem
        batches[batch_id] = {
            "input": json.loads((SOURCE_BATCHES / batch["path"]).read_text(encoding="utf-8")),
            "normalized": load(v22.WORK / "runs" / "C1" / batch_id / "normalized_reviews.json") if (v22.WORK / "runs" / "C1" / batch_id / "normalized_reviews.json").exists() else None,
        }
    return batches


def classify_unknown(case_error_kinds: set, review: dict, cited: bool) -> str:
    if review.get("rationale") != FILLER_RATIONALE:
        return "model_explicit_unknown"
    if cited or case_error_kinds:
        return "field_validation_error"
    return "unattributed_structural_unknown"


def compare() -> dict:
    freeze = v22.verify_freeze()
    reference = load(REFERENCE)
    reference_manifest = load(REFERENCE_MANIFEST)
    manifest = load(MANIFEST)
    if sha(REFERENCE) != reference_manifest.get("reference_sha256"):
        raise RuntimeError("reference hash does not match its freeze manifest")
    batches = load_batch_inputs()
    calls = {row["batch_id"]: row for row in manifest["calls"]}
    ref_cases = {row["case_id"]: row for row in reference["cases"]}
    if len(ref_cases) != 120:
        raise RuntimeError("reference case coverage is not 120")
    candidate_diffs = []
    bundle_diffs = []
    unknown_cause = Counter()
    unknown_bundle_cause = Counter()
    errors_by_batch = {}
    error_type_counts = Counter()
    raw_status = {}
    affected = {}
    candidate_total = 0
    bundle_total = 0
    exact_candidate_matches = 0
    exact_bundle_matches = 0

    for batch_id, payload in sorted(batches.items()):
        call = calls.get(batch_id, {})
        raw_status[batch_id] = {
            "recorded": bool(call),
            "exit_code": call.get("exit_code"),
            "json_valid": call.get("json_valid", False),
            "validated_case_count": call.get("validated_case_count", 0),
            "validation_error_count": len(call.get("validation_errors", [])),
            "raw_failed": not (call.get("json_valid") and call.get("validated_case_count") == 20),
        }
        errors_by_batch[batch_id] = list(call.get("validation_errors", []))
        error_pairs = [error_key(error) for error in call.get("validation_errors", [])]
        for kind, target in error_pairs:
            error_type_counts[kind] += 1
        candidate_errors = {target for kind, target in error_pairs if kind == "invalid_candidate_review" and target}
        case_level_errors = {target for kind, target in error_pairs if kind in {"candidate_coverage_incomplete", "case_omitted", "candidate_reviews_missing", "duplicate_candidate_index"} and target}
        bundle_errors = {target for kind, target in error_pairs if kind in {"invalid_bundle_review", "bundle_review_missing"} and target}
        normalized = payload["normalized"]

        for case in payload["input"]["cases"]:
            case_id = case["case_id"]
            ref_case = ref_cases[case_id]
            norm_case = normalized.get(case_id) if normalized else None
            if norm_case is None and not raw_status[batch_id]["raw_failed"]:
                raise RuntimeError(f"normalized output missing without raw failure: {case_id}")
            for index, candidate in enumerate(case["retrieved_candidates"]):
                candidate_total += 1
                key = f"{case_id}/{index}"
                ref_review = ref_case["candidate_reviews"][index]
                if ref_review["doc_id"] != candidate["doc_id"]:
                    raise RuntimeError(f"reference candidate misalignment: {case_id}/{index}")
                norm_review = (norm_case or {}).get("candidate_reviews", {}).get(candidate["doc_id"])
                if norm_review is None:
                    raise RuntimeError(f"normalized candidate missing: {case_id}/{index}")
                comparable_ref = {field: ref_review.get(field) for field in ("label", "paragraph_indexes", "source", "rationale")}
                comparable_norm = {field: norm_review.get(field) for field in ("label", "paragraph_indexes", "source", "rationale")}
                if comparable_ref == comparable_norm:
                    exact_candidate_matches += 1
                else:
                    candidate_diffs.append({"case_id": case_id, "batch": batch_id, "candidate_index": index, "doc_id": candidate["doc_id"], "reference": comparable_ref, "normalized": comparable_norm})
                if ref_review["label"] == "UNKNOWN":
                    if raw_status[batch_id]["raw_failed"]:
                        cause = "raw_batch_failure"
                    else:
                        case_error_kinds = {kind for kind, target in error_pairs if target == case_id and kind in {"candidate_coverage_incomplete", "case_omitted", "candidate_reviews_missing", "duplicate_candidate_index"}}
                        cause = classify_unknown(case_error_kinds, ref_review, key in candidate_errors)
                    unknown_cause[cause] += 1
                    affected.setdefault(case_id, {"batch": batch_id, "candidate_unknown": [], "bundle_unknown": False, "validation_errors": []})
                    affected[case_id]["candidate_unknown"].append({"candidate_index": index, "doc_id": candidate["doc_id"], "cause": cause})
            bundle_total += 1
            ref_bundle = ref_case["bundle_review"]
            norm_bundle = (norm_case or {}).get("bundle_review")
            if norm_bundle is None:
                raise RuntimeError(f"normalized bundle missing: {case_id}")
            comparable_ref = {field: ref_bundle.get(field) for field in ("label", "supporting_doc_ids", "conflicting_doc_ids", "rationale")}
            comparable_norm = {field: norm_bundle.get(field) for field in ("label", "supporting_doc_ids", "conflicting_doc_ids", "rationale")}
            if comparable_ref == comparable_norm:
                exact_bundle_matches += 1
            else:
                bundle_diffs.append({"case_id": case_id, "batch": batch_id, "reference": comparable_ref, "normalized": comparable_norm})
            if ref_bundle["label"] == "UNKNOWN":
                if raw_status[batch_id]["raw_failed"]:
                    cause = "raw_batch_failure"
                elif case_id in bundle_errors:
                    cause = "field_validation_error"
                elif ref_bundle.get("rationale") != FILLER_RATIONALE:
                    cause = "model_explicit_unknown"
                elif case_id in case_level_errors or case_id in bundle_errors:
                    cause = "field_validation_error"
                else:
                    cause = "unattributed_structural_unknown"
                unknown_bundle_cause[cause] += 1
                affected.setdefault(case_id, {"batch": batch_id, "candidate_unknown": [], "bundle_unknown": False, "validation_errors": []})
                affected[case_id]["bundle_unknown"] = True

    if candidate_total != 947 or bundle_total != 120:
        raise RuntimeError(f"coverage mismatch: {candidate_total} candidates, {bundle_total} bundles")
    reference_unknown = reference["candidate_label_counts"].get("UNKNOWN", 0)
    reference_bundle_unknown = reference["bundle_label_counts"].get("UNKNOWN", 0)
    if sum(unknown_cause.values()) != reference_unknown:
        raise RuntimeError("candidate UNKNOWN attribution does not cover the reference count")
    if sum(unknown_bundle_cause.values()) != reference_bundle_unknown:
        raise RuntimeError("bundle UNKNOWN attribution does not cover the reference count")
    if candidate_diffs or bundle_diffs:
        raise RuntimeError(f"reference/normalized divergence: {len(candidate_diffs)} candidates, {len(bundle_diffs)} bundles")
    for case_id, info in affected.items():
        info["validation_errors"] = [error for error in errors_by_batch[info["batch"]] if case_id in error]
    return {
        "schema": "ragin.evidence_support_field_error_report.v2.2.01",
        "report_script_sha256": sha(pathlib.Path(__file__)),
        "supersedes_report_sha256": sha(SUPERSEDES) if SUPERSEDES.exists() else None,
        "upstream_hashes": {
            "reference_sha256": sha(REFERENCE),
            "reference_manifest_sha256": sha(REFERENCE_MANIFEST),
            "run_manifest_sha256": sha(MANIFEST),
            "input_freeze_sha256": sha(INPUT_FREEZE),
            "locked_evaluation_addendum_sha256": sha(ADDENDUM),
        },
        "coverage": {"cases": 120, "candidate_slots": candidate_total, "bundle_slots": bundle_total},
        "reference_vs_normalized": {"candidate_exact_matches": exact_candidate_matches, "candidate_diffs": candidate_diffs, "bundle_exact_matches": exact_bundle_matches, "bundle_diffs": bundle_diffs},
        "candidate_unknown_by_cause": dict(sorted(unknown_cause.items())),
        "bundle_unknown_by_cause": dict(sorted(unknown_bundle_cause.items())),
        "validation_error_type_counts": dict(sorted(error_type_counts.items())),
        "validation_errors_by_batch": {batch: errors_by_batch[batch] for batch in sorted(errors_by_batch)},
        "raw_response_status_by_batch": {batch: raw_status[batch] for batch in sorted(raw_status)},
        "affected_cases": dict(sorted(affected.items())),
        "verdict": {
            "reference_matches_normalization": not candidate_diffs and not bundle_diffs,
            "every_unknown_attributed": sum(unknown_cause.values()) == reference_unknown and sum(unknown_bundle_cause.values()) == reference_bundle_unknown,
            "unattributed_candidate_unknowns": unknown_cause.get("unattributed_structural_unknown", 0),
            "unattributed_bundle_unknowns": unknown_bundle_cause.get("unattributed_structural_unknown", 0),
        },
    }


def write_report() -> None:
    if REPORT.exists():
        raise RuntimeError("field-level report already exists")
    report = compare()
    report["generated_at_utc"] = base.now_utc()
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(REPORT.relative_to(base.ROOT)), "sha256": sha(REPORT), "candidate_unknown_by_cause": report["candidate_unknown_by_cause"], "bundle_unknown_by_cause": report["bundle_unknown_by_cause"], "verdict": report["verdict"]}, indent=2))


def verify_report() -> None:
    stored = load(REPORT)
    stored.pop("generated_at_utc", None)
    fresh = compare()
    mismatched = [key for key in sorted(set(stored) | set(fresh)) if stored.get(key) != fresh.get(key)]
    if mismatched:
        raise RuntimeError("stored report is stale for fields: " + ", ".join(mismatched))
    print(json.dumps({"verified": str(REPORT.relative_to(base.ROOT)), "sha256": sha(REPORT), "keys": len(fresh)}, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=["report", "verify"])
    phase = parser.parse_args().phase
    try:
        {"report": write_report, "verify": verify_report}[phase]()
        return 0
    except Exception as error:
        print(f"BLOCKED: {type(error).__name__}: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
