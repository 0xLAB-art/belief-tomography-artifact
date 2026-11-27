from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock, patch

import pytest
from aiohttp.test_utils import TestClient, TestServer

from ragin.cycle.harness import Harness
from ragin.cycle.hitl import ApprovalGateway, ApprovalLevel
from ragin.cycle.sandbox import Sandbox, SandboxConfig
from ragin.cycle.session import EventType, Session
from ragin.graph.host_fiction import HostFictionStore


class FakeClassifier:
    def classify(self, attacker_input, session_context):
        return {"skill_level": "novice", "confidence": 1.0}


class FakeCti:
    def analyze(self, attacker_input, session_context):
        return {"threat_summary": "", "recommendations": [], "extracted_techniques": []}


class FakeDeceiver:
    def __init__(self, responses):
        self.responses = list(responses)

    def generate_response(self, attacker_input, session_context):
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return {"response_text": response, "persona_used": "test"}


class LabeledDeceiver:
    def generate_response(self, attacker_input, session_context):
        return {
            "response_text": "webapp@web-srv-01:~$ provenance",
            "persona_used": "test",
            "serve_path": "TEMPLATE_FALLBACK_VERIFIED",
        }


class SequenceVerifier:
    def __init__(self, decisions):
        self.decisions = list(decisions)
        self.calls = []

    def verify(self, response, session_context):
        self.calls.append(response.get("response_text", ""))
        decision = self.decisions.pop(0) if self.decisions else False
        if isinstance(decision, BaseException):
            raise decision
        return {"passed": decision, "issues": [] if decision else ["fixture_rejected"], "deterministic": True}


def make_harness(tmp_path, responses, decisions, *, retries=0, approval_gateway=None, verifier_missing=False, host_path=None):
    verifier = None if verifier_missing else SequenceVerifier(decisions)
    harness = Harness(
        classifier=FakeClassifier(),
        cti_engine=FakeCti(),
        deceiver=FakeDeceiver(responses),
        verifier=verifier,
        mandatory_verification=True,
        max_retries=retries,
        host_store=HostFictionStore("test-host", policy="per_session"),
        host_fiction_path=host_path,
        approval_gateway=approval_gateway,
    )
    if verifier_missing:
        harness._verifier = None
    return harness


def run(harness, tmp_path, command="whoami"):
    session = Session.create(source_ip="127.0.0.1", session_dir=str(tmp_path))
    return session, harness.process(session, command)


def test_no_verifier_configured_cannot_serve(tmp_path):
    harness = make_harness(tmp_path, ["untrusted"], [], verifier_missing=True)
    session, result = run(harness, tmp_path)
    assert result.response_text == ""
    assert result.error == "verified_serve_unavailable"
    assert not [event for event in session.replay() if event.event_type == EventType.SYSTEM_RESPONSE]


def test_rejected_candidate_is_not_served_or_committed(tmp_path):
    harness = make_harness(tmp_path, ["hostname web-srv-01.corp.local"], [False, False])
    session = Session.create(source_ip="127.0.0.1", session_dir=str(tmp_path))
    harness.fiction(session.session_id)
    baseline = [fact for fact in harness.fiction(session.session_id).facts()]
    result = harness.process(session, "hostname")
    assert baseline
    assert result.response_text == ""
    assert harness.fiction(session.session_id).facts() == baseline
    assert not [event for event in session.replay() if event.event_type == EventType.SYSTEM_RESPONSE]


def test_verifier_exception_fails_closed(tmp_path):
    harness = make_harness(tmp_path, ["candidate", "fallback"], [RuntimeError("boom"), RuntimeError("boom")])
    _, result = run(harness, tmp_path)
    assert result.response_text == ""
    assert result.error == "verified_serve_unavailable"


def test_retry_exhaustion_uses_verified_fallback(tmp_path):
    harness = make_harness(tmp_path, ["bad", "bad"], [False, False, True], retries=1)
    session, result = run(harness, tmp_path)
    assert result.response_text
    assert result.verification["serve_path"] == "FALLBACK_VERIFIED"
    served = [event.data["text"] for event in session.replay() if event.event_type == EventType.SYSTEM_RESPONSE]
    assert served == [result.response_text]
    assert "bad" not in served[0]


def test_candidate_provenance_label_survives_commit(tmp_path):
    harness = make_harness(tmp_path, [], [True])
    harness._deceiver = LabeledDeceiver()
    _, result = run(harness, tmp_path, command="echo provenance")
    assert result.response_text
    assert result.verification["serve_path"] == "TEMPLATE_FALLBACK_VERIFIED"


def test_invalid_fallback_is_not_served(tmp_path):
    harness = make_harness(tmp_path, ["bad"], [False, False])
    _, result = run(harness, tmp_path)
    assert result.response_text == ""
    assert result.error == "verified_serve_unavailable"


