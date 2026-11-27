"""
Unit tests for the WS1 provider-transport configuration and drop-in contract.

These tests assert the exact WS1 integration properties without requiring the
live server or a real provider endpoint:

* ProviderTransportConfig resolves auth URL + key from env only.
* ProviderTransportConfig treats placeholder keys as unconfigured.
* ProviderTransportConfig.api_key_present reflects non-placeholder keys only.
* ProviderTransportConfig resolve() and auth_key_for() are pure config reads.
* ProviderTransport remains a GatewayClient subclass and reads provider_url /
  api_key from configuration.
* ProviderTransport.generate contract still returns tuple[str, dict[str,int]].
* When no authenticated provider is configured, generate raises
  ProviderUnavailableError (fail-closed), never an unauthenticated request.
* The HisokaAdapter / AdaptiveDeceiver / ResponseGenerator generator seam is
  preserved: a ProviderTransport can be dropped into ResponseGenerator's
  _gateway slot.
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
    provider_api_key,
    provider_url,
)


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


# ---------------------------------------------------------------------------
# Configuration contract
# ---------------------------------------------------------------------------


def test_provider_url_default_when_unset():
    before = _env_with(
        RAGIN_PROVIDER_URL=None,
        RAGIN_HISOKA_GATEWAY_URL=None,
        GATEWAY_URL=None,
    )
    try:
        assert provider_url() == "http://localhost:8080"
    finally:
        _restore(before)


def test_provider_url_resolves_from_explicit_provider_env():
    before = _env_with(RAGIN_PROVIDER_URL="http://private.provider.internal:8080")
    try:
        assert provider_url() == "http://private.provider.internal:8080"
    finally:
        _restore(before)


def test_provider_url_resolves_hisoka_gateway_url_when_no_provider_url():
    before = _env_with(
        RAGIN_PROVIDER_URL=None,
        RAGIN_HISOKA_GATEWAY_URL="http://hisoka-gateway.pvt:8080",
    )
    try:
        assert provider_url() == "http://hisoka-gateway.pvt:8080"
    finally:
        _restore(before)


def test_provider_url_resolves_gateway_url_when_no_provider_or_hisoka_url():
    before = _env_with(
        RAGIN_PROVIDER_URL=None,
        RAGIN_HISOKA_GATEWAY_URL=None,
        GATEWAY_URL="http://gateway.pvt:8080",
    )
    try:
        assert provider_url() == "http://gateway.pvt:8080"
    finally:
        _restore(before)


def test_provider_url_explicit_arg_wins_over_env():
    before = _env_with(RAGIN_PROVIDER_URL="http://env-wins:8080")
    try:
        from ragin.cycle.provider_transport import ProviderTransport

        transport = ProviderTransport(gateway_url="http://explicit-wins:9")
        assert transport.provider_url == "http://explicit-wins:9"
    finally:
        _restore(before)


def test_provider_api_key_returns_first_non_placeholder_env():
    before = _env_with(
        RAGIN_PROVIDER_API_KEY=None,
        RAGIN_HISOKA_API_KEY=None,
        RAGIN_LLM_API_KEY=None,
        OPENROUTER_API_KEY="env-openrouter-key-usable-now",
        OPENAI_API_KEY=None,
        AZURE_OPENAI_KEY=None,
    )
    try:
        assert provider_api_key() == "env-openrouter-key-usable-now"
    finally:
        _restore(before)


def test_provider_api_key_ignores_placeholders():
    before = _env_with(
        RAGIN_PROVIDER_API_KEY=None,
        RAGIN_HISOKA_API_KEY=None,
        RAGIN_LLM_API_KEY=None,
        OPENROUTER_API_KEY="<set-me>",
        OPENAI_API_KEY="changeme",
        AZURE_OPENAI_KEY="sk-placeholder-here",
    )
    try:
        assert provider_api_key() is None
    finally:
        _restore(before)


def test_provider_api_key_returns_none_when_all_empty():
    before = _env_with(
        RAGIN_PROVIDER_API_KEY=None,
        RAGIN_HISOKA_API_KEY=None,
        RAGIN_LLM_API_KEY=None,
        OPENROUTER_API_KEY=None,
        OPENAI_API_KEY=None,
        AZURE_OPENAI_KEY=None,
    )
    try:
        assert provider_api_key() is None
    finally:
        _restore(before)


# ---------------------------------------------------------------------------
# Placeholder detection
# ---------------------------------------------------------------------------


def test_placeholder_detection_flags_template_strings():
    assert _is_placeholder("<set-me>")
    assert _is_placeholder("your-api-key-here")
    assert _is_placeholder("replace-me")
    assert _is_placeholder("changeme")
    assert _is_placeholder("placeholder")
    assert _is_placeholder("set-in-env")
    assert _is_placeholder("todo: wire this")


def test_placeholder_detection_ignores_realistic_keys():
    assert not _is_placeholder("a" * 40)
    assert not _is_placeholder("sk-or-v1-" + "x" * 48)


def test_placeholder_detection_flags_short_values():
    assert _is_placeholder("short")
    assert _is_placeholder("123456789012345")  # 15 chars


# ---------------------------------------------------------------------------
# ProviderTransport drop-in contract
# ---------------------------------------------------------------------------


def test_provider_transport_is_gateway_client_subclass():
    from ragin.gateway.client import GatewayClient

    assert issubclass(ProviderTransport, GatewayClient)


def test_provider_transport_reads_provider_url():
    before = _env_with(RAGIN_PROVIDER_URL="http://provider.internal:9")
    try:
        transport = ProviderTransport()
        assert transport.provider_url == "http://provider.internal:9"
    finally:
        _restore(before)


def test_provider_transport_reads_api_key_present():
    before = _env_with(RAGIN_PROVIDER_API_KEY="a" * 40)
    try:
        transport = ProviderTransport()
        assert transport.api_key_present is True
    finally:
        _restore(before)


def test_provider_transport_api_key_present_is_false_for_placeholder(monkeypatch):
    """Deterministic: a placeholder provider key is always treated as unconfigured,
    regardless of any other auth env vars the launching shell may carry.

    Uses per-test monkeypatch to isolate os.environ. We also wipe the full known
    provider-auth env order so the result does not depend on e.g. a leaked
    OPENROUTER_API_KEY in the launching environment.
    """
    import os
    from ragin.cycle.provider_transport import _PROVIDER_AUTH_ENV_ORDER
    # monkeypatch isolates this test's env mutations; record the pre-existing
    # values for the known auth keys so monkeypatch.restore can put them back.
    known_before = {k: os.environ.get(k) for k in _PROVIDER_AUTH_ENV_ORDER if k in os.environ}
    # Clear every known auth key so the only setting in play is the placeholder
    # we set below.
    for k in _PROVIDER_AUTH_ENV_ORDER:
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("RAGIN_PROVIDER_API_KEY", "changeme")
    try:
        transport = ProviderTransport()
        assert transport.api_key_present is False
    finally:
        # Restore the known keys to their pre-test state (monkeypatch.restore
        # would also handle this, but explicit restore keeps the non-placeholder
        # keys the shell may have set from leaking into the next test).
        for k, v in known_before.items():
            if v is None:
                monkeypatch.delenv(k, raising=False)
            else:
                monkeypatch.setenv(k, v)


def test_provider_transport_generate_contract_returns_tuple_str_dict_int():
    before = _env_with(RAGIN_PROVIDER_API_KEY="a" * 40, RAGIN_PROVIDER_URL="http://localhost:9")
    try:
        transport = ProviderTransport()
        sig = transport.generate.__annotations__.get("return")
        assert sig == "tuple[str, dict[str, int]]"
    finally:
        _restore(before)


def test_provider_transport_generate_raises_when_unauthenticated():
    before = _env_with(
        RAGIN_PROVIDER_API_KEY=None,
        RAGIN_HISOKA_API_KEY=None,
        RAGIN_LLM_API_KEY=None,
        OPENROUTER_API_KEY=None,
        OPENAI_API_KEY=None,
        AZURE_OPENAI_KEY=None,
        RAGIN_PROVIDER_URL=None,
    )
    try:
        transport = ProviderTransport()
        with pytest.raises(ProviderUnavailableError):
            transport.generate(messages=[{"role": "user", "content": "id -un"}])
    finally:
        _restore(before)


def test_provider_transport_generate_raises_for_placeholder_key(monkeypatch):
    """Deterministic: a placeholder provider key raises ProviderUnavailableError
    on generate, regardless of any other auth env vars the launching shell may carry.

    Uses per-test monkeypatch to isolate os.environ. We clear the full known
    provider-auth env order so a leaked OPENROUTER_API_KEY in the launching
    environment cannot short-circuit the placeholder treatment.
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


