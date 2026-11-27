#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
RESULTS = ROOT / "results" / "decision_fusion_v4"
HOLDOUT = RESULTS / "v4_hf2024_retrospective_holdout_freeze_v1a.json"
SESSIONS = ROOT / "data" / "external" / "hf_shell_attack_2024" / "d201aafbbcbb5347078ca64f06c5428fa6814bc9" / "sessions" / "2024.jsonl"
RAW = RESULTS / "v4_hf2024_retrospective_raw_arm_outputs_v1a.jsonl"
FREEZE = RESULTS / "v4_hf2024_retrospective_raw_execution_freeze_v1a.json"
ARMS = ("RAGIN_BASELINE", "RAGIN_V4_DETERMINISTIC", "RAGIN_V4_LOGISTIC")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_json(value: Any) -> str:
    return sha256_bytes(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def load_sessions() -> dict[str, dict[str, Any]]:
    sessions: dict[str, dict[str, Any]] = {}
    with SESSIONS.open() as handle:
        for line in handle:
            row = json.loads(line)
            sessions[row["session_id"]] = row
    return sessions


def build_runtime(arm: str) -> Any:
    from ragin.cycle.adapters import ChrolloAdapter, DonAdapter, HisokaAdapter
    from ragin.cycle.graph import DeceptionGraph
    from ragin.don.rag_engine import ThreatRAGEngine
    from ragin.hisoka.deceiver import AdaptiveDeceiver

    engine = ThreatRAGEngine(gateway_url="http://127.0.0.1:1/v1", api_key="")
    deceiver = AdaptiveDeceiver(gateway_url="http://127.0.0.1:1/v1", api_key="")
    deceiver._response_generator._gateway = None
    return DeceptionGraph(
        classifier=ChrolloAdapter(decision_arm=arm),
        analyzer=DonAdapter(engine=engine),
        deceiver=HisokaAdapter(deceiver=deceiver),
        decision_arm=arm,
        human_in_the_loop=False,
        max_retries=1,
    )


def compact_record(case: dict[str, Any], arm: str, output: dict[str, Any], elapsed_ms: float) -> dict[str, Any]:
    cti = output.get("cti_analysis", {}) or {}
    bundle = output.get("evidence_bundle") or cti.get("evidence_bundle") or {}
    policy = output.get("policy_decision") or {}
    response = output.get("deception_response", {}) or {}
    verification = output.get("verification", {}) or {}
    plan = output.get("plan", {}) or {}
    response_text = str(response.get("response_text", ""))
    return {
        "schema": "ragin.v4.hf2024.retrospective.raw_arm_case.v1",
        "case_id": case["case_id"],
        "source_group_id": case["source_group_id"],
        "arm": arm,
        "input_sha256": case["final_input_sha256"],
        "evidence_bundle_sha256": policy.get("evidence_bundle_sha256") or sha256_json(bundle),
        "gate_state": policy.get("gate_state", "NOT_APPLICABLE_BASELINE"),
        "gate_reason": policy.get("gate_reason"),
        "valid_doc_ids": policy.get("valid_doc_ids", bundle.get("retrieval", {}).get("relevant_doc_ids", [])),
        "policy_decision": policy,
        "selected_response_strategy": policy.get(
            "selected_response_strategy",
            (plan.get("strategy") or {}).get("selected_response_strategy", "baseline"),
        ),
        "supporting_evidence_refs": policy.get("supporting_evidence_refs", []),
        "policy_reason_code": policy.get("policy_reason_code"),
        "generation_input_sha256": policy.get("generation_input_sha256"),
        "strategy_reached_generator": policy.get("strategy_reached_generator", bool(policy)),
        "response_text": response_text,
        "response_sha256": sha256_bytes(response_text.encode()),
        "response_metadata": {**(response.get("metadata", {}) or {}), "external_generation_call": False, "local_deterministic_template": True},
        "serve_path": "TEMPLATE_FALLBACK_VERIFIED",
        "verification": verification,
        "approval": output.get("approval", {}),
        "latency_ms": round(elapsed_ms, 3),
        "raw_output_sha256": sha256_json(output),
        "attacker_command_executed": False,
    }


def main() -> None:
    os.environ.update(
        {
            "RAGIN_RAG_MODE": "offline",
            "RAGIN_LLM_BASE_URL": "http://127.0.0.1:1/v1",
            "RAGIN_LLM_MODEL": "opencode/space-bunny-free",
            "RAGIN_DON_MODEL": "opencode/space-bunny-free",
            "RAGIN_HISOKA_MODEL": "opencode/space-bunny-free",
            "RAGIN_LAYA_ENABLED": "0",
            "RAGIN_LAYA_EVAL_REQUIRE_REAL_MODEL": "0",
            "RAGIN_HOST_FICTION": "0",
        }
    )
    holdout = json.loads(HOLDOUT.read_text())
    if holdout["N"] != 240 or len(holdout["cases"]) != 240:
        raise RuntimeError("frozen holdout is not exactly N=240")
    sessions = load_sessions()
    runtimes = {arm: build_runtime(arm) for arm in ARMS}
    RESULTS.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    started = time.time()
    with RAW.open("w") as handle:
        for index, case in enumerate(holdout["cases"], 1):
            row = sessions[case["source_group_id"]]
            commands = [str(item) for item in row["commands"] if str(item).strip()]
            if not commands:
                raise RuntimeError(f"empty command sequence for {case['case_id']}")
            attacker_input = commands[-1]
            context = {
                "session_id": case["case_id"],
                "attacker_inputs": commands,
                "features": {"commands": commands},
            }
            for arm in ARMS:
                session_id = f"hf2024-{case['case_id']}-{arm.lower()}"
                t0 = time.perf_counter()
                output = runtimes[arm].invoke(session_id, attacker_input, context)
                elapsed_ms = (time.perf_counter() - t0) * 1000
                record = compact_record(case, arm, output, elapsed_ms)
                handle.write(json.dumps(record, sort_keys=True) + "\n")
                handle.flush()
                records.append(record)
            if index % 10 == 0:
                print(f"completed_cases={index}/240 records={len(records)}", flush=True)
    raw_hash = sha256_bytes(RAW.read_bytes())
    freeze = {
        "schema": "ragin.v4.hf2024.retrospective.raw_execution_freeze.v1a",
        "status": "RAW_EXECUTION_COMPLETE_REFERENCE_NOT_STARTED",
        "supersedes": "results/decision_fusion_v4/v4_hf2024_retrospective_raw_execution_freeze_v1.json",
        "holdout_path": str(HOLDOUT.relative_to(ROOT)),
        "holdout_sha256": sha256_bytes(HOLDOUT.read_bytes()),
        "N_cases": 240,
        "arms": list(ARMS),
        "expected_records": 720,
        "actual_records": len(records),
        "raw_output_path": str(RAW.relative_to(ROOT)),
        "raw_output_sha256": raw_hash,
        "runtime": {
            "chrollo": "repository ChrolloAdapter",
            "don": "repository DonAdapter + ThreatRAGEngine offline BM25",
            "hisoka": "repository AdaptiveDeceiver deterministic template/fast-path; gateway disabled",
            "model_name_metadata": "opencode/space-bunny-free",
            "external_generation_calls": False,
            "attacker_commands_executed": False,
        },
        "counts": {
            "baseline": sum(r["arm"] == ARMS[0] for r in records),
            "deterministic": sum(r["arm"] == ARMS[1] for r in records),
            "logistic": sum(r["arm"] == ARMS[2] for r in records),
            "verification_passed": sum(bool(r["verification"].get("passed")) for r in records),
            "fallback_or_template_responses": sum(r["serve_path"] == "TEMPLATE_FALLBACK_VERIFIED" for r in records),
        },
        "reference_annotations": 0,
        "effectiveness_metrics": 0,
        "started_unix": started,
        "completed_unix": time.time(),
    }
    FREEZE.write_text(json.dumps(freeze, indent=2, sort_keys=True) + "\n")
    print(json.dumps(freeze, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
