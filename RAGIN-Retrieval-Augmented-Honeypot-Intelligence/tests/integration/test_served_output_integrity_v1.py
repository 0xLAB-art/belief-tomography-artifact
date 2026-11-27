"""Served-output integrity: recorded bytes versus what the client receives.

Two layers, deliberately separated:

* closed-loop (this file's first half) — the real Harness/Sandbox/Session path
  with a fake generator and verifier. It proves the served-response hash in
  the interaction trace, the SYSTEM_RESPONSE event, and the response returned
  to the caller all describe the *same bytes*, and that the bounded
  ``served_text`` projection is a diagnostic that can truncate without
  touching the primary record.
* frozen evidence (second half) — read-only assertions over the October 23
  loopback persona runs. They prove, on real captured SSH bytes, that under
  transcript contract v2 each command appears exactly once on the wire while
  the historical v1 duplicate is preserved rather than edited away.

Offline only: no provider socket, no image, no model. A passing test is not
evidence of deception quality — it is evidence that the recorded served
output is the served output.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

_TEST_SCRATCH = Path(tempfile.mkdtemp(prefix="ragin-served-integrity-"))
os.environ.setdefault("RAGIN_SESSION_DIR", str(_TEST_SCRATCH / "sessions"))
os.environ.setdefault("RAGIN_HOST_FICTION_PATH", str(_TEST_SCRATCH / "host_fiction.json"))
Path(os.environ["RAGIN_SESSION_DIR"]).mkdir(parents=True, exist_ok=True)

from ragin.cycle.harness import Harness  # noqa: E402
from ragin.cycle.sandbox import Sandbox, SandboxConfig  # noqa: E402
from ragin.cycle.session import EventType, Session  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
V2_RUN = ROOT / "docs" / "research" / "persona_alignment_20261023T054559Z"
V1_RUN = ROOT / "docs" / "research" / "persona_alignment_20261023T052609Z"

PROMPT = "webapp@web-srv-01:~$"


# ---------------------------------------------------------------------------
# fakes (generator/verifier only — harness, sandbox, session are real)
# ---------------------------------------------------------------------------


class _Classifier:
    def classify(self, attacker_input, session_context):
        return {"skill_level": "novice", "confidence": 0.8, "features_used": ["test"]}


class _Cti:
    def analyze(self, attacker_input, session_context):
        return {"evidence_bundle": {}}


class _StaticDeceiver:
    def __init__(self, text: str) -> None:
        self.text = text

    def generate_response(self, attacker_input, session_context):
        return {"response_text": self.text, "persona_used": "novice", "metadata": {}}


class _PassingVerifier:
    def verify(self, response, session_context):
        return {"passed": True, "issues": [], "deterministic": True}


class _FailingVerifier:
    def verify(self, response, session_context):
        return {"passed": False, "issues": ["identity-pin: test rejection"], "deterministic": True}


def _harness(text: str, verifier=None) -> Harness:
    return Harness(
        classifier=_Classifier(),
        cti_engine=_Cti(),
        deceiver=_StaticDeceiver(text),
        verifier=verifier if verifier is not None else _PassingVerifier(),
        mandatory_verification=True,
        decision_arm="RAGIN_BASELINE",
        max_retries=0,
    )


def _sandbox(harness: Harness, tmp_path: Path) -> Sandbox:
    return Sandbox(harness=harness, config=SandboxConfig(session_dir=str(tmp_path / "sessions")))


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# closed-loop: recorded bytes == returned bytes
# ---------------------------------------------------------------------------


def test_trace_event_and_returned_bytes_agree(tmp_path: Path) -> None:
    text = "webapp\n"
    response = _sandbox(_harness(text), tmp_path).handle_command("10.0.0.1", "whoami")

    assert response.status == "ok"
    assert response.response_text == text
    assert response.served_response_sha256 == _sha(text)

    session = Session.wake(response.session_id, session_dir=str(tmp_path / "sessions"))
    trace = session.get_events_by_type(EventType.METRIC)[-1].data["trace"]
    assert trace["served_response_sha256"] == response.served_response_sha256
    assert trace["served_response_chars"] == len(text)

    event = session.get_events_by_type(EventType.SYSTEM_RESPONSE)[-1]
    assert event.data["text"] == response.response_text
    assert event.data["served_response_sha256"] == response.served_response_sha256


def test_bounded_served_text_is_a_diagnostic_not_the_primary_record(tmp_path: Path) -> None:
    # A long response: the audit projection truncates, the served hash must not.
    text = ("drwxr-xr-x 2 webapp webapp 4096 Mar 15 .\n" * 40)
    assert len(text) > 500
    response = _sandbox(_harness(text), tmp_path).handle_command("10.0.0.1", "ls -la")

    session = Session.wake(response.session_id, session_dir=str(tmp_path / "sessions"))
    trace = session.get_events_by_type(EventType.METRIC)[-1].data["trace"]
    assert trace["served_response_sha256"] == _sha(text)
    # ``served_text`` is the bounded projection (<= limit chars) while
    # ``served_text_chars`` reports the full minimized length it was cut from.
    assert trace["served_text_truncated"] is True
    assert len(trace["served_text"]) <= 500
    assert trace["served_text_chars"] > 500
    assert trace["served_text"] != text
    # The diagnostic truncation never changes what was served.
    assert response.response_text == text


def test_failed_verification_serves_empty_and_records_empty(tmp_path: Path) -> None:
    response = _sandbox(
        _harness("webapp\n", verifier=_FailingVerifier()), tmp_path
    ).handle_command("10.0.0.1", "whoami")

    assert response.status == "error"
    assert response.response_text == ""
    assert response.served_response_sha256 == ""

    session = Session.wake(response.session_id, session_dir=str(tmp_path / "sessions"))
    trace = session.get_events_by_type(EventType.METRIC)[-1].data["trace"]
    assert trace["served_response_sha256"] == ""
    assert trace["served_response_chars"] == 0


# ---------------------------------------------------------------------------
# frozen evidence: the client-received bytes under v1 and v2
# ---------------------------------------------------------------------------


def _load(run_dir: Path, name: str) -> Any:
    path = run_dir / name
    assert path.exists(), f"frozen evidence missing: {path}"
    return json.loads(path.read_text())


def test_v2_evidence_each_command_appears_once_on_the_wire() -> None:
    summary = _load(V2_RUN, "summary.json")
    assert summary["status"] == "PARTIAL_ALIGNMENT"
    contract = summary["transcript_contract"]
    assert contract["transcript_contract"] == "v2"
    assert contract["ok"] is True
    assert contract["served_payload_echo_turns"] == []
    assert contract["frontend_echo_missing_turns"] == []

    stdout = (V2_RUN / "ssh_client.ragin.stdout").read_text()
    terminal = _load(V2_RUN, "raw_terminal.ragin.json")
    assert terminal["turns"], "evidence run recorded no turns"
    for turn in terminal["turns"]:
        # The attacker-typed echo (frontend PTY) appears exactly once: no
        # server-prepended duplicate reached the client.
        assert stdout.count(turn["prompt_line"]) == 1, turn["prompt_line"]
        assert turn["served_echo_lines"] == [], turn["command"]

    # Prompt alignment is part of the same evidence: identical outer prompts.
    native = _load(V2_RUN, "raw_terminal.native.json")
    assert terminal["outer_prompts"] == native["outer_prompts"]


def test_v1_evidence_duplicate_is_preserved_as_history() -> None:
    summary = _load(V1_RUN, "summary.json")
    # The pre-contract run records no contract version, and the duplicate
    # echo it produced stays in the evidence: history is not rewritten.
    assert summary.get("transcript_contract") is None
    terminal = _load(V1_RUN, "raw_terminal.ragin.json")
    duplicated = [t["command"] for t in terminal["turns"] if t["served_echo_lines"]]
    assert duplicated, "the v1 duplicate-echo evidence is gone"
    stdout = (V1_RUN / "ssh_client.ragin.stdout").read_text()
    for command in duplicated:
        assert stdout.count(f"{PROMPT} {command}") >= 2, command
