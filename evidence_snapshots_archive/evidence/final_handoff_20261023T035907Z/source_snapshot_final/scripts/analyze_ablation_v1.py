#!/usr/bin/env python3
"""Prespecified session-level analysis CLI for Track B records.

It refuses invalid, mixed, Track A or analysis-ineligible records. It never
coerces missing data to a no-event, agreement, or zero effect.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ragin.evaluation.analysis import AnalysisPlan, analyze_primary  # noqa: E402
from ragin.evaluation.records import read_records, validate_record_set  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--plan", type=Path, default=ROOT / "configs/ablation/eval_v1/analysis_plan_v1.json")
    parser.add_argument("--out", type=Path, default=Path(f"/tmp/opencode/ragin_ablation_analysis_{stamp}"))
    parser.add_argument("--allow-partial", action="store_true")
    args = parser.parse_args()

    records = read_records(args.records)
    errors = validate_record_set(records)
    if errors:
        print(json.dumps({"status": "INVALID_RECORDS", "errors": errors}, indent=2), file=sys.stderr)
        return 3
    eligible = []
    for record in records:
        if record.get("track") != "B":
            print(
                f"refusing primary analysis: {record.get('record_id')} is Track {record.get('track')}",
                file=sys.stderr,
            )
            return 3
        if record.get("analysis_eligible") is False:
            print(f"refusing primary analysis: {record.get('record_id')} is not analysis eligible", file=sys.stderr)
            return 3
        eligible.append(record)

    plan_doc = json.loads(args.plan.read_text(encoding="utf-8"))
    plan = AnalysisPlan.from_dict(plan_doc)
    result = analyze_primary(eligible, plan)
    result["source"] = {
        "records": str(args.records),
        "plan": str(args.plan),
        "plan_sha256": hashlib.sha256(args.plan.read_bytes()).hexdigest(),
    }
    if args.out.exists():
        print(f"refusing to overwrite: {args.out}", file=sys.stderr)
        return 2
    args.out.mkdir(parents=True)
    (args.out / "analysis.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# Ablation analysis summary",
        "",
        f"- status: **{result['status']}**",
        f"- estimand: {result['primary_estimand']}",
        f"- ITT arms present: {', '.join(result['arms_present'])}",
        f"- Holm family: {result['itt']['holm_family_status']}",
        "",
        "Detection CIF is reported jointly with technical/unavailable/abandonment CIF and receipt/exposure.",
        "A missing or unexposed arm is NOT_ESTABLISHED, never a zero effect.",
    ]
    (args.out / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "out": str(args.out)}, indent=2))
    if result["status"] == "ESTIMATED":
        return 0
    return 0 if args.allow_partial else 2


if __name__ == "__main__":
    raise SystemExit(main())
