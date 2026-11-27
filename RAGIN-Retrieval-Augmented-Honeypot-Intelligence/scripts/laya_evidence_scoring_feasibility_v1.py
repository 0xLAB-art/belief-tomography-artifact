from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone


ROOT = pathlib.Path(__file__).resolve().parents[1]
DEV = ROOT / "results" / "evidence_judge_paired_validation_v1"
DEV_INPUTS = DEV / "frozen_paired_inputs.json"
DEV_ARMS = DEV / "matched_arm_results.json"
WORK = ROOT / "results" / "evidence_judge_laya_scoring_v1"
PROMPT = WORK / "SCORER_PROMPT_V1.txt"
SCHEMA = WORK / "output_schema_v1.json"
THRESHOLDS = WORK / "preregistered_thresholds_v1.json"
PROTOCOL = WORK / "LAYA_FEASIBILITY_PROTOCOL_V1.md"
PROBE = WORK / "model_probe_v1.json"
FREEZE_PATH = WORK / "input_freeze_v1.json"
RUNS = WORK / "runs" / "S1"
MANIFEST = WORK / "run_manifest_v1.json"
PROBES_OUT = WORK / "robustness_probes_v1.json"
DECISION = WORK / "feasibility_decision_v1.json"
DEV_INPUTS_SHA = "5dc2717279a6003043bfd8c64c4b129e2ab31c36dfbf5aa04fa7a818462aa7ca"
DEV_ARMS_SHA = "d94d5bc01510b4c3e0286641e69ef7ba25351e6613c3fe8c1591a15664ca56da"
MODEL = "gpt-5.6-luna"
CLI_VERSION = "codex-cli 0.162.1"
CANDIDATE_LABELS = {"DIRECT_SUPPORT", "PARTIAL", "IRRELEVANT", "CONTRADICTORY", "UNKNOWN"}
BUNDLE_LABELS = {"SUFFICIENT", "INSUFFICIENT", "CONFLICTING", "UNKNOWN"}
MAX_REQUEST_CHARS = 300_000
MAX_TOKENS = 16_384
CALL_TIMEOUT_S = 900
BATCH_SIZE = 20
FILLER_RATIONALE = "Review unavailable or invalid."
BLIND_CASE_KEYS = ["case_id", "command", "preceding_commands", "claimed_behavior"]
BLIND_CAND_KEYS = ["doc_id", "title", "content", "source", "source_version", "provenance_status"]


def sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: pathlib.Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: pathlib.Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def paragraph_count(text: str) -> int:
    return len([part for part in re.split(r"\n\s*\n", text.strip()) if part.strip()]) if text.strip() else 0


def word_count(text: str) -> int:
    return len(text.split())


def verify_dev() -> None:
    if sha(DEV_INPUTS) != DEV_INPUTS_SHA:
        raise RuntimeError("development inputs hash mismatch")
    if sha(DEV_ARMS) != DEV_ARMS_SHA:
        raise RuntimeError("development comparator outputs hash mismatch")


def load_cases() -> list[dict]:
    verify_dev()
    return load(DEV_INPUTS)["cases"]


def blind_payload(case: dict) -> dict:
    return {
        "case_id": case["case_id"],
        "command": case["command"],
        "preceding_commands": case.get("preceding_commands", []),
        "claimed_behavior": case["claimed_behavior"],
        "retrieved_candidates": [{key: candidate.get(key) for key in BLIND_CAND_KEYS} for candidate in case["candidate_documents"]],
    }


def derive_candidate_oracles(case: dict, mapping: dict) -> dict[str, str]:
    by_category = mapping["candidate_label_by_category"]
    rule = by_category[case["category"]]
    expected = {}
    for candidate in case["candidate_documents"]:
        if rule == "SPECIAL_CONTRADICTORY":
            label = "CONTRADICTORY" if candidate["doc_id"].endswith("-CONTRADICTORY") else "DIRECT_SUPPORT"
        elif rule == "SPECIAL_UNSUPPORTED":
            topic = (candidate["title"] + " " + " ".join(candidate.get("behavior_tags", []))).lower()
            label = "PARTIAL" if any(word in topic for word in ["credential", "persist"]) else "IRRELEVANT"
        else:
            label = rule
        expected[candidate["doc_id"]] = label
    return expected


def derive_bundle_oracle(case: dict) -> str:
    return case["fixture_oracle"]["expected_sufficiency"]


def validation_case(case_id: str, candidates: list[dict]) -> dict:
    return {"case_id": case_id, "candidates": candidates}


def unknown_payload(case: dict) -> dict:
    return {
        "candidate_reviews": {
            candidate["doc_id"]: {"doc_id": candidate["doc_id"], "label": "UNKNOWN", "paragraph_indexes": [], "rationale": FILLER_RATIONALE}
            for candidate in case["candidates"]
        },
        "bundle_review": {"label": "UNKNOWN", "supporting_doc_ids": [], "conflicting_doc_ids": [], "rationale": FILLER_RATIONALE},
    }


