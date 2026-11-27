"""Adapters bridging native RAGIN components to harness protocol interfaces.

Each adapter wraps a monolithic component (Chrollo, Don, Hisoka) and exposes
the simplified (attacker_input, context) -> dict interface expected by the
Harness pipeline. This lets us hot-swap components without changing the harness.

Design: adapters are thin — they translate I/O shapes, not business logic.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
from typing import Any

logger = logging.getLogger(__name__)


COMMAND_ENTRY_MAX_CHARS = 4096
EVALUATION_RAW_LOG_MAX_CHARS = 16384


def laya_assessment_mapper(payload: dict[str, Any], session_id: str, attacker_input: str) -> None:
    """Attach the optional Laya laya assessment to a Chrollo classification payload.

    Advisory only: bounded state, timeout → NO_SIGNAL, and never any mutation of
    fiction state or attacker-visible output. The assessment rides along in the
    classification dict so the existing CLASSIFICATION event carries the trace.
    """
    try:
        from ragin.decision.laya_runtime import laya_enabled

        if not laya_enabled():
            return
        from ragin.decision.laya_runtime import get_shared_runtime
        from ragin.decision.optional import LayaAssessmentAdapter

        adapter = LayaAssessmentAdapter(
            get_shared_runtime().infer,
            model="laya/english",
            timeout_s=float(os.environ.get("RAGIN_LAYA_TIMEOUT_S", "30")),
        )
        state = attacker_input if attacker_input else str(payload.get("feature_values", ""))
        r = adapter.assess(session_id=session_id, state=state)
        if r.status == "SIGNAL" and r.assessment is not None:
            d = r.assessment.to_dict()
            d["provider"] = "laya"
            d["status"] = "SIGNAL"
            d["latency_ms"] = round(r.latency_ms, 1)
            payload["laya_assessment"] = d
        else:
            payload["laya_assessment"] = {
                "provider": "laya",
                "status": "NO_SIGNAL",
                "error": r.error,
                "latency_ms": round(r.latency_ms, 1),
            }
    except Exception as exc:  # noqa: BLE001 - advisory signal must not break classify
        payload["laya_assessment"] = {
            "provider": "laya",
            "status": "NO_SIGNAL",
            "error": type(exc).__name__,
        }


def laya_decision_mapper(
    payload: dict[str, Any],
    session_id: str,
    attacker_input: str,
    adapter: Any = None,
) -> None:
    """Attach the V2 real-Laya decision event and its bounded strategy branch."""
    from ragin.decision.laya_runtime import eval_requires_real_model, laya_enabled

    if not laya_enabled():
        return
    try:
        if adapter is None:
            from ragin.decision.laya_decision import LayaDecisionAdapter
            from ragin.decision.laya_runtime import get_shared_runtime

            runtime = get_shared_runtime()
            if eval_requires_real_model():
                runtime.ensure_real_model()
            adapter = LayaDecisionAdapter(
                runtime.infer,
                model=f"laya/{runtime.model}",
                timeout_s=float(os.environ.get("RAGIN_LAYA_TIMEOUT_S", "30")),
                manifest_provider=runtime.manifest,
            )
        event = adapter.decide(session_id=session_id, state=attacker_input or str(payload.get("feature_values", "")))
        payload["laya_decision"] = event
        payload["laya_assessment"] = {
            "provider": "laya",
            "status": "SIGNAL" if event.get("availability") else "NO_SIGNAL",
            "answers": event.get("native_raw_output", {}).get("answers", {}),
            "latency_ms": event.get("latency_ms", 0.0),
            "error": event.get("error"),
        }
    except Exception as exc:  # noqa: BLE001 - non-evaluation mode fails safe
        payload["laya_decision"] = {
            "schema": "ragin.laya_decision_v2.decision_event.v2",
            "session_id": session_id,
            "laya_enabled": True,
            "real_model_verified": False,
            "model": "laya/english",
            "checkpoint": None,
            "model_hash": None,
            "input_sha256": "",
            "native_raw_output": {},
            "normalized_decision": {
                "available": False,
                "is_attack": None,
                "attack_probability": None,
                "stage": None,
                "severity": None,
                "attack_kind": None,
                "confidence": None,
                "provenance": {"provider": "laya", "real_model_verified": False},
                "latency_ms": 0.0,
                "uncertain": True,
            },
            "decision_policy_version": "LAYA_DECISION_POLICY_V2",
            "decision_policy_hash": "UNFROZEN",
            "availability": False,
            "latency_ms": 0.0,
            "error": type(exc).__name__,
            "fallback_reason": type(exc).__name__,
            "selected_workflow_branch": "BASELINE_NO_SIGNAL",
            "selected_response_strategy": "baseline",
            "policy_action": "baseline_fallback",
            "decision_reason": "adapter_initialization_failure",
        }
        payload["laya_assessment"] = {
            "provider": "laya",
            "status": "NO_SIGNAL",
            "error": type(exc).__name__,
        }


class ChrolloAdapter:
    """Wraps ChrolloClassifier to conform to the Classifier protocol.

    Protocol: classify(attacker_input, session_context) -> dict
    Native:   classify(session_log: SessionLog) -> ClassificationResult
    """

    def __init__(self, classifier: Any = None, decision_arm: str | None = None) -> None:
        if classifier is None:
            from ragin.chrollo.classifier import ChrolloClassifier

            classifier = ChrolloClassifier()
        self._classifier = classifier
        self._decision_arm = decision_arm
        self._laya_adapter: Any | None = None
        from ragin.decision_fusion_v4.config import resolve_arm

        if resolve_arm(decision_arm) != "RAGIN_BASELINE":
            return
        try:
            from ragin.decision.laya_runtime import eval_requires_real_model, get_shared_runtime, laya_enabled

            if eval_requires_real_model() and not laya_enabled():
                raise RuntimeError("RAGIN_LAYA_EVAL_REQUIRE_REAL_MODEL=1 requires RAGIN_LAYA_ENABLED=1")
            if laya_enabled():
                from ragin.decision.laya_decision import LayaDecisionAdapter

                runtime = get_shared_runtime()
                if eval_requires_real_model():
                    runtime.ensure_real_model()
                self._laya_adapter = LayaDecisionAdapter(
                    runtime.infer,
                    model=f"laya/{runtime.model}",
                    timeout_s=float(os.environ.get("RAGIN_LAYA_TIMEOUT_S", "30")),
                    manifest_provider=runtime.manifest,
                )
        except Exception as exc:  # noqa: BLE001 - advisory must never block startup
            if os.environ.get("RAGIN_LAYA_EVAL_REQUIRE_REAL_MODEL", "0").strip() == "1":
                raise
            logger.warning("Laya adapter unavailable at startup: %s", exc)

    def classify(self, attacker_input: str, session_context: dict[str, Any]) -> dict[str, Any]:
        from datetime import datetime, timezone

        from ragin.chrollo.models import CommandEntry, SessionLog

        session_id = session_context.get("session_id", "unknown")
        raw_commands = session_context.get("attacker_inputs", [])
        if not raw_commands and attacker_input:
            raw_commands = [attacker_input]

        # Convert string commands to CommandEntry objects
        now = datetime.now(timezone.utc)
        commands = []
        raw_log = ""
        for cmd in raw_commands:
            if isinstance(cmd, dict):
                cmd = cmd.get("command", str(cmd))
            command = str(cmd)
            if len(command) > COMMAND_ENTRY_MAX_CHARS:
                if len(command) > EVALUATION_RAW_LOG_MAX_CHARS:
                    raise ValueError("evaluation payload exceeds raw_log transport limit")
                if raw_log:
                    raise ValueError("multiple long evaluation payloads cannot share one session")
                raw_log = command
                continue
            commands.append(CommandEntry(timestamp=now, command=command))

        session_log = SessionLog(
            session_id=session_id,
            start_time=session_context.get("start_time", now),
            commands=commands,
            raw_log=raw_log,
            metadata=session_context.get("features", {}),
        )

        try:
            result = self._classifier.classify(session_log)
            from ragin.decision_fusion_v4.config import resolve_arm

            error = ""
            payload = {
                "skill_level": result.skill_level.value,
                "confidence": result.confidence,
                "session_id": result.session_id,
                "features_used": result.features_used[:10],
                "feature_values": {k: round(v, 4) for k, v in list(result.feature_values.items())[:20]},
                "error": error,
            }
            if self._laya_adapter is not None and resolve_arm(self._decision_arm) == "RAGIN_BASELINE":
                laya_decision_mapper(payload, session_id, attacker_input, self._laya_adapter)
            return payload
        except Exception as e:
            logger.warning("Chrollo classify failed: %s", e)
            return {
                "skill_level": "novice",
                "confidence": 0.0,
                "session_id": "",
                "features_used": [],
                "feature_values": {},
                "error": str(e),
            }


_EVASION_RULES: list[tuple[str, str]] = [
    ("history_disabled", r"unset\s+(history|histfile)|histfile=/dev/null"),
    ("log_cleared", r"(rm|truncate|>)[\s/]*(var/log|\.(bash|zsh|sh)_history)"),
    ("process_hiding", r"(nohup|disown|setsid)\s+"),
    ("timestamp_smudging", r"touch\s+[-][dt]\s+"),
    ("obfuscation", r"base64\s+[-]d|echo\s+.*\|.*base64|printf.*\\x"),
]
_TOOL_RULES: list[tuple[str, str]] = [
    ("curl", r"\bcurl\s+"),
    ("wget", r"\bwget\s+"),
    ("netcat", r"\b(nc|ncat|socat)\s+"),
    ("nmap", r"\bnmap\s+"),
    ("masscan", r"\bmasscan\s+"),
    ("python", r"\bpython[23]?\s+"),
    ("perl", r"\bperl\s+"),
    ("ruby", r"\bruby\s+"),
    ("ssh_client", r"\b(ssh|scp)\s+"),
    ("git", r"\bgit\s+"),
    ("openssl", r"\bopenssl\s+"),
    ("archive", r"\b(tar|gzip|zip)\s+"),
    ("tmux_screen", r"\b(tmux|screen)\s+"),
    ("ftp_client", r"\b(ftp|sftp)\s+"),
]
_CREDENTIAL_RULES: list[tuple[str, str]] = [
    ("password_file_read", r"/etc/(passwd|shadow)"),
    ("ssh_key_read", r"\.ssh/(id_rsa|authorized_keys|config)"),
    ("user_enumeration", r"\b(whoami|id|users|w|lastlog|last)\b"),
    ("sudo_su", r"\b(sudo|su)\s+"),
    ("history_sniff", r"\bhistory\b"),
    ("db_access", r"\b(mysql|psql|mongo|redis-cli)\s+"),
    ("passwd_change", r"\bpasswd\s+"),
]


def _match_rules(commands: list[str], rules: list[tuple[str, str]]) -> dict[str, list[str]]:
    import re

    result: dict[str, list[str]] = {}
    for cmd in commands:
        cmd_lower = cmd.lower().strip()
        if not cmd_lower:
            continue
        for key, pattern in rules:
            if re.search(pattern, cmd_lower):
                result.setdefault(key, []).append(cmd)
    return result


def _extract_evidence(session_context: dict[str, Any]) -> dict[str, Any]:
    commands: list[str] = []
    raw_inputs = session_context.get("attacker_inputs")
    for inp in raw_inputs if isinstance(raw_inputs, list) else []:
        if isinstance(inp, dict):
            commands.append(str(inp.get("command", inp.get("input", str(inp)))))
        else:
            commands.append(str(inp))
    return {
        "evasion_techniques": _match_rules(commands, _EVASION_RULES),
        "tools_used": _match_rules(commands, _TOOL_RULES),
        "credential_access": _match_rules(commands, _CREDENTIAL_RULES),
    }


class DonAdapter:
    """Wraps ThreatRAGEngine to conform to the CTIEngine protocol.

    Protocol: analyze(attacker_input, session_context) -> dict
    Native:   analyze(classification_result: AnalysisRequest, session_log: list) -> ThreatAnalysis
    """

    def __init__(
        self,
        engine: Any = None,
        gateway_url: str | None = None,
        api_key: str | None = None,
        vector_store_path: str | None = None,
    ) -> None:
        if engine is None:
            from ragin.don.rag_engine import ThreatRAGEngine

            engine = ThreatRAGEngine(
                gateway_url=gateway_url,
                api_key=api_key,
                vector_store_path=vector_store_path,
            )
        self._engine = engine

    def analyze(self, attacker_input: str, session_context: dict[str, Any]) -> dict[str, Any]:
        from ragin.cycle.classification import normalize_classification
        from ragin.decision_fusion_v4.evidence_export import build_evidence_bundle, failure_evidence_bundle
        from ragin.don.models import AnalysisRequest, ClassificationLabel

        # Historical/replayed contexts can carry a non-dict, null, or
        # out-of-vocabulary classification. Normalize before any attribute
        # access so a malformed payload yields "no verdict" instead of
        # raising outside the try block (and never a fabricated skill level).
        classification = normalize_classification(session_context.get("classification"))
        classification_str = classification.get("skill_level", "unknown")
        classification_map = {
            "novice": ClassificationLabel.BENIGN,
            "intermediate": ClassificationLabel.SUSPICIOUS,
            "advanced": ClassificationLabel.MALICIOUS,
            "expert": ClassificationLabel.MALICIOUS,
        }
        classification_label = classification_map.get(classification_str, ClassificationLabel.SUSPICIOUS)
        confidence = float(classification.get("confidence", 0.5))

        raw_session_id = session_context.get("session_id", "unknown")
        # AnalysisRequest.session_id must be alphanumeric (Pydantic validator)
        clean_session_id = "".join(c for c in str(raw_session_id) if c.isalnum())[:128]
        if not clean_session_id:
            clean_session_id = "unknown"

        raw_features = session_context.get("features")
        features = dict(raw_features) if isinstance(raw_features, dict) else {}
        if attacker_input:
            features.setdefault("attacker_input", attacker_input)

        req = AnalysisRequest(
            session_id=clean_session_id,
            classification=classification_label,
            confidence=confidence,
            features=features,
        )

        raw_inputs = session_context.get("attacker_inputs")
        raw_responses = session_context.get("system_responses")
        session_log = []
        for inp in raw_inputs if isinstance(raw_inputs, list) else []:
            session_log.append({"role": "attacker", "content": inp})
        for resp in raw_responses if isinstance(raw_responses, list) else []:
            session_log.append({"role": "system", "content": resp})
        if attacker_input:
            session_log.append({"role": "attacker", "content": attacker_input})

        evidence = _extract_evidence(session_context)
        # Downstream evidence export also indexes classification as a mapping;
        # hand it the normalized dict so a historical string/null payload does
        # not raise after the analysis already succeeded.
        safe_evidence_context = {
            **session_context,
            "classification": classification,
            "features": features,
        }
        provenance = getattr(self._engine, "retrieval_provenance", None)
        if isinstance(provenance, dict):
            safe_evidence_context["retrieval_provenance"] = provenance

        try:
            result = self._engine.analyze(req, session_log)
            error = ""
            payload = {
                "analysis_id": result.analysis_id,
                "severity": result.severity.value,
                "classification": result.classification.value,
                "confidence": result.confidence,
                "sophistication_score": result.sophistication_score,
                "threat_summary": result.summary if hasattr(result, "summary") else "",
                "recommendations": [
                    r if isinstance(r, str) else str(r) for r in getattr(result, "recommendations", [])
                ],
                "tactics": [
                    {"id": t.tactic_id, "name": t.tactic_name, "confidence": t.confidence} for t in result.tactics
                ],
                "candidate_actors": [
                    {
                        "name": a.name,
                        "confidence": a.confidence,
                        "known_ttps": a.known_ttps,
                        "basis": "tactic-heuristic",
                    }
                    for a in result.threat_actors
                ],
                "evasion_techniques": evidence["evasion_techniques"],
                "tools_used": evidence["tools_used"],
                "credential_access": evidence["credential_access"],
                "iocs": [{"type": ioc.type.value, "value": ioc.value} for ioc in result.iocs[:20]],
                "ttps_seen": sorted({tid for t in result.tactics for tid in t.techniques + t.sub_techniques}),
                "extracted_techniques": sorted(
                    {tid for t in result.tactics for tid in t.techniques + t.sub_techniques}
                ),
                # Full actor repertoires are metadata, not observations: a
                # single command has never "used" every technique an actor
                # is KNOWN to use. Listing them in ttps_seen/extracted_techniques
                # made per-turn TTP extraction look wildly noisy (one probe
                # yielding 9-17 techniques) and tanked TTP-accuracy scoring.
                # They stay attached to their actor under candidate_actors.
                "actor_repertoire_ttps": sorted(
                    {tid for a in result.threat_actors for tid in a.known_ttps}
                    - {tid for t in result.tactics for tid in t.techniques + t.sub_techniques}
                ),
                "error": error,
            }
            # The bundle's "chrollo" block describes the CLASSIFIER verdict.
            # This previously received the Don payload (whose "classification"
            # is benign/suspicious/malicious), so skill_level always degraded to
            # "unknown" and the evidence export disagreed with the CTI call.
            payload["evidence_bundle"] = build_evidence_bundle(result, safe_evidence_context, attacker_input)
            return payload
        except Exception as e:
            logger.warning("Don analyze failed: %s", e)
            payload = {
                "analysis_id": "",
                "severity": "unknown",
                "classification": "unknown",
                "confidence": 0.0,
                "sophistication_score": 0.0,
                "threat_summary": "",
                "recommendations": [],
                "tactics": [],
                "candidate_actors": [],
                "evasion_techniques": evidence["evasion_techniques"],
                "tools_used": evidence["tools_used"],
                "credential_access": evidence["credential_access"],
                "iocs": [],
                "ttps_seen": [],
                "extracted_techniques": [],
                "error": str(e),
            }
            failure_context = {**session_context, "classification": payload}
            if isinstance(provenance, dict):
                failure_context["retrieval_provenance"] = provenance
            payload["evidence_bundle"] = failure_evidence_bundle(failure_context, attacker_input, str(e))
            return payload


class HisokaAdapter:
    """Wraps AdaptiveDeceiver to conform to the Deceiver protocol.

    Protocol: generate_response(attacker_input, session_context) -> dict
    Native:   generate_response(attacker_input, session_context) -> DeceptionResponse

    The native API already takes (attacker_input, session_context) but returns
    a DeceptionResponse object. This adapter returns a plain dict.
    """

    def __init__(self, deceiver: Any = None, gateway_url: str | None = None, api_key: str | None = None) -> None:
        if deceiver is None:
            from ragin.hisoka.deceiver import AdaptiveDeceiver

            deceiver = AdaptiveDeceiver(gateway_url=gateway_url, api_key=api_key)
        self._deceiver = deceiver

    def generate_response(self, attacker_input: str, session_context: dict[str, Any]) -> dict[str, Any]:
        try:
            result = self._deceiver.generate_response(attacker_input, session_context)
            error = ""
            meta = result.metadata if isinstance(result.metadata, dict) else {}
            # Provenance: when the generator had to fall back to a template
            # (gateway outage, unsafe retry, template anchoring), translate the
            # generator's marks into the graph's serve-path label so serve-path
            # accounting never counts an outage template as a verified LLM
            # draft. Non-fallback calls carry no marks and are untouched —
            # generate_node's setdefault then stamps GENERATED_VERIFIED.
            extra: dict[str, Any] = {}
            if (
                meta.get("gateway_fallback")
                or meta.get("unsafe_retry_fallback")
                or meta.get("template_anchored")
                or meta.get("static_fallback")
            ):
                from ragin.cycle.graph import SERVE_PATH_TEMPLATE_FALLBACK

                extra["serve_path"] = SERVE_PATH_TEMPLATE_FALLBACK
            return {
                "session_id": result.session_id,
                "response_text": result.response_text,
                "persona_used": result.persona_used,
                "artifacts_injected": result.artifacts_injected,
                "engagement_score": result.engagement_score,
                # The harness propagates this into cti_analysis and the SIEM
                # connectors read it — dropping it here silenced every
                # honeytoken alert at the pipeline boundary.
                "honeytoken_triggered": result.honeytoken_triggered,
                # Same key-parity discipline: JEV fields and protocol markers
                # (imds_protocol, chained_bait, authorization_protocol) live
                # here; shedding them at the boundary blinds downstream
                # consumers the same way the honeytoken drop did.
                "metadata": result.metadata,
                "error": error,
                **extra,
            }
        except Exception as e:
            logger.warning("Hisoka generate_response failed: %s", e)
            return {
                "session_id": "",
                "response_text": "Error generating response.",
                "persona_used": "unknown",
                "artifacts_injected": False,
                "engagement_score": 0.0,
                "error": str(e),
            }


class SubstantiveStrategyAdapter:
    def __init__(self, runtime_mode: str) -> None:
        from ragin.hisoka.deceiver import AdaptiveDeceiver
        from ragin.hisoka.strategy_generator_v1 import StrategyAwareDeceptionGeneratorV1

        self.runtime_mode = runtime_mode
        self._generators: dict[str, StrategyAwareDeceptionGeneratorV1] = {}
        self._pending: dict[str, tuple[StrategyAwareDeceptionGeneratorV1, Any]] = {}
        self._baseline = HisokaAdapter(deceiver=AdaptiveDeceiver(gateway_url=None))

    def _fallback(self, attacker_input: str, context: dict[str, Any], reason: str) -> dict[str, Any]:
        result = self._baseline.generate_response(attacker_input, context)
        raw_metadata = result.get("metadata")
        metadata: dict[str, Any] = dict(raw_metadata) if isinstance(raw_metadata, dict) else {}
        result["metadata"] = metadata
        raw_decision = context.get("policy_decision")
        decision: dict[str, Any] = dict(raw_decision) if isinstance(raw_decision, dict) else {}
        selected = str(decision.get("selected_response_strategy", "baseline"))
        metadata.update(
            {
                "generator_version": "V1_SUBSTANTIVE_STRATEGY_GENERATOR",
                "runtime_mode": self.runtime_mode,
                "selected_strategy": selected,
                "strategy_source": "v4_policy_decision" if decision else "NOT_VERIFIABLE",
                "gate_state": decision.get("gate_state", "NOT_VERIFIABLE"),
                "strategy_delivered_to_generator": False,
                "strategy_consumed_by_template": False,
                "actual_generator_invocation": False,
                "strategy_runtime_fallback": reason,
                "serving_outcome": "GENERATION_NOT_APPLICABLE" if selected == "baseline" else "SAFE_FALLBACK_SERVED",
                "served_path": "SAFE_BASELINE_FALLBACK",
            }
        )
        return result

    def generate_response(self, attacker_input: str, session_context: dict[str, Any]) -> dict[str, Any]:
        decision = session_context.get("policy_decision")
        if not isinstance(decision, dict):
            return self._fallback(attacker_input, session_context, "missing_policy_decision")
        if decision.get("gate_state") != "VALID_EVIDENCE":
            return self._fallback(attacker_input, session_context, "invalid_evidence_gate")
        strategy = decision.get("selected_response_strategy")
        if strategy == "baseline":
            return self._fallback(attacker_input, session_context, "baseline_policy_fallback")
        from ragin.decision_fusion_v4.benchmark import ALLOWED_STRATEGIES

        if strategy not in ALLOWED_STRATEGIES:
            return self._fallback(attacker_input, session_context, "unsupported_strategy")
        from ragin.hisoka.strategy_generator_v1 import StrategyAwareDeceptionGeneratorV1

        session_id = str(session_context.get("session_id", "unknown"))
        generator = self._generators.setdefault(session_id, StrategyAwareDeceptionGeneratorV1(session_id, seed=0))
        candidate = generator.generate(
            attacker_input,
            str(strategy),
            skill_level=str((session_context.get("classification") or {}).get("skill_level", "novice")),
            identity=session_context.get("host_identity"),
        )
        response_text = candidate.response_text
        identity = session_context.get("host_identity") or {}
        if identity:
            prompt = f"{identity.get('user', 'webapp')}@{identity.get('host', 'web-srv-01')}:~$"
            response_text = re.sub(r"webapp@fiction-\d{4}:~\$", prompt, response_text, count=1)
        response_text = response_text.replace("service_account=decoy_user", "principal=svc_audit")
        response_text = re.sub(r"credential_id=decoy-svc-(\d{4})", r"access_ref=svc-ref-\1", response_text)
        response_text = re.sub(r"instrumentation_id=honeytoken-(\d{4})", r"trace_ref=ht-\1", response_text)
        candidate_id = hashlib.sha256(
            f"{session_id}:{generator.state.visits}:{strategy}:{candidate.action}:{response_text}".encode()
        ).hexdigest()[:24]
        self._pending[candidate_id] = (generator, candidate)
        candidate_hash = hashlib.sha256(response_text.encode()).hexdigest()
        return {
            "session_id": session_id,
            "response_text": response_text,
            "persona_used": str((session_context.get("classification") or {}).get("skill_level", "novice")),
            "engagement_score": 0.0,
            "serve_path": "SUBSTANTIVE_TEMPLATE_VERIFIED",
            "metadata": {
                "generator_version": "V1_SUBSTANTIVE_STRATEGY_GENERATOR",
                "runtime_mode": self.runtime_mode,
                "selected_strategy": strategy,
                "strategy_source": "v4_policy_decision",
                "gate_state": decision.get("gate_state"),
                "evidence_ids": list(decision.get("supporting_evidence_refs", [])),
                "strategy_delivered_to_generator": True,
                "strategy_consumed_by_template": True,
                "actual_generator_invocation": True,
                "candidate_response_sha256": candidate_hash,
                "serving_outcome": "STRATEGY_CONSUMED_AND_SERVED",
                "action_selected": candidate.action,
                "fictional_state_before_hash": hashlib.sha256(repr(generator.state).encode()).hexdigest(),
                "fictional_state_proposed_hash": hashlib.sha256(repr(candidate.proposed_state).encode()).hexdigest(),
                "strategy_candidate_id": candidate_id,
                "instrumentation": candidate.instrumentation,
            },
            "error": "",
        }

    def commit_candidate(self, candidate: dict[str, Any], *, verifier_passed: bool, hitl_approved: bool) -> dict[str, Any]:
        metadata = candidate.get("metadata") if isinstance(candidate, dict) else None
        candidate_id = metadata.get("strategy_candidate_id") if isinstance(metadata, dict) else None
        pending = self._pending.pop(str(candidate_id), None) if candidate_id else None
        if pending is None:
            return {"committed": False, "reason": "candidate_not_pending"}
        generator, proposal = pending
        return generator.commit(proposal, verifier_passed=verifier_passed, hitl_approved=hitl_approved)


# ── WS1 active wiring: provider transport seam ────────────────────────────────
# ProviderTransport is a GatewayClient subclass, so it is a direct drop-in for the
# existing generator seam. The ACTIVE generator path is unchanged:
#   server_v2 → Harness → HisokaAdapter → AdaptiveDeceiver → ResponseGenerator → GatewayClient.
#
# The provider backend is selected through configuration only:
#   * RAGIN_PROVIDER_URL / RAGIN_HISOKA_GATEWAY_URL / GATEWAY_URL for the URL
#   * RAGIN_PROVIDER_API_KEY / RAGIN_HISOKA_API_KEY / ... for auth
# When a non-placeholder key is present, ProviderTransport delegates to the existing
# authenticated GatewayClient behavior. When none is configured it fails closed on
# generate() with ProviderUnavailableError.
#
# No parallel inference pipeline is added. No public listener is introduced. The
# only bindable bridge in this repo remains the existing loopback-only OpenCode CLI
# proxy (scripts/opencode_proxy.py). The mandatory FictionConsistencyVerifier,
# fallback labeling, HITL policy, and accepted-state-only commit rules are untouched.
from ragin.cycle.provider_transport import ProviderTransport  # noqa: E402, F401
