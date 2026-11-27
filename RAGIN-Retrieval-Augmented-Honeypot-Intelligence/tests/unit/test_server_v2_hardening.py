"""Regression tests for the server_v2 pentest-remediation hardening.

Findings covered (references are the pentest numbering used in the fix):
  * 2-HIGH  — session theft via transcript-prefix: content-based continuity is
    REMOVED; no token is ever minted/returned through a transcript-resume path;
    any resume of an owned session requires its X-Session-Token.
  * 3-MED   — /health and /ready answer ``{"ok": true}`` to unauthenticated
    callers; the rich payload is only for API-key holders.
  * 4-MED   — the unbounded ``_TRANSCRIPT_MAP`` (16.8 GB) is gone entirely.
  * 5b-MED  — bridge session creation is rate-limited per source_ip (429).
  * 6b-MED  — session_command pipeline crash returns 503
    verified_serve_unavailable, not a raw 500.
  * 8-LOW   — _validate_security_config always builds the TLS context, so a
    half-prepared plaintext boot fails closed.
  * 9-LOW   — API-key comparisons use constant-time hmac.compare_digest.
  * 10-LOW  — application/json content-type enforced; oversized bodies are 413;
    legacy endpoint errors are generic (no str(e) leakage).
"""

from __future__ import annotations

import inspect
import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from aiohttp.test_utils import TestClient, TestServer

from ragin.cycle.sandbox import SandboxResponse

# ── Fixtures / helpers ────────────────────────────────────────────────────────


def _mock_harness() -> MagicMock:
    h = MagicMock()
    h._classifier = MagicMock()
    h._cti_engine = MagicMock()
    h._deceiver = MagicMock()
    return h


def _echo_sandbox() -> MagicMock:
    """Sandbox mock that echoes the requested session_id, so the bridge's
    token-discipline code paths (mint on creation, never on resume) are
    exercised against real ids."""
    sb = MagicMock()
    sb.create_session.return_value = SandboxResponse(session_id="abc123", response_text="", command_count=0)

    def _handle(*args: Any, **kwargs: Any) -> SandboxResponse:
        return SandboxResponse(
            session_id=kwargs.get("session_id", "abc123"),
            response_text="root@honeypot:~$ ",
            command_count=1,
            event_count=1,
        )

    sb.handle_command.side_effect = _handle
    sb.get_session_context.return_value = {"session_id": "abc123"}
    sb.get_active_sessions.return_value = {}
    return sb


@pytest.fixture(autouse=True)
def _isolate_bridge_state(tmp_path, monkeypatch):
    """Per-test isolation of module-level mutable state: bridge buckets,
    session ownership, and the field-export directory."""
    import ragin.server_v2 as sv2

    monkeypatch.setattr(sv2, "_FIELD_EXPORT", tmp_path / "field-export")
    sv2._SESSION_OWNERS.clear()
    sv2._BRIDGE_SESSION_BUCKETS.clear()
    yield
    sv2._SESSION_OWNERS.clear()
    sv2._BRIDGE_SESSION_BUCKETS.clear()


@pytest.fixture
async def client():
    """Test client with mocked pipeline globals, auth OFF (dev posture)."""
    import ragin.server_v2 as sv2

    orig = (
        sv2._harness,
        sv2._sandbox,
        sv2._component,
        sv2._COMPONENT_NAME,
        sv2.API_KEY,
        sv2.REQUIRE_AUTH,
        sv2._PROVIDER_INFO,
    )
    # Force auth off so middleware never blocks test requests (same pattern as
    # tests/unit/test_server_v2.py).
    sv2.API_KEY = ""
    sv2.REQUIRE_AUTH = False
    with patch.object(sv2, "_init_pipeline"):
        app = sv2.create_app(mode="pipeline")
    sv2._harness = _mock_harness()
    sv2._sandbox = _echo_sandbox()
    sv2._component = None
    sv2._COMPONENT_NAME = "pipeline"

    server = TestServer(app)
    c = TestClient(server)
    await c.start_server()
    yield c
    await c.close()

    (
        sv2._harness,
        sv2._sandbox,
        sv2._component,
        sv2._COMPONENT_NAME,
        sv2.API_KEY,
        sv2.REQUIRE_AUTH,
        sv2._PROVIDER_INFO,
    ) = orig


async def _post_chat(client: TestClient, messages: list, **extra: Any):
    payload = {"model": "field-frontend", "messages": messages, **extra}
    return await client.post("/v1/chat/completions", json=payload)


# ── 2-HIGH: transcript-prefix session theft ───────────────────────────────────


