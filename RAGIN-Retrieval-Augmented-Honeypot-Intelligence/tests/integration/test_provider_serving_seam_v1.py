"""Focused contract test for the resolved provider generation path.

This test re-runs the resolver and client introspection in a fresh interpreter
with only the augmented env, so it validates what the PROJECT actually resolves
for the serving path, not what the current shell happens to carry.

Deployed provider (2026-10-27): agentrouter.org/v1, model gpt-6.1-sol,
Responses transport, generation contract OFF (the endpoint rejects
temperature/top_p, so an enabled contract would assert fields that never go
on the wire). Expectations are pinned to that deployment but derived from the
authoritative .env, so a provider switch has to update this file deliberately.

No live provider request is made.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = ROOT / ".env"
_PROBE_TMPDIR = Path(tempfile.mkdtemp(prefix="apmix_serving_probe_"))

_PROBE_PY = _PROBE_TMPDIR / "_apmix_snapshot_probe_temp.py"
_ENV_FILE = _PROBE_TMPDIR / "_augmented_env.txt"


def _probe_paths() -> tuple[Path, Path]:
    _PROBE_SCRIPT = """\
import sys, os, json
sys.path.insert(0, "/home/elaref/Documents/research/ragin/RAGIN-Retrieval-Augmented-Honeypot-Intelligence")

_env_file = "@ENV_FILE@"

if os.path.exists(_env_file):
    for raw_line in open(_env_file):
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ[k.strip()] = v.strip()

from ragin.server_v2 import _resolve_provider_config
from ragin.gateway.client import GatewayClient
from ragin.gateway.generation import resolve_generation_config

provider = _resolve_provider_config()
client = GatewayClient().generation_snapshot()
contract = resolve_generation_config()
print(json.dumps({
    "provider": provider,
    "client": client,
    "contract": contract.config_sha256 if contract is not None else None,
}))
"""
    _PROBE_PY.write_text(_PROBE_SCRIPT.replace("@ENV_FILE@", str(_ENV_FILE)))
    return _PROBE_PY, _ENV_FILE


@pytest.fixture
def augmented_env() -> dict[str, str]:
    base = dict(os.environ)
    if ENV_FILE.is_file():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            base[k.strip()] = v.strip()
    return base


def _write_augmented_env(path: Path, augmented_env: dict[str, str]) -> None:
    path.write_text(
        "\n".join(f"{k}={v}" for k, v in augmented_env.items()) + "\n"
    )


def test_resolved_provider_is_deployed_endpoint(augmented_env: dict[str, str]) -> None:
    probe_py, env_file = _probe_paths()
    try:
        _write_augmented_env(env_file, augmented_env)
        result = subprocess.run(
            [sys.executable, str(probe_py)],
            cwd=str(ROOT),
            env={**augmented_env, "PYTHONPATH": str(ROOT)},
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, result.stderr + "\n" + result.stdout
        payload = json.loads(result.stdout)
    finally:
        probe_py.unlink(missing_ok=True)
        env_file.unlink(missing_ok=True)

    provider = payload["provider"]
    # Deployment pin: agentrouter.org, declared by the authoritative .env (the
    # resolver must report that same URL — not a legacy apmix fallback).
    assert augmented_env["RAGIN_LLM_BASE_URL"] == "https://agentrouter.org/v1"
    assert provider["gateway_url"] == "https://agentrouter.org/v1", payload
    assert provider["url_source"] == "RAGIN_LLM_BASE_URL", payload
    assert provider["key_source"] == "RAGIN_LLM_API_KEY", payload
    assert provider["api_key_configured"] is True, payload


def test_client_snapshots_generation_contract_state(augmented_env: dict[str, str]) -> None:
    probe_py, env_file = _probe_paths()
    try:
        _write_augmented_env(env_file, augmented_env)
        result = subprocess.run(
            [sys.executable, str(probe_py)],
            cwd=str(ROOT),
            env={**augmented_env, "PYTHONPATH": str(ROOT)},
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, result.stderr + "\n" + result.stdout
        payload = json.loads(result.stdout)
    finally:
        probe_py.unlink(missing_ok=True)
        env_file.unlink(missing_ok=True)

    client = payload["client"]
    # Deployment pin: the wired model is the agentrouter catalog model.
    assert augmented_env["RAGIN_LLM_MODEL"] == "gpt-6.1-sol"
    assert client["requested_model"] == "gpt-6.1-sol", client

    contract_flag = augmented_env.get("RAGIN_GENERATION_CONTRACT", "").strip().lower()
    if contract_flag in {"1", "true", "yes", "on"}:
        assert client["contract_active"] is True, client
        assert client["source"] == "ENV_VARS", client
        assert client["config_sha256"] is not None, client
        assert len(client["config_sha256"]) == 64, client
        assert client["decoding"] == {
            "temperature": 0.0,
            "max_tokens": 512,
            "top_p": 1.0,
            "seed": None,
        }, client
        assert payload["contract"] is not None, payload
        assert len(payload["contract"]) == 64, payload
    else:
        # Contract is deliberately OFF for this deployment: the endpoint's
        # /v1/responses rejects temperature/top_p, so an enabled contract
        # would assert decoding fields the provider never receives (the
        # client fails closed instead of silently drifting). The legacy path
        # serves with provider defaults and records the wire payload.
        assert client["contract_active"] is False, client
        assert client["version"] is None, client
        assert client["decoding"] is None, client
        assert client["config_sha256"] is None, client
        assert payload["contract"] is None, payload


def test_augmented_env_propagation_uses_single_authoritative_file(
    augmented_env: dict[str, str],
) -> None:
    probe_py, env_file = _probe_paths()
    alt_file = _PROBE_TMPDIR / "_augmented_env_local.txt"
    try:
        _write_augmented_env(env_file, augmented_env)
        _write_augmented_env(alt_file, augmented_env)
        result = subprocess.run(
            [sys.executable, str(probe_py)],
            cwd=str(ROOT),
            env={**augmented_env, "PYTHONPATH": str(ROOT)},
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, result.stderr + "\n" + result.stdout
        payload = json.loads(result.stdout)
    finally:
        probe_py.unlink(missing_ok=True)
        env_file.unlink(missing_ok=True)
        alt_file.unlink(missing_ok=True)

    assert payload["provider"]["gateway_url"] == augmented_env["RAGIN_LLM_BASE_URL"], payload


def teardown_module(module) -> None:
    try:
        import shutil

        shutil.rmtree(str(_PROBE_TMPDIR), ignore_errors=True)
    except Exception:
        pass
