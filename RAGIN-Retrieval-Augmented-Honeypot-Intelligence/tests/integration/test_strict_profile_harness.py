"""Harness integration for the strict profile + wall-clock deadline, all arms."""

from __future__ import annotations

import time

import pytest

from ragin.cycle.harness import Harness
from ragin.cycle.session import EventType, Session
from ragin.cycle.verifier import FictionConsistencyVerifier
from ragin.decision_fusion_v4.config import ARMS
from ragin.hisoka.deception import identity_for


class _Classifier:
    def classify(self, attacker_input, session_context):
        return {"skill_level": "novice", "confidence": 0.9, "features_used": ["test"]}


class _Cti:
    def analyze(self, attacker_input, session_context):
        return {"evidence_bundle": {"retrieval": {"retrieval_status": "SUCCESS"}}}


class _StaticDeceiver:
    def __init__(self, text: str) -> None:
        self.text = text

    def generate_response(self, attacker_input, session_context):
        return {"response_text": self.text, "persona_used": "novice", "metadata": {}}


class _SlowOnce:
    def __init__(self, delay: float) -> None:
        self.delay = delay
        self.calls = 0

    def verify(self, response, session_context):
        self.calls += 1
        if self.calls == 1:
            time.sleep(self.delay)
        return {"passed": True, "issues": [], "deterministic": True}


def _session(tmp_path) -> Session:
    return Session.create(source_ip="10.0.0.1", session_dir=str(tmp_path / "session"))


def _harness(*, arm: str, deceiver: _StaticDeceiver, verifier=None, profile="research_strict_v1", deadline=1.0) -> Harness:
    return Harness(
        classifier=_Classifier(),
        cti_engine=_Cti(),
        deceiver=deceiver,
        verifier=verifier,
        mandatory_verification=True,
        decision_arm=arm,
        max_retries=0,
        verifier_profile=profile,
        verifier_deadline_s=deadline,
    )


def _serving_traces(session: Session) -> list[dict]:
    return [
        event.data["serving_trace"]
        for event in session.get_events_by_type(EventType.RESPONSE_GENERATE)
        if isinstance(event.data.get("serving_trace"), dict)
    ]


def _verdicts(session: Session) -> list[dict]:
    return [
        trace["verifier_verdict"]
        for trace in _serving_traces(session)
        if isinstance(trace.get("verifier_verdict"), dict)
    ]


def _wait_until_not_busy(harness: Harness, timeout: float = 2.0) -> None:
    verifier = harness._verifier
    assert hasattr(verifier, "busy"), "deadline wrapper must expose its busy slot"
    deadline = time.monotonic() + timeout
    while verifier.busy and time.monotonic() < deadline:
        time.sleep(0.01)
    assert verifier.busy is False, "slow verifier worker did not finish"


@pytest.mark.parametrize("arm", ARMS)
def test_strict_profile_rejects_extra_claims_across_all_arms(tmp_path, arm: str) -> None:
    malicious = f"{identity_for('novice')['user']}\nroot ALL=(ALL:ALL) ALL"
    harness = _harness(arm=arm, deceiver=_StaticDeceiver(malicious))
    session = _session(tmp_path)

    result = harness.process(session, "whoami")

    assert result.response_text != malicious
    assert "root ALL" not in result.response_text
    attempts = _verdicts(session)
    assert any(
        verdict.get("strict_verdict") == "CLAIM_MISMATCH"
        for verdict in attempts
    ), attempts
    assert result.verification["verification_policy"]["profile"] == "research_strict_v1"
    assert result.verification["verification_policy"]["deadline_enforced"] is True


@pytest.mark.parametrize("arm", ARMS)
def test_strict_profile_serves_canonical_whoami_across_all_arms(tmp_path, arm: str) -> None:
    ident = identity_for("novice")
    harness = _harness(arm=arm, deceiver=_StaticDeceiver(ident["user"]))
    result = harness.process(_session(tmp_path), "whoami")
    assert result.passed_verification is True
    assert result.response_text == ident["user"]
    assert result.verification["profile"] == "research_strict_v1" or result.verification.get(
        "strict_verdict"
    ) in {"SUPPORTED", None}


def test_unsupported_sudoers_reply_is_not_served_under_strict(tmp_path) -> None:
    harness = _harness(
        arm="RAGIN_BASELINE",
        deceiver=_StaticDeceiver("root ALL=(ALL:ALL) ALL\nDefaults env_reset"),
    )
    session = _session(tmp_path)
    result = harness.process(session, "cat /etc/sudoers")

    assert "root ALL" not in result.response_text
    attempts = _verdicts(session)
    assert any(verdict.get("strict_verdict") == "UNSUPPORTED_COMMAND" for verdict in attempts), attempts