def normalize_output(cases: list[dict], output: object) -> tuple[dict, list[str]]:
    errors: list[str] = []
    rows = output.get("cases") if isinstance(output, dict) else None
    by_case: dict[str, dict] = {}
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict) and isinstance(row.get("case_id"), str):
                if row["case_id"] in by_case:
                    errors.append(f"duplicate case: {row['case_id']}")
                else:
                    by_case[row["case_id"]] = row
    normalized: dict[str, dict] = {}
    for case in cases:
        case_id = case["case_id"]
        candidates = case["candidates"]
        result = unknown_payload(case)
        row = by_case.get(case_id)
        if row is None:
            errors.append(f"case omitted: {case_id}")
            normalized[case_id] = result
            continue
        reviews = row.get("candidate_reviews")
        seen: set[int] = set()
        if isinstance(reviews, list):
            for item in reviews:
                if not isinstance(item, dict):
                    continue
                index = item.get("candidate_index")
                if type(index) is not int or index < 0 or index >= len(candidates):
                    continue
                if index in seen:
                    errors.append(f"duplicate candidate index: {case_id}/{index}")
                    continue
                seen.add(index)
                candidate = candidates[index]
                label = item.get("label")
                indexes = item.get("paragraph_indexes")
                rationale = item.get("rationale")
                valid = (
                    label in CANDIDATE_LABELS
                    and isinstance(indexes, list)
                    and all(type(i) is int and 1 <= i <= paragraph_count(candidate.get("content", "")) for i in indexes)
                    and isinstance(rationale, str)
                    and 0 < word_count(rationale) <= 8
                )
                if label == "UNKNOWN":
                    valid = valid and indexes == []
                else:
                    valid = valid and len(indexes or []) > 0
                if valid:
                    result["candidate_reviews"][candidate["doc_id"]] = {
                        "doc_id": candidate["doc_id"],
                        "label": label,
                        "paragraph_indexes": indexes,
                        "rationale": rationale,
                    }
                else:
                    errors.append(f"invalid candidate review: {case_id}/{index}")
        else:
            errors.append(f"candidate_reviews missing: {case_id}")
        missing = [index for index in range(len(candidates)) if index not in seen]
        if missing:
            errors.append(f"candidate review coverage incomplete: {case_id}")
        bundle = row.get("bundle_review")
        if isinstance(bundle, dict):
            label = bundle.get("label")
            supporting = bundle.get("supporting_candidate_indexes")
            conflicting = bundle.get("conflicting_candidate_indexes")
            rationale = bundle.get("rationale")
            valid_indexes = lambda values: isinstance(values, list) and all(type(i) is int and 0 <= i < len(candidates) for i in values)
            if label in BUNDLE_LABELS and valid_indexes(supporting) and valid_indexes(conflicting) and isinstance(rationale, str) and 0 < word_count(rationale) <= 12:
                result["bundle_review"] = {
                    "label": label,
                    "supporting_doc_ids": [candidates[i]["doc_id"] for i in supporting],
                    "conflicting_doc_ids": [candidates[i]["doc_id"] for i in conflicting],
                    "rationale": rationale,
                }
            else:
                errors.append(f"invalid bundle review: {case_id}")
        else:
            errors.append(f"bundle_review missing: {case_id}")
        normalized[case_id] = result
    return normalized, errors


def normalize_from_text(cases: list[dict], text: str) -> tuple[dict, list[str], bool]:
    try:
        output = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return {case["case_id"]: unknown_payload(case) for case in cases}, ["output parse failure"], False
    normalized, errors = normalize_output(cases, output)
    return normalized, errors, True


def degraded_output(cases: list[dict], reason: str) -> tuple[dict, list[str]]:
    return {case["case_id"]: unknown_payload(case) for case in cases}, [reason]


def wall_from_stdout(path: pathlib.Path) -> float | None:
    if not path.exists():
        return None
    stamps = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event.get("timestamp"), (int, float)):
            stamps.append(event["timestamp"])
    if len(stamps) < 2:
        return None
    return (max(stamps) - min(stamps)) / 1000.0


def codex_cmd(output_schema: pathlib.Path | None, final_path: pathlib.Path) -> list[str]:
    cmd = ["codex", "exec", "--ephemeral", "--json", "--skip-git-repo-check", "-m", MODEL, "-o", str(final_path), "-C", "/tmp", "-"]
    if output_schema is not None:
        cmd.insert(-3, "--output-schema")
        cmd.insert(-3, str(output_schema))
    return cmd


