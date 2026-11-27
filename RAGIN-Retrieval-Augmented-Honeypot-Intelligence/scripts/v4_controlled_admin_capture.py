#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import subprocess
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT))

from ragin.capture_v4.lineage import derive_canonical_record, seal_canonical_record, verify_canonical_record
from ragin.capture_v4.manifest import create_manifest, seal_raw_capture, validate_manifest
from ragin.capture_v4.privacy import privacy_minimize_record
from ragin.capture_v4.registry import append_registry_record, read_registry

RESULTS = ROOT / "results" / "decision_fusion_v4"
PROTOCOL_PATH = RESULTS / "v4_controlled_admin_capture_protocol_v1.json"
REGISTRY = ROOT / "data" / "prospective_v4" / "capture_registry.jsonl"
CAPTURE_DIR = ROOT / "data" / "prospective_v4" / "controlled_admin"

def utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def digest_bytes(value):
    return hashlib.sha256(value).hexdigest()

def digest_file(path):
    return digest_bytes(Path(path).read_bytes())

def canonical_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()

def environment_id():
    hostname = subprocess.check_output(["hostname"], text=True).strip()
    os_release_hash = digest_file("/etc/os-release")
    return "sha256:" + digest_bytes(f"controlled-admin|{hostname}|{os_release_hash}".encode())

def load_protocol():
    value = json.loads(PROTOCOL_PATH.read_text())
    if not value.get("created_before_session_1") or value.get("status") != "FROZEN_BEFORE_SESSION_1":
        raise RuntimeError("admin protocol is not frozen")
    return value, digest_bytes(canonical_bytes(value))

def run_native_shell(commands):
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": "/tmp", "LANG": "C", "TERM": "dumb"}
    process = subprocess.Popen(["/bin/bash", "--noprofile", "--norc"], cwd="/tmp", env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    events = [{"event_type": "session_start", "timestamp": utc_now(), "data": {"transport": "local-bash-session"}}]
    try:
        for command in commands:
            marker = "__RAGIN_V4_END_" + uuid.uuid4().hex
            process.stdin.write(command + "\nprintf '%s\\n' '" + marker + "'\n")
            process.stdin.flush()
            output = []
            while True:
                line = process.stdout.readline()
                if not line:
                    raise RuntimeError("native session ended before command marker")
                if line.rstrip("\n") == marker:
                    break
                output.append(line)
            events.append({"event_type": "operator_input", "timestamp": utc_now(), "operator_input": command, "output": "".join(output)})
        process.stdin.write("exit\n")
        process.stdin.flush()
        process.wait(timeout=10)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
    events.append({"event_type": "session_end", "timestamp": utc_now(), "return_code": process.returncode})
    return events

def atomic_write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("wb", dir=path.parent, delete=False) as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
        temp_path = Path(handle.name)
    os.replace(temp_path, path)
    return path

def capture_one(ordinal, protocol, protocol_hash):
    profile_name = ["A", "B", "C", "D"][(ordinal - 1) % 4]
    commands = protocol["procedure"]["profiles"][profile_name]
    capture_id = f"admin-{ordinal:03d}-{uuid.uuid4().hex}"
    native_session_id = capture_id
    started = utc_now()
    events = run_native_shell(commands)
    ended = utc_now()
    raw_path = CAPTURE_DIR / f"{capture_id}.raw.jsonl"
    raw_data = "".join(json.dumps(event, sort_keys=True, ensure_ascii=False) + "\n" for event in events).encode()
    atomic_write(raw_path, raw_data)
    collector_sha = digest_file(Path(__file__))
    manifest = create_manifest(
        raw_path, capture_id=capture_id, native_session_id=native_session_id, source_class="CONTROLLED_REAL_ADMIN",
        collector_name="v4_controlled_admin_capture.py", collector_version="v1", collector_sha256=collector_sha,
        deployment_id="local-controlled-admin", environment_id=environment_id(), capture_started_at_utc=started,
        capture_ended_at_utc=ended, event_count=len(events), input_event_count=len(commands), source_transport="local-bash-session",
        synthetic=False, replay=False, test_fixture=False, created_at_utc=utc_now(),
    )
    manifest_path = CAPTURE_DIR / f"{capture_id}.manifest.json"
    atomic_write(manifest_path, (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode())
    manifest_check = validate_manifest(manifest)
    if not manifest_check["eligible"]:
        raise RuntimeError("manifest failed before canonical derivation: " + json.dumps(manifest_check))
    canonical = derive_canonical_record(events, manifest, derivation_tool="v4_controlled_admin_capture.py", derivation_version="v1:" + protocol_hash, derivation_tool_sha256=collector_sha)
    canonical = seal_canonical_record(privacy_minimize_record(canonical))
    lineage_check = verify_canonical_record(canonical, manifest)
    if not lineage_check["valid"]:
        raise RuntimeError("lineage verification failed: " + json.dumps(lineage_check))
    canonical_path = CAPTURE_DIR / f"{capture_id}.canonical.json"
    atomic_write(canonical_path, (json.dumps(canonical, indent=2, sort_keys=True) + "\n").encode())
    seal_raw_capture(raw_path)
    manifest_check = validate_manifest(manifest)
    if not manifest_check["eligible"]:
        raise RuntimeError("manifest failed after sealing: " + json.dumps(manifest_check))
    row = {**manifest, "canonical_record_sha256": canonical["canonical_record_sha256"], "source_cluster_id": None}
    append_registry_record(REGISTRY, row)
    return {"capture_id": capture_id, "native_session_id": native_session_id, "profile": profile_name, "manifest": manifest_check, "lineage": lineage_check, "raw_sha256": manifest["raw_log_sha256"], "manifest_sha256": manifest["capture_manifest_sha256"], "canonical_sha256": canonical["canonical_record_sha256"], "registry_rows": len(read_registry(REGISTRY))}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=1)
    parser.add_argument("--start-ordinal", type=int, default=1)
    args = parser.parse_args()
    if args.count < 1 or args.count > 40 or args.start_ordinal < 1 or args.start_ordinal + args.count - 1 > 40:
        raise SystemExit("start ordinal and count must remain within 1..40")
    protocol, protocol_hash = load_protocol()
    CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    for ordinal in range(args.start_ordinal, args.start_ordinal + args.count):
        results.append(capture_one(ordinal, protocol, protocol_hash))
    print(json.dumps({"sessions": results, "eligible": len(results), "protocol_sha256": protocol_hash, "v4_evaluation_executed": False, "reference_labels": False, "effectiveness_seen": False}, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
