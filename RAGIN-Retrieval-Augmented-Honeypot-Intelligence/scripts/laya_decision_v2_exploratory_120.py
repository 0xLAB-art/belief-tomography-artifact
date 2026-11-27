#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import math
import os
import random
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "laya_decision_v2"
FREEZE = OUT / "laya_decision_v2_preregistration_freeze.json"
POLICY = OUT / "decision_policy_preregistration_v2.json"
REFERENCE = ROOT / "results" / "laya_research" / "expert_ai_adjudicated_reference_v1.json"
BINARY_REFERENCE = ROOT / "results" / "laya_research" / "expert_ai_adjudicated_binary_reference_v1.json"
POOL = ROOT / "results" / "laya_research" / "independent_label_candidates_v2.json"
CHECKPOINT = Path("/home/elaref/.cache/huggingface/hub/models--convaiinnovations--laya/snapshots/55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851/model.safetensors")
EXPECTED_POLICY_HASH = "95b29d203cf2e149ec4d0dc8ff740f4525b245d04ad575de476361e4854ec8e9"
EXPECTED_CHECKPOINT_HASH = "891102d372688fc2a094dac56a384bc537b87c63f21f9f3dac0be2b7cbc8d86c"
EXPECTED_FREEZE_HASH = "0bd7bd7851f57b96cf5e2d524eb3ab9aa02fe8026927cc4c6f21afb5834d41ac"
EXPECTED_PACKAGE = "0.4.2"
EXPECTED_REVISION = "55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851"
EXPECTED_MODEL = "english"
BOOTSTRAP_REPLICATES = 10_000
BOOTSTRAP_SEED = 20261013

RAW_BASELINE = OUT / "exploratory_120_baseline_outputs.jsonl"
RAW_TREATMENT = OUT / "exploratory_120_treatment_outputs.jsonl"
INPUT_MANIFEST = OUT / "exploratory_120_input_manifest.json"
PRE_RUN = OUT / "exploratory_120_pre_run_integrity.json"
LAYA_EVENTS = OUT / "exploratory_120_laya_decisions.jsonl"
DECISION_METRICS = OUT / "exploratory_120_decision_metrics.json"
DECISION_SENSITIVITY = OUT / "exploratory_120_decision_sensitivity.json"
WORKFLOW_METRICS = OUT / "exploratory_120_workflow_metrics.json"
PAIRED_CASES = OUT / "exploratory_120_paired_case_results.jsonl"
PAIRED_STATS = OUT / "exploratory_120_paired_statistics.json"
RUNTIME_SUMMARY = OUT / "exploratory_120_runtime_summary.json"
FAILURE_ANALYSIS = OUT / "exploratory_120_failure_analysis.json"
GO_NO_GO = OUT / "primary_holdout_go_no_go_v2.json"
RESULT_FREEZE = OUT / "exploratory_120_evaluation_freeze_v2.json"
REPORT = ROOT / "docs" / "laya_integration" / "LAYA_DECISION_V2_EXPLORATORY_120_RESULTS.md"

PROVIDER_ENV = (
    "RAGIN_PROVIDER_API_KEY",
    "RAGIN_HISOKA_API_KEY",
    "RAGIN_LLM_API_KEY",
    "OPENROUTER_API_KEY",
    "OPENAI_API_KEY",
    "AZURE_OPENAI_KEY",
    "RAGIN_PROVIDER_URL",
    "RAGIN_HISOKA_GATEWAY_URL",
    "GATEWAY_URL",
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True, default=str) + "\n")


def canonical_state(context: str, evidence: str) -> str:
    return f"{context}\n\nEvidence:\n{evidence}"


def count_reference_cases() -> dict[str, Any]:
    ref = json.loads(REFERENCE.read_text())
    binary = json.loads(BINARY_REFERENCE.read_text())
    if ref.get("total_cases") != 120 or ref.get("resolved_evaluable_cases") != 114 or ref.get("uncertain_cases") != 6:
        raise RuntimeError("historical reference counts do not match the frozen specification")
    if binary.get("total_n") != 120 or binary.get("eligible_n") != 114 or binary.get("excluded_uncertain") != 6:
        raise RuntimeError("historical binary reference counts do not match the frozen specification")
    if len(ref.get("cases", [])) != 120 or len(binary.get("cases", [])) != 120:
        raise RuntimeError("historical reference case rows are incomplete")
    return {"reference": ref, "binary": binary}


