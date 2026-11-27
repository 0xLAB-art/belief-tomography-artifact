from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results/laya_research"
WORKSPACE_ROOT = Path("/home/elaref/Documents/research/ragin_expert_panel_v1")
EXPECTED_ORIGINAL_SHA = "2515f1117f1d71fde890792ff645c9ed02d9bede712806d076e2b1ca13a2928b"
TAXONOMY = ["BENIGN", "RECON", "SUSPICIOUS", "EXPLOITATION", "PRIVILEGE_ESCALATION", "DATA_ACCESS", "PERSISTENCE", "OTHER_ATTACK", "UNCERTAIN"]
ASSIGNMENTS = {
    "expert_ai_01": {"model": "GPT-6-Luna", "packet": "r1.json", "packet_sha256": "8059af3cebe8ecde86cfcd2da3c65fa123ee988a202e445a8c5134eebf8ff4bc"},
    "expert_ai_02": {"model": "GPT-6.1-Sol", "packet": "r2.json", "packet_sha256": "f21dbd52a9efe3771acfcb7e3218f8a88e1634814fd30f83b7a7a670558960cc"},
    "expert_ai_03": {"model": "GPT-5.6-Terra", "packet": "r3.json", "packet_sha256": "1e178e1a58cc30e2367f057393ba27387bc11d54beeccf8feafd8707330bde7d"},
}
ALLOWED_FILES = {"packet.json", "INSTRUCTIONS.txt", "ANNOTATOR_PROMPT.txt", "RUN_METADATA_TEMPLATE.json"}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def prompt(session: str, model: str, path: Path) -> str:
    return (f"The human operator has selected the preregistered model for this session.\n"
"Treat the model identity in RUN_METADATA_TEMPLATE.json as operator-attested provenance. Do not attempt to infer or override it.\n\n"
f"You are one member of a preregistered independent expert-AI annotation panel.\n"
f"Session: {session}\n"
f"Persistent workspace: {path}\n"
f"Assigned model: {model}\n"
"Reasoning effort: MEDIUM\n\n"
"Your first filesystem action must be exactly:\n\n"
"pwd\n\n"
"If the result differs from the persistent workspace path above, STOP with\n"
"WORKSPACE_MISMATCH. Do not search for the workspace.\n\n"
"After the workspace check, use only this workspace. Read packet.json and apply\n"
"the frozen V3 semantic instructions. Keep the session independent, use only\n"
"this session's packet order, and do not communicate with other annotators.\n\n"
"Do not access the RAGIN repository, another expert-AI workspace, previous AI\n"
"annotations, human bundles, Chrollo predictions, Laya predictions, ground\n"
"truth, the web, or any external network. Do not use filesystem-wide searches\n"
"such as find /, rg /home, repository grep, locate, or parent-directory fd.\n\n"
"Use only these labels:\n\n"
"BENIGN\nRECON\nSUSPICIOUS\nEXPLOITATION\nPRIVILEGE_ESCALATION\nDATA_ACCESS\nPERSISTENCE\nOTHER_ATTACK\nUNCERTAIN\n\n"
"Do not modify the taxonomy or aggregation rules. This is an AI annotation\n"
"session in MULTI_MODEL_INDEPENDENT_AI_SESSIONS, not a human panel and not\n"
"human ground truth. Record labels only after the operator-attested metadata\n"
"and workspace checks are complete.\n")


def instructions(session: str) -> str:
    return (f"This is the persistent isolated workspace for {session}.\n\n"
"The workspace contains exactly one frozen packet, one assignment prompt, and\n"
"one run-metadata template. Use only files in this workspace during annotation.\n"
"Do not access the RAGIN repository, another expert-AI workspace, prior labels,\n"
"predictions, human bundles, ground truth, the web, or any external network.\n\n"
"The human operator attests the selected model in RUN_METADATA_TEMPLATE.json.\n"
"Model identity provenance is OPERATOR_UI_ATTESTED. Do not infer or override\n"
"the operator-attested model identity.\n")


