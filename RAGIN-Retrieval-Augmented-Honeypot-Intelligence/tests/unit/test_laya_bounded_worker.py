"""Synthetic regression tests for the v12 no-rerun safety repairs.

Covers two static defects from ``docs/laya_integration/LAYA_V12_NO_RERUN_RECOVERY_AUDIT.md``:

* finding 3 — per-request executors let timed-out callables pile up beyond the
  response deadline; the shared ``BoundedWorker`` now admits at most
  ``max_workers`` callables, holds the slot until the callable actually
  finishes, and reports an explicit ``busy`` instead of starting more work;
* finding 4 — both truncators could exceed the advertised character bound by
  prepending ``"..."`` on top of the maximum; ``bound_state`` keeps the marker
  inside the budget, and the decision event records source-state vs
  effective-input digests separately.

Every blocking callable here is finite (threading.Event or short sleeps).
No model, network, training, or inference is involved.
"""

from __future__ import annotations

import hashlib
import threading
import time

import pytest

from ragin.decision.bounded_worker import BoundedWorker, shared_infer_worker
from ragin.decision.laya_decision import LayaDecisionAdapter
from ragin.decision.laya_runtime import MAX_STATE_CHARS, _state_tail
from ragin.decision.optional import LayaAssessmentAdapter
from ragin.decision.state_bounds import TRUNCATION_POLICY, bound_state

# --------------------------------------------------------------------- bound_state


@pytest.mark.parametrize("max_chars", [4, 16, 8000])
def test_bounded_state_never_exceeds_advertised_bound(max_chars):
    for length in (0, 1, max_chars - 1, max_chars, max_chars + 1, max_chars * 3 + 7):
        if length < 0:
            continue
        bounded, _ = bound_state("x" * length, max_chars)
        assert len(bounded) <= max_chars


def test_short_state_passes_through_unchanged():
    bounded, truncated = bound_state("whoami", 8000)
    assert bounded == "whoami"
    assert truncated is False


def test_long_state_keeps_tail_with_ellipsis_inside_budget():
    state = "abcdefghij"
    bounded, truncated = bound_state(state, 6)
    assert truncated is True
    assert len(bounded) <= 6
    assert bounded.endswith("ij")
    assert bounded.startswith("...")


def test_tiny_bound_without_room_for_marker_still_respects_bound():
    bounded, truncated = bound_state("abcdef", 3)
    assert truncated is True
    assert len(bounded) <= 3


def test_bound_state_rejects_nonpositive_bound():
    with pytest.raises(ValueError):
        bound_state("x", 0)


def test_runtime_state_tail_uses_shared_bound():
    long_state = "y" * (MAX_STATE_CHARS + 123)
    tail = _state_tail(long_state)
    assert len(tail) <= MAX_STATE_CHARS
    assert tail.startswith("...")
    assert tail.endswith("y" * 50)
    # No second truncation beyond the shared bound: idempotent.
    assert _state_tail(tail) == tail


# ------------------------------------------------------------------ BoundedWorker


def test_worker_runs_sequential_calls_to_completion():
    worker = BoundedWorker(max_workers=1)
    try:
        for i in range(5):
            status, value = worker.run(lambda x: x + 1, i, timeout_s=1.0)
            assert (status, value) == ("ok", i + 1)
        assert worker.active == 0
    finally:
        worker.shutdown()


def test_provider_exception_is_returned_not_raised():
    worker = BoundedWorker(max_workers=1)
    try:
        status, exc = worker.run(lambda _: (_ for _ in ()).throw(RuntimeError("down")), None, timeout_s=1.0)
        assert status == "error"
        assert isinstance(exc, RuntimeError)
        assert worker.active == 0
    finally:
        worker.shutdown()


def test_timeout_holds_slot_until_callable_finishes_then_recovers():
    """A timed-out call keeps its slot; concurrent admission is refused as busy;
    once the finite callable finishes, admission reopens."""
    worker = BoundedWorker(max_workers=1)
    release = threading.Event()

    def blocker(_):
        release.wait(timeout=2.0)
        return "done"

    try:
        started = time.monotonic()
        status, value = worker.run(blocker, None, timeout_s=0.05)
        waited = time.monotonic() - started
        assert (status, value) == ("timeout", None)
        assert waited < 1.0  # the caller stopped waiting at the deadline
        assert worker.active == 1  # slot still held by the running callable

        # Admission must refuse new executing work while the slot is held.
        status2, _ = worker.run(lambda _: "other", None, timeout_s=0.05)
        assert status2 == "busy"
        assert worker.active == 1

        release.set()
        assert worker.wait_idle(timeout_s=2.0)
        assert worker.active == 0

        status3, value3 = worker.run(lambda _: "again", None, timeout_s=1.0)
        assert (status3, value3) == ("ok", "again")
    finally:
        release.set()
        worker.shutdown()


def test_concurrent_callers_never_exceed_max_workers():
    worker = BoundedWorker(max_workers=1)
    peak = 0
    peak_lock = threading.Lock()
    in_flight = 0

    def body(_):
        nonlocal in_flight, peak
        with peak_lock:
            in_flight += 1
            peak = max(peak, in_flight)
        time.sleep(0.03)
        with peak_lock:
            in_flight -= 1
        return "x"

    try:
        results = []

        def call():
            results.append(worker.run(body, None, timeout_s=5.0))

        threads = [threading.Thread(target=call) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10.0)
        assert len(results) == 4
        assert peak == 1  # never more than one executing callable
        # Every caller either ran or was explicitly refused as busy — none lost.
        assert all(status in {"ok", "busy"} for status, _ in results)
        assert any(status == "ok" for status, _ in results)
        assert worker.active == 0
    finally:
        worker.shutdown()