def call_codex(cmd: list[str], request_text: str, call_dir: pathlib.Path, final_path: pathlib.Path) -> dict:
    call_dir.mkdir(parents=True, exist_ok=True)
    (call_dir / "request_sha256.txt").write_text(hashlib.sha256(request_text.encode()).hexdigest() + "\n", encoding="utf-8")
    record: dict = {"command": cmd, "request_chars": len(request_text)}
    started = time.monotonic()
    try:
        result = subprocess.run(cmd, input=request_text, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=CALL_TIMEOUT_S, check=False)
        record["wall_seconds"] = time.monotonic() - started
        (call_dir / "stdout.jsonl").write_text(result.stdout, encoding="utf-8")
        (call_dir / "stderr.log").write_text(result.stderr, encoding="utf-8")
        record.update({"exit_code": result.returncode, "stdout_sha256": sha(call_dir / "stdout.jsonl"), "stderr_sha256": sha(call_dir / "stderr.log")})
        if final_path.exists():
            record["final_message_sha256"] = sha(final_path)
    except subprocess.TimeoutExpired:
        record["wall_seconds"] = time.monotonic() - started
        record["timeout"] = True
    except Exception as error:
        record["wall_seconds"] = time.monotonic() - started
        record["error"] = type(error).__name__ + ": " + str(error)
    record["finished_at_utc"] = now_utc()
    return record


def probe() -> None:
    if PROBE.exists():
        raise RuntimeError("model probe already frozen")
    final_path = WORK / "probe_final_message.json"
    cmd = codex_cmd(None, final_path)
    request = 'Return only the JSON object {"status":"READY"} and nothing else.'
    call_dir = WORK / "probe_call"
    record = call_codex(cmd, request, call_dir, final_path)
    if record.get("timeout") or record.get("exit_code") != 0 or not final_path.exists():
        raise RuntimeError("probe call failed: " + json.dumps(record, sort_keys=True))
    text = final_path.read_text(encoding="utf-8").strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = None
    if not isinstance(parsed, dict) or parsed.get("status") != "READY":
        raise RuntimeError("probe output is not READY JSON: " + text[:200])
    write(PROBE, {
        "schema": "ragin.laya_scorer_model_probe.v1",
        "model_id": MODEL,
        "cli_version": CLI_VERSION,
        "request": request,
        "probe_record": record,
        "final_message_sha256": sha(final_path),
        "observed_at_utc": now_utc(),
    })
    print(json.dumps({"probe": str(PROBE.relative_to(ROOT)), "sha256": sha(PROBE), "wall_seconds": record.get("wall_seconds")}, indent=2))


def truncation_probes(cases: list[dict]) -> dict:
    selected = [case for case in cases if case["category"] == "direct_relevant"][:2]
    if len(selected) != 2:
        raise RuntimeError("expected at least two direct_relevant cases for truncation probes")
    probes = []
    for case in selected:
        candidate = case["candidate_documents"][0]
        paragraphs = [part for part in re.split(r"\n\s*\n", candidate.get("content", "").strip()) if part.strip()]
        truncated = {**candidate, "content": paragraphs[0] + "\n\n[content truncated]"}
        payload = {
            "probe_id": "truncation-" + case["case_id"],
            "source_case_id": case["case_id"],
            "case": {
                "case_id": "truncation-" + case["case_id"],
                "command": case["command"],
                "preceding_commands": case.get("preceding_commands", []),
                "claimed_behavior": case["claimed_behavior"],
                "retrieved_candidates": [{key: truncated.get(key) for key in BLIND_CAND_KEYS}],
            },
            "expected_candidate_labels": {truncated["doc_id"]: "UNKNOWN"},
        }
        probes.append(payload)
    return {
        "schema": "ragin.laya_scorer_truncation_probes.v1",
        "construction": "First blank-line paragraph of a direct_relevant fixture document plus a truncation marker; never scored against fixture oracles, only against the frozen expected UNKNOWN.",
        "probes": probes,
    }


