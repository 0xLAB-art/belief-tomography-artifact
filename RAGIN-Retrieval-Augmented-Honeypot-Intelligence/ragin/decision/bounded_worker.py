"""Bounded admission for Laya inference callables.

The adapters previously created a fresh ``ThreadPoolExecutor`` per request and
only stopped *waiting* at the timeout; the submitted callable kept running, so
repeated timed-out requests could accumulate unbounded concurrent work against
the shared model
(``docs/laya_integration/LAYA_V12_NO_RERUN_RECOVERY_AUDIT.md``, finding 3).

This module owns ONE lazily-created worker shared by every Laya adapter:

* admission is bounded — at most ``max_workers`` in-flight callables; extra
  callers get an immediate ``("busy", None)`` and fail safe (baseline /
  ``NO_SIGNAL``) instead of queueing more work;
* a timed-out caller stops waiting but its callable keeps its slot until it
  actually finishes, so a timeout can never widen the concurrency bound; while
  it lingers, new callers are told ``busy``;
* lifecycle is managed once per process instead of per request
  (``ThreadPoolExecutor``'s own atexit hook joins idle workers).

No thread cancellation is claimed: running callables are never killed, and no
unrelated process is touched. Tests must use finite blocking callables only.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from typing import Any, Literal

RunStatus = Literal["ok", "timeout", "busy", "error"]

# One shared Router (``max_loaded=1``) backs the real runtime; predict calls are
# serialized here so admission control also protects the router itself.
DEFAULT_MAX_CONCURRENT = 1

_SHARED: BoundedWorker | None = None
_SHARED_LOCK = threading.Lock()


class BoundedWorker:
    """Single shared executor with bounded admission and explicit busy signaling."""

    def __init__(self, max_workers: int = DEFAULT_MAX_CONCURRENT) -> None:
        if max_workers <= 0:
            raise ValueError("max_workers must be positive")
        self._slots = threading.BoundedSemaphore(max_workers)
        self._active = 0
        self._active_lock = threading.Lock()
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="laya-infer"
        )

    @property
    def executor(self) -> ThreadPoolExecutor:
        return self._executor

    @property
    def active(self) -> int:
        with self._active_lock:
            return self._active

    def run(self, fn: Callable[[Any], Any], arg: Any, timeout_s: float) -> tuple[RunStatus, Any]:
        """Run ``fn(arg)`` under admission control within one shared deadline.

        Returns ``("ok", value)``, ``("timeout", None)``, ``("busy", None)`` or
        ``("error", exception)``. The caller waits at most ``timeout_s`` in
        total: first for an admission slot, then for the result. If no slot
        frees within the deadline the call is refused with an explicit
        ``busy`` — new executing work is never started beyond the bound. After
        submission the slot is owned by the callable's completion: a timed-out
        caller stops waiting but the slot stays held until the callable itself
        finishes, and the (idempotent) done-callback releases it exactly once
        on every path.
        """
        deadline = time.monotonic() + timeout_s
        remaining = deadline - time.monotonic()
        if remaining <= 0 or not self._slots.acquire(timeout=remaining):
            return ("busy", None)
        with self._active_lock:
            self._active += 1

        released = False

        def release_slot() -> None:
            # Idempotent: fired exactly once, either by future completion or
            # by the pre-submit failure paths below.
            nonlocal released
            if released:
                return
            released = True
            with self._active_lock:
                self._active -= 1
            self._slots.release()

        try:
            future = self._executor.submit(fn, arg)
        except Exception as exc:  # noqa: BLE001 - admission must fail safe
            release_slot()
            return ("error", exc)
        # The slot is owned by the callable's completion — including the case
        # where this caller stops waiting (timeout) or exits abnormally: a
        # running callable keeps the slot until it actually finishes, so
        # admission never reopens while work is still in flight.
        future.add_done_callback(lambda _f: release_slot())
        try:
            result = future.result(timeout=max(0.0, deadline - time.monotonic()))
        except FuturesTimeoutError:
            return ("timeout", None)
        except Exception as exc:  # noqa: BLE001 - provider failure is a signal, not a crash
            return ("error", exc)
        return ("ok", result)

    def wait_idle(self, timeout_s: float = 5.0) -> bool:
        """Block until no admitted callable is in flight (test/shutdown helper)."""
        elapsed = 0.0
        step = 0.01
        while elapsed <= timeout_s:
            if self._slots.acquire(timeout=step):
                self._slots.release()
                return True
            elapsed += step
        return False

    def shutdown(self, wait: bool = False) -> None:
        """Managed lifecycle: shut down the shared executor (idempotent)."""
        self._executor.shutdown(wait=wait, cancel_futures=True)


def shared_infer_worker() -> BoundedWorker:
    """Process-wide bounded worker backing all Laya adapter inference calls."""
    global _SHARED
    if _SHARED is None:
        with _SHARED_LOCK:
            if _SHARED is None:
                _SHARED = BoundedWorker()
    return _SHARED
