"""Tests for the timing-fingerprint experiment plumbing (deterministic parts).

The full experiment (scripts/timing_fingerprint_rocauc.py) mixes live
measurements; these tests pin the pure functions: cowrie gap parsing,
window feature construction, direction-corrected AUC logic, and the
gate semantics (detectability = max(AUC, 1-AUC) vs the real-vs-real floor).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.timing_fingerprint_rocauc import (  # noqa: E402
    MAX_GAP_MS,
    build_arms,
    build_windows,
    parse_cowrie_gaps,
)


class TestBuildWindows:
    def test_non_overlapping_windows_and_features(self):
        observed = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
        feats, labels = build_windows(observed, k=5)
        assert feats.shape == (2, 4)
        assert labels.shape == (2,)
        # Window 1: [10..50] mean 30; window 2: [60..100] mean 80
        assert feats[0][0] == 30.0
        assert feats[1][0] == 80.0
        assert set(labels.tolist()) == {1}

    def test_short_series_yields_no_windows(self):
        feats, labels = build_windows([1.0, 2.0, 3.0], k=5)
        assert len(feats) == 0
        assert len(labels) == 0


class TestBuildArms:
    def test_default_mix_respects_provenance_share(self):
        rng = np.random.default_rng(7)
        llm = [3000.0 + 10.0 * i for i in range(50)]
        fast = [0.1, 0.2, 0.3]
        real = [1000.0, 5000.0, 30000.0]
        arms = build_arms(rng, llm, fast, real, n_rows=100, llm_share=0.88)
        default = arms["ragin_default"]
        assert len(default) == 100
        fast_rows = sum(1 for x in default if x < 10.0)
        assert 6 <= fast_rows <= 18  # ~12% share with sampling slack
        assert len(arms["fastpath_only"]) == 100
        assert len(arms["fastpath_padded"]) == 100

    def test_padded_arm_sits_inside_real_envelope(self):
        rng = np.random.default_rng(11)
        llm = [3000.0]
        fast = [0.1]
        real = [1000.0, 5000.0, 30000.0]
        arms = build_arms(rng, llm, fast, real, n_rows=50)
        padded = np.asarray(arms["fastpath_padded"])
        assert padded.min() >= 1000.0  # never below the real envelope floor
        assert set(np.round(padded, 6)).issubset({1000.0, 5000.0, 30000.0})


class TestDirectionalAuc:
    def test_too_fast_means_detectable_not_hidden(self):
        """fastpath_only single-gap AUC ~ 0.0 (always below real gaps): the
        DIRECTIONAL value must read ~1.0 — 'too fast' is a fingerprint."""
        from scripts.timing_fingerprint_rocauc import SEED, arm_auc

        rng = np.random.default_rng(SEED)
        real = [500.0 + 100.0 * i for i in range(60)]
        fast = [0.05 + 0.01 * (i % 5) for i in range(200)]
        m = arm_auc(fast, real, rng, k=5, n_boot=50)
        assert m["auc_single_gap"] < 0.1
        assert m["auc_single_gap_directional"] > 0.9

    def test_padded_at_envelope_is_not_detectable(self):
        from scripts.timing_fingerprint_rocauc import SEED, arm_auc

        rng = np.random.default_rng(SEED)
        real = list(rng.choice([800.0, 2500.0, 9000.0, 45000.0], size=60))
        padded = list(rng.choice([800.0, 2500.0, 9000.0, 45000.0], size=200))
        m = arm_auc(padded, real, rng, k=5, n_boot=50)
        assert m["auc_single_gap_directional"] < 0.7


class TestCowrieGapParsing:
    def test_parses_gaps_from_synthetic_log(self, tmp_path):
        events = []
        base = 1_700_000_000.0
        for i, offset in enumerate([0.0, 2.5, 30.0]):  # gaps: 2500 ms, 27500 ms
            events.append(
                {
                    "eventid": "cowrie.command.input",
                    "session": "abc123",
                    "timestamp": __import__("datetime")
                    .datetime.fromtimestamp(
                        base + offset,
                        tz=__import__("datetime").timezone.utc,
                    )
                    .strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z",
                    "message": f"cmd {i}",
                }
            )
        p = tmp_path / "cowrie.json.test"
        p.write_text("\n".join(json.dumps(e) for e in events) + "\n")
        res = parse_cowrie_gaps(log_dir=tmp_path)
        assert res["sessions"] == 1
        assert res["commands"] == 3
        assert len(res["gaps_ms"]) == 2
        assert res["gaps_ms"][0] == 2500.0
        assert res["gaps_ms"][1] == 27500.0
        assert res["dropped_idle_gaps"] == 0

    def test_idle_gaps_dropped(self, tmp_path):
        import datetime as dt

        def ts(t):
            return dt.datetime.fromtimestamp(
                1_700_000_000.0 + t,
                tz=dt.timezone.utc,
            ).strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"

        events = [
            {"eventid": "cowrie.command.input", "session": "s1", "timestamp": ts(0.0), "message": "a"},
            {
                "eventid": "cowrie.command.input",
                "session": "s1",
                "timestamp": ts(MAX_GAP_MS / 1000.0 + 60.0),
                "message": "b",
            },  # idle outlier
            {
                "eventid": "cowrie.command.input",
                "session": "s1",
                "timestamp": ts(MAX_GAP_MS / 1000.0 + 62.0),
                "message": "c",
            },
        ]
        (tmp_path / "cowrie.json.idle").write_text("\n".join(json.dumps(e) for e in events) + "\n")
        res = parse_cowrie_gaps(log_dir=tmp_path)
        assert res["dropped_idle_gaps"] == 1
        assert len(res["gaps_ms"]) == 1  # only the 2000 ms gap survives


class TestRealClassSanity:
    def test_repo_cowrie_logs_yield_gaps(self):
        """The experiment's real class must be non-empty (regression guard:
        empty cowrie.json silently zeroed the class once)."""
        res = parse_cowrie_gaps()
        assert res["sessions"] >= 1
        assert len(res["gaps_ms"]) >= 10
        assert all(0 < g <= MAX_GAP_MS for g in res["gaps_ms"])
