"""IntelEnricher — live CVE intelligence for Don's retrieval pool (MCP-backed).

Bridges the cve-mcp-server intel clients (NVD/EPSS/KEV/ATT&CK) into the RAG
evidence pipeline. When an attacker session references software with versions
(OpenSSH, nginx, mysql, ...), the enricher pulls live CVE records and emits
them as bounded evidence documents into the same pool the hybrid retriever
draws from — the fiction stays current and believable.

Safety contract:
- Every intel document is labeled (source: cve-mcp/nvd|epss|kev) and enters
  Don's pipeline as UNTRUSTED evidence — it flows through the same verified
  serving loop as everything else (no direct prompt access).
- Fail-graceful: any intel failure returns [] and the static corpus continues.
- Bounded: max_queries per call, TTL cache via the MCP server's own SQLite.

Deployment: the enricher runs where outbound 443 to the intel APIs is
allowlisted (the intel plane). On the locked-down field CORE it is disabled
by default and enabled only when the intel plane is reachable.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

# Software fingerprints worth enriching: name -> NVD keyword + version regex
_SOFTWARE_SIGNATURES: tuple[tuple[str, str, str], ...] = (
    ("openssh", r"openssh[_ -]?([\d.p]+)", "OpenSSH {ver}"),
    ("nginx", r"nginx[/ ]([\d.]+)", "nginx {ver}"),
    ("apache", r"apache[/ ]([\d.]+)", "Apache HTTP Server {ver}"),
    ("mysql", r"mysql[^a-z]?\s*(?:Ver\s*)?([\d.]+)", "MySQL {ver}"),
    ("postgres", r"postgresql?\s*([\d.]+)", "PostgreSQL {ver}"),
    ("vsftpd", r"vsftpd\s*([\d.]+)", "vsftpd {ver}"),
    ("sudo", r"sudo\s*([\d.p]+)", "sudo {ver}"),
    ("openssl", r"openssl\s*([\d.a-z]+)", "OpenSSL {ver}"),
    ("kernel", r"linux version (\d+\.\d+[\d.-]*)", "Linux kernel {ver}"),
)

_MAX_QUERIES = 4
_DOC_CHAR_BUDGET = 700


@dataclass
class IntelDoc:
    doc_id: str
    title: str
    content: str
    source: str
    score: float
    metadata: dict[str, Any]

    def as_hit(self) -> dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "title": self.title,
            "content": self.content[:_DOC_CHAR_BUDGET],
            "source": self.source,
            "score": self.score,
            "hybrid_score": self.score,
            **({"relevance_grade": "high"} if self.metadata.get("kev") else {}),
            "metadata": {
                "intel_plane": True,
                "epss": self.metadata.get("epss"),
                "kev": self.metadata.get("kev"),
                "cvss": self.metadata.get("cvss"),
            },
        }


def detect_software(text: str) -> list[tuple[str, str]]:
    """Extract (name, version) pairs from session text. Bounded to first 4."""
    found: list[tuple[str, str]] = []
    seen: set[str] = set()
    for name, pattern, _label in _SOFTWARE_SIGNATURES:
        if len(found) >= _MAX_QUERIES:
            break
        m = re.search(pattern, text, re.IGNORECASE)
        if m and m.group(1) and name not in seen:
            found.append((name, m.group(1)))
            seen.add(name)
    return found


class IntelEnricher:
    """Async enrichment over the cve-mcp-server intel clients.

    Two modes:
    - local: imports the cve-mcp clients directly (intel plane on the same host)
    - http:  POSTs to a remote intel-plane service (CVE_INTEL_URL) — the mode
      used on the egress-locked honeypot plane (thin client, no cve_mcp import)
    """

    def __init__(self, cache_path: str = "/tmp/cve-mcp-cache.db", nvd_rate: float = 0.5) -> None:
        self._cache_path = cache_path
        self._nvd_rate = nvd_rate
        self._url = os.environ.get("CVE_INTEL_URL", "").rstrip("/")
        self._timeout = float(os.environ.get("CVE_INTEL_TIMEOUT", "25"))
        self._ready = True
        if not self._url:
            try:
                sys_path = os.environ.get("CVE_MCP_SRC", "/tmp/cve-mcp-server/src")
                if sys_path not in __import__("sys").path:
                    __import__("sys").path.insert(0, sys_path)
                import httpx  # noqa: F401
                from cve_mcp.cache.sqlite_cache import VulnCache  # noqa: F401
            except Exception as exc:  # noqa: BLE001
                logger.warning("intel plane unavailable: %s", exc)
                self._ready = False

    @property
    def available(self) -> bool:
        return self._ready

    async def enrich(self, session_text: str) -> list[dict[str, Any]]:
        """Return evidence hits for software referenced in the session text."""
        if not self._ready:
            return []
        targets = detect_software(session_text)
        if not targets:
            return []
        if self._url:
            return await self._enrich_http(targets, session_text)
        return await self._enrich_local(targets)

    async def _enrich_http(self, targets: list[tuple[str, str]], session_text: str) -> list[dict[str, Any]]:
        import requests
        try:
            r = requests.post(f"{self._url}/enrich",
                              json={"text": session_text[-2000:], "targets": [list(t) for t in targets]},
                              timeout=self._timeout)
            r.raise_for_status()
            return r.json().get("hits", [])[:_MAX_QUERIES * 2]
        except Exception as exc:  # noqa: BLE001
            logger.warning("intel plane HTTP error: %s", exc)
            return []

    def enrich_sync_http(self, session_text: str) -> list[dict[str, Any]]:
        """HTTP-mode synchronous enrichment (no event loop required)."""
        targets = detect_software(session_text)
        if not targets:
            return []
        import requests
        r = requests.post(f"{self._url}/enrich",
                          json={"text": session_text[-2000:], "targets": [list(t) for t in targets]},
                          timeout=self._timeout)
        r.raise_for_status()
        return r.json().get("hits", [])[:_MAX_QUERIES * 2]

    async def _enrich_local(self, targets: list[tuple[str, str]]) -> list[dict[str, Any]]:
        import httpx
        from cve_mcp.cache.sqlite_cache import VulnCache
        from cve_mcp.api.rate_limiter import TokenBucketRateLimiter

        hits: list[dict[str, Any]] = []
        cache = VulnCache(self._cache_path)
        limiter = TokenBucketRateLimiter(rate=self._nvd_rate, capacity=3)
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                for name, version in targets[:_MAX_QUERIES]:
                    try:
                        from cve_mcp.api.nvd_client import search_nvd
                        results = await search_nvd(name, "", 3, client, limiter, cache)
                        for rec in (results or [])[:2]:
                            if not isinstance(rec, dict) or not rec.get("id"):
                                continue
                            desc = next((d.get("value", "") for d in rec.get("descriptions", [])
                                         if d.get("lang") == "en"), "") or str(rec.get("id"))
                            cvss = _extract(r'"baseScore":\s*([\d.]+)', json_dumps(rec))
                            hits.append(IntelDoc(
                                doc_id=str(rec["id"]),
                                title=f"LIVE NVD: {name} {version} — {rec['id']}",
                                content=f"{desc} [live intel: verify against the session fiction before use]",
                                source="cve-mcp/nvd",
                                score=0.55,
                                metadata={"keyword": name, "cvss": cvss,
                                          "published": rec.get("published")},
                            ).as_hit())
                    except Exception as exc:  # noqa: BLE001
                        logger.warning("intel query failed for %s: %s", name, exc)
        except Exception as exc:  # noqa: BLE001
            logger.warning("intel plane error: %s", exc)
            return []
        return hits[:_MAX_QUERIES * 2]


def json_s(obj: Any) -> str:
    return json_dumps(obj)


def json_dumps(obj: Any) -> str:
    import json
    return json.dumps(obj, default=str)


def _extract(pattern: str, text: str) -> str | None:
    m = re.search(pattern, text)
    return m.group(1) if m else None


def enrich_sync(session_text: str) -> list[dict[str, Any]]:
    """Synchronous wrapper safe to call from a running event loop (the aiohttp
    server): the enrichment runs in its own thread with a private loop."""
    if os.environ.get("RAGIN_INTEL_ENABLED", "0").strip().lower() not in {"1", "true", "yes", "on"}:
        return []
    if os.environ.get("CVE_INTEL_URL", ""):
        # HTTP mode: no nested loop needed — plain requests in this thread.
        try:
            return IntelEnricher().enrich_sync_http(session_text)
        except Exception as exc:  # noqa: BLE001
            logger.warning("enrich_sync http failed: %s", exc)
            return []
    try:
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(lambda: asyncio.run(IntelEnricher().enrich(session_text)),
                               ).result(timeout=60)
    except Exception as exc:  # noqa: BLE001
        logger.warning("enrich_sync failed: %s", exc)
        return []
