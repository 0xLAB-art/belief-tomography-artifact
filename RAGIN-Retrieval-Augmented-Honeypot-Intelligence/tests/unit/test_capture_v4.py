import json
from pathlib import Path

import pytest

from ragin.capture_v4.lineage import derive_canonical_record, select_final_input_event, verify_canonical_record
from ragin.capture_v4.manifest import create_manifest, validate_manifest
from ragin.capture_v4.privacy import privacy_minimize_record, source_cluster_id
from ragin.capture_v4.registry import append_registry_record, read_registry

def events():
    return [
        {"event_type": "session_start", "data": {"session_id": "native-1", "source_ip": "198.51.100.9"}},
        {"event_type": "input", "input": "id"},
        {"event_type": "input", "input": "cat password=supersecret"},
    ]

def make_manifest(tmp_path, **kwargs):
    raw = tmp_path / "raw.jsonl"
    raw.write_text("\n".join(json.dumps(item) for item in events()) + "\n")
    defaults = {
        "raw_log_path": raw,
        "capture_id": "capture-1",
        "native_session_id": "native-1",
        "source_class": "CONTROLLED_REAL_HONEYPOT",
        "collector_name": "test-collector",
        "collector_version": "1",
        "collector_sha256": "a" * 64,
        "deployment_id": "deploy-1",
        "environment_id": "env-1",
        "capture_started_at_utc": "2026-10-14T00:00:00Z",
        "capture_ended_at_utc": "2026-10-14T00:01:00Z",
        "event_count": 3,
        "input_event_count": 2,
        "source_transport": "fixture",
        "created_at_utc": "2026-10-14T00:02:00Z",
    }
    defaults.update(kwargs)
    return raw, create_manifest(**defaults)

def test_manifest_creation_and_hash_verification(tmp_path):
    raw, manifest = make_manifest(tmp_path)
    assert validate_manifest(manifest)["eligible"] is True
    assert manifest["raw_log_size_bytes"] == raw.stat().st_size

def test_tamper_detection(tmp_path):
    raw, manifest = make_manifest(tmp_path)
    raw.write_text(raw.read_text() + "{}\n")
    result = validate_manifest(manifest)
    assert result["valid"] is False
    assert "raw log hash mismatch" in result["errors"]

def test_duplicate_native_id_and_registry_append(tmp_path):
    _, manifest = make_manifest(tmp_path)
    path = tmp_path / "capture_registry.jsonl"
    row = {**manifest, "canonical_record_sha256": "b" * 64, "source_cluster_id": "c"}
    append_registry_record(path, row)
    with pytest.raises(ValueError):
        append_registry_record(path, row)
    assert len(read_registry(path)) == 1

def test_lineage_and_final_input_selection(tmp_path):
    _, manifest = make_manifest(tmp_path)
    selected = select_final_input_event(events())
    assert selected[0] == 2
    record = derive_canonical_record(events(), manifest, derivation_tool="test", derivation_version="1", derivation_tool_sha256="d" * 64)
    assert record["selected_input"] == "cat password=supersecret"
    assert record["raw_parent_sha256"] == manifest["raw_log_sha256"]
    assert record["independence_group_id"] == "native-1"
    assert verify_canonical_record(record, manifest)["valid"] is True

def test_privacy_and_cluster_stability():
    value = {"source_ip": "203.0.113.5", "password": "secret", "command": "curl token=abc"}
    minimized = privacy_minimize_record(value)
    assert "203.0.113.5" not in json.dumps(minimized)
    assert "secret" not in json.dumps(minimized)
    assert source_cluster_id("study-secret", "network-1") == source_cluster_id("study-secret", "network-1")
    assert source_cluster_id("study-secret", "network-1") != source_cluster_id("study-secret", "network-2")

@pytest.mark.parametrize("flag", ["synthetic", "replay", "test_fixture"])
def test_invalid_source_flags_fail_closed(tmp_path, flag):
    _, manifest = make_manifest(tmp_path, **{flag: True})
    result = validate_manifest(manifest)
    assert result["valid"] is True
    assert result["eligible"] is False

def test_unpermitted_source_rejected(tmp_path):
    _, manifest = make_manifest(tmp_path, source_class="SYNTHETIC_GENERATOR")
    assert validate_manifest(manifest)["eligible"] is False

def test_missing_input_rejected(tmp_path):
    raw, manifest = make_manifest(tmp_path, input_event_count=0, event_count=1)
    raw.write_text(json.dumps({"event_type": "session_start"}) + "\n")
    manifest["raw_log_sha256"] = __import__("hashlib").sha256(raw.read_bytes()).hexdigest()
    manifest["raw_log_size_bytes"] = raw.stat().st_size
    manifest["capture_manifest_sha256"] = __import__("ragin.capture_v4.manifest", fromlist=["manifest_digest"]).manifest_digest(manifest)
    result = validate_manifest(manifest)
    assert result["eligible"] is False
