from __future__ import annotations

import os

ARMS = ("RAGIN_BASELINE", "RAGIN_V4_DETERMINISTIC", "RAGIN_V4_LOGISTIC")


def resolve_arm(explicit: str | None = None) -> str:
    if explicit in ARMS:
        return explicit
    configured = os.environ.get("RAGIN_DECISION_ARM", "").strip().upper()
    if configured in ARMS:
        return configured
    enabled = os.environ.get("RAGIN_V4_ENABLED", "").strip().lower() in {"1", "true", "yes", "on"}
    if enabled:
        selector = os.environ.get("RAGIN_V4_SELECTOR", "deterministic").strip().lower()
        return "RAGIN_V4_LOGISTIC" if selector == "logistic" else "RAGIN_V4_DETERMINISTIC"
    return "RAGIN_BASELINE"
