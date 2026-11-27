from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Mapping, Sequence
from types import MappingProxyType
from typing import Any

from ragin.don.evidence_judge import DeterministicEvidenceJudge, filter_judged_evidence, judge_bundle

from .benchmark import EvidenceQualityGate

_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "how", "in", "into",
    "is", "it", "of", "on", "or", "that", "the", "to", "via", "what", "when", "where",
    "which", "with",
}


def _query(session_context: Mapping[str, Any], attacker_input: str) -> str:
    classification = session_context.get("classification", {}) or {}
    features = session_context.get("features", {}) or {}
    parts = [str(classification.get("skill_level", "unknown"))]
    parts.extend(str(item) for item in features.get("observed_techniques", []))
    parts.extend(str(item) for item in features.get("commands", [])[:5])
    if attacker_input:
        parts.append(attacker_input)
    return " ".join(part for part in parts if part).strip()


def _coverage(query: str, documents: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    terms = [term for term in query.lower().split() if len(term) > 2 and term not in _STOPWORDS]
    text = " ".join(f"{doc.get('title', '')} {doc.get('content', '')}".lower() for doc in documents)
    covered = [term for term in terms if term in text]
    return {
        "complete": bool(documents) and (not terms or bool(covered)),
        "covered_terms": covered,
        "required_terms": terms,
    }


def _doc_dump(document: Any) -> dict[str, Any]:
    values = document.model_dump() if hasattr(document, "model_dump") else dict(document)
    entry = {
        "doc_id": str(values.get("doc_id", "")),
        "title": str(values.get("title", "")),
        "content": str(values.get("content", "")),
        "source": str(values.get("source", "")),
        "provenance_status": "VALID" if values.get("doc_id") and values.get("source") else "UNKNOWN",
        "sanitization_status": "SANITIZED" if values.get("content") is not None else "UNKNOWN",
        "conflict_status": "NONE",
    }
    if values.get("score") is not None:
        entry["score"] = values["score"]
        entry["relevance_grade"] = values["score"]
    if values.get("metadata"):
        entry.update(dict(values["metadata"]))
    return entry


def build_evidence_bundle(
    analysis: Any,
    session_context: Mapping[str, Any],
    attacker_input: str,
    error: str = "",
    evidence_judge: DeterministicEvidenceJudge | None = None,
    evidence_judge_filtering: bool | None = None,
) -> dict[str, Any]:
    documents = [_doc_dump(document) for document in getattr(analysis, "intel_documents", [])]
    raw_features = getattr(analysis, "raw_features", {}) or {}
    v2 = raw_features.get("command_aware_v2", {}) if isinstance(raw_features, Mapping) else {}
    trace = v2.get("retrieval_trace", {}) if isinstance(v2, Mapping) else {}
    query = str(trace.get("query") or _query(session_context, attacker_input))
    provenance_raw = session_context.get("retrieval_provenance")
    provenance = provenance_raw if isinstance(provenance_raw, Mapping) else {}
    backend = str(provenance.get("effective_backend") or ("command_aware_v2" if trace else "unrecorded"))
    requested_mode = str(provenance.get("requested_mode") or ("command_aware_v2" if trace else "unrecorded"))
    configured_mode = str(provenance.get("configured_mode") or requested_mode)
    if error:
        retrieval_status = "FAILURE"
    elif backend == "none":
        # "DISABLED" means the caller intentionally requested ``none``. An
        # empty configured hybrid (or a configured dense/bm25 arm with no
        # data) is unavailable/empty, not an intentional disable.
        retrieval_status = "DISABLED" if {"none"} & {requested_mode, configured_mode} else "EMPTY"
    else:
        retrieval_status = "SUCCESS"
    doc_ids = [document["doc_id"] for document in documents if document["doc_id"]]
    bundle = {
        "schema": "ragin.don.evidence_bundle.v4",
        "session": {"session_id": str(session_context.get("session_id", "unknown")), "current_input": attacker_input},
        "chrollo": {
            "skill_level": (session_context.get("classification", {}) or {}).get("skill_level", "unknown"),
            "confidence": float((session_context.get("classification", {}) or {}).get("confidence", 0.0)),
            "features_used": list((session_context.get("classification", {}) or {}).get("features_used", [])),
            "feature_values": dict((session_context.get("classification", {}) or {}).get("feature_values", {})),
        },
        "don_analysis": {
            "classification": getattr(getattr(analysis, "classification", None), "value", "unknown"),
            "severity": getattr(getattr(analysis, "severity", None), "value", "unknown"),
            "confidence": float(getattr(analysis, "confidence", 0.0)),
            "tactics": [
                item.model_dump() if hasattr(item, "model_dump") else dict(item)
                for item in getattr(analysis, "tactics", [])
            ],
            "ttps_seen": sorted(
                {
                    technique
                    for tactic in getattr(analysis, "tactics", [])
                    for technique in tactic.techniques + tactic.sub_techniques
                }
            ),
            "iocs": [
                item.model_dump() if hasattr(item, "model_dump") else dict(item)
                for item in getattr(analysis, "iocs", [])
            ],
        },
        "retrieval": {
            "retrieval_status": retrieval_status,
            "backend": backend,
            "backend_source": str(provenance.get("backend_source") or ("TRACE" if trace else "UNRECORDED")),
            "mode": requested_mode,
            "configured_mode": configured_mode,
            "sparse_documents": provenance.get("sparse_documents"),
            "dense_documents": provenance.get("dense_documents"),
            "implementation_version": v2.get("implementation_version") if trace else None,
            "query": query,
            "sub_queries": [query] if query else [],
            "retrieved_count": len(documents),
            "relevant_count": len(doc_ids),
            "relevant_doc_ids": doc_ids,
            "query_coverage": trace.get("query_coverage", _coverage(query, documents)),
            "documents": documents,
            "trace_summary": {
                "rounds": 0,
                "degraded": False,
                "usable_successful_retrieval": (not error) and backend not in {"none", "unrecorded"},
                "retrieval_error_code": error or None,
                "context_projection": trace.get("context_projection") if trace else None,
                "top_k": trace.get("top_k") if trace else None,
                "corpus_sha256": trace.get("corpus_sha256") if trace else None,
                "cache_key": trace.get("cache_key") if trace else None,
            },
        },
    }
    judge_enabled = os.environ.get("RAGIN_EVIDENCE_JUDGE_ENABLED", "0").strip().lower() in {
        "1", "true", "yes", "on",
    }
    filtering_enabled = (
        evidence_judge_filtering
        if evidence_judge_filtering is not None
        else os.environ.get("RAGIN_EVIDENCE_JUDGE_FILTERING_ENABLED", "0").strip().lower()
        in {"1", "true", "yes", "on"}
    )
    if evidence_judge is not None or judge_enabled or filtering_enabled:
        preceding = (
            trace.get("context_projection", {}).get("preceding_commands", [])
            if isinstance(trace, Mapping)
            else []
        )
        bundle["evidence_judge"] = judge_bundle(
            attacker_input,
            documents,
            preceding_commands=preceding if isinstance(preceding, list) else [],
            judge=evidence_judge,
        )
        if filtering_enabled:
            filtering = filter_judged_evidence(bundle["retrieval"], bundle["evidence_judge"])
            bundle["evidence_judge_filter"] = filtering
            bundle["retrieval"]["relevant_doc_ids"] = filtering["filtered_relevant_doc_ids"]
            bundle["retrieval"]["relevant_count"] = len(filtering["filtered_relevant_doc_ids"])
    gate_result = EvidenceQualityGate().evaluate(bundle)
    bundle["evidence_gate_preview"] = {
        "gate_state": gate_result["gate_state"],
        "reason_code": gate_result["reason_code"],
        "contract_version": gate_result["contract_version"],
    }
    if filtering_enabled:
        bundle["evidence_judge_filter"]["gate_policy_visible_evidence_ids"] = list(gate_result["valid_doc_ids"])
    return bundle


def failure_evidence_bundle(session_context: Mapping[str, Any], attacker_input: str, error: str) -> dict[str, Any]:
    analysis = type(
        "Analysis",
        (),
        {
            "intel_documents": [],
            "classification": type("Value", (), {"value": "unknown"})(),
            "severity": type("Value", (), {"value": "unknown"})(),
            "confidence": 0.0,
            "tactics": [],
            "iocs": [],
        },
    )()
    return build_evidence_bundle(analysis, session_context, attacker_input, error)


def canonical_json(value: Any) -> str:
    return json.dumps(thaw(value), sort_keys=True, separators=(",", ":"))


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def freeze_bundle(bundle: Mapping[str, Any]) -> Mapping[str, Any]:
    def freeze(value: Any) -> Any:
        if isinstance(value, Mapping):
            return MappingProxyType({key: freeze(item) for key, item in value.items()})
        if isinstance(value, list):
            return tuple(freeze(item) for item in value)
        return value

    return freeze(bundle)


def thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [thaw(item) for item in value]
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [thaw(item) for item in value]
    return value
