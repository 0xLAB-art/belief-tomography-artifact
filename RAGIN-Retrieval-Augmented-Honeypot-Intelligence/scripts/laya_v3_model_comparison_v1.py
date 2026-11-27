#!/usr/bin/env python3
"""Frozen two-arm model/task comparison runner (laya_v3_model_comparison_v1).

Study: results/laya_decision_v3/laya_v3_model_comparison_protocol_freeze_v1.json
  (schema ragin.laya_v3.model_comparison_protocol_freeze.v1, FROZEN_BEFORE_MODEL_COMPARISON_CALLS)
  Arms: english (control) vs typed-decisions (candidate), bundle convaiinnovations/laya @55cf4c4e.
  Schedule: 30 primary calls/arm + repeat subset x2 extra runs = 42 calls/arm, 84 total.
  Frozen caller-enforcement runs after predict, before metrics; 8 frozen gates per arm;
  classification is driven by the candidate arm.

Modes:
  --check     stdlib-only: verify the three frozen file digests (protocol, contract, set),
              cross-check the protocol's own invariants against this runner, validate set
              structure and build all 30 runtime question definitions. Imports no model code
              and touches no network.
  (default)   full run: same checks, then the frozen execution schedule. Aborts on any
              technical failure and writes no outputs; outputs are written only after all
              84 calls are recorded. Single run: refuses if outputs already exist.

Fractional metrics are computed exactly and gates are evaluated on the exact fraction;
reported values are rounded to 4 decimals. Latency describes all calls of an arm
(primary + repeat), matching the protocol's "repeat calls used only for repeatability and
latency descriptives".
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import math
import os
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = REPO_ROOT / "results" / "laya_decision_v3"

PROTOCOL_PATH = RESULTS_DIR / "laya_v3_model_comparison_protocol_freeze_v1.json"
CONTRACT_PATH = RESULTS_DIR / "laya_v3_task_adaptation_candidate_freeze_v1.json"
COMPARISON_SET_PATH = RESULTS_DIR / "laya_v3_model_comparison_validation_set_freeze_v1.json"
RESULTS_PATH = RESULTS_DIR / "laya_v3_model_comparison_results_v1.json"
DECISION_PATH = RESULTS_DIR / "laya_v3_model_comparison_final_decision_v1.json"

# Hardcoded frozen digests: this runner refuses to execute against any other revision.
EXPECTED_PROTOCOL_SHA256 = "56e8e68a365fd87bb379963c0ea087869f9233bdf6d3646c93e054149af412e6"
EXPECTED_CONTRACT_SHA256 = "c3fea3c979ed33b8831fcecee7e4ed8eea16bd9bf57bc23690071700c0feca9b"
EXPECTED_COMPARISON_SET_SHA256 = "58c8f056f87097039a62de53bf2b39cc2073b425abbffa2b248976a435cee10f"

EXPECTED_ARM_ORDER = ["english", "typed-decisions"]
CONTROL_ARM = "english"
CANDIDATE_ARM = "typed-decisions"
CANDIDATE_PASS_LABEL = "CANDIDATE_PASSES_FROZEN_CONTRACT"
CANDIDATE_FAIL_LABEL = "COMPARISON_FAIL_REDESIGN_REQUIRED"

EXPECTED_GATE_TABLE = [
    {"id": "G1", "metric": "schema_validity", "rule": "== 1.0"},
    {"id": "G2", "metric": "allow_list_compliance", "rule": "== 1.0"},
    {"id": "G3", "metric": "evidence_reference_validity", "rule": "== 1.0"},
    {"id": "G4", "metric": "required_abstain_recall", "rule": ">= 0.9"},
    {"id": "G5", "metric": "inappropriate_abstain_rate_on_sufficient", "rule": "<= 0.1"},
    {"id": "G6", "metric": "evidence_state_contract_alignment", "rule": ">= 0.85"},
    {"id": "G7", "metric": "strategy_compatibility_on_sufficient", "rule": ">= 0.8"},
    {"id": "G8", "metric": "evidence_reference_compatibility_on_sufficient", "rule": ">= 0.9"},
]

EXPECTED_REPEAT_SUBSET = ["CMP-01", "CMP-03", "CMP-05", "CMP-09", "CMP-14", "CMP-18"]
EXPECTED_PRIMARY_CALLS_PER_ARM = 30
EXPECTED_REPEAT_REPETITIONS = 3  # run_index 1..3 for repeat subset cases
EXPECTED_CALLS_PER_ARM = 42
EXPECTED_TOTAL_CALLS = 84
EXPECTED_CASE_COUNT = 30
EXPECTED_SUFFICIENT_CASES = 20
EXPECTED_REQUIRED_ABSTAIN_CASES = 10

EXPECTED_STATE_ORDER = ["SUFFICIENT", "INSUFFICIENT", "CONFLICTING"]
EXPECTED_STRATEGY_COUNT = 7
QUESTION_IDS = ["evidence_state", "strategy", "evidence_ref"]


class TechnicalFailure(SystemExit):
    pass


def fail(msg: str) -> "TechnicalFailure":
    print("ABORT: " + msg, file=sys.stderr, flush=True)
    return TechnicalFailure(2)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def json_safe(obj):
    """Model payloads are plain JSON already; this only guards against stray objects."""
    return json.loads(json.dumps(obj, default=str, ensure_ascii=False))


def supplied_doc_ids(case) -> list:
    retrieval = (case.get("state") or {}).get("retrieval") or {}
    documents = retrieval.get("documents") or []
    return sorted(str(doc.get("doc_id")) for doc in documents)


def build_runtime_questions(contract: dict, case: dict) -> dict:
    """Runtime question definitions per the frozen question-construction rule."""
    runtime = {}
    for qid in ("evidence_state", "strategy"):
        question = contract["questions"][qid]
        criteria = question["criteria"]
        runtime[qid] = {
            "type": question["type"],
            "instructions": question["instructions"],
            "criteria": {label: criteria[label] for label in question["criteria_order"]},
        }
    ref = contract["questions"]["evidence_ref"]
    ref_criteria = {doc_id: "Supplied document %s" % doc_id for doc_id in supplied_doc_ids(case)}
    ref_criteria["NONE"] = "No supplied document is adequate."
    runtime["evidence_ref"] = {
        "type": ref["type"],
        "instructions": ref["instructions"],
        "criteria": ref_criteria,
    }
    return runtime


def verify_frozen_inputs():
    """Digest checks plus protocol/contract/set structural invariants.

    Returns (protocol, contract, case_set); raises TechnicalFailure on any mismatch.
    """
    for path in (PROTOCOL_PATH, CONTRACT_PATH, COMPARISON_SET_PATH):
        if not path.exists():
            raise fail("frozen input file missing: %s" % path)

    actual = sha256_file(PROTOCOL_PATH)
    if actual != EXPECTED_PROTOCOL_SHA256:
        raise fail("protocol digest mismatch: %s" % actual)
    protocol = load_json(PROTOCOL_PATH)

    for key, path, expected in (
        ("contract_freeze", CONTRACT_PATH, EXPECTED_CONTRACT_SHA256),
        ("comparison_set", COMPARISON_SET_PATH, EXPECTED_COMPARISON_SET_SHA256),
    ):
        recorded = protocol["inputs"][key]
        if recorded["sha256"] != expected:
            raise fail("protocol records unexpected %s digest: %s" % (key, recorded["sha256"]))
        if (REPO_ROOT / recorded["path"]).resolve() != path.resolve():
            raise fail("%s path in protocol does not match runner path" % key)
        actual = sha256_file(path)
        if actual != expected:
            raise fail("%s digest mismatch: %s" % (key, actual))

    if protocol["schema"] != "ragin.laya_v3.model_comparison_protocol_freeze.v1":
        raise fail("unexpected protocol schema")
    if protocol["status"] != "FROZEN_BEFORE_MODEL_COMPARISON_CALLS":
        raise fail("unexpected protocol status")
    if protocol["gates"] != EXPECTED_GATE_TABLE:
        raise fail("protocol gate table differs from runner gate table")

    execution = protocol["execution"]
    schedule = execution["schedule"]
    if execution["arm_order"] != EXPECTED_ARM_ORDER:
        raise fail("unexpected arm order")
    if execution["device"] != "cpu" or execution["max_loaded"] != 1:
        raise fail("unexpected device / max_loaded")
    if sorted(execution["excluded_kwargs"]) != ["lang", "lang_guess", "min_confidence", "task"]:
        raise fail("unexpected excluded kwargs")
    if schedule["repeat_subset"] != EXPECTED_REPEAT_SUBSET:
        raise fail("unexpected repeat subset")
    if schedule["primary_calls_per_arm"] != EXPECTED_PRIMARY_CALLS_PER_ARM:
        raise fail("unexpected primary call count")
    if schedule["repeat_repetitions_per_subset_case"] != EXPECTED_REPEAT_REPETITIONS:
        raise fail("unexpected repeat repetitions")
    if schedule["calls_per_arm"] != EXPECTED_CALLS_PER_ARM or schedule["total_calls"] != EXPECTED_TOTAL_CALLS:
        raise fail("unexpected schedule totals")

    classification = protocol["classification"]
    if classification["candidate_arm"] != CANDIDATE_ARM:
        raise fail("unexpected candidate arm")
    if classification["all_gates_pass"] != CANDIDATE_PASS_LABEL:
        raise fail("unexpected pass label")
    if classification["otherwise"] != CANDIDATE_FAIL_LABEL:
        raise fail("unexpected fail label")

    if (REPO_ROOT / protocol["outputs"]["results"]).resolve() != RESULTS_PATH.resolve():
        raise fail("results output path mismatch")
    if (REPO_ROOT / protocol["outputs"]["final_decision"]).resolve() != DECISION_PATH.resolve():
        raise fail("final decision output path mismatch")

    checkpoint_pair = protocol["checkpoint_pair"]
    control = checkpoint_pair["control_english"]
    candidate = checkpoint_pair["candidate_typed_decisions"]
    if control["model"] != CONTROL_ARM or candidate["model"] != CANDIDATE_ARM:
        raise fail("unexpected checkpoint pair model names")
    if control["revision"] != candidate["revision"]:
        raise fail("checkpoint revisions differ")
    for entry in (control, candidate):
        if entry["file"] != "model.safetensors":
            raise fail("unexpected checkpoint artifact name")

    contract = load_json(CONTRACT_PATH)["contract"]
    for qid in QUESTION_IDS:
        if qid not in contract["questions"] or contract["questions"][qid]["type"] != "choice":
            raise fail("contract question %s missing or not choice" % qid)
    if contract["questions"]["evidence_state"]["criteria_order"] != EXPECTED_STATE_ORDER:
        raise fail("unexpected evidence_state criteria order")
    strategy_order = contract["questions"]["strategy"]["criteria_order"]
    if len(strategy_order) != EXPECTED_STRATEGY_COUNT or strategy_order[0] != "baseline":
        raise fail("unexpected strategy criteria order")
    if set(strategy_order) != set(contract["strategy_vocabulary"]):
        raise fail("strategy criteria order differs from strategy vocabulary")

    case_set = load_json(COMPARISON_SET_PATH)
    if case_set["schema"] != "ragin.laya_v3.model_comparison_validation_set_freeze.v1":
        raise fail("unexpected comparison set schema")
    if case_set["status"] != "FROZEN_BEFORE_MODEL_COMPARISON_CALLS":
        raise fail("unexpected comparison set status")
    cases = case_set["cases"]
    if case_set["case_count"] != EXPECTED_CASE_COUNT or len(cases) != EXPECTED_CASE_COUNT:
        raise fail("unexpected case count")
    expected_ids = ["CMP-%02d" % i for i in range(1, EXPECTED_CASE_COUNT + 1)]
    if [case["case_id"] for case in cases] != expected_ids:
        raise fail("case ids are not CMP-01..CMP-30 in order")

    inputs_meta = protocol["inputs"]["comparison_set"]
    if inputs_meta.get("case_count") != EXPECTED_CASE_COUNT:
        raise fail("protocol case_count mismatch")
    if inputs_meta.get("sufficient_cases") != EXPECTED_SUFFICIENT_CASES:
        raise fail("protocol sufficient_cases mismatch")
    if inputs_meta.get("required_abstain_cases") != EXPECTED_REQUIRED_ABSTAIN_CASES:
        raise fail("protocol required_abstain_cases mismatch")

    sufficient = [case for case in cases if case["oracle"]["evidence_state"] == "SUFFICIENT"]
    required_abstain = [case for case in cases if case["oracle"]["required_abstain"]]
    if len(sufficient) != EXPECTED_SUFFICIENT_CASES:
        raise fail("sufficient case count mismatch")
    if len(required_abstain) != EXPECTED_REQUIRED_ABSTAIN_CASES:
        raise fail("required-abstain case count mismatch")
    if set(case["case_id"] for case in sufficient) & set(case["case_id"] for case in required_abstain):
        raise fail("a case is both sufficient and required-abstain")
    if len(sufficient) + len(required_abstain) != EXPECTED_CASE_COUNT:
        raise fail("sufficient + required-abstain do not cover all cases")

    strategy_vocab = set(strategy_order)
    for case in cases:
        case_id = case["case_id"]
        oracle = case["oracle"]
        doc_ids = supplied_doc_ids(case)
        if len(doc_ids) != len(set(doc_ids)):
            raise fail("duplicate doc ids in %s" % case_id)
        retrieval = (case.get("state") or {}).get("retrieval") or {}
        for doc in retrieval.get("documents") or []:
            for key in ("doc_id", "title", "content_excerpt", "source", "retrieval_score"):
                if key not in doc:
                    raise fail("document missing %s in %s" % (key, case_id))
            if doc["source"] != "synthetic-comparison":
                raise fail("unexpected document source in %s" % case_id)
        if oracle["required_abstain"]:
            if oracle["evidence_state"] not in ("INSUFFICIENT", "CONFLICTING"):
                raise fail("required-abstain case with wrong state in %s" % case_id)
            if oracle["allowed_strategies"] != ["baseline"] or oracle["allowed_evidence_refs"] != []:
                raise fail("required-abstain oracle not baseline/empty in %s" % case_id)
        else:
            if oracle["evidence_state"] != "SUFFICIENT":
                raise fail("non-abstain case not SUFFICIENT in %s" % case_id)
            if not oracle["allowed_evidence_refs"] or not set(oracle["allowed_evidence_refs"]) <= set(doc_ids):
                raise fail("allowed_evidence_refs not a non-empty subset of supplied docs in %s" % case_id)
            if not set(oracle["allowed_strategies"]) <= strategy_vocab:
                raise fail("allowed_strategies outside vocabulary in %s" % case_id)
        runtime = build_runtime_questions(contract, case)
        if set(runtime["evidence_ref"]["criteria"]) != set(doc_ids) | {"NONE"}:
            raise fail("runtime evidence_ref criteria mismatch in %s" % case_id)
        if any(not runtime[qid]["criteria"] for qid in QUESTION_IDS):
            raise fail("empty runtime criteria in %s" % case_id)

    return protocol, contract, case_set


def parse_choice(answer, labels):
    """Return (label_or_None, schema_ok) for one question answer."""
    if not isinstance(answer, dict) or answer.get("type") != "choice":
        return None, False
    label = answer.get("choice")
    probabilities = answer.get("probabilities")
    probs_ok = (
        isinstance(probabilities, dict)
        and len(probabilities) > 0
        and all(
            isinstance(value, (int, float)) and not isinstance(value, bool)
            for value in probabilities.values()
        )
    )
    ok = isinstance(label, str) and label in labels and probs_ok
    return (label if isinstance(label, str) else None), ok


def apply_caller_rules(schema_ok, state_label, strategy_label, ref_label, supplied_ids):
    """Contract caller_rules, applied mechanically after predict, before metrics."""
    abstain = {"action": "ABSTAIN", "strategy": "baseline", "evidence_refs": []}
    if not schema_ok:
        return abstain
    if state_label != "SUFFICIENT":
        return abstain
    if ref_label in supplied_ids:
        return {"action": "SELECT", "strategy": strategy_label, "evidence_refs": [ref_label]}
    return abstain


def raw_choice(call, qid):
    answers = call.get("answers")
    if not isinstance(answers, dict):
        return None
    answer = answers.get(qid)
    if not isinstance(answer, dict):
        return None
    choice = answer.get("choice")
    return choice if isinstance(choice, str) else None


def process_call(case, runtime, arm, run_index, payload, latency_ms):
    answers = payload.get("answers") if isinstance(payload, dict) else None
    routing = payload.get("routing") if isinstance(payload, dict) else None
    labels = {qid: list(runtime[qid]["criteria"].keys()) for qid in QUESTION_IDS}

    parsed = {}
    schema_ok = True
    for qid in QUESTION_IDS:
        answer = answers.get(qid) if isinstance(answers, dict) else None
        label, ok = parse_choice(answer, labels[qid])
        parsed[qid] = label
        schema_ok = schema_ok and ok

    supplied_ids = set(supplied_doc_ids(case))
    canonical_refs = supplied_ids | {"NONE"}
    allow_list_valid = (
        parsed["evidence_state"] in labels["evidence_state"]
        and parsed["strategy"] in labels["strategy"]
        and parsed["evidence_ref"] in canonical_refs
    )
    evidence_ref_valid = parsed["evidence_ref"] in canonical_refs
    enforced = apply_caller_rules(
        schema_ok, parsed["evidence_state"], parsed["strategy"], parsed["evidence_ref"], supplied_ids
    )
    return {
        "case_id": case["case_id"],
        "arm": arm,
        "run_index": run_index,
        "answers": json_safe(answers),
        "routing": json_safe(routing),
        "latency_ms": round(latency_ms, 2),
        "schema_valid": bool(schema_ok),
        "allow_list_valid": bool(allow_list_valid),
        "evidence_ref_valid": bool(evidence_ref_valid),
        "enforced": enforced,
    }


def predict_and_record(router, arm, case, runtime, run_index):
    started = time.perf_counter()
    payload = router.predict(state=case["state"], questions=runtime, model=arm)
    latency_ms = (time.perf_counter() - started) * 1000.0
    record = process_call(case, runtime, arm, run_index, payload, latency_ms)
    print(
        "[%s] %s run %d -> %s strategy=%s refs=%s (%.1f ms)"
        % (
            arm,
            case["case_id"],
            run_index,
            record["enforced"]["action"],
            record["enforced"]["strategy"],
            record["enforced"]["evidence_refs"],
            record["latency_ms"],
        ),
        flush=True,
    )
    return record


def run_arm(router, arm, cases, runtime_by_case):
    calls = []
    for case in cases:
        calls.append(predict_and_record(router, arm, case, runtime_by_case[case["case_id"]], 1))
    for case_id in EXPECTED_REPEAT_SUBSET:
        case = next(case for case in cases if case["case_id"] == case_id)
        for run_index in (2, 3):
            calls.append(predict_and_record(router, arm, case, runtime_by_case[case_id], run_index))
    return calls


def compute_arm_metrics(primary_calls, oracle_by_id):
    count = len(primary_calls)
    schema_validity = sum(call["schema_valid"] for call in primary_calls) / count
    allow_list_compliance = sum(call["allow_list_valid"] for call in primary_calls) / count
    evidence_reference_validity = sum(call["evidence_ref_valid"] for call in primary_calls) / count
    alignment = sum(
        raw_choice(call, "evidence_state") == oracle_by_id[call["case_id"]]["evidence_state"]
        for call in primary_calls
    ) / count

    required = [call for call in primary_calls if oracle_by_id[call["case_id"]]["required_abstain"]]
    sufficient = [call for call in primary_calls if not oracle_by_id[call["case_id"]]["required_abstain"]]
    required_abstain_recall = sum(call["enforced"]["action"] == "ABSTAIN" for call in required) / len(required)
    inappropriate_abstain = sum(call["enforced"]["action"] == "ABSTAIN" for call in sufficient) / len(sufficient)
    strategy_compatibility = sum(
        call["enforced"]["action"] == "SELECT"
        and call["enforced"]["strategy"] in oracle_by_id[call["case_id"]]["allowed_strategies"]
        for call in sufficient
    ) / len(sufficient)
    reference_compatibility = sum(
        call["enforced"]["action"] == "SELECT"
        and bool(call["enforced"]["evidence_refs"])
        and call["enforced"]["evidence_refs"][0] in oracle_by_id[call["case_id"]]["allowed_evidence_refs"]
        for call in sufficient
    ) / len(sufficient)

    return {
        "schema_validity": schema_validity,
        "allow_list_compliance": allow_list_compliance,
        "evidence_reference_validity": evidence_reference_validity,
        "evidence_state_contract_alignment": alignment,
        "required_abstain_recall": required_abstain_recall,
        "inappropriate_abstain_rate_on_sufficient": inappropriate_abstain,
        "strategy_compatibility_on_sufficient": strategy_compatibility,
        "evidence_reference_compatibility_on_sufficient": reference_compatibility,
    }


def evaluate_gates(metrics):
    gates = {}
    failed = []
    for gate in EXPECTED_GATE_TABLE:
        value = metrics[gate["metric"]]
        op, rhs = gate["rule"].split()
        rhs = float(rhs)
        passed = {"==": value == rhs, ">=": value >= rhs, "<=": value <= rhs}[op]
        gates[gate["id"]] = {
            "metric": gate["metric"],
            "value": round(value, 4),
            "rule": gate["rule"],
            "pass": bool(passed),
        }
        if not passed:
            failed.append(gate["id"])
    return gates, failed


def compute_repeatability(calls):
    per_case = {}
    detail = {}
    for case_id in EXPECTED_REPEAT_SUBSET:
        rows = sorted(
            (call for call in calls if call["case_id"] == case_id),
            key=lambda call: call["run_index"],
        )
        outputs = [
            {
                "action": row["enforced"]["action"],
                "strategy": row["enforced"]["strategy"],
                "evidence_refs": list(row["enforced"]["evidence_refs"]),
            }
            for row in rows
        ]
        stable = len(rows) == EXPECTED_REPEAT_REPETITIONS and all(
            output == outputs[0] for output in outputs
        )
        per_case[case_id] = bool(stable)
        detail[case_id] = {"run_indexes": [row["run_index"] for row in rows], "enforced": outputs}
    return {"all_stable": all(per_case.values()), "per_case": per_case, "detail": detail}


def percentile(sorted_values, fraction):
    if len(sorted_values) == 1:
        return sorted_values[0]
    position = fraction * (len(sorted_values) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return sorted_values[lower]
    return sorted_values[lower] + (sorted_values[upper] - sorted_values[lower]) * (position - lower)


def latency_stats(calls):
    values = sorted(call["latency_ms"] for call in calls)
    return {
        "basis": "all calls per arm (30 primary + 12 repeat); wall-clock per predict call",
        "count": len(values),
        "mean": round(statistics.fmean(values), 2),
        "median": round(statistics.median(values), 2),
        "p90": round(percentile(values, 0.90), 2),
        "min": round(values[0], 2),
        "max": round(values[-1], 2),
    }


def library_versions():
    import laya  # noqa: F401  (imported for __version__ / metadata)

    try:
        import importlib.metadata as importlib_metadata

        laya_version = importlib_metadata.version("laya")
    except Exception:
        laya_version = getattr(laya, "__version__", "unknown")
    return {
        "python": "%d.%d.%d" % sys.version_info[:3],
        "torch": __import__("torch").__version__,
        "transformers": __import__("transformers").__version__,
        "laya": laya_version,
        "device": "cpu",
        "hf_offline": os.environ.get("HF_HUB_OFFLINE") == "1",
    }


def run_study(protocol, contract, case_set):
    if RESULTS_PATH.exists() or DECISION_PATH.exists():
        raise fail(
            "output file already exists; the frozen study is a single run "
            "(delete nothing, escalate instead): %s / %s" % (RESULTS_PATH, DECISION_PATH)
        )

    # Frozen environment sanitation before any model code is imported.
    os.environ.pop("LAYA_REVISION", None)
    os.environ.pop("LAYA_SHA256_DIGESTS", None)
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["TOKENIZERS_PARALLELISM"] = "false"

    from laya import Router

    control = protocol["checkpoint_pair"]["control_english"]
    candidate = protocol["checkpoint_pair"]["candidate_typed_decisions"]
    digests = {
        control["model"]: {control["file"]: control["sha256"]},
        candidate["model"]: {candidate["file"]: candidate["sha256"]},
    }
    # `default` is deliberately not set: every call passes model= explicitly, so the
    # routing fallback is never exercised (frozen predict_kwargs govern).
    router = Router(
        device="cpu",
        revision=control["revision"],
        max_loaded=1,
        sha256_digests=digests,
    )

    cases = case_set["cases"]
    runtime_by_case = {case["case_id"]: build_runtime_questions(contract, case) for case in cases}
    oracle_by_id = {case["case_id"]: case["oracle"] for case in cases}

    started_at = now_iso()
    calls_by_arm = {}
    for arm in EXPECTED_ARM_ORDER:
        print("[study] arm %s: starting" % arm, flush=True)
        calls_by_arm[arm] = run_arm(router, arm, cases, runtime_by_case)
        router.unload()
        gc.collect()
        print("[study] arm %s: %d calls recorded; unloaded" % (arm, len(calls_by_arm[arm])), flush=True)
    ended_at = now_iso()

    arm_reports = {}
    for arm in EXPECTED_ARM_ORDER:
        calls = calls_by_arm[arm]
        primary = [call for call in calls if call["run_index"] == 1]
        if len(primary) != EXPECTED_PRIMARY_CALLS_PER_ARM or len(calls) != EXPECTED_CALLS_PER_ARM:
            raise fail("arm %s recorded %d primary / %d total calls" % (arm, len(primary), len(calls)))
        metrics = compute_arm_metrics(primary, oracle_by_id)
        gates, failed_gates = evaluate_gates(metrics)
        arm_reports[arm] = {
            "model": arm,
            "role": "control" if arm == CONTROL_ARM else "candidate",
            "sha256": (control if arm == CONTROL_ARM else candidate)["sha256"],
            "calls": calls,
            "primary_case_summary": [
                {
                    "case_id": call["case_id"],
                    "state_raw": raw_choice(call, "evidence_state"),
                    "strategy_raw": raw_choice(call, "strategy"),
                    "evidence_ref_raw": raw_choice(call, "evidence_ref"),
                    "schema_valid": call["schema_valid"],
                    "enforced": call["enforced"],
                }
                for call in primary
            ],
            "metrics": {key: round(value, 4) for key, value in metrics.items()},
            "gates": gates,
            "gates_all_pass": not failed_gates,
            "failed_gates": failed_gates,
            "repeatability": compute_repeatability(calls),
            "latency_ms": latency_stats(calls),
        }

    candidate_failed = arm_reports[CANDIDATE_ARM]["failed_gates"]
    label = CANDIDATE_PASS_LABEL if not candidate_failed else CANDIDATE_FAIL_LABEL

    results = {
        "schema": "ragin.laya_v3.model_comparison_results.v1",
        "status": "COMPLETE",
        "study": "laya_v3_model_comparison_v1 (frozen protocol)",
        "protocol": {"path": str(PROTOCOL_PATH.relative_to(REPO_ROOT)), "sha256": EXPECTED_PROTOCOL_SHA256},
        "inputs": {
            "contract_freeze": {"path": str(CONTRACT_PATH.relative_to(REPO_ROOT)), "sha256": EXPECTED_CONTRACT_SHA256},
            "comparison_set": {
                "path": str(COMPARISON_SET_PATH.relative_to(REPO_ROOT)),
                "sha256": EXPECTED_COMPARISON_SET_SHA256,
                "case_count": EXPECTED_CASE_COUNT,
                "sufficient_cases": EXPECTED_SUFFICIENT_CASES,
                "required_abstain_cases": EXPECTED_REQUIRED_ABSTAIN_CASES,
            },
        },
        "checkpoint_pair": protocol["checkpoint_pair"],
        "environment": library_versions(),
        "execution": {
            "arm_order": EXPECTED_ARM_ORDER,
            "primary_calls_per_arm": EXPECTED_PRIMARY_CALLS_PER_ARM,
            "repeat_subset": EXPECTED_REPEAT_SUBSET,
            "repeat_repetitions_per_subset_case": EXPECTED_REPEAT_REPETITIONS,
            "calls_per_arm": EXPECTED_CALLS_PER_ARM,
            "total_calls": EXPECTED_TOTAL_CALLS,
            "started_at": started_at,
            "ended_at": ended_at,
        },
        "arms": arm_reports,
        "classification": {
            "candidate_arm": CANDIDATE_ARM,
            "label": label,
            "candidate_all_gates_pass": not candidate_failed,
            "candidate_failed_gates": candidate_failed,
        },
    }

    RESULTS_PATH.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    results_sha = sha256_file(RESULTS_PATH)

    next_step = (
        "Candidate passed all frozen gates on the synthetic contract comparison. Fusion remains "
        "gated: the task-adaptation final decision requires an untouched real-runtime holdout "
        "before any success claim, and this synthetic comparison makes no real-runtime claim."
        if label == CANDIDATE_PASS_LABEL
        else "Candidate failed at least one frozen gate. Redesign-only conclusion: no fusion; "
        "publish the failing gates with this same study version."
    )
    decision = {
        "schema": "ragin.laya_v3.model_comparison_final_decision.v1",
        "status": "COMPLETE",
        "classification": label,
        "decided_at": now_iso(),
        "results": {"path": str(RESULTS_PATH.relative_to(REPO_ROOT)), "sha256": results_sha},
        "protocol": {"path": str(PROTOCOL_PATH.relative_to(REPO_ROOT)), "sha256": EXPECTED_PROTOCOL_SHA256},
        "candidate_arm": CANDIDATE_ARM,
        "candidate_failed_gates": candidate_failed,
        "control_failed_gates": arm_reports[CONTROL_ARM]["failed_gates"],
        "candidate_metrics": arm_reports[CANDIDATE_ARM]["metrics"],
        "control_metrics": arm_reports[CONTROL_ARM]["metrics"],
        "next_step": next_step,
    }
    DECISION_PATH.write_text(json.dumps(decision, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print("[study] results: %s" % RESULTS_PATH, flush=True)
    print("[study] results sha256: %s" % results_sha, flush=True)
    print("[study] final decision: %s" % DECISION_PATH, flush=True)
    print("[study] CLASSIFICATION: %s" % label, flush=True)
    for arm in EXPECTED_ARM_ORDER:
        print(
            "[study] %s gates_all_pass=%s failed=%s"
            % (arm, arm_reports[arm]["gates_all_pass"], arm_reports[arm]["failed_gates"]),
            flush=True,
        )


def main():
    parser = argparse.ArgumentParser(description="Frozen two-arm model comparison (laya_v3_model_comparison_v1)")
    parser.add_argument(
        "--check",
        action="store_true",
        help="stdlib-only integrity check; no model code imported, no network, no outputs written",
    )
    args = parser.parse_args()

    protocol, contract, case_set = verify_frozen_inputs()
    cases = case_set["cases"]
    sufficient = sum(1 for case in cases if case["oracle"]["evidence_state"] == "SUFFICIENT")
    required_abstain = sum(1 for case in cases if case["oracle"]["required_abstain"])
    print("[check] protocol sha256 OK: %s" % EXPECTED_PROTOCOL_SHA256)
    print("[check] contract sha256 OK: %s" % EXPECTED_CONTRACT_SHA256)
    print("[check] comparison set sha256 OK: %s" % EXPECTED_COMPARISON_SET_SHA256)
    print(
        "[check] cases: %d (sufficient %d, required-abstain %d); repeat subset %s; %d runtime question defs built"
        % (len(cases), sufficient, required_abstain, EXPECTED_REPEAT_SUBSET, len(cases))
    )
    if args.check:
        print("CHECK OK")
        return
    run_study(protocol, contract, case_set)


if __name__ == "__main__":
    main()
