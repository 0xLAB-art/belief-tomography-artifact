"""Sandbox — isolated execution environment for attacker interactions.

Design principles from Anthropic Managed Agents:
- Sandbox = execution env (credentials never reach the sandbox)
- The sandbox is where attacker commands are "executed" (simulated)
- CTI corpus is the "hands" — the sandbox feeds data to the LLM brains
- Pets → Cattle: sandbox instances can be provisioned/destroyed freely

The sandbox manages:
- Command reception from attacker
- Routing through the pipeline (Harness)
- Response delivery back to attacker
- Artifact injection (honeytokens)
- Session lifecycle (create/resume/close)
"""

from __future__ import annotations

import hashlib
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Any

from ragin.capture_v4.privacy import bounded_redacted_text
from ragin.cycle.classification import normalize_classification
from ragin.cycle.harness import Harness
from ragin.cycle.session import Event, EventType, Session

logger = logging.getLogger(__name__)

# The generator's built-in default model name and the cost tracker's hardcoded
# label. Neither is evidence that a model was invoked for THIS interaction, so
# the trace labels them as configuration, never as observation.
_MODEL_ENV_VAR = "RAGIN_HISOKA_MODEL"
_SOURCE_DEFAULT_MODEL = "glm-5.3-flash-free"


_COMMAND_TEXT_LIMIT = 200


def _command_trace(command: str) -> dict[str, Any]:
    """Bounded, minimized command plus an independent full-command digest.

    The minimizer runs over the complete command *before* truncation, so a
    credential marker split at the limit cannot leak its tail. The raw command
    is never written to the METRIC event; the full digest is the integrity
    handle for matching the redacted row to the session's input event.
    """
    bounded = bounded_redacted_text(str(command), limit=_COMMAND_TEXT_LIMIT)
    return {
        "sha256": hashlib.sha256(str(command).encode()).hexdigest(),
        "text": bounded["text"],
        "chars": bounded["chars"],
        "truncated": bounded["truncated"],
        "availability": bounded["availability"],
    }


def _redacted_command(command: str) -> str:
    """Redact and bound a command before it enters the durable event log."""
    return str(_command_trace(command)["text"])


def _model_trace(metadata: dict[str, Any]) -> dict[str, Any]:
    observed = metadata.get("generator_model") or metadata.get("model")
    if isinstance(observed, str) and observed.strip():
        return {
            "value": observed.strip(),
            "availability": "OBSERVED_BY_GENERATOR",
            "runtime_model": None,
            "runtime_model_availability": "NOT_OBSERVED",
        }
    configured = os.environ.get(_MODEL_ENV_VAR)
    if isinstance(configured, str) and configured.strip():
        return {
            "value": configured.strip(),
            "availability": "CONFIGURED_NOT_OBSERVED",
            "runtime_model": None,
            "runtime_model_availability": "NOT_OBSERVED",
        }
    return {
        "value": _SOURCE_DEFAULT_MODEL,
        "availability": "SOURCE_DEFAULT_NOT_OBSERVED",
        "runtime_model": None,
        "runtime_model_availability": "NOT_OBSERVED",
    }


def _usage_trace(metadata: dict[str, Any]) -> dict[str, Any]:
    usage = metadata.get("usage")
    if isinstance(usage, dict) and ("prompt_tokens" in usage or "completion_tokens" in usage):
        return {
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "availability": str(usage.get("availability") or "REPORTED_BY_GENERATOR"),
        }
    return {"prompt_tokens": None, "completion_tokens": None, "availability": "NOT_AVAILABLE"}


def _cost_trace(metadata: dict[str, Any]) -> dict[str, Any]:
    cost = metadata.get("cost_usd")
    if isinstance(cost, (int, float)) and not isinstance(cost, bool):
        return {"value": float(cost), "availability": "REPORTED_BY_GENERATOR"}
    if metadata.get("cost_estimated") is not None or metadata.get("estimated_tokens") is not None:
        return {"value": None, "availability": "ESTIMATED_NOT_BILLED"}
    return {"value": None, "availability": "NOT_AVAILABLE"}


