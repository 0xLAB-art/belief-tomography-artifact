"""Provider-neutral Laya decision contract and fail-safe V2 policy.

This module is deliberately narrower than the old optional assessment adapter:
it normalizes one real Laya decision and selects only response-strategy context.
It has no access to fiction state, authorization, HITL, serving, or commit APIs.
"""

from __future__ import annotations

import hashlib
import math
import os
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from ragin.decision.bounded_worker import shared_infer_worker
from ragin.decision.state_bounds import TRUNCATION_POLICY, bound_state

POLICY_VERSION = "LAYA_DECISION_POLICY_V2"
# Updated to the canonical preregistration artifact hash before the freeze.
POLICY_HASH = "95b29d203cf2e149ec4d0dc8ff740f4525b245d04ad575de476361e4854ec8e9"
BASELINE_STRATEGY = "baseline"

_STAGE_TO_KIND = {
    "recon": "scanning",
    "persistence": "persistence",
    "credential_theft": "bruteforce",
    "lateral_movement": "lateral",
    "exfiltration": "exfiltration",
    "cleanup": "cleanup",
}
_STAGE_TO_STRATEGY = {
    "recon": "maximize_recon_surface",
    "persistence": "fake_success_and_return_visits",
    "credential_theft": "steer_to_honeytoken_credentials",
    "lateral_movement": "expose_decoy_internal_topology",
    "exfiltration": "contain_in_fiction_and_instrument",
    "cleanup": "contain_in_fiction_and_instrument",
}
_DOCUMENTED_STAGES = frozenset(
    {"benign_administration", "recon", "persistence", "credential_theft", "lateral_movement", "exfiltration", "cleanup"}
)


def _finite_number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    return value if math.isfinite(value) else None


def _bounded_number(value: Any, maximum: float = 1.0) -> float | None:
    number = _finite_number(value)
    return number if number is not None and 0.0 <= number <= maximum else None


def _native_answers(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    native = payload.get("native_output")
    if isinstance(native, Mapping) and isinstance(native.get("answers"), Mapping):
        return native["answers"]
    answers = payload.get("answers")
    return answers if isinstance(answers, Mapping) else {}


@dataclass(frozen=True)
class LayaDecisionSignal:
    available: bool
    is_attack: bool | None
    attack_probability: float | None
    stage: str | None
    severity: float | None
    attack_kind: str | None
    confidence: float | None
    provenance: dict[str, Any] = field(default_factory=dict)
    latency_ms: float = 0.0
    uncertain: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "is_attack": self.is_attack,
            "attack_probability": self.attack_probability,
            "stage": self.stage,
            "severity": self.severity,
            "attack_kind": self.attack_kind,
            "confidence": self.confidence,
            "provenance": dict(self.provenance),
            "latency_ms": self.latency_ms,
            "uncertain": self.uncertain,
        }


def normalize_laya_payload(
    payload: Mapping[str, Any],
    *,
    provenance: Mapping[str, Any] | None = None,
    latency_ms: float = 0.0,
) -> LayaDecisionSignal:
    """Normalize native Laya output without inventing probabilities."""

    answers = _native_answers(payload)
    attack = answers.get("attack")
    stage_answer = answers.get("stage")
    severity_answer = answers.get("severity")
    if not isinstance(attack, Mapping):
        return LayaDecisionSignal(
            available=False,
            is_attack=None,
            attack_probability=None,
            stage=None,
            severity=None,
            attack_kind=None,
            confidence=None,
            provenance=dict(provenance or {}),
            latency_ms=latency_ms,
            uncertain=True,
        )

    attack_probability = _bounded_number(attack.get("noul"))
    stage = stage_answer.get("choice") if isinstance(stage_answer, Mapping) else None
    stage = stage if isinstance(stage, str) and stage in _DOCUMENTED_STAGES else None
    severity = _bounded_number(severity_answer.get("score"), 3.0) if isinstance(severity_answer, Mapping) else None
    confidence = _bounded_number(attack.get("answer_confidence"))
    if confidence is None:
        confidence = _bounded_number(attack.get("confidence"))
    abstained = bool(attack.get("low_confidence")) or attack.get("abstention") == "abstained"
    is_attack = None if attack_probability is None or abstained else attack_probability >= 0.5
    return LayaDecisionSignal(
        available=is_attack is not None,
        is_attack=is_attack,
        attack_probability=attack_probability,
        stage=stage,
        severity=severity,
        attack_kind=_STAGE_TO_KIND.get(stage) if stage else None,
        confidence=confidence,
        provenance=dict(provenance or {}),
        latency_ms=latency_ms,
        uncertain=is_attack is None,
    )