def prepare() -> None:
    if FREEZE_PATH.exists():
        raise RuntimeError("input freeze already exists")
    if not PROBE.exists():
        raise RuntimeError("model probe is required before prepare")
    thresholds = load(THRESHOLDS)
    mapping = thresholds["oracle_extension"]
    cases = load_cases()
    if len(cases) != 60 or sum(len(case["candidate_documents"]) for case in cases) != 66:
        raise RuntimeError("development cohort coverage mismatch")
    label_counts = Counter()
    for case in cases:
        label_counts.update(derive_candidate_oracles(case, mapping).values())
    batches = []
    for index in range(3):
        chunk = cases[index * BATCH_SIZE : (index + 1) * BATCH_SIZE]
        name = f"batch_{index + 1:02d}.json"
        path = WORK / "blind_batches" / name
        write(path, {"schema": "ragin.laya_scorer_blind_batch.v1", "cases": [blind_payload(case) for case in chunk]})
        batches.append({"path": f"blind_batches/{name}", "sha256": sha(path), "case_ids": [case["case_id"] for case in chunk]})
    probes = truncation_probes(cases)
    write(WORK / "truncation_probes_v1.json", probes)
    write(FREEZE_PATH, {
        "schema": "ragin.laya_scorer_input_freeze.v1",
        "frozen_at_utc": now_utc(),
        "model_id": MODEL,
        "cli_version": CLI_VERSION,
        "dev_inputs_sha256": DEV_INPUTS_SHA,
        "dev_arms_sha256": DEV_ARMS_SHA,
        "prompt_sha256": sha(PROMPT),
        "schema_sha256": sha(SCHEMA),
        "thresholds_sha256": sha(THRESHOLDS),
        "protocol_sha256": sha(PROTOCOL),
        "probe_sha256": sha(PROBE),
        "truncation_probes_sha256": sha(WORK / "truncation_probes_v1.json"),
        "batches": batches,
        "case_count": 60,
        "candidate_count": 66,
        "oracle_candidate_label_counts": dict(sorted(label_counts.items())),
        "bounds": {"max_request_chars": MAX_REQUEST_CHARS, "max_completion_tokens": MAX_TOKENS, "call_timeout_s": CALL_TIMEOUT_S, "batches": 3, "cases_per_batch": BATCH_SIZE},
        "executor_path": str(pathlib.Path(__file__).relative_to(ROOT)),
        "executor_sha256": sha(pathlib.Path(__file__)),
        "preregistered_thresholds_sha256": sha(THRESHOLDS),
    })
    print(json.dumps({"freeze": str(FREEZE_PATH.relative_to(ROOT)), "sha256": sha(FREEZE_PATH), "batches": len(batches), "oracle_labels": dict(sorted(label_counts.items()))}, indent=2))


def verify_freeze() -> dict:
    freeze = load(FREEZE_PATH)
    checks = {
        "dev_inputs_sha256": DEV_INPUTS_SHA,
        "dev_arms_sha256": DEV_ARMS_SHA,
        "prompt_sha256": sha(PROMPT),
        "schema_sha256": sha(SCHEMA),
        "thresholds_sha256": sha(THRESHOLDS),
        "protocol_sha256": sha(PROTOCOL),
        "probe_sha256": sha(PROBE),
        "truncation_probes_sha256": sha(WORK / "truncation_probes_v1.json"),
    }
    for key, value in checks.items():
        if freeze.get(key) != value:
            raise RuntimeError(f"input freeze mismatch: {key}")
    for batch in freeze["batches"]:
        if sha(WORK / batch["path"]) != batch["sha256"]:
            raise RuntimeError(f"blind batch hash mismatch: {batch['path']}")
    current = sha(pathlib.Path(__file__))
    if freeze.get("executor_sha256") != current:
        amendments = sorted(WORK.glob("executor_amendment_v1*.json"))
        if not amendments:
            raise RuntimeError("executor differs from freeze and no amendment exists")
        expected = freeze["executor_sha256"]
        for path in amendments:
            record = load(path)
            if record.get("frozen_executor_sha256") != expected:
                raise RuntimeError("executor amendment chain is broken")
            expected = record["amended_executor_sha256"]
        if expected != current:
            raise RuntimeError("executor amendment does not match current runner")
    return freeze


def amend_executor() -> None:
    freeze = load(FREEZE_PATH)
    amendments = sorted(WORK.glob("executor_amendment_v1*.json"))
    path = WORK / ("executor_amendment_v1.json" if not amendments else f"executor_amendment_v1_{len(amendments) + 1:02d}.json")
    prior = load(amendments[-1])["amended_executor_sha256"] if amendments else freeze["executor_sha256"]
    write(path, {
        "schema": "ragin.laya_scorer_executor_amendment.v1",
        "reason": "Runner defect corrected after freeze; blind inputs, prompt, schema, thresholds, model identity, and validation rules unchanged.",
        "scope": "No change to frozen study inputs or gates.",
        "frozen_executor_sha256": prior,
        "amended_executor_sha256": sha(pathlib.Path(__file__)),
        "amended_at_utc": now_utc(),
    })
    print(json.dumps({"amendment": str(path.relative_to(ROOT)), "sha256": sha(path)}, indent=2))


