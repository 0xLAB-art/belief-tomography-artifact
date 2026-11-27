#!/usr/bin/env python3
from __future__ import annotations

import collections
import dataclasses
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
OUT = ROOT / "results" / "decision_fusion_v4" / "don_v2_substantive_final_v1"
SESSIONS = ROOT / "data" / "external" / "hf_shell_attack_2024" / "d201aafbbcbb5347078ca64f06c5428fa6814bc9" / "sessions" / "2024.jsonl"
EXPERIMENT_ID = "HF2024_DON_V2_SUBSTANTIVE_FINAL_V1"
ARMS = ("RAGIN_BASELINE", "RAGIN_V4_SUBSTANTIVE_DETERMINISTIC", "RAGIN_V4_SUBSTANTIVE_LOGISTIC")
DECISION_ARMS = {ARMS[0]: ARMS[0], ARMS[1]: "RAGIN_V4_DETERMINISTIC", ARMS[2]: "RAGIN_V4_LOGISTIC"}
PREVIOUS = (
    ROOT / "results/decision_fusion_v4/v4_hf2024_retrospective_holdout_freeze_v1a.json",
    ROOT / "results/decision_fusion_v4/hf2024_postfix_family_disjoint_v1/holdout_freeze.json",
    ROOT / "results/decision_fusion_v4/hf2024_substantive_final_v1/holdout_freeze.json",
)

def sha_bytes(value: bytes) -> str: return hashlib.sha256(value).hexdigest()
def sha_file(path: Path) -> str: return sha_bytes(path.read_bytes())
def sha_json(value: Any) -> str: return sha_bytes(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode())
def write_json(name: str, value: Any) -> Path:
    path = OUT / name; path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n"); return path
def git(*args: str) -> str: return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True).stdout
def norm(value: Any) -> str: return re.sub(r"\s+", " ", str(value).strip().lower())
def family(commands: list[str]) -> tuple[str, ...]: return tuple(norm(c) for c in commands if norm(c))

def load_rows() -> list[dict[str, Any]]:
    return [json.loads(line) for line in SESSIONS.read_text().splitlines() if line.strip()]