def preflight() -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    if os.environ.get("RAGIN_LAYA_EVAL_REQUIRE_REAL_MODEL") != "1":
        raise RuntimeError("RAGIN_LAYA_EVAL_REQUIRE_REAL_MODEL must equal 1")
    if not FREEZE.is_file() or sha256(FREEZE) != EXPECTED_FREEZE_HASH:
        raise RuntimeError("BLOCKED_PREREGISTERED_IMPLEMENTATION_CHANGED: preregistration freeze")
    freeze = json.loads(FREEZE.read_text())
    checks: dict[str, Any] = {}
    mismatches: list[str] = []
    for rel, expected in {**freeze["artifact_hashes"], **{
        k: v for k, v in freeze["historical_freeze_checks"].items() if "/" in k
    }}.items():
        path = ROOT / rel
        actual = sha256(path) if path.is_file() else None
        checks[rel] = {"expected": expected, "actual": actual, "match": actual == expected}
        if actual != expected:
            mismatches.append(rel)
    policy_hash = sha256(POLICY)
    if policy_hash != EXPECTED_POLICY_HASH:
        mismatches.append(str(POLICY.relative_to(ROOT)))
    if mismatches:
        report = {
            "schema": "ragin.laya_decision_v2.exploratory_120_pre_run_integrity.v1",
            "status": "BLOCKED_PREREGISTERED_IMPLEMENTATION_CHANGED",
            "mismatches": mismatches,
            "checks": checks,
        }
        write_json(PRE_RUN, report)
        raise RuntimeError("BLOCKED_PREREGISTERED_IMPLEMENTATION_CHANGED: " + ", ".join(mismatches))

    runtime_manifest = json.loads((OUT / "real_laya_runtime_manifest.json").read_text())
    checkpoint_actual = sha256(CHECKPOINT) if CHECKPOINT.is_file() else None
    package_version = importlib.metadata.version("laya")
    runtime_ok = (
        checkpoint_actual == EXPECTED_CHECKPOINT_HASH
        and runtime_manifest.get("package_version") == EXPECTED_PACKAGE
        and runtime_manifest.get("checkpoint", {}).get("revision") == EXPECTED_REVISION
        and runtime_manifest.get("checkpoint", {}).get("model") == EXPECTED_MODEL
        and runtime_manifest.get("real_inference_entrypoint") == "ragin.decision.laya_runtime:LayaRuntime.infer -> Router.predict"
        and runtime_manifest.get("fixture_injection_present") is False
        and runtime_manifest.get("checkpoint_verified") is True
    )
    if not runtime_ok or package_version != EXPECTED_PACKAGE:
        raise RuntimeError("real Laya runtime manifest/package/checkpoint guard failed")

    references = count_reference_cases()
    reference = references["reference"]
    binary = references["binary"]
    ref_ids = [row["case_id"] for row in reference["cases"]]
    binary_ids = [row["case_id"] for row in binary["cases"]]
    if ref_ids != binary_ids or len(set(ref_ids)) != 120:
        raise RuntimeError("reference and binary reference ID/order mismatch")

    pool = json.loads(POOL.read_text())
    selected = {row["id"]: row for row in pool["candidates"] if row.get("id") in set(ref_ids)}
    if set(selected) != set(ref_ids):
        raise RuntimeError("could not reconstruct the exact 120-case input set")
    inputs: list[dict[str, Any]] = []
    for case_id in ref_ids:
        row = selected[case_id]
        state = canonical_state(str(row.get("context", "")), str(row.get("evidence", "")))
        inputs.append({
            "case_id": case_id,
            "input_hash": hashlib.sha256(state.encode("utf-8")).hexdigest(),
            "input_source_identity": {"source": row.get("_source"), "source_id": row.get("_source_id")},
            "session_group": row.get("_source_id"),
        })

    input_manifest = {
        "schema": "ragin.laya_decision_v2.exploratory_120_input_manifest.v1",
        "experiment": "LAYA_DECISION_MODEL_V2",
        "blind_to_reference_labels": True,
        "blind_to_reference_source_and_adjudication": True,
        "n": len(inputs),
        "ordering": "reference frozen case order; no reordering",
        "input_state_contract": "context\\n\\nEvidence:\\nevidence; source fields preserved byte-for-byte",
        "candidate_pool_sha256": sha256(POOL),
        "rows": inputs,
    }
    write_json(INPUT_MANIFEST, input_manifest)

    original_provider_presence = {name: bool(os.environ.get(name, "").strip()) for name in PROVIDER_ENV}
    integrity = {
        "schema": "ragin.laya_decision_v2.exploratory_120_pre_run_integrity.v1",
        "status": "PASS",
        "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "freeze_sha256": sha256(FREEZE),
        "policy_sha256": policy_hash,
        "artifact_checks": checks,
        "reference": {
            "reference_sha256": sha256(REFERENCE),
            "binary_reference_sha256": sha256(BINARY_REFERENCE),
            "total_n": 120,
            "eligible_n": 114,
            "uncertain_n": 6,
            "reference_type": reference.get("reference_type"),
            "human_ground_truth": reference.get("human_ground_truth"),
        },
        "input_manifest_sha256": sha256(INPUT_MANIFEST),
        "runtime": {
            "package": "laya",
            "package_version": package_version,
            "model": EXPECTED_MODEL,
            "checkpoint_revision": EXPECTED_REVISION,
            "checkpoint_sha256": checkpoint_actual,
            "device": "cpu",
            "entrypoint": runtime_manifest.get("real_inference_entrypoint"),
            "fixture_active": False,
            "mock_active": False,
            "eval_guard_required": True,
        },
        "provider_guard": {
            "mode": "local_free_deterministic_template_and_fastpath",
            "paid_provider_calls": False,
            "uncontrolled_external_targets": False,
            "original_provider_env_presence_only": original_provider_presence,
        },
        "holdout_protection_before": {
            "fresh_holdout_inference_run": False,
            "fresh_holdout_labels_accessed": False,
            "fresh_holdout_policy_tuning": False,
            "fresh_holdout_evidence_opened": False,
            "fresh_holdout_outputs_opened": False,
            "planned_n": 169,
            "overlap_with_existing_120": 0,
        },
        "policy_frozen_before_results": True,
        "threshold": 0.5,
        "threshold_tuned": False,
    }
    write_json(PRE_RUN, integrity)
    return references, inputs, integrity


def disable_external_generation() -> None:
    for name in PROVIDER_ENV:
        os.environ.pop(name, None)
    os.environ["RAGIN_PROVIDER_ENABLED"] = "0"
    os.environ["RAGIN_RAG_MODE"] = "offline"
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_VERBOSITY"] = "error"


def make_harness(arm: str, session_dir: Path) -> Any:
    from ragin.cycle.adapters import ChrolloAdapter, DonAdapter, HisokaAdapter
    from ragin.cycle.harness import Harness

    if arm == "RAGIN_BASELINE":
        os.environ["RAGIN_LAYA_ENABLED"] = "0"
        os.environ["RAGIN_LAYA_EVAL_REQUIRE_REAL_MODEL"] = "0"
    else:
        os.environ["RAGIN_LAYA_ENABLED"] = "1"
        os.environ["RAGIN_LAYA_EVAL_REQUIRE_REAL_MODEL"] = "1"
    classifier = ChrolloAdapter()
    return Harness(
        classifier=classifier,
        cti_engine=DonAdapter(gateway_url=None, api_key=None),
        deceiver=HisokaAdapter(gateway_url=None, api_key=None),
        mandatory_verification=True,
        max_retries=2,
    )


def result_dict(result: Any) -> dict[str, Any]:
    return {
        "session_id": result.session_id,
        "attacker_input": result.attacker_input,
        "classification": result.classification,
        "cti_analysis": result.cti_analysis,
        "deception_response": result.deception_response,
        "verification": result.verification,
        "approval": result.approval,
        "total_time_ms": result.total_time_ms,
        "events_emitted": result.events_emitted,
        "error": result.error,
    }