def run() -> None:
    freeze = verify_freeze()
    prompt = PROMPT.read_text(encoding="utf-8").split("BLINDED_INPUT_JSON:", 1)[0].strip()
    manifest = load(MANIFEST) if MANIFEST.exists() else {"schema": "ragin.laya_scorer_run_manifest.v1", "model_id": MODEL, "cli_version": CLI_VERSION, "calls": []}
    completed = {
        row["batch_id"]
        for row in manifest["calls"]
        if row.get("json_valid") and row.get("validated_case_count") == BATCH_SIZE and (RUNS / row["batch_id"] / "normalized_reviews.json").exists()
    }
    for batch in freeze["batches"]:
        batch_id = pathlib.Path(batch["path"]).stem
        if batch_id in completed:
            print(json.dumps({"batch": batch_id, "preserved": True}), flush=True)
            continue
        payload = load(WORK / batch["path"])
        cases = [validation_case(row["case_id"], row["retrieved_candidates"]) for row in payload["cases"]]
        request_text = prompt + "\n\nBLINDED_INPUT_JSON:\n" + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        if len(request_text) > MAX_REQUEST_CHARS:
            raise RuntimeError(f"request exceeds frozen bound: {batch_id}")
        call_dir = RUNS / batch_id
        final_path = call_dir / "final_message.json"
        final_path.parent.mkdir(parents=True, exist_ok=True)
        cmd = codex_cmd(SCHEMA, final_path)
        record = {"batch_id": batch_id, "rater_id": "S1", "model_id": MODEL, "input_sha256": batch["sha256"], "started_at_utc": now_utc()}
        if final_path.exists() and not (call_dir / "request_sha256.txt").exists():
            raise RuntimeError(f"unexpected partial state for {batch_id}")
        if final_path.exists() and batch_id not in {row.get("batch_id") for row in manifest["calls"]}:
            record.update({"recovered_after_runner_crash": True, "wall_seconds": wall_from_stdout(call_dir / "stdout.jsonl"), "exit_code": None, "stdout_sha256": sha(call_dir / "stdout.jsonl"), "stderr_sha256": sha(call_dir / "stderr.log"), "finished_at_utc": now_utc()})
        else:
            record.update(call_codex(cmd, request_text, call_dir, final_path))
        if record.get("timeout"):
            normalized, errors = degraded_output(cases, "call timeout")
            write(call_dir / "normalized_reviews.json", normalized)
            record.update({"json_valid": False, "validation_errors": errors, "validated_case_count": BATCH_SIZE})
        elif final_path.exists():
            raw = final_path.read_text(encoding="utf-8")
            normalized, errors, parse_ok = normalize_from_text(cases, raw)
            write(call_dir / "normalized_reviews.json", normalized)
            record.update({"json_valid": parse_ok, "validation_errors": errors, "validated_case_count": BATCH_SIZE})
        else:
            normalized, errors = degraded_output(cases, "final message missing")
            write(call_dir / "normalized_reviews.json", normalized)
            record.update({"json_valid": False, "validation_errors": errors, "validated_case_count": BATCH_SIZE})
        manifest["calls"].append(record)
        write(MANIFEST, manifest)
        print(json.dumps({"batch": batch_id, "json_valid": record.get("json_valid"), "validation_error_count": len(record.get("validation_errors", [])), "wall_seconds": record.get("wall_seconds")}), flush=True)


