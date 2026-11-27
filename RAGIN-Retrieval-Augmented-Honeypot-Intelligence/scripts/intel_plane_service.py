#!/usr/bin/env python3
"""Intel plane HTTP service — wraps cve-mcp intel clients behind /enrich.

Runs on the intel-plane host (outbound 443 to NVD/EPSS/KEV allowlisted).
The honeypot plane (egress-locked) POSTs {"text": ..., "targets": [...]} and
receives labeled evidence hits. Bounded, cached, fail-graceful.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, os.environ.get("CVE_MCP_SRC", "/opt/intel/cve-mcp-server/src"))
CACHE = os.environ.get("CVE_MCP_CACHE", "/opt/intel/cache.db")
NVD_RATE = float(os.environ.get("NVD_RATE", "0.5"))

_loop = asyncio.new_event_loop()
_pool = ThreadPoolExecutor(max_workers=2)


def _run(coro):
    return _loop.run_until_complete(coro)


def _boot():
    asyncio.set_event_loop(_loop)
    import httpx
    from cve_mcp.cache.sqlite_cache import VulnCache
    global _CLIENT, _CACHE, _LIMITER
    _CACHE = VulnCache(CACHE)
    _CLIENT = httpx.AsyncClient(timeout=40)


def enrich(text: str, targets: list[list[str]]) -> list[dict]:
    from cve_mcp.api.nvd_client import search_nvd
    from cve_mcp.api.rate_limiter import TokenBucketRateLimiter

    async def one(name: str):
        limiter = TokenBucketRateLimiter(rate=NVD_RATE, capacity=3)
        try:
            res = await search_nvd(name, "", 3, _CLIENT, limiter, _CACHE)
            return res or []
        except Exception:
            return []

    hits: list[dict] = []
    seen: set[str] = set()
    for name, version in targets[:4]:
        records = _run(one(name))
        for rec in records[:2]:
            if not isinstance(rec, dict) or not rec.get("id") or rec["id"] in seen:
                continue
            seen.add(rec["id"])
            desc = next((d.get("value", "") for d in rec.get("descriptions", [])
                         if d.get("lang") == "en"), "") or str(rec["id"])
            hits.append({
                "doc_id": str(rec["id"]),
                "title": f"LIVE NVD: {name} {version} — {rec['id']}",
                "content": desc[:700] + " [live intel: verify against the session fiction before use]",
                "source": "cve-mcp/nvd",
                "score": 0.55,
                "hybrid_score": 0.55,
                "metadata": {"intel_plane": True, "keyword": name,
                             "published": rec.get("published")},
            })
    return hits[:8]


class Handler(BaseHTTPRequestHandler):
    def _json(self, code: int, obj: dict) -> None:
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self._json(200, {"status": "ok", "plane": "intel"})
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/enrich":
            self._json(404, {"error": "not found"})
            return
        try:
            length = min(int(self.headers.get("Content-Length", "0")), 65536)
            payload = json.loads(self.rfile.read(length) or b"{}")
            text = str(payload.get("text", ""))[:4000]
            targets = [t[:2] for t in payload.get("targets", []) if isinstance(t, list)]
            hits = _pool.submit(enrich, text, targets).result(timeout=90)
            self._json(200, {"hits": hits})
        except Exception as exc:  # noqa: BLE001 — fail-graceful to static corpus
            self._json(200, {"hits": [], "error": str(exc)[:200]})

    def log_message(self, fmt, *args):  # quiet
        pass


if __name__ == "__main__":
    _boot()
    port = int(os.environ.get("INTEL_PORT", "8000"))
    bind = os.environ.get("INTEL_BIND", "0.0.0.0")
    ThreadingHTTPServer((bind, port), Handler).serve_forever()
