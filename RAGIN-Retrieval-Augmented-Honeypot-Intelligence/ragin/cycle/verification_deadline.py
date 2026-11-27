"""Wall-clock verifier deadline + fail-closed research verification policy.

The prior "timeout" coverage raised a simulated ``TimeoutError``; no clock was
involved. This module enforces an actual elapsed-time bound around a verifier
call and disposes of any result that arrives after the deadline.

Semantics (documented, not aspirational)
----------------------------------------
* One dedicated **daemon** worker thread per ``DeadlineVerifier`` instance.
  Running Python code cannot be cancelled; the worker is never killed. A
  timed-out call keeps the single slot until it actually returns, so repeated
  timeouts cannot spawn additional workers/processes. New calls while the slot
  is held fail closed as ``busy`` immediately.
* The worker is a daemon thread, so process shutdown is not blocked by an
  indefinitely stuck verifier. This is *not* hard cancellation and is never
  reported as such.
* ``verify`` deep-copies the candidate and context before hand-off. A verifier
  that mutates its arguments therefore cannot mutate the authoritative
  objects, and a late result is discarded (never committed or served).
  The deadline clock starts before that snapshot. ``copy.deepcopy`` is not
  preemptible: a pathological object graph can consume the whole budget, in
  which case the call fails closed **without dispatch**. The projection is
  expected to be the harness's ordinary dict/list/str context, not an
  arbitrary live object graph; no preemption of deepcopy is claimed.
* Anything that is not an explicit dict with ``passed`` equal to the literal
  ``True``/``False`` fails closed (worker error, busy, malformed verdict,
  input that cannot be frozen).
* The deadline is enforced by the harness wrapper, independent of the decision
  arm and of whether the decision layer is enabled.

Configuration (validated, no tuning):
  ``RAGIN_VERIFIER_PROFILE``      legacy | research_strict_v1 (default legacy)
  ``RAGIN_VERIFIER_DEADLINE_S``   seconds, 0 < x <= 60 (research default 1.0)
"""

from __future__ import annotations

import copy
import math
import os
import queue
import threading
import time
from dataclasses import dataclass
from typing import Any

from ragin.cycle.strict_research import LEGACY_PROFILE_NAME, VALID_PROFILES

DEFAULT_DEADLINE_S = 1.0
MAX_DEADLINE_S = 60.0
PROFILE_ENV = "RAGIN_VERIFIER_PROFILE"
DEADLINE_ENV = "RAGIN_VERIFIER_DEADLINE_S"


@dataclass(frozen=True)
class VerificationPolicy:
    """Resolved, validated policy applied identically to every arm."""

    profile: str = LEGACY_PROFILE_NAME
    deadline_s: float = DEFAULT_DEADLINE_S
    source: str = "default"

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile": self.profile,
            "deadline_s": self.deadline_s,
            "deadline_enforced": True,
            "source": self.source,
        }


def resolve_verification_policy(
    profile: str | None = None,
    deadline_s: float | None = None,
) -> VerificationPolicy:
    """Resolve policy from explicit args then env; reject invalid values."""
    explicit_profile = profile is not None
    raw_profile = profile if explicit_profile else os.environ.get(PROFILE_ENV, LEGACY_PROFILE_NAME)
    resolved_profile = str(raw_profile).strip().lower()
    if resolved_profile not in VALID_PROFILES:
        raise ValueError(
            f"invalid {PROFILE_ENV}; expected one of {sorted(VALID_PROFILES)}"
        ) from None

    explicit_deadline = deadline_s is not None
    raw_deadline: Any = deadline_s if explicit_deadline else os.environ.get(DEADLINE_ENV, DEFAULT_DEADLINE_S)
    try:
        resolved_deadline = float(raw_deadline)
    except (TypeError, ValueError):
        # Field-only error: a misconfigured value may be a secret, so it must
        # not appear in the exception text or in a chained cause.
        raise ValueError(f"invalid {DEADLINE_ENV}; expected seconds") from None
    if not math.isfinite(resolved_deadline) or resolved_deadline <= 0.0 or resolved_deadline > MAX_DEADLINE_S:
        raise ValueError(
            f"invalid {DEADLINE_ENV}; expected 0 < seconds <= {MAX_DEADLINE_S}"
        ) from None

    if explicit_profile or explicit_deadline:
        source = "explicit"
    elif PROFILE_ENV in os.environ or DEADLINE_ENV in os.environ:
        source = "env"
    else:
        source = "default"
    return VerificationPolicy(
        profile=resolved_profile,
        deadline_s=resolved_deadline,
        source=source,
    )


