"""Print a blind slice of the E2-v1 audit sheet for manual labeling.

The sheet omits the oracle verdict and its reason. Label into
E2V1_AUDIT_LABELS.jsonl with fields:
  {"sheet_id": ..., "human_label": "breach"|"safe"|"unavailable"|"ambiguous",
   "rationale": "..."}

Run:
  python3 print_audit_batch.py --start 0 --end 10
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--end", type=int, default=None)
    ap.add_argument("--width", type=int, default=700)
    args = ap.parse_args()

    rows = [json.loads(l) for l in
            (HERE / "E2V1_AUDIT_BLIND.jsonl").read_text().splitlines() if l.strip()]
    end = args.end if args.end is not None else len(rows)
    print(f"{len(rows)} sessions on the blind sheet; showing [{args.start}, {end})\n")
    for i, r in enumerate(rows[args.start:end], start=args.start):
        print(f"### [{i}] {r['model']} | {r['family']}/g{r['generation']} | {r['session_id']}")
        for t in r["turns"]:
            print(f"  T{t['turn']} ADV: {t['adversary'][:args.width]}")
            if t.get("environment"):
                print(f"       ENV: {t['environment'][:args.width]}")
            print(f"       REPLY: {t['reply'][:args.width]}")
        print()


if __name__ == "__main__":
    main()
