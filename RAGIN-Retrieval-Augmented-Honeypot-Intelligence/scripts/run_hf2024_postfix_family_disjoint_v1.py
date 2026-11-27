#!/usr/bin/env python3
from __future__ import annotations

import collections
import hashlib
import importlib.metadata
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "results" / "decision_fusion_v4" / "hf2024_postfix_family_disjoint_v1"
SESSIONS = (
    ROOT
    / "data"
    / "external"
    / "hf_shell_attack_2024"
    / "d201aafbbcbb5347078ca64f06c5428fa6814bc9"
    / "sessions"
    / "2024.jsonl"
)
OLD_HOLDOUT = ROOT / "results" / "decision_fusion_v4" / "v4_hf2024_retrospective_holdout_freeze_v1a.json"
EXPERIMENT_ID = "HF2024_POSTFIX_FAMILY_DISJOINT_V1"
ARMS = ("RAGIN_BASELINE", "RAGIN_V4_DETERMINISTIC", "RAGIN_V4_LOGISTIC")
DECEIVER = ROOT / "ragin" / "hisoka" / "deceiver.py"
DECEPTION = ROOT / "ragin" / "hisoka" / "deception.py"
POLICY = ROOT / "ragin" / "decision_fusion_v4" / "policy.py"
MODEL = ROOT / "results" / "decision_fusion_v4" / "v4_selected_logistic_policy.joblib"


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha_file(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def sha_json(value: Any) -> str:
    return sha_bytes(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def write_json(name: str, value: Any) -> Path:
    path = OUT / name
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    return path


def norm(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value).strip().lower())


def family(commands: list[str]) -> tuple[str, ...]:
    return tuple(norm(command) for command in commands)


def git_output(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True).stdout


def implementation_freeze() -> dict[str, Any]:
    status = git_output("status", "--porcelain=v1", "--untracked-files=all")
    diff = git_output("diff", "--binary")
    marker = ""
    for line in DECEIVER.read_text().splitlines():
        if line.startswith("V4_GENERATOR_INTEGRATION_VERSION = "):
            marker = line.split("=", 1)[1].strip().strip('"')
    packages = {}
    for name in ("pytest", "ruff", "pydantic", "joblib", "scikit-learn"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = "NOT_INSTALLED"
    return {
        "schema": "ragin.v4.postfix.implementation_environment_freeze.v1",
        "experiment_id": EXPERIMENT_ID,
        "git_head": git_output("rev-parse", "HEAD").strip(),
        "worktree_status_sha256": sha_bytes(status.encode()),
        "complete_relevant_worktree_diff_sha256": sha_bytes(diff.encode()),
        "worktree_status_line_count": len(status.splitlines()),
        "changed_code_paths": {
            "ragin/hisoka/deceiver.py": sha_file(DECEIVER),
            "ragin/hisoka/deception.py": sha_file(DECEPTION),
            "ragin/decision_fusion_v4/policy.py": sha_file(POLICY),
            "results/decision_fusion_v4/v4_selected_logistic_policy.joblib": sha_file(MODEL),
        },
        "required_deceiver_sha256": "a56e78e3d1a8e89e8edec73c86d073e6e29d8725a2dda0689ace40e045bfc420",
        "required_deception_sha256": "a9eb0f46cdd54d1a691c692ff9f893f9fbff413e2b5ab23a666ab0d88ef1bbb8",
        "policy_engine_changed": False,
        "generator_version_marker": marker,
        "dependencies": packages,
        "runtime_settings": {
            "RAGIN_RAG_MODE": "offline",
            "RAGIN_LAYA_ENABLED": "0",
            "RAGIN_LAYA_EVAL_REQUIRE_REAL_MODEL": "0",
            "RAGIN_HOST_FICTION": "0",
            "external_generation_calls": False,
            "network_changes": False,
            "attacker_commands_executed": False,
        },
    }


def load_sessions() -> list[dict[str, Any]]:
    return [json.loads(line) for line in SESSIONS.read_text().splitlines() if line.strip()]


def select_holdout(rows: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    old = json.loads(OLD_HOLDOUT.read_text())
    old_groups = {case["source_group_id"] for case in old["cases"]}
    old_families = {family(next(row["commands"] for row in rows if row["session_id"] == group)) for group in old_groups}
    candidates: dict[tuple[str, ...], list[dict[str, Any]]] = collections.defaultdict(list)
    for row in rows:
        commands = [str(command) for command in row.get("commands", []) if str(command).strip()]
        if not commands or row["session_id"] in old_groups:
            continue
        fam = family(commands)
        if fam in old_families:
            continue
        candidates[fam].append({"row": row, "commands": commands})
    ranked_families = sorted(candidates, key=lambda fam: sha_json([EXPERIMENT_ID, "family", list(fam)]))
    selected_families = ranked_families[:240]
    if len(selected_families) != 240:
        raise RuntimeError(f"candidate family pool has {len(ranked_families)}, expected at least 240")
    cases = []
    for rank, fam in enumerate(selected_families, 1):
        chosen = min(candidates[fam], key=lambda item: sha_json([EXPERIMENT_ID, "record", item["row"]["session_id"]]))
        row = chosen["row"]
        commands = chosen["commands"]
        family_sha = sha_json(list(fam))
        case_id = f"postfix-{rank:03d}-{sha_json([EXPERIMENT_ID, row['session_id'], list(fam)])[:12]}"
        cases.append(
            {
                "case_id": case_id,
                "source_group_id": row["session_id"],
                "source_family_sha256": family_sha,
                "sequence_sha256": sha_json(commands),
                "command_count": len(commands),
                "final_input_sha256": sha_bytes(commands[-1].encode()),
                "preceding_context_sha256": sha_json(commands[:-1]),
                "selection_rank": rank,
                "selection_family_key_sha256": sha_json([EXPERIMENT_ID, "family", list(fam)]),
                "selection_record_key_sha256": sha_json([EXPERIMENT_ID, "record", row["session_id"]]),
            }
        )
    holdout = {
        "schema": "ragin.v4.hf2024.postfix_family_disjoint_holdout.v1",
        "experiment_id": EXPERIMENT_ID,
        "status": "FROZEN_BEFORE_EXECUTION",
        "source_dataset": str(SESSIONS.relative_to(ROOT)),
        "source_dataset_sha256": sha_file(SESSIONS),
        "previous_holdout_sha256": sha_file(OLD_HOLDOUT),
        "N": len(cases),
        "cases": cases,
        "selection_rule": (
            "Sort normalized family keys by SHA256(EXPERIMENT_ID, family, family); retain first 240. "
            "Select one source-group record per family by minimum SHA256(EXPERIMENT_ID, record, source_group_id)."
        ),
        "normalization": "lowercase, trim, collapse whitespace per command, preserve command order",
        "excluded_previous_source_groups": len(old_groups),
        "excluded_previous_normalized_families": len(old_families),
        "unique_case_ids": len({case["case_id"] for case in cases}),
        "unique_source_groups": len({case["source_group_id"] for case in cases}),
        "unique_families": len({case["source_family_sha256"] for case in cases}),
        "old_family_overlap": len(
            old_families
            & {
                family(next(row["commands"] for row in rows if row["session_id"] == case["source_group_id"]))
                for case in cases
            }
        ),
        "synthetic_or_replay_records_selected": False,
    }
    protocol = {
        "schema": "ragin.v4.hf2024.postfix.protocol_freeze.v1",
        "experiment_id": EXPERIMENT_ID,
        "holdout_path": "results/decision_fusion_v4/hf2024_postfix_family_disjoint_v1/holdout_freeze.json",
        "arms": list(ARMS),
        "expected_records": 720,
        "pipeline": "Chrollo -> Don -> Evidence Gate -> Policy -> Hisoka Template Generator -> Verifier/HITL",
        "reference_free": True,
        "attacker_commands_executed": False,
        "external_generation_calls": False,
        "analysis_endpoints": [
            "gate_state",
            "selected_strategy",
            "strategy_delivery",
            "strategy_consumption",
            "template_id",
            "response_sha256",
            "verification",
            "approval",
            "latency_ms",
            "errors",
        ],
        "frozen_before_execution": True,
    }
    return holdout, protocol


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


def record(case: dict[str, Any], arm: str, output: dict[str, Any], elapsed_ms: float) -> dict[str, Any]:
    policy = output.get("policy_decision") or {}
    response = output.get("deception_response") or {}
    metadata = response.get("metadata") or {}
    text = str(response.get("response_text", ""))
    return {
        "schema": "ragin.v4.hf2024.postfix.raw_arm_case.v1",
        "case_id": case["case_id"],
        "source_group_id": case["source_group_id"],
        "source_family_sha256": case["source_family_sha256"],
        "arm": arm,
        "evidence_bundle_sha256": policy.get("evidence_bundle_sha256") or output.get("evidence_bundle_sha256"),
        "gate_state": policy.get("gate_state", "NOT_APPLICABLE_BASELINE"),
        "gate_reason": policy.get("gate_reason"),
        "valid_doc_ids": policy.get("valid_doc_ids", []),
        "selected_response_strategy": policy.get(
            "selected_response_strategy",
            (output.get("plan", {}).get("strategy") or {}).get("selected_response_strategy", "baseline"),
        ),
        "strategy_source": metadata.get(
            "strategy_source", "baseline_existing_behavior" if arm == "RAGIN_BASELINE" else "NOT_VERIFIABLE"
        ),
        "strategy_delivered_to_generator": metadata.get("strategy_delivered_to_generator", "NOT_VERIFIABLE"),
        "strategy_consumed_by_template": metadata.get("strategy_consumed_by_template", "NOT_VERIFIABLE"),
        "template_id": metadata.get("template_id", "NOT_VERIFIABLE"),
        "template_fallback_reason": metadata.get("template_fallback_reason", "NOT_VERIFIABLE"),
        "generation_input_sha256": policy.get("generation_input_sha256"),
        "response_sha256": sha_bytes(text.encode()),
        "response_text": text,
        "verifier_status": output.get("verification", {}),
        "hitl_status": output.get("approval", {}),
        "commit_trace": "NOT_VERIFIABLE",
        "serve_path": response.get("serve_path", "NOT_VERIFIABLE"),
        "error": response.get("error") or output.get("error"),
        "latency_ms": round(elapsed_ms, 3),
        "external_generation_calls": False,
        "attacker_command_executed": False,
        "raw_output_sha256": sha_json(output),
    }


def analysis(records: list[dict[str, Any]]) -> dict[str, Any]:
    by_case = collections.defaultdict(dict)
    for row in records:
        by_case[row["case_id"]][row["arm"]] = row
    pairs = [(by_case[case], case) for case in sorted(by_case)]

    def compare(left: str, right: str) -> dict[str, int]:
        different_response = sum(rows[left]["response_sha256"] != rows[right]["response_sha256"] for rows, _ in pairs)
        different_template = sum(rows[left]["template_id"] != rows[right]["template_id"] for rows, _ in pairs)
        return {"N": len(pairs), "response_hash_changed": different_response, "template_id_changed": different_template}

    def distribution(arm: str, key: str) -> dict[str, int]:
        return dict(sorted(collections.Counter(row[key] for row in records if row["arm"] == arm).items()))

    v4 = [row for row in records if row["arm"] != "RAGIN_BASELINE"]
    return {
        "schema": "ragin.v4.hf2024.postfix.reference_free_behavioral_analysis.v1",
        "experiment_id": EXPERIMENT_ID,
        "records": len(records),
        "cases": len(by_case),
        "gate_states": {arm: distribution(arm, "gate_state") for arm in ARMS},
        "fallback_counts": {
            arm: sum(
                bool(row["template_fallback_reason"] not in (None, "", "NOT_VERIFIABLE"))
                for row in records
                if row["arm"] == arm
            )
            for arm in ARMS
        },
        "strategy_distributions": {arm: distribution(arm, "selected_response_strategy") for arm in ARMS},
        "strategy_disagreement": {
            "baseline_vs_deterministic": sum(
                by_case[c][ARMS[0]]["selected_response_strategy"] != by_case[c][ARMS[1]]["selected_response_strategy"]
                for c in by_case
            ),
            "baseline_vs_logistic": sum(
                by_case[c][ARMS[0]]["selected_response_strategy"] != by_case[c][ARMS[2]]["selected_response_strategy"]
                for c in by_case
            ),
            "deterministic_vs_logistic": sum(
                by_case[c][ARMS[1]]["selected_response_strategy"] != by_case[c][ARMS[2]]["selected_response_strategy"]
                for c in by_case
            ),
        },
        "strategy_delivery": {
            "v4_records": len(v4),
            "delivered_true": sum(row["strategy_delivered_to_generator"] is True for row in v4),
            "consumed_true": sum(row["strategy_consumed_by_template"] is True for row in v4),
            "delivery_not_verifiable": sum(row["strategy_delivered_to_generator"] == "NOT_VERIFIABLE" for row in v4),
        },
        "matched_response_comparison": {
            "baseline_vs_deterministic": compare(ARMS[0], ARMS[1]),
            "baseline_vs_logistic": compare(ARMS[0], ARMS[2]),
            "deterministic_vs_logistic": compare(ARMS[1], ARMS[2]),
        },
        "template_ids": {arm: distribution(arm, "template_id") for arm in ARMS},
        "verifier": {
            "passed": sum(bool(row["verifier_status"].get("passed")) for row in records),
            "failed": sum(not bool(row["verifier_status"].get("passed")) for row in records),
            "deterministic_false": sum(row["verifier_status"].get("deterministic") is False for row in records),
        },
        "hitl": {
            "approval_records": len(records),
            "human_interrupts": sum(
                row["hitl_status"].get("decided_by", "").startswith("operator:") for row in records
            ),
            "auto_or_gateway": sum(
                not row["hitl_status"].get("decided_by", "").startswith("operator:") for row in records
            ),
        },
        "commit_observability": {"not_verifiable": sum(row["commit_trace"] == "NOT_VERIFIABLE" for row in records)},
        "latency_ms": {
            arm: {
                "N": sum(row["arm"] == arm for row in records),
                "mean": round(
                    sum(row["latency_ms"] for row in records if row["arm"] == arm)
                    / max(1, sum(row["arm"] == arm for row in records)),
                    3,
                ),
            }
            for arm in ARMS
        },
        "errors": dict(collections.Counter(row["error"] for row in records if row["error"])),
        "missing_or_incomplete_traces": {
            key: sum(row[key] in (None, "", "NOT_VERIFIABLE") for row in records)
            for key in ("evidence_bundle_sha256", "strategy_source", "template_id", "commit_trace")
        },
        "claims_boundary": [
            "Reference-free behavioral comparison only",
            "No accuracy, superiority, deception-quality, or attacker-engagement claim",
            "Same-dataset retrospective validation is not independent prospective field evidence",
        ],
    }


def synthetic_smoke() -> dict[str, Any]:
    from ragin.cycle.adapters import HisokaAdapter
    from ragin.cycle.graph import DeceptionGraph
    from ragin.decision_fusion_v4.benchmark import generate_corpus
    from ragin.hisoka.deceiver import AdaptiveDeceiver

    case = next(item for item in generate_corpus("V4D-", 1, 17) if item.stratum == "valid_recon")

    class Classifier:
        def classify(self, attacker_input: str, context: dict[str, Any]) -> dict[str, Any]:
            return {"skill_level": "novice", "confidence": 0.9}

    class Analyzer:
        def analyze(self, attacker_input: str, context: dict[str, Any]) -> dict[str, Any]:
            return {"evidence_bundle": case.state, "extracted_techniques": ["T1046"]}

    deceiver = AdaptiveDeceiver()
    graph = DeceptionGraph(
        classifier=Classifier(),
        analyzer=Analyzer(),
        deceiver=HisokaAdapter(deceiver=deceiver),
        decision_arm="RAGIN_V4_DETERMINISTIC",
        max_retries=1,
    )
    result = graph.invoke("POSTFIX-SMOKE-V4", "printf postfix-smoke", {})
    v4_meta = result["deception_response"].get("metadata", {})
    baseline = AdaptiveDeceiver().generate_response(
        "printf postfix-smoke",
        {
            "session_id": "POSTFIX-SMOKE-BASELINE",
            "classification": {
                "skill_level": "novice",
                "laya_decision": {
                    "availability": True,
                    "selected_response_strategy": "fake_success_and_return_visits",
                    "normalized_decision": {"is_attack": True, "attack_kind": "persistence"},
                },
            },
        },
    )
    return {
        "schema": "ragin.v4.postfix.synthetic_smoke.v1",
        "experiment_id": EXPERIMENT_ID,
        "synthetic_only": True,
        "included_in_evaluation": False,
        "baseline_preservation": "change applied" in baseline.response_text,
        "v4_policy_reached_generator": v4_meta.get("strategy_source") == "v4_policy_decision",
        "selected_strategy_consumed": v4_meta.get("strategy_consumed_by_template") is True,
        "verifier_passed": bool(result["verification"].get("passed")),
        "verifier_bypass_observed": False,
        "external_generation_call": False,
        "gateway_configured": deceiver._response_generator._gateway is None,
        "response_hash": sha_bytes(result["deception_response"]["response_text"].encode()),
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    freeze = implementation_freeze()
    write_json("implementation_environment_freeze.json", freeze)
    if (
        freeze["changed_code_paths"]["ragin/hisoka/deceiver.py"] != freeze["required_deceiver_sha256"]
        or freeze["changed_code_paths"]["ragin/hisoka/deception.py"] != freeze["required_deception_sha256"]
    ):
        raise RuntimeError("corrected implementation hash mismatch")
    write_json("synthetic_smoke.json", synthetic_smoke())
    rows = load_sessions()
    holdout, protocol = select_holdout(rows)
    write_json("holdout_freeze.json", holdout)
    write_json("protocol_freeze.json", protocol)
    sessions = {row["session_id"]: row for row in rows}
    raw_path = OUT / "raw_arm_outputs.jsonl"
    records: list[dict[str, Any]] = []
    started = time.time()
    try:
        with raw_path.open("w") as handle:
            for index, case in enumerate(holdout["cases"], 1):
                row = sessions[case["source_group_id"]]
                commands = [str(command) for command in row["commands"] if str(command).strip()]
                for arm in ARMS:
                    runtime = build_runtime(arm)
                    context = {
                        "session_id": case["case_id"],
                        "attacker_inputs": commands,
                        "features": {"commands": commands},
                    }
                    t0 = time.perf_counter()
                    output = runtime.invoke(f"{EXPERIMENT_ID}-{case['case_id']}-{arm}", commands[-1], context)
                    elapsed_ms = (time.perf_counter() - t0) * 1000
                    item = record(case, arm, output, elapsed_ms)
                    handle.write(json.dumps(item, sort_keys=True) + "\n")
                    handle.flush()
                    records.append(item)
                if index % 10 == 0:
                    print(f"completed_cases={index}/240 records={len(records)}", flush=True)
    except Exception as exc:
        write_json(
            "aborted_attempt_freeze.json",
            {
                "schema": "ragin.v4.postfix.aborted_attempt.v1",
                "experiment_id": EXPERIMENT_ID,
                "status": "ABORTED",
                "records_written": len(records),
                "raw_path": str(raw_path.relative_to(ROOT)),
                "error": type(exc).__name__,
                "error_message": str(exc),
                "started_unix": started,
                "aborted_unix": time.time(),
            },
        )
        raise
    raw_hash = sha_file(raw_path)
    raw_freeze = {
        "schema": "ragin.v4.postfix.raw_execution_freeze.v1",
        "experiment_id": EXPERIMENT_ID,
        "status": "RAW_EXECUTION_COMPLETE",
        "holdout_sha256": sha_file(OUT / "holdout_freeze.json"),
        "raw_output_path": str(raw_path.relative_to(ROOT)),
        "raw_output_sha256": raw_hash,
        "N_cases": 240,
        "expected_records": 720,
        "actual_records": len(records),
        "arm_counts": dict(collections.Counter(row["arm"] for row in records)),
        "reference_annotations": 0,
        "effectiveness_metrics": 0,
        "started_unix": started,
        "completed_unix": time.time(),
    }
    write_json("raw_execution_freeze.json", raw_freeze)
    behavioral = analysis(records)
    write_json("reference_free_behavioral_analysis.json", behavioral)
    manifest_paths = sorted(path for path in OUT.iterdir() if path.name != "sha256_manifest.json")
    manifest = {
        "schema": "ragin.v4.postfix.sha256_manifest.v1",
        "experiment_id": EXPERIMENT_ID,
        "files": {str(path.relative_to(ROOT)): sha_file(path) for path in manifest_paths},
    }
    write_json("sha256_manifest.json", manifest)
    print(json.dumps({"raw_execution_freeze": raw_freeze, "analysis": behavioral}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
