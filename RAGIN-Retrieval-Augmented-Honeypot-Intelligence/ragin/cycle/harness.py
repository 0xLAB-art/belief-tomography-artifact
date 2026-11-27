"""Harness — stateless orchestration loop for RAGIN.

Design principles from Anthropic Managed Agents + revfactory/harness:
- Harness = the loop (stateless, replaceable, crash-safe)
- All state lives in Session (append-only event log)
- Crashes don't lose data — wake(sessionId) resumes from log
- Pipeline pattern: Chrollo → Don → Hisoka (sequential dependent tasks)
- Producer-Reviewer: Hisoka generates → EvasionDetector verifies
- emitEvent() writes to session log for durable recording

The harness itself holds NO session state. It receives a Session object,
runs the pipeline, and emits events. If it crashes mid-pipeline, the next
harness instance picks up by replaying the session log.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Protocol

from ragin.capture_v4.privacy import bounded_redacted_text
from ragin.cycle.hitl import ApprovalGateway, RequiresApprovalError
from ragin.cycle.session import Event, EventType, Session
from ragin.cycle.strict_research import LEGACY_PROFILE_NAME, PROFILE_NAME, StrictResearchVerifier
from ragin.cycle.verification_deadline import DeadlineVerifier, VerificationPolicy, resolve_verification_policy
from ragin.hisoka.deception import _deep_shell_facts_for
from ragin.cycle.verifier import FictionConsistencyVerifier
from ragin.decision_fusion_v4.config import resolve_arm
from ragin.decision_fusion_v4.evidence_export import failure_evidence_bundle
from ragin.decision_fusion_v4.policy import build_selector
from ragin.graph.fiction import FictionGraph
from ragin.graph.host_fiction import HostFictionStore, HostFictionVerifier
from ragin.hisoka.deception import ResponseGenerator, identity_for


logger = logging.getLogger(__name__)


try:
    from ragin.cycle.coordination import (
        DeceptionReviewer,
        EnhancedProducerReviewer,
        ExpertPool,
        QualityReviewer,
        SecurityReviewer,
        Supervisor,
        VotingSystem,
    )

    HAS_COORDINATION = True
except ImportError:
    HAS_COORDINATION = False


class Classifier(Protocol):
    """Interface for the Chrollo classifier."""

    def classify(self, attacker_input: str, session_context: dict[str, Any]) -> dict[str, Any]:
        """Classify attacker skill level. Returns dict with 'skill_level', 'confidence'."""
        ...


class CTIEngine(Protocol):
    """Interface for the Don CTI engine."""

    def analyze(
        self,
        attacker_input: str,
        session_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Analyze threat intelligence. Returns dict with 'threat_summary', 'recommendations'."""
        ...


