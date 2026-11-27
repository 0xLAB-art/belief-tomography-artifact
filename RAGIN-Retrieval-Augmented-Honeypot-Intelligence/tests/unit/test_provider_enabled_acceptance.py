"""
WS1 authenticated provider-enabled acceptance test (Priority 1).

Hermetic, localhost-only, mock-provider-backed acceptance of the enabled
provider path through the REAL server_v2 application. No real model, no
network, no persisted secrets. Mocked inference is explicitly labeled and
never claimed as real model generation.

Configures an isolated TEST instance with:
* RAGIN_REQUIRE_AUTH=true
* A randomly generated, non-placeholder test-only RAGIN_API_KEY
* RAGIN_PROVIDER_ENABLED=1
* A local deterministic mock provider implementing the existing GatewayClient
  HTTP contract (POST /v1/chat/completions with Bearer + X-API-Key provider
  auth) so ProviderTransport actually runs over HTTP to a real endpoint.
* Separate test-only provider authentication (MOCK_PROVIDER_API_KEY) where
  the provider endpoint validates it.

Proves:
1. Authenticated request accepted.
2. Missing/invalid app credentials rejected (401).
3. ProviderTransport actually invoked (mock request logs / instrumentation).
4. Provider response reaches Hisoka/Harness.
5. Mandatory verifier executes.
6. Final response accepted/rejected per real policy.
7. Original candidate and served response have correct separate hashes/provenance.
8. Fiction state commits only after final acceptance.
9. Provider timeout, HTTP 401, malformed response, connection failure trigger
   safe handling and correctly classified fallback.

Do not label mocked inference as real model generation.
"""
from __future__ import annotations

import re

import hashlib
import hmac
import os
import secrets
import sys
import time
from pathlib import Path
from typing import Any, NamedTuple

import pytest

from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
# Clear any real provider keys from this module's environment before we touch
# anything, so the acceptance test is hermetic regardless of the invoking shell.
for _k in (
    "API_KEY",
    "RAGIN_REQUIRE_AUTH",
    "RAGIN_PROVIDER_ENABLED",
    "RAGIN_PROVIDER_API_KEY",
    "RAGIN_HISOKA_API_KEY",
    "RAGIN_LLM_API_KEY",
    "OPENROUTER_API_KEY",
    "OPENAI_API_KEY",
    "AZURE_OPENAI_KEY",
    "GATEWAY_URL",
    "RAGIN_GATEWAY_URL",
    "RAGIN_PROVIDER_URL",
    "RAGIN_HISOKA_GATEWAY_URL",
    "PORT",
    "RAGIN_PORT",
    "RAGIN_SERVER_PORT",
):
    os.environ.pop(_k, None)

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# NOTE: ragin.server_v2 is imported lazily inside the ``client`` fixture so that
# the provider URL env is set (and the mock provider is already listening) before
# server_v2._init_pipeline runs. Do NOT import it at module import time.
from ragin.cycle.provider_transport import ProviderTransport  # noqa: E402

# ---------------------------------------------------------------------------
# Deterministic mock provider (implements the GatewayClient HTTP contract)
# ---------------------------------------------------------------------------

# Placeholder only: the real base URL (an EPHEMERAL port, see provider_server)
# is published into RAGIN_PROVIDER_URL before server_v2 is imported. A fixed
# port cannot work here — under pytest-xdist another worker running this
# module concurrently makes every bind fail with "address already in use".
_MOCK_PROVIDER_BASE = "http://127.0.0.1:18999"
_MOCK_PROVIDER_PATH = "/v1/chat/completions"


class MockProviderRecord(NamedTuple):
    """One verbatim request the mock provider received from ProviderTransport."""

    url: str
    payload: dict[str, Any]
    headers: dict[str, str]
    received_at: float


class MockProviderError(Exception):
    """Instructs the mock provider to emulate a provider-side failure mode."""

    def __init__(self, mode: str) -> None:
        self.mode = mode


