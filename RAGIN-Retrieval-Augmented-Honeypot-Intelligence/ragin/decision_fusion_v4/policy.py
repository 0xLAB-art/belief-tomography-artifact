from __future__ import annotations

import hashlib
import json
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Callable, Mapping

import joblib

from .benchmark import ALLOWED_STRATEGIES, EvidenceQualityGate, deterministic_policy, extract_features
from .evidence_export import canonical_json, freeze_bundle, sha256_json, thaw

POLICY_SCHEMA = "ragin.decision_fusion_v4.policy_decision.v1"
DETERMINISTIC_RULE_TABLE = ("credential_access", "persistence", "reconnaissance", "exploitation", "data_access", "benign_administration", "baseline_fallback")
DETERMINISTIC_RULE_TABLE_VERSION = "deterministic_v1"
DETERMINISTIC_RULE_TABLE_HASH = hashlib.sha256(json.dumps(DETERMINISTIC_RULE_TABLE, separators=(",", ":")).encode()).hexdigest()
LOGISTIC_MODEL_RELATIVE = "results/decision_fusion_v4/v4_selected_logistic_policy.joblib"
LOGISTIC_MODEL_SHA256 = "4056337ad6a41132a73a89fc0ef3b18cf41b10086bb0f25f7e6fc953bbd0a6a8"
LOGISTIC_FEATURE_MAP = ("chrollo_confidence", "chrollo_skill=advanced", "chrollo_skill=novice", "coverage_complete", "don_classification=benign", "don_classification=malicious", "don_severity=high", "don_severity=info", "ioc_count", "relevant_count", "retrieved_count", "tactic_TA0001", "tactic_TA0003", "tactic_TA0006", "tactic_TA0009", "tactic_TA0043", "ttp_T1003", "ttp_T1005", "ttp_T1046", "ttp_T1053.003", "ttp_T1190", "vetted_document_count")
LOGISTIC_FEATURE_MAP_HASH = hashlib.sha256(json.dumps(LOGISTIC_FEATURE_MAP, separators=(",", ":")).encode()).hexdigest()
LOGISTIC_PREPROCESSING_HASH = hashlib.sha256(b"DictVectorizer(sparse=False)").hexdigest()


def _safe_input_digest(value: Any) -> str:
    """SHA-256 over the canonical JSON of ``value`` that never raises.

    Bundles reach this module from caller-controlled state; a value that is
    not JSON-serialisable (e.g. a ``set``) must degrade to a stable
    placeholder digest instead of breaking the baseline contract.
    """
    try:
        return sha256_json(value)
    except (TypeError, ValueError):
        return hashlib.sha256(b"ragin.decision_fusion_v4.unserializable_input").hexdigest()


class PolicySelector(ABC):
    policy_engine_id = "abstract"
    policy_version = "V4_POLICY_V1"

    def __init__(self, gate: EvidenceQualityGate | None = None) -> None:
        self.gate = gate or EvidenceQualityGate()

    def select(self, evidence_bundle: Mapping[str, Any]) -> dict[str, Any]:
        started = time.perf_counter_ns()
        try:
            frozen = freeze_bundle(evidence_bundle)
            gate_result = self.gate.evaluate(frozen)
            evidence_hash = _safe_input_digest(frozen)
        except Exception as exc:
            # The freeze/hash/gate step runs OUTSIDE the per-arm try below by
            # design (a bundle that cannot be serialised is not an arm
            # failure). It must still honour the same contract: a bundle whose
            # content is not JSON-serialisable (e.g. a set value) yields a
            # baseline decision, never an uncaught TypeError.
            gate_result = {
                "gate_state": "EVALUATION_ERROR",
                "reason_code": "bundle_freeze_failed",
                "valid_doc_ids": [],
            }
            return self._decision(evidence_bundle, gate_result, "baseline", [], "gate_not_valid", started, "", type(exc).__name__)
        if gate_result["gate_state"] != "VALID_EVIDENCE":
            return self._decision(frozen, gate_result, "baseline", [], "gate_not_valid", started, evidence_hash, "evidence_gate_fallback")
        try:
            decision = self._select_valid(frozen, gate_result["valid_doc_ids"])
            return self._validate(decision, frozen, gate_result, started, evidence_hash)
        except Exception as exc:
            return self._decision(frozen, gate_result, "baseline", [], "policy_exception", started, evidence_hash, type(exc).__name__)

    def fallback_decision(self, evidence_bundle: Mapping[str, Any], gate_result: dict[str, Any]) -> dict[str, Any]:
        started = time.perf_counter_ns()
        frozen = freeze_bundle(evidence_bundle)
        return self._decision(frozen, gate_result, "baseline", [], "gate_not_valid", started, _safe_input_digest(frozen), "evidence_gate_fallback")

    @abstractmethod
    def _select_valid(self, evidence_bundle: Mapping[str, Any], valid_doc_ids: list[str]) -> dict[str, Any]:
        raise NotImplementedError

    def _validate(self, decision: dict[str, Any], bundle: Mapping[str, Any], gate_result: dict[str, Any], started: int, evidence_hash: str) -> dict[str, Any]:
        strategy = decision.get("selected_response_strategy")
        refs = decision.get("supporting_evidence_refs")
        valid_refs = set(gate_result["valid_doc_ids"])
        if strategy not in ALLOWED_STRATEGIES:
            return self._decision(bundle, gate_result, "baseline", [], "unsupported_strategy", started, evidence_hash, "unsupported_strategy")
        if not isinstance(refs, list) or not set(refs).issubset(valid_refs):
            return self._decision(bundle, gate_result, "baseline", [], "invalid_evidence_reference", started, evidence_hash, "invalid_evidence_reference")
        return self._decision(bundle, gate_result, strategy, refs, str(decision.get("policy_reason_code", "selected")), started, evidence_hash, "")

    def _decision(self, bundle: Mapping[str, Any], gate_result: dict[str, Any], strategy: str, refs: list[str], reason: str, started: int, evidence_hash: str, fallback_reason: str) -> dict[str, Any]:
        latency = (time.perf_counter_ns() - started) / 1_000_000
        policy_input = evidence_hash or _safe_input_digest(bundle)
        return {
            "schema": POLICY_SCHEMA,
            "policy_engine_id": self.policy_engine_id if not fallback_reason else "caller_fallback",
            "policy_version": self.policy_version,
            "policy_hash": self.policy_hash,
            "selected_response_strategy": strategy if strategy in ALLOWED_STRATEGIES else "baseline",
            "supporting_evidence_refs": list(refs),
            "policy_reason_code": reason,
            "input_digest": policy_input,
            "policy_input_sha256": policy_input,
            "evidence_bundle_sha256": evidence_hash,
            "gate_state": gate_result.get("gate_state"),
            "gate_reason": gate_result.get("reason_code"),
            "valid_doc_ids": list(gate_result.get("valid_doc_ids", [])),
            "latency_ms": latency,
            "policy_latency_ms": latency,
            "fallback_reason": fallback_reason or None,
            "model_hash": getattr(self, "model_hash", None),
            "feature_map_hash": getattr(self, "feature_map_hash", None),
            "preprocessing_hash": getattr(self, "preprocessing_hash", None),
        }

    @property
    def policy_hash(self) -> str:
        return hashlib.sha256(f"{self.policy_engine_id}:{self.policy_version}".encode()).hexdigest()