def _evidence_trace(result: Any) -> dict[str, Any]:
    cti = getattr(result, "cti_analysis", None)
    cti = cti if isinstance(cti, dict) else {}
    bundle = cti.get("evidence_bundle")
    if not isinstance(bundle, dict):
        return {
            "doc_ids": [],
            "ttps": [],
            "retrieval_status": "NOT_AVAILABLE",
            "backend": "NOT_AVAILABLE",
            "availability": "NOT_AVAILABLE",
        }
    retrieval_raw = bundle.get("retrieval")
    retrieval: dict[str, Any] = retrieval_raw if isinstance(retrieval_raw, dict) else {}
    don_raw = bundle.get("don_analysis")
    don: dict[str, Any] = don_raw if isinstance(don_raw, dict) else {}
    doc_ids = retrieval.get("relevant_doc_ids")
    ttps = don.get("ttps_seen")
    return {
        "doc_ids": [str(item) for item in doc_ids[:20]] if isinstance(doc_ids, list) else [],
        "ttps": [str(item) for item in ttps[:20]] if isinstance(ttps, list) else [],
        "retrieval_status": retrieval.get("retrieval_status", "NOT_AVAILABLE"),
        "backend": retrieval.get("backend", "NOT_AVAILABLE"),
        "availability": "OBSERVED_BUNDLE",
    }


def _interaction_trace(
    result: Any,
    verification: dict[str, Any],
    *,
    served_response_sha256: str,
    status: str,
    elapsed_ms: float,
    safe_response: str,
    arm: str,
) -> dict[str, Any]:
    raw_response = getattr(result, "deception_response", None)
    metadata = raw_response.get("metadata") if isinstance(raw_response, dict) else None
    metadata = metadata if isinstance(metadata, dict) else {}

    classification = normalize_classification(getattr(result, "classification", None))
    issues = verification.get("issues")
    issues = issues if isinstance(issues, list) else []
    serve_path = str(verification.get("serve_path") or metadata.get("serve_path") or "")

    reason = metadata.get("fallback_reason") or metadata.get("strategy_runtime_fallback")
    if reason in (None, "", "NOT_VERIFIABLE"):
        reason = None
    fallback_occurred = (
        serve_path == "FALLBACK_VERIFIED"
        or bool(metadata.get("fallback_served"))
        or bool(reason)
    )

    served_text = bounded_redacted_text(safe_response, limit=500)
    attempts = metadata.get("serving_attempts")
    attempts = attempts if isinstance(attempts, list) else []
    last_attempt = attempts[-1] if attempts and isinstance(attempts[-1], dict) else {}
    decision_event_id = metadata.get("decision_event_id") or last_attempt.get("decision_event_id")
    decision_event_sha256 = metadata.get("decision_event_sha256") or last_attempt.get("decision_event_sha256")
    decision_selected = metadata.get("decision_selected") or last_attempt.get("decision_selected")
    decision_availability = (
        "OBSERVED_EVENT_REFERENCE"
        if isinstance(decision_event_id, str) and decision_event_id not in {"", "NOT_VERIFIABLE"}
        else "NOT_AVAILABLE"
    )

    return {
        "schema": "ragin.interaction_trace.v1",
        "status": status,
        "arm": arm,
        "candidate_sha256": str(verification.get("candidate_sha256", "")),
        "served_response_sha256": served_response_sha256,
        "served_response_chars": len(safe_response),
        # Bounded final text for audit. The SHA-256 above is over the actual
        # bytes served, independent of this minimized/truncated projection.
        "served_text": served_text["text"],
        "served_text_chars": served_text["chars"],
        "served_text_truncated": served_text["truncated"],
        "served_text_availability": served_text["availability"],
        "classification": {
            "skill_level": classification.get("skill_level", "unknown"),
            "confidence": classification.get("confidence"),
            "availability": "OBSERVED" if "skill_level" in classification else "NOT_AVAILABLE",
        },
        "evidence_refs": _evidence_trace(result),
        "decision": {
            "serve_path": serve_path,
            "verification_passed": verification.get("passed") is True,
            "selected_strategy": str(metadata.get("selected_strategy", "NOT_AVAILABLE")),
            "event_id": str(decision_event_id) if decision_event_id else "NOT_AVAILABLE",
            "event_sha256": str(decision_event_sha256) if decision_event_sha256 else "NOT_AVAILABLE",
            "selected": decision_selected if isinstance(decision_selected, dict) else "NOT_AVAILABLE",
            "availability": decision_availability,
        },
        "verification": {
            "passed": verification.get("passed") is True,
            "reason": [str(item)[:200] for item in issues[:10]],
            "reason_availability": "OBSERVED" if issues else "NO_ISSUES_REPORTED",
        },
        "fallback": {
            "occurred": fallback_occurred,
            "reason": str(reason or ("UNRECORDED" if fallback_occurred else "NO_FALLBACK")),
        },
        "model_identity": _model_trace(metadata),
        "latency_ms": round(float(elapsed_ms), 3),
        "tokens": _usage_trace(metadata),
        "cost": _cost_trace(metadata),
    }


