"""Focused tests for wall-clock verifier deadlines and policy validation."""

from __future__ import annotations

import threading
import time

import pytest

import ragin.cycle.verification_deadline as vd
from ragin.cycle.verification_deadline import (
    DEFAULT_DEADLINE_S,
    DeadlineVerifier,
    resolve_verification_policy,
)


class _Fast:
    def verify(self, response, context):
        return {"passed": True, "issues": [], "deterministic": True}


class _Sleeping:
    def __init__(self, delay: float, result: dict | None = None) -> None:
        self.delay = delay
        self.result = result or {"passed": True, "issues": [], "deterministic": True}

    def verify(self, response, context):
        time.sleep(self.delay)
        return dict(self.result)


class _OnceSlow(_Fast):
    def __init__(self, delay: float) -> None:
        self.delay = delay
        self.calls = 0

    def verify(self, response, context):
        self.calls += 1
        if self.calls == 1:
            time.sleep(self.delay)
        return super().verify(response, context)


class _Blocking:
    def __init__(self, release: threading.Event) -> None:
        self.release = release

    def verify(self, response, context):
        self.release.wait(2.0)
        return {"passed": True, "issues": [], "deterministic": True}


class _Raising:
    def verify(self, response, context):
        raise RuntimeError("boom")


class _Mutator:
    def verify(self, response, context):
        response["response_text"] = "MUTATED"
        context["attacker_input"] = "MUTATED"
        return {"passed": True, "issues": [], "deterministic": True}


def _wait_not_busy(verifier: DeadlineVerifier, timeout: float = 1.0) -> None:
    deadline = time.monotonic() + timeout
    while verifier.busy and time.monotonic() < deadline:
        time.sleep(0.005)


# ── policy ──────────────────────────────────────────────────────────────────


def test_policy_defaults_preserve_legacy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RAGIN_VERIFIER_PROFILE", raising=False)
    monkeypatch.delenv("RAGIN_VERIFIER_DEADLINE_S", raising=False)
    policy = resolve_verification_policy()
    assert policy.profile == "legacy"
    assert policy.deadline_s == DEFAULT_DEADLINE_S == 1.0
    assert policy.source == "default"


def test_policy_reads_validated_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RAGIN_VERIFIER_PROFILE", "research_strict_v1")
    monkeypatch.setenv("RAGIN_VERIFIER_DEADLINE_S", "0.35")
    policy = resolve_verification_policy()
    assert policy.profile == "research_strict_v1"
    assert policy.deadline_s == 0.35
    assert policy.source == "env"


def test_explicit_policy_overrides_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RAGIN_VERIFIER_PROFILE", "legacy")
    monkeypatch.setenv("RAGIN_VERIFIER_DEADLINE_S", "9")
    policy = resolve_verification_policy(profile="research_strict_v1", deadline_s=0.2)
    assert policy.profile == "research_strict_v1"
    assert policy.deadline_s == 0.2
    assert policy.source == "explicit"


@pytest.mark.parametrize(
    ("env", "value"),
    [
        ("RAGIN_VERIFIER_PROFILE", "bogus"),
        ("RAGIN_VERIFIER_PROFILE", ""),
        ("RAGIN_VERIFIER_DEADLINE_S", "0"),
        ("RAGIN_VERIFIER_DEADLINE_S", "-1"),
        ("RAGIN_VERIFIER_DEADLINE_S", "nan"),
        ("RAGIN_VERIFIER_DEADLINE_S", "inf"),
        ("RAGIN_VERIFIER_DEADLINE_S", "61"),
        ("RAGIN_VERIFIER_DEADLINE_S", "abc"),
    ],
)
def test_invalid_policy_env_raises(
    monkeypatch: pytest.MonkeyPatch, env: str, value: str
) -> None:
    monkeypatch.delenv("RAGIN_VERIFIER_PROFILE", raising=False)
    monkeypatch.delenv("RAGIN_VERIFIER_DEADLINE_S", raising=False)
    monkeypatch.setenv(env, value)
    with pytest.raises(ValueError) as caught:
        resolve_verification_policy()
    if value:
        assert value not in str(caught.value) or value in {"0", "-1", "61"}
    assert caught.value.__cause__ is None


