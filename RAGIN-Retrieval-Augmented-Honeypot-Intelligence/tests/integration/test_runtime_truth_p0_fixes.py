"""P0 fix regressions: classification normalization, serving observability,
verifier consistency across decision arms, and self-endpoint guarding.

Offline only: no provider socket is opened. Fakes stand in for the external
generator where inference would otherwise be required; the verifier, sandbox,
session replay, and HTTP handlers under test are the real objects.
"""

from __future__ import annotations

import hashlib
from unittest.mock import patch

import pytest
from aiohttp.test_utils import TestClient, TestServer

import ragin.server_v2 as sv2
from ragin.capture_v4.privacy import bounded_redacted_text
from ragin.cycle.adapters import DonAdapter
from ragin.cycle.classification import latest_skill_classification, normalize_classification
from ragin.cycle.harness import Harness, PipelineResult
from ragin.cycle.sandbox import Sandbox, SandboxConfig, SandboxResponse
from ragin.cycle.session import EventType, Session
from ragin.cycle.verifier import FictionConsistencyVerifier
from ragin.decision_fusion_v4.config import ARMS
from ragin.hisoka.deception import identity_for

# ── Fakes ────────────────────────────────────────────────────────────────────


class _RecordingEngine:
    """Records what Don actually received, unlike a RecordingDon bypass."""

    def __init__(self) -> None:
        self.requests: list = []
        self.logs: list[list] = []

    def analyze(self, request, session_log):
        from ragin.don.models import ClassificationLabel, SeverityLevel, ThreatAnalysis

        self.requests.append(request)
        self.logs.append(list(session_log))
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


class _Classifier:
    def __init__(self, skill_level: str = "expert") -> None:
        self.skill_level = skill_level

    def classify(self, attacker_input, session_context):
        return {"skill_level": self.skill_level, "confidence": 0.91, "features_used": ["test"]}


class _Cti:
    def analyze(self, attacker_input, session_context):
        return {
            "evidence_bundle": {
                "retrieval": {
                    "relevant_doc_ids": ["T1003", "T1059"],
                    "retrieval_status": "SUCCESS",
                    "backend": "bm25",
                },
                "don_analysis": {"ttps_seen": ["T1003"]},
            }
        }


class _StaticDeceiver:
    def __init__(self, text: str) -> None:
        self.text = text

    def generate_response(self, attacker_input, session_context):
        return {"response_text": self.text, "persona_used": "expert", "metadata": {}}


class _RaisingDeceiver:
    def generate_response(self, attacker_input, session_context):
        raise TimeoutError("generator timed out")


class _PassingVerifier:
    def verify(self, response, session_context):
        return {"passed": True, "issues": [], "deterministic": True}


class _FailingVerifier:
    def verify(self, response, session_context):
        return {"passed": False, "issues": ["identity-pin: test rejection"], "deterministic": True}


class _MalformedVerifier:
    def verify(self, response, session_context):
        return {}


class _RaisingVerifier:
    def verify(self, response, session_context):
        raise RuntimeError("verifier crashed")


class _RaisingHarness:
    mandatory_verification = True
    decision_arm = "RAGIN_BASELINE"

    def process(self, session, command):
        raise RuntimeError("pipeline exploded")


class _FixedResultHarness:
    """Returns a fixed PipelineResult; used for max-command / endpoint tests."""

    mandatory_verification = True
    decision_arm = "RAGIN_BASELINE"

    def __init__(self, result: PipelineResult) -> None:
        self._result = result

    def process(self, session, command):
        return self._result


def _session(tmp_path, name: str = "session") -> Session:
    return Session.create(source_ip="10.0.0.1", session_dir=str(tmp_path / name))


def _real_harness(*, verifier=None, deceiver=None, arm: str = "RAGIN_BASELINE") -> Harness:
    return Harness(
        classifier=_Classifier(),
        cti_engine=_Cti(),
        deceiver=deceiver or _StaticDeceiver("placeholder"),
        verifier=verifier if verifier is not None else _PassingVerifier(),
        mandatory_verification=True,
        decision_arm=arm,
        max_retries=0,
    )


