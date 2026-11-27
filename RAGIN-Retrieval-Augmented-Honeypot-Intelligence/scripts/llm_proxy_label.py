"""Minimal LLM proxy labeler.

Reads a JSON payload from argv[1], sends it to the RAGIN gateway /v1/chat/completions,
parses the rubric-format response, and prints ONLY the parsed JSON label.

This is a lightweight standalone script so the labeling pipeline can run without
importing the full RAGIN server stack.
"""
from __future__ import annotations

import json
import os
import sys
import time

import httpx

GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://localhost:8080")
API_KEY = os.environ.get("API_KEY", "")


def main() -> None:
    payload = json.loads(sys.argv[1])
    body = {
        "model": "deepseek-v4-flash-free",
        "messages": [
            {"role": "system", "content": payload["rubric"]},
            {"role": "user", "content": payload["task"] + "\n\nCommands:\n" + "\n".join(payload["commands"])},
        ],
        "temperature": 0.0,
        "max_tokens": 512,
        "response_format": {"type": "json_object"},
    }
    headers = {}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
    t0 = time.time()
    try:
        r = httpx.post(
            f"{GATEWAY_URL}/v1/chat/completions",
            headers=headers,
            json=body,
            timeout=30.0,
        )
        elapsed = round(time.time() - t0, 2)
        resp = r.json()
        content = resp.get("choices", [{}])[0].get("message", {}).get("content", "")
        parsed = json.loads(content.strip())
        parsed["_elapsed_s"] = elapsed
        parsed["_raw"] = content
        print(json.dumps(parsed))
    except Exception as e:
        print(json.dumps({"_error": str(e), "_elapsed_s": round(time.time() - t0, 2)}))


if __name__ == "__main__":
    main()
