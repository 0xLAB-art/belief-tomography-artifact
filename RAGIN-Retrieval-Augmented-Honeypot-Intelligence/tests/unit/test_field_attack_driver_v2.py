"""Tests for the v2 attack driver helpers (scripts/field_attack_driver_v2.py).

The driver's correctness properties that matter for the study: the persona
caps match the pre-registration, the egress guard refuses anything that is not
the allowlisted provider, and refusal text is detected rather than sent to a
shell as if it were a command.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.field_attack_driver_v2 import (  # noqa: E402
    PERSONAS,
    _looks_like_refusal,
    guarded_url,
    load_env,
)


def test_persona_caps_match_the_v2_preregistration():
    assert {p: v["cap"] for p, v in PERSONAS.items()} == {
        "novice_scriptkiddie": 12,
        "evasion_probe": 18,
        "credential_hunter": 25,
        "recon_operator": 30,
        "apt_patient": 30,
    }


def test_egress_guard_refuses_non_allowlisted_targets():
    with pytest.raises(ValueError):
        guarded_url("http://agentrouter.org")
    with pytest.raises(ValueError):
        guarded_url("https://evil.example")
    assert guarded_url("https://agentrouter.org").endswith("/v1/responses")


def test_load_env_ignores_comments_and_blank_lines(tmp_path: Path):
    path = tmp_path / ".env"
    path.write_text("# comment\n\nA=1\nB = two\n")
    assert load_env(path) == {"A": "1", "B": "two"}


def test_refusal_detection_keeps_real_commands():
    assert _looks_like_refusal("I cannot help with that request.")
    assert _looks_like_refusal("I can't assist with credential theft")
    assert not _looks_like_refusal("cat /etc/passwd")
    assert not _looks_like_refusal("getent passwd")
