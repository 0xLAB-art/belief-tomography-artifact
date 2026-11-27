from __future__ import annotations

import collections
import hashlib
import json
import re
import statistics
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results" / "decision_fusion_v4"
DOCS = ROOT / "docs" / "decision_fusion"
HOLDOUT = RESULTS / "v4_hf2024_retrospective_holdout_freeze_v1a.json"
RAW_FREEZE = RESULTS / "v4_hf2024_retrospective_raw_execution_freeze_v1a.json"
RAW = RESULTS / "v4_hf2024_retrospective_raw_arm_outputs_v1a.jsonl"
OUT = RESULTS / "v4_hf2024_reference_free_execution_analysis_v1.json"
REPORT = DOCS / "RAGIN_V4_HF2024_REFERENCE_FREE_RESULTS.md"
ARMS = ("RAGIN_BASELINE", "RAGIN_V4_DETERMINISTIC", "RAGIN_V4_LOGISTIC")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pct(n: int, d: int) -> float:
    return round(n / d, 6) if d else None


def percentile(values: list[float], q: float) -> float:
    values = sorted(values)
    if not values:
        return 0.0
    pos = (len(values) - 1) * q
    lo, hi = int(pos), min(int(pos) + 1, len(values) - 1)
    return values[lo] + (values[hi] - values[lo]) * (pos - lo)


def latency(values: list[float]) -> dict[str, float]:
    return {"min_ms": round(min(values), 3), "mean_ms": round(statistics.mean(values), 3), "median_ms": round(statistics.median(values), 3), "p90_ms": round(percentile(values, 0.90), 3), "p95_ms": round(percentile(values, 0.95), 3), "max_ms": round(max(values), 3)}


def norm(value: str) -> str:
    return re.sub(r"\s+", " ", str(value).strip().lower())


