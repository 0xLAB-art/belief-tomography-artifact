import time

from ragin.decision.optional import LayaAssessmentAdapter


def _fixture(_: str) -> dict:
    return {
        "model": "laya-fixture-1",
        "answers": {
            "attack": {"type": "noul", "noul": 0.9},
            "severity": {"type": "score", "score": 2, "confidence": 0.8},
            "attack_kind": {"type": "choice", "choice": "scanning"},
        },
    }


def test_fixture_adapter_returns_typed_signal_with_provenance():
    result = LayaAssessmentAdapter(_fixture, model="laya-fixture-1").assess(
        session_id="s-1", state="nmap -sV"
    )

    assert result.status == "SIGNAL"
    assert result.provider == "laya"
    assert result.model == "laya-fixture-1"
    assert result.assessment is not None
    assert result.assessment.is_attack is True
    assert result.assessment.attack_kind.value == "scanning"


def test_provider_failure_returns_no_signal():
    def fail(_: str) -> dict:
        raise RuntimeError("fixture failure")

    result = LayaAssessmentAdapter(fail, model="laya-fixture-1").assess(session_id="s-1", state="x")

    assert result.status == "NO_SIGNAL"
    assert result.assessment is None
    assert result.error == "RuntimeError"


def test_provider_timeout_returns_no_signal():
    def slow(_: str) -> dict:
        time.sleep(0.05)
        return _fixture("")

    result = LayaAssessmentAdapter(slow, model="laya-fixture-1", timeout_s=0.001).assess(
        session_id="s-1", state="x"
    )

    assert result.status == "NO_SIGNAL"
    assert result.error == "timeout"
