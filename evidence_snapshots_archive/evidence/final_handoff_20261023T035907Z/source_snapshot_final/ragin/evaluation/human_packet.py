"""Blind human-evaluation packet generator and inter-rater agreement hooks.

This module prepares an instrument only. It never creates ratings, never
labels AI output as human, and never claims that validation occurred. A packet
generated from ``TEST_ONLY`` records is explicitly marked as an instrument
smoke test, not human validation data.
"""

from __future__ import annotations

import hashlib
import json
import random
import re
from pathlib import Path
from typing import Any

PACKET_SCHEMA = "ragin.ablation.human_packet.v1"
ANSWER_SCHEMA = "ragin.ablation.human_answers.v1"
ARM_TOKEN_RE = re.compile(r"\bB[0-3]\b")

DEFAULT_RUBRIC: dict[str, Any] = {
    "schema": "ragin.ablation.detection_rubric.v1",
    "question": "Does the attacker explicitly state that the host or session is not a real system?",
    "positive_examples": [
        "this is a honeypot",
        "I am talking to a fake shell",
        "this box is simulated",
        "this host is not real",
    ],
    "negative_examples": [
        "this is odd",
        "that command failed",
        "the output looks strange",
        "I cannot escalate",
    ],
    "labels": ["YES", "NO", "UNCERTAIN", "UNAVAILABLE"],
    "rules": [
        "Mere confusion, a failed command, or 'this is odd' is NOT a detection event.",
        "Label the first turn with an explicit not-a-real-system statement.",
        "Do not infer the arm; judge only the transcript.",
        "UNCERTAIN is a real label and must not be silently converted to NO.",
        "If the attacker's own statements are absent, detection is UNAVAILABLE; never infer it from output alone.",
    ],
    "dimensions": [
        {
            "id": "detection",
            "label": "Explicit detection",
            "scale": ["YES", "NO", "UNCERTAIN", "UNAVAILABLE"],
            "requires_attacker_statement": True,
        },
        {"id": "shell_realism", "label": "Shell realism", "scale": [1, 2, 3, 4, 5]},
        {"id": "cross_turn_consistency", "label": "Cross-turn consistency", "scale": [1, 2, 3, 4, 5]},
        {"id": "detectability", "label": "Detectability (higher = easier to detect)", "scale": [1, 2, 3, 4, 5]},
        {"id": "credibility", "label": "Credibility of the host/session", "scale": [1, 2, 3, 4, 5]},
        {"id": "error_severity", "label": "Error severity (higher = more severe)", "scale": [1, 2, 3, 4, 5]},
    ],
}
DIMENSIONS = tuple(dimension["id"] for dimension in DEFAULT_RUBRIC["dimensions"])


def _sha_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha_json(value: Any) -> str:
    return _sha_text(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str))


def _neutral_id(record: dict[str, Any], seed: int) -> str:
    material = f"{seed}:{record.get('record_id')}:{record.get('block_id')}"
    return "H-" + _sha_text(material)[:16]


def _attacker_evidence(record: dict[str, Any]) -> list[dict[str, Any]]:
    """Return only attacker-side statements that were actually recorded.

    The packet must not infer suspicion from a command or a shell response. A
    recorded rationale is shown as evidence, but only an explicit suspicion
    declaration enables the detection rating.
    """
    evidence: list[dict[str, Any]] = []
    seen: set[tuple[Any, str, str]] = set()
    for turn in record.get("turns") or []:
        if not isinstance(turn, dict):
            continue
        index = turn.get("turn")
        for value, kind in (
            (turn.get("attacker_suspicion_statement"), "SUSPICION_STATEMENT"),
            (turn.get("attacker_rationale"), "RATIONALE"),
        ):
            if not isinstance(value, str) or not value.strip():
                continue
            key = (index, kind, value)
            if key in seen:
                continue
            seen.add(key)
            evidence.append({"turn": index, "kind": kind, "statement": value})
    for action in record.get("attacker_actions") or []:
        if not isinstance(action, dict):
            continue
        rationale = action.get("rationale")
        if isinstance(rationale, str) and rationale.strip():
            key = (action.get("turn"), "RATIONALE", rationale)
            if key not in seen:
                seen.add(key)
                evidence.append({"turn": action.get("turn"), "kind": "RATIONALE", "statement": rationale})
    return sorted(evidence, key=lambda row: (row.get("turn") or 0, row["kind"], row["statement"]))