# ── A. Classification normalization ─────────────────────────────────────────


@pytest.mark.parametrize(
    ("context_classification", "expected_skill", "expected_confidence"),
    [
        (None, "unknown", 0.5),
        ("expert", "unknown", 0.5),
        ({}, "unknown", 0.5),
        ({"skill_level": "expert"}, "expert", 0.5),
        ({"skill_level": "EXPERT", "confidence": 0.8}, "expert", 0.8),
        ({"skill_level": "root", "confidence": 0.9}, "unknown", 0.9),
        ({"skill_level": "novice", "confidence": "high"}, "novice", 0.5),
        ({"skill_level": "advanced", "confidence": 1.5}, "advanced", 0.5),
        ({"skill_level": None, "confidence": None}, "unknown", 0.5),
        ({"confidence": 0.7}, "unknown", 0.7),
    ],
)
def test_don_adapter_normalizes_historical_classification(
    context_classification, expected_skill, expected_confidence
):
    engine = _RecordingEngine()
    adapter = DonAdapter(engine=engine)

    payload = adapter.analyze(
        "whoami",
        {
            "session_id": "sess-1",
            "classification": context_classification,
            "attacker_inputs": [{"command": "whoami"}],
            "system_responses": ["webapp"],
        },
    )

    assert payload["error"] == ""
    request = engine.requests[0]
    assert request.confidence == pytest.approx(expected_confidence)
    # A missing/invalid verdict must never be promoted to MALICIOUS (the
    # high-risk label); the adapter keeps its documented SUSPICIOUS default.
    mapping = {
        "novice": "benign",
        "intermediate": "suspicious",
        "advanced": "malicious",
        "expert": "malicious",
        "unknown": "suspicious",
    }
    assert request.classification.value == mapping[expected_skill]
    assert payload["evidence_bundle"]["chrollo"]["skill_level"] == expected_skill


def test_don_adapter_tolerates_non_list_history():
    engine = _RecordingEngine()
    adapter = DonAdapter(engine=engine)

    payload = adapter.analyze(
        "whoami",
        {
            "session_id": 123,  # non-str id
            "classification": {"skill_level": "novice"},
            "attacker_inputs": None,
            "system_responses": "not-a-list",
            "features": "not-a-dict",
        },
    )

    assert payload["error"] == ""
    assert engine.requests[0].session_id == "123"


def test_normalize_classification_never_invents_a_skill_level():
    assert normalize_classification({"skill_level": "root"}) == {}
    assert normalize_classification("expert") == {}
    assert normalize_classification(None) == {}
    assert normalize_classification({"confidence": 2.0}) == {}


def test_latest_skill_classification_skips_supervisor_and_malformed():
    events = [
        {"skill_level": "novice", "confidence": 0.2},
        {"stage": "supervisor", "routing_decision": {"persona": "x"}},
        {"skill_level": "not-a-level", "confidence": 0.9},
        {"confidence": 0.4},
    ]
    assert latest_skill_classification(events) == {"skill_level": "novice", "confidence": 0.2}
    assert latest_skill_classification([]) == {}
    assert latest_skill_classification(None) == {}


def test_build_context_keeps_history_but_skips_supervisor_verdict(tmp_path):
    session = _session(tmp_path)
    session.emit(EventType.CLASSIFICATION, {"skill_level": "novice", "confidence": 0.2}, source="chrollo")
    session.emit(
        EventType.CLASSIFICATION,
        {"stage": "supervisor", "routing_decision": {"persona": "expert"}},
        source="supervisor",
    )

    context = session.build_context()

    # The routing event stays in the full history ...
    assert len(context["classifications"]) == 2
    # ... but never becomes the singular semantic classification.
    assert context["classification"]["skill_level"] == "novice"


