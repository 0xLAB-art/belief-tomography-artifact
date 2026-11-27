#!/usr/bin/env python3
"""Interleaved runner for the v2 A/C workload.

The v2 pre-registration asks for A and C to be interleaved per persona run
(seeded shuffle), so provider drift or a host restart cannot land on one arm.
Sessions are executed one at a time through `field_attack_driver_v2.py`, which
keeps each arm's JSONL append-only and resumable.

Usage:
  python3 scripts/run_ab_v2.py --runs 4                 # full study (20/arm)
  python3 scripts/run_ab_v2.py --runs 1 --personas novice_scriptkiddie   # pilot
"""

from __future__ import annotations

import argparse
import json
import os
import random
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / "scripts" / "field_attack_driver_v2.py"
RESULTS = ROOT / "results" / "field_attack"
PORTS = {"A": 2221, "C": 2223}
PERSONAS = ["novice_scriptkiddie", "recon_operator", "credential_hunter",
            "apt_patient", "evasion_probe"]
SEED = 20261028


def plan(personas: list[str], runs: int) -> list[tuple[str, int, str]]:
    rng = random.Random(SEED)
    order: list[tuple[str, int, str]] = []
    for persona in personas:
        for run_id in range(1, runs + 1):
            arms = ["A", "C"]
            rng.shuffle(arms)
            order.extend((persona, run_id, arm) for arm in arms)
    return order


def done(path: Path) -> set[tuple[str, int]]:
    seen: set[tuple[str, int]] = set()
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("partial") or not rec.get("error"):
                seen.add((rec.get("persona"), rec.get("run_id")))
    return seen


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=4)
    parser.add_argument("--personas", nargs="*", default=PERSONAS)
    parser.add_argument("--max-turns", type=int, default=30)
    args = parser.parse_args(argv[1:])

    schedule = plan(args.personas, args.runs)
    for persona, run_id, arm in schedule:
        out = RESULTS / f"sessions_v2_arm{arm}.jsonl"
        if (persona, run_id) in done(out):
            print(f"skip {arm} {persona} #{run_id} (already complete)", flush=True)
            continue
        cmd = [
            sys.executable, str(DRIVER),
            "--persona", persona, "--run-id", str(run_id), "--arm", arm,
            "--host", "127.0.0.1", "--port", str(PORTS[arm]), "--out", str(out),
        ]
        proc = subprocess.run(cmd, cwd=ROOT, timeout=3600,
                              env={**os.environ,
                                   "RAGIN_ATTACK_MAX_TURNS": str(args.max_turns)})
        if proc.returncode != 0:
            print(f"driver exited {proc.returncode} for {arm} {persona} #{run_id}", flush=True)
            return proc.returncode
    print("schedule complete", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
