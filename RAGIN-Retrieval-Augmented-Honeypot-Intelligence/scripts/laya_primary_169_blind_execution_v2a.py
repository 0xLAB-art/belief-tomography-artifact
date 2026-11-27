from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "results" / "laya_decision_v2"
FREEZE = OUT / "laya_decision_v2_preregistration_freeze_v2a.json"
POLICY = OUT / "decision_policy_preregistration_v2.json"
HOLDOUT = OUT / "fresh_holdout_selection_preregistration_v2.json"
CORRECTION_FREEZE = OUT / "v2a_freeze_hash_correction_freeze.json"
POOL = ROOT / "results" / "laya_research" / "independent_label_candidates_v2.json"
CHECKPOINT = Path("/home/elaref/.cache/huggingface/hub/models--convaiinnovations--laya/snapshots/55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851/model.safetensors")
EXPECTED_FREEZE = "f4e465d8a1c4957fdf45230c9e524c8f0c6c1f190376e244cbf6e57faba833ce"
EXPECTED_CORRECTION_FREEZE = "9d95e964dcc1644705a92346b306bb21fc1fb8a51242fe00f8f83c03d28a2990"
EXPECTED_POLICY = "95b29d203cf2e149ec4d0dc8ff740f4525b245d04ad575de476361e4854ec8e9"
EXPECTED_CHECKPOINT = "891102d372688fc2a094dac56a384bc537b87c63f21f9f3dac0be2b7cbc8d86c"
EXPECTED_REVISION = "55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851"
TARGETS = [
    "primary_169_pre_run_integrity_v2a.json",
    "primary_169_input_manifest_v2a.json",
    "primary_169_baseline_outputs_v2a.jsonl",
    "primary_169_treatment_outputs_v2a.jsonl",
    "primary_169_laya_decisions_v2a.jsonl",
    "primary_169_structural_completion_v2a.json",
    "primary_169_manipulation_delivery_check_v2a.json",
    "primary_169_raw_execution_freeze_v2a.json",
    "primary_169_blind_annotation_source_v2a.json",
    "primary_169_annotation_blindness_audit_v2a.json",
]


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest(value: Any) -> str:
    return digest_bytes(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode())


def file_hash(path: Path) -> str:
    return digest_bytes(path.read_bytes())


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def source_hashes(freeze: dict[str, Any]) -> dict[str, Any]:
    actual = {rel: file_hash(ROOT / rel) for rel in freeze["source_hashes"]}
    expected = freeze["source_hashes"]
    return {rel: {"expected": expected[rel], "actual": actual[rel], "match": expected[rel] == actual[rel]} for rel in expected}