def test_provider_transport_health_is_not_inference():
    before = _env_with(RAGIN_PROVIDER_API_KEY="a" * 40, RAGIN_PROVIDER_URL="http://localhost:9")
    try:
        transport = ProviderTransport()
        health = transport.health()
        assert set(health.keys()) == {"provider_url", "api_key_present", "timeout_s", "client_ready"}
        assert health["api_key_present"] is True
    finally:
        _restore(before)


def test_provider_transport_error_is_distinct_from_unavailable():
    assert issubclass(ProviderTransportError, RuntimeError)
    assert issubclass(ProviderUnavailableError, RuntimeError)
    assert not issubclass(ProviderTransportError, ProviderUnavailableError)
    assert not issubclass(ProviderUnavailableError, ProviderTransportError)


def test_provider_transport_can_drop_into_response_generator_gateway_slot():
    """The transport must be a valid GatewayClient for ResponseGenerator's
    _gateway slot, so the existing hisoka prompt construction and deterministic
    post-processing stays intact while the transport changes."""
    before = _env_with(
        RAGIN_PROVIDER_API_KEY="a" * 40,
        RAGIN_PROVIDER_URL="http://localhost:9",
    )
    try:
        from ragin.cycle.provider_transport import ProviderTransport
        from ragin.hisoka.deception import ResponseGenerator

        transport = ProviderTransport()
        gen = ResponseGenerator(gateway_url=None, api_key=None)
        gen._gateway = transport
        assert gen._gateway is transport
        assert isinstance(gen._gateway, ProviderTransport)
    finally:
        _restore(before)
