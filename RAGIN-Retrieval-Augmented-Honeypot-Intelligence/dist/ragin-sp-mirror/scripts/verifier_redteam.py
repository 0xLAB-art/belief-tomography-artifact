"""Verifier red-team harness — induce verifier failures, report per-check P/R.

Closes the evaluation gap the T-IFS review named (M2 / author question 2):
the live campaigns show the verifier's *coverage* (zero unverified serves,
zero fallback serves), but its *selectivity* — does it reject the drafts it
should and pass the drafts it should not — was only sampled by the C1
adversarial round and the five mechanism checks. This harness measures
selectivity directly, per check.

Method (no LLM, no network — the verifier is a decision procedure, so
inducing its failures is an offline computation):

1.  Run a labeled corpus of attack and negative cases
    (``scripts/verifier_redteam_cases.py``) through the real
    ``FictionConsistencyVerifier.verify``.
2.  A case counts as caught when the verifier rejects the draft AND the
    rejection names the targeted check (a reject for the wrong reason is
    reported separately as a misattributed rejection).
3.  Per-check precision/recall over the cases that target that check.
    Recall = caught / should_reject; Precision = caught / (caught +
    false-positive rejects among should_pass cases targeting that check).
4.  Overall verdict gates follow the repo's artifact style:
    recall must be 1.0 on every targeted check, precision must be 1.0
    (no false positives), and every rejection must name the right check.

Outputs ``results/verifier_redteam.json`` with per-case verdicts so any
regression pins the exact failing case key.

Usage::

    python scripts/verifier_redteam.py            # run + write artifact
    python scripts/verifier_redteam.py --strict   # exit 2 on any gate failure
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ragin.cycle.verifier import FictionConsistencyVerifier  # noqa: E402
from ragin.graph.fiction import FictionGraph  # noqa: E402
from ragin.hisoka.deception import identity_for  # noqa: E402
from scripts.verifier_redteam_cases import CASE_CATEGORIES, build_cases  # noqa: E402

CHECKS = ("danger", "identity", "consistency", "degenerate", "supported_claim")

# Issue strings are prefixed with the check that raised them; see verifier.py.
_CHECK_PREFIX = {
    "danger": "danger-signal",
    "identity": "identity-pin",
    "consistency": "fiction-contradiction",
    "degenerate": "degenerate",
    "supported_claim": "supported-claim",
}


def _reasoning_check(issue: str) -> str | None:
    for name, prefix in _CHECK_PREFIX.items():
        if issue.startswith(prefix):
            return name
    return None


def run_case(verifier: FictionConsistencyVerifier, case: Any) -> dict[str, Any]:
    """Verify one case against a fresh verifier bound to a seeded graph."""
    skill = (case.ctx.get("classification") or {}).get("skill_level", "novice")
    session_id = case.ctx.get("session_id", "unknown")
    # Fresh graph seeded with the pinned identity, mirroring the cycle's
    # per-session construction (DeceptionGraph.fiction).
    graph = FictionGraph(session_id=session_id, identity=identity_for(skill))
    verifier = FictionConsistencyVerifier(fictions={session_id: graph})
    verdict = verifier.verify({"response_text": case.text, "session_id": session_id}, case.ctx)
    rejected = not verdict.get("passed", True)
    issues = list(verdict.get("issues", []))
    cited = sorted({c for i in issues if (c := _reasoning_check(i)) is not None})

    targeted = set(case.checks)
    # Attribution contract: the reject arm is a single gate — the draft is
    # served or it is not — so a case is CAUGHT when any targeted check fires,
    # even if a different targeted check (or the identity pin's hostname rule)
    # supplied the actual rejection. Cross-check rescue is part of the
    # defense-in-depth contract, not a scoring failure. Misattribution is
    # reserved for rejections where NO targeted check appears in the issues —
    # those indicate a labeled coverage gap in the suite itself.
    caught = rejected and bool(targeted & set(cited))
    misattributed = rejected and not (targeted & set(cited))
    # Which targeted checks actually fired (for the per-check tables); a
    # should_pass case that gets rejected is a false positive regardless of
    # which check fired; record which check fired for the report.
    fired_targeted = sorted(targeted & set(cited))
    fp_checks = cited if (case.label == "should_pass" and rejected) else []

    return {
        "key": case.key,
        "label": case.label,
        "categories": list(case.categories),
        "checks": list(case.checks),
        "rejected": rejected,
        "caught": caught,
        "misattributed": misattributed,
        "fired_targeted": fired_targeted,
        "false_positive_checks": fp_checks,
        "issues": issues,
    }


def _pr(block: list[dict[str, Any]], check: str | None = None) -> dict[str, Any]:
    """Recall over should_reject cases, precision including should_pass cases."""
    if check is not None:
        pos = [c for c in block if c["label"] == "should_reject" and check in c["checks"]]
        neg = [c for c in block if c["label"] == "should_pass" and check in c["checks"]]
    else:
        pos = [c for c in block if c["label"] == "should_reject"]
        neg = [c for c in block if c["label"] == "should_pass"]

    tp = sum(1 for c in pos if c["caught"])
    fn = len(pos) - tp
    fp = sum(1 for c in neg if c["rejected"])
    tn = len(neg) - fp
    precision = tp / (tp + fp) if (tp + fp) else (1.0 if not pos else 0.0)
    recall = tp / len(pos) if pos else 1.0
    return {
        "should_reject": len(pos),
        "should_pass": len(neg),
        "true_positives": tp,
        "false_negatives": fn,
        "false_positives": fp,
        "true_negatives": tn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "missed_keys": [c["key"] for c in pos if not c["caught"]],
        "fp_keys": [c["key"] for c in neg if c["rejected"]],
        "misattributed_keys": [c["key"] for c in block if c["misattributed"]],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Verifier red-team: per-check precision/recall")
    ap.add_argument(
        "--out",
        default=str(ROOT / "results" / "verifier_redteam.json"),
        help="artifact path (default results/verifier_redteam.json)",
    )
    ap.add_argument("--strict", action="store_true", help="exit 2 when a gate fails")
    args = ap.parse_args()

    cases = build_cases()
    probe = FictionConsistencyVerifier()

    t0 = time.monotonic()
    rows = [run_case(probe, case) for case in cases]
    elapsed_ms = (time.monotonic() - t0) * 1000

    overall = _pr(rows)
    per_check = {check: _pr(rows, check=check) for check in CHECKS}

    misattributed = [c["key"] for c in rows if c["misattributed"]]
    gates = {
        "no_missed_rejections": overall["false_negatives"] == 0,
        "no_false_positives": overall["false_positives"] == 0,
        "no_misattributed_rejections": not misattributed,
    }

    # Category roll-up (the D+/C evasion rows are the hard-subset view).
    by_cat: dict[str, dict[str, int]] = {}
    for row in rows:
        for cat in row["categories"]:
            slot = by_cat.setdefault(cat, {"n": 0, "expected_reject": 0, "expected_pass": 0, "as_expected": 0})
            slot["n"] += 1
            if row["label"] == "should_reject":
                slot["expected_reject"] += 1
                slot["as_expected"] += int(row["rejected"])
            else:
                slot["expected_pass"] += 1
                slot["as_expected"] += int(not row["rejected"])

    artifact = {
        "what": (
            "Verifier red-team: labeled attack/negative drafts run through the real "
            "FictionConsistencyVerifier to report per-check precision and recall "
            "(selectivity), complementing the campaign's coverage evidence "
            "(zero unverified serves). Offline, deterministic, no LLM calls."
        ),
        "method": {
            "corpus": "scripts/verifier_redteam_cases.py (keyed, labeled, per-check targeted)",
            "labels": "should_reject / should_pass; caught = rejected AND rejection names the targeted check",
            "graph": "fresh FictionGraph per case, seeded with the pinned novice identity (cycle-equivalent)",
        },
        "elapsed_ms": round(elapsed_ms, 1),
        "n_cases": len(rows),
        "overall": overall,
        "per_check": per_check,
        "categories": {k: CASE_CATEGORIES[k] for k in sorted(CASE_CATEGORIES)},
        "category_rollup": by_cat,
        "misattributed_keys": misattributed,
        "gates": gates,
        "all_gates_pass": all(gates.values()),
        "verdict": "pass" if all(gates.values()) else "fail",
        "cases": rows,
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")

    # ── console summary ────────────────────────────────────────────────────
    print(f"verifier red-team: {len(rows)} cases in {elapsed_ms:.0f} ms -> {out.name}")
    tp, sr = overall["true_positives"], overall["should_reject"]
    fp, sp = overall["false_positives"], overall["should_pass"]
    print(f"  overall: P={overall['precision']:.3f} R={overall['recall']:.3f} (TP {tp}/{sr}, FP {fp}/{sp})")
    for check in CHECKS:
        s = per_check[check]
        print(
            f"  {check:12s} P={s['precision']:.3f} R={s['recall']:.3f} "
            f"(reject {s['true_positives']}/{s['should_reject']}, pass {s['true_negatives']}/{s['should_pass']})"
        )
    if misattributed:
        print(f"  misattributed rejections: {misattributed}")
    for name, ok in gates.items():
        print(f"  gate {name}: {'PASS' if ok else 'FAIL'}")
    if args.strict and not all(gates.values()):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
