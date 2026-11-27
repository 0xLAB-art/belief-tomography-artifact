"""EPK-EPI: runtime attacker-knowledge closure tracker.

K_t = CLOSURE_O(H_t): the set of facts an attacker can infer from everything
served so far, under the ontology O. Implemented as a semi-naive Datalog
fixpoint over ground facts; at fact-graph sizes this is milliseconds per turn
(PAL-fragment model checking is P-complete and the world is small).

This is the first published runtime tracker of an attacker's inferable
knowledge in a deception system (see docs/IND_DECEPTION_SPEC.md §3).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ragin.epk.graph import Fact, FactGraph
from ragin.epk.rules import STARTER_RULES, Rule


@dataclass
class ClosureResult:
    facts: dict[str, Fact] = field(default_factory=dict)  # key -> Fact
    derived: dict[str, str] = field(default_factory=dict)  # fact key -> rule name

    def __contains__(self, fact: Fact) -> bool:
        return fact.key in self.facts

    def __len__(self) -> int:
        return len(self.facts)

    def conflicts(self) -> list[tuple[Fact, Fact]]:
        """Pairs of closure facts sharing a FUNCTIONAL slot with different
        values (an inferable contradiction). Set-valued predicates cannot
        conflict — a host holding two accounts is ordinary, not a tell."""
        from ragin.epk.graph import SET_VALUED_PREDS

        by_slot: dict[str, Fact] = {}
        out: list[tuple[Fact, Fact]] = []
        for f in self.facts.values():
            if f.pred in SET_VALUED_PREDS:
                continue
            seen = by_slot.get(f.slot)
            if seen is not None:
                out.append((seen, f))
            else:
                by_slot[f.slot] = f
        return out


class EpistemicTracker:
    """Maintains K_t incrementally: base facts (world + announced) in, closure
    fixpoint out. `announced()` folds a served response's facts into H_t."""

    def __init__(self, world: FactGraph, rules: list[Rule] | None = None) -> None:
        self.world = world
        self.rules = rules if rules is not None else STARTER_RULES
        self._announced: dict[str, Fact] = {}  # served-history H_t
        self._base_keys: set[str] = set()

    # -- history -------------------------------------------------------------
    def announced(self, facts: list[Fact]) -> None:
        """Fold the facts a served response made public into H_t."""
        for f in facts:
            self._announced[f.key] = f

    def served_history(self) -> list[Fact]:
        return list(self._announced.values())

    def retract(self, facts: list[Fact]) -> None:
        """Remove candidate facts from H_t (firewall denial rollback)."""
        for f in facts:
            self._announced.pop(f.key, None)

    # -- closure ---------------------------------------------------------------
    def closure(self) -> ClosureResult:
        """Fixpoint over base = world facts + announced facts, with value
        unification across rule joins (Datalog semi-naive, tiny at world
        scale — PAL fragment is P-complete and the graph is small)."""
        result = ClosureResult()
        for f in list(self.world.facts()) + list(self._announced.values()):
            result.facts[f.key] = f

        frontier = list(result.facts.values())
        while frontier:
            new_frontier: list[Fact] = []
            for rule in self.rules:
                pools: list[list[Fact]] = [
                    [f for f in result.facts.values() if f.pred == p]
                    for p in rule.body_preds
                ]
                for combo in _join(pools, rule.joins):
                    for head in rule.derive(*combo):
                        if head.key not in result.facts:
                            result.facts[head.key] = head
                            result.derived[head.key] = rule.name
                            new_frontier.append(head)
            frontier = new_frontier
        return result


def _access(fact: Fact, access: str) -> str:
    if access == "value":
        return fact.value
    if access.startswith("arg"):
        return fact.args[int(access[3:])]
    raise ValueError(f"bad accessor: {access}")


def _join(pools: list[list[Fact]], joins):
    """Cartesian product across body pools filtered by equality joins
    (accessor equality between two body positions)."""
    import itertools

    for combo in itertools.product(*pools):
        ok = True
        for i, ai, j, aj in joins:
            if _access(combo[i], ai) != _access(combo[j], aj):
                ok = False
                break
        if ok:
            yield combo
