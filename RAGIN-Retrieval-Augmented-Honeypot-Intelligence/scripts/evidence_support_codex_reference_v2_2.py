from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import subprocess
import sys
from collections import Counter

import evidence_support_ai_reference_v2 as base


WORK = base.BASE / "ai_reference_v2_2"
MODEL = "gpt-5.6-luna"
CLI_VERSION = "codex-cli 0.162.1"
SOURCE_BATCHES = base.BASE / "ai_reference_v2_1" / "primary_inputs"
PROMPT_SOURCE = base.BASE / "ai_reference_v2_1" / "AI_PRIMARY_PROMPT_V2.txt"


def sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: pathlib.Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def prepare() -> None:
    if (WORK / "input_freeze_v2_2.json").exists():
        raise RuntimeError("V2.2 input freeze already exists")
    packet = base.verify_source()
    references = []
    for index in range(1, 7):
        source = SOURCE_BATCHES / f"batch_{index:02d}.json"
        data = json.loads(source.read_text(encoding="utf-8"))
        if len(data.get("cases", [])) != 20:
            raise RuntimeError(f"unexpected case count in {source.name}")
        references.append({"path": source.name, "sha256": sha(source), "case_ids": [row["case_id"] for row in data["cases"]], "candidate_count": sum(len(row["retrieved_candidates"]) for row in data["cases"])})
    freeze = {
        "schema": "ragin.evidence_support_codex_input_freeze.v2.2",
        "source_packet_sha256": base.SOURCE_SHA,
        "case_count": sum(len(row["case_ids"]) for row in references),
        "candidate_count": sum(row["candidate_count"] for row in references),
        "model_id": MODEL,
        "cli_version": CLI_VERSION,
        "prompt_sha256": sha(PROMPT_SOURCE),
        "protocol_sha256": sha(WORK / "CODEX_REFERENCE_PROTOCOL_V2_2.md"),
        "schema_sha256": sha(WORK / "output_schema.json"),
        "executor_path": str(pathlib.Path(__file__).relative_to(base.ROOT)),
        "executor_sha256": sha(pathlib.Path(__file__)),
        "source_batch_directory": str(SOURCE_BATCHES.relative_to(base.ROOT)),
        "batches": references,
        "annotation_rule": "one fixed reviewer; invalid, missing, or uncited fields normalize to UNKNOWN",
    }
    if freeze["case_count"] != 120 or freeze["candidate_count"] != 947:
        raise RuntimeError("frozen input coverage does not match the source packet")
    write(WORK / "input_freeze_v2_2.json", freeze)
    print(json.dumps({"input_freeze_sha256": sha(WORK / "input_freeze_v2_2.json"), "cases": freeze["case_count"], "candidates": freeze["candidate_count"], "model_id": MODEL}, indent=2))


def verify_freeze() -> dict:
    path = WORK / "input_freeze_v2_2.json"
    freeze = json.loads(path.read_text(encoding="utf-8"))
    checks = {
        "source_packet_sha256": base.SOURCE_SHA,
        "prompt_sha256": sha(PROMPT_SOURCE),
        "protocol_sha256": sha(WORK / "CODEX_REFERENCE_PROTOCOL_V2_2.md"),
        "schema_sha256": sha(WORK / "output_schema.json"),
    }
    for key, value in checks.items():
        if freeze.get(key) != value:
            raise RuntimeError(f"input freeze mismatch: {key}")
    current_executor = sha(pathlib.Path(__file__))
    if freeze.get("executor_sha256") != current_executor:
        amendment_paths = sorted(WORK.glob("executor_amendment_v2_2*.json"))
        if not amendment_paths:
            raise RuntimeError("executor differs from freeze and no amendment exists")
        expected = freeze.get("executor_sha256")
        for amendment_path in amendment_paths:
            amendment = json.loads(amendment_path.read_text(encoding="utf-8"))
            if amendment.get("frozen_executor_sha256") != expected:
                raise RuntimeError("executor amendment chain is broken")
            expected = amendment.get("amended_executor_sha256")
        if expected != current_executor:
            raise RuntimeError("executor amendment does not match current runner")
    for batch in freeze["batches"]:
        source = SOURCE_BATCHES / batch["path"]
        if sha(source) != batch["sha256"]:
            raise RuntimeError(f"source batch hash mismatch: {batch['path']}")
    return freeze


