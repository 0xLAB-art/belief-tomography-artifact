"""Shared rate gate for the beatapi free tier (1 successful request/minute).

All panel jobs (out-of-sample probe, cross-family jury, v3 attacker brain)
share one key and one limit; every call must pass through wait_gate() before
the request and gate_mark() after a successful response.

SSRF policy (same contract as scripts/ai_jury_v1.py): https only, hostname
must equal the allowlisted host, and every resolved address must be public —
loopback, private, link-local, reserved, and multicast addresses are refused,
and the URL is rebuilt from the validated endpoint constant rather than from
caller input.
"""

import ipaddress
import json
import socket
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
_APINEX_WAIT_UNTIL = 0.0
_LAST = Path("/tmp/beatapi_last_ok")
MIN_INTERVAL = 62.0

ALLOWED_HOST = "api.beatapi.io"
ENDPOINT = "https://api.beatapi.io/v1/chat/completions"


def load_env(path: Path | None = None) -> dict[str, str]:
    env: dict[str, str] = {}
    for line in (path or ROOT / ".env").read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip()
    return env


def guarded_endpoint() -> str:
    """Validate the fixed endpoint against the egress policy; return its URL."""
    parsed = urlparse(ENDPOINT)
    if parsed.scheme != "https":
        raise ValueError(f"refused non-https scheme: {parsed.scheme!r}")
    if (parsed.hostname or "").lower() != ALLOWED_HOST:
        raise ValueError(f"refused host outside allowlist: {parsed.hostname!r}")
    for info in socket.getaddrinfo(ALLOWED_HOST, 443, proto=socket.IPPROTO_TCP):
        ip = ipaddress.ip_address(info[4][0])
        if (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
                or ip.is_multicast or ip.is_unspecified):
            raise ValueError(f"refused non-public address {ip} for {ALLOWED_HOST}")
    return ENDPOINT


def gate_wait() -> None:
    if _LAST.exists():
        elapsed = time.time() - _LAST.stat().st_mtime
        if elapsed < MIN_INTERVAL:
            time.sleep(MIN_INTERVAL - elapsed)


def gate_mark() -> None:
    _LAST.write_text(str(time.time()))


def chat(model: str, messages: list[dict], max_tokens: int = 400,
         timeout: float = 300.0) -> str:
    """One gated chat-completions call to the validated endpoint. Raises on failure."""
    env = load_env()
    key = env.get("RAGIN_JEVI_API_KEY", "")
    if not key:
        raise RuntimeError("RAGIN_JEVI_API_KEY missing")
    url = guarded_endpoint()
    gate_wait()
    req = urllib.request.Request(
        url,
        data=json.dumps({"model": model, "messages": messages,
                         "max_tokens": max_tokens}).encode(),
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            doc = json.loads(resp.read())
        gate_mark()
        return (doc.get("choices") or [{}])[0].get("message", {}).get("content", "")
    except urllib.error.HTTPError as exc:
        # Stamp EVERY attempt: the limiter counts recent requests, so a 429
        # must cool a full window before the next call — otherwise callers
        # that retry without a success stamp hammer the endpoint.
        _LAST.write_text(str(time.time()))
        if exc.code == 429:
            time.sleep(MIN_INTERVAL)
        raise


# apinex.bond free tier: non-OpenAI families (gemini/qwen/kimi/deepseek/glm).
APINEX_HOST = "api.apinex.bond"
APINEX_ENDPOINT = "https://api.apinex.bond/v1/chat/completions"


def _guarded(host: str, endpoint: str) -> str:
    """SSRF guard shared by both providers: https, allowlisted host, public IPs."""
    parsed = urlparse(endpoint)
    if parsed.scheme != "https":
        raise ValueError(f"refused non-https scheme: {parsed.scheme!r}")
    if (parsed.hostname or "").lower() != host:
        raise ValueError(f"refused host outside allowlist: {parsed.hostname!r}")
    for info in socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP):
        ip = ipaddress.ip_address(info[4][0])
        if (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
                or ip.is_multicast or ip.is_unspecified):
            raise ValueError(f"refused non-public address {ip} for {host}")
    return endpoint


def apinex_chat(model: str, messages: list[dict], max_tokens: int = 400,
                timeout: float = 120.0) -> str:
    """Chat call to api.apinex.bond (free tier). Requires an explicit
    User-Agent — the gateway 403s python-urllib's default. No rate limit
    observed at bursts of 6+ calls."""
    env = load_env()
    key = env.get("APINEX_API_KEY", "")
    if not key:
        raise RuntimeError("APINEX_API_KEY missing")
    url = _guarded(APINEX_HOST, APINEX_ENDPOINT)
    headers = {"Authorization": f"Bearer {key}",
               "Content-Type": "application/json",
               "User-Agent": "ragin-v3/1.0", "Accept": "application/json"}
    # Adaptive pacing: the gateway reports x-ratelimit-remaining/reset on
    # every response; sleep until the window resets before exhausting it.
    global _APINEX_WAIT_UNTIL
    if _APINEX_WAIT_UNTIL > time.time():
        time.sleep(_APINEX_WAIT_UNTIL - time.time())
    req = urllib.request.Request(
        url,
        data=json.dumps({"model": model, "messages": messages,
                         "max_tokens": max_tokens}).encode(),
        headers={**headers})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        doc = json.loads(resp.read())
        rem = resp.headers.get("x-ratelimit-remaining")
        rst = resp.headers.get("x-ratelimit-reset")
        if rem is not None and rem.isdigit() and int(rem) <= 1 and rst:
            _APINEX_WAIT_UNTIL = float(rst)
    return (doc.get("choices") or [{}])[0].get("message", {}).get("content", "")
