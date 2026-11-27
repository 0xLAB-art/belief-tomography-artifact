"""Tests for ragin/server_v2.py — pipeline and standalone endpoints."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from aiohttp.test_utils import TestClient, TestServer

from ragin.cycle.sandbox import SandboxResponse
from ragin.cycle.session import Session

# ── Helpers ───────────────────────────────────────────────────────────────────


def _mock_sandbox() -> MagicMock:
    sb = MagicMock()
    sb.create_session.return_value = SandboxResponse(session_id="abc123", response_text="", command_count=0)
    sb.handle_command.return_value = SandboxResponse(
        session_id="abc123",
        response_text="root@honeypot:~$ ",
        command_count=1,
        event_count=3,
    )
    sb.get_session_context.return_value = {
        "session_id": "abc123",
        "attacker_inputs": ["whoami"],
        "system_responses": ["root"],
        "total_events": 3,
        "interaction_count": 1,
        "source_ip": "10.0.0.1",
    }
    sb.get_active_sessions.return_value = {"abc123": {}}
    return sb


def _mock_harness() -> MagicMock:
    h = MagicMock()
    h._classifier = MagicMock()
    h._cti_engine = MagicMock()
    h._deceiver = MagicMock()
    return h


@pytest.fixture
async def client():
    """Create test client with mocked server_v2 globals.

    Suppresses _init_pipeline so it doesn't overwrite our mocks.
    """
    import ragin.server_v2 as sv2

    orig_harness = sv2._harness
    orig_sandbox = sv2._sandbox
    orig_component = sv2._component
    orig_comp_name = sv2._COMPONENT_NAME
    orig_api_key = sv2.API_KEY
    orig_require_auth = sv2.REQUIRE_AUTH

    # Force API_KEY empty so auth middleware never blocks test requests.
    # When pytest loads .env via dotenv, the module-level API_KEY becomes
    # non-empty and the middleware returns 401 on every non-health route.
    sv2.API_KEY = ""
    sv2.REQUIRE_AUTH = False

    # Patch _init_pipeline to prevent it from creating real components
    with patch.object(sv2, "_init_pipeline"):
        app = sv2.create_app(mode="pipeline")

    # Now set our mocks AFTER create_app (so routes are registered but
    # handlers will see our mocks at request time)
    sv2._harness = _mock_harness()
    sv2._sandbox = _mock_sandbox()
    sv2._component = None
    sv2._COMPONENT_NAME = "pipeline"

    server = TestServer(app)
    client = TestClient(server)
    await client.start_server()
    yield client
    await client.close()

    sv2._harness = orig_harness
    sv2._sandbox = orig_sandbox
    sv2._component = orig_component
    sv2._COMPONENT_NAME = orig_comp_name
    sv2.API_KEY = orig_api_key
    sv2.REQUIRE_AUTH = orig_require_auth


# ── Health / Readiness ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_health(client: TestClient) -> None:
    resp = await client.get("/health")
    assert resp.status == 200
    data = await resp.json()
    assert data["component"] == "pipeline"
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_ready(client: TestClient) -> None:
    resp = await client.get("/ready")
    assert resp.status == 200
    data = await resp.json()
    assert data["ready"] is True


@pytest.mark.asyncio
async def test_metrics(client: TestClient) -> None:
    resp = await client.get("/metrics")
    assert resp.status == 200


# ── Session endpoints ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_session_create(client: TestClient) -> None:
    resp = await client.post(
        "/api/session/create",
        json={"source_ip": "10.0.0.5", "max_commands": 500},
    )
    assert resp.status == 200
    data = await resp.json()
    assert data["session_id"] == "abc123"
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_session_create_default(client: TestClient) -> None:
    resp = await client.post("/api/session/create", json={})
    assert resp.status == 200
    data = await resp.json()
    assert data["session_id"] == "abc123"


@pytest.mark.asyncio
async def test_session_command(client: TestClient) -> None:
    resp = await client.post(
        "/api/session/command",
        json={"session_id": "abc123", "command": "whoami"},
    )
    assert resp.status == 200
    data = await resp.json()
    assert data["session_id"] == "abc123"
    assert data["response_text"] == "root@honeypot:~$ "
    assert data["command_count"] == 1
    assert data["event_count"] == 3


@pytest.mark.asyncio
async def test_session_command_missing_session_id(client: TestClient) -> None:
    resp = await client.post(
        "/api/session/command",
        json={"command": "whoami"},
    )
    assert resp.status == 400
    data = await resp.json()
    assert "session_id required" in data["error"]


@pytest.mark.asyncio
async def test_session_command_missing_command(client: TestClient) -> None:
    resp = await client.post(
        "/api/session/command",
        json={"session_id": "abc123"},
    )
    assert resp.status == 400
    data = await resp.json()
    assert "command required" in data["error"]


@pytest.mark.asyncio
async def test_session_command_invalid_json(client: TestClient) -> None:
    resp = await client.post(
        "/api/session/command",
        data="not json",
        headers={"Content-Type": "text/plain"},
    )
    assert resp.status == 400


@pytest.mark.asyncio
async def test_session_context(client: TestClient) -> None:
    resp = await client.get("/api/session/abc123/context")
    assert resp.status == 200
    data = await resp.json()
    assert data["session_id"] == "abc123"
    assert "attacker_inputs" in data


@pytest.mark.asyncio
async def test_session_context_not_found(client: TestClient) -> None:
    import ragin.server_v2 as sv2

    sv2._sandbox.get_session_context.return_value = None
    resp = await client.get("/api/session/unknown/context")
    assert resp.status == 404


@pytest.mark.asyncio
async def test_session_replay(client: TestClient) -> None:
    mock_session = MagicMock()
    mock_session.session_id = "abc123"
    mock_event = MagicMock()
    mock_event.to_dict.return_value = {
        "event_id": "aabbccdd1122",
        "timestamp": "2026-01-01T00:00:00",
        "event_type": "attacker_input",
        "data": {"command": "whoami"},
    }
    mock_session.replay.return_value = [mock_event]

    with patch.object(Session, "wake", return_value=mock_session):
        resp = await client.post(
            "/api/session/replay",
            json={"session_id": "abc123"},
        )
    assert resp.status == 200
    data = await resp.json()
    assert data["session_id"] == "abc123"
    assert isinstance(data["events"], list)
    assert data["count"] == 1


@pytest.mark.asyncio
async def test_session_replay_missing_session_id(client: TestClient) -> None:
    resp = await client.post(
        "/api/session/replay",
        json={},
    )
    assert resp.status == 400


@pytest.mark.asyncio
async def test_session_wake(client: TestClient) -> None:
    import ragin.server_v2 as sv2

    mock_session = MagicMock()
    mock_session.session_id = "abc123"
    mock_context = {
        "total_events": 5,
        "interaction_count": 2,
    }

    with patch.object(sv2.Harness, "wake", return_value=(mock_session, mock_context), create=True):
        resp = await client.post(
            "/api/session/wake",
            json={"session_id": "abc123"},
        )
    assert resp.status == 200
    data = await resp.json()
    assert data["session_id"] == "abc123"
    assert data["status"] == "resumed"


@pytest.mark.asyncio
async def test_session_wake_missing_session_id(client: TestClient) -> None:
    resp = await client.post(
        "/api/session/wake",
        json={},
    )
    assert resp.status == 400


@pytest.mark.asyncio
async def test_session_command_uses_attacker_input_alias(client: TestClient) -> None:
    resp = await client.post(
        "/api/session/command",
        json={"session_id": "abc123", "attacker_input": "id"},
    )
    assert resp.status == 200
    data = await resp.json()
    assert data["session_id"] == "abc123"


# ── Cowrie LLM-backend bridge (/v1/chat/completions, field arm C) ────────────


@pytest.fixture(autouse=True)
def _isolate_field_export(tmp_path, monkeypatch):
    """Bridge responses export JSONL transcripts; keep test runs from writing
    residue into the repo's data/field/ directory."""
    import ragin.server_v2 as sv2

    monkeypatch.setattr(sv2, "_FIELD_EXPORT", tmp_path / "field-export")