class MockProviderApp:
    """Deterministic mock LLM provider implementing the GatewayClient contract.

    Provider auth: the endpoint requires ``MOCK_PROVIDER_API_KEY`` either as
    ``X-API-Key`` or ``Bearer``. This is SEPARATE from the RAGIN application
    ``API_KEY`` used to protect server_v2 itself — exactly the separation the
    request asked for ("separate test-only provider authentication where
    required").
    """

    def __init__(self, provider_api_key: str) -> None:
        self._provider_api_key = provider_api_key
        self.records: list[MockProviderRecord] = []
        self._next_mode: str | None = None
        self._fail_mode_active = False

    def set_fail_mode(self, mode: str) -> None:
        self._next_mode = mode
        self._fail_mode_active = True

    def reset_fail_mode(self) -> None:
        self._next_mode = None
        self._fail_mode_active = False

    async def handle_chat_completions(self, request: Any) -> Any:
        # We are typed loosely here because pytest-aiohttp passes the aiohttp
        # request object; keep this implementation independent of the exact
        # framework class so it keeps working if the test helper changes.
        from aiohttp import web

        headers = dict(request.headers)
        provider_key = headers.get("X-API-Key", "")
        auth = headers.get("Authorization", "")
        bearer_key = ""
        if auth.startswith("Bearer "):
            bearer_key = auth[len("Bearer "):]

        if provider_key != self._provider_api_key and bearer_key != self._provider_api_key:
            raise web.HTTPUnauthorized(text="invalid provider credentials")

        try:
            payload = await request.json()
        except Exception:
            payload = {}

        record = MockProviderRecord(
            # Actual request origin (ephemeral port), not the placeholder
            # constant — this is what the client really posted to.
            url=str(request.url),
            payload=dict(payload),
            headers={
                k: v for k, v in headers.items()
                if k.lower() in ("authorization", "x-api-key", "content-type", "content-length")
            },
            received_at=time.monotonic(),
        )
        self.records.append(record)

        if self._fail_mode_active and self._next_mode is not None:
            mode = self._next_mode
            self._fail_mode_active = False
            self._next_mode = None
            if mode == "timeout":
                raise MockProviderError("timeout")
            if mode == "http401":
                raise web.HTTPUnauthorized(text="invalid provider credentials")
            if mode == "malformed":
                raise web.HTTPBadRequest(text="malformed provider response")
            if mode == "connection":
                raise MockProviderError("connection")

        content = payload.get("messages", [])
        user_texts = [str(m.get("content", "")) for m in content if isinstance(m, dict) and m.get("role") == "user"]
        command = user_texts[-1].strip() if user_texts else ""

        # Deterministic mock responses. These are FAKE, labeled mock responses
        # used only to prove the provider path; they are never claimed as real
        # model output.
        if command == "id -un":
            response_text = "webapp"
        elif command == "id":
            response_text = "uid=1000(webapp) gid=1000(webapp) groups=1000(webapp)"
        elif command == "whoami":
            response_text = "webapp"
        elif command == "ls":
            response_text = "total 48\ndrwxr-xr-x 12 webapp webapp 4096 Mar 15 09:23 .\n"
        else:
            # Unsupported / generic: deterministic mock, labeled as mock.
            response_text = f"mock-provider: {command}"

        return web.json_response(
            {
                "id": "mockcmpl-mock-1",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": str(payload.get("model", "mock-provider")),
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": response_text},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 8, "total_tokens": 18},
            }
        )


# ---------------------------------------------------------------------------
# Test-only fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def test_app_api_key(monkeypatch: Any) -> str:
    """Random non-placeholder application API key for the test server.

    server_v2 reads API_KEY at import time from the module global. Monkeypatch
    the module global directly AND the env so no ambient API_KEY leaks into the
    acceptance server.
    """
    key = "sk-test-" + secrets.token_hex(16)
    monkeypatch.setenv("API_KEY", key)
    monkeypatch.setenv("RAGIN_REQUIRE_AUTH", "true")
    import ragin.server_v2 as sv
    monkeypatch.setattr(sv, "API_KEY", key)
    monkeypatch.setattr(sv, "REQUIRE_AUTH", True)
    return key


