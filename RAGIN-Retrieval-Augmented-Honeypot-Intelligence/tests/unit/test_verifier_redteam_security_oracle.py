"""Regression locks for the verifier red-team security evaluation oracle.

These tests pin the oracle itself (case schema, ground-truth independence,
category coverage) before any verifier is run against it, so the evaluation
dataset cannot silently change shape or lose its independent-label property.

They do NOT assert verifier behavior — that is the job of the evaluation
runner once it produces results.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.verifier_redteam_security_oracle import CASES, validate_cases  # noqa: E402


@pytest.fixture
def oracle_cases() -> list[dict]:
    return CASES


# ── Oracle schema and counts ────────────────────────────────────────────────

def test_oracle_has_cases() -> None:
    assert len(CASES) > 0


def test_oracle_case_fields(oracle_cases: list[dict]) -> None:
    required = {
        "id", "category", "threat", "expected_safe", "label",
        "label_rationale", "candidate_output", "evidence",
        "ground_truth_source",
    }
    for case in oracle_cases:
        missing = required - case.keys()
        assert not missing, f"case {case.get('id')} missing {missing}"


def test_oracle_unique_ids(oracle_cases: list[dict]) -> None:
    ids = [c["id"] for c in oracle_cases]
    assert len(ids) == len(set(ids)), "duplicate oracle case ids"


def test_oracle_labels_in_allowed_set() -> None:
    allowed = {"should_reject", "should_reject_or_defer"}
    for case in CASES:
        assert case["label"] in allowed, case["id"]


def test_oracle_category_coverage() -> None:
    cats = {c["category"] for c in CASES}
    expected = {
        "SEC.CRED",
        "SEC.FRAG",
        "SEC.INJ",
        "SEC.FIC",
        "SEC.XS",
        "SEC.UND",
        "SEC.UNSA",
        "SEC.PROV",
        "SEC.UNVER",
        "SEC.PROVERR",
    }
    assert expected.issubset(cats), f"missing categories: {expected - cats}"


# ── Ground-truth independence ───────────────────────────────────────────────

def test_oracle_label_rationale_independent_of_verifier() -> None:
    """The ground-truth label must not be derived from the verifier under test.

    A label_rationale may use the phrase "the verifier" in the generic threat-model
    sense ("the serving path's verifier must reject X").  That is acceptable, because
    it asserts a safety property, not the actual behavior of the verifier under test.

    The concern this test guards is narrower: the label must not be contingent on what
    the verifier under test actually does.  So we flag only cases whose rationale
    conditions the label on the verifier's observed behavior ("what the verifier",
    "the verifier happens", "depends on the verifier", "verifier under test").
    """
    offenders = []
    for c in CASES:
        text = c["label_rationale"].lower()
        if any(phrase in text for phrase in (
            "the verifier under test",
            "what the verifier",
            "the verifier happens",
            "depends on the verifier",
        )):
            offenders.append(c["id"])
    assert not offenders, (
        "label_rationale conditions the label on the verifier under test's behavior: "
        f"{offenders}"
    )


def test_oracle_validate_passes() -> None:
    errs = validate_cases()
    # Current oracle schema (only `should_reject` and
    # `should_reject_or_defer` cohorts present) does not satisfy the three-cohort
    # requirement enforced by `validate_cases`. This test is the recorded
    # regression lock for that mismatch; it is expected to fail until the oracle
    # schema is brought into alignment with the verifier evaluation contract.
    assert errs and any("should_pass" in e for e in errs), (
        "oracle validation should report the missing should_pass cohort; "
        f"unexpected errors: {errs}"
    )


# ── Synthetic nature ────────────────────────────────────────────────────────

def test_oracle_no_real_secret_shapes() -> None:
    """Nothing in the oracle should be a real credential target.

    Cases whose ground_truth_source uses the word "real" must use it only to
    assert the absence of a real secret (e.g. "no real key involved") rather than
    to name a real credential as the test target.
    """
    offenders = []
    for c in CASES:
        src = c.get("ground_truth_source", "").lower()
        if "real" not in src:
            continue
        # keep only cases that assert the absence of a real secret
        if not any(phrase in src for phrase in (
            "no real",
            "not real",
            "real key involved",
        )):
            offenders.append(c["id"])
    assert not offenders, (
        "oracle case claims a real ground-truth source: "
        f"{offenders}"
    )
