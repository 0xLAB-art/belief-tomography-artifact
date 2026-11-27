"""EPK-SCHED: the epistemic firewall.

Every candidate response is scored by its inference profile BEFORE serving:
  Δ⁻(r): detection-enabling entailments — facts the response would put into
         H_t whose closure conflicts with K_{t-1} (the attacker could infer a
         contradiction), or facts leaking real-host observations into the
         synthetic world's served channel.
  Δ⁺(r): misleading entailments — new closure facts the response enables that
         advance the deception plan.

T1 enforcement point: a candidate may only carry world-internal provenance
(seed | plan | observed-fiction | synthesized | inferred | drift). Facts whose
provenance is "real-observed" (measured on the deployment host) are a T1
boundary violation — serving them lets the attacker reason about the real
machine. The formal containment K_t ⊆ CLOSURE_O(F ∪ F_synth) then holds by
construction, and T2 is enforced by the conflict simulation below. This
upgrades the existing lexical verifier: the old gate rejects a response that
*is* contradictory; the firewall rejects a response that *lets the attacker
infer* a contradiction or a world-boundary violation.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ragin.epk.closure import EpistemicTracker
from ragin.epk.graph import Fact, FactGraph

OUT_OF_WORLD_PROVENANCE = {"real-observed"}


@dataclass
class Profile:
    admitted: bool
    deny_reasons: list[str] = field(default_factory=list)
    misleading_new: list[str] = field(default_factory=list)  # fact keys (Δ⁺)
    detecting: list[str] = field(default_factory=list)  # fact keys (Δ⁻)

    def to_dict(self) -> dict:
        return {
            "admitted": self.admitted,
            "deny_reasons": self.deny_reasons,
            "misleading_new": self.misleading_new,
            "detecting": self.detecting,
        }


class EpistemicFirewall:
    def __init__(self, world: FactGraph, tracker: EpistemicTracker) -> None:
        self.world = world
        self.tracker = tracker

    def evaluate(self, candidate_facts: list[Fact]) -> Profile:
        """Score a candidate response's announced facts without committing."""
        before = self.tracker.closure()
        profile = Profile(admitted=True)

        # T1 check: provenance/namespace boundary — nothing measured on the
        # real deployment host may enter the served channel.
        in_world_hosts = {f.value for f in self.world.facts("host.name")}
        for f in candidate_facts:
            if f.provenance in OUT_OF_WORLD_PROVENANCE:
                profile.admitted = False
                profile.deny_reasons.append(
                    f"T1 boundary: {f.key} carries out-of-world provenance "
                    f"'{f.provenance}'"
                )
                profile.detecting.append(f.key)
            elif f.pred == "host.name" and in_world_hosts and f.value not in in_world_hosts:
                profile.admitted = False
                profile.deny_reasons.append(
                    f"T1 boundary: hostname '{f.value}' is outside the pinned "
                    f"fiction world {sorted(in_world_hosts)}"
                )
                profile.detecting.append(f.key)

        # T2 check: simulate the announcement — does the new closure contain
        # a functional-slot conflict (an inferable contradiction)?
        self.tracker.announced(candidate_facts)
        after = self.tracker.closure()
        for a, b in after.conflicts():
            profile.admitted = False
            profile.deny_reasons.append(
                f"T2 inferable contradiction: {a.key} vs {b.key}"
            )
            profile.detecting.extend([a.key, b.key])

        # Δ⁺: new facts the candidate enables beyond the pre-announcement closure
        prev_keys = set(before.facts)
        profile.misleading_new = [
            k for k in after.facts if k not in prev_keys
        ]

        if not profile.admitted:
            # roll the simulated announcement back (recompute H_t without it)
            self.tracker.retract(candidate_facts)
        return profile