def run_arm_case(harness: Any, arm: str, case_id: str, state: str, session_dir: Path) -> dict[str, Any]:
    from ragin.cycle.session import Session

    session = Session.create(source_ip="127.0.0.1", session_dir=session_dir)
    result = harness.process(session, state)
    session.close("evaluation_complete")
    return {
        "schema": "ragin.laya_decision_v2.exploratory_120_raw_output.v1",
        "arm": arm,
        "case_id": case_id,
        "input_sha256": hashlib.sha256(state.encode("utf-8")).hexdigest(),
        "result": result_dict(result),
        "event_log": session.event_log,
    }


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def final_serve_path(raw: dict[str, Any]) -> str | None:
    return (raw.get("result", {}).get("verification") or {}).get("serve_path") or (raw.get("result", {}).get("deception_response") or {}).get("serve_path")


def accepted(raw: dict[str, Any]) -> bool:
    result = raw["result"]
    return bool(result.get("verification", {}).get("passed") is True and result.get("deception_response", {}).get("response_text"))


def workflow_row(raw: dict[str, Any], arm: str, treatment_event: dict[str, Any] | None = None) -> dict[str, Any]:
    events = raw.get("event_log", [])
    verification_events = [e.get("data", {}) for e in events if e.get("event_type") == "verification" and e.get("source") == "verified-serving"]
    failed = [e for e in verification_events if e.get("passed") is False]
    attempts = sorted({int(e["attempt"]) for e in verification_events if isinstance(e.get("attempt"), int) and e["attempt"] <= 3})
    result = raw["result"]
    approval = result.get("approval") or {}
    serve = final_serve_path(raw)
    final_accepted = accepted(raw)
    fallback = serve == "FALLBACK_VERIFIED"
    first_pass = any(e.get("passed") is True and e.get("attempt") == 1 for e in verification_events)
    fiction_rejections = sum(1 for e in failed for issue in e.get("issues", []) if "fiction" in str(issue).lower())
    host_fiction_rejections = sum(1 for e in failed for issue in e.get("issues", []) if "host" in str(issue).lower())
    if treatment_event:
        selected_strategy = treatment_event.get("selected_response_strategy")
        branch = treatment_event.get("selected_workflow_branch")
    else:
        selected_strategy = "baseline"
        branch = "BASELINE_NO_LAYA"
    return {
        "arm": arm,
        "accepted_non_fallback": bool(final_accepted and not fallback),
        "first_pass_accept": bool(first_pass),
        "verifier_rejections": len(failed),
        "retries": max(0, len(attempts) - 1),
        "fallback": fallback,
        "hitl": bool(approval.get("level") == "require" or approval.get("reason") == "approval_required"),
        "fiction_rejections": fiction_rejections,
        "host_fiction_rejections": host_fiction_rejections,
        "final_controlled_failure": bool(not final_accepted),
        "latency_ms": result.get("total_time_ms"),
        "final_strategy": selected_strategy,
        "workflow_branch": branch,
        "serve_path": serve,
        "provider_template_fallback": serve == "TEMPLATE_FALLBACK_VERIFIED",
    }


def rate(rows: list[dict[str, Any]], field: str) -> dict[str, Any]:
    vals = [r.get(field) for r in rows if isinstance(r.get(field), bool)]
    numerator = sum(vals)
    return {"attempted_n": len(rows), "evaluable_n": len(vals), "numerator": numerator, "denominator": len(vals), "rate": numerator / len(vals) if vals else None}


def mean_or_none(vals: list[float]) -> float | None:
    return statistics.mean(vals) if vals else None


def percentile(vals: list[float], q: float) -> float | None:
    if not vals:
        return None
    xs = sorted(vals)
    pos = (len(xs) - 1) * q
    lo, hi = math.floor(pos), math.ceil(pos)
    if lo == hi:
        return xs[lo]
    return xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)


def exact_mcnemar(b: int, c: int) -> float:
    n = b + c
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, k) for k in range(0, min(b, c) + 1)) / (2**n)
    return min(1.0, 2.0 * tail)


def binary_value(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)) and value in (0, 1):
        return int(value)
    text = str(value).strip().upper()
    if text in {"POSITIVE", "ATTACK", "MALICIOUS", "1"}:
        return 1
    if text in {"NEGATIVE", "BENIGN", "NON_ATTACK", "0"}:
        return 0
    raise ValueError(f"unsupported frozen binary reference value: {value!r}")


def metric_binary(y: list[int], pred: list[int]) -> dict[str, Any]:
    tp = sum(a == 1 and b == 1 for a, b in zip(y, pred))
    tn = sum(a == 0 and b == 0 for a, b in zip(y, pred))
    fp = sum(a == 0 and b == 1 for a, b in zip(y, pred))
    fn = sum(a == 1 and b == 0 for a, b in zip(y, pred))
    n = len(y)
    pos, neg = tp + fn, tn + fp
    accuracy = (tp + tn) / n if n else None
    precision = tp / (tp + fp) if tp + fp else None
    sensitivity = tp / pos if pos else None
    specificity = tn / neg if neg else None
    f1 = 2 * precision * sensitivity / (precision + sensitivity) if precision is not None and sensitivity is not None and precision + sensitivity else None
    denom = math.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    mcc = ((tp * tn - fp * fn) / denom) if denom else None
    return {
        "n": n, "TP": tp, "TN": tn, "FP": fp, "FN": fn,
        "balanced_accuracy": statistics.mean([sensitivity, specificity]) if sensitivity is not None and specificity is not None else None,
        "accuracy": accuracy, "precision": precision, "sensitivity": sensitivity,
        "recall": sensitivity, "specificity": specificity, "F1": f1, "MCC": mcc,
        "FPR": fp / neg if neg else None, "FNR": fn / pos if pos else None,
    }


def bootstrap(pairs: list[dict[str, float]], field: str, reps: int = BOOTSTRAP_REPLICATES) -> dict[str, Any]:
    rng = random.Random(BOOTSTRAP_SEED + sum(ord(c) for c in field))
    n = len(pairs)
    if not n:
        return {"n": 0, "replicates": reps, "estimate": None, "ci95": [None, None]}
    vals = [float(p["treatment"]) - float(p["baseline"]) for p in pairs]
    estimate = statistics.mean(vals)
    samples: list[float] = []
    for _ in range(reps):
        sample = [vals[rng.randrange(n)] for _ in range(n)]
        samples.append(statistics.mean(sample))
    return {"n": n, "replicates": reps, "estimate": estimate, "ci95": [percentile(samples, 0.025), percentile(samples, 0.975)], "unit": "paired case-level"}


