"""P0 runtime-truth regressions: context propagation, fail-closed serving,
final-response observability, provider resolution, and Laya provenance.

These tests are fully offline. They exercise the real Harness/Sandbox objects
with deterministic fakes only where an external model would otherwise be
required; no test opens a provider socket.
"""

from __future__ import annotations

import hashlib
from unittest.mock import MagicMock

import pytest

import ragin.server_v2 as sv2
from ragin.cycle.harness import Harness, PipelineResult
from ragin.cycle.sandbox import Sandbox, SandboxConfig
from ragin.cycle.session import EventType, Session
from ragin.decision.laya_runtime import LayaRuntime


class _Classifier:
    def __init__(self, skill_level: str = "expert") -> None:
        self.skill_level = skill_level

    def classify(self, attacker_input, session_context):
        return {
            "skill_level": self.skill_level,
            "confidence": 0.91,
            "features_used": ["test_feature"],
        }


class _RecordingDon:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def analyze(self, attacker_input, session_context):
        self.calls.append(dict(session_context))
        return {
            "threat_summary": "",
            "recommendations": [],
            "extracted_techniques": [],
        }


class _Deceiver:
    def __init__(self, text: str = "uid=1000(webapp) gid=1000(webapp)") -> None:
        self.text = text

    def generate_response(self, attacker_input, session_context):
        return {"response_text": self.text, "persona_used": "expert"}


class _PassingVerifier:
    def verify(self, response, session_context):
        return {"passed": True, "issues": [], "deterministic": True}


class _RaisingVerifier:
    def verify(self, response, session_context):
        raise RuntimeError("verifier crashed")


class _UnverifiedHarness:
    mandatory_verification = True

    def __init__(self, result: PipelineResult) -> None:
        self._result = result

    def process(self, session, command):
        return self._result


def _session(tmp_path, name: str = "session") -> Session:
    return Session.create(source_ip="10.0.0.1", session_dir=str(tmp_path / name))


def _harness(
    *,
    mandatory: bool = True,
    verifier=None,
    max_retries: int = 0,
) -> tuple[Harness, _RecordingDon]:
    don = _RecordingDon()
    harness = Harness(
        classifier=_Classifier(),
        cti_engine=don,
        deceiver=_Deceiver(),
        verifier=verifier or _PassingVerifier(),
        mandatory_verification=mandatory,
        max_retries=max_retries,
    )
    return harness, don


# ── Context propagation ──────────────────────────────────────────────────────


def test_harness_passes_current_classification_to_don(tmp_path):
    harness, don = _harness()
    result = harness.process(_session(tmp_path), "whoami")

    assert result.passed_verification is True
    assert don.calls, "Don was never called"
    assert don.calls[0]["classification"]["skill_level"] == "expert"
    assert don.calls[0]["classification"]["confidence"] == 0.91


def test_build_context_exposes_latest_classification_singular(tmp_path):
    session = _session(tmp_path)
    session.emit(EventType.CLASSIFICATION, {"skill_level": "novice", "confidence": 0.2}, source="test")
    session.emit(EventType.CLASSIFICATION, {"skill_level": "expert", "confidence": 0.9}, source="test")

    context = session.build_context()

    assert context["classification"]["skill_level"] == "expert"
    assert len(context["classifications"]) == 2


# ── Fail-closed verification ─────────────────────────────────────────────────


def test_missing_verification_is_not_a_pass():
    result = PipelineResult(session_id="s", attacker_input="whoami")
    assert result.passed_verification is False


def test_legacy_verifier_exception_fails_closed(tmp_path):
    harness, _ = _harness(
        mandatory=False,
        verifier=_RaisingVerifier(),
        max_retries=0,
    )
    result = harness.process(_session(tmp_path), "whoami")

    assert result.passed_verification is False
    assert result.verification["passed"] is False
    assert any("verifier_exception" in issue for issue in result.verification["issues"])


