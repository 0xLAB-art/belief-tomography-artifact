#!/usr/bin/env python3
"""Cluster-bootstrap confidence intervals for the induced-draft battery.

Why this exists
---------------
``results/verifier_redteam_cross_family.json`` reports precision/recall with
Wilson score intervals computed over *drafts*. Several drafts are generated per
case (one per repeat), so drafts inside a case are not independent and a
binomial interval over them is optimistically narrow. This script recomputes
the same quantities with a cluster bootstrap that resamples **cases**, which is
the unit the battery actually draws independently.

Inputs are the persisted per-case artifacts; nothing is re-scored and no
provider call is made. The point estimates are asserted against the published
``overall`` block of each artifact, so a drift in either the artifacts or this
aggregation fails loudly instead of silently widening an interval.

Usage::

    python scripts/verifier_ci_cluster_bootstrap.py            # write artifact
    python scripts/verifier_ci_cluster_bootstrap.py --check    # verify only
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"

BOOTSTRAP_ITERS = 10_000
SEED = 20261008

FAMILIES: dict[str, str] = {
    "space-bunny-free": "verifier_redteam_live_space-bunny_rescored_after_fix.json",
    "deepseek-v4-flash-free": "verifier_redteam_live_deepseek-v4-flash-free_rescored_after_fix.json",
    "llama-3.3-70b": "verifier_redteam_live_llama33_complete.json",
}

# Published counts, used as an assertion that this aggregation agrees with the
# artifacts' own scoring path before any interval is reported.
PUBLISHED: dict[str, dict[str, int]] = {
    "space-bunny-free": {"tp": 185, "fn": 8, "fp": 0, "tn": 68},
    "deepseek-v4-flash-free": {"tp": 170, "fn": 3, "fp": 0, "tn": 63},
    "llama-3.3-70b": {"tp": 185, "fn": 21, "fp": 17, "tn": 58},
}


def case_counts(artifact: dict[str, Any]) -> dict[str, tuple[int, int, int, int]]:
    """Per-case (tp, fn, fp, tn) over the case's *valid* drafts.

    Labels follow the operational definitions the artifacts use:

    * ``should_reject`` draft -> TP when the gate caught it (rejected and named
      the targeted check), FN otherwise.
    * ``should_pass`` draft -> FP when the gate **rejected** it at all, whether
      or not the rejection named a targeted check. A benign draft diverted to
      the fallback is operationally a false positive even when it was rejected
      for an incidental reason, so ``rejected`` rather than ``caught`` is the
      correct numerator here; ``caught`` alone would silently reclassify
      wrong-reason rejections as true negatives and understate the precision
      loss.
    """
    out: dict[str, tuple[int, int, int, int]] = {}
    for key, entry in sorted(artifact.get("per_case", {}).items()):
        tp = fn = fp = tn = 0
        for variant in entry.get("variants", []):
            if not variant.get("valid", False):
                continue
            if entry.get("label") == "should_reject":
                caught = bool(variant.get("caught"))
                tp += int(caught)
                fn += int(not caught)
            else:
                rejected = bool(variant.get("rejected"))
                fp += int(rejected)
                tn += int(not rejected)
        out[key] = (tp, fn, fp, tn)
    return out


def rates(counts: tuple[int, int, int, int]) -> tuple[float | None, float | None]:
    tp, fn, fp, _tn = counts
    precision = tp / (tp + fp) if (tp + fp) else None
    recall = tp / (tp + fn) if (tp + fn) else None
    return precision, recall


def cluster_bootstrap(
    per_case: dict[str, tuple[int, int, int, int]],
    iters: int = BOOTSTRAP_ITERS,
    seed: int = SEED,
) -> dict[str, Any]:
    """Percentile CI resampling whole cases with replacement."""
    keys = sorted(per_case)
    if not keys:
        return {"n_cases": 0}
    rng = random.Random(seed)
    precisions: list[float] = []
    recalls: list[float] = []
    for _ in range(iters):
        tp = fn = fp = tn = 0
        for _ in range(len(keys)):
            c_tp, c_fn, c_fp, c_tn = per_case[keys[rng.randrange(len(keys))]]
            tp += c_tp
            fn += c_fn
            fp += c_fp
            tn += c_tn
        precision, recall = rates((tp, fn, fp, tn))
        if precision is not None:
            precisions.append(precision)
        if recall is not None:
            recalls.append(recall)
    precisions.sort()
    recalls.sort()

    def pct(values: list[float], q: float) -> float:
        if not values:
            return float("nan")
        return values[min(int(q * len(values)), len(values) - 1)]

    return {
        "n_cases": len(keys),
        "precision_ci95": [round(pct(precisions, 0.025), 4), round(pct(precisions, 0.975), 4)],
        "recall_ci95": [round(pct(recalls, 0.025), 4), round(pct(recalls, 0.975), 4)],
    }


def wilson(k: int, n: int) -> list[float]:
    """Wilson interval, for the width comparison the paper now reports."""
    if n == 0:
        return [float("nan"), float("nan")]
    z = 1.959963984540054
    p = k / n
    denom = n + z * z
    center = (k + z * z / 2) / denom
    half = (z / denom) * ((k * (n - k) / n + z * z / 4) ** 0.5)
    return [round(max(0.0, center - half), 4), round(min(1.0, center + half), 4)]


def build(check_only: bool) -> int:
    report: dict[str, Any] = {
        "what": "Cluster-bootstrap CIs over cases for the induced-draft battery",
        "method": {
            "resampling_unit": "case (cluster)",
            "iterations": BOOTSTRAP_ITERS,
            "seed": SEED,
            "estimator": "percentile",
            "supersedes": "Wilson-over-drafts intervals in verifier_redteam_cross_family.json",
            "rationale": "repeats within a case share a scenario, so drafts are not independent",
        },
        "families": {},
    }
    mismatches: list[str] = []
    pooled_cases: dict[str, list[tuple[int, int, int, int]]] = {}

    for family, filename in FAMILIES.items():
        path = RESULTS / filename
        if not path.exists():
            report["families"][family] = {"error": f"missing {filename}"}
            mismatches.append(f"{family}: artifact missing")
            continue
        artifact = json.loads(path.read_text())
        per_case = case_counts(artifact)
        tp = sum(c[0] for c in per_case.values())
        fn = sum(c[1] for c in per_case.values())
        fp = sum(c[2] for c in per_case.values())
        tn = sum(c[3] for c in per_case.values())
        published = PUBLISHED[family]
        if (tp, fn, fp, tn) != (published["tp"], published["fn"], published["fp"], published["tn"]):
            mismatches.append(
                f"{family}: aggregated {(tp, fn, fp, tn)} != published "
                f"{(published['tp'], published['fn'], published['fp'], published['tn'])}"
            )
        precision, recall = rates((tp, fn, fp, tn))
        report["families"][family] = {
            "artifact": f"results/{filename}",
            "drafts": tp + fn + fp + tn,
            "tp": tp, "fn": fn, "fp": fp, "tn": tn,
            "precision": None if precision is None else round(precision, 4),
            "recall": None if recall is None else round(recall, 4),
            "wilson_precision_draft_level": wilson(tp, tp + fp),
            "wilson_recall_draft_level": wilson(tp, tp + fn),
            "cluster_bootstrap": cluster_bootstrap(per_case, seed=SEED + len(pooled_cases)),
        }
        pooled_cases[family] = list(per_case.values())

    # Pooled: stratified by family, cases resampled within each family so the
    # two providers keep their observed case counts.
    pooled: dict[str, tuple[int, int, int, int]] = {}
    for family, counts in pooled_cases.items():
        for i, c in enumerate(counts):
            pooled[f"{family}#{i:03d}"] = c
    tp = sum(c[0] for c in pooled.values())
    fn = sum(c[1] for c in pooled.values())
    fp = sum(c[2] for c in pooled.values())
    tn = sum(c[3] for c in pooled.values())
    precision, recall = rates((tp, fn, fp, tn))
    report["pooled"] = {
        "n_cases": len(pooled),
        "drafts": tp + fn + fp + tn,
        "tp": tp, "fn": fn, "fp": fp, "tn": tn,
        "precision": None if precision is None else round(precision, 4),
        "recall": None if recall is None else round(recall, 4),
        "wilson_precision_draft_level": wilson(tp, tp + fp),
        "wilson_recall_draft_level": wilson(tp, tp + fn),
        "cluster_bootstrap": cluster_bootstrap(pooled, seed=SEED + 99),
        "stratified_by": "author family",
    }
    report["aggregation_matches_published"] = not mismatches
    report["mismatches"] = mismatches

    if not check_only:
        out = RESULTS / "verifier_ci_cluster_bootstrap.json"
        out.write_text(json.dumps(report, indent=2) + "\n")

    for family, block in report["families"].items():
        if "error" in block:
            print(f"{family}: ERROR {block['error']}")
            continue
        cb = block["cluster_bootstrap"]
        print(
            f"{family:24s} drafts={block['drafts']:4d} P={block['precision']:.4f} "
            f"cluster95={cb['precision_ci95']} (draft-level Wilson {block['wilson_precision_draft_level']})  "
            f"R={block['recall']:.4f} cluster95={cb['recall_ci95']} "
            f"(draft-level Wilson {block['wilson_recall_draft_level']})"
        )
    p = report["pooled"]
    print(
        f"{'POOLED (stratified)':24s} drafts={p['drafts']:4d} P={p['precision']:.4f} "
        f"cluster95={p['cluster_bootstrap']['precision_ci95']}  "
        f"R={p['recall']:.4f} cluster95={p['cluster_bootstrap']['recall_ci95']}"
    )
    print(f"aggregation matches published counts: {report['aggregation_matches_published']}")
    for m in mismatches:
        print(f"  MISMATCH {m}")
    return 0 if report["aggregation_matches_published"] else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="verify aggregation without writing the artifact")
    args = ap.parse_args()
    return build(args.check)


if __name__ == "__main__":
    raise SystemExit(main())