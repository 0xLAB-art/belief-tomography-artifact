#!/usr/bin/env python3
"""Build a blind human-evaluation packet and empty answer templates.

No ratings are generated. TEST_ONLY records produce an explicitly labelled
instrument smoke test, never human-validation data.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ragin.evaluation.human_packet import build_answer_template, build_packet, write_packet  # noqa: E402
from ragin.evaluation.records import read_records, validate_record_set  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20261023)
    parser.add_argument("--raters", type=int, default=2)
    parser.add_argument("--allow-test-only", action="store_true")
    parser.add_argument("--rater-ids", default="rater_a,rater_b")
    args = parser.parse_args()

    records = read_records(args.records)
    errors = validate_record_set(records)
    if errors:
        print(json.dumps({"status": "INVALID_RECORDS", "errors": errors}, indent=2), file=sys.stderr)
        return 3
    try:
        packet = build_packet(
            records,
            seed=args.seed,
            rater_count=args.raters,
            allow_test_only=args.allow_test_only,
        )
    except ValueError as exc:
        print(f"packet refused: {exc}", file=sys.stderr)
        return 2
    rater_ids = [item.strip() for item in args.rater_ids.split(",") if item.strip()]
    if len(rater_ids) != args.raters:
        print(f"expected {args.raters} rater ids, got {rater_ids}", file=sys.stderr)
        return 2
    templates = [build_answer_template(packet, rater) for rater in rater_ids]
    packet_path = args.out / "packet.json"
    files = write_packet(packet_path, packet, templates)
    summary = {
        "schema": "ragin.ablation.human_packet.summary.v1",
        "status": packet["status"],
        "items": len(packet["items"]),
        "raters": rater_ids,
        "files": files,
        "claim": (
            "Instrument only. No human ratings were collected. "
            "TEST_ONLY packets are not human-validation data."
        ),
    }
    (args.out / "packet_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
