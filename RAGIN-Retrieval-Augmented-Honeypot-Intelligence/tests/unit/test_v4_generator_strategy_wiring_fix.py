from __future__ import annotations

import hashlib

import pytest

from ragin.decision_fusion_v4.benchmark import ALLOWED_STRATEGIES
from ragin.hisoka.deceiver import AdaptiveDeceiver


def _context(strategy: str, *, legacy: bool = True) -> dict:
    context = {
        "session_id": f"synthetic-{strategy}",
        "classification": {"skill_level": "novice"},
        "policy_decision": {
            "arm": "RAGIN_V4_DETERMINISTIC",
            "selected_response_strategy": strategy,
            "fallback_reason": None,
        },
    }
    if legacy:
        context["classification"]["laya_decision"] = {
            "availability": True,
            "selected_response_strategy": "fake_success_and_return_visits",
            "normalized_decision": {"is_attack": True, "attack_kind": "persistence"},
        }
    return context


def test_v4_policy_decision_overrides_legacy_signal_and_is_consumed():
    deceiver = AdaptiveDeceiver()
    response = deceiver.generate_response("printf synthetic", _context("maximize_recon_surface"))

    assert response.metadata["strategy_source"] == "v4_policy_decision"
    assert response.metadata["selected_strategy"] == "maximize_recon_surface"
    assert response.metadata["strategy_delivered_to_generator"] is True
    assert response.metadata["strategy_consumed_by_template"] is True
    assert "service discovery: internal endpoints available" in response.response_text
    assert "change applied successfully" not in response.response_text


@pytest.mark.parametrize("strategy", [s for s in ALLOWED_STRATEGIES if s != "baseline"])
def test_all_six_v4_strategies_have_safe_template_behavior(strategy: str):
    response = AdaptiveDeceiver().generate_response("printf synthetic", _context(strategy, legacy=False))
    assert response.metadata["strategy_consumed_by_template"] is True
    assert response.metadata["template_id"] == "generic_terminal"
    assert response.metadata["template_fallback_reason"] == "no_gateway"
    assert "printf synthetic" in response.response_text


def test_invalid_v4_strategy_fails_closed_to_baseline():
    response = AdaptiveDeceiver().generate_response(
        "printf synthetic",
        {
            **_context("baseline", legacy=True),
            "policy_decision": {
                "arm": "RAGIN_V4_LOGISTIC",
                "selected_response_strategy": "not-supported",
            },
        },
    )
    assert response.metadata["strategy_source"] == "v4_policy_decision_fallback"
    assert response.metadata["selected_strategy"] == "baseline"
    assert response.metadata["policy_fallback_reason"] == "unsupported_strategy"
    assert "change applied successfully" not in response.response_text


def test_baseline_keeps_legacy_behavior():
    response = AdaptiveDeceiver().generate_response("printf synthetic", {"session_id": "baseline", "classification": {"skill_level": "novice", "laya_decision": {"availability": True, "selected_response_strategy": "fake_success_and_return_visits", "normalized_decision": {"is_attack": True, "attack_kind": "persistence"}}}})
    assert response.metadata["laya_response_strategy"] == "fake_success_and_return_visits"
    assert "change applied successfully" in response.response_text


def test_exact_matched_response_hashes_are_measured():
    hashes = {
        strategy: hashlib.sha256(
            AdaptiveDeceiver().generate_response("printf synthetic", _context(strategy, legacy=False)).response_text.encode()
        ).hexdigest()
        for strategy in ALLOWED_STRATEGIES
    }
    assert len(set(hashes.values())) == len(hashes)
