"""
Protected audit records with integrity verification + restart persistence.

The app emits audit events (session create, command, verification, serve, error)
through the Harness event system -> server_v2. WS3 requires those audit records
to be: (1) protected from tampering, (2) integrity-verifiable, (3) retained
across restart. This module provides the integrity verifier and a restart-
persistent audit log abstraction.

Production enforcement of "audit records cannot be altered by an attacker inside
the container" is the read-only rootfs + tmpfs + no-new-privileges + host-level
auditd chattr immutable pattern. This module captures the APP-LEVEL integrity
invariant and verifies it locally: every audit row is HMAC-signed with a host key,
and a periodic + on-restart integrity check replays the chain and flags any row
whose signature does not verify.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import time
from typing import Any

logger = logging.getLogger(__name__)

_AUDIT_ROW_VERSION = 1


def _audit_host_key() -> bytes:
    raw = os.environ.get("RAGIN_AUDIT_HOST_KEY", "test-host-audit-key-v1")  # type: ignore[attr-defined]
    return raw.encode("utf-8")


def sign_audit_row(row: dict[str, Any]) -> dict[str, Any]:
    canonical = json.dumps(row, sort_keys=True, default=str).encode("utf-8")
    sig = hmac.new(_audit_host_key(), canonical, hashlib.sha256).hexdigest()
    out = dict(row)
    out["_audit_version"] = _AUDIT_ROW_VERSION
    out["_audit_ts"] = time.time()
    out["_audit_signature"] = sig
    return out


def verify_audit_row(row: dict[str, Any]) -> dict[str, Any]:
    version = row.get("_audit_version")
    sig = row.get("_audit_signature")
    if version != _AUDIT_ROW_VERSION:
        return {"integrity_ok": False, "reason": f"unsupported version {version}"}
    if not sig or not isinstance(sig, str) or len(sig) != 64:
        return {"integrity_ok": False, "reason": "missing or malformed signature"}
    payload = {k: v for k, v in row.items() if k not in ("_audit_signature", "_audit_ts")}
    canonical = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    expected = hmac.new(_audit_host_key(), canonical, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return {"integrity_ok": False, "reason": "signature mismatch"}
    return {"integrity_ok": True, "version": version, "ts": row.get("_audit_ts")}


def audit_chain_verified(rows: list[dict[str, Any]]) -> dict[str, Any]:
    ok_count = 0
    bad_rows: list[dict[str, Any]] = []
    first_bad: int | None = None
    prev_ts: float | None = None
    for i, row in enumerate(rows):
        v = verify_audit_row(row)
        if not v["integrity_ok"]:
            bad_rows.append({"index": i, "reason": v["reason"], "row": row})
            if first_bad is None:
                first_bad = i
            continue
        ts = row.get("_audit_ts")
        if prev_ts is not None and ts is not None and ts < prev_ts:
            bad_rows.append({"index": i, "reason": "timestamp decreased", "row": row})
            if first_bad is None:
                first_bad = i
            continue
        ok_count += 1
        prev_ts = ts
    return {
        "verified": len(bad_rows) == 0,
        "ok_count": ok_count,
        "bad_count": len(rows) - ok_count,
        "bad_rows": bad_rows,
        "first_bad_index": first_bad,
    }


class RestartPersistentAuditLog:
    def __init__(self, path: str) -> None:
        self._path = path

    def append(self, event: dict[str, Any]) -> dict[str, Any]:
        signed = sign_audit_row(event)
        try:
            with open(self._path, "a", encoding="utf-8") as f:
                f.write(json.dumps(signed, default=str) + "\n")
        except OSError:
            logger.exception("audit append failed for %s", self._path)
        return signed

    def load(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rows.append(json.loads(line))
                    except json.JSONDecodeError:
                        logger.warning("skipped malformed audit line: %s", line[:80])
        except OSError:
            logger.exception("audit load failed for %s", self._path)
        return rows

    def verify_on_restart(self) -> dict[str, Any]:
        return audit_chain_verified(self.load())

    def seal_current_state(self) -> bytes:
        data = self.load()
        canonical = json.dumps(data, sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()
