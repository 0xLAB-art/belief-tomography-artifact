"""Prespecified session-level competing-risks analysis.

Primary estimand: cause-specific cumulative incidence of explicit detection at
turn 12, with abandonment/objective completion and technical failure/unavailable
as explicit competing causes. The unit is the session; turns are never
pseudoreplicated. The primary between-arm summaries are paired risk differences
from matched blocks with block-bootstrap 95% CIs.

Missing, incomplete, mismatched or unexposed arms produce ``NOT_ESTABLISHED``.
They are never coerced to a zero effect.
"""

from __future__ import annotations

import math
import random
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

PRIMARY_CAUSE = "DETECTION"
COMPETING_CAUSES = ("ABANDONMENT", "OBJECTIVE_COMPLETION", "TECHNICAL_FAILURE", "UNAVAILABLE")
EVENT_CAUSES = (PRIMARY_CAUSE, *COMPETING_CAUSES)
CENSOR_CAUSES = ("TURN_CAP", "ADMIN_CENSORED")
ALL_TERMINAL = (*EVENT_CAUSES, *CENSOR_CAUSES)


class DataContractError(ValueError):
    """Raised when records cannot support the prespecified analysis."""


def _event_time(record: dict[str, Any]) -> int:
    """Return an explicit event/censor time; never invent a default.

    ``UNAVAILABLE`` may carry ``event_turn=0`` only when it is declared as a
    pre-interaction unavailability. All other causes require an explicit,
    valid positive event turn.
    """
    cause = record.get("terminal_cause")
    turn = record.get("event_turn")
    if cause == "DETECTION":
        turn = record.get("detection_turn")
        if not isinstance(turn, int) or isinstance(turn, bool) or turn < 1:
            raise DataContractError(f"{record.get('record_id')}: detection without a valid positive detection_turn")
        return turn
    if cause in CENSOR_CAUSES:
        if not isinstance(turn, int) or isinstance(turn, bool) or turn < 1:
            raise DataContractError(f"{record.get('record_id')}: {cause} requires an explicit positive event_turn")
        turns = record.get("turns") or []
        if isinstance(turns, list) and turns and turn != len(turns):
            raise DataContractError(f"{record.get('record_id')}: {cause} event_turn must equal observed turn count")
        return turn
    if cause == "UNAVAILABLE":
        if not isinstance(turn, int) or isinstance(turn, bool) or turn < 0:
            raise DataContractError(
                f"{record.get('record_id')}: UNAVAILABLE requires an explicit event_turn (0 pre-interaction or >=1)"
            )
        return turn
    if cause in COMPETING_CAUSES:
        if not isinstance(turn, int) or isinstance(turn, bool) or turn < 1:
            raise DataContractError(f"{record.get('record_id')}: {cause} requires an explicit positive event_turn")
        return turn
    raise DataContractError(f"{record.get('record_id')}: unanalyzable terminal_cause {cause!r}")


def _check_records(records: list[dict[str, Any]], *, horizon: int = 12) -> None:
    if not records:
        raise DataContractError("no records")
    ids: set[str] = set()
    blocks: dict[str, dict[str, str]] = {}
    tracks: set[str] = set()
    splits: set[str] = set()
    for record in records:
        record_id = record.get("record_id")
        if not isinstance(record_id, str) or not record_id:
            raise DataContractError("record_id is required and must be a non-empty string")
        if record_id in ids:
            raise DataContractError(f"duplicate record_id: {record_id}")
        ids.add(record_id)
        cause = record.get("terminal_cause")
        if cause not in ALL_TERMINAL:
            raise DataContractError(f"{record_id}: terminal_cause {cause!r} is not analyzable")
        arm = record.get("arm")
        if arm not in {"B0", "B1", "B2", "B3"}:
            raise DataContractError(f"{record_id}: invalid arm {arm!r}")
        block_id = record.get("block_id")
        if not isinstance(block_id, str) or not block_id:
            raise DataContractError(f"{record_id}: block_id is required")
        if arm in blocks.setdefault(block_id, {}):
            raise DataContractError(
                f"duplicate block+arm {block_id}/{arm}: {blocks[block_id][arm]} and {record_id}; refusing to overwrite"
            )
        blocks[block_id][arm] = record_id
        tracks.add(str(record.get("track")))
        splits.add(str(record.get("split")))
        turn = _event_time(record)
        if turn > horizon:
            raise DataContractError(f"{record_id}: event/censor turn {turn} exceeds declared horizon {horizon}")
        if cause == "TURN_CAP" and turn != horizon:
            raise DataContractError(f"{record_id}: TURN_CAP must be at the declared horizon {horizon}, got {turn}")
        turns = record.get("turns") or []
        if cause != "UNAVAILABLE" and isinstance(turns, list) and turn > len(turns):
            raise DataContractError(
                f"{record_id}: event/censor turn {turn} exceeds the {len(turns)} observed turn(s); "
                "event times are never invented"
            )
        if cause == "DETECTION":
            detection_turn = record.get("detection_turn")
            if not isinstance(detection_turn, int) or isinstance(detection_turn, bool) or detection_turn != turn:
                raise DataContractError(f"{record_id}: DETECTION detection_turn must equal the explicit event turn")
    if len(tracks) > 1:
        raise DataContractError(f"mixed tracks in one analysis: {sorted(tracks)}")
    if tracks != {"B"}:
        raise DataContractError(f"primary analysis accepts Track B only, got {sorted(tracks)}")
    if len(splits) > 1:
        raise DataContractError(f"mixed splits in one analysis: {sorted(splits)}")