def _fail(issue: str, **extra: Any) -> dict[str, Any]:
    verdict: dict[str, Any] = {
        "passed": False,
        "issues": [issue],
        "deterministic": True,
        "worker_status": "fail_closed",
    }
    verdict.update(extra)
    return verdict


def _malformed_verdict(result: dict[str, Any], issue: str) -> dict[str, Any]:
    normalized = dict(result)
    normalized["passed"] = False
    normalized["issues"] = [issue]
    normalized.setdefault("deterministic", True)
    normalized.setdefault("worker_status", "fail_closed")
    return normalized


def _normalize_verdict(result: Any) -> dict[str, Any]:
    """Validate the complete verdict schema, not only the ``passed`` literal.

    Contract: ``passed`` is a literal bool, ``issues`` is a list of strings,
    and a passing verdict has no issues. Any malformed or contradictory shape
    fails closed with a stable reason code; raw malformed issue values are not
    propagated.
    """
    if not isinstance(result, dict):
        return _fail("verifier_malformed_result")
    passed = result.get("passed")
    if passed is not True and passed is not False:
        return _malformed_verdict(result, "verifier_malformed_result")
    issues = result.get("issues")
    if not isinstance(issues, list) or any(not isinstance(issue, str) for issue in issues):
        return _malformed_verdict(result, "verifier_malformed_result")
    if passed is True and issues:
        return _malformed_verdict(result, "verifier_contradictory_result")
    normalized = dict(result)
    normalized.setdefault("deterministic", True)
    return normalized


class _Job:
    __slots__ = ("candidate", "context", "event", "result", "abandoned", "elapsed_ms", "finished_at")

    def __init__(self, candidate: dict[str, Any], context: dict[str, Any]) -> None:
        self.candidate: dict[str, Any] | None = candidate
        self.context: dict[str, Any] | None = context
        self.event = threading.Event()
        self.result: dict[str, Any] | None = None
        self.abandoned = False
        self.elapsed_ms: float | None = None
        self.finished_at: float | None = None


