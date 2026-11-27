"""Tests for the aggregate-only field census (scripts/field_census.py).

The census runs on the endpoint, so two properties matter more than the
numbers: it must never emit a raw source address, and it must separate
attacker commands from the deception model's refusal strings that land in the
same `cowrie.command.input` channel.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.field_census import census, hash_ip  # noqa: E402

RAW_IP = "203.0.113.77"


def _event(session: str, src: str, eventid: str, **extra) -> str:
    return json.dumps(
        {"session": session, "src_ip": src, "eventid": eventid,
         "timestamp": extra.pop("ts", "2026-10-26T10:00:00.000000Z"), **extra}
    )


def _fixture(tmp_path: Path) -> Path:
    log_dir = tmp_path / "cowrie"
    log_dir.mkdir()
    lines = [
        _event("s1", RAW_IP, "cowrie.session.connect"),
        _event("s1", RAW_IP, "cowrie.login.success", username="root", password="x"),
        _event("s1", RAW_IP, "cowrie.command.input", input="whoami"),
        _event("s1", RAW_IP, "cowrie.command.input", input="I cannot help with that request."),
        _event("s2", RAW_IP, "cowrie.session.connect", ts="2026-10-27T09:00:00.000000Z"),
        _event("s2", RAW_IP, "cowrie.command.input", input="uname -a",
               ts="2026-10-27T09:01:00.000000Z"),
    ]
    (log_dir / "cowrie.json").write_text("\n".join(lines) + "\nnot-json\n", encoding="utf-8")
    return log_dir


def test_census_counts_days_sessions_and_refusals(tmp_path: Path):
    payload = census(_fixture(tmp_path))
    totals = payload["totals"]
    assert totals["sessions_connected"] == 2
    assert totals["commands"] == 3
    assert totals["refusal_shaped_commands"] == 1
    assert totals["file_downloads"] == 0
    assert payload["by_day"]["2026-10-26"]["session_connect"] == 1
    assert payload["by_day"]["2026-10-27"]["commands"] == 1


@pytest.fixture(autouse=True)
def _census_salt(monkeypatch: pytest.MonkeyPatch):
    """Every census call hashes source IPs; give the suite a salt by default.
    Individual tests may delenv to exercise the refuse-without-salt path."""
    monkeypatch.setenv("RAGIN_IP_SALT", "test-salt")


def test_census_never_emits_a_raw_address(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("RAGIN_IP_SALT", "test-salt")
    payload = census(_fixture(tmp_path))
    dumped = json.dumps(payload)
    assert RAW_IP not in dumped
    assert payload["hashed_sources"] == [hash_ip(RAW_IP)]
    assert len(payload["hashed_sources"][0]) == 12


def test_hash_matches_the_pipeline_convention(monkeypatch: pytest.MonkeyPatch):
    # ragin/utils.hash_ip convention: HMAC-SHA256 keyed with RAGIN_IP_SALT
    import hashlib
    import hmac

    monkeypatch.setenv("RAGIN_IP_SALT", "test-salt")
    expected = hmac.new(b"test-salt", RAW_IP.encode(), hashlib.sha256).hexdigest()[:12]
    assert hash_ip(RAW_IP) == expected
    assert hash_ip("unknown") == "unknown"


def test_census_refuses_to_hash_without_a_salt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("RAGIN_IP_SALT", raising=False)
    with pytest.raises(RuntimeError, match="RAGIN_IP_SALT"):
        hash_ip(RAW_IP)