def test_build_context_latest_valid_verdict_wins(tmp_path):
    session = _session(tmp_path)
    session.emit(EventType.CLASSIFICATION, {"skill_level": "novice", "confidence": 0.2}, source="chrollo")
    session.emit(EventType.CLASSIFICATION, {"skill_level": "expert", "confidence": 0.9}, source="chrollo")
    session.emit(
        EventType.CLASSIFICATION,
        {"stage": "supervisor", "routing_decision": {"persona": "novice"}},
        source="supervisor",
    )

    context = session.build_context()

    assert context["classification"]["skill_level"] == "expert"
    assert context["classification"]["confidence"] == pytest.approx(0.9)


# ── B. HTTP observability + max-command status ──────────────────────────────


def _mock_harness() -> object:
    from unittest.mock import MagicMock

    return MagicMock()


def _mock_sandbox() -> object:
    from unittest.mock import MagicMock

    sandbox = MagicMock()
    sandbox.create_session.return_value = SandboxResponse(session_id="abc123", response_text="", command_count=0)
    return sandbox


@pytest.fixture
async def client():
    import ragin.server_v2 as server

    orig = (server._harness, server._sandbox, server._component, server._COMPONENT_NAME, server.API_KEY, server.REQUIRE_AUTH)
    server.API_KEY = ""
    server.REQUIRE_AUTH = False
    with patch.object(server, "_init_pipeline"):
        app = server.create_app(mode="pipeline")
    server._harness = _mock_harness()
    server._sandbox = _mock_sandbox()
    server._component = None
    server._COMPONENT_NAME = "pipeline"

    test_client = TestClient(TestServer(app))
    await test_client.start_server()
    yield test_client
    await test_client.close()

    (
        server._harness,
        server._sandbox,
        server._component,
        server._COMPONENT_NAME,
        server.API_KEY,
        server.REQUIRE_AUTH,
    ) = orig


async def test_session_command_exposes_served_hash_and_verification(client):
    served = "uid=1001(webapp) gid=1001(webapp)"
    sv2._sandbox.handle_command.return_value = SandboxResponse(
        session_id="abc123",
        response_text=served,
        command_count=1,
        event_count=6,
        status="ok",
        serve_path="GENERATED_VERIFIED",
        candidate_sha256="c" * 64,
        served_response_sha256=hashlib.sha256(served.encode()).hexdigest(),
        verification={"passed": True, "issues": [], "serve_path": "GENERATED_VERIFIED"},
    )

    resp = await client.post("/api/session/command", json={"session_id": "abc123", "command": "id"})
    assert resp.status == 200
    data = await resp.json()

    assert data["status"] == "ok"
    assert data["serve_path"] == "GENERATED_VERIFIED"
    assert data["candidate_sha256"] == "c" * 64
    assert data["served_response_sha256"] == hashlib.sha256(served.encode()).hexdigest()
    assert data["verification"]["passed"] is True


async def test_session_command_error_stays_503_and_echoes_audit_fields(client):
    sv2._sandbox.handle_command.return_value = SandboxResponse(
        session_id="abc123",
        response_text="",
        command_count=2,
        status="error",
        error="verified_serve_unavailable:identity-pin",
        serve_path="",
        candidate_sha256="",
        served_response_sha256="",
        verification={"passed": False, "issues": ["identity-pin"]},
    )

    resp = await client.post("/api/session/command", json={"session_id": "abc123", "command": "whoami"})
    assert resp.status == 503
    data = await resp.json()

    assert data["error"] == "verified_serve_unavailable"
    assert data["status"] == "error"
    assert data["response_text"] == ""
    assert data["served_response_sha256"] == ""
    assert data["verification"]["passed"] is False