def test_policy_error_does_not_echo_a_secret_looking_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("RAGIN_VERIFIER_PROFILE", raising=False)
    monkeypatch.delenv("RAGIN_VERIFIER_DEADLINE_S", raising=False)
    monkeypatch.setenv("RAGIN_VERIFIER_DEADLINE_S", "sk-live-do-not-echo")
    with pytest.raises(ValueError) as caught:
        resolve_verification_policy()
    assert "sk-live-do-not-echo" not in str(caught.value)
    assert caught.value.__cause__ is None

    monkeypatch.delenv("RAGIN_VERIFIER_DEADLINE_S")
    monkeypatch.setenv("RAGIN_VERIFIER_PROFILE", "profile-do-not-echo")
    with pytest.raises(ValueError) as caught:
        resolve_verification_policy()
    assert "profile-do-not-echo" not in str(caught.value)
    assert caught.value.__cause__ is None


# ── real wall clock ─────────────────────────────────────────────────────────


def test_deadline_is_real_wall_clock_and_fails_closed() -> None:
    verifier = DeadlineVerifier(_Sleeping(0.30), 0.05)
    try:
        started = time.monotonic()
        verdict = verifier.verify({"response_text": "x"}, {})
        elapsed = time.monotonic() - started
        assert elapsed >= 0.04
        assert elapsed < 0.25
        assert verdict["passed"] is False
        assert verdict["issues"] == ["verifier_deadline_exceeded"]
        assert verdict["worker_status"] == "timeout"
        assert verdict["deadline_enforced"] is True
        assert verifier.worker_daemon is True
    finally:
        verifier.shutdown()


def test_repeated_timeouts_use_one_worker_and_do_not_spawn() -> None:
    release = threading.Event()
    verifier = DeadlineVerifier(_Blocking(release), 0.05)
    try:
        first = verifier.verify({"response_text": "x"}, {})
        assert first["issues"] == ["verifier_deadline_exceeded"]
        thread = verifier._thread
        second = verifier.verify({"response_text": "x"}, {})
        third = verifier.verify({"response_text": "x"}, {})
        assert second["issues"] == ["verifier_busy"]
        assert third["issues"] == ["verifier_busy"]
        assert verifier._thread is thread
        assert verifier.worker_started is True
        release.set()
        _wait_not_busy(verifier)
        assert verifier._thread is thread
        assert verifier.late_results_discarded == 1
        fourth = verifier.verify({"response_text": "x"}, {})
        assert fourth["passed"] is True
    finally:
        release.set()
        verifier.shutdown()


def test_late_result_is_discarded_then_worker_is_reusable() -> None:
    inner = _OnceSlow(0.15)
    verifier = DeadlineVerifier(inner, 0.03)
    try:
        first = verifier.verify({"response_text": "x"}, {})
        assert first["issues"] == ["verifier_deadline_exceeded"]
        _wait_not_busy(verifier, timeout=1.0)
        assert verifier.late_results_discarded == 1
        second = verifier.verify({"response_text": "x"}, {})
        assert second["passed"] is True
        assert second["worker_status"] == "ok"
    finally:
        verifier.shutdown()


def test_worker_failure_is_fail_closed() -> None:
    verifier = DeadlineVerifier(_Raising(), 0.5)
    try:
        verdict = verifier.verify({"response_text": "x"}, {})
        assert verdict["passed"] is False
        assert verdict["issues"] == ["verifier_exception:RuntimeError"]
        assert verdict["worker_status"] == "error"
    finally:
        verifier.shutdown()


@pytest.mark.parametrize(
    "result",
    [
        {},
        None,
        [],
        {"passed": "true"},
        {"passed": 1},
        {"passed": True},
        {"passed": True, "issues": 123},
        {"passed": True, "issues": "not-a-list"},
        {"passed": False, "issues": ["ok", 7]},
    ],
)
def test_malformed_verdict_is_fail_closed(result) -> None:
    class _Malformed:
        def verify(self, response, context):
            return result

    verifier = DeadlineVerifier(_Malformed(), 0.5)
    try:
        verdict = verifier.verify({"response_text": "x"}, {})
        assert verdict["passed"] is False
        assert verdict["issues"]
    finally:
        verifier.shutdown()


