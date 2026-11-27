"""Synthetic payload regression tests; never load or invoke a model."""
import pytest

from ragin.decision.laya_decision import normalize_laya_payload


@pytest.mark.parametrize("choice", [[], {}, ["recon"]])
def test_unhashable_stage_is_treated_as_unknown(choice):
    signal = normalize_laya_payload({"answers": {
        "attack": {"noul": 0.9}, "stage": {"choice": choice},
    }})
    assert signal.stage is None
    assert signal.attack_kind is None


@pytest.mark.parametrize("probability", [-0.1, 1.1, True, float("nan"), float("inf")])
def test_invalid_attack_probability_produces_no_signal(probability):
    signal = normalize_laya_payload({"answers": {"attack": {"noul": probability}}})
    assert not signal.available
    assert signal.is_attack is None
    assert signal.attack_probability is None


@pytest.mark.parametrize("probability", [0.0, 0.5, 1.0])
def test_probability_boundaries_remain_valid(probability):
    signal = normalize_laya_payload({"answers": {"attack": {"noul": probability}}})
    assert signal.available
    assert signal.attack_probability == probability


def test_out_of_domain_auxiliary_values_are_not_exposed():
    signal = normalize_laya_payload({"answers": {
        "attack": {"noul": 0.9, "answer_confidence": 1.1},
        "severity": {"score": 4},
    }})
    assert signal.confidence is None
    assert signal.severity is None
