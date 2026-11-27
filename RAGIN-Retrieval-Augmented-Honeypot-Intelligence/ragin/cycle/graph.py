"""LangGraph orchestration for the RAGIN deception loop.

Re-implements the stateless Harness loop as a checkpointed, replayable LangGraph
state graph — the LangGraph/composeable-orchestration pillar of the TDSC novelty
plan. Nodes:

    classify -> analyze -> plan -> approval_gate -> generate -> verify -> finalize

New capabilities over the linear harness:

* Typed shared state (no ad-hoc context dict threading).
* Human-in-the-loop: the ``approval_gate`` node pauses via ``interrupt()`` and
  the graph is resumed with an operator decision, fully checkpointed.
* Replay/debug via the checkpointer; a crashed turn resumes from its checkpoint.
* Conditional retry edge: verification failure loops back to ``generate``.
* Graph-informed planning: the ``plan`` node augments the CTI analysis with
  next-TTP predictions and the session's fiction-graph fact block, so deception
  is proactive (steering) rather than reactive.

Graceful degradation: when LangGraph is not importable the pipeline falls back
to a deterministic linear executor of the *same* node functions, so behaviour
differs only in orchestration mechanics, never in component semantics.
"""

from __future__ import annotations

import logging
import os
import time
import hashlib
import json
from typing import Any, TypedDict

from ragin.cycle.hitl import ApprovalGateway, ApprovalRequest, RequiresApprovalError
from ragin.cycle.verifier import FictionConsistencyVerifier
from ragin.graph.fiction import FictionGraph
from ragin.graph.mitre import attach_strategy_context
from ragin.hisoka.deception import identity_for
from ragin.decision_fusion_v4.config import resolve_arm
from ragin.decision_fusion_v4.evidence_export import failure_evidence_bundle, sha256_json
from ragin.decision_fusion_v4.policy import build_selector

logger = logging.getLogger(__name__)

try:
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.graph import END, START, StateGraph
    from langgraph.types import Command, interrupt

    HAS_LANGGRAPH = True
except ImportError:  # pragma: no cover - exercised only in no-langgraph envs
    HAS_LANGGRAPH = False
    MemorySaver = None  # type: ignore[assignment,misc]
    START = END = None  # type: ignore[assignment]


class DeceptionState(TypedDict, total=False):
    """Shared state flowing through the LangGraph deception pipeline."""

    session_id: str
    session_dir: str
    attacker_input: str
    context: dict[str, Any]
    classification: dict[str, Any]
    cti_analysis: dict[str, Any]
    plan: dict[str, Any]
    fiction: dict[str, Any]
    approval: dict[str, Any]
    deception_response: dict[str, Any]
    verification: dict[str, Any]
    result: dict[str, Any]
    retries_left: int
    retry_feedback: str
    evidence_bundle: dict[str, Any]
    policy_decision: dict[str, Any]


# Direct serve-path provenance (S&P requirement: no latency inference).
# Every finalized turn carries one of these labels, stamped by the node that
# actually produced the served bytes:
#   GENERATED_VERIFIED    LLM draft that passed the deterministic verifier
#   GENERATED_RETRY       LLM draft that failed once, was regenerated, passed
#   FASTPATH_DETERMINISTIC  vetted template/fast-path content (designed rung,
#                         not degradation)
#   FALLBACK_VERIFIED     fail-safe template served after verification failure
#   HITL_SERVED           content served after explicit operator decision
SERVE_PATH_GENERATED_VERIFIED = "GENERATED_VERIFIED"
SERVE_PATH_GENERATED_RETRY = "GENERATED_RETRY"
SERVE_PATH_GENERATED_UNVERIFIED = "GENERATED_UNVERIFIED"
SERVE_PATH_FASTPATH = "FASTPATH_DETERMINISTIC"
SERVE_PATH_FALLBACK = "FALLBACK_VERIFIED"
# Gateway-unavailable deterministic template that the DECEIVER served (not the
# graph's fail-safe swap). Until 2026-09-28 these were stamped
# GENERATED_VERIFIED by generate_node's setdefault — a provenance hole the
# manual audit exposed (outage templates counted as verified LLM drafts).
SERVE_PATH_TEMPLATE_FALLBACK = "TEMPLATE_FALLBACK_VERIFIED"
SERVE_PATH_HITL = "HITL_SERVED"


