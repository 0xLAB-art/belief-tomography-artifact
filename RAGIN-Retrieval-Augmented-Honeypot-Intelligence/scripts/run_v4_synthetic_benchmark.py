from __future__ import annotations

import hashlib
import json
import os
import statistics
import sys
import time
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import LogisticRegression

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ragin.decision_fusion_v4 import EvidenceQualityGate, deterministic_policy, extract_features, generate_corpus, run_policy
from ragin.decision_fusion_v4.benchmark import STRATA, SyntheticCase

OUT = ROOT / "results" / "decision_fusion_v4"
GATE = EvidenceQualityGate()
SEED = 20261014
THRESHOLDS = {
    "gate_fail_safe_recall": 0.95,
    "invalid_or_insufficient_pass_through": 0.05,
    "strategy_compatibility": 0.80,
    "catastrophic_rate": 0.05,
    "schema_compliance": 1.0,
}


def dump(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def binomial_ci(successes: int, total: int) -> dict[str, Any]:
    if total == 0:
        return {"numerator": 0, "denominator": 0, "estimate": None, "ci95": [None, None]}
    p = successes / total
    z = 1.959963984540054
    den = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / den
    half = z * ((p * (1 - p) / total + z * z / (4 * total * total)) ** 0.5) / den
    return {"numerator": successes, "denominator": total, "estimate": p, "ci95": [max(0.0, centre - half), min(1.0, centre + half)]}


def write_corpus(path: Path, cases: list[SyntheticCase], seed: int, phase: str) -> None:
    counts = {stratum: sum(case.stratum == stratum for case in cases) for stratum in STRATA}
    payload = {
        "schema": f"ragin.decision_fusion_v4.{phase}_corpus_freeze.v1",
        "status": "FROZEN_BEFORE_POLICY_EXECUTION",
        "phase": phase,
        "N": len(cases),
        "generator": "ragin.decision_fusion_v4.benchmark.generate_corpus",
        "generator_version": "v4.1.synthetic_templates.1",
        "rng_seed": seed,
        "template_policy": "development and validation use disjoint case IDs and validation-specific template prefixes/content",
        "strata": list(STRATA),
        "stratum_distribution": counts,
        "evidence_schema": "ragin.don.evidence_bundle.v4",
        "oracle_schema": "SYNTHETIC_CONTRACT_ORACLE",
        "cases": [case.to_dict() for case in cases],
        "scientific_boundary": {
            "real_ground_truth": False,
            "prior_ragin_holdout_used": False,
            "prior_laya_v3_cases_used": False,
        },
    }
    dump(path, payload)


def gate_metrics(cases: list[SyntheticCase]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    rows = []
    for case in cases:
        result = GATE.evaluate(case.state)
        expected = case.oracle["evidence_gate_expected"]
        rows.append({"case_id": case.case_id, "expected": expected, "observed": result, "agreement": result["gate_state"] == expected})
    nonvalid = [row for row in rows if row["expected"] != "VALID_EVIDENCE"]
    invalid = [row for row in nonvalid if row["expected"] in {"INVALID_PROVENANCE", "UNRESOLVED_CONFLICT", "RETRIEVAL_FAILURE", "NO_EVIDENCE", "LOW_RELEVANCE"}]
    metrics = {
        "gate_state_contract_alignment": binomial_ci(sum(row["agreement"] for row in rows), len(rows)),
        "fail_safe_recall": binomial_ci(sum(row["observed"]["gate_state"] != "VALID_EVIDENCE" for row in nonvalid), len(nonvalid)),
        "invalid_or_insufficient_pass_through": binomial_ci(sum(row["observed"]["gate_state"] == "VALID_EVIDENCE" for row in invalid), len(invalid)),
        "N": len(rows),
        "nonvalid_N": len(nonvalid),
    }
    return metrics, rows


def policy_metrics(cases: list[SyntheticCase], engine: Any, engine_id: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    rows = []
    latencies = []
    valid_cases = []
    for case in cases:
        gate_result = GATE.evaluate(case.state)
        if gate_result["gate_state"] != "VALID_EVIDENCE":
            continue
        valid_cases.append(case)
        start = time.perf_counter_ns()
        output = run_policy(engine, case.state, gate_result)
        latencies.append((time.perf_counter_ns() - start) / 1_000_000)
        allowed = set(case.oracle["allowed_strategies_if_valid"])
        supporting = set(case.oracle["supporting_evidence_ids"])
        strategy = output.get("selected_response_strategy")
        refs = output.get("supporting_evidence_refs")
        schema_ok = (
            output.get("schema") == "ragin.decision_fusion_v4.policy_decision.v1"
            and strategy in set(__import__("ragin.decision_fusion_v4", fromlist=["ALLOWED_STRATEGIES"]).ALLOWED_STRATEGIES)
            and isinstance(refs, list)
        )
        ref_ok = schema_ok and bool(set(refs).issubset(supporting)) and bool(refs)
        compatible = schema_ok and strategy in allowed
        catastrophic = schema_ok and strategy in set(case.oracle["forbidden_strategies"])
        rows.append({"case_id": case.case_id, "engine": engine_id, "output": output, "strategy_compatible": compatible, "catastrophic": catastrophic, "reference_compatible": ref_ok, "schema_valid": schema_ok})
    total = len(rows)
    metrics = {
        "engine": engine_id,
        "valid_evidence_N": total,
        "strategy_compatibility": binomial_ci(sum(row["strategy_compatible"] for row in rows), total),
        "catastrophic_rate": binomial_ci(sum(row["catastrophic"] for row in rows), total),
        "reference_compatibility": binomial_ci(sum(row["reference_compatible"] for row in rows), total),
        "schema_compliance": binomial_ci(sum(row["schema_valid"] for row in rows), total),
        "latency_ms": {"mean": statistics.mean(latencies) if latencies else None, "median": statistics.median(latencies) if latencies else None, "p90": float(np.percentile(latencies, 90)) if latencies else None},
    }
    return metrics, rows


def train_models(cases: list[SyntheticCase]) -> tuple[dict[str, Any], DictVectorizer, Any, Any]:
    gate_valid = [(case, GATE.evaluate(case.state)) for case in cases]
    train = [(case, gate) for case, gate in gate_valid if gate["gate_state"] == "VALID_EVIDENCE"]
    vectors = [extract_features(case.state, gate["valid_doc_ids"]) for case, gate in train]
    labels = [case.oracle["allowed_strategies_if_valid"][0] for case, _gate in train]
    vectorizer = DictVectorizer(sparse=False)
    matrix = vectorizer.fit_transform(vectors)
    logistic = LogisticRegression(max_iter=2000, random_state=SEED, solver="lbfgs")
    logistic.fit(matrix, labels)
    boosted = GradientBoostingClassifier(random_state=SEED, n_estimators=80, max_depth=2, learning_rate=0.08)
    boosted.fit(matrix, labels)
    dump_path = OUT / "v4_dev_logistic_policy.joblib"
    joblib.dump({"vectorizer": vectorizer, "model": logistic}, dump_path)
    dump(OUT / "v4_dev_gradient_boosted_policy.joblib.json", {"model_type": "development_only", "note": "binary metadata; selected model artifact is frozen separately"})
    summary = {"training_N": len(train), "feature_count": len(vectorizer.feature_names_), "feature_map": sorted(vectorizer.feature_names_), "seed": SEED, "label_counts": {label: labels.count(label) for label in sorted(set(labels))}}
    return summary, vectorizer, logistic, boosted


def model_engine(vectorizer: DictVectorizer, model: Any):
    def engine(bundle: dict[str, Any], refs: list[str]) -> dict[str, Any]:
        features = vectorizer.transform([extract_features(bundle, refs)])
        strategy = str(model.predict(features)[0])
        return {
            "schema": "ragin.decision_fusion_v4.policy_decision.v1",
            "policy_engine_id": "learned_candidate",
            "selected_response_strategy": strategy,
            "supporting_evidence_refs": list(refs[:1]),
            "policy_reason_code": "learned_structured_features",
            "input_digest": hashlib.sha256(json.dumps(bundle, sort_keys=True).encode()).hexdigest(),
        }
    return engine


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    amendment = json.loads((OUT / "synthetic_benchmark_protocol_amendment_v1a.json").read_text())
    if amendment["benchmark_executed_before_amendment"] or amendment["development_outputs_seen"] or amendment["validation_outputs_seen"] or amendment["candidate_selected"]:
        raise RuntimeError("amendment was not pre-execution")
    dev = generate_corpus("V4D-", 12, SEED)
    if len(dev) != 192 or [case.case_id for case in dev] != [f"V4D-{i:04d}" for i in range(1, 193)]:
        raise RuntimeError("development corpus shape mismatch")
    write_corpus(OUT / "v4_development_corpus_freeze_v1.json", dev, SEED, "development")
    gate_dev, gate_rows = gate_metrics(dev)
    dump(OUT / "v4_evidence_gate_development_results_v1.json", {"schema": "ragin.decision_fusion_v4.evidence_gate_development_results.v1", "status": "COMPLETE", "metrics": gate_dev, "case_results": gate_rows, "oracle_type": "SYNTHETIC_CONTRACT_ORACLE"})
    train_summary, vectorizer, logistic, boosted = train_models(dev)
    det_metrics, det_rows = policy_metrics(dev, lambda bundle, refs: deterministic_policy(bundle, refs), "deterministic_v1")
    log_metrics, log_rows = policy_metrics(dev, model_engine(vectorizer, logistic), "logistic_regression_v1")
    boost_metrics, boost_rows = policy_metrics(dev, model_engine(vectorizer, boosted), "gradient_boosted_tree_v1")
    dump(OUT / "v4_deterministic_policy_development_v1.json", {"schema": "ragin.decision_fusion_v4.deterministic_policy_development.v1", "status": "COMPLETE", "rule_table_version": "deterministic_v1", "rules": ["credential_access", "persistence", "reconnaissance", "exploitation", "data_access", "benign_administration", "baseline_fallback"], "metrics": det_metrics, "case_results": det_rows})
    dump(OUT / "v4_learned_policy_development_v1.json", {"schema": "ragin.decision_fusion_v4.learned_policy_development.v1", "status": "COMPLETE", "feature_map": train_summary, "candidates": [{"family": "multinomial_logistic_regression", "hyperparameters": {"max_iter": 2000, "solver": "lbfgs", "multi_class": "multinomial", "random_state": SEED}, "metrics": log_metrics, "case_results": log_rows}, {"family": "gradient_boosted_tree_classifier", "hyperparameters": {"n_estimators": 80, "max_depth": 2, "learning_rate": 0.08, "random_state": SEED}, "metrics": boost_metrics, "case_results": boost_rows}], "selection_rule": "development-only metrics, then deterministic tie-break to logistic regression if candidates are tied"})
    local_inventory = json.loads((OUT / "local_instruction_model_inventory_v1.json").read_text())
    if local_inventory["classification"] != "LOCAL_INSTRUCTION_CANDIDATE_UNAVAILABLE":
        raise RuntimeError("unexpected local instruction inventory status")
    selected_model = OUT / "v4_selected_logistic_policy.joblib"
    joblib.dump({"vectorizer": vectorizer, "model": logistic}, selected_model)
    candidate_freeze = {
        "schema": "ragin.decision_fusion_v4.candidate_freeze.v1",
        "status": "FROZEN_BEFORE_VALIDATION_CORPUS",
        "evidence_gate": {"implementation": "ragin/decision_fusion_v4/benchmark.py", "implementation_sha256": sha(ROOT / "ragin/decision_fusion_v4/benchmark.py"), "contract": "results/decision_fusion_v4/evidence_gate_contract_v1.json", "rule_precedence": "malformed/failure -> retrieval failure; provenance/sanitization/duplicates -> invalid provenance; unresolved conflict; no evidence; low coverage; valid evidence"},
        "deterministic": {"version": "deterministic_v1", "rule_table": ["credential_access", "persistence", "reconnaissance", "exploitation", "data_access", "benign_administration", "baseline_fallback"]},
        "learned": {"selected_family": "multinomial_logistic_regression", "feature_map": train_summary, "algorithm": "LogisticRegression", "hyperparameters": {"max_iter": 2000, "solver": "lbfgs", "multi_class_behavior": "library_default_for_multiclass", "random_state": SEED}, "trained_model_path": str(selected_model.relative_to(ROOT)), "trained_model_sha256": sha(selected_model)},
        "instruction": {"available": False, "classification": "LOCAL_INSTRUCTION_CANDIDATE_UNAVAILABLE"},
        "hardware": {"python": os.sys.version.split()[0], "device": "CPU", "numpy": np.__version__},
        "latency_timing": "time.perf_counter_ns around policy call only; gate and policy reported separately",
        "evaluation_code": {"path": "scripts/run_v4_synthetic_benchmark.py", "sha256": sha(Path(__file__))},
        "advancement_thresholds": THRESHOLDS,
        "validation_tuning_locked": True,
    }
    dump(OUT / "v4_candidate_freeze_v1.json", candidate_freeze)
    val = generate_corpus("V4V-", 6, SEED + 1)
    if len(val) != 96 or [case.case_id for case in val] != [f"V4V-{i:04d}" for i in range(1, 97)]:
        raise RuntimeError("validation corpus shape mismatch")
    dev_ids = {case.case_id for case in dev}
    if dev_ids.intersection(case.case_id for case in val):
        raise RuntimeError("development/validation overlap")
    write_corpus(OUT / "v4_validation_corpus_freeze_v1.json", val, SEED + 1, "validation")
    gate_val, gate_val_rows = gate_metrics(val)
    policy_candidates = [("deterministic_v1", lambda bundle, refs: deterministic_policy(bundle, refs)), ("logistic_regression_v1", model_engine(vectorizer, logistic))]
    validation_policy = {}
    for engine_id, engine in policy_candidates:
        validation_policy[engine_id], _rows = policy_metrics(val, engine, engine_id)
    dump(OUT / "v4_locked_validation_results_v1.json", {"schema": "ragin.decision_fusion_v4.locked_validation_results.v1", "status": "COMPLETE_LOCKED_VALIDATION", "N": 96, "gate": gate_val, "policy": validation_policy, "repeatability": {"preregistered": False, "status": "not required for deterministic candidates"}, "confidence_intervals": "Wilson 95% intervals reported for every rate", "no_selective_reruns": True})
    decisions = {}
    gate_pass = gate_val["fail_safe_recall"]["estimate"] >= THRESHOLDS["gate_fail_safe_recall"] and gate_val["invalid_or_insufficient_pass_through"]["estimate"] <= THRESHOLDS["invalid_or_insufficient_pass_through"]
    for engine_id, metrics in validation_policy.items():
        policy_pass = metrics["strategy_compatibility"]["estimate"] >= THRESHOLDS["strategy_compatibility"] and metrics["catastrophic_rate"]["estimate"] <= THRESHOLDS["catastrophic_rate"] and metrics["schema_compliance"]["estimate"] >= THRESHOLDS["schema_compliance"]
        decisions[engine_id] = {"gate_pass": gate_pass, "policy_pass": policy_pass, "classification": "ADVANCE_TO_REAL_PROTOTYPE" if gate_pass and policy_pass else "REJECT_FOR_POLICY_ROLE"}
    det = validation_policy["deterministic_v1"]
    log = validation_policy["logistic_regression_v1"]
    decisions["logistic_regression_v1"]["not_materially_worse_than_deterministic"] = log["strategy_compatibility"]["estimate"] >= det["strategy_compatibility"]["estimate"] - 0.05 and log["catastrophic_rate"]["estimate"] <= det["catastrophic_rate"]["estimate"] + 0.02
    if decisions["logistic_regression_v1"]["classification"] == "ADVANCE_TO_REAL_PROTOTYPE" and not decisions["logistic_regression_v1"]["not_materially_worse_than_deterministic"]:
        decisions["logistic_regression_v1"]["classification"] = "PROMISING_BUT_NOT_VALIDATED"
    dump(OUT / "v4_candidate_selection_decision_v1.json", {"schema": "ragin.decision_fusion_v4.candidate_selection_decision.v1", "status": "COMPLETE", "decisions": decisions, "local_instruction": {"classification": "LOCAL_INSTRUCTION_CANDIDATE_UNAVAILABLE"}, "shallow_mlp": "SHALLOW_MLP_NOT_ADVANCED_DUE_TO_SMALL_SYNTHETIC_TRAINING_REGIME", "validation_selection_used": False, "real_effectiveness_claim": False})


if __name__ == "__main__":
    main()
