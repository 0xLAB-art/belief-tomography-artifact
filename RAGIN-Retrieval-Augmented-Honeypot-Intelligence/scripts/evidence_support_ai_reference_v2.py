from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone


ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE = ROOT / "results/evidence_judge_real_data_ablation_v1"
WORK = BASE / "ai_reference_v2"
PACKET = BASE / "blinded_reference_packet.json"
SOURCE_SHA = "975f24fca75b0deb8d930252294ddf729eff850d715f87dc8bcac0706c4aacb5"
SOURCE_PROTOCOL_SHA = "fa5a7908b8d131b3db2a32b0330ab1713beda10008aa6760e50843804837d5b4"
MODELS = {
    "P1": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
    "P2": "thinkingmachines/inkling:free",
    "A1": "dots-studio/dots-3-note-preview:free",
}
CANDIDATE_LABELS = {"DIRECT_SUPPORT", "PARTIAL", "IRRELEVANT", "CONTRADICTORY", "UNKNOWN"}
BUNDLE_LABELS = {"SUFFICIENT", "INSUFFICIENT", "CONFLICTING", "UNKNOWN"}


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(path: pathlib.Path) -> str:
    return sha_bytes(path.read_bytes())


def write_json(path: pathlib.Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def verify_source() -> dict:
    if pathlib.Path.cwd().resolve() != ROOT.resolve():
        raise RuntimeError(f"wrong workspace: {pathlib.Path.cwd()}")
    if sha_file(PACKET) != SOURCE_SHA:
        raise RuntimeError("blinded packet hash mismatch")
    if sha_file(BASE / "protocol_freeze.json") != SOURCE_PROTOCOL_SHA:
        raise RuntimeError("source protocol hash mismatch")
    packet = read_json(PACKET)
    if packet.get("decisions_omitted") is not True or packet.get("judge_outputs_omitted") is not True or packet.get("gate_outputs_omitted") is not True:
        raise RuntimeError("blinded packet omission attestations failed")
    if len(packet.get("cases", [])) != 120 or len({c.get("case_id") for c in packet["cases"]}) != 120:
        raise RuntimeError("expected 120 unique cases")
    if sum(len(c.get("retrieved_candidates", [])) for c in packet["cases"]) != 947:
        raise RuntimeError("expected 947 candidates")
    return packet


def strip_case(case: dict) -> dict:
    return {
        "case_id": case["case_id"],
        "observed_command": case.get("observed_command", ""),
        "available_context": case.get("available_context", ""),
        "behavioral_claim": case.get("behavioral_claim", ""),
        "retrieved_candidates": [
            {"doc_id": c["doc_id"], "source": c.get("source", ""), "title": c.get("title", ""), "content": c.get("content", ""), "source_version": c.get("source_version", ""), "provenance_hash": c.get("provenance_hash", "")}
            for c in case.get("retrieved_candidates", [])
        ],
    }


def expected_files() -> list[tuple[pathlib.Path, str]]:
    return [
        (WORK / "AI_REFERENCE_PROTOCOL_V2.md", "protocol_sha256"),
        (WORK / "AI_PRIMARY_PROMPT_V2.txt", "primary_prompt_sha256"),
        (WORK / "AI_ADJUDICATION_PROMPT_V2.txt", "adjudication_prompt_sha256"),
        (WORK / "model_catalog_freeze_v2.json", "model_catalog_sha256"),
    ]


def prepare() -> None:
    packet = verify_source()
    input_freeze_path = WORK / "primary_input_freeze_v2.json"
    if input_freeze_path.exists():
        raise RuntimeError("primary input freeze already exists")
    cases = [strip_case(c) for c in packet["cases"]]
    batches = []
    for i in range(6):
        block = cases[i * 20 : (i + 1) * 20]
        rel = pathlib.Path("primary_inputs") / f"batch_{i + 1:02d}.json"
        target = WORK / rel
        if target.exists():
            raise RuntimeError(f"refusing to overwrite {target}")
        write_json(target, {"cases": block})
        batches.append({"path": rel.as_posix(), "sha256": sha_file(target), "case_ids": [c["case_id"] for c in block], "candidate_count": sum(len(c["retrieved_candidates"]) for c in block)})
    hashes = {key: sha_file(path) for path, key in expected_files()}
    write_json(input_freeze_path, {
        "schema": "ragin.evidence_support_ai_primary_input_freeze.v2",
        "frozen_at_utc": now_utc(), "source_packet_sha256": SOURCE_SHA,
        "case_count": len(cases), "candidate_count": sum(len(c["retrieved_candidates"]) for c in cases),
        "model_ids": MODELS, "batches": batches, "batch_policy": "six consecutive batches of twenty in frozen packet order",
        "excluded_fields": ["source_group_id", "input/context hashes", "all review slots", "Judge/Gate/arm/policy outputs", "analysis summaries"],
        "runner_sha256": sha_file(pathlib.Path(__file__)), **hashes,
    })
    print(json.dumps({"primary_input_freeze_sha256": sha_file(input_freeze_path), "cases": len(cases), "candidates": sum(len(c["retrieved_candidates"]) for c in cases), "batches": len(batches)}, indent=2))


def check_primary_freeze() -> dict:
    verify_source()
    freeze = read_json(WORK / "primary_input_freeze_v2.json")
    if freeze.get("runner_sha256") != sha_file(pathlib.Path(__file__)):
        raise RuntimeError("runner differs from frozen primary input preparation")
    for path, key in expected_files():
        if sha_file(path) != freeze[key]:
            raise RuntimeError(f"frozen protocol input changed: {path}")
    for batch in freeze["batches"]:
        if sha_file(WORK / batch["path"]) != batch["sha256"]:
            raise RuntimeError(f"frozen primary batch changed: {batch['path']}")
    return freeze


def paragraph_count(text: str) -> int:
    return len([part for part in re.split(r"\n\s*\n", text.strip()) if part.strip()]) if text.strip() else 0


def openrouter_request(body: dict, key: str) -> dict:
    request = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"), method="POST",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json", "HTTP-Referer": "https://localhost/ragin-evidence-reference", "X-OpenRouter-Title": "RAGIN AI Evidence Reference V2"},
    )
    with urllib.request.urlopen(request, timeout=300) as response:
        return json.loads(response.read())