@pytest.mark.parametrize(
    "result",
    [
        {"passed": True},
        {"passed": True, "issues": 123},
        {"passed": True, "issues": "not-a-list"},
        {"passed": False, "issues": ["ok", 7]},
    ],
)
def test_malformed_verdict_issues_are_rejected_not_retyped(result: dict) -> None:
    class _Malformed:
        def verify(self, response, context):
            return result

    verifier = DeadlineVerifier(_Malformed(), 0.5)
    try:
        verdict = verifier.verify({"response_text": "x"}, {})
        assert verdict["passed"] is False
        assert verdict["issues"] == ["verifier_malformed_result"]
    finally:
        verifier.shutdown()


def test_passed_true_with_issues_fails_closed_as_contradictory() -> None:
    class _Contradictory:
        def verify(self, response, context):
            return {"passed": True, "issues": ["should-not-pass"]}

    verifier = DeadlineVerifier(_Contradictory(), 0.5)
    try:
        verdict = verifier.verify({"response_text": "x"}, {})
        assert verdict["passed"] is False
        assert verdict["issues"] == ["verifier_contradictory_result"]
    finally:
        verifier.shutdown()


def test_candidate_and_context_are_frozen() -> None:
    verifier = DeadlineVerifier(_Mutator(), 0.5)
    try:
        candidate = {"response_text": "original"}
        context = {"attacker_input": "original"}
        verdict = verifier.verify(candidate, context)
        assert verdict["passed"] is True
        assert candidate == {"response_text": "original"}
        assert context == {"attacker_input": "original"}
    finally:
        verifier.shutdown()


def test_shutdown_does_not_block_on_stuck_worker() -> None:
    release = threading.Event()
    verifier = DeadlineVerifier(_Blocking(release), 0.03)
    try:
        verdict = verifier.verify({"response_text": "x"}, {})
        assert verdict["issues"] == ["verifier_deadline_exceeded"]
        started = time.monotonic()
        verifier.shutdown(wait=True)
        assert time.monotonic() - started < 0.5
        assert verifier.worker_daemon is True
    finally:
        release.set()


def test_snapshot_cost_is_inside_the_deadline(monkeypatch: pytest.MonkeyPatch) -> None:
    import copy

    real_deepcopy = copy.deepcopy

    def slow_deepcopy(value, *args, **kwargs):
        time.sleep(0.05)
        return real_deepcopy(value, *args, **kwargs)

    monkeypatch.setattr(vd.copy, "deepcopy", slow_deepcopy)
    verifier = DeadlineVerifier(_Fast(), 0.01)
    try:
        verdict = verifier.verify({"response_text": "x"}, {})
        assert verdict["passed"] is False
        assert verdict["phase"] == "snapshot"
        assert verdict["issues"] == ["verifier_deadline_exceeded"]
        assert verifier.worker_started is False
    finally:
        verifier.shutdown()


def test_completion_after_absolute_deadline_rejects_even_if_event_wait_says_true(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inner = _Sleeping(0.04)
    verifier = DeadlineVerifier(inner, 0.02)
    real_wait = threading.Event.wait

    def delayed_wait(event, timeout=None):
        time.sleep(0.06)
        return real_wait(event, 0.5)

    monkeypatch.setattr(threading.Event, "wait", delayed_wait)
    try:
        verdict = verifier.verify({"response_text": "x"}, {})
        assert verdict["passed"] is False
        assert verdict["issues"] == ["verifier_deadline_exceeded"]
    finally:
        verifier.shutdown()


def test_normalization_error_does_not_leave_worker_busy(monkeypatch: pytest.MonkeyPatch) -> None:
    real_normalize = vd._normalize_verdict
    calls = {"n": 0}

    def flaky(result):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("normalize failed")
        return real_normalize(result)

    monkeypatch.setattr(vd, "_normalize_verdict", flaky)
    verifier = DeadlineVerifier(_Fast(), 0.5)
    try:
        first = verifier.verify({"response_text": "x"}, {})
        assert first["passed"] is False
        assert first["issues"] == ["verifier_exception:RuntimeError"]
        assert verifier.busy is False
        second = verifier.verify({"response_text": "x"}, {})
        assert second["passed"] is True
    finally:
        verifier.shutdown()
