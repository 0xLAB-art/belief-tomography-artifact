from __future__ import annotations

import pytest

from ragin.hisoka.strategy_generator_v1 import (
    STRATEGY_GENERATOR_VERSION,
    StrategyAwareDeceptionGeneratorV1,
)

STRATEGIES = (
    "maximize_recon_surface",
    "fake_success_and_return_visits",
    "steer_to_honeytoken_credentials",
    "expose_decoy_internal_topology",
    "contain_in_fiction_and_instrument",
    "low_intensity_administration",
)


def test_all_nonbaseline_strategies_have_substantive_semantics():
    traces = []
    for strategy in STRATEGIES:
        generator = StrategyAwareDeceptionGeneratorV1(f"synthetic-{strategy}", seed=17)
        first = generator.generate("status", strategy)
        assert first.response_text
        assert first.instrumentation["mode"] == STRATEGY_GENERATOR_VERSION
        assert first.instrumentation["attacker_command_executed"] is False
        traces.append((strategy, first.response_text, first.proposed_state))
    assert len({response for _, response, _ in traces}) == len(STRATEGIES)


def test_semantic_effects_survive_decorative_marker_removal():
    commands = {
        "maximize_recon_surface": "ls -la",
        "fake_success_and_return_visits": "deploy fictional-app",
        "steer_to_honeytoken_credentials": "credentials",
        "expose_decoy_internal_topology": "ss -tlnp",
        "contain_in_fiction_and_instrument": "apply change",
        "low_intensity_administration": "status service",
    }
    for strategy, command in commands.items():
        generator = StrategyAwareDeceptionGeneratorV1(f"semantic-{strategy}", seed=3)
        candidate = generator.generate(command, strategy)
        assert "service discovery: internal endpoints available" not in candidate.response_text
        assert "administration request completed" not in candidate.response_text
        assert candidate.proposed_state != generator.state or strategy == "low_intensity_administration"


def test_multiturn_state_is_consistent_and_persists_only_after_commit():
    generator = StrategyAwareDeceptionGeneratorV1("synthetic-continuity", seed=9)
    candidate = generator.generate("deploy fictional-app", "fake_success_and_return_visits")
    assert generator.state.completed_operations == ()
    assert generator.commit(candidate, verifier_passed=True, hitl_approved=True)["committed"] is True
    followup = generator.generate("status operation", "fake_success_and_return_visits")
    assert generator.state.completed_operations
    assert generator.state.completed_operations[-1] in followup.response_text


def test_rejected_candidate_never_mutates_fictional_state():
    generator = StrategyAwareDeceptionGeneratorV1("synthetic-rejection", seed=4)
    before = generator.state
    candidate = generator.generate("show credentials", "steer_to_honeytoken_credentials")
    assert generator.commit(candidate, verifier_passed=False, hitl_approved=True)["committed"] is False
    assert generator.state == before
    assert generator.commit(candidate, verifier_passed=True, hitl_approved=False)["committed"] is False
    assert generator.state == before


def test_invalid_strategy_and_unallowlisted_command_fail_safe():
    generator = StrategyAwareDeceptionGeneratorV1("synthetic-safe", seed=2)
    with pytest.raises(ValueError):
        generator.generate("status", "not-a-strategy")
    before = generator.state
    candidate = generator.generate("python -c do_not_run", "maximize_recon_surface")
    assert candidate.action == "unsupported"
    assert candidate.proposed_state == before
    assert generator.commit(candidate, verifier_passed=True, hitl_approved=True)["committed"] is True
    assert generator.state == before


def test_baseline_delegates_without_strategy_suffix_or_state_mutation():
    generator = StrategyAwareDeceptionGeneratorV1("synthetic-baseline", seed=1)
    before = generator.state
    result = generator.generate("whoami", "baseline")
    assert result.response_text == generator._baseline.generate("novice", "whoami")
    assert result.proposed_state == before
    assert result.metadata["strategy_consumed_by_template"] is False
