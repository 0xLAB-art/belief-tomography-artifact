"""Jev orchestration glue — plugs System One assessments into RAGIN's cycles.

Three additive integrations, none of which replaces existing logic:

1. ``JevReviewer`` — implements the ``Reviewer`` protocol from
   ``ragin.cycle.coordination`` so a Jev assessment can join the
   ``VotingSystem`` pool (a fast, free second opinion before a response
   ships).

2. ``JevRoutingSignal`` — a small dataclass carrying risk/attack signals
   that the :class:`~ragin.cycle.coordination.Supervisor` (or any routing
   function) can fold into its decision; ``risk_boost`` maps severity to
   the RiskLevel vocabulary already used by the orchestrator.

3. ``SupervisorJevMixin`` — optional mixin so a Supervisor subclass can
   enrich routing with a Jev assessment synchronously (best-effort; a Jev
   failure leaves the base decision unchanged).
"""

from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING, Any

from ragin.jev.assessment import JevAssessor
from ragin.jev.models import JevAssessment

logger = logging.getLogger(__name__)

# Severity score (0-3) to coordinator RiskLevel vocabulary.
_SEVERITY_TO_RISK = {0: "low", 1: "medium", 2: "high", 3: "critical"}


class JevRoutingSignal:
    """Jev-derived signals ready for Supervisor / routing functions."""

    def __init__(self, assessment: JevAssessment | None) -> None:
        self.assessment = assessment

    @property
    def available(self) -> bool:
        return self.assessment is not None

    @property
    def risk_level(self) -> str:
        """Map Jev severity to the orchestrator's low/medium/high/critical."""
        assessment = self.assessment
        if assessment is None:
            return ""
        severity = assessment.severity
        if severity is None or not math.isfinite(severity):
            # A non-finite severity must not reach int(round(...)) — that
            # raises ValueError outside any handler and takes the routing
            # decision down with it. Treat it as "no usable signal".
            return ""
        return _SEVERITY_TO_RISK.get(int(round(severity)), "medium")

    @property
    def is_attack(self) -> bool | None:
        assessment = self.assessment
        return assessment.is_attack if assessment is not None else None

    @property
    def attack_kind(self) -> str:
        assessment = self.assessment
        if assessment is None or not assessment.attack_kind:
            return ""
        return assessment.attack_kind.value

    def adjust_risk(self, current: str) -> str:
        """Compose a Jev risk posture with a base risk level.

        Returns the *higher* of the two, or the current level unchanged
        when Jev is unavailable. This makes the signal strictly additive.
        """
        jev_level = self.risk_level
        if not jev_level:
            return current
        order = ["low", "medium", "high", "critical"]
        try:
            current_idx = order.index(current)
            jev_idx = order.index(jev_level)
        except ValueError:
            return current if current else jev_level
        return jev_level if jev_idx > current_idx else current

    def to_dict(self) -> dict[str, Any]:
        assessment = self.assessment
        if assessment is None:
            return {"available": False}
        return {
            "available": True,
            "risk_level": self.risk_level,
            "is_attack": self.is_attack,
            "attack_kind": self.attack_kind,
            "severity": assessment.severity,
            "answers": assessment.to_dict()["answers"],
        }


class JevReviewer:
    """Reviewer-protocol adapter: a Jev assessment votes pass/fail on a response.

    Implements the ``review(response, context) -> dict`` contract used by
    :class:`~ragin.cycle.coordination.VotingSystem` and
    :class:`~ragin.cycle.coordination.EnhancedProducerReviewer`. The verdict
    is derived from the ``attack`` noul probability and the ``severity``
    score returned by Jev over the session state.

    Args:
        threshold: Jev ``attack`` probability at/above which the reviewer
            fails the response (default 0.7).
        severity_cap: maximum Jev severity allowed to pass (default 1 —
            "low concern"). Higher severity fails the response.
        assessor: inject an assessor (stubbed in tests); one is built lazily
            otherwise.
    """

    def __init__(
        self,
        threshold: float = 0.7,
        severity_cap: int = 1,
        assessor: JevAssessor | None = None,
    ) -> None:
        self._threshold = threshold
        self._severity_cap = severity_cap
        self._assessor = assessor

    def review(self, response: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        try:
            assessor = self._assessor or JevAssessor()
            assessment = assessor.assess_context(context)
        except Exception:
            logger.warning("JevReviewer could not assess context — passing by default")
            return {"passed": True, "confidence": 0.0, "issues": [], "suggestion": ""}

        if assessment is None:
            return {"passed": True, "confidence": 0.0, "issues": [], "suggestion": ""}

        signal = JevRoutingSignal(assessment)
        issues: list[str] = []
        passed = True

        attack_prob = assessment.noul_probability("attack")
        if attack_prob is not None and attack_prob >= self._threshold:
            passed = False
            issues.append(f"Jev flags attack probability {attack_prob:.2f} (>= {self._threshold})")

        severity = assessment.severity
        if severity is not None and severity > self._severity_cap:
            passed = False
            issues.append(
                f"Jev severity {severity:.2f} exceeds cap {self._severity_cap} (kind={signal.attack_kind or 'unknown'})"
            )

        confidence = max(attack_prob or 0.0, (severity or 0.0) / 3)
        return {
            "passed": passed,
            "confidence": round(min(confidence, 1.0), 4),
            "issues": issues,
            "suggestion": signal.attack_kind or "",
        }


class SupervisorJevMixin:
    """Best-effort Jev enrichment for a Supervisor subclass.

    Mix into a custom Supervisor and call ``route_with_jev`` to fold Jev
    signals into the decision's risk level.    Jev being unavailable leaves
    the base decision untouched — this is strictly additive.
    """

    if TYPE_CHECKING:
        # The Supervisor surface this mixin composes with. Declared only
        # for type checking: a real Protocol base would shadow the host
        # class's route() in the MRO with the stub body.
        def route(
            self,
            session_context: dict[str, Any],
            classification: dict[str, Any],
            session_id: str = "",
            current_persona: str = "",
        ) -> Any: ...

    def __init__(self, *args: Any, assessor: JevAssessor | None = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._jevi_assessor = assessor

    def _jev_signal(self, context: dict[str, Any]) -> JevRoutingSignal:
        try:
            assessor = self._jevi_assessor or JevAssessor()
            assessment = assessor.assess_context(context)
        except Exception:
            logger.warning("Jev mixin could not assess context — no signal")
            return JevRoutingSignal(None)
        return JevRoutingSignal(assessment)

    def route_with_jev(
        self,
        session_context: dict[str, Any],
        classification: dict[str, Any],
        session_id: str = "",
        current_persona: str = "",
    ):
        """Run ``route()`` then raise the risk level to the Jev posture."""
        decision = self.route(
            session_context=session_context,
            classification=classification,
            session_id=session_id,
            current_persona=current_persona,
        )
        signal = self._jev_signal(session_context)
        if signal.available:
            from ragin.cycle.coordination import RiskLevel

            adjusted = signal.adjust_risk(decision.risk_level.value)
            if adjusted != decision.risk_level.value:
                logger.info(
                    "Supervisor risk adjusted %s -> %s by Jev (%s)",
                    decision.risk_level.value,
                    adjusted,
                    signal.attack_kind or "no-kind",
                )
                decision.risk_level = RiskLevel(adjusted)
            decision.context_enrichments = [
                *decision.context_enrichments,
                f"Jev: {signal.to_dict()}",
            ]
        return decision