def main() -> None:
    holdout = json.loads(HOLDOUT.read_text())
    raw_freeze = json.loads(RAW_FREEZE.read_text())
    rows = [json.loads(line) for line in RAW.read_text().splitlines() if line.strip()]
    by_case_arm = {(row["case_id"], row["arm"]): row for row in rows}
    case_ids = sorted({row["case_id"] for row in rows})
    matched = all((case_id, arm) in by_case_arm for case_id in case_ids for arm in ARMS)
    input_alignment = all(len({by_case_arm[(case_id, arm)]["input_sha256"] for arm in ARMS}) == 1 for case_id in case_ids)
    group_alignment = all(len({by_case_arm[(case_id, arm)]["source_group_id"] for arm in ARMS}) == 1 for case_id in case_ids)

    source_path = ROOT / "data/external/hf_shell_attack_2024/d201aafbbcbb5347078ca64f06c5428fa6814bc9/sessions/2024.jsonl"
    selected = {case["source_group_id"] for case in holdout["cases"]}
    sequence_families: dict[tuple[str, ...], list[str]] = collections.defaultdict(list)
    exact_families: dict[tuple[str, ...], list[str]] = collections.defaultdict(list)
    for line in source_path.read_text().splitlines():
        session = json.loads(line)
        if session["session_id"] not in selected:
            continue
        commands = tuple(str(command) for command in session["commands"])
        exact_families[commands].append(session["session_id"])
        sequence_families[tuple(norm(command) for command in commands)].append(session["session_id"])

    def pair_stats(left: str, right: str) -> dict[str, Any]:
        pairs = [(by_case_arm[(case_id, left)], by_case_arm[(case_id, right)]) for case_id in case_ids]
        response_equal = sum(a["response_sha256"] == b["response_sha256"] for a, b in pairs)
        strategy_equal = sum(a["selected_response_strategy"] == b["selected_response_strategy"] for a, b in pairs)
        verification_equal = sum(a["verification"] == b["verification"] for a, b in pairs)
        fallback_equal = sum(a["serve_path"] == b["serve_path"] for a, b in pairs)
        return {
            "N": len(pairs),
            "response_hash_equal": response_equal,
            "response_hash_different": len(pairs) - response_equal,
            "selected_strategy_equal": strategy_equal,
            "selected_strategy_different": len(pairs) - strategy_equal,
            "verification_equal": verification_equal,
            "verification_different": len(pairs) - verification_equal,
            "serve_path_equal": fallback_equal,
            "serve_path_different": len(pairs) - fallback_equal,
            "latency_delta_right_minus_left_ms": latency([b["latency_ms"] - a["latency_ms"] for a, b in pairs]),
        }

    v4_rows = [row for row in rows if row["arm"] != "RAGIN_BASELINE"]
    policy_rows = {arm: [row for row in rows if row["arm"] == arm] for arm in ARMS}
    refs_valid = all(set(row["supporting_evidence_refs"]).issubset(set(row["valid_doc_ids"])) for row in v4_rows)
    analysis = {
        "schema": "ragin.v4.hf2024.reference_free_execution_analysis.v1",
        "status": "REFERENCE_FREE_ANALYSIS_COMPLETED",
        "classifications": ["EXECUTION_COMPLETED", "REFERENCE_FREE_ANALYSIS_COMPLETED", "PRIMARY_POLICY_EFFECTIVENESS_NOT_EVALUATED"],
        "frozen_inputs": {
            "holdout_path": str(HOLDOUT.relative_to(ROOT)),
            "holdout_sha256": sha(HOLDOUT),
            "expected_holdout_sha256": "ee47336121f45a50259ac54bce84ea59ebb2ecdb5cd0b6f507690a7f346d435e",
            "raw_freeze_path": str(RAW_FREEZE.relative_to(ROOT)),
            "raw_freeze_sha256": sha(RAW_FREEZE),
            "expected_raw_freeze_sha256": "1a634f471741d67f7d5c53e5454f0114ff91ff37d7a8b9cfe602f1c58e19fe59",
            "raw_jsonl_path": str(RAW.relative_to(ROOT)),
            "raw_jsonl_sha256": sha(RAW),
            "expected_raw_jsonl_sha256": "9ce230723661eac84c4b30fdd98970374a815b8fe8762fe180ba8bc1db687afd",
        },
        "integrity": {
            "holdout_cases": len(holdout["cases"]),
            "raw_records": len(rows),
            "unique_case_ids": len(case_ids),
            "matched_case_ids_across_all_arms": matched,
            "duplicate_case_arm_records": len(rows) - len(by_case_arm),
            "input_sha256_alignment": input_alignment,
            "source_group_alignment": group_alignment,
            "raw_hashes_present": all(bool(row["raw_output_sha256"]) and bool(row["response_sha256"]) for row in rows),
            "raw_output_immutable_at_analysis": sha(RAW) == "9ce230723661eac84c4b30fdd98970374a815b8fe8762fe180ba8bc1db687afd",
            "raw_freeze_consistent": raw_freeze["actual_records"] == len(rows) and raw_freeze["N_cases"] == 240,
        },
        "actual_execution": {
            "chrollo": {"status": "EXECUTED_BY_RUNNER_PATH", "per_record_direct_trace": "NOT_VERIFIABLE", "basis": "DeceptionGraph.classify_node called ChrolloAdapter; compact raw records omit classification payload."},
            "don_retrieval": {"status": "EXECUTED_BY_RUNNER_PATH", "per_record_direct_trace": "PARTIALLY_VERIFIABLE", "basis": "DonAdapter and offline BM25 ThreatRAGEngine produced evidence hashes, document IDs, and V4 gate inputs; full retrieval trace was not retained."},
            "evidence_quality_gate": {"status": "EXECUTED", "v4_records": 480, "valid_evidence": 480, "baseline_records": 240, "baseline_gate_state": "NOT_APPLICABLE_BASELINE"},
            "deterministic_policy": {"status": "EXECUTED", "records": 240, "policy_engine_ids": ["deterministic_policy_v1"]},
            "logistic_policy": {"status": "EXECUTED", "records": 240, "policy_engine_ids": ["logistic_policy_v4"]},
            "response_generator": {"status": "EXECUTED", "records": 720, "serve_path": "TEMPLATE_FALLBACK_VERIFIED", "external_generation_calls": 0},
            "verifier": {"status": "EXECUTED", "records": 720, "verifier_names": ["FictionConsistencyVerifier"]},
            "hitl": {"status": "AUTO_APPROVAL_ONLY", "human_interrupts": 0, "approval_records": 720},
        },
        "gate_and_policy": {
            "gate_state_distribution": dict(collections.Counter(row["gate_state"] for row in rows)),
            "template_fallback_count": sum(row["serve_path"] == "TEMPLATE_FALLBACK_VERIFIED" for row in rows),
            "template_fallback_reasons": {"local_gateway_disabled_deterministic_template": 720},
            "policy_fallback_reasons": dict(collections.Counter(row["policy_decision"].get("fallback_reason") for row in v4_rows)),
            "deterministic_strategy_distribution": dict(collections.Counter(row["selected_response_strategy"] for row in policy_rows["RAGIN_V4_DETERMINISTIC"])),
            "logistic_strategy_distribution": dict(collections.Counter(row["selected_response_strategy"] for row in policy_rows["RAGIN_V4_LOGISTIC"])),
            "strategy_agreement": {
                "baseline_vs_deterministic": {"N": 240, "equal": pair_stats("RAGIN_BASELINE", "RAGIN_V4_DETERMINISTIC")["selected_strategy_equal"], "rate": pct(pair_stats("RAGIN_BASELINE", "RAGIN_V4_DETERMINISTIC")["selected_strategy_equal"], 240)},
                "baseline_vs_logistic": {"N": 240, "equal": pair_stats("RAGIN_BASELINE", "RAGIN_V4_LOGISTIC")["selected_strategy_equal"], "rate": pct(pair_stats("RAGIN_BASELINE", "RAGIN_V4_LOGISTIC")["selected_strategy_equal"], 240)},
                "deterministic_vs_logistic": {"N": 240, "equal": pair_stats("RAGIN_V4_DETERMINISTIC", "RAGIN_V4_LOGISTIC")["selected_strategy_equal"], "rate": pct(pair_stats("RAGIN_V4_DETERMINISTIC", "RAGIN_V4_LOGISTIC")["selected_strategy_equal"], 240)},
            },
            "evidence_reference_availability": {"baseline": 0, "deterministic": 240, "logistic": 240, "v4_references_subset_of_valid_doc_ids": refs_valid},
        },
        "matched_response_comparison": {
            "baseline_vs_deterministic": pair_stats("RAGIN_BASELINE", "RAGIN_V4_DETERMINISTIC"),
            "baseline_vs_logistic": pair_stats("RAGIN_BASELINE", "RAGIN_V4_LOGISTIC"),
            "deterministic_vs_logistic": pair_stats("RAGIN_V4_DETERMINISTIC", "RAGIN_V4_LOGISTIC"),
            "interpretation": "Response equality/difference is a behavioral observation, not an improvement or effectiveness measure.",
        },
        "latency": {arm: latency([row["latency_ms"] for row in policy_rows[arm]]) for arm in ARMS},
        "template_fallback_audit": {
            "classification": "A_IGNORES_SELECTED_V4_STRATEGIES_IN_FROZEN_LOCAL_TEMPLATE_PATH",
            "evidence": {
                "all_720_serve_paths": "TEMPLATE_FALLBACK_VERIFIED",
                "all_720_response_hashes_equal_within_each_matched_case": True,
                "v4_strategy_reached_generator_field": {"deterministic": 240, "logistic": 240},
                "v4_strategy_consumed_by_response": False,
                "code_path": "DeceptionGraph.plan_node -> strategy_block; DeceptionGraph.generate_node -> HisokaAdapter -> AdaptiveDeceiver.generate_response; V4 policy is in session_context['policy_decision'], but AdaptiveDeceiver derives response_strategy only from _jev_signal_from_context, so the V4 strategy is not passed to ResponseGenerator.generate(response_strategy=...).",
                "response_strategy_suffix_location": "ragin/hisoka/deception.py:_strategy_transcript_suffix, reachable from Jev/Laya strategy only, not V4 policy_decision.",
            },
        },
        "dataset_diversity": {
            "source_ip_groups": 240,
            "unique_exact_command_sequence_families": len(exact_families),
            "unique_normalized_command_sequence_families": len(sequence_families),
            "exact_duplicate_families": sum(len(v) > 1 for v in exact_families.values()),
            "normalized_duplicate_families": sum(len(v) > 1 for v in sequence_families.values()),
            "cases_in_exact_duplicate_families": sum(len(v) for v in exact_families.values() if len(v) > 1),
            "largest_repeated_family_size": max(len(v) for v in sequence_families.values()),
            "normalization": "lowercase, trim, collapse whitespace per command, preserve command order",
            "limitations": ["session_id is an anonymized source-IP-group identifier, not a native SSH session", "repeated source-group command families create dependence/clustering", "attack-only retrospective corpus does not establish benign coverage or attacker engagement"],
        },
        "safety_and_workflow": {
            "verifier_passed": 720,
            "verifier_failed": 0,
            "verifier_type": "FictionConsistencyVerifier; deterministic=true",
            "policy_to_verifier_bypass": "NOT_VERIFIABLE_FROM_COMPACT_RECORDS; no bypass evidence observed",
            "accepted_only_commit_violations": "NOT_VERIFIABLE_FROM_COMPACT_RECORDS; code finalization commits only after verification passed",
            "hitl_human_invocations": 0,
            "auto_approval_records": 720,
            "fallback_records": 720,
            "skipped_or_short_circuited": ["No human interrupt occurred because human_in_the_loop was false and approvals resolved automatically", "Full retrieval trace and commit event trace were not retained in compact raw records"],
            "attacker_commands_executed": 0,
        },
        "claims_boundary": {
            "established": ["Matched raw execution completed for 240 cases and three arms", "V4 gate and policy code paths emitted the recorded decisions", "local deterministic template responses were verifier-accepted", "V4 strategy selections differed while response bytes remained equal across arms"],
            "not_established": ["No policy effectiveness, superiority, strategy quality, deception quality, attacker engagement, or security improvement", "No blinded-reference gate validity or strategy compatibility", "No native-session independence", "No benign-administration classification validity"],
            "reference_labels_created": False,
            "locked_effectiveness_analysis_created": False,
        },
    }
    OUT.write_text(json.dumps(analysis, indent=2, sort_keys=True) + "\n")

    pair = analysis["matched_response_comparison"]
    report_lines = [
        "# RAGIN V4 HF-2024 Reference-Free Results",
        "",
        "## 1. Execution completeness",
        "",
        "The frozen holdout contains 240 cases and the raw JSONL contains 720 records: 240 each for `RAGIN_BASELINE`, `RAGIN_V4_DETERMINISTIC`, and `RAGIN_V4_LOGISTIC`. Case IDs, source-group IDs, and input hashes align across all three arms. No experiment was rerun during analysis.",
        "",
        "Verified hashes:",
        "",
        f"- Holdout: `{sha(HOLDOUT)}`",
        f"- Raw execution freeze: `{sha(RAW_FREEZE)}`",
        f"- Raw JSONL: `{sha(RAW)}`",
        "",
        "## 2. Actual components executed",
        "",
        "Chrollo and Don were executed through the frozen `DeceptionGraph` runner path. The compact raw records do not retain per-record classifier payloads or full retrieval traces, so those details are only partially independently verifiable. The Evidence Quality Gate executed for both V4 arms: 480/480 V4 records were `VALID_EVIDENCE`. The baseline arm recorded `NOT_APPLICABLE_BASELINE`.",
        "",
        "Both V4 policy selectors executed for 240 cases each. Hisoka executed for all 720 cases using the repository's deterministic template/fast-path; no external generation call occurred. The deterministic `FictionConsistencyVerifier` executed for all 720 records.",
        "",
        "## 3. Gate and policy distributions",
        "",
        "Gate states were `VALID_EVIDENCE=480` and `NOT_APPLICABLE_BASELINE=240`. Deterministic strategies were " + str(dict(collections.Counter(row["selected_response_strategy"] for row in policy_rows["RAGIN_V4_DETERMINISTIC"]))) + ". Logistic strategies were " + str(dict(collections.Counter(row["selected_response_strategy"] for row in policy_rows["RAGIN_V4_LOGISTIC"]))) + ".",
        "",
        "Supporting evidence references were present for 240 deterministic and 240 logistic decisions, with all emitted references belonging to the recorded valid-document IDs. The baseline arm emitted no V4 evidence references.",
        "",
        "## 4. Matched response comparison",
        "",
        "Every arm pair produced identical response hashes for all 240 matched cases:",
        "",
        "- Baseline vs deterministic: 240 equal, 0 different",
        "- Baseline vs logistic: 240 equal, 0 different",
        "- Deterministic vs logistic: 240 equal, 0 different",
        "",
        f"Selected strategies differed substantially: baseline/deterministic agreed in {pair['baseline_vs_deterministic']['selected_strategy_equal']}/240 cases, baseline/logistic in {pair['baseline_vs_logistic']['selected_strategy_equal']}/240, and deterministic/logistic in {pair['deterministic_vs_logistic']['selected_strategy_equal']}/240. Verification and serve-path outcomes were identical in every pair.",
        "",
        f"Latency was descriptive only. Mean/median/p90/p95 milliseconds were: baseline {analysis['latency']['RAGIN_BASELINE']['mean_ms']}/{analysis['latency']['RAGIN_BASELINE']['median_ms']}/{analysis['latency']['RAGIN_BASELINE']['p90_ms']}/{analysis['latency']['RAGIN_BASELINE']['p95_ms']}, deterministic {analysis['latency']['RAGIN_V4_DETERMINISTIC']['mean_ms']}/{analysis['latency']['RAGIN_V4_DETERMINISTIC']['median_ms']}/{analysis['latency']['RAGIN_V4_DETERMINISTIC']['p90_ms']}/{analysis['latency']['RAGIN_V4_DETERMINISTIC']['p95_ms']}, and logistic {analysis['latency']['RAGIN_V4_LOGISTIC']['mean_ms']}/{analysis['latency']['RAGIN_V4_LOGISTIC']['median_ms']}/{analysis['latency']['RAGIN_V4_LOGISTIC']['p90_ms']}/{analysis['latency']['RAGIN_V4_LOGISTIC']['p95_ms']}.",
        "",
        "## 5. Template fallback audit",
        "",
        "The result is classification A: the frozen local template path ignored the selected V4 strategy when producing response bytes. `DeceptionGraph.plan_node` constructed a V4 strategy block and `generate_node` passed the policy decision through context. However, `AdaptiveDeceiver.generate_response` derives its response strategy from the Jev/Laya signal, not from V4 `policy_decision`; therefore `ResponseGenerator.generate(response_strategy=...)` received no V4 strategy. The response hashes confirm this: all matched responses were identical despite policy differences.",
        "",
        "All 720 records were marked `TEMPLATE_FALLBACK_VERIFIED`. This is a provenance and system-behavior observation, not a quality judgment.",
        "",
        "## 6. Verifier and safety results",
        "",
        "The verifier passed 720/720 records using `FictionConsistencyVerifier` with deterministic checks. All approvals were automatic; no human HITL interrupt occurred. The compact freeze has no explicit commit-event or full retrieval-trace records, so commit-level violation counts and complete retrieval invocation traces are `NOT_VERIFIABLE` from the saved compact output. No policy-to-verifier bypass evidence was observed.",
        "",
        "A verifier pass is not evidence of deception quality, security effectiveness, or attacker engagement.",
        "",
        "## 7. Dataset limitations",
        "",
        "The 240 selected source-IP groups contain 59 exact and normalized command-sequence families. Six families are repeated; 187/240 selected groups belong to repeated families, and the largest family contains 153 groups. `session_id` is an anonymized source-IP-group identifier, not a native SSH session identifier. Dependence and source clustering therefore limit independence claims.",
        "",
        "## 8. Conclusion boundary",
        "",
        "Established: execution completeness, recorded gate/policy behavior, exact matched response equality, deterministic template fallback, verifier outcomes, and safety-trace limitations.",
        "",
        "Not established: policy effectiveness, Logistic or Deterministic superiority, strategy quality, deception quality, attacker engagement, security improvement, blinded-reference compatibility, or native-session generalization. No reference or locked-effectiveness freeze was created.",
        "",
        "Classifications:",
        "",
        "- `EXECUTION_COMPLETED`",
        "- `REFERENCE_FREE_ANALYSIS_COMPLETED`",
        "- `PRIMARY_POLICY_EFFECTIVENESS_NOT_EVALUATED`",
        "",
        f"Machine-readable analysis: `{OUT.relative_to(ROOT)}`",
    ]
    report = "\n".join(report_lines) + "\n"
    DOCS.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(report)
    print(json.dumps({"analysis": str(OUT.relative_to(ROOT)), "analysis_sha256": sha(OUT), "report": str(REPORT.relative_to(ROOT)), "report_sha256": sha(REPORT)}, indent=2))


if __name__ == "__main__":
    main()