def test_sandbox_refuses_result_without_explicit_passed_verdict(tmp_path):
    result = PipelineResult(
        session_id="s",
        attacker_input="whoami",
        deception_response={"response_text": "UNVERIFIED DRAFT"},
        verification={},
    )
    sandbox = Sandbox(
        harness=_UnverifiedHarness(result),
        config=SandboxConfig(session_dir=str(tmp_path / "sessions")),
    )

    response = sandbox.handle_command("10.0.0.1", "whoami")

    assert response.response_text == ""
    assert response.status == "error"
    assert response.error
    assert response.served_response_sha256 == ""


# ── Final-response observability ─────────────────────────────────────────────


def test_served_bytes_match_the_verified_bytes(tmp_path):
    harness, _ = _harness()
    session = _session(tmp_path)
    result = harness.process(session, "whoami")

    expected = hashlib.sha256(result.response_text.encode()).hexdigest()
    assert result.verification["served_response_sha256"] == expected
    assert result.verification["verified_response_sha256"] == expected

    events = session.get_events_by_type(EventType.SYSTEM_RESPONSE)
    assert events, "no SYSTEM_RESPONSE event"
    assert events[-1].data["text"] == result.response_text
    assert events[-1].data["served_response_sha256"] == expected
    assert events[-1].data["verification_passed"] is True


# ── Provider resolution ──────────────────────────────────────────────────────


@pytest.fixture
def clean_provider_env(monkeypatch):
    for name in (
        "GATEWAY_URL",
        "RAGIN_LLM_BASE_URL",
        "RAGIN_PROVIDER_URL",
        "RAGIN_GATEWAY_URL",
        "RAGIN_HISOKA_GATEWAY_URL",
        "RAGIN_PROVIDER_API_KEY",
        "RAGIN_HISOKA_API_KEY",
        "RAGIN_LLM_API_KEY",
        "OPENROUTER_API_KEY",
        "AZURE_OPENAI_KEY",
        "OPENAI_API_KEY",
        "RAGIN_PROVIDER_ENABLED",
        "RAGIN_REQUIRE_PROVIDER",
    ):
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


def test_provider_resolution_prefers_gateway_then_base_url(clean_provider_env):
    env = clean_provider_env
    env.setenv("RAGIN_LLM_BASE_URL", "http://provider.invalid/v1")
    env.setenv("RAGIN_LLM_API_KEY", "x" * 24)

    resolved = sv2._resolve_provider_config()
    assert resolved["gateway_url"] == "http://provider.invalid/v1"
    assert resolved["url_source"] == "RAGIN_LLM_BASE_URL"
    assert resolved["api_key"] == "x" * 24
    assert resolved["key_source"] == "RAGIN_LLM_API_KEY"

    env.setenv("GATEWAY_URL", "http://gateway.local:8080")
    resolved = sv2._resolve_provider_config()
    assert resolved["gateway_url"] == "http://gateway.local:8080"
    assert resolved["url_source"] == "GATEWAY_URL"

    env.delenv("GATEWAY_URL")
    env.setenv("RAGIN_PROVIDER_URL", "http://provider.local:9000")
    resolved = sv2._resolve_provider_config()
    assert resolved["gateway_url"] == "http://provider.local:9000"
    assert resolved["url_source"] == "RAGIN_PROVIDER_URL"


def test_provider_resolution_rejects_non_http_endpoint(clean_provider_env):
    clean_provider_env.setenv("GATEWAY_URL", "file:///tmp/model")
    with pytest.raises(RuntimeError, match="invalid inference endpoint"):
        sv2._resolve_provider_config()


def test_provider_preflight_requires_key_when_enabled(clean_provider_env):
    env = clean_provider_env
    env.setenv("RAGIN_LLM_BASE_URL", "http://provider.invalid/v1")
    env.setenv("RAGIN_PROVIDER_ENABLED", "1")

    resolved = sv2._resolve_provider_config()
    with pytest.raises(RuntimeError, match="no provider API key"):
        sv2._preflight_provider(resolved)