class BaselinePolicySelector(PolicySelector):
    policy_engine_id = "baseline_policy"
    policy_version = "BASELINE_POLICY_V1"

    def _select_valid(self, evidence_bundle: Mapping[str, Any], valid_doc_ids: list[str]) -> dict[str, Any]:
        return {"selected_response_strategy": "baseline", "supporting_evidence_refs": [], "policy_reason_code": "baseline_arm"}


class DeterministicPolicySelector(PolicySelector):
    policy_engine_id = "deterministic_policy_v1"
    policy_version = DETERMINISTIC_RULE_TABLE_VERSION

    @property
    def policy_hash(self) -> str:
        return DETERMINISTIC_RULE_TABLE_HASH

    def _select_valid(self, evidence_bundle: Mapping[str, Any], valid_doc_ids: list[str]) -> dict[str, Any]:
        decision = deterministic_policy(thaw(evidence_bundle), valid_doc_ids)
        decision["policy_reason_code"] = f"{DETERMINISTIC_RULE_TABLE_VERSION}:{decision['policy_reason_code']}"
        return decision


class LogisticPolicySelector(PolicySelector):
    policy_engine_id = "logistic_policy_v4"
    policy_version = "logistic_regression_v1"
    model_hash = LOGISTIC_MODEL_SHA256
    feature_map_hash = LOGISTIC_FEATURE_MAP_HASH
    preprocessing_hash = LOGISTIC_PREPROCESSING_HASH

    def __init__(self, model_path: str | Path | None = None, gate: EvidenceQualityGate | None = None) -> None:
        super().__init__(gate)
        root = Path(__file__).resolve().parents[2]
        path = Path(model_path) if model_path else root / LOGISTIC_MODEL_RELATIVE
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != self.model_hash:
            raise RuntimeError("logistic model hash mismatch")
        artifact = joblib.load(path)
        self.vectorizer = artifact["vectorizer"]
        self.model = artifact["model"]
        if tuple(self.vectorizer.feature_names_) != LOGISTIC_FEATURE_MAP:
            raise RuntimeError("logistic feature-map mismatch")

    def _select_valid(self, evidence_bundle: Mapping[str, Any], valid_doc_ids: list[str]) -> dict[str, Any]:
        features = extract_features(thaw(evidence_bundle), valid_doc_ids)
        matrix = self.vectorizer.transform([features])
        strategy = str(self.model.predict(matrix)[0])
        return {"selected_response_strategy": strategy, "supporting_evidence_refs": list(valid_doc_ids[:1]), "policy_reason_code": "logistic_structured_features"}


def build_selector(arm: str) -> PolicySelector:
    if arm == "RAGIN_V4_LOGISTIC":
        return LogisticPolicySelector()
    if arm == "RAGIN_V4_DETERMINISTIC":
        return DeterministicPolicySelector()
    return BaselinePolicySelector()
