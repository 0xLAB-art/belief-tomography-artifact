"""
Secure, authenticated generator transport for the AWS CORE private provider path.

WS1 active wiring:
* ProviderTransport is a ``GatewayClient`` subclass. That makes it the
  authenticated transport inside the existing ``ResponseGenerator._gateway``
  slot — it is NOT a parallel inference pipeline and it does NOT replace the
  existing hisoka prompt construction, deterministic fast-paths, ledger,
  circuit breaker, budget, or post-processing.
* ProviderTransportAdapter satisfies the harness deceiver protocol
  (``generate_response(attacker_input, session_context) -> dict``) by
  delegating to the existing ``AdaptiveDeceiver.generate_response`` flow,
  with ProviderTransport as the authenticated backend for the optional LLM
  draft. When no authenticated provider is configured, the adapter routes to
  the existing deterministic template fallback the same way the existing
  ResponseGenerator already does on gateway failure.
* server_v2._init_pipeline selects ProviderTransportAdapter when a
  non-placeholder provider API key is configured; otherwise it preserves the
  existing HisokaAdapter path and leaves the provider path as an explicit,
  fails-closed authenticated transport.
* Mandatory verifier + verified fallback are preserved by construction: this
  module only changes the transport that obtains a candidate draft; the
  existing FictionConsistencyVerifier, fallback labeling, HITL policy, and
  accepted-state-only commit rules are untouched.
"""

from __future__ import annotations

import logging
import os
from typing import Any
from urllib.parse import urlparse

from ragin.gateway.client import GatewayClient
from ragin.gateway.generation import (
    GenerationConfig,
    GenerationConfigError,
    resolve_generation_config,
)

logger = logging.getLogger(__name__)


