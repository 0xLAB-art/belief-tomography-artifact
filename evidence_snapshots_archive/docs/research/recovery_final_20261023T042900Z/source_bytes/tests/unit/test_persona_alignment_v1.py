"""Focused contract checks for the bounded Cowrie persona proof."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import prove_cowrie_persona_alignment_v1 as proof  # noqa: E402


def test_terminal_parser_removes_pty_controls_but_keeps_observed_fields() -> None:
    raw = (
        b"Welcome to web-srv-01\r\n"
        b"\x1b[4hwebapp@web-srv-01:~$ whoami\r\n"
        b"\x1b[4lwebapp\r\n"
        b"\x1b[4hwebapp@web-srv-01:~$ "
    )
    parsed = proof.parse_terminal(raw, ["whoami"])
    assert parsed["banners"] == ["Welcome to web-srv-01"]
    assert parsed["turns"][0]["prompt_prefix"] == "webapp@web-srv-01:~$ "
    assert parsed["turns"][0]["answer_lines"] == ["webapp"]


def test_native_expectations_are_fixture_derived() -> None:
    assert proof.EXPECTED["native"]["hostname"] == ["web-srv-01"]
    assert proof.NATIVE_PROMPT == "webapp@web-srv-01:~$ "
    assert proof.IMAGE_ID.endswith("a30cd459")


def test_loopback_proof_keeps_strict_verification_and_provider_off() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        env = proof.safe_env(Path(temp_dir))
        assert env["RAGIN_VERIFIER_PROFILE"] == "research_strict_v1"
        assert env["RAGIN_PROVIDER_ENABLED"] == "0"
    source = (ROOT / "scripts/prove_cowrie_persona_alignment_v1.py").read_text()
    assert '"COWRIE_LLM_API_KEY": LOCAL_API_KEY' in source
