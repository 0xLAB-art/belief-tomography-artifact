#!/usr/bin/env python3
"""Recompute the blinded AI-annotator reliability audit from raw run files.

This script deliberately names only the reliability inputs.  It does not open
prediction, ground-truth, or confirmatory-evaluation files.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "laya_research"
DOCS = ROOT / "docs" / "laya_integration"

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

SOURCE_RUNS = [
    {
        "legacy_id": "ai_r1",
        "run_id": "agent_run_01",
        "path": "results/laya_research/ai_raters/codex_r1.json",
        "packet": "r1",
        "model": "gpt-5.6-luna",
        "model_provenance": "OBSERVED",
    },
    {
        "legacy_id": "ai_r2",
        "run_id": "agent_run_02",
        "path": "results/laya_research/ai_raters/codex_r2.json",
        "packet": "r2",
        "model": "gpt-5.6-luna",
        "model_provenance": "OBSERVED",
    },
    {
        "legacy_id": "ai_r3",
        "run_id": "agent_run_03",
        "path": "results/laya_research/ai_raters/codex_r3.json",
        "packet": "r3",
        "model": "gpt-5.6-luna",
        "model_provenance": "OBSERVED",
    },
    {
        "legacy_id": "human_r1",
        "run_id": "agent_run_04",
        "path": "results/laya_research/rater_labels/r1.json",
        "packet": "r1",
        "model": "UNKNOWN",
        "model_provenance": "DERIVED_UNVERIFIED",
    },
    {
        "legacy_id": "human_r2",
        "run_id": "agent_run_05",
        "path": "results/laya_research/rater_labels/r2.json",
        "packet": "r2",
        "model": "UNKNOWN",
        "model_provenance": "DERIVED_UNVERIFIED",
    },
    {
        "legacy_id": "human_r3",
        "run_id": "agent_run_06",
        "path": "results/laya_research/rater_labels/r3.json",
        "packet": "r3",
        "model": "UNKNOWN",
        "model_provenance": "DERIVED_UNVERIFIED",
    },
]

PACKETS = [
    {
        "legacy_id": "packet_r1",
        "run_id": "packet_r1",
        "path": "results/laya_research/rater_packets/r1.json",
        "packet": "r1",
    },
    {
        "legacy_id": "packet_r2",
        "run_id": "packet_r2",
        "path": "results/laya_research/rater_packets/r2.json",
        "packet": "r2",
    },
    {
        "legacy_id": "packet_r3",
        "run_id": "packet_r3",
        "path": "results/laya_research/rater_packets/r3.json",
        "packet": "r3",
    },
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def rate(value: float) -> float:
    return round(value, 6)


def load_labels(path: Path) -> dict[str, str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    entries = payload.get("labels", payload.get("items"))
    if not isinstance(entries, list):
        raise AssertionError(f"No label list in {path}")
    labels = {entry["case_id"]: entry["label"] for entry in entries}
    if len(labels) != len(entries):
        raise AssertionError(f"Duplicate case IDs in {path}")
    return labels


def nominal_kappa(left: list[str], right: list[str], categories: list[str]) -> float:
    if len(left) != len(right) or not left:
        raise AssertionError("Kappa inputs must have equal nonzero length")
    n = len(left)
    observed = sum(a == b for a, b in zip(left, right)) / n
    left_counts = Counter(left)
    right_counts = Counter(right)
    expected = sum(left_counts[c] * right_counts[c] for c in categories) / (n * n)
    return 1.0 if expected == 1.0 else (observed - expected) / (1.0 - expected)


def fleiss(matrix: list[list[str]], categories: list[str]) -> dict[str, float]:
    if not matrix or not matrix[0]:
        raise AssertionError("Fleiss matrix must be nonempty")
    n_cases = len(matrix)
    n_raters = len(matrix[0])
    if any(len(row) != n_raters for row in matrix):
        raise AssertionError("Fleiss matrix has variable rater counts")
    if n_raters < 2:
        raise AssertionError("Fleiss requires at least two raters")
    agreements = []
    for row in matrix:
        counts = Counter(row)
        agreements.append((sum(value * value for value in counts.values()) - n_raters) / (n_raters * (n_raters - 1)))
    observed = sum(agreements) / n_cases
    proportions = [
        sum(row.count(category) for row in matrix) / (n_cases * n_raters)
        for category in categories
    ]
    expected = sum(value * value for value in proportions)
    kappa = 1.0 if expected == 1.0 else (observed - expected) / (1.0 - expected)
    return {
        "observed_agreement": rate(observed),
        "expected_agreement": rate(expected),
        "fleiss_kappa": rate(kappa),
    }


def transition_list(left: dict[str, str], right: dict[str, str], cases: list[str]) -> list[dict[str, object]]:
    transitions = Counter(
        (left[case], right[case])
        for case in cases
        if left[case] != right[case]
    )
    return [
        {"from": source, "to": target, "count": count}
        for (source, target), count in sorted(
            transitions.items(), key=lambda item: (-item[1], item[0][0], item[0][1])
        )
    ]


def pair_metrics(left_id: str, right_id: str, labels: dict[str, dict[str, str]], cases: list[str]) -> dict[str, Any]:
    left = labels[left_id]
    right = labels[right_id]
    left_values = [left[case] for case in cases]
    right_values = [right[case] for case in cases]
    exact_agreement = sum(a == b for a, b in zip(left_values, right_values))
    binary_cases = [
        case
        for case in cases
        if left[case] != "UNCERTAIN" and right[case] != "UNCERTAIN"
    ]
    left_binary = ["POSITIVE" if left[case] in POSITIVE else "NEGATIVE" for case in binary_cases]
    right_binary = ["POSITIVE" if right[case] in POSITIVE else "NEGATIVE" for case in binary_cases]
    binary_agreement = sum(a == b for a, b in zip(left_binary, right_binary))
    return {
        "pair_id": f"{left_id}__{right_id}",
        "pair": [left_id, right_id],
        "n": len(cases),
        "exact_agreement": exact_agreement,
        "exact_rate": rate(exact_agreement / len(cases)),
        "disagreement_count": len(cases) - exact_agreement,
        "cohens_kappa": rate(nominal_kappa(left_values, right_values, TAXONOMY)),
        "binary_n": len(binary_cases),
        "excluded_uncertain": len(cases) - len(binary_cases),
        "binary_agreement": binary_agreement,
        "binary_rate": rate(binary_agreement / len(binary_cases)),
        "binary_cohens_kappa": rate(nominal_kappa(left_binary, right_binary, ["NEGATIVE", "POSITIVE"])),
        "label_transitions": transition_list(left, right, cases),
    }


def consensus_records(labels: dict[str, dict[str, str]], run_ids: list[str], cases: list[str]) -> tuple[list[dict[str, Any]], Counter, Counter, Counter]:
    records: list[dict[str, Any]] = []
    exact_counts = Counter()
    binary_view_counts = Counter()
    ambiguity_reasons = Counter()
    for case in cases:
        per_run = {run_id: labels[run_id][case] for run_id in run_ids}
        values = list(per_run.values())
        counts = Counter(values)
        uncertain_count = values.count("UNCERTAIN")
        positive_count = sum(value in POSITIVE for value in values)
        negative_count = values.count("BENIGN")
        non_uncertain_count = positive_count + negative_count
        exact_consensus = len(counts) == 1
        majority_count = max(counts.values())
        strict_majority = majority_count >= 4
        binary_unanimous = non_uncertain_count >= 4 and (
            positive_count == non_uncertain_count or negative_count == non_uncertain_count
        )
        binary_strict_majority = max(positive_count, negative_count) >= 4
        if exact_consensus:
            ambiguity_class = "STRONG_CONSENSUS"
        elif binary_unanimous:
            ambiguity_class = "BINARY_CONSENSUS"
        elif strict_majority:
            ambiguity_class = "STRICT_MAJORITY"
        else:
            ambiguity_class = "HIGH_AMBIGUITY"
        if exact_consensus:
            binary_view = "BINARY_STRONG_CONSENSUS"
        elif binary_unanimous:
            binary_view = "BINARY_CONSENSUS"
        elif binary_strict_majority:
            binary_view = "BINARY_STRICT_MAJORITY"
        else:
            binary_view = "HIGH_AMBIGUITY"
        exact_counts[ambiguity_class] += 1
        binary_view_counts[binary_view] += 1
        if ambiguity_class == "HIGH_AMBIGUITY":
            if majority_count == 3:
                ambiguity_reasons["no_exact_label_at_least_4_of_6"] += 1
            if positive_count and negative_count:
                ambiguity_reasons["cross_binary_disagreement"] += 1
            if non_uncertain_count < 4:
                ambiguity_reasons["too_many_uncertain_for_binary_support"] += 1
        majority_label = None
        if sum(value == majority_count for value in counts.values()) == 1:
            majority_label = next(label for label, count in counts.items() if count == majority_count)
        records.append(
            {
                "case_id": case,
                "labels": per_run,
                "unique_label_count": len(counts),
                "uncertain_count": uncertain_count,
                "exact_consensus_6_of_6": exact_consensus,
                "strict_multiclass_majority": strict_majority,
                "strict_multiclass_majority_count": majority_count,
                "strict_multiclass_majority_label": majority_label,
                "binary_non_uncertain_count": non_uncertain_count,
                "binary_positive_count": positive_count,
                "binary_negative_count": negative_count,
                "binary_unanimous": binary_unanimous,
                "binary_strict_majority": binary_strict_majority,
                "ambiguity_class": ambiguity_class,
            }
        )
    return records, exact_counts, binary_view_counts, ambiguity_reasons


def markdown_table(rows: list[list[object]], headers: list[str]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    lines.extend("| " + " | ".join(str(cell) for cell in row) + " |" for row in rows)
    return "\n".join(lines)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    DOCS.mkdir(parents=True, exist_ok=True)

    labels: dict[str, dict[str, str]] = {}
    source_records: list[dict[str, Any]] = []
    for spec in SOURCE_RUNS:
        path = ROOT / spec["path"]
        run_labels = load_labels(path)
        labels[spec["run_id"]] = run_labels
        source_records.append(
            {
                "run_id": spec["run_id"],
                "previous_run_id": spec["legacy_id"],
                "original_path": spec["path"],
                "rater_packet_id": spec["packet"],
                "instrument_only": False,
                "has_labels": True,
                "model_identity": spec["model"],
                "model_identity_provenance": spec["model_provenance"],
                "timestamp": "2026-10-12T00:00:00Z",
                "timestamp_provenance": "DERIVED_UNVERIFIED",
                "sha256": sha256(path),
                "case_count": len(run_labels),
                "label_distribution": dict(sorted(Counter(run_labels.values()).items())),
            }
        )

    packet_records: list[dict[str, Any]] = []
    for spec in PACKETS:
        path = ROOT / spec["path"]
        packet_labels = load_labels(path)
        packet_records.append(
            {
                "run_id": spec["run_id"],
                "previous_run_id": spec["legacy_id"],
                "original_path": spec["path"],
                "rater_packet_id": spec["packet"],
                "instrument_only": True,
                "has_labels": False,
                "model_identity": "UNKNOWN",
                "model_identity_provenance": "UNKNOWN",
                "timestamp": "2026-10-12T00:00:00Z",
                "timestamp_provenance": "DERIVED_UNVERIFIED",
                "sha256": sha256(path),
                "case_count": len(packet_labels),
                "label_distribution": dict(sorted(Counter(packet_labels.values()).items())),
            }
        )

    run_ids = [spec["run_id"] for spec in SOURCE_RUNS]
    cases = sorted(labels[run_ids[0]])
    if len(run_ids) != 6 or len(packet_records) != 3:
        raise AssertionError("Expected six labeled runs and three instrument-only packets")
    if any(set(labels[run_id]) != set(cases) for run_id in run_ids):
        raise AssertionError("Labeled run case ID sets do not match")
    if any(len(labels[run_id]) != 120 for run_id in run_ids):
        raise AssertionError("Each labeled run must contain exactly 120 cases")
    if any(label not in TAXONOMY for run_id in run_ids for label in labels[run_id].values()):
        raise AssertionError("A labeled run contains a label outside the taxonomy")
    if any(label == "" for run_id in run_ids for label in labels[run_id].values()):
        raise AssertionError("A labeled run contains a blank label")
    if any(record["label_distribution"] != {"": 120} for record in packet_records):
        raise AssertionError("An instrument-only packet is not blank")

    pair_records = [
        pair_metrics(left_id, right_id, labels, cases)
        for left_id, right_id in itertools.combinations(run_ids, 2)
    ]
    if len(pair_records) != 15:
        raise AssertionError("Expected exactly 15 pairwise comparisons")
    for pair in pair_records:
        if pair["exact_agreement"] + pair["disagreement_count"] != 120:
            raise AssertionError(f"Exact/disagreement invariant failed for {pair['pair_id']}")
        if pair["binary_n"] + pair["excluded_uncertain"] != 120:
            raise AssertionError(f"Binary denominator invariant failed for {pair['pair_id']}")

    multiclass_matrix = [[labels[run_id][case] for run_id in run_ids] for case in cases]
    multiclass_fleiss = fleiss(multiclass_matrix, TAXONOMY)
    binary_cases = [case for case in cases if all(labels[run_id][case] != "UNCERTAIN" for run_id in run_ids)]
    binary_matrix = [
        ["POSITIVE" if labels[run_id][case] in POSITIVE else "NEGATIVE" for run_id in run_ids]
        for case in binary_cases
    ]
    binary_fleiss = fleiss(binary_matrix, ["NEGATIVE", "POSITIVE"])

    consensus, exact_counts, binary_view_counts, ambiguity_reasons = consensus_records(labels, run_ids, cases)
    if sum(exact_counts.values()) != 120 or len(consensus) != 120:
        raise AssertionError("Strict consensus categories do not sum to 120")
    if any(sum(record["ambiguity_class"] == category for record in consensus) != exact_counts[category] for category in exact_counts):
        raise AssertionError("A case was assigned inconsistently in strict consensus")

    manifest = {
        "schema_version": "ai_rater_runs_manifest_v2",
        "description": "Corrected provenance manifest for six labeled AI-agent annotation runs and three blank instrument packets.",
        "labeled_run_count": 6,
        "instrument_only_count": 3,
        "run_records": source_records + packet_records,
        "classification_rule": "Only records with nonblank labels are LABELED_AI_RUN; blank packets are INSTRUMENT_ONLY.",
        "model_provenance_rule": "Model identity is OBSERVED only when independently supported by preserved execution evidence; otherwise UNKNOWN/DERIVED_UNVERIFIED.",
        "timestamp_provenance_rule": "The legacy timestamp is retained as DERIVED_UNVERIFIED metadata and is not treated as machine-observed timing.",
    }
    write_json(OUT / "ai_rater_runs_manifest_v2.json", manifest)

    pairwise = {
        "schema_version": "ai_rater_pairwise_agreement_v2",
        "run_ids": run_ids,
        "pair_count": len(pair_records),
        "case_count": len(cases),
        "taxonomy": TAXONOMY,
        "binary_projection": {
            "NEGATIVE": ["BENIGN"],
            "POSITIVE": sorted(POSITIVE),
            "UNCERTAIN": "excluded when present in either member of a pair",
        },
        "pairs": pair_records,
    }
    write_json(OUT / "ai_rater_pairwise_agreement_v2.json", pairwise)

    multirater = {
        "schema_version": "ai_rater_multirater_reliability_v2",
        "run_ids": run_ids,
        "n_raters": 6,
        "case_count": len(cases),
        "multiclass": {
            "N": len(cases),
            "n_raters": 6,
            **multiclass_fleiss,
            "statistic": "Fleiss kappa with all six fixed ratings per case",
        },
        "binary": {
            "eligible_N": len(binary_cases),
            "excluded_cases_because_of_uncertain": len(cases) - len(binary_cases),
            "n_raters": 6,
            **binary_fleiss,
            "statistic": "Fleiss kappa, Option A: retain only cases with six non-UNCERTAIN ratings",
            "excluded_rule": "A case is excluded if any of the six labels is UNCERTAIN; no variable-rater rows are used.",
        },
    }
    write_json(OUT / "ai_rater_multirater_reliability_v2.json", multirater)

    with (OUT / "ai_rater_disagreement_map_v2.jsonl").open("w", encoding="utf-8") as handle:
        for record in consensus:
            handle.write(json.dumps(record, sort_keys=False) + "\n")

    repeated_pairs = [("agent_run_01", "agent_run_04"), ("agent_run_02", "agent_run_05"), ("agent_run_03", "agent_run_06")]
    same_model_pairs = [("agent_run_01", "agent_run_02"), ("agent_run_01", "agent_run_03"), ("agent_run_02", "agent_run_03")]
    stability_pairs: list[dict[str, Any]] = []
    for group_name, pairs in [("repeated_packet_pair", repeated_pairs), ("same_observed_model_pair", same_model_pairs)]:
        for left_id, right_id in pairs:
            metrics = pair_metrics(left_id, right_id, labels, cases)
            left_spec = next(spec for spec in SOURCE_RUNS if spec["run_id"] == left_id)
            right_spec = next(spec for spec in SOURCE_RUNS if spec["run_id"] == right_id)
            status = "OBSERVED" if left_spec["model_provenance"] == right_spec["model_provenance"] == "OBSERVED" else "DERIVED_UNVERIFIED"
            stability_pairs.append(
                {
                    "comparison_group": group_name,
                    "pair": [left_id, right_id],
                    "rater_packet_ids": [left_spec["packet"], right_spec["packet"]],
                    "comparison_label": "RUN-TO-RUN ANNOTATION STABILITY",
                    "model_identity_status": status,
                    "model_identity_note": (
                        "Both runs are tied to the observed gpt-5.6-luna execution manifest."
                        if status == "OBSERVED"
                        else "Model identity for at least one run is derived/unverified; the result is reported as run-to-run stability, not model-specific stability."
                    ),
                    "exact_agreement": metrics["exact_agreement"],
                    "exact_rate": metrics["exact_rate"],
                    "binary_n": metrics["binary_n"],
                    "excluded_uncertain": metrics["excluded_uncertain"],
                    "binary_agreement": metrics["binary_agreement"],
                    "binary_rate": metrics["binary_rate"],
                    "multiclass_cohens_kappa": metrics["cohens_kappa"],
                    "binary_cohens_kappa": metrics["binary_cohens_kappa"],
                    "changed_cases": metrics["disagreement_count"],
                    "most_common_label_transitions": metrics["label_transitions"][:10],
                }
            )
    stability = {
        "schema_version": "ai_rater_stability_summary_v2",
        "run_ids": run_ids,
        "case_count": len(cases),
        "language_rule": "Use RUN-TO-RUN ANNOTATION STABILITY unless model identity is independently supported; do not claim cross-model stability for an unverified run.",
        "repeated_packet_pairs": [pair for pair in stability_pairs if pair["comparison_group"] == "repeated_packet_pair"],
        "same_observed_model_pairs": [pair for pair in stability_pairs if pair["comparison_group"] == "same_observed_model_pair"],
    }
    write_json(OUT / "ai_rater_stability_summary_v2.json", stability)

    exact_order = ["STRONG_CONSENSUS", "BINARY_CONSENSUS", "STRICT_MAJORITY", "HIGH_AMBIGUITY"]
    binary_order = ["BINARY_STRONG_CONSENSUS", "BINARY_CONSENSUS", "BINARY_STRICT_MAJORITY", "HIGH_AMBIGUITY"]
    pair_rows = []
    for pair in pair_records:
        pair_rows.append([
            " × ".join(pair["pair"]),
            pair["exact_agreement"],
            f"{pair['exact_rate']:.4f}",
            pair["cohens_kappa"],
            pair["binary_n"],
            pair["excluded_uncertain"],
            pair["binary_agreement"],
            f"{pair['binary_rate']:.4f}",
            pair["binary_cohens_kappa"],
        ])
    repeated_rows = []
    for pair in stability["repeated_packet_pairs"]:
        repeated_rows.append([
            " × ".join(pair["pair"]),
            pair["exact_agreement"],
            f"{pair['exact_rate']:.4f}",
            pair["binary_n"],
            pair["excluded_uncertain"],
            pair["binary_agreement"],
            f"{pair['binary_rate']:.4f}",
            pair["multiclass_cohens_kappa"],
            pair["binary_cohens_kappa"],
            pair["changed_cases"],
            pair["model_identity_status"],
        ])
    narrative = f"""# AI Annotator Agreement Audit v2