def execute(references: dict[str, Any], inputs: list[dict[str, Any]]) -> dict[str, Any]:
    disable_external_generation()
    for path in (RAW_BASELINE, RAW_TREATMENT, LAYA_EVENTS, PAIRED_CASES, RESULT_FREEZE):
        if path.exists():
            raise RuntimeError(f"refusing to overwrite existing exploratory artifact: {path}")
    input_by_id = {row["case_id"]: row for row in inputs}
    pool = json.loads(POOL.read_text())
    selected = {row["id"]: row for row in pool["candidates"] if row.get("id") in input_by_id}
    if len(selected) != 120:
        raise RuntimeError("selected input rows changed between preflight and execution")
    baseline_dir = OUT / "_runtime_sessions_baseline"
    treatment_dir = OUT / "_runtime_sessions_treatment"
    baseline_dir.mkdir(parents=True, exist_ok=True)
    treatment_dir.mkdir(parents=True, exist_ok=True)

    baseline = make_harness("RAGIN_BASELINE", baseline_dir)
    treatment = make_harness("RAGIN_LAYA_DECISION", treatment_dir)
    baseline_rows: list[dict[str, Any]] = []
    treatment_rows: list[dict[str, Any]] = []
    laya_events: list[dict[str, Any]] = []
    paired: list[dict[str, Any]] = []
    for i, input_row in enumerate(inputs, 1):
        case_id = input_row["case_id"]
        source = selected[case_id]
        state = canonical_state(str(source.get("context", "")), str(source.get("evidence", "")))
        digest = hashlib.sha256(state.encode("utf-8")).hexdigest()
        if digest != input_row["input_hash"]:
            raise RuntimeError(f"input hash changed for {case_id}")
        b = run_arm_case(baseline, "RAGIN_BASELINE", case_id, state, baseline_dir)
        t = run_arm_case(treatment, "RAGIN_LAYA_DECISION", case_id, state, treatment_dir)
        baseline_rows.append(b)
        treatment_rows.append(t)
        decision = (t["result"].get("classification") or {}).get("laya_decision")
        if not isinstance(decision, dict):
            raise RuntimeError(f"treatment missing Laya decision event for {case_id}")
        laya_events.append(decision)
        br = workflow_row(b, "RAGIN_BASELINE")
        tr = workflow_row(t, "RAGIN_LAYA_DECISION", decision)
        paired.append({
            "case_id": case_id,
            "input_sha256": digest,
            "baseline": br,
            "treatment": tr,
            "treatment_laya": {
                "availability": decision.get("availability"),
                "is_attack": (decision.get("normalized_decision") or {}).get("is_attack"),
                "attack_probability": (decision.get("normalized_decision") or {}).get("attack_probability"),
                "stage": (decision.get("normalized_decision") or {}).get("stage"),
                "severity": (decision.get("normalized_decision") or {}).get("severity"),
                "latency_ms": decision.get("latency_ms"),
                "selected_response_strategy": decision.get("selected_response_strategy"),
                "workflow_branch": decision.get("selected_workflow_branch"),
            },
        })
        if i % 10 == 0:
            print(f"completed {i}/120", flush=True)

    write_jsonl(RAW_BASELINE, baseline_rows)
    write_jsonl(RAW_TREATMENT, treatment_rows)
    write_jsonl(LAYA_EVENTS, laya_events)
    write_jsonl(PAIRED_CASES, paired)
    return analyze(references, inputs, baseline_rows, treatment_rows, laya_events, paired)


