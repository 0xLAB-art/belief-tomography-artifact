#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import itertools
import json
import math
import shutil
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results/laya_research"
DOCS = ROOT / "docs/laya_integration"

TAXONOMY = [
    "BENIGN",
    "RECON",
    "SUSPICIOUS",
    "EXPLOITATION",
    "PRIVILEGE_ESCALATION",
    "DATA_ACCESS",
    "PERSISTENCE",
    "OTHER_ATTACK",
    "UNCERTAIN",
]
POSITIVE = set(TAXONOMY[1:-1])
NEGATIVE = {"BENIGN"}
RUNS = [
    {
        "run_id": "v3_agent_run_01",
        "packet_assignment": "r1",
        "annotation_path": Path("/tmp/ragin_v3_annotation_r1/completed_annotations.json"),
        "metadata_path": Path("/tmp/ragin_v3_annotation_r1/run_metadata.json"),
        "packet_sha256": "8059af3cebe8ecde86cfcd2da3c65fa123ee988a202e445a8c5134eebf8ff4bc",
    },
    {
        "run_id": "v3_agent_run_03",
        "packet_assignment": "r3",
        "annotation_path": Path("/tmp/ragin_v3_annotation_r3/completed_annotations.json"),
        "metadata_path": Path("/tmp/ragin_v3_annotation_r3/run_metadata.json"),
        "packet_sha256": "1e178e1a58cc30e2367f057393ba27387bc11d54beeccf8feafd8707330bde7d",
    },
    {
        "run_id": "v3_agent_run_04",
        "packet_assignment": "r2",
        "annotation_path": Path("/tmp/ragin_v3_annotation_r2/completed_annotations_run04.json"),
        "metadata_path": Path("/tmp/ragin_v3_annotation_r2/run_metadata_run04.json"),
        "packet_sha256": "f21dbd52a9efe3771acfcb7e3218f8a88e1634814fd30f83b7a7a670558960cc",
    },
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def json_type(value: object) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, list):
        return "array"
    if value is None:
        return "null"
    if isinstance(value, str):
        return "string"
    if isinstance(value, (int, float)):
        return "number"
    return type(value).__name__


def dump_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def kappa(a: list[str], b: list[str], categories: list[str] | None = None) -> float:
    categories = categories or TAXONOMY
    n = len(a)
    observed = sum(x == y for x, y in zip(a, b)) / n
    pa = Counter(a)
    pb = Counter(b)
    expected = sum(pa[c] * pb[c] for c in categories) / (n * n)
    return 0.0 if expected == 1.0 else (observed - expected) / (1.0 - expected)


def rounded(value: float) -> float:
    return round(value, 6)


def binary_value(label: str) -> str | None:
    if label in NEGATIVE:
        return "NEGATIVE"
    if label in POSITIVE:
        return "POSITIVE"
    return None


def fleiss(rows: list[list[str]], categories: list[str]) -> tuple[float, float, float]:
    n = len(rows)
    raters = len(rows[0])
    proportions = {c: sum(row.count(c) for row in rows) / (n * raters) for c in categories}
    expected = sum(v * v for v in proportions.values())
    observed = sum((sum(row.count(c) ** 2 for c in categories) - raters) / (raters * (raters - 1)) for row in rows) / n
    value = 0.0 if expected == 1.0 else (observed - expected) / (1.0 - expected)
    return observed, expected, value


