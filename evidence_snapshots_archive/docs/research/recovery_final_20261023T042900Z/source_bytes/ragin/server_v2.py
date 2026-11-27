"""RAGIN v2 HTTP server — Harness + Session + Sandbox architecture.

Phase 2 of the harness/loop integration:
- Harness: stateless orchestration (Chrollo→Don→Hisoka pipeline)
- Session: append-only crash-safe event log
- Sandbox: attacker interaction isolation

Backward compatible: individual component endpoints still work.
New: /api/session/* endpoints use the full harness pipeline.

Usage:
    python -m ragin.server_v2                          # full pipeline
    python -m ragin.server_v2 --component chrollo      # individual component
    RAGIN_LAYA_ENABLED=0 python -m ragin.server_v2   # Laya decision OFF (default)
    RAGIN_LAYA_ENABLED=1 python -m ragin.server_v2   # Laya decision ON (opt-in)
"""

from __future__ import annotations

import argparse
import asyncio
import hmac
import json
import logging
import os
import re
import secrets
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml
from aiohttp import web

from ragin.cycle.adapters import ChrolloAdapter, DonAdapter, HisokaAdapter, SubstantiveStrategyAdapter
from ragin.cycle.harness import Harness
from ragin.cycle.sandbox import Sandbox, SandboxConfig
from ragin.cycle.session import Session
from ragin.decision_fusion_v4.runtime_mode import decision_arm_for_runtime, resolve_runtime_mode
from ragin.graph.host_fiction import HostFictionStore
from ragin.transport.mtls import (
    MTLSConfigError,
    build_server_context_from_env,
    peer_certificate_authorized,
)

logger = logging.getLogger("ragin.server_v2")

API_KEY = os.environ.get("API_KEY", "")
REQUIRE_AUTH = os.environ.get("RAGIN_REQUIRE_AUTH", "1").strip().lower() not in ("0", "false", "no", "off")
LOG_LEVEL = os.environ.get("RAGIN_LOG_LEVEL", "INFO")
_PLACEHOLDER_KEYS = {"", "changeme", "change_me", "change_me_backend_key", "placeholder"}
_SESSION_OWNERS: dict[str, str] = {}
_MTLS_PUBLIC_PATHS = {"/health", "/ready"}

# Optional Laya decision model. Default OFF; explicit opt-in only.
# This is the smallest first-class config surface for Laya on the server_v2 path.
# It does NOT create a second serving path; it only controls whether the existing
# ChrolloAdapter carries a bounded Laya decision signal. When disabled the
# baseline behaviour is preserved byte-for-byte (no Laya infer callable is built,
# no Laya block is emitted, no extra latency is incurred).
_LAYA_ENV_ENABLED_STR = os.environ.get("RAGIN_LAYA_ENABLED", "0").strip().lower()
_LAYA_TIMEOUT_S = float(os.environ.get("RAGIN_LAYA_TIMEOUT_S", "30"))
_LAYA_SYMBOL_NAME = "laya"
_LAYA_VALID_BOOLEANS = frozenset({"1", "true", "yes", "on"})


def laya_enabled() -> bool:
    """Public server_v2 config predicate for optional Laya decision.

    Default OFF. Only explicit opt-in values enable it. Invalid/non-standard
    values are treated as OFF safely (no crash, no guessing).
    """
    # Explicit opt-in only. Invalid / non-standard values are treated as OFF
    # safely so a misconfigured deployment never silently turns Laya on.
    env = _LAYA_ENV_ENABLED_STR
    return env in _LAYA_VALID_BOOLEANS


def laya_enabled_str() -> str:
    """Resolved Laya config value after env parsing, for diagnostics/logs."""
    return _LAYA_ENV_ENABLED_STR


def laya_timeout_s() -> float:
    """Predefined Laya decision timeout used by the optional adapter path."""
    return _LAYA_TIMEOUT_S


def laya_symbol_name() -> str:
    """Symbol/label used for optional Laya decision provenance traces."""
    return _LAYA_SYMBOL_NAME

# Production safety policy: production deployments must never silently enter
# unauthenticated mode. This module-level helper is read by tests and by
# _validate_security_config / startup logging.

_PRODUCTION_REQUIRE_AUTH_VALUES = frozenset({"1", "true", "yes", "on"})
_LOCAL_DEV_REQUIRE_AUTH_VALUES = frozenset({"0", "false", "no", "off"})

# Known placeholder API_KEY values that are never acceptable in production.
# This set is intentionally small and explicit; it is extended by the
# placeholder-detection helper below, which also treats the default .env.example
# template as a placeholder.
_PLACEHOLDER_KEYS = {"", "changeme", "change_me", "change_me_backend_key", "placeholder"}

_DEFAULT_ENV_TEMPLATE_API_KEY = "ragin-<generate-a-new-random-hex-key>"


def _api_key_is_placeholder(key: str) -> bool:
    """True when `key` is a known placeholder or the default .env.example template.

    This is deliberately conservative: it treats the literal default template
    value from .env.example as a placeholder so a copy/paste deployment does not
    silently run with the template value as the production key.
    """
    if not key:
        return True
    if key.strip().lower() in _PLACEHOLDER_KEYS:
        return True
    return key == _DEFAULT_ENV_TEMPLATE_API_KEY


def _is_production_auth_disabled() -> bool:
    """True when the process will start with auth fully disabled (no API key
    check and no session-token check). This is safe ONLY in a narrowly scoped
    local-development posture; production deployments must not use it."""
    return (not REQUIRE_AUTH) and (not API_KEY.strip())