def generation_info(generation_id: str, key: str) -> dict:
    url = "https://openrouter.ai/api/v1/generation?id=" + urllib.parse.quote(generation_id)
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {key}", "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read()).get("data", {})


def build_body(model: str, prompt: str, data: dict, limit: int) -> dict:
    return {"model": model, "messages": [{"role": "system", "content": prompt}, {"role": "user", "content": "BLINDED_INPUT_JSON:\n" + json.dumps(data, ensure_ascii=False, separators=(",", ":"))}], "temperature": 0, "max_tokens": limit, "provider": {"allow_fallbacks": False, "require_parameters": True}}


def execute_requests(schedule: list[dict], prompt: str, phase: str, max_tokens: int) -> None:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY is unavailable")
    manifest_path = WORK / f"{phase}_call_manifest_v2.json"
    manifest = read_json(manifest_path) if manifest_path.exists() else {"schema": "ragin.evidence_support_ai_call_manifest.v2", "phase": phase, "calls": []}
    by_key = {(row["rater_id"], row["batch_id"]): row for row in manifest["calls"]}
    for item in schedule:
        key_pair = (item["rater_id"], item["batch_id"])
        existing = by_key.get(key_pair)
        if existing and existing.get("success"):
            print(f"PRESERVED {phase} {key_pair[0]} {key_pair[1]}", flush=True)
            continue
        if existing:
            row = existing
            attempt_start = len(row["attempts"]) + 1
            if attempt_start > 3:
                print(f"EXHAUSTED {phase} {key_pair[0]} {key_pair[1]}", flush=True)
                continue
            body = row["body"]
        else:
            body = build_body(item["model_id"], prompt, item["data"], max_tokens)
            request_hash = sha_bytes(json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode())
            call_dir = WORK / "runs_v2" / phase / item["rater_id"] / item["batch_id"]
            call_dir.mkdir(parents=True, exist_ok=False)
            write_json(call_dir / "request_body.json", body)
            row = {"rater_id": item["rater_id"], "model_id_requested": item["model_id"], "batch_id": item["batch_id"], "input_sha256": item["input_sha256"], "request_sha256": request_hash, "attempts": [], "success": False, "body": body}
            manifest["calls"].append(row)
            by_key[key_pair] = row
            write_json(manifest_path, manifest)
            attempt_start = 1
        call_dir = WORK / "runs_v2" / phase / item["rater_id"] / item["batch_id"]
        for attempt_number in range(attempt_start, 4):
            attempt = {"attempt": attempt_number, "started_at_utc": now_utc()}
            response_path = call_dir / f"response_attempt_{attempt_number:02d}.json"
            try:
                response = openrouter_request(body, key)
                write_json(response_path, response)
                provider_error = response.get("error") if isinstance(response, dict) else None
                if isinstance(provider_error, dict):
                    attempt.update({"status": "provider_error", "code": provider_error.get("code"), "message": provider_error.get("message"), "response_sha256": sha_file(response_path)})
                    retryable = provider_error.get("code") in {408, 425, 429, 500, 502, 503, 504}
                else:
                    choice = response.get("choices", [{}])[0]
                    returned_model = response.get("model")
                    generation_id = response.get("id")
                    meta = {}
                    meta_error = None
                    if generation_id:
                        try:
                            meta = generation_info(generation_id, key)
                            write_json(call_dir / f"generation_{attempt_number:02d}.json", meta)
                        except Exception as err:
                            meta_error = type(err).__name__ + ": " + str(err)
                    usage = response.get("usage", {})
                    cost_value = meta.get("total_cost", usage.get("cost"))
                    cost = float(cost_value) if cost_value is not None else None
                    content = choice.get("message", {}).get("content")
                    attempt.update({"status": "response_received", "response_sha256": sha_file(response_path), "generation_id": generation_id, "model_returned": returned_model, "provider_name": meta.get("provider_name"), "usage": usage, "total_cost": cost, "generation_metadata_error": meta_error, "finish_reason": choice.get("finish_reason")})
                    if returned_model != item["model_id"]:
                        attempt.update({"status": "identity_mismatch", "error": f"requested {item['model_id']}; returned {returned_model}"})
                        retryable = False
                    elif cost is not None and cost != 0:
                        attempt.update({"status": "nonzero_cost", "error": "unexpected billed cost"})
                        retryable = False
                    elif not content:
                        attempt.update({"status": "empty_content"})
                        retryable = False
                    else:
                        try:
                            output = json.loads(content)
                            annotation_path = call_dir / f"annotation_attempt_{attempt_number:02d}.json"
                            write_json(annotation_path, output)
                            attempt.update({"status": "captured_json", "annotation_path": str(annotation_path.relative_to(WORK)), "annotation_sha256": sha_file(annotation_path)})
                            row.update({"success": True, "annotation_path": attempt["annotation_path"]})
                        except (json.JSONDecodeError, TypeError) as err:
                            attempt.update({"status": "invalid_json", "error": type(err).__name__ + ": " + str(err)})
                        retryable = False
                row["attempts"].append(attempt)
                write_json(manifest_path, manifest)
                print(json.dumps({"phase": phase, "rater": row["rater_id"], "batch": row["batch_id"], "attempt": attempt_number, "status": attempt["status"], "cost": attempt.get("total_cost")}), flush=True)
                if row.get("success") or attempt["status"] in {"identity_mismatch", "nonzero_cost"}:
                    break
                if not retryable or attempt_number == 3:
                    break
                time.sleep(10 * attempt_number)
            except urllib.error.HTTPError as err:
                body_text = err.read().decode("utf-8", "replace")
                write_json(call_dir / f"error_attempt_{attempt_number:02d}.json", {"http_status": err.code, "reason": err.reason, "response_body": body_text})
                attempt.update({"status": "http_error", "code": err.code, "reason": err.reason, "body_sha256": sha_bytes(body_text.encode())})
                row["attempts"].append(attempt)
                write_json(manifest_path, manifest)
                if err.code not in {408, 425, 429, 500, 502, 503, 504} or attempt_number == 3:
                    break
                time.sleep(10 * attempt_number)
            except Exception as err:
                attempt.update({"status": "transport_error", "error": type(err).__name__ + ": " + str(err)})
                row["attempts"].append(attempt)
                write_json(manifest_path, manifest)
                if attempt_number == 3:
                    break
                time.sleep(10 * attempt_number)