def preflight() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if file_hash(FREEZE) != EXPECTED_FREEZE:
        raise RuntimeError("BLOCKED_V2A_FREEZE_HASH_MISMATCH")
    if file_hash(CORRECTION_FREEZE) != EXPECTED_CORRECTION_FREEZE:
        raise RuntimeError("BLOCKED_V2A_CANONICAL_FREEZE_HASH_MISMATCH")
    freeze = load_json(FREEZE)
    policy_hash = file_hash(POLICY)
    if policy_hash != EXPECTED_POLICY:
        raise RuntimeError("BLOCKED_V2A_FREEZE_HASH_MISMATCH: policy")
    source_checks = source_hashes(freeze)
    if not all(v["match"] for v in source_checks.values()):
        raise RuntimeError("BLOCKED_V2A_FREEZE_HASH_MISMATCH: implementation")
    runtime = load_json(OUT / "real_laya_runtime_manifest.json")
    runtime_ok = (
        runtime.get("runtime_verified") is True
        and runtime.get("checkpoint_verified") is True
        and runtime.get("fixture_injection_present") is False
        and runtime.get("package_version") == "0.4.2"
        and runtime.get("real_inference_entrypoint") == "ragin.decision.laya_runtime:LayaRuntime.infer -> Router.predict"
        and runtime.get("checkpoint", {}).get("revision") == EXPECTED_REVISION
        and runtime.get("checkpoint", {}).get("model") == "english"
        and runtime.get("model_hash") == EXPECTED_CHECKPOINT
    )
    if not runtime_ok or not CHECKPOINT.is_file() or file_hash(CHECKPOINT) != EXPECTED_CHECKPOINT:
        raise RuntimeError("BLOCKED_V2A_FREEZE_HASH_MISMATCH: runtime")
    selection = load_json(HOLDOUT)
    ids = selection.get("candidate_ids")
    if not isinstance(ids, list) or len(ids) != 169 or len(set(ids)) != 169:
        raise RuntimeError("holdout selection is not exactly 169 unique ordered IDs")
    if selection.get("planned_n") != 169 or selection.get("overlap_with_existing_120") != 0:
        raise RuntimeError("holdout selection count or overlap mismatch")
    if any(selection.get(k) is not False for k in ("prediction_conditioned_selection", "laya_output_conditioned_selection", "chrollo_confidence_conditioned_selection")):
        raise RuntimeError("holdout selection independence flags failed")
    pool = load_json(POOL)
    candidates = pool.get("candidates", [])
    by_id = {row.get("id"): row for row in candidates}
    if set(ids) != set(by_id).intersection(ids):
        raise RuntimeError("holdout IDs are not all present in the frozen unlabeled pool")
    cases = []
    for case_id in ids:
        row = by_id[case_id]
        state = f"{row.get('context', '')}\n\nEvidence:\n{row.get('evidence', '')}"
        cases.append({
            "case_id": case_id,
            "state": state,
            "input_sha256": digest_bytes(state.encode()),
            "input_source_identifier": {"source": row.get("_source"), "source_id": row.get("_source_id"), "pool_type": row.get("_pool_type")},
            "session_group": row.get("_source_id"),
        })
    return {
        "freeze": freeze,
        "runtime": runtime,
        "selection": selection,
        "source_checks": source_checks,
        "policy_hash": policy_hash,
        "holdout_hash": file_hash(HOLDOUT),
        "pool_hash": file_hash(POOL),
        "cases": cases,
    }, cases


def make_arm(arm: str, session_dir: Path):
    from scripts.laya_decision_v2_exploratory_120 import disable_external_generation, make_harness

    disable_external_generation()
    return make_harness(arm, session_dir)


def isolation_check() -> dict[str, Any]:
    from ragin.cycle.session import Session

    root = OUT / "_primary_169_isolation_check"
    baseline_dir = root / "baseline"
    treatment_dir = root / "treatment"
    baseline = make_arm("RAGIN_BASELINE", baseline_dir)
    bs = Session.create(session_dir=baseline_dir)
    br = baseline.process(bs, "printf arm-isolation")
    bs.close("isolation_complete")
    treatment = make_arm("RAGIN_LAYA_DECISION", treatment_dir)
    ts = Session.create(session_dir=treatment_dir)
    tr = treatment.process(ts, "printf arm-isolation-treatment")
    ts.close("isolation_complete")
    bd = br.classification or {}
    td = tr.classification or {}
    decision = td.get("laya_decision") or {}
    return {
        "baseline_laya_invocations": 0 if "laya_decision" not in bd else 1,
        "baseline_contains_laya_decision": "laya_decision" in bd,
        "baseline_contains_selected_laya_strategy": "selected_response_strategy" in bd,
        "treatment_real_model_verified": decision.get("real_model_verified") is True,
        "treatment_decision_present": isinstance(decision, dict) and bool(decision),
        "treatment_strategy_present": bool(decision.get("selected_response_strategy")),
        "state_leakage_detected": "laya_decision" in bd or "selected_response_strategy" in bd,
        "passed": "laya_decision" not in bd and decision.get("real_model_verified") is True and bool(decision.get("selected_response_strategy")),
    }


def verification_events(raw: dict[str, Any]) -> list[dict[str, Any]]:
    return [e.get("data", {}) for e in raw.get("event_log", []) if e.get("event_type") in ("verification", "response_verify")]


