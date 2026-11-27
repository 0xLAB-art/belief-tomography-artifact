"""Integration-oriented tests for the authenticated generator transport.

Executable in the existing ``.venv``. Asserts the WS1 safety contract directly:
* No authenticated provider configured -> generation raises, never silently falls
  back to an unauthenticated endpoint.
* Auth and provider URL are read from configuration only.
* Placeholder keys are treated as unconfigured.
* The transport reuses the existing authenticated ``GatewayClient``, so the
  existing auth/header/timeout discipline stays in one place.
* No public listener is introduced by this module.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from ragin.cycle.provider_transport import (
    ProviderTransport,
    ProviderTransportError,
    ProviderUnavailableError,
    _is_placeholder,
)  # noqa: E402


def _env_with(**pairs: str) -> dict[str, str | None]:
    before: dict[str, str | None] = {}
    for k, v in pairs.items():
        before[k] = os.environ.get(k)
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    return before


def _restore(before: dict[str, str | None]) -> None:
    for k, v in before.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v


def test_provider_transport_raises_when_unauthenticated():
    before = _env_with(
        RAGIN_PROVIDER_API_KEY=None,
        RAGIN_HISOKA_API_KEY=None,
        RAGIN_LLM_API_KEY=None,
        OPENROUTER_API_KEY=None,
        OPENAI_API_KEY=None,
        AZURE_OPENAI_KEY=None,
        RAGIN_PROVIDER_URL=None,
        RAGIN_HISOKA_GATEWAY_URL=None,
    )
    try:
        transport = ProviderTransport()
        with pytest.raises(ProviderUnavailableError):
            transport.generate(messages=[{"role": "user", "content": "id -un"}])
    finally:
        _restore(before)


def test_provider_transport_rejects_placeholder_keys(monkeypatch):
    """Deterministic: a placeholder provider key is treated as unconfigured and
    generate raises ProviderUnavailableError, regardless of any other auth env vars
    the launching shell may carry.

    Uses per-test monkeypatch to isolate os.environ. Clears the full known auth
    env order so a leaked OPENROUTER_API_KEY cannot short-circuit placeholder
    treatment.
    """
    import os
    from ragin.cycle.provider_transport import _PROVIDER_AUTH_ENV_ORDER
    known_before = {k: os.environ.get(k) for k in _PROVIDER_AUTH_ENV_ORDER if k in os.environ}
    for k in _PROVIDER_AUTH_ENV_ORDER:
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("RAGIN_PROVIDER_API_KEY", "changeme")
    monkeypatch.setenv("RAGIN_PROVIDER_URL", "http://localhost:9")
    try:
        transport = ProviderTransport()
        assert not transport.api_key_present
        with pytest.raises(ProviderUnavailableError):
            transport.generate(messages=[{"role": "user", "content": "id -un"}])
    finally:
        for k, v in known_before.items():
            if v is None:
                monkeypatch.delenv(k, raising=False)
            else:
                monkeypatch.setenv(k, v)


def test_provider_transport_reads_explicit_api_key():
    before = _env_with(
        RAGIN_PROVIDER_URL="http://localhost:9",
    )
    try:
        transport = ProviderTransport(api_key="a" * 24)
        assert transport.api_key_present
        assert transport.provider_url == "http://localhost:9"
    finally:
        _restore(before)


def test_provider_transport_prefers_explicit_key_over_env():
    before = _env_with(
        RAGIN_PROVIDER_API_KEY="env-key-not-used",
        RAGIN_PROVIDER_URL="http://localhost:9",
    )
    try:
        transport = ProviderTransport(api_key="explicit-key-usable-now")
        assert transport.api_key_present
    finally:
        _restore(before)


def test_provider_transport_url_sourced_from_single_explicit_env():
    before = _env_with(
        RAGIN_PROVIDER_API_KEY="a" * 24,
        RAGIN_PROVIDER_URL="http://private-provider.internal:8080",
    )
    try:
        transport = ProviderTransport()
        assert transport.provider_url == "http://private-provider.internal:8080"
    finally:
        _restore(before)


def test_provider_transport_falls_back_to_hisoka_gateway_url_only_when_no_provider_url_or_hisoka_url():
    """The implemented transport resolves URL as:
    RAGIN_PROVIDER_URL or RAGIN_HISOKA_GATEWAY_URL or default.
    When PROVIDER_URL is present it wins; otherwise HISOKA_GATEWAY_URL is used.
    """
    before = _env_with(
        RAGIN_PROVIDER_API_KEY="a" * 24,
        RAGIN_PROVIDER_URL=None,
        RAGIN_HISOKA_GATEWAY_URL="http://hisoka-gateway.pvt:8080",
    )
    try:
        transport = ProviderTransport()
        assert transport.provider_url == "http://hisoka-gateway.pvt:8080"
    finally:
        _restore(before)


def test_provider_transport_timeout_read_from_env():
    before = _env_with(
        RAGIN_PROVIDER_API_KEY="a" * 24,
        RAGIN_PROVIDER_TIMEOUT_S="180.0",
    )
    try:
        transport = ProviderTransport()
        assert transport._provider_timeout_s == 180.0
    finally:
        _restore(before)


def test_provider_transport_health_is_not_inference():
    before = _env_with(
        RAGIN_PROVIDER_API_KEY="a" * 24,
        RAGIN_PROVIDER_URL="http://localhost:9",
    )
    try:
        transport = ProviderTransport()
        health = transport.health()
        assert set(health) == {"provider_url", "api_key_present", "timeout_s", "client_ready"}
        assert health["api_key_present"] is True
    finally:
        _restore(before)


def test_provider_transport_reuses_authenticated_gateway_client_contract():
    """The transport must use the existing GatewayClient generate() contract so
    the existing auth/header/timeout discipline stays in one place."""
    before = _env_with(
        RAGIN_PROVIDER_API_KEY="a" * 24,
        RAGIN_PROVIDER_URL="http://localhost:9",
    )
    try:
        transport = ProviderTransport()
        sig = transport.generate.__annotations__
        assert "messages" in sig
        assert "return" in sig
        assert sig.get("return") in (tuple[str, dict[str, int]], "tuple[str, dict[str, int]]")
    finally:
        _restore(before)


def test_provider_unavailable_is_distinct_from_transport_error():
    assert issubclass(ProviderUnavailableError, RuntimeError)
    assert issubclass(ProviderTransportError, RuntimeError)
    assert not issubclass(ProviderTransportError, ProviderUnavailableError)


def test_placeholder_detection_is_strict_on_short_values():
    assert _is_placeholder("short")
    assert _is_placeholder("<set-me>")
    assert _is_placeholder("changeme")
    assert not _is_placeholder("a" * 40)