def cause_specific_cif(
    records: list[dict[str, Any]],
    cause: str,
    horizon: int = 12,
) -> dict[str, Any]:
    """Aalen-Johansen cause-specific CIF at each turn for one cause.

    ``d_all`` counts detection plus competing *events* only. ``TURN_CAP``
    censoring is never an event; censored sessions leave the risk set after
    their censor time without incrementing the event probability.
    """
    _check_records(records, horizon=horizon)
    if cause not in ALL_TERMINAL:
        raise DataContractError(f"unknown cause {cause!r}")
    times = {record["record_id"]: _event_time(record) for record in records}
    n_total = len(records)
    cif: list[float] = []
    cumulative = 0.0
    survival = 1.0
    detail: list[dict[str, Any]] = []

    # Pre-interaction unavailability (time 0) is an explicit competing event,
    # not a missing value and not a turn-1 event.
    d0_cause = sum(
        1
        for record in records
        if times[record["record_id"]] == 0 and record["terminal_cause"] == cause
    )
    d0_all = sum(
        1
        for record in records
        if times[record["record_id"]] == 0 and record["terminal_cause"] in EVENT_CAUSES
    )
    if d0_all:
        cumulative += d0_cause / n_total
        survival *= 1.0 - d0_all / n_total

    for turn in range(1, horizon + 1):
        at_risk = [record for record in records if times[record["record_id"]] >= turn]
        n = len(at_risk)
        if n == 0:
            detail.append(
                {
                    "turn": turn,
                    "at_risk": 0,
                    "cause_events": 0,
                    "all_events": 0,
                    "censored": 0,
                    "cif": cumulative,
                }
            )
            cif.append(cumulative)
            continue
        d_cause = sum(
            1
            for record in at_risk
            if times[record["record_id"]] == turn and record["terminal_cause"] == cause
        )
        d_all = sum(
            1
            for record in at_risk
            if times[record["record_id"]] == turn and record["terminal_cause"] in EVENT_CAUSES
        )
        censored = sum(
            1
            for record in at_risk
            if times[record["record_id"]] == turn and record["terminal_cause"] in CENSOR_CAUSES
        )
        previous = survival
        cumulative += previous * d_cause / n
        survival = previous * (1.0 - d_all / n)
        cif.append(cumulative)
        detail.append(
            {
                "turn": turn,
                "at_risk": n,
                "cause_events": d_cause,
                "all_events": d_all,
                "censored": censored,
                "cif": cumulative,
                "survival_previous": previous,
            }
        )
    return {
        "cause": cause,
        "horizon": horizon,
        "cif": cif,
        "cif_at_horizon": cif[-1] if cif else 0.0,
        "cif_at_time_zero": d0_cause / n_total if n_total else 0.0,
        "detail": detail,
        "n_sessions": len(records),
    }


def _arm_cif(records: list[dict[str, Any]], arm: str, cause: str, horizon: int) -> dict[str, Any]:
    subset = [record for record in records if record.get("arm") == arm]
    if not subset:
        return {"status": "NOT_ESTABLISHED", "reason": f"no sessions allocated to {arm}"}
    result = cause_specific_cif(subset, cause, horizon)
    result["status"] = "ESTIMATED"
    result["arm"] = arm
    result["events"] = sum(
        1 for record in subset if record.get("terminal_cause") == cause and _event_time(record) <= horizon
    )
    result["competing_events"] = {
        competing: sum(
            1
            for record in subset
            if record.get("terminal_cause") == competing and _event_time(record) <= horizon
        )
        for competing in COMPETING_CAUSES
    }
    result["censored"] = sum(
        1 for record in subset if record.get("terminal_cause") in CENSOR_CAUSES and _event_time(record) <= horizon
    )
    return result


