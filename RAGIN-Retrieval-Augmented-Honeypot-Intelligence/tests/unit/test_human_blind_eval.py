"""Tests for the blind human-eval packet builder/scorer."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.human_blind_eval import normalize_transcript, score  # noqa: E402


def test_normalize_strips_identity_and_ips():
    text = "webapp@web-srv-01:~$ curl http://203.0.113.5/x\n2026-09-26T22:00:00+03:00 done"
    out, mapping = normalize_transcript(text, "k1")
    assert "web-srv-01" not in out and "webapp" not in out
    assert "203.0.113.5" not in out
    assert "10.0.0.1" in out and "<ts>" in out
    assert mapping  # something was mapped


def test_normalize_is_deterministic_per_key():
    a, _ = normalize_transcript("host web-srv-01", "same-key")
    b, _ = normalize_transcript("host web-srv-01", "same-key")
    c, _ = normalize_transcript("host web-srv-01", "other-key")
    assert a == b
    # Different keys may map to different canonical hosts — that's the point.


def test_score_math(tmp_path, monkeypatch):
    # Build packet + truth + answers by hand and check accuracy/FP-rate/kappa plumbing.
    packet = {
        "rater": "r1",
        "items": [
            {"position": 1, "id": "aaaa", "transcript": "x"},
            {"position": 2, "id": "bbbb", "transcript": "y"},
            {"position": 3, "id": "cccc", "transcript": "z"},
            {"position": 4, "id": "dddd", "transcript": "w"},
        ],
    }
    truth = {"aaaa": "ragin", "bbbb": "real_linux", "cccc": "cowrie", "dddd": "real_linux"}
    answers = {
        "rater": "r1",
        "verdicts": [
            {"id": "aaaa", "verdict": "honeypot", "confidence": 4},
            {"id": "bbbb", "verdict": "honeypot", "confidence": 4},  # FP: real->honeypot
            {"id": "cccc", "verdict": "real", "confidence": 2},
            {"id": "dddd", "verdict": "real", "confidence": 5},
        ],
    }
    p = tmp_path / "packet_r1.json"
    p.write_text(json.dumps(packet))
    tmp_path.joinpath("packet_r1_truth.json").write_text(json.dumps(truth))
    a = tmp_path / "answers_r1.json"
    a.write_text(json.dumps(answers))

    score(p, a)
    report = json.loads(a.with_name("answers_r1_scored.json").read_text())
    assert report["n"] == 4
    assert report["accuracy"] == 0.5
    assert report["false_honeypot_rate"] == 0.25
    assert len(report["confusions"]) == 4
