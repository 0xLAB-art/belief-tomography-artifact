"""Targeted record-contract tests for the bounded evaluation infrastructure.

The interpreter must be started with unique RAGIN_SESSION_DIR and
RAGIN_HOST_FICTION_PATH values; these assignments are a defensive fallback and
never point at the repository's historical/default session directory.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

os.environ.setdefault("RAGIN_SESSION_DIR", tempfile.mkdtemp(prefix="ragin-ablation-records-session-"))
os.environ.setdefault(
    "RAGIN_HOST_FICTION_PATH",
    str(Path(tempfile.mkdtemp(prefix="ragin-ablation-records-fiction-")) / "host_fiction.json"),
)

from ragin.evaluation.records import (  # noqa: E402
    SCHEMA,
    sha256_text,
    validate_record,
    validate_record_set,
)


def measurement(value: float | None = None) -> dict:
    if value is None:
        return {"availability": "UNAVAILABLE"}
    return {"availability": "MEASURED", "value": value}


def turn(index: int, command: str, *, status: str = "SERVED", text: str = "uid=1001") -> dict:
    served = status == "SERVED"
    empty = status == "EMPTY"
    return {
        "turn": index,
        "command": command,
        "command_redacted": command,
        "input_redacted": command,
        "raw_input_sha256": sha256_text(command),
        "serve_status": status,
        "failure_reason": None if served else "explicit non-served turn",
        "served_text": text if served else "",
        "served_text_sha256": sha256_text(text if served else ""),
        "served_raw_sha256": sha256_text(text) if served else None,
        "served_sha256": sha256_text(text) if served else None,
        "served_availability": "RAW" if served else "UNAVAILABLE",
        "candidate_sha256": None,
        "verified_sha256": None,
        "generation_kind": "NATIVE_SHELL" if not empty else "UNAVAILABLE",
        "decision_consumed": False,
        "arm_exposure": "OBSERVED" if served or empty else "UNAVAILABLE",
        "model_exposure": {"observed": False},
        "verification": {"profile": "NATIVE_TRANSPORT_ONLY", "passed": served},
        "latency_ms": measurement(12.5) if served else measurement(),
        "tokens_in": measurement(),
        "tokens_out": measurement(),
        "cost_usd": measurement(),
        "redaction": {"input_method": "minimize_then_truncate", "served_text": "retained"},
    }


def record(*, turns: list[dict], cause: str = "TURN_CAP", event_turn: int = 12, detection_turn=None) -> dict:
    from ragin.evaluation.attacker_policies import engagement_denominators

    commands = [row["command"] for row in turns if row["serve_status"] in {"SERVED", "EMPTY"}]
    return {
        "schema": SCHEMA,
        "record_id": "TESTONLY-REC-1",
        "track": "B",
        "test_only": True,
        "test_label": "TEST_ONLY_UNIT_RECORD",
        "split": "development",
        "block_id": "scenario::profile::s1",
        "allocation_index": 0,
        "arm": "B0",
        "scenario_id": "scenario",
        "profile_id": "profile",
        "seed": 1,
        "provenance": {
            "transport": "UNIT_FAKE",
            "generator": "NONE",
            "llm_inference": "NOT_ESTABLISHED",
            "mock": False,
        },
        "turns": turns,
        "terminal_cause": cause,
        "detection_turn": detection_turn,
        "event_turn": event_turn,
        "objective_action_indices": [],
        "operational": engagement_denominators(commands),
        "verification": {"profile": "NATIVE_TRANSPORT_ONLY", "passed": True},
        "analysis_eligible": False,
    }


def test_valid_turn_cap_record_passes() -> None:
    turns = [turn(index, f"probe-{index}") for index in range(1, 13)]
    assert validate_record(record(turns=turns)) == []


def test_detection_requires_turn_and_no_detection_elsewhere() -> None:
    turns = [turn(1, "id")]
    errors = validate_record(record(turns=turns, cause="DETECTION", event_turn=1, detection_turn=1))
    assert errors == []
    bad = validate_record(record(turns=turns, cause="DETECTION", event_turn=1, detection_turn=2))
    assert any("detection_turn" in error for error in bad)
    bad_cause = validate_record(record(turns=turns, cause="ABANDONMENT", event_turn=1, detection_turn=1))
    assert any("must not carry a detection_turn" in error for error in bad_cause)


def test_detection_requires_a_positive_event_turn() -> None:
    turns = [turn(1, "id")]
    errors = validate_record(record(turns=turns, cause="DETECTION", event_turn=0, detection_turn=1))
    assert any("DETECTION requires an explicit positive event_turn" in error for error in errors)


def test_failed_and_empty_turns_are_preserved_and_operational_counts_served() -> None:
    turns = [turn(1, "id"), turn(2, "cat missing", status="FAILED")]
    rec = record(turns=turns, cause="TECHNICAL_FAILURE", event_turn=2)
    rec["technical_reason"] = "transport failed after turn 1"
    assert validate_record(rec) == []
    assert rec["operational"]["served_turns"] == 1

    empty = [turn(1, "true", status="EMPTY")]
    empty_record = record(turns=empty, cause="ADMIN_CENSORED", event_turn=1)
    assert validate_record(empty_record) == []


def test_missing_measurement_cannot_carry_zero() -> None:
    turns = [turn(1, "id")]
    turns[0]["latency_ms"] = {"availability": "UNAVAILABLE", "value": 0.0}
    errors = validate_record(record(turns=turns, cause="ADMIN_CENSORED", event_turn=1))
    assert any("missing must not be coerced to zero" in error for error in errors)


def test_mixed_test_only_and_duplicate_block_arm_are_rejected() -> None:
    turns = [turn(1, "id")]
    left = record(turns=turns, cause="ADMIN_CENSORED", event_turn=1)
    right = record(turns=[turn(1, "whoami")], cause="ADMIN_CENSORED", event_turn=1)
    right["record_id"] = "MEASURED-REC-2"
    right["test_only"] = False
    right["test_label"] = None
    right["split"] = "development"
    right["provenance"]["mock"] = False
    errors = validate_record_set([left, right])
    assert any("mixed TEST_ONLY" in error for error in errors)

    right["test_only"] = True
    right["test_label"] = "TEST_ONLY_UNIT_RECORD"
    right["record_id"] = "TESTONLY-REC-2"
    right["block_id"] = left["block_id"]
    right["arm"] = left["arm"]
    errors = validate_record_set([left, right])
    assert any("duplicate allocation slot" in error for error in errors)
    assert any("duplicate block+arm" in error for error in errors)