def test_wait_idle_reports_idle_worker():
    worker = BoundedWorker(max_workers=1)
    try:
        assert worker.wait_idle(timeout_s=0.2) is True
    finally:
        worker.shutdown()


def test_shared_worker_is_a_singleton():
    assert shared_infer_worker() is shared_infer_worker()


# -------------------------------------------------- adapter-level fail-safe wiring


def _native_payload(*, attack: float = 0.9, stage: str = "recon") -> dict:
    native = {
        "answers": {
            "attack": {"type": "noul", "noul": attack, "confidence": 0.9},
            "stage": {"type": "choice", "choice": stage, "probabilities": {stage: 1.0}},
            "severity": {"type": "score", "score": 2, "confidence": 0.9},
        },
        "routing": {"model": "english"},
    }
    return {"model": "laya/english", "native_output": native, "answers": native["answers"]}


def test_decision_adapter_busy_falls_back_to_baseline():
    """While a blocking call holds the shared slot, a second decision must fall
    back to the baseline branch with an explicit busy error — no queue growth."""
    worker = shared_infer_worker()
    release = threading.Event()

    def blocker(_):
        release.wait(timeout=2.0)
        return _native_payload()

    blocker_adapter = LayaDecisionAdapter(blocker, model="laya/english", timeout_s=0.05)
    holder = threading.Thread(
        target=lambda: blocker_adapter.decide(session_id="s-hold", state="x")
    )
    holder.start()
    try:
        deadline = time.monotonic() + 2.0
        while worker.active < 1 and time.monotonic() < deadline:
            time.sleep(0.01)
        assert worker.active == 1

        other = LayaDecisionAdapter(lambda _: _native_payload(), model="laya/english", timeout_s=0.05)
        decision = other.decide(session_id="s-busy", state="nmap -sV")
        assert decision["error"] == "busy"
        assert decision["availability"] is False
        assert decision["selected_workflow_branch"] == "BASELINE_NO_SIGNAL"
        assert decision["selected_response_strategy"] == "baseline"
        assert decision["policy_action"] == "baseline_fallback"
    finally:
        release.set()
        holder.join(timeout=5.0)
        assert worker.wait_idle(timeout_s=5.0)


def test_assessment_adapter_busy_returns_no_signal():
    worker = shared_infer_worker()
    release = threading.Event()

    def blocker(_):
        release.wait(timeout=2.0)
        return {"model": "laya-fixture", "answers": {"attack": {"type": "noul", "noul": 0.9}}}

    holder = LayaAssessmentAdapter(blocker, model="laya-fixture", timeout_s=0.05)
    thread = threading.Thread(target=lambda: holder.assess(session_id="s-hold", state="x"))
    thread.start()
    try:
        deadline = time.monotonic() + 2.0
        while worker.active < 1 and time.monotonic() < deadline:
            time.sleep(0.01)
        assert worker.active == 1

        other = LayaAssessmentAdapter(blocker, model="laya-fixture", timeout_s=0.05)
        result = other.assess(session_id="s-busy", state="x")
        assert result.status == "NO_SIGNAL"
        assert result.error == "busy"
        assert result.assessment is None
    finally:
        release.set()
        thread.join(timeout=5.0)
        assert worker.wait_idle(timeout_s=5.0)


# ------------------------------------------------------- input provenance (finding 4)


def test_decision_event_separates_source_and_effective_digests():
    received = {}

    def capture(state: str) -> dict:
        received["state"] = state
        return _native_payload()

    max_chars = 64
    source = "s" * (max_chars * 3)
    adapter = LayaDecisionAdapter(capture, model="laya/english", max_state_chars=max_chars)
    decision = adapter.decide(session_id="s-prov", state=source)

    source_digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    effective_digest = hashlib.sha256(received["state"].encode("utf-8")).hexdigest()

    # The provider received the bounded text, within the advertised bound.
    assert len(received["state"]) <= max_chars
    # digests are named precisely and differ when truncation happened
    assert decision["input_sha256"] == source_digest
    assert decision["source_state_sha256"] == source_digest
    assert decision["effective_input_sha256"] == effective_digest
    assert decision["input_truncated"] is True
    assert decision["source_state_sha256"] != decision["effective_input_sha256"]
    provenance = decision["normalized_decision"]["provenance"]
    assert provenance["source_state_chars"] == len(source)
    assert provenance["effective_input_chars"] == len(received["state"])
    assert provenance["truncation_policy"] == TRUNCATION_POLICY
    # Neither digest ever exposes the raw input itself.
    assert source_digest != source


def test_decision_event_short_state_digests_are_equal():
    adapter = LayaDecisionAdapter(lambda _: _native_payload(), model="laya/english")
    decision = adapter.decide(session_id="s-short", state="ls -la")
    assert decision["input_truncated"] is False
    assert decision["source_state_sha256"] == decision["effective_input_sha256"]
    assert decision["normalized_decision"]["provenance"]["truncation_policy"] == TRUNCATION_POLICY


def test_assessment_adapter_bounds_provider_input():
    received = {}

    def capture(state: str) -> dict:
        received["state"] = state
        return {"model": "laya-fixture", "answers": {"attack": {"type": "noul", "noul": 0.2}}}

    max_chars = 32
    adapter = LayaAssessmentAdapter(capture, model="laya-fixture", max_state_chars=max_chars)
    adapter.assess(session_id="s-bound", state="z" * (max_chars + 100))
    assert len(received["state"]) <= max_chars
    assert received["state"].startswith("...")