class LayaDecisionPolicy:
    """Exact preregistered response-strategy policy."""

    def evaluate(self, signal: LayaDecisionSignal, *, error: str | None = None) -> dict[str, Any]:
        if not signal.available or signal.uncertain:
            reason = error or "uncertain_or_no_signal"
            return {
                "selected_workflow_branch": "BASELINE_NO_SIGNAL",
                "selected_response_strategy": BASELINE_STRATEGY,
                "policy_action": "baseline_fallback",
                "decision_reason": reason,
            }
        if signal.is_attack is False:
            return {
                "selected_workflow_branch": "LAYA_NON_ATTACK_STRATEGY",
                "selected_response_strategy": "low_intensity_administration",
                "policy_action": "use_laya_non_attack_strategy",
                "decision_reason": "native_non_attack_decision",
            }
        # Truthiness, matching the decision_reason below: a missing/empty stage
        # resolves to the same default dict.get(None/"") would have returned.
        strategy = (
            _STAGE_TO_STRATEGY.get(signal.stage, "contain_in_fiction_and_instrument")
            if signal.stage
            else "contain_in_fiction_and_instrument"
        )
        return {
            "selected_workflow_branch": "LAYA_ATTACK_STRATEGY",
            "selected_response_strategy": strategy,
            "policy_action": "use_laya_attack_strategy",
            "decision_reason": "native_attack_decision_with_stage" if signal.stage else "attack_missing_stage",
        }


class LayaDecisionAdapter:
    """Bounded adapter from the real runtime to a decision event."""

    def __init__(
        self,
        infer: Callable[[str], Mapping[str, Any]],
        *,
        model: str,
        timeout_s: float = 30.0,
        max_state_chars: int = 8000,
        manifest_provider: Callable[[], Mapping[str, Any]] | None = None,
    ) -> None:
        if timeout_s <= 0 or max_state_chars <= 0:
            raise ValueError("timeout_s and max_state_chars must be positive")
        self._infer = infer
        self._model = model
        self._timeout_s = timeout_s
        self._max_state_chars = max_state_chars
        self._manifest_provider = manifest_provider
        self._policy = LayaDecisionPolicy()
        if os.environ.get("RAGIN_LAYA_EVAL_REQUIRE_REAL_MODEL", "0").strip() == "1":
            if manifest_provider is None:
                raise RuntimeError("evaluation mode rejects adapters without a real-model manifest")
            manifest = dict(manifest_provider())
            if not manifest.get("runtime_verified") or not manifest.get("checkpoint_verified"):
                raise RuntimeError("evaluation mode requires an initialized, checkpoint-verified real Laya model")

    def _manifest(self) -> dict[str, Any]:
        if self._manifest_provider is None:
            return {}
        try:
            return dict(self._manifest_provider())
        except Exception as exc:  # pragma: no cover - provenance must not break fallback
            return {"manifest_error": type(exc).__name__}

    def decide(self, *, session_id: str, state: str) -> dict[str, Any]:
        started = time.monotonic()
        # Provenance names both digests: the source state and the exact bounded
        # text handed to the provider, plus the truncation that separated them.
        source_state_sha256 = hashlib.sha256(state.encode("utf-8")).hexdigest()
        bounded_state, truncated = bound_state(state, self._max_state_chars)
        effective_input_sha256 = hashlib.sha256(bounded_state.encode("utf-8")).hexdigest()
        input_sha256 = source_state_sha256
        payload: Mapping[str, Any] = {}
        error: str | None = None
        # Bounded admission: a shared worker with an explicit busy outcome
        # instead of a per-request executor whose timed-out callables pile up.
        status, result = shared_infer_worker().run(self._infer, bounded_state, self._timeout_s)
        if status == "timeout":
            error = "timeout"
        elif status == "busy":
            error = "busy"
        elif status == "error":
            error = type(result).__name__
        elif not isinstance(result, Mapping):
            error = "TypeError"
        else:
            payload = result

        latency_ms = (time.monotonic() - started) * 1000
        manifest = self._manifest()
        provenance = {
            "provider": "laya",
            "model": self._model,
            "package_version": manifest.get("package_version"),
            "repository": manifest.get("source_repository") or manifest.get("repository"),
            "checkpoint": manifest.get("checkpoint"),
            "revision": manifest.get("revision"),
            "model_hash": manifest.get("model_hash"),
            "input_sha256": source_state_sha256,
            "source_state_sha256": source_state_sha256,
            "effective_input_sha256": effective_input_sha256,
            "source_state_chars": len(state),
            "effective_input_chars": len(bounded_state),
            "input_truncated": truncated,
            "truncation_policy": TRUNCATION_POLICY,
            "native_schema": "laya.Router.predict",
            "real_model_verified": bool(manifest.get("runtime_verified") and manifest.get("checkpoint_verified")),
        }
        signal = normalize_laya_payload(payload, provenance=provenance, latency_ms=latency_ms)
        action = self._policy.evaluate(signal, error=error)
        native_raw = payload.get("native_output", payload)
        if not isinstance(native_raw, Mapping):
            native_raw = {}
        return {
            "schema": "ragin.laya_decision_v2.decision_event.v2",
            "session_id": session_id,
            "laya_enabled": True,
            "real_model_verified": provenance["real_model_verified"],
            "model": self._model,
            "checkpoint": provenance["checkpoint"],
            "model_hash": provenance["model_hash"],
            "input_sha256": input_sha256,
            "source_state_sha256": source_state_sha256,
            "effective_input_sha256": effective_input_sha256,
            "input_truncated": truncated,
            "native_raw_output": dict(native_raw),
            "normalized_decision": signal.to_dict(),
            "decision_policy_version": POLICY_VERSION,
            "decision_policy_hash": POLICY_HASH,
            "availability": signal.available,
            "latency_ms": round(latency_ms, 3),
            "error": error,
            "fallback_reason": error if error else ("low_confidence_or_malformed" if signal.uncertain else None),
            **action,
        }