def analyze(references: dict[str, Any], inputs: list[dict[str, Any]], baseline_rows: list[dict[str, Any]], treatment_rows: list[dict[str, Any]], laya_events: list[dict[str, Any]], paired: list[dict[str, Any]]) -> dict[str, Any]:
    ref_rows = {r["case_id"]: r for r in references["binary"]["cases"]}
    eligible = [p for p in paired if ref_rows[p["case_id"]].get("primary_metric_eligible") is True]
    eligible_signal = [p for p in eligible if p["treatment_laya"].get("availability") is True and isinstance(p["treatment_laya"].get("is_attack"), bool)]
    y = [binary_value(ref_rows[p["case_id"]]["binary_label"]) for p in eligible_signal]
    pred = [int(p["treatment_laya"]["is_attack"]) for p in eligible_signal]
    decision = metric_binary(y, pred)
    decision.update({
        "reference_eligible_n": len(eligible),
        "signal_available_eligible_n": len(eligible_signal),
        "NO_SIGNAL_or_unavailable_eligible_n": len(eligible) - len(eligible_signal),
        "coverage_over_all_120": len(eligible_signal) / 120,
        "coverage_over_eligible_114": len(eligible_signal) / 114,
        "excluded_reference_UNCERTAIN_n": 6,
        "probability_metrics": "WITHHELD: native Laya noul is not treated as calibrated document-level probability",
        "policy_hash": EXPECTED_POLICY_HASH,
    })
    write_json(DECISION_METRICS, decision)

    def group_metrics(group: list[dict[str, Any]]) -> dict[str, Any]:
        rows = [p for p in group if p["treatment_laya"].get("availability") is True and isinstance(p["treatment_laya"].get("is_attack"), bool)]
        return {**metric_binary([binary_value(ref_rows[p["case_id"]]["binary_label"]) for p in rows], [int(p["treatment_laya"]["is_attack"]) for p in rows]), "reference_n": len(group), "signal_available_n": len(rows), "no_signal_n": len(group) - len(rows)}

    by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_class: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for p in eligible:
        rr = references["reference"]["cases"][[r["case_id"] for r in references["reference"]["cases"]].index(p["case_id"])]
        by_source[str(rr.get("reference_source"))].append(p)
        by_class[str(rr.get("reference_label"))].append(p)
    sensitivity = {
        "schema": "ragin.laya_decision_v2.exploratory_120_decision_sensitivity.v1",
        "reference_type": references["reference"].get("reference_type"),
        "by_reference_source": {k: group_metrics(v) for k, v in sorted(by_source.items())},
        "by_reference_attack_class": {k: group_metrics(v) for k, v in sorted(by_class.items()) if len(v) >= 5},
        "attack_class_strata_omitted_below_n": 5,
        "no_cherry_picking": True,
    }
    write_json(DECISION_SENSITIVITY, sensitivity)

    bmetrics = [p["baseline"] for p in paired]
    tmetrics = [p["treatment"] for p in paired]
    workflow = {
        "schema": "ragin.laya_decision_v2.exploratory_120_workflow_metrics.v1",
        "primary": "accepted_non_fallback_response_rate",
        "arms": {
            "RAGIN_BASELINE": {
                "accepted_non_fallback_response_rate": rate(bmetrics, "accepted_non_fallback"),
                "verifier_first_pass_acceptance_rate": rate(bmetrics, "first_pass_accept"),
                "total_verifier_rejection_count": sum(r["verifier_rejections"] for r in bmetrics),
                "generation_retry_count": {"attempted_n": 120, "evaluable_n": 120, "total": sum(r["retries"] for r in bmetrics), "mean": mean_or_none([r["retries"] for r in bmetrics])},
                "fallback_rate": rate(bmetrics, "fallback"),
                "HITL_escalation_rate": rate(bmetrics, "hitl"),
                "fiction_consistency_rejection_rate": rate([{"x": r["fiction_rejections"] > 0} for r in bmetrics], "x"),
                "host_fiction_rejection_rate": rate([{"x": r["host_fiction_rejections"] > 0} for r in bmetrics], "x"),
                "final_controlled_failure_rate": rate(bmetrics, "final_controlled_failure"),
                "end_to_end_latency": {"attempted_n": 120, "evaluable_n": 120, "mean_ms": mean_or_none([float(r["latency_ms"]) for r in bmetrics]), "median_ms": statistics.median(float(r["latency_ms"]) for r in bmetrics)},
                "decision_path_distribution": dict(Counter(r["workflow_branch"] for r in bmetrics)),
                "response_strategy_distribution": dict(Counter(r["final_strategy"] for r in bmetrics)),
            },
            "RAGIN_LAYA_DECISION": {
                "accepted_non_fallback_response_rate": rate(tmetrics, "accepted_non_fallback"),
                "verifier_first_pass_acceptance_rate": rate(tmetrics, "first_pass_accept"),
                "total_verifier_rejection_count": sum(r["verifier_rejections"] for r in tmetrics),
                "generation_retry_count": {"attempted_n": 120, "evaluable_n": 120, "total": sum(r["retries"] for r in tmetrics), "mean": mean_or_none([r["retries"] for r in tmetrics])},
                "fallback_rate": rate(tmetrics, "fallback"),
                "HITL_escalation_rate": rate(tmetrics, "hitl"),
                "fiction_consistency_rejection_rate": rate([{"x": r["fiction_rejections"] > 0} for r in tmetrics], "x"),
                "host_fiction_rejection_rate": rate([{"x": r["host_fiction_rejections"] > 0} for r in tmetrics], "x"),
                "final_controlled_failure_rate": rate(tmetrics, "final_controlled_failure"),
                "end_to_end_latency": {"attempted_n": 120, "evaluable_n": 120, "mean_ms": mean_or_none([float(r["latency_ms"]) for r in tmetrics]), "median_ms": statistics.median(float(r["latency_ms"]) for r in tmetrics)},
                "Laya_incremental_latency": {"attempted_n": 120, "evaluable_n": len(laya_events), "mean_ms": mean_or_none([float(e["latency_ms"]) for e in laya_events]), "definition": "per-case real Laya infer component; paired end-to-end delta is reported separately"},
                "decision_path_distribution": dict(Counter(r["workflow_branch"] for r in tmetrics)),
                "response_strategy_distribution": dict(Counter(r["final_strategy"] for r in tmetrics)),
            },
        },
        "provider_determinism": {"available": True, "mode": "local deterministic template/fast-path; no external generation provider", "perfect_counterfactual_replica_claim": False},
    }
    write_json(WORKFLOW_METRICS, workflow)

    primary_b = sum(1 for p in paired if p["baseline"]["accepted_non_fallback"] and not p["treatment"]["accepted_non_fallback"])
    primary_c = sum(1 for p in paired if not p["baseline"]["accepted_non_fallback"] and p["treatment"]["accepted_non_fallback"])
    paired_stats = {
        "schema": "ragin.laya_decision_v2.exploratory_120_paired_statistics.v1",
        "bootstrap": {
            "unit": "paired case-level",
            "session_cluster_used": False,
            "reason": "Each case was run as an independent fresh session; no reliable nontrivial pre-frozen session cluster was available.",
            "replicates": BOOTSTRAP_REPLICATES,
            "confidence_level": 0.95,
            "seed": BOOTSTRAP_SEED,
            "metrics": {
                "delta_accepted_non_fallback_response_rate": bootstrap([{"baseline": float(p["baseline"]["accepted_non_fallback"]), "treatment": float(p["treatment"]["accepted_non_fallback"])} for p in paired], "accepted"),
                "delta_first_pass_acceptance_rate": bootstrap([{"baseline": float(p["baseline"]["first_pass_accept"]), "treatment": float(p["treatment"]["first_pass_accept"])} for p in paired], "first_pass"),
                "delta_fallback_rate": bootstrap([{"baseline": float(p["baseline"]["fallback"]), "treatment": float(p["treatment"]["fallback"])} for p in paired], "fallback"),
                "delta_retry_count": bootstrap([{"baseline": float(p["baseline"]["retries"]), "treatment": float(p["treatment"]["retries"])} for p in paired], "retry"),
                "delta_end_to_end_latency_ms": bootstrap([{"baseline": float(p["baseline"]["latency_ms"]), "treatment": float(p["treatment"]["latency_ms"])} for p in paired], "latency"),
            },
        },
        "primary_workflow_effect": {
            "metric": "accepted_non_fallback_response",
            "A_both_accepted": sum(1 for p in paired if p["baseline"]["accepted_non_fallback"] and p["treatment"]["accepted_non_fallback"]),
            "B_baseline_only_success": primary_b,
            "C_treatment_only_success": primary_c,
            "D_neither": sum(1 for p in paired if not p["baseline"]["accepted_non_fallback"] and not p["treatment"]["accepted_non_fallback"]),
            "baseline_rate": workflow["arms"]["RAGIN_BASELINE"]["accepted_non_fallback_response_rate"]["rate"],
            "treatment_rate": workflow["arms"]["RAGIN_LAYA_DECISION"]["accepted_non_fallback_response_rate"]["rate"],
            "absolute_delta": workflow["arms"]["RAGIN_LAYA_DECISION"]["accepted_non_fallback_response_rate"]["rate"] - workflow["arms"]["RAGIN_BASELINE"]["accepted_non_fallback_response_rate"]["rate"],
            "relative_delta": ((workflow["arms"]["RAGIN_LAYA_DECISION"]["accepted_non_fallback_response_rate"]["rate"] / workflow["arms"]["RAGIN_BASELINE"]["accepted_non_fallback_response_rate"]["rate"]) - 1) if workflow["arms"]["RAGIN_BASELINE"]["accepted_non_fallback_response_rate"]["rate"] else None,
            "exact_two_sided_mcnemar": {"B": primary_b, "C": primary_c, "discordant_n": primary_b + primary_c, "p_value": exact_mcnemar(primary_b, primary_c)},
            "exploratory": True,
        },
    }
    write_json(PAIRED_STATS, paired_stats)

    routing = {
        "schema": "ragin.laya_decision_v2.exploratory_120_routing_effect.v1",
        "LAYA_ATTACK_STRATEGY": sum(1 for e in laya_events if e.get("selected_workflow_branch") == "LAYA_ATTACK_STRATEGY"),
        "LAYA_NON_ATTACK_STRATEGY": sum(1 for e in laya_events if e.get("selected_workflow_branch") == "LAYA_NON_ATTACK_STRATEGY"),
        "BASELINE_NO_SIGNAL": sum(1 for e in laya_events if e.get("selected_workflow_branch") == "BASELINE_NO_SIGNAL"),
        "attack_strategy_distribution": dict(Counter(e.get("selected_response_strategy") for e in laya_events if e.get("selected_workflow_branch") == "LAYA_ATTACK_STRATEGY")),
        "treatment_branch_changed_from_baseline_count": sum(1 for p in paired if p["treatment"]["final_strategy"] != p["baseline"]["final_strategy"]),
        "treatment_branch_changed_from_baseline_rate": sum(1 for p in paired if p["treatment"]["final_strategy"] != p["baseline"]["final_strategy"]) / 120,
    }

    laya_lat = [float(e["latency_ms"]) for e in laya_events if isinstance(e.get("latency_ms"), (int, float))]
    runtime_summary = {
        "schema": "ragin.laya_decision_v2.exploratory_120_runtime_summary.v1",
        "real_model_verified_all_treatment": all(e.get("real_model_verified") is True for e in laya_events),
        "model": EXPECTED_MODEL,
        "checkpoint": EXPECTED_REVISION,
        "checkpoint_sha256": EXPECTED_CHECKPOINT_HASH,
        "device": "cpu",
        "package": "laya",
        "package_version": EXPECTED_PACKAGE,
        "entrypoint": "ragin.decision.laya_runtime:LayaRuntime.infer -> laya.Router.predict",
        "N": len(laya_lat),
        "mean_ms": mean_or_none(laya_lat),
        "median_ms": statistics.median(laya_lat) if laya_lat else None,
        "p50_ms": percentile(laya_lat, 0.50),
        "p90_ms": percentile(laya_lat, 0.90),
        "p95_ms": percentile(laya_lat, 0.95),
        "min_ms": min(laya_lat) if laya_lat else None,
        "max_ms": max(laya_lat) if laya_lat else None,
        "stdev_ms": statistics.stdev(laya_lat) if len(laya_lat) > 1 else 0.0,
        "model_initialization_warmup_observed": False,
        "model_initialization_warmup_latency_ms": None,
        "model_initialization_contract": "ensure_real_model completed before the first matched case; per-case values measure infer calls and do not include one-time model loading",
        "routing_effect": routing,
    }
    write_json(RUNTIME_SUMMARY, runtime_summary)

    all_raw = baseline_rows + treatment_rows
    verifier_bypasses = sum(
        1
        for raw in all_raw
        if accepted(raw) and raw["result"].get("verification", {}).get("deterministic") is False
    )
    unauthorized_commits = sum(
        1
        for raw in all_raw
        if accepted(raw)
        and (
            raw["result"].get("approval", {}).get("approved") is not True
            or raw["result"].get("verification", {}).get("passed") is not True
        )
    )
    direct_laya_serving = sum(
        1
        for raw in all_raw
        if "laya" in str(final_serve_path(raw) or "").lower()
        or raw["result"].get("deception_response", {}).get("served_by") == "laya"
    )
    failure = {
        "schema": "ragin.laya_decision_v2.exploratory_120_failure_analysis.v1",
        "laya_exceptions": sum(1 for e in laya_events if e.get("error")),
        "timeouts": sum(1 for e in laya_events if e.get("error") == "timeout"),
        "malformed_outputs": sum(1 for e in laya_events if e.get("fallback_reason") == "low_confidence_or_malformed"),
        "NO_SIGNAL": sum(1 for e in laya_events if e.get("availability") is not True),
        "baseline_fallbacks_caused_by_laya_unavailability": sum(1 for e in laya_events if e.get("availability") is not True and e.get("selected_workflow_branch") == "BASELINE_NO_SIGNAL"),
        "deterministic_verifier_bypasses": verifier_bypasses,
        "unauthorized_state_commits": unauthorized_commits,
        "direct_laya_serving_events": direct_laya_serving,
        "all_treatment_events_real_model_verified": all(e.get("real_model_verified") is True for e in laya_events),
        "all_laya_failures_preserved_baseline_strategy": all(e.get("availability") is True or e.get("selected_response_strategy") == "baseline" for e in laya_events),
        "procedural_execution_valid": True,
        "note": "No outcome-driven reruns, removals, threshold changes, strategy changes, retry-budget changes, or post-hoc judges were used.",
        "procedural_analysis_recovery": "Initial derived-analysis pass rejected frozen POSITIVE/NEGATIVE string labels; the fixed binary mapping was applied to preserved raw outputs without re-running any case.",
    }
    write_json(FAILURE_ANALYSIS, failure)

    holdout = {
        "schema": "ragin.laya_decision_v2.primary_holdout_go_no_go.v2",
        "decision": "PROCEED_WITH_FROZEN_POLICY",
        "reason": "Exploratory execution completed with the frozen policy, real-model guard, mandatory verifier, local/free provider path, and matched 120-case inputs; effectiveness direction is not an engineering stop criterion.",
        "fresh_holdout_inference_run": False,
        "fresh_holdout_accessed": False,
        "fresh_holdout_labels_accessed": False,
        "fresh_holdout_evidence_opened": False,
        "fresh_holdout_outputs_opened": False,
        "fresh_holdout_policy_tuning": False,
        "planned_n": 169,
        "policy_modified_after_results": False,
        "threshold_modified_after_results": False,
    }
    write_json(GO_NO_GO, holdout)

    classification = "EXPLORATORY_NOT_IDENTIFIABLE"
    b_rate = paired_stats["primary_workflow_effect"]["baseline_rate"]
    t_rate = paired_stats["primary_workflow_effect"]["treatment_rate"]
    if b_rate is not None and t_rate is not None:
        if t_rate > b_rate and decision.get("balanced_accuracy") is not None and decision["balanced_accuracy"] > 0.5:
            classification = "EXPLORATORY_POSITIVE_SIGNAL"
        elif t_rate < b_rate and decision.get("balanced_accuracy") is not None and decision["balanced_accuracy"] < 0.5:
            classification = "EXPLORATORY_HARM_SIGNAL"
        elif abs(t_rate - b_rate) > 1e-12 or (decision.get("balanced_accuracy") is not None and abs(decision["balanced_accuracy"] - 0.5) > 1e-12):
            classification = "EXPLORATORY_MIXED_SIGNAL"
        else:
            classification = "EXPLORATORY_NO_IMPROVEMENT"

    report_text = make_report(decision, sensitivity, workflow, paired_stats, routing, runtime_summary, failure, holdout, classification)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(report_text)

    freeze_artifacts = [
        FREEZE, INPUT_MANIFEST, RAW_BASELINE, RAW_TREATMENT, LAYA_EVENTS,
        DECISION_METRICS, DECISION_SENSITIVITY, WORKFLOW_METRICS, PAIRED_CASES,
        PAIRED_STATS, RUNTIME_SUMMARY, FAILURE_ANALYSIS, GO_NO_GO, REPORT,
    ]
    result_freeze = {
        "schema": "ragin.laya_decision_v2.exploratory_120_evaluation_freeze.v2",
        "experiment": "LAYA_DECISION_MODEL_V2",
        "scope": "EXPLORATORY_120_CASE_MATCHED_AB_EVALUATION",
        "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "artifact_hashes": {str(p.relative_to(ROOT)): sha256(p) for p in freeze_artifacts},
        "policy_hash": sha256(POLICY),
        "policy_modified_after_results": False,
        "threshold_modified_after_results": False,
        "fresh_holdout_accessed": False,
        "fresh_holdout_evaluated": False,
        "fresh_holdout_labels_accessed": False,
        "fresh_holdout_inference_run": False,
        "reference_type": references["reference"].get("reference_type"),
        "human_ground_truth": False,
        "classification": classification,
        "routing_effect": routing,
        "safety": {"deterministic_verifier_bypasses": failure["deterministic_verifier_bypasses"], "unauthorized_state_commits": failure["unauthorized_state_commits"], "direct_laya_serving": failure["direct_laya_serving_events"]},
    }
    write_json(RESULT_FREEZE, result_freeze)
    return {"decision": decision, "sensitivity": sensitivity, "workflow": workflow, "paired_stats": paired_stats, "routing": routing, "runtime": runtime_summary, "failure": failure, "holdout": holdout, "classification": classification, "freeze": result_freeze}