def _production_auth_is_enforced() -> bool:
    """True when production auth is active: REQUIRE_AUTH enabled AND a non-empty
    API_KEY is configured. Placeholder keys do NOT count as production-ready."""
    return REQUIRE_AUTH and (not _api_key_is_placeholder(API_KEY)) and bool(API_KEY.strip())


def _load_config() -> dict[str, Any]:
    config_path = os.path.join(os.path.dirname(__file__), "config", "settings.yaml")
    if os.path.exists(config_path):
        with open(config_path) as f:
            return yaml.safe_load(f) or {}
    return {}


# Field-collection export root: a copy of each session's event log is dumped
# here when the session closes, so collect_field_data.py can pull transcripts
# without touching live session state.
_FIELD_EXPORT = Path(os.environ.get("RAGIN_FIELD_EXPORT_DIR", "data/field/ragin"))


def _field_export_dir() -> Path:
    try:
        _FIELD_EXPORT.mkdir(parents=True, exist_ok=True)
    except OSError:
        return _FIELD_EXPORT
    return _FIELD_EXPORT


# In-memory transcript-prefix map for cowrie bridge sessions. Stock cowrie's
# LLM backend sends the FULL growing conversation on every command and echoes
# no session header, so continuity is reconstructed by content: each request
# resumes the session whose transcript is a prefix of this one (cowrie appends
# monotonically within an SSH session). Keyed on (role, content) tuples;
# bounded to keep memory flat under long-running field deployments.
_TRANSCRIPT_MAP: dict[tuple, str] = {}
_TRANSCRIPT_MAP_MAX = 20_000


def _messages_key(messages: list) -> tuple:
    return tuple((str(m.get("role", "")), str(m.get("content", ""))) for m in messages if isinstance(m, dict))


def _resolve_bridge_session(messages: list) -> str | None:
    """Return the session id whose transcript is the longest prefix of this
    conversation, or None when no known prefix exists (new SSH session).
    """
    key = _messages_key(messages)
    for k in range(len(key), 0, -1):
        sid = _TRANSCRIPT_MAP.get(key[:k])
        if sid:
            return sid
    return None


def _remember_bridge_session(messages: list, session_id: str) -> None:
    if len(_TRANSCRIPT_MAP) >= _TRANSCRIPT_MAP_MAX:
        _TRANSCRIPT_MAP.clear()  # crude bound; sessions on disk remain resumable
    _TRANSCRIPT_MAP[_messages_key(messages)] = session_id


# ── Shared state ─────────────────────────────────────────────────────────────

_harness: Harness | None = None
_sandbox: Sandbox | None = None
_component: Any = None
_COMPONENT_NAME: str = "pipeline"
# Redacted provider resolution recorded at pipeline init, exposed by /health so
# an operator can see WHERE inference will be sent without printing the key.
_PROVIDER_INFO: dict[str, Any] = {}


# ── Middleware ────────────────────────────────────────────────────────────────


def _request_authorized(request: web.Request) -> bool:
    """X-API-Key (RAGIN servers) or Bearer (OpenAI-compatible clients,
    e.g. cowrie's LLM backend POSTing /v1/chat/completions)."""
    if not REQUIRE_AUTH and not API_KEY:
        return True
    if API_KEY.strip().lower() in _PLACEHOLDER_KEYS:
        return False
    if request.headers.get("X-API-Key", "") == API_KEY:
        return True
    auth = request.headers.get("Authorization", "")
    return auth.startswith("Bearer ") and auth[len("Bearer ") :] == API_KEY


def _validate_security_config() -> None:
    if REQUIRE_AUTH and _api_key_is_placeholder(API_KEY):
        key_desc = "empty" if not API_KEY.strip() else "placeholder"
        raise RuntimeError(
            f"RAGIN_REQUIRE_AUTH is enabled but API_KEY is {key_desc}. "
            "Generate a real API key and set it in the deployment environment."
        )
    if _is_production_auth_disabled():
        logger.warning(
            "SECURITY: RAGIN_REQUIRE_AUTH is disabled and API_KEY is empty. "
            "All routes (including the Cowrie bridge and session-command endpoints) "
            "will accept unauthenticated requests. This is acceptable ONLY for isolated "
            "local development. Production deployments must set RAGIN_REQUIRE_AUTH=1 "
            "and a non-empty API_KEY."
        )
    mtls_required = os.environ.get("RAGIN_MTLS_REQUIRED", "0").strip().lower() in {"1", "true", "yes", "on"}
    if mtls_required and not os.environ.get("RAGIN_MTLS_ALLOWED_IDENTITIES", "").strip():
        raise MTLSConfigError("RAGIN_MTLS_ALLOWED_IDENTITIES is required when mTLS is enabled")
    if mtls_required:
        build_server_context_from_env()


def _session_token() -> str:
    return secrets.token_urlsafe(32)


def _register_session(session_id: str) -> str:
    token = _session_token()
    _SESSION_OWNERS[session_id] = token
    return token


def _session_authorized(request: web.Request, session_id: str, *, transcript_proof: bool = False) -> bool:
    if not REQUIRE_AUTH:
        return True
    supplied = request.headers.get("X-Session-Token", "")
    expected = _SESSION_OWNERS.get(session_id, "")
    if supplied and expected:
        return hmac.compare_digest(supplied, expected)
    return transcript_proof


@web.middleware
async def auth_middleware(request: web.Request, handler: Any) -> web.Response:
    if request.path in ("/health", "/ready"):
        return await handler(request)
    if not _request_authorized(request):
        return web.json_response({"error": "unauthorized"}, status=401)
    return await handler(request)