def _failed_interaction_trace(*, status: str, error: str, arm: str, latency_ms: float) -> dict[str, Any]:
    """Trace row for interactions that never reached the verifier."""
    return {
        "schema": "ragin.interaction_trace.v1",
        "status": status,
        "arm": arm,
        "candidate_sha256": "",
        "served_response_sha256": "",
        "served_response_chars": 0,
        "served_text": "",
        "served_text_chars": 0,
        "served_text_truncated": False,
        "served_text_availability": "NOT_AVAILABLE",
        "classification": {"skill_level": "unknown", "confidence": None, "availability": "NOT_AVAILABLE"},
        "evidence_refs": {
            "doc_ids": [],
            "ttps": [],
            "retrieval_status": "NOT_AVAILABLE",
            "backend": "NOT_AVAILABLE",
            "availability": "NOT_AVAILABLE",
        },
        "decision": {
            "serve_path": "",
            "verification_passed": False,
            "selected_strategy": "NOT_AVAILABLE",
            "event_id": "NOT_AVAILABLE",
            "event_sha256": "NOT_AVAILABLE",
            "selected": "NOT_AVAILABLE",
            "availability": "NOT_AVAILABLE",
        },
        "verification": {"passed": None, "reason": [], "reason_availability": "NOT_RUN"},
        "fallback": {"occurred": False, "reason": error},
        "model_identity": _model_trace({}),
        "latency_ms": round(float(latency_ms), 3),
        "tokens": {"prompt_tokens": None, "completion_tokens": None, "availability": "NOT_AVAILABLE"},
        "cost": {"value": None, "availability": "NOT_AVAILABLE"},
    }



@dataclass
class SandboxConfig:
    """Configuration for a sandbox instance."""

    source_ip: str = "_"
    max_commands: int = 1000
    timeout_s: float = 30.0
    enable_artifacts: bool = True
    enable_verification: bool = True
    session_dir: str | None = None


@dataclass
class SandboxResponse:
    """Response from the sandbox to the attacker."""

    session_id: str
    response_text: str
    command_count: int
    status: str = "ok"
    persona_used: str = ""
    artifacts_injected: list[str] = field(default_factory=list)
    engagement_score: float = 0.0
    serve_path: str = ""
    candidate_sha256: str = ""
    # Final-response observability: hash of the bytes actually returned to the
    # attacker (empty when the turn failed closed), plus the verifier verdict
    # that cleared them. The HTTP shim echoes the hash in its metadata so a
    # transcript row can be matched to its verification evidence.
    served_response_sha256: str = ""
    verification: dict[str, Any] = field(default_factory=dict)
    approval: dict[str, Any] | None = None
    processing_time_ms: float = 0.0
    event_count: int = 0
    error: str | None = None