# ── Laya provenance ──────────────────────────────────────────────────────────


def test_laya_reports_upstream_base_as_served():
    runtime = LayaRuntime(model="english")
    provenance = runtime.checkpoint_provenance()

    assert provenance["served_checkpoint"] == "upstream_base"
    assert provenance["fine_tuned_checkpoint_loaded"] is False


def test_laya_fine_tuned_directory_name_is_not_reported_as_served():
    runtime = LayaRuntime(model="laya_v12_balanced_allrows_gpu_redesign_v1_final_v1")
    provenance = runtime.checkpoint_provenance()

    assert provenance["served_checkpoint"] == "unsupported_local_or_custom"
    assert provenance["fine_tuned_checkpoint_loaded"] is False


# ── Composition root ─────────────────────────────────────────────────────────


def test_init_pipeline_resolves_provider_and_forces_mandatory_verification(
    tmp_path, clean_provider_env, monkeypatch
):
    env = clean_provider_env
    env.setenv("GATEWAY_URL", "http://gateway.local:8080")
    env.setenv("RAGIN_LLM_API_KEY", "k" * 24)
    env.setenv("RAGIN_HOST_FICTION_PATH", str(tmp_path / "host.json"))

    fake_harness = MagicMock()
    fake_harness.mandatory_verification = True
    monkeypatch.setattr(sv2, "ChrolloAdapter", MagicMock(return_value=MagicMock()))
    monkeypatch.setattr(sv2, "DonAdapter", MagicMock(return_value=MagicMock()))
    monkeypatch.setattr(sv2, "HisokaAdapter", MagicMock(return_value=MagicMock()))
    monkeypatch.setattr(sv2, "Harness", MagicMock(return_value=fake_harness))

    sv2._init_pipeline()

    harness_kwargs = sv2.Harness.call_args.kwargs
    assert harness_kwargs["mandatory_verification"] is True
    assert harness_kwargs["decision_arm"] == "RAGIN_BASELINE"
    sv2.DonAdapter.assert_called_once_with(
        gateway_url="http://gateway.local:8080",
        api_key="k" * 24,
    )
    assert sv2._PROVIDER_INFO["gateway_url"] == "http://gateway.local:8080"
    assert sv2._PROVIDER_INFO["api_key_configured"] is True
    assert "api_key" not in sv2._PROVIDER_INFO


# ── Evidence-bundle schema ───────────────────────────────────────────────────


class _FakeDonEngine:
    def analyze(self, request, session_log):
        from ragin.don.models import ClassificationLabel, SeverityLevel, ThreatAnalysis

        return ThreatAnalysis(
            analysis_id="a1",
            session_id=request.session_id,
            classification=ClassificationLabel.MALICIOUS,
            severity=SeverityLevel.HIGH,
            confidence=request.confidence,
            tactics=[],
            threat_actors=[],
            iocs=[],
            sophistication_score=0.0,
        )


def test_evidence_bundle_chrollo_block_uses_classifier_verdict():
    from ragin.cycle.adapters import DonAdapter

    adapter = DonAdapter(engine=_FakeDonEngine())
    payload = adapter.analyze(
        "whoami",
        {
            "session_id": "s1",
            "classification": {
                "skill_level": "expert",
                "confidence": 0.93,
                "features_used": ["command_complexity"],
                "feature_values": {"command_complexity": 1.0},
            },
            "attacker_inputs": [{"command": "whoami"}],
            "system_responses": [],
        },
    )

    assert payload["classification"] == "malicious"
    assert payload["confidence"] == 0.93
    bundle = payload["evidence_bundle"]
    assert bundle["chrollo"]["skill_level"] == "expert"
    assert bundle["chrollo"]["confidence"] == 0.93
    assert bundle["chrollo"]["features_used"] == ["command_complexity"]