def run_probes() -> None:
    freeze = verify_freeze()
    if PROBES_OUT.exists():
        raise RuntimeError("robustness probe record already exists")
    probe_doc = load(WORK / "truncation_probes_v1.json")
    probe_cases = [probe["case"] for probe in probe_doc["probes"]]
    probe_validation = [validation_case(case["case_id"], case["retrieved_candidates"]) for case in probe_cases]
    malformed_normalized, malformed_errors, malformed_ok = normalize_from_text(probe_validation, '{"cases": [broken')
    malformed_passed = (not malformed_ok) and all(
        review["label"] == "UNKNOWN" for case in malformed_normalized.values() for review in case["candidate_reviews"].values()
    ) and all(case["bundle_review"]["label"] == "UNKNOWN" for case in malformed_normalized.values())
    timeout_normalized, timeout_errors = degraded_output(probe_validation, "simulated timeout")
    timeout_passed = all(
        review["label"] == "UNKNOWN" for case in timeout_normalized.values() for review in case["candidate_reviews"].values()
    ) and all(case["bundle_review"]["label"] == "UNKNOWN" for case in timeout_normalized.values())
    prompt = PROMPT.read_text(encoding="utf-8").split("BLINDED_INPUT_JSON:", 1)[0].strip()
    payload = {"schema": "ragin.laya_scorer_blind_batch.v1", "cases": probe_cases}
    validation_cases = [validation_case(case["case_id"], case["retrieved_candidates"]) for case in probe_cases]
    request_text = prompt + "\n\nBLINDED_INPUT_JSON:\n" + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    if len(request_text) > MAX_REQUEST_CHARS:
        raise RuntimeError("probe request exceeds frozen bound")
    call_dir = RUNS / "truncation_probes"
    final_path = call_dir / "final_message.json"
    cmd = codex_cmd(SCHEMA, final_path)
    record = {"batch_id": "truncation_probes", "rater_id": "S1", "model_id": MODEL, "started_at_utc": now_utc()}
    record.update(call_codex(cmd, request_text, call_dir, final_path))
    results = []
    if final_path.exists():
        raw = final_path.read_text(encoding="utf-8")
        normalized, errors, parse_ok = normalize_from_text(validation_cases, raw)
        write(call_dir / "normalized_reviews.json", normalized)
        record.update({"json_valid": parse_ok, "validation_errors": errors})
        for probe in probe_doc["probes"]:
            case = normalized.get(probe["case"]["case_id"], unknown_payload(validation_case(probe["case"]["case_id"], probe["case"]["retrieved_candidates"])))
            labels = {doc_id: review["label"] for doc_id, review in case["candidate_reviews"].items()}
            results.append({"probe_id": probe["probe_id"], "labels": labels, "expected": probe["expected_candidate_labels"], "all_unknown": all(label == "UNKNOWN" for label in labels.values())})
    else:
        record.update({"json_valid": False, "validation_errors": ["final message missing"]})
        results = [{"probe_id": probe["probe_id"], "labels": {}, "expected": probe["expected_candidate_labels"], "all_unknown": False} for probe in probe_doc["probes"]]
    truncation_unknown = sum(1 for row in results if row["all_unknown"])
    write(PROBES_OUT, {
        "schema": "ragin.laya_scorer_robustness_probes.v1",
        "frozen_thresholds_sha256": sha(THRESHOLDS),
        "truncation": {"call": record, "results": results, "unknown_probe_count": truncation_unknown},
        "malformed_output_selftest": {"passed": malformed_passed, "errors": malformed_errors},
        "simulated_timeout_selftest": {"passed": timeout_passed, "errors": timeout_errors},
        "recorded_at_utc": now_utc(),
    })
    print(json.dumps({"probes": str(PROBES_OUT.relative_to(ROOT)), "sha256": sha(PROBES_OUT), "truncation_unknown": truncation_unknown, "malformed_selftest": malformed_passed, "timeout_selftest": timeout_passed}, indent=2))


def baseline_from_dev(mapping: dict) -> dict:
    cases = load_cases()
    arms = load(DEV_ARMS)
    by_id = {case["case_id"]: case for case in cases}
    crosswalk = mapping["judge_label_crosswalk"]
    cand_ok = cand_n = bundle_ok = bundle_n = fr_ok = fr_n = 0
    for row in arms["results"]:
        case = by_id[row["case_id"]]
        oracle = derive_candidate_oracles(case, mapping)
        labels = {judgment["doc_id"]: crosswalk[judgment["label"]] for judgment in row["arm_b"]["judge"]["candidate_judgments"]}
        for doc_id, expected in oracle.items():
            cand_n += 1
            cand_ok += labels.get(doc_id) == expected
            if expected == "DIRECT_SUPPORT":
                fr_n += 1
                fr_ok += labels.get(doc_id) == "DIRECT_SUPPORT"
        bundle_n += 1
        bundle_ok += row["arm_b"]["judge"]["sufficiency"]["label"] == derive_bundle_oracle(case)
    return {
        "candidate_exact_agreement": {"numerator": cand_ok, "denominator": cand_n, "value": cand_ok / cand_n},
        "bundle_exact_agreement": {"numerator": bundle_ok, "denominator": bundle_n, "value": bundle_ok / bundle_n},
        "direct_support_false_rejection": {"numerator": fr_n - fr_ok, "denominator": fr_n, "value": (fr_n - fr_ok) / fr_n},
    }


