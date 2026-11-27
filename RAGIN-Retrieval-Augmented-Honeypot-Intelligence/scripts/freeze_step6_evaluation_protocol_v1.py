"""Freeze the Step 6 matched controlled evaluation protocol (evidence-judge contrast).

What this script does (PLAN Step 6, docs/PAPER_REMAINING_STEPS_2026-10-14.md):
  * Inventories the prospective controlled-real-admin capture source and records
    exclusions BEFORE any selection happens (selection never reads judge or
    reference artifacts).
  * Selects the case cohort deterministically (all eligible captures, ordered by
    capture_id) and derives the same identity keys used by the frozen HF2024
    holdouts (sha_bytes / sha_json family, sequence, preceding-context keys) so
    cross-cohort comparison is byte-exact.
  * Runs a key-by-key disjointness gate against every used cohort (HF2024
    holdouts, Laya real/manifest cohorts, fixture 60, substantive-final
    holdouts, Laya v3 validation set, synthetic development corpus). Zero
    overlap required at every comparable key.
  * Computes the paired power/precision analysis (paired-t noncentrality,
    scipy nct) for the preregistered smallest effect size of interest and
    derives the sample-size decision from it instead of reusing a convenient
    count.
  * Writes the full preregistered protocol (arms, outcomes, thresholds,
    multiplicity, missingness, seeds, execution/abort rules, reference
    identity) with sha256 locks over data, code anchors and the Step 3
    reference-protocol artifacts.

Modes:
  run    - write all artifacts + freeze manifest + sha256 manifest
  verify - re-derive keys, re-run disjointness and power, re-hash every locked
           source and output; print PASS/FAIL JSON and set exit status.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "step6_matched_evaluation_protocol_v1"
EXPERIMENT_ID = "ragin.step6.matched_judge_contrast.v1"

CAPTURE_DIR = ROOT / "data" / "prospective_v4" / "controlled_admin"
REGISTRY = ROOT / "data" / "prospective_v4" / "capture_registry.jsonl"
COWRIE_DIR = ROOT / "data" / "prospective_v4" / "cowrie"
CORPUS_DIR = ROOT / "data" / "corpus"

# Preregistered statistical constants (chosen BEFORE data inspection, justified
# in power_analysis_v1.json).
SEED = 20261015
ALPHA = 0.05
POWER_TARGET = 0.80
DELTA_STAR = 0.15          # smallest effect size of interest (absolute)
SIGMA_CENTRAL = 0.25       # central assumption for SD of paired differences
SIGMA_GRID = [0.15, 0.20, 0.25, 0.30, 0.35]

# Code anchors locked by the freeze (identity of everything the arms invoke).
CODE_ANCHORS = [
    "ragin/don/evidence_judge.py",
    "ragin/don/command_aware_v2.py",
    "ragin/don/rag_engine.py",
    "ragin/decision_fusion_v4/benchmark.py",
    "ragin/decision_fusion_v4/policy.py",
    "ragin/decision_fusion_v4/evidence_export.py",
    "ragin/cycle/harness.py",
    "ragin/cycle/adapters.py",
    "ragin/cycle/hitl.py",
    "ragin/cycle/session.py",
    "ragin/cycle/verifier.py",
    "ragin/hisoka/strategy_generator_v1.py",
    "ragin/hisoka/deceiver.py",
    "results/decision_fusion_v4/v4_selected_logistic_policy.joblib",
    "scripts/freeze_step6_evaluation_protocol_v1.py",
]

# Step 3 blinded-reference protocol identity (reused unchanged for the new
# cohort; constructed before and independently of arm outcomes).
REFERENCE_PROTOCOL_FILES = [
    "results/evidence_judge_real_data_ablation_v1/ai_reference_v2_2/CODEX_REFERENCE_PROTOCOL_V2_2.md",
    "results/evidence_judge_real_data_ablation_v1/ai_reference_v2_2/output_schema.json",
    "results/evidence_judge_real_data_ablation_v1/ai_reference_v2_2/reference_freeze_manifest_v2_2.json",
    "results/evidence_judge_real_data_ablation_v1/ai_reference_v2_1/AI_PRIMARY_PROMPT_V2.txt",
    "scripts/evidence_support_codex_reference_v2_2.py",
    "scripts/locked_evidence_support_evaluation_v2_2.py",
]

REFERENCE_MODEL_IDENTITY = "gpt-5.6-luna via Codex CLI; AI-derived reference, not human ground truth or independent consensus"

USED_COHORTS: dict[str, dict[str, Any]] = {
    "hf2024_postfix_family_disjoint_240": {
        "path": "results/decision_fusion_v4/hf2024_postfix_family_disjoint_v1/holdout_freeze.json",
        "kind": "digest+group",
    },
    "hf2024_retrospective_holdout_v1_240": {
        "path": "results/decision_fusion_v4/v4_hf2024_retrospective_holdout_freeze_v1.json",
        "kind": "digest+group",
    },
    "hf2024_retrospective_holdout_v1a_240": {
        "path": "results/decision_fusion_v4/v4_hf2024_retrospective_holdout_freeze_v1a.json",
        "kind": "digest+group",
    },
    "don_v2_substantive_final_240": {
        "path": "results/decision_fusion_v4/don_v2_substantive_final_v1/holdout_freeze.json",
        "kind": "digest+group+plaintext",
    },
    "v4_real_holdout_manifest_240": {
        "path": "results/decision_fusion_v4/v4_real_holdout_manifest_v1.json",
        "kind": "laya_raw_digest",
    },
    "v4_real_holdout_manifest_v1a": {
        "path": "results/decision_fusion_v4/v4_real_holdout_manifest_v1a.json",
        "kind": "empty_manifest",
    },
    "evidence_judge_ablation_selection_120": {
        "path": "results/evidence_judge_real_data_ablation_v1/frozen_case_selection.json",
        "kind": "digest+group",
    },
    "laya_primary_169_v2b": {
        "path": "results/laya_decision_v2/primary_169_input_manifest_v2b.json",
        "kind": "laya_raw_digest",
    },
    "laya_primary_169_v2a": {
        "path": "results/laya_decision_v2/primary_169_input_manifest_v2a.json",
        "kind": "laya_raw_digest",
    },
    "laya_exploratory_120": {
        "path": "results/laya_decision_v2/exploratory_120_input_manifest.json",
        "kind": "laya_raw_digest",
    },
    "evidence_judge_fixture_60": {
        "path": "results/evidence_judge_paired_validation_v1/frozen_paired_inputs.json",
        "kind": "plaintext",
    },
    "laya_v3_validation_set_30": {
        "path": "results/laya_decision_v3/laya_v3_task_adaptation_validation_set_freeze_v1.json",
        "kind": "non_shell_names",
    },
    "v4_development_corpus_192": {
        "path": "results/decision_fusion_v4/v4_development_corpus_freeze_v1.json",
        "kind": "non_shell_names",
    },
}


# ---------------------------------------------------------------- helpers


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha_file(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def sha_json(value: Any) -> str:
    """Byte-exact with the HF2024 holdout derivation."""
    return sha_bytes(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def sha_json_ascii(value: Any) -> str:
    """Byte-exact with the Laya preregistration derivation (ensure_ascii=False)."""
    return sha_bytes(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode())


def norm(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value).strip().lower())


def family(commands: list[str]) -> tuple[str, ...]:
    return tuple(norm(command) for command in commands if norm(command))


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def git_output(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True).stdout


def write_json(name: str, value: Any) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def corpus_hashes() -> dict[str, Any]:
    files = []
    for path in sorted(CORPUS_DIR.rglob("*")):
        if path.is_file() and path.suffix.lower() in {".txt", ".json", ".jsonl", ".md"}:
            files.append({"path": str(path.relative_to(ROOT)), "sha256": sha_file(path)})
    manifest_sha = sha_bytes(
        json.dumps(files, sort_keys=True, separators=(",", ":")).encode()
    )
    return {"file_count": len(files), "files": files, "manifest_sha256": manifest_sha}


# ------------------------------------------------- case selection pipeline


def load_registry() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows = [json.loads(line) for line in REGISTRY.read_text(encoding="utf-8").splitlines() if line.strip()]
    return rows, {"registry_path": str(REGISTRY.relative_to(ROOT)), "registry_sha256": sha_file(REGISTRY), "row_count": len(rows)}


def inspect_exclusions(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Exclusions are recorded BEFORE selection and never consult judge or
    reference artifacts (selection inputs are registry provenance fields only)."""
    on_disk = {p.name for p in sorted(CAPTURE_DIR.glob("*.canonical.json"))}
    in_registry = {f"{row.get('capture_id')}.canonical.json" for row in rows}

    ineligible = []
    eligible = []
    derive_checks = []
    for row in rows:
        name = f"{row.get('capture_id')}.canonical.json"
        path = CAPTURE_DIR / name
        exists = path.is_file()
        derive_ok = None
        if exists:
            derive_ok = read_json(path).get("canonical_record_sha256") == row.get("canonical_record_sha256")
        checks = {
            "capture_id": row.get("capture_id"),
            "canonical_file_exists": exists,
            "derive_sha256_matches": derive_ok,
            "registry_eligible": bool(row.get("eligible_for_real_evaluation")),
            "selected_input_present": bool(str(read_json(path).get("selected_input") if exists else "").strip()),
        }
        derive_checks.append(checks)
        reasons = []
        if not exists:
            reasons.append("canonical_file_missing")
        if derive_ok is False:
            reasons.append("derive_sha256_mismatch")
        if not row.get("eligible_for_real_evaluation"):
            reasons.append(f"registry_ineligible:{row.get('ineligibility_reason')}")
        if not exists or not str(read_json(path).get("selected_input") or "").strip():
            reasons.append("selected_input_empty")
        if reasons:
            ineligible.append({"capture_id": row.get("capture_id"), "reasons": reasons})
        else:
            eligible.append(row)

    cowrie_sessions = sorted(str(p.relative_to(ROOT)) for p in (COWRIE_DIR / "sessions").glob("*")) if (COWRIE_DIR / "sessions").exists() else []
    watcher_states = []
    for state in sorted(COWRIE_DIR.rglob("watcher_state.json")):
        data = read_json(state)
        watcher_states.append(
            {
                "path": str(state.relative_to(ROOT)),
                "sessions_seen": len(data.get("sessions") or []),
                "files_seen": len(data.get("files") or []),
                "sha256": sha_file(state),
            }
        )

    return {
        "schema": "ragin.step6.exclusions_preselection.v1",
        "inspected_at": utc_now(),
        "selection_never_reads": ["evidence_judge outputs", "reference labels", "arm outputs", "gate outcomes"],
        "canonical_files_on_disk": sorted(on_disk),
        "registry_entries": len(rows),
        "orphan_files_not_in_registry": sorted(on_disk - in_registry),
        "registry_entries_missing_on_disk": sorted(in_registry - on_disk),
        "derive_sha256_checks": derive_checks,
        "ineligible": ineligible,
        "cowrie_prospective_capture": {
            "sessions_dir_files": cowrie_sessions,
            "watcher_states": watcher_states,
            "note": "Cowrie prospective capture produced no attacker sessions; excluded from the case cohort as ineligible source (0 usable cases).",
        },
        "eligible_capture_count": len(eligible),
    }


