#!/usr/bin/env python3
"""apmix catalog + quota watch — appends one probe to a JSONL history.

Checks (0 tokens when quota is exhausted; exactly 1 token when live):
  1. catalog — GET /models (free): are the wired models still listed?
  2. quota   — 1-token live probe on the configured transport style
               (POST /chat/completions, or POST /responses when
               RAGIN_LLM_API_STYLE=responses).
  3. reseed  — if any raw benchmark run is newer than its judge-audited
     sibling, re-run the panel audit and audited stability offline so the
     published numbers stay consistent with the artifacts (never calls the
     LLM; see scripts/reseed_audit_pipeline.py).

Emits/updates:
  results/apmix_probe_history.jsonl  — one JSON line per probe (append-only)
  results/apmix_quota_status.json    — latest probe (what the snapshot doc renders)

Exit codes (systemd Unit Failure semantics):
  exit 0 healthy · exit 2 catalog drift · exit 3 reseeded but stability
  verdict is ``review`` · exit 1 probe/network failure

Standalone:  python3 scripts/check_apmix_catalog.py
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

HISTORY = ROOT / "results" / "apmix_probe_history.jsonl"
STATUS = ROOT / "results" / "apmix_quota_status.json"


def _env(name: str) -> str:
    val = os.environ.get(name, "")
    if not val:
        print(f"[apmix-watch] missing env var {name} — cannot probe", file=sys.stderr)
        raise SystemExit(1)
    return val


def _apmix(method: str, path: str, api_key: str, body: dict | None = None, timeout: int = 30) -> tuple[int, bytes]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    # Some gateways only answer requests identifying as a supported client
    # (RAGIN_LLM_USER_AGENT); without it every probe 401s before auth.
    ua = os.environ.get("RAGIN_LLM_USER_AGENT", "").strip()
    if ua:
        headers["User-Agent"] = ua
    req = urllib.request.Request(
        os.environ["RAGIN_LLM_BASE_URL"].rstrip("/") + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except (urllib.error.URLError, TimeoutError) as e:
        print(f"[apmix-watch] network error: {e}", file=sys.stderr)
        return 0, b""


def main() -> int:
    load_dotenv(ROOT / ".env")
    _env("RAGIN_LLM_BASE_URL")  # validated; the URL itself lives in _apmix
    key = _env("RAGIN_LLM_API_KEY")
    models_to_check = [m for m in (
        os.environ.get("RAGIN_LLM_MODEL", ""),
        os.environ.get("RAGIN_DON_MODEL", ""),
        os.environ.get("EVAL_MODEL", ""),
    ) if m]

    probe: dict = {
        "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "models_wired": models_to_check,
    }

    # ── catalog gate (free) ────────────────────────────────────────────────
    code, body = _apmix("GET", "/models", key)
    if code != 200:
        probe.update({"catalog_http": code, "catalog_status": "unreachable"})
        print(f"[apmix-watch] catalog unreachable: HTTP {code}")
    else:
        try:
            listed = {m.get("id") for m in json.loads(body).get("data", [])}
        except json.JSONDecodeError:
            listed = set()
        probe.update({
            "catalog_http": 200,
            "catalog_models": sorted(listed),
            "models_missing": sorted(set(models_to_check) - listed),
        })
        if probe["models_missing"]:
            probe["catalog_status"] = "drift"
            print(f"[apmix-watch] CATALOG DRIFT — missing from provider: {probe['models_missing']}")
            print(f"[apmix-watch] current catalog: {probe['catalog_models']}")
        else:
            probe["catalog_status"] = "ok"
            print(f"[apmix-watch] catalog ok ({len(listed)} models, all wired models present)")

    # ── quota probe (1 token only when live) ───────────────────────────────
    quota_http, quota_status = 0, "not_probed"
    if probe.get("catalog_status") == "ok":
        # Probe the endpoint the deployment actually uses: providers that only
        # route their current models through the OpenAI Responses API answer
        # /chat/completions with "model does not support this interface".
        style = (os.environ.get("RAGIN_LLM_API_STYLE") or "chat").strip().lower()
        if style == "responses":
            quota_path = "/responses"
            quota_body = {
                "model": models_to_check[0],
                "input": [{"role": "user", "content": "ping"}],
                "max_output_tokens": 1,
            }
        else:
            quota_path = "/chat/completions"
            quota_body = {
                "model": models_to_check[0],
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 1,
            }
        code, body = _apmix("POST", quota_path, key, quota_body, timeout=45)
        quota_http = code
        if code == 200:
            quota_status = "live"
            print("[apmix-watch] quota LIVE — 1 token spent, ready to run the eval")
        elif code == 429:
            quota_status = "exhausted"
            print("[apmix-watch] quota exhausted (429 allowance_exhausted)")
        elif code == 402:
            quota_status = "payment_required"
            print("[apmix-watch] quota blocked (402 payment required)")
        else:
            quota_status = f"http_{code}" if code else "network_error"
            print(f"[apmix-watch] quota probe unexpected: HTTP {code}")

    probe.update({"quota_http": quota_http, "quota_status": quota_status})

    # ── reseed the audit pipeline (offline, never calls the LLM) ────────────
    # Keeps the judge-audited panel and audited stability consistent with
    # any campaign runs that landed since the last probe.
    reseed_rc, reseed_info = 0, {"status": "skipped"}
    if probe.get("catalog_status") != "unreachable":
        try:
            import subprocess
            proc = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "reseed_audit_pipeline.py")],
                capture_output=True, text=True, timeout=600,
            )
            reseed_rc = proc.returncode
            tail = (proc.stdout.strip().splitlines() or [""])[-1]
            if reseed_rc == 0:
                reseed_info = {"status": "ok", "detail": tail}
            elif reseed_rc == 3:
                reseed_info = {"status": "review", "detail": tail}
            else:
                reseed_info = {"status": "failed",
                               "detail": (proc.stderr.strip().splitlines() or [""])[-1]}
        except Exception as exc:
            reseed_rc = 1
            reseed_info = {"status": "failed", "detail": f"{type(exc).__name__}: {exc}"}
    probe["audit_pipeline"] = reseed_info

    # ── persist: append history, overwrite latest-status ───────────────────
    # Atomic write (tmp + os.replace): an interrupted run must never leave the
    # 0-byte STATUS file that breaks tests/unit/test_watch_audit_pipeline.py
    # and every consumer that json.loads() it.
    HISTORY.parent.mkdir(exist_ok=True)
    with HISTORY.open("a") as f:
        f.write(json.dumps(probe) + "\n")
    tmp_status = STATUS.with_suffix(".json.tmp")
    tmp_status.write_text(json.dumps(probe, indent=2) + "\n")
    os.replace(tmp_status, STATUS)

    # ── exit semantics for the systemd timer ───────────────────────────────
    if probe.get("catalog_status") == "drift":
        return 2
    if reseed_rc == 3:
        return 3  # reseeded; audited stability wants human review
    if reseed_info.get("status") == "failed":
        return 1
    if quota_status in {"live"}:
        return 0
    if quota_status in {"exhausted", "payment_required"}:
        return 0  # expected states, not failures
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