class Deceiver(Protocol):
    """Interface for the Hisoka deceiver."""

    def generate_response(
        self,
        attacker_input: str,
        session_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate deception response. Returns dict with 'response_text', 'persona_used', etc."""
        ...


class ResponseVerifier(Protocol):
    """Interface for response verification (Producer-Reviewer pattern)."""

    def verify(
        self,
        response: dict[str, Any],
        session_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Verify response quality. Returns dict with 'passed', 'issues', 'confidence'."""
        ...


@dataclass
class PipelineResult:
    """Result of a single harness pipeline execution."""

    session_id: str
    attacker_input: str
    classification: dict[str, Any] = field(default_factory=dict)
    cti_analysis: dict[str, Any] = field(default_factory=dict)
    deception_response: dict[str, Any] = field(default_factory=dict)
    verification: dict[str, Any] = field(default_factory=dict)
    approval: dict[str, Any] = field(default_factory=dict)
    plan: dict[str, Any] = field(default_factory=dict)
    total_time_ms: float = 0.0
    events_emitted: int = 0
    error: str | None = None

    @property
    def response_text(self) -> str:
        return self.deception_response.get("response_text", "")

    @property
    def passed_verification(self) -> bool:
        # Fail closed: only an explicit verifier "passed": true counts. An
        # empty/absent verdict means "not verified", never "assume passed".
        return self.verification.get("passed") is True


@dataclass
class _ProcessContext:
    """Mutable state bundled through pipeline stages.

    Reduces parameter threading across stage methods and
    keeps events_emitted in one place.
    """

    result: PipelineResult
    session: Session
    events_emitted: int = 0
    context: dict[str, Any] = field(default_factory=dict)

    def emit(self, event_type: EventType, data: dict, source: str) -> Event:
        event = self.session.emit(event_type, data, source=source)
        self.events_emitted += 1
        return event


class Harness:
    """Stateless orchestration loop for RAGIN.

    The harness holds NO session state. It receives a Session object,
    runs the pipeline, and emits events. If it crashes mid-pipeline,
    the next harness instance picks up by replaying the session log.

    Pipeline: Chrollo (classify) → Don (CTI) → Hisoka (deceive) → Verify

    Usage::

        harness = Harness(
            classifier=ChrolloClassifier(),
            cti_engine=ThreatRAGEngine(),
            deceiver=AdaptiveDeceiver(),
        )
        session = Session.create(source_ip="10.0.0.1")
        result = harness.process(session, "whoami")
        print(result.response_text)
    """

    def __init__(
        self,
        classifier: Classifier | None = None,
        cti_engine: CTIEngine | None = None,
        deceiver: Deceiver | None = None,
        verifier: Any = None,
        max_retries: int = 2,
        mandatory_verification: bool = False,
        host_store: HostFictionStore | None = None,
        host_fiction_path: str | None = None,
        approval_gateway: ApprovalGateway | None = None,
        decision_arm: str | None = None,
        verifier_profile: str | None = None,
        verifier_deadline_s: float | None = None,
    ) -> None:
        self._classifier = classifier
        self._cti_engine = cti_engine
        self._deceiver = deceiver
        self._verifier = verifier
        self._max_retries = max_retries
        self._mandatory_verification = mandatory_verification
        # Verification policy is resolved once, independent of the decision
        # arm, and applied identically to every arm. Invalid env values raise
        # instead of silently selecting a weaker contract.
        self._verification_policy: VerificationPolicy = resolve_verification_policy(
            profile=verifier_profile,
            deadline_s=verifier_deadline_s,
        )
        self._fiction_graphs: dict[str, FictionGraph] = {}
        self._host_fiction_path = host_fiction_path
        self._host_store = host_store
        self._approval_gateway = approval_gateway or ApprovalGateway()
        self._decision_arm = resolve_arm(decision_arm)
        self._policy_selector = build_selector(self._decision_arm)
        if mandatory_verification:
            if self._host_store is None:
                self._host_store = HostFictionStore(
                    host_key=os.environ.get("RAGIN_HOST_KEY", "default-host"),
                    policy=os.environ.get("RAGIN_HOST_FICTION_POLICY", "per_session"),
                )
            if self._verifier is None:
                inner = FictionConsistencyVerifier(
                    fictions=self._fiction_graphs,
                    profile=self._verification_policy.profile,
                )
                self._verifier = HostFictionVerifier(inner, self._host_store)
        if self._verifier is not None:
            self._verifier = self._apply_verification_policy(self._verifier)

    def _apply_verification_policy(self, verifier: Any) -> Any:
        """Add the shared strict profile and the wall-clock deadline.

        ``legacy`` leaves the inner verifier untouched apart from the deadline
        wrapper. ``research_strict_v1`` additionally wraps verifiers that do
        not already expose the profile. The wrapper order means the deadline
        bounds both the legacy and strict checks.
        """
        profile = self._verification_policy.profile
        wrapped = verifier
        if profile == PROFILE_NAME and getattr(wrapped, "profile", LEGACY_PROFILE_NAME) != PROFILE_NAME:
            wrapped = StrictResearchVerifier(wrapped)
        return DeadlineVerifier(wrapped, self._verification_policy.deadline_s)

    @property
    def verification_policy(self) -> VerificationPolicy:
        """Resolved profile/deadline applied to this harness."""
        return self._verification_policy

    @property
    def mandatory_verification(self) -> bool:
        return self._mandatory_verification

    @property
    def decision_arm(self) -> str:
        """Resolved decision arm, for per-interaction trace attribution."""
        return str(self._decision_arm)

    def fiction(self, session_id: str, skill_level: str = "novice") -> FictionGraph:
        existing = self._fiction_graphs.get(session_id)
        if existing is not None:
            return existing
        identity = identity_for(skill_level)
        if self._host_store is not None:
            identity = self._host_store.pinned_identity or identity
            graph = self._host_store.session_graph(session_id, identity=identity)
        else:
            graph = FictionGraph(session_id=session_id, identity=identity)
        self._fiction_graphs[session_id] = graph
        return graph

    def _strict_verification_context(self, ctx: _ProcessContext) -> dict[str, Any]:
        session_graph = self._fiction_graphs.get(ctx.result.session_id)
        pinned: dict[str, Any] | None = None
        if self._host_store is not None and self._host_store.pinned_identity:
            pinned = self._host_store.pinned_identity
        elif session_graph is not None:
            graph_identity = getattr(session_graph, "identity", None)
            if isinstance(graph_identity, dict):
                pinned = dict(graph_identity)
        return {
            **ctx.context,
            "session_id": ctx.result.session_id,
            "attacker_input": ctx.result.attacker_input,
            "classification": ctx.result.classification,
            "cti_analysis": ctx.result.cti_analysis,
            "deception_response": ctx.result.deception_response,
            # The strict profile judges claims against the SAME pinned host
            # identity generation used, not a re-derived classification.
            "pinned_identity": pinned,
        }

    @staticmethod
    def _candidate_digest(candidate: dict[str, Any]) -> str:
        return hashlib.sha256(str(candidate.get("response_text", "")).encode()).hexdigest()

    @staticmethod
    def _graph_digest(graph: FictionGraph) -> str:
        """Canonical digest of the session fiction-graph state (facts + contradictions)."""
        return hashlib.sha256(json.dumps(graph.summary(), sort_keys=True, default=str).encode()).hexdigest()

    @staticmethod
    def _serving_attempt(candidate: dict[str, Any], attempt: int) -> dict[str, Any]:
        raw_metadata = candidate.get("metadata")
        metadata: dict[str, Any] = dict(raw_metadata) if isinstance(raw_metadata, dict) else {}
        candidate_text = bounded_redacted_text(str(candidate.get("response_text", "")), limit=500)
        return {
            "attempt": attempt,
            # Per-attempt candidate text is bounded and minimized before
            # truncation. The raw-byte digest remains the independent
            # integrity value; this field is for human/audit inspection only.
            "candidate_text": candidate_text["text"],
            "candidate_text_chars": candidate_text["chars"],
            "candidate_text_truncated": candidate_text["truncated"],
            "candidate_text_availability": candidate_text["availability"],
            "selected_strategy": metadata.get("selected_strategy", "NOT_VERIFIABLE"),
            "decision_event_id": metadata.get("decision_event_id", "NOT_VERIFIABLE"),
            "decision_event_sha256": metadata.get("decision_event_sha256", "NOT_VERIFIABLE"),
            "decision_selected": metadata.get("decision_selected", "NOT_VERIFIABLE"),
            "strategy_delivered_to_generator": metadata.get("strategy_delivered_to_generator", "NOT_VERIFIABLE"),
            "strategy_consumed_by_template": metadata.get("strategy_consumed_by_template", "NOT_VERIFIABLE"),
            "actual_generator_invocation": metadata.get("actual_generator_invocation", "NOT_VERIFIABLE"),
            "candidate_response_sha256": metadata.get("candidate_response_sha256", Harness._candidate_digest(candidate)),
            "verifier_verdict": "NOT_VERIFIABLE",
            "hitl_result": "NOT_VERIFIABLE",
            "fallback_reason": metadata.get("strategy_runtime_fallback", "NOT_VERIFIABLE"),
            "served_path": candidate.get("serve_path", "NOT_VERIFIABLE"),
            "fictional_state_before_hash": metadata.get("fictional_state_before_hash", "NOT_VERIFIABLE"),
            "fictional_state_proposed_hash": metadata.get("fictional_state_proposed_hash", "NOT_VERIFIABLE"),
            "fictional_state_after_hash": metadata.get("fictional_state_after_hash", "NOT_VERIFIABLE"),
            "generation_error": str(candidate.get("error") or ""),
            "commit_event": "NOT_VERIFIABLE",
            "commit_reason": "NOT_VERIFIABLE",
            "commit_state_effect": "not_committed",
            "commit_graph_before_sha256": None,
            "commit_graph_after_sha256": None,
            "outcome": "EXECUTION_FAILED",
        }

    @staticmethod
    def _attach_decision_reference(ctx: _ProcessContext, candidate: dict[str, Any]) -> None:
        """Attach the actual STRATEGY_UPDATE reference to a candidate.

        The per-turn decision is already emitted as a durable event. This makes
        the serving trace point at that event (and carries a small, explicit
        selection projection) instead of inferring a decision from unrelated
        metadata.
        """
        decision = ctx.context.get("policy_decision")
        if not isinstance(decision, dict):
            return
        metadata = candidate.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}
        selected = {
            key: decision.get(key)
            for key in (
                "selected_response_strategy",
                "policy_reason_code",
                "gate_state",
                "gate_reason",
                "fallback_reason",
                "arm",
                "policy_version",
            )
            if key in decision
        }
        refs = decision.get("supporting_evidence_refs")
        if isinstance(refs, list):
            selected["supporting_evidence_refs"] = [str(item)[:128] for item in refs[:20]]
        metadata.setdefault("decision_event_id", ctx.context.get("strategy_update_event_id", "NOT_VERIFIABLE"))
        metadata.setdefault(
            "decision_event_sha256", ctx.context.get("strategy_update_event_sha256", "NOT_VERIFIABLE")
        )
        metadata.setdefault("decision_selected", selected)
        candidate["metadata"] = metadata

    @staticmethod
    def _attach_serving_trace(response: dict[str, Any], attempts: list[dict[str, Any]], outcome: str) -> None:
        from ragin.cycle.transcript_contract import describe as describe_contract

        metadata = response.setdefault("metadata", {})
        metadata["serving_outcome"] = outcome
        metadata["serving_attempts"] = [dict(item) for item in attempts]
        served_text = str(response.get("response_text", ""))
        metadata["served_response_sha256"] = hashlib.sha256(served_text.encode()).hexdigest()
        # Serving-boundary provenance: the bytes recorded here are RAGIN's
        # response payload, and the contract says whether a command echo belongs
        # to this payload or to the frontend's PTY. Without this pair, a reader
        # cannot tell a duplicated echo from a legitimate one.
        metadata["served_response_bytes"] = len(served_text.encode())
        metadata["served_text_scope"] = "ragin_response_payload"
        metadata["transcript_contract"] = describe_contract()

    def _strict_candidate(self, ctx: _ProcessContext, feedback: str, attempt: int) -> dict[str, Any]:
        if self._deceiver is None:
            return {"response_text": "", "error": "generator_unavailable"}
        context = {
            **self._enrich_context(ctx),
            "feedback": feedback,
            "retry_attempt": attempt,
        }
        graph = self.fiction(
            ctx.result.session_id,
            str(ctx.result.classification.get("skill_level", "novice")),
        )
        context["fiction_block"] = graph.fact_block()
        if self._host_store is not None and self._host_store.pinned_identity:
            context["host_identity"] = self._host_store.pinned_identity
        try:
            candidate = self._deceiver.generate_response(ctx.result.attacker_input, context)
        except Exception as exc:
            return {"response_text": "", "error": f"generator_exception:{exc.__class__.__name__}"}
        return candidate if isinstance(candidate, dict) else {"response_text": str(candidate)}

    def _strict_verify(self, candidate: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        policy = self._verification_policy.to_dict()
        if self._verifier is None:
            return {
                "passed": False,
                "issues": ["verifier_unconfigured"],
                "deterministic": False,
                "verification_policy": policy,
            }
        try:
            decision = self._verifier.verify(candidate, context)
        except Exception as exc:
            return {
                "passed": False,
                "issues": [f"verifier_exception:{exc.__class__.__name__}"],
                "deterministic": True,
                "verification_policy": policy,
            }
        if not isinstance(decision, dict):
            return {
                "passed": False,
                "issues": ["verifier_malformed_result"],
                "deterministic": True,
                "verification_policy": policy,
            }
        decision = dict(decision)
        decision.setdefault("verification_policy", policy)
        if decision.get("passed") is not True:
            # Preserve whatever the verifier reported, but ALWAYS make the
            # failure explicit. Returning a bare {} here (the old behavior for
            # a dict without "passed") lost the reason and left downstream
            # observers unable to distinguish malformed from absent evidence.
            malformed = dict(decision)
            malformed["passed"] = False
            malformed.setdefault("issues", ["verifier_malformed_result"])
            return malformed
        return decision

    def _strict_approval(self, ctx: _ProcessContext, candidate: dict[str, Any]) -> dict[str, Any]:
        state = self._strict_verification_context(ctx)
        state["deception_response"] = candidate
        try:
            decision = self._approval_gateway.resolve(state)
        except RequiresApprovalError as exc:
            return {
                "approved": False,
                "level": "require",
                "reason": "approval_required",
                "request": exc.request.to_dict(),
            }
        except Exception as exc:
            return {"approved": False, "level": "error", "reason": f"approval_exception:{exc.__class__.__name__}"}
        return decision.to_dict()

    def _emit_rejected_verification(
        self,
        ctx: _ProcessContext,
        verification: dict[str, Any],
        attempt_trace: dict[str, Any],
        candidate: dict[str, Any],
    ) -> None:
        """Emit a rejection with the same sanitized contract as an acceptance.

        The accepted path emits the full verification dict plus the explicit
        commit disposition. A rejected path must not silently drop
        ``strict_verdict``, ``verification_policy``, ``deadline_enforced``, or
        the disposition: downstream trace readers use the VERIFICATION event
        itself to distinguish a verifier rejection from an absent verdict.
        The verifier contract carries only stable reason codes and digests, so
        extending it here does not expose candidate or attacker text.
        """
        event = dict(verification)
        event.update(
            {
                "attempt": attempt_trace.get("attempt"),
                "candidate_sha256": self._candidate_digest(candidate),
                "commit_event": attempt_trace.get("commit_event", "not_attempted"),
                "commit_reason": attempt_trace.get("commit_reason", "verification_failed"),
                "commit_state_effect": attempt_trace.get(
                    "commit_state_effect", "not_committed"
                ),
                "commit_graph_before_sha256": attempt_trace.get(
                    "commit_graph_before_sha256"
                ),
                "commit_graph_after_sha256": attempt_trace.get(
                    "commit_graph_after_sha256"
                ),
            }
        )
        ctx.emit(EventType.VERIFICATION, event, source="verified-serving")

    def _strict_commit(
        self,
        ctx: _ProcessContext,
        candidate: dict[str, Any],
        verification: dict[str, Any],
        approval: dict[str, Any],
        serve_path: str,
        attempt: int,
    ) -> dict[str, Any]:
        """Attempt the fiction commit transaction for a verifier/HITL-cleared
        candidate.

        Always returns an explicit disposition dict — never an inference:
        ``committed`` (transaction outcome), ``commit_event`` (accepted|rejected),
        ``commit_reason``, ``commit_state_effect`` (state_changed |
        no_op_state_unchanged | not_committed) and the fiction-graph state
        hashes before/after the transaction so rollback and no-op commits are
        observable in the serving trace.
        """
        serve_path = str(candidate.get("serve_path") or serve_path)
        graph = self.fiction(
            ctx.result.session_id,
            str(ctx.result.classification.get("skill_level", "novice")),
        )
        graph_before = graph.clone()
        before_hash = self._graph_digest(graph)
        host_before = self._host_store.to_dict() if self._host_store is not None else None
        staged = graph.clone()
        observed = staged.observe(str(candidate.get("response_text", "")), source="accepted")
        if observed.contradictions:
            return {
                "committed": False,
                "commit_event": "rejected",
                "commit_reason": "staged_state_contradiction",
                "commit_state_effect": "not_committed",
                "commit_graph_before_sha256": before_hash,
                "commit_graph_after_sha256": before_hash,
            }
        graph.replace_from(staged)

        # The candidate the verifier cleared is the candidate that is served.
        # A former post-verification prompt-template substitution was
        # unreachable here (it read ctx.context["attacker_input"], a key
        # build_context never emits) and, if it had fired, would have changed
        # the wire bytes after the verifier cleared them. It is removed so the
        # invariant "verified bytes == served bytes" holds structurally.
        served_response_sha256 = self._candidate_digest(candidate)

        try:
            if self._host_store is not None:
                self._host_store.mark_verified(ctx.result.session_id)
                self._host_store.promote_verified(ctx.result.session_id)
                if self._host_fiction_path:
                    self._host_store.save(self._host_fiction_path)
            commit_candidate = getattr(self._deceiver, "commit_candidate", None)
            if callable(commit_candidate) and isinstance(candidate.get("metadata"), dict) and "strategy_candidate_id" in candidate["metadata"]:
                commit_result = commit_candidate(candidate, verifier_passed=True, hitl_approved=True)
                if not commit_result.get("committed"):
                    graph.replace_from(graph_before)
                    if self._host_store is not None and host_before is not None:
                        self._host_store.restore_from_dict(host_before)
                        # The host store was promoted + saved before the
                        # generator commit; persist the rollback too so a
                        # restart cannot resurrect the rejected update.
                        if self._host_fiction_path:
                            self._host_store.save(self._host_fiction_path)
                    return {
                        "committed": False,
                        "commit_event": "rejected",
                        "commit_reason": f"generator_commit_rejected:{commit_result.get('reason') or 'not_committed'}",
                        "commit_state_effect": "not_committed",
                        "commit_graph_before_sha256": before_hash,
                        "commit_graph_after_sha256": self._graph_digest(graph),
                    }
                candidate = dict(candidate)
                candidate["metadata"] = dict(candidate["metadata"])
                candidate["metadata"]["fictional_state_after_hash"] = commit_result.get("state_version")
                candidate["metadata"]["fictional_commit_event"] = "accepted"
            after_hash = self._graph_digest(graph)
            state_effect = "state_changed" if after_hash != before_hash else "no_op_state_unchanged"
            ctx.result.deception_response = dict(candidate)
            ctx.result.verification = {
                **verification,
                "passed": True,
                "accepted": True,
                "serve_path": serve_path,
                "attempt": attempt,
                "candidate_sha256": served_response_sha256,
                # Explicit final-response observability: the verifier and the
                # attacker saw the same bytes. These fields are emitted in the
                # VERIFICATION and SYSTEM_RESPONSE events and exported to the
                # field JSONL, so a served response can always be matched to
                # the verdict that cleared it.
                "served_response_sha256": served_response_sha256,
                "verified_response_sha256": served_response_sha256,
                "served_response_chars": len(str(candidate.get("response_text", ""))),
                "commit_event": "accepted",
                "commit_reason": "accepted",
                "commit_state_effect": state_effect,
                "commit_graph_before_sha256": before_hash,
                "commit_graph_after_sha256": after_hash,
            }
            ctx.result.approval = approval
            ctx.emit(EventType.VERIFICATION, ctx.result.verification, source="verified-serving")
            self._emit_system_response(
                ctx,
                {
                    "serve_path": serve_path,
                    "approval": approval,
                    "candidate_sha256": served_response_sha256,
                    "served_response_sha256": served_response_sha256,
                },
            )
            return {
                "committed": True,
                "commit_event": "accepted",
                "commit_reason": "accepted",
                "commit_state_effect": state_effect,
                "commit_graph_before_sha256": before_hash,
                "commit_graph_after_sha256": after_hash,
            }
        except Exception as exc:
            # FAIL CLOSED: a commit-time exception (host promote/persist,
            # disk failure, ...) aborts the turn — never served, never
            # retried into a fallback. Restore in-memory state, best-effort
            # persist the rollback, attach the explicit disposition for the
            # serving trace, then re-raise so the turn records
            # verified_serve_failed.
            logger.error("Fiction commit failed (rolling back): %s", exc, exc_info=True)
            graph.replace_from(graph_before)
            if self._host_store is not None and host_before is not None:
                self._host_store.restore_from_dict(host_before)
                if self._host_fiction_path:
                    with contextlib.suppress(Exception):
                        self._host_store.save(self._host_fiction_path)
            disposition = {
                "committed": False,
                "commit_event": "rejected",
                "commit_reason": f"commit_exception:{exc.__class__.__name__}",
                "commit_state_effect": "not_committed",
                "commit_graph_before_sha256": before_hash,
                "commit_graph_after_sha256": self._graph_digest(graph),
            }
            with contextlib.suppress(Exception):
                exc.step5_commit_disposition = disposition
            raise

    def _process_verified(self, session: Session, attacker_input: str) -> PipelineResult:
        start = time.monotonic()
        ctx = _ProcessContext(
            result=PipelineResult(session_id=session.session_id, attacker_input=attacker_input),
            session=session,
        )
        feedback = ""
        serving_attempts: list[dict[str, Any]] = []
        try:
            self._emit_attacker_input(ctx, attacker_input)
            self._build_and_store_context(ctx)
            self._run_classification(ctx, attacker_input)
            self._run_cti_lookup(ctx, attacker_input)
            if self._decision_arm != "RAGIN_BASELINE":
                bundle = ctx.result.cti_analysis.get("evidence_bundle") if isinstance(ctx.result.cti_analysis, dict) else None
                if not isinstance(bundle, dict):
                    bundle = failure_evidence_bundle(ctx.context, attacker_input, "missing_evidence_bundle")
                gate_result = self._policy_selector.gate.evaluate(bundle)
                policy_decision = (
                    self._policy_selector.select(bundle)
                    if gate_result.get("gate_state") == "VALID_EVIDENCE"
                    else self._policy_selector.fallback_decision(bundle, gate_result)
                )
                policy_decision["session_id"] = session.session_id
                policy_decision["arm"] = self._decision_arm
                ctx.context["policy_decision"] = policy_decision
                strategy_event = ctx.emit(EventType.STRATEGY_UPDATE, policy_decision, source="v4-policy")
                ctx.context["strategy_update_event_id"] = strategy_event.event_id
                ctx.context["strategy_update_event_sha256"] = hashlib.sha256(
                    json.dumps(policy_decision, sort_keys=True, default=str).encode()
                ).hexdigest()
            self.fiction(session.session_id, str(ctx.result.classification.get("skill_level", "novice")))
            for attempt in range(1, self._max_retries + 2):
                candidate = self._strict_candidate(ctx, feedback, attempt)
                self._attach_decision_reference(ctx, candidate)
                # E23: declare the deep shell-fiction facts into the session
                # graph BEFORE verification — the registered deep layer's
                # facts are fiction ground truth, not unsupported attacker
                # claims (the verifier grounds against this same graph).
                for _df in _deep_shell_facts_for(ctx.result.attacker_input):
                    self.fiction(
                        ctx.result.session_id,
                        str(ctx.result.classification.get("skill_level", "novice")),
                    ).declare(_df[0], _df[1], _df[2], "deep-fiction")
                attempt_trace = self._serving_attempt(candidate, attempt)
                serving_attempts.append(attempt_trace)
                context = self._strict_verification_context(ctx)
                verification = self._strict_verify(candidate, context)
                attempt_trace["verifier_verdict"] = dict(verification)
                if verification.get("passed") is True:
                    approval = self._strict_approval(ctx, candidate)
                    attempt_trace["hitl_result"] = dict(approval)
                    if approval.get("approved") is True:
                        try:
                            commit = self._strict_commit(ctx, candidate, verification, approval, "GENERATED_VERIFIED", attempt)
                        except Exception as exc:  # fail-closed: record the explicit disposition + attempt evidence, then abort the turn
                            commit = getattr(exc, "step5_commit_disposition", None) or {
                                "committed": False,
                                "commit_event": "rejected",
                                "commit_reason": f"commit_exception:{exc.__class__.__name__}",
                                "commit_state_effect": "not_committed",
                                "commit_graph_before_sha256": None,
                                "commit_graph_after_sha256": None,
                            }
                            attempt_trace["commit_event"] = commit["commit_event"]
                            attempt_trace["commit_reason"] = commit["commit_reason"]
                            attempt_trace["commit_state_effect"] = commit["commit_state_effect"]
                            attempt_trace["commit_graph_before_sha256"] = commit["commit_graph_before_sha256"]
                            attempt_trace["commit_graph_after_sha256"] = commit["commit_graph_after_sha256"]
                            discard_on_abort = getattr(self._deceiver, "commit_candidate", None)
                            if callable(discard_on_abort) and isinstance(candidate.get("metadata"), dict) and "strategy_candidate_id" in candidate["metadata"]:
                                with contextlib.suppress(Exception):
                                    discard_on_abort(candidate, verifier_passed=False, hitl_approved=False)
                            if attempt_trace["outcome"] == "EXECUTION_FAILED":
                                attempt_trace["outcome"] = "STRATEGY_CONSUMED_BUT_REJECTED" if attempt_trace["strategy_consumed_by_template"] is True else "EXECUTION_FAILED"
                                attempt_trace["fallback_reason"] = commit["commit_reason"]
                            ctx.emit(EventType.RESPONSE_GENERATE, {"attempt": attempt, "serving_trace": dict(attempt_trace)}, source="verified-serving")
                            raise
                        attempt_trace["commit_event"] = commit["commit_event"]
                        attempt_trace["commit_reason"] = commit["commit_reason"]
                        attempt_trace["commit_state_effect"] = commit["commit_state_effect"]
                        attempt_trace["commit_graph_before_sha256"] = commit["commit_graph_before_sha256"]
                        attempt_trace["commit_graph_after_sha256"] = commit["commit_graph_after_sha256"]
                        if commit["committed"]:
                            served = ctx.result.deception_response
                            # Metadata-less candidates (baseline Hisoka arm)
                            # never consumed a strategy — label the serve
                            # honestly instead of claiming V4 consumption.
                            attempt_trace["outcome"] = served.get("metadata", {}).get("serving_outcome", "VERIFIED_SERVED")
                            attempt_trace["served_path"] = served.get("serve_path", attempt_trace["served_path"])
                            attempt_trace["fictional_state_after_hash"] = served.get("metadata", {}).get("fictional_state_after_hash", attempt_trace["fictional_state_after_hash"])
                            attempt_trace["served_response_sha256"] = hashlib.sha256(str(served.get("response_text", "")).encode()).hexdigest()
                            self._attach_serving_trace(served, serving_attempts, attempt_trace["outcome"])
                            ctx.emit(EventType.RESPONSE_GENERATE, {"attempt": attempt, "serving_trace": dict(attempt_trace)}, source="verified-serving")
                            return self._finalize_result(ctx, start)
                        verification = {
                            "passed": False,
                            "issues": ["staged_state_conflict"],
                            "deterministic": True,
                        }
                    else:
                        ctx.result.approval = approval
                        verification = {
                            **verification,
                            "passed": False,
                            "issues": ["approval_not_granted"],
                        }
                        attempt_trace["outcome"] = "STRATEGY_CONSUMED_BUT_REJECTED" if attempt_trace["strategy_consumed_by_template"] is True else "SAFE_FALLBACK_SERVED"
                        attempt_trace["fallback_reason"] = "approval_not_granted"
                        attempt_trace["commit_event"] = "not_attempted"
                        attempt_trace["commit_reason"] = "approval_not_granted"
                discard_candidate = getattr(self._deceiver, "commit_candidate", None)
                if callable(discard_candidate) and isinstance(candidate.get("metadata"), dict) and "strategy_candidate_id" in candidate["metadata"]:
                    # Best-effort generator-side cleanup of the rejected
                    # candidate. A discard failure must not abort the turn's
                    # observability (the attempt's disposition is already
                    # recorded) nor prevent the retry/fallback path.
                    with contextlib.suppress(Exception):
                        discard_candidate(candidate, verifier_passed=False, hitl_approved=False)
                ctx.result.verification = verification
                feedback = "Previous response failed verification: " + "; ".join(verification.get("issues", []))
                if attempt_trace["outcome"] == "EXECUTION_FAILED":
                    attempt_trace["outcome"] = "STRATEGY_CONSUMED_BUT_REJECTED" if attempt_trace["strategy_consumed_by_template"] is True else "EXECUTION_FAILED"
                    attempt_trace["fallback_reason"] = ";".join(verification.get("issues", [])) or "verification_failed"
                # Explicit dispositions — never left as NOT_VERIFIABLE, never
                # inferred: a commit that was not attempted says so, with why.
                if attempt_trace["commit_event"] == "NOT_VERIFIABLE":
                    generation_error = str(attempt_trace.get("generation_error") or "")
                    attempt_trace["commit_event"] = "not_attempted"
                    attempt_trace["commit_reason"] = f"generation_failed:{generation_error}" if generation_error else "verification_failed"
                if attempt_trace["hitl_result"] == "NOT_VERIFIABLE":
                    attempt_trace["hitl_result"] = {"evaluated": False, "approved": None, "reason": "verification_not_passed"}
                self._emit_rejected_verification(ctx, verification, attempt_trace, candidate)
                ctx.emit(EventType.RESPONSE_GENERATE, {"attempt": attempt, "serving_trace": dict(attempt_trace)}, source="verified-serving")
                if verification.get("issues") == ["approval_not_granted"]:
                    break

            skill = str(ctx.result.classification.get("skill_level", "novice"))
            identity = self._host_store.pinned_identity if self._host_store is not None else None
            fallback = ResponseGenerator()._generate_template(skill, attacker_input, feedback, identity)
            fallback_candidate = {"response_text": fallback, "serve_path": "FALLBACK_VERIFIED", "fallback_served": True}
            self._attach_decision_reference(ctx, fallback_candidate)
            fallback_trace = self._serving_attempt(fallback_candidate, self._max_retries + 2)
            fallback_trace["selected_strategy"] = (ctx.context.get("policy_decision") or {}).get("selected_response_strategy", "NOT_VERIFIABLE")
            fallback_trace["strategy_consumed_by_template"] = False
            fallback_trace["actual_generator_invocation"] = False
            fallback_trace["fallback_reason"] = serving_attempts[-1].get("fallback_reason", "verified_serve_unavailable") if serving_attempts else "verified_serve_unavailable"
            serving_attempts.append(fallback_trace)
            raw_fallback_metadata = fallback_candidate.get("metadata")
            fallback_metadata: dict[str, Any] = (
                dict(raw_fallback_metadata) if isinstance(raw_fallback_metadata, dict) else {}
            )
            fallback_metadata.update({"serving_outcome": "SAFE_FALLBACK_SERVED", "selected_strategy": fallback_trace["selected_strategy"], "strategy_consumed_by_template": False, "actual_generator_invocation": False, "fallback_reason": fallback_trace["fallback_reason"]})
            fallback_candidate["metadata"] = fallback_metadata
            fallback_verification = self._strict_verify(fallback_candidate, self._strict_verification_context(ctx))
            fallback_trace["verifier_verdict"] = dict(fallback_verification)
            if fallback_verification.get("passed") is not True:
                fallback_trace["commit_event"] = "not_attempted"
                fallback_trace["commit_reason"] = "verification_failed"
                fallback_trace["hitl_result"] = {"evaluated": False, "approved": None, "reason": "verification_not_passed"}
            else:
                approval = self._strict_approval(ctx, fallback_candidate)
                fallback_trace["hitl_result"] = dict(approval)
                if approval.get("approved") is not True:
                    fallback_trace["commit_event"] = "not_attempted"
                    fallback_trace["commit_reason"] = "approval_not_granted"
                else:
                    try:
                        commit = self._strict_commit(ctx, fallback_candidate, fallback_verification, approval, "FALLBACK_VERIFIED", self._max_retries + 2)
                    except Exception as exc:  # fail-closed: record the fallback attempt's disposition + evidence, then abort
                        commit = getattr(exc, "step5_commit_disposition", None) or {
                            "committed": False,
                            "commit_event": "rejected",
                            "commit_reason": f"commit_exception:{exc.__class__.__name__}",
                            "commit_state_effect": "not_committed",
                            "commit_graph_before_sha256": None,
                            "commit_graph_after_sha256": None,
                        }
                        fallback_trace["commit_event"] = commit["commit_event"]
                        fallback_trace["commit_reason"] = commit["commit_reason"]
                        fallback_trace["commit_state_effect"] = commit["commit_state_effect"]
                        fallback_trace["commit_graph_before_sha256"] = commit["commit_graph_before_sha256"]
                        fallback_trace["commit_graph_after_sha256"] = commit["commit_graph_after_sha256"]
                        self._emit_rejected_verification(
                            ctx, fallback_verification, fallback_trace, fallback_candidate
                        )
                        ctx.emit(EventType.RESPONSE_GENERATE, {"attempt": fallback_trace["attempt"], "serving_trace": dict(fallback_trace)}, source="verified-serving")
                        raise
                    fallback_trace["commit_event"] = commit["commit_event"]
                    fallback_trace["commit_reason"] = "accepted_safe_fallback" if commit["committed"] else commit["commit_reason"]
                    fallback_trace["commit_state_effect"] = commit["commit_state_effect"]
                    fallback_trace["commit_graph_before_sha256"] = commit["commit_graph_before_sha256"]
                    fallback_trace["commit_graph_after_sha256"] = commit["commit_graph_after_sha256"]
                    if commit["committed"]:
                        fallback_trace["outcome"] = "SAFE_FALLBACK_SERVED"
                        fallback_trace["served_path"] = "FALLBACK_VERIFIED"
                        fallback_trace["served_response_sha256"] = hashlib.sha256(str(ctx.result.deception_response.get("response_text", "")).encode()).hexdigest()
                        self._attach_serving_trace(ctx.result.deception_response, serving_attempts, "SAFE_FALLBACK_SERVED")
                        ctx.emit(EventType.RESPONSE_GENERATE, {"attempt": fallback_trace["attempt"], "serving_trace": dict(fallback_trace)}, source="verified-serving")
                        return self._finalize_result(ctx, start)
            # Emit the fallback attempt trace ONCE, after its verifier/approval/
            # commit dispositions are known, so the event carries them. The
            # fallback rejection itself is also a VERIFICATION event, so a
            # rejected fallback is not observable only through RESPONSE_GENERATE.
            self._emit_rejected_verification(
                ctx, fallback_verification, fallback_trace, fallback_candidate
            )
            ctx.emit(EventType.RESPONSE_GENERATE, {"attempt": fallback_trace["attempt"], "serving_trace": dict(fallback_trace)}, source="verified-serving")
            ctx.result.deception_response = {}
            ctx.result.error = "verified_serve_unavailable"
            ctx.emit(
                EventType.ERROR,
                {"stage": "verified_serving", "error": ctx.result.error},
                source="verified-serving",
            )
        except Exception as exc:
            logger.error("Verified serving failed: %s", exc, exc_info=True)
            ctx.result.deception_response = {}
            ctx.result.error = "verified_serving_failed"
            with contextlib.suppress(Exception):
                ctx.emit(EventType.ERROR, {"stage": "verified_serving", "error": ctx.result.error}, source="verified-serving")
        return self._finalize_result(ctx, start)

    @classmethod
    def wake(
        cls,
        session_id: str,
        classifier: Classifier | None = None,
        cti_engine: CTIEngine | None = None,
        deceiver: Deceiver | None = None,
        session_dir: str | None = None,
    ) -> tuple[Session, dict[str, Any]]:
        """Resume a crashed session from its durable event log.

        Replays the log to rebuild the interaction counters the pipeline
        relies on, emits SESSION_RESUME, and returns (session, context)
        where context carries the replay summary the /api/session/wake
        endpoint reports. The returned session can be handed straight to
        process() on a fresh Harness instance.

        Raises FileNotFoundError if the session log does not exist.
        """
        session = Session.wake(session_id, session_dir=session_dir)
        interactions = session.get_events_by_type(EventType.ATTACKER_INPUT)
        context: dict[str, Any] = {
            "total_events": session._event_count,
            "interaction_count": len(interactions),
        }
        logger.info(
            "Harness wake: session %s resumed with %d interactions replayed",
            session_id,
            context["interaction_count"],
        )
        return session, context

    # ------------------------------------------------------------------
    # Context helpers
    # ------------------------------------------------------------------

    def _enrich_context(self, ctx: _ProcessContext) -> dict[str, Any]:
        return {
            **ctx.context,
            "classification": ctx.result.classification,
            "cti_analysis": ctx.result.cti_analysis,
        }

    def _emit_attacker_input(self, ctx: _ProcessContext, attacker_input: str) -> None:
        ctx.emit(EventType.ATTACKER_INPUT, {"command": attacker_input}, source="harness")

    def _build_and_store_context(self, ctx: _ProcessContext) -> dict[str, Any]:
        ctx.context = ctx.session.build_context()
        return ctx.context

    def _record_pipeline_error(self, ctx: _ProcessContext, error: str) -> None:
        ctx.result.error = error
        ctx.emit(EventType.ERROR, {"stage": "pipeline", "error": error}, source="harness")

    def _finalize_result(self, ctx: _ProcessContext, start: float) -> PipelineResult:
        ctx.result.total_time_ms = (time.monotonic() - start) * 1000
        ctx.result.events_emitted = ctx.events_emitted
        return ctx.result

    # ------------------------------------------------------------------
    # Pipeline stage helpers  (used by all process_* variants)
    # ------------------------------------------------------------------

    def _run_classification(self, ctx: _ProcessContext, attacker_input: str, timer=None) -> None:
        if not self._classifier:
            return
        try:
            with timer.track("classification") if timer else contextlib.nullcontext():
                ctx.result.classification = self._classifier.classify(attacker_input, ctx.context)
            ctx.emit(EventType.CLASSIFICATION, ctx.result.classification, source="chrollo")
        except Exception as e:
            logger.warning("Classification failed: %s", e)
            ctx.result.classification = {
                "skill_level": "novice",
                "confidence": 0.0,
                "error": str(e),
            }
            ctx.emit(EventType.ERROR, {"stage": "classification", "error": str(e)}, source="chrollo")

    def _run_cti_lookup(self, ctx: _ProcessContext, attacker_input: str, timer=None) -> None:
        if not self._cti_engine:
            return
        try:
            # Don's protocol expects the CURRENT turn's classification under
            # the singular ``classification`` key. ctx.context is rebuilt from
            # the append-only log BEFORE this turn's classification event is
            # written, so it carries only prior turns (and historically only a
            # ``classifications`` list). Pass the current verdict explicitly;
            # otherwise Don silently analyzed every command as
            # "unknown"/SUSPICIOUS with confidence 0.5.
            cti_context = {**ctx.context, "classification": ctx.result.classification}
            with timer.track("cti_lookup") if timer else contextlib.nullcontext():
                ctx.result.cti_analysis = self._cti_engine.analyze(attacker_input, cti_context)
            ctx.emit(EventType.CTI_LOOKUP, ctx.result.cti_analysis, source="don")
        except Exception as e:
            logger.warning("CTI lookup failed: %s", e)
            ctx.result.cti_analysis = {
                "threat_summary": "",
                "recommendations": [],
                "error": str(e),
            }
            ctx.emit(EventType.ERROR, {"stage": "cti_lookup", "error": str(e)}, source="don")

    def _run_response_generation(self, ctx: _ProcessContext, attacker_input: str, timer=None) -> None:
        if not self._deceiver:
            return
        try:
            enriched = self._enrich_context(ctx)
            with timer.track("response") if timer else contextlib.nullcontext():
                ctx.result.deception_response = self._deceiver.generate_response(attacker_input, enriched)
            ctx.emit(
                EventType.RESPONSE_GENERATE,
                {
                    "persona_used": ctx.result.deception_response.get("persona_used", ""),
                    "engagement_score": ctx.result.deception_response.get("engagement_score", 0.0),
                },
                source="hisoka",
            )
            if ctx.result.deception_response.get("honeytoken_triggered"):
                ctx.result.cti_analysis["honeytoken_triggered"] = True
        except Exception as e:
            logger.warning("Response generation failed: %s", e)
            ctx.result.deception_response = {
                "response_text": "Error generating response.",
                "error": str(e),
            }
            ctx.emit(EventType.ERROR, {"stage": "response_generate", "error": str(e)}, source="hisoka")

    def _run_verification(
        self,
        ctx: _ProcessContext,
        event_type: EventType = EventType.RESPONSE_VERIFY,
        event_source: str = "verifier",
        timer=None,
        verifier: Any = None,
    ) -> None:
        if not self._verifier and not verifier:
            return
        if not ctx.result.deception_response:
            return
        try:
            # Use the explicitly-passed verifier if any; fall back to the
            # instance verifier. Read-only access — no swapping — so parallel
            # benchmark threads never observe each other's verifier.
            active_verifier = verifier or self._verifier
            if active_verifier is None:
                return
            with timer.track("verify") if timer else contextlib.nullcontext():
                ctx.result.verification = active_verifier.verify(ctx.result.deception_response, ctx.context)
            ctx.emit(event_type, ctx.result.verification, source=event_source)
            if not ctx.result.passed_verification and self._max_retries > 0:
                retry_events = self._retry_with_feedback(ctx, ctx.result, ctx.context)
                ctx.events_emitted += retry_events
        except Exception as e:
            # Fail closed. A verifier crash is not evidence of safety; the old
            # {"passed": True, "error": ...} made an exception indistinguishable
            # from a clean verdict on the legacy (non-mandatory) path.
            logger.warning("Verification failed closed: %s", e)
            ctx.result.verification = {
                "passed": False,
                "issues": [f"verifier_exception:{e.__class__.__name__}"],
                "deterministic": True,
                "error": str(e),
            }

    def _emit_system_response(self, ctx: _ProcessContext, extra: dict | None = None) -> None:
        verification = ctx.result.verification or {}
        data: dict[str, Any] = {
            "text": ctx.result.response_text,
            "persona_used": ctx.result.deception_response.get("persona_used", ""),
            "verification_passed": verification.get("passed") is True,
            "served_response_sha256": verification.get("served_response_sha256"),
        }
        if extra:
            data.update(extra)
        ctx.emit(EventType.SYSTEM_RESPONSE, data, source="harness")

    # ------------------------------------------------------------------
    # Extension stage helpers  (process_with_* variants only)
    # ------------------------------------------------------------------

    def _run_threat_modeling(
        self,
        ctx: _ProcessContext,
        attacker_input: str,
        threat_modeler: Any,
        timer=None,
    ):
        """Run STRIDE threat modeling. Returns the threat_model object or None."""
        if threat_modeler is None:
            return None
        try:
            if timer:
                with timer.track("threat_modeling"):
                    threat_model = threat_modeler.analyze(attacker_input, ctx.context)
            else:
                threat_model = threat_modeler.analyze(attacker_input, ctx.context)
            ctx.emit(EventType.THREAT_MODEL, threat_model.to_dict(), source="threat_modeler")
            ctx.context["threat_model"] = threat_model.to_dict()
            return threat_model
        except Exception as e:
            logger.warning("Threat modeling failed: %s", e)
            ctx.emit(EventType.ERROR, {"stage": "threat_modeling", "error": str(e)}, source="threat_modeler")
            return None

    def _run_supervisor_routing(self, ctx: _ProcessContext, supervisor: Any, attacker_input: str):
        """Run supervisor routing. Returns the routing_decision or None."""
        if not HAS_COORDINATION:
            return None
        try:
            decision = supervisor.route(
                session_context=ctx.context,
                classification=ctx.result.classification,
                session_id=ctx.session.session_id,
                current_persona=ctx.context.get("persona", ""),
            )
            ctx.emit(
                EventType.CLASSIFICATION,
                {"routing_decision": decision.to_dict(), "stage": "supervisor"},
                source="supervisor",
            )
            ctx.context["supervisor_routing"] = decision.to_dict()
            ctx.context["persona"] = decision.persona
            ctx.context["risk_level"] = decision.risk_level.value
            ctx.context["context_enrichments"] = decision.context_enrichments
            return decision
        except Exception as e:
            logger.warning("Supervisor routing failed: %s", e)
            ctx.emit(EventType.ERROR, {"stage": "supervisor_routing", "error": str(e)}, source="supervisor")
            return None

    def _run_expert_analysis(
        self,
        ctx: _ProcessContext,
        routing_decision: Any,
        expert_pool: Any,
        attacker_input: str,
    ) -> None:
        if not routing_decision.needs_expert:
            return
        try:
            expert_task = {
                "techniques": ctx.context.get("observed_ttps", []),
                "attacker_input": attacker_input,
                "domain": routing_decision.expert_domain,
            }
            expert_result = expert_pool.dispatch(routing_decision.expert_domain, expert_task, ctx.context)
            ctx.emit(
                EventType.CTI_LOOKUP,
                {
                    "expert_domain": routing_decision.expert_domain,
                    "expert_result": expert_result.to_dict(),
                    "stage": "expert_pool",
                },
                source="expert_pool",
            )
            ctx.context["expert_analysis"] = expert_result.to_dict()
        except Exception as e:
            logger.warning("Expert dispatch failed: %s", e)
            ctx.emit(EventType.ERROR, {"stage": "expert_dispatch", "error": str(e)}, source="expert_pool")

    def _run_voting(self, ctx: _ProcessContext, routing_decision: Any, voting_system: Any) -> None:
        if not routing_decision.needs_voting:
            return
        try:
            vote_result = voting_system.vote(ctx.result.deception_response, ctx.context)
            ctx.emit(
                EventType.RESPONSE_VERIFY,
                {
                    "vote_outcome": vote_result.outcome.value,
                    "confidence": vote_result.confidence,
                    "dissent_count": vote_result.dissent_count,
                    "stage": "voting_system",
                },
                source="voting_system",
            )
            if vote_result.final_response != ctx.result.deception_response:
                ctx.result.deception_response = vote_result.final_response
                ctx.result.verification["voting_applied"] = True
        except Exception as e:
            logger.warning("Voting failed: %s", e)
            ctx.emit(EventType.ERROR, {"stage": "voting", "error": str(e)}, source="voting_system")

    def _run_enhanced_review(self, ctx: _ProcessContext, enhanced_reviewer: Any) -> None:
        if not ctx.result.deception_response:
            return
        try:
            review_result = enhanced_reviewer.review(ctx.result.deception_response, ctx.context)
            ctx.emit(
                EventType.RESPONSE_VERIFY,
                {
                    "passed": review_result.get("passed", True),
                    "confidence": review_result.get("confidence", 0.0),
                    "stage": "enhanced_review",
                },
                source="enhanced_reviewer",
            )
            ctx.result.verification["enhanced_review"] = review_result
        except Exception as e:
            logger.warning("Enhanced review failed: %s", e)

    def _run_attack_chain(self, ctx: _ProcessContext, attack_chain_builder: Any) -> None:
        try:
            observed_ttps = ctx.context.get("observed_ttps", [])
            ttp_history = ctx.context.get("ttp_history", [])
            if not observed_ttps and not ttp_history:
                return
            chain = attack_chain_builder.build_from_session_context(ctx.session.session_id, ctx.context)
            if chain.step_count > 0:
                ctx.emit(EventType.ATTACK_CHAIN, chain.to_dict(), source="attack_chain_builder")
                ctx.result.verification["attack_chain"] = chain.to_dict()
        except Exception as e:
            logger.warning("Attack chain building failed: %s", e)

    def _run_finding(self, ctx: _ProcessContext, threat_model: Any) -> None:
        if not threat_model or threat_model.overall_risk not in ("high", "critical"):
            return
        ctx.emit(
            EventType.FINDING,
            {
                "session_id": ctx.session.session_id,
                "risk_level": threat_model.overall_risk,
                "threat_count": threat_model.threat_count,
                "high_risk_threats": [t.to_dict() for t in threat_model.high_risk_threats],
                "source_ip": ctx.context.get("source_ip", ""),
            },
            source="threat_modeler",
        )

    def _run_mtta(
        self,
        ctx: _ProcessContext,
        mtta_tracker: Any,
        timer,
        threat_model: Any,
        events_at_end: int,
    ) -> None:
        try:
            interaction_id = f"{ctx.session.session_id}-{events_at_end}"
            mtta_tracker.record_interaction(
                interaction_id=interaction_id,
                session_id=ctx.session.session_id,
                attacker_input=ctx.result.attacker_input,
                stages=timer.timings if timer else [],
                total_duration_ms=ctx.result.total_time_ms,
                metadata={
                    "threat_model_risk": threat_model.overall_risk if threat_model else "unknown",
                },
            )
        except Exception as e:
            logger.warning("MTTA recording failed: %s", e)

    def _init_timer(self, mtta_tracker=None):
        """Return a StageTimer if mtta_tracker is available, else None."""
        if mtta_tracker:
            try:
                from ragin.cycle.metrics import StageTimer

                return StageTimer()
            except ImportError:
                pass
        return None

    # ------------------------------------------------------------------
    # Public process methods
    # ------------------------------------------------------------------

    def process(
        self,
        session: Session,
        attacker_input: str,
    ) -> PipelineResult:
        if self._mandatory_verification:
            return self._process_verified(session, attacker_input)
        start = time.monotonic()
        ctx = _ProcessContext(
            result=PipelineResult(session_id=session.session_id, attacker_input=attacker_input),
            session=session,
        )

        try:
            self._emit_attacker_input(ctx, attacker_input)
            self._build_and_store_context(ctx)
            self._run_classification(ctx, attacker_input)
            self._run_cti_lookup(ctx, attacker_input)
            self._run_response_generation(ctx, attacker_input)
            self._run_verification(ctx)
            self._emit_system_response(ctx)
        except Exception as e:
            logger.error("Pipeline error: %s", e, exc_info=True)
            self._record_pipeline_error(ctx, str(e))

        return self._finalize_result(ctx, start)

    def process_with_supervisor(
        self,
        session: Session,
        attacker_input: str,
        supervisor: Any = None,
        voting_system: Any = None,
        expert_pool: Any = None,
        enhanced_reviewer: Any = None,
    ) -> PipelineResult:
        if self._mandatory_verification:
            return self._process_verified(session, attacker_input)
        start = time.monotonic()
        ctx = _ProcessContext(
            result=PipelineResult(session_id=session.session_id, attacker_input=attacker_input),
            session=session,
        )
        routing_decision = None

        try:
            self._emit_attacker_input(ctx, attacker_input)
            self._build_and_store_context(ctx)
            self._run_classification(ctx, attacker_input)
            routing_decision = self._run_supervisor_routing(ctx, supervisor, attacker_input)
            self._run_cti_lookup(ctx, attacker_input)
            self._run_expert_analysis(ctx, routing_decision, expert_pool, attacker_input)
            self._run_response_generation(ctx, attacker_input)
            self._run_voting(ctx, routing_decision, voting_system)
            if enhanced_reviewer:
                self._run_enhanced_review(ctx, enhanced_reviewer)
            self._run_verification(ctx)
            persona = routing_decision.persona if routing_decision else ""
            self._emit_system_response(ctx, {"persona": persona})
        except Exception as e:
            logger.error("Pipeline error: %s", e, exc_info=True)
            self._record_pipeline_error(ctx, str(e))

        return self._finalize_result(ctx, start)

    def process_with_threat_modeling(
        self,
        session: Session,
        attacker_input: str,
        threat_modeler: Any = None,
        response_verifier: Any = None,
        attack_chain_builder: Any = None,
        mtta_tracker: Any = None,
    ) -> PipelineResult:
        if self._mandatory_verification:
            return self._process_verified(session, attacker_input)
        start = time.monotonic()
        timer = self._init_timer(mtta_tracker)
        ctx = _ProcessContext(
            result=PipelineResult(session_id=session.session_id, attacker_input=attacker_input),
            session=session,
        )
        threat_model = None

        try:
            self._emit_attacker_input(ctx, attacker_input)
            self._build_and_store_context(ctx)
            self._run_classification(ctx, attacker_input, timer)
            threat_model = self._run_threat_modeling(ctx, attacker_input, threat_modeler, timer)
            self._run_cti_lookup(ctx, attacker_input, timer)
            self._run_response_generation(ctx, attacker_input, timer)

            # Use threat-model-aware verifier if provided, else standard verifier
            verifier = response_verifier or self._verifier
            if verifier and ctx.result.deception_response:
                self._run_verification(ctx, EventType.VERIFICATION, "threat_model_verifier", timer, verifier=verifier)

            self._emit_system_response(ctx)
            self._run_attack_chain(ctx, attack_chain_builder)
            self._run_finding(ctx, threat_model)
        except Exception as e:
            logger.error("Pipeline error: %s", e, exc_info=True)
            self._record_pipeline_error(ctx, str(e))

        result = self._finalize_result(ctx, start)
        self._run_mtta(ctx, mtta_tracker, timer, threat_model, ctx.events_emitted)
        return result

    def _retry_with_feedback(
        self,
        ctx: _ProcessContext,
        failed_result: PipelineResult,
        context: dict[str, Any],
    ) -> int:
        """Retry response generation with verification feedback.

        Returns the number of events emitted during retries.
        """
        issues = failed_result.verification.get("issues", [])
        feedback = f"Previous response had issues: {'; '.join(issues)}. Improve."
        events = 0

        for attempt in range(self._max_retries):
            if self._deceiver is None:  # retry needs the generator; without it there is nothing to retry
                return events
            try:
                enriched_context = {
                    **context,
                    "classification": failed_result.classification,
                    "cti_analysis": failed_result.cti_analysis,
                    "feedback": feedback,
                    "retry_attempt": attempt + 1,
                }
                new_response = self._deceiver.generate_response(failed_result.attacker_input, enriched_context)

                # Verify again
                if self._verifier:
                    new_verification = self._verifier.verify(new_response, enriched_context)
                    if new_verification.get("passed", True):
                        ctx.session.emit(
                            EventType.RESPONSE_GENERATE,
                            {
                                "persona_used": new_response.get("persona_used", ""),
                                "retry_attempt": attempt + 1,
                            },
                            source="hisoka",
                        )
                        events += 1
                        failed_result.deception_response = new_response
                        return events

                # If verifier passed or no verifier, accept response
                if not self._verifier:
                    failed_result.deception_response = new_response
                    return events

            except Exception:
                continue

        return events