def case_keys(selected_input: str, preceding: list[str]) -> dict[str, Any]:
    commands = list(preceding) + [selected_input]
    fam = family(commands)
    return {
        "final_input_sha256_bytes": sha_bytes(selected_input.encode("utf-8")),
        "final_input_sha256_json": sha_json(selected_input),
        "final_input_sha256_json_ascii": sha_json_ascii(selected_input),
        "source_family_sha256": sha_json(list(fam)),
        "sequence_sha256": sha_json(commands),
        "preceding_context_sha256": sha_json(commands[:-1]),
        "normalized_session_text": "\n".join(fam),
        "normalized_input_text": norm(selected_input),
        "command_count": len(commands),
    }


def select_cases(rows: list[dict[str, Any]]) -> dict[str, Any]:
    eligible = []
    for row in rows:
        name = f"{row.get('capture_id')}.canonical.json"
        path = CAPTURE_DIR / name
        if not path.is_file():
            continue
        if read_json(path).get("canonical_record_sha256") != row.get("canonical_record_sha256"):
            continue
        canonical = read_json(path)
        if not row.get("eligible_for_real_evaluation") or not str(canonical.get("selected_input") or "").strip():
            continue
        eligible.append(row)
    eligible.sort(key=lambda row: str(row["capture_id"]))

    cases = []
    for row in eligible:
        canonical = read_json(CAPTURE_DIR / f"{row['capture_id']}.canonical.json")
        selected_input = str(canonical["selected_input"])
        preceding = [
            str(event.get("operator_input"))
            for event in canonical.get("prior_session_context") or []
            if event.get("event_type") == "operator_input"
        ][: int(canonical.get("selected_input_event_index") or 0)]
        keys = case_keys(selected_input, preceding)
        cases.append(
            {
                "case_id": f"controlled-admin-{row['capture_id']}",
                "capture_id": row["capture_id"],
                "selected_input": selected_input,
                "preceding_commands": preceding,
                "identity_keys": {k: v for k, v in keys.items() if k not in {"normalized_session_text", "normalized_input_text"}},
                "normalized_session_text_sha256": sha_bytes(keys["normalized_session_text"].encode("utf-8")),
                "normalized_input_text_sha256": sha_bytes(keys["normalized_input_text"].encode("utf-8")),
                "_plaintext": {
                    "normalized_session_text": keys["normalized_session_text"],
                    "normalized_input_text": keys["normalized_input_text"],
                },
                "provenance": {
                    "canonical_record_sha256": row.get("canonical_record_sha256"),
                    "raw_log_sha256": row.get("raw_log_sha256"),
                    "capture_manifest_sha256": row.get("capture_manifest_sha256"),
                },
                "independence": {"source_cluster_id": row.get("source_cluster_id"), "native_session_id": row.get("native_session_id")},
                "evidence_integrity": {"source_class": row.get("source_class"), "deployment_id": row.get("deployment_id")},
                "canonical_record_sha256": row.get("canonical_record_sha256"),
                "canonical_file_sha256": sha_file(CAPTURE_DIR / f"{row['capture_id']}.canonical.json"),
                "canonical_command_count": len(canonical.get("commands") or []),
            }
        )
    return {
        "schema": "ragin.step6.selected_cases.v1",
        "experiment_id": EXPERIMENT_ID,
        "status": "FROZEN_BEFORE_CONFIRMATORY_CALLS",
        "frozen_at": utc_now(),
        "selection_rule": (
            "All registry-eligible controlled-real-admin captures with verified "
            "canonical derive_sha256 and non-empty selected_input, ordered by "
            "capture_id ascending. No judge, reference, gate or arm output is "
            "read during selection."
        ),
        "source_registry_sha256": sha_file(REGISTRY),
        "N": len(cases),
        "unique_capture_ids": len({c["capture_id"] for c in cases}),
        "unique_final_inputs": len({c["identity_keys"]["final_input_sha256_bytes"] for c in cases}),
        "unique_families": len({c["identity_keys"]["source_family_sha256"] for c in cases}),
        "cases": cases,
    }


