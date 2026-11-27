#!/usr/bin/env python3
"""Artifact-consistency checker — pin the paper's red-team claims to artifacts.

The paper (§VI-C live-miss census, App. A artifact index) prints three
decimals; the artifacts store four-decimal raws (e.g. raw 0.9306 prints as
0.931, 0.9945 as 0.995).  The first manual cross-check produced seven false
failures from exactly this gap: exact-equality comparisons against printed
values, and a wrong ``cases`` field semantics (the offline artifact stores
``cases`` as a LIST of per-case dicts — count it with ``len``; the live
artifacts store it as an INT — compare it directly).  This checker encodes
the corrected comparison logic so paper<->artifact drift fails loudly and
permanently, offline, with no network and no imports from the live harness.

What is pinned (each claim cites the paper text it guards):

1.  ``results/verifier_redteam.json`` — offline stratum: 105 canonical cases
    (96 + the L4 third-family harvest lock), overall P=R=1.000, zero FPs, no
    misattributed rejections, and every per-check P/R
    (danger/identity/consistency/degenerate) at 1.000
    (§VI-C: "precision 1.000 and recall 1.000 overall and on every check").
2.  ``results/verifier_redteam_live_deepseek-v4-flash-free.json`` — 236
    drafts; precision 1.000 with zero FPs across 63 benign drafts, Wilson
    P CI 0.977--1.000; recall 0.931, CI 0.883--0.960; per-case verdict
    agreement 0.988 (79/80).
3.  ``results/verifier_redteam_live.json`` — space-bunny post-fix
    re-derivation on the grown suite: 261 drafts; precision 0.995 with a
    single residual FP over 68 benign drafts; recall 0.943; agreement 1.000.
4.  ``results/verifier_redteam_live_space-bunny-free_prefix.json`` — pre-fix
    run: precision 0.994, recall 0.942, agreement 1.000.

Every artifact with an ``overall`` block is also checked for internal
count consistency (tp+fn = should_reject, tn+fp = should_pass, and the
stored P/R match the counts at printed precision) so a corrupted count
fails even if the headline metrics were edited to match.

Usage::

    python scripts/verifier_redteam_check.py                 # repo artifacts
    python scripts/verifier_redteam_check.py --results-dir D # other dir

Exit codes: 0 all checks pass, 1 any check fails (or an artifact is
missing/unreadable).  Fully offline; safe to run in CI.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

# Half-way values stored at 4 decimals (0.9938, 0.9945, ...) must round to
# the paper's 3-decimal print; the nudge makes round-half-even print half-up
# exactly as the paper's tables do.
_R3_NUDGE = 1e-12


def r3(x: float) -> float:
    """Round to the 3 decimals the paper prints (nudged for half-way raws)."""
    return round(float(x) + _R3_NUDGE, 3)


# ── Declarative claims table ────────────────────────────────────────────────
# Each claim: (kind, path, expected, label).  Kinds:
#   "eq"        — exact equality (ints, strings, bools, empty lists)
#   "r3"        — r3(actual) == expected (floats vs printed 3 decimals)
#   "cases_len" — actual is a list and len(actual) == expected
# Path segments index dicts by str and lists by int.
Claim = tuple[str, tuple[Any, ...], Any, str]

_OFFLINE_CHECKS = ("danger", "identity", "consistency", "degenerate")

CLAIMS: dict[str, list[Claim]] = {
    # §VI-C: "precision 1.000 and recall 1.000 overall and on every check"
    "verifier_redteam.json": [
        # L4 growth (third-family llama regression lock): 96 → 103 cases
        # V16b growth (cross-family rescore regression lock): 103 → 105 cases
        # (7 new: 6 harvest-locked danger/secret shapes + 1 benign probe).
        ("eq", ("n_cases",), 105, "105 canonical cases"),
        ("cases_len", ("cases",), 105, "cases is a list of 105 per-case dicts"),
        ("r3", ("overall", "precision"), 1.0, "overall precision 1.000"),
        ("r3", ("overall", "recall"), 1.0, "overall recall 1.000"),
        ("eq", ("overall", "false_positives"), 0, "zero false positives"),
        ("eq", ("overall", "false_negatives"), 0, "zero false negatives"),
        ("eq", ("overall", "should_reject"), 78, "78 should-reject cases"),
        ("eq", ("overall", "should_pass"), 27, "27 should-pass cases"),
        ("eq", ("overall", "misattributed_keys"), [], "no misattributed rejections"),
        ("eq", ("all_gates_pass",), True, "all verdict gates pass"),
    ]
    + [
        claim
        for check in _OFFLINE_CHECKS
        for claim in (
            ("r3", ("per_check", check, "precision"), 1.0, f"{check} precision 1.000"),
            ("r3", ("per_check", check, "recall"), 1.0, f"{check} recall 1.000"),
        )
    ],
    # §VI-C: "precision 1.000 (95% Wilson CI 0.977–1.000, zero false positives
    # across 63 benign drafts), recall 0.931 (CI 0.883–0.960), per-case
    # verdict agreement 0.988" over "236 drafts"
    "verifier_redteam_live_deepseek-v4-flash-free.json": [
        ("eq", ("model",), "deepseek-v4-flash-free", "model is deepseek-v4-flash-free"),
        ("eq", ("authored_drafts",), 236, "236 authored drafts"),
        ("eq", ("cases",), 80, "80-case grown suite"),
        ("r3", ("overall", "precision"), 1.0, "precision 1.000"),
        ("eq", ("overall", "false_positives"), 0, "zero FPs across benign drafts"),
        ("eq", ("overall", "should_pass"), 63, "63 benign drafts"),
        ("r3", ("overall_wilson95", "precision", 0), 0.977, "Wilson P lo 0.977"),
        ("r3", ("overall_wilson95", "precision", 1), 1.0, "Wilson P hi 1.000"),
        ("r3", ("overall", "recall"), 0.931, "recall 0.931"),
        ("r3", ("overall_wilson95", "recall", 0), 0.883, "Wilson R lo 0.883"),
        ("r3", ("overall_wilson95", "recall", 1), 0.960, "Wilson R hi 0.960"),
        ("r3", ("category_agreement", "rate"), 0.988, "verdict agreement 0.988"),
        ("eq", ("category_agreement", "agree"), 79, "agreement count 79/80"),
        ("eq", ("category_agreement", "total"), 80, "agreement total 80"),
        ("eq", ("authoring_errors",), 0, "no authoring errors"),
    ],
    # §VI-C: second-author run "reproduced the deepseek result on the grown
    # suite: precision 0.995 with a single residual FP … recall 0.943,
    # agreement 1.000" over 261 drafts (post-fix canonical live artifact)
    "verifier_redteam_live.json": [
        ("eq", ("model",), "space-bunny-free", "model is space-bunny-free"),
        ("eq", ("authored_drafts",), 261, "261 authored drafts"),
        ("eq", ("cases",), 89, "89-case grown suite"),
        ("r3", ("overall", "precision"), 0.995, "precision 0.995"),
        ("eq", ("overall", "false_positives"), 1, "a single residual FP"),
        ("eq", ("overall", "should_pass"), 68, "68 benign drafts"),
        ("r3", ("overall", "recall"), 0.943, "recall 0.943"),
        ("r3", ("category_agreement", "rate"), 1.0, "agreement 1.000"),
        ("eq", ("authoring_errors",), 0, "no authoring errors"),
    ],
    # §VI-C: the re-run "re-derived the deepseek result almost exactly
    # (precision 0.994, recall 0.942, agreement 1.000)" (pre-fix artifact)
    "verifier_redteam_live_space-bunny-free_prefix.json": [
        ("eq", ("model",), "space-bunny-free", "model is space-bunny-free"),
        ("eq", ("cases",), 80, "80-case suite"),
        ("r3", ("overall", "precision"), 0.994, "precision 0.994"),
        ("r3", ("overall", "recall"), 0.942, "recall 0.942"),
        ("r3", ("category_agreement", "rate"), 1.0, "agreement 1.000"),
    ],
}


def _get(doc: dict[str, Any], path: tuple[Any, ...]) -> Any:
    node: Any = doc
    for seg in path:
        node = node[seg]
    return node


def _check_claim(doc: dict[str, Any], claim: Claim) -> str | None:
    """Return a failure message, or None if the claim holds."""
    kind, path, expected, label = claim
    where = ".".join(str(seg) for seg in path)
    try:
        actual = _get(doc, path)
    except (KeyError, IndexError, TypeError) as exc:
        return f"{where}: missing field ({exc})"
    if kind == "eq":
        if actual != expected:
            return f"{where}: got {actual!r}, expected {expected!r}"
    elif kind == "r3":
        if not isinstance(actual, (int, float)):
            return f"{where}: got {actual!r}, expected a number"
        if r3(actual) != expected:
            return f"{where}: got {actual} (prints {r3(actual)}), expected {expected}"
    elif kind == "cases_len":
        if not isinstance(actual, list):
            return f"{where}: expected a list of cases, got {type(actual).__name__}"
        if len(actual) != expected:
            return f"{where}: len {len(actual)}, expected {expected}"
    else:  # pragma: no cover - table is closed above
        return f"{where}: unknown claim kind {kind!r}"
    return None


def _check_internal_consistency(doc: dict[str, Any]) -> list[str]:
    """Counts must agree with each other and with the stored P/R rates."""
    fails: list[str] = []
    o = doc.get("overall")
    if not isinstance(o, dict):
        return ["overall: missing block for internal-consistency check"]
    tp, fn = o.get("true_positives"), o.get("false_negatives")
    fp, tn = o.get("false_positives"), o.get("true_negatives")
    sr, sp = o.get("should_reject"), o.get("should_pass")
    if None in (tp, fn, fp, tn, sr, sp):
        return ["overall: missing count fields for internal-consistency check"]
    if tp + fn != sr:
        fails.append(f"overall: tp+fn={tp + fn} != should_reject={sr}")
    if tn + fp != sp:
        fails.append(f"overall: tn+fp={tn + fp} != should_pass={sp}")
    # Degenerate strata can have an empty denominator; the harness defines
    # those rates as 1.0, so only check rates over non-empty denominators.
    if tp + fp > 0 and r3(o["precision"]) != r3(tp / (tp + fp)):
        fails.append(
            f"overall: precision {o['precision']} != tp/(tp+fp)={tp / (tp + fp):.4f}"
        )
    if tp + fn > 0 and r3(o["recall"]) != r3(tp / (tp + fn)):
        fails.append(
            f"overall: recall {o['recall']} != tp/(tp+fn)={tp / (tp + fn):.4f}"
        )
    return fails


def check_artifacts(results_dir: Path) -> tuple[int, int, list[str]]:
    """Run all claims; return (passed, failed, failure messages)."""
    passed = failed = 0
    fails: list[str] = []
    for name in sorted(CLAIMS):
        path = results_dir / name
        print(f"── {path}")
        if not path.is_file():
            print(f"FAIL {name}: artifact missing")
            fails.append(f"{name}: artifact missing")
            failed += 1
            continue
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"FAIL {name}: unreadable ({exc})")
            fails.append(f"{name}: unreadable ({exc})")
            failed += 1
            continue
        for claim in CLAIMS[name]:
            msg = _check_claim(doc, claim)
            if msg is None:
                passed += 1
                print(f"PASS {name}: {claim[3]}")
            else:
                failed += 1
                fails.append(f"{name}: {msg}")
                print(f"FAIL {name}: {msg}")
        for msg in _check_internal_consistency(doc):
            failed += 1
            fails.append(f"{name}: {msg}")
            print(f"FAIL {name}: {msg}")
    return passed, failed, fails


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check red-team artifacts against the paper's claims (offline)."
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=ROOT / "results",
        help="directory holding the red-team artifacts (default: repo results/)",
    )
    parser.add_argument(
        "--manifest-out",
        type=Path,
        default=None,
        help="if set, write a SHA-256 manifest to this path after checks pass",
    )
    args = parser.parse_args(argv)
    passed, failed, fails = check_artifacts(args.results_dir)
    print("─" * 60)
    if failed:
        print(f"FAIL: {failed} of {passed + failed} checks failed")
        for msg in fails:
            print(f"  - {msg}")
        return 1
    print(f"PASS: all {passed} artifact-consistency checks hold")

    if args.manifest_out:
        _write_manifest(args.results_dir, args.manifest_out)
        print("manifest written:", args.manifest_out)
    return 0


def _write_manifest(results_dir: Path, out: Path) -> None:
    """Emit a deterministic SHA-256 manifest for the four source artifacts."""
    import hashlib

    out.parent.mkdir(parents=True, exist_ok=True)
    entries: list[dict[str, str | int]] = []
    for name in (
        "verifier_redteam.json",
        "verifier_redteam_live_deepseek-v4-flash-free.json",
        "verifier_redteam_live.json",
        "verifier_redteam_live_space-bunny-free_prefix.json",
    ):
        path = results_dir / name
        blob = path.read_bytes()
        entries.append(
            {
                "artifact": name,
                "sha256": hashlib.sha256(blob).hexdigest(),
                "size_bytes": len(blob),
            }
        )
    manifest = {
        "kind": "verifier_redteam_artifact_manifest",
        "generated_by": str(Path(__file__).relative_to(ROOT).as_posix()),
        "artifacts": entries,
    }
    out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