def test_max_command_path_is_an_error_not_ok(tmp_path, monkeypatch):
    session = _session(tmp_path)
    result = PipelineResult(
        session_id=session.session_id,
        attacker_input="whoami",
        deception_response={"response_text": "webapp"},
        verification={"passed": True, "issues": [], "serve_path": "GENERATED_VERIFIED"},
    )
    sandbox = Sandbox(
        harness=_FixedResultHarness(result),
        config=SandboxConfig(max_commands=0, session_dir=str(tmp_path / "sessions")),
    )

    response = sandbox.handle_command("10.0.0.1", "whoami")

    assert response.status == "error"
    assert response.error == "max_commands_reached"
    assert response.served_response_sha256 == ""

    metrics = Session.wake(response.session_id, session_dir=str(tmp_path / "sessions")).get_events_by_type(
        EventType.METRIC
    )
    trace = metrics[-1].data["trace"]
    assert trace["status"] == "error"
    assert trace["verification"]["reason_availability"] == "NOT_RUN"


# ── C. Per-interaction trace ────────────────────────────────────────────────


def test_trace_separates_candidate_and_served_and_labels_unknowns(tmp_path):
    text = "webapp@web-srv-01:~$ whoami\nwebapp"
    result = PipelineResult(
        session_id="s1",
        attacker_input="whoami",
        classification={"skill_level": "expert", "confidence": 0.91},
        cti_analysis={
            "evidence_bundle": {
                "retrieval": {"relevant_doc_ids": ["T1003"], "retrieval_status": "SUCCESS", "backend": "bm25"},
                "don_analysis": {"ttps_seen": ["T1003"]},
            }
        },
        deception_response={"response_text": text, "persona_used": "expert", "metadata": {}},
        verification={
            "passed": True,
            "issues": [],
            "serve_path": "GENERATED_VERIFIED",
            "candidate_sha256": "c" * 64,
        },
    )
    sandbox = Sandbox(
        harness=_FixedResultHarness(result),
        config=SandboxConfig(session_dir=str(tmp_path / "sessions")),
    )

    response = sandbox.handle_command("10.0.0.1", "whoami")
    session = Session.wake(response.session_id, session_dir=str(tmp_path / "sessions"))
    trace = session.get_events_by_type(EventType.METRIC)[-1].data["trace"]

    assert trace["schema"] == "ragin.interaction_trace.v1"
    assert trace["arm"] == "RAGIN_BASELINE"
    assert trace["candidate_sha256"] == "c" * 64
    assert trace["served_response_sha256"] == hashlib.sha256(text.encode()).hexdigest()
    assert trace["served_response_chars"] == len(text)
    assert trace["classification"] == {"skill_level": "expert", "confidence": 0.91, "availability": "OBSERVED"}
    assert trace["evidence_refs"]["doc_ids"] == ["T1003"]
    assert trace["decision"]["verification_passed"] is True
    assert trace["verification"]["reason_availability"] == "NO_ISSUES_REPORTED"
    assert trace["latency_ms"] >= 0.0

    # Unobserved data must be labelled, never presented as known.
    assert trace["model_identity"]["availability"] in {
        "SOURCE_DEFAULT_NOT_OBSERVED",
        "CONFIGURED_NOT_OBSERVED",
        "OBSERVED_BY_GENERATOR",
    }
    assert trace["model_identity"]["availability"] != "OBSERVED_BY_GENERATOR"
    assert trace["tokens"]["availability"] == "NOT_AVAILABLE"
    assert trace["cost"]["availability"] == "NOT_AVAILABLE"


def test_trace_represents_failed_serving(tmp_path):
    result = PipelineResult(
        session_id="s1",
        attacker_input="whoami",
        classification={"skill_level": "expert"},
        deception_response={"response_text": "root", "metadata": {}},
        verification={"passed": False, "issues": ["identity-pin: wrong user"], "serve_path": ""},
        error="verified_serve_unavailable",
    )
    sandbox = Sandbox(
        harness=_FixedResultHarness(result),
        config=SandboxConfig(session_dir=str(tmp_path / "sessions")),
    )

    response = sandbox.handle_command("10.0.0.1", "whoami")
    session = Session.wake(response.session_id, session_dir=str(tmp_path / "sessions"))
    trace = session.get_events_by_type(EventType.METRIC)[-1].data["trace"]

    assert response.status == "error"
    assert response.response_text == ""
    assert trace["status"] == "error"
    assert trace["served_response_sha256"] == ""
    assert trace["verification"]["passed"] is False
    assert trace["verification"]["reason"] == ["identity-pin: wrong user"]


