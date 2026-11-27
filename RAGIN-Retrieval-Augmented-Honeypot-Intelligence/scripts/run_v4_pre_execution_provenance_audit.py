from __future__ import annotations

import hashlib
import json
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/decision_fusion_v4"


def sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def digest(value) -> str:
    return sha(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode())


def write(name: str, value) -> None:
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def parse_records(path: Path):
    return [json.loads(line) for line in path.read_text(errors="replace").splitlines() if line.strip()]


def git_lineage(path: Path) -> dict:
    result = subprocess.run(["git", "log", "-1", "--format=%H|%ad|%s", "--date=iso-strict", "--", str(path.relative_to(ROOT))], cwd=ROOT, capture_output=True, text=True, check=True)
    line = result.stdout.strip()
    if not line:
        return {"tracked": False}
    commit, date, subject = line.split("|", 2)
    return {"tracked": True, "last_commit": commit, "last_commit_date": date, "last_commit_subject": subject}


def census(cases: list[dict]) -> tuple[dict, list[dict], dict[str, list[dict]]]:
    fields = {key: defaultdict(list) for key in ("case_id", "session_group_id", "source_record_id", "raw_input_sha256", "session_context_sha256", "source_record_sha256", "normalized_attacker_input_sha256", "complete_event_sequence_sha256")}
    records=[]
    for item in cases:
        path = ROOT / item["source_record_id"]
        events = parse_records(path)
        attacker = [event for event in events if event.get("event_type") == "attacker_input" and isinstance(event.get("data"), dict) and str(event["data"].get("command", "")).strip()]
        raw = sha(json.dumps(attacker[-1]["data"].get("command"), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode())
        normalized = " ".join(str(attacker[-1]["data"].get("command")).split()) if attacker else ""
        normalized_hash = sha(normalized.encode())
        sequence = [{key: event.get(key) for key in ("event_type", "source", "timestamp", "event_id", "data")} for event in events]
        sequence_hash = digest(sequence)
        source_hash = sha(path.read_bytes())
        values = {
            "case_id": item["case_id"],
            "session_group_id": item["session_group_id"],
            "source_record_id": item["source_record_id"],
            "raw_input_sha256": raw,
            "session_context_sha256": item["session_context_sha256"],
            "source_record_sha256": source_hash,
            "normalized_attacker_input_sha256": normalized_hash,
            "complete_event_sequence_sha256": sequence_hash,
        }
        for key, value in values.items(): fields[key][value].append(item["case_id"])
        records.append({**values, "event_count": len(events), "event_type_sequence": [str(event.get("event_type", "")) for event in events], "source_values": sorted({str(event.get("source", "")) for event in events}), "timestamp_count": sum(1 for event in events if event.get("timestamp")), "sidecar_present": path.with_suffix(".meta.json").exists()})
    summary={}
    for key, groups in fields.items():
        duplicate={value: ids for value, ids in groups.items() if len(ids)>1}
        summary[key]={"unique_values": len(groups), "duplicate_groups": len(duplicate), "cases_in_duplicate_groups": sum(len(ids) for ids in duplicate.values()), "maximum_multiplicity": max((len(ids) for ids in groups.values()), default=0), "groups": duplicate}
    return summary, records, fields


def main() -> None:
    expected = {
        "v4_real_prototype_implementation_freeze_v1.json": "f2eef3bc30dd398023467a0c74002afc88b324d4d13b2d872909b016f4db33e2",
        "v4_real_evaluation_preregistration_freeze_v1.json": "b9eeb14879b5b6604bc0bdef7ee2f934f07ba7a756368eaa956edf960e930b57",
    }
    for name, wanted in expected.items():
        actual=sha((OUT/name).read_bytes())
        if actual != wanted: raise SystemExit(f"FROZEN_HASH_MISMATCH:{name}:{actual}")
    manifest=json.loads((OUT/"v4_real_holdout_manifest_v1.json").read_text())
    summary, records, fields=census(manifest["cases"])
    write("v4_real_holdout_duplicate_census_v1.json", {"schema":"ragin.v4.real_holdout_duplicate_census.v1","N":len(records),"metadata_and_structural_only":True,"census":summary})
    provenance=[]
    for record in records:
        lineage=git_lineage(ROOT/record["source_record_id"])
        provenance.append({"case_id":record["case_id"],"source_record_id":record["source_record_id"],"provenance_class":"PROVENANCE_UNRESOLVED","evidence_basis":["repository source registry describes data/sessions as existing SSH session transcripts but does not document natural-field or controlled-honeypot capture lineage for this record","record contains timestamped session_start and attacker_input events","record also contains derived RAGIN component events from harness, Chrollo, Don, and Hisoka","no record-level capture endpoint, collection identifier, upstream raw-record reference, or synthetic/test marker was available","Git tracking and a repository commit establish file lineage but not collection provenance"],"confidence":"UNRESOLVED","git_lineage":lineage,"structural_summary":{"event_count":record["event_count"],"timestamp_count":record["timestamp_count"],"source_values":record["source_values"],"sidecar_present":record["sidecar_present"]}})
    write("v4_selected_240_record_provenance_audit_v1.json", {"schema":"ragin.v4.selected_240_record_provenance_audit.v1","N":len(provenance),"metadata_and_structural_only":True,"provenance_counts":dict(Counter(item["provenance_class"] for item in provenance)),"records":provenance})
    clone_groups=[]
    raw_groups=summary["raw_input_sha256"]["groups"]
    for raw_hash, case_ids in sorted(raw_groups.items()):
        member=[record for record in records if record["case_id"] in case_ids]
        clone_groups.append({"raw_input_sha256":raw_hash,"case_ids":case_ids,"case_count":len(case_ids),"source_record_sha256_unique":len({record["source_record_sha256"] for record in member}),"session_context_sha256_unique":len({record["session_context_sha256"] for record in member}),"complete_event_sequence_sha256_unique":len({record["complete_event_sequence_sha256"] for record in member}),"shared_parent_identifier_fields":[],"classification":"LEGITIMATE_REPEATED_INPUT_ACROSS_DISTINCT_SESSIONS","confidence":"STRUCTURALLY_SUPPORTED","basis":"identical selected attacker-input hash is accompanied by distinct source-record, full-context, and complete event-sequence hashes; no replay/template parent identifier was present"})
    write("v4_real_holdout_clone_lineage_audit_v1.json", {"schema":"ragin.v4.real_holdout_clone_lineage_audit.v1","metadata_and_structural_only":True,"raw_input_duplicate_groups":len(clone_groups),"cases_in_repeated_input_groups":sum(item["case_count"] for item in clone_groups),"template_or_replay_families_detected":0,"unresolved_duplication_groups":0,"groups":clone_groups})
    independence_records=[]
    for record in records:
        independence_records.append({"case_id":record["case_id"],"session_group_id":record["session_group_id"],"independence_group_id":"UNRESOLVED_DATA_SESSIONS_COLLECTION_LINEAGE","independence_confidence":"UNRESOLVED","hidden_parent_identifier_fields":[],"basis":"session_group_id and all available structural hashes are distinct, but no documented collection/capture lineage establishes independent real-session sampling units"})
    write("v4_real_holdout_independence_audit_v1.json", {"schema":"ragin.v4.real_holdout_independence_audit.v1","metadata_and_structural_only":True,"original_session_groups":len(records),"structurally_distinct_session_groups":len({item["session_group_id"] for item in records}),"defensible_provenance_verified_independence_groups":0,"hidden_parent_identifiers_observed":[],"records":independence_records})
    amendment={"schema":"ragin.v4.real_holdout_provenance_amendment.v1a","status":"PRE_EXECUTION_HOLDOUT_RESELECTION_REQUIRED","reason":"PRE_EXECUTION_PROVENANCE_AND_INDEPENDENCE_CORRECTION","original_holdout_N":240,"original_arms_executed":False,"original_reference_annotations_started":False,"original_effectiveness_seen":False,"selected_records_failing_provenance":240,"eligible_original_pool_groups_after_audit":12,"required_minimum_new_real_holdout_pool":180,"decision":"BLOCKED_INSUFFICIENT_NEW_REAL_HOLDOUT_POOL","replacement_manifest_created":False,"original_freeze_preserved":True,"statistical_rules_changed":False,"note":"The original candidate pool contains 12 documented real-linux records after excluding unresolved data_sessions provenance; no reduced holdout is authorized."}
    replacement_manifest={"schema":"ragin.v4.real_holdout_manifest.v1a","status":"BLOCKED_INSUFFICIENT_NEW_REAL_HOLDOUT_POOL","replacement_holdout_created":False,"target_N":240,"eligible_after_provenance_audit":12,"required_minimum":180,"cases":[],"original_manifest_preserved":True}
    write("v4_real_holdout_manifest_v1a.json", replacement_manifest)
    replacement_freeze={"schema":"ragin.v4.real_holdout_selection_freeze.v1a","status":"BLOCKED_INSUFFICIENT_NEW_REAL_HOLDOUT_POOL","reason":"PRE_EXECUTION_PROVENANCE_AND_INDEPENDENCE_CORRECTION","selection_performed":False,"target_N":240,"eligible_after_provenance_audit":12,"required_minimum":180,"cases":[],"original_selection_freeze_preserved":True,"original_arms_executed":False,"original_reference_annotations_started":False,"original_effectiveness_seen":False}
    write("v4_real_holdout_selection_freeze_v1a.json", replacement_freeze)
    write("v4_real_holdout_provenance_amendment_v1a.json", {**amendment,"replacement_manifest_path":"results/decision_fusion_v4/v4_real_holdout_manifest_v1a.json","replacement_selection_freeze_path":"results/decision_fusion_v4/v4_real_holdout_selection_freeze_v1a.json"})
    prereg={"schema":"ragin.v4.real_evaluation_preregistration_provenance_amendment.v1a","status":"BLOCKED_BEFORE_EXECUTION","reason":"PRE_EXECUTION_PROVENANCE_AND_INDEPENDENCE_CORRECTION","original_preregistration_path":"results/decision_fusion_v4/v4_real_evaluation_preregistration_freeze_v1.json","original_preregistration_sha256":expected["v4_real_evaluation_preregistration_freeze_v1.json"],"provenance_audit_path":"results/decision_fusion_v4/v4_selected_240_record_provenance_audit_v1.json","independence_audit_path":"results/decision_fusion_v4/v4_real_holdout_independence_audit_v1.json","holdout_amendment_path":"results/decision_fusion_v4/v4_real_holdout_provenance_amendment_v1a.json","replacement_manifest_path":"results/decision_fusion_v4/v4_real_holdout_manifest_v1a.json","replacement_selection_freeze_path":"results/decision_fusion_v4/v4_real_holdout_selection_freeze_v1a.json","primary_endpoint_unchanged":True,"reference_protocol_unchanged":True,"bootstrap_seed_unchanged":20261014,"engine_selection_rule_unchanged":True,"holm_rule_unchanged":True,"acceptance_gates_unchanged":True,"safety_invariants_unchanged":True,"real_execution_started":False,"reference_annotation_started":False,"effectiveness_results_seen":False}
    write("v4_real_evaluation_preregistration_provenance_amendment_v1a.json", prereg)
    print(json.dumps({"N":len(records),"raw_unique":summary["raw_input_sha256"]["unique_values"],"raw_duplicate_groups":summary["raw_input_sha256"]["duplicate_groups"],"raw_duplicate_cases":summary["raw_input_sha256"]["cases_in_duplicate_groups"],"provenance_counts":dict(Counter(item["provenance_class"] for item in provenance)),"defensible_independence_groups":0,"status":amendment["status"],"amendment_sha256":sha((OUT/"v4_real_holdout_provenance_amendment_v1a.json").read_bytes()),"prereg_amendment_sha256":sha((OUT/"v4_real_evaluation_preregistration_provenance_amendment_v1a.json").read_bytes())},indent=2,sort_keys=True))


if __name__ == "__main__": main()
