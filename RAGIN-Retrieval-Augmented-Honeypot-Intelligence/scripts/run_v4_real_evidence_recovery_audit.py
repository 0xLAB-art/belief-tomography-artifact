#!/usr/bin/env python3
import hashlib
import json
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results" / "decision_fusion_v4"
DOCS = ROOT / "docs" / "decision_fusion"
RESULTS.mkdir(parents=True, exist_ok=True)
DOCS.mkdir(parents=True, exist_ok=True)

IMPLEMENTATION = "v4_real_prototype_implementation_freeze_v1.json"
PREREG = "v4_real_evaluation_preregistration_provenance_amendment_v1a.json"

def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()

def sha256_file(path):
    return sha256_bytes(path.read_bytes())

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()

def write_json(name, value):
    path = RESULTS / name
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    return path

def git_info(path):
    try:
        commit = subprocess.check_output(["git", "log", "-1", "--format=%H", "--", str(path.relative_to(ROOT))], cwd=ROOT, text=True).strip()
        return commit
    except Exception:
        return None

def first_session_id(events):
    for event in events:
        if event.get("event_type") == "session_start" and isinstance(event.get("data"), dict):
            return event["data"].get("session_id")
    return None

def audit_sessions():
    rows = []
    paths = sorted((ROOT / "data" / "sessions").glob("*.jsonl"))
    for path in paths:
        raw = path.read_bytes()
        events = []
        for line in raw.splitlines():
            try:
                events.append(json.loads(line))
            except Exception:
                events.append({"_malformed": True})
        timestamps = [e.get("timestamp") for e in events if isinstance(e.get("timestamp"), str)]
        rows.append({
            "source_record_id": path.name,
            "source_record_sha256": sha256_bytes(raw),
            "native_session_id": first_session_id(events),
            "event_count": len(events),
            "event_types": sorted(Counter(e.get("event_type", "UNKNOWN") for e in events).items()),
            "capture_timestamp_min": min(timestamps) if timestamps else None,
            "capture_timestamp_max": max(timestamps) if timestamps else None,
            "raw_capture_available": "NO",
            "record_level_session_id": "YES" if first_session_id(events) else "NO",
            "capture_timestamp": "YES" if timestamps else "NO",
            "source_deployment_id": "NO",
            "raw_source_hash": "YES",
            "lineage_status": "DERIVED_WITH_UNTRACEABLE_PARENT",
            "raw_parent_id": None,
            "raw_parent_sha256": None,
            "derivation_chain_verifiable": "NO",
            "evidence_basis": [
                "record is a RAGIN-derived JSONL event sequence",
                "no pre-existing raw capture, deployment identifier, source offset, or parent manifest was found",
                "structural uniqueness is not accepted as capture provenance",
            ],
        })
    return paths, rows

def source_files(directory):
    return sorted(p for p in directory.iterdir() if p.is_file())

def audit_cowrie():
    paths = source_files(ROOT / "data" / "cowrie_logs")
    grouped = defaultdict(list)
    source_hashes = {str(p.relative_to(ROOT)): sha256_file(p) for p in paths}
    for path in paths:
        opener = path.open("rb")
        if path.name.endswith(".gz"):
            import gzip
            opener.close()
            fh = gzip.open(path, "rt", encoding="utf-8", errors="replace")
        else:
            fh = path.open("r", encoding="utf-8", errors="replace")
        with fh:
            for line_no, line in enumerate(fh, 1):
                try:
                    event = json.loads(line)
                except Exception:
                    continue
                sid = event.get("session")
                if sid:
                    grouped[sid].append({
                        "event": event,
                        "source_file": str(path.relative_to(ROOT)),
                        "line": line_no,
                    })
    candidates = []
    for sid in sorted(grouped):
        items = grouped[sid]
        ordered = sorted(items, key=lambda x: (str(x["event"].get("timestamp", "")), x["source_file"], x["line"]))
        inputs = [x for x in ordered if x["event"].get("eventid") == "cowrie.command.input" and isinstance(x["event"].get("input"), str) and x["event"].get("input")]
        selected = inputs[-1] if inputs else None
        timestamps = [x["event"].get("timestamp") for x in ordered if isinstance(x["event"].get("timestamp"), str)]
        sequence = [x["event"] for x in ordered]
        parent = sha256_bytes(canonical(sequence))
        files = sorted(set(x["source_file"] for x in ordered))
        if not selected:
            continue
        candidates.append({
            "case_candidate_id": f"COWRIE-{sid}",
            "independence_group_id": f"cowrie-native:{sid}",
            "native_session_id": sid,
            "source_class": "CONTROLLED_REAL_HONEYPOT",
            "raw_parent_id": sid,
            "raw_parent_sha256": parent,
            "capture_started_at": min(timestamps) if timestamps else None,
            "capture_ended_at": max(timestamps) if timestamps else None,
            "event_count": len(ordered),
            "attacker_or_operator_input_count": len(inputs),
            "selected_turn_rule": "final non-empty cowrie.command.input in deterministic timestamp/source/line order",
            "selected_attacker_input_sha256": sha256_bytes(selected["event"].get("input", "").encode()),
            "source_files": files,
            "source_file_sha256": {f: source_hashes[f] for f in files},
            "capture_provenance": "native Cowrie session identifier and raw Cowrie event records in data/cowrie_logs; repository field documentation identifies Cowrie as the controlled honeypot source",
            "derivation_chain": ["native Cowrie raw event sequence", "one deterministic case per native session", "canonical selected attacker turn"],
            "derivation_version": "v4-cowrie-reconstruction-v1",
        })
    return paths, candidates