def test_trace_represents_harness_crash_and_redacts_credentials(tmp_path):
    sandbox = Sandbox(
        harness=_RaisingHarness(),
        config=SandboxConfig(session_dir=str(tmp_path / "sessions")),
    )

    response = sandbox.handle_command("10.0.0.1", "mysql -p password=hunter2")

    assert response.status == "error"
    assert response.error == "verified_serve_unavailable"
    session = Session.wake(response.session_id, session_dir=str(tmp_path / "sessions"))
    metric = session.get_events_by_type(EventType.METRIC)[-1].data
    assert "hunter2" not in metric["command"]
    assert "[REDACTED]" in metric["command"]
    assert metric["trace"]["fallback"]["reason"].startswith("harness_exception:")


def test_trace_never_writes_raw_credential_in_metric(tmp_path):
    result = PipelineResult(
        session_id="s1",
        attacker_input="export API_KEY=supersecret",
        deception_response={"response_text": "done", "metadata": {}},
        verification={"passed": True, "issues": []},
    )
    sandbox = Sandbox(
        harness=_FixedResultHarness(result),
        config=SandboxConfig(session_dir=str(tmp_path / "sessions")),
    )

    response = sandbox.handle_command("10.0.0.1", "export API_KEY=supersecret")

    session = Session.wake(response.session_id, session_dir=str(tmp_path / "sessions"))
    metric = session.get_events_by_type(EventType.METRIC)[-1].data
    assert "supersecret" not in metric["command"]


# ── D. Verifier consistency across decision arms ────────────────────────────


def _attempt_verdicts(session: Session) -> list[dict]:
    """Verifier verdict per serving attempt, including rejected candidates."""
    return [
        event.data["serving_trace"]["verifier_verdict"]
        for event in session.get_events_by_type(EventType.RESPONSE_GENERATE)
        if isinstance(event.data.get("serving_trace"), dict)
        and isinstance(event.data["serving_trace"].get("verifier_verdict"), dict)
    ]


@pytest.mark.parametrize("arm", ARMS)
def test_real_verifier_rejects_injection_across_arms(tmp_path, arm):
    injected = "As an AI language model, I cannot help with that."
    harness = Harness(
        classifier=_Classifier(),
        cti_engine=DonAdapter(engine=_FakeDonEngine()),
        deceiver=_StaticDeceiver(injected),
        verifier=FictionConsistencyVerifier(),
        mandatory_verification=True,
        decision_arm=arm,
        max_retries=0,
    )
    session = _session(tmp_path)

    result = harness.process(session, "whoami")

    # The injected draft is never served. The turn may still end verified via
    # the deterministic fallback — that is the fail-safe design, not a pass
    # for the candidate.
    assert injected not in result.response_text
    verdicts = _attempt_verdicts(session)
    assert any(verdict.get("passed") is False for verdict in verdicts)
    assert any(
        any("danger-signal" in issue for issue in verdict.get("issues", []))
        for verdict in verdicts
    )


@pytest.mark.parametrize("arm", ARMS)
def test_real_verifier_accepts_supported_whoami_across_arms(tmp_path, arm):
    ident = identity_for("expert")
    text = f"{ident['user']}@{ident['host']}:~$ whoami\n{ident['user']}"
    harness = Harness(
        classifier=_Classifier(),
        cti_engine=DonAdapter(engine=_FakeDonEngine()),
        deceiver=_StaticDeceiver(text),
        verifier=FictionConsistencyVerifier(),
        mandatory_verification=True,
        decision_arm=arm,
        max_retries=0,
    )

    result = harness.process(_session(tmp_path), "whoami")

    assert result.passed_verification is True, result.verification