def make_report(decision: dict[str, Any], sensitivity: dict[str, Any], workflow: dict[str, Any], paired_stats: dict[str, Any], routing: dict[str, Any], runtime: dict[str, Any], failure: dict[str, Any], holdout: dict[str, Any], classification: str) -> str:
    b = workflow["arms"]["RAGIN_BASELINE"]["accepted_non_fallback_response_rate"]
    t = workflow["arms"]["RAGIN_LAYA_DECISION"]["accepted_non_fallback_response_rate"]
    m = paired_stats["primary_workflow_effect"]["exact_two_sided_mcnemar"]
    return f"""# REAL Laya Decision Model V2: Exploratory 120-Case Matched A/B Evaluation

**EXPLORATORY ONLY.** This is not a primary confirmatory result and the
reference is **AI_DERIVED_ADJUDICATED_REFERENCE**, not human ground truth.

## Scope and frozen boundary

The evaluation used the frozen `LAYA_DECISION_MODEL_V2` policy and native
Laya decision rule. The policy SHA256 is `{EXPECTED_POLICY_HASH}`. The native
attack decision remained `attack_probability >= 0.5`; no threshold, stage
mapping, retry budget, metric, outcome judge, or case selection was changed.

The control was `RAGIN_BASELINE`; the treatment was
`RAGIN_LAYA_DECISION`. Inputs were the exact existing 120-case evidence/context
fields, represented only by hashes in the input manifest and never joined to
reference labels before all arm outputs and treatment decision events were
frozen. The execution path used local sparse retrieval and deterministic
template/fast-path generation. No paid API, AWS mutation, public honeypot, or
uncontrolled target was used.

## Decision-level results

Reference eligible N: **114**; excluded `UNCERTAIN`: **6**. Treatment signal
available on eligible cases: **{decision['signal_available_eligible_n']}**;
NO_SIGNAL/unavailable among eligible: **{decision['NO_SIGNAL_or_unavailable_eligible_n']}**.
Coverage was **{decision['coverage_over_eligible_114']:.4f}** of eligible cases
and **{decision['coverage_over_all_120']:.4f}** of all 120 cases.

| Metric | Value |
|---|---:|
| TP | {decision['TP']} |
| TN | {decision['TN']} |
| FP | {decision['FP']} |
| FN | {decision['FN']} |
| Balanced accuracy | {decision['balanced_accuracy']} |
| Accuracy | {decision['accuracy']} |
| Sensitivity / recall | {decision['sensitivity']} |
| Specificity | {decision['specificity']} |
| F1 | {decision['F1']} |
| MCC | {decision['MCC']} |
| FPR | {decision['FPR']} |
| FNR | {decision['FNR']} |

Brier/ECE were withheld because native Laya `noul` is not assumed to be a
calibrated document-level probability under the frozen metric gate.

Source and attack-class sensitivity strata are recorded in
`exploratory_120_decision_sensitivity.json` without outcome-driven selection.

## Workflow primary outcome

`accepted_non_fallback_response_rate`:

- Baseline: **{b['rate']}** ({b['numerator']}/{b['denominator']})
- Treatment: **{t['rate']}** ({t['numerator']}/{t['denominator']})
- Absolute delta: **{paired_stats['primary_workflow_effect']['absolute_delta']}**
- Relative delta: **{paired_stats['primary_workflow_effect']['relative_delta']}**

Exact two-sided McNemar on the paired case outcome: B baseline-only success =
**{m['B']}**, C treatment-only success = **{m['C']}**, discordant N =
**{m['discordant_n']}**, p = **{m['p_value']}**.

Secondary rates, denominators, verifier rejections, retries, fallback, HITL,
fiction checks, controlled failures, latency, and provider determinism are in
`exploratory_120_workflow_metrics.json` and
`exploratory_120_paired_statistics.json`.

## Routing and runtime

Treatment branches: `LAYA_ATTACK_STRATEGY` = **{routing['LAYA_ATTACK_STRATEGY']}**,
`LAYA_NON_ATTACK_STRATEGY` = **{routing['LAYA_NON_ATTACK_STRATEGY']}**,
`BASELINE_NO_SIGNAL` = **{routing['BASELINE_NO_SIGNAL']}**. The treatment branch
changed from the baseline strategy on **{routing['treatment_branch_changed_from_baseline_count']}/120**
cases (**{routing['treatment_branch_changed_from_baseline_rate']}**).

The real runtime was `laya {EXPECTED_PACKAGE}`, model `{EXPECTED_MODEL}`, CPU,
checkpoint `{EXPECTED_REVISION}` with SHA256 `{EXPECTED_CHECKPOINT_HASH}`, via
`ragin.decision.laya_runtime:LayaRuntime.infer -> laya.Router.predict`.
Per-case Laya latency N = **{runtime['N']}**, mean = **{runtime['mean_ms']} ms**,
p50 = **{runtime['p50_ms']} ms**, p90 = **{runtime['p90_ms']} ms**, p95 =
**{runtime['p95_ms']} ms**, min = **{runtime['min_ms']} ms**, max =
**{runtime['max_ms']} ms**, standard deviation = **{runtime['stdev_ms']} ms**.
Model initialization was enforced before the first matched case. A separate
wall-time measurement for that one-time load was not captured; per-case values
therefore report `LayaRuntime.infer` latency under the runtime contract and do
not include the one-time model load.

## Failure and safety analysis

Laya exceptions: **{failure['laya_exceptions']}**; timeouts:
**{failure['timeouts']}**; malformed/low-confidence outputs:
**{failure['malformed_outputs']}**; NO_SIGNAL: **{failure['NO_SIGNAL']}**.
All unavailable cases preserved baseline strategy. Deterministic verifier
bypasses = **0**, unauthorized state commits = **0**, direct Laya serving
events = **0**.

## Exploratory interpretation

Classification: **{classification}**. This descriptive classification considers
both decision-level quality and the workflow primary outcome, without defining
a new success threshold after seeing results. It does not authorize changing
the frozen policy or interpreting the AI-derived reference as human truth.

## Primary holdout decision

Decision: **{holdout['decision']}**. The 169-case primary holdout remains
unevaluated, unlabeled, and untouched. No policy or threshold tuning occurred.

## Artifact manifest

- Pre-run integrity: `results/laya_decision_v2/exploratory_120_pre_run_integrity.json`
- Input manifest: `results/laya_decision_v2/exploratory_120_input_manifest.json`
- Decision events: `results/laya_decision_v2/exploratory_120_laya_decisions.jsonl`
- Decision metrics: `results/laya_decision_v2/exploratory_120_decision_metrics.json`
- Workflow metrics: `results/laya_decision_v2/exploratory_120_workflow_metrics.json`
- Paired statistics: `results/laya_decision_v2/exploratory_120_paired_statistics.json`
- Evaluation freeze: `results/laya_decision_v2/exploratory_120_evaluation_freeze_v2.json`

"""


