from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "step7_full_system_evaluation_v1"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    run = read(OUT / "run_manifest.json")
    raw = read(OUT / "raw_output_manifest.json")
    ingress = read(OUT / "ingress_proof_v3" / "ingress_proof.json")
    ingress_manifest = read(OUT / "ingress_proof_v3" / "ingress_manifest.json")
    selection = read(ROOT / "results" / "step6_matched_evaluation_protocol_v1" / "selected_cases_v1.json")
    expected_ids = {case["case_id"] for case in selection["cases"]}
    records = []
    for arm in ("A_judge_off", "B_judge_on"):
        records.extend(read_jsonl(OUT / arm / "case_arm_records.jsonl"))
    pairs = {(row.get("case_id"), row.get("arm")) for row in records}
    by_pair = {(row.get("case_id"), row.get("arm")): row for row in records}
    trace_requirements = {"session_start", "attacker_input", "classification", "cti_lookup", "strategy_update", "verification", "system_response", "response_generate", "metric"}
    trace_results = []
    manipulation_results = []
    retrieval_by_pair = {}
    for row in records:
        path = Path(row["session_path"])
        events = read_jsonl(path)
        types = {event.get("event_type") for event in events}
        trace_results.append(trace_requirements.issubset(types))
        manipulation_results.append("strategy_update" in types and "response_generate" in types)
        lookup = next((event.get("data", {}).get("evidence_bundle", {}).get("retrieval", {}) for event in events if event.get("event_type") == "cti_lookup"), {})
        retrieval_by_pair[(row.get("case_id"), row.get("arm"))] = {key: lookup.get(key) for key in ("retrieval_status", "backend", "query", "sub_queries", "retrieved_count", "documents")}
    input_symmetry = all(by_pair[(case_id, "A_judge_off")].get("input_sha256") == by_pair[(case_id, "B_judge_on")].get("input_sha256") for case_id in expected_ids)
    retrieval_symmetry = all(retrieval_by_pair[(case_id, "A_judge_off")] == retrieval_by_pair[(case_id, "B_judge_on")] for case_id in expected_ids)
    raw_hashes_match = True
    for relative, expected in raw["files"].items():
        path = OUT / relative
        if not path.is_file() or sha(path) != expected:
            raw_hashes_match = False
    ingress_hashes_match = all(sha(OUT / "ingress_proof_v3" / relative) == expected for relative, expected in ingress_manifest["files"].items())
    http_logs = [(OUT / arm / "server.log").read_text(encoding="utf-8", errors="replace") for arm in ("A_judge_off", "B_judge_on")]
    safety = all(row.get("final_status") == 200 and row.get("status") == "COMPLETE" for row in records)
    checks = {
        "exact_case_arm_coverage": len(expected_ids) == 40 and len(records) == 80 and {row.get("case_id") for row in records} == expected_ids,
        "unique_case_arm_pairs": len(pairs) == 80 and all(pair[0] in expected_ids and pair[1] in {"A_judge_off", "B_judge_on"} for pair in pairs),
        "immutable_http_raw_output": raw["status"] == "FROZEN_BEFORE_ANALYSIS" and raw_hashes_match,
        "immutable_ssh_ingress_output": ingress["status"] == "PASS" and ingress_manifest["status"] == "FROZEN" and ingress_hashes_match,
        "input_symmetry": input_symmetry and all(row.get("input_sha256") for row in records),
        "model_identity": all("RAGIN_V4_SUBSTANTIVE_DETERMINISTIC" in log for log in http_logs) and ingress["model_identity"] == {"mode": "RAGIN_V4_SUBSTANTIVE_DETERMINISTIC", "model": "ragin-local", "provider_backed": False},
        "retrieval_symmetry": retrieval_symmetry,
        "manipulation_delivery": all(row.get("turn_count", 0) >= 1 for row in records) and all(manipulation_results),
        "complete_trace_coverage": len(trace_results) == 80 and all(trace_results),
        "safety_invariants": safety and ingress["served"]["candidate_sha256"] == ingress["served"]["response_text_sha256"],
        "ingress_bridge_correlation": ingress["client"]["served_text_substring"] and ingress["bridge"]["http_200_observed"] and ingress["served"]["commit_event"] == "accepted",
        "raw_before_analysis": run["status"] == "RAW_OUTPUTS_FROZEN_BEFORE_ANALYSIS",
    }
    result = {
        "schema": "ragin.step7.completion_gate.v1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "experiment_id": run["experiment_id"],
        "arms": run["arms"],
        "N_cases": 40,
        "case_arm_pairs": len(pairs),
        "checks": checks,
        "limitations": ["deterministic provider-unavailable mode only", "SSH proof uses isolated local Cowrie container with host networking", "no provider-backed inference or external deployment was exercised"],
        "artifacts": {"run_manifest": str((OUT / "run_manifest.json").relative_to(ROOT)), "raw_output_manifest": str((OUT / "raw_output_manifest.json").relative_to(ROOT)), "ingress_proof": str((OUT / "ingress_proof_v3" / "ingress_proof.json").relative_to(ROOT)), "ingress_manifest": str((OUT / "ingress_proof_v3" / "ingress_manifest.json").relative_to(ROOT))},
    }
    path = OUT / "step7_completion_gate.json"
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


if __name__ == "__main__":
    raise SystemExit(main())