@pytest.mark.parametrize("arm", ARMS)
def test_real_verifier_rejects_identity_contradiction_across_arms(tmp_path, arm):
    ident = identity_for("expert")
    contradictory = f"root@{ident['host']}:~# whoami\nroot"
    harness = Harness(
        classifier=_Classifier(),
        cti_engine=DonAdapter(engine=_FakeDonEngine()),
        deceiver=_StaticDeceiver(contradictory),
        verifier=FictionConsistencyVerifier(),
        mandatory_verification=True,
        decision_arm=arm,
        max_retries=0,
    )
    session = _session(tmp_path)

    result = harness.process(session, "whoami")

    assert contradictory not in result.response_text
    verdicts = _attempt_verdicts(session)
    assert any(verdict.get("passed") is False for verdict in verdicts)
    assert any(
        any("identity-pin" in issue for issue in verdict.get("issues", []))
        for verdict in verdicts
    )


def test_fail_closed_supported_claim_rejects_hedge(tmp_path, monkeypatch):
    monkeypatch.setenv("RAGIN_FAIL_CLOSED", "1")
    ident = identity_for("expert")
    hedged = f"{ident['user']}@{ident['host']}:~$ uname -a\nunknown"
    harness = Harness(
        classifier=_Classifier(),
        cti_engine=DonAdapter(engine=_FakeDonEngine()),
        deceiver=_StaticDeceiver(hedged),
        verifier=FictionConsistencyVerifier(),
        mandatory_verification=True,
        max_retries=0,
    )
    session = _session(tmp_path)

    result = harness.process(session, "uname -a")

    verdicts = _attempt_verdicts(session)
    assert any(
        any("supported-claim" in issue for issue in verdict.get("issues", []))
        for verdict in verdicts
    )
    # The hedged draft itself must not be what the attacker receives.
    if result.response_text:
        assert "unknown" not in result.response_text.lower()


def test_mandatory_harness_installs_the_real_verifier():
    harness = Harness(
        classifier=_Classifier(),
        cti_engine=_Cti(),
        deceiver=_StaticDeceiver("webapp"),
        verifier=None,
        mandatory_verification=True,
        max_retries=0,
    )

    # "No verifier configured" is not a reachable state when mandatory
    # verification is on: the composition installs HostFictionVerifier.
    assert harness._verifier is not None


@pytest.mark.parametrize("verifier", [_MalformedVerifier(), _RaisingVerifier()])
def test_broken_verifier_fails_closed_with_a_reason(tmp_path, verifier):
    harness = Harness(
        classifier=_Classifier(),
        cti_engine=_Cti(),
        deceiver=_StaticDeceiver("webapp"),
        verifier=verifier,
        mandatory_verification=True,
        max_retries=0,
    )

    result = harness.process(_session(tmp_path), "whoami")

    assert result.passed_verification is False
    assert result.verification["passed"] is False
    assert result.verification["issues"]


def test_generator_timeout_serves_verified_fallback(tmp_path):
    harness = Harness(
        classifier=_Classifier(),
        cti_engine=_Cti(),
        deceiver=_RaisingDeceiver(),
        verifier=FictionConsistencyVerifier(),
        mandatory_verification=True,
        max_retries=0,
    )

    result = harness.process(_session(tmp_path), "whoami")

    assert result.passed_verification is True, result.verification
    assert result.verification["serve_path"] == "FALLBACK_VERIFIED"
    assert result.response_text


def test_unverified_result_is_not_served_by_sandbox(tmp_path):
    result = PipelineResult(
        session_id="s1",
        attacker_input="whoami",
        deception_response={"response_text": "UNVERIFIED"},
        verification={},
    )
    sandbox = Sandbox(
        harness=_FixedResultHarness(result),
        config=SandboxConfig(session_dir=str(tmp_path / "sessions")),
    )

    response = sandbox.handle_command("10.0.0.1", "whoami")

    assert response.response_text == ""
    assert response.status == "error"