@web.middleware
async def mtls_middleware(request: web.Request, handler: Any) -> web.Response:
    enabled = os.environ.get("RAGIN_MTLS_REQUIRED", "0").strip().lower() in {"1", "true", "yes", "on"}
    if not enabled or request.path in _MTLS_PUBLIC_PATHS:
        return await handler(request)

    transport = request.transport
    certificate = transport.get_extra_info("peercert") if transport is not None else None
    allowed = frozenset(
        identity.strip()
        for identity in os.environ.get("RAGIN_MTLS_ALLOWED_IDENTITIES", "").split(",")
        if identity.strip()
    )
    if not peer_certificate_authorized(certificate, allowed):
        return web.json_response({"error": "client identity unauthorized"}, status=403)
    return await handler(request)


@web.middleware
async def timing_middleware(request: web.Request, handler: Any) -> web.Response:
    start = time.monotonic()
    response = await handler(request)
    elapsed = time.monotonic() - start
    response.headers["X-Response-Time"] = f"{elapsed:.3f}s"
    return response


# ── Pipeline endpoints (full harness flow) ───────────────────────────────────


async def session_create(request: web.Request) -> web.Response:
    """Create a new attacker session via Sandbox."""
    try:
        data = await request.json()
    except Exception:
        data = {}

    source_ip = data.get("source_ip", request.remote or "unknown")
    max_commands = data.get("max_commands", 1000)

    config = SandboxConfig(source_ip=source_ip, max_commands=max_commands)
    if _sandbox is None:
        return web.json_response({"error": "sandbox not initialized"}, status=503)
    resp = _sandbox.create_session(config)
    token = _register_session(resp.session_id)

    return web.json_response(
        {
            "session_id": resp.session_id,
            "status": resp.status,
            "session_token": token,
        }
    )


async def session_command(request: web.Request) -> web.Response:
    """Process an attacker command through the full Harness pipeline."""
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON body"}, status=400)

    session_id = data.get("session_id")
    command = data.get("command", data.get("attacker_input", ""))

    if not session_id:
        return web.json_response({"error": "session_id required"}, status=400)
    if not command:
        return web.json_response({"error": "command required"}, status=400)
    if not _session_authorized(request, session_id):
        return web.json_response({"error": "session unauthorized"}, status=403)

    if _sandbox is None:
        return web.json_response({"error": "sandbox not initialized"}, status=503)
    resp = await asyncio.to_thread(
        _sandbox.handle_command,
        source_ip="_",
        command=command,
        session_id=session_id,
    )
    if resp.error:
        # Fail closed: the served text is empty and the transport error is
        # explicit. Observability fields are echoed so a caller can audit WHY
        # nothing was served; they never turn this into a success.
        return web.json_response(
            {
                "error": "verified_serve_unavailable",
                "status": resp.status,
                "session_id": resp.session_id,
                "command_count": resp.command_count,
                "response_text": "",
                "serve_path": resp.serve_path,
                "candidate_sha256": resp.candidate_sha256,
                "served_response_sha256": resp.served_response_sha256,
                "verification": resp.verification,
            },
            status=503,
        )

    return web.json_response(
        {
            "session_id": resp.session_id,
            "response_text": resp.response_text,
            "command_count": resp.command_count,
            "event_count": resp.event_count,
            "status": resp.status,
            "serve_path": resp.serve_path,
            "candidate_sha256": resp.candidate_sha256,
            "served_response_sha256": resp.served_response_sha256,
            "verification": resp.verification,
            "error": resp.error,
        }
    )


async def session_wake(request: web.Request) -> web.Response:
    """Wake a crashed session and resume processing."""
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON body"}, status=400)

    session_id = data.get("session_id")
    if not session_id:
        return web.json_response({"error": "session_id required"}, status=400)
    if not _session_authorized(request, session_id):
        return web.json_response({"error": "session unauthorized"}, status=403)

    session, context = await asyncio.to_thread(
        Harness.wake,
        session_id,
        classifier=_harness._classifier if _harness else None,
        cti_engine=_harness._cti_engine if _harness else None,
        deceiver=_harness._deceiver if _harness else None,
    )

    return web.json_response(
        {
            "session_id": session.session_id,
            "events_replayed": context["total_events"],
            "interaction_count": context["interaction_count"],
            "status": "resumed",
        }
    )


async def session_context(request: web.Request) -> web.Response:
    """Get current session context (build_context)."""
    session_id = request.match_info.get("session_id")
    if not session_id:
        return web.json_response({"error": "session_id required"}, status=400)
    if not _session_authorized(request, session_id):
        return web.json_response({"error": "session unauthorized"}, status=403)

    if _sandbox is None:
        return web.json_response({"error": "sandbox not initialized"}, status=503)
    context = _sandbox.get_session_context(session_id)
    if context is None:
        return web.json_response({"error": "session not found"}, status=404)

    return web.json_response(context)


async def session_replay(request: web.Request) -> web.Response:
    """Replay session events since a given event ID."""
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON body"}, status=400)

    session_id = data.get("session_id")
    after_event_id = data.get("after_event_id")

    if not session_id:
        return web.json_response({"error": "session_id required"}, status=400)
    if not _session_authorized(request, session_id):
        return web.json_response({"error": "session unauthorized"}, status=403)

    session = await asyncio.to_thread(Session.wake, session_id)
    events = session.replay_since(after_event_id) if after_event_id else list(session.replay())

    return web.json_response(
        {
            "session_id": session_id,
            "events": [e.to_dict() for e in events],
            "count": len(events),
        }
    )