def run_primary() -> None:
    freeze = check_primary_freeze()
    prompt = (WORK / "AI_PRIMARY_PROMPT_V2.txt").read_text(encoding="utf-8").strip()
    schedule = []
    for rater in ("P1", "P2"):
        for index, batch_ref in enumerate(freeze["batches"], 1):
            schedule.append({"rater_id": rater, "model_id": MODELS[rater], "batch_id": f"batch_{index:02d}", "input_sha256": batch_ref["sha256"], "data": read_json(WORK / batch_ref["path"])})
    execute_requests(schedule, prompt, "primary", 12000)


def validate_primary_batch(cases: list[dict], output: dict) -> tuple[dict, list[str]]:
    errors = []
    results = output.get("cases") if isinstance(output, dict) else None
    if not isinstance(results, list) or len(results) != len(cases) or [r.get("case_id") if isinstance(r, dict) else None for r in results] != [c["case_id"] for c in cases]:
        return {}, ["missing cases array"]
    by_case = {row.get("case_id"): row for row in results if isinstance(row, dict)}
    normalized = {}
    for case in cases:
        case_id = case["case_id"]
        row = by_case.get(case_id)
        if row is None:
            errors.append(f"case omitted: {case_id}")
            normalized[case_id] = unknown_case(case)
            continue
        source_candidates = case["retrieved_candidates"]
        reviews = row.get("candidate_reviews")
        case_result = unknown_case(case)
        if isinstance(reviews, list):
            seen_indexes = set()
            for item in reviews:
                if not isinstance(item, dict):
                    continue
                index = item.get("candidate_index")
                if type(index) is not int or index < 0 or index >= len(source_candidates):
                    continue
                if index in seen_indexes:
                    case_result["candidate_reviews"][source_candidates[index]["doc_id"]] = unknown_case({"retrieved_candidates": [source_candidates[index]]})["candidate_reviews"][source_candidates[index]["doc_id"]]
                    errors.append(f"duplicate candidate index: {case_id}/{index}")
                    continue
                seen_indexes.add(index)
                candidate = source_candidates[index]
                label = item.get("label")
                indexes = item.get("paragraph_indexes")
                rationale = item.get("rationale")
                valid = label in CANDIDATE_LABELS and isinstance(indexes, list) and all(type(i) is int and 1 <= i <= paragraph_count(candidate.get("content", "")) for i in indexes) and isinstance(rationale, str) and 0 < len(rationale.split()) <= 8
                if label == "UNKNOWN":
                    valid = valid and indexes == []
                else:
                    valid = valid and len(indexes or []) > 0
                if valid:
                    case_result["candidate_reviews"][candidate["doc_id"]] = {"doc_id": candidate["doc_id"], "source": candidate.get("source"), "label": label, "paragraph_indexes": indexes, "rationale": rationale}
                else:
                    errors.append(f"invalid candidate review: {case_id}/{index}")
            if len(seen_indexes) != len(source_candidates):
                errors.append(f"candidate review coverage incomplete: {case_id}")
        else:
            errors.append(f"candidate_reviews missing: {case_id}")
        bundle = row.get("bundle_review")
        if isinstance(bundle, dict):
            label = bundle.get("label")
            supporting = bundle.get("supporting_candidate_indexes")
            conflicting = bundle.get("conflicting_candidate_indexes")
            rationale = bundle.get("rationale")
            valid_indexes = lambda values: isinstance(values, list) and all(type(i) is int and 0 <= i < len(source_candidates) for i in values)
            if label in BUNDLE_LABELS and valid_indexes(supporting) and valid_indexes(conflicting) and isinstance(rationale, str) and 0 < len(rationale.split()) <= 12:
                case_result["bundle_review"] = {"label": label, "supporting_doc_ids": [source_candidates[i]["doc_id"] for i in supporting], "conflicting_doc_ids": [source_candidates[i]["doc_id"] for i in conflicting], "rationale": rationale}
            else:
                errors.append(f"invalid bundle review: {case_id}")
        else:
            errors.append(f"bundle_review missing: {case_id}")
        normalized[case_id] = case_result
    return normalized, errors