def main() -> None:
    original = RESULTS / "expert_ai_panel_preregistration_freeze_v1.json"
    if digest(original) != EXPECTED_ORIGINAL_SHA:
        raise SystemExit("BLOCKED_ORIGINAL_FREEZE_MISMATCH")
    original_freeze = json.loads(original.read_text())
    if original_freeze.get("annotation_started") is not False or original_freeze.get("annotation_completed") is not False:
        raise SystemExit("BLOCKED_ORIGINAL_FREEZE_NOT_PRE_ANNOTATION")

    WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat()
    workspace_records = []
    for session, assignment in ASSIGNMENTS.items():
        workspace = WORKSPACE_ROOT / session
        workspace.mkdir(parents=True, exist_ok=True)
        entries = {p.name for p in workspace.iterdir()}
        if entries - ALLOWED_FILES:
            raise SystemExit(f"BLOCKED_UNEXPECTED_WORKSPACE_FILES:{session}:{sorted(entries - ALLOWED_FILES)}")
        source_packet = RESULTS / "rater_packets_v3" / assignment["packet"]
        packet_data = json.loads(source_packet.read_text())
        if len(packet_data) != 120 or any(row.get("label") not in ("", None) for row in packet_data):
            raise SystemExit(f"BLOCKED_PACKET_NOT_BLANK:{session}")
        if digest(source_packet) != assignment["packet_sha256"]:
            raise SystemExit(f"BLOCKED_PACKET_SOURCE_HASH:{session}")
        destination_packet = workspace / "packet.json"
        if destination_packet.exists() and destination_packet.read_bytes() != source_packet.read_bytes():
            raise SystemExit(f"BLOCKED_PACKET_DESTINATION_MISMATCH:{session}")
        if not destination_packet.exists():
            shutil.copyfile(source_packet, destination_packet)
        if digest(destination_packet) != digest(source_packet):
            raise SystemExit(f"BLOCKED_PACKET_COPY_HASH:{session}")
        workspace_path = str(workspace)
        (workspace / "INSTRUCTIONS.txt").write_text(instructions(session))
        (workspace / "ANNOTATOR_PROMPT.txt").write_text(prompt(session, assignment["model"], workspace))
        metadata = {
            "session_id": session,
            "panel_type": "MULTI_MODEL_INDEPENDENT_AI_SESSIONS",
            "assigned_model": assignment["model"],
            "reasoning_effort": "MEDIUM",
            "operator_attested_model": assignment["model"],
            "model_identity_provenance": "OPERATOR_UI_ATTESTED",
            "model_assignment_verified": True,
            "model_assignment_violation": False,
            "packet_sha256": digest(destination_packet),
            "prompt_sha256": None,
            "output_sha256": None,
            "repository_access_used": False,
            "network_access_used": False,
            "external_files_accessed": False,
            "blindness_violation": False,
            "annotation_started": False,
            "annotation_completed": False,
            "run_validity": "READY",
        }
        write_json(workspace / "RUN_METADATA_TEMPLATE.json", metadata)
        workspace_records.append({
            "session_id": session,
            "path": workspace_path,
            "exists": workspace.is_dir(),
            "is_git_repository": (workspace / ".git").exists(),
            "contains_symlinks": any(p.is_symlink() for p in workspace.iterdir()),
            "exact_file_count": len(list(workspace.iterdir())),
            "files": {
                "packet.json": {"sha256": digest(destination_packet), "case_count": 120, "labels_empty": True, "byte_identical_to_source": destination_packet.read_bytes() == source_packet.read_bytes()},
                "INSTRUCTIONS.txt": {"sha256": digest(workspace / "INSTRUCTIONS.txt")},
                "ANNOTATOR_PROMPT.txt": {"sha256": digest(workspace / "ANNOTATOR_PROMPT.txt"), "operator_attested_model": assignment["model"], "self_introspection_model_gate": "self-verify" not in (workspace / "ANNOTATOR_PROMPT.txt").read_text().lower()},
                "RUN_METADATA_TEMPLATE.json": {"sha256": digest(workspace / "RUN_METADATA_TEMPLATE.json"), "assigned_model": assignment["model"], "operator_attested_model": assignment["model"], "reasoning_effort": "MEDIUM", "model_identity_provenance": "OPERATOR_UI_ATTESTED", "model_assignment_verified": True, "model_assignment_violation": False, "annotation_started": False, "annotation_completed": False, "run_validity": "READY"},
            },
            "repository_source_exposed": False,
            "previous_labels_exposed": False,
            "predictions_exposed": False,
        })

    workspace_audit = {
        "audit_version": "expert_ai_workspace_integrity_v1a",
        "audit_timestamp": timestamp,
        "workspace_root": str(WORKSPACE_ROOT),
        "root_outside_ragin_repository": WORKSPACE_ROOT.resolve() != ROOT.resolve() and ROOT.resolve() not in WORKSPACE_ROOT.resolve().parents,
        "workspaces": workspace_records,
        "global_assertions": {"all_packets_have_120_cases": True, "all_labels_empty": True, "all_prompts_operator_attested": True, "self_introspection_model_gate_absent": True, "no_prior_labels_or_predictions_copied": True, "annotation_performed": False},
    }
    audit_path = RESULTS / "expert_ai_workspace_integrity_v1a.json"
    write_json(audit_path, workspace_audit)

    amendment = {
        "amendment_id": "EXPERT_AI_REFERENCE_PANEL_V1_AMENDMENT_01",
        "amendment_number": 1,
        "amendment_timestamp": timestamp,
        "amendment_status": "PRE_ANNOTATION",
        "annotation_cases_completed_before_amendment": 0,
        "annotation_outputs_created_before_amendment": False,
        "annotation_cases_completed_after_amendment": 0,
        "amendment_based_on_annotation_outcomes": False,
        "predictions_accessed": False,
        "ground_truth_accessed": False,
        "previous_annotations_accessed": False,
        "reason": "Pre-annotation infrastructure and model-identity verification correction.",
        "original_freeze": {"path": "results/laya_research/expert_ai_panel_preregistration_freeze_v1.json", "sha256": digest(original), "preserved_unchanged": True},
        "old_assignments": {"expert_ai_01": "GPT-6-Luna / MEDIUM", "expert_ai_02": "GPT-5.6-Sol / MEDIUM", "expert_ai_03": "GPT-5.6-Terra / MEDIUM"},
        "new_assignments": {session: f"{a['model']} / MEDIUM" for session, a in ASSIGNMENTS.items()},
        "panel_type": "MULTI_MODEL_INDEPENDENT_AI_SESSIONS",
        "old_model_verification_rule": "Each AI agent had to independently observe and verify its own model identity from the Codex UI; failure to observe a matching model could invalidate the run.",
        "new_model_verification_rule": {"model_identity_provenance": "OPERATOR_UI_ATTESTED", "operator_responsibility": "The human operator selects the assigned model in the Codex UI before launching each annotation session and records the selected model.", "required_metadata": ["assigned_model", "operator_attested_model", "reasoning_effort", "model_identity_provenance"], "agent_self_introspection_required": False, "agent_must_not_hallucinate_model_identity": True, "assignment_violation_only_if": ["The operator states the wrong model was selected.", "Available session metadata explicitly contradicts the assignment."], "cannot_self_observe_model_name_is_not_a_violation": True},
        "old_workspace_strategy": {"paths": ["/tmp/ragin_expert_ai_01/", "/tmp/ragin_expert_ai_02/", "/tmp/ragin_expert_ai_03/"], "failure": "The Codex execution process could not reliably enter some /tmp workspaces and produced Failed to create unified exec process: No such file or directory."},
        "new_workspace_strategy": {"root": str(WORKSPACE_ROOT), "workspaces": [str(WORKSPACE_ROOT / s) for s in ASSIGNMENTS], "outside_ragin_repository": True, "git_repositories": False, "symlinks_to_ragin_repository": False, "allowed_files_only": sorted(ALLOWED_FILES), "first_filesystem_action": "pwd", "workspace_mismatch_action": "STOP with WORKSPACE_MISMATCH"},
        "packet_source_mapping": {session: f"results/laya_research/rater_packets_v3/{a['packet']}" for session, a in ASSIGNMENTS.items()},
        "resource_and_scientific_rules": {"selection_before_annotation": True, "outcome_driven_selection": False, "taxonomy_unchanged": True, "aggregation_rules_unchanged": True, "frozen_v3_semantics_unchanged": True},
    }
    amendment_path = RESULTS / "expert_ai_panel_amendment_01.json"
    write_json(amendment_path, amendment)

    manifest = {"manifest_version": "expert_ai_panel_manifest_v1a", "panel_type": "MULTI_MODEL_INDEPENDENT_AI_SESSIONS", "status": "AMENDED_PREREGISTERED_PRE_ANNOTATION", "annotation_started": False, "annotation_completed": False, "case_count": 120, "case_set": "FROZEN_V3", "selection_timing": "FIXED_BEFORE_ANNOTATION_OUTCOMES", "capability_equivalence_claim": False, "human_panel": False, "human_ground_truth_claim": False, "assignments": [{"session_id": s, "assigned_model": a["model"], "operator_attested_model": a["model"], "reasoning_effort": "MEDIUM", "model_identity_provenance": "OPERATOR_UI_ATTESTED", "workspace": str(WORKSPACE_ROOT / s), "packet": str(RESULTS / "rater_packets_v3" / a["packet"])} for s, a in ASSIGNMENTS.items()], "preserved_rules": {"separate_contexts": True, "separate_shuffled_packet_order": True, "repository_access": False, "web_search": False, "annotator_communication": False, "taxonomy": "UNCHANGED_V3", "semantic_instructions": "UNCHANGED_V3", "aggregation_policy": "UNCHANGED"}, "annotation_boundary": {"previous_case_level_annotations_accessed_for_this_freeze": False, "predictions_accessed_for_this_freeze": False, "ground_truth_accessed_for_this_freeze": False}}
    manifest_path = RESULTS / "expert_ai_panel_manifest_v1a.json"
    write_json(manifest_path, manifest)

    freeze_inputs = [original, amendment_path, manifest_path, audit_path]
    for session in ASSIGNMENTS:
        workspace = WORKSPACE_ROOT / session
        freeze_inputs.extend(workspace / name for name in sorted(ALLOWED_FILES))
    freeze = {"freeze_version": "expert_ai_panel_preregistration_freeze_v1a", "freeze_status": "AMENDED_FROZEN_PRE_ANNOTATION", "amendment_id": amendment["amendment_id"], "amendment_number": 1, "amendment_pre_annotation": True, "cases_annotated_before_amendment": 0, "outcomes_seen_before_amendment": False, "new_panel": {s: f"{a['model']} / MEDIUM" for s, a in ASSIGNMENTS.items()}, "model_identity_provenance": "OPERATOR_UI_ATTESTED", "workspace_root": str(WORKSPACE_ROOT), "predictions_accessed": False, "previous_annotations_accessed": False, "ground_truth_created": False, "annotation_performed": False, "labels_calculated": False, "artifacts_sha256": {str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p): digest(p) for p in freeze_inputs}}
    freeze_path = RESULTS / "expert_ai_panel_preregistration_freeze_v1a.json"
    write_json(freeze_path, freeze)
    verified = all(digest(Path(path) if Path(path).is_absolute() else ROOT / path) == value for path, value in freeze["artifacts_sha256"].items())
    if not verified:
        raise SystemExit("BLOCKED_AMENDED_FREEZE_HASH_VERIFICATION")
    if digest(original) != EXPECTED_ORIGINAL_SHA:
        raise SystemExit("BLOCKED_ORIGINAL_FREEZE_CHANGED")
    print(json.dumps({"status": "PASS", "original_sha256": digest(original), "amended_freeze_sha256": digest(freeze_path), "workspace_root": str(WORKSPACE_ROOT), "sessions": list(ASSIGNMENTS)}, indent=2))


if __name__ == "__main__":
    main()
