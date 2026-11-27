"""Tests for the MITRE next-TTP prediction graph (proactive deception)."""

from __future__ import annotations

from ragin.graph.mitre import (
    _TACTIC_CHAIN,
    attach_strategy_context,
    suggest_next_techniques,
    tactic_name,
)


class TestTactics:
    def test_full_kill_chain_ordered(self):
        assert list(_TACTIC_CHAIN) == [
            "TA0043",
            "TA0042",
            "TA0001",
            "TA0002",
            "TA0003",
            "TA0004",
            "TA0005",
            "TA0006",
            "TA0007",
            "TA0008",
            "TA0009",
            "TA0011",
            "TA0010",
            "TA0040",
        ]

    def test_tactic_labels_exist(self):
        assert tactic_name("TA0007")  # Discovery
        assert tactic_name("TA0008")  # Lateral Movement


class TestSuggestions:
    def test_discovery_steers_to_lateral_movement(self):
        suggestions = suggest_next_techniques(["T1033"])  # System Owner/User Discovery
        ids = [s["technique_id"] for s in suggestions]
        assert "T1021" in ids  # Remote Services, next tactic TA0008

    def test_suggestions_are_scored(self):
        suggestions = suggest_next_techniques(["T1033"])
        assert all(s["rationale"] for s in suggestions)
        # Suggestions arrive ranked by descending score (the old assertion
        # sorted first — it could only pass when every score was equal).
        scores = [s["score"] for s in suggestions]
        assert scores == sorted(scores, reverse=True)

    def test_explicit_edge_outranks_tactic_batch(self):
        # T1552 has an explicit edge to T1003 (operator chain) plus a generic
        # Discovery-batch; the curated edge must rank above the batch ties.
        suggestions = suggest_next_techniques(["T1552"])
        assert suggestions[0]["technique_id"] == "T1003"

    def test_explicit_edge_beats_tactic_transition(self):
        suggestions = suggest_next_techniques(["T1046"])  # has explicit edge -> T1021, T1571
        ids = [s["technique_id"] for s in suggestions]
        assert "T1021" in ids

    def test_subtechnique_input_keeps_subtactic(self):
        suggestions = suggest_next_techniques(["T1059.001"])
        assert all(s["technique_id"] for s in suggestions)

    def test_unknown_technique_degrades_with_fallback(self):
        suggestions = suggest_next_techniques(["T9999"])
        assert suggestions  # falls back to a generic discovery/lateral steer
        assert len(suggestions) <= 3


class TestStrategyContext:
    def test_attaches_strategy_block(self):
        cti = {"extracted_techniques": ["T1059.001", "T1571"], "threat_summary": "x"}
        out = attach_strategy_context(cti)
        strategy = out["deception_strategy"]
        assert set(strategy["techniques"]) == {"T1059.001", "T1571"}
        assert strategy["steer"]
        assert strategy["bait"]
        assert strategy["current_tactic"]
        assert out["next_techniques_predicted"]

    def test_empty_cti_get_defaults(self):
        out = attach_strategy_context({})
        assert out["deception_strategy"]["steer"]
        assert out["next_techniques_predicted"] == []

    def test_observed_techniques_populate_fiction_hint(self):
        cti = {"extracted_techniques": ["T1003", "T1003.008"]}
        out = attach_strategy_context(cti)
        bait = " ".join(out["deception_strategy"]["bait"])
        assert "etc/shadow" in bait or "shadow" in bait or "credential" in bait.lower()