def scorer_decisions(cases: list[dict], mapping: dict) -> tuple[Counter, dict]:
    freeze = load(FREEZE_PATH)
    thresholds = load(THRESHOLDS)
    batch_ids = [pathlib.Path(batch["path"]).stem for batch in freeze["batches"]]
    normalized_all: dict[str, dict] = {}
    manifest = load(MANIFEST) if MANIFEST.exists() else {"calls": []}
    calls = {row["batch_id"]: row for row in manifest["calls"]}
    schema_valid = 0
    field_errors = 0
    walls = []
    case_batch = {}
    for batch in freeze["batches"]:
        batch_id = pathlib.Path(batch["path"]).stem
        for case_id in batch["case_ids"]:
            case_batch[case_id] = batch_id
        call = calls.get(batch_id, {})
        if call.get("json_valid"):
            schema_valid += 1
        field_errors += len(call.get("validation_errors", []))
        if call.get("wall_seconds") is not None:
            walls.append((batch_id, call["wall_seconds"]))
    for batch_id in batch_ids:
        path = RUNS / batch_id / "normalized_reviews.json"
        if path.exists():
            normalized_all.update(load(path))
    for case in cases:
        if case["case_id"] not in normalized_all:
            normalized_all[case["case_id"]] = unknown_payload(validation_case(case["case_id"], case["candidate_documents"]))
    metrics = {
        "candidate_correct": 0,
        "bundle_correct": 0,
        "direct_total": 0,
        "direct_rejected": 0,
        "natural_total": 0,
        "natural_non_unknown": 0,
        "ambiguous_candidates": 0,
        "ambiguous_candidates_unknown": 0,
        "ambiguous_bundles": 0,
        "ambiguous_bundles_unknown": 0,
        "missing_provenance_candidates": 0,
        "missing_provenance_candidates_unknown": 0,
        "scorer_candidate_labels": Counter(),
        "scorer_bundle_labels": Counter(),
    }
    for case in cases:
        oracle = derive_candidate_oracles(case, mapping)
        bundle_oracle = derive_bundle_oracle(case)
        result = normalized_all[case["case_id"]]
        for candidate in case["candidate_documents"]:
            doc_id = candidate["doc_id"]
            expected = oracle[doc_id]
            got = result["candidate_reviews"][doc_id]["label"]
            metrics["scorer_candidate_labels"][got] += 1
            metrics["candidate_correct"] += got == expected
            if expected == "DIRECT_SUPPORT":
                metrics["direct_total"] += 1
                metrics["direct_rejected"] += got != "DIRECT_SUPPORT"
            if case["category"] not in {"ambiguous_shell_command", "missing_provenance"}:
                metrics["natural_total"] += 1
                metrics["natural_non_unknown"] += got != "UNKNOWN"
            if case["category"] == "ambiguous_shell_command":
                metrics["ambiguous_candidates"] += 1
                metrics["ambiguous_candidates_unknown"] += got == "UNKNOWN"
            if case["category"] == "missing_provenance":
                metrics["missing_provenance_candidates"] += 1
                metrics["missing_provenance_candidates_unknown"] += got == "UNKNOWN"
        bundle_got = result["bundle_review"]["label"]
        metrics["scorer_bundle_labels"][bundle_got] += 1
        metrics["bundle_correct"] += bundle_got == bundle_oracle
        if case["category"] == "ambiguous_shell_command":
            metrics["ambiguous_bundles"] += 1
            metrics["ambiguous_bundles_unknown"] += bundle_got == "UNKNOWN"
    execution = {
        "schema_valid_batches": schema_valid,
        "total_batches": len(batch_ids),
        "field_errors": field_errors,
        "field_error_rate": field_errors / 126.0,
        "walls": walls,
        "mean_amortized_s_per_case": (sum(w for _, w in walls) / 60.0) if walls else None,
        "max_call_wall_s": max((w for _, w in walls), default=None),
    }
    return metrics, execution


