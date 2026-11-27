#!/usr/bin/env python3
"""Deterministic loopback OpenAI-compatible mock provider for RAGIN integration tests.

Real running HTTP process. Bound only to 127.0.0.1. No internet. No keys.
"""
from __future__ import annotations
import json
import logging
import sys
import time
from aiohttp import web

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("mock_provider")

# Deterministic responses keyed on model + a simple method/content shape.
RESPONSES = {
    ("chat completions", "opencode/space-bunny-free"): {
        "id": "mockcmpl-determ-001",
        "object": "chat.completion",
        "created": None,
        "model": "opencode/space-bunny-free",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Deterministic mock candidate — bridge verifier artifact will canonicalize served output.",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    },
}

async def handler(request: web.Request) -> web.Response:
    started = time.monotonic()
    try:
        data = await request.json()
    except Exception:
        data = {}
    model = (data.get("model") or "").strip()
    messages = data.get("messages") or []
    body = {"model": model, "messages": messages}
    log.info("request model=%r msg_count=%d", model, len(messages))
    resp = RESPONSES.get(("chat completions", model))
    if resp is None:
        resp = RESPONSES.get(("chat completions", ""))
    if resp is None:
        return web.json_response({"error": {"message": "no mock for model", "type": "invalid_request_error"}}, status=400)
    resp = dict(resp)
    resp["created"] = int(time.time())
    payload = json.dumps(resp).encode("utf-8")
    log.info("responded model=%r len=%d elapsed=%.3fs", model, len(payload), time.monotonic() - started)
    return web.Response(body=payload, content_type="application/json")

async def health(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})

def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--port", type=int, default=8731)
    p.add_argument("--host", default="127.0.0.1")
    args = p.parse_args()
    app = web.Application()
    app.router.add_post("/v1/chat/completions", handler)
    app.router.add_get("/health", health)
    log.info("mock provider starting on %s:%d", args.host, args.port)
    web.run_app(app, host=args.host, port=args.port)

if __name__ == "__main__":
    main()
