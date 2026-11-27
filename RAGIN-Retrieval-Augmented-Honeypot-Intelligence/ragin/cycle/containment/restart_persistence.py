"""
Restart persistence for containment-critical state.

WS3 requires containment-critical state (host fiction, audit seal, egress policy
provenance, session ownership map) to survive a container restart so that a
restart does not silently weaken the posture. This module provides the
restart-persistence helpers used by server_v2 on startup.

Production enforcement: these files live on a durability-bearing volume (bind
mount / field export dir) outside the container's ephemeral writable layer, and
their integrity is verified by audit_integrity.seal_current_state + the
host-level chattr immutable pattern where applicable.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from pathlib import Path

from ragin.cycle.containment.audit_integrity import RestartPersistentAuditLog

logger = logging.getLogger(__name__)


def persistent_audit_path() -> Path:
    raw = os.environ.get("RAGIN_AUDIT_PATH", "data/audit/ragin/audit.jsonl")  # type: ignore[attr-defined]
    p = Path(raw)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def load_host_fiction_on_restart(path: str | None = None) -> dict:
    target = Path(path or os.environ.get("RAGIN_HOST_FICTION_PATH", "data/host_fiction.json"))  # type: ignore[attr-defined]
    if not target.exists():
        return {}
    try:
        return json.loads(target.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        logger.exception("host fiction load failed on restart; starting fresh")
        return {}


def egress_policy_provenance_path() -> Path:
    p = Path(os.environ.get("RAGIN_EGRESS_POLICIES_PATH", "data/field/ragin/egress_policies.json"))  # type: ignore[attr-defined]
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def persist_egress_policy(provisions: dict) -> None:
    path = egress_policy_provenance_path()
    row = {
        "persisted_at": time.time(),
        "provisions": provisions,
        "content_hash": hashlib.sha256(
            json.dumps(provisions, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest(),
    }
    path.write_text(json.dumps(row, indent=2, default=str), encoding="utf-8")


def verify_egress_policy_on_restart(provisions: dict) -> dict[str, Any]:
    path = egress_policy_provenance_path()
    if not path.exists():
        return {"verified": False, "reason": "no persisted egress policy"}
    try:
        stored = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"verified": False, "reason": "malformed persisted egress policy"}
    expected_hash = hashlib.sha256(
        json.dumps(provisions, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()
    return {
        "verified": stored.get("content_hash") == expected_hash,
        "persisted_at": stored.get("persisted_at"),
        "stored_hash": stored.get("content_hash"),
        "expected_hash": expected_hash,
    }