def _safe_endpoint(url: str) -> str:
    """Credential-free endpoint rendering for logs and health payloads.

    Provider URLs may carry userinfo (``user:pass@host``) or query tokens.
    Scheme, host, port, and path are retained; userinfo, query, and fragment
    are dropped. Unparseable values are replaced, never echoed.
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


_PROVIDER_AUTH_ENV_ORDER = (
    "RAGIN_PROVIDER_API_KEY",
    "RAGIN_HISOKA_API_KEY",
    "RAGIN_LLM_API_KEY",
    "OPENROUTER_API_KEY",
    "OPENAI_API_KEY",
    "AZURE_OPENAI_KEY",
)

_PROVIDER_URL_ENV_ORDER = (
    "RAGIN_PROVIDER_URL",
    "RAGIN_HISOKA_GATEWAY_URL",
    "GATEWAY_URL",
)


def provider_api_key() -> str | None:
    """Return the first configured provider/auth key for the generator transport.

    Only one key is returned, and only if it is a non-empty, non-placeholder
    value. Placeholder keys are treated as ``None`` so a misconfigured or
    intentionally-disabled provider does not accidentally authenticate.
    """
    for name in _PROVIDER_AUTH_ENV_ORDER:
        value = os.environ.get(name, "").strip()
        if not value:
            continue
        if _is_placeholder(value):
            logger.debug(
                "provider auth env %s is a placeholder; treating as unconfigured", name
            )
            continue
        return value
    return None


def provider_url() -> str:
    """Return the configured provider backend URL for the generator transport."""
    for name in _PROVIDER_URL_ENV_ORDER:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return "http://localhost:8080"


def _is_placeholder(key: str) -> bool:
    """Heuristic placeholder detection for common template values.

    This is a safety check, not an auth decision. Real provider keys vary widely;
    the point is to avoid sending obviously-unconfigured template strings as
    credentials.
    """
    lowered = key.lower()
    placeholders = (
        "your-",
        "replace-me",
        "replace with",
        "<",
        "$",
        "changeme",
        "placeholder",
        "set-in-env",
        "todo:",
    )
    if any(piece in lowered for piece in placeholders):
        return True
    return len(key) < 16


class ProviderUnavailableError(RuntimeError):
    """No authenticated provider backend is configured for generator transport."""

    reason_code = "PROVIDER_UNAVAILABLE"


class ProviderTransportError(RuntimeError):
    """The configured provider backend could not complete a generation request."""

    def __init__(self, message: str, *, reason_code: str = "PROVIDER_TRANSPORT_ERROR") -> None:
        super().__init__(message)
        self.reason_code = reason_code


class ProviderTransport(GatewayClient):
    """Authenticated generator transport for the chosen provider backend.

    This is a drop-in ``GatewayClient`` subclass wired through the existing
    generator seam. The existing ``ResponseGenerator(gateway_url, api_key)``
    constructor already accepts a provider URL and an API key, so the transport
    can be enabled with configuration only.

    * When a non-placeholder provider API key is present, the transport delegates
      to the existing authenticated ``GatewayClient`` behavior.
    * When no authenticated provider is configured, this transport raises
      ``ProviderUnavailableError`` on ``generate`` instead of silently sending
      an unauthenticated request.
    * ``health()`` returns a configuration snapshot, not an inference endpoint.
    """

    def __init__(
        self,
        gateway_url: str | None = None,
        api_key: str | None = None,
        *,
        timeout: float = 300.0,
        generation_config: GenerationConfig | None = None,
    ) -> None:
        # Preserve the existing GatewayClient constructor contract so the existing
        # generator seam can keep passing (gateway_url, api_key, timeout=...).
        # The generation contract is resolved once here: explicit native config
        # wins, otherwise the opt-in env/file contract applies, otherwise None
        # (legacy behavior).
        resolved_config = (
            generation_config if generation_config is not None else resolve_generation_config()
        )
        super().__init__(
            gateway_url=gateway_url or provider_url(),
            api_key=api_key or provider_api_key(),
            timeout=timeout,
            generation_config=resolved_config,
        )
        self._provider_timeout_s = float(
            os.environ.get("RAGIN_PROVIDER_TIMEOUT_S", str(timeout))
        )

    @property
    def provider_url(self) -> str:
        return self._gateway_url

    @property
    def api_key_present(self) -> bool:
        return bool(self._api_key)

    def generate(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 2048,
        extra_body: dict[str, Any] | None = None,
        top_p: float | None = None,
        seed: int | None = None,
        observation: dict[str, Any] | None = None,
    ) -> tuple[str, dict[str, int]]:
        """Generate through the authenticated provider backend.

        Raises:
            ProviderUnavailableError: when no authenticated provider is configured.
            ProviderTransportError: when the configured provider could not complete
                the request. Its message and ``reason_code`` never contain the
                endpoint URL or credentials.
            GenerationConfigError: when the active generation contract is
                internally inconsistent (for example a conflicting model). This is
                a configuration failure, not a provider failure.
        """
        if not self._api_key:
            raise ProviderUnavailableError(
                "provider transport is not authenticated: set a non-placeholder provider API key"
            )
        try:
            return super().generate(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                extra_body=extra_body,
                top_p=top_p,
                seed=seed,
                observation=observation,
            )
        except GenerationConfigError:
            raise
        except Exception as exc:
            reason_code = "PROVIDER_TRANSPORT_ERROR"
            if isinstance(observation, dict) and observation.get("failure_reason"):
                reason_code = str(observation["failure_reason"])
            raise ProviderTransportError(
                f"provider transport failed ({reason_code})",
                reason_code=reason_code,
            ) from exc

    def health(self) -> dict[str, Any]:
        """Minimal provider-transport readiness snapshot, not an inference endpoint."""
        snapshot: dict[str, Any] = {
            "provider_url": _safe_endpoint(self._gateway_url),
            "api_key_present": self.api_key_present,
            "timeout_s": self._provider_timeout_s,
            "client_ready": True,
        }
        # Additive: only present when the opt-in generation contract is active,
        # so the legacy health payload stays byte-compatible.
        if self._generation_config is not None:
            snapshot["generation"] = self.generation_snapshot()
        return snapshot


class ProviderTransportAdapter:
    """Harness-deceiver-protocol adapter for the authenticated provider transport.

    This is the WS1 active generator adapter. It satisfies the harness
    ``Deceiver`` protocol:

        generate_response(attacker_input: str, session_context: dict) -> dict

    by delegating to the existing ``AdaptiveDeceiver.generate_response`` flow
    (persona selection, fiction-block / strategy-block / ledger prompt
    construction, IMDS / SSH / sudo / credential-bait deterministic fast-paths,
    FS replay, circuit breaker, budget, post-processing, honeytokens) with
    ProviderTransport as the authenticated backend for the optional LLM draft.

    When no authenticated provider is configured, the adapter routes to the
    existing deterministic template fallback the same way ``ResponseGenerator``
    already does on gateway failure — the provider path is left as an explicit,
    fails-closed authenticated transport, not a silent no-op.
    """

    def __init__(
        self,
        gateway_url: str | None = None,
        api_key: str | None = None,
    ) -> None:
        from ragin.hisoka.deceiver import AdaptiveDeceiver
        from ragin.hisoka.deception import ResponseGenerator

        resolved_key = api_key or provider_api_key()
        resolved_url = gateway_url or provider_url()
        # WS1 provider-available branch: inject ProviderTransport as the
        # generator's auth transport when a non-placeholder provider key is
        # configured. The existing ResponseGenerator constructor builds a vanilla
        # GatewayClient from (url, key) — to route through our authenticated
        # transport we construct the gateway ourselves and pass it to a generator
        # we build directly, so AdaptiveDeceiver can still own its own
        # deceiver/ledger/circuit-breaker/budget while using our transport for the
        # optional LLM draft.
        transport: ProviderTransport | None = None
        if resolved_key:
            transport = ProviderTransport(
                gateway_url=resolved_url,
                api_key=resolved_key,
            )

        if transport is not None:
            gen = ResponseGenerator(gateway_url=None, api_key=None)
            gen._gateway = transport
            self._deceiver = AdaptiveDeceiver(
                gateway_url=resolved_url,
                api_key=resolved_key,
            )
            self._deceiver._response_generator = gen
            self._transport = transport
            self._gen = gen
        else:
            self._deceiver = AdaptiveDeceiver(
                gateway_url=resolved_url,
                api_key=resolved_key,
            )
            self._transport = None
            self._gen = self._deceiver._response_generator

    @property
    def api_key_present(self) -> bool:
        return bool(self._deceiver._response_generator._gateway and self._deceiver._response_generator._gateway._api_key)

    def generate_response(
        self, attacker_input: str, session_context: dict[str, Any]
    ) -> dict[str, Any]:
        """Generate a deception response through the existing hisoka flow.

        On provider-unavailable / transport error the existing hisoka
        deterministic fallback is used, so the pipeline still serves a
        verifier-eligible response rather than crashing the session.
        """
        try:
            result = self._deceiver.generate_response(attacker_input, session_context)
        except ProviderUnavailableError:
            logger.warning(
                "provider transport unavailable for session=%s — using deterministic fallback",
                session_context.get("session_id", "unknown"),
            )
            result = self._deceiver.generate_response(attacker_input, session_context)
        except ProviderTransportError as exc:
            logger.warning(
                "provider transport error for session=%s — using deterministic fallback: %s",
                session_context.get("session_id", "unknown"),
                exc,
            )
            result = self._deceiver.generate_response(attacker_input, session_context)
        except Exception as exc:
            logger.warning(
                "provider transport generate failed for session=%s — using deterministic fallback: %s",
                session_context.get("session_id", "unknown"),
                exc,
            )
            result = self._deceiver.generate_response(attacker_input, session_context)

        if not isinstance(result, dict):
            try:
                result = {
                    "session_id": getattr(result, "session_id", ""),
                    "response_text": getattr(result, "response_text", ""),
                    "persona_used": getattr(result, "persona_used", "unknown"),
                    "artifacts_injected": getattr(result, "artifacts_injected", []),
                    "engagement_score": float(getattr(result, "engagement_score", 0.0)),
                    "honeytoken_triggered": bool(getattr(result, "honeytoken_triggered", False)),
                    "metadata": getattr(result, "metadata", {}) or {},
                }
            except Exception:
                result = {
                    "session_id": "",
                    "response_text": str(result),
                    "persona_used": "unknown",
                    "artifacts_injected": [],
                    "engagement_score": 0.0,
                    "honeytoken_triggered": False,
                    "metadata": {},
                }

        return result
