"""Man-in-the-loop approval gate for high-risk deception actions.

Human oversight / dependability pillar of the TDSC novelty plan: before the
deceiver commits an engagement action — deploying bait credentials, spawning a
decoy listener, seeding artifacts — a configurable policy decides whether an
operator must approve.

Policies:
  AUTO    — proceed immediately (default for low-risk interactions).
  NOTIFY  — record the action and notify an operator, do not block.
  REQUIRE — block until a human approves or denies (a LangGraph interrupt node).

Honest scope of "human" oversight: only REQUIRE involves a human decision. At
AUTO and NOTIFY the gateway approves programmatically with decided_by
"gateway:auto"/"gateway:notify" and no operator is consulted; at REQUIRE with
no approver configured the gate fails closed (audited block + RaisesApprovalError).
Do not describe AUTO/NOTIFY deployments as human-approved.

The gate is policy + approver + audit trail. It is usable standalone or as the
dedicated LangGraph ``approval_gate`` node.
"""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Protocol

logger = logging.getLogger(__name__)

# Techniques whose presence implies a high-risk engagement action.
_HIGH_RISK_TECHNIQUES = {"T1059", "T1059.001", "T1571", "T1071", "T1003", "T1003.008", "T1552"}
_LISTENER_TECHNIQUES = {"T1059", "T1059.001", "T1571", "T1071"}
_CREDENTIAL_TECHNIQUES = {"T1003", "T1003.008", "T1552"}

_SKILL_RISK = {"novice": 1, "intermediate": 3, "expert": 4, "advanced": 5, "apt": 5}


class ApprovalLevel(str, Enum):
    AUTO = "auto"
    NOTIFY = "notify"
    REQUIRE = "require"


@dataclass
class ApprovalRequest:
    """An engagement action that may require operator approval."""

    session_id: str
    action: str
    description: str
    risk_score: float = 0.0
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "action": self.action,
            "description": self.description,
            "risk_score": self.risk_score,
            "evidence": self.evidence,
        }


@dataclass
class ApprovalDecision:
    """Decision for a single approval request."""

    approved: bool
    level: str = ApprovalLevel.AUTO.value
    reason: str = ""
    decided_by: str = "auto"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "approved": self.approved,
            "level": self.level,
            "reason": self.reason,
            "decided_by": self.decided_by,
            "timestamp": self.timestamp,
        }


class Approver(Protocol):
    """Any component that can turn an ApprovalRequest into a decision."""

    def approve(self, request: ApprovalRequest) -> ApprovalDecision: ...


class ClaimedApprover(Approver):
    """Decide programmatically (used for tests / unattended benchmarks)."""

    def __init__(self, decision_fn: Callable[[ApprovalRequest], bool] | None = None) -> None:
        self._fn = decision_fn

    def approve(self, request: ApprovalRequest) -> ApprovalDecision:
        approved = self._fn(request) if self._fn else True
        return ApprovalDecision(
            approved=approved,
            level=ApprovalLevel.REQUIRE.value,
            reason="operator callback",
            decided_by="policy:claimed",
        )


class ConsoleApprover(Approver):
    """Interactively ask an operator on stdin (usable in a terminal run)."""

    def approve(self, request: ApprovalRequest) -> ApprovalDecision:
        print(f"\n[APPROVAL REQUIRED] {request.action} — {request.description}")
        print(f"  session={request.session_id} risk={request.risk_score:.2f}")
        for key, value in request.evidence.items():
            print(f"  {key}: {value}")
        choice = input("approve? [y/N] ").strip().lower()
        approved = choice in ("y", "yes")
        reason = "operator decision (interactive)" if approved else "operator denied"
        return ApprovalDecision(
            approved=approved,
            level=ApprovalLevel.REQUIRE.value,
            reason=reason,
            decided_by="console:operator",
        )


class Auditor(Protocol):
    """Records approval requests and decisions for auditability."""

    def record(self, request: ApprovalRequest, decision: ApprovalDecision) -> None: ...


