#!/usr/bin/env python3
"""Prediction-blind confirmatory subset selection for the Laya independent eval.

Selection rules:
- Use the candidate quality audit only.
- Exclude EXCLUDE-band cases.
- Prefer annotatable cases: INTERPRETABLE and PARTIAL interpretability are
  eligible for the primary allocation; NOT_INTERPRETABLE cases are only used
  as fallback filler if the annotatable pool is too small to reach min_n.
- Deduplicate by cluster: one representative per cluster unless we need more
  cases to reach min_n.
- Stratified by observable evidence characteristics only:
    - source_family
    - context_depth
    - quality_band
- Attempt a target near 120, allowed range 100-150.
- Never consult Chrollo / Laya / confidence / disagreement / model fields.

Outputs:
    results/laya_research/confirmatory_subset_manifest.json
    results/laya_research/confirmatory_case_ids.txt
"""

from __future__ import annotations

import hashlib
import json
import random
import time
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
POOL = REPO / "results/laya_research/independent_label_candidates_v2.json"
AUDIT = REPO / "results/laya_research/candidate_quality_audit.jsonl"
CLUSTERS = REPO / "results/laya_research/deduplication_clusters.json"


def load() -> tuple[dict, list[dict], list[dict], list[dict]]:
    pool = json.loads(POOL.read_text())
    cands = pool["candidates"]
    audit = [json.loads(line) for line in AUDIT.read_text().splitlines() if line.strip()]
    clusters = json.loads(CLUSTERS.read_text())
    return pool, cands, audit, clusters


def stratified_pick(
    pool_rows: list[dict],
    target: int,
    rng: random.Random,
    strata_key_fn,
) -> tuple[list[dict], dict[tuple, list[str]]]:
    """Proportional stratified pick of `target` rows from `pool_rows`."""
    strata: dict[tuple, list[dict]] = {}
    for row in pool_rows:
        strata.setdefault(strata_key_fn(row), []).append(row)

    keys_sorted = sorted(strata.keys(), key=lambda k: len(strata[k]), reverse=True)
    total = len(pool_rows)

    alloc: dict[tuple, int] = {}
    allocated_total = 0
    for k in keys_sorted:
        size = len(strata[k])
        raw = max(1, round(target * size / total)) if total else 1
        alloc[k] = min(raw, size)
        allocated_total += alloc[k]

    # adjust to target
    diff = allocated_total - target
    if diff > 0:
        for k in keys_sorted:
            if diff <= 0:
                break
            can = max(0, alloc[k] - 1)
            trim = min(can, diff)
            alloc[k] -= trim
            diff -= trim
    elif diff < 0:
        for k in keys_sorted:
            if diff <= 0:
                break
            can = len(strata[k]) - alloc[k]
            add_n = min(can, diff)
            alloc[k] += add_n
            diff -= add_n

    picked: list[dict] = []
    picked_ids: dict[tuple, list[str]] = {}
    for k in keys_sorted:
        pool_k = list(strata[k])
        rng.shuffle(pool_k)
        chosen = pool_k[: alloc[k]]
        picked.extend(chosen)
        picked_ids[k] = [r["case_id"] for r in chosen]

    return picked, picked_ids