def unknown_case(case: dict) -> dict:
    return {
        "candidate_reviews": {c["doc_id"]: {"doc_id": c["doc_id"], "source": c.get("source"), "label": "UNKNOWN", "paragraph_indexes": [], "rationale": "Review unavailable or invalid."} for c in case["retrieved_candidates"]},
        "bundle_review": {"label": "UNKNOWN", "supporting_doc_ids": [], "conflicting_doc_ids": [], "rationale": "Review unavailable or invalid."},
    }


def load_primary_reviews() -> tuple[dict, dict, dict]:
    freeze = check_primary_freeze()
    packet = verify_source()
    manifest_path = WORK / "primary_call_manifest_v2.json"
    manifest = read_json(manifest_path) if manifest_path.exists() else {"calls": []}
    call_map = {(c["rater_id"], c["batch_id"]): c for c in manifest["calls"]}
    all_reviews = {"P1": {}, "P2": {}}
    status = {}
    for rater in ("P1", "P2"):
        for index, batch in enumerate(freeze["batches"], 1):
            source_cases = read_json(WORK / batch["path"])["cases"]
            call = call_map.get((rater, f"batch_{index:02d}"))
            if call and call.get("success") and call.get("annotation_path"):
                output = read_json(WORK / call["annotation_path"])
                normalized, errors = validate_primary_batch(source_cases, output)
            else:
                normalized = {case["case_id"]: unknown_case(case) for case in source_cases}
                errors = ["no valid captured model output"]
            all_reviews[rater].update(normalized)
            status[f"{rater}/batch_{index:02d}"] = {"valid_response": bool(call and call.get("success")), "errors": errors, "cases": len(source_cases)}
        if len(all_reviews[rater]) != 120:
            raise RuntimeError(f"{rater} primary coverage is incomplete")
    return packet, all_reviews, status


