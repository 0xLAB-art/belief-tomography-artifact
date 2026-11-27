"""Two-track session record contract and integrity validation.

The record is the analysis unit: one SSH session (Track B) or one fixed-trace
response cell (Track A). Turns are clustered within the record and are never
treated as independent observations. The validator refuses silent coercion of
missing data and refuses to mix ``TEST_ONLY`` integration controls with
measured sessions.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

SCHEMA = "ragin.ablation.session_record.v1"
TRACKS = {"A", "B"}
ARMS = {"B0", "B1", "B2", "B3"}
SPLITS = {"development", "calibration", "holdout"}
TERMINAL_CAUSES = {
    "DETECTION",
    "ABANDONMENT",
    "OBJECTIVE_COMPLETION",
    "TURN_CAP",
    "ADMIN_CENSORED",
    "TECHNICAL_FAILURE",
    "UNAVAILABLE",
}
GENERATION_KINDS = {"NATIVE_SHELL", "GENERATED", "TEMPLATE", "FALLBACK", "MOCK", "UNAVAILABLE"}
SERVE_STATUSES = {"SERVED", "REJECTED", "FAILED", "EMPTY", "UNAVAILABLE"}
SERVED_AVAILABILITY = {"RAW", "REDACTED_MINIMIZED", "UNAVAILABLE"}
AVAILABILITY = {"MEASURED", "ESTIMATED", "UNAVAILABLE"}
EXPOSURE = {"OBSERVED", "CONFIGURED_NOT_OBSERVED", "NOT_APPLICABLE", "UNAVAILABLE"}
TOP_LEVEL_REQUIRED = (
    "schema",
    "record_id",
    "track",
    "test_only",
    "split",
    "block_id",
    "allocation_index",
    "arm",
    "scenario_id",
    "profile_id",
    "seed",
    "provenance",
    "turns",
    "terminal_cause",
    "detection_turn",
    "event_turn",
    "objective_action_indices",
    "operational",
    "verification",
)
TURN_REQUIRED = (
    "turn",
    "command",
    "serve_status",
    "served_text",
    "served_text_sha256",
    "served_raw_sha256",
    "served_availability",
    "generation_kind",
    "decision_consumed",
    "arm_exposure",
    "model_exposure",
    "input_redacted",
    "raw_input_sha256",
    "latency_ms",
    "tokens_in",
    "tokens_out",
    "cost_usd",
    "verification",
)
HASH_LEN = 64


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _is_sha(value: Any) -> bool:
    return isinstance(value, str) and len(value) == HASH_LEN and all(c in "0123456789abcdef" for c in value)


def _check_measurement(value: Any, *, label: str, errors: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append(f"{label} must be an object with availability/value")
        return
    availability = value.get("availability")
    if availability not in AVAILABILITY:
        errors.append(f"{label}.availability must be one of {sorted(AVAILABILITY)}, got {availability!r}")
        return
    if availability == "UNAVAILABLE":
        if "value" in value and value.get("value") is not None:
            errors.append(f"{label} is UNAVAILABLE but carries a value; missing must not be coerced to zero")
    elif isinstance(value.get("value"), bool) or not isinstance(value.get("value"), (int, float)):
        errors.append(f"{label} is {availability} but has no finite numeric value")
    elif not math.isfinite(float(value["value"])):
        errors.append(f"{label} must be finite (NaN/inf are not measurements)")
    elif value["value"] < 0:
        errors.append(f"{label} must be non-negative")


def _check_verification(verification: Any, *, label: str, errors: list[str]) -> None:
    if not isinstance(verification, dict):
        errors.append(f"{label} must be an object")
        return
    if not isinstance(verification.get("passed"), bool):
        errors.append(f"{label}.passed must be a boolean, got {verification.get('passed')!r}")
    if not verification.get("profile"):
        errors.append(f"{label}.profile is required")


def validate_turn(turn: dict[str, Any], *, index: int, record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    label = f"turns[{index}]"
    for key in TURN_REQUIRED:
        if key not in turn:
            errors.append(f"{label} missing {key}")
    if turn.get("turn") != index + 1:
        errors.append(f"{label}.turn must be {index + 1}, got {turn.get('turn')!r}")
    command = turn.get("command")
    if not isinstance(command, str) or not command.strip():
        errors.append(f"{label}.command must be a non-empty string")
    serve_status = turn.get("serve_status")
    if serve_status not in SERVE_STATUSES:
        errors.append(f"{label}.serve_status must be one of {sorted(SERVE_STATUSES)}")
    availability = turn.get("served_availability")
    if availability not in SERVED_AVAILABILITY:
        errors.append(f"{label}.served_availability must be one of {sorted(SERVED_AVAILABILITY)}")
    served_text = turn.get("served_text")
    if not isinstance(served_text, str):
        errors.append(f"{label}.served_text must be a string (empty is allowed for a failed/rejected turn)")
        served_text = ""
    text_sha = turn.get("served_text_sha256")
    raw_sha = turn.get("served_raw_sha256")
    if not _is_sha(text_sha):
        errors.append(f"{label}.served_text_sha256 must hash the stored (possibly redacted) text")
    elif sha256_text(served_text) != text_sha:
        errors.append(f"{label}.served_text_sha256 does not match the stored text")
    if serve_status == "SERVED":
        if not served_text:
            errors.append(f"{label} is SERVED but served_text is empty")
        if availability == "UNAVAILABLE":
            errors.append(f"{label} is SERVED but served availability is UNAVAILABLE")
        if not _is_sha(raw_sha):
            errors.append(f"{label}.served_raw_sha256 is required for a served turn")
    else:
        if not turn.get("failure_reason"):
            errors.append(f"{label}.failure_reason is required for serve_status={serve_status!r}")
        if raw_sha is not None and not _is_sha(raw_sha):
            errors.append(f"{label}.served_raw_sha256 must be a SHA-256 when present")
    if availability == "RAW" and _is_sha(raw_sha) and raw_sha != text_sha:
        errors.append(f"{label} declares RAW availability but raw and stored-text hashes differ")
    if availability == "REDACTED_MINIMIZED" and raw_sha is not None and raw_sha == text_sha:
        errors.append(f"{label} declares REDACTED_MINIMIZED but raw and stored-text hashes are identical")

    kind = turn.get("generation_kind")
    if kind not in GENERATION_KINDS:
        errors.append(f"{label}.generation_kind must be one of {sorted(GENERATION_KINDS)}")
    candidate = turn.get("candidate_sha256")
    verified = turn.get("verified_sha256")
    if serve_status == "SERVED":
        if kind == "GENERATED":
            for name, value in (("candidate_sha256", candidate), ("verified_sha256", verified)):
                if not _is_sha(value):
                    errors.append(f"{label}.{name} is required for a generated serve")
            if _is_sha(candidate) and _is_sha(verified) and candidate != verified:
                errors.append(f"{label} candidate and verified hashes differ")
            if _is_sha(verified) and verified != raw_sha:
                errors.append(f"{label} verified and raw-served hashes differ")
        elif kind in {"TEMPLATE", "FALLBACK"}:
            if not _is_sha(turn.get("verified_sha256")):
                errors.append(f"{label}.verified_sha256 is required for a {kind} serve")
            if _is_sha(turn.get("verified_sha256")) and turn["verified_sha256"] != raw_sha:
                errors.append(f"{label} verified and raw-served hashes differ for {kind}")
        elif kind == "MOCK":
            if record.get("test_only") is not True:
                errors.append(f"{label} is MOCK outside a TEST_ONLY record")
            if turn.get("verified_sha256") is not None and not _is_sha(turn.get("verified_sha256")):
                errors.append(f"{label}.verified_sha256 must be a SHA-256 when present")
        elif kind == "NATIVE_SHELL":
            if candidate is not None:
                errors.append(f"{label} native shell must not claim a generated candidate hash")
    elif kind != "UNAVAILABLE" and candidate is not None:
        errors.append(f"{label} failed/rejected turn must not claim a candidate hash")

    if not isinstance(turn.get("decision_consumed"), bool):
        errors.append(
            f"{label}.decision_consumed must be a boolean "
            "(generated/template/fallback/decision are distinct)"
        )
    exposure = turn.get("arm_exposure")
    if exposure not in EXPOSURE:
        errors.append(f"{label}.arm_exposure must be one of {sorted(EXPOSURE)}")
    model_exposure = turn.get("model_exposure")
    if not isinstance(model_exposure, dict):
        errors.append(f"{label}.model_exposure must be an object")
    else:
        if model_exposure.get("observed") not in (True, False):
            errors.append(f"{label}.model_exposure.observed must be boolean")
        if record.get("arm") in {"B1", "B2", "B3"} and model_exposure.get("observed") is True:
            for key in ("model_id", "model_sha256"):
                if not model_exposure.get(key):
                    errors.append(f"{label}.model_exposure missing {key} for an observed model attempt")
    if not isinstance(turn.get("input_redacted"), str) or not turn.get("input_redacted"):
        errors.append(f"{label}.input_redacted must be a non-empty redacted string")
    if not _is_sha(turn.get("raw_input_sha256")):
        errors.append(f"{label}.raw_input_sha256 must record the raw-input integrity hash")
    for key in ("latency_ms", "tokens_in", "tokens_out", "cost_usd"):
        _check_measurement(turn.get(key), label=f"{label}.{key}", errors=errors)
    _check_verification(turn.get("verification"), label=f"{label}.verification", errors=errors)
    if record.get("arm") == "B0" and turn.get("verification", {}).get("profile") != "NATIVE_TRANSPORT_ONLY":
        errors.append(f"{label}.verification.profile must be NATIVE_TRANSPORT_ONLY for B0")
    return errors


def validate_record(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in TOP_LEVEL_REQUIRED:
        if key not in record:
            errors.append(f"record missing {key}")
    if record.get("schema") != SCHEMA:
        errors.append(f"unsupported record schema: {record.get('schema')!r}")
    if record.get("track") not in TRACKS:
        errors.append(f"track must be one of {sorted(TRACKS)}")
    if record.get("arm") not in ARMS:
        errors.append(f"arm must be one of {sorted(ARMS)}")
    if record.get("split") not in SPLITS:
        errors.append(f"split must be one of {sorted(SPLITS)}")
    if not isinstance(record.get("test_only"), bool):
        errors.append("test_only must be boolean")
    if record.get("test_only") is True:
        label = str(record.get("test_label") or "")
        if not label.startswith("TEST_ONLY"):
            errors.append("test_only records require a test_label beginning with TEST_ONLY")
        if record.get("split") == "holdout":
            errors.append("TEST_ONLY records must never use the holdout split")
    else:
        provenance = record.get("provenance") or {}
        if provenance.get("mock") is not False:
            errors.append("measured record must declare provenance.mock=false")
        if record.get("replace_of"):
            errors.append("outcome-dependent replacement is forbidden; replace_of must be absent")
    provenance = record.get("provenance") or {}
    for key in ("transport", "generator", "llm_inference"):
        if not provenance.get(key):
            errors.append(f"provenance.{key} is required")
    if provenance.get("llm_inference") not in {"ESTABLISHED", "NOT_ESTABLISHED"}:
        errors.append("provenance.llm_inference must be ESTABLISHED or NOT_ESTABLISHED")
    if record.get("test_only") is True and provenance.get("llm_inference") == "ESTABLISHED":
        errors.append("a TEST_ONLY integration control cannot claim established LLM inference")
    if not isinstance(record.get("allocation_index"), int) or record["allocation_index"] < 0:
        errors.append("allocation_index must be a non-negative integer")
    if not isinstance(record.get("seed"), int):
        errors.append("seed must be an integer")
    for key in ("block_id", "scenario_id", "profile_id", "record_id"):
        if not isinstance(record.get(key), str) or not record.get(key):
            errors.append(f"{key} must be a non-empty string")

    turns = record.get("turns")
    if not isinstance(turns, list):
        errors.append("turns must be a list")
        turns = []
    if len(turns) > 12:
        errors.append(f"turn count {len(turns)} exceeds the protocol cap of 12")
    for index, turn in enumerate(turns):
        if not isinstance(turn, dict):
            errors.append(f"turns[{index}] is not an object")
            continue
        errors.extend(validate_turn(turn, index=index, record=record))

    cause = record.get("terminal_cause")
    detection_turn = record.get("detection_turn")
    if cause not in TERMINAL_CAUSES:
        errors.append(f"terminal_cause must be one of {sorted(TERMINAL_CAUSES)}")
    event_turn = record.get("event_turn")
    if cause == "DETECTION":
        if not isinstance(detection_turn, int) or not (1 <= detection_turn <= len(turns)):
            errors.append("DETECTION requires detection_turn within the observed turns")
        if not isinstance(event_turn, int) or isinstance(event_turn, bool) or event_turn < 1:
            errors.append("DETECTION requires an explicit positive event_turn")
        elif isinstance(detection_turn, int) and detection_turn != event_turn:
            errors.append("DETECTION event_turn must equal detection_turn; contradictory event times are forbidden")
    elif detection_turn is not None:
        errors.append(f"terminal_cause {cause} must not carry a detection_turn (it is not a detection event)")
    if cause == "TURN_CAP":
        if len(turns) != 12:
            errors.append("TURN_CAP requires exactly 12 observed turns")
        if event_turn != 12:
            errors.append("TURN_CAP requires an explicit event_turn=12")
    elif cause == "ADMIN_CENSORED":
        if not isinstance(event_turn, int) or event_turn != len(turns) or not (1 <= event_turn <= 12):
            errors.append("ADMIN_CENSORED requires event_turn equal to the observed turn count (1..12)")
    elif cause == "UNAVAILABLE":
        if turns:
            errors.append("UNAVAILABLE sessions must not carry served turns")
        if event_turn not in (0, 1):
            errors.append("UNAVAILABLE requires event_turn 0 (pre-interaction) or 1")
    elif cause == "TECHNICAL_FAILURE":
        if not record.get("technical_reason"):
            errors.append("TECHNICAL_FAILURE requires technical_reason")
        if not isinstance(event_turn, int) or event_turn < 1:
            errors.append("TECHNICAL_FAILURE requires an explicit positive event_turn")
    elif cause in {"DETECTION", "ABANDONMENT", "OBJECTIVE_COMPLETION"}:
        if not isinstance(event_turn, int) or event_turn < 1:
            errors.append(f"{cause} requires an explicit positive event_turn")

    operational = record.get("operational")
    if not isinstance(operational, dict):
        errors.append("operational must be an object")
    else:
        eligible = [
            (index, turn)
            for index, turn in enumerate(turns)
            if isinstance(turn, dict) and turn.get("serve_status") in {"SERVED", "EMPTY"}
        ]
        commands = [str(turn.get("command", "")) for _, turn in eligible]
        index_map = {original: position for position, (original, _) in enumerate(eligible)}
        indices = record.get("objective_action_indices")
        if not isinstance(indices, list) or any(
            not isinstance(item, int) or isinstance(item, bool) or item not in index_map for item in indices
        ):
            errors.append(
                "objective_action_indices must be a list of zero-based turn indices that produced SERVED/EMPTY turns"
            )
            indices = []
        mapped_indices = [index_map[item] for item in indices]
        from ragin.evaluation.attacker_policies import engagement_denominators

        recomputed = engagement_denominators(commands, objective_actions=sorted(mapped_indices))
        for key in ("served_turns", "substantive_turns", "automated_noop_turns", "objective_directed_actions"):
            if operational.get(key) != recomputed[key]:
                errors.append(
                    f"operational.{key}={operational.get(key)!r} disagrees with the "
                    f"turn-derived value {recomputed[key]!r}"
                )
    _check_verification(record.get("verification"), label="verification", errors=errors)
    return errors


def validate_record_set(records: list[dict[str, Any]]) -> list[str]:
    """Validate a complete set, including blocking and TEST_ONLY separation."""
    errors: list[str] = []
    for record in records:
        errors.extend(f"{record.get('record_id', '<unknown>')}: {error}" for error in validate_record(record))
    if not records:
        return errors + ["no records"]

    test_flags = {bool(record.get("test_only")) for record in records}
    if len(test_flags) > 1:
        errors.append("mixed TEST_ONLY and measured records in one set")
    splits = {str(record.get("split")) for record in records}
    if len(splits) > 1:
        errors.append(f"mixed splits in one set: {sorted(splits)}")

    slots: dict[tuple[Any, ...], str] = {}
    block_arms: dict[tuple[str, str], str] = {}
    blocks: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        slot = (record.get("allocation_index"), record.get("block_id"), record.get("arm"))
        if slot in slots:
            errors.append(f"duplicate allocation slot {slot}: {slots[slot]} and {record.get('record_id')}")
        slots[slot] = str(record.get("record_id"))
        block_arm = (str(record.get("block_id")), str(record.get("arm")))
        if block_arm in block_arms:
            errors.append(
                f"duplicate block+arm {block_arm}: {block_arms[block_arm]} and {record.get('record_id')}; "
                "records are never overwritten"
            )
        block_arms[block_arm] = str(record.get("record_id"))
        blocks.setdefault(str(record.get("block_id")), []).append(record)
    for block_id, rows in blocks.items():
        arms = sorted(str(row.get("arm")) for row in rows)
        if len(arms) != len(set(arms)):
            errors.append(f"block {block_id} has duplicate arms")
    return errors


def read_records(path: Path) -> list[dict[str, Any]]:
    records = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_number}: {exc}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_number}: record is not an object")
        records.append(value)
    return records


def write_records(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f"refusing to overwrite frozen records: {path}")
    path.write_text(
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )
