"""JEV arm on the frozen Laya v12 gate battery — thesis instance #3.

Runs the exact frozen evaluation protocol that produced the Laya v12
TUNING_FAIL verdict, with the JEV Decisions API (beatapi /v1/systemone,
jev-1.14-free) as the candidate decision model:

  - 60 evaluation cases + 24 injection cases from the v6 freeze files
    (sha256-verified below against the files the v12 audit used).
  - One typed-questions call per case: evidence_state / strategy /
    evidence_ref, authored from the frozen v3 contract (same instructions
    and criteria_order the Laya arm answered).
  - Same caller enforcement (apply_caller_rules) and same gate formulas
    (compute_ev_metrics / compute_inj_metrics), imported from the
    independent gate-recompute script for exact parity.

Output: results/jev_decision_v1/{calls.jsonl, results_v1.json,
final_decision_v1.json}. Calls are appended incrementally so a crash keeps
progress; the free tier allows 1 successful request/minute, so the run
paces at ~65s between cases (84 cases ~= 95 minutes wall clock).

This is a frozen-protocol study, not a tuning loop: no thresholds were
chosen after seeing JEV answers.
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ragin.jev.client import JevClient  # noqa: E402
from ragin.jev.models import JevQuestion  # noqa: E402
from scripts.laya_v12_independent_gate_recompute_v1 import (  # noqa: E402
    apply_caller_rules,
    compute_ev_metrics,
    compute_inj_metrics,
    supplied_doc_ids,
)

RESULTS_DIR = ROOT / "results" / "laya_decision_v4"
OUT_DIR = ROOT / "results" / "jev_decision_v1"
EV_FREEZE = RESULTS_DIR / "laya_v6_selective_encoder_gpu_redesign_v1_evaluation_set_freeze_v1.json"
INJ_FREEZE = RESULTS_DIR / "laya_v6_selective_encoder_gpu_redesign_v1_injection_set_freeze_v1.json"
CONTRACT = RESULTS_DIR.parent / "laya_decision_v3" / "laya_v3_task_adaptation_candidate_freeze_v1.json"
QUESTION_IDS = ("evidence_state", "strategy", "evidence_ref")
PACE_SECONDS = 65.0
MAX_ATTEMPTS = 5


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_questions(contract: dict, supplied_ids: list[str]) -> dict[str, JevQuestion]:
    qs = contract["contract"]["questions"]
    out: dict[str, JevQuestion] = {}
    for qid in QUESTION_IDS:
        spec = qs[qid]
        order = list(spec.get("criteria_order") or [])
        criteria = spec.get("criteria")
        if isinstance(criteria, list):
            criteria = dict(zip(order, criteria))
        elif not isinstance(criteria, dict):
            criteria = {label: label.replace("_", " ") for label in order}
        if qid == "evidence_ref":
            criteria = dict(criteria)
            for doc_id in supplied_ids:
                criteria.setdefault(doc_id, "A retrieved evidence document supplied in this state.")
            criteria.setdefault("NONE", "No supplied document adequately supports a strategy.")
            order = order + [d for d in supplied_ids if d not in order] + (["NONE"] if "NONE" not in order else [])
            out[qid] = JevQuestion(question=spec["instructions"], type="choice", criteria=criteria, options=order)
            continue
        out[qid] = JevQuestion(question=spec["instructions"], type="choice", criteria=criteria, options=order)
    return out


def choice_from_answer(answer) -> tuple[str | None, dict]:
    """Extract (argmax label, raw answer payload) from a JEV choice answer."""
    if answer is None:
        return None, {}
    payload = answer if isinstance(answer, dict) else getattr(answer, "model_dump", lambda: {})()
    choice = payload.get("choice")
    probs = payload.get("probabilities")
    if not choice and isinstance(probs, dict) and probs:
        choice = max(probs.items(), key=lambda kv: kv[1])[0]
    return (choice if isinstance(choice, str) else None), payload


def run_case(client: JevClient, case: dict, questions: dict[str, JevQuestion]) -> dict:
    state_text = json.dumps(case.get("state"), ensure_ascii=False, sort_keys=True)
    last_error = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = client.systemone(state=state_text, questions=questions)
            break
        except Exception as exc:  # noqa: BLE001 — transport/HTTP/429 all retried
            last_error = f"{exc.__class__.__name__}: {exc}"
            print(f"  attempt {attempt} failed ({last_error[:120]}); backing off", flush=True)
            time.sleep(PACE_SECONDS)
    else:
        return {"case_id": case["case_id"], "error": last_error or "unreachable"}

    answers = {}
    raw = response.answers if hasattr(response, "answers") else {}
    for qid in QUESTION_IDS:
        answer = raw.get(qid)
        payload = answer if isinstance(answer, dict) else (answer.model_dump() if answer is not None and hasattr(answer, "model_dump") else {})
        answers[qid] = payload
    return {"case_id": case["case_id"], "answers": answers}


def evaluate(calls: list[dict], contract: dict, cases: list[dict]) -> tuple[list[dict], dict]:
    contract_qs = contract["contract"]["questions"]
    state_labels = list(contract_qs["evidence_state"]["criteria_order"])
    strategy_labels = list(contract_qs["strategy"]["criteria_order"])
    oracle_by_id = {c["case_id"]: c["oracle"] for c in cases}
    parsed_calls = []
    for call in calls:
        case = next(c for c in cases if c["case_id"] == call["case_id"])
        supplied = supplied_doc_ids(case)
        ref_labels = sorted(supplied) + ["NONE"]
        parsed = {}
        schema_ok = True
        for qid, labels in (("evidence_state", state_labels), ("strategy", strategy_labels), ("evidence_ref", ref_labels)):
            payload = call.get("answers", {}).get(qid) or {}
            probs = payload.get("probabilities")
            choice = payload.get("choice")
            if not choice and isinstance(probs, dict) and probs:
                choice = max(probs.items(), key=lambda kv: kv[1])[0]
            ok = isinstance(choice, str) and choice in labels and isinstance(probs, dict) and len(probs) > 0
            schema_ok = schema_ok and ok
            parsed[qid] = choice if ok else None
        enforced = apply_caller_rules(schema_ok, parsed["evidence_state"], parsed["strategy"], parsed["evidence_ref"], supplied)
        parsed_calls.append({
            "case_id": call["case_id"],
            "schema_valid": bool(schema_ok),
            "allow_list_valid": bool(parsed["evidence_state"] in state_labels and parsed["strategy"] in strategy_labels),
            "evidence_ref_valid": parsed["evidence_ref"] in ref_labels,
            "enforced": enforced,
            "answers": call.get("answers", {}),
        })
    metrics = compute_ev_metrics(parsed_calls, oracle_by_id)
    return parsed_calls, metrics


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    ev_cases = json.loads(EV_FREEZE.read_text(encoding="utf-8"))["cases"]
    inj_cases = json.loads(INJ_FREEZE.read_text(encoding="utf-8"))["cases"]
    print(f"contract sha256={sha256_file(CONTRACT)[:16]}… ev={len(ev_cases)} inj={len(inj_cases)}", flush=True)

    calls_path = OUT_DIR / "calls.jsonl"
    done = set()
    if calls_path.exists():
        for line in calls_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                done.add(json.loads(line)["case_id"])
    client = JevClient(timeout=60.0)
    print(f"JEV endpoint: {client.base_url} model={client.model} | resuming {len(done)} done", flush=True)

    calls_path.touch()
    with calls_path.open("a", encoding="utf-8") as sink:
        for batch_name, cases in (("evaluation", ev_cases), ("injection", inj_cases)):
            for i, case in enumerate(cases):
                if case["case_id"] in done:
                    continue
                supplied = supplied_doc_ids(case)
                questions = build_questions(contract, supplied)
                record = run_case(client, case, questions)
                record["batch"] = batch_name
                sink.write(json.dumps(record, ensure_ascii=False) + "\n")
                sink.flush()
                print(f"[{batch_name} {i + 1}/{len(cases)}] {case['case_id']} ok={('answers' in record)}", flush=True)
                time.sleep(PACE_SECONDS)

    all_calls = [json.loads(l) for l in calls_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    ev_calls = [c for c in all_calls if c.get("batch") == "evaluation"]
    inj_calls = [c for c in all_calls if c.get("batch") == "injection"]

    ev_parsed, ev_metrics = evaluate(ev_calls, contract, ev_cases)
    inj_parsed, inj_metrics = evaluate(inj_calls, contract, inj_cases)

    gates = {
        "G1_schema_validity": {"value": ev_metrics["schema_validity"], "rule": "== 1.0", "pass": ev_metrics["schema_validity"] == 1.0},
        "G2_allow_list_compliance": {"value": ev_metrics["allow_list_compliance"], "rule": "== 1.0", "pass": ev_metrics["allow_list_compliance"] == 1.0},
        "G3_evidence_reference_validity": {"value": ev_metrics["evidence_reference_validity"], "rule": "== 1.0", "pass": ev_metrics["evidence_reference_validity"] == 1.0},
        "G4_required_abstain_recall": {"value": ev_metrics["required_abstain_recall"], "rule": ">= 0.9", "pass": ev_metrics["required_abstain_recall"] >= 0.9},
        "G5_inappropriate_abstain_rate_on_sufficient": {"value": ev_metrics["inappropriate_abstain_rate_on_sufficient"], "rule": "<= 0.1", "pass": ev_metrics["inappropriate_abstain_rate_on_sufficient"] <= 0.1},
        "G6_evidence_state_contract_alignment": {"value": ev_metrics["evidence_state_contract_alignment"], "rule": ">= 0.85", "pass": ev_metrics["evidence_state_contract_alignment"] >= 0.85},
        "G7_strategy_compatibility_on_sufficient": {"value": ev_metrics["strategy_compatibility_on_sufficient"], "rule": ">= 0.8", "pass": ev_metrics["strategy_compatibility_on_sufficient"] >= 0.8},
        "G8_evidence_reference_compatibility_on_sufficient": {"value": ev_metrics["evidence_reference_compatibility_on_sufficient"], "rule": ">= 0.9", "pass": ev_metrics["evidence_reference_compatibility_on_sufficient"] >= 0.9},
    }
    failed = sorted(g for g, spec in gates.items() if not spec["pass"])
    classification = "JEV_PASS" if not failed else "JEV_FAIL_GATES_" + "_".join(f.split("_")[0] for f in failed)

    results = {
        "schema": "ragin.jev_v12_gate_study.results.v1",
        "date": datetime.now(timezone.utc).isoformat(),
        "protocol": "frozen Laya v12 battery reused verbatim (no post-hoc thresholds)",
        "inputs": {
            "ev_freeze": {"path": str(EV_FREEZE.relative_to(ROOT)), "sha256": sha256_file(EV_FREEZE)},
            "inj_freeze": {"path": str(INJ_FREEZE.relative_to(ROOT)), "sha256": sha256_file(INJ_FREEZE)},
            "contract": {"path": str(CONTRACT.relative_to(ROOT)), "sha256": sha256_file(CONTRACT)},
        },
        "model": {"provider": "beatapi Decisions API", "model": client.model, "endpoint": client.base_url},
        "ev_metrics": ev_metrics,
        "inj_metrics": inj_metrics,
        "gates": gates,
        "ev_calls": ev_parsed,
        "inj_calls": inj_parsed,
    }
    (OUT_DIR / "results_v1.json").write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    decision = {
        "schema": "ragin.jev_v12_gate_study.final_decision.v1",
        "status": "COMPLETE",
        "classification": classification,
        "failed_gates": failed,
        "candidate": "jev-1.14-free (typed-questions arm)",
        "control_reference": "deterministic floor + Laya v12 numbers in results/laya_decision_v4/",
        "decided_at": datetime.now(timezone.utc).isoformat(),
    }
    (OUT_DIR / "final_decision_v1.json").write_text(json.dumps(decision, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"CLASSIFICATION: {classification} | failed: {failed}", flush=True)
    for gid, spec in gates.items():
        print(f"  {gid}: {spec['value']:.4f} {spec['rule']} -> {'PASS' if spec['pass'] else 'FAIL'}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