class DeceptionGraph:
    """Checkpointed LangGraph state machine for a full deception turn."""

    def __init__(
        self,
        classifier: Any = None,
        analyzer: Any = None,
        deceiver: Any = None,
        verifier: Any = None,
        approval_gateway: ApprovalGateway | None = None,
        checkpointer: Any | None = None,
        human_in_the_loop: bool = False,
        max_retries: int = 1,
        decision_arm: str | None = None,
    ) -> None:
        self._classifier = classifier
        self._analyzer = analyzer
        self._deceiver = deceiver
        self._fiction_graphs: dict[str, FictionGraph] = {}
        # Host-level persistent fiction (OPT-IN via RAGIN_HOST_FICTION=1):
        # sessions facing the same host share/promote fiction across session
        # boundaries (cross-session consistency, plan advisory #9). Default
        # off — behavior is byte-identical to the session-scoped baseline.
        self._host_store: Any | None = None
        if os.environ.get("RAGIN_HOST_FICTION", "").strip().lower() in ("1", "true", "yes", "on"):
            from ragin.graph.host_fiction import HostFictionStore, HostFictionVerifier

            policy = os.environ.get("RAGIN_HOST_FICTION_POLICY", "per_session").strip().lower()
            self._host_store = HostFictionStore(
                host_key=os.environ.get("RAGIN_HOST_KEY", "default-host"), policy=policy
            )
        # Verification-before-serve (C2): default to the fiction-consistency
        # verifier so every graph run is machine-verified unless the caller
        # explicitly supplies another verifier. It shares the per-session
        # fiction graphs so verification checks the SAME facts the generation
        # node seeded (single invariant source).
        self._verifier = verifier if verifier is not None else FictionConsistencyVerifier(fictions=self._fiction_graphs)
        if self._host_store is not None:
            # Cross-session checks wrap (never replace) the session verifier:
            # a draft must pass its session checks BEFORE host-level facts
            # are consulted (fail-closed, session-first).
            from ragin.graph.host_fiction import HostFictionVerifier

            self._verifier = HostFictionVerifier(self._verifier, self._host_store)
        self._approval_gateway = approval_gateway or ApprovalGateway()
        self._checkpointer = checkpointer
        self._human_in_the_loop = human_in_the_loop
        self._max_retries = max_retries
        self._decision_arm = resolve_arm(decision_arm)
        self._policy_selector = build_selector(self._decision_arm)
        self._compiled: Any | None = None

    # ------------------------------------------------------------------
    # Fiction graph (per-session consistency memory)
    # ------------------------------------------------------------------

    def fiction(self, session_id: str, skill_level: str = "novice") -> FictionGraph:
        if self._host_store is not None:
            # Host-pinned provisioning: first contact pins the identity; every
            # later session is seeded with the SAME machine regardless of how
            # the attacker's classification changed. The graph is ALSO
            # registered in the shared registry so the verifier reads the
            # same object generation seeded (single invariant source).
            ident = self._host_store.pinned_identity or identity_for(skill_level)
            graph = self._host_store.session_graph(session_id, identity=ident)
            self._fiction_graphs[session_id] = graph
            return graph
        graph = self._fiction_graphs.get(session_id)
        if graph is None:
            graph = FictionGraph(session_id=session_id, identity=identity_for(skill_level))
            self._fiction_graphs[session_id] = graph
        return graph

    # ------------------------------------------------------------------
    # Nodes
    # ------------------------------------------------------------------

    def classify_node(self, state: DeceptionState) -> dict[str, Any]:
        if not self._classifier:
            return {"classification": {"skill_level": "novice", "confidence": 0.0}}
        out = self._classifier.classify(state["attacker_input"], state.get("context", {}) or {})
        return {
            "classification": {
                "skill_level": out.get("skill_level", "novice"),
                "confidence": out.get("confidence", 0.0),
                "error": out.get("error", ""),
            }
        }

    def analyze_node(self, state: DeceptionState) -> dict[str, Any]:
        ctx = dict(state.get("context", {}) or {})
        ctx["classification"] = state.get("classification", {})
        if not self._analyzer:
            out: dict[str, Any] = {"threat_summary": "", "recommendations": [], "extracted_techniques": []}
        else:
            out = self._analyzer.analyze(state["attacker_input"], ctx)
            if not isinstance(out, dict):
                out = {"threat_summary": str(out), "recommendations": []}
            out["extracted_techniques"] = out.get("extracted_techniques") or out.get("ttp_ids") or []
        bundle = out.get("evidence_bundle") if isinstance(out, dict) else None
        if not isinstance(bundle, dict):
            bundle = failure_evidence_bundle(ctx, state["attacker_input"], "missing_evidence_bundle")
        return {"cti_analysis": out, "evidence_bundle": bundle}

    def plan_node(self, state: DeceptionState) -> dict[str, Any]:
        cti = dict(state.get("cti_analysis", {}) or {})
        skill = (state.get("classification", {}) or {}).get("skill_level", "novice")
        fiction = self.fiction(state["session_id"], skill_level=skill)
        fiction_block = fiction.fact_block()

        policy_decision = None
        if self._decision_arm == "RAGIN_BASELINE":
            cti = attach_strategy_context(cti)
            strategy = cti.get("deception_strategy", {}) or {}
            bait = strategy.get("bait") or []
            steer = strategy.get("steer") or ""
            strategy_lines = [f"  likely next moves (steer): {steer or 'generic continuation'}"]
            strategy_lines.extend(f"  bait: {hint}" for hint in bait[:6])
            strategy_block = "Deception strategy for this engagement:\n" + "\n".join(strategy_lines) + "\n"
        else:
            bundle = state.get("evidence_bundle") or failure_evidence_bundle(state.get("context", {}) or {}, state["attacker_input"], "missing_evidence_bundle")
            gate_result = self._policy_selector.gate.evaluate(bundle)
            policy_decision = self._policy_selector.select(bundle) if gate_result["gate_state"] == "VALID_EVIDENCE" else self._policy_selector.fallback_decision(bundle, gate_result)
            policy_decision["session_id"] = state["session_id"]
            policy_decision["arm"] = self._decision_arm
            selected = policy_decision["selected_response_strategy"]
            strategy = {"selected_response_strategy": selected, "policy_reason_code": policy_decision["policy_reason_code"]}
            strategy_block = f"Bounded response strategy: {selected}\n"

        plan = {
            "persona": skill,
            "strategy": strategy,
            "strategy_block": strategy_block,
            "next_techniques_predicted": cti.get("next_techniques_predicted", []),
            "fiction_block": fiction_block,
            "identity": identity_for(skill),
        }
        updates: dict[str, Any] = {"cti_analysis": cti, "plan": plan, "fiction": fiction.to_dict()}
        if policy_decision is not None:
            updates["policy_decision"] = policy_decision
        return updates

    def approval_node(self, state: DeceptionState) -> dict[str, Any]:
        gateway = self._approval_gateway
        # DeceptionState is a TypedDict, i.e. a dict[str, Any] at runtime;
        # the approval gateway's dict-typed API consumes it directly.
        state_dict: dict[str, Any] = dict(state)
        if gateway.requires_approval(state_dict) and self._human_in_the_loop:
            request: ApprovalRequest = gateway.build_request(state_dict)
            payload = interrupt(
                {"type": "approval_request", "session_id": request.session_id, "request": request.to_dict()}
            )
            if isinstance(payload, dict) and "decided" in payload:
                decided = bool(payload.get("decided"))
                reason = str(payload.get("reason", "") or "operator decision via interrupt")
            elif isinstance(payload, bool):
                decided = payload
                reason = "operator decision via interrupt"
            else:
                decided = False
                reason = "operator decision via interrupt (no payload)"
            from datetime import datetime, timezone

            return {
                "approval": {
                    "approved": decided,
                    "level": "require",
                    "reason": reason,
                    "decided_by": "operator:human",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            }
        try:
            decision = gateway.resolve(state_dict)
        except RequiresApprovalError as exc:
            return {
                "approval": {
                    "approved": False,
                    "level": "require",
                    "reason": "approval required but no approver configured",
                    "decided_by": "gateway:blocked",
                    "request": exc.request.to_dict(),
                }
            }
        return {"approval": decision.to_dict()}

    def generate_node(self, state: DeceptionState) -> dict[str, Any]:
        ctx = dict(state.get("context", {}) or {})
        ctx["classification"] = state.get("classification", {})
        ctx["cti_analysis"] = state.get("cti_analysis", {})
        ctx["plan"] = state.get("plan", {})
        ctx["policy_decision"] = state.get("policy_decision", {})
        if self._host_store is not None:
            # Host-fiction identity binding for GENERATION: the deceiver must
            # draft on the machine pinned at first contact — otherwise a
            # reclassified row drafts on a different host while verification
            # (pinned seed) demands the pinned one, forcing fallback serves.
            pinned = self._host_store.pinned_identity
            if pinned:
                ctx["host_identity"] = dict(pinned)
        ctx["approval"] = state.get("approval", {})
        # Retry feedback: on a verification-failure loop the issues from the
        # previous attempt are injected so the generator corrects them.
        feedback = state.get("retry_feedback", "")
        if feedback:
            ctx["feedback"] = feedback
            ctx["retry_attempt"] = max(1, self._max_retries - int(state.get("retries_left", 0) or 0))
        plan = state.get("plan", {}) or {}
        fiction_block = plan.get("fiction_block", "")
        strategy_block = plan.get("strategy_block", "")
        if fiction_block:
            ctx["fiction_block"] = fiction_block
        if strategy_block:
            ctx["strategy_block"] = strategy_block
        if self._deceiver is None:
            return {
                "deception_response": {
                    "response_text": "",
                    "persona_used": "",
                    "error": "no deceiver",
                    "serve_path": SERVE_PATH_FASTPATH,
                }
            }
        out = self._deceiver.generate_response(state["attacker_input"], ctx)
        if not isinstance(out, dict):
            out = {"response_text": str(out), "persona_used": "", "error": ""}
        # Attempted provenance: this node produced an LLM draft. verify_node
        # re-stamps it GENERATED_RETRY / FALLBACK_VERIFIED if the draft was a
        # retry product or was swapped for the fail-safe template. When the
        # DECEIVER had to fall back to a deterministic template (gateway
        # outage, unsafe retry, template anchoring) the serve is labeled
        # TEMPLATE_FALLBACK_VERIFIED — it IS verified (the template is pinned
        # fiction), but it is NOT an LLM draft and must never count as one.
        # The common-command fast-path (RAGIN_FASTPATH_COMMON) is the deliberate
        # sibling of those: same pinned-fiction bytes, chosen instead of a
        # gateway call — so it carries the same never-an-LLM-draft label, with
        # metadata.common_command_fastpath distinguishing choice from outage.
        meta = out.get("metadata")
        if isinstance(meta, dict) and (
            meta.get("gateway_fallback")
            or meta.get("unsafe_retry_fallback")
            or meta.get("template_anchored")
            or meta.get("static_fallback")
            or meta.get("common_command_fastpath")
        ):
            out["serve_path"] = SERVE_PATH_TEMPLATE_FALLBACK
        else:
            out.setdefault("serve_path", SERVE_PATH_GENERATED_VERIFIED)
        policy_decision = state.get("policy_decision")
        if isinstance(policy_decision, dict) and policy_decision:
            policy_decision = dict(policy_decision)
            selected_strategy = policy_decision.get("selected_response_strategy")
            policy_decision["strategy_reached_generator"] = isinstance(selected_strategy, str) and selected_strategy in str(strategy_block)
            generation_material = {
                "attacker_input": state["attacker_input"],
                "strategy_block": strategy_block,
                "policy_decision": policy_decision,
            }
            policy_decision["generation_input_sha256"] = hashlib.sha256(json.dumps(generation_material, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()
        updates = {
            "deception_response": out,
            "fiction": self.fiction(state["session_id"]).to_dict(),
        }
        if policy_decision:
            updates["policy_decision"] = policy_decision
        return updates

    def verify_node(self, state: DeceptionState) -> dict[str, Any]:
        response = state.get("deception_response", {}) or {}
        if not self._verifier or not response:
            return {"verification": {"passed": False, "issues": ["verifier_unconfigured"]}}
        out = self._verifier.verify(
            response,
            {
                "deception_response": response,
                "attacker_input": state["attacker_input"],
                "session_id": state.get("session_id", "unknown"),
                "classification": state.get("classification", {}),
            },
        )
        passed = bool(out.get("passed", False))
        # Provenance contract: a verifier that did NOT perform deterministic
        # checks (a null/pass-through verifier in baseline arms) declares it
        # with "deterministic": False in its result. The served draft is then
        # labeled GENERATED_UNVERIFIED so provenance accounting never mistakes
        # it for a verified serve. Default True preserves existing verifiers.
        if response:
            if out.get("deterministic", True) is False:
                response = dict(response)
                response["serve_path"] = SERVE_PATH_GENERATED_UNVERIFIED
                updates: dict[str, Any] = {"verification": out, "deception_response": response}
                return updates
            if passed and int(state.get("retries_left", self._max_retries) or 0) < self._max_retries:
                # A draft that survived verification on a later attempt: the
                # served bytes are an LLM regeneration, not the first-pass
                # draft. Re-stamp and persist the new label.
                response = dict(response)
                response["serve_path"] = SERVE_PATH_GENERATED_RETRY
                updates = {"verification": out, "deception_response": response}
                return updates
        updates = {"verification": out}
        if not passed:
            retries_left = max(0, int(state.get("retries_left", self._max_retries)) - 1)
            updates["retries_left"] = retries_left
            # Carry the issues back into generate so the retry is targeted.
            issues = out.get("issues") or []
            if issues:
                updates["retry_feedback"] = (
                    "Previous response failed verification: " + "; ".join(issues) + ". Fix these issues."
                )
            # Fail-safe default (C2's promise): when retries are exhausted,
            # a failed response must NEVER reach the attacker. Swap in the
            # deterministic identity-bound template for the same input —
            # it is pinned fiction and passes verification by construction.
            if retries_left == 0:
                skill = (state.get("classification", {}) or {}).get("skill_level", "novice")
                # Host fiction: the fail-safe template must speak for the
                # PINNED machine (generation and verification share one
                # identity source), not the per-skill classification's host.
                fallback_ident = identity_for(skill)
                if self._host_store is not None:
                    fallback_ident = self._host_store.pinned_identity or fallback_ident
                try:
                    from ragin.hisoka.deception import ResponseGenerator

                    fallback = ResponseGenerator()._generate_template(
                        skill,
                        state["attacker_input"],
                        state.get("retry_feedback", ""),
                        fallback_ident,
                    )
                    if fallback:
                        fallback_response = dict(response, response_text=fallback, serve_path=SERVE_PATH_FALLBACK)
                        fallback_verification = self._verifier.verify(
                            fallback_response,
                            {
                                "deception_response": fallback_response,
                                "attacker_input": state["attacker_input"],
                                "session_id": state.get("session_id", "unknown"),
                                "classification": state.get("classification", {}),
                            },
                        )
                        if fallback_verification.get("passed") is True:
                            updates["deception_response"] = fallback_response
                            updates["verification"] = dict(fallback_verification, passed=True, fallback_served=True)
                            updates["retry_feedback"] = ""
                        else:
                            updates["deception_response"] = {"response_text": "", "serve_path": "REJECTED"}
                except Exception:  # noqa: BLE001 — fail-safe must never fail the turn
                    pass
        return updates

    def finalize_node(self, state: DeceptionState) -> dict[str, Any]:
        # Host-fiction bookkeeping: a turn whose final verification PASSED
        # (first-pass, retry, or fail-safe fallback) promotes its stable
        # facts to the host store, binding what the attacker was TOLD to
        # every future session on this host. Failed turns promote nothing.
        if state.get("verification", {}).get("passed", False):
            session_id = str(state.get("session_id", "unknown"))
            graph = self.fiction(session_id, (state.get("classification", {}) or {}).get("skill_level", "novice"))
            staged = graph.clone()
            observed = staged.observe(
                str((state.get("deception_response", {}) or {}).get("response_text", "")), source="accepted"
            )
            if observed.contradictions:
                state = dict(state)
                state["verification"] = {"passed": False, "issues": ["staged_state_conflict"]}
            else:
                graph.replace_from(staged)
                if self._host_store is not None:
                    self._host_store.mark_verified(session_id)
                    self._host_store.promote_verified(session_id)
        result = {
            "session_id": state["session_id"],
            "attacker_input": state["attacker_input"],
            "classification": state.get("classification", {}),
            "cti_analysis": state.get("cti_analysis", {}),
            "deception_response": state.get("deception_response", {}),
            "verification": state.get("verification", {}),
            "approval": state.get("approval", {}),
            "plan": state.get("plan", {}),
            "fiction": state.get("fiction", {}),
        }
        if state.get("policy_decision"):
            result["policy_decision"] = state["policy_decision"]
            result["evidence_bundle_sha256"] = sha256_json(state.get("evidence_bundle", {}))
        return {"result": result}

    # ------------------------------------------------------------------
    # Graph assembly
    # ------------------------------------------------------------------

    def _should_retry(self, state: DeceptionState) -> str:
        verification = state.get("verification", {}) or {}
        if not verification.get("passed", True) and (state.get("retries_left", self._max_retries) or 0) > 0:
            return "retry"
        return "done"

    def build(self) -> Any:
        """Compile (once) the LangGraph state machine.

        The compiled graph and its checkpointer are cached per DeceptionGraph
        so a paused run can be resumed: ``resume()`` must reload the *same*
        checkpoint, which requires the same compiled instance.
        """
        if not HAS_LANGGRAPH:
            return None
        if self._compiled is not None:
            return self._compiled
        builder = StateGraph(DeceptionState)
        builder.add_node("classify", self.classify_node)
        builder.add_node("analyze", self.analyze_node)
        builder.add_node("plan", self.plan_node)
        builder.add_node("approval", self.approval_node)
        builder.add_node("generate", self.generate_node)
        builder.add_node("verify", self.verify_node)
        builder.add_node("finalize", self.finalize_node)

        builder.add_edge(START, "classify")
        builder.add_edge("classify", "analyze")
        builder.add_edge("analyze", "plan")
        builder.add_edge("plan", "approval")
        builder.add_edge("approval", "generate")
        builder.add_edge("generate", "verify")
        builder.add_conditional_edges(
            "verify",
            self._should_retry,
            {"retry": "generate", "done": "finalize"},
        )
        builder.add_edge("finalize", END)
        self._compiled = builder.compile(checkpointer=self._checkpointer or MemorySaver())
        return self._compiled

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def _initial_input(self, session_id: str, attacker_input: str, context: dict[str, Any]) -> dict[str, Any]:
        return {
            "session_id": session_id,
            "attacker_input": attacker_input,
            "context": context,
            "retries_left": self._max_retries,
        }

    def config(self, session_id: str) -> dict[str, Any]:
        return {"configurable": {"thread_id": session_id}}

    def invoke(self, session_id: str, attacker_input: str, context: dict[str, Any]) -> dict[str, Any]:
        """Run one full deception turn (or pause at a HITL gate)."""
        graph = self.build()
        if graph is None:
            return self._run_linear(session_id, attacker_input, context)
        return graph.invoke(self._initial_input(session_id, attacker_input, context), self.config(session_id))

    def resume(self, session_id: str, decided: bool, reason: str = "") -> dict[str, Any]:
        """Resume a paused graph with an operator decision."""
        graph = self.build()
        if graph is None:
            raise RuntimeError("LangGraph required for resume()")
        state = graph.invoke(
            Command(resume={"decided": decided, "reason": reason}),
            self.config(session_id),
        )
        return state.get("result", state)

    def _run_linear(self, session_id: str, attacker_input: str, context: dict[str, Any]) -> dict[str, Any]:
        """Deterministic fallback when LangGraph is unavailable."""
        state: dict[str, Any] = {
            "session_id": session_id,
            "attacker_input": attacker_input,
            "context": context,
            "retries_left": self._max_retries,
        }
        state.update(self.classify_node(state))  # type: ignore[arg-type]
        state.update(self.analyze_node(state))  # type: ignore[arg-type]
        state.update(self.plan_node(state))  # type: ignore[arg-type]
        state.update(self.approval_node(state))  # type: ignore[arg-type]
        state.update(self.generate_node(state))  # type: ignore[arg-type]
        state.update(self.verify_node(state))  # type: ignore[arg-type]
        while self._should_retry(state) == "retry":  # type: ignore[arg-type]
            state.update(self.generate_node(state))  # type: ignore[arg-type]
            state.update(self.verify_node(state))  # type: ignore[arg-type]
        state.update(self.finalize_node(state))  # type: ignore[arg-type]
        return state.get("result", state)


class DeceptionPipeline:
    """Harness-compatible facade over the LangGraph deception pipeline.

    Mirrors ``Harness.process_with_threat_modeling`` output shape so existing
    benchmarks and the human-eval runner can swap it in unmodified.
    """

    def __init__(
        self,
        classifier: Any = None,
        analyzer: Any = None,
        deceiver: Any = None,
        verifier: Any = None,
        approval_gateway: ApprovalGateway | None = None,
        human_in_the_loop: bool = False,
        max_retries: int = 1,
        decision_arm: str | None = None,
    ) -> None:
        from ragin.cycle.adapters import ChrolloAdapter, DonAdapter, HisokaAdapter

        self._classifier = classifier if classifier is not None else ChrolloAdapter(decision_arm=decision_arm)
        self._analyzer = analyzer if analyzer is not None else DonAdapter()
        self._deceiver = deceiver if deceiver is not None else HisokaAdapter()
        self._verifier = verifier
        self._graph = DeceptionGraph(
            classifier=self._classifier,
            analyzer=self._analyzer,
            deceiver=self._deceiver,
            verifier=self._verifier,
            approval_gateway=approval_gateway,
            human_in_the_loop=human_in_the_loop,
            max_retries=max_retries,
            decision_arm=decision_arm,
        )

    def process(self, session: Any, attacker_input: str) -> Any:
        """Process one deception turn and return a PipelineResult-shaped object."""
        from ragin.cycle.harness import PipelineResult

        start = time.monotonic()
        result: dict[str, Any] = {}
        error: str | None = None
        try:
            result = self._graph.invoke(session.session_id, attacker_input, session.build_context())
        except RequiresApprovalError as e:
            error = f"approval-pending: {e.request.action}"
            result = {"approval": {"approved": False, "action": e.request.action}, "deception_response": {}}

        return PipelineResult(
            session_id=session.session_id,
            attacker_input=attacker_input,
            classification=result.get("classification", {}),
            cti_analysis=result.get("cti_analysis", {}),
            deception_response=result.get("deception_response", {}),
            verification=result.get("verification", {}),
            approval=result.get("approval", {}),
            plan=result.get("plan", {}),
            total_time_ms=(time.monotonic() - start) * 1000,
            events_emitted=0,
            error=error or result.get("error"),
        )

    def resume(self, session_id: str, decided: bool, reason: str = "") -> Any:
        from ragin.cycle.harness import PipelineResult

        result = self._graph.resume(session_id, decided, reason)
        return PipelineResult(
            session_id=session_id,
            attacker_input=result.get("attacker_input", ""),
            classification=result.get("classification", {}),
            cti_analysis=result.get("cti_analysis", {}),
            deception_response=result.get("deception_response", {}),
            verification=result.get("verification", {}),
            events_emitted=0,
        )
