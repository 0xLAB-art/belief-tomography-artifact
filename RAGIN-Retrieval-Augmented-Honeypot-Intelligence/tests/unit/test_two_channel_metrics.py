"""Tests for declared scoring channels (two-channel §VI metrics).

Pins the 2026-09-27 rubric-diff investigation's fix: served-text and
CTI-analysis channels are scored SEPARATELY (no silent max), the deception
suite has no analysis channel, and every external-baseline arm declares its
channels in its artifact.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.two_channel_metrics import _channel_scores  # noqa: E402


def _outcome(response_text: str, ttps: list[str], candidate_actors: list[str] | None = None):
    return SimpleNamespace(
        response_text=response_text,
        cti_analysis={
            "threat_summary": "T1489 service stop detected; actor APT41 known for T1110",
            "ttps_seen": ttps,
            "extracted_techniques": [],
            "candidate_actors": [{"name": n, "confidence": 0.9, "known_ttps": []} for n in (candidate_actors or [])],
        },
        ttps_extracted=ttps,
    )


class TestChannelSeparation:
    def test_technique_channels_scored_separately_no_max(self):
        """Served text mentions nothing; analysis channel carries the ID:
        the two channels must differ — silently max()ing them is the bug
        the rubric-diff investigation retracted."""
        qa = {"expected_technique": "T1489", "query": "What is service stop?"}
        out = _outcome("webapp@web-srv-01:~$ uname -a\nLinux web-srv-01", ["T1489"])
        ch = _channel_scores(out, qa, "cti_technique")
        assert ch["served_text"] == 0.0
        assert ch["cti_analysis"] >= 0.85  # ttp bonus channel
        assert ch["served_text"] != ch["cti_analysis"]

    def test_served_text_channel_ignores_analysis(self):
        """A technique-carrying SERVED text must score in served_text even
        when the analysis channel is empty (no Don summary, no extracted IDs)."""
        qa = {"expected_technique": "T1489", "query": "What is service stop?"}
        out = SimpleNamespace(
            response_text="service stop T1489 explained",
            cti_analysis={"threat_summary": "", "ttps_seen": [], "extracted_techniques": [], "candidate_actors": []},
            ttps_extracted=[],
        )
        ch = _channel_scores(out, qa, "cti_technique")
        assert ch["served_text"] >= 0.8
        assert ch["cti_analysis"] < 0.8

    def test_actor_channels_separate(self):
        qa = {"expected_actor": "APT41", "sector": "healthcare", "query": "Who is APT41?"}
        out = _outcome("no actor named here", [], candidate_actors=["APT41"])
        ch = _channel_scores(out, qa, "cti_actor")
        assert ch["served_text"] == 0.0
        assert ch["cti_analysis"] >= 0.85

    def test_deception_suite_has_no_analysis_channel(self):
        out = _outcome("uid=1001(webapp) gid=1001(webapp)", [])
        ch = _channel_scores(out, {"expected_traits": [], "query": "id"}, "deception")
        assert ch["cti_analysis"] is None
        assert ch["served_text"] >= 0.0


class TestArtifactDeclarations:
    def test_all_external_baseline_arms_declare_channels(self):
        src = (Path(__file__).resolve().parents[2] / "scripts" / "run_external_baseline.py").read_text()
        assert src.count("scoring_channels") >= 6, "every arm must declare its channels"
        assert "served_text" in src

    def test_two_channel_artifact_declares_channel_definitions(self):
        """The persisted full-run artifact must carry channel definitions."""
        p = Path(__file__).resolve().parents[2] / "results" / "two_channel_metrics.json"
        if not p.exists():
            return  # full run not present in this checkout
        d = json.loads(p.read_text())
        assert "channel_definitions" in d
        assert "served_text" in d["channel_definitions"]
        assert "cti_analysis" in d["channel_definitions"]
        for suite, s in d["by_suite"].items():
            if suite == "deception":
                assert s["cti_analysis_avg"] is None  # no analysis channel by design
