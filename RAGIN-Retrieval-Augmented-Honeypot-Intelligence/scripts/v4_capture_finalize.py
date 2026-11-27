#!/usr/bin/env python3
import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ragin.capture_v4.lineage import derive_canonical_record, seal_canonical_record, select_final_input_event
from ragin.capture_v4.manifest import create_manifest, seal_raw_capture, validate_manifest
from ragin.capture_v4.privacy import privacy_minimize_record, source_cluster_id
from ragin.capture_v4.registry import append_registry_record

def load_events(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-log", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--canonical", required=True)
    parser.add_argument("--registry", required=True)
    parser.add_argument("--capture-id", required=True)
    parser.add_argument("--native-session-id", required=True)
    parser.add_argument("--source-class", required=True)
    parser.add_argument("--collector-name", required=True)
    parser.add_argument("--collector-version", required=True)
    parser.add_argument("--collector-sha256", required=True)
    parser.add_argument("--deployment-id", required=True)
    parser.add_argument("--environment-id", required=True)
    parser.add_argument("--started", required=True)
    parser.add_argument("--ended", required=True)
    parser.add_argument("--source-transport", required=True)
    parser.add_argument("--study-secret")
    parser.add_argument("--source-network-id")
    parser.add_argument("--synthetic", action="store_true")
    parser.add_argument("--replay", action="store_true")
    parser.add_argument("--test-fixture", action="store_true")
    args = parser.parse_args()
    events = load_events(args.raw_log)
    inputs = sum(select_final_input_event([event]) is not None for event in events)
    manifest = create_manifest(
        args.raw_log, capture_id=args.capture_id, native_session_id=args.native_session_id,
        source_class=args.source_class, collector_name=args.collector_name, collector_version=args.collector_version,
        collector_sha256=args.collector_sha256, deployment_id=args.deployment_id, environment_id=args.environment_id,
        capture_started_at_utc=args.started, capture_ended_at_utc=args.ended, event_count=len(events),
        input_event_count=inputs, source_transport=args.source_transport, synthetic=args.synthetic,
        replay=args.replay, test_fixture=args.test_fixture,
    )
    Path(args.manifest).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    validation = validate_manifest(manifest)
    if not validation["valid"]:
        print(json.dumps(validation, sort_keys=True))
        raise SystemExit(2)
    cluster = source_cluster_id(args.study_secret, args.source_network_id)
    canonical = derive_canonical_record(
        events, manifest, derivation_tool="v4_capture_finalize.py", derivation_version="v1",
        derivation_tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), source_cluster_id=cluster,
    )
    canonical = seal_canonical_record(privacy_minimize_record(canonical))
    Path(args.canonical).write_text(json.dumps(canonical, indent=2, sort_keys=True) + "\n")
    row = dict(manifest)
    row["canonical_record_sha256"] = canonical["canonical_record_sha256"]
    row["source_cluster_id"] = cluster
    append_registry_record(args.registry, row)
    seal_raw_capture(args.raw_log)
    print(json.dumps({"manifest": validation, "capture_id": args.capture_id, "eligible_for_real_evaluation": manifest["eligible_for_real_evaluation"]}, sort_keys=True))

if __name__ == "__main__":
    main()