# ── E. Self-endpoint guard ──────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("url", "bind", "port", "expected"),
    [
        ("http://localhost:8080", "127.0.0.1", 8080, True),
        ("http://127.0.0.1:8080", "127.0.0.1", 8080, True),
        ("http://localhost:9090", "127.0.0.1", 8080, False),
        ("http://127.0.0.1:8080", "0.0.0.0", 8080, True),
        ("http://provider.invalid:8080", "127.0.0.1", 8080, False),
    ],
)
def test_is_self_endpoint(url, bind, port, expected):
    assert sv2._is_self_endpoint(url, bind, port) is expected


def test_configured_self_endpoint_raises():
    config = {"gateway_url": "http://127.0.0.1:8080", "url_source": "GATEWAY_URL"}
    with pytest.raises(RuntimeError, match="own listener"):
        sv2._assert_provider_not_self(config, "127.0.0.1", 8080)


def test_unconfigured_default_self_collision_now_raises():
    # The default is checked at the CLI's actual listen port. Deterministic
    # mode must set a non-colliding loopback endpoint (for example :9).
    config = {"gateway_url": "http://localhost:8080", "url_source": "default"}
    with pytest.raises(RuntimeError, match="own listener"):
        sv2._assert_provider_not_self(config, "127.0.0.1", 8080)


def test_self_collision_error_never_echoes_credentials():
    config = {
        "gateway_url": "http://user:supersecret@127.0.0.1:8080/v1?token=abc123",
        "url_source": "GATEWAY_URL",
    }
    with pytest.raises(RuntimeError) as excinfo:
        sv2._assert_provider_not_self(config, "127.0.0.1", 8080)
    message = str(excinfo.value)
    assert "supersecret" not in message
    assert "abc123" not in message
    assert "http://" not in message


def test_configured_nondefault_port_is_allowed():
    config = {"gateway_url": "http://127.0.0.1:9090", "url_source": "GATEWAY_URL"}
    sv2._assert_provider_not_self(config, "127.0.0.1", 8080)  # must not raise


# ── F. Observability text, decision references, and privacy bounds ──────────


def test_bounded_redaction_precedes_truncation():
    # The credential marker begins just before the bound. Truncating first
    # would split ``password=`` from its value and could leak the value.
    # The filler must SURVIVE minimization for this test to mean anything: a
    # long unbroken run (the old "x" * 188) is itself redacted as a base64
    # blob, which shrinks the text below the bound, so `truncated` stays False
    # and the redact-then-truncate ordering is never exercised. Repeating
    # "x " keeps every token run at one character while still placing the
    # credential marker right before the bound (index 188 < 200).
    command = "x " * 94 + "password=supersecret-value"
    bounded = bounded_redacted_text(command, limit=200)
    assert "supersecret-value" not in bounded["text"]
    # The marker itself may be cut by the bound; what matters is that the
    # secret was removed before truncation, not that the marker survives.
    assert "password=" in bounded["text"]
    assert len(bounded["text"]) <= 200
    assert bounded["truncated"] is True
    assert bounded["availability"] == "REDACTED_MINIMIZED"


@pytest.mark.parametrize(
    "text",
    [
        "curl -H 'Authorization: Bearer abcdef0123456789' https://example.invalid/",
        "export AWS_SECRET_ACCESS_KEY=abcdefghijklmnopqrstuvwxyz",
        "sshpass -p hunter2 ssh root@127.0.0.1",
        "https://user:passw0rd@example.invalid/v1?token=abc123",
        "ghp_abcdefghijklmnopqrstuvwxyz0123456789",
    ],
)
def test_bounded_redaction_covers_credential_and_authorization_forms(text):
    bounded = bounded_redacted_text(text, limit=400)
    lowered = bounded["text"].lower()
    for secret in ("abcdef0123456789", "abcdefghijklmnopqrstuvwxyz", "hunter2", "passw0rd", "abc123"):
        assert secret not in lowered