def freeze_primary() -> None:
    packet, reviews, status = load_primary_reviews()
    target = WORK / "primary_annotation_freeze_v2.json"
    if target.exists():
        raise RuntimeError("primary annotation freeze already exists")
    summaries = {}
    for rater in ("P1", "P2"):
        candidate = [reviews[rater][case["case_id"]]["candidate_reviews"][doc["doc_id"]]["label"] for case in packet["cases"] for doc in case["retrieved_candidates"]]
        bundle = [reviews[rater][case["case_id"]]["bundle_review"]["label"] for case in packet["cases"]]
        summaries[rater] = {"model_id": MODELS[rater], "case_count": 120, "candidate_count": 947, "candidate_labels": dict(sorted(Counter(candidate).items())), "bundle_labels": dict(sorted(Counter(bundle).items()))}
    agreements = []
    disagreements = []
    candidate_votes = []
    bundle_votes = []
    for case in packet["cases"]:
        case_id = case["case_id"]
        for index, candidate in enumerate(case["retrieved_candidates"]):
            left = reviews["P1"][case_id]["candidate_reviews"][candidate["doc_id"]]
            right = reviews["P2"][case_id]["candidate_reviews"][candidate["doc_id"]]
            candidate_votes.append([left["label"], right["label"]])
            record = {"case_id": case_id, "candidate_index": index, "doc_id": candidate["doc_id"], "P1": left, "P2": right}
            (agreements if left["label"] == right["label"] else disagreements).append(record)
        left = reviews["P1"][case_id]["bundle_review"]
        right = reviews["P2"][case_id]["bundle_review"]
        bundle_votes.append([left["label"], right["label"]])
        if left["label"] != right["label"]:
            disagreements.append({"case_id": case_id, "bundle": True, "P1": left, "P2": right})
    summary = {
        "schema": "ragin.evidence_support_ai_primary_freeze.v2", "status": "PRIMARY_AI_REVIEWS_FROZEN",
        "source_packet_sha256": SOURCE_SHA, "primary_input_freeze_sha256": sha_file(WORK / "primary_input_freeze_v2.json"),
        "model_ids": {"P1": MODELS["P1"], "P2": MODELS["P2"]}, "primary_rater_summaries": summaries,
        "candidate_exact_agreement": sum(a == b for row in candidate_votes for a, b in [row]), "candidate_total": len(candidate_votes),
        "candidate_fleiss_kappa": fleiss_kappa(candidate_votes), "bundle_exact_agreement": sum(row[0] == row[1] for row in bundle_votes),
        "bundle_total": len(bundle_votes), "bundle_fleiss_kappa": fleiss_kappa(bundle_votes),
        "candidate_and_bundle_disagreements": disagreements, "batch_validation": status,
        "reviews_by_rater": reviews, "frozen_at_utc": now_utc(),
    }
    write_json(target, summary)
    write_json(WORK / "primary_freeze_manifest_v2.json", {"primary_freeze_sha256": sha_file(target), "call_manifest_sha256": sha_file(WORK / "primary_call_manifest_v2.json"), "input_freeze_sha256": sha_file(WORK / "primary_input_freeze_v2.json"), "protocol_sha256": sha_file(WORK / "AI_REFERENCE_PROTOCOL_V2.md"), "primary_prompt_sha256": sha_file(WORK / "AI_PRIMARY_PROMPT_V2.txt"), "source_packet_sha256": SOURCE_SHA, "frozen_at_utc": now_utc()})
    print(json.dumps({"primary_frozen": True, "candidate_exact_agreement": summary["candidate_exact_agreement"], "candidate_total": summary["candidate_total"], "candidate_kappa": summary["candidate_fleiss_kappa"], "bundle_exact_agreement": summary["bundle_exact_agreement"], "bundle_total": summary["bundle_total"], "bundle_kappa": summary["bundle_fleiss_kappa"], "disagreement_fields": len(disagreements), "freeze_sha256": sha_file(target)}, indent=2))


def fleiss_kappa(rows: list[list[str]]) -> float | None:
    if not rows or len(rows[0]) < 2:
        return None
    labels = sorted({value for row in rows for value in row})
    n = len(rows[0])
    counts = [[row.count(label) for label in labels] for row in rows]
    p_i = [(sum(v * v for v in row) - n) / (n * (n - 1)) for row in counts]
    p_bar = sum(p_i) / len(p_i)
    p = [sum(row[i] for row in counts) / (len(counts) * n) for i in range(len(labels))]
    p_e = sum(x * x for x in p)
    return (p_bar - p_e) / (1 - p_e) if p_e != 1 else None


