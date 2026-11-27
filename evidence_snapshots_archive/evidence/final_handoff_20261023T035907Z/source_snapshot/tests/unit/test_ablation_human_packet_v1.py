"""Blind human-packet instrument tests: hashes, labels, and rater identity.

The interpreter must be started with unique RAGIN_SESSION_DIR and
RAGIN_HOST_FICTION_PATH values; these assignments are a defensive fallback and
never point at the repository's historical/default session directory.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path

os.environ.setdefault("RAGIN_SESSION_DIR", tempfile.mkdtemp(prefix="ragin-ablation-human-session-"))
os.environ.setdefault(
    "RAGIN_HOST_FICTION_PATH",
    str(Path(tempfile.mkdtemp(prefix="ragin-ablation-human-fiction-")) / "host_fiction.json"),
)

from ragin.evaluation.human_packet import (  # noqa: E402
    DIMENSIONS,
    PACKET_SCHEMA,
    build_answer_template,
    build_packet,
    validate_labels,
)


def sha_json(value: object) -> str:
    material = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def human_turn(
    index: int,
    *,
    command: str = "id",
    served_text: str = "uid=1000(user)",
    suspicion: str | None = None,
    rationale: str | None = None,
) -> dict:
    return {
        "turn": index,
        "command": command,
        "served_text": served_text,
        "serve_status": "SERVED",
        "failure_reason": None,
        "attacker_suspicion_statement": suspicion,
        "attacker_rationale": rationale,
    }


def human_record(record_id: str, *, cause: str, turns: list[dict], block_id: str = "block-1") -> dict:
    return {
        "record_id": record_id,
        "block_id": block_id,
        "arm": "B1",
        "terminal_cause": cause,
        "detection_turn": 1 if cause == "DETECTION" else None,
        "test_only": False,
        "turns": turns,
    }


def suspicious_packet() -> dict:
    record = human_record(
        "HUMAN-REC-1",
        cause="DETECTION",
        turns=[
            human_turn(
                1,
                suspicion="this host is not real; it is a honeypot",
                rationale="the banner and filesystem look synthetic",
            )
        ],
    )
    return build_packet([record], seed=11, rater_count=2)


def rows_for(packet: dict, detection: dict[str, str] | None = None) -> list[dict]:
    detection = detection or {}
    rows = []
    for item in packet["items"]:
        item_id = item["item_id"]
        label = detection.get(item_id)
        if label is None:
            label = "NO" if item["detection_rating_allowed"] else "UNAVAILABLE"
        ratings = {dimension: "" for dimension in DIMENSIONS}
        ratings["detection"] = label
        rows.append(
            {
                "item_id": item_id,
                "ratings": ratings,
                "detection_turn": 1 if label == "YES" else None,
                "confidence": "",
                "rationale": "",
            }
        )
    return rows


def submission(
    packet: dict,
    rater: str,
    rows: list[dict],
    *,
    completed: bool = True,
    declared: str | None = None,
) -> dict:
    return {
        "packet_sha256": packet["packet_sha256"],
        "rater_id": declared if declared is not None else rater,
        "source": "HUMAN",
        "completed": completed,
        "labels": rows,
    }


def test_packet_hash_recomputes_and_ratings_are_not_synthetic() -> None:
    packet = suspicious_packet()

    assert packet["schema"] == PACKET_SCHEMA
    material = {key: value for key, value in packet.items() if key != "packet_sha256"}
    assert sha_json(material) == packet["packet_sha256"]
    assert packet["arm_hidden"] is True

    item = packet["items"][0]
    assert item["rating_dimensions"] == list(DIMENSIONS)
    assert set(item["ratings"]) == set(DIMENSIONS)
    assert all(value == "" for value in item["ratings"].values())
    assert item["detection_turn"] is None
    assert item["confidence"] == ""
    assert item["rationale"] == ""

    template = build_answer_template(packet, "rater-a")
    assert template["completed"] is False
    assert template["source"] == "HUMAN"
    assert all(value == "" for row in template["labels"] for value in row["ratings"].values())
    assert all(row["detection_turn"] is None for row in template["labels"])


def test_rating_instrument_is_multi_dimensional() -> None:
    packet = suspicious_packet()
    item_dimensions = set(packet["items"][0]["rating_dimensions"])
    rubric_ids = {dimension["id"] for dimension in packet["rubric"]["dimensions"]}

    assert "detection" in DIMENSIONS
    assert len(DIMENSIONS) >= 2
    assert {
        "shell_realism",
        "cross_turn_consistency",
        "detectability",
        "credibility",
        "error_severity",
    } <= item_dimensions
    assert item_dimensions == rubric_ids == set(DIMENSIONS)
    assert all("scale" in dimension for dimension in packet["rubric"]["dimensions"])


def test_yes_requires_detection_turn_within_observed_turns() -> None:
    packet = suspicious_packet()
    item = packet["items"][0]
    assert item["detection_rating_allowed"] is True
    assert item["detection_evidence_status"] == "OBSERVED"

    yes_rows = rows_for(packet, {item["item_id"]: "YES"})
    result = validate_labels(
        packet,
        {"rater-a": submission(packet, "rater-a", yes_rows), "rater-b": submission(packet, "rater-b", yes_rows)},
    )
    assert result["status"] == "COMPUTED"
    assert result["raters"] == ["rater-a", "rater-b"]

    out_of_range = rows_for(packet, {item["item_id"]: "YES"})
    out_of_range[0]["detection_turn"] = int(item["session_length"]) + 1
    invalid = validate_labels(
        packet,
        {
            "rater-a": submission(packet, "rater-a", out_of_range),
            "rater-b": submission(packet, "rater-b", out_of_range),
        },
    )
    assert invalid["status"] == "INVALID"
    assert any("not within the observed turns" in error for error in invalid["errors"])


def test_no_and_uncertain_require_null_detection_turn() -> None:
    packet = suspicious_packet()
    item = packet["items"][0]

    for label in ("NO", "UNCERTAIN"):
        rows = rows_for(packet, {item["item_id"]: label})
        assert rows[0]["detection_turn"] is None
        valid = validate_labels(
            packet,
            {"rater-a": submission(packet, "rater-a", rows), "rater-b": submission(packet, "rater-b", rows)},
        )
        assert valid["status"] == "COMPUTED"

        rows[0]["detection_turn"] = 1
        invalid = validate_labels(
            packet,
            {"rater-a": submission(packet, "rater-a", rows), "rater-b": submission(packet, "rater-b", rows)},
        )
        assert invalid["status"] == "INVALID"
        assert any(f"is {label} but detection_turn must be null" in error for error in invalid["errors"])


def test_no_explicit_statement_forces_detection_unavailable() -> None:
    record = human_record(
        "HUMAN-REC-2",
        cause="TURN_CAP",
        turns=[human_turn(1, rationale="no privileged signal observed; continue low-noise recon")],
    )
    packet = build_packet([record], seed=11, rater_count=2)
    item = packet["items"][0]

    assert item["detection_rating_allowed"] is False
    assert item["detection_evidence_status"] == "UNAVAILABLE"
    assert {row["kind"] for row in item["attacker_statements"]} == {"RATIONALE"}
    assert packet["detection_unavailable_items"] == 1
    assert packet["status"] == "READY_FOR_BLIND_HUMAN_LABELING_DETECTION_PARTIAL"

    unavailable_rows = rows_for(packet)
    valid = validate_labels(
        packet,
        {
            "rater-a": submission(packet, "rater-a", unavailable_rows),
            "rater-b": submission(packet, "rater-b", unavailable_rows),
        },
    )
    assert valid["status"] == "COMPUTED"

    inferred = rows_for(packet, {item["item_id"]: "YES"})
    inferred[0]["detection_turn"] = 1
    invalid = validate_labels(
        packet,
        {"rater-a": submission(packet, "rater-a", inferred), "rater-b": submission(packet, "rater-b", inferred)},
    )
    assert invalid["status"] == "INVALID"
    assert any("must be UNAVAILABLE, not inferred" in error for error in invalid["errors"])
    assert any("carries a detection_turn" in error for error in invalid["errors"])


def test_completed_unique_rows_and_rater_identity_are_enforced() -> None:
    packet = suspicious_packet()
    good_rows = rows_for(packet)

    incomplete = validate_labels(
        packet,
        {
            "rater-a": submission(packet, "rater-a", good_rows, completed=False),
            "rater-b": submission(packet, "rater-b", good_rows),
        },
    )
    assert incomplete["status"] == "INVALID"
    assert any("completed must be true" in error for error in incomplete["errors"])

    duplicated = validate_labels(
        packet,
        {
            "rater-a": submission(packet, "rater-a", [good_rows[0], good_rows[0]]),
            "rater-b": submission(packet, "rater-b", good_rows),
        },
    )
    assert duplicated["status"] == "INVALID"
    assert any("duplicate item rows are forbidden" in error for error in duplicated["errors"])

    reused = validate_labels(
        packet,
        {
            "rater-a": submission(packet, "rater-a", good_rows, declared="ghost-rater"),
            "rater-b": submission(packet, "rater-b", good_rows, declared="ghost-rater"),
        },
    )
    assert reused["status"] == "INVALID"
    assert any("does not match the submission key" in error for error in reused["errors"])
    assert any("used by more than one submission" in error for error in reused["errors"])

    distinct = validate_labels(
        packet,
        {
            "rater-a": submission(packet, "rater-a", good_rows),
            "rater-b": submission(packet, "rater-b", good_rows),
        },
    )
    assert distinct["status"] == "COMPUTED"
    assert distinct["raters"] == ["rater-a", "rater-b"]