def _contrast_arms(label: str) -> tuple[str, str]:
    parts = label.split("_vs_")
    if len(parts) != 2:
        raise DataContractError(f"contrast label must be ARM_vs_ARM, got {label!r}")
    return parts[0], parts[1]


def _paired_blocks(
    records: list[dict[str, Any]], arm_a: str, arm_b: str
) -> tuple[dict[str, dict[str, dict[str, Any]]], list[str], list[str]]:
    blocks: dict[str, dict[str, dict[str, Any]]] = {}
    warnings: list[str] = []
    invalid: list[str] = []
    for record in records:
        arm = record.get("arm")
        if arm not in (arm_a, arm_b):
            continue
        block_id = str(record.get("block_id"))
        blocks.setdefault(block_id, {})
        if arm in blocks[block_id]:
            invalid.append(f"block {block_id} has duplicate {arm}; refusing to overwrite")
            continue
        blocks[block_id][str(arm)] = record
    complete = {block: rows for block, rows in blocks.items() if set(rows) == {arm_a, arm_b}}
    if len(complete) != len(blocks):
        missing = sorted(set(blocks) - set(complete))
        warnings.append(
            f"{len(missing)} block(s) are missing one arm for {arm_a} vs {arm_b}: {missing[:5]}; "
            "the primary paired contrast is NOT_ESTABLISHED (complete-case is a labelled sensitivity only)"
        )
        invalid.extend(f"incomplete block: {block}" for block in missing)
    return complete, warnings, invalid


def _difference(records: list[dict[str, Any]], arm_a: str, arm_b: str, cause: str, horizon: int) -> float | None:
    cif_a = _arm_cif(records, arm_a, cause, horizon)
    cif_b = _arm_cif(records, arm_b, cause, horizon)
    if cif_a.get("status") != "ESTIMATED" or cif_b.get("status") != "ESTIMATED":
        return None
    return float(cif_a["cif_at_horizon"]) - float(cif_b["cif_at_horizon"])


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        raise DataContractError("no bootstrap values")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * pct
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def bootstrap_contrast(
    records: list[dict[str, Any]],
    *,
    arm_a: str,
    arm_b: str,
    cause: str = PRIMARY_CAUSE,
    horizon: int = 12,
    iterations: int = 2000,
    seed: int = 20261023,
) -> dict[str, Any]:
    """Paired block bootstrap for a risk difference at the horizon."""
    if iterations < 100:
        raise DataContractError("bootstrap iterations must be >= 100")
    complete, warnings, invalid = _paired_blocks(records, arm_a, arm_b)
    block_ids = sorted(complete)
    if invalid:
        return {
            "status": "NOT_ESTABLISHED",
            "reason": "incomplete or duplicate matched blocks; primary contrast is not estimable",
            "invalid_blocks": invalid,
            "warnings": warnings,
        }
    if not block_ids:
        return {
            "status": "NOT_ESTABLISHED",
            "reason": "no complete matched blocks for this contrast",
            "warnings": warnings,
        }
    observed = _difference(
        [record for rows in complete.values() for record in rows.values()],
        arm_a,
        arm_b,
        cause,
        horizon,
    )
    if observed is None:
        return {"status": "NOT_ESTABLISHED", "reason": "one or both arms are unexposed", "warnings": warnings}
    if len(block_ids) < 2:
        warnings.append("fewer than two matched blocks; the bootstrap CI is degenerate and not informative")

    rng = random.Random(seed)
    values: list[float] = []
    for iteration in range(iterations):
        sample = [rng.choice(block_ids) for _ in block_ids]
        resampled = []
        for draw_index, block_id in enumerate(sample):
            for record in complete[block_id].values():
                resampled.append(
                    {
                        **record,
                        "record_id": f"{record.get('record_id')}::boot{iteration}.{draw_index}",
                        "block_id": f"{record.get('block_id')}::boot{iteration}.{draw_index}",
                    }
                )
        difference = _difference(resampled, arm_a, arm_b, cause, horizon)
        if difference is not None:
            values.append(difference)
    if not values:
        return {
            "status": "NOT_ESTABLISHED",
            "reason": "bootstrap produced no estimable resamples",
            "warnings": warnings,
        }
    return {
        "status": "ESTIMATED",
        "contrast": f"{arm_a}_vs_{arm_b}",
        "cause": cause,
        "horizon": horizon,
        "risk_difference": observed,
        "ci95": [_percentile(values, 0.025), _percentile(values, 0.975)],
        "bootstrap_iterations": iterations,
        "bootstrap_seed": seed,
        "matched_blocks": len(block_ids),
        "small_sample_warning": (
            "block bootstrap is unreliable with very few blocks and does not repair a small pilot; "
            "it quantifies within-sample uncertainty only"
        ),
        "warnings": warnings,
    }