@pytest.mark.asyncio
async def test_resume_by_transcript_never_grants_prior_session_token(client: TestClient) -> None:
    """The pentest kill-chain: attacker replays the victim's first command,
    extends the transcript, and receives her session token. Content is no
    longer an ownership proof: the extending request gets a fresh session and
    the victim's token is never emitted again."""
    import ragin.server_v2 as sv2

    msgs = [{"role": "user", "content": "ls -la"}]
    r1 = await _post_chat(client, msgs)
    assert r1.status == 200
    victim_sid = r1.headers["X-Session-Id"]
    victim_token = r1.headers["X-Session-Token"]
    assert victim_sid and victim_token, "creator must receive the session token once"

    grown = msgs + [
        {"role": "assistant", "content": "out"},
        {"role": "user", "content": "whoami"},
    ]
    r2 = await _post_chat(client, grown)
    assert r2.status == 200
    # The extended transcript did NOT attach to the victim's session...
    assert r2.headers["X-Session-Id"] != victim_sid
    assert sv2._sandbox.handle_command.call_args.kwargs["session_id"] != victim_sid
    # ...and the victim's token was not re-emitted to this caller.
    assert r2.headers.get("X-Session-Token", "") != victim_token
    # Victim ownership record untouched.
    assert sv2._SESSION_OWNERS[victim_sid] == victim_token


@pytest.mark.asyncio
async def test_resume_by_transcript_creates_fresh_session_not_prior_one(client: TestClient) -> None:
    """Even with an EXACT known transcript (no extension), a headerless request
    mints a new session: the prefix map is gone, so there is no content-based
    resume path at all."""
    import ragin.server_v2 as sv2

    msgs = [{"role": "user", "content": "uname -a"}]
    r1 = await _post_chat(client, msgs)
    assert r1.status == 200
    first_sid = r1.headers["X-Session-Id"]

    r2 = await _post_chat(client, list(msgs))
    assert r2.status == 200
    assert r2.headers["X-Session-Id"] != first_sid
    assert sv2._sandbox.handle_command.call_args.kwargs["session_id"] != first_sid


@pytest.mark.asyncio
async def test_resume_requires_session_token_when_owned(client: TestClient) -> None:
    """Pentest 2-HIGH/c: any resume of an owned session requires its token.
    Without it — or with a forged one — the bridge answers 403; with the right
    token it resumes and still never re-emits the token."""
    import ragin.server_v2 as sv2

    sv2.REQUIRE_AUTH = True
    sv2.API_KEY = "k" * 32
    auth = {"Authorization": "Bearer " + sv2.API_KEY}
    payload = {"model": "t", "messages": [{"role": "user", "content": "id"}]}

    r1 = await client.post("/v1/chat/completions", json=payload, headers=auth)
    assert r1.status == 200
    sid = r1.headers["X-Session-Id"]
    tok = r1.headers["X-Session-Token"]

    no_token = await client.post(
        "/v1/chat/completions", json=payload, headers={**auth, "X-Session-Id": sid}
    )
    assert no_token.status == 403

    forged = await client.post(
        "/v1/chat/completions",
        json=payload,
        headers={**auth, "X-Session-Id": sid, "X-Session-Token": "forged-token"},
    )
    assert forged.status == 403

    good = await client.post(
        "/v1/chat/completions",
        json=payload,
        headers={**auth, "X-Session-Id": sid, "X-Session-Token": tok},
    )
    assert good.status == 200
    assert good.headers.get("X-Session-Token", "") == "", "resume must never re-emit the token"


@pytest.mark.asyncio
async def test_explicit_session_adoption_grants_token_once(client: TestClient) -> None:
    """A caller naming a brand-new X-Session-Id adopts it and receives the
    token exactly once; later requests naming it do not get the token again."""
    import ragin.server_v2 as sv2

    payload = {"model": "t", "messages": [{"role": "user", "content": "id"}]}
    r1 = await client.post(
        "/v1/chat/completions", json=payload, headers={"X-Session-Id": "cowrie-explicit"}
    )
    assert r1.status == 200
    assert r1.headers["X-Session-Id"] == "cowrie-explicit"
    tok = r1.headers["X-Session-Token"]
    assert tok

    r2 = await client.post(
        "/v1/chat/completions", json=payload, headers={"X-Session-Id": "cowrie-explicit"}
    )
    assert r2.status == 200
    assert r2.headers.get("X-Session-Token", "") == ""
    assert sv2._SESSION_OWNERS["cowrie-explicit"] == tok


def test_transcript_prefix_map_removed() -> None:
    """Pentest 4-MED: the unbounded, content-sized transcript map (16.8 GB
    hazard) is removed at the source rather than merely byte-bounded, because
    2-HIGH/б removes content-based continuity entirely."""
    import ragin.server_v2 as sv2

    for name in (
        "_TRANSCRIPT_MAP",
        "_TRANSCRIPT_MAP_MAX",
        "_messages_key",
        "_resolve_bridge_session",
        "_remember_bridge_session",
    ):
        assert not hasattr(sv2, name), f"{name} must be gone"


# ── 5b-MED: per-source_ip session-creation rate limit ─────────────────────────


@pytest.mark.asyncio
async def test_bridge_session_creation_rate_limited(client: TestClient, monkeypatch) -> None:
    import ragin.server_v2 as sv2

    monkeypatch.setattr(sv2, "_SESSION_CREATE_BURST", 2.0)
    monkeypatch.setattr(sv2, "_SESSION_CREATE_REFILL_PER_S", 0.0)

    for i in range(2):
        r = await _post_chat(client, [{"role": "user", "content": f"cmd-{i}"}])
        assert r.status == 200, f"request {i} within burst must pass"

    flooded = await _post_chat(client, [{"role": "user", "content": "third"}])
    assert flooded.status == 429
    assert "Retry-After" in flooded.headers
    body = await flooded.json()
    assert body["error"] == "rate_limited"
    # Polite response: no internals beyond the error/detail strings.
    assert set(body) <= {"error", "detail"}

    # Explicit resume is NOT throttled by the creation bucket.
    resumed = await client.post(
        "/v1/chat/completions",
        json={"model": "t", "messages": [{"role": "user", "content": "id"}]},
        headers={"X-Session-Id": "pre-existing-id"},
    )
    assert resumed.status == 200


# ── 3-MED: /health and /ready minimal for unauthenticated callers ────────────


@pytest.mark.asyncio
async def test_health_and_ready_without_key_are_minimal(client: TestClient) -> None:
    import ragin.server_v2 as sv2

    sv2.REQUIRE_AUTH = True
    sv2.API_KEY = "k" * 32

    anon_health = await client.get("/health")
    assert anon_health.status == 200
    assert await anon_health.json() == {"ok": True}

    anon_ready = await client.get("/ready")
    assert anon_ready.status == 200
    assert await anon_ready.json() == {"ok": True}


@pytest.mark.asyncio
async def test_health_and_ready_rich_payload_behind_key(client: TestClient) -> None:
    import ragin.server_v2 as sv2

    sv2.REQUIRE_AUTH = True
    sv2.API_KEY = "k" * 32
    headers = {"X-API-Key": sv2.API_KEY}

    health = await client.get("/health", headers=headers)
    assert health.status == 200
    data = await health.json()
    assert data["ok"] is True
    assert data["component"] == "pipeline"
    assert data["status"] == "healthy"

    ready = await client.get("/ready", headers=headers)
    assert ready.status == 200
    rdata = await ready.json()
    assert rdata["ready"] is True
    assert "provider" in rdata


# ── 10-LOW: body hardening (413 + content-type) ───────────────────────────────


@pytest.mark.asyncio
async def test_oversized_payload_returns_413(monkeypatch) -> None:
    import ragin.server_v2 as sv2

    monkeypatch.setenv("RAGIN_MAX_REQUEST_BYTES", "1024")
    monkeypatch.setattr(sv2, "REQUIRE_AUTH", False)
    monkeypatch.setattr(sv2, "API_KEY", "")
    with patch.object(sv2, "_init_pipeline"):
        app = sv2.create_app(mode="pipeline")

    server = TestServer(app)
    c = TestClient(server)
    await c.start_server()
    try:
        big_body = json.dumps({"messages": [{"role": "user", "content": "x" * 8192}]})
        resp = await c.post(
            "/v1/chat/completions",
            data=big_body,
            headers={"Content-Type": "application/json"},
        )
        assert resp.status == 413, await resp.text()
        body = await resp.json()
        assert body == {"error": "request body too large"}
    finally:
        await c.close()


