#!/usr/bin/env python3
"""Serve-path provenance v2 — direct instrumentation, no latency inference.

Reads one or more live-campaign artifacts whose per-row results carry the
explicit ``serve_path`` label stamped by the graph loop (GENERATED_VERIFIED /
GENERATED_RETRY / GENERATED_UNVERIFIED / FASTPATH_DETERMINISTIC /
FALLBACK_VERIFIED / HITL_SERVED) and emits the serve-path split per suite.

This supersedes the latency-threshold estimate in serve_provenance.json: the
v1 method inferred the serve path from a 4 s round-trip cutoff (with threshold
sensitivity 2 s–10 s, where the split moved 88.1% → 67.0%). The graph loop now
stamps ``serve_path`` on every deception_response at the node that produced the
served bytes, so the split is an exact count, not an estimate. The old latency
method is kept as a cross-check: where both are available for the same run,
v2 reports the disagreement rate — every disagreement is a row the threshold
misclassified.

Usage:
    python scripts/serve_provenance_v2.py \
        --runs results/live_benchmark_zodiac_20260922.json \
               results/live_benchmark_zodiac_20260922_run2.json \
        --out results/serve_provenance_v2.json

Rows without a ``serve_path`` key are counted as UNKNOWN and reported
separately — they are rows produced before instrumentation or by a code path
that bypasses the graph loop; they must never be silently folded into a
labeled bucket.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

# Suite-name normalization: campaign artifacts use both spellings.
_SUITE_ALIASES = {
    "CTI technique": "cti_technique",
    "CTI actor": "cti_actor",
    "Persona": "deception",
    "cti_technique": "cti_technique",
    "cti_actor": "cti_actor",
    "deception": "deception",
}

KNOWN_PATHS = (
    "GENERATED_VERIFIED",
    "GENERATED_RETRY",
    "GENERATED_UNVERIFIED",
    "FASTPATH_DETERMINISTIC",
    "FALLBACK_VERIFIED",
    "TEMPLATE_FALLBACK_VERIFIED",
    "HITL_SERVED",
    "UNKNOWN",
)


def _normalize_suite(raw: str) -> str:
    return _SUITE_ALIASES.get(raw, raw or "unknown")


def _iter_rows(artifact: dict):
    """Yield (suite, row) from either per_row layout or the *_results layout."""
    if isinstance(artifact.get("per_row"), list):
        for row in artifact["per_row"]:
            yield _normalize_suite(str(row.get("suite", ""))), row
        return
    results_layout = (
        ("technique_results", "cti_technique"),
        ("actor_results", "cti_actor"),
        ("persona_results", "deception"),
    )
    for key, suite in results_layout:
        for row in artifact.get(key, []) or []:
            yield suite, row


def analyze_run(path: Path) -> dict:
    artifact = json.loads(path.read_text())
    per_suite: dict[str, Counter] = {}
    disagreements = 0
    latency_available = 0
    for suite, row in _iter_rows(artifact):
        counter = per_suite.setdefault(suite, Counter())
        label = row.get("serve_path") or "UNKNOWN"
        counter[label] += 1
        # Latency cross-check (v1 rule: >4000 ms ⇒ LLM-in-the-loop).
        latency_ms = row.get("response_time_ms") or row.get("latency_ms")  # noqa: E501
        if isinstance(latency_ms, (int, float)) and label in KNOWN_PATHS and label != "UNKNOWN":
            latency_available += 1
            v1_guess = "llm_verified" if latency_ms > 4000 else "vetted_deterministic"
            v2_truth = "llm_verified" if label.startswith("GENERATED") else "vetted_deterministic"
            if v1_guess != v2_truth:
                disagreements += 1

    total = sum(sum(c.values()) for c in per_suite.values())
    suite_report = {}
    for suite, counter in sorted(per_suite.items()):
        n = sum(counter.values())
        suite_report[suite] = {
            "n": n,
            "counts": dict(counter),
            "pct": {k: round(100.0 * v / n, 1) for k, v in counter.items() if v},
        }
    known = total - sum(per_suite.get(s, Counter()).get("UNKNOWN", 0) for s in per_suite)
    return {
        "source": str(path),
        "total_rows": total,
        "labeled_rows": known,
        "per_suite": suite_report,
        "overall_pct": _overall(per_suite),
        "latency_cross_check": (
            {
                "rows_with_latency": latency_available,
                "v1_disagreements": disagreements,
                "note": "every disagreement is a row the 4 s threshold misclassified",
            }
            if latency_available
            else None
        ),
    }


def _overall(per_suite: dict[str, Counter]) -> dict:
    total: Counter = Counter()
    for counter in per_suite.values():
        total.update(counter)
    n = sum(total.values())
    if not n:
        return {}
    return {k: round(100.0 * v / n, 1) for k, v in sorted(total.items()) if v}


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve-path provenance from explicit serve_path labels")
    parser.add_argument("--runs", nargs="+", required=True, help="Campaign artifacts with per-row serve_path labels")
    parser.add_argument("--out", default="results/serve_provenance_v2.json")
    args = parser.parse_args()

    runs = [analyze_run(Path(p)) for p in args.runs]
    report = {
        "what": (
            "Serve-path provenance v2: exact per-row counts from direct instrumentation "
            "(serve_path stamped by the graph loop), replacing the latency-threshold estimate"
        ),
        "labels": {
            "GENERATED_VERIFIED": "LLM draft passed the deterministic verifier",
            "GENERATED_RETRY": "LLM draft passed verification after a regeneration",
            "GENERATED_UNVERIFIED": "draft served with no verifier in the loop (baseline arm)",
            "FASTPATH_DETERMINISTIC": "vetted deterministic fast-path content (designed rung)",
            "FALLBACK_VERIFIED": "fail-safe template served after verification failure",
            "HITL_SERVED": "content served after explicit operator decision",
        },
        "runs": runs,
        "reading": (
            "No headline percentage may be derived from latency inference anymore; "
            "UNKNOWN rows are reported as such and must be instrumented, "
            "not folded into a labeled bucket."
        ),
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))
    print(f"provenance report saved: {out}")
    for run in runs:
        print(f"  {run['source']}: {run['labeled_rows']}/{run['total_rows']} labeled — overall {run['overall_pct']}")


if __name__ == "__main__":
    main()