def complete_case_sensitivity(
    records: list[dict[str, Any]],
    *,
    arm_a: str,
    arm_b: str,
    cause: str = PRIMARY_CAUSE,
    horizon: int = 12,
    iterations: int = 2000,
    seed: int = 20261023,
) -> dict[str, Any]:
    """Explicitly labelled, non-primary complete-case sensitivity analysis.

    The primary contrast never silently drops an incomplete block. This helper
    exists only so a prespecified sensitivity can be requested and reported with
    its own label and warning; callers must not present it as the primary result.
    """
    complete, warnings, invalid = _paired_blocks(records, arm_a, arm_b)
    duplicates = [item for item in invalid if "duplicate" in item]
    if duplicates:
        return {
            "status": "NOT_ESTABLISHED",
            "label": "SENSITIVITY_COMPLETE_CASE_NONPRIMARY",
            "reason": "duplicate block+arm makes even the sensitivity inestimable",
            "invalid_blocks": duplicates,
        }
    if not complete:
        return {
            "status": "NOT_ESTABLISHED",
            "label": "SENSITIVITY_COMPLETE_CASE_NONPRIMARY",
            "reason": "no complete matched blocks",
            "warnings": warnings,
        }
    rows = [record for block in complete.values() for record in block.values()]
    result = bootstrap_contrast(
        rows,
        arm_a=arm_a,
        arm_b=arm_b,
        cause=cause,
        horizon=horizon,
        iterations=iterations,
        seed=seed,
    )
    result["label"] = "SENSITIVITY_COMPLETE_CASE_NONPRIMARY"
    result["primary_status"] = "NOT_ESTABLISHED_IF_ANY_BLOCK_IS_INCOMPLETE"
    result["warnings"] = [*result.get("warnings", []), *warnings]
    result["interpretation_guard"] = (
        "Complete-case sensitivity only. It is not the prespecified primary contrast and cannot restore "
        "a missing or unexposed arm."
    )
    return result


def permutation_contrast(
    records: list[dict[str, Any]],
    *,
    arm_a: str,
    arm_b: str,
    cause: str = PRIMARY_CAUSE,
    horizon: int = 12,
    iterations: int = 2000,
    seed: int = 20261023,
) -> dict[str, Any]:
    """Within-block arm-label randomization for the paired risk difference."""
    if iterations < 100:
        raise DataContractError("permutation iterations must be >= 100")
    complete, warnings, invalid = _paired_blocks(records, arm_a, arm_b)
    if invalid:
        return {
            "status": "NOT_ESTABLISHED",
            "reason": "incomplete or duplicate matched blocks; permutation contrast is not estimable",
            "invalid_blocks": invalid,
            "warnings": warnings,
        }
    if not complete:
        return {"status": "NOT_ESTABLISHED", "reason": "no complete matched blocks", "warnings": warnings}
    all_rows = [record for rows in complete.values() for record in rows.values()]
    observed = _difference(all_rows, arm_a, arm_b, cause, horizon)
    if observed is None:
        return {"status": "NOT_ESTABLISHED", "reason": "one or both arms are unexposed", "warnings": warnings}
    rng = random.Random(seed)
    block_ids = sorted(complete)
    exceed = 0
    valid = 0
    for _ in range(iterations):
        randomized = []
        for block_id in block_ids:
            rows = complete[block_id]
            if rng.random() < 0.5:
                left, right = rows[arm_a], rows[arm_b]
                randomized.append({**left, "arm": arm_b})
                randomized.append({**right, "arm": arm_a})
            else:
                randomized.extend(rows.values())
        difference = _difference(randomized, arm_a, arm_b, cause, horizon)
        if difference is None:
            continue
        valid += 1
        if abs(difference) >= abs(observed) - 1e-12:
            exceed += 1
    if valid == 0:
        return {"status": "NOT_ESTABLISHED", "reason": "no valid permutations", "warnings": warnings}
    return {
        "status": "ESTIMATED",
        "contrast": f"{arm_a}_vs_{arm_b}",
        "risk_difference": observed,
        "p_value": (exceed + 1) / (valid + 1),
        "permutations": valid,
        "permutation_seed": seed,
        "warnings": warnings,
    }