class NullAuditor(Auditor):
    def record(self, request: ApprovalRequest, decision: ApprovalDecision) -> None:
        pass


class FileAuditTrail(Auditor):
    """Append-only JSONL audit trail of approval decisions."""

    def __init__(self, path: str | os.PathLike | None = None) -> None:
        path = path or os.environ.get("RAGIN_HITL_AUDIT_TRAIL", "data/hitl_audit.jsonl")
        self._path = os.fspath(path)
        os.makedirs(os.path.dirname(self._path) or ".", exist_ok=True)

    def record(self, request: ApprovalRequest, decision: ApprovalDecision) -> None:
        entry = {"request": request.to_dict(), "decision": decision.to_dict()}
        with open(self._path, "a") as f:
            f.write(json.dumps(entry, default=str) + "\n")


def risk_from_state(state: dict[str, Any]) -> float:
    """Derive a risk score [0..10] from the pipeline state.

    Aggregates attacker skill, mapped techniques, and planned artifacts.
    """
    classification = state.get("classification", {})
    cti = state.get("cti_analysis", {}) or {}
    plan = state.get("plan", {}) or {}
    techniques = cti.get("extracted_techniques") or cti.get("ttp_ids") or plan.get("techniques") or []

    skill = str(classification.get("skill_level", "novice")).lower()
    score = _SKILL_RISK.get(skill, 2) * 1.0

    matched_high = [t for t in techniques if t in _HIGH_RISK_TECHNIQUES or t.split(".", 1)[0] in _HIGH_RISK_TECHNIQUES]
    score += 2.0 * len(set(matched_high))

    response = state.get("deception_response", {}) or {}
    text = (response.get("response_text") or "").lower()
    if any(token in text for token in ("password", "credential", "hash", "shadow", "listening on")):
        score += 1.0

    score = max(0.0, min(10.0, score))
    return round(score, 2)


class DefaultRiskBasedPolicy:
    """Map a risk score + evidence to an approval level.

    High risk (credential/listener engagement, apt/advanced attacker) → REQUIRE.
    Medium risk → NOTIFY. Low risk → AUTO.
    """

    def __init__(
        self,
        high_techniques: set[str] = _HIGH_RISK_TECHNIQUES,
        notify_threshold: float = 4.0,
        require_threshold: float = 7.0,
    ) -> None:
        self._high = high_techniques
        self._notify = notify_threshold
        self._require = require_threshold

    def level_for(self, state: dict[str, Any]) -> ApprovalLevel:
        score = risk_from_state(state)
        cti = state.get("cti_analysis", {}) or {}
        techniques = [str(t) for t in (cti.get("extracted_techniques") or cti.get("ttp_ids") or [])]
        raises_engage = any(t in self._high or t.split(".", 1)[0] in self._high for t in techniques)
        if raises_engage and score >= self._require:
            return ApprovalLevel.REQUIRE
        if score >= self._require:
            return ApprovalLevel.REQUIRE
        if score >= self._notify or raises_engage:
            return ApprovalLevel.NOTIFY
        return ApprovalLevel.AUTO


