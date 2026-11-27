#!/usr/bin/env python3
"""Pipeline reseed — keep the judge audit and audited stability current.

Called by the scheduled apmix watch (and safe to run by hand). Idempotent:

  1. Panel audit  — if any raw run artifact is newer than its
     ``*_judgescored.json`` sibling (or the panel summary is older than
     the newest scored file), re-run ``rescore_judge_panel.main()``.
     Offline: the audit is deterministic re-scoring, no LLM calls.
  2. Stability    — if the stability artifact is older than the newest
     raw run (or older than the panel summary), re-run
     ``compare_run_stability.main()`` so the ``audited_panel`` section
     always reflects the corrected rows.

Exit codes (systemd failure semantics):
  0  nothing to do, or reseed succeeded
  1  reseed attempted but failed (error printed)
  3  reseed succeeded AND a new stability verdict is ``review`` — the
     caller (watch) should surface this loudly.

Usage:
    python3 scripts/reseed_audit_pipeline.py [--force]
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"

PANEL = RESULTS / "live_benchmark_judge_panel_corrected.json"
STABILITY = RESULTS / "stability_run1_vs_run2.json"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _newest(pattern: str) -> Path | None:
    files = [p for p in RESULTS.glob(pattern)
             if not p.name.endswith("_judgescored.json")
             and "corrected" not in p.name and "stability" not in p.name]
    return max(files, key=lambda p: p.stat().st_mtime) if files else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--force", action="store_true",
                    help="re-run both stages regardless of timestamps")
    args = ap.parse_args()

    ran = []

    # ── Stage 1: panel audit ────────────────────────────────────────────────
    runs = [p for p in RESULTS.glob("live_benchmark_*.json")
            if not p.name.endswith("_judgescored.json")
            and "corrected" not in p.name and "stability" not in p.name]
    scored = {p: p.with_name(p.stem + "_judgescored.json") for p in runs}

    needs_audit = args.force or any(
        not s.exists() or s.stat().st_mtime < p.stat().st_mtime
        for p, s in scored.items()
    ) or (PANEL.exists() and scored and PANEL.stat().st_mtime < max(
        s.stat().st_mtime for s in scored.values() if s.exists()))

    if needs_audit:
        try:
            rescore = _load("rescore_judge_panel",
                            ROOT / "scripts" / "rescore_judge_panel.py")
            rescore.main()
            ran.append("panel_audit")
        except Exception as exc:
            print(f"[reseed] panel audit FAILED: {type(exc).__name__}: {exc}",
                  file=sys.stderr)
            return 1

    # ── Stage 2: audited stability ──────────────────────────────────────────
    newest_run = _newest("live_benchmark_*.json")
    freshest = [p.stat().st_mtime for p in (PANEL, newest_run) if p and p.exists()]
    needs_stability = args.force or (
        STABILITY.exists() and freshest
        and STABILITY.stat().st_mtime < max(freshest))

    if needs_stability:
        try:
            compare = _load("compare_run_stability",
                            ROOT / "scripts" / "compare_run_stability.py")
            # compare_run_stability.main() reads sys.argv; drive it with
            # defaults (run1 vs run2) so the artifact path is unchanged.
            sys.argv = ["compare_run_stability"]
            rc = compare.main()
            if rc not in (0, None):
                raise RuntimeError(f"compare_run_stability returned {rc}")
            ran.append("audited_stability")
        except Exception as exc:
            print(f"[reseed] stability FAILED: {type(exc).__name__}: {exc}",
                  file=sys.stderr)
            return 1

    if not ran:
        print("[reseed] nothing to do — audit and stability are current")
        return 0

    verdict = "n/a"
    if STABILITY.exists():
        art = json.loads(STABILITY.read_text())
        verdict = art.get("composite", {}).get("verdict", "n/a")
        # The audited panel is the binding comparison; prefer its verdict.
        audited = art.get("audited_panel", {}).get("composite", {}).get("verdict")
        if audited:
            verdict = audited
    print(f"[reseed] reseeded: {', '.join(ran)} — stability verdict: {verdict}")
    return 3 if verdict == "review" else 0


if __name__ == "__main__":
    raise SystemExit(main())