# ── Cowrie LLM-backend bridge (OpenAI-compatible) ───────────────────────────


async def openai_chat_completions(request: web.Request) -> web.Response:
    """OpenAI-compatible /v1/chat/completions shim for cowrie's native LLM
    backend (field arm C).

    Cowrie terminates the attacker's SSH session and POSTs the conversation
    here; we map it onto the sandbox and return the VERIFIED response:

      * X-Session-Id header (set by a previous response) resumes that session;
      * otherwise the source-IP hash (or a fresh id) keys a per-attacker
        session, resumed-or-created exactly like Sandbox.handle_command does;
      * the attacker's command is the last user message; cowrie's own system
        prompt is dropped (the pipeline has its own identity);
      * each response sets X-Session-Id so the frontend pins the session;
      * on sandbox error (or a pipeline crash) this endpoint FAILS CLOSED with
        HTTP 503 ``{"error": "verified_serve_unavailable"}``: no unverified
        draft is ever served, and the failure is logged loudly. It does NOT
        synthesize a shell error body — the Cowrie front-end's reaction to a
        503 is a transport-layer behaviour that must be OBSERVED, not assumed.
        If a synthetic shell error is ever served, it must be a fixed,
        pre-approved string carrying no verification claim (empty
        ``served_response_sha256``, ``verification.passed = false``).

    Session transcripts export to RAGIN_FIELD_EXPORT_DIR as JSONL so
    collect_field_data.py can pull them without touching live session state.
    """
    data: dict[str, Any] = {}
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON body"}, status=400)

    messages = data.get("messages") or []
    if not isinstance(messages, list):
        return web.json_response({"error": "messages must be a list"}, status=400)

    user_texts = [str(m.get("content", "")) for m in messages if isinstance(m, dict) and m.get("role") == "user"]
    command = user_texts[-1].strip() if user_texts else ""
    if not command:
        # Cowrie EXEC path (non-interactive `ssh host cmd`): with empty history
        # the OpenAI-format messages carry ONLY the system context, which
        # embeds the command as "The command to execute is: <cmd>". Parse it
        # (live-smoke finding 2026-09-28: such requests 400'd and the attacker
        # saw an empty serve).
        for m in messages:
            if isinstance(m, dict) and m.get("role") == "system":
                mm = re.search(
                    r"The command to execute is:\s*(.+?)\s*$",
                    str(m.get("content", "")),
                    re.MULTILINE,
                )
                if mm:
                    command = mm.group(1).strip()
                    break
    if not command:
        return web.json_response({"error": "no user message"}, status=400)

    if _sandbox is None:
        return web.json_response({"error": "sandbox not initialized"}, status=503)

    # Continuity by content (see _resolve_bridge_session): resume the session
    # this transcript extends, else let handle_command create a fresh one.
    # X-Session-Id, when present (API callers / future frontends), wins.
    explicit_session_id = request.headers.get("X-Session-Id", "")
    transcript_session_id = _resolve_bridge_session(messages)
    if explicit_session_id and not _session_authorized(request, explicit_session_id):
        return web.json_response({"error": "session unauthorized"}, status=403)
    if transcript_session_id and not explicit_session_id:
        session_id = transcript_session_id
    else:
        session_id = explicit_session_id or f"cowrie-{int(time.time() * 1000):x}-{secrets.token_hex(4)}"
    token = _register_session(session_id) if session_id not in _SESSION_OWNERS else _SESSION_OWNERS[session_id]
    try:
        resp = await asyncio.to_thread(
            _sandbox.handle_command,
            source_ip=request.remote or "_",
            command=command,
            session_id=session_id,
        )
    except Exception:  # noqa: BLE001 — fail SAFE: a crashed pipeline must
        # still serve plausible text (a 500 here leaves the attacker with an
        # empty terminal and a honeypot tell; live-smoke finding 2026-09-28).
        logger.exception("cowrie bridge pipeline crash session=%s", session_id)
        return web.json_response(
            {"error": "verified_serve_unavailable"},
            status=503,
            headers={"X-Session-Id": session_id, "X-Session-Token": token},
        )
    _remember_bridge_session(messages, resp.session_id)

    _export_field_session(resp)

    if resp.error:
        logger.error(
            "cowrie bridge session=%s command_error=%s — returning safe transport error",
            resp.session_id,
            resp.error,
        )
        return web.json_response(
            {"error": "verified_serve_unavailable"},
            status=503,
            headers={"X-Session-Id": resp.session_id, "X-Session-Token": _SESSION_OWNERS.get(resp.session_id, "")},
        )

    return web.json_response(
        {
            "id": f"chatcmpl-{resp.session_id}-{resp.command_count}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": data.get("model", "ragin-pipeline"),
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": resp.response_text,
                        "serve_path": getattr(resp, "serve_path", None),
                        "candidate_sha256": getattr(resp, "candidate_sha256", None),
                        "served_response_sha256": getattr(resp, "served_response_sha256", None),
                        "verification_passed": (getattr(resp, "verification", None) or {}).get("passed") is True,
                        "persona_used": getattr(resp, "persona_used", None),
                        "approval": getattr(resp, "approval", None),
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        },
        headers={"X-Session-Id": resp.session_id, "X-Session-Token": _SESSION_OWNERS.get(resp.session_id, "")},
    )