def evaluate() -> None:
    freeze = verify_freeze()
    thresholds = load(THRESHOLDS)
    cases = load_cases()
    mapping = thresholds["oracle_extension"]
    recomputed = baseline_from_dev(mapping)
    recorded = thresholds["comparator"]["baseline"]
    for key in recorded:
        if recomputed[key]["numerator"] != recorded[key]["numerator"] or recomputed[key]["denominator"] != recorded[key]["denominator"]:
            raise RuntimeError(f"baseline recomputation mismatch: {key}")
    if DECISION.exists():
        raise RuntimeError("feasibility decision already exists")
    if not PROBES_OUT.exists():
        raise RuntimeError("robustness probes must run before evaluation")
    metrics, execution = scorer_decisions(cases, mapping)
    probes = load(PROBES_OUT)
    gates = thresholds["gates"]
    results = {}

    def gate(name: str, value, passed: bool, threshold):
        results[name] = {"value": value, "threshold": threshold, "passed": bool(passed)}

    gate("candidate_exact_agreement", {"count": metrics["candidate_correct"], "denominator": 66, "value": metrics["candidate_correct"] / 66}, metrics["candidate_correct"] >= gates["candidate_exact_agreement"]["min_count"], gates["candidate_exact_agreement"])
    gate("bundle_exact_agreement", {"count": metrics["bundle_correct"], "denominator": 60, "value": metrics["bundle_correct"] / 60}, metrics["bundle_correct"] >= gates["bundle_exact_agreement"]["min_count"], gates["bundle_exact_agreement"])
    gate("direct_support_false_rejection", {"count": metrics["direct_rejected"], "denominator": metrics["direct_total"], "value": metrics["direct_rejected"] / metrics["direct_total"] if metrics["direct_total"] else None}, metrics["direct_rejected"] <= gates["direct_support_false_rejection"]["max_count"], gates["direct_support_false_rejection"])
    gate("ambiguous_candidate_unknown", {"count": metrics["ambiguous_candidates_unknown"], "denominator": metrics["ambiguous_candidates"]}, metrics["ambiguous_candidates_unknown"] >= gates["ambiguous_candidate_unknown"]["min_count"], gates["ambiguous_candidate_unknown"])
    gate("ambiguous_bundle_unknown", {"count": metrics["ambiguous_bundles_unknown"], "denominator": metrics["ambiguous_bundles"]}, metrics["ambiguous_bundles_unknown"] >= gates["ambiguous_bundle_unknown"]["min_count"], gates["ambiguous_bundle_unknown"])
    gate("missing_provenance_candidate_unknown", {"count": metrics["missing_provenance_candidates_unknown"], "denominator": metrics["missing_provenance_candidates"]}, metrics["missing_provenance_candidates_unknown"] >= gates["missing_provenance_candidate_unknown"]["min_count"], gates["missing_provenance_candidate_unknown"])
    gate("natural_candidate_coverage", {"count": metrics["natural_non_unknown"], "denominator": metrics["natural_total"], "value": metrics["natural_non_unknown"] / metrics["natural_total"] if metrics["natural_total"] else None}, metrics["natural_non_unknown"] >= gates["natural_candidate_coverage"]["min_count"], gates["natural_candidate_coverage"])
    gate("schema_valid_batches", {"count": execution["schema_valid_batches"], "denominator": execution["total_batches"]}, execution["schema_valid_batches"] >= gates["schema_valid_batches"]["min_count"], gates["schema_valid_batches"])
    gate("field_error_rate", {"count": execution["field_errors"], "denominator": 126, "value": execution["field_error_rate"]}, execution["field_error_rate"] <= gates["field_error_rate"]["max_rate"], gates["field_error_rate"])
    gate("truncation_probe_candidate_unknown", {"count": probes["truncation"]["unknown_probe_count"], "denominator": 2}, probes["truncation"]["unknown_probe_count"] >= gates["truncation_probe_candidate_unknown"]["min_count"], gates["truncation_probe_candidate_unknown"])
    selftests_passed = probes["malformed_output_selftest"]["passed"] and probes["simulated_timeout_selftest"]["passed"]
    gate("harness_selftests", {"malformed": probes["malformed_output_selftest"]["passed"], "timeout": probes["simulated_timeout_selftest"]["passed"]}, selftests_passed, gates["harness_selftests_required"])
    mean_latency = execution["mean_amortized_s_per_case"]
    max_latency = execution["max_call_wall_s"]
    gate("latency_mean_amortized_s_per_case", mean_latency, mean_latency is not None and mean_latency <= gates["latency_mean_amortized_s_per_case"]["max"], gates["latency_mean_amortized_s_per_case"])
    gate("latency_per_call_wall_s", max_latency, max_latency is not None and max_latency <= gates["latency_per_call_wall_s"]["max"], gates["latency_per_call_wall_s"])
    verdict = "PASS" if all(item["passed"] for item in results.values()) else "FAIL"
    write(DECISION, {
        "schema": "ragin.laya_scorer_feasibility_decision.v1",
        "verdict": verdict,
        "pass_rule": thresholds["pass_rule"],
        "preregistered_thresholds_sha256": sha(THRESHOLDS),
        "input_freeze_sha256": sha(FREEZE_PATH),
        "protocol_sha256": sha(PROTOCOL),
        "baseline_assertion": {"recomputed": recomputed, "recorded": recorded, "matches": True},
        "scorer_metrics": {
            "candidate_exact_agreement": {"count": metrics["candidate_correct"], "denominator": 66, "value": metrics["candidate_correct"] / 66},
            "bundle_exact_agreement": {"count": metrics["bundle_correct"], "denominator": 60, "value": metrics["bundle_correct"] / 60},
            "direct_support_false_rejection": {"count": metrics["direct_rejected"], "denominator": metrics["direct_total"]},
            "natural_candidate_coverage": {"count": metrics["natural_non_unknown"], "denominator": metrics["natural_total"]},
            "scorer_candidate_label_counts": dict(sorted(metrics["scorer_candidate_labels"].items())),
            "scorer_bundle_label_counts": dict(sorted(metrics["scorer_bundle_labels"].items())),
        },
        "execution": execution,
        "gates": results,
        "run_manifest_sha256": sha(MANIFEST) if MANIFEST.exists() else None,
        "robustness_probes_sha256": sha(PROBES_OUT),
        "decided_at_utc": now_utc(),
    })
    print(json.dumps({"decision": str(DECISION.relative_to(ROOT)), "sha256": sha(DECISION), "verdict": verdict, "failed_gates": [name for name, item in results.items() if not item["passed"]]}, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=["probe", "prepare", "amend-executor", "run", "run-probes", "evaluate"])
    phase = parser.parse_args().phase
    try:
        {"probe": probe, "prepare": prepare, "amend-executor": amend_executor, "run": run, "run-probes": run_probes, "evaluate": evaluate}[phase]()
        return 0
    except Exception as error:
        print(f"BLOCKED: {type(error).__name__}: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