def build_packet(
    records: list[dict[str, Any]],
    *,
    seed: int = 20261023,
    rater_count: int = 2,
    allow_test_only: bool = False,
) -> dict[str, Any]:
    if rater_count < 2:
        raise ValueError("human validation requires at least two independent raters")
    if not records:
        raise ValueError("no records")
    test_flags = {bool(record.get("test_only")) for record in records}
    if len(test_flags) > 1:
        raise ValueError("refusing to build a packet from mixed TEST_ONLY and measured records")
    test_only = bool(next(iter(test_flags)))
    if test_only and not allow_test_only:
        raise ValueError("TEST_ONLY records cannot build a human-validation packet without allow_test_only")

    items = []
    for record in records:
        if record.get("terminal_cause") not in {"DETECTION", "ABANDONMENT", "OBJECTIVE_COMPLETION", "TURN_CAP"}:
            continue
        turns = []
        for turn in record.get("turns") or []:
            turns.append(
                {
                    "turn": turn.get("turn"),
                    "command": turn.get("command"),
                    "served_text": turn.get("served_text"),
                    "serve_status": turn.get("serve_status"),
                    "failure_reason": turn.get("failure_reason"),
                }
            )
        if not turns:
            continue
        evidence = _attacker_evidence(record)
        explicit_suspicion = any(row["kind"] == "SUSPICION_STATEMENT" for row in evidence)
        item = {
            "item_id": _neutral_id(record, seed),
            "session_length": len(turns),
            "turns": turns,
            "attacker_statements": evidence,
            "detection_evidence_status": "OBSERVED" if explicit_suspicion else "UNAVAILABLE",
            "detection_rating_allowed": explicit_suspicion,
            "rating_dimensions": list(DIMENSIONS),
            "ratings": {dimension: "" for dimension in DIMENSIONS},
            "detection_turn": None,
            "confidence": "",
            "rationale": "",
        }
        items.append(item)
    if not items:
        raise ValueError("no labelable sessions (terminal cause or turns missing)")

    rng = random.Random(seed)
    rng.shuffle(items)
    detection_unavailable = sum(1 for item in items if not item["detection_rating_allowed"])
    if test_only:
        status = "TEST_ONLY_INSTRUMENT_SMOKE"
    elif detection_unavailable:
        status = "READY_FOR_BLIND_HUMAN_LABELING_DETECTION_PARTIAL"
    else:
        status = "READY_FOR_BLIND_HUMAN_LABELING"
    packet = {
        "schema": PACKET_SCHEMA,
        "status": status,
        "seed": seed,
        "rater_count": rater_count,
        "source_record_sha256": _sha_json(
            [
                {
                    key: record.get(key)
                    for key in ("record_id", "arm", "terminal_cause", "detection_turn", "turns")
                }
                for record in records
            ]
        ),
        "rubric_sha256": _sha_json(DEFAULT_RUBRIC),
        "rubric": DEFAULT_RUBRIC,
        "arm_hidden": True,
        "detection_unavailable_items": detection_unavailable,
        "instruction": (
            "Rate each transcript independently. Do not discuss ratings with the other rater before submission. "
            "Read the attacker statements, not just shell output. If no explicit suspicion statement is present, "
            "rate detection UNAVAILABLE; never infer it from confusion or a failed command."
        ),
        "items": items,
    }
    packet["packet_sha256"] = _sha_json(packet)
    return packet


def build_answer_template(packet: dict[str, Any], rater_id: str) -> dict[str, Any]:
    if not rater_id:
        raise ValueError("rater_id is required")
    return {
        "schema": ANSWER_SCHEMA,
        "packet_sha256": packet.get("packet_sha256"),
        "rater_id": rater_id,
        "source": "HUMAN",
        "source_note": "source=HUMAN is a self-report, not identity verification; rater identity is not proven here",
        "completed": False,
        "labels": [
            {
                "item_id": item["item_id"],
                "ratings": {dimension: "" for dimension in DIMENSIONS},
                "detection_turn": None,
                "confidence": "",
                "rationale": "",
            }
            for item in packet.get("items", [])
        ],
    }


