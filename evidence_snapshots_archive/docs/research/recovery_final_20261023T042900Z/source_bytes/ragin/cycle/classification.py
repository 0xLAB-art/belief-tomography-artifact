"""Canonical classification normalization shared by session replay and Don.

The pipeline stores classifications as *event payloads*, so a replay can hand
downstream consumers arbitrary historical shapes: missing keys, ``None``, a
string, a supervisor routing event, or a dict with an out-of-vocabulary
``skill_level``. Two consumers read that data and previously trusted it:

* ``Session.build_context`` exposed the LAST ``CLASSIFICATION`` event as the
  singular ``classification`` key;
* ``DonAdapter.analyze`` chained ``.get(...).get(...)`` on it and passed the
  result straight into a Pydantic model.

This module centralizes the rules so both agree:

* only the four supported skill levels are accepted (case-normalized);
* confidence must be a finite number in ``[0.0, 1.0]`` (bools rejected);
* supervisor-only routing events carry no skill verdict and are skipped for
  the singular semantic classification (they remain in the full history);
* malformed input yields ``{}`` — never a fabricated verdict.
"""

from __future__ import annotations

import math
from typing import Any

VALID_SKILL_LEVELS: tuple[str, ...] = ("novice", "intermediate", "advanced", "expert")

_SUPERVISOR_STAGES = frozenset({"supervisor"})


def _valid_confidence(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    if not math.isfinite(number) or number < 0.0 or number > 1.0:
        return None
    return number


def normalize_classification(value: Any) -> dict[str, Any]:
    """Return a safe classification dict without inventing a verdict.

    Non-dict input yields ``{}``. Unknown skill levels are *removed* rather
    than coerced, so callers that need a label can distinguish "no verdict"
    from "benign". Extra keys are preserved unchanged (they are internal
    event fields, not attacker-controlled credentials).
    """
    if not isinstance(value, dict):
        return {}

    out: dict[str, Any] = dict(value)

    skill = out.get("skill_level")
    if isinstance(skill, str) and skill.strip().lower() in VALID_SKILL_LEVELS:
        out["skill_level"] = skill.strip().lower()
    else:
        out.pop("skill_level", None)

    confidence = _valid_confidence(out.get("confidence"))
    if confidence is None:
        out.pop("confidence", None)
    else:
        out["confidence"] = confidence

    return out


def is_supervisor_event(value: Any) -> bool:
    """True when a ``CLASSIFICATION`` payload is supervisor routing, not a verdict."""
    if not isinstance(value, dict):
        return False
    if str(value.get("stage", "")).strip().lower() in _SUPERVISOR_STAGES:
        return True
    # Supervisor events carry ``routing_decision`` and no skill verdict.
    return "routing_decision" in value and "skill_level" not in value


def latest_skill_classification(events: Any) -> dict[str, Any]:
    """Select the most recent event that carries a valid skill verdict.

    The full ``classifications`` history stays untouched for callers that need
    it; only the singular compatibility key is derived here. Supervisor-only
    and malformed events are skipped, so a routing event cannot poison the
    semantic classification for later turns.
    """
    if not isinstance(events, list):
        return {}
    for event in reversed(events):
        if is_supervisor_event(event):
            continue
        normalized = normalize_classification(event)
        if "skill_level" in normalized:
            return normalized
    return {}


__all__ = [
    "VALID_SKILL_LEVELS",
    "is_supervisor_event",
    "latest_skill_classification",
    "normalize_classification",
]