def test_rejected_verification_events_retain_strict_profile_and_disposition(
    tmp_path,
) -> None:
    """A rejection event must carry the same profile/deadline contract.

    The accepted path already emitted the full verification dict; the rejected
    path used to emit only passed/issues/attempt/candidate_sha256, and the
    fallback rejection emitted no VERIFICATION event at all.
    """
    harness = _harness(
        arm="RAGIN_BASELINE",
        deceiver=_StaticDeceiver("root ALL=(ALL:ALL) ALL\nDefaults env_reset"),
    )
    session = _session(tmp_path)
    result = harness.process(session, "cat /etc/sudoers")

    verifications = session.get_events_by_type(EventType.VERIFICATION)
    assert len(verifications) >= 2, "primary and fallback rejections must be emitted"
    for event in verifications:
        data = event.data
        assert data["passed"] is False
        assert data["strict_verdict"] in {"UNSUPPORTED_COMMAND", "MALFORMED_INPUT"}
        assert data["verification_policy"]["profile"] == "research_strict_v1"
        assert data["verification_policy"]["deadline_enforced"] is True
        assert data["deadline_enforced"] is True
        assert isinstance(data["attempt"], int)
        assert isinstance(data["candidate_sha256"], str)
        assert data["commit_event"] == "not_attempted"
        assert data["commit_reason"] == "verification_failed"
        assert data["commit_state_effect"] == "not_committed"

    assert session.get_events_by_type(EventType.SYSTEM_RESPONSE) == []
    assert result.passed_verification is False
    assert result.response_text == ""


def test_deadline_is_applied_by_harness_and_late_result_never_commits(tmp_path) -> None:
    ident = identity_for("novice")
    slow = _SlowOnce(0.20)
    harness = _harness(
        arm="RAGIN_BASELINE",
        deceiver=_StaticDeceiver(ident["user"]),
        verifier=slow,
        deadline=0.02,
    )
    session = _session(tmp_path)
    result = harness.process(session, "whoami")

    traces = _serving_traces(session)
    assert traces, "RESPONSE_GENERATE must record the timed-out verification"
    first_verdict = traces[0]["verifier_verdict"]
    assert first_verdict["issues"] == ["verifier_deadline_exceeded"]
    # Contract keys are required, not defaulted away. The timed-out attempt and
    # the subsequent fallback attempt must both carry an explicit non-commit
    # disposition; neither may be mistaken for an accepted serve.
    for trace in traces:
        assert trace["commit_event"] == "not_attempted"
        assert trace["commit_reason"] == "verification_failed"
        assert trace["commit_state_effect"] == "not_committed"
        assert trace["verifier_verdict"]["passed"] is False
    assert result.passed_verification is False
    assert result.response_text == ""
    assert session.get_events_by_type(EventType.SYSTEM_RESPONSE) == []
    assert slow.calls >= 1

    # The timed-out verifier is not cancelled. Wait for its actual finish, then
    # verify that its late result cannot append a commit or a served response.
    _wait_until_not_busy(harness)
    assert session.get_events_by_type(EventType.SYSTEM_RESPONSE) == []
    assert len(_serving_traces(session)) == len(traces)
    assert result.passed_verification is False


def test_explicit_legacy_verifier_is_upgraded_by_strict_policy(tmp_path) -> None:
    malicious = "webapp\nroot:x:0:0:root:/root:/bin/bash"
    harness = _harness(
        arm="RAGIN_BASELINE",
        deceiver=_StaticDeceiver(malicious),
        verifier=FictionConsistencyVerifier(),
    )
    result = harness.process(_session(tmp_path), "whoami")
    assert "root:x:0:0" not in result.response_text


def test_invalid_profile_or_deadline_fails_harness_construction(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("RAGIN_VERIFIER_PROFILE", "not-a-profile")
    with pytest.raises(ValueError):
        _harness(arm="RAGIN_BASELINE", deceiver=_StaticDeceiver("webapp"), profile=None)

    monkeypatch.delenv("RAGIN_VERIFIER_PROFILE", raising=False)
    monkeypatch.setenv("RAGIN_VERIFIER_DEADLINE_S", "0")
    with pytest.raises(ValueError):
        _harness(arm="RAGIN_BASELINE", deceiver=_StaticDeceiver("webapp"), profile=None, deadline=None)