def test_hitl_require_without_approval_cannot_serve(tmp_path):
    gateway = ApprovalGateway(policy=lambda state: ApprovalLevel.REQUIRE)
    harness = make_harness(tmp_path, ["candidate"], [True, False], approval_gateway=gateway)
    _, result = run(harness, tmp_path)
    assert result.response_text == ""
    assert result.approval["approved"] is False


def test_persistence_failure_is_safe(tmp_path):
    store = HostFictionStore("test-host", policy="per_session")
    store.save = MagicMock(side_effect=OSError("disk full"))
    harness = Harness(
        classifier=FakeClassifier(),
        cti_engine=FakeCti(),
        deceiver=FakeDeceiver(["candidate"]),
        verifier=SequenceVerifier([True]),
        mandatory_verification=True,
        host_store=store,
        host_fiction_path=str(tmp_path / "host.json"),
    )
    _, result = run(harness, tmp_path)
    assert result.response_text == ""
    assert result.error == "verified_serving_failed"


def test_concurrent_commands_are_serialized(tmp_path):
    harness = make_harness(tmp_path, ["safe"] * 8, [True] * 8)
    sandbox = Sandbox(harness=harness, config=SandboxConfig(session_dir=str(tmp_path / "sessions")))
    session = sandbox.create_session()
    with ThreadPoolExecutor(max_workers=8) as pool:
        responses = list(
            pool.map(
                lambda command: sandbox.handle_command("127.0.0.1", command, session_id=session.session_id),
                [f"echo {index}" for index in range(8)],
            )
        )
    assert all(response.response_text == "safe" for response in responses)
    assert responses[-1].command_count == 8


@pytest.mark.asyncio
async def test_local_ingress_to_verified_serving_path(tmp_path, monkeypatch):
    import ragin.server_v2 as server

    harness = make_harness(tmp_path, ["safe"], [True])
    sandbox = Sandbox(harness=harness, config=SandboxConfig(session_dir=str(tmp_path / "sessions")))
    originals = (server._harness, server._sandbox, server.API_KEY, server.REQUIRE_AUTH)
    server._harness = harness
    server._sandbox = sandbox
    server.API_KEY = "service-key"
    server.REQUIRE_AUTH = True
    try:
        with patch.object(server, "_init_pipeline"):
            app = server.create_app(mode="pipeline")
        client = TestClient(TestServer(app))
        await client.start_server()
        response = await client.post(
            "/v1/chat/completions",
            json={"messages": [{"role": "user", "content": "whoami"}]},
            headers={"Authorization": "Bearer service-key"},
        )
        assert response.status == 200
        body = await response.json()
        assert body["choices"][0]["message"]["content"] == "safe"
        await client.close()
    finally:
        server._harness, server._sandbox, server.API_KEY, server.REQUIRE_AUTH = originals


@pytest.mark.asyncio
async def test_missing_auth_and_unauthorized_session_are_rejected(tmp_path):
    import ragin.server_v2 as server

    originals = (server._harness, server._sandbox, server.API_KEY, server.REQUIRE_AUTH)
    server._harness = MagicMock()
    server._sandbox = MagicMock()
    server.API_KEY = "service-key"
    server.REQUIRE_AUTH = True
    try:
        with patch.object(server, "_init_pipeline"):
            app = server.create_app(mode="pipeline")
        client = TestClient(TestServer(app))
        await client.start_server()
        missing = await client.post("/api/session/command", json={"session_id": "s", "command": "id"})
        assert missing.status == 401
        metrics = await client.get("/metrics")
        assert metrics.status == 401
        unauthorized = await client.get(
            "/api/session/s/context", headers={"X-API-Key": "service-key"}
        )
        assert unauthorized.status == 403
        await client.close()
    finally:
        server._harness, server._sandbox, server.API_KEY, server.REQUIRE_AUTH = originals


@pytest.mark.asyncio
async def test_legacy_generative_route_is_disabled():
    import ragin.server as legacy

    original_key = legacy.API_KEY
    original_require_auth = legacy.REQUIRE_AUTH
    legacy.API_KEY = "legacy-key"
    legacy.REQUIRE_AUTH = True
    try:
        app = legacy.create_app("hisoka")
        client = TestClient(TestServer(app))
        await client.start_server()
        response = await client.post(
            "/api/deceive",
            json={"attacker_input": "id"},
            headers={"X-API-Key": "legacy-key"},
        )
        assert response.status == 410
        assert legacy.PUBLIC_PREFIXES == ("/health", "/ready")
        await client.close()
    finally:
        legacy.API_KEY = original_key
        legacy.REQUIRE_AUTH = original_require_auth


def test_missing_production_service_key_rejects_app_creation():
    import ragin.server_v2 as server

    original_key = server.API_KEY
    original_require_auth = server.REQUIRE_AUTH
    server.API_KEY = ""
    server.REQUIRE_AUTH = True
    try:
        with pytest.raises(RuntimeError, match="API_KEY"):
            server.create_app(mode="pipeline")
    finally:
        server.API_KEY = original_key
        server.REQUIRE_AUTH = original_require_auth


