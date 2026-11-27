#!/usr/bin/env python3
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ragin.capture_v4.registry import read_registry

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("registry")
    args = parser.parse_args()
    rows = read_registry(args.registry)
    valid = [row for row in rows if row.get("eligible_for_real_evaluation") is True]
    report = {
        "total_captured_sessions": len(rows),
        "provenance_valid_sessions": len(valid),
        "invalid_sessions": len(rows) - len(valid),
        "source_class_counts": dict(Counter(row.get("source_class") for row in rows)),
        "unique_native_session_ids": len({row.get("native_session_id") for row in rows}),
        "unique_source_clusters": len({row.get("source_cluster_id") for row in rows if row.get("source_cluster_id")}),
        "capture_day_counts": dict(Counter(str(row.get("capture_started_at_utc", ""))[:10] for row in rows)),
        "outcome_fields_included": False,
    }
    print(json.dumps(report, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