class Sandbox:
    """Isolated execution environment for attacker interactions.

    The sandbox is the "hands" of RAGIN — it receives attacker commands,
    routes them through the pipeline (Harness), and returns deceptive
    responses. The LLM brains (Chrollo, Don, Hisoka) never touch the
    attacker directly — all interaction goes through the sandbox.

    Usage::

        sandbox = Sandbox(
            harness=Harness(classifier=..., cti_engine=..., deceiver=...),
        )
        # New session
        response = sandbox.handle_command("10.0.0.1", "whoami")
        # Continue session
        response = sandbox.handle_command(
            "10.0.0.1", "cat /etc/passwd", session_id=response.session_id
        )
    """

    def __init__(
        self,
        harness: Harness,
        config: SandboxConfig | None = None,
    ) -> None:
        self._harness = harness
        self._config = config or SandboxConfig()
        self._sessions: dict[str, Session] = {}  # session_id → Session
        # Per-session SandboxConfig captured at create_session() time so a
        # session-scoped max_commands (e.g. from the HTTP create endpoint)
        # is honored instead of the sandbox-wide default.
        self._session_configs: dict[str, SandboxConfig] = {}
        # Lock shards: one RLock per session_id. A slow or contended session
        # must never serialize (freeze) unrelated sessions — the previous
        # single global RLock did exactly that.
        self._session_locks: dict[str, threading.RLock] = {}
        # Guards ONLY the three registries above (short dict operations).
        # Pipeline processing runs under the per-session shard, never under
        # this lock. Lock ordering: session shard → registry lock.
        self._registry_lock = threading.Lock()

    # ── Lock sharding ─────────────────────────────────────────────────────

    def _session_lock(self, session_id: str) -> threading.RLock:
        """Return the lock shard for a session, creating it on first use."""
        with self._registry_lock:
            lock = self._session_locks.get(session_id)
            if lock is None:
                lock = threading.RLock()
                self._session_locks[session_id] = lock
            return lock

    def _drop_session_lock(self, session_id: str) -> None:
        """Remove a session's lock shard (cleanup on session close).

        Called while the caller already holds that shard, so any thread that
        fetched the same object is either inside (and re-checks session state)
        or still waiting on it — never running unlocked against a live session.
        """
        with self._registry_lock:
            self._session_locks.pop(session_id, None)

    def _register_session(self, session: Session, config: SandboxConfig | None = None) -> None:
        with self._registry_lock:
            self._sessions[session.session_id] = session
            if config is not None:
                self._session_configs[session.session_id] = config

    def _deregister_session(self, session_id: str) -> None:
        """Remove a closed session (and its per-session config) from the registries."""
        with self._registry_lock:
            self._sessions.pop(session_id, None)
            self._session_configs.pop(session_id, None)

    # ── Session creation ──────────────────────────────────────────────────

    def create_session(self, config: SandboxConfig | None = None) -> SandboxResponse:
        """Create a new session and return its ID.

        The supplied config (not just its source_ip/session_dir) is kept for
        the lifetime of the session, so a session-scoped ``max_commands`` —
        e.g. the one the HTTP create endpoint passes in — is enforced for
        that session only.
        """
        cfg = config or self._config
        session = Session.create(
            source_ip=cfg.source_ip if hasattr(cfg, "source_ip") else "_",
            session_dir=cfg.session_dir,
        )
        self._register_session(session, cfg)
        return SandboxResponse(
            session_id=session.session_id,
            response_text="",
            command_count=0,
            persona_used="",
        )

    # ── Command handling ──────────────────────────────────────────────────

    def handle_command(
        self,
        source_ip: str,
        command: str,
        session_id: str | None = None,
    ) -> SandboxResponse:
        # Lock sharding: serialize commands per session_id, not globally.
        # A session-creating call (session_id=None) has no contended session
        # yet — it only touches the registries, which have their own guard.
        if session_id is None:
            return self._handle_command_unlocked(source_ip, command, None)
        with self._session_lock(session_id):
            return self._handle_command_unlocked(source_ip, command, session_id)

    def _wake_session_locked(self, session_id: str) -> Session:
        """Wake a session from its durable log and register it.

        Caller must hold the session's lock shard. Raises FileNotFoundError
        when no log exists; ValueError propagates for invalid session ids
        (path-traversal defence) and is never converted into a file access.
        """
        session = Session.wake(session_id, session_dir=self._config.session_dir)
        self._register_session(session)
        # Restore _command_count from existing log
        restored = getattr(session, "_command_count", 0) or 0
        if restored == 0:
            session._command_count = len(session.get_events_by_type(EventType.ATTACKER_INPUT))  # type: ignore[attr-defined]
        return session

    def _effective_max_commands(self, session_id: str) -> int:
        """Per-session limit when one was configured, else the sandbox default."""
        cfg = self._session_configs.get(session_id)
        if cfg is not None:
            mc = getattr(cfg, "max_commands", None)
            if isinstance(mc, int) and not isinstance(mc, bool):
                return mc
        return self._config.max_commands

    def _handle_command_unlocked(
        self,
        source_ip: str,
        command: str,
        session_id: str | None = None,
    ) -> SandboxResponse:
        """Handle a single attacker command.

        If session_id is provided, resumes that session. Otherwise creates
        a new one. Caller holds the session's lock shard (when session_id
        was given), so events of one session never interleave.
        """
        # Get or create session
        if session_id is not None:
            with self._registry_lock:
                session = self._sessions.get(session_id)
            if session is None:
                # Try to wake from disk
                try:
                    session = self._wake_session_locked(session_id)
                except FileNotFoundError:
                    session = Session.create(source_ip=source_ip, session_dir=self._config.session_dir)
                    self._register_session(session)
                    # The requested id has no session; drop the stale lock
                    # shard keyed by it so attacker-controlled unknown ids
                    # cannot grow the shard registry without bound.
                    self._drop_session_lock(session_id)
        else:
            session = Session.create(source_ip=source_ip, session_dir=self._config.session_dir)
            self._register_session(session)

        # A closed session must never be written to again: emit() would raise
        # RuntimeError and escape as a 500. Return an explicit, durable-reason
        # error response instead.
        if session.is_closed:
            reason = session.closed_reason or "closed"
            return SandboxResponse(
                session_id=session.session_id,
                response_text="Session is closed.",
                command_count=getattr(session, "_command_count", 0) or 0,
                status="error",
                error=f"session_closed:{reason}",
            )

        # Check command limit (use _command_count which tracks actual commands,
        # not event_count which includes SESSION_START/END lifecycle events)
        command_count = getattr(session, "_command_count", 0) or 0
        command_count += 1
        session._command_count = command_count  # type: ignore[attr-defined]

        if command_count > self._effective_max_commands(session.session_id):
            arm = str(getattr(self._harness, "decision_arm", "UNKNOWN"))
            session.emit(
                EventType.METRIC,
                {
                    "command": _redacted_command(command),
                    "command_trace": _command_trace(command),
                    "processing_time_ms": 0.0,
                    "persona_used": "",
                    "artifacts_count": 0,
                    "trace": _failed_interaction_trace(
                        status="error",
                        error="max_commands_reached",
                        arm=arm,
                        latency_ms=0.0,
                    ),
                },
                source="sandbox",
            )
            session.close(reason="max_commands_reached")
            # The session is now closed: deregister it so later commands get
            # the explicit session_closed/max_commands response above instead
            # of a RuntimeError from emit() on a closed session.
            self._deregister_session(session.session_id)
            if session_id is not None:
                # Drop the shard we hold (cleanup on close, per [1a]).
                self._drop_session_lock(session_id)
            return SandboxResponse(
                session_id=session.session_id,
                response_text="Session limit reached.",
                command_count=command_count,
                status="error",
                error="max_commands_reached",
            )

        # Run through harness pipeline
        start = time.monotonic()
        try:
            result = self._harness.process(session, command)
        except Exception as exc:  # noqa: BLE001 — a crashed pipeline must be
            # an explicit, recorded failure, not an unhandled exception that
            # escapes the sandbox with no trace row.
            elapsed_ms = (time.monotonic() - start) * 1000
            arm = str(getattr(self._harness, "decision_arm", "UNKNOWN"))
            error = "verified_serve_unavailable"
            session.emit(
                EventType.METRIC,
                {
                    "command": _redacted_command(command),
                    "command_trace": _command_trace(command),
                    "processing_time_ms": elapsed_ms,
                    "persona_used": "",
                    "artifacts_count": 0,
                    "trace": _failed_interaction_trace(
                        status="error",
                        error=f"harness_exception:{exc.__class__.__name__}",
                        arm=arm,
                        latency_ms=elapsed_ms,
                    ),
                },
                source="sandbox",
            )
            return SandboxResponse(
                session_id=session.session_id,
                response_text="",
                command_count=getattr(session, "_command_count", 0),
                status="error",
                processing_time_ms=elapsed_ms,
                event_count=session.event_count,
                error=error,
            )
        elapsed_ms = (time.monotonic() - start) * 1000

        raw_response = getattr(result, "deception_response", None)
        response_dict = raw_response if isinstance(raw_response, dict) else {}
        artifacts = response_dict.get("artifacts_injected", [])
        if not isinstance(artifacts, list):
            artifacts = []

        verification = getattr(result, "verification", None)
        verification = verification if isinstance(verification, dict) else {}

        # Fail closed on an explicit verdict only. During mandatory serving an
        # absent/malformed verdict is NOT a pass, and the served bytes are
        # emptied rather than trusting a default.
        verified = verification.get("passed") is True
        raw_text = response_dict.get("response_text", "")
        safe_response = raw_text if isinstance(raw_text, str) else ""
        safe_error = getattr(result, "error", None)
        safe_status = "ok"
        mandatory = bool(getattr(self._harness, "mandatory_verification", True))
        if mandatory and not verified:
            safe_response = ""
            issues = verification.get("issues") or []
            safe_error = safe_error or (
                "verified_serve_unavailable:" + ",".join(str(i) for i in issues)
                if issues
                else "verified_serve_unavailable"
            )
            safe_status = "error"

        served_response_sha256 = (
            hashlib.sha256(safe_response.encode()).hexdigest() if safe_response else ""
        )

        # Final-response observability: one trace row per interaction, emitted
        # through the existing METRIC seam. The row separates the candidate
        # digest from the served digest, labels unavailable model/token/cost
        # data honestly, and represents failed/empty turns instead of dropping
        # them. The command is redacted before it is written.
        arm = str(getattr(self._harness, "decision_arm", "UNKNOWN"))
        trace = _interaction_trace(
            result,
            verification,
            served_response_sha256=served_response_sha256,
            status=safe_status,
            elapsed_ms=elapsed_ms,
            safe_response=safe_response,
            arm=arm,
        )
        session.emit(
            EventType.METRIC,
            {
                "command": _redacted_command(command),
                "command_trace": _command_trace(command),
                "processing_time_ms": elapsed_ms,
                "persona_used": response_dict.get("persona_used", ""),
                "artifacts_count": len(artifacts),
                "trace": trace,
            },
            source="sandbox",
        )

        return SandboxResponse(
            session_id=session.session_id,
            response_text=safe_response,
            command_count=getattr(session, "_command_count", 0),
            status=safe_status,
            persona_used=response_dict.get("persona_used", ""),
            artifacts_injected=artifacts,
            engagement_score=response_dict.get("engagement_score", 0.0),
            processing_time_ms=elapsed_ms,
            event_count=session.event_count,
            error=safe_error,
            serve_path=verification.get("serve_path", ""),
            # Candidate and final digests are distinct: the candidate is what
            # the generator produced, the served hash is what the attacker got
            # (empty when the turn failed closed).
            candidate_sha256=str(verification.get("candidate_sha256") or ""),
            served_response_sha256=served_response_sha256,
            verification=verification,
            approval=getattr(result, "approval", None) or None,
        )

    # ── Session management ───────────────────────────────────────────────

    def wake_session(self, session_id: str) -> tuple[Session, dict[str, Any]]:
        """Resume a session from its durable log under the session's lock.

        Wraps Session.wake so the HTTP wake path never resumes a session
        outside the sandbox: the wake, registration and command-count restore
        are serialized against any concurrent handle_command for the same
        session, so replayed state cannot interleave with live events.
        Returns (session, context) with the same summary keys Harness.wake
        reports. Raises FileNotFoundError for unknown sessions and ValueError
        for session ids failing path-traversal validation.
        """
        with self._session_lock(session_id):
            session = self._wake_session_locked(session_id)
            interactions = session.get_events_by_type(EventType.ATTACKER_INPUT)
            context: dict[str, Any] = {
                "total_events": session.event_count,
                "interaction_count": len(interactions),
            }
            return session, context

    def replay_session(
        self,
        session_id: str,
        after_event_id: str | None = None,
    ) -> list[Event]:
        """Read-only replay of a session's durable log under the session's lock.

        Unlike Session.wake this NEVER appends a SESSION_RESUME event, so
        repeated replay calls leave the log byte-identical (the previous
        wake-per-replay pattern grew the log on every call). Reading happens
        under the session's lock so it cannot race a concurrent append.
        Raises FileNotFoundError for unknown sessions and ValueError for
        invalid session ids.
        """
        with self._session_lock(session_id):
            session = Session(session_id, session_dir=self._config.session_dir)
            if not session._log_path.exists():
                raise FileNotFoundError(
                    f"Session {session_id} not found at {session._log_path}"
                )
            if after_event_id:
                return session.replay_since(after_event_id)
            return session.replay()

    def get_session_context(self, session_id: str) -> dict[str, Any] | None:
        """Get reconstructed context for a session."""
        with self._registry_lock:
            session = self._sessions.get(session_id)
        if session is not None:
            with self._session_lock(session_id):
                return session.build_context()
        try:
            with self._session_lock(session_id):
                session = Session.wake(session_id, session_dir=self._config.session_dir)
                return session.build_context()
        except FileNotFoundError:
            return None

    def close_session(self, session_id: str, reason: str = "normal") -> bool:
        """Close a session."""
        with self._registry_lock:
            session = self._sessions.get(session_id)
        if session is None:
            return False
        with self._session_lock(session_id):
            if not session.is_closed:
                session.close(reason=reason)
            self._drop_session_lock(session_id)
        return True

    def get_active_sessions(self) -> list[str]:
        """List active (non-closed) session IDs."""
        with self._registry_lock:
            sessions = list(self._sessions.items())
        return [sid for sid, session in sessions if not session.is_closed]

    # ── Batch operations ─────────────────────────────────────────────────

    def handle_commands(
        self,
        source_ip: str,
        commands: list[str],
        session_id: str | None = None,
    ) -> list[SandboxResponse]:
        """Handle multiple commands in sequence (same session)."""
        responses = []
        current_session_id = session_id
        for cmd in commands:
            resp = self.handle_command(source_ip, cmd, session_id=current_session_id)
            current_session_id = resp.session_id
            responses.append(resp)
        return responses

    # ── Metrics ──────────────────────────────────────────────────────────

    def get_metrics(self) -> dict[str, Any]:
        """Get aggregate metrics across all sessions."""
        with self._registry_lock:
            sessions = list(self._sessions.values())
        total_sessions = len(sessions)
        active_sessions = sum(1 for s in sessions if not s.is_closed)
        total_events = sum(s.event_count for s in sessions)
        return {
            "total_sessions": total_sessions,
            "active_sessions": active_sessions,
            "total_events": total_events,
        }
