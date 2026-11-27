"""Tests for the Jev System One integration (ragin.jev).

Covers: question builders, typed-answer parsing, JevClient request/response
handling (mocked transport), JevAssessor state building, the Reviewer-protocol
adapter, the Supervisor mixin, and the Chrollo additive integration. All
HTTP is mocked — no live calls.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from ragin.chrollo.models import CommandEntry, SessionLog
from ragin.chrollo.pipeline import ChrolloPipeline
from ragin.cycle.coordination import RiskLevel, Supervisor
from ragin.jev.assessment import JevAssessor, JevError
from ragin.jev.client import JevClient
from ragin.jev.models import (
    AttackKind,
    ChoiceAnswer,
    JevAssessment,
    NoulAnswer,
    ScoreAnswer,
    choice_question,
    noul_question,
    parse_answer,
    score_question,
)
from ragin.jev.orchestration import JevReviewer, JevRoutingSignal, SupervisorJevMixin

pytestmark = pytest.mark.unit


# ── Fixtures ─────────────────────────────────────────────────────────────────


def _sample_response(*, attack: float = 0.9, severity: float = 2.0, model: str = "jev-1.14-free") -> dict:
    return {
        "model": model,
        "answers": {
            "attack": {"type": "noul", "noul": attack},
            "severity": {
                "type": "score",
                "score": severity,
                "confidence": 0.7,
                "legend": {"0": "benign", "1": "low", "2": "suspicious", "3": "critical"},
                "probabilities": {"0": 0.0, "1": 0.0, "2": 1.0, "3": 0.0},
            },
            "attack_kind": {
                "type": "choice",
                "choice": ["bruteforce"],
                "allow_multi": True,
                "probabilities": {"bruteforce": 0.8},
            },
        },
        "usage": {"input_tokens": 300, "output_tokens": 40},
        "cost": "0",
    }


def _fake_response(payload: dict | None = None) -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = payload or _sample_response()
    return resp


def _make_assessment(payload: dict) -> JevAssessment:
    """Build a JevAssessment from an API-style payload (test helper)."""
    from ragin.jev.models import JevResponse

    response = JevResponse.from_payload(payload)
    return JevAssessment(
        session_id="sess_test",
        answers=response.answers,
        model=response.model,
        usage=response.usage,
    )


def _make_session(**overrides) -> SessionLog:
    return SessionLog(
        session_id=overrides.pop("session_id", "sess_test"),
        start_time=overrides.pop("start_time", "2026-09-20T10:00:00Z"),
        commands=[
            CommandEntry(
                timestamp="2026-09-20T10:00:00Z",
                command="cat /etc/passwd",
                user="root",
                exit_code=0,
                output_length=500,
            )
        ],
        **overrides,
    )


# ── Question builders ────────────────────────────────────────────────────────


class TestQuestionBuilders:
    def test_noul_question_shape(self):
        q = noul_question("Is this an attack?", true_criteria="yes text", false_criteria="no text")
        assert q.type == "noul"
        assert q.model_dump_for_api() == {
            "instructions": "Is this an attack?",
            "type": "noul",
            "criteria": {"true": "yes text", "false": "no text"},
        }

    def test_score_question_shape_and_length_validation(self):
        q = score_question("severity?", minimum=0, maximum=3, criteria=["a", "b", "c", "d"])
        assert q.type == "score"
        assert q.min == 0
        assert q.max == 3
        wire = q.model_dump_for_api()
        assert wire["criteria"] == ["a", "b", "c", "d"]

        with pytest.raises(ValueError, match="score criteria length"):
            score_question("bad", minimum=0, maximum=3, criteria=["a", "b"])

    def test_choice_question_shape(self):
        q = choice_question("kind?", options=["bruteforce", "scanning"], allow_multi=True)
        assert q.type == "choice"
        assert q.allow_multi is True
        wire = q.model_dump_for_api()
        assert wire["options"] == ["bruteforce", "scanning"]

        with pytest.raises(ValueError, match="requires at least one option"):
            choice_question("empty", options=[])


# ── Answer parsing ───────────────────────────────────────────────────────────


class TestAnswerParsing:
    def test_parse_noul(self):
        ans = parse_answer({"type": "noul", "noul": 0.83})
        assert isinstance(ans, NoulAnswer)
        assert ans.noul == 0.83

    def test_parse_score(self):
        ans = parse_answer(
            {
                "type": "score",
                "score": 2.5,
                "confidence": 0.53,
                "legend": {"0": "a", "1": "b", "2": "c", "3": "d"},
                "probabilities": {"0": 0.1, "1": 0.2, "2": 0.3, "3": 0.4},
            }
        )
        assert isinstance(ans, ScoreAnswer)
        assert ans.top_label == "d"  # highest probability bin
        assert abs(ans.top_probability - 0.4) < 1e-6

    def test_parse_choice_single(self):
        ans = parse_answer({"type": "choice", "choice": "bruteforce", "probabilities": {}})
        assert isinstance(ans, ChoiceAnswer)
        assert ans.options_selected == ["bruteforce"]

    def test_parse_choice_multi(self):
        ans = parse_answer({"type": "choice", "choice": ["a", "b"], "allow_multi": True})
        assert isinstance(ans, ChoiceAnswer)
        assert ans.options_selected == ["a", "b"]

    def test_parse_unknown_type_raises(self):
        with pytest.raises(ValueError, match="Unknown Jev answer type"):
            parse_answer({"type": "text", "text": "nope"})


# ── JevClient ────────────────────────────────────────────────────────────────


class TestJevClient:
    def test_payload_construction_and_url(self):
        with patch("requests.Session.post") as mock_post:
            mock_post.return_value = _fake_response()
            client = JevClient(base_url="http://fake/v1", api_key="k", model="jev-test")
            client.systemone(
                state="some state",
                questions={
                    "attack": noul_question("attack?", true_criteria="t", false_criteria="f"),
                },
            )
            mock_post.assert_called_once()
            call = mock_post.call_args
            assert call[0][0] == "http://fake/v1/systemone"
            headers = call[1]["headers"]
            assert headers["Authorization"] == "Bearer k"
            payload = call[1]["json"]
            assert payload["model"] == "jev-test"
            assert payload["state"] == "some state"
            assert payload["questions"]["attack"]["type"] == "noul"

    def test_transient_status_retries_then_raises(self):
        resp429 = MagicMock()
        resp429.status_code = 429
        resp429.raise_for_status.side_effect = __import__("requests").HTTPError
        with patch("requests.Session.post", side_effect=[resp429, resp429]) as mock_post:
            client = JevClient(base_url="http://fake/v1", timeout=5)
            with pytest.raises(__import__("requests").ReadTimeout):
                client.systemone("state", {"q": noul_question("q?", true_criteria="t", false_criteria="f")})
            assert mock_post.call_count == 2

    def test_assess_wraps_into_jev_assessment(self):
        with patch("requests.Session.post") as mock_post:
            mock_post.return_value = _fake_response()
            client = JevClient(base_url="http://fake/v1")
            assessment = client.assess(
                session_id="s-1",
                state="some state",
                questions=JevAssessor.default_questions(),
            )
            assert isinstance(assessment, JevAssessment)
            assert assessment.session_id == "s-1"
            assert assessment.noul_probability("attack") == 0.9
            assert assessment.score_value("severity") == 2.0
            assert assessment.attack_kind == AttackKind.BRUTEFORCE
            assert assessment.is_attack is True

    def test_env_resolution_selects_configured_endpoint_and_model(self, monkeypatch):
        """RAGIN_JEVI_* env vars must drive the client, incl. the supplied
        BeatAPI Decisions endpoint shape (base + /systemone, model jev-1.14-free).
        """
        monkeypatch.setenv("RAGIN_JEVI_BASE_URL", "https://api.beatapi.io/v1")
        monkeypatch.setenv("RAGIN_JEVI_API_KEY", "k")
        monkeypatch.setenv("RAGIN_JEVI_MODEL", "jev-1.14-free")
        client = JevClient()
        assert client.base_url == "https://api.beatapi.io/v1"
        assert client.model == "jev-1.14-free"
        with patch("requests.Session.post") as mock_post:
            mock_post.return_value = _fake_response()
            client.systemone(
                state="some state",
                questions={
                    "attack": noul_question("attack?", true_criteria="t", false_criteria="f"),
                },
            )
            assert mock_post.call_args[0][0] == "https://api.beatapi.io/v1/systemone"
            assert mock_post.call_args[1]["json"]["model"] == "jev-1.14-free"

    def test_defaults_when_env_unset(self, monkeypatch):
        for key in ("RAGIN_JEVI_BASE_URL", "RAGIN_JEVI_API_KEY", "RAGIN_JEVI_MODEL"):
            monkeypatch.delenv(key, raising=False)
        client = JevClient()
        assert client.base_url == "https://api.beatapi.io/v1"
        assert client.model == "jev-1.14-free"


# ── JevAssessor ──────────────────────────────────────────────────────────────


class TestJevAssessor:
    def test_state_from_session_log_includes_commands(self):
        session = _make_session()
        state = JevAssessor.state_from_session_log(session)
        assert "cat /etc/passwd" in state
        assert state.startswith("session ")  # session_id is sha256-hashed by SessionLog

    def test_state_from_commands(self):
        state = JevAssessor.state_from_commands(["ls -la", "whoami"], context="ctx line")
        assert state.startswith("ctx line")
        assert "ls -la" in state

    def test_default_questions_cover_decision_set(self):
        questions = JevAssessor.default_questions()
        assert set(questions) == {"attack", "severity", "attack_kind"}

    def test_disabled_assessor_raises(self):
        assessor = JevAssessor(enabled=False)
        with pytest.raises(JevError):
            assessor.assess_session(_make_session())

    def test_assess_session(self):
        with patch("requests.Session.post") as mock_post:
            mock_post.return_value = _fake_response()
            assessor = JevAssessor()
            assessment = assessor.assess_session(_make_session())
            assert assessment.is_attack is True
            assert assessment.severity == 2.0

    def test_assess_context_empty_returns_none(self):
        assessor = JevAssessor()
        with patch("requests.Session.post") as mock_post:
            assert assessor.assess_context({"session_id": "s"}) is None
            mock_post.assert_not_called()


# ── JevAssessment convenience ────────────────────────────────────────────────


class TestJevAssessmentHelpers:
    def test_missing_keys_return_none_or_empty(self):
        assessment = _make_assessment({"answers": {}})
        assert assessment.is_attack is None
        assert assessment.severity is None
        assert assessment.attack_kind is None

    def test_to_dict_serialises_answers(self):
        assessment = JevAssessment(
            session_id="s",
            answers={"attack": NoulAnswer(noul=0.5)},
        )
        as_dict = assessment.to_dict()
        assert as_dict["answers"]["attack"]["type"] == "noul"


# ── JevRoutingSignal ─────────────────────────────────────────────────────────


class TestJevRoutingSignal:
    def _assessment(self, severity: float = 2.0, attack: float = 0.9):
        payload = _sample_response(attack=attack, severity=severity)
        return _make_assessment(payload)

    def test_risk_level_from_severity(self):
        signal = JevRoutingSignal(self._assessment(severity=3.0))
        assert signal.risk_level == "critical"

    def test_no_assessment_returns_empty(self):
        signal = JevRoutingSignal(None)
        assert signal.available is False
        assert signal.risk_level == ""
        assert signal.adjust_risk("low") == "low"

    def test_adjust_risk_picks_higher(self):
        signal = JevRoutingSignal(self._assessment(severity=2.0))
        assert signal.adjust_risk("low") == "high"
        assert signal.adjust_risk("critical") == "critical"


# ── JevReviewer (Reviewer protocol) ──────────────────────────────────────────


class TestJevReviewer:
    def _reviewer(self, action: str = "return"):
        assessor = MagicMock()
        assessor.assess_context.return_value = _make_assessment(_sample_response())
        return JevReviewer(assessor=assessor)

    def test_review_fails_on_high_attack_probability(self):
        reviewer = self._reviewer()
        result = reviewer.review({"response_text": "x"}, {"attacker_inputs": ["cat /etc/shadow"]})
        assert result["passed"] is False
        assert any("attack" in issue for issue in result["issues"])

    def test_review_passes_on_benign(self):
        assessor = MagicMock()
        assessor.assess_context.return_value = _make_assessment(_sample_response(attack=0.1, severity=0.0))
        reviewer = JevReviewer(threshold=0.7, severity_cap=1, assessor=assessor)
        result = reviewer.review({"response_text": "x"}, {"attacker_inputs": ["ls"]})
        assert result["passed"] is True

    def test_review_handles_missing_assessment(self):
        assessor = MagicMock()
        assessor.assess_context.return_value = None
        reviewer = JevReviewer(assessor=assessor)
        result = reviewer.review({}, {})
        assert result["passed"] is True

    def test_review_handles_exception(self):
        assessor = MagicMock()
        assessor.assess_context.side_effect = RuntimeError("boom")
        reviewer = JevReviewer(assessor=assessor)
        result = reviewer.review({}, {})
        assert result["passed"] is True


# ── Supervisor + Jev mixin ───────────────────────────────────────────────────


class TestSupervisorJevMixin:
    def test_mixin_adjusts_risk_when_jev_available(self):
        class CustomSupervisor(SupervisorJevMixin, Supervisor):
            pass

        assessor = MagicMock()
        assessor.assess_context.return_value = _make_assessment(_sample_response(severity=3.0))
        supervisor = CustomSupervisor(assessor=assessor)
        decision = supervisor.route_with_jev(
            session_context={"interaction_count": 2},
            classification={"skill_level": "novice", "confidence": 0.9},
            session_id="s-2",
        )
        assert decision.risk_level == RiskLevel.CRITICAL
        assert any("Jev:" in e for e in decision.context_enrichments)

    def test_mixin_unaffected_when_jev_unavailable(self):
        class CustomSupervisor(SupervisorJevMixin, Supervisor):
            pass

        assessor = MagicMock()
        assessor.assess_context.return_value = None
        supervisor = CustomSupervisor(assessor=assessor)
        decision = supervisor.route_with_jev(
            session_context={"interaction_count": 2},
            classification={"skill_level": "novice", "confidence": 0.9},
            session_id="s-3",
        )
        # Novice + low depth -> low risk, unchanged by Jev absence
        assert decision.risk_level == RiskLevel.LOW


# ── Chrollo additive integration ─────────────────────────────────────────────


class TestChrolloJevIntegration:
    def _pipeline_with_fake_classifier(self):
        classifier = MagicMock()
        classifier.classify.return_value = type(
            "Result",
            (),
            {
                "skill_level": "intermediate",
                "confidence": 0.8,
                "features_used": ["x"],
                "session_id": "sess_test",
                "jev_assessment": None,
            },
        )()
        pipeline = ChrolloPipeline(classifier=classifier, gateway_url="http://localhost:9999")
        return pipeline

    def test_process_with_jev_enriches_result(self):
        pipeline = self._pipeline_with_fake_classifier()
        with patch("requests.Session.post") as mock_post:
            mock_post.return_value = _fake_response()
            result = pipeline.process_with_jev(_make_session())
        assert result.jev_assessment is not None
        assert result.jev_assessment["answers"]["attack"]["noul"] == 0.9

    def test_process_with_jev_skips_when_disabled(self):
        pipeline = self._pipeline_with_fake_classifier()
        imported = {}

        with patch.dict("os.environ", {"RAGIN_JEVI_ENABLED": "0"}), patch("requests.Session.post") as mock_post:
            result = pipeline.process_with_jev(_make_session())
        assert result.jev_assessment is None
        imported["called"] = mock_post.called
        assert not imported["called"]
