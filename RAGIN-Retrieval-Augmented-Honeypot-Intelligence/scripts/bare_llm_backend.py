#!/usr/bin/env python3
"""Arm-B bare LLM backend — the field honeypot's generator, nothing else.

Cowrie terminates the attacker's SSH session and its (native upstream) LLM
backend POSTs the conversation to this service. We translate the OpenAI-
compatible request into a GatewayClient generation call — persona system
prompt + attacker input — and return the completion in the exact response
shape cowrie's LLMClient parses.

Deliberately absent (that is the experiment): no CTI retrieval (Don), no
fiction graph, no deterministic verifier, no fail-closed fallback, no
honeytokens. It is the in-field counterpart of the external-baseline
``llm_unverified`` arm: the same persona prompt and the same generator, so
the field study isolates architecture, not model choice.

Env contract (all from .env.field, mirrored in .env.field.example):
    RAGIN_LLM_BASE_URL  — gateway base (canonical form carries /v1)
    RAGIN_LLM_API_KEY   — gateway key (sent as Bearer + X-API-Key)
    RAGIN_LLM_MODEL     — generator model (default deepseek-v4-flash-free)
    BARE_BACKEND_PORT   — bind port (default 8084)
    RAGIN_BIND_HOST     — bind host (default 127.0.0.1; compose sets 0.0.0.0)
    API_KEY             — if set, incoming requests must carry it as
                          X-API-Key or Bearer (cowrie.cfg [llm] api_key)
    BARE_PERSONA_PROMPT — optional persona override (defaults to the
                          llm_unverified arm's pinned prompt)

Run:  python -m scripts.bare_llm_backend   (or: python scripts/bare_llm_backend.py)
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import time
from pathlib import Path

from aiohttp import web

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ragin.gateway.client import GatewayClient  # noqa: E402

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
API_KEY = os.environ.get("API_KEY", "")

logger = logging.getLogger("bare_llm_backend")

# Pinned persona prompt — byte-identical to the llm_unverified arm in
# scripts/run_external_baseline.py so the field arm B measures the same
# architecture the external baseline measured.
_PERSONA_PROMPT = (
    "You are a slightly misconfigured but real Ubuntu 22.04 web/database server. "
    "Answer the attacker's input exactly as that machine's shell or service would. "
    "Output only the machine's response — no commentary, no refusals, no explanations. "
    "If asked for credentials, print a plausible credentials document. "
    "If asked about the system, print realistic command output."
)

_MAX_TRANSCRIPT_CHARS = 24_000


def _extract_attacker_input(messages: list) -> str:
    """Cowrie sends a system prompt (its Linux-server simulation instruction),
    then alternating turns, ending with the attacker's command as the last
    user message. We drop cowrie's system prompt (we have our own persona)
    and keep the rest of the transcript as context for the generator."""
    user_texts = [str(m.get("content", "")) for m in messages if isinstance(m, dict) and m.get("role") == "user"]
    if not user_texts:
        return ""
    return user_texts[-1]


def _transcript_context(messages: list) -> str:
    """Recent-turn context (everything except the final user message) so
    follow-up commands stay consistent within a session."""
    if len(messages) <= 1:
        return ""
    parts = []
    for m in messages[:-1]:
        if not isinstance(m, dict):
            continue
        role = m.get("role", "?")
        content = str(m.get("content", ""))[:400]
        parts.append(f"{role}: {content}")
    ctx = "\n".join(parts)
    return ctx[-_MAX_TRANSCRIPT_CHARS:]


def _authorized(request: web.Request) -> bool:
    if not API_KEY:
        return True
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer ") and auth[len("Bearer ") :] == API_KEY:
        return True
    return request.headers.get("X-API-Key", "") == API_KEY


async def chat_completions(request: web.Request) -> web.Response:
    if not _authorized(request):
        return web.json_response({"error": "Unauthorized"}, status=401)
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON body"}, status=400)

    messages = data.get("messages") or []
    if not isinstance(messages, list):
        return web.json_response({"error": "messages must be a list"}, status=400)

    attacker_input = _extract_attacker_input(messages)
    if not attacker_input:
        return web.json_response({"error": "no user message"}, status=400)

    client: GatewayClient = request.app["gateway"]
    persona: str = request.app["persona"]
    gen_messages = [{"role": "system", "content": persona}]

    ctx = _transcript_context(messages)
    if ctx:
        # Recent turns as context; the persona block stays authoritative.
        gen_messages.append({"role": "system", "content": f"Session transcript so far (context only):\n{ctx}"})
    gen_messages.append({"role": "user", "content": attacker_input})

    try:
        # GatewayClient.generate is sync (requests); keep the event loop free
        # for concurrent cowrie sessions by running it in a worker thread.
        content, _usage = await asyncio.to_thread(
            client.generate,
            gen_messages,
            request.app["model"],
            0.2,
            500,
        )
    except Exception as exc:  # noqa: BLE001 — fail-safe text, not a verified serve
        logger.warning("generation error: %s", exc)
        content = ""

    if not content:
        # No deterministic fallback on this arm BY DESIGN (it is the baseline
        # being measured) — but the session must never hang. Serve a minimal
        # plausible-looking error line and log it loudly.
        logger.error("bare backend produced no content — serving empty-shell line")
        content = "bash: syntax error near unexpected token"

    payload = {
        "id": f"chatcmpl-bare-{int(time.time() * 1000)}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": data.get("model") or request.app["model"],
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }
    return web.json_response(payload)


async def health(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok", "arm": "vanilla_llm"})


def main() -> None:
    logging.basicConfig(
        level=LOG_LEVEL,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    gateway_url = os.environ.get("RAGIN_LLM_BASE_URL", "http://localhost:8080").rstrip("/")
    api_key = os.environ.get("RAGIN_LLM_API_KEY") or ""
    model = os.environ.get("RAGIN_LLM_MODEL", "deepseek-v4-flash-free")
    port = int(os.environ.get("BARE_BACKEND_PORT", "8084"))
    bind_host = os.environ.get("RAGIN_BIND_HOST", "127.0.0.1")
    persona = os.environ.get("BARE_PERSONA_PROMPT", _PERSONA_PROMPT)

    if not api_key:
        logger.warning("RAGIN_LLM_API_KEY unset — generator calls will be unauthenticated and will likely fail")

    app = web.Application()
    app["gateway"] = GatewayClient(gateway_url=gateway_url, api_key=api_key, default_model=model, timeout=45.0)
    app["model"] = model
    app["persona"] = persona

    app.router.add_get("/health", health)
    app.router.add_post("/v1/chat/completions", chat_completions)

    logger.info(
        "bare_llm_backend: gateway=%s model=%s bind=%s:%d auth=%s",
        gateway_url,
        model,
        bind_host,
        port,
        "on" if API_KEY else "OFF (loopback/internal-net only!)",
    )
    web.run_app(app, host=bind_host, port=port)


if __name__ == "__main__":
    main()
