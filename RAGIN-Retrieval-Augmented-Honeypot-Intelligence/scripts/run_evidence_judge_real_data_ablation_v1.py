from __future__ import annotations

import hashlib
import json
import re
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

from ragin.decision_fusion_v4.benchmark import EvidenceQualityGate
from ragin.decision_fusion_v4.evidence_export import sha256_json
from ragin.don.command_aware_v2 import CommandAwareRetrieverV2
from ragin.don.evidence_judge import judge_bundle

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/evidence_judge_real_data_ablation_v1"
HF_SESSIONS = ROOT / "data/external/hf_shell_attack_2024/d201aafbbcbb5347078ca64f06c5428fa6814bc9/sessions/2024.jsonl"
COMMAND_CORPUS = ROOT / "data/corpus/command_aware_v2.jsonl"
V1_FREEZE = ROOT / "results/evidence_judge/evidence_judge_contract_freeze_v1.json"
PREVIOUS_HOLDOUTS = (
    ROOT / "results/decision_fusion_v4/v4_hf2024_retrospective_holdout_freeze_v1.json",
    ROOT / "results/decision_fusion_v4/v4_hf2024_retrospective_holdout_freeze_v1a.json",
    ROOT / "results/decision_fusion_v4/hf2024_postfix_family_disjoint_v1/holdout_freeze.json",
    ROOT / "results/decision_fusion_v4/hf2024_substantive_final_v1/holdout_freeze.json",
)
EXPERIMENT_ID = "EVIDENCE_JUDGE_REAL_ABLATION_V1"


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha_file(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def sha_json(value: Any) -> str:
    return sha_bytes(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode())


def norm(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value).strip().lower())


def family(commands: list[str]) -> tuple[str, ...]:
    return tuple(norm(command) for command in commands if norm(command))


def redact(value: str) -> str:
    value = re.sub(r"(?i)(password|passwd|secret|token)(\s*[=:]\s*)[^\s|;&]+", r"\1\2<REDACTED>", value)
    value = re.sub(r"[A-Za-z0-9+/]{32,}={0,2}", "<REDACTED_LONG_TOKEN>", value)
    return value