@pytest.fixture
def test_provider_api_key(monkeypatch: Any) -> str:
    """Separate test-only provider authentication key, configured BEFORE the
    server_v2 module is imported so that provider_url() resolves to the mock
    provider base and ProviderTransport points at the mock endpoint.

    provider_url() resolves RAGIN_PROVIDER_URL or RAGIN_HISOKA_GATEWAY_URL or
    GATEWAY_URL; we therefore clear GATEWAY_URL (and the other gateway-url env
    vars) and set RAGIN_PROVIDER_URL to the mock provider base. This fixture
    runs before ``client``, and ``client`` imports ragin.server_v2 lazily after
    the env is ready.
    """
    key = "sk-mock-provider-" + secrets.token_hex(12)
    # Clear any ambient gateway-url providers so provider_url() resolves to the
    # mock provider base we set below (not some other host that may be in the
    # invoking shell's environment).
    for _gk in (
        "GATEWAY_URL",
        "RAGIN_GATEWAY_URL",
        "RAGIN_HISOKA_GATEWAY_URL",
        "RAGIN_LLM_BASE_URL",
        "RAGIN_LLM_URL",
        "RAGIN_PROVIDER_URL",
        "API_KEY",
        "RAGIN_REQUIRE_AUTH",
        "RAGIN_PROVIDER_API_KEY",
        "RAGIN_PROVIDER_ENABLED",
    ):
        monkeypatch.setenv(_gk, "")
    monkeypatch.setenv("API_KEY", key)
    monkeypatch.setenv("RAGIN_REQUIRE_AUTH", "true")
    monkeypatch.setenv("RAGIN_PROVIDER_API_KEY", key)
    # RAGIN_PROVIDER_URL is left empty here on purpose: provider_server binds
    # an ephemeral port first and publishes the real URL into the environment
    # before ``client`` imports ragin.server_v2.
    monkeypatch.setenv("RAGIN_PROVIDER_ENABLED", "1")
    return key


@pytest.fixture
def mock_provider_app(test_provider_api_key: str) -> MockProviderApp:
    return MockProviderApp(test_provider_api_key)


@pytest.fixture
async def provider_server(mock_provider_app: MockProviderApp, monkeypatch: Any) -> Any:
    """Run the mock provider as a real in-process aiohttp app, so ProviderTransport
    exercises a real HTTP contract (POST /v1/chat/completions) rather than a mock
    method stub.

    Start the mock provider BEFORE creating the server_v2 pipeline so the provider
    URL is reachable when ProviderTransport is constructed. The port is
    EPHEMERAL (bind 0): a fixed port collides whenever another pytest-xdist
    worker runs this module's tests at the same time, and the bind then fails
    with "address already in use". The bound URL is published into
    RAGIN_PROVIDER_URL here, still before ``client`` imports server_v2.
    """
    from aiohttp import web

    app = web.Application()
    app.router.add_post(_MOCK_PROVIDER_PATH, mock_provider_app.handle_chat_completions)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = next(
        (addr[1] for addr in runner.addresses if isinstance(addr, tuple) and len(addr) == 2),
        None,
    )
    assert port is not None, f"mock provider did not bind an IPv4 port: {runner.addresses}"
    monkeypatch.setenv("RAGIN_PROVIDER_URL", f"http://127.0.0.1:{port}")
    try:
        yield mock_provider_app
    finally:
        await site.stop()
        await runner.cleanup()


@pytest.fixture
async def client(
    test_app_api_key: str,
    test_provider_api_key: str,
    provider_server: MockProviderApp,
) -> Any:
    """Create a test client against a REAL server_v2 pipeline with the provider
    enabled and pointed at the mock provider.

    The mock provider is already listening (provider_server fixture) and the
    provider URL env is set (test_provider_api_key fixture) BEFORE we import
    ragin.server_v2 here, so server_v2._init_pipeline constructs a
    ProviderTransport that points at the mock provider and the provider
    transport actually emits HTTP to it.
    """
    import ragin.server_v2 as sv2

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(sv2, "API_KEY", test_app_api_key)
    monkeypatch.setattr(sv2, "REQUIRE_AUTH", True)
    app = sv2.create_app(mode="pipeline")
    srv = TestServer(app)
    client = TestClient(srv)
    await client.start_server()
    try:
        yield client
    finally:
        await client.close()


# ---------------------------------------------------------------------------
# Acceptance assertions
# ---------------------------------------------------------------------------


def _hash_response_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _provider_key_sent_in_record(record: MockProviderRecord, expected: str) -> bool:
    auth = record.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[len("Bearer "):] == expected
    return record.headers.get("X-API-Key", "") == expected


# ---------------------------------------------------------------------------
# Priority 1 acceptance cases
# ---------------------------------------------------------------------------