def holm_adjust(pvalues: dict[str, float]) -> dict[str, Any]:
    """Holm step-down over the explicitly requested contrasts.

    If any requested contrast is unsupported, the family is reported INCOMPLETE
    and no adjusted p-value is fabricated for the remaining tests.
    """
    if not pvalues:
        raise DataContractError("Holm family is empty")
    for label, value in pvalues.items():
        if value is None or not (0.0 <= float(value) <= 1.0):
            raise DataContractError(f"invalid p-value for {label}: {value!r}")
    ordered = sorted(((float(value), label) for label, value in pvalues.items()), key=lambda item: (item[0], item[1]))
    m = len(ordered)
    adjusted: dict[str, float] = {}
    running = 0.0
    for rank, (value, label) in enumerate(ordered, start=1):
        candidate = min(1.0, (m - rank + 1) * value)
        running = max(running, candidate)
        adjusted[label] = running
    return {"status": "COMPLETE", "family_size": m, "adjusted": adjusted, "method": "holm"}


def _exposure_filter(records: list[dict[str, Any]], exposure: str) -> tuple[list[dict[str, Any]], list[str]]:
    if exposure not in {"ITT", "PER_PROTOCOL"}:
        raise DataContractError(f"unknown exposure mode {exposure!r}")
    warnings: list[str] = []
    if exposure == "ITT":
        return list(records), warnings
    kept = []
    for record in records:
        turns = record.get("turns") or []
        exposed = all(turn.get("arm_exposure") == "OBSERVED" for turn in turns) if turns else False
        if record.get("terminal_cause") == "TECHNICAL_FAILURE":
            warnings.append(f"{record.get('record_id')}: excluded from per-protocol (technical failure)")
            continue
        if not exposed:
            warnings.append(f"{record.get('record_id')}: excluded from per-protocol (arm not observed)")
            continue
        kept.append(record)
    return kept, warnings


@dataclass
class AnalysisPlan:
    horizon: int = 12
    primary_cause: str = PRIMARY_CAUSE
    contrasts: tuple[str, ...] = ("B2_vs_B1", "B3_vs_B1", "B3_vs_B2")
    h1_contrast: str | None = "B1_vs_B0"
    bootstrap_iterations: int = 2000
    permutation_iterations: int = 2000
    seed: int = 20261023
    alpha: float = 0.05
    acceptance_criteria: dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> AnalysisPlan:
        return cls(
            horizon=int(value.get("horizon_turns", 12)),
            primary_cause=str(value.get("primary_cause", PRIMARY_CAUSE)),
            contrasts=tuple(value.get("retrieval_contrasts", ("B2_vs_B1", "B3_vs_B1", "B3_vs_B2"))),
            h1_contrast=value.get("h1_contrast", "B1_vs_B0"),
            bootstrap_iterations=int(value.get("bootstrap_iterations", 2000)),
            permutation_iterations=int(value.get("permutation_iterations", 2000)),
            seed=int(value.get("seed", 20261023)),
            alpha=float(value.get("alpha", 0.05)),
            acceptance_criteria=value.get("acceptance_criteria"),
        )