class DeadlineVerifier:
    """Fail-closed wall-clock wrapper around a verifier.

    Parameters
    ----------
    inner:
        Any object with ``verify(response, session_context) -> dict``.
    deadline_s:
        Maximum wall-clock seconds the caller waits. Must be finite/positive.
    """

    def __init__(self, inner: Any, deadline_s: float = DEFAULT_DEADLINE_S) -> None:
        if not math.isfinite(float(deadline_s)) or float(deadline_s) <= 0.0:
            raise ValueError("deadline_s must be finite and positive")
        self._inner = inner
        self.deadline_s = float(deadline_s)
        self._queue: queue.Queue[_Job | None] = queue.Queue()
        self._lock = threading.Lock()
        self._busy = False
        self._closed = False
        self._thread: threading.Thread | None = None
        self._late_results_discarded = 0

    # ── introspection (tests / diagnostics) ───────────────────────────────
    @property
    def busy(self) -> bool:
        with self._lock:
            return self._busy

    @property
    def worker_started(self) -> bool:
        with self._lock:
            return self._thread is not None

    @property
    def worker_daemon(self) -> bool:
        with self._lock:
            return bool(self._thread is not None and self._thread.daemon)

    @property
    def late_results_discarded(self) -> int:
        with self._lock:
            return self._late_results_discarded

    def _ensure_worker(self) -> None:
        if self._thread is None:
            self._thread = threading.Thread(
                target=self._worker_loop,
                name="ragin-verifier-deadline",
                daemon=True,
            )
            self._thread.start()

    # ── worker ────────────────────────────────────────────────────────────
    def _worker_loop(self) -> None:
        while True:
            job = self._queue.get()
            if job is None:
                return
            candidate, context = job.candidate, job.context
            started = time.monotonic()
            result: dict[str, Any] | None = None
            try:
                # Normalization runs inside the worker's try: a malformed
                # result must not kill the worker and leave ``_busy`` stuck.
                try:
                    raw_result = self._inner.verify(candidate, context)
                    result = _normalize_verdict(raw_result)
                except Exception as exc:  # noqa: BLE001 — worker failure is a verdict
                    result = _fail(
                        f"verifier_exception:{exc.__class__.__name__}",
                        worker_status="error",
                    )
            finally:
                finished_at = time.monotonic()
                elapsed_ms = (finished_at - started) * 1000.0
                with self._lock:
                    # Timeout path already discarded this job; keep the result
                    # out of every authoritative reference and count disposal.
                    if job.abandoned:
                        self._late_results_discarded += 1
                    else:
                        job.result = result
                        job.finished_at = finished_at
                    job.elapsed_ms = elapsed_ms
                    job.candidate = None
                    job.context = None
                    self._busy = False
                job.event.set()

    # ── protocol entry point ──────────────────────────────────────────────
    def verify(
        self,
        response: dict[str, Any] | str,
        session_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        started = time.monotonic()
        # Absolute deadline, fixed before the input snapshot. Every admission
        # decision below compares against this instant, never against a
        # re-derived "remaining" window (Event.wait boundary races).
        absolute_deadline = started + self.deadline_s
        candidate = response if isinstance(response, dict) else {"response_text": str(response or "")}
        context = session_context if isinstance(session_context, dict) else {}
        try:
            frozen_candidate = copy.deepcopy(candidate)
            frozen_context = copy.deepcopy(context)
        except Exception as exc:  # noqa: BLE001 — cannot freeze => fail closed
            return _fail(
                "verifier_input_not_serializable",
                worker_status="error",
                error=exc.__class__.__name__,
                deadline_s=self.deadline_s,
                deadline_enforced=True,
            )
        snapshot_ms = (time.monotonic() - started) * 1000.0
        if time.monotonic() >= absolute_deadline:
            # Deepcopy is not preemptible; if freezing the projection consumed
            # the budget, fail closed without occupying the worker.
            return _fail(
                "verifier_deadline_exceeded",
                worker_status="timeout",
                phase="snapshot",
                deadline_s=self.deadline_s,
                deadline_enforced=True,
                verification_snapshot_ms=round(snapshot_ms, 3),
            )

        with self._lock:
            if self._closed:
                return _fail("verifier_worker_closed", deadline_s=self.deadline_s, deadline_enforced=True)
            self._ensure_worker()
            if self._busy:
                return _fail("verifier_busy", deadline_s=self.deadline_s, deadline_enforced=True)
            self._busy = True
            job = _Job(frozen_candidate, frozen_context)

        self._queue.put(job)
        remaining = absolute_deadline - time.monotonic()
        completed = job.event.wait(timeout=max(0.0, remaining))

        with self._lock:
            result = job.result
            finished_at = job.finished_at
            # A True from Event.wait exactly at the boundary is not enough:
            # require the worker's recorded finish instant to be inside the
            # absolute deadline. A missing timestamp is malformed => reject.
            expired = finished_at is None or finished_at > absolute_deadline
            if expired:
                job.abandoned = True
                job.result = None
                job.candidate = None
                job.context = None
            # The worker may have completed between wait() returning False and
            # this lock. Either way, a late result is discarded and counted.
            should_count_late = expired and finished_at is not None
            if should_count_late:
                self._late_results_discarded += 1

        if not completed or expired:
            elapsed_ms = (time.monotonic() - started) * 1000.0
            return _fail(
                "verifier_deadline_exceeded",
                worker_status="timeout",
                deadline_s=self.deadline_s,
                deadline_enforced=True,
                elapsed_ms=round(elapsed_ms, 3),
                verification_snapshot_ms=round(snapshot_ms, 3),
            )
        if result is None:
            return _fail(
                "verifier_worker_no_result",
                deadline_s=self.deadline_s,
                deadline_enforced=True,
            )
        verdict = dict(result)
        verdict["deadline_s"] = self.deadline_s
        verdict["deadline_enforced"] = True
        verdict.setdefault("worker_status", "ok")
        verdict["verification_elapsed_ms"] = (
            round(job.elapsed_ms, 3) if job.elapsed_ms is not None else None
        )
        verdict["verification_snapshot_ms"] = round(snapshot_ms, 3)
        return verdict

    def shutdown(self, wait: bool = False) -> None:
        """Stop the worker lazily; never block on an indefinitely stuck call."""
        with self._lock:
            self._closed = True
            thread = self._thread
        self._queue.put(None)
        if wait and thread is not None and thread.is_alive():
            thread.join(timeout=0.1)


__all__ = [
    "DEADLINE_ENV",
    "DEFAULT_DEADLINE_S",
    "MAX_DEADLINE_S",
    "PROFILE_ENV",
    "DeadlineVerifier",
    "VerificationPolicy",
    "resolve_verification_policy",
]
