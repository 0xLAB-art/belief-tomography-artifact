"""Shared input-bound helpers for the Laya decision boundary.

ONE truncation rule, used by every place that shortens a state before it can
reach the model: ``LayaDecisionAdapter.decide``, ``LayaAssessmentAdapter.assess``
and ``LayaRuntime.infer``. The three-character ``...`` marker is counted INSIDE
the advertised maximum, so a bounded string is never longer than ``max_chars``.

This is a safety/provenance repair module from the v12 no-rerun recovery audit
(``docs/laya_integration/LAYA_V12_NO_RERUN_RECOVERY_AUDIT.md``, findings 4):
it changes input formatting only for states above the bound, and it does not
touch any frozen checkpoint, label, gate, weight, or saved prediction.
"""

from __future__ import annotations

DEFAULT_MAX_STATE_CHARS = 8000
TRUNCATION_POLICY = "tail_with_ellipsis_within_max_chars"


def bound_state(state: str, max_chars: int) -> tuple[str, bool]:
    """Return ``(bounded_state, truncated)`` with ``len(bounded_state) <= max_chars``.

    States at or below the bound pass through unchanged (``truncated`` is
    ``False``). Longer states keep their tail, prefixed by ``"..."`` which is
    part of — never added on top of — the budget. The previous behavior kept
    ``max_chars`` tail characters *and* prepended the marker, producing strings
    of ``max_chars + 3`` characters while advertising ``max_chars``.
    """
    if max_chars <= 0:
        raise ValueError("max_chars must be positive")
    if len(state) <= max_chars:
        return state, False
    if max_chars <= 3:
        # No room for the marker: keep the tail within the bound anyway.
        return state[-max_chars:], True
    return "..." + state[-(max_chars - 3) :], True
