"""Known-answer and contract tests for the prespecified ablation analysis.

The interpreter must be started with unique RAGIN_SESSION_DIR and
RAGIN_HOST_FICTION_PATH values; these assignments are a defensive fallback and
never point at the repository's historical/default session directory.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

os.environ.setdefault("RAGIN_SESSION_DIR", tempfile.mkdtemp(prefix="ragin-ablation-analysis-session-"))
os.environ.setdefault(
    "RAGIN_HOST_FICTION_PATH",
    str(Path(tempfile.mkdtemp(prefix="ragin-ablation-analysis-fiction-")) / "host_fiction.json"),
)

from ragin.evaluation.analysis import (  # noqa: E402
    AnalysisPlan,
    DataContractError,
    analyze_primary,
    bootstrap_contrast,
    cause_specific_cif,
    complete_case_sensitivity,
)


def served_turn(index: int) -> dict:
    return {
        "turn": index,
        "serve_status": "SERVED",
        "served_text": "uid=1000(user)",
        "generation_kind": "NATIVE_SHELL",
        "verification": {"passed": True},
        "latency_ms": {"availability": "MEASURED", "value": 1.0},
        "arm_exposure": "OBSERVED",
    }


def session(
    record_id: str,
    *,
    arm: str = "B1",
    block_id: str = "block-1",
    cause: str = "DETECTION",
    event_turn: int = 1,
    observed_turns: int | None = None,
    split: str = "development",
    track: str = "B",
) -> dict:
    if cause == "TURN_CAP":
        observed_turns = 12
        event_turn = 12
    if observed_turns is None:
        observed_turns = max(event_turn, 1)
    return {
        "record_id": record_id,
        "track": track,
        "split": split,
        "arm": arm,
        "block_id": block_id,
        "terminal_cause": cause,
        "event_turn": event_turn,
        "detection_turn": event_turn if cause == "DETECTION" else None,
        "turns": [served_turn(index) for index in range(1, observed_turns + 1)],
    }


def test_aalen_johansen_known_answer_competing_risks() -> None:
    records = [
        session("S1", block_id="b1", cause="DETECTION", event_turn=2),
        session("S2", block_id="b2", cause="DETECTION", event_turn=2),
        session("S3", block_id="b3", cause="ABANDONMENT", event_turn=1),
        session("S4", block_id="b4", cause="TURN_CAP"),
    ]

    result = cause_specific_cif(records, "DETECTION", horizon=12)

    assert result["n_sessions"] == 4
    assert result["cif_at_horizon"] == pytest.approx(0.5)
    assert result["cif"][0] == pytest.approx(0.0)
    assert result["cif"][1] == pytest.approx(0.5)
    assert result["cif"][-1] == pytest.approx(0.5)

    # Turn 1: one competing event (abandonment) and no detection.
    first = result["detail"][0]
    assert first["at_risk"] == 4
    assert first["cause_events"] == 0
    assert first["all_events"] == 1
    assert first["censored"] == 0
    assert first["survival_previous"] == pytest.approx(1.0)

    # Turn 2: two detections among the three still at risk; survival 0.75 first.
    second = result["detail"][1]
    assert second["at_risk"] == 3
    assert second["cause_events"] == 2
    assert second["all_events"] == 2
    assert second["survival_previous"] == pytest.approx(0.75)
    assert second["cif"] == pytest.approx(0.5)

    # Turn 3 onwards only the turn-cap session remains at risk.
    third = result["detail"][2]
    assert third["at_risk"] == 1
    assert third["cif"] == pytest.approx(0.5)


def test_turn_cap_censoring_does_not_increment_detection() -> None:
    records = [session("CENSORED", cause="TURN_CAP")]

    result = cause_specific_cif(records, "DETECTION", horizon=12)

    assert result["cif_at_horizon"] == pytest.approx(0.0)
    assert all(row["cause_events"] == 0 for row in result["detail"])
    assert result["detail"][-1]["turn"] == 12
    assert result["detail"][-1]["censored"] == 1
    assert result["detail"][-1]["cif"] == pytest.approx(0.0)


def test_known_answer_detection_censor_vs_technical_failure_at_turn_one() -> None:
    """The old bug treated a censor as an event or dropped the turn-2 risk set.

    A detection at turn 1, a turn-cap censor at turn 1, and a detection at
    turn 2 leave the second session at risk and produce CIF=1.0. Replacing the
    censor with a technical-failure competing event removes it from the risk
    set and produces CIF=2/3.
    """
    censored = [
        session("D1", block_id="b1", cause="DETECTION", event_turn=1),
        session("C1", block_id="b2", cause="ADMIN_CENSORED", event_turn=1),
        session("D2", block_id="b3", cause="DETECTION", event_turn=2),
    ]
    result = cause_specific_cif(censored, "DETECTION", horizon=12)
    assert result["cif"][0] == pytest.approx(1 / 3)
    assert result["cif"][1] == pytest.approx(1.0)
    assert result["detail"][1]["at_risk"] == 1
    assert result["detail"][0]["censored"] == 1

    failed = [
        session("D1", block_id="b1", cause="DETECTION", event_turn=1),
        session("F1", block_id="b2", cause="TECHNICAL_FAILURE", event_turn=1),
        session("D2", block_id="b3", cause="DETECTION", event_turn=2),
    ]
    failed_result = cause_specific_cif(failed, "DETECTION", horizon=12)
    assert failed_result["cif"][0] == pytest.approx(1 / 3)
    assert failed_result["cif"][1] == pytest.approx(2 / 3)
    assert failed_result["detail"][1]["at_risk"] == 1


def test_competing_cause_incidence_is_reported_separately() -> None:
    records = [
        session("S1", block_id="b1", cause="DETECTION", event_turn=2),
        session("S2", block_id="b2", cause="DETECTION", event_turn=2),
        session("S3", block_id="b3", cause="ABANDONMENT", event_turn=1),
        session("S4", block_id="b4", cause="TURN_CAP"),
    ]

    detection = cause_specific_cif(records, "DETECTION", horizon=12)
    abandonment = cause_specific_cif(records, "ABANDONMENT", horizon=12)

    assert detection["cif_at_horizon"] == pytest.approx(0.5)
    assert abandonment["cif_at_horizon"] == pytest.approx(0.25)


def test_incomplete_block_makes_primary_contrast_not_established() -> None:
    records = [
        # Complete matched block.
        session("B1-1", arm="B1", block_id="block-complete", event_turn=2),
        session("B2-1", arm="B2", block_id="block-complete", event_turn=4),
        # Incomplete matched block: B2 is missing.
        session("B1-2", arm="B1", block_id="block-incomplete", event_turn=3),
    ]

    bootstrap = bootstrap_contrast(records, arm_a="B2", arm_b="B1", iterations=100)
    assert bootstrap["status"] == "NOT_ESTABLISHED"
    assert any("incomplete" in item for item in bootstrap["invalid_blocks"])
    assert "risk_difference" not in bootstrap

    plan = AnalysisPlan(
        contrasts=("B2_vs_B1",),
        h1_contrast=None,
        bootstrap_iterations=100,
        permutation_iterations=100,
    )
    analysis = analyze_primary(records, plan)

    assert analysis["status"] == "PARTIAL_OR_NOT_ESTABLISHED"
    assert analysis["itt"]["contrasts"]["B2_vs_B1"]["status"] == "NOT_ESTABLISHED"
    assert analysis["itt"]["holm_family_status"] == "INCOMPLETE"
    assert analysis["itt"]["contrasts"]["B2_vs_B1"]["p_holm"] is None


def test_duplicate_block_arm_makes_primary_contrast_not_established() -> None:
    records = [
        session("B1-1", arm="B1", block_id="block-dup", event_turn=2),
        session("B2-1", arm="B2", block_id="block-dup", event_turn=3),
        # A second B1 in the same block would overwrite the first if accepted.
        session("B1-2", arm="B1", block_id="block-dup", event_turn=4),
    ]

    result = bootstrap_contrast(records, arm_a="B2", arm_b="B1", iterations=100)

    assert result["status"] == "NOT_ESTABLISHED"
    assert any("duplicate" in item for item in result["invalid_blocks"])

    # The primary analysis refuses the duplicate outright instead of overwriting.
    with pytest.raises(DataContractError, match="duplicate block\\+arm"):
        analyze_primary(records, AnalysisPlan(contrasts=("B2_vs_B1",), h1_contrast=None))


def test_complete_case_sensitivity_is_labelled_non_primary() -> None:
    records = [
        session("B1-1", arm="B1", block_id="block-1", event_turn=2),
        session("B2-1", arm="B2", block_id="block-1", event_turn=4),
        session("B1-2", arm="B1", block_id="block-2", event_turn=3),
        session("B2-2", arm="B2", block_id="block-2", event_turn=6),
        # Incomplete block retained by the primary contrast, dropped only from
        # this explicitly labelled sensitivity analysis.
        session("B1-3", arm="B1", block_id="block-3", event_turn=5),
    ]

    result = complete_case_sensitivity(records, arm_a="B2", arm_b="B1", iterations=100)

    assert result["status"] == "ESTIMATED"
    assert result["label"] == "SENSITIVITY_COMPLETE_CASE_NONPRIMARY"
    assert result["primary_status"] == "NOT_ESTABLISHED_IF_ANY_BLOCK_IS_INCOMPLETE"
    assert "not the prespecified primary contrast" in result["interpretation_guard"]
    assert any("missing one arm" in warning for warning in result["warnings"])

    # The prespecified primary contrast remains refused for the same records.
    primary = bootstrap_contrast(records, arm_a="B2", arm_b="B1", iterations=100)
    assert primary["status"] == "NOT_ESTABLISHED"
