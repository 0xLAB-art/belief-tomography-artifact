"""IP-hashing regression tests.

2026-11-05 hardening: hash_ip moved from plain sha256(ip + committed static
salt "ragin-ip-v1") to HMAC-SHA256 keyed with RAGIN_IP_SALT (no committed
default). These tests pin the convention AND assert the stdlib-only endpoint
scripts (field_census, cowrie_pipeline_bridge, validate_phase1) derive hashes
identically to ragin.utils.hash_ip, so the derivations cannot drift.
"""

from __future__ import annotations

import hashlib
import hmac
import importlib.util
import logging
from pathlib import Path

import pytest

from ragin.utils import hash_ip

ROOT = Path(__file__).resolve().parents[2]
IP = "203.0.113.7"
SALT = "unit-test-salt"

pytestmark = pytest.mark.unit


def _load_script(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_explicit_salt_is_deterministic_hmac(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RAGIN_IP_SALT", SALT)
    expected = hmac.new(SALT.encode(), IP.encode(), hashlib.sha256).hexdigest()
    assert hash_ip(IP) == expected
    assert hash_ip(IP) == hash_ip(IP)


def test_no_salt_uses_process_key_and_warns(monkeypatch: pytest.MonkeyPatch, caplog) -> None:
    monkeypatch.delenv("RAGIN_IP_SALT", raising=False)
    with caplog.at_level(logging.WARNING, logger="ragin.utils"):
        h1 = hash_ip(IP)
    assert any("RAGIN_IP_SALT is not set" in r.message for r in caplog.records)
    # stable within the process (same ephemeral key), never the old static default
    assert hash_ip(IP) == h1
    assert h1 != hashlib.sha256(f"{IP}ragin-ip-v1".encode()).hexdigest()


def test_different_salts_give_different_hashes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RAGIN_IP_SALT", "salt-a")
    a = hash_ip(IP)
    monkeypatch.setenv("RAGIN_IP_SALT", "salt-b")
    assert hash_ip(IP) != a


def test_sentinels_pass_through() -> None:
    for sentinel in ("", "unknown", "_", "0.0.0.0", "::"):
        assert hash_ip(sentinel) == sentinel


@pytest.mark.parametrize("script", ["field_census", "cowrie_pipeline_bridge", "validate_phase1"])
def test_endpoint_scripts_match_pipeline_derivation(
    script: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("RAGIN_IP_SALT", SALT)
    mod = _load_script(script)
    expected = hash_ip(IP)
    if script == "field_census":
        assert mod.hash_ip(IP) == expected[:12]  # census truncates to 12 hex chars
    else:
        assert mod.hash_ip(IP) == expected


def test_endpoint_scripts_refuse_without_salt(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RAGIN_IP_SALT", raising=False)
    for script in ("field_census", "cowrie_pipeline_bridge", "validate_phase1"):
        mod = _load_script(script)
        with pytest.raises(RuntimeError, match="RAGIN_IP_SALT"):
            mod.hash_ip(IP)
