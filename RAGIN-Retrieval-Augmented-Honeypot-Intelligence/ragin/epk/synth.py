"""EPK-SYNTH: constrained self-extension of the synthetic world.

When an attacker's command falls outside the world's coverage, the generator
drafts an answer; this module turns that draft into COMMITTED world state —
but only if the closure survives. Two-phase: stage the draft's facts
(provenance=synthesized) → firewall.evaluate (T1/T2) → commit on admit,
rollback on deny. A denied draft is never served AND never becomes state:
the world only grows along paths that keep every inference inside it.

This is the kernel of the "generative OS": state extension that cannot
contradict itself, because extension IS a transaction over the closure.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ragin.epk.graph import Fact, FactGraph
from ragin.epk.integrate import EPKScreen
from ragin.epk.sched import Profile


@dataclass
class SynthesisResult:
    committed: bool
    facts: list[Fact] = field(default_factory=list)
    profile: Profile | None = None
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "committed": self.committed,
            "facts": [f.to_dict() for f in self.facts],
            "profile": self.profile.to_dict() if self.profile else None,
            "reason": self.reason,
        }


class WorldSynthesizer:
    """Extends the world from drafted responses under closure constraints."""

    def __init__(self, screen: EPKScreen) -> None:
        self.screen = screen
        self.world = screen.world

    def extend(self, response_text: str) -> SynthesisResult:
        """Extract typed facts from a drafted response and, if the firewall
        admits the resulting inference profile, commit them as world state.
        The draft itself is the caller's responsibility to serve — this
        module only governs whether the world absorbs it."""
        facts = self.screen.extract(response_text)
        if not facts:
            return SynthesisResult(committed=False, reason="nothing typeable to extend")
        for f in facts:
            self.world.stage(f)
        profile = self.screen.firewall.evaluate(facts)
        if not profile.admitted:
            self.world.rollback()
            return SynthesisResult(committed=False, facts=facts,
                                   profile=profile, reason="firewall denial")
        committed = self.world.commit()
        return SynthesisResult(committed=True, facts=committed, profile=profile)
