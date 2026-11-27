"""Focused contract, safety, and seam tests for LAYA_DECISION_MODEL_V2."""

from __future__ import annotations

import time
from types import SimpleNamespace

import pytest

from ragin.chrollo.features import FeatureExtractor
from ragin.cycle.adapters import ChrolloAdapter
from ragin.cycle.harness import Harness
from ragin.cycle.session import EventType, Session
from ragin.decision.laya_decision import LayaDecisionAdapter
from ragin.hisoka.deceiver import AdaptiveDeceiver
from ragin.hisoka.deception import ResponseGenerator, _jev_signal_from_context, jev_kind_strategy


def _native_payload(*, attack: float = 0.9, stage: str = "recon", severity: float = 2.0) -> dict:
    native = {
        "answers": {
            "attack": {"type": "noul", "noul": attack, "confidence": 0.9},
            "stage": {"type": "choice", "choice": stage, "probabilities": {stage: 1.0}},
            "severity": {"type": "score", "score": severity, "confidence": 0.9},
        },
        "routing": {"model": "english"},
    }
    return {"model": "laya/english", "native_output": native, "answers": native["answers"]}


def _verified_manifest() -> dict:
    return {
        "runtime_verified": True,
        "checkpoint_verified": True,
        "package_version": "0.4.2",
        "source_repository": "https://huggingface.co/convaiinnovations/laya",
        "checkpoint": "english@55cf4c4e",
        "revision": "55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851",
        "model_hash": "sha256-test",
    }


def test_laya_off_preserves_baseline_classification_path(monkeypatch):
    monkeypatch.setenv("RAGIN_LAYA_ENABLED", "0")
    result = SimpleNamespace(
        skill_level=SimpleNamespace(value="novice"),
        confidence=0.5,
        session_id="s-off",
        features_used=[],
        feature_values={},
    )
    payload = ChrolloAdapter(classifier=SimpleNamespace(classify=lambda _: result)).classify("whoami", {"session_id": "s-off"})
    assert "laya_decision" not in payload
    assert "laya_assessment" not in payload


def test_laya_off_remains_off_after_later_treatment_initialization(monkeypatch):
    monkeypatch.setenv("RAGIN_LAYA_ENABLED", "0")
    result = SimpleNamespace(
        skill_level=SimpleNamespace(value="novice"),
        confidence=0.5,
        session_id="s-arm",
        features_used=[],
        feature_values={},
    )
    baseline = ChrolloAdapter(classifier=SimpleNamespace(classify=lambda _: result))
    monkeypatch.setenv("RAGIN_LAYA_ENABLED", "1")
    monkeypatch.setenv("RAGIN_LAYA_EVAL_REQUIRE_REAL_MODEL", "0")
    baseline_payload = baseline.classify("whoami", {"session_id": "s-arm"})
    assert "laya_decision" not in baseline_payload


def test_laya_on_changes_only_the_preregistered_strategy_seam():
    adapter = LayaDecisionAdapter(lambda _: _native_payload(), model="laya/english", manifest_provider=_verified_manifest)
    decision = adapter.decide(session_id="s-on", state="nmap -sV")
    assert decision["selected_workflow_branch"] == "LAYA_ATTACK_STRATEGY"
    assert decision["selected_response_strategy"] == "maximize_recon_surface"
    signal = _jev_signal_from_context({"classification": {"laya_decision": decision}})
    assert signal["source"] == "laya"
    assert signal["attack_kind"] == "scanning"
    assert jev_kind_strategy(signal["attack_kind"])["objective"] == "maximize_recon_surface"


def test_laya_failure_falls_back_to_baseline():
    decision = LayaDecisionAdapter(lambda _: (_ for _ in ()).throw(RuntimeError("down")), model="laya/english").decide(
        session_id="s-fail", state="x"
    )
    assert decision["availability"] is False
    assert decision["selected_workflow_branch"] == "BASELINE_NO_SIGNAL"
    assert decision["selected_response_strategy"] == "baseline"


def test_fixture_rejected_in_evaluation_real_model_mode(monkeypatch):
    monkeypatch.setenv("RAGIN_LAYA_EVAL_REQUIRE_REAL_MODEL", "1")
    with pytest.raises(RuntimeError, match="evaluation mode"):
        LayaDecisionAdapter(lambda _: _native_payload(), model="fixture")


class _RejectingVerifier:
    def verify(self, response, context):
        return {"passed": False, "issues": ["deterministic_rejection"], "deterministic": True}


def _rejecting_harness(tmp_path):
    classifier = SimpleNamespace(
        classify=lambda _input, _context: {"skill_level": "novice", "confidence": 0.5, "laya_decision": {"selected_response_strategy": "maximize_recon_surface"}}
    )
    don = SimpleNamespace(analyze=lambda _input, _context: {})
    deceiver = SimpleNamespace(generate_response=lambda _input, _context: {"response_text": "draft"})
    return Harness(
        classifier=classifier,
        cti_engine=don,
        deceiver=deceiver,
        verifier=_RejectingVerifier(),
        mandatory_verification=True,
        max_retries=0,
        host_fiction_path=str(tmp_path / "host.json"),
    )


def test_laya_cannot_bypass_verifier_or_commit_state(tmp_path):
    harness = _rejecting_harness(tmp_path)
    session = Session.create(session_dir=tmp_path / "sessions")
    result = harness.process(session, "whoami")
    assert result.passed_verification is False
    assert result.deception_response == {}
    assert not session.get_events_by_type(EventType.SYSTEM_RESPONSE)
    assert not harness._host_store.to_dict()["host_facts"]


