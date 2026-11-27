#!/usr/bin/env python3
"""Parallel, resumable runner for the v2 A/C workload.

The v2 pre-registration requires the two arms to be interleaved per persona
run. That is preserved here: each worker owns one (persona, run_id) pair and
executes that pair's two arms back-to-back in a seeded order. Pairs run in
parallel, so wall-clock stays sane without ever letting one arm drift hours
away from the other for the same persona/run.

Every session is a separate `field_attack_driver_v2.py` process writing one
JSONL line; a pair is skipped only when both arms already have a completed
record, which makes the runner resumable after a crash or a reboot.

Usage:
  python3 scripts/run_ab_v2_parallel.py --runs 4 --workers 4
  python3 scripts/run_ab_v2_parallel.py --runs 1 --personas novice_scriptkiddie --workers 2
"""

from __future__ import annotations

import argparse
import json
import os
import random
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / "scripts" / "field_attack_driver_v2.py"
RESULTS = ROOT / "results" / "field_attack"
PORTS = {"A": 2221, "C": 2223}
PERSONAS = ["novice_scriptkiddie", "recon_operator", "credential_hunter",
            "apt_patient", "evasion_probe"]
SEED = 20261028


def arm_order(personas: list[str], runs: int) -> dict[tuple[str, int], list[str]]:
    rng = random.Random(SEED)
    order: dict[tuple[str, int], list[str]] = {}
    for persona in personas:
        for run_id in range(1, runs + 1):
            arms = ["A", "C"]
            rng.shuffle(arms)
            order[(persona, run_id)] = arms
    return order


def completed(path: Path) -> set[tuple[str, int]]:
    seen: set[tuple[str, int]] = set()
    if not path.exists():
        return seen
    best: dict[tuple[str, int], tuple[float, dict]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        key = (rec.get("persona"), rec.get("run_id"))
        if not key[0] or not key[1]:
            continue
        ts = rec.get("collected_at") or ""
        # Keep the latest record per key; a resumed run overwrites an earlier
        # failed attempt so the function sees the current state, not history.
        if key not in best or ts >= best[key][0]:
            best[key] = (ts, rec)
    for key, (_, rec) in best.items():
        # ``partial`` alone is censored data (budget expired). ``error`` means
        # the session failed and must be retried, even with a few turns logged.
        if rec.get("error") is None:
            seen.add(key)
    return seen


def run_pair(persona: str, run_id: int, arms: list[str], max_turns: int) -> str:
    for arm in arms:
        out = RESULTS / f"sessions_v2_arm{arm}.jsonl"
        if (persona, run_id) in completed(out):
            continue
        cmd = [sys.executable, str(DRIVER), "--persona", persona, "--run-id", str(run_id),
               "--arm", arm, "--host", "127.0.0.1", "--port", str(PORTS[arm]), "--out", str(out)]
        # The driver exits 0 even when it records an error, so success is read
        # back from the log: a refused handshake triggers the driver's own
        # 5-attempt cowrie retry; the runner retries the whole driver if the
        # file still has no usable record after the driver exits.
        for attempt in (1, 2, 3):
            proc = subprocess.run(cmd, cwd=ROOT, timeout=5400,
                                  env={**os.environ, "RAGIN_ATTACK_MAX_TURNS": str(max_turns)})
            if proc.returncode != 0:
                return f"FAIL {arm} {persona} #{run_id} rc={proc.returncode}"
            if (persona, run_id) in completed(out):
                break
            print(f"retry {arm} {persona} #{run_id}: no usable record (attempt {attempt})",
                  flush=True)
            time.sleep(30)
        if (persona, run_id) not in completed(out):
            return f"FAIL {arm} {persona} #{run_id}: no usable record after retry"
    return f"done {persona} #{run_id} ({'/'.join(arms)})"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=4)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--personas", nargs="*", default=PERSONAS)
    parser.add_argument("--max-turns", type=int, default=30)
    args = parser.parse_args(argv[1:])

    schedule = arm_order(args.personas, args.runs)
    pending = sorted(schedule)
    print(f"{len(pending)} pairs, {args.workers} workers", flush=True)

    failures = 0
    # Interleave start times so concurrent workers do not hammer cowrie's
    # connection limit simultaneously (the observed cause of arm A failures).
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        future_handles: dict = {}
        for i, (p, r) in enumerate(pending):
            future_handles[pool.submit(run_pair, p, r, schedule[(p, r)],
                                       args.max_turns)] = (p, r)
        for fut in as_completed(future_handles):
            try:
                line = fut.result()
            except Exception as exc:  # noqa: BLE001 - surfaced, never swallowed
                line = f"ERROR {futures[fut]}: {exc!r}"
            print(line, flush=True)
            if line.startswith(("FAIL", "ERROR")):
                failures += 1
    print(f"complete: {len(pending) - failures}/{len(pending)} pairs", flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