def amend_executor() -> None:
    freeze = json.loads((WORK / "input_freeze_v2_2.json").read_text(encoding="utf-8"))
    manifest_path = WORK / "run_manifest_v2_2.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    prior_amendments = sorted(WORK.glob("executor_amendment_v2_2*.json"))
    amendment_path = WORK / ("executor_amendment_v2_2.json" if not prior_amendments else f"executor_amendment_v2_2_{len(prior_amendments) + 1:02d}.json")
    prior_hash = json.loads(prior_amendments[-1].read_text(encoding="utf-8"))["amended_executor_sha256"] if prior_amendments else freeze["executor_sha256"]
    first = next((row for row in manifest["calls"] if row.get("batch_id") == "batch_01"), None)
    final_path = WORK / "runs" / "C1" / "batch_01" / "final_message.json"
    normalized_path = WORK / "runs" / "C1" / "batch_01" / "normalized_reviews.json"
    if not first or not first.get("json_valid") or first.get("validated_case_count") != 20 or not final_path.exists() or not normalized_path.exists():
        raise RuntimeError("preserved first call is not valid")
    write(amendment_path, {
        "schema": "ragin.evidence_support_codex_executor_amendment.v2.2",
        "reason": "Corrected a print-only flush keyword passed to json.dumps after batch artifacts were durably written.",
        "scope": "No change to source packet, inputs, model, prompt, schema, request, validation, or accepted annotations.",
        "frozen_executor_sha256": prior_hash,
        "amended_executor_sha256": sha(pathlib.Path(__file__)),
        "preserved_batch_01_final_message_sha256": sha(final_path),
        "preserved_batch_01_normalized_reviews_sha256": sha(normalized_path),
        "preserved_batch_01_call": first,
        "amended_at_utc": base.now_utc(),
    })
    print(json.dumps({"amendment_sha256": sha(amendment_path), "amended_executor_sha256": sha(pathlib.Path(__file__))}, indent=2))


def run() -> None:
    freeze = verify_freeze()
    prompt = PROMPT_SOURCE.read_text(encoding="utf-8").split("BLINDED_INPUT_JSON:", 1)[0].strip()
    manifest_path = WORK / "run_manifest_v2_2.json"
    manifest_path = WORK / "run_manifest_v2_2.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {"schema": "ragin.evidence_support_codex_run_manifest.v2.2", "model_id": MODEL, "cli_version": CLI_VERSION, "calls": []}
    completed = {row["batch_id"] for row in manifest["calls"] if row.get("json_valid") and row.get("validated_case_count") == 20 and (WORK / "runs" / "C1" / row["batch_id"] / "normalized_reviews.json").exists()}
    for batch in freeze["batches"]:
        input_path = SOURCE_BATCHES / batch["path"]
        data = json.loads(input_path.read_text(encoding="utf-8"))
        batch_id = pathlib.Path(batch["path"]).stem
        if batch_id in completed:
            print(json.dumps({"batch": batch_id, "preserved": True}), flush=True)
            continue
        call_dir = WORK / "runs" / "C1" / batch_id
        call_dir.mkdir(parents=True, exist_ok=True)
        final_path = call_dir / "final_message.json"
        cmd = ["codex", "exec", "--ephemeral", "--json", "--skip-git-repo-check", "-m", MODEL, "--output-schema", str(WORK / "output_schema.json"), "-o", str(final_path), "-C", "/tmp", "-"]
        call = {"rater_id": "C1", "model_id": MODEL, "batch_id": batch_id, "input_sha256": batch["sha256"], "command": cmd, "started_at_utc": base.now_utc()}
        request_text = prompt + "\n\nBLINDED_INPUT_JSON:\n" + json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        (call_dir / "request_sha256.txt").write_text(hashlib.sha256(request_text.encode()).hexdigest() + "\n", encoding="utf-8")
        try:
            result = subprocess.run(cmd, input=request_text, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=1200, check=False)
            (call_dir / "stdout.jsonl").write_text(result.stdout, encoding="utf-8")
            (call_dir / "stderr.log").write_text(result.stderr, encoding="utf-8")
            call.update({"exit_code": result.returncode, "stdout_sha256": sha(call_dir / "stdout.jsonl"), "stderr_sha256": sha(call_dir / "stderr.log"), "final_message_exists": final_path.exists()})
            if final_path.exists():
                call["final_message_sha256"] = sha(final_path)
                try:
                    output = json.loads(final_path.read_text(encoding="utf-8"))
                    normalized, errors = base.validate_primary_batch(data["cases"], output)
                    call.update({"json_valid": True, "validation_errors": errors, "validated_case_count": len(normalized)})
                    write(call_dir / "normalized_reviews.json", normalized)
                except (json.JSONDecodeError, TypeError) as error:
                    call.update({"json_valid": False, "parse_error": type(error).__name__ + ": " + str(error)})
            call["finished_at_utc"] = base.now_utc()
        except Exception as error:
            call.update({"exit_code": None, "error": type(error).__name__ + ": " + str(error), "finished_at_utc": base.now_utc()})
        manifest["calls"].append(call)
        write(manifest_path, manifest)
        print(json.dumps({"batch": batch_id, "exit_code": call.get("exit_code"), "json_valid": call.get("json_valid", False), "validation_error_count": len(call.get("validation_errors", []))}), flush=True)


