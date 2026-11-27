from __future__ import annotations

import os

RUNTIME_MODES = (
    "RAGIN_BASELINE",
    "RAGIN_V4_SUBSTANTIVE_DETERMINISTIC",
    "RAGIN_V4_SUBSTANTIVE_LOGISTIC",
)


def resolve_runtime_mode(explicit: str | None = None) -> str:
    value = (explicit or os.environ.get("RAGIN_RUNTIME_MODE", "RAGIN_BASELINE")).strip().upper()
    return value if value in RUNTIME_MODES else "RAGIN_BASELINE"


def decision_arm_for_runtime(mode: str) -> str:
    if mode == "RAGIN_V4_SUBSTANTIVE_LOGISTIC":
        return "RAGIN_V4_LOGISTIC"
    if mode == "RAGIN_V4_SUBSTANTIVE_DETERMINISTIC":
        return "RAGIN_V4_DETERMINISTIC"
    return "RAGIN_BASELINE"
