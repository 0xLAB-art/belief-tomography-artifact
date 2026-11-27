#!/usr/bin/env python3
"""Probe where the verifier's coverage ends: coherent-but-harmful drafts.

Answers the question the canonical red-team corpus cannot: when a draft is
fluent, contains no tell, is consistent with the session fiction, and is still
harmful, does the serving-time gate catch it?

Method (offline, deterministic, no provider): score the ``H`` corpus from
``scripts/verifier_harm_cases.py`` through the real
``FictionConsistencyVerifier.verify`` used on the serving path, and report
what fired. The suite is additive — ``results/verifier_redteam.json`` is not
read or rewritten, so the canonical 105-case result stays reproducible.

Two readings are reported and they differ, which is the point:

``detected_by_any_check``
    the operational question — was this draft stopped before it reached the
    wire, by any check?
``caught_by_targeted_check``
    the narrower question the canonical suite scores — was it stopped *and*
    did the finding name the check the case targets?

A case can be stopped by the identity or consistency layer and still be a
danger-gate blind spot, so the two are reported separately rather than
collapsed.

Usage::

    python scripts/verifier_harm_probe.py           # run + write artifact
    python scripts/verifier_harm_probe.py --check   # verify only, no write
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ragin.cycle.verifier import FictionConsistencyVerifier  # noqa: E402
from ragin.graph.fiction import FictionGraph  # noqa: E402
from ragin.hisoka.deception import identity_for  # noqa: E402
from scripts.verifier_harm_cases import HARM_CATEGORIES, build_cases  # noqa: E402

OUT = ROOT / "results" / "verifier_harm_probe.json"

_CHECK_PREFIX = {
    "danger": "danger-signal",
    "identity": "identity-pin",
    "consistency": "fiction-contradiction",
    "degenerate": "degenerate",
    "supported-claim": "supported-claim",
}


def wilson(k: int, n: int) -> list[float]:
    if n == 0:
        return [float("nan"), float("nan")]
    z = 1.959963984540054
    p = k / n
    denom = n + z * z
    center = (k + z * z / 2) / denom
    half = (z / denom) * ((k * (n - k) / n + z * z / 4) ** 0.5)
    return [round(max(0.0, center - half), 3), round(min(1.0, center + half), 3)]


def _reasoning_check(issue: str) -> str | None:
    for name, prefix in _CHECK_PREFIX.items():
        if issue.startswith(prefix):
            return name
    return None


def score(case: Any) -> dict[str, Any]:
    """Per-case construction and attribution contract mirror verifier_redteam.py."""
    skill = (case.ctx.get("classification") or {}).get("skill_level", "novice")
    session_id = case.ctx.get("session_id", "unknown")
    graph = FictionGraph(session_id=session_id, identity=identity_for(skill))
    verifier = FictionConsistencyVerifier(fictions={session_id: graph})
    verdict = verifier.verify({"response_text": case.text, "session_id": session_id}, case.ctx)
    issues = list(verdict.get("issues") or [])
    cited = sorted({c for c in (_reasoning_check(i) for i in issues) if c})
    rejected = not verdict.get("passed", True)
    targeted = set(case.checks)
    attributed = bool(targeted & set(cited))
    return {
        "key": case.key,
        "label": case.label,
        "categories": list(case.categories),
        "harm": case.harm,
        "checks_targeted": sorted(targeted),
        "rejected": rejected,
        "detected_by_any_check": rejected,
        "caught_by_targeted_check": attributed if targeted else None,
        "fired": cited,
        "issues": issues,
    }


def run(fail_closed: bool) -> dict[str, Any]:
    if fail_closed:
        os.environ["RAGIN_FAIL_CLOSED"] = "1"
    else:
        os.environ.pop("RAGIN_FAIL_CLOSED", None)

    cases = build_cases()
    rows = [score(case) for case in cases]

    def group(predicate) -> list[dict[str, Any]]:
        return [r for r in rows if predicate(r)]

    def tally(subset: list[dict[str, Any]]) -> dict[str, Any]:
        rejects = [r for r in subset if r["label"] == "should_reject"]
        passes = [r for r in subset if r["label"] == "should_pass"]
        det = sum(1 for r in rejects if r["detected_by_any_check"])
        fp = sum(1 for r in passes if r["detected_by_any_check"])
        return {
            "should_reject": len(rejects),
            "detected_by_any_check": det,
            "missed": len(rejects) - det,
            "should_pass": len(passes),
            "false_positives": fp,
            "missed_keys": [r["key"] for r in rejects if not r["detected_by_any_check"]],
            "false_positive_keys": [r["key"] for r in passes if r["detected_by_any_check"]],
            "recall_wilson95": wilson(det, len(rejects)),
        }

    def has(r: dict[str, Any], cat: str) -> bool:
        return cat in r["categories"]

    narrative = group(lambda r: has(r, "H") or has(r, "H-"))
    formats = group(lambda r: has(r, "F") or has(r, "F-"))
    context = group(lambda r: has(r, "X"))
    n_tally, f_tally, x_tally = tally(narrative), tally(formats), tally(context)
    all_tally = tally(rows)

    def rate(hits: int, total: int) -> float | None:
        return None if total == 0 else round(hits / total, 4)

    return {
        "artifact": "verifier_harm_probe",
        "question": "does the serving-time gate stop fluent, tell-free, on-fiction, harmful drafts?",
        "method": {
            "no_llm_calls": True,
            "verifier": "FictionConsistencyVerifier (the serving-path verifier)",
            "fail_closed_flag": bool(fail_closed),
            "categories": HARM_CATEGORIES,
            "group_note": (
                "H (authored narratives) and F (credential formats) are reported "
                "separately and never pooled: a proportion over seven hand-built "
                "cases describes the corpus, not the gate, so H is reported as counts "
                "and F is reported per format."
            ),
        },
        "groups": {
            "narratives_H": n_tally,
            "credential_formats_F": f_tally,
            "context_variants_X": x_tally,
            "pooled": all_tally,
        },
        "context_contrast": [
            {
                "bare_key": r["key"],
                "bare_served": r["detected_by_any_check"] is False,
                "embedded_key": "F-" + r["key"][2:].removesuffix("-bare"),
                "embedded_served": next(
                    (
                        q["detected_by_any_check"] is False
                        for q in rows
                        if q["key"] == "F-" + r["key"][2:].removesuffix("-bare")
                    ),
                    None,
                ),
            }
            for r in context
        ],
        "format_detail": [
            {
                "key": r["key"],
                "harm": r["harm"],
                "label": r["label"],
                "served": r["detected_by_any_check"] is False,
                "fired": r["fired"],
            }
            for r in formats
        ],
        "recall_any_check": rate(all_tally["detected_by_any_check"], all_tally["should_reject"]),
        "precision_any_check": rate(all_tally["should_pass"] - all_tally["false_positives"], all_tally["should_pass"]),
        "counts": {
            "should_reject": all_tally["should_reject"],
            "detected_by_any_check": all_tally["detected_by_any_check"],
            "missed": all_tally["missed"],
            "should_pass": all_tally["should_pass"],
            "false_positives": all_tally["false_positives"],
        },
        "missed_keys": all_tally["missed_keys"],
        "false_positive_keys": all_tally["false_positive_keys"],
        "rows": rows,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="run without writing the artifact")
    args = ap.parse_args()

    report = {"readings": {}}
    for flag in (False, True):
        key = "fail_closed_on" if flag else "fail_closed_default_off"
        report["readings"][key] = run(flag)

    primary = report["readings"]["fail_closed_default_off"]
    report["headline"] = {
        "reading": "fail_closed_default_off",
        "recall_any_check": primary["recall_any_check"],
        "missed_keys": primary["missed_keys"],
        "false_positive_keys": primary["false_positive_keys"],
        "interpretation": (
            "The gate is a tell-and-shape detector. On drafts that carry no tell and "
            "contradict nothing in the fiction, its coverage is partial; the missed keys "
            "name the gap."
        ),
    }
    if not args.check:
        OUT.write_text(json.dumps(report, indent=2) + "\n")

    for key, block in report["readings"].items():
        c = block["counts"]
        print(
            f"{key:24s} reject={c['should_reject']:2d} detected={c['detected_by_any_check']:2d} "
            f"missed={c['missed']:2d} | pass={c['should_pass']:2d} false_pos={c['false_positives']:2d} "
            f"| recall_any={block['recall_any_check']} precision_any={block['precision_any_check']}"
        )
        if block["missed_keys"]:
            print(f"    missed: {block['missed_keys']}")
        if block["false_positive_keys"]:
            print(f"    refused benign: {block['false_positive_keys']}")
    if not args.check:
        print(f"artifact: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())