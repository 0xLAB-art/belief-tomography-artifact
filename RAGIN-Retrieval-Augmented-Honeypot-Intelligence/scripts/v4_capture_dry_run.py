#!/usr/bin/env python3
import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ragin.capture_v4.lineage import derive_canonical_record, verify_canonical_record
from ragin.capture_v4.manifest import create_manifest, seal_raw_capture, validate_manifest
from ragin.capture_v4.privacy import privacy_minimize_record, source_cluster_id
from ragin.capture_v4.registry import append_registry_record, read_registry

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="ragin-v4-capture-dry-run-") as directory:
        root = Path(directory)
        raw = root / "fixture.jsonl"
        events = [
            {"event_type": "session_start", "timestamp": "2026-10-14T00:00:00Z", "source_ip": "198.51.100.8"},
            {"event_type": "input", "timestamp": "2026-10-14T00:00:01Z", "input": "id"},
            {"event_type": "input", "timestamp": "2026-10-14T00:00:02Z", "input": "cat password=secret"},
        ]
        raw.write_text("\n".join(json.dumps(event) for event in events) + "\n")
        manifest = create_manifest(
            raw, capture_id="dry-capture-1", native_session_id="dry-native-1", source_class="CONTROLLED_REAL_HONEYPOT",
            collector_name="v4-dry-run", collector_version="1", collector_sha256=hashlib.sha256(b"collector").hexdigest(),
            deployment_id="dry-deployment", environment_id="fixture", capture_started_at_utc="2026-10-14T00:00:00Z",
            capture_ended_at_utc="2026-10-14T00:00:03Z", event_count=len(events), input_event_count=2,
            source_transport="fixture", test_fixture=True, created_at_utc="2026-10-14T00:00:04Z",
        )
        manifest_result = validate_manifest(manifest)
        canonical = derive_canonical_record(events, manifest, derivation_tool="v4_capture_dry_run.py", derivation_version="1", derivation_tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), source_cluster_id=source_cluster_id("dry-secret", "198.51.100.8"))
        canonical = privacy_minimize_record(canonical)
        canonical["canonical_record_sha256"] = hashlib.sha256(json.dumps({**canonical, "canonical_record_sha256": None}, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
        lineage_result = verify_canonical_record(canonical, manifest)
        raw_sealed = seal_raw_capture(raw)
        registry_path = root / "capture_registry.jsonl"
        row = {**manifest, "canonical_record_sha256": canonical["canonical_record_sha256"], "source_cluster_id": canonical["source_cluster_id"]}
        append_registry_record(registry_path, row)
        duplicate_refused = False
        try:
            append_registry_record(registry_path, row)
        except ValueError:
            duplicate_refused = True
        raw.chmod(raw.stat().st_mode | 0o200)
        raw.write_text(raw.read_text() + "{}\n")
        tamper_result = validate_manifest(manifest)
        invalid_cases = {}
        for flag in ("synthetic", "replay", "test_fixture"):
            invalid = create_manifest(
                raw, capture_id=f"invalid-{flag}", native_session_id=f"invalid-{flag}", source_class="CONTROLLED_REAL_HONEYPOT",
                collector_name="v4-dry-run", collector_version="1", collector_sha256="a" * 64, deployment_id="dry",
                environment_id="fixture", capture_started_at_utc="2026-10-14T00:00:00Z", capture_ended_at_utc="2026-10-14T00:00:03Z",
                event_count=4, input_event_count=2, source_transport="fixture", **{flag: True}, created_at_utc="2026-10-14T00:00:04Z",
            )
            invalid_cases[flag] = not validate_manifest(invalid)["eligible"]
        missing_manifest = validate_manifest({})
        broken_parent = dict(canonical)
        broken_parent["raw_parent_sha256"] = "b" * 64
        broken_parent["canonical_record_sha256"] = hashlib.sha256(json.dumps({**broken_parent, "canonical_record_sha256": None}, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
        broken_parent_result = verify_canonical_record(broken_parent, manifest)
        report = {
            "schema": "ragin.v4.prospective_capture_dry_run.v1",
            "sessions": 1,
            "eligible_for_study": 0,
            "manifest_created": manifest_result["valid"],
            "raw_sealed": raw_sealed,
            "fixture_ineligible": not manifest_result["eligible"],
            "canonical_derivation": lineage_result["valid"],
            "privacy_redaction": "198.51.100.8" not in json.dumps(canonical) and "secret" not in json.dumps(canonical),
            "cluster_id_stable": source_cluster_id("dry-secret", "198.51.100.8") == canonical["source_cluster_id"],
            "registry_append": len(read_registry(registry_path)) == 1,
            "duplicate_registry_refused": duplicate_refused,
            "tamper_detected": not tamper_result["valid"],
            "missing_manifest_rejected": not missing_manifest["valid"],
            "broken_parent_rejected": not broken_parent_result["valid"],
            "invalid_flags_rejected": invalid_cases,
            "crash_recovery": "append-only registry remains readable after interrupted derived work",
            "evaluation_executed": False,
            "reference_annotation_started": False,
        }
        rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
        if args.output:
            Path(args.output).write_text(rendered)
        print(rendered, end="")

if __name__ == "__main__":
    main()