async def _post_chat(client: TestClient, messages: list, **extra) -> object:
    payload = {"model": "field-frontend", "messages": messages, **extra}
    return await client.post("/v1/chat/completions", json=payload)


@pytest.mark.asyncio
async def test_cowrie_bridge_serves_verified_response(client: TestClient) -> None:
    import ragin.server_v2 as sv2

    messages = [
        {"role": "system", "content": "cowrie system prompt"},
        {"role": "user", "content": "uname -a"},
    ]
    resp = await _post_chat(client, messages)
    assert resp.status == 200
    data = await resp.json()
    assert data["choices"][0]["message"]["content"] == "root@honeypot:~$ "
    assert data["choices"][0]["finish_reason"] == "stop"
    # Session pinning header for API callers.
    assert resp.headers["X-Session-Id"] == "abc123"
    # The sandbox saw the attacker's command, not cowrie's system prompt.
    sv2._sandbox.handle_command.assert_called_once()
    assert sv2._sandbox.handle_command.call_args.kwargs["command"] == "uname -a"


@pytest.mark.asyncio
async def test_cowrie_bridge_transcript_extension_gets_fresh_session(client: TestClient) -> None:
    """UPDATED 2026-10-24 (pentest finding 2-HIGH remediation): the old
    content-based transcript-prefix resume is REMOVED — it let any caller who
    knew a victim's first commands resume her session AND receive its
    X-Session-Token. Continuity is now explicit only (X-Session-Id +
    X-Session-Token), so a grown transcript from a headerless stock-cowrie
    caller maps onto a FRESH session and never onto the previous one."""
    import ragin.server_v2 as sv2

    sv2._sandbox.reset_mock()
    msgs = [{"role": "user", "content": "uname -a"}]
    r1 = await _post_chat(client, msgs)
    sid1 = (await r1.json())["id"]
    grown = msgs + [
        {"role": "assistant", "content": "root@honeypot:~$ "},
        {"role": "user", "content": "whoami"},
    ]
    r2 = await _post_chat(client, grown)
    second_call_sid = sv2._sandbox.handle_command.call_args.kwargs["session_id"]
    # The transcript prefix is no longer an ownership proof: the second request
    # must NOT resume the session the first response pointed at. (This file's
    # mock pins SandboxResponse.session_id to "abc123", so only the session_id
    # actually handed to the pipeline is meaningful here.)
    assert second_call_sid != "abc123"
    # Each fresh session still gets its own id in the chatcmpl id (unchanged).
    assert sid1.startswith("chatcmpl-")