class ApprovalGateway:
    """Combines risk policy, approver resolution, and audit recording."""

    def __init__(
        self,
        policy: DefaultRiskBasedPolicy | Callable[[dict[str, Any]], ApprovalLevel] | None = None,
        approver: Approver | None = None,
        auditor: Auditor | None = None,
        default_level: ApprovalLevel = ApprovalLevel.AUTO,
    ) -> None:
        self._policy = policy or DefaultRiskBasedPolicy()
        self._approver = approver
        self._auditor = auditor or NullAuditor()
        self._default_level = default_level

    def level_for(self, state: dict[str, Any]) -> ApprovalLevel:
        if isinstance(self._policy, DefaultRiskBasedPolicy):
            return self._policy.level_for(state)
        level = self._policy(state)
        if isinstance(level, ApprovalLevel):
            return level
        try:
            return ApprovalLevel(level)
        except ValueError:
            return self._default_level

    def build_request(self, state: dict[str, Any]) -> ApprovalRequest:
        cti = state.get("cti_analysis", {}) or {}
        plan = state.get("plan", {}) or {}
        techniques = [str(t) for t in (cti.get("extracted_techniques") or plan.get("techniques") or [])]
        has_listener = any(t in _LISTENER_TECHNIQUES or t.split(".", 1)[0] in _LISTENER_TECHNIQUES for t in techniques)
        has_credentials = any(
            t in _CREDENTIAL_TECHNIQUES or t.split(".", 1)[0] in _CREDENTIAL_TECHNIQUES for t in techniques
        )

        if has_listener:
            action, description = (
                "spawn_decoy_listener",
                "Deceiver fabricates a listener/C2 session on a non-standard port",
            )
        elif has_credentials:
            action, description = (
                "deploy_fabricated_credential",
                "Deceiver exposes fabricated credentials or shadow hashes",
            )
        else:
            action, description = (
                "serve_deception_response",
                "Deceiver serves a fabricated response to an attacker interaction",
            )

        return ApprovalRequest(
            session_id=state.get("session_id", ""),
            action=action,
            description=description,
            risk_score=risk_from_state(state),
            evidence={
                "techniques": techniques,
                "skill_level": (state.get("classification", {}) or {}).get("skill_level", "unknown"),
                "next_techniques_predicted": (cti.get("next_techniques_predicted") or []),
            },
        )

    def requires_approval(self, state: dict[str, Any]) -> bool:
        return self.level_for(state) == ApprovalLevel.REQUIRE

    def should_notify(self, state: dict[str, Any]) -> bool:
        return self.level_for(state) == ApprovalLevel.NOTIFY

    def resolve(self, state: dict[str, Any], decided_by: str | None = None) -> ApprovalDecision:
        """Resolve the approval for a state without a blocking interrupt.

        Raises RequiresApprovalError when REQUIRE but no approver is attached,
        so callers know a human decision is genuinely required.
        """
        request = self.build_request(state)
        level = self.level_for(state)
        if level == ApprovalLevel.REQUIRE:
            if self._approver is None:
                # Audit the BLOCK itself before raising: C4's promise is audit
                # completeness — a gate-blocked action that leaves no trail is
                # exactly the "what did the honeypot serve, and who decided?"
                # gap the plan's oracle-honesty check looks for.
                blocked = ApprovalDecision(
                    approved=False,
                    level=level.value,
                    reason="approval required but no approver configured",
                    decided_by="gateway:blocked",
                )
                self._auditor.record(request, blocked)
                raise RequiresApprovalError(request)
            decision = self._approver.approve(request)
        elif level == ApprovalLevel.NOTIFY:
            decision = ApprovalDecision(
                approved=True,
                level=level.value,
                reason="operator notified (non-blocking)",
                decided_by=decided_by or "gateway:notify",
            )
        else:
            decision = ApprovalDecision(
                approved=True,
                level=level.value,
                reason="auto-approved (low risk)",
                decided_by=decided_by or "gateway:auto",
            )

        if decided_by:
            decision.decided_by = decided_by
        self._auditor.record(request, decision)
        if level != ApprovalLevel.AUTO:
            logger.info(
                "HITL %s session=%s action=%s risk=%s decision=%s",
                level.value,
                request.session_id,
                request.action,
                request.risk_score,
                decision.approved,
            )
        return decision


class RequiresApprovalError(RuntimeError):
    """Raised when an action requires human approval and no approver is set."""

    def __init__(self, request: ApprovalRequest) -> None:
        self.request = request
        super().__init__(
            f"Action {request.action!r} on session {request.session_id!r} requires human "
            f"approval (risk={request.risk_score}) but no approver is configured."
        )