def test_trace_carries_bounded_served_text_and_decision_reference(tmp_path):
    harness = _real_harness(
        deceiver=_StaticDeceiver("uid=1000(webapp) gid=1000(webapp)"),
        verifier=_PassingVerifier(),
        arm="RAGIN_V4_DETERMINISTIC",
    )
    sandbox = Sandbox(harness=harness, config=SandboxConfig(session_dir=str(tmp_path / "sessions")))
    response = sandbox.handle_command("10.0.0.1", "id")
    session = Session.wake(response.session_id, session_dir=str(tmp_path / "sessions"))
    metric = session.get_events_by_type(EventType.METRIC)[-1].data
    trace = metric["trace"]

    assert trace["served_text"] == "uid=1000(webapp) gid=1000(webapp)"
    assert trace["served_text_availability"] == "REDACTED_MINIMIZED"
    assert trace["served_text_chars"] == len(trace["served_text"])
    assert trace["served_response_sha256"] == hashlib.sha256(response.response_text.encode()).hexdigest()

    strategy_events = session.get_events_by_type(EventType.STRATEGY_UPDATE)
    assert strategy_events, "non-baseline harness must emit the per-turn decision"
    assert trace["decision"]["event_id"] == strategy_events[-1].event_id
    assert trace["decision"]["availability"] == "OBSERVED_EVENT_REFERENCE"
    assert trace["decision"]["selected"]["selected_response_strategy"] in {
        "baseline",
        "credential_bait",
        "process_disclosure",
        "network_disclosure",
        "persistence",
        "lateral_movement",
    }


def test_metric_command_keeps_full_digest_but_not_raw_text(tmp_path):
    result = PipelineResult(
        session_id="s1",
        attacker_input="export API_KEY=supersecret",
        deception_response={"response_text": "done", "metadata": {}},
        verification={"passed": True, "issues": []},
    )
    sandbox = Sandbox(
        harness=_FixedResultHarness(result),
        config=SandboxConfig(session_dir=str(tmp_path / "sessions")),
    )
    response = sandbox.handle_command("10.0.0.1", "export API_KEY=supersecret")
    session = Session.wake(response.session_id, session_dir=str(tmp_path / "sessions"))
    metric = session.get_events_by_type(EventType.METRIC)[-1].data
    assert metric["command_trace"]["sha256"] == hashlib.sha256(b"export API_KEY=supersecret").hexdigest()
    assert "supersecret" not in metric["command_trace"]["text"]
    assert metric["command_trace"]["availability"] == "REDACTED_MINIMIZED"


# ── G. Verification-contract boundaries ────────────────────────────────────


def test_unverifiable_grounding_gap_is_recorded():
    """Characterization test for a known coverage gap.

    FictionConsistencyVerifier checks fiction consistency, danger signals, and
    identity pins. It does not require external evidence for an arbitrary file
    or privilege claim, so a plausible ungrounded claim can pass with no
    evidence. The assertion records the current contract; it is not a claim
    that grounding is guaranteed.
    """
    verifier = FictionConsistencyVerifier()
    verdict = verifier.verify(
        {"response_text": "root ALL=(ALL:ALL) ALL\nDefaults env_reset"},
        {"session_id": "gap-1", "attacker_input": "cat /etc/sudoers", "classification": {"skill_level": "expert"}},
    )
    assert verdict["passed"] is True
    assert verdict["issues"] == []


class _TimeoutVerifier:
    def verify(self, response, session_context):
        raise TimeoutError("simulated verifier timeout")


def test_timeout_exception_is_fail_closed_but_not_a_deadline_proof():
    """A raised TimeoutError is handled fail-closed.

    This is a simulated exception, not wall-clock deadline enforcement. No
    code path in this test starts a timer or cancels a verifier call.
    """
    harness = _real_harness(deceiver=_StaticDeceiver("root"), verifier=_TimeoutVerifier())
    verdict = harness._strict_verify({"response_text": "root"}, {})
    assert verdict["passed"] is False
    assert verdict["issues"] == ["verifier_exception:TimeoutError"]
