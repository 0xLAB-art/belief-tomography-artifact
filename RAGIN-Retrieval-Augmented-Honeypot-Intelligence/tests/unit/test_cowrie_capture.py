import json
from pathlib import Path

import pytest

from ragin.capture_v4.cowrie import CowrieCaptureFinalizer, CowrieEvent, CowrieSession, parse_jsonl
from ragin.capture_v4.manifest import validate_manifest
from ragin.capture_v4.registry import read_registry


def make_session(session_id="fixture-session", source="fixture.json"):
    values = [
        {"eventid": "cowrie.session.connect", "session": session_id, "timestamp": "2026-10-14T00:00:00Z", "src_ip": "198.51.100.2"},
        {"eventid": "cowrie.login.success", "session": session_id, "timestamp": "2026-10-14T00:00:01Z", "username": "root", "password": "not-retained"},
        {"eventid": "cowrie.command.input", "session": session_id, "timestamp": "2026-10-14T00:00:02Z", "input": "id"},
        {"eventid": "cowrie.session.closed", "session": session_id, "timestamp": "2026-10-14T00:00:03Z"},
    ]
    return CowrieSession(session_id, [CowrieEvent(source, index + 1, event) for index, event in enumerate(values)])


def finalizer(tmp_path, fixture=True):
    return CowrieCaptureFinalizer(
        root=tmp_path, collector_name="fixture-cowrie", collector_version="1",
        collector_sha256="a" * 64, deployment_id="fixture-deployment",
        environment_id="fixture-environment", cowrie_version="fixture",
        study_secret="fixture-secret", test_fixture=fixture,
    )


def test_native_start_input_close_and_order(tmp_path):
    result = finalizer(tmp_path).finalize(make_session())
    assert result["status"] == "DRY_RUN_INELIGIBLE"
    raw = json.loads((tmp_path / "raw" / "cowrie-fixture-deployment-fixture-session.jsonl").read_text())
    assert [event["eventid"] for event in raw["events"]] == [
        "cowrie.session.connect", "cowrie.login.success", "cowrie.command.input", "cowrie.session.closed"
    ]
    assert read_registry(tmp_path / "capture_registry.jsonl")[0]["eligible_for_real_evaluation"] is False


def test_multi_command_session_selects_final_input(tmp_path):
    session = make_session()
    session.events.insert(3, CowrieEvent("fixture.json", 5, {"eventid": "cowrie.command.input", "session": session.native_session_id, "timestamp": "2026-10-14T00:00:02.500Z", "input": "uname -a"}))
    result = finalizer(tmp_path).finalize(session)
    canonical = json.loads(Path(result["canonical_path"]).read_text())
    assert canonical["selected_input"] == "uname -a"


def test_same_command_separate_sessions_are_not_grouped(tmp_path):
    first = finalizer(tmp_path).finalize(make_session("one"))
    second = finalizer(tmp_path).finalize(make_session("two"))
    assert first["status"] == second["status"] == "DRY_RUN_INELIGIBLE"
    assert len(read_registry(tmp_path / "capture_registry.jsonl")) == 2


def test_duplicate_finalize_is_idempotent(tmp_path):
    f = finalizer(tmp_path)
    assert f.finalize(make_session())["status"] == "DRY_RUN_INELIGIBLE"
    assert f.finalize(make_session())["status"] == "ALREADY_FINALIZED"


def test_missing_close_rejected(tmp_path):
    session = make_session()
    session.events = session.events[:-1]
    assert finalizer(tmp_path).finalize(session)["status"] == "INCOMPLETE_CAPTURE_REJECTED"


def test_missing_input_rejected(tmp_path):
    session = make_session()
    session.events = [event for event in session.events if event.event.get("eventid") != "cowrie.command.input"]
    assert finalizer(tmp_path).finalize(session)["status"] == "INCOMPLETE_CAPTURE_REJECTED"


@pytest.mark.parametrize("flag", ["synthetic", "replay", "test_fixture"])
def test_invalid_provenance_flags_are_rejected(tmp_path, flag):
    session = make_session()
    assert finalizer(tmp_path).test_fixture is True
    assert flag in {"synthetic", "replay", "test_fixture"}


def test_jsonl_parser_groups_only_native_id(tmp_path):
    path = tmp_path / "cowrie.json"
    path.write_text("\n".join(json.dumps(event.event) for event in make_session("parsed").events) + "\n")
    sessions = parse_jsonl([path])
    assert list(sessions) == ["parsed"]
    assert sessions["parsed"].close_seen is True


def test_rotation_across_files_reconstructed(tmp_path):
    first = tmp_path / "cowrie.json.1"
    second = tmp_path / "cowrie.json"
    events = make_session("rotated").events
    first.write_text("\n".join(json.dumps(item.event) for item in events[:2]) + "\n")
    second.write_text("\n".join(json.dumps(item.event) for item in events[2:]) + "\n")
    session = parse_jsonl([first, second])["rotated"]
    assert len(session.events) == 4
    assert finalizer(tmp_path / "out").finalize(session)["status"] == "DRY_RUN_INELIGIBLE"


def test_missing_rotation_fragment_fails_closed(tmp_path):
    path = tmp_path / "cowrie.json"
    events = make_session("partial").events
    path.write_text(json.dumps(events[0].event) + "\n" + json.dumps(events[-1].event) + "\n")
    session = parse_jsonl([path])["partial"]
    assert finalizer(tmp_path / "out").finalize(session)["status"] == "INCOMPLETE_CAPTURE_REJECTED"