def reference_input_freeze(selection: dict[str, Any]) -> dict[str, Any]:
    cases = []
    for case in selection["cases"]:
        cases.append(
            {
                "case_id": case["case_id"],
                "capture_id": case["capture_id"],
                "selected_input": case["selected_input"],
                "preceding_commands": case["preceding_commands"],
                "identity_keys": case["identity_keys"],
                "normalized_session_text_sha256": case["normalized_session_text_sha256"],
                "normalized_input_text_sha256": case["normalized_input_text_sha256"],
            }
        )
    return {
        "schema": "ragin.step6.blinded_reference_input_freeze.v1",
        "experiment_id": EXPERIMENT_ID,
        "status": "FROZEN_BEFORE_ARM_OUTCOMES",
        "reference_status": "INPUTS_FROZEN_LABELS_PENDING_RETRIEVAL_PACKET",
        "blinding_contract": {
            "allowed_fields": ["case_id", "capture_id", "selected_input", "preceding_commands", "identity_keys", "normalized_*_sha256", "retrieval_candidates"],
            "forbidden_fields": ["arm", "arm_a", "arm_b", "judge", "gate", "policy", "generator", "verifier", "hitl", "commit", "outcome", "served_response"],
            "rule": "Construct retrieval candidates from frozen inputs before any arm outcome is joined; labels are not present in this input freeze.",
        },
        "source_selection_sha256": sha_file(OUT / "selected_cases_v1.json"),
        "N": selection["N"],
        "cases": cases,
    }


def holdout_freeze(selection: dict[str, Any], exclusions: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "ragin.step6.untouched_holdout_freeze.v1",
        "experiment_id": EXPERIMENT_ID,
        "status": "FROZEN_BEFORE_CONFIRMATORY_CALLS",
        "holdout_role": "prospective controlled-real-admin evaluation cohort; no prior judge, reference, gate, policy, or arm outcomes used for selection",
        "selection_manifest": "results/step6_matched_evaluation_protocol_v1/selected_cases_v1.json",
        "selection_manifest_sha256": sha_file(OUT / "selected_cases_v1.json"),
        "registry_path": str(REGISTRY.relative_to(ROOT)),
        "registry_sha256": sha_file(REGISTRY),
        "N": selection["N"],
        "case_ids": [case["case_id"] for case in selection["cases"]],
        "case_ids_sha256": sha_json([case["case_id"] for case in selection["cases"]]),
        "preselection_exclusions_sha256": sha_file(OUT / "exclusions_preselection_v1.json"),
        "preselection_summary": {
            "registry_entries": exclusions["registry_entries"],
            "eligible_capture_count": exclusions["eligible_capture_count"],
            "ineligible_count": len(exclusions["ineligible"]),
            "orphan_file_count": len(exclusions["orphan_files_not_in_registry"]),
        },
        "untouched_rule": "No confirmatory arm execution, reference label, judge output, gate output, policy output, or outcome is present in this freeze.",
    }


def retrieval_evidence_freeze(selection: dict[str, Any]) -> dict[str, Any]:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from ragin.don.command_aware_v2 import CommandAwareRetrieverV2

    retriever = CommandAwareRetrieverV2(corpus_path=ROOT / "data/corpus/command_aware_v2.jsonl")
    cases = []
    for case in selection["cases"]:
        result = retriever.retrieve(
            case["selected_input"],
            case["preceding_commands"],
            session_id=case["case_id"],
            classification="step6_reference_prearm",
        )
        candidates = []
        for document in result["documents"]:
            candidates.append(
                {
                    key: value
                    for key, value in document.items()
                    if key not in {"score", "relevance_grade"}
                }
            )
        cases.append(
            {
                "case_id": case["case_id"],
                "input_sha256": case["identity_keys"]["final_input_sha256_bytes"],
                "candidate_count": len(candidates),
                "candidates": candidates,
                "retrieval_trace": result["trace"],
            }
        )
    return {
        "schema": "ragin.step6.blinded_retrieval_evidence_freeze.v1",
        "experiment_id": EXPERIMENT_ID,
        "status": "FROZEN_BEFORE_ARM_OUTCOMES",
        "reference_role": "retrieval candidates supplied to the blinded reference constructor; no judge, gate, policy, generator, verifier, HITL, commit, or served-output fields",
        "retriever_version": "DON_COMMAND_AWARE_V2",
        "corpus_path": "data/corpus/command_aware_v2.jsonl",
        "corpus_sha256": retriever.corpus_sha256,
        "N": len(cases),
        "cases": cases,
    }