def load_rows() -> list[dict[str, Any]]:
    return [json.loads(line) for line in HF_SESSIONS.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_previous_exclusions(rows: list[dict[str, Any]]) -> tuple[set[str], set[tuple[str, ...]]]:
    by_id = {str(row["session_id"]): row for row in rows}
    groups: set[str] = set()
    families: set[tuple[str, ...]] = set()
    for path in PREVIOUS_HOLDOUTS:
        data = json.loads(path.read_text(encoding="utf-8"))
        for case in data["cases"]:
            group = str(case.get("source_group_id") or case.get("session_group_id"))
            groups.add(group)
            source = by_id.get(group)
            commands = source.get("commands", []) if source else case.get("commands", [])
            families.add(family([str(item) for item in commands]))
    return groups, families


def select_cases(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    groups, old_families = load_previous_exclusions(rows)
    candidates: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        commands = [str(item) for item in row.get("commands", []) if str(item).strip()]
        key = family(commands)
        if commands and str(row["session_id"]) not in groups and key not in old_families:
            candidates[key].append({"row": row, "commands": commands})
    ranked = sorted(candidates, key=lambda key: sha_json([EXPERIMENT_ID, "family", list(key)]))
    if len(ranked) < 120:
        raise RuntimeError(f"only {len(ranked)} eligible families remain")
    selected: list[dict[str, Any]] = []
    for rank, key in enumerate(ranked[:120], 1):
        item = min(candidates[key], key=lambda value: sha_json([EXPERIMENT_ID, "record", value["row"]["session_id"]]))
        row = item["row"]
        commands = item["commands"]
        selected.append({
            "case_id": f"real-hf2024-{rank:03d}-{sha_json([EXPERIMENT_ID, row['session_id'], list(key)])[:12]}",
            "source_group_id": str(row["session_id"]),
            "source_family_sha256": sha_json(list(key)),
            "sequence_sha256": sha_json(commands),
            "final_input_sha256": sha_bytes(commands[-1].encode()),
            "preceding_context_sha256": sha_json(commands[:-1]),
            "commands": commands,
            "final_input": commands[-1],
            "preceding_context": commands[:-1],
            "selection_rank": rank,
            "selection_family_key_sha256": sha_json([EXPERIMENT_ID, "family", list(key)]),
            "selection_record_key_sha256": sha_json([EXPERIMENT_ID, "record", row["session_id"]]),
        })
    protocol = {
        "schema": "ragin.evidence_judge_real_ablation.protocol.v1",
        "status": "SAME_SOURCE_RETROSPECTIVE_REFERENCE_PENDING",
        "experiment_id": EXPERIMENT_ID,
        "data_source": "HF-2024 pinned source-IP command aggregates",
        "source_path": str(HF_SESSIONS.relative_to(ROOT)),
        "source_revision": "d201aafbbcbb5347078ca64f06c5428fa6814bc9",
        "source_sha256": sha_file(HF_SESSIONS),
        "observation_unit": "one selected HF-2024 source-group command sequence; not asserted to be a native SSH session",
        "same_source_retrospective": True,
        "separate_prospective_cowrie_available": False,
        "source_rows": len(rows),
        "previous_source_groups_excluded": len(groups),
        "previous_families_excluded": len(old_families),
        "previous_holdout_paths": [str(path.relative_to(ROOT)) for path in PREVIOUS_HOLDOUTS],
        "eligible_families_before_selection": len(ranked),
        "selection_rule": "exclude prior source groups and normalized command families, then sort family keys by SHA256(JSON([EXPERIMENT_ID, family, normalized_family])) and choose one record per first 120 families by deterministic record hash",
        "selection_conditioning": "none on gate, judge, policy, labels, or outcomes",
        "arms": {"A": "Don V2 retrieval -> Evidence Gate", "B": "Don V2 retrieval -> Evidence Judge V1 -> Evidence Gate"},
        "frozen_settings": {"retrieval_version": "DON_COMMAND_AWARE_V2", "retrieval_corpus": str(COMMAND_CORPUS.relative_to(ROOT)), "gate_version": "EVIDENCE_GATE_V1", "judge_version": "EVIDENCE_JUDGE_V1", "policy_active": False, "generator_run": False},
        "reference_status": "REFERENCE_UNAVAILABLE",
        "reference_rule": "No self-generated labels, judge outputs, gate outcomes, or prior model outputs may serve as reference labels.",
        "analysis_plan": ["freeze selected cases and input hashes", "freeze retrieval evidence and blinded packet", "run matched arms", "freeze outputs", "score only if independent labels are later supplied"],
    }
    return selected, protocol


def corpus_docs() -> dict[str, dict[str, Any]]:
    rows = [json.loads(line) for line in COMMAND_CORPUS.read_text(encoding="utf-8").splitlines() if line.strip()]
    return {str(row["evidence_id"]): row for row in rows}


def retrieved_evidence(case: dict[str, Any], retriever: CommandAwareRetrieverV2, docs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    started = time.perf_counter_ns()
    result = retriever.retrieve(case["final_input"], case["preceding_context"], session_id=case["case_id"], classification="real_retrospective")
    latency_ms = (time.perf_counter_ns() - started) / 1_000_000
    trace = result["trace"]
    ids = [str(item["evidence_id"]) for item in trace["top_k"] if str(item["evidence_id"]) in docs]
    relevant_ids = [str(item) for item in trace["relevant_evidence_ids"]]
    candidates = []
    for doc_id in ids:
        row = docs[doc_id]
        candidates.append({
            "doc_id": doc_id,
            "title": str(row.get("title", "")),
            "content": str(row.get("content", "")),
            "source": str(row.get("source", "")),
            "provenance_status": "VALID" if row.get("source") and row.get("provenance_hash") else "UNKNOWN",
            "sanitization_status": "SANITIZED",
            "conflict_status": "NONE",
            "source_version": str(row.get("source_version", "")),
            "provenance_hash": str(row.get("provenance_hash", "")),
            "command_patterns": [str(value) for value in row.get("command_patterns", [])],
            "behavior_tags": [str(value) for value in row.get("behavior_tags", [])],
            "retrieval_score": next((item["score"] for item in trace["top_k"] if str(item["evidence_id"]) == doc_id), None),
            "retrieval_relevance": next((item["relevance"] for item in trace["top_k"] if str(item["evidence_id"]) == doc_id), None),
        })
    return {"trace": trace, "trace_sha256": sha256_json(trace), "retrieval_latency_ms": latency_ms, "documents": candidates, "relevant_doc_ids": relevant_ids}


def base_bundle(case: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    documents = evidence["documents"]
    ids = list(evidence["relevant_doc_ids"])
    return {
        "schema": "ragin.don.evidence_bundle.v4",
        "session": {"session_id": case["case_id"], "current_input": case["final_input"]},
        "chrollo": {"skill_level": "unknown", "confidence": 0.0, "features_used": [], "feature_values": {}},
        "don_analysis": {"classification": "unknown", "severity": "info", "confidence": 0.0, "tactics": [], "ttps_seen": [], "iocs": []},
        "retrieval": {
            "retrieval_status": "SUCCESS", "backend": "command_aware_v2", "implementation_version": "DON_COMMAND_AWARE_V2",
            "query": evidence["trace"]["query"], "sub_queries": [evidence["trace"]["query"]], "retrieved_count": len(documents), "relevant_count": len(ids),
            "relevant_doc_ids": ids, "query_coverage": evidence["trace"]["query_coverage"], "documents": documents,
            "trace_summary": {"rounds": 0, "degraded": False, "usable_successful_retrieval": True, "context_projection": evidence["trace"]["context_projection"], "top_k": evidence["trace"]["top_k"], "corpus_sha256": evidence["trace"]["corpus_sha256"], "retrieval_trace_sha256": evidence["trace_sha256"]},
        },
    }


def blinded_packet(cases: list[dict[str, Any]], evidence: dict[str, dict[str, Any]]) -> dict[str, Any]:
    packet_cases = []
    for case in cases:
        packet_cases.append({
            "case_id": case["case_id"],
            "source_group_id": case["source_group_id"],
            "observed_command": redact(case["final_input"]),
            "available_context": [redact(value) for value in case["preceding_context"]],
            "input_sha256": case["final_input_sha256"],
            "context_sha256": case["preceding_context_sha256"],
            "behavioral_claim": f"Whether the retrieved documents substantively support the behavior expressed by this observed command in its available context: {redact(case['final_input'])}",
            "retrieved_candidates": [{"doc_id": doc["doc_id"], "title": doc["title"], "content": redact(doc["content"]), "source": doc["source"], "provenance_hash": doc["provenance_hash"], "source_version": doc["source_version"], "review": {"DIRECT_SUPPORT": None, "PARTIAL": None, "IRRELEVANT": None, "CONTRADICTORY": None, "UNKNOWN": None}} for doc in evidence[case["case_id"]]["documents"]],
            "bundle_sufficiency_review": {"SUFFICIENT": None, "INSUFFICIENT": None, "CONFLICTING": None, "UNKNOWN": None},
        })
    return {"schema": "ragin.evidence_judge_blinded_reference_packet.v1", "status": "REFERENCE_UNAVAILABLE", "decisions_omitted": True, "judge_outputs_omitted": True, "gate_outputs_omitted": True, "cases": packet_cases}


def run_arms(cases: list[dict[str, Any]], evidence: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    gate = EvidenceQualityGate()
    results = []
    for case in cases:
        bundle_a = base_bundle(case, evidence[case["case_id"]])
        started = time.perf_counter_ns()
        gate_a = gate.evaluate(bundle_a)
        gate_a_ms = (time.perf_counter_ns() - started) / 1_000_000
        bundle_b = base_bundle(case, evidence[case["case_id"]])
        started = time.perf_counter_ns()
        judge = judge_bundle(case["final_input"], bundle_b["retrieval"]["documents"], preceding_commands=case["preceding_context"])
        judge_ms = (time.perf_counter_ns() - started) / 1_000_000
        bundle_b["evidence_judge"] = judge
        started = time.perf_counter_ns()
        gate_b = gate.evaluate(bundle_b)
        gate_b_ms = (time.perf_counter_ns() - started) / 1_000_000
        results.append({
            "case_id": case["case_id"], "input_sha256": case["final_input_sha256"], "retrieval_trace_sha256": evidence[case["case_id"]]["trace_sha256"],
            "retrieved_candidate_ids": [doc["doc_id"] for doc in evidence[case["case_id"]]["documents"]], "relevant_candidate_ids": evidence[case["case_id"]]["relevant_doc_ids"],
            "arm_a": {"gate": gate_a, "gate_latency_ms": gate_a_ms, "bundle_sha256": sha256_json(bundle_a)},
            "arm_b": {"judge": judge, "gate": gate_b, "judge_latency_ms": judge_ms, "gate_latency_ms": gate_b_ms, "bundle_sha256": sha256_json(bundle_b)},
            "retrieval_latency_ms": evidence[case["case_id"]]["retrieval_latency_ms"],
            "provenance_complete": all(doc["provenance_status"] == "VALID" for doc in evidence[case["case_id"]]["documents"]),
        })
    return results


def descriptive_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    labels = [row["arm_b"]["judge"]["sufficiency"]["label"] for row in results]
    return {
        "reference_status": "REFERENCE_UNAVAILABLE",
        "accuracy_metrics": "NOT_EVALUATED",
        "cases": len(results),
        "arm_a_gate_states": {state: sum(row["arm_a"]["gate"]["gate_state"] == state for row in results) for state in sorted({row["arm_a"]["gate"]["gate_state"] for row in results})},
        "arm_b_gate_states": {state: sum(row["arm_b"]["gate"]["gate_state"] == state for row in results) for state in sorted({row["arm_b"]["gate"]["gate_state"] for row in results})},
        "arm_b_sufficiency_labels": {label: labels.count(label) for label in sorted(set(labels))},
        "arm_a_retained_candidate_count": sum(len(row["arm_a"]["gate"]["valid_doc_ids"]) for row in results),
        "arm_b_retained_candidate_count": sum(len(row["arm_b"]["gate"]["valid_doc_ids"]) for row in results),
        "arm_b_abstention_or_rejection_count": sum(row["arm_b"]["gate"]["gate_state"] != "VALID_EVIDENCE" for row in results),
        "provenance_complete_count": sum(row["provenance_complete"] for row in results),
        "missing_trace_count": sum(not row["arm_b"]["judge"].get("trace_sha256") for row in results),
        "latency_ms": {"retrieval_sum": sum(row["retrieval_latency_ms"] for row in results), "judge_sum": sum(row["arm_b"]["judge_latency_ms"] for row in results), "arm_a_gate_sum": sum(row["arm_a"]["gate_latency_ms"] for row in results), "arm_b_gate_sum": sum(row["arm_b"]["gate_latency_ms"] for row in results)},
        "limitations": "Descriptive execution only because no genuine independent reviewer labels are present.",
    }


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def main() -> None:
    v1 = json.loads(V1_FREEZE.read_text(encoding="utf-8"))
    for relative, expected in v1["source_sha256"].items():
        if sha_file(ROOT / relative) != expected:
            raise RuntimeError(f"V1 source hash mismatch: {relative}")
    rows = load_rows()
    cases, protocol = select_cases(rows)
    docs = corpus_docs()
    retriever = CommandAwareRetrieverV2(corpus_path=COMMAND_CORPUS)
    evidence: dict[str, dict[str, Any]] = {}
    for case in cases:
        evidence[case["case_id"]] = retrieved_evidence(case, retriever, docs)
    protocol["retrieval_freeze"] = {"retrieval_trace_version": "DON_COMMAND_AWARE_V2", "retrieval_corpus_sha256": sha_file(COMMAND_CORPUS), "candidate_count_per_case": "top_k candidates from frozen trace", "retrieval_executed_before_arm_comparison": True}
    OUT.mkdir(parents=True, exist_ok=True)
    write_json(OUT / "protocol_freeze.json", protocol)
    write_json(OUT / "frozen_case_selection.json", {"schema": "ragin.evidence_judge_real_ablation.selection.v1", "status": "FROZEN_BEFORE_ARM_OUTCOMES", "cases": [{key: value for key, value in case.items() if key != "commands" and key != "final_input" and key != "preceding_context"} for case in cases]})
    write_json(OUT / "frozen_arm_inputs.json", {"schema": "ragin.evidence_judge_real_ablation.arm_inputs.v1", "status": "FROZEN_BEFORE_ARM_OUTCOMES", "cases": cases})
    write_json(OUT / "frozen_retrieval_evidence.json", {"schema": "ragin.evidence_judge_real_ablation.retrieval_evidence.v1", "status": "FROZEN_BEFORE_ARM_OUTCOMES", "cases": evidence})
    write_json(OUT / "blinded_reference_packet.json", blinded_packet(cases, evidence))
    results = run_arms(cases, evidence)
    write_json(OUT / "matched_arm_results.json", {"schema": "ragin.evidence_judge_real_ablation.matched_results.v1", "status": "FROZEN_BEFORE_SCORING", "reference_status": "REFERENCE_UNAVAILABLE", "results": results})
    write_json(OUT / "descriptive_execution_summary.json", descriptive_summary(results))
    (OUT / "limitations_report.md").write_text("\n".join(["# Real-data Evidence Judge V1 ablation limitations", "", "The preferred separate prospective Cowrie/SSH corpus was unavailable. This ablation therefore uses 120 same-source retrospective HF-2024 source-group command families, selected after excluding prior source groups and normalized command families.", "", "No genuine independent reviewer labels were available. The blinded packet contains empty candidate and bundle review fields, and no Judge, Gate, or prior model output was used as reference truth. Accuracy, precision, recall, false admissions, false rejections, confidence intervals, and paired agreement are therefore not evaluated.", "", "The two arms share the frozen command/context inputs, Don V2 retrieval configuration, retrieved evidence, corpus, and existing gate. No policy, generator, verifier, HITL, or commit path was run.", ""]), encoding="utf-8")
    manifest_paths = ["protocol_freeze.json", "frozen_case_selection.json", "frozen_arm_inputs.json", "frozen_retrieval_evidence.json", "blinded_reference_packet.json", "matched_arm_results.json", "descriptive_execution_summary.json", "limitations_report.md", "../evidence_judge/evidence_judge_contract_freeze_v1.json", "../decision_fusion_v4/v4_hf2024_retrospective_holdout_freeze_v1.json", "../decision_fusion_v4/v4_hf2024_retrospective_holdout_freeze_v1a.json", "../decision_fusion_v4/hf2024_postfix_family_disjoint_v1/holdout_freeze.json", "../decision_fusion_v4/hf2024_substantive_final_v1/holdout_freeze.json", "../../data/external/hf_shell_attack_2024/d201aafbbcbb5347078ca64f06c5428fa6814bc9/sessions/2024.jsonl", "../../data/corpus/command_aware_v2.jsonl", "../../ragin/don/evidence_judge.py", "../../ragin/decision_fusion_v4/evidence_export.py", "../../ragin/decision_fusion_v4/benchmark.py", "../../scripts/run_evidence_judge_real_data_ablation_v1.py"]
    write_json(OUT / "sha256_manifest.json", {"schema": "ragin.evidence_judge_real_ablation.sha256_manifest.v1", "reference_status": "REFERENCE_UNAVAILABLE", "files": {path: sha_file((OUT / path).resolve()) for path in manifest_paths}})
    print(json.dumps({"status": "REAL_DATA_ABLATION_REFERENCE_PENDING", "cases": len(cases), "output": str(OUT.relative_to(ROOT)), "selection_sha256": sha_file(OUT / "frozen_case_selection.json")}, sort_keys=True))


if __name__ == "__main__":
    main()
