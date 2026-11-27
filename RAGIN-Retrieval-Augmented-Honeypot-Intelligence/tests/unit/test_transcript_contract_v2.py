"""Contract v1/v2 checks: who owns the command echo, and what the server may emit.

The attacker-visible SSH turn has exactly one mandatory echo — the PTY echoing
the typed bytes. These tests pin both contracts so neither can drift silently:

* v1 (legacy) prepends ``prompt$ command`` to a bare body;
* v2 (new evidence) never prepends and strips only an *exact* leading echo.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ragin.cycle import transcript_contract as contract  # noqa: E402
from ragin.cycle.harness import Harness  # noqa: E402
from ragin.hisoka.deception import (  # noqa: E402
    _looks_like_shell_command,
    _postprocess_llm_output_with_provenance,
    _style_as_transcript,
    identity_for,
)

IDENT = identity_for("intermediate")
PROMPT_ECHO = "webapp@app-db-02:~$ "
OS_RELEASE = (
    'PRETTY_NAME="Ubuntu 22.04.3 LTS"\n'
    'NAME="Ubuntu"\n'
    'VERSION_ID="22.04"\n'
    'VERSION="22.04.3 LTS (Jammy Jellyfish)"\n'
    "ID=ubuntu"
)


# ── contract resolution ─────────────────────────────────────────────────────


def test_default_contract_is_legacy_and_explicit_values_win(monkeypatch) -> None:
    monkeypatch.delenv(contract.CONTRACT_ENV, raising=False)
    assert contract.resolve() == contract.LEGACY_CONTRACT
    assert contract.describe()["default"] is True
    assert contract.resolve("v2") == contract.CURRENT_CONTRACT
    monkeypatch.setenv(contract.CONTRACT_ENV, "V2 ")
    assert contract.resolve() == contract.CURRENT_CONTRACT
    assert contract.describe()["echo_owner"] == "frontend"


def test_unknown_contract_raises_instead_of_guessing(monkeypatch) -> None:
    monkeypatch.setenv(contract.CONTRACT_ENV, "v3")
    with pytest.raises(ValueError, match="unknown transcript contract"):
        contract.resolve()


# ── v1 legacy behaviour is preserved byte-for-byte ──────────────────────────


def test_v1_still_prepends_the_echo_for_bare_output() -> None:
    styled = _style_as_transcript("webapp", "whoami", IDENT, contract="v1")
    assert styled == f"{PROMPT_ECHO}whoami\nwebapp"


def test_v1_leaves_an_existing_echo_untouched() -> None:
    body = f"{PROMPT_ECHO}whoami\nwebapp"
    assert _style_as_transcript(body, "whoami", IDENT, contract="v1") == body


# ── v2: the frontend owns the echo ──────────────────────────────────────────


def test_v2_never_prepends_an_echo_to_bare_output() -> None:
    assert _style_as_transcript("webapp", "whoami", IDENT, contract="v2") == "webapp"


def test_v2_strips_only_an_exact_leading_echo() -> None:
    assert (
        _style_as_transcript(f"{PROMPT_ECHO}whoami\nwebapp", "whoami", IDENT, contract="v2")
        == "webapp"
    )
    # A prompt-shaped line for a DIFFERENT command is real content, not an echo.
    other = f"{PROMPT_ECHO}id\nwebapp"
    assert _style_as_transcript(other, "whoami", IDENT, contract="v2") == other


def test_v2_preserves_multiline_output_errors_and_empty_bodies() -> None:
    styled = _style_as_transcript(OS_RELEASE, "cat /etc/os-release", IDENT, contract="v2")
    assert styled == OS_RELEASE
    assert styled.count("\n") == OS_RELEASE.count("\n")
    error = "bash: hostname: command not found"
    assert _style_as_transcript(error, "hostname", IDENT, contract="v2") == error
    assert _style_as_transcript("", "true", IDENT, contract="v2") == ""
    assert _style_as_transcript("\n\n", "true", IDENT, contract="v2") == ""


def test_v2_five_turns_never_accumulate_an_echo(monkeypatch) -> None:
    monkeypatch.setenv(contract.CONTRACT_ENV, "v2")
    served = [
        _style_as_transcript("webapp", "whoami", IDENT) for _ in range(5)
    ]
    assert served == ["webapp"] * 5
    assert all(PROMPT_ECHO not in text for text in served)


def test_postprocessing_strips_a_model_echo_only_under_v2(monkeypatch) -> None:
    # `hostname` has no deterministic identity replacement, so the draft bytes
    # are what get measured and the contract, not another layer, is under test.
    draft = f"{PROMPT_ECHO}hostname\napp-db-02"
    monkeypatch.setenv(contract.CONTRACT_ENV, "v2")
    text, provenance = _postprocess_llm_output_with_provenance(draft, "hostname", "intermediate")
    assert text == "app-db-02"
    assert provenance == "MODEL_CONTENT_POSTPROCESSED"
    monkeypatch.setenv(contract.CONTRACT_ENV, "v1")
    kept, _ = _postprocess_llm_output_with_provenance(draft, "hostname", "intermediate")
    assert kept == draft


# ── the heuristic defect behind the per-turn inconsistency ──────────────────


def test_flag_commands_are_commands_not_prose() -> None:
    for command in ("uname -a", "ls -a", "df -a", "cat /etc/os-release", "id"):
        assert _looks_like_shell_command(command) is True, command
    for prose in ("check a web server", "what is the hostname", "show me the logs"):
        assert _looks_like_shell_command(prose) is False, prose


# ── serving-boundary provenance ────────────────────────────────────────────


def test_serving_trace_records_contract_and_payload_scope(monkeypatch) -> None:
    monkeypatch.setenv(contract.CONTRACT_ENV, "v2")
    response: dict = {"response_text": "webapp"}
    Harness._attach_serving_trace(response, [], "COMMITTED")
    metadata = response["metadata"]
    assert metadata["transcript_contract"]["version"] == "v2"
    assert metadata["transcript_contract"]["echo_owner"] == "frontend"
    assert metadata["served_text_scope"] == "ragin_response_payload"
    assert metadata["served_response_bytes"] == len("webapp")