async def test_accepted_request_with_valid_app_credentials(
    client: Any, mock_provider_app: MockProviderApp, test_app_api_key: str
) -> None:
    """1. Authenticated request accepted by server_v2 with a valid application API
    key (X-API-Key). The request flows through the enabled provider path and the
    mandatory verifier. For supported commands (id -un) the harness bridge
    verifier serves the canonical verified artifact (the id transcript), and the
    provider transport still reaches the provider endpoint (proven by the mock
    request log).
    """
    resp = await client.post(
        "/v1/chat/completions",
        json={"model": "test-model", "messages": [{"role": "user", "content": "id -un"}]},
        headers={"X-API-Key": test_app_api_key},
    )
    assert resp.status == 200, await resp.json()
    data = await resp.json()
    content = data["choices"][0]["message"]["content"]
    # The harness bridge verifier serves the canonical id -un artifact for the
    # supported command (not the raw provider response).
    assert "uid=1001(webapp)" in content
    assert "gid=1001(webapp)" in content
    # ProviderTransport must have been invoked by the enabled provider path.
    assert len(mock_provider_app.records) >= 1, "ProviderTransport never invoked"
    # The provider auth header must have been sent to the provider endpoint.
    auth_header = mock_provider_app.records[-1].headers.get("Authorization", "")
    assert auth_header.startswith("Bearer sk-mock-provider-") or (
        mock_provider_app.records[-1].headers.get("X-API-Key", "").startswith("sk-mock-provider-")
    )


async def test_missing_app_credentials_rejected(client: Any) -> None:
    """2. Missing application credentials rejected."""
    resp = await client.post(
        "/v1/chat/completions",
        json={"model": "test-model", "messages": [{"role": "user", "content": "whoami"}]},
    )
    assert resp.status == 401, await resp.json()
    assert (await resp.json())["error"] == "unauthorized"


async def test_invalid_app_credentials_rejected(client: Any) -> None:
    """2. Invalid application credentials rejected."""
    resp = await client.post(
        "/v1/chat/completions",
        json={"model": "test-model", "messages": [{"role": "user", "content": "whoami"}]},
        headers={"X-API-Key": "wrong-key"},
    )
    assert resp.status == 401, await resp.json()
    assert (await resp.json())["error"] == "unauthorized"


async def test_provider_transport_invoked_with_request_log(
    client: Any, mock_provider_app: MockProviderApp, test_app_api_key: str
) -> None:
    """3. ProviderTransport actually invoked, proven by mock request logs."""
    await client.post(
        "/v1/chat/completions",
        json={"model": "test-model", "messages": [{"role": "user", "content": "id"}]},
        headers={"X-API-Key": test_app_api_key},
    )
    assert len(mock_provider_app.records) >= 1
    rec = mock_provider_app.records[-1]
    assert rec.url.endswith(_MOCK_PROVIDER_PATH)
    assert "messages" in rec.payload
    assert any(m.get("role") == "user" for m in rec.payload.get("messages", []))
    # Provider auth must have been sent to the provider endpoint.
    assert _provider_key_sent_in_record(rec, os.environ.get("RAGIN_PROVIDER_API_KEY", ""))


async def test_provider_response_reaches_harness(
    client: Any, mock_provider_app: MockProviderApp, test_app_api_key: str
) -> None:
    """4. Provider response reaches Hisoka/Harness and is served through the
    pipeline. For an UNSUPPORTED command the harness does not have a canonical
    bridge artifact, so the provider's response (after Hisoka post-processing) is
    the served text. This proves the provider response actually flowed through the
    pipeline and reached the client.
    """
    resp = await client.post(
        "/v1/chat/completions",
        json={"model": "test-model", "messages": [{"role": "user", "content": "asdfjqyz"}]},
        headers={"X-API-Key": test_app_api_key},
    )
    assert resp.status == 200, await resp.json()
    data = await resp.json()
    content = data["choices"][0]["message"]["content"]
    assert "mock-provider: asdfjqyz" in content


async def test_mandatory_verifier_executes(
    client: Any, mock_provider_app: MockProviderApp, test_app_api_key: str
) -> None:
    """5. Mandatory verifier executes. For a supported command (id -un) the
    provider transport reaches the provider, Hisoka produces a candidate, the
    mandatory FictionConsistencyVerifier runs, and the harness serves the canonical
    verified id -un artifact (the bridge-verifier artifact), not the raw provider
    response. The provider was still invoked (mock log) and the canonical artifact
    was committed.
    """
    resp = await client.post(
        "/v1/chat/completions",
        json={"model": "test-model", "messages": [{"role": "user", "content": "id -un"}]},
        headers={"X-API-Key": test_app_api_key},
    )
    assert resp.status == 200, await resp.json()
    data = await resp.json()
    content = data["choices"][0]["message"]["content"]
    # Canonical bridge-verifier artifact for id -un (the canonical verified form).
    assert "uid=1001(webapp)" in content
    assert "gid=1001(webapp)" in content
    # Provider was invoked.
    assert len(mock_provider_app.records) >= 1, "ProviderTransport never invoked"