## 1. Scope

This is a provenance correction and conservative reliability recomputation for six labeled AI-agent annotation runs over the same 120 cases. The three blank annotation packets are instrument-only files and do not enter any reliability statistic. This audit does not inspect Chrollo or Laya predictions, confidence/probability scores, model-disagreement flags, ground truth, or confirmatory evaluation results.

The six labels are AI-agent annotations. They are not human ground truth, and agreement does not establish correctness.

## 2. Provenance correction

The original manifest had nine entries: three blank packets and six labeled files. The legacy IDs `human_r1`, `human_r2`, and `human_r3` were misleading labels for labeled AI-agent files. The corrected manifest assigns immutable neutral IDs `agent_run_01` through `agent_run_06` and preserves each legacy ID only in a `previous_run_id` field.

The three `codex_*` outputs are tied by preserved execution evidence to model `gpt-5.6-luna`; this is recorded as `model_identity_provenance: OBSERVED`. The three former `human_*` source files have no independently preserved model/session evidence, so their model identity is `UNKNOWN` with `DERIVED_UNVERIFIED` provenance. The legacy timestamp is retained only as `DERIVED_UNVERIFIED` metadata; it is not claimed to be a machine-observed run time.

## 3. Why blank packets are not raters

`packet_r1`, `packet_r2`, and `packet_r3` contain 120 blank labels each. They define the annotation instrument but contribute no observations. Counting them as raters would introduce missing/blank values into agreement and would misstate the number of independent labeled runs. The v2 audit therefore classifies exactly three records as `INSTRUMENT_ONLY` and excludes them from all statistics.