def _export_field_session(resp: Any) -> None:
    """Append the served interaction to the field-export JSONL (best-effort:
    an export failure must never break the serve)."""
    try:
        out_dir = _field_export_dir()
        verification = getattr(resp, "verification", None) or {}
        row = {
            "ts": time.time(),
            "session_id": resp.session_id,
            "command_count": resp.command_count,
            "response_text": resp.response_text,
            "served_response_sha256": getattr(resp, "served_response_sha256", ""),
            "verification_passed": verification.get("passed") is True,
            "verification_issues": verification.get("issues", []),
            "serve_path": getattr(resp, "serve_path", ""),
            "candidate_sha256": getattr(resp, "candidate_sha256", ""),
            "error": resp.error,
        }
        with open(out_dir / f"{resp.session_id}.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
    except Exception:  # noqa: BLE001 — export is best-effort by design
        logger.exception("field export failed for session %s", getattr(resp, "session_id", "?"))


# ── Legacy component endpoints (backward compatible) ─────────────────────────


async def classify(request: web.Request) -> web.Response:
    """Individual classify endpoint — backward compatible with server.py."""
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON body"}, status=400)

    if _component is None or not hasattr(_component, "classify"):
        return web.json_response({"error": "chrollo not available in pipeline mode"}, status=400)

    try:
        from datetime import datetime, timezone

        from ragin.chrollo.models import SessionLog

        session_log = SessionLog(
            session_id=data.get("session_id", "unknown"),
                start_time=data.get("start_time", datetime.now(tz=timezone.utc).isoformat()),
            commands=data.get("commands", []),
            # duration_seconds/features have no dedicated SessionLog fields;
            # carry them in metadata instead of letting pydantic drop them.
            metadata={
                "duration_seconds": data.get("duration_seconds", 0),
                "features": data.get("features", {}),
            },
        )
        result = await asyncio.to_thread(_component.classify, session_log)
        return web.json_response(
            {
                "skill_level": result.skill_level.value,
                "confidence": result.confidence,
                "session_id": result.session_id,
            }
        )
    except Exception as e:
        logger.exception("classify error")
        return web.json_response({"error": str(e)}, status=500)


async def analyze(request: web.Request) -> web.Response:
    """Individual analyze endpoint — uses DonAdapter for full Phase-1 schema."""
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON body"}, status=400)

    if _component is None or not hasattr(_component, "analyze"):
        return web.json_response({"error": "don not available in pipeline mode"}, status=400)

    try:
        from ragin.cycle.adapters import DonAdapter

        attacker_input = data.get("command", data.get("attacker_input", ""))
        commands = data.get("commands", data.get("features", {}).get("commands", []))
        if not commands and attacker_input:
            commands = [attacker_input]

        session_context = {
            "session_id": data.get("session_id", "unknown"),
            "attacker_inputs": commands,
            "classification": {
                "skill_level": data.get("classification", "unknown"),
                "confidence": data.get("confidence", 0.0),
            },
            "features": data.get("features", {}),
        }
        system_responses = data.get("system_responses", data.get("session_log", []))
        if system_responses:
            session_context["system_responses"] = system_responses

        da = DonAdapter(
            gateway_url=os.environ.get("GATEWAY_URL"),
            api_key=os.environ.get("OPENROUTER_API_KEY"),
        )
        result = await asyncio.to_thread(da.analyze, attacker_input, session_context)
        return web.json_response(result)
    except Exception as e:
        logger.exception("analyze error")
        return web.json_response({"error": str(e)}, status=500)


async def deceive(request: web.Request) -> web.Response:
    """Individual deceive endpoint — backward compatible with server.py."""
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON body"}, status=400)

    if _component is None or not hasattr(_component, "generate_response"):
        return web.json_response({"error": "hisoka not available in pipeline mode"}, status=400)

    try:
        attacker_input = data.get("attacker_input", data.get("command", "ls"))
        session_context = {
            "session_id": data.get("session_id", "unknown"),
            "skill_level": data.get("skill_level", "novice"),
            "context": data.get("context", ""),
        }
        result = await asyncio.to_thread(_component.generate_response, attacker_input, session_context)
        return web.json_response(
            {
                "session_id": result.session_id,
                "response_text": result.response_text,
                "persona_used": result.persona_used,
                "engagement_score": result.engagement_score,
            }
        )
    except Exception as e:
        logger.exception("deceive error")
        return web.json_response({"error": str(e)}, status=500)


# ── Health / Metrics ─────────────────────────────────────────────────────────


async def health(request: web.Request) -> web.Response:
    report: dict[str, Any] = {
        "component": _COMPONENT_NAME,
        "status": "healthy",
        "timestamp": time.time(),
    }
    if _harness:
        report["harness"] = "active"
        report["pipeline"] = ["chrollo", "don", "hisoka"]
        report["verification"] = (
            "mandatory" if getattr(_harness, "mandatory_verification", False) else "legacy-optional"
        )
        runtime_mode = resolve_runtime_mode()
        report["runtime_mode"] = runtime_mode
        report["decision_arm"] = decision_arm_for_runtime(runtime_mode)
        report["provider"] = _provider_health()
        if laya_enabled():
            try:
                from ragin.decision.laya_runtime import get_shared_runtime

                # Provenance only: get_shared_runtime() constructs the lazy
                # runtime object; it does NOT load or hash the checkpoint.
                report["laya"] = get_shared_runtime().checkpoint_provenance()
            except Exception as exc:  # noqa: BLE001 - health must never crash
                report["laya"] = {"enabled": True, "error": exc.__class__.__name__}
    if _sandbox:
        report["active_sessions"] = len(_sandbox.get_active_sessions())
    return web.json_response(report)


async def ready(request: web.Request) -> web.Response:
    pipeline_ready = bool(_harness) if _COMPONENT_NAME == "pipeline" else bool(_component)
    return web.json_response(
        {
            "ready": pipeline_ready,
            "component": _COMPONENT_NAME,
            "pipeline_initialized": bool(_harness),
            "provider": _provider_health(),
        }
    )


async def metrics(request: web.Request) -> web.Response:
    return web.json_response({"status": "metrics placeholder"})


# ── App factory ──────────────────────────────────────────────────────────────


_PROVIDER_URL_ENV_ORDER = (
    "GATEWAY_URL",
    "RAGIN_PROVIDER_URL",
    "RAGIN_LLM_BASE_URL",
    "RAGIN_GATEWAY_URL",
    "RAGIN_HISOKA_GATEWAY_URL",
)
_PROVIDER_KEY_ENV_ORDER = (
    "RAGIN_PROVIDER_API_KEY",
    "RAGIN_HISOKA_API_KEY",
    "RAGIN_LLM_API_KEY",
    "OPENROUTER_API_KEY",
    "AZURE_OPENAI_KEY",
    "OPENAI_API_KEY",
)


def _truthy_env(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _safe_endpoint(url: str) -> str:
    """Credential-free endpoint representation for logs and errors.

    Provider URLs may carry userinfo (``user:pass@host``) or query tokens.
    Neither is safe to interpolate into an exception, a log message, or the
    unauthenticated health payload. Scheme, host, port, and path are retained;
    userinfo, query, and fragment are dropped.
    """
    try:
        parsed = urlparse(str(url))
    except Exception:
        return "[unparseable-endpoint]"
    if not parsed.scheme or not parsed.hostname:
        return "[invalid-endpoint]"
    host = parsed.hostname
    try:
        port = f":{parsed.port}" if parsed.port is not None else ""
    except ValueError:
        port = ""
    return f"{parsed.scheme}://{host}{port}{parsed.path or ''}"


def _resolve_provider_config(
    gateway_url: str | None = None,
    api_key: str | None = None,
) -> dict[str, Any]:
    """Resolve the one inference endpoint/key every adapter will use.

    Precedence (first non-empty wins):
      URL:  explicit arg -> GATEWAY_URL -> RAGIN_LLM_BASE_URL ->
            RAGIN_GATEWAY_URL -> settings ragin.cloud.gateway_url -> localhost
      KEY:  explicit arg -> RAGIN_PROVIDER_API_KEY -> RAGIN_HISOKA_API_KEY ->
            RAGIN_LLM_API_KEY -> OPENROUTER_API_KEY -> AZURE_OPENAI_KEY ->
            OPENAI_API_KEY

    The old resolver read only GATEWAY_URL/OPENROUTER_API_KEY. A local .env that
    sets only RAGIN_LLM_BASE_URL/RAGIN_LLM_API_KEY (the documented names) was
    therefore silently sent to http://localhost:8080. This resolver is static:
    it validates the URL shape but performs NO network request.
    """
    cfg = _load_config()
    ragin_cfg = cfg.get("ragin")
    configured_url = None
    if isinstance(ragin_cfg, dict):
        configured_url = (ragin_cfg.get("cloud") or {}).get("gateway_url")

    url = ""
    url_source = "default"
    candidates: list[tuple[str, str | None]] = [
        ("argument", gateway_url),
        *[(name, os.environ.get(name)) for name in _PROVIDER_URL_ENV_ORDER],
        ("settings.ragin.cloud.gateway_url", configured_url),
    ]
    for source, value in candidates:
        if isinstance(value, str) and value.strip():
            url = value.strip()
            url_source = source
            break
    if not url:
        url = "http://localhost:8080"

    key = ""
    key_source = "unconfigured"
    key_candidates: list[tuple[str, str | None]] = [
        ("argument", api_key),
        *[(name, os.environ.get(name)) for name in _PROVIDER_KEY_ENV_ORDER],
    ]
    for source, value in key_candidates:
        if isinstance(value, str) and value.strip():
            key = value.strip()
            key_source = source
            break

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise RuntimeError(
            f"invalid inference endpoint {_safe_endpoint(url)!r} (from {url_source}); expected an http(s) URL"
        )

    return {
        "gateway_url": url.rstrip("/"),
        "api_key": key,
        "url_source": url_source,
        "key_source": key_source,
        "api_key_configured": bool(key),
    }


def _preflight_provider(config: dict[str, Any]) -> None:
    """Static provider preflight. Never opens a socket; never logs the key."""
    requires_key = _truthy_env("RAGIN_REQUIRE_PROVIDER") or _truthy_env("RAGIN_PROVIDER_ENABLED")
    if requires_key and not config.get("api_key_configured"):
        raise RuntimeError(
            "RAGIN_PROVIDER_ENABLED/RAGIN_REQUIRE_PROVIDER is set but no provider API key "
            "was found in RAGIN_PROVIDER_API_KEY, RAGIN_HISOKA_API_KEY, RAGIN_LLM_API_KEY, "
            "OPENROUTER_API_KEY, AZURE_OPENAI_KEY or OPENAI_API_KEY"
        )
    logger.info(
        "Inference endpoint resolved: url=%s (source=%s) auth=%s (source=%s)",
        _safe_endpoint(str(config.get("gateway_url") or "")),
        config.get("url_source"),
        "configured" if config.get("api_key_configured") else "MISSING",
        config.get("key_source"),
    )


_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1", "0.0.0.0", "::", ""})


def _is_self_endpoint(url: str, bind_host: str, port: int) -> bool:
    """True when ``url`` resolves to the server's own listening endpoint.

    Loopback aliases (``localhost`` / ``127.0.0.1`` / ``::1``) and wildcard
    binds (``0.0.0.0`` / ``::``) are treated as the same endpoint when the
    ports match. Static only — never resolves DNS or opens a socket.
    """
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return False
    bind = (bind_host or "").strip().lower()
    url_host = parsed.hostname.strip().lower()
    same_host = url_host == bind or (bind in _LOOPBACK_HOSTS and url_host in _LOOPBACK_HOSTS)
    if not same_host:
        return False
    try:
        url_port = int(parsed.port) if parsed.port is not None else (443 if parsed.scheme == "https" else 80)
    except ValueError:
        return False
    return url_port == int(port)


def _assert_provider_not_self(config: dict[str, Any], bind_host: str, port: int) -> None:
    """Refuse a provider endpoint that is this server's own listener.

    A self-call would re-enter ``/v1/chat/completions`` while the same thread
    holds the sandbox lock and block until ``RAGIN_HISOKA_TIMEOUT``. The check
    applies to the CLI's actual bind host/port, including the built-in
    ``http://localhost:8080`` default; offline/deterministic users can set a
    non-colliding loopback endpoint (for example ``http://127.0.0.1:9``).

    This is a static equality check only: it does not resolve DNS, follow
    redirects, probe the endpoint, or detect aliases/container hostnames. The
    guard message never interpolates the URL, which may contain userinfo or a
    query token. ``create_app`` callers that have no actual listen port are not
    checked here.
    """
    url = str(config.get("gateway_url") or "")
    if _is_self_endpoint(url, bind_host, int(port)):
        raise RuntimeError(
            f"configured inference endpoint (source={config.get('url_source')}) "
            f"resolves to this server's own listener {bind_host}:{port}. Refusing a "
            "self-call that would deadlock on the sandbox lock. Set a distinct "
            "provider endpoint or a non-colliding loopback endpoint for deterministic mode."
        )


def _provider_health() -> dict[str, Any]:
    if not _PROVIDER_INFO:
        return {"configured": False}
    return {
        "configured": True,
        "gateway_url": _safe_endpoint(str(_PROVIDER_INFO.get("gateway_url") or "")),
        "url_source": _PROVIDER_INFO.get("url_source"),
        "api_key_configured": bool(_PROVIDER_INFO.get("api_key_configured")),
        "api_key_source": _PROVIDER_INFO.get("key_source"),
    }


def _init_pipeline(gateway_url: str | None = None, api_key: str | None = None) -> None:
    """Initialize the full Harness pipeline with adapter-wrapped components."""
    global _harness, _sandbox, _PROVIDER_INFO

    provider = _resolve_provider_config(gateway_url, api_key)
    _preflight_provider(provider)
    _PROVIDER_INFO = {k: v for k, v in provider.items() if k != "api_key"}
    g_url = provider["gateway_url"]
    a_key = provider["api_key"]
    runtime_mode = resolve_runtime_mode()
    decision_arm = decision_arm_for_runtime(runtime_mode)

    classifier = ChrolloAdapter(decision_arm=decision_arm)
    cti_engine = DonAdapter(gateway_url=g_url, api_key=a_key)

    # WS1 active wiring: route the authenticated provider transport through the
    # existing hisoka generator seam WITHOUT building a parallel inference
    # pipeline and WITHOUT changing the harness deceiver protocol. ProviderTransport
    # is a GatewayClient subclass that drops into ResponseGenerator._gateway; the
    # ProviderTransportAdapter then satisfies the harness Deceiver protocol
    # (generate_response(attacker_input, session_context) -> dict) by delegating to
    # the existing AdaptiveDeceiver.generate_response flow with ProviderTransport as
    # the authenticated backend for the optional LLM draft. When no non-placeholder
    # provider API key is configured, the existing HisokaAdapter path is preserved
    # and the provider path is left as an explicit, fails-closed authenticated
    # transport (ProviderUnavailableError on generate).
    deceiver: Any = None
    if runtime_mode != "RAGIN_BASELINE":
        deceiver = SubstantiveStrategyAdapter(runtime_mode)
    elif os.environ.get("RAGIN_PROVIDER_ENABLED", "").strip().lower() in ("1", "true", "yes"):
        from ragin.cycle.provider_transport import ProviderTransportAdapter

        deceiver = ProviderTransportAdapter(
            gateway_url=g_url,
            api_key=(
                os.environ.get("RAGIN_PROVIDER_API_KEY")
                or os.environ.get("RAGIN_HISOKA_API_KEY")
                or os.environ.get("RAGIN_LLM_API_KEY")
                or os.environ.get("OPENROUTER_API_KEY")
                or os.environ.get("OPENAI_API_KEY")
                or os.environ.get("AZURE_OPENAI_KEY")
            ),
        )
    else:
        deceiver = HisokaAdapter(gateway_url=g_url)

    host_path = os.environ.get("RAGIN_HOST_FICTION_PATH", "data/host_fiction.json")
    if os.path.exists(host_path):
        host_store = HostFictionStore.load(host_path)
    else:
        host_store = HostFictionStore(
            host_key=os.environ.get("RAGIN_HOST_KEY", "default-host"),
            policy=os.environ.get("RAGIN_HOST_FICTION_POLICY", "per_session"),
        )
    _harness = Harness(
        classifier=classifier,
        cti_engine=cti_engine,
        deceiver=deceiver,
        mandatory_verification=True,
        host_store=host_store,
        host_fiction_path=host_path,
        decision_arm=decision_arm,
    )

    # Sandbox uses the harness's internal _process_one for command handling
    # We override handle_command to go through the harness pipeline
    _sandbox = Sandbox(harness=_harness)

    logger.info(
        "Pipeline initialized: Chrollo → Don → Evidence Gate → Policy → Hisoka "
        "(%s, arm=%s, verification=mandatory, provider=%s auth=%s)%s",
        runtime_mode,
        decision_arm,
        _safe_endpoint(provider["gateway_url"]),
        "configured" if provider["api_key_configured"] else "MISSING",
        " + Laya decision" if laya_enabled() else "",
    )
    if laya_enabled():
        try:
            from ragin.decision.laya_runtime import get_shared_runtime

            provenance = get_shared_runtime().checkpoint_provenance()
            logger.warning(
                "Laya enabled: served checkpoint=%s model=%s revision=%s "
                "(fine_tuned_checkpoint_loaded=%s). Fine-tuned checkpoints under "
                "models/ are NOT loaded by LayaRuntime.",
                provenance.get("served_checkpoint"),
                provenance.get("model"),
                provenance.get("revision"),
                provenance.get("fine_tuned_checkpoint_loaded"),
            )
        except Exception as exc:  # noqa: BLE001 - provenance must not block startup
            logger.warning("Laya provenance unavailable: %s", exc.__class__.__name__)


def _init_component(name: str) -> None:
    """Initialize a single component (backward compatible mode)."""
    global _component, _PROVIDER_INFO
    provider = _resolve_provider_config()
    _preflight_provider(provider)
    _PROVIDER_INFO = {k: v for k, v in provider.items() if k != "api_key"}
    g_url = provider["gateway_url"]
    a_key = provider["api_key"]

    if name == "chrollo":
        from ragin.chrollo.classifier import ChrolloClassifier

        _component = ChrolloClassifier()
    elif name == "don":
        from ragin.don.rag_engine import ThreatRAGEngine

        _component = ThreatRAGEngine(gateway_url=g_url, api_key=a_key)
    elif name == "hisoka":
        from ragin.hisoka.deceiver import AdaptiveDeceiver

        _component = AdaptiveDeceiver(gateway_url=g_url)
    else:
        raise ValueError(f"Unknown component: {name}")

    logger.info("Component %s initialized (standalone mode)", name)


def create_app(mode: str = "pipeline", component: str | None = None) -> web.Application:
    """Create the aiohttp application.

    mode:
        "pipeline" — full Harness + Session + Sandbox (default)
        "standalone" — single component (backward compatible with server.py)
    """
    global _COMPONENT_NAME

    if mode not in ("pipeline", "standalone"):
        raise RuntimeError(f"unknown mode {mode!r}; expected pipeline or standalone")

    app = web.Application(
        middlewares=[mtls_middleware, auth_middleware, timing_middleware],
        client_max_size=int(os.environ.get("RAGIN_MAX_REQUEST_BYTES", str(1024 * 1024))),
    )

    # Health / readiness (always available)
    app.router.add_get("/health", health)
    app.router.add_get("/ready", ready)
    app.router.add_get("/metrics", metrics)

    _validate_security_config()
    if mode == "pipeline":
        _COMPONENT_NAME = "pipeline"
        _init_pipeline()
        # Session management endpoints
        app.router.add_post("/api/session/create", session_create)
        app.router.add_post("/api/session/command", session_command)
        app.router.add_post("/api/session/wake", session_wake)
        app.router.add_post("/api/session/replay", session_replay)
        app.router.add_get("/api/session/{session_id}/context", session_context)
        # Cowrie LLM-backend bridge (field arm C frontend calls this).
        app.router.add_post("/v1/chat/completions", openai_chat_completions)
    else:
        raise RuntimeError("standalone mode is disabled; use the mandatory verified pipeline")

    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="RAGIN v2 HTTP server")
    parser.add_argument(
        "--mode",
        choices=["pipeline", "standalone"],
        default="pipeline",
        help="pipeline = full harness (default), standalone = single component",
    )
    parser.add_argument(
        "--component",
        choices=["chrollo", "don", "hisoka"],
        default=os.environ.get("COMPONENT", "chrollo"),
        help="Component to run in standalone mode",
    )
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8080")))
    args = parser.parse_args()

    logging.basicConfig(
        level=LOG_LEVEL,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    bind_host = os.environ.get("RAGIN_BIND_HOST", "127.0.0.1")
    # Static self-endpoint guard BEFORE the pipeline builds any HTTP client.
    # Uses the actual listening port; exempts the unconfigured default.
    _assert_provider_not_self(_resolve_provider_config(), bind_host, args.port)
    app = create_app(mode=args.mode, component=args.component)
    _validate_security_config()
    ssl_context = build_server_context_from_env()
    if os.environ.get("RAGIN_MTLS_REQUIRED", "0").strip().lower() in {"1", "true", "yes", "on"} and ssl_context is None:
        raise MTLSConfigError("mTLS is required but no server context was configured")
    logger.info("Starting RAGIN v2 server (mode=%s) on %s:%d", args.mode, bind_host, args.port)
    web.run_app(app, host=bind_host, port=args.port, ssl_context=ssl_context)


if __name__ == "__main__":
    main()