# ------------------------------------------------------- disjointness gate


def cohort_identity_sets(name: str, spec: dict[str, Any]) -> dict[str, Any]:
    path = ROOT / spec["path"]
    data = read_json(path)
    sets: dict[str, set[str]] = {
        "final_input_bytes": set(), "final_input_json": set(), "final_input_json_ascii": set(),
        "source_family": set(), "sequence": set(), "preceding_context": set(),
        "raw_input_digest": set(), "normalized_text": set(), "group_or_case_id": set(),
    }
    notes: list[str] = []

    def add_case(case: dict[str, Any]) -> None:
        for key, target in (
            ("final_input_sha256", "final_input_bytes"),
            ("sequence_sha256", "sequence"),
            ("preceding_context_sha256", "preceding_context"),
            ("source_family_sha256", "source_family"),
            ("raw_input_sha256", "raw_input_digest"),
            ("input_hash", "raw_input_digest"),
        ):
            value = case.get(key)
            if isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value):
                sets[target].add(value.lower())
        for key in ("source_group_id", "session_group_id", "case_id"):
            value = case.get(key)
            if isinstance(value, str) and value:
                sets["group_or_case_id"].add(value)
        commands = case.get("commands")
        if isinstance(commands, list) and commands:
            sets["normalized_text"].add("\n".join(family([str(c) for c in commands])))
            final = str(commands[-1])
            sets["final_input_bytes"].add(sha_bytes(final.encode("utf-8")))
            sets["final_input_json"].add(sha_json(final))
            sets["final_input_json_ascii"].add(sha_json_ascii(final))
            sets["preceding_context"].add(sha_json([str(c) for c in commands[:-1]]))
            sets["sequence"].add(sha_json([str(c) for c in commands]))
            sets["source_family"].add(sha_json(list(family([str(c) for c in commands]))))
        command = case.get("command")
        if isinstance(command, str) and command:
            sets["normalized_text"].add(norm(command))
            sets["final_input_bytes"].add(sha_bytes(command.encode("utf-8")))
            sets["final_input_json"].add(sha_json(command))
            sets["final_input_json_ascii"].add(sha_json_ascii(command))
        for pre in case.get("preceding_commands") or []:
            if isinstance(pre, str) and pre:
                sets["normalized_text"].add(norm(pre))
        name_value = case.get("name")
        if isinstance(name_value, str) and name_value:
            sets["group_or_case_id"].add(name_value)

    if spec["kind"] == "empty_manifest":
        notes.append("manifest is an empty-cases amendment; no identity to compare")
    else:
        container = data.get("cases") if isinstance(data, dict) else data
        if isinstance(container, list):
            for case in container:
                if isinstance(case, dict):
                    add_case(case)
        rows = data.get("rows") if isinstance(data, dict) else None
        if isinstance(rows, list):
            for row in rows:
                if isinstance(row, dict):
                    add_case(row)
    return {
        "path": spec["path"],
        "sha256": sha_file(path),
        "kind": spec["kind"],
        "sets": {key: sorted(value) for key, value in sets.items()},
        "set_sizes": {key: len(value) for key, value in sets.items()},
        "notes": notes,
    }


def run_disjointness(cases: list[dict[str, Any]]) -> dict[str, Any]:
    comparisons = []
    total_hits = 0
    for name, spec in USED_COHORTS.items():
        identity = cohort_identity_sets(name, spec)
        sets = {key: set(value) for key, value in identity["sets"].items()}
        hits: list[dict[str, Any]] = []
        for case in cases:
            keys = case["identity_keys"]
            plain = case["_plaintext"]
            checks: dict[str, list[str]] = {}
            mapping = {
                "final_input_bytes": [keys["final_input_sha256_bytes"]],
                "final_input_json": [keys["final_input_sha256_json"]],
                "final_input_json_ascii": [keys["final_input_sha256_json_ascii"]],
                "source_family": [keys["source_family_sha256"]],
                "sequence": [keys["sequence_sha256"]],
                "preceding_context": [keys["preceding_context_sha256"]],
                "raw_input_digest": [keys["final_input_sha256_json"], keys["final_input_sha256_json_ascii"], keys["final_input_sha256_bytes"]],
                "normalized_text": [plain["normalized_session_text"], plain["normalized_input_text"]],
                "group_or_case_id": [case["case_id"], case["capture_id"], case["canonical_record_sha256"], f"controlled-admin-v4-{case['capture_id']}"],
            }
            for set_name, values in mapping.items():
                for value in values:
                    if value in sets[set_name]:
                        checks.setdefault(set_name, []).append(value)
            for set_name, matched in checks.items():
                hits.append({"case_id": case["case_id"], "cohort_key": set_name, "matched_values": matched})
        total_hits += len(hits)
        comparisons.append(
            {
                "cohort": name,
                "source": identity["path"],
                "source_sha256": identity["sha256"],
                "kind": identity["kind"],
                "cohort_set_sizes": identity["set_sizes"],
                "notes": identity["notes"],
                "overlap_hits": hits,
                "overlap_count": len(hits),
                "status": "PASS" if not hits else "FAIL",
            }
        )
    return {
        "schema": "ragin.step6.disjointness_audit.v1",
        "experiment_id": EXPERIMENT_ID,
        "checked_at": utc_now(),
        "keys_compared": [
            "final_input (sha_bytes, sha_json, sha_json ensure_ascii=False)",
            "normalized family (sha_json of normalized command family)",
            "normalized session sequence (sha_json of raw command list)",
            "preceding context (sha_json of commands[:-1])",
            "normalized plaintext session/input text (where cohort exposes plaintext)",
            "group/case/record identifiers",
        ],
        "case_count": len(cases),
        "comparisons": comparisons,
        "total_overlap_hits": total_hits,
        "status": "PASS" if total_hits == 0 else "FAIL",
        "unavailable_cohorts": [
            {
                "cohort": "laya_independent_169_primary_model_execution",
                "status": "UNAVAILABLE",
                "reason": "locked primary runs require Laya model execution; not present in repository",
                "effect_on_disjointness": "none — the 169 primary manifest inputs were compared (rows above)",
            }
        ],
    }


# ------------------------------------------------------------ power analysis


def paired_t_power(n: int, delta: float, sigma: float, alpha: float = ALPHA) -> float:
    from scipy import stats

    d = delta / sigma
    df = n - 1
    ncp = d * math.sqrt(n)
    crit = float(stats.t.ppf(1 - alpha / 2, df))
    return float(stats.nct.sf(crit, df, ncp) + stats.nct.cdf(-crit, df, ncp))