def prepare_adjudication() -> None:
    primary_path = WORK / "primary_annotation_freeze_v2.json"
    primary_manifest_path = WORK / "primary_freeze_manifest_v2.json"
    if not primary_path.exists() or not primary_manifest_path.exists():
        raise RuntimeError("primary AI freeze must exist before preparing adjudication")
    primary = read_json(primary_path)
    p_manifest = read_json(primary_manifest_path)
    if sha_file(primary_path) != p_manifest["primary_freeze_sha256"]:
        raise RuntimeError("primary freeze hash mismatch")
    packet = verify_source()
    target = WORK / "adjudication_input_freeze_v2.json"
    if target.exists():
        raise RuntimeError("adjudication input freeze already exists")
    disagreements = primary["candidate_and_bundle_disagreements"]
    cases_by_id = {case["case_id"]: strip_case(case) for case in packet["cases"]}
    disputed_by_case = {}
    for item in disagreements:
        case_id = item["case_id"]
        case = disputed_by_case.setdefault(case_id, {"case": cases_by_id[case_id], "candidate_disagreements": [], "bundle_disagreement": None})
        if item.get("bundle"):
            case["bundle_disagreement"] = {"P1": item["P1"], "P2": item["P2"]}
        else:
            case["candidate_disagreements"].append({"candidate_index": item["candidate_index"], "doc_id": item["doc_id"], "P1": item["P1"], "P2": item["P2"]})
    groups = []
    for batch_number in range(6):
        case_ids = [c["case_id"] for c in packet["cases"][batch_number * 20 : (batch_number + 1) * 20]]
        cases = [disputed_by_case[cid] for cid in case_ids if cid in disputed_by_case]
        rel = pathlib.Path("adjudication_inputs") / f"batch_{batch_number + 1:02d}.json"
        path = WORK / rel
        write_json(path, {"cases": cases})
        groups.append({"batch_id": f"batch_{batch_number + 1:02d}", "path": rel.as_posix(), "sha256": sha_file(path), "case_ids": [c["case"]["case_id"] for c in cases], "candidate_disputes": sum(len(c["candidate_disagreements"]) for c in cases), "bundle_disputes": sum(c["bundle_disagreement"] is not None for c in cases)})
    freeze = {"schema": "ragin.evidence_support_ai_adjudication_input_freeze.v2", "frozen_at_utc": now_utc(), "source_packet_sha256": SOURCE_SHA, "primary_freeze_sha256": sha_file(primary_path), "adjudication_prompt_sha256": sha_file(WORK / "AI_ADJUDICATION_PROMPT_V2.txt"), "adjudicator_model_id": MODELS["A1"], "disagreement_rule": "all differing P1/P2 labels, including one-sided UNKNOWN; exact agreements are omitted", "batches": groups, "case_count": len(disputed_by_case), "candidate_disagreement_count": sum(len(c["candidate_disagreements"]) for c in disputed_by_case.values()), "bundle_disagreement_count": sum(c["bundle_disagreement"] is not None for c in disputed_by_case.values()), "runner_sha256": sha_file(pathlib.Path(__file__))}
    write_json(target, freeze)
    print(json.dumps({"adjudication_cases": freeze["case_count"], "candidate_disputes": freeze["candidate_disagreement_count"], "bundle_disputes": freeze["bundle_disagreement_count"], "adjudication_input_freeze_sha256": sha_file(target)}, indent=2))


def run_adjudication() -> None:
    if not (WORK / "adjudication_input_freeze_v2.json").exists():
        raise RuntimeError("adjudication inputs must be frozen first")
    freeze = read_json(WORK / "adjudication_input_freeze_v2.json")
    if freeze.get("runner_sha256") != sha_file(pathlib.Path(__file__)):
        raise RuntimeError("adjudication runner hash changed")
    if freeze.get("adjudication_prompt_sha256") != sha_file(WORK / "AI_ADJUDICATION_PROMPT_V2.txt"):
        raise RuntimeError("adjudication prompt changed")
    prompt = (WORK / "AI_ADJUDICATION_PROMPT_V2.txt").read_text(encoding="utf-8").strip()
    schedule = []
    for batch in freeze["batches"]:
        data = read_json(WORK / batch["path"])
        if not data["cases"]:
            continue
        schedule.append({"rater_id": "A1", "model_id": MODELS["A1"], "batch_id": batch["batch_id"], "input_sha256": batch["sha256"], "data": data})
    execute_requests(schedule, prompt, "adjudication", 12000)


def load_adjudication() -> dict:
    freeze = read_json(WORK / "adjudication_input_freeze_v2.json")
    manifest_path = WORK / "adjudication_call_manifest_v2.json"
    manifest = read_json(manifest_path) if manifest_path.exists() else {"calls": []}
    calls = {(c["rater_id"], c["batch_id"]): c for c in manifest["calls"]}
    results = {}
    status = {}
    for batch in freeze["batches"]:
        cases = read_json(WORK / batch["path"])["cases"]
        if not cases:
            continue
        call = calls.get(("A1", batch["batch_id"]))
        batch_results = {}
        errors = []
        if call and call.get("success"):
            output = read_json(WORK / call["annotation_path"])
            rows = output.get("cases", []) if isinstance(output, dict) else []
            by_id = {c.get("case_id"): c for c in rows if isinstance(c, dict)}
            for disputed in cases:
                case_id = disputed["case"]["case_id"]
                row = by_id.get(case_id, {})
                resolved = {"candidate_decisions": {}, "bundle_decision": None}
                source_candidates = disputed["case"]["retrieved_candidates"]
                for dec in row.get("candidate_decisions", []):
                    i = dec.get("candidate_index")
                    if type(i) is not int or i < 0 or i >= len(source_candidates):
                        continue
                    candidate = source_candidates[i]
                    indexes = dec.get("paragraph_indexes")
                    label = dec.get("label")
                    valid = label in CANDIDATE_LABELS and isinstance(indexes, list) and all(type(x) is int and 1 <= x <= paragraph_count(candidate.get("content", "")) for x in indexes) and isinstance(dec.get("rationale"), str) and 0 < len(dec["rationale"].split()) <= 8
                    if label == "UNKNOWN":
                        valid = valid and indexes == []
                    else:
                        valid = valid and bool(indexes)
                    if valid:
                        resolved["candidate_decisions"][i] = {"label": label, "paragraph_indexes": indexes, "rationale": dec["rationale"]}
                bundle = row.get("bundle_decision")
                if isinstance(bundle, dict) and bundle.get("label") in BUNDLE_LABELS and isinstance(bundle.get("rationale"), str) and 0 < len(bundle["rationale"].split()) <= 12:
                    si = bundle.get("supporting_candidate_indexes", [])
                    ci = bundle.get("conflicting_candidate_indexes", [])
                    if isinstance(si, list) and isinstance(ci, list) and all(type(x) is int and 0 <= x < len(source_candidates) for x in si + ci):
                        resolved["bundle_decision"] = {"label": bundle["label"], "supporting_doc_ids": [source_candidates[x]["doc_id"] for x in si], "conflicting_doc_ids": [source_candidates[x]["doc_id"] for x in ci], "rationale": bundle["rationale"]}
                batch_results[case_id] = resolved
        else:
            errors.append("adjudicator response missing or invalid")
            for disputed in cases:
                batch_results[disputed["case"]["case_id"]] = {"candidate_decisions": {}, "bundle_decision": None}
        results.update(batch_results)
        status[batch["batch_id"]] = {"disputed_cases": len(cases), "valid_case_outputs": sum(bool(v["candidate_decisions"] or v["bundle_decision"]) for v in batch_results.values()), "errors": errors}
    return results, status


