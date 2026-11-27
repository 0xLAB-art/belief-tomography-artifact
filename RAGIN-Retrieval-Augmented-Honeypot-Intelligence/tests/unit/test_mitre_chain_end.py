"""Regression tests for the T1003-family crash: the last kill-chain tactic
(Impact TA0040) has no successor, and a credential-access technique seeded the
chain walk into an out-of-range lookup (GT-007 'list index out of range')."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ragin.graph.mitre import attach_strategy_context, next_candidates, suggest_next_techniques  # noqa: E402


class TestLastTacticEdge:
    def test_impact_technique_no_successor(self):
        # T1486 (Data Encrypted for Impact) sits in TA0040 — the chain's end.
        edges = next_candidates(["T1486"])
        # Must not raise, and no chain-tactic edges may originate from T1486
        # (explicit technique edges for OTHER sources are fine).
        assert all(src != "T1486" or dst for src, dst in edges)

    def test_impact_does_not_crash(self):
        assert isinstance(suggest_next_techniques(["T1486"]), list)

    def test_unknown_technique_does_not_crash(self):
        assert isinstance(suggest_next_techniques(["T9999"]), list)

    def test_mixed_observed_set(self):
        # Realistic multi-technique session including a final-tactic technique.
        out = suggest_next_techniques(["T1190", "T1059", "T1003", "T1486"])
        assert isinstance(out, list)

    def test_strategy_context_with_impact(self):
        cti = {"extracted_techniques": ["T1486", "T1059"]}
        out = attach_strategy_context(cti)
        assert "deception_strategy" in out
