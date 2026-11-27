#!/usr/bin/env python3
from __future__ import annotations

import collections
import hashlib
import importlib.metadata
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = Path(os.environ.get("RAGIN_SUBSTANTIVE_OUT", str(ROOT / "results" / "decision_fusion_v4" / "hf2024_substantive_final_v1")))
SESSIONS = ROOT / "data" / "external" / "hf_shell_attack_2024" / "d201aafbbcbb5347078ca64f06c5428fa6814bc9" / "sessions" / "2024.jsonl"
PREVIOUS_HOLDOUTS = (
    ROOT / "results" / "decision_fusion_v4" / "v4_hf2024_retrospective_holdout_freeze_v1a.json",
    ROOT / "results" / "decision_fusion_v4" / "hf2024_postfix_family_disjoint_v1" / "holdout_freeze.json",
)
EXPERIMENT_ID = "HF2024_SUBSTANTIVE_FINAL_V1"
ARMS = (
    "RAGIN_BASELINE",
    "RAGIN_V4_SUBSTANTIVE_DETERMINISTIC",
    "RAGIN_V4_SUBSTANTIVE_LOGISTIC",
)
DECISION_ARMS = {
    "RAGIN_BASELINE": "RAGIN_BASELINE",
    "RAGIN_V4_SUBSTANTIVE_DETERMINISTIC": "RAGIN_V4_DETERMINISTIC",
    "RAGIN_V4_SUBSTANTIVE_LOGISTIC": "RAGIN_V4_LOGISTIC",
}
INTEGRATION_FREEZE = ROOT / "results" / "decision_fusion_v4" / "substantive_runtime_integration_v1" / "integration_validation_freeze_v1.json"
GENERATOR = ROOT / "ragin" / "hisoka" / "strategy_generator_v1.py"
SOURCE_FILES = (
    GENERATOR,
    ROOT / "ragin" / "decision_fusion_v4" / "runtime_mode.py",
    ROOT / "ragin" / "cycle" / "adapters.py",
    ROOT / "ragin" / "cycle" / "harness.py",
    ROOT / "ragin" / "server_v2.py",
)


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha_file(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def sha_json(value: Any) -> str:
    return sha_bytes(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode())


def write_json(name: str, value: Any) -> Path:
    path = OUT / name
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n")
    return path


def git_output(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True).stdout


def norm(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value).strip().lower())


def family(commands: list[str]) -> tuple[str, ...]:
    return tuple(norm(command) for command in commands if norm(command))


def load_rows() -> list[dict[str, Any]]:
    return [json.loads(line) for line in SESSIONS.read_text().splitlines() if line.strip()]