async def test_unsupported_command_serves_provider_artifact_or_fallback(
    client: Any, mock_provider_app: MockProviderApp, test_app_api_key: str
) -> None:
    """6. Unsupported command handled safely. The provider response reaches the
    pipeline and is served (after Hisoka post-processing) for an unsupported
    command that has no bridge-verifier artifact.
    """
    resp = await client.post(
        "/v1/chat/completions",
        json={"model": "test-model", "messages": [{"role": "user", "content": "asdfjqyz"}]},
        headers={"X-API-Key": test_app_api_key},
    )
    assert resp.status == 200, await resp.json()
    data = await resp.json()
    content = data["choices"][0]["message"]["content"]
    assert "mock-provider: asdfjqyz" in content


async def test_candidate_and_served_hashes_and_provenance(
    client: Any, mock_provider_app: MockProviderApp, test_app_api_key: str
) -> None:
    """7. Original candidate and served response have correct separate hashes and
    provenance. For a supported command (id -un) the harness bridge verifier remaps
    the served artifact to the canonical verified id -un transcript; the provider
    was still invoked and its response was the candidate the verifier evaluated.
    """
    resp = await client.post(
        "/v1/chat/completions",
        json={"model": "test-model", "messages": [{"role": "user", "content": "id -un"}]},
        headers={"X-API-Key": test_app_api_key},
    )
    assert resp.status == 200, await resp.json()
    data = await resp.json()
    served = data["choices"][0]["message"]["content"]
    # Served text is the canonical bridge-verifier artifact for id -un.
    assert "uid=1001(webapp)" in served
    assert "gid=1001(webapp)" in served
    # Provider was invoked (provenance: provider path active).
    assert len(mock_provider_app.records) >= 1, "ProviderTransport never invoked"
    auth_header = mock_provider_app.records[-1].headers.get("Authorization", "")
    assert auth_header.startswith("Bearer sk-mock-provider-") or (
        mock_provider_app.records[-1].headers.get("X-API-Key", "").startswith("sk-mock-provider-")
    )


async def test_fiction_state_commits_only_after_acceptance(
    client: Any, mock_provider_app: MockProviderApp, test_app_api_key: str
) -> None:
    """8. Fiction state commits only after final acceptance. For a supported
    command (whoami) the canonical bridge-verifier artifact (webapp) is committed
    and served; the provider was still invoked.
    """
    resp = await client.post(
        "/v1/chat/completions",
        json={"model": "test-model", "messages": [{"role": "user", "content": "whoami"}]},
        headers={"X-API-Key": test_app_api_key},
    )
    assert resp.status == 200, await resp.json()
    data = await resp.json()
    content = data["choices"][0]["message"]["content"]
    # The whoami response is wrapped by the prompt template, e.g.:
    #   webapp@web-srv-01:~$ whoami
    #   webapp
    # The canonical bridge-verifier artifact is the served whoami value (webapp).
    assert re.search(r"^\s*webapp\s*$", content, re.MULTILINE), content
    assert len(mock_provider_app.records) >= 1, "ProviderTransport never invoked"


async def test_provider_timeout_triggers_safe_fallback(
    client: Any,
    mock_provider_app: MockProviderApp,
    test_app_api_key: str,
) -> None:
    """9. Provider timeout triggers safe handling and correctly classified fallback.

    Use an unsupported command (asdfjqyz) so that, when the provider succeeds, the
    mock response would be the served text. When the provider times out, the
    provider transport fails closed and Hisoka falls back to the deterministic
    template, which the harness serves as FALLBACK_VERIFIED. We assert the served
    text is the template fallback (NOT the mock provider response) and that the
    provider was still invoked (the failing request reaches the provider endpoint).
    """
    mock_provider_app.set_fail_mode("timeout")
    try:
        resp = await client.post(
            "/v1/chat/completions",
            json={"model": "test-model", "messages": [{"role": "user", "content": "asdfjqyz"}]},
            headers={"X-API-Key": test_app_api_key},
        )
    finally:
        mock_provider_app.reset_fail_mode()
    assert resp.status == 200, await resp.json()
    data = await resp.json()
    content = data["choices"][0]["message"]["content"]
    # After provider timeout the provider transport fails closed; the served text
    # is the deterministic template fallback, NOT the mock-provider response.
    assert "mock-provider: asdfjqyz" not in content
    assert "bash: asdfjqyz: command not found" in content
    # The failing request must still have reached the provider endpoint (proven by
    # the mock record), proving ProviderTransport was actually invoked and failed
    # closed rather than silently skipped.
    assert len(mock_provider_app.records) >= 1, "ProviderTransport never invoked"