def raw_row(raw: dict[str, Any], case: dict[str, Any], arm: str) -> dict[str, Any]:
    result = raw["result"]
    classification = result.get("classification") or {}
    decision = classification.get("laya_decision") if arm == "RAGIN_LAYA_DECISION" else None
    strategy = decision.get("selected_response_strategy") if isinstance(decision, dict) else "baseline"
    branch = decision.get("selected_workflow_branch") if isinstance(decision, dict) else "BASELINE_NO_LAYA"
    generation_contract = {
        "attacker_input": case["state"],
        "skill_level": classification.get("skill_level"),
        "selected_response_strategy": strategy,
        "selected_workflow_branch": branch,
        "normalized_decision": (decision or {}).get("normalized_decision") if isinstance(decision, dict) else None,
    }
    deception = result.get("deception_response") or {}
    verification = result.get("verification") or {}
    response_text = str(deception.get("response_text") or "")
    events = verification_events(raw)
    serve_path = verification.get("serve_path") or deception.get("serve_path")
    return {
        "case_id": case["case_id"],
        "arm": arm,
        "input_sha256": case["input_sha256"],
        "generation_input_sha256": digest(generation_contract),
        "candidate_sha256": verification.get("candidate_sha256") or digest(response_text),
        "response_sha256": digest_bytes(response_text.encode()),
        "response_text": response_text,
        "accepted_non_fallback": bool(verification.get("passed") is True and response_text and serve_path != "FALLBACK_VERIFIED"),
        "first_pass_accept": any(e.get("passed") is True and e.get("attempt") == 1 for e in events),
        "verifier_rejections": sum(e.get("passed") is False for e in events),
        "generation_retries": max(0, len({e.get("attempt") for e in events if isinstance(e.get("attempt"), int)}) - 1),
        "fallback": serve_path == "FALLBACK_VERIFIED",
        "HITL": (result.get("approval") or {}).get("level") == "require" or (result.get("approval") or {}).get("reason") == "approval_required",
        "fiction_rejections": sum("fiction" in str(issue).lower() for e in events for issue in e.get("issues", [])),
        "host_fiction_rejections": sum("host" in str(issue).lower() for e in events for issue in e.get("issues", [])),
        "final_controlled_failure": verification.get("passed") is not True,
        "end_to_end_latency_ms": result.get("total_time_ms"),
        "serve_path": serve_path,
        "verification_attempts": events,
        "provider_model_provenance": {
            "provider": "local deterministic Hisoka ResponseGenerator template/fast-path",
            "model": "none",
            "external_provider": False,
        },
        "result": result,
        "event_log": raw.get("event_log", []),
        "real_model_verified": decision.get("real_model_verified") is True if isinstance(decision, dict) else False,
        "laya": {
            "model": decision.get("model") if isinstance(decision, dict) else None,
            "checkpoint": decision.get("checkpoint") if isinstance(decision, dict) else None,
            "checkpoint_hash": decision.get("model_hash") if isinstance(decision, dict) else None,
            "raw_output": decision.get("native_raw_output") if isinstance(decision, dict) else None,
            "normalized_decision": decision.get("normalized_decision") if isinstance(decision, dict) else None,
            "attack_probability": (decision.get("normalized_decision") or {}).get("attack_probability") if isinstance(decision, dict) else None,
            "is_attack": (decision.get("normalized_decision") or {}).get("is_attack") if isinstance(decision, dict) else None,
            "stage": (decision.get("normalized_decision") or {}).get("stage") if isinstance(decision, dict) else None,
            "severity": (decision.get("normalized_decision") or {}).get("severity") if isinstance(decision, dict) else None,
            "availability": decision.get("availability") if isinstance(decision, dict) else None,
            "fallback_reason": decision.get("fallback_reason") if isinstance(decision, dict) else None,
            "latency_ms": decision.get("latency_ms") if isinstance(decision, dict) else None,
            "selected_workflow_branch": branch,
            "selected_response_strategy": strategy,
            "decision_policy_hash": decision.get("decision_policy_hash") if isinstance(decision, dict) else None,
        } if arm == "RAGIN_LAYA_DECISION" else None,
    }