def required_n(delta: float, sigma: float, power_target: float = POWER_TARGET) -> int | None:
    for n in range(4, 501):
        if paired_t_power(n, delta, sigma) >= power_target:
            return n
    return None


def mde(n: int, sigma: float, power_target: float = POWER_TARGET) -> float | None:
    delta = 0.005
    while delta <= 1.0:
        if paired_t_power(n, delta, sigma) >= power_target:
            return round(delta, 3)
        delta += 0.005
    return None


def ci_half_width(n: int, sigma: float) -> float:
    from scipy import stats

    return float(stats.t.ppf(1 - ALPHA / 2, n - 1) * sigma / math.sqrt(n))


def power_analysis(n_available: int) -> dict[str, Any]:
    from scipy import stats  # noqa: F401  (presence asserted for the analysis)

    table = []
    for sigma in SIGMA_GRID:
        table.append(
            {
                "sigma": sigma,
                "power_at_delta_star": round(paired_t_power(n_available, DELTA_STAR, sigma), 4),
                "required_n_for_delta_star": required_n(DELTA_STAR, sigma),
                "mde_at_available_n": mde(n_available, sigma),
                "ci95_half_width_at_available_n": round(ci_half_width(n_available, sigma), 4),
            }
        )
    req_central = required_n(DELTA_STAR, SIGMA_CENTRAL)
    if req_central is not None and req_central <= n_available:
        decision = (
            f"N={n_available} (all eligible captures) exceeds the required "
            f"n={req_central} for the preregistered effect target under the "
            f"central sigma assumption ({SIGMA_CENTRAL}); sample size fixed at "
            "the full eligible cohort."
        )
        decision_code = "ALL_ELIGIBLE_EXCEEDS_REQUIRED_N"
        n_frozen = n_available
    else:
        decision = (
            f"Required n={req_central} for the preregistered effect target "
            f"under the central sigma assumption exceeds the available "
            f"{n_available} eligible captures. Confirmatory N is frozen at "
            f"{n_available} with the shortfall disclosed; the confirmatory "
            "claim is gated on the reported achieved precision and the study "
            "is labeled underpowered for effects below the observed MDE."
        )
        decision_code = "REQUIRED_N_EXCEEDS_AVAILABLE_DISCLOSED"
        n_frozen = n_available
    return {
        "schema": "ragin.step6.power_analysis.v1",
        "experiment_id": EXPERIMENT_ID,
        "computed_at": utc_now(),
        "design": "paired (both arms run every case; per-case outcome difference B minus A)",
        "primary_statistic": "mean paired difference in per-case unsupported-admission fraction",
        "test": "two-sided paired permutation (sign-flip, 100000 draws, frozen seed) with paired-t power approximation for design",
        "alpha": ALPHA,
        "power_target": POWER_TARGET,
        "smallest_effect_size_of_interest": {
            "delta": DELTA_STAR,
            "justification": (
                "0.15 absolute reduction in the per-case unsupported-admission "
                "fraction. On the frozen historical cohort the gate-only arm "
                "admitted a 0.741 candidate-level unsupported rate, and the "
                "judge demonstrably misses adjacent/ambiguous support, so the "
                "achievable headroom is bounded; a stage that changes fewer "
                "than roughly 1 in 7 admitted-evidence decisions does not "
                "justify its added latency and complexity in the deployed "
                "pipeline."
            ),
        },
        "central_sigma_assumption": {
            "sigma": SIGMA_CENTRAL,
            "justification": (
                "Paired design: both arms share identical retrieval candidates "
                "per case, so per-case fractions are strongly correlated and "
                "paired differences concentrate near zero on the majority of "
                "cases; historical judge-vs-gate agreement on the old cohort "
                "was 1.0 at case level, so dispersion is driven only by cases "
                "where the judge changes admissions."
            ),
        },
        "sigma_sensitivity_table": table,
        "n_available_eligible": n_available,
        "required_n_at_central_sigma": req_central,
        "sample_size_decision_code": decision_code,
        "sample_size_decision": decision,
        "n_frozen": n_frozen,
        "precision_statement": (
            f"At N={n_frozen} the expected 95% CI half-width for the mean "
            f"paired difference is {ci_half_width(n_frozen, SIGMA_CENTRAL):.3f} "
            f"under central sigma; MDE for 80% power is "
            f"{mde(n_frozen, SIGMA_CENTRAL)} at central sigma and "
            f"{mde(n_frozen, SIGMA_GRID[-1])} at the conservative sigma "
            f"({SIGMA_GRID[-1]})."
        ),
    }


# --------------------------------------------------------------- protocol