@pytest.mark.asyncio
async def test_cowrie_bridge_divergent_transcript_gets_fresh_session(client: TestClient) -> None:
    import ragin.server_v2 as sv2

    sv2._sandbox.reset_mock()
    # A brand-new single-message transcript after a previous session: the
    # prefix map has no matching prefix -> a fresh session id is minted and
    # passed to handle_command.
    await _post_chat(client, [{"role": "user", "content": "totally new session"}])
    sid = sv2._sandbox.handle_command.call_args.kwargs["session_id"]
    assert sid and sid != "abc123"


@pytest.mark.asyncio
async def test_cowrie_bridge_explicit_session_header_wins(client: TestClient) -> None:
    import ragin.server_v2 as sv2

    sv2._sandbox.reset_mock()
    resp = await client.post(
        "/v1/chat/completions",
        json={"model": "field-frontend", "messages": [{"role": "user", "content": "id"}]},
        headers={"X-Session-Id": "cowrie-explicit"},
    )
    assert resp.status == 200
    assert sv2._sandbox.handle_command.call_args.kwargs["session_id"] == "cowrie-explicit"


@pytest.mark.asyncio
async def test_cowrie_bridge_returns_safe_transport_error_on_sandbox_error(client: TestClient) -> None:
    import ragin.server_v2 as sv2

    sv2._sandbox.handle_command.side_effect = None
    sv2._sandbox.handle_command.return_value = SandboxResponse(
        session_id="abc123", response_text="", command_count=1, event_count=1, error="pipeline exploded"
    )
    resp = await _post_chat(client, [{"role": "user", "content": "ls"}])
    assert resp.status == 503
    data = await resp.json()
    assert data == {"error": "verified_serve_unavailable"}


@pytest.mark.asyncio
async def test_cowrie_bridge_rejects_missing_user_message(client: TestClient) -> None:
    resp = await _post_chat(client, [{"role": "system", "content": "only a system prompt"}])
    assert resp.status == 400


@pytest.mark.asyncio
async def test_cowrie_bridge_rejects_invalid_json(client: TestClient) -> None:
    resp = await client.post("/v1/chat/completions", data="not json", headers={"Content-Type": "application/json"})
    assert resp.status == 400


@pytest.mark.asyncio
async def test_cowrie_bridge_requires_auth_when_api_key_set(client: TestClient) -> None:
    import ragin.server_v2 as sv2

    orig = sv2.API_KEY
    sv2.API_KEY = "sekrit"
    try:
        # Bearer (cowrie-style) is accepted by the same middleware.
        ok = await client.post(
            "/v1/chat/completions",
            json={"messages": [{"role": "user", "content": "ls"}]},
            headers={"Authorization": "Bearer sekrit"},
        )
        assert ok.status == 200
        # Wrong key -> 401.
        bad = await client.post(
            "/v1/chat/completions",
            json={"messages": [{"role": "user", "content": "ls"}]},
            headers={"Authorization": "Bearer wrong"},
        )
        assert bad.status == 401
    finally:
        sv2.API_KEY = orig