@pytest.mark.parametrize(
    "payload",
    [
        {"answers": {"attack": {"type": "noul", "noul": "not-a-number"}}},
        {"status": "NO_SIGNAL"},
    ],
)
def test_malformed_and_no_signal_preserve_baseline(payload):
    decision = LayaDecisionAdapter(lambda _: payload, model="laya/english").decide(session_id="s", state="x")
    assert decision["availability"] is False
    assert decision["selected_response_strategy"] == "baseline"


def test_timeout_preserves_baseline():
    def slow(_):
        time.sleep(0.05)
        return _native_payload()

    decision = LayaDecisionAdapter(slow, model="laya/english", timeout_s=0.001).decide(session_id="s", state="x")
    assert decision["error"] == "timeout"
    assert decision["selected_workflow_branch"] == "BASELINE_NO_SIGNAL"


def test_provenance_is_recorded_without_raw_input():
    decision = LayaDecisionAdapter(lambda _: _native_payload(), model="laya/english", manifest_provider=_verified_manifest).decide(
        session_id="session-1", state="private input"
    )
    assert decision["session_id"] == "session-1"
    assert decision["real_model_verified"] is True
    assert decision["model_hash"] == "sha256-test"
    assert len(decision["input_sha256"]) == 64
    assert decision["input_sha256"] != "private input"
    assert decision["native_raw_output"]["answers"]["attack"]["noul"] == 0.9
    assert decision["decision_policy_version"] == "LAYA_DECISION_POLICY_V2"


def test_local_generator_consumes_attack_and_non_attack_strategies():
    generator = ResponseGenerator()
    baseline = generator.generate("novice", "printf smoke", response_strategy="baseline")
    attack = generator.generate("novice", "printf smoke", response_strategy="fake_success_and_return_visits")
    non_attack = generator.generate("novice", "printf smoke", response_strategy="low_intensity_administration")
    assert attack != baseline
    assert non_attack != baseline
    assert attack != non_attack


def test_laya_strategy_reaches_adaptive_deceiver_candidate():
    deceiver = AdaptiveDeceiver()
    base_context = {"session_id": "strategy-smoke", "classification": {"skill_level": "novice"}}
    attack_context = {
        "session_id": "strategy-smoke-attack",
        "classification": {
            "skill_level": "novice",
            "laya_decision": {
                "availability": True,
                "selected_response_strategy": "fake_success_and_return_visits",
                "normalized_decision": {
                    "available": True,
                    "is_attack": True,
                    "attack_kind": "persistence",
                    "attack_probability": 0.9,
                    "severity": 2.0,
                },
            },
        },
    }
    baseline = deceiver.generate_response("printf smoke", base_context)
    treatment = deceiver.generate_response("printf smoke", attack_context)
    assert treatment.response_text != baseline.response_text
    assert treatment.metadata["laya_response_strategy"] == "fake_success_and_return_visits"


@pytest.mark.parametrize("length", [4095, 4096, 4097, 5607, 16384])
def test_long_evaluation_payload_preserves_raw_log_without_command_truncation(length):
    captured = {}

    def classify(session_log):
        captured["session_log"] = session_log
        return SimpleNamespace(
            skill_level=SimpleNamespace(value="novice"),
            confidence=0.5,
            session_id="long-input",
            features_used=[],
            feature_values={},
        )

    payload = "x" * length
    result = ChrolloAdapter(classifier=SimpleNamespace(classify=classify)).classify(
        payload,
        {"session_id": "long-input", "attacker_inputs": [{"command": payload}]},
    )
    assert result["skill_level"] == "novice"
    assert captured["session_log"].raw_log == payload if length > 4096 else captured["session_log"].commands[0].command == payload
    if length > 4096:
        assert captured["session_log"].commands == []
        assert FeatureExtractor().extract(captured["session_log"])["custom_tool_usage"] == 0.0


def test_long_payload_above_transport_limit_is_rejected():
    payload = "x" * 16385
    with pytest.raises(ValueError, match="raw_log transport limit"):
        ChrolloAdapter(classifier=SimpleNamespace(classify=lambda _: None)).classify(
            payload,
            {"session_id": "too-long", "attacker_inputs": [{"command": payload}]},
        )


def test_long_payload_hash_and_base_representation_are_stable():
    import hashlib

    payload = "context\n\nEvidence:\n" + "e" * 5588
    captured = {}

    def classify(session_log):
        captured["session_log"] = session_log
        return SimpleNamespace(
            skill_level=SimpleNamespace(value="novice"),
            confidence=0.5,
            session_id="stable-input",
            features_used=[],
            feature_values={},
        )

    adapter = ChrolloAdapter(classifier=SimpleNamespace(classify=classify))
    adapter.classify(payload, {"session_id": "stable-input", "attacker_inputs": [{"command": payload}]})
    first = captured["session_log"]
    adapter.classify(payload, {"session_id": "stable-input", "attacker_inputs": [{"command": payload}]})
    second = captured["session_log"]
    assert hashlib.sha256(first.raw_log.encode()).hexdigest() == hashlib.sha256(payload.encode()).hexdigest()
    assert first.raw_log == second.raw_log == payload
    assert first.commands == second.commands == []
