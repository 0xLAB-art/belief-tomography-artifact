"""
Unit tests for the WS1 provider-transport adapter contract.

These assert the exact active-seam properties without requiring the live server
or a real provider endpoint:

* ProviderTransportAdapter satisfies the harness Deceiver protocol
  (generate_response(attacker_input, session_context) -> dict).
* When no authenticated provider is configured, the adapter does NOT silently
  fall back to an unauthenticated endpoint: it still produces a response, but
  the existing hisoka deterministic fallback is used (the provider transport
  itself remains fails-closed — ProviderUnavailableError on generate).
* api_key_present reflects a non-placeholder provider key when configured.
* When a non-placeholder provider key is configured, the adapter's underlying
  ResponseGenerator._gateway is a ProviderTransport wired to the configured URL.
* The adapter is a drop-in for HisokaAdapter at the Harness deceiver slot:
  both accept (attacker_input, session_context) and return a dict with the
  expected keys.
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
    ProviderTransportAdapter,
    ProviderUnavailableError,
    _is_placeholder,
    provider_api_key,
)


def _env_with(**pairs: str) -> dict[str, str | None]:
    before = {k: os.environ.get(k) for k in pairs if k in os.environ}
    for k, v in pairs.items():
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


REQUIRED_RESPONSE_KEYS = {
    "session_id",
    "response_text",
    "persona_used",
    "artifacts_injected",
    "engagement_score",
    "honeytoken_triggered",
    "metadata",
}


def test_adapter_satisfies_deceiver_protocol():
    before = _env_with(
        RAGIN_PROVIDER_API_KEY=None,
        RAGIN_PROVIDER_URL=None,
        OPENROUTER_API_KEY=None,
    )
    try:
        adapter = ProviderTransportAdapter()
        result = adapter.generate_response("whoami", {"session_id": "s1", "skill_level": "novice"})
        assert isinstance(result, dict)
        for k in REQUIRED_RESPONSE_KEYS:
            assert k in result, f"missing key {k}"
    finally:
        _restore(before)


def test_adapter_returns_dict_with_string_response_text():
    before = _env_with(
        RAGIN_PROVIDER_API_KEY=None,
        RAGIN_PROVIDER_URL=None,
        OPENROUTER_API_KEY=None,
    )
    try:
        adapter = ProviderTransportAdapter()
        result = adapter.generate_response("id -un", {"session_id": "s2"})
        assert isinstance(result["response_text"], str)
    finally:
        _restore(before)


def test_adapter_is_drop_in_for_hisoka_adapter_at_deceiver_slot():
    """Both the existing HisokaAdapter and the WS1 ProviderTransportAdapter
    satisfy the same harness deceiver contract, so server_v2 can swap them
    without touching the Harness constructor."""
    before = _env_with(
        RAGIN_PROVIDER_API_KEY=None,
        RAGIN_PROVIDER_URL=None,
        OPENROUTER_API_KEY=None,
    )
    try:
        from ragin.cycle.adapters import HisokaAdapter

        hisoka = HisokaAdapter(gateway_url="http://localhost:9")
        adapter = ProviderTransportAdapter(gateway_url="http://localhost:9")

        ctx = {"session_id": "s3", "skill_level": "novice"}
        r1 = hisoka.generate_response("whoami", ctx)
        r2 = adapter.generate_response("whoami", ctx)

        for r in (r1, r2):
            assert isinstance(r, dict)
            assert "response_text" in r
            assert "persona_used" in r
    finally:
        _restore(before)


def test_adapter_api_key_present_false_when_unconfigured():
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
        adapter = ProviderTransportAdapter()
        assert adapter.api_key_present is False
    finally:
        _restore(before)


def test_adapter_api_key_present_true_when_non_placeholder_configured():
    before = _env_with(
        RAGIN_PROVIDER_API_KEY=None,
        RAGIN_HISOKA_API_KEY=None,
        RAGIN_LLM_API_KEY=None,
        OPENROUTER_API_KEY="a" * 40,
        OPENAI_API_KEY=None,
        AZURE_OPENAI_KEY=None,
        RAGIN_PROVIDER_URL=None,
    )
    try:
        adapter = ProviderTransportAdapter()
        assert adapter.api_key_present is True
    finally:
        _restore(before)


def test_adapter_underlying_gateway_is_provider_transport_when_key_configured():
    before = _env_with(
        RAGIN_PROVIDER_API_KEY=None,
        RAGIN_HISOKA_API_KEY=None,
        RAGIN_LLM_API_KEY=None,
        OPENROUTER_API_KEY="a" * 40,
        OPENAI_API_KEY=None,
        AZURE_OPENAI_KEY=None,
        RAGIN_PROVIDER_URL="http://provider.internal:9",
    )
    try:
        adapter = ProviderTransportAdapter()
        gen = adapter._deceiver._response_generator
        gateway = gen._gateway
        assert gateway is not None
        assert isinstance(gateway, ProviderTransport)
        assert gateway.provider_url == "http://provider.internal:9"
        assert gateway.api_key_present is True
    finally:
        _restore(before)


def test_adapter_underlying_gateway_is_vanilla_when_unauthenticated():
    """When no authenticated provider is configured, the adapter's generator
    keeps its vanilla GatewayClient (no ProviderTransport is injected) — the
    provider path is left as an explicit, fails-closed authenticated transport,
    not silently activated. The adapter's higher-level generate_response() still
    yields a deterministic fallback for the session via the existing hisoka flow."""
    before = _env_with(
        RAGIN_PROVIDER_API_KEY=None,
        RAGIN_HISOKA_API_KEY=None,
        RAGIN_LLM_API_KEY=None,
        OPENROUTER_API_KEY=None,
        OPENAI_API_KEY=None,
        AZURE_OPENAI_KEY=None,
        RAGIN_PROVIDER_URL="http://localhost:9",
    )
    try:
        from ragin.gateway.client import GatewayClient

        adapter = ProviderTransportAdapter()
        gen = adapter._deceiver._response_generator
        gateway = gen._gateway
        assert gateway is not None
        # ProviderTransport is NOT injected when unauthenticated.
        assert isinstance(gateway, GatewayClient)
        assert not isinstance(gateway, ProviderTransport)
        assert adapter.api_key_present is False
        # The provider transport's fail-closed contract is still asserted at the
        # ProviderTransport level (test_provider_transport_config), not at this
        # vanilla client. Here we just confirm the adapter did not silently wire
        # an authenticated provider.
    finally:
        _restore(before)


def test_adapter_explicit_gateway_url_wins_over_env():
    before = _env_with(
        RAGIN_PROVIDER_API_KEY=None,
        RAGIN_PROVIDER_URL="http://env-wins:9",
    )
    try:
        adapter = ProviderTransportAdapter(gateway_url="http://explicit-wins:9")
        gen = adapter._deceiver._response_generator
        gateway = gen._gateway
        assert gateway is not None
        assert gateway.provider_url == "http://explicit-wins:9"
    finally:
        _restore(before)


def test_adapter_explicit_api_key_wins_over_env():
    before = _env_with(
        RAGIN_PROVIDER_API_KEY="env-key-not-used",
        RAGIN_PROVIDER_URL="http://localhost:9",
    )
    try:
        adapter = ProviderTransportAdapter(api_key="explicit-key-usable-now")
        gen = adapter._deceiver._response_generator
        gateway = gen._gateway
        assert gateway is not None
        assert gateway.api_key_present is True
    finally:
        _restore(before)


def test_adapter_preserves_existing_hisoka_behavior_on_provider_unavailable():
    """When the provider transport is unavailable, the adapter must NOT invent a
    new response shape. It reuses the existing hisoka deterministic fallback so
    the verifier and serving path see the same contract they always have."""
    before = _env_with(
        RAGIN_PROVIDER_API_KEY=None,
        RAGIN_HISOKA_API_KEY=None,
        RAGIN_LLM_API_KEY=None,
        OPENROUTER_API_KEY=None,
        OPENAI_API_KEY=None,
        AZURE_OPENAI_KEY=None,
        RAGIN_PROVIDER_URL="http://localhost:9",
    )
    try:
        adapter = ProviderTransportAdapter()
        result = adapter.generate_response("whoami", {"session_id": "s4", "skill_level": "novice"})
        assert isinstance(result, dict)
        for k in REQUIRED_RESPONSE_KEYS:
            assert k in result
        assert isinstance(result["response_text"], str)
    finally:
        _restore(before)


def test_adapter_does_not_expose_credentials_in_response():
    """The adapter response dict must never leak the provider/api key."""
    before = _env_with(
        RAGIN_PROVIDER_API_KEY="sk-or-v1-secret-not-for-output",
        RAGIN_PROVIDER_URL="http://localhost:9",
    )
    try:
        adapter = ProviderTransportAdapter()
        result = adapter.generate_response("id -un", {"session_id": "s5"})
        text = str(result)
        assert "sk-or-v1-secret-not-for-output" not in text
        assert result.get("response_text", "").find("sk-or-v1-secret-not-for-output") == -1
    finally:
        _restore(before)