def test_production_rejects_default_env_template_key():
    """P0-B regression: the default .env.example API_KEY template must not be
    accepted as a production key when auth is enabled."""
    import ragin.server_v2 as server

    original_key = server.API_KEY
    original_require_auth = server.REQUIRE_AUTH
    server.API_KEY = "ragin-<generate-a-new-random-hex-key>"
    server.REQUIRE_AUTH = True
    try:
        with pytest.raises(RuntimeError, match="API_KEY"):
            server.create_app(mode="pipeline")
    finally:
        server.API_KEY = original_key
        server.REQUIRE_AUTH = original_require_auth


def test_production_starts_with_real_nonempty_api_key():
    """P0-B regression: a real non-empty API key under enabled auth must start
    the app (no RuntimeError). This is the production posture we want."""
    import ragin.server_v2 as server

    original_key = server.API_KEY
    original_require_auth = server.REQUIRE_AUTH
    server.API_KEY = "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4"
    server.REQUIRE_AUTH = True
    try:
        with patch.object(server, "_init_pipeline"):
            app = server.create_app(mode="pipeline")
        assert app is not None
    finally:
        server.API_KEY = original_key
        server.REQUIRE_AUTH = original_require_auth


def test_auth_disabled_with_empty_key_emits_warning_not_silent_pass():
    """P0-1 regression: disabling auth with an empty API key is not a silent
    pass in production. The module must flag the configuration explicitly so a
    reviewer or startup log can see it. This test asserts the helper's contract
    and that create_app does not raise when auth is deliberately disabled for
    local development (the module keeps that posture available)."""
    import ragin.server_v2 as server

    original_key = server.API_KEY
    original_require_auth = server.REQUIRE_AUTH
    server.API_KEY = ""
    server.REQUIRE_AUTH = False
    try:
        # The security helper must recognize this as the unsafe local-dev posture.
        assert server._is_production_auth_disabled() is True
        assert server._production_auth_is_enforced() is False
        # create_app must still start in locally-disabled mode (no RuntimeError).
        with patch.object(server, "_init_pipeline"):
            app = server.create_app(mode="pipeline")
        assert app is not None
    finally:
        server.API_KEY = original_key
        server.REQUIRE_AUTH = original_require_auth


def test_auth_disabled_with_placeholder_key_is_not_production_ready():
    """P0-1 regression: a placeholder API key under disabled auth is not a
    production-grade configuration even though requests would otherwise pass."""
    import ragin.server_v2 as server

    original_key = server.API_KEY
    original_require_auth = server.REQUIRE_AUTH
    server.API_KEY = "changeme"
    server.REQUIRE_AUTH = False
    try:
        # auth middleware would pass requests, but the config is not production.
        assert server._is_production_auth_disabled() is False
        assert server._production_auth_is_enforced() is False
    finally:
        server.API_KEY = original_key
        server.REQUIRE_AUTH = original_require_auth


def test_auth_enabled_with_nonempty_key_is_production_enforced():
    """P0-1 regression: the intended production posture is explicitly recognized."""
    import ragin.server_v2 as server

    original_key = server.API_KEY
    original_require_auth = server.REQUIRE_AUTH
    server.API_KEY = "abc123"
    server.REQUIRE_AUTH = True
    try:
        assert server._production_auth_is_enforced() is True
    finally:
        server.API_KEY = original_key
        server.REQUIRE_AUTH = original_require_auth


def test_production_does_not_start_with_api_key_equal_to_default_template():
    """P0-B regression: a common deployment mistake is copying .env.example's
    default API_KEY template into production. The server must reject that exact
    placeholder at startup when auth is enabled, not only the tiny placeholder
    wordlist."""
    import ragin.server_v2 as server

    original_key = server.API_KEY
    original_require_auth = server.REQUIRE_AUTH
    server.API_KEY = "ragin-<generate-a-new-random-hex-key>"
    server.REQUIRE_AUTH = True
    try:
        with pytest.raises(RuntimeError, match="API_KEY"):
            server.create_app(mode="pipeline")
    finally:
        server.API_KEY = original_key
        server.REQUIRE_AUTH = original_require_auth


def test_production_starts_with_real_nonempty_api_key():
    """P0-B regression: a real non-empty API key under enabled auth must start
    the app (no RuntimeError). This is the production posture we want."""
    import ragin.server_v2 as server

    original_key = server.API_KEY
    original_require_auth = server.REQUIRE_AUTH
    server.API_KEY = "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4"
    server.REQUIRE_AUTH = True
    try:
        with patch.object(server, "_init_pipeline"):
            app = server.create_app(mode="pipeline")
        assert app is not None
    finally:
        server.API_KEY = original_key
        server.REQUIRE_AUTH = original_require_auth