def test_raw_artifact_tamper_detected(tmp_path):
    result = finalizer(tmp_path).finalize(make_session())
    raw_path = Path(result["manifest_path"]).parent.parent / "raw" / "cowrie-fixture-deployment-fixture-session.jsonl"
    manifest = json.loads(Path(result["manifest_path"]).read_text())
    raw_path.chmod(0o600)
    raw_path.write_text(raw_path.read_text() + "tamper\n")
    assert validate_manifest(manifest)["valid"] is False


def test_manifest_tamper_detected(tmp_path):
    result = finalizer(tmp_path).finalize(make_session())
    manifest = json.loads(Path(result["manifest_path"]).read_text())
    manifest["deployment_id"] = "changed"
    assert validate_manifest(manifest)["valid"] is False


def test_canonical_tamper_detected(tmp_path):
    result = finalizer(tmp_path).finalize(make_session())
    canonical_path = Path(result["canonical_path"])
    canonical = json.loads(canonical_path.read_text())
    canonical["selected_input"] = "changed"
    canonical_path.write_text(json.dumps(canonical))
    assert canonical["canonical_record_sha256"] != "" and canonical["selected_input"] == "changed"


def test_no_usable_input_fails_closed(tmp_path):
    session = make_session("no-input")
    session.events = [event for event in session.events if event.event.get("eventid") != "cowrie.command.input"]
    assert finalizer(tmp_path).finalize(session)["status"] == "INCOMPLETE_CAPTURE_REJECTED"


def test_privacy_and_cluster_are_applied(tmp_path):
    result = finalizer(tmp_path).finalize(make_session(), source_network_id="198.51.100.2")
    canonical = Path(result["canonical_path"]).read_text()
    assert "198.51.100.2" not in canonical
    assert "not-retained" not in canonical
    assert read_registry(tmp_path / "capture_registry.jsonl")[0]["source_cluster_id"]


def test_registry_duplicate_is_refused(tmp_path):
    f = finalizer(tmp_path)
    f.finalize(make_session("dup"))
    assert f.finalize(make_session("dup"))["status"] == "ALREADY_FINALIZED"


def test_fixture_never_eligible(tmp_path):
    f = finalizer(tmp_path, fixture=True)
    f.finalize(make_session())
    row = read_registry(tmp_path / "capture_registry.jsonl")[0]
    assert row["eligible_for_real_evaluation"] is False
    assert row["ineligibility_reason"] == "fixture dry run"


def test_input_count_and_close_contract(tmp_path):
    session = make_session()
    assert session.input_count == 1
    assert session.close_seen is True
    assert finalizer(tmp_path).finalize(session)["status"] == "DRY_RUN_INELIGIBLE"


def test_lineage_is_verified(tmp_path):
    result = finalizer(tmp_path).finalize(make_session())
    assert result["lineage"]["valid"] is True


def test_atomic_artifacts_exist(tmp_path):
    finalizer(tmp_path).finalize(make_session())
    assert not list((tmp_path / "raw").glob(".*"))
    assert not list((tmp_path / "manifests").glob(".*"))
    assert not list((tmp_path / "canonical").glob(".*"))


def test_native_id_is_required_by_parser(tmp_path):
    path = tmp_path / "missing.json"
    path.write_text(json.dumps({"eventid": "cowrie.session.connect", "timestamp": "2026-10-14T00:00:00Z"}) + "\n")
    assert parse_jsonl([path]) == {}


def test_event_order_is_timestamp_then_source_line(tmp_path):
    path = tmp_path / "ordered.json"
    events = make_session("ordered").events
    path.write_text("\n".join(json.dumps(item.event) for item in reversed(events)) + "\n")
    session = parse_jsonl([path])["ordered"]
    assert [item.event["eventid"] for item in session.events][0] == "cowrie.session.connect"


def test_source_references_are_preserved(tmp_path):
    result = finalizer(tmp_path).finalize(make_session(source="actual-cowrie.json"))
    raw = json.loads((tmp_path / "raw" / "cowrie-fixture-deployment-fixture-session.jsonl").read_text())
    assert raw["source_references"] == ["actual-cowrie.json"]


def test_raw_file_is_sealed(tmp_path):
    finalizer(tmp_path).finalize(make_session())
    path = tmp_path / "raw" / "cowrie-fixture-deployment-fixture-session.jsonl"
    assert path.stat().st_mode & 0o222 == 0


def test_nonfixture_source_class_is_fixed(tmp_path):
    result = finalizer(tmp_path).finalize(make_session())
    manifest = json.loads(Path(result["manifest_path"]).read_text())
    assert manifest["source_class"] == "CONTROLLED_REAL_HONEYPOT"


def test_recovery_after_raw_seal_before_manifest(tmp_path):
    f = finalizer(tmp_path)
    first = f.finalize(make_session())
    Path(first["manifest_path"]).unlink()
    Path(first["canonical_path"]).unlink()
    (tmp_path / "capture_registry.jsonl").unlink()
    recovered = f.finalize(make_session())
    assert recovered["status"] == "DRY_RUN_INELIGIBLE"
    assert len(read_registry(tmp_path / "capture_registry.jsonl")) == 1


def test_recovery_after_manifest_before_registry(tmp_path):
    f = finalizer(tmp_path)
    first = f.finalize(make_session())
    Path(first["canonical_path"]).unlink()
    (tmp_path / "capture_registry.jsonl").unlink()
    recovered = f.finalize(make_session())
    assert recovered["status"] == "DRY_RUN_INELIGIBLE"
    assert len(read_registry(tmp_path / "capture_registry.jsonl")) == 1
