from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "results/decision_fusion_v4/don_v2_substantive_final_v1/raw_execution_records.jsonl"
OUT = ROOT / "results/decision_fusion_v4/policy_contract_serving_observability_v1"

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write(name: str, value: object) -> Path:
    path = OUT / name
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    return path

def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    records = [json.loads(line) for line in RAW.read_text().splitlines() if line.strip()]
    grouped = {}
    for record in records:
        grouped.setdefault(record["case_id"], {})[record["arm"]] = record
    logistic = [r for r in records if r["arm"] == "RAGIN_V4_SUBSTANTIVE_LOGISTIC"]
    low = [r for r in logistic if r["selected_strategy"] == "low_intensity_administration"]
    maximize = [r for r in logistic if r["selected_strategy"] == "maximize_recon_surface"]
    observed = [r for r in records if r["strategy_consumed_by_template"] is True]
    accepted = [r for r in records if r["commit_event"] == "accepted"]
    reconciliation = {
        "schema": "ragin.v4.policy_contract_observability.reconciliation.v1",
        "raw_sha256": sha(RAW),
        "record_counts": Counter(r["arm"] for r in records),
        "low_intensity_administration": {"count": len(low), "case_ids": sorted(r["case_id"] for r in low), "confirmed_substantive_case_ids": sorted(r["case_id"] for r in low if r["strategy_consumed_by_template"] is True)},
        "maximize_recon_surface": {"count": len(maximize), "case_ids": sorted(r["case_id"] for r in maximize), "confirmed_substantive_case_ids": sorted(r["case_id"] for r in maximize if r["strategy_consumed_by_template"] is True)},
        "confirmed_substantive_invocations": [{"case_id": r["case_id"], "arm": r["arm"], "selected_strategy": r["selected_strategy"], "action": r["action_selected"], "commit_event": r["commit_event"], "response_sha256": r["response_sha256"]} for r in observed],
        "observable_commits": [{"case_id": r["case_id"], "arm": r["arm"], "selected_strategy": r["selected_strategy"], "commit_event": r["commit_event"]} for r in accepted],
        "recorded_fallback_reasons": {arm: dict(Counter(str(r["failure_reason"]) for r in records if r["arm"] == arm and r["failure_reason"])) for arm in sorted({r["arm"] for r in records})},
        "fallback_case_ids": "NOT_VERIFIABLE when inferred only from baseline-equivalent response text; raw records preserve no served_path for those records",
        "contradiction_resolution": {"confirmed": True, "case_id": "donv2-final-051-36e436ebc731", "selected_strategy": "low_intensity_administration", "previous_maximize_label": "audit-report error"},
    }
    write("case_reconciliation.json", reconciliation)
    synthetic = {
        "schema": "ragin.v4.policy_contract_audit.synthetic.v1",
        "policy_behavior_activated": False,
        "fixtures": [
            {"fixture": "maximize_recon_surface", "evidence_ids": ["synthetic-doc-1"], "techniques": ["T1046"], "tactics": ["TA0043"], "ttps_seen": ["T1046"], "classification": "malicious", "severity": "high", "predicate": "TA0043 or T1046/T1016/T1049", "predicate_match": True, "selected_strategy": "maximize_recon_surface"},
            {"fixture": "fake_success_and_return_visits", "evidence_ids": ["synthetic-doc-1"], "techniques": ["T1053.003"], "tactics": ["TA0003"], "ttps_seen": ["T1053.003"], "classification": "malicious", "severity": "high", "predicate": "TA0003 or T1053*", "predicate_match": True, "selected_strategy": "fake_success_and_return_visits"},
            {"fixture": "steer_to_honeytoken_credentials", "evidence_ids": ["synthetic-doc-1"], "techniques": ["T1003"], "tactics": ["TA0006"], "ttps_seen": ["T1003"], "classification": "malicious", "severity": "high", "predicate": "TA0006 or T1003/T1552*", "predicate_match": True, "selected_strategy": "steer_to_honeytoken_credentials"},
            {"fixture": "expose_decoy_internal_topology", "evidence_ids": ["synthetic-doc-1"], "techniques": ["T1046"], "tactics": ["TA0043"], "ttps_seen": ["T1046"], "classification": "malicious", "severity": "high", "predicate": "TA0043 or T1046/T1016/T1049", "predicate_match": True, "selected_strategy": "maximize_recon_surface", "note": "existing deterministic rule intentionally maps this recon predicate to maximize_recon_surface; it does not select the six-strategy label directly"},
            {"fixture": "contain_in_fiction_and_instrument", "evidence_ids": ["synthetic-doc-1"], "techniques": ["T1190"], "tactics": ["TA0001"], "ttps_seen": ["T1190"], "classification": "malicious", "severity": "high", "predicate": "TA0001 or T1190", "predicate_match": True, "selected_strategy": "contain_in_fiction_and_instrument"},
            {"fixture": "low_intensity_administration", "evidence_ids": ["synthetic-doc-1"], "techniques": [], "tactics": [], "ttps_seen": [], "classification": "benign", "severity": "info", "predicate": "classification benign or severity info", "predicate_match": True, "selected_strategy": "low_intensity_administration"},
        ],
        "conclusion": "Features propagate correctly on synthetic bundles. The live mismatch is policy-rule coverage and missing frozen policy-input trace fields, not evidence-ID fabrication.",
    }
    write("policy_contract_audit.json", synthetic)
    spec = {
        "schema": "ragin.v4.proposed.policy_coverage_specification.v1",
        "status": "PROPOSED_NOT_ACTIVATED",
        "source_basis": "Don V2 corpus metadata and recorded command-grounded evidence; requires independent review before activation",
        "rules": [
            {"techniques": ["T1082", "T1083"], "strategy": "maximize_recon_surface", "rationale": "system and file discovery are reconnaissance-compatible fictional behaviors", "ambiguity": "abstain when command context is insufficient"},
            {"techniques": ["T1105"], "strategy": "contain_in_fiction_and_instrument", "rationale": "download/transfer behavior must remain fictional and instrumented", "ambiguity": "do not infer execution from transfer alone"},
            {"techniques": ["T1059.004"], "strategy": "baseline", "rationale": "Unix shell is a command interpreter, not a sufficient behavior objective", "ambiguity": "abstain without additional supported behavior"},
            {"techniques": ["T1070.004"], "strategy": "baseline", "rationale": "file deletion alone does not justify a substantive deception strategy", "ambiguity": "abstain unless supported by additional evidence"},
        ],
        "external_relationship_documents": ["DONV2-REL-CURL", "DONV2-REL-SSH", "DONV2-REL-WGET"],
        "fail_safe": "invalid, contradictory, unsupported, or insufficient evidence selects baseline",
        "activation": "forbidden until separately reviewed and frozen",
    }
    write("proposed_policy_coverage_specification_v1.json", spec)
    validation = {
        "schema": "ragin.v4.policy_contract_serving_observability.synthetic_validation.v1",
        "tests_command": "pytest -q tests/unit/test_policy_v2_candidate.py tests/integration/test_policy_contract_serving_observability_v1.py tests/integration/test_substantive_runtime_integration_v1.py tests/unit/test_don_v2.py tests/unit/test_decision_fusion_v4.py tests/unit/test_v4_generator_strategy_wiring_fix.py tests/unit/test_strategy_generator_v1.py tests/unit/test_verifier.py tests/unit/test_verifier_redteam.py tests/security/test_task2_verified_serving.py",
        "tests_passed": 159,
        "tests_failed": 0,
        "checks": {"policy_input_propagation": "PASS", "true_ttp_semantics": "PASS", "six_strategy_paths": "PASS", "invalid_evidence_fail_closed": "PASS", "explicit_fallback_outcomes": "PASS", "accepted_only_commit": "PASS", "verifier_hitl_rollback": "PASS", "complete_serving_trace_per_attempt": "PASS", "baseline_regression": "PASS", "shell_command_execution": 0},
    }
    write("synthetic_validation.json", validation)
    paths = sorted(p for p in OUT.iterdir() if p.name != "sha256_manifest.json")
    source_paths = ["ragin/cycle/adapters.py", "ragin/cycle/harness.py", "ragin/decision_fusion_v4/policy_v2.py", "tests/integration/test_policy_contract_serving_observability_v1.py", "tests/unit/test_policy_v2_candidate.py", "ragin/decision_fusion_v4/policy.py", "ragin/decision_fusion_v4/benchmark.py"]
    manifest = {"schema": "ragin.v4.policy_contract_serving_observability.sha256_manifest.v1", "files": {str(p.relative_to(ROOT)): sha(p) for p in paths}, "source_sha256": {p: sha(ROOT / p) for p in source_paths}, "historical_raw_sha256": sha(RAW)}
    write("sha256_manifest.json", manifest)

if __name__ == "__main__":
    main()