def protocol_document(cases: list[dict[str, Any]], power: dict[str, Any], corpus: dict[str, Any], reference_freeze: dict[str, Any], holdout: dict[str, Any], retrieval_freeze: dict[str, Any]) -> dict[str, Any]:
    n = power["n_frozen"]
    return {
        "schema": "ragin.step6.matched_evaluation_protocol.v1",
        "experiment_id": EXPERIMENT_ID,
        "status": "FROZEN_BEFORE_CONFIRMATORY_CALLS",
        "frozen_at": utc_now(),
        "plan_step": "Step 6 — matched controlled evaluation protocol (docs/PAPER_REMAINING_STEPS_2026-10-14.md)",
        "design": "within-case matched contrast on the prospective controlled-real-admin cohort",
        "cases": {
            "manifest": "results/step6_matched_evaluation_protocol_v1/selected_cases_v1.json",
            "manifest_sha256": sha_file(OUT / "selected_cases_v1.json"),
            "N": n,
            "source": "controlled-real-admin prospective captures (synthetic evidence, real capture protocol)",
            "session_isolation": "one isolated session per (case, arm); session_id = sha256(EXPERIMENT_ID, case_id, arm); no cross-case or cross-arm state carryover",
            "untouched_holdout": {
                "manifest": "results/step6_matched_evaluation_protocol_v1/holdout_freeze_v1.json",
                "manifest_sha256": sha_file(OUT / "holdout_freeze_v1.json"),
                "N": holdout["N"],
            },
        },
        "arms": {
            "A_judge_off": {
                "description": "baseline Don evidence (CommandAwareRetrieverV2 retrieval) with the evidence judge and judge filtering disabled; EvidenceQualityGate applied to the Don evidence bundle",
                "evidence_judge": "disabled (judge not invoked)",
                "evidence_judge_filtering": "disabled",
                "gate": "EvidenceQualityGate (EVIDENCE_GATE_V1)",
            },
            "B_judge_on": {
                "description": "identical Don evidence plus DeterministicEvidenceJudge (DETERMINISTIC_COMMAND_GROUNDED_V1) and judge filtering; the same EvidenceQualityGate applied to the filtered bundle",
                "evidence_judge": "DETERMINISTIC_COMMAND_GROUNDED_V1 (score >= 0.72 SUPPORT, >= 0.45 PARTIAL, < 0.45 CONTRADICTORY; provenance and context-missing rules per judge contract)",
                "evidence_judge_filtering": "enabled (EVIDENCE_JUDGE_FILTERING_V1)",
                "gate": "EvidenceQualityGate (EVIDENCE_GATE_V1), unchanged",
            },
            "held_identical_within_contrast": {
                "retrieval": "CommandAwareRetrieverV2 over the frozen corpus (identical candidates in both arms)",
                "policy": "RAGIN_V4_DETERMINISTIC (frozen; policy model and thresholds hash-locked; logistic model locked for exploratory estimand E3 only)",
                "generator": "V1_SUBSTANTIVE_STRATEGY_GENERATOR deterministic, seed 0, runtime RAGIN_V4_SUBSTANTIVE_DETERMINISTIC",
                "verifier": "FictionConsistencyVerifier (mandatory verification on)",
                "hitl": "ApprovalGateway REQUIRE (deterministic recorded decisions)",
                "provider": "closed-port deterministic gateway (127.0.0.1:1); provider-backed serving is secondary-mode only and excluded from the confirmatory primary",
                "host_fiction": "disabled (RAGIN_HOST_FICTION=0)",
                "laya": "disabled (RAGIN_LAYA_ENABLED=0; not in this pipeline path)",
            },
            "arm_order": "counterbalanced by capture_id parity (even: A then B; odd: B then A), recorded per case",
        },
        "reference": {
            "protocol": "Step 3 blinded AI reference (v2_2): constructed from input, context and retrieval candidates only, with all arm identifiers, gate outputs and policy outputs stripped",
            "blinding": "reference construction runs and is frozen + hash-locked BEFORE any arm outcome is joined",
            "model_identity": REFERENCE_MODEL_IDENTITY,
            "reference_type": "AI_DERIVED_ADJUDICATED_REFERENCE",
            "files_locked": list(REFERENCE_PROTOCOL_FILES),
            "input_freeze": "results/step6_matched_evaluation_protocol_v1/reference_input_freeze_v1.json",
            "input_freeze_sha256": sha_file(OUT / "reference_input_freeze_v1.json"),
            "input_freeze_status": reference_freeze["reference_status"],
            "retrieval_freeze": "results/step6_matched_evaluation_protocol_v1/retrieval_evidence_freeze_v1.json",
            "retrieval_freeze_sha256": sha_file(OUT / "retrieval_evidence_freeze_v1.json"),
            "retrieval_freeze_status": retrieval_freeze["status"],
            "labels": "per-candidate support label in {DIRECT_SUPPORT, PARTIAL_SUPPORT, IRRELEVANT, CONTRADICTORY, UNKNOWN} plus bundle sufficiency, per the v2_2 output schema",
            "unsupported_definition": "candidate admitted while its reference label is not DIRECT_SUPPORT (PARTIAL_SUPPORT counted as unsupported in the primary; a PARTIAL-as-supported sensitivity analysis is preregistered as secondary)",
        },
        "outcomes": {
            "P1_primary_evidence_quality": {
                "name": "unsupported-evidence admission fraction",
                "unit": "case",
                "definition": "U_i = |admitted candidates whose reference label is not DIRECT_SUPPORT| / |admitted candidates| in arm X for case i; a case with zero admitted candidates contributes U_i = 0 and is flagged abstention (co-reported)",
                "admitted_definition": "candidate doc id present in the arm's gate valid_doc_ids (policy-visible evidence set)",
                "contrast": "paired difference B minus A across all N cases",
                "test": "two-sided paired permutation (sign-flip, 100000 draws, seed 20261015)",
                "ci": "paired bootstrap percentile CI (20000 draws, seed 20261015)",
                "success_criterion": "p < 0.05 AND point estimate <= -0.15 (the preregistered smallest effect size of interest)",
            },
            "P2_co_primary_working_system_utility": {
                "name": "reference-grounded strategy consumption rate",
                "unit": "case",
                "definition": "G_i = fraction of served turns in case i whose response was served as a V4-consumed strategy (serving_outcome STRATEGY_CONSUMED_AND_SERVED) AND every policy-visible supporting evidence id is reference-DIRECT_SUPPORT; fallback, no-serve and ungrounded serves count 0",
                "justification_separate_from_P1": (
                    "P1 measures admission quality at the gate boundary; P2 "
                    "measures whether the working system actually serves "
                    "strategies grounded in validated evidence. It is "
                    "sensitive to the proposed change (filtering alters the "
                    "policy-visible set and therefore grounding) and is not "
                    "the ceiling'd accepted-non-fallback rate: on the frozen "
                    "historical cohort accepted-non-fallback sat at its "
                    "ceiling while unsupported admissions were 0.741, so "
                    "groundedness retains headroom."
                ),
                "contrast": "paired difference B minus A across all N cases",
                "test": "two-sided paired permutation (sign-flip, 100000 draws, seed 20261015)",
                "ci": "paired bootstrap percentile CI (20000 draws, seed 20261015)",
                "hierarchy": "tested only if P1 rejects at alpha 0.05 (fixed-sequence gatekeeping)",
            },
            "key_secondaries": {
                "false_rejection_rate": "fraction of reference-DIRECT_SUPPORT candidates excluded by the arm's admission path (arm B) or missing from retrieval-relevance admission (arm A); non-inferiority margin +0.05 (B minus A upper CI bound)",
                "abstention_rate": "fraction of cases whose gate state is not VALID_EVIDENCE; non-inferiority margin +0.10",
                "gate_validity_flip_rate": "fraction of cases where A and B gate states differ",
                "policy_correct_when_referenced": "fraction of served V4-consumed turns whose selected strategy is supported by the case's reference-backed tactics (descriptive)",
                "judge_reference_confusion_matrix": "judge labels vs reference labels at candidate level (descriptive)",
                "response_consistency": "within-case response hash/length consistency and arm-difference summaries (descriptive)",
                "safety": "verifier bypasses, unauthorized commits, unsafe evidence promotion, arm-state leakage, and rejected-update invariants (descriptive)",
                "operational": "fallback/retry/error counts, provider attempts, per-stage and end-to-end latency, response length (descriptive)",
                "multiplicity": "Benjamini-Hochberg q = 0.10 within the secondary family; secondaries support (never establish) claims",
            },
            "E3_exploratory_policy_contrast": {
                "name": "policy contrast (RAGIN_V4_DETERMINISTIC vs RAGIN_V4_LOGISTIC)",
                "status": "separate exploratory estimand, NOT part of the judge contrast",
                "analysis": "paired per-case P1 outcome difference between policy arms under arm B wiring, reported with CI only; no confirmatory claim; promoting it requires its own protocol amendment with its own multiplicity budget",
                "separation_guarantee": "the judge contrast (A vs B) holds the policy fixed; any policy comparison is reported in a distinct section and never pooled with A-vs-B contrasts",
            },
        },
        "multiplicity": {
            "familywise_alpha": ALPHA,
            "gatekeeping": "P1 first at alpha 0.05 two-sided; P2 tested only if P1 rejects (fixed sequence); secondaries BH q 0.10 descriptive; E3 separate exploratory bucket",
        },
        "missingness_and_failures": {
            "complete_pair_rule": "primary analyses use complete (A, B) case pairs; incomplete pairs are counted and reported with reasons",
            "downgrade": "if incomplete pairs exceed 10% of N, P1 and P2 are reported as descriptive only",
            "provider_failure_reporting": "every provider call records attempts and errors; provider failures never substitute outcomes — closed-port deterministic serving is the confirmatory mode",
            "crash_rule": "a crashed case/arm is rerun with the identical frozen inputs and seed; the rerun and the crash are both recorded",
        },
        "thresholds": {
            "gate": "EVIDENCE_GATE_V1 thresholds as frozen in ragin/decision_fusion_v4/benchmark.py (hash-locked)",
            "judge": "judge score thresholds as frozen in ragin/don/evidence_judge.py (hash-locked)",
            "strategy_filter": "strategy-specific tactic/TP matching thresholds as frozen in ragin/decision_fusion_v4/policy.py (hash-locked)",
        },
        "statistics": {
            "seed": SEED,
            "observation_unit": "case; paired A/B differences, with candidate-level summaries clustered by case and source/independence group where available",
            "clustering": "primary inference is case-level; candidate labels never treated as independent observations; source_cluster_id and independence_group_id are reported and used for sensitivity grouping when nontrivial",
            "permutation_draws": 100000,
            "bootstrap_draws": 20000,
            "test": "paired sign-flip permutation, two-sided",
            "power_table": "results/step6_matched_evaluation_protocol_v1/power_analysis_v1.json",
            "power_note": (
                f"required n={power['required_n_at_central_sigma']} for delta*="
                f"{DELTA_STAR} at central sigma {SIGMA_CENTRAL}; frozen N={n}; "
                "sensitivity across sigma grid is preregistered and reported regardless of outcome"
            ),
        },
        "execution": {
            "runner": "Step 7 execution script (to be written after this freeze; must assert this manifest's hashes before any call)",
            "pipeline": "Chrollo -> Don (retrieval + optional judge/filter) -> EvidenceGate -> V4 deterministic policy -> substantive generator -> FictionConsistencyVerifier -> ApprovalGateway -> commit -> serving",
            "abort_policy": "any source/code/corpus hash mismatch against freeze_manifest_v1.json aborts execution before any case runs",
            "record_contract": "per-turn records carry the Step 5 required-evidence field groups (15 groups) plus arm, reference join keys and groundedness fields",
            "assertions_at_execution": [
                "policy code and model hash identical across arms",
                "retrieval corpus hash identical across arms",
                "reference freeze file hash unchanged between construction and join",
                "no arm label present in any reference-construction input",
                "raw arm outputs are frozen before any reference-label or outcome join",
            ],
        },
        "data_sources": {
            "cases": "the 40 frozen controlled-real-admin captures (selected_cases_v1.json)",
            "corpus": {
                "path": "data/corpus",
                "file_count": corpus["file_count"],
                "manifest_sha256": corpus["manifest_sha256"],
            },
            "unavailable": [
                {"cohort": "laya_real_169", "status": "UNAVAILABLE (model execution artifacts absent); manifest inputs used for disjointness only"},
                {"cohort": "hf2024_120_evidence_judge_audit", "status": "used cohort (disjointness only); not a case source for this study"},
            ],
        },
    }