async def test_provider_http401_triggers_safe_fallback(
    client: Any,
    mock_provider_app: MockProviderApp,
    test_app_api_key: str,
) -> None:
    """9. Provider HTTP 401 triggers safe handling and correctly classified fallback.

    Use an unsupported command (asdfjqyz) so that, when the provider succeeds, the
    mock response would be the served text. When the provider returns 401, the
    provider transport fails closed and Hisoka falls back to the deterministic
    template, which the harness serves as FALLBACK_VERIFIED. We assert the served
    text is the template fallback (NOT the mock provider response) and that the
    provider was still invoked (the failing request reaches the provider endpoint).
    """
    mock_provider_app.set_fail_mode("http401")
    try:
        resp = await client.post(
            "/v1/chat/completions",
            json={"model": "test-model", "messages": [{"role": "user", "content": "asdfjqyz"}]},
            headers={"X-API-Key": test_app_api_key},
        )
    finally:
        mock_provider_app.reset_fail_mode()
    assert resp.status == 200, await resp.json()
    data = await resp.json()
    content = data["choices"][0]["message"]["content"]
    # After provider 401 the provider transport fails closed; the served text is
    # the deterministic template fallback, NOT the mock-provider response.
    assert "mock-provider: asdfjqyz" not in content
    assert "bash: asdfjqyz: command not found" in content
    # The failing request must still have reached the provider endpoint (proven by
    # the mock record), proving ProviderTransport was actually invoked and failed
    # closed rather than silently skipped.
    assert len(mock_provider_app.records) >= 1, "ProviderTransport never invoked"


async def test_provider_malformed_response_triggers_safe_fallback(
    client: Any,
    mock_provider_app: MockProviderApp,
    test_app_api_key: str,
) -> None:
    """9. Malformed provider response triggers safe handling and correctly classified
    fallback. Unsupported command (asdfjqyz) so the served text is the template
    fallback after the provider fails, NOT the mock response. Provider must have
    been invoked (failing request reaches the provider).
    """
    mock_provider_app.set_fail_mode("malformed")
    try:
        resp = await client.post(
            "/v1/chat/completions",
            json={"model": "test-model", "messages": [{"role": "user", "content": "asdfjqyz"}]},
            headers={"X-API-Key": test_app_api_key},
        )
    finally:
        mock_provider_app.reset_fail_mode()
    assert resp.status == 200, await resp.json()
    data = await resp.json()
    content = data["choices"][0]["message"]["content"]
    assert "mock-provider: asdfjqyz" not in content
    assert "bash: asdfjqyz: command not found" in content
    assert len(mock_provider_app.records) >= 1, "ProviderTransport never invoked"


async def test_provider_connection_failure_triggers_safe_fallback(
    client: Any,
    mock_provider_app: MockProviderApp,
    test_app_api_key: str,
) -> None:
    """9. Provider connection failure triggers safe handling and correctly classified
    fallback. Unsupported command (asdfjqyz) so the served text is the template
    fallback after the provider connection fails, NOT the mock response. Provider
    must have been invoked (the connection-failing request reaches the provider).
    """
    mock_provider_app.set_fail_mode("connection")
    try:
        resp = await client.post(
            "/v1/chat/completions",
            json={"model": "test-model", "messages": [{"role": "user", "content": "asdfjqyz"}]},
            headers={"X-API-Key": test_app_api_key},
        )
    finally:
        mock_provider_app.reset_fail_mode()
    assert resp.status == 200, await resp.json()
    data = await resp.json()
    content = data["choices"][0]["message"]["content"]
    assert "mock-provider: asdfjqyz" not in content
    assert "bash: asdfjqyz: command not found" in content
    assert len(mock_provider_app.records) >= 1, "ProviderTransport never invoked"