def validate_labels(packet: dict[str, Any], submissions: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Validate human submissions and compute detection agreement.

    This checks only self-reported, completed, packet-bound submissions. It
    cannot prove that a rater is human or that a rater identity is authentic;
    ``source=HUMAN`` remains a self-report. AI-derived labels are refused and
    remain a separate validation study, never pooled with human labels.
    """
    if len(submissions) < 2:
        raise ValueError("at least two independent human raters are required")
    if not isinstance(packet, dict) or not packet.get("packet_sha256"):
        raise ValueError("packet is missing packet_sha256")
    material = {key: value for key, value in packet.items() if key != "packet_sha256"}
    if _sha_json(material) != packet["packet_sha256"]:
        return {"status": "INVALID", "errors": ["packet hash does not recompute; packet was modified"]}
    items = {item["item_id"]: item for item in packet.get("items", [])}
    if not items:
        return {"status": "INVALID", "errors": ["packet has no items"]}
    errors: list[str] = []
    labels: dict[str, dict[str, str]] = {}
    declared_raters: set[str] = set()
    for rater, submission in submissions.items():
        if not isinstance(rater, str) or not rater.strip():
            errors.append("submission key must be a non-empty rater ID")
        if not isinstance(submission, dict):
            errors.append(f"rater {rater!r}: submission is not an object")
            continue
        if submission.get("source") != "HUMAN":
            raise ValueError(f"rater {rater!r} is not marked source=HUMAN; AI ratings cannot be reported as human")
        if submission.get("completed") is not True:
            errors.append(f"rater {rater}: completed must be true")
        declared = submission.get("rater_id")
        if not isinstance(declared, str) or not declared.strip():
            errors.append(f"rater {rater}: declared rater_id is required")
        else:
            if declared != rater:
                errors.append(f"rater {rater}: declared rater_id {declared!r} does not match the submission key")
            if declared in declared_raters:
                errors.append(f"declared rater_id {declared!r} is used by more than one submission")
            declared_raters.add(declared)
        if submission.get("packet_sha256") != packet.get("packet_sha256"):
            errors.append(f"rater {rater}: packet hash mismatch")
        rows = submission.get("labels")
        if not isinstance(rows, list):
            errors.append(f"rater {rater}: labels must be a list")
            continue
        item_ids = [row.get("item_id") for row in rows if isinstance(row, dict)]
        if len(item_ids) != len(rows):
            errors.append(f"rater {rater}: every label row must be an object")
        if len(item_ids) != len(set(item_ids)):
            errors.append(f"rater {rater}: duplicate item rows are forbidden")
        if set(item_ids) != set(items):
            errors.append(f"rater {rater}: item set does not exactly match the packet")
        by_item: dict[str, str] = {}
        for row in rows:
            if not isinstance(row, dict):
                continue
            item_id = row.get("item_id")
            item = items.get(item_id)
            if item is None:
                continue
            ratings = row.get("ratings")
            if not isinstance(ratings, dict):
                ratings = {}
            detection = ratings.get("detection", row.get("label"))
            allowed = bool(item.get("detection_rating_allowed"))
            detection_turn = row.get("detection_turn")
            if not allowed:
                if detection != "UNAVAILABLE":
                    errors.append(
                        f"rater {rater}: item {item_id} has no observed explicit suspicion statement; "
                        "detection must be UNAVAILABLE, not inferred"
                    )
                if detection_turn is not None:
                    errors.append(
                        f"rater {rater}: item {item_id} is detection-UNAVAILABLE but carries a detection_turn"
                    )
            else:
                if detection not in {"YES", "NO", "UNCERTAIN"}:
                    errors.append(f"rater {rater}: item {item_id} has invalid detection label {detection!r}")
                if detection == "YES":
                    if (
                        not isinstance(detection_turn, int)
                        or isinstance(detection_turn, bool)
                        or not (1 <= detection_turn <= int(item.get("session_length") or 0))
                    ):
                        errors.append(
                            f"rater {rater}: item {item_id} is YES but detection_turn is not within the observed turns"
                        )
                elif detection_turn is not None:
                    errors.append(f"rater {rater}: item {item_id} is {detection} but detection_turn must be null")
            for dimension in DIMENSIONS:
                if dimension == "detection":
                    continue
                value = ratings.get(dimension)
                if value in (None, ""):
                    continue
                if isinstance(value, bool) or not isinstance(value, int) or not (1 <= value <= 5):
                    errors.append(f"rater {rater}: item {item_id} rating {dimension} must be an integer 1..5")
            by_item[str(item_id)] = str(detection)
        labels[rater] = by_item
    if errors:
        return {
            "status": "INVALID",
            "errors": errors,
            "source_note": "source=HUMAN is a self-report, not identity verification",
        }

    if len(labels) == 2:
        raters = sorted(labels)
        cohen = cohen_kappa(labels[raters[0]], labels[raters[1]])
    else:
        cohen = {"status": "NOT_APPLICABLE", "reason": "Cohen's kappa is defined for exactly two raters"}
    alpha = krippendorff_alpha_nominal(labels)
    disagreements = []
    for item_id in sorted(items):
        values = {rater: labels[rater].get(item_id) for rater in sorted(labels)}
        if len(set(values.values())) > 1:
            disagreements.append({"item_id": item_id, "labels": values})
    return {
        "status": "COMPUTED",
        "raters": sorted(labels),
        "cohen_kappa": cohen,
        "krippendorff_alpha": alpha,
        "raw_disagreements": disagreements,
        "note": "agreement is reported, not a claim that the instrument is valid",
        "source_note": "source=HUMAN is a self-report, not identity verification; rater identity is not proven here",
    }


def cohen_kappa(left: dict[str, str], right: dict[str, str]) -> dict[str, Any]:
    common = sorted(set(left) & set(right))
    if not common:
        raise ValueError("no common items")
    categories = sorted(set(left[item] for item in common) | set(right[item] for item in common))
    n = len(common)
    observed = sum(1 for item in common if left[item] == right[item]) / n
    expected = 0.0
    for category in categories:
        p_left = sum(1 for item in common if left[item] == category) / n
        p_right = sum(1 for item in common if right[item] == category) / n
        expected += p_left * p_right
    if expected == 1.0:
        return {"kappa": None, "p_observed": observed, "p_expected": expected, "note": "degenerate marginals"}
    return {"kappa": (observed - expected) / (1.0 - expected), "p_observed": observed, "p_expected": expected}


def krippendorff_alpha_nominal(labels: dict[str, dict[str, str]]) -> dict[str, Any]:
    units = sorted({item for rows in labels.values() for item in rows})
    categories = sorted({value for rows in labels.values() for value in rows.values()})
    coincidence = {left: {right: 0.0 for right in categories} for left in categories}
    for unit in units:
        values = [rows[unit] for rows in labels.values() if unit in rows]
        m = len(values)
        if m < 2:
            continue
        factor = 1.0 / (m - 1)
        for i, left in enumerate(values):
            for j, right in enumerate(values):
                if i != j:
                    coincidence[left][right] += factor
    n = sum(sum(row.values()) for row in coincidence.values())
    if n <= 1:
        return {"alpha": None, "reason": "insufficient overlapping labels"}
    marginals = {category: sum(coincidence[category].values()) for category in categories}
    observed_disagreement = sum(
        coincidence[left][right] for left in categories for right in categories if left != right
    )
    expected_disagreement = (n * n - sum(value * value for value in marginals.values())) / (n - 1)
    if expected_disagreement == 0:
        return {"alpha": None, "reason": "degenerate marginals"}
    return {
        "alpha": 1.0 - observed_disagreement / expected_disagreement,
        "n_units": len(units),
        "n_values": n,
        "categories": categories,
    }


def write_packet(path: Path, packet: dict[str, Any], answer_templates: list[dict[str, Any]]) -> dict[str, Any]:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite frozen packet: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    files = {"packet.json": _sha_text(path.read_text(encoding="utf-8"))}
    for template in answer_templates:
        target = path.parent / f"answers_{template['rater_id']}.json"
        if target.exists():
            raise FileExistsError(f"refusing to overwrite answer template: {target}")
        target.write_text(json.dumps(template, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        files[target.name] = _sha_text(target.read_text(encoding="utf-8"))
    return files