# ------------------------------------------------------ freeze and manifests


def freeze_manifest(cases: list[dict[str, Any]], corpus: dict[str, Any]) -> dict[str, Any]:
    sources: dict[str, str] = {
        str(REGISTRY.relative_to(ROOT)): sha_file(REGISTRY),
    }
    for case in cases:
        sources[f"data/prospective_v4/controlled_admin/{case['capture_id']}.canonical.json"] = case["canonical_file_sha256"]
    for name, spec in USED_COHORTS.items():
        sources[spec["path"]] = sha_file(ROOT / spec["path"])
    for rel in CODE_ANCHORS + REFERENCE_PROTOCOL_FILES:
        sources[rel] = sha_file(ROOT / rel)
    return {
        "schema": "ragin.step6.freeze_manifest.v1",
        "experiment_id": EXPERIMENT_ID,
        "frozen_at": utc_now(),
        "status": "FROZEN_BEFORE_CONFIRMATORY_CALLS",
        "git_head": git_output("rev-parse", "HEAD").strip(),
        "complete_relevant_worktree_diff_sha256": sha_bytes(git_output("diff", "--binary").encode()),
        "worktree_status_sha256": sha_bytes(git_output("status", "--porcelain=v1", "--untracked-files=all").encode()),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "scipy_available": _scipy_version(),
        "source_hashes": dict(sorted(sources.items())),
        "corpus": {"file_count": corpus["file_count"], "manifest_sha256": corpus["manifest_sha256"]},
        "random_seed": SEED,
    }


def _scipy_version() -> str:
    try:
        import scipy

        return scipy.__version__
    except Exception:
        return "MISSING"


OUTPUT_FILES = [
    "exclusions_preselection_v1.json",
    "selected_cases_v1.json",
    "disjointness_audit_v1.json",
    "power_analysis_v1.json",
    "reference_input_freeze_v1.json",
    "holdout_freeze_v1.json",
    "retrieval_evidence_freeze_v1.json",
    "protocol_v1.json",
    "freeze_manifest_v1.json",
]


def sha256_manifest() -> dict[str, Any]:
    return {
        "schema": "ragin.step6.sha256_manifest.v1",
        "experiment_id": EXPERIMENT_ID,
        "generated_at": utc_now(),
        "files": {name: sha_file(OUT / name) for name in OUTPUT_FILES if (OUT / name).is_file()},
    }