@pytest.mark.asyncio
async def test_non_json_content_type_is_rejected(client: TestClient) -> None:
    resp = await client.post(
        "/v1/chat/completions",
        data='{"messages": [{"role": "user", "content": "ls"}]}',
        headers={"Content-Type": "text/plain"},
    )
    assert resp.status == 400
    resp2 = await client.post(
        "/api/session/command",
        data="{}",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert resp2.status == 400


# ── 9-LOW: constant-time secret comparisons ───────────────────────────────────


def test_constant_time_key_comparison_is_used() -> None:
    """Both the API-key paths and the session-token path must compare through
    the hmac.compare_digest helper (no plain == on secrets)."""
    import ragin.server_v2 as sv2

    src = inspect.getsource(sv2._consteq)
    assert "compare_digest" in src
    # Behavioural sanity of the helper itself.
    assert sv2._consteq("same", "same") is True
    assert sv2._consteq("a", "b") is False
    # Route checks: no direct == on secrets in the two authorizers.
    assert "_consteq(" in inspect.getsource(sv2._request_authorized)
    assert "_consteq(" in inspect.getsource(sv2._session_authorized)
    assert "== API_KEY" not in inspect.getsource(sv2._request_authorized)


# ── 6b-MED: session_command pipeline crash → 503, not raw 500 ────────────────


@pytest.mark.asyncio
async def test_session_command_pipeline_crash_returns_503_not_500(client: TestClient) -> None:
    import ragin.server_v2 as sv2

    sv2._sandbox.handle_command.side_effect = RuntimeError("pipeline exploded: internal detail")
    resp = await client.post(
        "/api/session/command", json={"session_id": "abc123", "command": "whoami"}
    )
    assert resp.status == 503
    body = await resp.json()
    assert body == {"error": "verified_serve_unavailable"}
    assert "exploded" not in json.dumps(body)


# ── 8-LOW: TLS context built unconditionally at validation time ──────────────


def test_validate_security_config_builds_tls_context_unconditionally(monkeypatch) -> None:
    import ragin.server_v2 as sv2

    for name in (
        "RAGIN_MTLS_REQUIRED",
        "RAGIN_MTLS_ALLOWED_IDENTITIES",
        "RAGIN_MTLS_CERT_FILE",
        "RAGIN_MTLS_KEY_FILE",
        "RAGIN_MTLS_CA_FILE",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(sv2, "REQUIRE_AUTH", True)
    monkeypatch.setattr(sv2, "API_KEY", "k" * 32)

    calls: list[int] = []

    def _fake_build():
        calls.append(1)
        return None

    monkeypatch.setattr(sv2, "build_server_context_from_env", _fake_build)
    sv2._validate_security_config()
    assert calls == [1], "build_server_context_from_env must run even without mTLS required"


def test_plaintext_boot_with_half_prepared_tls_vars_fails_closed(monkeypatch) -> None:
    """Pentest 8-LOW: cert variables set while RAGIN_MTLS_REQUIRED is disabled
    (a half-prepared plaintext boot) must fail during validation, matching
    main()'s boot-time behaviour."""
    import ragin.server_v2 as sv2
    from ragin.transport.mtls import MTLSConfigError

    monkeypatch.delenv("RAGIN_MTLS_REQUIRED", raising=False)
    monkeypatch.delenv("RAGIN_MTLS_ALLOWED_IDENTITIES", raising=False)
    monkeypatch.delenv("RAGIN_MTLS_KEY_FILE", raising=False)
    monkeypatch.delenv("RAGIN_MTLS_CA_FILE", raising=False)
    monkeypatch.setenv("RAGIN_MTLS_CERT_FILE", "/nonexistent/cert.pem")
    monkeypatch.setattr(sv2, "REQUIRE_AUTH", True)
    monkeypatch.setattr(sv2, "API_KEY", "k" * 32)

    with pytest.raises(MTLSConfigError):
        sv2._validate_security_config()


# ── 10-LOW: legacy component errors are generic ───────────────────────────────


@pytest.mark.asyncio
async def test_legacy_component_error_responses_are_generic(monkeypatch) -> None:
    """classify/analyze/deceive must not echo str(e) — internal endpoints and
    exception text stay out of the response body (logged instead)."""
    import ragin.server_v2 as sv2

    comp = MagicMock()
    comp.classify.side_effect = RuntimeError("gateway=http://10.9.9.9:8080 key=sk-secret")
    comp.generate_response.side_effect = RuntimeError("secret-deceiver-detail")
    monkeypatch.setattr(sv2, "_component", comp)

    async def _body(_request: Any) -> dict:
        return {}

    monkeypatch.setattr(sv2, "_read_json_body", _body)

    resp = await sv2.classify(MagicMock())
    assert resp.status == 500
    assert json.loads(resp.text) == {"error": "internal error"}

    resp2 = await sv2.deceive(MagicMock())
    assert resp2.status == 500
    assert json.loads(resp2.text) == {"error": "internal error"}

    with patch("ragin.cycle.adapters.DonAdapter", side_effect=RuntimeError("secret-don-detail")):
        resp3 = await sv2.analyze(MagicMock())
    assert resp3.status == 500
    assert json.loads(resp3.text) == {"error": "internal error"}