def freeze_reference() -> None:
    packet = verify_source()
    primary_path = WORK / "primary_annotation_freeze_v2.json"
    adjudication_input_path = WORK / "adjudication_input_freeze_v2.json"
    if not primary_path.exists() or not adjudication_input_path.exists():
        raise RuntimeError("primary and adjudication input freezes are required")
    primary_manifest = read_json(WORK / "primary_freeze_manifest_v2.json")
    if sha_file(primary_path) != primary_manifest["primary_freeze_sha256"]:
        raise RuntimeError("primary reference changed after freeze")
    adjudication = read_json(adjudication_input_path)
    adju_results, adju_status = load_adjudication()
    primary = read_json(primary_path)
    p_reviews = primary["reviews_by_rater"]
    cases_out = []
    cand_counts = Counter()
    bundle_counts = Counter()
    candidate_disagreements = 0
    candidate_adjudicated = 0
    bundle_disagreements = 0
    bundle_adjudicated = 0
    for case in packet["cases"]:
        case_id = case["case_id"]
        out_case = {"case_id": case_id, "candidate_reviews": [], "bundle_review": {}}
        for i, source_candidate in enumerate(case["retrieved_candidates"]):
            doc_id = source_candidate["doc_id"]
            p1 = p_reviews["P1"][case_id]["candidate_reviews"][doc_id]
            p2 = p_reviews["P2"][case_id]["candidate_reviews"][doc_id]
            adju = adju_results.get(case_id, {}).get("candidate_decisions", {}).get(i)
            if p1["label"] == p2["label"]:
                label = p1["label"]
                citations = [{"rater_id": "P1", **{k: p1.get(k) for k in ("source", "paragraph_indexes", "rationale")}}, {"rater_id": "P2", **{k: p2.get(k) for k in ("source", "paragraph_indexes", "rationale")}}]
            else:
                candidate_disagreements += 1
                if adju:
                    label = adju["label"]
                    candidate_adjudicated += label != "UNKNOWN"
                    citations = [{"rater_id": "P1", "source": p1.get("source"), "paragraph_indexes": p1.get("paragraph_indexes", []), "rationale": p1.get("rationale")}, {"rater_id": "P2", "source": p2.get("source"), "paragraph_indexes": p2.get("paragraph_indexes", []), "rationale": p2.get("rationale")}, {"rater_id": "A1", "source": source_candidate.get("source"), "paragraph_indexes": adju.get("paragraph_indexes", []), "rationale": adju.get("rationale")}]
                else:
                    label = "UNKNOWN"
                    citations = [{"rater_id": "P1", "source": p1.get("source"), "paragraph_indexes": p1.get("paragraph_indexes", []), "rationale": p1.get("rationale")}, {"rater_id": "P2", "source": p2.get("source"), "paragraph_indexes": p2.get("paragraph_indexes", []), "rationale": p2.get("rationale")}, {"rater_id": "A1", "label": "UNKNOWN", "reason": "No valid adjudicator decision."}]
            cand_counts[label] += 1
            out_case["candidate_reviews"].append({"doc_id": doc_id, "source": source_candidate.get("source"), "label": label, "primary_labels": {"P1": p1["label"], "P2": p2["label"]}, "adjudicator_label": adju.get("label") if adju else None, "citations_and_rationales": citations})
        p1b = p_reviews["P1"][case_id]["bundle_review"]
        p2b = p_reviews["P2"][case_id]["bundle_review"]
        adju_bundle = adju_results.get(case_id, {}).get("bundle_decision")
        if p1b["label"] == p2b["label"]:
            bundle_label = p1b["label"]
            bundle_citations = [{"rater_id": "P1", **p1b}, {"rater_id": "P2", **p2b}]
        else:
            bundle_disagreements += 1
            if adju_bundle:
                bundle_label = adju_bundle["label"]
                bundle_adjudicated += bundle_label != "UNKNOWN"
                bundle_citations = [{"rater_id": "P1", **p1b}, {"rater_id": "P2", **p2b}, {"rater_id": "A1", **adju_bundle}]
            else:
                bundle_label = "UNKNOWN"
                bundle_citations = [{"rater_id": "P1", **p1b}, {"rater_id": "P2", **p2b}, {"rater_id": "A1", "label": "UNKNOWN", "reason": "No valid adjudicator decision."}]
        bundle_counts[bundle_label] += 1
        out_case["bundle_review"] = {"label": bundle_label, "primary_labels": {"P1": p1b["label"], "P2": p2b["label"]}, "adjudicator_label": adju_bundle.get("label") if adju_bundle else None, "citations_and_rationales": bundle_citations}
        cases_out.append(out_case)
    target = WORK / "reference_freeze_v2.json"
    if target.exists():
        raise RuntimeError("reference freeze already exists")
    candidate_total = sum(len(c["retrieved_candidates"]) for c in packet["cases"])
    reference = {
        "schema": "ragin.evidence_support_ai_derived_reference.v2", "status": "AI_DERIVED_REFERENCE_FROZEN",
        "reference_type": "AI_DERIVED_TWO_PRIMARY_PLUS_AI_ADJUDICATION",
        "human_ground_truth": False, "independent_consensus_claim": False,
        "source_packet_sha256": SOURCE_SHA, "primary_freeze_sha256": sha_file(primary_path),
        "adjudication_input_freeze_sha256": sha_file(adjudication_input_path),
        "model_ids": MODELS, "case_count": len(cases_out), "candidate_count": candidate_total,
        "candidate_label_counts": dict(sorted(cand_counts.items())), "bundle_label_counts": dict(sorted(bundle_counts.items())),
        "candidate_unknown_count": cand_counts["UNKNOWN"], "bundle_unknown_count": bundle_counts["UNKNOWN"],
        "candidate_primary_disagreement_count": candidate_disagreements, "candidate_adjudicated_resolved_count": candidate_adjudicated,
        "bundle_primary_disagreement_count": bundle_disagreements, "bundle_adjudicated_resolved_count": bundle_adjudicated,
        "primary_candidate_exact_agreement": primary["candidate_exact_agreement"], "primary_candidate_agreement_total": primary["candidate_total"],
        "primary_candidate_fleiss_kappa": primary["candidate_fleiss_kappa"], "primary_bundle_exact_agreement": primary["bundle_exact_agreement"],
        "primary_bundle_agreement_total": primary["bundle_total"], "primary_bundle_fleiss_kappa": primary["bundle_fleiss_kappa"],
        "adjudication_batch_status": adju_status, "cases": cases_out, "frozen_at_utc": now_utc(),
    }
    write_json(target, reference)
    write_json(WORK / "reference_freeze_manifest_v2.json", {
        "schema": "ragin.evidence_support_ai_reference_freeze_manifest.v2", "reference_sha256": sha_file(target),
        "primary_freeze_sha256": sha_file(primary_path), "primary_call_manifest_sha256": sha_file(WORK / "primary_call_manifest_v2.json"),
        "adjudication_input_freeze_sha256": sha_file(adjudication_input_path),
        "adjudication_call_manifest_sha256": sha_file(WORK / "adjudication_call_manifest_v2.json") if (WORK / "adjudication_call_manifest_v2.json").exists() else None,
        "source_packet_sha256": SOURCE_SHA, "frozen_at_utc": now_utc(),
    })
    print(json.dumps({"reference_frozen": True, "cases": len(cases_out), "candidates": candidate_total, "candidate_labels": reference["candidate_label_counts"], "bundle_labels": reference["bundle_label_counts"], "candidate_disagreements": candidate_disagreements, "candidate_adjudicated_resolved": candidate_adjudicated, "bundle_disagreements": bundle_disagreements, "bundle_adjudicated_resolved": bundle_adjudicated, "reference_sha256": sha_file(target)}, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=["prepare", "run-primary", "freeze-primary", "prepare-adjudication", "run-adjudication", "freeze-reference"])
    phase = parser.parse_args().phase
    actions = {"prepare": prepare, "run-primary": run_primary, "freeze-primary": freeze_primary, "prepare-adjudication": prepare_adjudication, "run-adjudication": run_adjudication, "freeze-reference": freeze_reference}
    try:
        actions[phase]()
        return 0
    except Exception as err:
        print(f"BLOCKED: {type(err).__name__}: {err}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