def _family_operational(records: list[dict[str, Any]]) -> dict[str, Any]:
    latencies: list[float] = []
    unavailable_latency = 0
    attempted = 0
    served = 0
    failed = 0
    verified = 0
    fallback = 0
    mock = 0
    for record in records:
        for turn in record.get("turns") or []:
            attempted += 1
            status = turn.get("serve_status", "SERVED")
            if status != "SERVED":
                failed += 1
                continue
            served += 1
            fallback += int(turn.get("generation_kind") in {"TEMPLATE", "FALLBACK"})
            mock += int(turn.get("generation_kind") == "MOCK")
            verified += int(bool(turn.get("verification", {}).get("passed")))
            latency = turn.get("latency_ms") or {}
            if latency.get("availability") == "UNAVAILABLE":
                unavailable_latency += 1
            elif isinstance(latency.get("value"), (int, float)):
                latencies.append(float(latency["value"]))
    latencies.sort()

    def pct(p: float) -> float | None:
        if not latencies:
            return None
        position = (len(latencies) - 1) * p
        lower = math.floor(position)
        upper = math.ceil(position)
        if lower == upper:
            return latencies[lower]
        return latencies[lower] + (latencies[upper] - latencies[lower]) * (position - lower)

    return {
        "family": "operational",
        "attempted_turns": attempted,
        "served_turns": served,
        "failed_or_rejected_turns": failed,
        "verified_turns": verified,
        "fallback_turns": fallback,
        "mock_turns": mock,
        "latency_p50_ms": pct(0.5),
        "latency_p95_ms": pct(0.95),
        "latency_unavailable_turns": unavailable_latency,
        "note": "latency excludes attacker think time and is reported separately from detection",
    }


def _family_quality(records: list[dict[str, Any]]) -> dict[str, Any]:
    served = sum(
        1 for record in records for turn in record.get("turns") or [] if turn.get("serve_status") == "SERVED"
    )
    passed = sum(
        int(bool(turn.get("verification", {}).get("passed")))
        for record in records
        for turn in record.get("turns") or []
        if turn.get("serve_status") == "SERVED"
    )
    return {
        "family": "quality",
        "verification_pass_rate": (passed / served) if served else None,
        "served_turns": served,
        "note": "verification is a consistency/identity check, not a general semantic-grounding score",
    }


def _family_safety(records: list[dict[str, Any]]) -> dict[str, Any]:
    unverified = 0
    total = 0
    for record in records:
        for turn in record.get("turns") or []:
            if turn.get("serve_status") != "SERVED":
                continue
            total += 1
            if turn.get("verification", {}).get("passed") is not True:
                unverified += 1
    return {
        "family": "safety",
        "unverified_served_turns": unverified,
        "served_turns": total,
        "note": "no composite safety score is formed",
    }


def _family_engagement(records: list[dict[str, Any]]) -> dict[str, Any]:
    sessions = len(records)
    meaningful = sum(1 for record in records if (record.get("operational") or {}).get("meaningful_engagement") is True)
    noop = sum(int((record.get("operational") or {}).get("automated_noop_turns", 0)) for record in records)
    substantive = sum(int((record.get("operational") or {}).get("substantive_turns", 0)) for record in records)
    return {
        "family": "engagement",
        "sessions": sessions,
        "meaningful_sessions": meaningful,
        "meaningful_engagement_rate": (meaningful / sessions) if sessions else None,
        "substantive_turns": substantive,
        "automated_noop_turns": noop,
        "note": "process measure only; operational denominators are reported separately",
    }


def _competing_incidence(records: list[dict[str, Any]], horizon: int) -> dict[str, Any]:
    """Jointly report every terminal family; detection CIF alone is misleading."""
    rows: dict[str, Any] = {}
    for arm in sorted({str(record.get("arm")) for record in records}):
        subset = [record for record in records if record.get("arm") == arm]
        rows[arm] = {
            cause: cause_specific_cif(subset, cause, horizon)["cif_at_horizon"] for cause in ALL_TERMINAL
        }
    return rows