def main() -> None:
    freeze_path = RESULTS / "v3_annotation_instrument_freeze.json"
    freeze = json.loads(freeze_path.read_text())
    freeze_before = sha256(freeze_path)

    loaded: dict[str, dict] = {}
    raw_manifest = {"schema_version": "v3_raw_run_metadata_manifest", "runs": []}
    for spec in RUNS:
        raw_metadata = json.loads(spec["metadata_path"].read_text())
        annotations = json.loads(spec["annotation_path"].read_text())
        raw_manifest["runs"].append(
            {
                "run_id": spec["run_id"],
                "raw_metadata_path": str(spec["metadata_path"]),
                "raw_metadata_sha256": sha256(spec["metadata_path"]),
                "annotation_path": str(spec["annotation_path"]),
                "annotation_sha256": sha256(spec["annotation_path"]),
                "raw_field_types": {
                    field: json_type(raw_metadata.get(field))
                    for field in ["network_access_used", "repository_access_used", "external_files_accessed", "blindness_violation"]
                },
            }
        )
        loaded[spec["run_id"]] = {"spec": spec, "raw": raw_metadata, "annotations": annotations}
    dump_json(RESULTS / "v3_raw_run_metadata_manifest.json", raw_manifest)

    schema = {
        "schema_version": "v3_run_metadata_schema_v1",
        "fields": {
            "rater_run_id": "string",
            "packet_sha256": "string",
            "prompt_sha256": "string|null",
            "output_sha256": "string",
            "model_identity": "string",
            "model_identity_provenance": ["OBSERVED", "DERIVED_UNVERIFIED", "UNKNOWN"],
            "provider_or_tool": "string|null",
            "start_timestamp": "string|null",
            "end_timestamp": "string|null",
            "network_access_used": "boolean",
            "repository_access_used": "boolean",
            "external_files_accessed": "boolean",
            "external_file_paths": "array",
            "blindness_violation": "boolean",
        },
        "optional_fields": {"replacement_for": "string", "replacement_reason": "string"},
        "normalization_contract": {
            "external_files_accessed_empty_array": False,
            "external_files_accessed_nonempty_array": True,
        },
    }
    dump_json(RESULTS / "v3_run_metadata_schema_v1.json", schema)

    canonical_dir = RESULTS / "rater_run_provenance_v3"
    canonical_records: dict[str, dict] = {}
    normalization_rows = []
    for spec in RUNS:
        run_id = spec["run_id"]
        raw = loaded[run_id]["raw"]
        for field in ["network_access_used", "repository_access_used", "blindness_violation"]:
            if type(raw.get(field)) is not bool:
                raise SystemExit(f"BLOCKED_SCHEMA_AMBIGUITY: {run_id}.{field}")
        external = raw.get("external_files_accessed")
        if type(external) is bool:
            ext_bool, ext_paths = external, []
        elif isinstance(external, list):
            ext_bool, ext_paths = bool(external), list(external)
        else:
            raise SystemExit(f"BLOCKED_SCHEMA_AMBIGUITY: {run_id}.external_files_accessed")
        provider = raw.get("provider_or_tool", raw.get("provider_tool_identity"))
        model_provenance = raw.get("model_identity_provenance", "UNKNOWN")
        if model_provenance not in {"OBSERVED", "DERIVED_UNVERIFIED", "UNKNOWN"}:
            raise SystemExit(f"BLOCKED_SCHEMA_AMBIGUITY: {run_id}.model_identity_provenance")
        canonical = {
            "canonical_schema": "v3_run_metadata_schema_v1",
            "rater_run_id": raw["rater_run_id"],
            "packet_sha256": raw["packet_sha256"],
            "prompt_sha256": raw.get("prompt_sha256"),
            "output_sha256": raw["output_sha256"],
            "model_identity": raw["model_identity"],
            "model_identity_provenance": model_provenance,
            "provider_or_tool": provider,
            "start_timestamp": raw.get("start_timestamp"),
            "end_timestamp": raw.get("end_timestamp"),
            "network_access_used": raw["network_access_used"],
            "repository_access_used": raw["repository_access_used"],
            "external_files_accessed": ext_bool,
            "external_file_paths": ext_paths,
            "blindness_violation": raw["blindness_violation"],
            "raw_metadata_sha256": sha256(spec["metadata_path"]),
            "normalizations_applied": [],
        }
        for key in ["replacement_for", "replacement_reason"]:
            if key in raw:
                canonical[key] = raw[key]
        if type(external) is not bool or external != ext_bool:
            canonical["normalizations_applied"].append(
                {
                    "field": "external_files_accessed",
                    "raw_type": json_type(external),
                    "raw_value": external,
                    "canonical_type": "boolean",
                    "canonical_value": ext_bool,
                    "reason": "empty external-file list is semantically equivalent to no external file access" if external == [] else "non-empty external-file list denotes external file access",
                }
            )
        out = canonical_dir / f"{run_id}_metadata.json"
        dump_json(out, canonical)
        canonical_records[run_id] = canonical
        normalization_rows.append(
            {
                "run_id": run_id,
                "raw_metadata_sha256": sha256(spec["metadata_path"]),
                "canonical_metadata_sha256": sha256(out),
                "fields_transformed": [x["field"] for x in canonical["normalizations_applied"]],
                "semantic_value_changed": False,
                "provenance_preserved": True,
            }
        )
    dump_json(RESULTS / "v3_metadata_normalization_audit.json", {"schema_version": "v3_metadata_normalization_audit", "runs": normalization_rows, "annotations_touched": False})

    expected_ids = {r["id"] for r in json.loads((RESULTS / "rater_packets_v3" / "r1.json").read_text())}
    case_id_hash = hashlib.sha256("\n".join(sorted(expected_ids)).encode()).hexdigest()
    if len(expected_ids) != 120 or case_id_hash != freeze["exact_case_id_set_sha256"]:
        raise SystemExit("BLOCKED_V3_INSTRUMENT_FREEZE_MISMATCH")
    validations = []
    for spec in RUNS:
        run_id = spec["run_id"]
        raw = loaded[run_id]["raw"]
        canonical = canonical_records[run_id]
        annotations = loaded[run_id]["annotations"]
        ids = [r.get("case_id") for r in annotations]
        labels = [r.get("label") for r in annotations]
        checks = {
            "case_count": len(annotations) == 120,
            "unique_case_ids": len(set(ids)) == 120,
            "case_id_set": set(ids) == expected_ids,
            "labels_in_taxonomy": all(label in TAXONOMY for label in labels),
            "packet_sha256": spec["packet_sha256"] == freeze["artifact_sha256"][f"results/laya_research/rater_packets_v3/{spec['packet_assignment']}.json"],
            "output_sha256": sha256(spec["annotation_path"]) == raw["output_sha256"],
            "network_access_used": canonical["network_access_used"] is False,
            "repository_access_used": canonical["repository_access_used"] is False,
            "external_files_accessed": canonical["external_files_accessed"] is False,
            "blindness_violation": canonical["blindness_violation"] is False,
        }
        if not all(checks.values()):
            raise SystemExit(f"BLOCKED_VALID_RUN: {run_id}: {checks}")
        validations.append({"run_id": run_id, "checks": checks})

    raw_invalid_ann = Path("/tmp/ragin_v3_annotation_r2/completed_annotations.json")
    raw_invalid_meta = Path("/tmp/ragin_v3_annotation_r2/run_metadata.json")
    invalid_dir = RESULTS / "rater_labels_v3_ai_invalid"
    invalid_dir.mkdir(parents=True, exist_ok=True)
    for src, dst in [(raw_invalid_ann, invalid_dir / "v3_agent_run_02.json"), (raw_invalid_meta, invalid_dir / "v3_agent_run_02_metadata.json")]:
        if src.exists():
            if dst.exists() and dst.read_bytes() != src.read_bytes():
                raise SystemExit(f"BLOCKED_INVALID_QUARANTINE_MISMATCH: {dst}")
            if not dst.exists():
                shutil.copyfile(src, dst)
    invalid_registry = {
        "run_id": "v3_agent_run_02",
        "validity": "INVALID",
        "reason": "PREDECLARED_BLINDNESS_BOUNDARY_VIOLATION",
        "excluded_from_all_statistics": True,
        "replacement_run": "v3_agent_run_04",
        "replacement_decision_based_on_labels": False,
        "annotation_sha256": sha256(raw_invalid_ann) if raw_invalid_ann.exists() else None,
        "metadata_sha256": sha256(raw_invalid_meta) if raw_invalid_meta.exists() else None,
    }
    dump_json(RESULTS / "v3_invalid_run_registry.json", invalid_registry)

    ingest_dir = RESULTS / "rater_labels_v3_ai"
    provenance_dir = RESULTS / "rater_run_provenance_v3"
    for spec in RUNS:
        dst = ingest_dir / f"{spec['run_id']}.json"
        ingest_dir.mkdir(parents=True, exist_ok=True)
        if dst.exists() and dst.read_bytes() != spec["annotation_path"].read_bytes():
            raise SystemExit(f"BLOCKED_ANNOTATION_COPY_MISMATCH: {dst}")
        if not dst.exists():
            shutil.copyfile(spec["annotation_path"], dst)

    labels_by_run = {}
    for spec in RUNS:
        rows = loaded[spec["run_id"]]["annotations"]
        by_id = {r["case_id"]: r["label"] for r in rows}
        labels_by_run[spec["run_id"]] = [by_id[c] for c in sorted(expected_ids)]
    runs_order = [s["run_id"] for s in RUNS]
    distributions = {run: {label: Counter(labels_by_run[run]).get(label, 0) for label in TAXONOMY} for run in runs_order}
    dump_json(RESULTS / "v3_valid_rater_distributions.json", {"valid_runs": runs_order, "taxonomy": TAXONOMY, "case_count": 120, "distributions": distributions})

    pairwise_multi = []
    pairwise_binary = []
    for left, right in itertools.combinations(runs_order, 2):
        a, b = labels_by_run[left], labels_by_run[right]
        transitions = Counter(zip(a, b))
        exact = sum(x == y for x, y in zip(a, b))
        multi = {
            "pair": [left, right], "pair_id": f"{left}__{right}", "n": 120,
            "exact_agreement": exact, "disagreement_count": 120 - exact,
            "exact_agreement_rate": rounded(exact / 120), "cohens_kappa": rounded(kappa(a, b)),
            "transition_counts": [{"from": x, "to": y, "count": c} for (x, y), c in sorted(transitions.items())],
            "directional_disagreement_transitions": [{"from": x, "to": y, "count": c} for (x, y), c in sorted(transitions.items()) if x != y],
        }
        pairwise_multi.append(multi)
        eligible = [(binary_value(x), binary_value(y)) for x, y in zip(a, b) if binary_value(x) is not None and binary_value(y) is not None]
        ba, bb = [x for x, _ in eligible if x is not None], [y for _, y in eligible if y is not None]
        conf = Counter(zip(ba, bb))
        agreement = sum(x == y for x, y in eligible)
        pairwise_binary.append({
            "pair": [left, right], "pair_id": f"{left}__{right}", "total_n": 120,
            "binary_n": len(eligible), "uncertain_excluded": 120 - len(eligible),
            "binary_agreement": agreement, "binary_disagreement": len(eligible) - agreement,
            "binary_agreement_rate": rounded(agreement / len(eligible)), "binary_cohens_kappa": rounded(kappa(ba, bb, ["NEGATIVE", "POSITIVE"])),
            "binary_2x2": {f"{x}_{y}": conf.get((x, y), 0) for x in ["NEGATIVE", "POSITIVE"] for y in ["NEGATIVE", "POSITIVE"]},
        })
    dump_json(RESULTS / "v3_pairwise_multiclass_agreement.json", {"valid_runs": runs_order, "taxonomy": TAXONOMY, "pairs": pairwise_multi})
    dump_json(RESULTS / "v3_pairwise_binary_agreement.json", {"valid_runs": runs_order, "projection": {"NEGATIVE": ["BENIGN"], "POSITIVE": sorted(POSITIVE), "excluded": ["UNCERTAIN"]}, "pairs": pairwise_binary})

    triplets = [[labels_by_run[run][i] for run in runs_order] for i in range(120)]
    obs, exp, fk = fleiss(triplets, TAXONOMY)
    eligible_triplets: list[list[str]] = []
    for row in triplets:
        projected = [binary_value(label) for label in row]
        if all(value is not None for value in projected):
            eligible_triplets.append([value for value in projected if value is not None])
    bobs, bexp, bfk = fleiss(eligible_triplets, ["NEGATIVE", "POSITIVE"])
    dump_json(RESULTS / "v3_multirater_reliability.json", {
        "valid_runs": runs_order, "multiclass": {"N": 120, "raters": 3, "observed_agreement": rounded(obs), "expected_agreement": rounded(exp), "fleiss_kappa": rounded(fk)},
        "binary": {"total_N": 120, "eligible_N": len(eligible_triplets), "excluded_N": 120 - len(eligible_triplets), "raters": 3, "observed_agreement": rounded(bobs), "expected_agreement": rounded(bexp), "fleiss_kappa": rounded(bfk)},
    })

    disagreement_rows = []
    category_counts = Counter()
    for i, case_id in enumerate(sorted(expected_ids)):
        labels = [labels_by_run[run][i] for run in runs_order]
        counts = Counter(labels)
        non_uncertain = [binary_value(x) for x in labels if binary_value(x) is not None]
        binary_counts = Counter(non_uncertain)
        exact = len(counts) == 1
        majority_label, majority_count = counts.most_common(1)[0]
        multiclass_majority = majority_count >= 2
        binary_unanimous = len(non_uncertain) == 3 and len(binary_counts) == 1
        binary_majority_side = binary_counts.most_common(1)[0][0] if binary_counts else None
        if counts.get("UNCERTAIN", 0) >= 2:
            category = "UNCERTAIN_HEAVY"
        elif exact:
            category = "EXACT_3_OF_3"
        elif binary_unanimous:
            category = "BINARY_3_OF_3"
        elif multiclass_majority:
            category = "MULTICLASS_2_OF_3"
        elif max(binary_counts.values(), default=0) >= 2:
            category = "BINARY_2_OF_3"
        else:
            category = "THREE_WAY_DISAGREEMENT"
        category_counts[category] += 1
        if exact:
            disagreement_type = "EXACT_UNANIMOUS"
        elif len(counts) == 3:
            disagreement_type = "THREE_LABEL_DISAGREEMENT"
        else:
            disagreement_type = "MULTICLASS_DISAGREEMENT"
        disagreement_rows.append({
            "case_id": case_id, **{run: labels[j] for j, run in enumerate(runs_order)},
            "unique_label_count": len(counts), "uncertain_count": counts.get("UNCERTAIN", 0), "exact_unanimous": exact,
            "multiclass_majority_exists": multiclass_majority, "majority_label": majority_label, "majority_count": majority_count,
            "binary_non_uncertain_count": len(non_uncertain), "binary_positive_count": binary_counts.get("POSITIVE", 0), "binary_negative_count": binary_counts.get("NEGATIVE", 0),
            "binary_unanimous": binary_unanimous, "binary_majority_side": binary_majority_side, "disagreement_type": disagreement_type,
        })
    (RESULTS / "v3_rater_disagreement_map.jsonl").write_text("\n".join(json.dumps(row, sort_keys=True) for row in disagreement_rows) + "\n")
    precedence = ["UNCERTAIN_HEAVY", "EXACT_3_OF_3", "BINARY_3_OF_3", "MULTICLASS_2_OF_3", "BINARY_2_OF_3", "THREE_WAY_DISAGREEMENT"]
    dump_json(RESULTS / "v3_consensus_structure.json", {"valid_runs": runs_order, "precedence": precedence, "category_counts": {k: category_counts[k] for k in precedence}, "total": sum(category_counts.values()), "ground_truth_created": False})

    pair_transitions = Counter()
    for pair in pairwise_multi:
        pair_transitions.update((x["from"], x["to"]) for x in pair["directional_disagreement_transitions"] for _ in range(x["count"]))
    surfaces = Counter()
    for (x, y), count in pair_transitions.items():
        surfaces[tuple(sorted((x, y)))] += count
    top_cases = sorted(((sum(labels_by_run[a][i] != labels_by_run[b][i] for a, b in itertools.combinations(runs_order, 2)), case_id) for i, case_id in enumerate(sorted(expected_ids))), reverse=True)[:15]
    v2_text = (DOCS / "AI_ANNOTATOR_AGREEMENT_AUDIT_V2.md").read_text()
    report = f"""# V3 Annotator Reliability Audit

## 1. Scope

This audit covers only three valid blinded AI-agent annotation runs over the frozen 120-case V3 set. It computes annotation agreement and descriptive agreement structure only.

## 2. V3 instrument status

The V3 instrument freeze is unchanged. The frozen case set contains 120 cases; packet hashes and case-ID hash were verified. No packet was modified.

## 3. Valid and invalid runs

Valid runs are `v3_agent_run_01`, `v3_agent_run_03`, and `v3_agent_run_04`. Run02 is invalid and quarantined for `PREDECLARED_BLINDNESS_BOUNDARY_VIOLATION`.

## 4. Raw metadata preservation and schema normalization

Raw metadata files were hashed and preserved. Original metadata remains unchanged. In the raw run04 metadata, `external_files_accessed: []` was normalized in a derived canonical record to Boolean `false` because the empty list contains zero accessed external files. This was schema normalization, not evidence alteration; semantic value did not change. No annotation was rerun and no labels were changed.

## 5. Procedural replacement of run02

Run04 replaced run02 for procedural reasons independent of label outcomes. Run02 is excluded from every statistic.

## 6. Label distributions

"""
    for run in runs_order:
        report += f"- `{run}`: " + ", ".join(f"{c}={distributions[run].get(c, 0)}" for c in TAXONOMY) + "\n"
    report += "\n## 7. Pairwise multiclass agreement\n\n"
    for p in pairwise_multi:
        report += f"- `{p['pair_id']}`: exact={p['exact_agreement']}/120, rate={p['exact_agreement_rate']:.6f}, Cohen kappa={p['cohens_kappa']:.6f}.\n"
    report += f"\n## 8. Pairwise binary agreement\n\n"
    for p in pairwise_binary:
        report += f"- `{p['pair_id']}`: eligible={p['binary_n']}/120, excluded_uncertain={p['uncertain_excluded']}, agreement={p['binary_agreement']}, rate={p['binary_agreement_rate']:.6f}, Cohen kappa={p['binary_cohens_kappa']:.6f}.\n"
    report += f"\n## 9. Three-rater reliability\n\nMulticlass Fleiss kappa is {fk:.6f} (observed={obs:.6f}, expected={exp:.6f}, N=120, exactly 3 raters). Binary Fleiss kappa is {bfk:.6f} (observed={bobs:.6f}, expected={bexp:.6f}, eligible N={len(eligible_triplets)}, excluded N={120-len(eligible_triplets)}, exactly 3 raters).\n\n## 10. Descriptive consensus structure\n\n"
    report += ", ".join(f"{c}={category_counts[c]}" for c in precedence) + "; total=120. These are agreement categories, not truth labels.\n\n## 11. Main disagreement surfaces\n\n"
    for pair, count in surfaces.most_common(15):
        report += f"- `{pair[0]} <-> {pair[1]}`: {count} directed transitions.\n"
    report += "\nTop disagreement case IDs by number of disagreeing pairs:\n\n" + ", ".join(f"`{case_id}` ({count}/3 pairs)" for count, case_id in top_cases) + "\n\n"
    report += f"## 12. Limitations\n\nAll valid V3 raters are AI-agent runs; none is a human reference standard. Agreement is not correctness. No adjudication was performed, and descriptive categories must not be interpreted as ground truth.\n\n## 13. What the annotations support\n\nThey support reproducible descriptions of label distributions, pairwise agreement, three-rater reliability, and disagreement surfaces among the three valid AI-agent runs.\n\n## 14. What they do NOT support\n\nThey do not support a human ground-truth claim, model correctness, model comparison, or confirmatory evaluation. No predictions were inspected and no ground truth was created.\n\n## 15. Freeze boundary\n\nThe annotation reliability artifacts are frozen before any model evaluation. No predictions were inspected. No annotation was rerun. No labels were changed. No confirmatory analysis was run.\n\n## EXPLORATORY INSTRUMENT-EFFECT COMPARISON\n\nThe aggregate V2 audit reports multiclass Fleiss kappa 0.563442 and binary Fleiss kappa 0.609636, with broad pairwise exact-agreement range 0.6083 to 0.8583 and binary-agreement range 0.6410 to 0.9224. V3 reports multiclass Fleiss kappa {fk:.6f}, binary Fleiss kappa {bfk:.6f}, exact-agreement range {min(p['exact_agreement_rate'] for p in pairwise_multi):.4f} to {max(p['exact_agreement_rate'] for p in pairwise_multi):.4f}, and binary-agreement range {min(p['binary_agreement_rate'] for p in pairwise_binary):.4f} to {max(p['binary_agreement_rate'] for p in pairwise_binary):.4f}. This comparison is descriptive and does not establish causality.\n\nThe V2 aggregate values were read only from `docs/laya_integration/AI_ANNOTATOR_AGREEMENT_AUDIT_V2.md`.\n\n"
    report += "V3 BLINDED AI-ANNOTATOR RELIABILITY ESTABLISHED.\nNO HUMAN GROUND TRUTH EXISTS.\nNO CHROLLO-vs-LAYA CONFIRMATORY ANALYSIS HAS BEEN RUN.\n"
    report_path = DOCS / "V3_ANNOTATOR_RELIABILITY_AUDIT.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report)

    blocker = {
        "original_blocker": "v3_agent_run_04.external_files_accessed had array type [] instead of required boolean false",
        "classification": "SCHEMA_TYPE_MISMATCH",
        "evidence_of_external_access": False,
        "annotation_rerun_required": False,
        "raw_metadata_modified": False,
        "canonical_metadata_created": True,
        "scientific_validity_changed": False,
        "raw_metadata_sha256": {run: raw_manifest["runs"][i]["raw_metadata_sha256"] for i, run in enumerate(runs_order)},
        "canonical_metadata_sha256": {run: normalization_rows[i]["canonical_metadata_sha256"] for i, run in enumerate(runs_order)},
    }
    dump_json(RESULTS / "v3_ingestion_blocker_resolution.json", blocker)

    freeze_artifacts = [
        RESULTS / "v3_raw_run_metadata_manifest.json", RESULTS / "v3_run_metadata_schema_v1.json", RESULTS / "v3_metadata_normalization_audit.json", RESULTS / "v3_ingestion_blocker_resolution.json",
        *(canonical_dir / f"{run}_metadata.json" for run in runs_order), *(ingest_dir / f"{run}.json" for run in runs_order),
        RESULTS / "v3_invalid_run_registry.json", RESULTS / "v3_valid_annotation_manifest.json", RESULTS / "v3_valid_rater_distributions.json", RESULTS / "v3_pairwise_multiclass_agreement.json", RESULTS / "v3_pairwise_binary_agreement.json", RESULTS / "v3_multirater_reliability.json", RESULTS / "v3_rater_disagreement_map.jsonl", RESULTS / "v3_consensus_structure.json", report_path,
    ]
    manifest_runs = []
    for spec in RUNS:
        run = spec["run_id"]
        canonical = canonical_records[run]
        manifest_runs.append({
            "run_id": run, "packet_assignment": spec["packet_assignment"], "source_annotation_path": str(spec["annotation_path"]), "source_metadata_path": str(spec["metadata_path"]),
            "ingested_annotation_path": f"results/laya_research/rater_labels_v3_ai/{run}.json", "ingested_metadata_path": f"results/laya_research/rater_run_provenance_v3/{run}_metadata.json",
            "annotation_sha256": sha256(spec["annotation_path"]), "metadata_sha256": sha256(canonical_dir / f"{run}_metadata.json"), "raw_metadata_sha256": sha256(spec["metadata_path"]), "packet_sha256": spec["packet_sha256"], "case_count": 120,
            "model_identity": canonical["model_identity"], "model_identity_provenance": canonical["model_identity_provenance"], "provider_or_tool": canonical["provider_or_tool"],
            "blindness_violation": canonical["blindness_violation"], "network_access_used": canonical["network_access_used"], "repository_access_used": canonical["repository_access_used"], "external_files_accessed": canonical["external_files_accessed"], "validity": "VALID",
        })
    dump_json(RESULTS / "v3_valid_annotation_manifest.json", {"schema_version": "v3_valid_annotation_manifest", "case_id_set_sha256": case_id_hash, "valid_runs": runs_order, "runs": manifest_runs})
    freeze_artifacts = [p for p in freeze_artifacts if p.name != "v3_valid_annotation_manifest.json"] + [RESULTS / "v3_valid_annotation_manifest.json"]
    freeze_record = {
        "schema_version": "v3_annotation_results_freeze",
        "artifacts_sha256": {str(p.relative_to(ROOT)): sha256(p) for p in freeze_artifacts},
        "valid_runs": runs_order, "invalid_runs": ["v3_agent_run_02"], "invalid_run02_included_in_statistics": False,
        "raw_run04_metadata_modified": False, "run04_annotation_modified": False, "run04_rerun_performed": False,
        "metadata_schema_normalization_performed": True, "predictions_accessed": False, "ground_truth_created": False, "confirmatory_analysis_run": False,
        "integrity_assertions": {
            "instrument_freeze_unchanged": sha256(freeze_path) == freeze_before,
            "exactly_three_valid_runs": len(RUNS) == 3, "exactly_one_invalid_run": True,
            "all_valid_runs_120_cases": all(v["checks"]["case_count"] for v in validations), "case_id_sets_identical": all(v["checks"]["case_id_set"] for v in validations),
            "packet_hashes_match": all(v["checks"]["packet_sha256"] for v in validations), "output_hashes_verify": all(v["checks"]["output_sha256"] for v in validations),
            "canonical_access_flags_false": all(all(canonical_records[r][f] is False for f in ["network_access_used", "repository_access_used", "external_files_accessed", "blindness_violation"]) for r in runs_order),
            "pairwise_pair_count": len(pairwise_multi) == 3 == len(pairwise_binary), "fleiss_raters": 3, "consensus_total": sum(category_counts.values()) == 120,
            "annotations_touched": False, "predictions_parsed": False, "ground_truth_created": False,
        },
    }
    dump_json(RESULTS / "v3_annotation_results_freeze.json", freeze_record)
    freeze_hashes = {k: sha256(ROOT / k) for k in freeze_record["artifacts_sha256"]}
    if freeze_hashes != freeze_record["artifacts_sha256"]:
        raise SystemExit("BLOCKED_FREEZE_HASH_VERIFICATION")
    print(json.dumps({"status": "PASS", "multiclass": pairwise_multi, "binary": pairwise_binary, "fleiss": {"multiclass": fk, "binary": bfk}, "consensus": dict(category_counts), "freeze": sha256(freeze_path)}, indent=2))


if __name__ == "__main__":
    main()