# ----------------------------------------------------------------- commands


def do_run() -> int:
    rows, registry_meta = load_registry()
    exclusions = inspect_exclusions(rows)
    write_json("exclusions_preselection_v1.json", exclusions)
    selection = select_cases(rows)
    write_json("selected_cases_v1.json", selection)
    disjointness = run_disjointness(selection["cases"])
    write_json("disjointness_audit_v1.json", disjointness)
    if disjointness["status"] != "PASS":
        print(json.dumps({"status": "ABORT", "reason": "disjointness_overlap", "hits": disjointness["total_overlap_hits"]}, indent=2))
        return 1
    corpus = corpus_hashes()
    power = power_analysis(selection["N"])
    write_json("power_analysis_v1.json", power)
    reference_freeze = reference_input_freeze(selection)
    write_json("reference_input_freeze_v1.json", reference_freeze)
    holdout = holdout_freeze(selection, exclusions)
    write_json("holdout_freeze_v1.json", holdout)
    retrieval_freeze = retrieval_evidence_freeze(selection)
    write_json("retrieval_evidence_freeze_v1.json", retrieval_freeze)
    protocol = protocol_document(selection["cases"], power, corpus, reference_freeze, holdout, retrieval_freeze)
    write_json("protocol_v1.json", protocol)
    write_json("freeze_manifest_v1.json", freeze_manifest(selection["cases"], corpus))
    write_json("sha256_manifest.json", sha256_manifest())
    print(
        json.dumps(
            {
                "status": "PASS",
                "N": selection["N"],
                "disjointness": disjointness["status"],
                "overlap_hits": disjointness["total_overlap_hits"],
                "sample_decision": power["sample_size_decision_code"],
                "required_n": power["required_n_at_central_sigma"],
                "outputs": sorted(OUTPUT_FILES + ["sha256_manifest.json"]),
            },
            indent=2,
        )
    )
    return 0


def do_verify() -> int:
    checks: list[dict[str, Any]] = []

    def check(name: str, ok: bool, detail: Any = None) -> None:
        checks.append({"check": name, "status": "PASS" if ok else "FAIL", "detail": detail})

    manifest = read_json(OUT / "freeze_manifest_v1.json")
    for rel, expected in manifest["source_hashes"].items():
        actual = sha_file(ROOT / rel)
        check(f"source_hash:{rel}", actual == expected, {"expected": expected, "actual": actual})
    sha_manifest = read_json(OUT / "sha256_manifest.json")
    check("output_manifest_complete", set(sha_manifest["files"]) == set(OUTPUT_FILES))
    for name, expected in sha_manifest["files"].items():
        actual = sha_file(OUT / name)
        check(f"output_hash:{name}", actual == expected, {"expected": expected, "actual": actual})

    selection = read_json(OUT / "selected_cases_v1.json")
    rows, _ = load_registry()
    fresh = select_cases(rows)
    check("selection_reproducible", fresh["cases"] == selection["cases"])
    exclusions = read_json(OUT / "exclusions_preselection_v1.json")
    check("preselection_matches_selection", exclusions["eligible_capture_count"] == selection["N"] and not exclusions["ineligible"] and not exclusions["orphan_files_not_in_registry"])
    reference_freeze = read_json(OUT / "reference_input_freeze_v1.json")
    check("blinded_reference_input_freeze", reference_freeze["N"] == selection["N"] and len(reference_freeze["cases"]) == selection["N"] and reference_freeze["reference_status"] == "INPUTS_FROZEN_LABELS_PENDING_RETRIEVAL_PACKET")
    forbidden = ("arm", "judge", "gate", "policy", "generator", "verifier", "hitl", "commit", "outcome", "served_response")
    check("reference_input_has_no_arm_outcome_fields", not any(key in reference_freeze["cases"][0] for key in forbidden))
    holdout = read_json(OUT / "holdout_freeze_v1.json")
    check("untouched_holdout_freeze", holdout["N"] == selection["N"] and holdout["case_ids"] == [case["case_id"] for case in selection["cases"]] and holdout["status"] == "FROZEN_BEFORE_CONFIRMATORY_CALLS")
    retrieval_freeze = read_json(OUT / "retrieval_evidence_freeze_v1.json")
    check("retrieval_evidence_freeze", retrieval_freeze["N"] == selection["N"] and len(retrieval_freeze["cases"]) == selection["N"] and retrieval_freeze["status"] == "FROZEN_BEFORE_ARM_OUTCOMES" and all("score" not in candidate and "relevance_grade" not in candidate for case in retrieval_freeze["cases"] for candidate in case["candidates"]))
    protocol = read_json(OUT / "protocol_v1.json")
    check("protocol_locks_prearm_packets", protocol["reference"]["input_freeze_sha256"] == sha_file(OUT / "reference_input_freeze_v1.json") and protocol["reference"]["retrieval_freeze_sha256"] == sha_file(OUT / "retrieval_evidence_freeze_v1.json") and protocol["cases"]["untouched_holdout"]["manifest_sha256"] == sha_file(OUT / "holdout_freeze_v1.json"))
    fresh_disjoint = run_disjointness(selection["cases"])
    stored_disjoint = read_json(OUT / "disjointness_audit_v1.json")
    check("disjointness_reproducible_zero_overlap", fresh_disjoint["total_overlap_hits"] == 0 and fresh_disjoint["status"] == stored_disjoint["status"] == "PASS")
    fresh_power = power_analysis(selection["N"])
    stored_power = read_json(OUT / "power_analysis_v1.json")
    check(
        "power_reproducible",
        fresh_power["required_n_at_central_sigma"] == stored_power["required_n_at_central_sigma"]
        and fresh_power["n_frozen"] == stored_power["n_frozen"],
        {"required_n": fresh_power["required_n_at_central_sigma"]},
    )
    check("frozen_before_confirmatory_calls", selection["status"] == "FROZEN_BEFORE_CONFIRMATORY_CALLS" and manifest["status"] == "FROZEN_BEFORE_CONFIRMATORY_CALLS")

    failed = [c for c in checks if c["status"] == "FAIL"]
    print(json.dumps({"status": "PASS" if not failed else "FAIL", "checks": len(checks), "failed": failed[:10]}, indent=2))
    return 0 if not failed else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["run", "verify"], nargs="?", default="run")
    args = parser.parse_args()
    if args.mode == "run":
        return do_run()
    return do_verify()


if __name__ == "__main__":
    sys.exit(main())