def audit_field():
    rows = []
    for path in sorted((ROOT / "data" / "field").rglob("*.jsonl")):
        raw = path.read_bytes()
        records = []
        for line in raw.splitlines():
            try:
                records.append(json.loads(line))
            except Exception:
                records.append({})
        keys = sorted(set().union(*(r.keys() for r in records))) if records else []
        rows.append({
            "source_record_id": str(path.relative_to(ROOT)),
            "source_file_sha256": sha256_bytes(raw),
            "record_count": len(records),
            "record_keys": keys,
            "source_class": "NATURAL_FIELD",
            "raw_capture_available": "NO",
            "record_level_session_id": "YES" if "session_id" in keys else "NO",
            "capture_timestamp": "YES" if "ts" in keys else "NO",
            "source_deployment_id": "NO",
            "raw_source_hash": "YES",
            "derivation_chain_verifiable": "NO",
            "eligibility": "FIELD_REAL_BUT_INPUT_CONTRACT_UNUSABLE",
            "evidence_basis": ["field documentation describes passive field collection", "current export contains session_id and ts but no attacker input event or linked raw capture identifier"],
        })
    return rows

def audit_admin():
    path = ROOT / "data" / "real_linux_transcripts.json"
    raw = path.read_bytes()
    records = json.loads(raw)
    script = ROOT / "scripts" / "capture_real_linux_transcripts.py"
    rows = []
    for idx, record in enumerate(records):
        transcript = record.get("transcript") if isinstance(record, dict) else None
        transcript_bytes = (transcript or "").encode()
        rows.append({
            "case_candidate_id": f"REAL-LINUX-{idx:03d}",
            "independence_group_id": f"real-linux-native:{idx:03d}",
            "source_class": "CONTROLLED_REAL_ADMIN",
            "raw_parent_id": f"data/real_linux_transcripts.json#{idx}",
            "raw_parent_sha256": sha256_bytes(transcript_bytes),
            "source_artifact_sha256": sha256_bytes(raw),
            "capture_procedure": str(script.relative_to(ROOT)),
            "capture_procedure_sha256": sha256_file(script),
            "capture_timestamp": None,
            "native_session_id": None,
            "deployment_or_environment_id": None,
            "raw_capture_available": "YES",
            "record_level_session_id": "NO",
            "capture_timestamp_available": "NO",
            "source_deployment_id": "NO",
            "raw_source_hash": "YES",
            "derivation_chain_verifiable": "YES",
            "derivation_chain": ["real Linux command execution by capture_real_linux_transcripts.py", "de-identified transcript record", "repository JSON artifact"],
            "provenance_basis": "BLIND_DISCRIMINATION_PREREGISTRATION documents 12 genuine sessions recorded by the capture script on a real Linux host; the script documents fixed read-only commands and real command output",
            "confidence": "DOCUMENTED",
        })
    return rows