## 4. Six labeled AI-agent runs

{markdown_table([[r["run_id"], r["previous_run_id"], r["rater_packet_id"], r["model_identity"], r["model_identity_provenance"], r["case_count"]] for r in source_records], ["run_id", "previous_run_id", "packet", "model_identity", "model provenance", "cases"])}

All six runs contain exactly 120 case IDs, the case-ID sets match exactly, all labels are nonblank, and all labels belong to the nine-label taxonomy.

## 5. Pairwise multiclass agreement

All 15 combinations of the six labeled runs were recomputed with nominal Cohen's kappa over the nine-label taxonomy. `n` is always 120.

{markdown_table(pair_rows, ["pair", "exact", "rate", "κ", "binary n", "excluded U", "binary agree", "binary rate", "binary κ"])}

Exact agreement ranges from {min(p["exact_rate"] for p in pair_records):.4f} to {max(p["exact_rate"] for p in pair_records):.4f}; mean is {sum(p["exact_rate"] for p in pair_records)/len(pair_records):.4f} and median is {sorted(p["exact_rate"] for p in pair_records)[len(pair_records)//2]:.4f}. The best pair is `{' × '.join(max(pair_records, key=lambda p: p['exact_rate'])['pair'])}`; the worst is `{' × '.join(min(pair_records, key=lambda p: p['exact_rate'])['pair'])}`.

## 6. Pairwise binary agreement

The binary projection maps `BENIGN` to `NEGATIVE`, the seven attack-related labels to `POSITIVE`, and excludes `UNCERTAIN` whenever it occurs in either member of a pair. Thus `binary_n + excluded_uncertain = 120` for every pair; the binary denominator is not silently fixed at 120.

Binary agreement ranges from {min(p["binary_rate"] for p in pair_records):.4f} to {max(p["binary_rate"] for p in pair_records):.4f}; mean is {sum(p["binary_rate"] for p in pair_records)/len(pair_records):.4f} and median is {sorted(p["binary_rate"] for p in pair_records)[len(pair_records)//2]:.4f}. The best pair is `{' × '.join(max(pair_records, key=lambda p: p['binary_rate'])['pair'])}`; the worst is `{' × '.join(min(pair_records, key=lambda p: p['binary_rate'])['pair'])}`.

## 7. Multi-rater reliability

Multiclass reliability uses Fleiss' kappa with all six fixed ratings per case: N = 120, observed agreement = {multiclass_fleiss['observed_agreement']:.6f}, expected agreement = {multiclass_fleiss['expected_agreement']:.6f}, Fleiss κ = {multiclass_fleiss['fleiss_kappa']:.6f}.

Binary reliability uses Option A: only cases where all six ratings are non-`UNCERTAIN` are retained. The eligible N is {len(binary_cases)}; {len(cases) - len(binary_cases)} cases are excluded because at least one rating is `UNCERTAIN`. Observed agreement = {binary_fleiss['observed_agreement']:.6f}, expected agreement = {binary_fleiss['expected_agreement']:.6f}, Fleiss κ = {binary_fleiss['fleiss_kappa']:.6f}. This preserves the fixed six-rater assumption.

## 8. Strict consensus structure

The v2 exact-label view assigns each case to exactly one category in precedence order: strong six-of-six consensus, conservative binary consensus, strict exact-label majority, or high ambiguity. Binary consensus requires at least four non-`UNCERTAIN` ratings and unanimity on the binary side; therefore a pattern such as 2 `BENIGN` + 4 `UNCERTAIN` is not binary consensus.

### View A: exact-label strict consensus

{markdown_table([[category, exact_counts[category]] for category in exact_order], ["category", "count"])}

The previous reported structure was `STRONG_CONSENSUS = 60`, `BINARY_CONSENSUS = 8`, `MAJORITY_ONLY = 52`, `HIGH_AMBIGUITY = 0`. The corrected structure is `60 / 6 / 41 / 13`. The former permissive majority bucket included cases without an exact label receiving at least four of six votes.

### View B: conservative binary-support consensus

This mutually exclusive binary view uses the same six-of-six strong bucket, requires at least four non-`UNCERTAIN` ratings for binary consensus, then counts remaining cases with a binary side receiving at least four of six ratings as binary strict majority.

{markdown_table([[category, binary_view_counts[category]] for category in binary_order], ["category", "count"])}

## 9. Ambiguous cases

There are {exact_counts['HIGH_AMBIGUITY']} `HIGH_AMBIGUITY` cases. They are preserved in `ai_rater_disagreement_map_v2.jsonl`, not removed or converted into truth labels. The audit records the following non-exclusive diagnostic reasons: {', '.join(f'`{key}` = {value}' for key, value in sorted(ambiguity_reasons.items()))}. The case-level map retains all six labels, uncertainty counts, binary support counts, majority flags, and the final ambiguity category.

## 10. Run-to-run stability

Repeated-packet comparisons are reported as `RUN-TO-RUN ANNOTATION STABILITY`. The former `human_*` naming is not used as evidence of human annotation, and no unverified comparison is called cross-model stability.

{markdown_table(repeated_rows, ["pair", "exact", "rate", "binary n", "excluded U", "binary agree", "binary rate", "multiclass κ", "binary κ", "changed", "model status"])}

For the three repeated-packet pairs, model identity is `DERIVED_UNVERIFIED` because at least one member lacks independently supported model identity. The three `agent_run_01`/`02`/`03` within-Codex comparisons are separately retained as same-observed-model run-to-run comparisons; they do not establish correctness or generalize beyond these runs.

## 11. What these results DO support

- A reproducible description of agreement among six labeled AI-agent annotation runs on 120 shared cases.
- Conservative multiclass and fixed-rater binary reliability estimates with explicit `UNCERTAIN` handling.
- Identification and preservation of exact consensus, binary-supported consensus, strict exact majorities, and ambiguous cases.
- Descriptive run-to-run stability for repeated packet assignments.

## 12. What these results DO NOT support

- They do not establish human inter-rater reliability or create human ground truth.
- They do not establish that any annotation is correct.
- They do not justify majority-voting AI annotations into final truth.
- They do not support a model-specific or cross-model stability claim where model identity is unverified.
- They do not provide a Chrollo-vs-Laya prediction comparison or a confirmatory scientific result.

## 13. Freeze boundary before confirmatory analysis

This v2 reliability audit is frozen before any confirmatory labels or predictions are joined. No Chrollo/Laya prediction was inspected, no ground truth was created, and no confirmatory Chrollo-vs-Laya analysis was run. Ambiguous cases remain represented in the audit artifacts. The confirmatory scientific verdict remains **INCONCLUSIVE**.

The machine-generated freeze manifest is `results/laya_research/ai_rater_reliability_freeze_v2.json`. Do not modify it after confirmatory labels or predictions are joined.
"""
    narrative_path = DOCS / "AI_ANNOTATOR_AGREEMENT_AUDIT_V2.md"
    narrative_path.write_text(narrative, encoding="utf-8")

    freeze_files = [
        "results/laya_research/ai_rater_runs_manifest_v2.json",
        "results/laya_research/ai_rater_pairwise_agreement_v2.json",
        "results/laya_research/ai_rater_multirater_reliability_v2.json",
        "results/laya_research/ai_rater_disagreement_map_v2.jsonl",
        "results/laya_research/ai_rater_stability_summary_v2.json",
        "docs/laya_integration/AI_ANNOTATOR_AGREEMENT_AUDIT_V2.md",
    ]
    freeze = {
        "schema_version": "ai_rater_reliability_freeze_v2",
        "freeze_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "artifact_sha256": {path: sha256(ROOT / path) for path in freeze_files},
        "source_annotation_files": [
            {"path": spec["path"], "sha256": sha256(ROOT / spec["path"]), "run_id": spec["run_id"]}
            for spec in SOURCE_RUNS
        ],
        "instrument_only_packet_files": [
            {"path": spec["path"], "sha256": sha256(ROOT / spec["path"]), "run_id": spec["run_id"]}
            for spec in PACKETS
        ],
        "number_of_labeled_runs": 6,
        "number_of_instrument_only_packets": 3,
        "case_count": len(cases),
        "run_ids": run_ids,
        "statement": "No Chrollo/Laya predictions or ground truth were accessed.",
        "confirmatory_analysis_run": False,
        "ground_truth_created": False,
        "freeze_boundary": "Do not modify this freeze after confirmatory labels/predictions are joined.",
    }
    write_json(OUT / "ai_rater_reliability_freeze_v2.json", freeze)

    emitted_manifest = json.loads((OUT / "ai_rater_runs_manifest_v2.json").read_text())
    emitted_pairwise = json.loads((OUT / "ai_rater_pairwise_agreement_v2.json").read_text())
    emitted_multi = json.loads((OUT / "ai_rater_multirater_reliability_v2.json").read_text())
    emitted_stability = json.loads((OUT / "ai_rater_stability_summary_v2.json").read_text())
    emitted_freeze = json.loads((OUT / "ai_rater_reliability_freeze_v2.json").read_text())
    map_records = [json.loads(line) for line in (OUT / "ai_rater_disagreement_map_v2.jsonl").read_text().splitlines()]
    assert sum(record["has_labels"] for record in emitted_manifest["run_records"]) == 6
    assert sum(record["instrument_only"] for record in emitted_manifest["run_records"]) == 3
    assert len(emitted_pairwise["pairs"]) == 15
    assert len(map_records) == 120
    assert emitted_multi["binary"]["eligible_N"] == 104
    assert sum(exact_counts.values()) == 120
    assert sum(binary_view_counts.values()) == 120
    assert all(record["model_identity"] != "human" for record in emitted_manifest["run_records"] if record["has_labels"])
    assert all(sha256(ROOT / path) == digest for path, digest in emitted_freeze["artifact_sha256"].items())
    print(json.dumps({
        "labeled_runs": 6,
        "instrument_only_packets": 3,
        "pair_count": len(pair_records),
        "multiclass_fleiss_kappa": multiclass_fleiss["fleiss_kappa"],
        "binary_fleiss_kappa": binary_fleiss["fleiss_kappa"],
        "binary_eligible_N": len(binary_cases),
        "strict_consensus": dict(exact_counts),
        "binary_view": dict(binary_view_counts),
        "freeze_hashes_verified": True,
    }, indent=2))


if __name__ == "__main__":
    main()
