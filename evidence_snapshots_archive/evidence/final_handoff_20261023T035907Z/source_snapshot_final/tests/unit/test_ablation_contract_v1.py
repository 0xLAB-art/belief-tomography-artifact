"""Small boundary tests for the verifier deadline/hook contract.

The interpreter must be started with unique RAGIN_SESSION_DIR and
RAGIN_HOST_FICTION_PATH values; these assignments are a defensive fallback and
never point at the repository's historical/default session directory.
"""

from __future__ import annotations

import copy
import math
import os
import tempfile
from pathlib import Path

os.environ.setdefault("RAGIN_SESSION_DIR", tempfile.mkdtemp(prefix="ragin-ablation-contract-session-"))
os.environ.setdefault(
    "RAGIN_HOST_FICTION_PATH",
    str(Path(tempfile.mkdtemp(prefix="ragin-ablation-contract-fiction-")) / "host_fiction.json"),
)

from ragin.evaluation.ablation_contract import _check_analysis, _check_verification  # noqa: E402


def contract(*, seconds: object = 1.0, hook_seconds: object = "1.0") -> dict:
    return {
        "verification": {
            "profile": "research_strict_v1",
            "integration_status": "AVAILABLE",
            "source_sha256": "5cff1d20b01eb76b89da1a7cb580defa1f8cb625832daf12da5fcc813ad53692",
            "hook_env_fields": {
                "RAGIN_VERIFIER_PROFILE": "research_strict_v1",
                "RAGIN_VERIFIER_DEADLINE_S": hook_seconds,
            },
            "deadline": {"enforcement": "WALL_CLOCK", "seconds": seconds},
        }
    }


def check(value: dict) -> tuple[list, dict]:
    blockers: list = []
    resolved: dict = {}
    _check_verification(value, blockers, resolved)
    return blockers, resolved


def test_valid_deadline_is_core_resolved_and_finite() -> None:
    blockers, resolved = check(contract())
    assert blockers == []
    assert resolved["verification"]["deadline"]["deadline_s"] == 1.0
    assert resolved["verification"]["deadline"]["deadline_enforced"] is True


def test_bool_nan_inf_zero_negative_and_over_60_are_rejected() -> None:
    for seconds in (True, float("nan"), float("inf"), float("-inf"), 0, -1, 61, 60.0001):
        blockers, _ = check(contract(seconds=seconds))
        assert any(blocker.code == "VERIFIER_DEADLINE_NOT_ENFORCED" for blocker in blockers), seconds


def test_hook_must_select_same_profile_and_deadline() -> None:
    blockers, _ = check(contract(hook_seconds="2.0"))
    assert any(blocker.code == "VERIFICATION_HOOK_MISMATCH" for blocker in blockers)

    wrong_profile = copy.deepcopy(contract())
    wrong_profile["verification"]["hook_env_fields"]["RAGIN_VERIFIER_PROFILE"] = "legacy"
    blockers, _ = check(wrong_profile)
    assert any(blocker.code == "VERIFICATION_HOOK_MISMATCH" for blocker in blockers)

    bool_hook = contract(hook_seconds=True)
    blockers, _ = check(bool_hook)
    assert any(blocker.code == "VERIFICATION_HOOK_MISMATCH" for blocker in blockers)


def test_deadline_resolution_is_not_a_float_coercion_shortcut() -> None:
    # A string policy seconds value is not accepted merely because float() can parse it.
    blockers, _ = check(contract(seconds="1.0"))
    assert any(blocker.code == "VERIFIER_DEADLINE_NOT_ENFORCED" for blocker in blockers)
    assert math.isfinite(1.0)


def check_analysis(value: dict) -> tuple[list, dict]:
    blockers: list = []
    resolved: dict = {}
    _check_analysis(value, blockers, resolved)
    return blockers, resolved


def test_higher_level_stats_absence_is_an_explicit_blocker() -> None:
    # The local package supports Aalen-Johansen + bootstrap only. It must not
    # silently imply that the preregistered Cox/family-level model exists.
    blockers, _ = check_analysis({"analysis": {"acceptance_criteria": None}})
    codes = {blocker.code for blocker in blockers}
    assert {"UNRESOLVED_ACCEPTANCE_CRITERIA", "HIGHER_LEVEL_STATS_NOT_IMPLEMENTED",
            "UNRESOLVED_HIERARCHICAL_CLUSTER_COUNT"} <= codes


def test_resolved_acceptance_and_higher_level_plan_clear_the_blockers() -> None:
    blockers, resolved = check_analysis(
        {
            "analysis": {
                "acceptance_criteria": {"availability": ">= 0.9", "utility": ">= 0.8"},
                "higher_level_model": {"status": "IMPLEMENTED", "adequate_family_count": 24},
            }
        }
    )
    assert blockers == []
    assert resolved["higher_level_model"]["adequate_family_count"] == 24