def freeze_holdout(rows: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    by_id = {r["session_id"]: r for r in rows}; old_groups: set[str] = set(); old_families: set[tuple[str, ...]] = set()
    for path in PREVIOUS:
        data = json.loads(path.read_text())
        for c in data["cases"]:
            old_groups.add(c["source_group_id"])
            if c["source_group_id"] in by_id: old_families.add(family([str(x) for x in by_id[c["source_group_id"]].get("commands", [])]))
    candidates: dict[tuple[str, ...], list[dict[str, Any]]] = collections.defaultdict(list)
    for row in rows:
        commands = [str(x) for x in row.get("commands", []) if str(x).strip()]; fam = family(commands)
        if commands and row["session_id"] not in old_groups and fam not in old_families: candidates[fam].append({"row": row, "commands": commands})
    ranked = sorted(candidates, key=lambda f: sha_json([EXPERIMENT_ID, "family", list(f)]))
    if len(ranked) < 240: raise RuntimeError(f"fewer than 240 eligible families remain: {len(ranked)}")
    cases = []
    for rank, fam in enumerate(ranked[:240], 1):
        chosen = min(candidates[fam], key=lambda x: sha_json([EXPERIMENT_ID, "record", x["row"]["session_id"]])); row = chosen["row"]; cmds = chosen["commands"]
        cases.append({"case_id": f"donv2-final-{rank:03d}-{sha_json([EXPERIMENT_ID,row['session_id'],list(fam)])[:12]}", "source_group_id": row["session_id"], "commands": cmds, "final_input": cmds[-1], "preceding_context": cmds[:-1], "source_family_sha256": sha_json(list(fam)), "sequence_sha256": sha_json(cmds), "final_input_sha256": sha_bytes(cmds[-1].encode()), "preceding_context_sha256": sha_json(cmds[:-1]), "selection_rank": rank, "selection_family_key_sha256": sha_json([EXPERIMENT_ID,"family",list(fam)]), "selection_record_key_sha256": sha_json([EXPERIMENT_ID,"record",row["session_id"]])})
    holdout = {"schema":"ragin.v4.hf2024.don_v2_substantive_final.family_disjoint_holdout.v1","experiment_id":EXPERIMENT_ID,"status":"FROZEN_BEFORE_EXECUTION","observation_unit":"one selected HF-2024 source-group record and its observed ordered command sequence; source groups are not asserted to be native SSH sessions","source_dataset":str(SESSIONS.relative_to(ROOT)),"source_dataset_revision":"d201aafbbcbb5347078ca64f06c5428fa6814bc9","source_dataset_sha256":sha_file(SESSIONS),"previous_holdout_paths":[str(p.relative_to(ROOT)) for p in PREVIOUS],"previous_source_groups_excluded":len(old_groups),"previous_unique_families_excluded":len(old_families),"remaining_eligible_unique_families_before_selection":len(ranked),"N":len(cases),"cases":cases,"normalization":"lowercase, trim, collapse whitespace within each command, preserve observed command ordering","selection_rule":"sort normalized family keys by SHA256(JSON([EXPERIMENT_ID,'family',family])) and retain first 240; choose one record per family by minimum SHA256(JSON([EXPERIMENT_ID,'record',source_group_id]))","semantic_balancing":False,"label_based_filtering":False,"policy_based_sampling":False,"synthetic_or_replay_records_selected":False,"unique_case_ids":len({c['case_id'] for c in cases}),"unique_source_groups":len({c['source_group_id'] for c in cases}),"unique_command_families":len({c['source_family_sha256'] for c in cases}),"prior_family_overlap":0}
    protocol = {"schema":"ragin.v4.hf2024.don_v2_substantive_final.protocol_freeze.v1","experiment_id":EXPERIMENT_ID,"status":"FROZEN_BEFORE_EXECUTION","holdout_path":"results/decision_fusion_v4/don_v2_substantive_final_v1/holdout_freeze.json","arms":list(ARMS),"expected_cases":240,"expected_records":720,"pipeline":"server_v2 -> Harness -> Chrollo -> Don V2 -> Evidence Gate -> V4 Policy -> substantive Hisoka generator -> mandatory verifier/HITL -> accepted-only fictional-state commit","matched_inputs":"same frozen source command sequence and final input across arms; preceding commands are emitted as inert retrospective context","don_version":"DON_COMMAND_AWARE_V2","environment":{"RAGIN_DON_RETRIEVAL_VERSION":"DON_COMMAND_AWARE_V2","RAGIN_RAG_MODE":"offline","RAGIN_PROVIDER_ENABLED":"0","RAGIN_LAYA_ENABLED":"0","external_generation_calls":False,"aws_or_network_changes":False,"attacker_commands_executed":False},"comparison":"raw response hash, semantic response hash after removing only prompt/decorative marker lines, action signature, and fictional state hashes","selection_exclusions":"all three prior HF-2024 holdouts and their source groups/families","analysis_plan":["valid/invalid evidence and reason codes","reference and score diversity","strategy delivery/consumption/fallback","non-decorative response and state differences","verifier/HITL/commit safety","latency/errors/missing traces"],"missing_data":"NOT_VERIFIABLE; never imputed"}
    return holdout, protocol

def implementation_freeze() -> dict[str, Any]:
    paths = ["ragin/don/command_aware_v2.py","ragin/don/rag_engine.py","ragin/don/models.py","ragin/decision_fusion_v4/evidence_export.py","ragin/decision_fusion_v4/policy.py","ragin/cycle/adapters.py","ragin/cycle/harness.py","ragin/server_v2.py","ragin/hisoka/strategy_generator_v1.py","ragin/cycle/verifier.py","results/decision_fusion_v4/v4_selected_logistic_policy.joblib","data/corpus/command_aware_v2.jsonl","results/decision_fusion_v4/don_v2_command_aware/don_v2_freeze_v1.json","results/decision_fusion_v4/substantive_runtime_integration_v1/integration_validation_freeze_v1.json"]
    packages = {n: importlib.metadata.version(n) if importlib.util.find_spec(n) else "NOT_INSTALLED" for n in ("pytest","pydantic","joblib","scikit-learn")}
    return {"schema":"ragin.v4.don_v2_substantive_final.implementation_environment_freeze.v1","experiment_id":EXPERIMENT_ID,"git_head":git("rev-parse","HEAD").strip(),"worktree_status_sha256":sha_bytes(git("status","--porcelain=v1","--untracked-files=all").encode()),"complete_relevant_worktree_diff_sha256":sha_bytes(git("diff","--binary").encode()),"source_sha256":{p:sha_file(ROOT/p) for p in paths},"dependencies":packages,"runtime_settings":{"RAGIN_DON_RETRIEVAL_VERSION":"DON_COMMAND_AWARE_V2","RAGIN_RAG_MODE":"offline","RAGIN_PROVIDER_ENABLED":"0","RAGIN_LAYA_ENABLED":"0","external_generation_calls":False,"attacker_commands_executed":False,"policy_algorithms_modified":False},"historical_artifacts_preserved":True}

def build_runtime(arm: str):
    from ragin.cycle.adapters import ChrolloAdapter, DonAdapter, HisokaAdapter, SubstantiveStrategyAdapter
    from ragin.cycle.harness import Harness
    from ragin.don.rag_engine import ThreatRAGEngine
    from ragin.hisoka.deceiver import AdaptiveDeceiver
    classifier = ChrolloAdapter(decision_arm=DECISION_ARMS[arm]); engine = ThreatRAGEngine(gateway_url="http://127.0.0.1:1/v1", api_key=""); analyzer = DonAdapter(engine=engine)
    deceiver = HisokaAdapter(deceiver=AdaptiveDeceiver(gateway_url=None, api_key=None)) if arm == ARMS[0] else SubstantiveStrategyAdapter(arm)
    return Harness(classifier=classifier, cti_engine=analyzer, deceiver=deceiver, mandatory_verification=True, max_retries=0, decision_arm=DECISION_ARMS[arm])

def _semantic(text: str) -> str:
    lines = str(text).splitlines()[1:]; lines = [x for x in lines if not re.fullmatch(r"\s*(?:\[strategy:[^\]]+\]|strategy[:=][^\s]+)\s*", x, re.I)]
    return re.sub(r"\s+", " ", " ".join(lines).strip())

def run_case(case: dict[str, Any], arm: str, harnesses: dict[str, Any]) -> dict[str, Any]:
    from ragin.cycle.session import EventType, Session
    session_id = f"{case['case_id']}-{arm.lower()}"
    with tempfile.TemporaryDirectory(prefix="ragin-donv2-final-") as directory:
        session = Session(session_id, session_dir=directory); session.emit(EventType.SESSION_START,{"session_id":session_id,"source_ip":"retrospective-inert"},source="harness")
        for cmd in case["preceding_context"]: session.emit(EventType.ATTACKER_INPUT,{"command":cmd,"retrospective_context":True},source="retrospective-input")
        started = time.perf_counter(); result = harnesses[arm].process(session, case["final_input"]); elapsed = (time.perf_counter()-started)*1000; events = [e.to_dict() for e in session.replay()]
    decision = next((e["data"] for e in events if e["event_type"]=="strategy_update"), {}); response = result.deception_response or {}; meta = response.get("metadata") or {}; cti = result.cti_analysis or {}; bundle = cti.get("evidence_bundle") or {}; retrieval = bundle.get("retrieval") or {}; trace = retrieval.get("trace_summary") or {}; gate = bundle.get("evidence_gate_preview") or {}
    text_value = str(response.get("response_text", "")); top_k = trace.get("top_k", []); docs = retrieval.get("documents", [])
    return {"schema":"ragin.v4.don_v2_substantive_final.raw_arm_case.v1","case_id":case["case_id"],"source_group_id":case["source_group_id"],"source_family_sha256":case["source_family_sha256"],"arm":arm,"session_id":session_id,"input_sha256":case["final_input_sha256"],"observed_command_sequence_sha256":case["sequence_sha256"],"preceding_context_sha256":case["preceding_context_sha256"],"don_query":retrieval.get("query","NOT_VERIFIABLE"),"don_context_projection":trace.get("context_projection","NOT_VERIFIABLE"),"don_command_features":(trace.get("context_projection") or {}).get("features","NOT_VERIFIABLE"),"don_top_k":top_k,"evidence_documents":docs,"evidence_ids":decision.get("valid_doc_ids", retrieval.get("relevant_doc_ids",[])),"evidence_relevance":[{"evidence_id":d.get("doc_id"),"relevance":d.get("relevance_grade",d.get("relevance")),"provenance_hash":d.get("provenance_hash")} for d in docs],"evidence_coverage":retrieval.get("query_coverage","NOT_VERIFIABLE"),"evidence_gate_reason_code":gate.get("reason_code", "NOT_VERIFIABLE"),"gate_state":decision.get("gate_state",gate.get("gate_state","NOT_APPLICABLE_BASELINE")),"policy_decision":decision or "NOT_APPLICABLE_BASELINE","selected_strategy":decision.get("selected_response_strategy","baseline"),"strategy_source":meta.get("strategy_source","baseline_existing_behavior" if arm==ARMS[0] else "NOT_VERIFIABLE"),"strategy_delivered_to_generator":meta.get("strategy_delivered_to_generator",meta.get("strategy_delivered_by_generator","NOT_VERIFIABLE")),"strategy_consumed_by_template":meta.get("strategy_consumed_by_template","NOT_VERIFIABLE"),"generator_version":meta.get("generator_version","NOT_VERIFIABLE"),"action_selected":meta.get("action_selected","NOT_VERIFIABLE"),"response_text":text_value,"response_sha256":sha_bytes(text_value.encode()),"semantic_response_sha256":sha_bytes(_semantic(text_value).encode()),"fictional_state_before_hash":meta.get("fictional_state_before_hash","NOT_VERIFIABLE"),"fictional_state_proposed_hash":meta.get("fictional_state_proposed_hash","NOT_VERIFIABLE"),"fictional_state_after_hash":meta.get("fictional_state_after_hash","NOT_VERIFIABLE"),"verification":result.verification,"hitl":result.approval,"commit_event":meta.get("fictional_commit_event","NOT_VERIFIABLE"),"failure_reason":result.error or meta.get("strategy_runtime_fallback"),"latency_ms":round(elapsed,3),"external_generation_calls":False,"attacker_command_executed":False,"event_trace_sha256":sha_json(events)}

def pairs(records: list[dict[str,Any]], left: str, right: str):
    grouped = collections.defaultdict(dict)
    for r in records: grouped[r["case_id"]][r["arm"]]=r
    return [(v[left],v[right]) for v in grouped.values() if left in v and right in v]
def cmp(records,left,right,key):
    ps=pairs(records,left,right); return {"N":len(ps),"changed":sum(a[key]!=b[key] for a,b in ps),"equal":sum(a[key]==b[key] for a,b in ps)}
def dist(records,arm,key): return dict(sorted(collections.Counter(str(r[key]) for r in records if r["arm"]==arm).items()))

def analyze(records, holdout):
    v4=[r for r in records if r["arm"]!=ARMS[0]]
    refs={evidence_id for r in records for evidence_id in r.get("evidence_ids",[]) if evidence_id}
    sets={sha_json(sorted(r.get("evidence_ids",[]))) for r in records}
    score_sets={sha_json([(x.get("evidence_id"),x.get("score")) for x in r.get("don_top_k",[])]) for r in records}
    return {"schema":"ragin.v4.don_v2_substantive_final.locked_analysis.v1","experiment_id":EXPERIMENT_ID,"records":len(records),"arm_counts":dict(collections.Counter(r["arm"] for r in records)),"gate_states":{a:dist(records,a,"gate_state") for a in ARMS},"valid_evidence_total":sum(r["gate_state"]=="VALID_EVIDENCE" for r in records),"evidence_reference_diversity":{"unique_evidence_ids":len(refs),"unique_retrieval_sets":len(sets),"unique_score_sets":len(score_sets)},"strategy_distributions":{a:dist(records,a,"selected_strategy") for a in ARMS},"strategy_delivery":{"v4_records":len(v4),"delivered_true":sum(r["strategy_delivered_to_generator"] is True for r in v4),"consumed_true":sum(r["strategy_consumed_by_template"] is True for r in v4),"delivery_not_verifiable":sum(r["strategy_delivered_to_generator"]=="NOT_VERIFIABLE" for r in v4),"consumption_not_verifiable":sum(r["strategy_consumed_by_template"]=="NOT_VERIFIABLE" for r in v4)},"fallback_reasons":dict(collections.Counter(str(r["failure_reason"]) for r in records if r["failure_reason"])),"response_comparison":{"raw":{"baseline_vs_deterministic":cmp(records,ARMS[0],ARMS[1],"response_sha256"),"baseline_vs_logistic":cmp(records,ARMS[0],ARMS[2],"response_sha256"),"deterministic_vs_logistic":cmp(records,ARMS[1],ARMS[2],"response_sha256")},"non_decorative":{"baseline_vs_deterministic":cmp(records,ARMS[0],ARMS[1],"semantic_response_sha256"),"baseline_vs_logistic":cmp(records,ARMS[0],ARMS[2],"semantic_response_sha256"),"deterministic_vs_logistic":cmp(records,ARMS[1],ARMS[2],"semantic_response_sha256")}},"state_transition_comparison":{"baseline_vs_deterministic":cmp(records,ARMS[0],ARMS[1],"fictional_state_after_hash"),"baseline_vs_logistic":cmp(records,ARMS[0],ARMS[2],"fictional_state_after_hash"),"deterministic_vs_logistic":cmp(records,ARMS[1],ARMS[2],"fictional_state_after_hash")},"commit_counts":{"accepted":sum(r["commit_event"]=="accepted" for r in records),"rejected":sum(r["commit_event"] not in ("accepted","NOT_VERIFIABLE") for r in records),"not_verifiable":sum(r["commit_event"]=="NOT_VERIFIABLE" for r in records)},"verifier":{"passed":sum(bool(r["verification"].get("passed")) for r in records),"failed":sum(not bool(r["verification"].get("passed")) for r in records),"safety_violations":sum(bool(r["verification"].get("issues")) and not bool(r["verification"].get("passed")) for r in records)},"hitl":{"approved":sum(bool(r["hitl"].get("approved")) for r in records),"human_reviews":sum(str(r["hitl"].get("decided_by","")).startswith("operator:") for r in records)},"latency_ms":{a:{"N":sum(r["arm"]==a for r in records),"mean":round(sum(r["latency_ms"] for r in records if r["arm"]==a)/max(1,sum(r["arm"]==a for r in records)),3)} for a in ARMS},"missing_or_incomplete_traces":{k:sum(r.get(k) in (None,"","NOT_VERIFIABLE") for r in records) for k in ("don_query","don_context_projection","don_top_k","evidence_gate_reason_code","strategy_source","generator_version","fictional_state_after_hash","commit_event")},"holdout_integrity":{k:holdout[k] for k in ("N","unique_case_ids","unique_source_groups","unique_command_families","prior_family_overlap")},"claims_boundary":["reference-free runtime observations only","no policy correctness or superiority claim","no attacker engagement claim","same-source retrospective corpus"]}

def main():
    os.environ.update({"RAGIN_DON_RETRIEVAL_VERSION":"DON_COMMAND_AWARE_V2","RAGIN_RAG_MODE":"offline","RAGIN_PROVIDER_ENABLED":"0","RAGIN_LAYA_ENABLED":"0","RAGIN_LAYA_EVAL_REQUIRE_REAL_MODEL":"0","RAGIN_HOST_FICTION":"0"})
    OUT.mkdir(parents=True,exist_ok=True)
    if (OUT/"raw_execution_records.jsonl").exists(): raise RuntimeError("refusing to rerun existing raw output")
    holdout,protocol=freeze_holdout(load_rows())
    if (holdout["N"],holdout["unique_case_ids"],holdout["unique_source_groups"],holdout["unique_command_families"],holdout["prior_family_overlap"])!=(240,240,240,240,0): raise RuntimeError("holdout integrity failed")
    write_json("implementation_environment_freeze.json",implementation_freeze()); write_json("holdout_freeze.json",holdout); write_json("protocol_freeze.json",protocol)
    harnesses={a:build_runtime(a) for a in ARMS}; records=[]; raw=OUT/"raw_execution_records.jsonl"; started=time.time()
    try:
        with raw.open("w") as handle:
            for i,case in enumerate(holdout["cases"],1):
                for arm in ARMS:
                    row=run_case(case,arm,harnesses); handle.write(json.dumps(row,sort_keys=True)+"\n"); handle.flush(); records.append(row)
                if i%10==0: print(f"completed_cases={i}/240 records={len(records)}",flush=True)
    except Exception as exc:
        write_json("aborted_attempt_freeze.json",{"status":"ABORTED","records_written":len(records),"error":type(exc).__name__,"error_message":str(exc),"started_unix":started,"aborted_unix":time.time()}); raise
    if len(records)!=720 or len({(r["case_id"],r["arm"]) for r in records})!=720: raise RuntimeError("raw completeness failed")
    raw_freeze={"schema":"ragin.v4.don_v2_substantive_final.raw_execution_freeze.v1","status":"RAW_EXECUTION_COMPLETE","raw_path":str(raw.relative_to(ROOT)),"raw_sha256":sha_file(raw),"holdout_sha256":sha_file(OUT/"holdout_freeze.json"),"records":len(records),"arm_counts":dict(collections.Counter(r["arm"] for r in records)),"attacker_commands_executed":False,"external_generation_calls":False,"started_unix":started,"completed_unix":time.time()}
    write_json("raw_execution_freeze.json",raw_freeze); write_json("locked_behavioral_analysis.json",analyze(records,holdout))
    files=sorted(p for p in OUT.iterdir() if p.name!="sha256_manifest.json"); write_json("sha256_manifest.json",{"schema":"ragin.v4.don_v2_substantive_final.sha256_manifest.v1","experiment_id":EXPERIMENT_ID,"files":{str(p.relative_to(ROOT)):sha_file(p) for p in files}})
    print(json.dumps({"raw_freeze":raw_freeze,"analysis":json.loads((OUT/"locked_behavioral_analysis.json").read_text())},indent=2,sort_keys=True))
if __name__=="__main__": main()
