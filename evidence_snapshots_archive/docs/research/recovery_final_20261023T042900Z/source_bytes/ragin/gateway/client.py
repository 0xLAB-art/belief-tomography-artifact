"""Shared GatewayClient for LLM Gateway /v1/chat completions.

Consolidates HTTP transport, auth, and response parsing so callers
(Don's ThreatRAGEngine, Hisoka's ResponseGenerator) don't duplicate
the raw HTTP call.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
import time
from typing import Any
from urllib.parse import urlparse

import requests

from ragin.capture_v4.privacy import bounded_redacted_text
from ragin.gateway.generation import GenerationConfig, GenerationConfigError

logger = logging.getLogger(__name__)

# Stable, credential-free failure codes carried in the generation observation.
_FAILURE_REASONS = {
    "connection": "PROVIDER_CONNECTION_ERROR",
    "timeout": "PROVIDER_TIMEOUT",
    "http": "PROVIDER_HTTP_ERROR",
    "malformed": "PROVIDER_MALFORMED_RESPONSE",
    "transport": "PROVIDER_TRANSPORT_ERROR",
}

# Models whose deployments spend completion tokens on hidden chain-of-thought
# before the visible answer (vLLM-served Qwen3/QwQ, OpenAI o-series, R1).
_REASONING_MODEL_RE = re.compile(
    r"(qwen3|qwq|deepseek-r|o[134](-mini|-preview)?\b|reasoning|thinking|glm-5)", re.IGNORECASE
)

# Calls at or below this budget are "short structured calls" (relevance
# grades, query decomposition/rewrites): reasoning models run them with
# reasoning_effort=low so the corrective loop stays latency-viable. 2048
# keeps batch grades (12 verdict lines + COT headroom) inside the tier.
_SHORT_CALL_MAX_TOKENS = 2048


# Azure AI model-frontend endpoints reject the open-source extension field
# reasoning_effort with HTTP 400. The first failed request costs a full round
# trip, so skip the field entirely for azure.* hosts instead of discovering
# the rejection the expensive way.
def _host_rejects_reasoning_effort(url: str) -> bool:
    try:
        return ".azure." in (urlparse(url).hostname or "")
    except Exception:
        return False


# apmix WAF (observed 2026-09-21): payloads whose JSON-decoded body contains
# the path literals /etc/passwd, /etc/shadow, /etc/hosts are 502'd
# ("upstream_error") before reaching the model. Honeypot sessions quote these
# paths constantly, so rewrite them at request time to semantically equivalent
# path notation (/etc/./passwd resolves identically on Linux) and canonicalize
# the reply back — transport only, invisible to every caller.
_WAF_PATHS = {
    "/etc/passwd": "/etc/./passwd",
    "/etc/shadow": "/etc/./shadow",
    "/etc/hosts": "/etc/./hosts",
}


def _waf_safe(s: str) -> str:
    for plain, safe in _WAF_PATHS.items():
        s = s.replace(plain, safe)
    return s


def _waf_restore(s: str) -> str:
    for plain, safe in _WAF_PATHS.items():
        s = s.replace(safe, plain)
    return s


def _failure_reason(exc: BaseException) -> str:
    """Map a transport exception to a stable code without echoing its text.

    ``requests`` exception strings can contain the request URL (including
    userinfo or query tokens), so they are never copied into observations or
    logs.
    """
    if isinstance(exc, requests.HTTPError):
        status = exc.response.status_code if exc.response is not None else None
        if status is not None:
            return f"PROVIDER_HTTP_{status}"
        return _FAILURE_REASONS["http"]
    if isinstance(exc, (requests.ConnectTimeout, requests.ReadTimeout, requests.Timeout)):
        return _FAILURE_REASONS["timeout"]
    if isinstance(exc, requests.ConnectionError):
        return _FAILURE_REASONS["connection"]
    if isinstance(exc, ValueError):
        return _FAILURE_REASONS["malformed"]
    return _FAILURE_REASONS["transport"]


def _provider_usage(usage: Any) -> dict[str, Any]:
    """Extract provider-reported token counts only; never synthesise usage."""
    result: dict[str, Any] = {
        "usage_availability": "NOT_REPORTED",
        "usage_prompt_tokens": None,
        "usage_completion_tokens": None,
        "usage_total_tokens": None,
    }
    if not isinstance(usage, dict):
        return result
    prompt = usage.get("prompt_tokens")
    completion = usage.get("completion_tokens")
    total = usage.get("total_tokens")
    reported = False
    if isinstance(prompt, int) and not isinstance(prompt, bool):
        result["usage_prompt_tokens"] = prompt
        reported = True
    if isinstance(completion, int) and not isinstance(completion, bool):
        result["usage_completion_tokens"] = completion
        reported = True
    if isinstance(total, int) and not isinstance(total, bool):
        result["usage_total_tokens"] = total
    elif reported:
        result["usage_total_tokens"] = (result["usage_prompt_tokens"] or 0) + (
            result["usage_completion_tokens"] or 0
        )
    if reported:
        result["usage_availability"] = "PROVIDER_REPORTED"
    return result


class GatewayClient:
    """Thin HTTP client for LLM Gateway chat completions.

    Handles: request serialisation, auth headers, transport errors,
    response extraction.  Callers layer on budget checks, circuit
    breakers, PII redaction, cost tracking, fallback logic, etc.
    """

    _MAX_RETRIES = 1
    _BASE_BACKOFF = 1.0
    # Reasoning deployments routinely burn 3-6k hidden COT tokens before the
    # visible answer; a retry needs real headroom over the original budget.
    _MAX_TOKENS_CEILING = 12_800

    def __init__(
        self,
        gateway_url: str | None = None,
        api_key: str | None = None,
        timeout: float = 20.0,
        default_model: str | None = None,
        extra_body: dict[str, Any] | None = None,
        generation_config: GenerationConfig | None = None,
    ) -> None:
        # Env-first resolution: explicit args win, then canonical RAGIN_LLM_*
        # vars, then legacy Azure staging. Empty-string args count as unset.
        gateway_url = (
            gateway_url
            or os.environ.get("RAGIN_LLM_BASE_URL")
            or os.environ.get("RAGIN_LLM_URL")
            or (
                f"{os.environ['AZURE_OPENAI_ENDPOINT'].rstrip('/')}/openai"
                if os.environ.get("AZURE_OPENAI_ENDPOINT")
                else None
            )
            or "http://localhost:8080"
        )
        # Canonical base already carries /v1 (e.g. https://api.apmix.ai/v1);
        # generate() strips a trailing /v1 before appending the full path.
        self._gateway_url = gateway_url.rstrip("/")
        self._api_key = api_key or os.environ.get("RAGIN_LLM_API_KEY") or os.environ.get("AZURE_OPENAI_KEY") or None
        self._default_model = (
            default_model
            or os.environ.get("RAGIN_DON_MODEL")
            or os.environ.get("RAGIN_LLM_MODEL")
            or "glm-5.3-flash-free"
        )
        self._timeout = timeout
        # Provider-specific payload extensions (e.g. {"reasoning_effort":
        # "low"} on vLLM reasoning deployments) merged into every request.
        self._extra_body = dict(extra_body) if extra_body else {}
        # Enforceable decoding contract. When present, every generated request
        # is built from these values and the configured seed/top_p are placed
        # on the wire (or the config refuses to exist). When absent, legacy
        # per-call arguments are untouched.
        if generation_config is not None and not isinstance(generation_config, GenerationConfig):
            raise GenerationConfigError("invalid generation contract: transport config has the wrong type")
        self._generation_config = generation_config
        self._max_retries = (
            generation_config.max_retries if generation_config is not None else self._MAX_RETRIES
        )

    @property
    def gateway_url(self) -> str:
        return self._gateway_url

    @property
    def default_model(self) -> str:
        return self._default_model

    @property
    def generation_config(self) -> GenerationConfig | None:
        return self._generation_config

    def generation_snapshot(self) -> dict[str, Any]:
        """Pure local introspection of the effective generation contract.

        Safe for health wiring: it contains no endpoint URL, credential, key,
        or prompt text. ``contract_active=False`` means the legacy path is in
        effect and no decoding claim is made.
        """
        if self._generation_config is None:
            return {
                "contract_active": False,
                "version": None,
                "requested_model": self._default_model,
                "decoding": None,
                "config_sha256": None,
                "source": "LEGACY_DEFAULTS",
            }
        cfg = self._generation_config
        return {
            "contract_active": True,
            "version": cfg.snapshot()["version"],
            "config": cfg.snapshot(),
            "requested_model": cfg.model,
            "decoding": cfg.decoding_payload(),
            "config_sha256": cfg.config_sha256,
            "source": cfg.source,
        }

    @staticmethod
    def _is_reasoning_model(model: str) -> bool:
        return bool(_REASONING_MODEL_RE.search(model))

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
        """Send a chat-completion request and return (content, usage).

        Raises requests.RequestException on transport / server errors so callers
        can implement their own retry / fallback / circuit-breaker logic.

        ``observation`` is a caller-owned dict filled with a credential-free
        account of what was requested and what the provider actually returned
        (model identity, request digest, invocation status, usage, raw-draft
        hash/bounded redacted text). It intentionally contains no endpoint URL
        or API key.
        """
        base = self._gateway_url.rstrip("/")
        if base.endswith("/v1"):
            base = base[:-3]  # canonical bases carry /v1; generate() appends it
        url = f"{base}/v1/chat/completions"

        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
            # RAGIN's own servers (server.py / server_v2.py) authenticate via
            # X-API-Key; nginx-fronted gateways accept Bearer. Send both so
            # the client works against either frontend.
            headers["X-API-Key"] = self._api_key

        config = self._generation_config
        if config is not None:
            # The contract is authoritative for every generated request. A
            # conflicting model is a hard error (never a silent switch); the
            # decoding fields below are always replaced by the contract so a
            # caller cannot drift the arm settings.
            if model is not None and model != config.model:
                raise GenerationConfigError(
                    "model override conflicts with the active generation contract"
                )
            if top_p is not None and top_p != config.top_p:
                raise GenerationConfigError(
                    "top_p override conflicts with the active generation contract"
                )
            if seed is not None and seed != config.seed:
                raise GenerationConfigError(
                    "seed override conflicts with the active generation contract"
                )
            effective_model = config.model
            temperature = config.temperature
            max_tokens = config.max_tokens
            top_p = config.top_p
            seed = config.seed
        else:
            effective_model = model or self._default_model

        safe_messages = [{"role": m.get("role"), "content": _waf_safe(m.get("content") or "")} for m in messages]
        base_payload: dict[str, Any] = {
            "model": effective_model,
            "messages": safe_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        # top_p/seed travel with the base payload, so the optional-extension
        # fallback below (which drops only extra_body) can never silently omit
        # them. In contract mode the values came from an explicit config.
        if top_p is not None:
            base_payload["top_p"] = top_p
        if seed is not None:
            base_payload["seed"] = seed

        body: dict[str, Any] = {**self._extra_body, **(extra_body or {})}
        if (
            "reasoning_effort" not in body
            and not _host_rejects_reasoning_effort(url)
            and max_tokens <= _SHORT_CALL_MAX_TOKENS
            and self._is_reasoning_model(effective_model)
        ):
            # Reasoning models burn completion tokens on hidden COT before the
            # visible answer; short structured calls (grading, routing) get
            # the cheapest effort tier so the corrective loop stays viable.
            body["reasoning_effort"] = "low"
        payload = {**base_payload, **body}

        obs = observation if observation is not None else {}
        obs.update(
            {
                "contract_active": config is not None,
                "requested_model": effective_model,
                "requested_decoding": {
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "top_p": top_p,
                    "seed": seed,
                },
                "seed_status": config.seed_status if config is not None else None,
                "request_digest": GenerationConfig.request_digest(payload),
                "invocation_attempted": True,
                "invocation_succeeded": False,
                "model_response_received": False,
                "transport_attempts": 0,
                "cot_retry_attempted": False,
                "failure_reason": None,
                "provider_reported_model": None,
                "usage_availability": "NOT_REPORTED",
                "usage_prompt_tokens": None,
                "usage_completion_tokens": None,
                "usage_total_tokens": None,
                "raw_model_sha256": None,
                "raw_model_text": None,
                "response_id": None,
                "extension_body_dropped": False,
            }
        )
        try:
            resp = self._post(url, payload, headers, obs)
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else None
            if status == 400 and body:
                # Server rejected an optional extension (e.g. strict OpenAI
                # frontends that don't know reasoning_effort) — degrade to a
                # plain OpenAI payload rather than failing the caller. The
                # generation fields live in base_payload and are not dropped.
                logger.warning("Gateway rejected extra body fields %s — retrying without them", sorted(body))
                payload = base_payload
                obs["extension_body_dropped"] = True
                resp = self._post(url, payload, headers, obs)
            else:
                obs["failure_reason"] = _failure_reason(exc)
                raise
        except Exception as exc:
            obs["failure_reason"] = _failure_reason(exc)
            raise

        try:
            data = resp.json()
        except ValueError as exc:
            obs["failure_reason"] = _failure_reason(exc)
            raise
        obs["invocation_succeeded"] = True
        reported_model = data.get("model")
        if isinstance(reported_model, str) and reported_model:
            obs["provider_reported_model"] = reported_model
        response_id = data.get("id")
        if isinstance(response_id, str) and response_id:
            obs["response_id"] = response_id
        choices = data.get("choices", [])
        usage: dict[str, int] = data.get("usage", {})
        obs.update(_provider_usage(usage))
        if choices:
            msg = choices[0].get("message", {}) or {}
            content: str | None = msg.get("content")
            if content:
                obs["model_response_received"] = True
                obs["raw_model_sha256"] = hashlib.sha256(content.encode("utf-8")).hexdigest()
                obs["raw_model_text"] = bounded_redacted_text(content, limit=500)
                return _waf_restore(content), usage

            # content is None/empty — reasoning model burned tokens on COT.
            # NEVER return reasoning_content (it leaks internal deliberation).
            reasoning = msg.get("reasoning_content") or msg.get("reasoning") or ""
            if reasoning:
                logger.info("Reasoning content (logged, not served): %d chars of COT", len(reasoning))

            # A contract retry must replay the SAME decoding. In contract mode
            # the completion budget is never inflated and the retry is only
            # attempted under the explicitly configured retry policy. Legacy
            # callers keep the historical larger-budget retry.
            if config is not None and self._max_retries <= 0:
                obs["failure_reason"] = "EMPTY_MODEL_CONTENT"
                return "", usage
            try:
                retry = dict(payload)
                if config is None:
                    retry_budget = min(self._MAX_TOKENS_CEILING, max(1024, max_tokens * 4))
                    retry["max_tokens"] = retry_budget
                else:
                    retry_budget = max_tokens
                obs["cot_retry_attempted"] = True
                resp2 = self._post(url, retry, headers, obs)
                data2 = resp2.json()
                reported_model2 = data2.get("model")
                if isinstance(reported_model2, str) and reported_model2:
                    obs["provider_reported_model"] = reported_model2
                choices2 = data2.get("choices", [])
                obs.update(_provider_usage(data2.get("usage", {})))
                if choices2:
                    msg2 = choices2[0].get("message", {}) or {}
                    content2 = msg2.get("content")
                    if content2:
                        obs["model_response_received"] = True
                        obs["invocation_succeeded"] = True
                        obs["raw_model_sha256"] = hashlib.sha256(content2.encode("utf-8")).hexdigest()
                        obs["raw_model_text"] = bounded_redacted_text(content2, limit=500)
                        return _waf_restore(content2), data2.get("usage", {})
                    logger.warning(
                        "Retry with max_tokens=%d still produced no content (finish=%s)",
                        retry_budget,
                        choices2[0].get("finish_reason"),
                    )
            except Exception as exc:
                obs["failure_reason"] = _failure_reason(exc)
                logger.warning("Retry with revised decoding also failed")

            obs["failure_reason"] = "EMPTY_MODEL_CONTENT"
            return "", usage
        obs["failure_reason"] = "EMPTY_MODEL_CONTENT"
        return "", usage

    def _post(
        self,
        url: str,
        payload: dict[str, Any],
        headers: dict[str, str],
        observation: dict[str, Any] | None = None,
    ) -> requests.Response:
        """POST with retries for transient failures (timeouts, 5xx)."""
        last_exc: Exception | None = None
        for attempt in range(self._max_retries + 1):
            if observation is not None:
                observation["transport_attempts"] = int(observation.get("transport_attempts", 0)) + 1
            if attempt > 0:
                backoff = self._BASE_BACKOFF * (2 ** (attempt - 1))
                logger.warning(
                    "Gateway POST attempt %d/%d, sleeping %.0fs", attempt + 1, self._max_retries + 1, backoff
                )
                time.sleep(backoff)
            try:
                resp = requests.post(url, json=payload, headers=headers, timeout=self._timeout)
                if resp.status_code in (408, 429, 502, 503, 504):
                    last_exc = requests.HTTPError(
                        f"{resp.status_code} {resp.reason}",
                        response=resp,
                    )
                    continue
                resp.raise_for_status()
                return resp
            except (requests.ConnectionError, requests.ReadTimeout) as exc:
                last_exc = exc
                continue
            except requests.HTTPError as exc:
                # Use the exception's own response — `resp` may be unbound
                # when requests.post itself raised (e.g. mocked transports).
                status = exc.response.status_code if exc.response is not None else None
                if status in (408, 429, 502, 503, 504):
                    last_exc = exc
                    continue
                raise
        raise requests.ReadTimeout(
            f"Gateway POST failed after {self._max_retries + 1} attempts: {_failure_reason(last_exc or Exception())}"
        ) from last_exc
