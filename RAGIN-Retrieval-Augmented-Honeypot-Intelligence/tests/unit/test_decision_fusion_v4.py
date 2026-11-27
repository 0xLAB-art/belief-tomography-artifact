from __future__ import annotations

import copy

from ragin.decision_fusion_v4 import EvidenceQualityGate, deterministic_policy, generate_corpus, run_policy


def valid_bundle() -> dict:
    return generate_corpus("V4D-", 1, 17)[0].state


def test_valid_multi_document_evidence_passes() -> None:
    bundle = valid_bundle()
    result = EvidenceQualityGate().evaluate(bundle)
    assert result["gate_state"] == "VALID_EVIDENCE"


def test_fail_closed_contract_cases() -> None:
    base = valid_bundle()
    cases = []
    malformed = copy.deepcopy(base)
    malformed.pop("retrieval")
    cases.append(malformed)
    missing = copy.deepcopy(base)
    missing["retrieval"].pop("query_coverage")
    cases.append(missing)
    failure = copy.deepcopy(base)
    failure["retrieval"]["retrieval_status"] = "FAILURE"
    cases.append(failure)
    degraded = copy.deepcopy(base)
    degraded["retrieval"]["retrieval_status"] = "DEGRADED"
    cases.append(degraded)
    no_docs = copy.deepcopy(base)
    no_docs["retrieval"]["documents"] = []
    no_docs["retrieval"]["relevant_doc_ids"] = []
    no_docs["retrieval"]["relevant_count"] = 0
    cases.append(no_docs)
    incomplete = copy.deepcopy(base)
    incomplete["retrieval"]["query_coverage"]["complete"] = False
    cases.append(incomplete)
    for key, value in (("provenance_status", "INVALID"), ("provenance_status", "UNKNOWN"), ("sanitization_status", "UNSANITIZED"), ("sanitization_status", "UNKNOWN"), ("conflict_status", "UNRESOLVED")):
        altered = copy.deepcopy(base)
        altered["retrieval"]["documents"][0][key] = value
        cases.append(altered)
    duplicate = copy.deepcopy(base)
    duplicate["retrieval"]["documents"].append(copy.deepcopy(duplicate["retrieval"]["documents"][0]))
    cases.append(duplicate)
    inconsistent = copy.deepcopy(base)
    inconsistent["retrieval"]["documents"].append(copy.deepcopy(inconsistent["retrieval"]["documents"][0]))
    inconsistent["retrieval"]["documents"][-1]["content"] = "different"
    cases.append(inconsistent)
    for altered in cases:
        assert EvidenceQualityGate().evaluate(altered)["gate_state"] != "VALID_EVIDENCE"


def test_policy_is_not_called_when_gate_is_invalid() -> None:
    called = False

    def engine(_bundle, _refs):
        nonlocal called
        called = True
        return deterministic_policy(_bundle, _refs)

    bundle = valid_bundle()
    gate_result = {"gate_state": "LOW_RELEVANCE", "valid_doc_ids": []}
    result = run_policy(engine, bundle, gate_result)
    assert result["selected_response_strategy"] == "baseline"
    assert called is False


def test_low_score_relevant_and_high_score_noise_do_not_use_numeric_threshold() -> None:
    cases = generate_corpus("V4D-", 1, 17)
    low = next(case for case in cases if case.stratum == "low_score_relevant")
    high = next(case for case in cases if case.stratum == "high_score_irrelevant")
    assert EvidenceQualityGate().evaluate(low.state)["gate_state"] == "VALID_EVIDENCE"
    assert EvidenceQualityGate().evaluate(high.state)["gate_state"] == "VALID_EVIDENCE"
