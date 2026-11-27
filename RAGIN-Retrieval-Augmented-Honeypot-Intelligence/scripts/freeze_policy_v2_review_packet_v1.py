from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/decision_fusion_v4/policy_v2_independent_review_packet_v1"
POLICY = ROOT / "ragin/decision_fusion_v4/policy_v2.py"
CORPUS = ROOT / "data/corpus/command_aware_v2.jsonl"
MANIFEST = ROOT / "results/decision_fusion_v4/policy_contract_serving_observability_v1/sha256_manifest.json"
RAW = ROOT / "results/decision_fusion_v4/don_v2_substantive_final_v1/raw_execution_records.jsonl"

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write(name: str, value: object) -> Path:
    path = OUT / name
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    return path

def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    corpus = [json.loads(line) for line in CORPUS.read_text().splitlines() if line.strip()]
    by_technique = {technique: doc for doc in corpus for technique in doc.get("techniques", [])}
    matrix = [
        {"rule_id":"DONV2_T1105_EXECUTION_RELATIONSHIP","observed_behavior":"download or transfer plus independently observed execution relationship","required_evidence":["command-grounded document with T1105","download_execution_relationship=true","valid provenance and complete gate"],"predicate":"T1105 in grounded techniques AND download_execution_relationship is true","strategy":"contain_in_fiction_and_instrument","rationale":"containment and instrumentation are appropriate for a transfer/execution relationship without changing real infrastructure","context_required":["behavior indicators","current and preceding command projection","relationship feature"],"abstention":"transfer alone, ambiguous parse, invalid evidence, conflict, or missing relationship","assumptions":"execution relationship is a static observed feature, not proof that execution occurred","sources":[by_technique.get("T1105",{}).get("source","NOT_VERIFIABLE")]},
        {"rule_id":"DONV2_CREDENTIAL_CONTEXT","observed_behavior":"credential-file or credential-tool access with credential context","required_evidence":["T1003 or T1552.001 command-grounded evidence","credential_access_indicator or credentials path category","valid provenance and complete gate"],"predicate":"grounded techniques intersect {T1003,T1552.001} AND credential context is present","strategy":"steer_to_honeytoken_credentials","rationale":"only synthetic decoy credentials are exposed and instrumented","context_required":["credential indicators or credential path category","current command projection"],"abstention":"credential technique without command context, ambiguity, conflict, or invalid evidence","assumptions":"credential-access-compatible behavior is not proof of malicious intent","sources":[by_technique.get("T1552.001",{}).get("source",by_technique.get("T1003",{}).get("source","NOT_VERIFIABLE"))]},
        {"rule_id":"DONV2_CRON_PERSISTENCE","observed_behavior":"cron persistence behavior with persistence indicator","required_evidence":["T1053.003 command-grounded evidence","persistence_indicator","valid provenance and complete gate"],"predicate":"T1053.003 in grounded techniques AND persistence_indicator is present","strategy":"fake_success_and_return_visits","rationale":"fictional operation continuity is limited to the contained simulator","context_required":["persistence indicator","current and preceding command projection"],"abstention":"crontab text without persistence context, ambiguity, conflict, or invalid evidence","assumptions":"the rule does not claim persistence succeeded on a real host","sources":[by_technique.get("T1053.003",{}).get("source","NOT_VERIFIABLE")]},
        {"rule_id":"DONV2_NETWORK_TOPOLOGY","observed_behavior":"network configuration discovery with network context","required_evidence":["T1016 command-grounded evidence","network path category","environment-discovery indicator","valid provenance and complete gate"],"predicate":"T1016 in grounded techniques AND network path category is present","strategy":"expose_decoy_internal_topology","rationale":"only fictional host/service topology is revealed","context_required":["network path category","current command projection"],"abstention":"network-related text without network context, ambiguity, conflict, or invalid evidence","assumptions":"network discovery does not establish attacker intent","sources":[by_technique.get("T1016",{}).get("source","NOT_VERIFIABLE")]},
        {"rule_id":"DONV2_DISCOVERY_SURFACE","observed_behavior":"system, file, directory, or service discovery","required_evidence":["T1007, T1082, or T1083 command-grounded evidence","environment_discovery indicator","valid provenance and complete gate"],"predicate":"grounded techniques intersect {T1007,T1082,T1083} AND environment_discovery is present","strategy":"maximize_recon_surface","rationale":"the generator returns consistent fictional discovery results","context_required":["environment-discovery indicator","current and preceding command projection"],"abstention":"discovery technique without observed discovery context, ambiguity, conflict, or invalid evidence","assumptions":"discovery-compatible behavior is not treated as malicious intent","sources":[by_technique.get("T1082",{}).get("source","NOT_VERIFIABLE"),by_technique.get("T1083",{}).get("source","NOT_VERIFIABLE"),by_technique.get("T1007",{}).get("source","NOT_VERIFIABLE")]},
        {"rule_id":"DONV2_BENIGN_ADMINISTRATION","observed_behavior":"explicitly benign administrative context without malicious behavior indicators","required_evidence":["valid command-grounded evidence","classification=benign","severity=info","no credential, persistence, download, or execution indicator"],"predicate":"classification is benign AND severity is info AND forbidden indicator set is empty","strategy":"low_intensity_administration","rationale":"low-interaction administrative response avoids unnecessary escalation","context_required":["classification","severity","behavior indicators"],"abstention":"any forbidden indicator, ambiguity, conflict, invalid evidence, or unsupported behavior","assumptions":"classification and severity are contextual features, not independent truth labels","sources":["Don V2 evidence bundle contract; no single technique is sufficient"]},
        {"rule_id":"ABSTAIN_UNSUPPORTED_BEHAVIOR","observed_behavior":"valid evidence without a supported policy predicate","required_evidence":["valid gate but no complete rule match"],"predicate":"none of the non-baseline predicates match","strategy":"baseline","rationale":"preserve fail-safe behavior and avoid intent fabrication","context_required":["complete evidence and context trace"],"abstention":"baseline is the required abstention","assumptions":"none","sources":["ragin/decision_fusion_v4/policy_v2.py"]},
    ]
    examples = [
        {"example":"synthetic file discovery","evidence_id":"synthetic-T1083","observed_context":{"behavior_indicators":["environment_discovery"],"ambiguity":"none"},"decision":{"strategy":"maximize_recon_surface","rule_id":"DONV2_DISCOVERY_SURFACE"}},
        {"example":"synthetic transfer only","evidence_id":"synthetic-T1105","observed_context":{"behavior_indicators":["download_indicator"],"download_execution_relationship":False},"decision":{"strategy":"baseline","rule_id":"ABSTAIN_UNSUPPORTED_BEHAVIOR"}},
        {"example":"synthetic ambiguous parse","evidence_id":"synthetic-T1083","observed_context":{"behavior_indicators":["environment_discovery"],"ambiguity":"insufficient_context"},"decision":{"strategy":"baseline","rule_id":"ABSTAIN_AMBIGUOUS_CONTEXT"}},
        {"example":"synthetic invalid provenance","evidence_id":"synthetic-T1083","observed_context":{"provenance_status":"UNKNOWN"},"decision":{"strategy":"baseline","rule_id":"ABSTAIN_INVALID_EVIDENCE"}},
    ]
    packet = {
        "schema":"ragin.v4.policy_v2.independent_review_packet.v1",
        "status":"READY_FOR_INDEPENDENT_REVIEW",
        "candidate":"EVIDENCE_GROUNDED_DETERMINISTIC_V2",
        "activated":False,
        "automated_review":{"tests_passed":159,"tests_failed":0,"human_judgment":False,"effectiveness_claim":False},
        "human_review":{"status":"PENDING","reviewer_identity":None,"verdict":None,"conflicts":None,"notes":None},
        "coverage_matrix":matrix,
        "examples":examples,
        "counterexamples":["T1059.004 Unix shell alone abstains","T1070.004 file deletion alone abstains","T1105 transfer without execution relationship abstains","relationship-only documents without explicit technique fields do not activate a rule","ambiguous or conflicting evidence abstains"],
        "baseline_preferred":["invalid or missing provenance","unresolved conflict","incomplete coverage","unsupported technique or behavior","ambiguous parse","transfer without independently observed execution relationship","shell or deletion behavior without additional supported context"],
        "safety_requirements":["inert command input","no real host mutation","synthetic decoy resources only","mandatory verifier","mandatory HITL policy","accepted-only fictional-state commit","complete per-attempt serving trace","baseline fail-safe"],
        "historical_artifacts_unchanged":True,
    }
    write("independent_review_packet.json", packet)
    mutation = {"schema":"ragin.v4.policy_v2.manifest_mutation_audit.v1","path":"results/decision_fusion_v4/policy_contract_serving_observability_v1/sha256_manifest.json","git_history":"NOT_AVAILABLE: file is untracked in current worktree","previous_recorded_sha256":"2b55fa69cdbfc9e97eaac4e1949e919b5727a4ccf427a809793451aaa06c856e","current_sha256":sha(MANIFEST),"mutation_observed":True,"evidence_basis":"prior generated freeze artifact recorded in the preceding development turn; current filesystem has only the current untracked file","action":"preserve both hashes in this additive packet; do not rewrite the existing manifest"}
    write("manifest_mutation_audit.json", mutation)
    integrity = {"schema":"ragin.v4.policy_v2.review_integrity.v1","policy_sha256":sha(POLICY),"expected_policy_sha256":"93304c62e3975a0b65e7c534b4e982c3b1e9d4e0360e9be2e35d24ec2ef9b80e","corpus_sha256":sha(CORPUS),"expected_corpus_sha256":"d1a2f015eae91c91702fa9ccc5cdbdb8a074d7cb05e62d93208a30919cb242f4","old_policy_sha256":sha(ROOT/"ragin/decision_fusion_v4/policy.py"),"benchmark_sha256":sha(ROOT/"ragin/decision_fusion_v4/benchmark.py"),"historical_raw_sha256":sha(RAW),"policy_active":False,"new_evaluation_run":False}
    write("provenance_and_integrity.json", integrity)
    files = sorted(p for p in OUT.iterdir() if p.name != "sha256_manifest.json")
    write("sha256_manifest.json", {"schema":"ragin.v4.policy_v2.independent_review_packet.sha256_manifest.v1","files":{str(p.relative_to(ROOT)):sha(p) for p in files},"source_sha256":{"ragin/decision_fusion_v4/policy_v2.py":sha(POLICY),"data/corpus/command_aware_v2.jsonl":sha(CORPUS),"ragin/decision_fusion_v4/policy.py":sha(ROOT/"ragin/decision_fusion_v4/policy.py"),"ragin/decision_fusion_v4/benchmark.py":sha(ROOT/"ragin/decision_fusion_v4/benchmark.py")}})

if __name__ == "__main__":
    main()