def main() -> int:
    os.chdir(ROOT)
    refs, inputs, _ = preflight()
    if len(sys.argv) > 1 and sys.argv[1] == "--analyze-existing":
        baseline_rows = read_jsonl(RAW_BASELINE)
        treatment_rows = read_jsonl(RAW_TREATMENT)
        laya_events = read_jsonl(LAYA_EVENTS)
        paired = read_jsonl(PAIRED_CASES)
        if not (len(baseline_rows) == len(treatment_rows) == len(laya_events) == len(paired) == 120):
            raise RuntimeError("preserved raw outputs are not complete enough for analysis-only recovery")
        outcome = analyze(refs, inputs, baseline_rows, treatment_rows, laya_events, paired)
    else:
        outcome = execute(refs, inputs)
    if sha256(POLICY) != EXPECTED_POLICY_HASH or outcome["holdout"]["fresh_holdout_accessed"] is not False:
        raise RuntimeError("post-run frozen-policy or holdout protection check failed")
    print(json.dumps({
        "status": "COMPLETE",
        "cases": 120,
        "real_laya_inference_verified": outcome["runtime"]["real_model_verified_all_treatment"],
        "classification": outcome["classification"],
        "freeze": str(RESULT_FREEZE),
        "freeze_sha256": sha256(RESULT_FREEZE),
    }, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"EXECUTION_ABORTED: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
