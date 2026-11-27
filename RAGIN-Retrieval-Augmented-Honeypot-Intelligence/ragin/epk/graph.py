"""EPK-FS: typed fact graph for the Epistemic Deception Kernel.

A fact is a grounded predicate `pred(args..., value)` with provenance. The
graph is the kernel's synthetic world; the ontology (`ragin/epk/rules.py`)
defines what an attacker may infer from it. Facts are immutable once
committed; corrections are new facts that supersede (never rewrite) history,
so the served-history closure remains auditable.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Iterable


# Predicate cardinality. FUNCTIONAL slots hold one value (pkg.version, …):
# two different values in one slot is an inferable contradiction (T2).
# SET_VALUED predicates allow many values per slot (a host legitimately holds
# several accounts; several CVEs apply). Every new predicate must declare its
# cardinality — this declaration is itself part of the audited ontology.
SET_VALUED_PREDS: set[str] = {
    "cred.valid",
    "host.holds_account",
    "host.vuln",
    "svc.listening",
    "svc.banner",
    "cve.affects",
    "file.exists",
}


@dataclass(frozen=True)
class Fact:
    """A grounded predicate: pred(args..., value). Frozen + hashable."""

    pred: str
    args: tuple[str, ...]
    value: str
    provenance: str  # seed | plan | observed | synthesized | drift
    ts: float = field(default_factory=time.time)

    @property
    def key(self) -> str:
        """Positional identity: same pred+args+value is the same fact."""
        return f"{self.pred}({','.join(self.args)})={self.value}"

    @property
    def slot(self) -> str:
        """Functional slot: same pred+args is the same world-slot (a fact in
        a different value conflicts with it under the closure)."""
        return f"{self.pred}({','.join(self.args)})"

    def to_dict(self) -> dict[str, Any]:
        return {
            "pred": self.pred,
            "args": list(self.args),
            "value": self.value,
            "provenance": self.provenance,
            "ts": self.ts,
        }


class FactGraph:
    """The synthetic world state. Transactional: stage() then commit() or
    rollback(), so EPK-SYNTH drafts never leak into the closure on rejection.

    Drift semantics (the self-repairing trapdoor, IND_DECEPTION_SPEC §4):
    a real host changes legitimately — patches land, versions move. A commit
    with provenance="drift" SUPERSEDES the active value of a functional slot
    instead of conflicting: the old value stays in history() (a real host's
    apt history shows old versions too), the closure sees only active facts,
    and the attacker experiences the change as ordinary operations."""

    def __init__(self) -> None:
        self._facts: dict[str, Fact] = {}  # active facts (key -> Fact)
        self._history: list[Fact] = []  # every committed fact, in order
        self._staged: dict[str, Fact] = {}

    # -- query surface ----------------------------------------------------
    def facts(self, pred: str | None = None) -> list[Fact]:
        if pred is None:
            return list(self._facts.values())
        return [f for f in self._facts.values() if f.pred == pred]

    def get(self, pred: str, args: Iterable[str]) -> Fact | None:
        slot = f"{pred}({','.join(args)})"
        return self._facts_by_slot().get(slot)

    def slot_conflict(self, fact: Fact) -> Fact | None:
        """The committed fact occupying the same slot with a different value."""
        existing = self._facts_by_slot().get(fact.slot)
        if existing is not None and existing.key != fact.key:
            return existing
        return None

    # -- transaction surface ------------------------------------------------
    def stage(self, fact: Fact) -> None:
        self._staged[fact.key] = fact

    def commit(self) -> list[Fact]:
        """Two-phase commit (call only after closure check passed). Returns
        the committed facts. A functional-slot conflict raises UNLESS the
        incoming fact is a drift event, which supersedes the active value."""
        committed = []
        for fact in self._staged.values():
            conflict = self.slot_conflict(fact)
            if conflict is not None:
                if fact.provenance == "drift" and conflict.provenance != "drift":
                    # supersede: retire the old active fact (already in history
                    # from its own commit) — no duplicate record
                    self._facts.pop(conflict.key, None)
                else:
                    self._staged.clear()
                    raise ValueError(
                        f"slot conflict: {fact.key} conflicts with {conflict.key} "
                        f"(use provenance='drift' for legitimate operational change)"
                    )
            self._facts[fact.key] = fact
            self._history.append(fact)
            committed.append(fact)
        self._staged.clear()
        return committed

    def history(self) -> list[Fact]:
        """Every fact ever committed, in order — the world's own apt-log."""
        return list(self._history)

    def rollback(self) -> None:
        self._staged.clear()

    def digest(self) -> str:
        """World-state digest for audit logs (sha256 over sorted fact keys)."""
        joined = "\n".join(sorted(self._facts))
        return hashlib.sha256(joined.encode()).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        return {
            "facts": [f.to_dict() for f in self._facts.values()],
            "history_len": len(self._history),
            "digest": self.digest(),
        }

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, indent=2)

    # -- internals ----------------------------------------------------------
    def _facts_by_slot(self) -> dict[str, Fact]:
        return {f.slot: f for f in self._facts.values()}