def _receipt_metrics(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Separate allocation, receipt (served) and conditional served metrics."""
    rows: dict[str, Any] = {}
    for arm in sorted({str(record.get("arm")) for record in records}):
        subset = [record for record in records if record.get("arm") == arm]
        served = [
            record
            for record in subset
            if any(turn.get("serve_status") == "SERVED" for turn in record.get("turns") or [])
        ]
        compliant = [
            record
            for record in served
            if all(turn.get("arm_exposure") == "OBSERVED" for turn in record.get("turns") or [])
        ]
        rows[arm] = {
            "allocated_sessions": len(subset),
            "served_sessions": len(served),
            "compliant_exposure_sessions": len(compliant),
            "admission_rate": (len(served) / len(subset)) if subset else None,
            "compliant_exposure_rate_among_served": (len(compliant) / len(served)) if served else None,
            "unavailable_sessions": sum(1 for record in subset if record.get("terminal_cause") == "UNAVAILABLE"),
            "technical_failure_sessions": sum(
                1 for record in subset if record.get("terminal_cause") == "TECHNICAL_FAILURE"
            ),
        }
    return {
        "by_arm": rows,
        "definitions": {
            "receipt": "allocated session that produced at least one served turn",
            "conditional": "served-session metrics are conditional on receipt and are reported separately",
            "itt": "all allocated sessions remain in the primary ITT analysis",
        },
    }


def _claims_support(
    records: list[dict[str, Any]],
    plan: AnalysisPlan,
    receipt: dict[str, Any],
) -> dict[str, Any]:
    """Refuse H1-H5 support claims without prespecified criteria and exposure."""
    arms = {str(record.get("arm")) for record in records}
    criteria = plan.acceptance_criteria
    exposure = receipt["by_arm"]

    def compliant(arm: str) -> bool:
        row = exposure.get(arm) or {}
        return bool(row.get("served_sessions")) and row.get("compliant_exposure_rate_among_served") == 1.0

    def decision(claim: str, required: tuple[str, ...], extra: str | None = None) -> dict[str, Any]:
        missing = [arm for arm in required if arm not in arms]
        if missing:
            return {
                "claim": claim,
                "status": "NOT_ESTABLISHED",
                "reason": f"arm(s) absent/unexposed: {missing}",
            }
        if criteria is None:
            return {
                "claim": claim,
                "status": "NOT_ESTABLISHED",
                "reason": (
                    "no prespecified availability/utility acceptance criteria; "
                    "arbitrary thresholds are forbidden"
                ),
            }
        noncompliant = [arm for arm in required if not compliant(arm)]
        if noncompliant:
            return {
                "claim": claim,
                "status": "NOT_ESTABLISHED",
                "reason": (
                    f"compliant model exposure not demonstrated for {noncompliant}; "
                    "missing/unexposed is not negative evidence"
                ),
            }
        if extra:
            return {"claim": claim, "status": "NOT_ESTABLISHED", "reason": extra}
        return {
            "claim": claim,
            "status": "CONDITIONAL_ON_FROZEN_CRITERIA",
            "reason": "criteria and exposure are present; a result still requires the actual analysis and its CI",
        }

    return {
        "H1_system_package_B1_vs_B0": decision(
            "H1",
            ("B0", "B1"),
            "B0 native Cowrie has no shared RAGIN verifier and its native user/OS/kernel/hostname/persona baseline "
            "is not established as matched to B1-B3; H1 is a system-package effect in unmatched environments and "
            "cannot be claimed as a pure generator effect",
        ),
        "H2_retrieval_B2_vs_B1": decision("H2", ("B1", "B2")),
        "H3_dense_vs_sparse_B3_vs_B2": decision("H3", ("B2", "B3")),
        "H4_decision_layers": {
            "claim": "H4",
            "status": "NOT_ESTABLISHED",
            "reason": "B4/B5 are NOT READY; no decision-layer experiment is authorized",
        },
        "H5_full_utility": decision(
            "H5",
            ("B0", "B1", "B2", "B3"),
            "full utility also requires a prespecified acceptance rule; no composite is defined",
        ),
        "criteria_status": "MISSING" if criteria is None else "PRESPECIFIED",
        "note": (
            "No support claim is made from CIF alone; technical/unavailable/abandonment CIF and "
            "exposure are always reported jointly."
        ),
    }


def analyze_primary(records: list[dict[str, Any]], plan: AnalysisPlan | None = None) -> dict[str, Any]:
    plan = plan or AnalysisPlan()
    _check_records(records)
    if plan.primary_cause != PRIMARY_CAUSE:
        raise DataContractError("the primary cause is frozen as DETECTION")
    if plan.horizon != 12:
        raise DataContractError("the primary horizon is frozen at 12 attacker turns")

    arms_present = sorted({str(record.get("arm")) for record in records})
    requested = list(plan.contrasts)
    if plan.h1_contrast:
        requested.append(plan.h1_contrast)

    itt_records, itt_warnings = _exposure_filter(records, "ITT")
    pp_records, pp_warnings = _exposure_filter(records, "PER_PROTOCOL")

    def _run(subset: list[dict[str, Any]], exposure: str) -> dict[str, Any]:
        arm_summaries = {
            arm: _arm_cif(subset, arm, PRIMARY_CAUSE, plan.horizon) for arm in sorted({r.get("arm") for r in subset})
        }
        contrast_rows: dict[str, Any] = {}
        raw_p: dict[str, float] = {}
        estimable_all = True
        for label in requested:
            arm_a, arm_b = _contrast_arms(label)
            if arm_a not in arms_present or arm_b not in arms_present:
                contrast_rows[label] = {
                    "status": "NOT_ESTABLISHED",
                    "reason": f"arm(s) absent or unexposed in this analysis: {arm_a}, {arm_b}",
                }
                estimable_all = False
                continue
            bootstrap = bootstrap_contrast(
                subset,
                arm_a=arm_a,
                arm_b=arm_b,
                cause=plan.primary_cause,
                horizon=plan.horizon,
                iterations=plan.bootstrap_iterations,
                seed=plan.seed,
            )
            if bootstrap.get("status") != "ESTIMATED":
                contrast_rows[label] = {
                    "status": "NOT_ESTABLISHED",
                    "reason": bootstrap.get("reason", "contrast not estimable"),
                    "warnings": bootstrap.get("warnings", []),
                }
                estimable_all = False
                continue
            permutation = permutation_contrast(
                subset,
                arm_a=arm_a,
                arm_b=arm_b,
                cause=plan.primary_cause,
                horizon=plan.horizon,
                iterations=plan.permutation_iterations,
                seed=plan.seed,
            )
            row = {
                "status": "ESTIMATED",
                "risk_difference": bootstrap["risk_difference"],
                "ci95": bootstrap["ci95"],
                "p_raw": permutation.get("p_value") if permutation.get("status") == "ESTIMATED" else None,
                "matched_blocks": bootstrap["matched_blocks"],
                "bootstrap": bootstrap,
                "permutation": permutation,
                "interpretation": (
                    "difference of cause-specific CIF at turn 12; not a hazard ratio and not zero when non-significant"
                ),
            }
            contrast_rows[label] = row
            if row["p_raw"] is not None:
                raw_p[label] = float(row["p_raw"])
            else:
                estimable_all = False
        if estimable_all and len(raw_p) == len(requested):
            holm = holm_adjust(raw_p)
            for label, value in holm["adjusted"].items():
                contrast_rows[label]["p_holm"] = value
            holm_status = "COMPLETE"
        else:
            holm_status = "INCOMPLETE"
            for row in contrast_rows.values():
                row.setdefault("p_holm", None)
        return {
            "exposure": exposure,
            "arms": {
                arm: {key: value for key, value in summary.items() if key != "detail"}
                for arm, summary in arm_summaries.items()
            },
            "contrasts": contrast_rows,
            "holm_family_status": holm_status,
            "holm_family_size": len(requested),
            "warnings": ([f"{exposure}: mixed or incomplete arms leave one or more effects NOT_ESTABLISHED"]
                         if not estimable_all else []),
        }

    itt = _run(itt_records, "ITT")
    per_protocol = _run(pp_records, "PER_PROTOCOL") if pp_records else {
        "exposure": "PER_PROTOCOL",
        "status": "NOT_ESTABLISHED",
        "reason": "no per-protocol sessions remain",
    }
    families = {
        "operational": _family_operational(records),
        "quality": _family_quality(records),
        "safety": _family_safety(records),
        "engagement": _family_engagement(records),
    }
    receipt = _receipt_metrics(records)
    competing = _competing_incidence(records, plan.horizon)
    claims = _claims_support(records, plan, receipt)
    return {
        "schema": "ragin.ablation.analysis.v1",
        "status": "ESTIMATED" if all(
            row.get("status") == "ESTIMATED" for row in itt["contrasts"].values()
        ) else "PARTIAL_OR_NOT_ESTABLISHED",
        "horizon": plan.horizon,
        "primary_cause": plan.primary_cause,
        "primary_estimand": "paired risk difference in cause-specific CIF at turn 12",
        "arms_present": arms_present,
        "requested_contrasts": requested,
        "itt": itt,
        "per_protocol": per_protocol,
        "joint_terminal_incidence_by_arm": competing,
        "receipt_and_exposure": receipt,
        "claims_support": claims,
        "families": families,
        "warnings": [*itt_warnings, *pp_warnings],
        "interpretation_guard": (
            "Detection CIF can fall because an arm fails or is abandoned more often. Read detection jointly with "
            "technical/unavailable/abandonment CIF and with receipt/admission and compliant-exposure rates. "
            "A missing or unexposed arm is NOT_ESTABLISHED, never negative evidence of a zero effect."
        ),
        "non_significance_is_not_zero": True,
        "no_primary_composite": True,
    }


def sanitize_for_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): sanitize_for_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [sanitize_for_json(item) for item in value]
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return value


def iter_json_values(value: Iterable[Any]) -> Iterable[Any]:
    for item in value:
        yield sanitize_for_json(item)