def run_primary(cases: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    from ragin.cycle.session import Session

    baseline_rows: list[dict[str, Any]] = []
    treatment_rows: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []
    session_root = OUT / "_primary_169_runtime_sessions"
    for index, case in enumerate(cases):
        case_root = session_root / f"{index:03d}_{case['case_id']}"
        baseline_dir = case_root / "baseline"
        treatment_dir = case_root / "treatment"
        baseline = make_arm("RAGIN_BASELINE", baseline_dir)
        bs = Session.create(session_dir=baseline_dir)
        bresult = baseline.process(bs, case["state"])
        bs.close("primary_169_complete")
        braw = {"result": {"session_id": bresult.session_id, "attacker_input": bresult.attacker_input, "classification": bresult.classification, "cti_analysis": bresult.cti_analysis, "deception_response": bresult.deception_response, "verification": bresult.verification, "approval": bresult.approval, "total_time_ms": bresult.total_time_ms, "events_emitted": bresult.events_emitted, "error": bresult.error}, "event_log": bs.event_log}
        if braw["result"]["classification"].get("laya_decision") is not None:
            raise RuntimeError("BLOCKED_ARM_STATE_LEAKAGE")
        baseline_rows.append(raw_row(braw, case, "RAGIN_BASELINE"))
        treatment = make_arm("RAGIN_LAYA_DECISION", treatment_dir)
        ts = Session.create(session_dir=treatment_dir)
        tresult = treatment.process(ts, case["state"])
        ts.close("primary_169_complete")
        traw = {"result": {"session_id": tresult.session_id, "attacker_input": tresult.attacker_input, "classification": tresult.classification, "cti_analysis": tresult.cti_analysis, "deception_response": tresult.deception_response, "verification": tresult.verification, "approval": tresult.approval, "total_time_ms": tresult.total_time_ms, "events_emitted": tresult.events_emitted, "error": tresult.error}, "event_log": ts.event_log}
        decision = traw["result"]["classification"].get("laya_decision")
        if not isinstance(decision, dict) or decision.get("real_model_verified") is not True:
            raise RuntimeError("real Laya decision missing or unverified")
        if decision.get("decision_policy_hash") != EXPECTED_POLICY:
            raise RuntimeError("treatment decision policy hash mismatch")
        treatment_rows.append(raw_row(traw, case, "RAGIN_LAYA_DECISION"))
        decisions.append({"case_id": case["case_id"], **decision})
        if len(decisions) % 10 == 0:
            print(f"completed {len(decisions)}/169", flush=True)
    return baseline_rows, treatment_rows, decisions


def create_annotation_source(cases: list[dict[str, Any]], baseline: list[dict[str, Any]], treatment: list[dict[str, Any]], decisions: list[dict[str, Any]]) -> dict[str, Any]:
    pool = load_json(POOL)
    by_id = {row["id"]: row for row in pool["candidates"]}
    rows = [{"case_id": case["case_id"], "evidence": by_id[case["case_id"]]["evidence"], "neutral_context": by_id[case["case_id"]]["context"]} for case in cases]
    path = OUT / "primary_169_blind_annotation_source_v2a.json"
    write_json(path, {"schema": "ragin.laya_decision_v2.primary_169_blind_annotation_source.v2a", "n": len(rows), "rows": rows})
    forbidden_hashes = {r["response_sha256"] for r in baseline + treatment} | {r["candidate_sha256"] for r in baseline + treatment} | {r["generation_input_sha256"] for r in baseline + treatment}
    serialized = path.read_text()
    top_keys = set(load_json(path))
    leaked_hashes = sorted(h for h in forbidden_hashes if h in serialized)
    audit = {
        "schema": "ragin.laya_decision_v2.primary_169_annotation_blindness_audit.v2a",
        "n": len(rows),
        "case_ids_exact": [r["case_id"] for r in rows] == [c["case_id"] for c in cases],
        "contains_model_outputs": False,
        "contains_laya_decisions": False,
        "contains_reference_hints": False,
        "contains_execution_hashes": bool(leaked_hashes),
        "leaked_execution_hashes": leaked_hashes,
        "top_level_keys": sorted(top_keys),
        "allowed_row_keys": ["case_id", "evidence", "neutral_context"],
        "passed": len(rows) == 169 and not leaked_hashes and top_keys == {"schema", "n", "rows"} and all(set(row) == {"case_id", "evidence", "neutral_context"} for row in rows),
    }
    write_json(OUT / "primary_169_annotation_blindness_audit_v2a.json", audit)
    return audit


def main() -> None:
    for name in TARGETS:
        if (OUT / name).exists():
            raise RuntimeError(f"refusing to overwrite frozen primary artifact: {name}")
    pre, cases = preflight()
    isolation = isolation_check()
    if not isolation["passed"]:
        raise RuntimeError("BLOCKED_ARM_STATE_LEAKAGE")
    manifest = {
        "schema": "ragin.laya_decision_v2.primary_169_input_manifest.v2a",
        "designation": "PRIMARY_FRESH_HOLDOUT",
        "n": 169,
        "ordering": "frozen candidate_ids order",
        "blind_to_reference_labels": True,
        "rows": [{k: v for k, v in case.items() if k != "state"} for case in cases],
    }
    write_json(OUT / "primary_169_input_manifest_v2a.json", manifest)
    integrity = {
        "schema": "ragin.laya_decision_v2.primary_169_pre_run_integrity.v2a",
        "holdout_N": 169,
        "holdout_ID_match": True,
        "holdout_previously_inferred": False,
        "holdout_labels_available_to_runner": False,
        "policy_hash_verified": pre["policy_hash"] == EXPECTED_POLICY,
        "implementation_hashes_verified": all(v["match"] for v in pre["source_checks"].values()),
        "v2a_freeze_hash": file_hash(FREEZE),
        "v2a_freeze_hash_verified": file_hash(FREEZE) == EXPECTED_FREEZE,
        "correction_freeze_hash": file_hash(CORRECTION_FREEZE),
        "correction_freeze_hash_verified": file_hash(CORRECTION_FREEZE) == EXPECTED_CORRECTION_FREEZE,
        "holdout_selection_hash": pre["holdout_hash"],
        "runtime_manifest_hash": file_hash(OUT / "real_laya_runtime_manifest.json"),
        "runtime_package_version": importlib.metadata.version("laya"),
        "checkpoint_sha256": file_hash(CHECKPOINT),
        "checkpoint_revision": EXPECTED_REVISION,
        "device": "cpu",
        "entrypoint": "ragin.decision.laya_runtime:LayaRuntime.infer -> laya.Router.predict",
        "fixture_active": False,
        "mock_active": False,
        "manipulation_smoke_verified": load_json(OUT / "manipulation_smoke_v2a.json").get("candidate_can_change") is True,
        "holdout_protection_verified": load_json(OUT / "laya_decision_v2_holdout_protection_check_v2a.json").get("ids_unchanged") is True,
        "arm_isolation": isolation,
        "reference_labels_accessed": False,
        "effectiveness_metrics_computed": False,
    }
    write_json(OUT / "primary_169_pre_run_integrity_v2a.json", integrity)
    baseline, treatment, decisions = run_primary(cases)
    write_jsonl(OUT / "primary_169_baseline_outputs_v2a.jsonl", baseline)
    write_jsonl(OUT / "primary_169_treatment_outputs_v2a.jsonl", treatment)
    write_jsonl(OUT / "primary_169_laya_decisions_v2a.jsonl", decisions)
    if [r["case_id"] for r in decisions] != [c["case_id"] for c in cases] or len({r["case_id"] for r in decisions}) != 169:
        raise RuntimeError("primary decision event coverage mismatch")
    structural = {
        "schema": "ragin.laya_decision_v2.primary_169_structural_completion.v2a",
        "baseline_completed": len(baseline),
        "treatment_completed": len(treatment),
        "real_laya_invocation_count": sum(isinstance(r.get("laya"), dict) and r["laya"].get("availability") is not None for r in treatment),
        "laya_available_count": sum(r["laya"].get("availability") is True for r in treatment),
        "NO_SIGNAL_count": sum(r["laya"].get("availability") is not True for r in treatment),
        "strategy_propagation_count": sum(bool(r["laya"].get("selected_response_strategy")) and bool(r["laya"].get("selected_workflow_branch")) for r in treatment),
        "baseline_candidate_hash_present_count": sum(bool(r.get("candidate_sha256")) for r in baseline),
        "treatment_candidate_hash_present_count": sum(bool(r.get("candidate_sha256")) for r in treatment),
        "baseline_response_hash_present_count": sum(bool(r.get("response_sha256")) for r in baseline),
        "treatment_response_hash_present_count": sum(bool(r.get("response_sha256")) for r in treatment),
        "baseline_failures": sum(bool(r.get("final_controlled_failure")) for r in baseline),
        "treatment_failures": sum(bool(r.get("final_controlled_failure")) for r in treatment),
        "timeouts": sum(r["laya"].get("fallback_reason") == "timeout" for r in treatment),
        "reference_labels_accessed": False,
        "effectiveness_metrics_computed": False,
    }
    write_json(OUT / "primary_169_structural_completion_v2a.json", structural)
    generation_differ = sum(b["generation_input_sha256"] != t["generation_input_sha256"] for b, t in zip(baseline, treatment, strict=True))
    candidate_differ = sum(b["candidate_sha256"] != t["candidate_sha256"] for b, t in zip(baseline, treatment, strict=True))
    delivery = {
        "schema": "ragin.laya_decision_v2.primary_169_manipulation_delivery_check.v2a",
        "n": 169,
        "strategy_reached_generator_n": structural["strategy_propagation_count"],
        "baseline_treatment_generation_input_hashes_differ_n": generation_differ,
        "candidate_hashes_differ_n": candidate_differ,
        "status": "PRIMARY_INTERVENTION_DELIVERED" if structural["strategy_propagation_count"] == 169 and generation_differ > 0 else "PRIMARY_INTERVENTION_NOT_DELIVERED",
        "effectiveness_metric": False,
        "reference_labels_accessed": False,
    }
    write_json(OUT / "primary_169_manipulation_delivery_check_v2a.json", delivery)
    component_files = ["laya_decision_v2_preregistration_freeze_v2a.json", "v2a_freeze_hash_correction_freeze.json", "fresh_holdout_selection_preregistration_v2.json", "primary_169_input_manifest_v2a.json", "primary_169_baseline_outputs_v2a.jsonl", "primary_169_treatment_outputs_v2a.jsonl", "primary_169_laya_decisions_v2a.jsonl", "primary_169_structural_completion_v2a.json", "primary_169_manipulation_delivery_check_v2a.json", "real_laya_runtime_manifest.json"]
    raw_freeze = {
        "schema": "ragin.laya_decision_v2.primary_169_raw_execution_freeze.v2a",
        "designation": "PRIMARY_FRESH_HOLDOUT",
        "n": 169,
        "artifact_hashes": {name: file_hash(OUT / name) for name in component_files},
        "implementation_source_hashes": pre["source_checks"],
        "checkpoint_hash": file_hash(CHECKPOINT),
        "reference_labels_accessed": False,
        "reference_labels_created": False,
        "effectiveness_metrics_computed": False,
        "workflow_arm_comparison_computed": False,
        "decision_accuracy_computed": False,
        "mcnemar_run": False,
        "bootstrap_run": False,
        "correction_harm_computed": False,
        "policy_modified": False,
        "threshold_modified": False,
        "holdout_modified": False,
        "model_rerun_after_results": False,
        "annotation_source_created_after_raw_freeze": True,
    }
    write_json(OUT / "primary_169_raw_execution_freeze_v2a.json", raw_freeze)
    reread = load_json(OUT / "primary_169_raw_execution_freeze_v2a.json")
    if any(file_hash(OUT / name) != expected for name, expected in reread["artifact_hashes"].items()):
        raise RuntimeError("raw execution freeze artifact verification failed")
    annotation_audit = create_annotation_source(cases, baseline, treatment, decisions)
    if not annotation_audit["passed"]:
        raise RuntimeError("annotation source leakage audit failed")
    print(json.dumps({"baseline_completed": len(baseline), "treatment_completed": len(treatment), "laya_invocations": structural["real_laya_invocation_count"], "laya_available": structural["laya_available_count"], "no_signal": structural["NO_SIGNAL_count"], "strategy_reached": delivery["strategy_reached_generator_n"], "generation_hashes_differ": generation_differ, "candidate_hashes_differ": candidate_differ, "delivery_status": delivery["status"], "annotation_blindness": annotation_audit["passed"]}, sort_keys=True))


if __name__ == "__main__":
    main()