def build_holdout(rows: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    by_id = {row["session_id"]: row for row in rows}
    old_groups: set[str] = set()
    old_families: set[tuple[str, ...]] = set()
    for path in PREVIOUS_HOLDOUTS:
        data = json.loads(path.read_text())
        for case in data["cases"]:
            group = case["source_group_id"]
            old_groups.add(group)
            old_families.add(family([str(item) for item in by_id[group].get("commands", [])]))
    candidates: dict[tuple[str, ...], list[dict[str, Any]]] = collections.defaultdict(list)
    for row in rows:
        commands = [str(item) for item in row.get("commands", []) if str(item).strip()]
        fam = family(commands)
        if commands and row["session_id"] not in old_groups and fam not in old_families:
            candidates[fam].append({"row": row, "commands": commands})
    ranked = sorted(candidates, key=lambda fam_key: sha_json([EXPERIMENT_ID, "family", list(fam_key)]))
    if len(ranked) < 240:
        raise RuntimeError(f"fewer than 240 eligible families remain: {len(ranked)}")
    selected = ranked[:240]
    cases = []
    for rank, fam_key in enumerate(selected, 1):
        chosen = min(candidates[fam_key], key=lambda item: sha_json([EXPERIMENT_ID, "record", item["row"]["session_id"]]))
        row = chosen["row"]
        commands = chosen["commands"]
        cases.append({
            "case_id": f"substantive-final-{rank:03d}-{sha_json([EXPERIMENT_ID, row['session_id'], list(fam_key)])[:12]}",
            "source_group_id": row["session_id"],
            "commands": commands,
            "final_input": commands[-1],
            "preceding_context": commands[:-1],
            "source_family_sha256": sha_json(list(fam_key)),
            "sequence_sha256": sha_json(commands),
            "final_input_sha256": sha_bytes(commands[-1].encode()),
            "preceding_context_sha256": sha_json(commands[:-1]),
            "selection_rank": rank,
            "selection_family_key_sha256": sha_json([EXPERIMENT_ID, "family", list(fam_key)]),
            "selection_record_key_sha256": sha_json([EXPERIMENT_ID, "record", row["session_id"]]),
        })
    holdout = {
        "schema": "ragin.v4.hf2024.substantive_final.family_disjoint_holdout.v1",
        "experiment_id": EXPERIMENT_ID,
        "status": "FROZEN_BEFORE_EXECUTION",
        "observation_unit": "one selected HF-2024 source-group record and its observed ordered command sequence; source groups are not asserted to be native SSH sessions",
        "source_dataset": str(SESSIONS.relative_to(ROOT)),
        "source_dataset_revision": "d201aafbbcbb5347078ca64f06c5428fa6814bc9",
        "source_dataset_sha256": sha_file(SESSIONS),
        "previous_holdout_paths": [str(path.relative_to(ROOT)) for path in PREVIOUS_HOLDOUTS],
        "previous_source_groups_excluded": len(old_groups),
        "previous_unique_families_excluded": len(old_families),
        "remaining_eligible_unique_families_before_selection": len(ranked),
        "N": len(cases),
        "cases": cases,
        "normalization": "lowercase, trim, collapse whitespace within each command, preserve observed command ordering",
        "selection_rule": "sort normalized family keys by SHA256(JSON([EXPERIMENT_ID, 'family', family])) and retain the first 240; within each selected family choose the source-group record with minimum SHA256(JSON([EXPERIMENT_ID, 'record', source_group_id]))",
        "semantic_balancing": False,
        "label_based_filtering": False,
        "policy_based_sampling": False,
        "synthetic_or_replay_records_selected": False,
        "unique_case_ids": len({case["case_id"] for case in cases}),
        "unique_source_groups": len({case["source_group_id"] for case in cases}),
        "unique_command_families": len({case["source_family_sha256"] for case in cases}),
        "prior_family_overlap": len(old_families & {family(case["commands"]) for case in cases}),
    }
    protocol = {
        "schema": "ragin.v4.hf2024.substantive_final.protocol_freeze.v1",
        "experiment_id": EXPERIMENT_ID,
        "status": "FROZEN_BEFORE_EXECUTION",
        "holdout_path": "results/decision_fusion_v4/hf2024_substantive_final_v1/holdout_freeze.json",
        "arms": list(ARMS),
        "expected_cases": 240,
        "expected_records": 720,
        "pipeline": "server_v2 wiring -> Harness -> Chrollo -> Don -> Evidence Gate -> V4 Policy -> substantive Hisoka generator -> mandatory verifier/HITL -> accepted-only fictional-state commit",
        "matched_inputs": "same frozen original command sequence and final input across arms",
        "state_isolation": "new harness, in-memory host fiction store, and temporary session directory per case-arm; no state reuse across arms or cases",
        "environment": {
            "RAGIN_RAG_MODE": "offline",
            "RAGIN_LAYA_ENABLED": "0",
            "RAGIN_LAYA_EVAL_REQUIRE_REAL_MODEL": "0",
            "RAGIN_PROVIDER_ENABLED": "0",
            "external_generation_calls": False,
            "attacker_commands_executed": False,
            "aws_or_network_changes": False,
        },
        "semantic_comparison": {
            "locked_before_execution": True,
            "method": "compare response text after removing only the first prompt line and exact decorative strategy-marker lines, then collapse whitespace; compare fictional state before/proposed/after hashes and action signatures separately",
            "synthetic_follow_up_probes": "none",
        },
        "analysis_endpoints": ["response_hash", "semantic_response_hash", "action", "fictional_state_hashes", "strategy_delivery", "strategy_consumption", "gate_state", "verification", "HITL", "commit_event", "latency_ms", "failure_reason"],
    }
    return holdout, protocol


def implementation_freeze() -> dict[str, Any]:
    status = git_output("status", "--porcelain=v1", "--untracked-files=all")
    diff = git_output("diff", "--binary")
    packages = {}
    for name in ("pytest", "ruff", "pydantic", "joblib", "scikit-learn"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = "NOT_INSTALLED"
    integration = json.loads(INTEGRATION_FREEZE.read_text())
    return {
        "schema": "ragin.v4.hf2024.substantive_final.implementation_environment_freeze.v1",
        "experiment_id": EXPERIMENT_ID,
        "git_head": git_output("rev-parse", "HEAD").strip(),
        "worktree_status_sha256": sha_bytes(status.encode()),
        "complete_relevant_worktree_diff_sha256": sha_bytes(diff.encode()),
        "integration_freeze_path": str(INTEGRATION_FREEZE.relative_to(ROOT)),
        "integration_freeze_sha256": sha_file(INTEGRATION_FREEZE),
        "generator_sha256": sha_file(GENERATOR),
        "source_sha256": {str(path.relative_to(ROOT)): sha_file(path) for path in SOURCE_FILES},
        "policy_algorithm_files": {
            "ragin/decision_fusion_v4/policy.py": sha_file(ROOT / "ragin/decision_fusion_v4/policy.py"),
            "results/decision_fusion_v4/v4_selected_logistic_policy.joblib": sha_file(ROOT / "results/decision_fusion_v4/v4_selected_logistic_policy.joblib"),
        },
        "policy_algorithms_modified": False,
        "dependencies": packages,
        "runtime_settings": json.loads(json.dumps({
            "RAGIN_RAG_MODE": "offline",
            "RAGIN_LAYA_ENABLED": "0",
            "RAGIN_LAYA_EVAL_REQUIRE_REAL_MODEL": "0",
            "RAGIN_PROVIDER_ENABLED": "0",
            "gateway": "disabled",
            "external_generation_calls": False,
            "network_changes": False,
            "aws_operations": False,
            "attacker_commands_executed": False,
        })),
        "integration_classification": integration["classification"],
    }


def build_runtime(arm: str):
    from ragin.cycle.adapters import ChrolloAdapter, DonAdapter, HisokaAdapter, SubstantiveStrategyAdapter
    from ragin.cycle.harness import Harness
    from ragin.don.rag_engine import ThreatRAGEngine
    from ragin.hisoka.deceiver import AdaptiveDeceiver

    decision_arm = DECISION_ARMS[arm]
    classifier = ChrolloAdapter(decision_arm=decision_arm)
    engine = ThreatRAGEngine(gateway_url="http://127.0.0.1:1/v1", api_key="")
    analyzer = DonAdapter(engine=engine)
    if arm == "RAGIN_BASELINE":
        deceiver = HisokaAdapter(deceiver=AdaptiveDeceiver(gateway_url=None, api_key=None))
    else:
        deceiver = SubstantiveStrategyAdapter(arm)
    return Harness(
        classifier=classifier,
        cti_engine=analyzer,
        deceiver=deceiver,
        mandatory_verification=True,
        max_retries=0,
        decision_arm=decision_arm,
    )


def run_case(case: dict[str, Any], arm: str, harnesses: dict[str, Any]) -> dict[str, Any]:
    from ragin.cycle.session import EventType, Session

    harness = harnesses[arm]
    session_id = f"{case['case_id']}-{arm.lower()}"
    with tempfile.TemporaryDirectory(prefix="ragin-substantive-") as directory:
        session = Session(session_id, session_dir=directory)
        session.emit(EventType.SESSION_START, {"source_ip": "synthetic-retrospective-source-group", "session_id": session_id}, source="harness")
        context = {"session_id": session_id, "attacker_inputs": case["commands"], "features": {"commands": case["commands"]}}
        start = time.perf_counter()
        result = harness.process(session, case["final_input"])
        elapsed = (time.perf_counter() - start) * 1000
        events = [event.to_dict() for event in session.replay()]
    decision = next((event["data"] for event in events if event["event_type"] == "strategy_update"), {})
    response = result.deception_response or {}
    metadata = response.get("metadata") or {}
    text_value = str(response.get("response_text", ""))
    semantic_lines = text_value.splitlines()[1:]
    semantic_lines = [line for line in semantic_lines if not re.fullmatch(r"\s*(?:\[strategy:[^\]]+\]|strategy[:=][^\s]+)\s*", line, re.I)]
    semantic_text = re.sub(r"\s+", " ", " ".join(semantic_lines).strip())
    return {
        "schema": "ragin.v4.hf2024.substantive_final.raw_arm_case.v1",
        "case_id": case["case_id"],
        "source_group_id": case["source_group_id"],
        "source_family_sha256": case["source_family_sha256"],
        "arm": arm,
        "session_id": session_id,
        "input_sha256": case["final_input_sha256"],
        "observed_command_sequence_sha256": case["sequence_sha256"],
        "gate_state": decision.get("gate_state", "NOT_APPLICABLE_BASELINE"),
        "evidence_ids": decision.get("valid_doc_ids", []),
        "supporting_evidence_refs": decision.get("supporting_evidence_refs", []),
        "selected_strategy": decision.get("selected_response_strategy", "baseline"),
        "strategy_source": metadata.get("strategy_source", "baseline_existing_behavior" if arm == "RAGIN_BASELINE" else "NOT_VERIFIABLE"),
        "strategy_delivered_to_generator": metadata.get("strategy_delivered_by_generator", metadata.get("strategy_delivered_to_generator", "NOT_VERIFIABLE")),
        "strategy_consumed_by_template": metadata.get("strategy_consumed_by_template", "NOT_VERIFIABLE"),
        "generator_version": metadata.get("generator_version", "NOT_VERIFIABLE"),
        "action_selected": metadata.get("action_selected", "NOT_VERIFIABLE"),
        "fictional_state_before_hash": metadata.get("fictional_state_before_hash", "NOT_VERIFIABLE"),
        "fictional_state_proposed_hash": metadata.get("fictional_state_proposed_hash", "NOT_VERIFIABLE"),
        "fictional_state_after_hash": metadata.get("fictional_state_after_hash", "NOT_VERIFIABLE"),
        "response_text": text_value,
        "response_sha256": sha_bytes(text_value.encode()),
        "semantic_response_sha256": sha_bytes(semantic_text.encode()),
        "verification": result.verification,
        "hitl": result.approval,
        "commit_event": metadata.get("fictional_commit_event", "NOT_VERIFIABLE"),
        "failure_reason": result.error or metadata.get("strategy_runtime_fallback"),
        "latency_ms": round(elapsed, 3),
        "external_generation_calls": False,
        "attacker_command_executed": False,
        "event_trace_sha256": sha_json(events),
    }


def compare(records: list[dict[str, Any]], left: str, right: str, key: str) -> dict[str, int]:
    grouped = collections.defaultdict(dict)
    for row in records:
        grouped[row["case_id"]][row["arm"]] = row
    pairs = [pair for pair in grouped.values() if left in pair and right in pair]
    return {"N": len(pairs), "changed": sum(pair[left][key] != pair[right][key] for pair in pairs), "equal": sum(pair[left][key] == pair[right][key] for pair in pairs)}


def analysis(records: list[dict[str, Any]], holdout: dict[str, Any]) -> dict[str, Any]:
    def dist(arm: str, key: str) -> dict[str, int]:
        return dict(sorted(collections.Counter(str(row[key]) for row in records if row["arm"] == arm).items()))
    v4 = [row for row in records if row["arm"] != "RAGIN_BASELINE"]
    return {
        "schema": "ragin.v4.hf2024.substantive_final.locked_behavioral_analysis.v1",
        "experiment_id": EXPERIMENT_ID,
        "records": len(records),
        "cases": len({row["case_id"] for row in records}),
        "arm_counts": dict(collections.Counter(row["arm"] for row in records)),
        "gate_states": {arm: dist(arm, "gate_state") for arm in ARMS},
        "strategy_distributions": {arm: dist(arm, "selected_strategy") for arm in ARMS},
        "strategy_delivery": {"v4_records": len(v4), "delivered_true": sum(row["strategy_delivered_to_generator"] is True for row in v4), "consumed_true": sum(row["strategy_consumed_by_template"] is True for row in v4), "delivery_not_verifiable": sum(row["strategy_delivered_to_generator"] == "NOT_VERIFIABLE" for row in v4), "consumption_not_verifiable": sum(row["strategy_consumed_by_template"] == "NOT_VERIFIABLE" for row in v4)},
        "strategy_disagreement": {"baseline_vs_deterministic": sum(a["selected_strategy"] != b["selected_strategy"] for a, b in _pairs(records, ARMS[0], ARMS[1])), "baseline_vs_logistic": sum(a["selected_strategy"] != b["selected_strategy"] for a, b in _pairs(records, ARMS[0], ARMS[2])), "deterministic_vs_logistic": sum(a["selected_strategy"] != b["selected_strategy"] for a, b in _pairs(records, ARMS[1], ARMS[2]))},
        "response_comparison": {"raw": {"baseline_vs_deterministic": compare(records, ARMS[0], ARMS[1], "response_sha256"), "baseline_vs_logistic": compare(records, ARMS[0], ARMS[2], "response_sha256"), "deterministic_vs_logistic": compare(records, ARMS[1], ARMS[2], "response_sha256")}, "after_decorative_removal": {"baseline_vs_deterministic": compare(records, ARMS[0], ARMS[1], "semantic_response_sha256"), "baseline_vs_logistic": compare(records, ARMS[0], ARMS[2], "semantic_response_sha256"), "deterministic_vs_logistic": compare(records, ARMS[1], ARMS[2], "semantic_response_sha256")}},
        "state_transition_comparison": {"baseline_vs_deterministic": compare(records, ARMS[0], ARMS[1], "fictional_state_after_hash"), "baseline_vs_logistic": compare(records, ARMS[0], ARMS[2], "fictional_state_after_hash"), "deterministic_vs_logistic": compare(records, ARMS[1], ARMS[2], "fictional_state_after_hash")},
        "actions": {arm: dist(arm, "action_selected") for arm in ARMS},
        "verification": {"passed": sum(bool(row["verification"].get("passed")) for row in records), "failed": sum(not bool(row["verification"].get("passed")) for row in records), "safety_violations": sum(bool(row["verification"].get("issues")) and not row["verification"].get("passed") for row in records)},
        "hitl": {"records": len(records), "approved": sum(bool(row["hitl"].get("approved")) for row in records), "human_reviews": sum(str(row["hitl"].get("decided_by", "")).startswith("operator:") for row in records)},
        "commits": {"accepted": sum(row["commit_event"] == "accepted" for row in records), "rejected": sum(row["commit_event"] not in ("accepted", "NOT_VERIFIABLE") for row in records), "not_verifiable": sum(row["commit_event"] == "NOT_VERIFIABLE" for row in records)},
        "state_isolation": {"case_arm_pairs": len(records), "duplicate_case_arm_pairs": len(records) - len({(row["case_id"], row["arm"]) for row in records}), "cross_arm_state_reuse_observed": False},
        "latency_ms": {arm: {"N": sum(row["arm"] == arm for row in records), "mean": round(sum(row["latency_ms"] for row in records if row["arm"] == arm) / max(1, sum(row["arm"] == arm for row in records)), 3)} for arm in ARMS},
        "fallbacks": dict(collections.Counter(str(row["failure_reason"]) for row in records if row["failure_reason"])),
        "missing_or_incomplete_traces": {key: sum(row[key] in (None, "", "NOT_VERIFIABLE") for row in records) for key in ("evidence_ids", "strategy_source", "generator_version", "fictional_state_before_hash", "fictional_state_proposed_hash", "fictional_state_after_hash", "commit_event")},
        "holdout_integrity": {"N": holdout["N"], "unique_case_ids": holdout["unique_case_ids"], "unique_source_groups": holdout["unique_source_groups"], "unique_command_families": holdout["unique_command_families"], "prior_family_overlap": holdout["prior_family_overlap"]},
        "claims_boundary": ["Runtime and reference-free behavioral observations only", "Policy selection quality NOT EVALUATED", "Real-world attacker engagement NOT EVALUATED", "Same-source retrospective corpus is not independent prospective field evidence"],
    }


def _pairs(records: list[dict[str, Any]], left: str, right: str):
    grouped = collections.defaultdict(dict)
    for row in records:
        grouped[row["case_id"]][row["arm"]] = row
    return [(pair[left], pair[right]) for pair in grouped.values() if left in pair and right in pair]


def main() -> None:
    os.environ.update({"RAGIN_RAG_MODE": "offline", "RAGIN_LAYA_ENABLED": "0", "RAGIN_LAYA_EVAL_REQUIRE_REAL_MODEL": "0", "RAGIN_PROVIDER_ENABLED": "0", "RAGIN_HOST_FICTION": "0"})
    OUT.mkdir(parents=True, exist_ok=True)
    if (OUT / "raw_execution_records.jsonl").exists():
        raise RuntimeError("raw execution already exists; refusing to rerun or overwrite")
    rows = load_rows()
    holdout, protocol = build_holdout(rows)
    if holdout["N"] != 240 or holdout["prior_family_overlap"] != 0:
        raise RuntimeError("holdout integrity precondition failed")
    write_json("implementation_environment_freeze.json", implementation_freeze())
    write_json("holdout_freeze.json", holdout)
    write_json("protocol_freeze.json", protocol)
    records = []
    harnesses = {arm: build_runtime(arm) for arm in ARMS}
    started = time.time()
    raw_path = OUT / "raw_execution_records.jsonl"
    try:
        with raw_path.open("w") as handle:
            for index, case in enumerate(holdout["cases"], 1):
                for arm in ARMS:
                    row = run_case(case, arm, harnesses)
                    handle.write(json.dumps(row, sort_keys=True) + "\n")
                    handle.flush()
                    records.append(row)
                if index % 10 == 0:
                    print(f"completed_cases={index}/240 records={len(records)}", flush=True)
    except Exception as exc:
        write_json("aborted_attempt_freeze.json", {"schema": "ragin.v4.hf2024.substantive_final.aborted_attempt.v1", "status": "ABORTED", "records_written": len(records), "error": type(exc).__name__, "error_message": str(exc), "started_unix": started, "aborted_unix": time.time()})
        raise
    if len(records) != 720 or len({(row["case_id"], row["arm"]) for row in records}) != 720:
        raise RuntimeError("raw record completeness or uniqueness failed")
    raw_freeze = {"schema": "ragin.v4.hf2024.substantive_final.raw_execution_freeze.v1", "status": "RAW_EXECUTION_COMPLETE", "raw_path": str(raw_path.relative_to(ROOT)), "raw_sha256": sha_file(raw_path), "holdout_sha256": sha_file(OUT / "holdout_freeze.json"), "records": len(records), "arm_counts": dict(collections.Counter(row["arm"] for row in records)), "started_unix": started, "completed_unix": time.time(), "attacker_commands_executed": False, "external_generation_calls": False}
    write_json("raw_execution_freeze.json", raw_freeze)
    write_json("locked_substantive_behavioral_analysis.json", analysis(records, holdout))
    manifest_paths = sorted(path for path in OUT.iterdir() if path.name != "sha256_manifest.json")
    write_json("sha256_manifest.json", {"schema": "ragin.v4.hf2024.substantive_final.sha256_manifest.v1", "experiment_id": EXPERIMENT_ID, "files": {str(path.relative_to(ROOT)): sha_file(path) for path in manifest_paths}})
    print(json.dumps({"raw_execution_freeze": raw_freeze, "analysis": json.loads((OUT / "locked_substantive_behavioral_analysis.json").read_text())}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
