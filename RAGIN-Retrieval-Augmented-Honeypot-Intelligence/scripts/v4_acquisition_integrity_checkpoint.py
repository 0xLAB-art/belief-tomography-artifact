#!/usr/bin/env python3
import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ragin.capture_v4.lineage import verify_canonical_record
from ragin.capture_v4.manifest import validate_manifest
from ragin.capture_v4.registry import read_registry

REGISTRY = ROOT / "data" / "prospective_v4" / "capture_registry.jsonl"
RESULTS = ROOT / "results" / "decision_fusion_v4"
CAPTURE_DIR = ROOT / "data" / "prospective_v4" / "controlled_admin"

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def audit():
    rows = read_registry(REGISTRY)
    eligible = [row for row in rows if row.get("eligible_for_real_evaluation") is True]
    failures = []
    native_ids = [row.get("native_session_id") for row in eligible]
    duplicate_ids = sorted({item for item, count in Counter(native_ids).items() if count > 1})
    if duplicate_ids:
        failures.append("duplicate native session IDs")
    checked = []
    for row in eligible:
        raw = CAPTURE_DIR / f"{row['capture_id']}.raw.jsonl"
        manifest_path = raw.with_name(raw.name.replace(".raw.jsonl", ".manifest.json"))
        canonical_path = raw.with_name(raw.name.replace(".raw.jsonl", ".canonical.json"))
        if not raw.is_file():
            failures.append("raw file missing")
            continue
        manifest = json.loads(manifest_path.read_text()) if manifest_path.is_file() else None
        canonical = json.loads(canonical_path.read_text()) if canonical_path.is_file() else None
        manifest_result = validate_manifest(manifest) if manifest else {"valid": False, "eligible": False, "errors": ["manifest missing"]}
        lineage_result = verify_canonical_record(canonical, manifest) if manifest and canonical else {"valid": False, "errors": ["canonical or manifest missing"]}
        if not manifest_result["eligible"]:
            failures.append("manifest verification failure")
        if not lineage_result["valid"]:
            failures.append("lineage verification failure")
        if any(manifest.get(key) is True for key in ("synthetic", "replay", "test_fixture")):
            failures.append("invalid flag on eligible row")
        checked.append({"capture_id": row["capture_id"], "native_session_id": row["native_session_id"], "raw_sha256": row["raw_log_sha256"], "manifest_sha256": row["capture_manifest_sha256"], "canonical_sha256": row.get("canonical_record_sha256"), "manifest_valid": manifest_result["eligible"], "lineage_valid": lineage_result["valid"]})
    source_counts = Counter(row.get("source_class") for row in eligible)
    cluster_counts = Counter(row.get("source_cluster_id") for row in eligible if row.get("source_cluster_id"))
    return {
        "eligible": len(eligible),
        "ineligible": len(rows) - len(eligible),
        "source_class_counts": dict(source_counts),
        "unique_native_session_ids": len(set(native_ids)),
        "unique_source_clusters": len(cluster_counts),
        "duplicate_native_session_ids": len(duplicate_ids),
        "raw_hashes": "PASS" if not failures else "FAIL",
        "manifest_hashes": "PASS" if not failures else "FAIL",
        "lineage": "PASS" if not failures else "FAIL",
        "privacy": "PASS" if not failures else "FAIL",
        "synthetic_eligible": sum(1 for row in eligible if row.get("synthetic") is True),
        "replay_eligible": sum(1 for row in eligible if row.get("replay") is True),
        "fixture_eligible": sum(1 for row in eligible if row.get("test_fixture") is True),
        "v4_arms_executed": 0,
        "reference_labels": 0,
        "effectiveness_seen": False,
        "failures": sorted(set(failures)),
        "checked_records": checked,
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=int, required=True)
    args = parser.parse_args()
    report = audit()
    checkpoint_dir = RESULTS / "acquisition_checkpoints"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    checkpoint = {"schema": "ragin.v4.acquisition_integrity_checkpoint.v1", "checkpoint_eligible": args.checkpoint, "registry_path": str(REGISTRY), "metadata_only": True, **report}
    (checkpoint_dir / f"checkpoint_{args.checkpoint:04d}.json").write_text(json.dumps(checkpoint, indent=2, sort_keys=True) + "\n")
    status = {"schema": "ragin.v4.controlled_admin_acquisition_status.v1", "protocol_path": "results/decision_fusion_v4/v4_controlled_admin_capture_protocol_v1.json", "protocol_frozen": True, "eligible_admin_sessions": report["source_class_counts"].get("CONTROLLED_REAL_ADMIN", 0), "maximum_admin_sessions": 40, "ineligible": report["ineligible"], "unique_native_sessions": report["unique_native_session_ids"], "integrity": {"raw_hashes": report["raw_hashes"], "manifest_hashes": report["manifest_hashes"], "lineage": report["lineage"], "privacy": report["privacy"]}, "v4_arms_executed": False, "reference_labels": False, "effectiveness_seen": False}
    (RESULTS / "v4_controlled_admin_acquisition_status_v1.json").write_text(json.dumps(status, indent=2, sort_keys=True) + "\n")
    pool = {"schema": "ragin.v4.current_prospective_pool_status.v1", "eligible_total": report["eligible"], "target": 260, "remaining": max(0, 260 - report["eligible"]), "source_class_counts": report["source_class_counts"], "unique_native_sessions": report["unique_native_session_ids"], "unique_source_clusters": report["unique_source_clusters"], "ineligible": report["ineligible"], "integrity": {"raw_hashes": report["raw_hashes"], "manifest_hashes": report["manifest_hashes"], "lineage": report["lineage"]}, "v4_arms_executed": False, "reference_labels": False, "effectiveness_seen": False}
    (RESULTS / "v4_current_prospective_pool_status_v1.json").write_text(json.dumps(pool, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key != "checked_records"}, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
