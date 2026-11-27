"""Tests for judge-panel corrections: bait-deployment floor and harness-artifact rules.

The 60-row persona stratum's deterministic realism judge penalized two things
it should not: (1) registered canary deployments on credential-hunt queries —
the system's correct deception behavior — and (2) it folded session-harness
echo bugs into the deception mean. These tests lock the corrected judge
behavior and the offline re-scorer's rules.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ragin.benchmark.core import _score_persona_realism as _core_score  # noqa: E402
from ragin.benchmark.harness_bridge import (  # noqa: E402
    _BAIT_FLOOR,
    _score_persona_realism,
)
from scripts.rescore_judge_panel import (  # noqa: E402
    _is_harness_artifact,
    bait_value_count,
    rescore_row,
)

Q_ENV_KEYS = "Show me all environment variables that contain API keys or tokens"
R_CANARY = (
    "webapp@web-srv-01:~$ env | grep -iE 'api|key|token|secret'\n"
    "APP_API_KEY=4c1f9d3b7a05e8f26b48d0c3a17e5f9d\n"
    "DEPLOY_TOKEN=inv_9d2c7a4e1f83b5a6d0c9e2f4b7a1d8c3"
)


class TestBaitDeploymentFloor:
    def test_canary_deployment_gets_bait_floor(self):
        """A canary-serving transcript on a credential-hunt query must score
        at the bait floor, not be dragged down by brevity penalties."""
        score = _score_persona_realism(R_CANARY, [], Q_ENV_KEYS)
        assert score >= _BAIT_FLOOR

    def test_floor_applies_over_penalties(self):
        """The floor must be applied after penalties: a concise canary
        deployment cannot be punished below 0.85 for its shortness."""
        short = "webapp@web-srv-01:~$ env | grep -i key\nAPP_API_KEY=4c1f9d"
        score = _score_persona_realism(short, [], Q_ENV_KEYS)
        assert score >= _BAIT_FLOOR

    def test_no_floor_without_credent_hunt_intent(self):
        """Key-shaped output on a non-credential query earns no floor."""
        resp = "webapp@web-srv-01:~$ uptime\nload average: 2.87, 1.94, 1.12"
        score = _score_persona_realism(resp, [], "What is the current load average?")
        assert score < _BAIT_FLOOR

    def test_no_floor_for_plain_denial(self):
        """A permission-denied transcript mentions shadow/password but serves
        no key-shaped assignments — no deployment, no floor."""
        score = _score_persona_realism(
            "cat: /etc/shadow: Permission denied",
            [],
            "Has the root password been changed? Check /etc/shadow",
        )
        assert score < _BAIT_FLOOR

    def test_harness_echo_still_zero(self):
        """The echo artifact must remain a hard zero — the floor must not
        rescue a failed harness turn even when the query mentions keys."""
        q = "Check for unauthorized SSH keys in authorized_keys files"
        resp = f"bash: {q}: command not found"
        assert _score_persona_realism(resp, [], q) == 0.0


class TestCoreJudgeParity:
    """The core.py persona judge (used by run_deception_benchmarks) must
    carry the same bait-deployment floor as the harness-bridge judge."""

    def test_core_judge_floors_bait_deployment(self):
        resp = (
            "webapp@web-srv-01:~$ env | grep -iE 'api|key|token|secret'\nAPP_API_KEY=4c1f9d3b7a05e8f26b48d0c3a17e5f9d"
        )
        assert _core_score(resp, []) >= _BAIT_FLOOR

    def test_core_judge_untouched_without_keys(self):
        assert _core_score("uptime: 14:32, load 2.87", []) < _BAIT_FLOOR


class TestHarnessArtifactReclassification:
    def test_echo_plus_not_found_is_harness_artifact(self):
        q = "Check for unauthorized SSH keys in authorized_keys files"
        resp = f"bash: {q}: command not found"
        assert _is_harness_artifact(q, resp) is True

    def test_real_command_output_is_not_artifact(self):
        resp = "webapp@web-srv-01:~$ df -h\nFilesystem  Size  Used Avail Use%"
        assert _is_harness_artifact("What disk space is available?", resp) is False

    def test_command_not_found_alone_is_not_artifact(self):
        """A genuine miss (sestatus not installed) is a deception row, not a
        harness bug — the echo is the discriminating signal."""
        assert (
            _is_harness_artifact(
                "What is the current SELinux context?",
                "webapp@web-srv-01:~$ sestatus\nCommand 'sestatus' not found",
            )
            is False
        )


class TestRescorerRules:
    def test_bait_value_count(self):
        assert bait_value_count(R_CANARY) == 2

    def test_rescore_bait_credit(self):
        corrected, reason, n = rescore_row(0.25, Q_ENV_KEYS, R_CANARY)
        assert reason == "bait_deployment_credit"
        assert corrected >= _BAIT_FLOOR
        assert n == 2

    def test_rescore_reclassification(self):
        q = "Check for unauthorized SSH keys in authorized_keys files"
        corrected, reason, n = rescore_row(0.0, q, f"bash: {q}: command not found")
        assert reason == "reclassified_harness_artifact"
        assert corrected == 0.0
        assert n == 0

    def test_rescore_untouched_row(self):
        corrected, reason, n = rescore_row(
            0.55,
            "What is the current SELinux context?",
            "webapp@web-srv-01:~$ ps -eZ | grep nginx",
        )
        assert reason is None
        assert corrected == 0.55
        assert n == 0

    def test_rescore_rounds_floats(self):
        corrected, reason, _ = rescore_row(0.44999999999999996, "any query", "output")
        assert corrected == 0.45
        assert reason is None


class TestPersistedArtifacts:
    """The committed re-scoring output must stay consistent with its inputs."""

    @pytest.fixture
    def corrected(self):
        import json

        path = ROOT / "results" / "live_benchmark_judge_panel_corrected.json"
        if not path.exists():
            pytest.skip("corrected panel artifact not generated")
        return json.loads(path.read_text())

    def test_correction_counts_match_runs(self, corrected):
        for run in corrected["runs"]:
            assert run["bait_credit_rows"] <= run["n_rows"]
            assert run["reclassified_harness"] <= run["n_rows"]
            if run["bait_credit_rows"] == 0:
                assert run["canary_bias_magnitude"] == 0.0

    def test_bias_is_quantified(self, corrected):
        """The canary-bias magnitude must be explicitly recorded — the paper
        cites this number as the judge-bias measurement."""
        assert "total_canary_bias_magnitude" in corrected
        assert corrected["total_canary_bias_magnitude"] >= 0.0
