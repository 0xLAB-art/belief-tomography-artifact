from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .lineage import derive_canonical_record, select_final_input_event, verify_canonical_record
from .manifest import create_manifest, manifest_digest, seal_raw_capture, sha256_file, validate_manifest
from .privacy import privacy_minimize_record, source_cluster_id
from .registry import append_registry_record, read_registry


SCHEMA = "ragin.cowrie.raw_session.v1"
COWRIE_SOURCE_CLASS = "CONTROLLED_REAL_HONEYPOT"
DEFAULT_CLOSE_EVENTS = frozenset({"cowrie.session.closed"})


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_timestamp(value: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError("Cowrie timestamp is not a string")
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        raise ValueError("Cowrie timestamp has no timezone")
    return parsed.astimezone(timezone.utc)


def event_timestamp(event: dict) -> datetime:
    return parse_timestamp(event["timestamp"])


# Fallback ordering instant for events whose timestamp is missing or invalid:
# one corrupt line in one file must not lose every session from every file
# (parse_jsonl used to raise KeyError/ValueError from the sort key).
_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def _sort_timestamp(event: dict) -> datetime:
    try:
        return event_timestamp(event)
    except (KeyError, TypeError, ValueError):
        return _EPOCH


def event_id(event: dict) -> str | None:
    value = event.get("eventid", event.get("event_id"))
    return str(value) if value is not None else None


def native_session_id(event: dict) -> str | None:
    for key in ("session", "session_id", "sessionid"):
        value = event.get(key)
        if value:
            return str(value)
    return None


def is_input_event(event: dict) -> bool:
    return select_final_input_event([event]) is not None


@dataclass(frozen=True)
class CowrieEvent:
    source_path: str
    line_number: int
    event: dict


@dataclass
class CowrieSession:
    native_session_id: str
    events: list[CowrieEvent]

    @property
    def event_dicts(self) -> list[dict]:
        return [item.event for item in self.events]

    @property
    def close_seen(self) -> bool:
        return any(event_id(item.event) in DEFAULT_CLOSE_EVENTS for item in self.events)

    @property
    def input_count(self) -> int:
        return sum(is_input_event(item.event) for item in self.events)

    @property
    def start(self) -> datetime:
        return min(_sort_timestamp(item.event) for item in self.events)

    @property
    def end(self) -> datetime:
        return max(_sort_timestamp(item.event) for item in self.events)


def parse_jsonl(paths: Iterable[str | Path]) -> dict[str, CowrieSession]:
    sessions: dict[str, CowrieSession] = {}
    for path_value in paths:
        path = Path(path_value)
        with path.open(encoding="utf-8", errors="strict") as handle:
            for line_number, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    # A malformed line degrades that line only: sibling files
                    # and the rest of this file still parse.
                    continue
                if not isinstance(event, dict):
                    continue
                sid = native_session_id(event)
                if not sid:
                    continue
                session = sessions.setdefault(sid, CowrieSession(sid, []))
                session.events.append(CowrieEvent(str(path), line_number, event))
    for session in sessions.values():
        session.events.sort(key=lambda item: (_sort_timestamp(item.event), item.source_path, item.line_number))
    return sessions


def _atomic_json(path: Path, value: dict, *, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _atomic_raw(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class CowrieCaptureFinalizer:
    def __init__(self, *, root: str | Path, collector_name: str, collector_version: str,
                 collector_sha256: str, deployment_id: str, environment_id: str,
                 cowrie_version: str, study_secret: str | None = None,
                 test_fixture: bool = False):
        self.root = Path(root)
        self.raw_dir = self.root / "raw"
        self.manifest_dir = self.root / "manifests"
        self.canonical_dir = self.root / "canonical"
        self.registry_path = self.root / "capture_registry.jsonl"
        self.collector_name = collector_name
        self.collector_version = collector_version
        self.collector_sha256 = collector_sha256
        self.deployment_id = deployment_id
        self.environment_id = environment_id
        self.cowrie_version = cowrie_version
        self.study_secret = study_secret
        self.test_fixture = test_fixture

    def _existing(self, native_id: str) -> dict | None:
        for row in read_registry(self.registry_path):
            if row.get("native_session_id") == native_id and row.get("deployment_id") == self.deployment_id:
                return row
        return None

    def finalize(self, session: CowrieSession, *, source_network_id: str | None = None,
                 capture_id: str | None = None) -> dict:
        if self._existing(session.native_session_id):
            return {"status": "ALREADY_FINALIZED", "native_session_id": session.native_session_id}
        if not session.close_seen:
            return {"status": "INCOMPLETE_CAPTURE_REJECTED", "reason": "native close event missing"}
        if session.input_count < 1:
            return {"status": "INCOMPLETE_CAPTURE_REJECTED", "reason": "no usable input event"}
        capture_id = capture_id or f"cowrie-{self.deployment_id}-{session.native_session_id}"
        raw_path = self.raw_dir / f"{capture_id}.jsonl"
        raw_payload = {
            "schema": SCHEMA,
            "capture_id": capture_id,
            "native_session_id": session.native_session_id,
            "source_class": COWRIE_SOURCE_CLASS,
            "deployment_id": self.deployment_id,
            "cowrie_version": self.cowrie_version,
            "source_references": sorted({item.source_path for item in session.events}),
            "events": session.event_dicts,
        }
        if raw_path.is_file():
            try:
                existing_payload = json.loads(raw_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                return {"status": "HASH_MISMATCH_REJECTED", "reason": "existing raw artifact unreadable"}
            if existing_payload != raw_payload:
                return {"status": "HASH_MISMATCH_REJECTED", "reason": "existing raw artifact differs"}
        else:
            _atomic_raw(raw_path, raw_payload)
        sealed = seal_raw_capture(raw_path)
        if not sealed:
            return {"status": "INCOMPLETE_CAPTURE_REJECTED", "reason": "raw seal failed"}
        raw_hash = sha256_file(raw_path)
        manifest_path = self.manifest_dir / f"{capture_id}.json"
        if manifest_path.is_file():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                return {"status": "HASH_MISMATCH_REJECTED", "reason": "existing manifest unreadable"}
        else:
            manifest = create_manifest(
                raw_path, capture_id=capture_id, native_session_id=session.native_session_id,
                source_class=COWRIE_SOURCE_CLASS, collector_name=self.collector_name,
                collector_version=self.collector_version, collector_sha256=self.collector_sha256,
                deployment_id=self.deployment_id, environment_id=self.environment_id,
                capture_started_at_utc=session.start.isoformat().replace("+00:00", "Z"),
                capture_ended_at_utc=session.end.isoformat().replace("+00:00", "Z"),
                event_count=len(session.events), input_event_count=session.input_count,
                source_transport="cowrie-jsonlog", synthetic=False, replay=False,
                test_fixture=self.test_fixture, eligible_for_real_evaluation=not self.test_fixture,
                ineligibility_reason="fixture dry run" if self.test_fixture else None,
                signing_key=self.study_secret,
            )
            manifest.update({
                "cowrie_version": self.cowrie_version,
                "native_event_count": len(session.events),
                "first_event_timestamp": manifest["capture_started_at_utc"],
                "last_event_timestamp": manifest["capture_ended_at_utc"],
                "native_source_references": raw_payload["source_references"],
                "raw_parent_sha256": raw_hash,
            })
            manifest["capture_manifest_sha256"] = manifest_digest(manifest, signing_key=self.study_secret)
            _atomic_json(manifest_path, manifest)
        validation = validate_manifest(manifest, signing_key=self.study_secret if manifest.get("capture_manifest_digest_kind") == "hmac-sha256" else None)
        if not validation["valid"] or not validation["eligible"] and not self.test_fixture:
            return {"status": "INCOMPLETE_CAPTURE_REJECTED", "reason": "; ".join(validation["errors"])}
        cluster = source_cluster_id(self.study_secret, source_network_id)
        canonical_path = self.canonical_dir / f"{capture_id}.json"
        if canonical_path.is_file():
            try:
                canonical = json.loads(canonical_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                return {"status": "HASH_MISMATCH_REJECTED", "reason": "existing canonical artifact unreadable"}
        else:
            canonical = derive_canonical_record(
                session.event_dicts, manifest, derivation_tool="ragin.capture_v4.cowrie",
                derivation_version="v1", derivation_tool_sha256=self.collector_sha256,
                source_cluster_id=cluster,
            )
            canonical = privacy_minimize_record(canonical)
            canonical["canonical_record_sha256"] = __import__("ragin.capture_v4.lineage", fromlist=["canonical_digest"]).canonical_digest(canonical)
            _atomic_json(canonical_path, canonical)
        lineage = verify_canonical_record(canonical, manifest)
        if not lineage["valid"]:
            return {"status": "INCOMPLETE_CAPTURE_REJECTED", "reason": "; ".join(lineage["errors"])}
        row = dict(manifest)
        row["canonical_record_sha256"] = canonical["canonical_record_sha256"]
        row["source_cluster_id"] = cluster
        append_registry_record(self.registry_path, row)
        return {"status": "RECOVERED_VALID_CAPTURE" if not self.test_fixture else "DRY_RUN_INELIGIBLE",
                "capture_id": capture_id, "native_session_id": session.native_session_id,
                "manifest_path": str(manifest_path), "canonical_path": str(canonical_path),
                "lineage": lineage}