def freeze() -> None:
    freeze_input = verify_freeze()
    manifest_path = WORK / "run_manifest_v2_2.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    by_batch = {row["batch_id"]: row for row in manifest["calls"]}
    packet = base.verify_source()
    labels = Counter()
    bundle_labels = Counter()
    case_rows = []
    for batch in freeze_input["batches"]:
        batch_id = pathlib.Path(batch["path"]).stem
        call_dir = WORK / "runs" / "C1" / batch_id
        data = json.loads((SOURCE_BATCHES / batch["path"]).read_text(encoding="utf-8"))
        normalized_path = call_dir / "normalized_reviews.json"
        normalized = json.loads(normalized_path.read_text(encoding="utf-8")) if normalized_path.exists() else {}
        call = by_batch.get(batch_id, {})
        if call.get("input_sha256") != batch["sha256"]:
            raise RuntimeError(f"run/input mismatch for {batch_id}")
        for case in data["cases"]:
            case_id = case["case_id"]
            reviewed = normalized.get(case_id, base.unknown_case(case))
            out = {"case_id": case_id, "candidate_reviews": [], "bundle_review": reviewed["bundle_review"]}
            for index, source in enumerate(case["retrieved_candidates"]):
                review = reviewed["candidate_reviews"][source["doc_id"]]
                labels[review["label"]] += 1
                out["candidate_reviews"].append({"candidate_index": index, **review})
            bundle_labels[out["bundle_review"]["label"]] += 1
            case_rows.append(out)
    if len(case_rows) != 120 or sum(len(row["candidate_reviews"]) for row in case_rows) != 947:
        raise RuntimeError("reference coverage mismatch")
    reference = {
        "schema": "ragin.evidence_support_codex_ai_reference.v2.2",
        "status": "AI_DERIVED_REFERENCE_FROZEN",
        "reference_type": "SINGLE_FIXED_MODEL_AI_DERIVED_REVIEW",
        "human_ground_truth": False,
        "independent_consensus_claim": False,
        "model_id": MODEL,
        "cli_version": CLI_VERSION,
        "source_packet_sha256": base.SOURCE_SHA,
        "input_freeze_sha256": sha(WORK / "input_freeze_v2_2.json"),
        "run_manifest_sha256": sha(manifest_path),
        "case_count": len(case_rows),
        "candidate_count": sum(len(row["candidate_reviews"]) for row in case_rows),
        "candidate_label_counts": dict(sorted(labels.items())),
        "bundle_label_counts": dict(sorted(bundle_labels.items())),
        "candidate_evaluable_count": sum(value for key, value in labels.items() if key != "UNKNOWN"),
        "bundle_evaluable_count": sum(value for key, value in bundle_labels.items() if key != "UNKNOWN"),
        "cases": case_rows,
        "frozen_at_utc": base.now_utc(),
    }
    output = WORK / "reference_freeze_v2_2.json"
    if output.exists():
        raise RuntimeError("reference freeze already exists")
    write(output, reference)
    amendments = {path.name: sha(path) for path in sorted(WORK.glob("executor_amendment_v2_2*.json"))}
    write(WORK / "reference_freeze_manifest_v2_2.json", {"reference_sha256": sha(output), "input_freeze_sha256": sha(WORK / "input_freeze_v2_2.json"), "run_manifest_sha256": sha(manifest_path), "protocol_sha256": sha(WORK / "CODEX_REFERENCE_PROTOCOL_V2_2.md"), "prompt_sha256": sha(PROMPT_SOURCE), "schema_sha256": sha(WORK / "output_schema.json"), "executor_amendment_hashes": amendments, "source_packet_sha256": base.SOURCE_SHA, "frozen_at_utc": base.now_utc()})
    print(json.dumps({"reference_sha256": sha(output), "cases": reference["case_count"], "candidates": reference["candidate_count"], "candidate_labels": reference["candidate_label_counts"], "bundle_labels": reference["bundle_label_counts"]}, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=["prepare", "amend-executor", "run", "freeze"])
    phase = parser.parse_args().phase
    try:
        {"prepare": prepare, "amend-executor": amend_executor, "run": run, "freeze": freeze}[phase]()
        return 0
    except Exception as error:
        print(f"BLOCKED: {type(error).__name__}: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
