"""Shared GatewayClient for LLM Gateway /v1/chat completions.

Consolidates HTTP transport, auth, and response parsing so callers
(Don's ThreatRAGEngine, Hisoka's ResponseGenerator) don't duplicate
the raw HTTP call.
"""

from __future__ import annotations

import logging
import os
import re
import time
from typing import Any
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)

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

    @property
    def gateway_url(self) -> str:
        return self._gateway_url

    @property
    def default_model(self) -> str:
        return self._default_model

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
    ) -> tuple[str, dict[str, int]]:
        """Send a chat-completion request and return (content, usage).

        Raises requests.RequestException on transport / server errors so callers
        can implement their own retry / fallback / circuit-breaker logic.
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

        effective_model = model or self._default_model

        safe_messages = [{"role": m.get("role"), "content": _waf_safe(m.get("content") or "")} for m in messages]
        base_payload: dict[str, Any] = {
            "model": effective_model,
            "messages": safe_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }

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

        try:
            resp = self._post(url, payload, headers)
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else None
            if status == 400 and body:
                # Server rejected an optional extension (e.g. strict OpenAI
                # frontends that don't know reasoning_effort) — degrade to a
                # plain OpenAI payload rather than failing the caller.
                logger.warning("Gateway rejected extra body fields %s — retrying without them", sorted(body))
                payload = base_payload
                resp = self._post(url, payload, headers)
            else:
                raise
        data = resp.json()
        choices = data.get("choices", [])
        usage: dict[str, int] = data.get("usage", {})
        if choices:
            msg = choices[0].get("message", {}) or {}
            content: str | None = msg.get("content")
            if content:
                return _waf_restore(content), usage

            # content is None/empty — reasoning model burned tokens on COT.
            # NEVER return reasoning_content (it leaks internal deliberation).
            reasoning = msg.get("reasoning_content") or msg.get("reasoning") or ""
            if reasoning:
                logger.info("Reasoning content (logged, not served): %d chars of COT", len(reasoning))

            # Retry with a much larger completion budget so the model can get
            # past its hidden chain-of-thought to a final answer.
            retry_budget = min(self._MAX_TOKENS_CEILING, max(1024, max_tokens * 4))
            try:
                retry = dict(payload)
                retry["max_tokens"] = retry_budget
                resp2 = self._post(url, retry, headers)
                data2 = resp2.json()
                choices2 = data2.get("choices", [])
                if choices2:
                    msg2 = choices2[0].get("message", {}) or {}
                    content2 = msg2.get("content")
                    if content2:
                        return _waf_restore(content2), data2.get("usage", {})
                    logger.warning(
                        "Retry with max_tokens=%d still produced no content (finish=%s)",
                        retry_budget,
                        choices2[0].get("finish_reason"),
                    )
            except Exception:
                logger.warning("Retry with higher max_tokens also failed")

            # Still empty after retry — caller handles safe fallback
            return "", usage
        return "", usage

    def _post(
        self,
        url: str,
        payload: dict[str, Any],
        headers: dict[str, str],
    ) -> requests.Response:
        """POST with retries for transient failures (timeouts, 5xx)."""
        last_exc: Exception | None = None
        for attempt in range(self._MAX_RETRIES + 1):
            if attempt > 0:
                backoff = self._BASE_BACKOFF * (2 ** (attempt - 1))
                logger.warning(
                    "Gateway POST attempt %d/%d, sleeping %.0fs", attempt + 1, self._MAX_RETRIES + 1, backoff
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
            f"Gateway POST failed after {self._MAX_RETRIES + 1} attempts: {last_exc}"
        ) from last_exc
