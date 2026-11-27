"""Tests for the pre-registered A/B statistics (scripts/field_arm_stats.py).

The analysis must keep attacker intent (commands) separate from surface
behaviour (what the fiction returns), apply Holm across exactly the
confirmatory family, and stay pinned to its artifact + pre-registration.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.field_arm_stats import (  # noqa: E402
    CONFIRMATORY,
    PREREG,
    DEFAULT_A,
    DEFAULT_C,
    DEFAULT_OUT,
    holm,
    session_metrics,
    strat_bootstrap_diff,
)


def _rec(persona: str, run_id: int, cmds: list[str], outputs: list[str] | None = None) -> dict:
    return {
        "persona": persona,
        "run_id": run_id,
        "turns": len(cmds),
        "dwell_s": 10.0 * max(len(cmds), 1),
        "log": [
            {"turn": i + 1, "cmd": c, "output_chars": 5, "latency_s": 1.0}
            for i, c in enumerate(cmds)
        ],
        "transcript": "\n".join(outputs or [f"$ {c}\nout" for c in cmds]),
    }


def test_bait_targeting_counts_commands_not_returned_content():
    # intent: the attacker asked for a planted credential path
    hit = _rec("credential_hunter", 1, ["cat /home/dev/.dbpass"])
    assert session_metrics(hit)["bait_targeting"] == 1
    # surface: the bait appears in the output, but the attacker never asked for it
    served = _rec("recon_operator", 1, ["ls -la"], ["$ ls\n-rw-r--r-- .env"])
    assert session_metrics(served)["bait_targeting"] == 0
    plain = _rec("novice_scriptkiddie", 1, ["whoami", "uname -a"])
    assert session_metrics(plain)["bait_targeting"] == 0


def test_bootstrap_is_deterministic_and_brackets_the_point_difference():
    strata_a = {"p1": np.array([10.0, 12.0, 14.0]), "p2": np.array([20.0, 21.0, 22.0])}
    strata_c = {"p1": np.array([8.0, 9.0, 11.0]), "p2": np.array([18.0, 19.0, 20.0])}
    first = strat_bootstrap_diff(strata_a, strata_c, np.random.default_rng(20261028), 500)
    second = strat_bootstrap_diff(strata_a, strata_c, np.random.default_rng(20261028), 500)
    assert first["ci95"] == second["ci95"]
    assert first["diff"] < 0  # C is faster in this fixture
    assert first["ci95"][0] <= first["diff"] <= first["ci95"][1]
    assert first["n_a"] == first["n_c"] == 6


def test_holm_matches_the_step_down_definition():
    adjusted = holm({"a": 0.01, "b": 0.04, "c": 0.03})
    # sorted: a(0.01) b*2=0.06, c(0.03)*2=0.06, step-down keeps monotone
    assert adjusted["a"] == 0.03
    assert adjusted["b"] == 0.06
    assert adjusted["c"] == 0.06


def test_confirmatory_family_is_exactly_three_endpoints():
    assert CONFIRMATORY == ("dwell_s", "first_turn_latency_s", "bait_targeting")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_artifact_is_pinned_to_its_preregistration_and_inputs():
    payload = json.loads(DEFAULT_OUT.read_text(encoding="utf-8"))
    assert payload["schema"] == "ragin.field_attack.arm_stats_bootstrap.v1"
    assert payload["preregistration"]["sha256"] == _sha(PREREG)
    assert payload["inputs"]["arm_a"]["sha256"] == _sha(DEFAULT_A)
    assert payload["inputs"]["arm_c"]["sha256"] == _sha(DEFAULT_C)
    assert payload["inputs"]["sessions"] == {"a": 15, "c": 15}
    assert payload["bootstrap"]["seed"] == 20261028
    assert payload["bootstrap"]["statistic"].startswith("difference of means")


def test_artifact_holm_and_decisions_are_consistent():
    payload = json.loads(DEFAULT_OUT.read_text(encoding="utf-8"))
    for name in CONFIRMATORY:
        endpoint = payload["endpoints"][name]
        assert endpoint["p_holm"] >= endpoint["p_raw"]
        assert endpoint["significant_holm"] is (endpoint["p_holm"] < 0.05)
    # the recorded finding: the mean dwell gap is carried by three long
    # sessions in the stock arm, the medians do not move
    dwell = payload["endpoints"]["dwell_s"]
    assert abs(dwell["median_diff"]) < 10.0
    assert payload["censoring"]["cap_turns"] == 14
    assert payload["censoring"]["censored_a"] == 9
    assert payload["censoring"]["censored_c"] == 8


def test_artifact_keeps_surface_counts_out_of_the_contrast():
    payload = json.loads(DEFAULT_OUT.read_text(encoding="utf-8"))
    surface = payload["descriptive"]["surface_dependent"]
    assert "NOT a controlled contrast" in surface["label"]
    assert set(surface["sensitive_read_hits"]) == {"A_cowrie_only", "C_ragin"}
    assert "bait_targeting" in payload["endpoints"]