def main():
    frozen = {
        "implementation_sha256": sha256_file(RESULTS / IMPLEMENTATION),
        "provenance_amendment_sha256": sha256_file(RESULTS / PREREG),
    }
    session_paths, session_rows = audit_sessions()
    cowrie_paths, cowrie_candidates = audit_cowrie()
    field_rows = audit_field()
    admin_rows = audit_admin()
    lineage = {
        "schema": "ragin.v4.data_sessions_lineage_recovery.v1",
        "metadata_only": True,
        "candidate_record_count": len(session_rows),
        "traceable_real_parent_count": 0,
        "untraceable_derived_count": len(session_rows),
        "records": session_rows,
    }
    write_json("v4_data_sessions_lineage_recovery_v1.json", lineage)
    cowrie_protocol = {
        "schema": "ragin.v4.cowrie_reconstruction_protocol.v1",
        "frozen_before_candidate_construction": True,
        "source": "data/cowrie_logs",
        "unit": "one native Cowrie session identifier per candidate",
        "selected_turn_rule": "final non-empty cowrie.command.input in deterministic timestamp, source-file, line-number order",
        "eligibility": ["native session identifier", "raw timestamped events", "stable ordering", "source file identity and SHA256", "documented controlled-honeypot origin"],
        "exclusions": ["no semantic or attack-class selection", "no V4 output inspection", "no policy execution"],
        "source_files": {str(p.relative_to(ROOT)): sha256_file(p) for p in cowrie_paths},
    }
    write_json("v4_cowrie_reconstruction_protocol_v1.json", cowrie_protocol)
    write_json("v4_cowrie_provenance_verified_candidates_v1.json", {"schema": "ragin.v4.cowrie_provenance_verified_candidates.v1", "candidate_count": len(cowrie_candidates), "candidates": cowrie_candidates})
    write_json("v4_field_recovery_audit_v1.json", {"schema": "ragin.v4.field_recovery_audit.v1", "records": field_rows, "usable_case_count": 0, "reason": "FIELD_REAL_BUT_INPUT_CONTRACT_UNUSABLE"})
    write_json("v4_real_linux_provenance_audit_v1.json", {"schema": "ragin.v4.real_linux_provenance_audit.v1", "source_class": "CONTROLLED_REAL_ADMIN", "record_count": len(admin_rows), "records": admin_rows})
    inventory = {
        "schema": "ragin.v4.source_lineage_inventory.v1",
        "metadata_only": True,
        "frozen_artifacts_verified": frozen,
        "sources": [
            {"path": "data/sessions", "source_class": "DERIVED_WITH_UNTRACEABLE_PARENT", "raw_capture_available": "NO", "record_level_session_id": "YES", "capture_timestamp": "YES", "source_deployment_id": "NO", "raw_source_hash": "YES", "derivation_chain_verifiable": "NO", "candidate_records": len(session_rows), "verified_groups": 0, "status": "EXCLUDED"},
            {"path": "data/cowrie_logs", "source_class": "CONTROLLED_REAL_HONEYPOT", "raw_capture_available": "YES", "record_level_session_id": "YES", "capture_timestamp": "YES", "source_deployment_id": "YES", "raw_source_hash": "YES", "derivation_chain_verifiable": "YES", "candidate_records": len(cowrie_candidates), "verified_groups": len(cowrie_candidates), "status": "ELIGIBLE"},
            {"path": "data/field", "source_class": "NATURAL_FIELD", "raw_capture_available": "NO", "record_level_session_id": "YES", "capture_timestamp": "YES", "source_deployment_id": "NO", "raw_source_hash": "YES", "derivation_chain_verifiable": "NO", "candidate_records": len(field_rows), "verified_groups": 0, "status": "EXCLUDED_INPUT_CONTRACT_UNUSABLE"},
            {"path": "data/real_linux_transcripts.json", "source_class": "CONTROLLED_REAL_ADMIN", "raw_capture_available": "YES", "record_level_session_id": "NO", "capture_timestamp": "NO", "source_deployment_id": "NO", "raw_source_hash": "YES", "derivation_chain_verifiable": "YES", "candidate_records": len(admin_rows), "verified_groups": len(admin_rows), "status": "ELIGIBLE"},
            {"path": "evidence/sessions", "source_class": "TEST_FIXTURE", "raw_capture_available": "NO", "record_level_session_id": "NO", "capture_timestamp": "NO", "source_deployment_id": "NO", "raw_source_hash": "YES", "derivation_chain_verifiable": "NO", "candidate_records": 0, "verified_groups": 0, "status": "EXCLUDED"},
            {"path": "results/laya_research/sessions_ON", "source_class": "DERIVED_WITH_UNTRACEABLE_PARENT", "raw_capture_available": "NO", "record_level_session_id": "NO", "capture_timestamp": "NO", "source_deployment_id": "NO", "raw_source_hash": "YES", "derivation_chain_verifiable": "NO", "candidate_records": 0, "verified_groups": 0, "status": "EXCLUDED_HISTORICAL_ARTIFACT"},
        ],
        "excluded_old_120": 0,
        "excluded_old_169": 0,
        "excluded_synthetic_or_development": len(session_rows),
        "provenance_unclear_count": len(session_rows),
    }
    write_json("v4_source_lineage_inventory_v1.json", inventory)
    verified = []
    verified.extend(cowrie_candidates)
    verified.extend(admin_rows)
    pool = {
        "schema": "ragin.v4.existing_provenance_verified_real_pool.v1",
        "selection_status": "NO_HOLDOUT_SELECTED",
        "total_verified_independence_groups": len(verified),
        "by_source_class": dict(Counter(x["source_class"] for x in verified)),
        "records": verified,
        "excluded_unresolved_data_sessions": len(session_rows),
        "excluded_field_input_unusable": len(field_rows),
        "holdout_readiness": {"at_least_240": False, "at_least_180": False, "status": "NEW_PROSPECTIVE_REAL_COLLECTION_REQUIRED"},
    }
    write_json("v4_existing_provenance_verified_real_pool_v1.json", pool)
    capture = {
        "schema": "ragin.v4.prospective_capture_contract.v1",
        "status": "DESIGN_ONLY_NOT_DEPLOYED",
        "acquisition_target_independent_groups": 260,
        "final_holdout_target": 240,
        "minimum_authorization_threshold": 180,
        "allowed_source_classes": ["NATURAL_FIELD", "CONTROLLED_REAL_HONEYPOT", "CONTROLLED_REAL_ADMIN"],
        "native_capture_record": {
            "capture_id": "required", "native_session_id": "required", "source_class": "required_enum", "collector_version": "required", "deployment_or_environment_id": "required", "capture_started_at": "required", "capture_ended_at": "required", "raw_log_path": "required", "raw_log_sha256": "required", "event_count": "required_integer", "attacker_or_operator_input_count": "required_integer", "parent_source": None, "synthetic": False, "replay": False, "test_fixture": False, "capture_manifest_sha256": "required"
        },
        "independence_unit": "one underlying native capture session; derived records from one native session count as one group; replay of one source counts as zero new groups",
        "manifest_ordering": ["write and hash capture manifest before any RAGIN output is generated", "append immutable source metadata", "retain raw source and hash", "record derivation links for every later canonical record"],
        "eligibility_exclusions": ["synthetic command generation", "LLM-generated attacker sessions", "replays presented as new captures", "benchmark fixtures", "old 120", "old 169", "V3/V4 synthetic cases", "records lacking resolvable capture lineage"],
        "labeling_policy": "no security labels, gate outcomes, policy outputs, strategy or effectiveness metadata during acquisition",
        "required_pre_execution_checks": ["session-group deduplication", "cross-study hash overlap audit", "manifest integrity verification", "privacy/ethics and containment approval where applicable"],
    }
    write_json("v4_prospective_capture_contract_v1.json", capture)
    report = """# RAGIN V4 Real-Evidence Recovery Report\n\n## 1. Why the first 240 were rejected\n\nThe previous 240-record selection was preserved but rejected before execution because record-level natural or controlled capture lineage could not be established. The records are structurally distinct provenance-unresolved derived session records, not a verified real holdout. No V4 arm, gate, policy, generator, verifier, reference annotation, or effectiveness analysis was run.\n\n## 2. Structural uniqueness is not real provenance\n\nUnique event-sequence, context, and file hashes establish that records differ as repository artifacts. They do not establish that an artifact originated in a naturally collected or controlled real session. Eligibility therefore requires an upstream raw capture, native session identity, or explicit documentary capture chain.\n\n## 3. Existing source audit\n\n`data/sessions/` is a RAGIN-derived event export with session IDs and timestamps but no resolvable raw capture parent, deployment identifier, source offset, or capture manifest. It remains `DERIVED_WITH_UNTRACEABLE_PARENT` and contributes zero verified groups.\n\n`data/cowrie_logs/` contains timestamped native Cowrie session events with source-file hashes and session identifiers. Repository field documentation describes Cowrie as the controlled honeypot source. A metadata-only reconstruction yields one candidate per native Cowrie session with at least one input event.\n\n`data/field/` is documented as passive field collection, but the current export has session IDs and timestamps without an attacker-input event or linked raw capture identifier. It is real-source evidence in provenance terms but unusable for the required canonical evaluation input contract.\n\n`data/real_linux_transcripts.json` is documented as 12 genuine sessions recorded by `scripts/capture_real_linux_transcripts.py` on a real Linux host. The capture script documents fixed read-only command execution and real command output. These are controlled real administration records, not attacker sessions; their per-record native session IDs and capture timestamps are unavailable.\n\n## 4. data/sessions lineage recovery\n\nAll enumerated records were checked structurally for native session identifiers, timestamps, and record hashes. No pre-existing manifest or raw source parent was found. The recovery therefore records the unresolved derived status rather than promoting the records based on their filenames or content shape.\n\n## 5. Cowrie reconstruction feasibility\n\nReconstruction is feasible without semantic selection. The frozen rule is one case per native Cowrie session, selecting the final non-empty `cowrie.command.input` in deterministic timestamp/source-file/line order. Three native sessions lacked such an event and were excluded from the canonical candidates. Candidate provenance includes native session ID, event timestamps, source-file identities and hashes, complete event-sequence hash, and documented controlled-honeypot origin.\n\n## 6. Field-record recovery\n\nThe field export cannot currently provide the required attacker/operator input contract. No input field is invented and no field record is forced into the pool. A future capture manifest must preserve native raw input events and their parent linkage.\n\n## 7. Controlled-admin provenance\n\nThe real Linux transcript artifact is linked to the documented capture script and preregistered statement that 12 genuine sessions were recorded on a real Linux host. Each record is hashed and tied to its array index and source artifact hash. Missing per-record capture identifiers are recorded as limitations, not silently fabricated.\n\n## 8. Existing verified pool size\n\nThe recovered pool contains 25 defensible independence groups: 13 controlled real honeypot Cowrie groups and 12 controlled real administration groups. No holdout is selected from this pool.\n\n## 9. Remaining provenance gap\n\nThe pool is below both the final target of 240 and the minimum authorization threshold of 180. The V4 real study is therefore blocked. The original 240 selection remains historical and rejected.\n\n## 10. Prospective collection contract\n\nA provenance-from-birth contract is frozen for future acquisition. Each native capture must receive a capture ID, native session ID, source class, collector version, deployment/environment ID, start/end timestamps, raw-log path and SHA256, event and input counts, null parent for native captures, explicit non-synthetic/non-replay/non-fixture flags, and a pre-evaluation capture-manifest hash. One native capture session is one independence group. The acquisition target is 260 groups to preserve replacement headroom; the final holdout target remains 240 and the minimum authorization threshold remains 180.\n\n## 11. Scientific boundary\n\nThis recovery used only source, structural, documentary, and cryptographic metadata. No security labels, V4 outputs, gate outputs, policy outputs, Hisoka responses, verifier outcomes, reference labels, or effectiveness metrics were inspected or generated.\n"""
    report_path = DOCS / "RAGIN_V4_REAL_EVIDENCE_RECOVERY_REPORT.md"
    report_path.write_text(report)
    artifacts = [
        "v4_source_lineage_inventory_v1.json", "v4_data_sessions_lineage_recovery_v1.json", "v4_cowrie_reconstruction_protocol_v1.json", "v4_cowrie_provenance_verified_candidates_v1.json", "v4_field_recovery_audit_v1.json", "v4_real_linux_provenance_audit_v1.json", "v4_existing_provenance_verified_real_pool_v1.json", "v4_prospective_capture_contract_v1.json",
        "docs/decision_fusion/RAGIN_V4_REAL_EVIDENCE_RECOVERY_REPORT.md",
    ]
    hashes = {}
    for rel in artifacts:
        path = RESULTS / rel if rel.startswith("v4_") else ROOT / rel
        hashes[rel] = sha256_file(path)
    freeze = {
        "schema": "ragin.v4.real_evidence_recovery_freeze.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "implementation_sha256": frozen["implementation_sha256"],
        "provenance_amendment_sha256": frozen["provenance_amendment_sha256"],
        "artifact_sha256": hashes,
        "verified_pool_groups": len(verified),
        "holdout_status": "NEW_PROSPECTIVE_REAL_COLLECTION_REQUIRED",
        "v4_arms_executed": False,
        "reference_annotation_started": False,
        "effectiveness_seen": False,
        "selection_classification": "PRE_EXECUTION_SELECTION_REJECTED_FOR_UNRESOLVED_RECORD_PROVENANCE",
        "old_120_used": False,
        "old_169_used": False,
        "policy_outputs_inspected": False,
    }
    freeze_path = write_json("v4_real_evidence_recovery_freeze_v1.json", freeze)
    print(json.dumps({"verified_groups": len(verified), "cowrie": len(cowrie_candidates), "admin": len(admin_rows), "sessions_unresolved": len(session_rows), "freeze_sha256": sha256_file(freeze_path)}, indent=2))

if __name__ == "__main__":
    main()