def build_selection(
    audit: list[dict],
    clusters: list[dict],
    target_n: int = 120,
    min_n: int = 100,
    max_n: int = 150,
    seed: int = 20261012,
) -> dict:
    rng = random.Random(seed)

    rep_by_cluster: dict[str, str] = {}
    case_to_cluster: dict[str, str] = {}
    for c in clusters:
        rep_by_cluster[c["cluster_id"]] = c["representative_id"]
        for m in c["member_ids"]:
            case_to_cluster[m] = c["cluster_id"]

    # Eligible = not EXCLUDE. Cluster representatives only for primary pass.
    not_excluded = [r for r in audit if r["quality_band"] != "EXCLUDE"]
    primary_eligible = [
        r for r in not_excluded
        if r["case_id"] == rep_by_cluster.get(case_to_cluster.get(r["case_id"], ""), r["case_id"])
    ]

    # Split annotatable vs not-interpretable
    annotatable = [r for r in primary_eligible if r["interpretability"] in ("INTERPRETABLE", "PARTIAL")]
    non_interp = [r for r in primary_eligible if r["interpretability"] == "NOT_INTERPRETABLE"]

    def strata_key(row: dict) -> tuple:
        return (row["source_family"], row["context_depth"], row["quality_band"])

    # Primary allocation over annotatable cases only.
    annot_target = min(target_n, len(annotatable))
    selected, strata_allocation = stratified_pick(annotatable, annot_target, rng, strata_key)

    # Fallback: if annotatable pool cannot reach min_n, fill from
    # NOT_INTERPRETABLE representatives (still prediction-blind, still
    # deduplicated) and report the fallback explicitly.
    fallback_used = False
    if len(selected) < min_n:
        fallback_used = True
        already = {r["case_id"] for r in selected}
        fill_pool = [r for r in non_interp if r["case_id"] not in already]
        need = min_n - len(selected)
        fill_target = min(need, len(fill_pool))
        if fill_target > 0:
            filled, fill_alloc = stratified_pick(fill_pool, fill_target, rng, strata_key)
            selected.extend(filled)
            for k, ids in fill_alloc.items():
                strata_allocation.setdefault(k, []).extend(ids)

    # Enforce max_n by trimming weakest quality first
    if len(selected) > max_n:
        order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}
        selected = sorted(
            selected,
            key=lambda r: (order.get(r["quality_band"], 0), -r["evidence_length_chars"]),
        )[:max_n]
        # rebuild allocation view from trimmed selection
        picked_set = {r["case_id"] for r in selected}
        strata_allocation = {
            k: [cid for cid in ids if cid in picked_set] for k, ids in strata_allocation.items()
        }
        strata_allocation = {k: v for k, v in strata_allocation.items() if v}

    selected_ids = [r["case_id"] for r in selected]

    # Diagnostics: cluster collisions inside the selection (should be rare)
    cluster_counts = Counter(case_to_cluster[cid] for cid in selected_ids if cid in case_to_cluster)
    multi_selected_clusters = sorted([cid for cid, n in cluster_counts.items() if n > 1])

    quality_dist = dict(Counter(r["quality_band"] for r in selected))
    source_dist = dict(Counter(r["source_family"] for r in selected))
    depth_dist = dict(Counter(r["context_depth"] for r in selected))
    interp_dist = dict(Counter(r["interpretability"] for r in selected))

    return {
        "selection_version": "v2",
        "selection_timestamp": int(time.time()),
        "selection_seed": seed,
        "total_candidates_before": len(audit),
        "excluded_count": len([r for r in audit if r["quality_band"] == "EXCLUDE"]),
        "selected_count": len(selected_ids),
        "source_distribution": source_dist,
        "quality_distribution": quality_dist,
        "context_depth_distribution": depth_dist,
        "interpretability_distribution": interp_dist,
        "duplicate_cluster_count": len(clusters),
        "duplicate_cluster_policy": (
            "One representative per near-duplicate cluster in the primary "
            "allocation. NOT_INTERPRETABLE representatives were only used as "
            "fallback filler if annotatable cases could not reach min_n. No "
            "model predictions were consulted at any step."
        ),
        "selection_algorithm": (
            "Prediction-blind stratified selection across (source_family, "
            "context_depth, quality_band) strata over annotatable cases "
            "(INTERPRETABLE/PARTIAL), with proportional allocation, deterministic "
            "shuffle by selection_seed, and cluster-aware deduplication."
        ),
        "blind_selection": True,
        "model_predictions_consulted": False,
        "not_interpretable_fallback_used": fallback_used,
        "annotatable_pool_size": len(annotatable),
        "non_interpretable_pool_size": len(non_interp),
        "strata_used": [
            f"{src}/{depth}/{band}:{n}"
            for (src, depth, band), n in sorted(
                Counter(strata_key(r) for r in annotatable).items()
            )
        ],
        "strata_allocation": {
            f"{src}/{depth}/{band}": ids
            for (src, depth, band), ids in strata_allocation.items()
        },
        "selected_case_ids": sorted(selected_ids),
        "excluded_ids": sorted([r["case_id"] for r in audit if r["quality_band"] == "EXCLUDE"]),
        "soft_excluded_by_leakage": sorted([r["case_id"] for r in audit if r["leakage_terms"]]),
        "clusters_with_multiple_selected": multi_selected_clusters,
    }


def main() -> None:
    pool, cands, audit, clusters = load()

    out_dir = REPO / "results/laya_research"
    out_dir.mkdir(parents=True, exist_ok=True)

    selection = build_selection(audit, clusters)

    manifest_path = out_dir / "confirmatory_subset_manifest.json"
    ids_path = out_dir / "confirmatory_case_ids.txt"

    ids = selection["selected_case_ids"]
    ids_path.write_text("\n".join(ids) + "\n")
    ids_hash = hashlib.sha256(ids_path.read_bytes()).hexdigest()
    selection["confirmatory_case_ids_hash_sha256"] = ids_hash

    manifest_path.write_text(json.dumps(selection, indent=2) + "\n")

    print("Wrote", manifest_path)
    print("Wrote", ids_path)
    print("selected N:", len(ids))
    print("ids_hash:", ids_hash)
    print(json.dumps({
        k: selection[k] for k in (
            "selection_version", "selection_timestamp", "selection_seed",
            "total_candidates_before", "excluded_count", "selected_count",
            "source_distribution", "quality_distribution",
            "context_depth_distribution", "interpretability_distribution",
            "duplicate_cluster_count", "blind_selection",
            "model_predictions_consulted", "not_interpretable_fallback_used",
            "annotatable_pool_size", "non_interpretable_pool_size",
            "confirmatory_case_ids_hash_sha256",
        )
    }, indent=2))


if __name__ == "__main__":
    main()
