"""Tests for the v2 analysis (scripts/field_attack_stats_v2.py).

The survival machinery has to behave like Kaplan-Meier with censoring, the
log-rank test has to separate a real gap from noise, and the bait-capture rule
must count attacker behaviour (read, then reuse) rather than surface output.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.field_attack_stats_v2 import (  # noqa: E402
    km_curve,
    logrank,
    restricted_mean,
    session_metrics,
)


def _row(turns: int, cap: int, persona: str = "recon_operator") -> dict:
    return {"persona": persona, "cap": cap, "turns": turns, "censored": turns >= cap}


def test_km_curve_drops_only_on_events():
    rows = [_row(5, 10), _row(5, 10), _row(10, 10), _row(10, 10)]
    curve = km_curve(rows)
    after_first = next(c for c in curve if c["t"] == 5)
    assert after_first["survival"] == 0.5
    assert after_first["events"] == 2
    last = curve[-1]
    assert last["survival"] == 0.5  # censored sessions do not drop the curve


def test_logrank_separates_a_real_gap_and_ignores_noise():
    a = [_row(5, 30) for _ in range(10)] + [_row(30, 30) for _ in range(10)]
    c = [_row(30, 30) for _ in range(20)]
    assert logrank(a, c)["p"] < 0.01
    same = [_row(10, 30) for _ in range(10)] + [_row(20, 30) for _ in range(10)]
    other = [_row(10, 30) for _ in range(10)] + [_row(20, 30) for _ in range(10)]
    assert logrank(same, other)["p"] > 0.9


def test_restricted_mean_never_exceeds_the_horizon():
    curve = km_curve([_row(5, 10), _row(10, 10)])
    assert 0 < restricted_mean(curve, 10) <= 10


def _session(commands: list[str]) -> dict:
    log = [{"turn": i + 1, "cmd": c, "think_s": 1.0, "server_s": 0.5,
            "output_chars": 10} for i, c in enumerate(commands)]
    return {"persona": "credential_hunter", "run_id": 1, "cap": 30, "dwell_s": 60.0, "log": log}


def test_bait_capture_requires_read_then_reuse():
    captured = session_metrics(_session(["cat /home/dev/.dbpass", "ssh dev@10.0.0.5"]))
    assert captured["bait_read"] and captured["bait_capture"]
    read_only = session_metrics(_session(["cat .env", "ls -la"]))
    assert read_only["bait_read"] and not read_only["bait_capture"]
    untouched = session_metrics(_session(["whoami", "ls"]))
    assert not untouched["bait_read"] and not untouched["bait_capture"]


def test_cap_is_read_from_the_record_not_assumed():
    record = _session(["whoami"])
    record["cap"] = 12
    assert session_metrics(record)["censored"] is False
