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
WORK = BASE / "ai_reference_v1"
PACKET = BASE / "blinded_reference_packet.json"
PROTOCOL = WORK / "AI_REFERENCE_PROTOCOL_V1.md"
PROMPT = WORK / "AI_ANNOTATION_PROMPT_V1.txt"
CATALOG = WORK / "model_catalog_freeze_v1.json"
FREEZE_INPUTS = WORK / "annotation_input_freeze_v1.json"
SOURCE_SHA = "975f24fca75b0deb8d930252294ddf729eff850d715f87dc8bcac0706c4aacb5"
SOURCE_PROTOCOL_SHA = "fa5a7908b8d131b3db2a32b0330ab1713beda10008aa6760e50843804837d5b4"
RATERS = [
    ("AI-R1", "nvidia/nemotron-3-ultra-550b-a55b:free"),
    ("AI-R2", "thinkingmachines/inkling:free"),
    ("AI-R3", "dots-studio/dots-3-note-preview:free"),
]
CANDIDATE_LABELS = {"DIRECT_SUPPORT", "PARTIAL", "IRRELEVANT", "CONTRADICTORY", "UNKNOWN"}
BUNDLE_LABELS = {"SUFFICIENT", "INSUFFICIENT", "CONFLICTING", "UNKNOWN"}


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest_file(path: pathlib.Path) -> str:
    return digest_bytes(path.read_bytes())


def write_json(path: pathlib.Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def verify_frozen_source() -> dict:
    if pathlib.Path.cwd().resolve() != ROOT.resolve():
        raise RuntimeError(f"wrong workspace: {pathlib.Path.cwd()}")
    if digest_file(PACKET) != SOURCE_SHA:
        raise RuntimeError("blinded reference packet hash mismatch")
    source_protocol = json.loads((BASE / "protocol_freeze.json").read_text(encoding="utf-8"))
    if digest_file(BASE / "protocol_freeze.json") != SOURCE_PROTOCOL_SHA:
        raise RuntimeError("original Evidence Judge protocol hash mismatch")
    if source_protocol.get("reference_status") != "REFERENCE_UNAVAILABLE":
        raise RuntimeError("source reference status is not the expected pending state")
    packet = json.loads(PACKET.read_text(encoding="utf-8"))
    if packet.get("decisions_omitted") is not True:
        raise RuntimeError("packet does not attest omission of decisions")
    if packet.get("judge_outputs_omitted") is not True or packet.get("gate_outputs_omitted") is not True:
        raise RuntimeError("packet is not blind to Judge/Gate outputs")
    cases = packet.get("cases")
    if not isinstance(cases, list) or len(cases) != 120:
        raise RuntimeError("expected exactly 120 packet cases")
    if len({c.get("case_id") for c in cases}) != 120:
        raise RuntimeError("case IDs are missing or duplicated")
    if sum(len(c.get("retrieved_candidates", [])) for c in cases) != 947:
        raise RuntimeError("candidate count differs from frozen cohort")
    return packet


def stripped_case(case: dict) -> dict:
    return {
        "case_id": case["case_id"],
        "observed_command": case.get("observed_command", ""),
        "available_context": case.get("available_context", ""),
        "behavioral_claim": case.get("behavioral_claim", ""),
        "retrieved_candidates": [
            {
                "doc_id": candidate["doc_id"],
                "source": candidate.get("source", ""),
                "title": candidate.get("title", ""),
                "content": candidate.get("content", ""),
                "source_version": candidate.get("source_version", ""),
                "provenance_hash": candidate.get("provenance_hash", ""),
            }
            for candidate in case.get("retrieved_candidates", [])
        ],
    }


def prepare() -> None:
    packet = verify_frozen_source()
    if FREEZE_INPUTS.exists() or (WORK / "reference_freeze_v1.json").exists():
        raise RuntimeError("refusing to overwrite an existing freeze")
    cases = [stripped_case(case) for case in packet["cases"]]
    batches = []
    for batch_index in range(4):
        batch_cases = cases[batch_index * 30 : (batch_index + 1) * 30]
        rel = pathlib.Path("inputs") / f"batch_{batch_index + 1:02d}.json"
        batch_path = WORK / rel
        if batch_path.exists():
            raise RuntimeError(f"refusing to overwrite existing batch: {batch_path}")
        write_json(batch_path, {"cases": batch_cases})
        batches.append(
            {
                "path": rel.as_posix(),
                "sha256": digest_file(batch_path),
                "case_count": len(batch_cases),
                "candidate_count": sum(len(c["retrieved_candidates"]) for c in batch_cases),
                "case_ids": [c["case_id"] for c in batch_cases],
            }
        )
    freeze = {
        "schema": "ragin.evidence_support_ai_annotation_input_freeze.v1",
        "frozen_at_utc": now_utc(),
        "source_packet_path": str(PACKET.relative_to(ROOT)),
        "source_packet_sha256": SOURCE_SHA,
        "source_protocol_sha256": SOURCE_PROTOCOL_SHA,
        "annotation_protocol_sha256": digest_file(PROTOCOL),
        "annotation_prompt_sha256": digest_file(PROMPT),
        "model_catalog_sha256": digest_file(CATALOG),
        "rater_models": [{"rater_id": rater, "model_id": model} for rater, model in RATERS],
        "case_count": len(cases),
        "candidate_count": sum(len(c["retrieved_candidates"]) for c in cases),
        "batch_policy": "packet order, four consecutive batches of 30 cases",
        "batches": batches,
        "blinding_fields_excluded": [
            "source_group_id", "input_sha256", "context_sha256", "candidate review slots",
            "bundle review slots", "Judge outputs", "Gate outputs", "matched arm outcomes",
            "descriptive analysis summaries",
        ],
    }
    write_json(FREEZE_INPUTS, freeze)
    print(json.dumps({"prepared": True, "case_count": len(cases), "candidate_count": freeze["candidate_count"], "batch_count": len(batches), "input_freeze_sha256": digest_file(FREEZE_INPUTS)}, indent=2))


def read_freeze() -> tuple[dict, dict]:
    packet = verify_frozen_source()
    freeze = json.loads(FREEZE_INPUTS.read_text(encoding="utf-8"))
    for path, expected in [
        (PROTOCOL, freeze["annotation_protocol_sha256"]),
        (PROMPT, freeze["annotation_prompt_sha256"]),
        (CATALOG, freeze["model_catalog_sha256"]),
    ]:
        if digest_file(path) != expected:
            raise RuntimeError(f"frozen protocol input changed: {path}")
    for batch in freeze["batches"]:
        path = WORK / batch["path"]
        if digest_file(path) != batch["sha256"]:
            raise RuntimeError(f"frozen annotation batch changed: {path}")
    return freeze, packet


def request_body(model: str, prompt: str, batch: dict) -> dict:
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": "BLINDED_INPUT_JSON:\n" + json.dumps(batch, ensure_ascii=False, separators=(",", ":"))},
        ],
        "temperature": 0,
        "max_tokens": 32768,
        "provider": {"allow_fallbacks": False, "require_parameters": True},
    }


def openrouter_post(body: dict, key: str) -> dict:
    raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=raw,
        method="POST",
        headers={
            "Authorization": f"Bearer {key}", "Content-Type": "application/json",
            "HTTP-Referer": "https://localhost/ragin-research-artifact",
            "X-OpenRouter-Title": "RAGIN AI Evidence Support Reference V1",
        },
    )
    with urllib.request.urlopen(request, timeout=600) as response:
        return json.loads(response.read())


def generation_metadata(generation_id: str, key: str) -> dict:
    url = "https://openrouter.ai/api/v1/generation?id=" + urllib.parse.quote(generation_id)
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {key}", "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read()).get("data", {})


def call_cost(metadata: dict, usage: dict) -> float | None:
    value = metadata.get("total_cost", usage.get("cost"))
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def run_calls() -> None:
    freeze, _ = read_freeze()
    amendment_path = WORK / "annotation_run_amendment_v2.json"
    if not amendment_path.exists():
        raise RuntimeError("current annotation run amendment is required before model calls")
    amendment = json.loads(amendment_path.read_text(encoding="utf-8"))
    if amendment.get("runner_sha256") != digest_file(pathlib.Path(__file__)):
        raise RuntimeError("runner differs from the pre-resume amendment hash")
    if amendment.get("input_freeze_sha256") != digest_file(FREEZE_INPUTS):
        raise RuntimeError("amendment refers to another annotation input freeze")
    if amendment.get("prior_amendment_sha256") != digest_file(WORK / "annotation_run_amendment_v1.json"):
        raise RuntimeError("runner amendment chain does not match")
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY is not set")
    prompt = PROMPT.read_text(encoding="utf-8").strip()
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    if {m["model_id"] for m in catalog["models"]} != {model for _, model in RATERS}:
        raise RuntimeError("catalog model list differs from frozen rater identities")
    call_manifest_path = WORK / "call_manifest_v1.json"
    call_manifest = json.loads(call_manifest_path.read_text(encoding="utf-8")) if call_manifest_path.exists() else {"schema": "ragin.evidence_support_ai_call_manifest.v1", "calls": []}
    prior = {}
    for row in call_manifest["calls"]:
        prior[(row["rater_id"], row["batch_index"])] = row
    for row in call_manifest["calls"]:
        for attempt in row.get("attempts", []):
            if attempt.get("status") == "empty_content" and attempt.get("response_path"):
                response_path = WORK / attempt["response_path"]
                if response_path.exists():
                    response = json.loads(response_path.read_text(encoding="utf-8"))
                    provider_error = response.get("error") if isinstance(response, dict) else None
                    if isinstance(provider_error, dict):
                        attempt["status_before_reclassification"] = "empty_content"
                        attempt["status"] = "provider_error"
                        attempt["provider_error_code"] = provider_error.get("code")
                        attempt["provider_error_message"] = provider_error.get("message")
    write_json(call_manifest_path, call_manifest)
    for rater_id, model in RATERS:
        for batch_index, batch_ref in enumerate(freeze["batches"], 1):
            key_pair = (rater_id, batch_index)
            batch = json.loads((WORK / batch_ref["path"]).read_text(encoding="utf-8"))
            body = request_body(model, prompt, batch)
            body_bytes = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode()
            call_dir = WORK / "runs" / rater_id / f"batch_{batch_index:02d}"
            if key_pair in prior and prior[key_pair].get("success"):
                print(f"PRESERVED {rater_id} batch {batch_index}: prior success", flush=True)
                continue
            if call_dir.exists() and key_pair not in prior:
                request_path = call_dir / "request_body.json"
                recorded_body = json.loads(request_path.read_text(encoding="utf-8")) if request_path.exists() else None
                recorded_hash = digest_bytes(json.dumps(recorded_body, ensure_ascii=False, separators=(",", ":")).encode()) if recorded_body is not None else None
                if recorded_hash != digest_bytes(body_bytes):
                    raise RuntimeError(f"orphan attempt request does not match frozen bytes: {call_dir}")
                row = {
                    "rater_id": rater_id, "model_id_requested": model, "batch_index": batch_index,
                    "batch_sha256": batch_ref["sha256"], "request_body_sha256": digest_bytes(body_bytes),
                    "started_at_utc": "INTERRUPTED_REQUEST_START_TIME_NOT_CAPTURED", "attempts": [
                        {"attempt": 1, "status": "transport_interrupted", "request_was_sent": True, "response_captured": False, "recorded_at_utc": now_utc()}
                    ], "success": False,
                }
                call_manifest["calls"].append(row)
                prior[key_pair] = row
                write_json(call_manifest_path, call_manifest)
            elif key_pair in prior:
                row = prior[key_pair]
                req_path = call_dir / "request_body.json"
                recorded_body = json.loads(req_path.read_text(encoding="utf-8"))
                recorded_hash = digest_bytes(json.dumps(recorded_body, ensure_ascii=False, separators=(",", ":")).encode())
                if recorded_hash != digest_bytes(body_bytes):
                    raise RuntimeError(f"retry request differs from recorded bytes: {call_dir}")
            else:
                call_dir.mkdir(parents=True)
                write_json(call_dir / "request_body.json", body)
                row = {
                    "rater_id": rater_id, "model_id_requested": model, "batch_index": batch_index,
                    "batch_sha256": batch_ref["sha256"], "request_body_sha256": digest_bytes(body_bytes),
                    "started_at_utc": now_utc(), "attempts": [], "success": False,
                }
                call_manifest["calls"].append(row)
                prior[key_pair] = row
                write_json(call_manifest_path, call_manifest)
            if len(row.get("attempts", [])) >= 3:
                print(f"PRESERVED exhausted attempts {rater_id} batch {batch_index}", flush=True)
                continue
            for attempt_index in range(len(row.get("attempts", [])) + 1, 4):
                attempt = {"attempt": attempt_index, "started_at_utc": now_utc()}
                try:
                    response = openrouter_post(body, key)
                    response_path = call_dir / f"response_attempt_{attempt_index:02d}.json"
                    write_json(response_path, response)
                    provider_error = response.get("error") if isinstance(response, dict) else None
                    if isinstance(provider_error, dict):
                        attempt.update({
                            "status": "provider_error", "provider_error_code": provider_error.get("code"),
                            "provider_error_message": provider_error.get("message"),
                            "response_path": str(response_path.relative_to(WORK)),
                            "response_sha256": digest_file(response_path),
                        })
                        row["attempts"].append(attempt)
                        if provider_error.get("code") not in {408, 425, 429, 500, 502, 503, 504} or attempt_index == 3:
                            break
                        time.sleep(10 * attempt_index)
                        continue
                    choice = response.get("choices", [{}])[0]
                    usage = response.get("usage", {})
                    actual_model = response.get("model")
                    generation_id = response.get("id")
                    metadata = {}
                    metadata_error = None
                    if generation_id:
                        try:
                            metadata = generation_metadata(generation_id, key)
                            write_json(call_dir / f"generation_metadata_{attempt_index:02d}.json", metadata)
                        except Exception as error:
                            metadata_error = type(error).__name__ + ": " + str(error)
                    content = choice.get("message", {}).get("content")
                    cost = call_cost(metadata, usage)
                    attempt.update({
                        "status": "response_received", "generation_id": generation_id,
                        "model_returned": actual_model, "provider_name": metadata.get("provider_name"),
                        "finish_reason": choice.get("finish_reason"), "usage": usage,
                        "total_cost": cost, "generation_metadata_error": metadata_error,
                        "response_path": str(response_path.relative_to(WORK)),
                        "response_sha256": digest_file(response_path),
                    })
                    if not content:
                        attempt["status"] = "empty_content"
                    elif actual_model != model:
                        attempt.update({"status": "model_identity_mismatch", "error": f"requested {model}; returned {actual_model}"})
                    elif cost is None:
                        attempt.update({"status": "cost_unverified", "error": "generation endpoint did not report actual cost"})
                    elif cost != 0:
                        attempt.update({"status": "nonzero_cost_stop", "error": "actual cost was nonzero"})
                    else:
                        try:
                            parsed = json.loads(content)
                            annotation_path = call_dir / "annotation.json"
                            write_json(annotation_path, parsed)
                            attempt["annotation_path"] = str(annotation_path.relative_to(WORK))
                            attempt["annotation_sha256"] = digest_file(annotation_path)
                            attempt["status"] = "captured_json"
                            row["success"] = True
                            row["response_path"] = attempt["response_path"]
                            row["annotation_path"] = attempt["annotation_path"]
                        except (json.JSONDecodeError, TypeError) as error:
                            attempt.update({"status": "schema_parse_error", "error": type(error).__name__ + ": " + str(error)})
                    row["attempts"].append(attempt)
                    if row["success"] or attempt["status"] in {"model_identity_mismatch", "cost_unverified", "nonzero_cost_stop", "empty_content", "schema_parse_error"}:
                        break
                except urllib.error.HTTPError as error:
                    message = error.read().decode("utf-8", "replace")
                    error_path = call_dir / f"error_attempt_{attempt_index:02d}.json"
                    write_json(error_path, {"status": error.code, "reason": error.reason, "body": message})
                    attempt.update({"status": "http_error", "http_status": error.code, "reason": error.reason, "body_sha256": digest_bytes(message.encode())})
                    row["attempts"].append(attempt)
                    if error.code not in {408, 425, 429, 500, 502, 503, 504} or attempt_index == 3:
                        break
                    time.sleep(10 * attempt_index)
                except Exception as error:
                    attempt.update({"status": "transport_error", "error": type(error).__name__ + ": " + str(error)})
                    row["attempts"].append(attempt)
                    if attempt_index < 3:
                        time.sleep(10 * attempt_index)
            row["completed_at_utc"] = now_utc()
            write_json(call_manifest_path, call_manifest)
            prior[key_pair] = row
            status = row["attempts"][-1].get("status") if row["attempts"] else "no_response"
            print(json.dumps({"rater": rater_id, "batch": batch_index, "success": row["success"], "attempts": len(row["attempts"]), "status": status}), flush=True)
            if status in {"model_identity_mismatch", "cost_unverified", "nonzero_cost_stop"}:
                raise RuntimeError("identity or cost gate failed; remaining calls stopped")
    print(json.dumps({"scheduled_calls": 12, "successful_calls": sum(bool(x.get("success")) for x in call_manifest["calls"]), "manifest": str(call_manifest_path.relative_to(ROOT))}, indent=2))


def paragraph_count(content: str) -> int:
    return len([p for p in re.split(r"\n\s*\n", content.strip()) if p.strip()]) if content.strip() else 0


def validated_batch(call_dir: pathlib.Path, cases: list[dict]) -> tuple[dict | None, list[str]]:
    path = call_dir / "annotation.json"
    if not path.exists():
        return None, ["annotation output missing"]
    try:
        output = json.loads(path.read_text(encoding="utf-8"))
    except Exception as error:
        return None, ["annotation output unreadable: " + str(error)]
    results = output.get("cases") if isinstance(output, dict) else None
    if not isinstance(results, list) or len(results) != len(cases):
        return None, ["case count/schema mismatch"]
    normalized = {}
    errors = []
    for source_case, result in zip(cases, results):
        case_id = source_case["case_id"]
        if not isinstance(result, dict) or result.get("case_id") != case_id or case_id in normalized:
            errors.append(f"case identity/order mismatch: {case_id}")
            continue
        source_candidates = source_case["retrieved_candidates"]
        reviews = result.get("candidate_reviews")
        bundle = result.get("bundle_review")
        if not isinstance(reviews, list) or len(reviews) != len(source_candidates) or not isinstance(bundle, dict):
            errors.append(f"candidate/bundle schema mismatch: {case_id}")
            continue
        candidate_by_id = {c["doc_id"]: c for c in source_candidates}
        case_reviews = {}
        for candidate, review in zip(source_candidates, reviews):
            doc_id = candidate["doc_id"]
            if not isinstance(review, dict):
                errors.append(f"candidate review is not an object: {case_id}/{doc_id}")
                continue
            label = review.get("label")
            indexes = review.get("paragraph_indexes")
            if review.get("doc_id") != doc_id or label not in CANDIDATE_LABELS:
                errors.append(f"candidate identity/label invalid: {case_id}/{doc_id}")
                continue
            if not isinstance(review.get("rationale"), str) or not review["rationale"].strip():
                errors.append(f"candidate rationale missing: {case_id}/{doc_id}")
                continue
            if not isinstance(indexes, list) or any(type(i) is not int for i in indexes):
                errors.append(f"paragraph locator type invalid: {case_id}/{doc_id}")
                continue
            if label == "UNKNOWN":
                if indexes:
                    errors.append(f"UNKNOWN has passage locator: {case_id}/{doc_id}")
                    continue
            else:
                if review.get("source") != candidate.get("source") or not indexes:
                    errors.append(f"source/passage citation missing: {case_id}/{doc_id}")
                    continue
                total = paragraph_count(candidate.get("content", ""))
                if any(i < 1 or i > total for i in indexes):
                    errors.append(f"paragraph locator outside candidate: {case_id}/{doc_id}")
                    continue
            case_reviews[doc_id] = review
        bundle_label = bundle.get("label")
        supporting = bundle.get("supporting_doc_ids", [])
        conflicting = bundle.get("conflicting_doc_ids", [])
        if bundle_label not in BUNDLE_LABELS or not isinstance(supporting, list) or not isinstance(conflicting, list) or not isinstance(bundle.get("rationale"), str) or not bundle["rationale"].strip():
            errors.append(f"bundle label/document ID schema invalid: {case_id}")
            continue
        if not set(supporting + conflicting).issubset(candidate_by_id):
            errors.append(f"bundle cites non-packet doc_id: {case_id}")
            continue
        normalized[case_id] = {"candidate_reviews": case_reviews, "bundle_review": bundle}
    if errors:
        return None, errors
    return normalized, []


def fleiss_kappa(rows: list[list[str]]) -> float | None:
    if not rows or len(rows[0]) < 2:
        return None
    categories = sorted({label for row in rows for label in row})
    n = len(rows[0])
    counts = [[row.count(category) for category in categories] for row in rows]
    p_i = [(sum(value * value for value in row) - n) / (n * (n - 1)) for row in counts]
    p_bar = sum(p_i) / len(p_i)
    p = [sum(row[index] for row in counts) / (len(counts) * n) for index in range(len(categories))]
    p_e = sum(value * value for value in p)
    return (p_bar - p_e) / (1 - p_e) if p_e != 1 else None


def materialize_and_freeze() -> None:
    freeze, packet = read_freeze()
    call_manifest = json.loads((WORK / "call_manifest_v1.json").read_text(encoding="utf-8"))
    rater_cases = {rater: {} for rater, _ in RATERS}
    batch_status = {}
    for rater, _ in RATERS:
        for batch_index, batch_ref in enumerate(freeze["batches"], 1):
            batch_cases = json.loads((WORK / batch_ref["path"]).read_text(encoding="utf-8"))["cases"]
            call_dir = WORK / "runs" / rater / f"batch_{batch_index:02d}"
            validated, errors = validated_batch(call_dir, batch_cases)
            batch_status[f"{rater}/batch_{batch_index:02d}"] = {"valid": validated is not None, "errors": errors, "case_count": len(batch_cases)}
            if validated is None:
                for case in batch_cases:
                    candidate_reviews = {
                        c["doc_id"]: {"doc_id": c["doc_id"], "label": "UNKNOWN", "source": c["source"], "paragraph_indexes": [], "rationale": "Missing or invalid model output under the frozen schema."}
                        for c in case["retrieved_candidates"]
                    }
                    rater_cases[rater][case["case_id"]] = {
                        "candidate_reviews": candidate_reviews,
                        "bundle_review": {"label": "UNKNOWN", "supporting_doc_ids": [], "conflicting_doc_ids": [], "rationale": "Missing or invalid model output under the frozen schema."},
                    }
            else:
                rater_cases[rater].update(validated)
        if len(rater_cases[rater]) != 120:
            raise RuntimeError(f"{rater} has {len(rater_cases[rater])} cases after UNKNOWN completion")
    rater_summary = {}
    for rater, model in RATERS:
        labels = [
            rater_cases[rater][case["case_id"]]["candidate_reviews"].get(candidate["doc_id"], {}).get("label", "UNKNOWN")
            for case in packet["cases"] for candidate in case["retrieved_candidates"]
        ]
        bundles = [rater_cases[rater][case["case_id"]]["bundle_review"].get("label", "UNKNOWN") for case in packet["cases"]]
        rater_summary[rater] = {
            "model_id": model,
            "case_reviews": len(rater_cases[rater]),
            "candidate_reviews": len(labels),
            "candidate_label_counts": dict(sorted(Counter(labels).items())),
            "bundle_label_counts": dict(sorted(Counter(bundles).items())),
        }
    candidate_reference = []
    bundle_reference = []
    candidate_votes = []
    bundle_votes = []
    resolved_candidates = 0
    resolved_bundles = 0
    for case in packet["cases"]:
        rater_rows = [rater_cases[rater][case["case_id"]] for rater, _ in RATERS]
        out_case = {"case_id": case["case_id"], "candidate_reviews": [], "bundle_review": {}}
        for candidate in case["retrieved_candidates"]:
            doc_id = candidate["doc_id"]
            reviews = [row["candidate_reviews"].get(doc_id, {"label": "UNKNOWN"}) for row in rater_rows]
            labels = [review.get("label", "UNKNOWN") if review.get("label") in CANDIDATE_LABELS else "UNKNOWN" for review in reviews]
            votes = Counter(labels)
            label, votes_count = votes.most_common(1)[0]
            if votes_count < 2:
                label = "UNKNOWN"
            if label != "UNKNOWN":
                resolved_candidates += 1
            candidate_votes.append(labels)
            citations = [
                {"rater_id": rater, "source": review.get("source"), "paragraph_indexes": review.get("paragraph_indexes", []), "rationale": review.get("rationale", "")}
                for (rater, _), review in zip(RATERS, reviews) if review.get("label") == label and label != "UNKNOWN"
            ]
            out_case["candidate_reviews"].append({"doc_id": doc_id, "label": label, "votes": dict(sorted(votes.items())), "citations_and_rationales": citations})
        bundles = [row["bundle_review"] for row in rater_rows]
        labels = [bundle.get("label", "UNKNOWN") if bundle.get("label") in BUNDLE_LABELS else "UNKNOWN" for bundle in bundles]
        votes = Counter(labels)
        label, votes_count = votes.most_common(1)[0]
        if votes_count < 2:
            label = "UNKNOWN"
        if label != "UNKNOWN":
            resolved_bundles += 1
        bundle_votes.append(labels)
        citations = [
            {"rater_id": rater, "supporting_doc_ids": bundle.get("supporting_doc_ids", []), "conflicting_doc_ids": bundle.get("conflicting_doc_ids", []), "rationale": bundle.get("rationale", "")}
            for (rater, _), bundle in zip(RATERS, bundles) if bundle.get("label") == label and label != "UNKNOWN"
        ]
        out_case["bundle_review"] = {"label": label, "votes": dict(sorted(votes.items())), "citations_and_rationales": citations}
        candidate_reference.append(out_case)
        bundle_reference.append({"case_id": case["case_id"], "label": label, "votes": dict(sorted(votes.items())), "citations_and_rationales": citations})
    ratings_path = WORK / "rater_reviews_v1.json"
    reference_path = WORK / "reference_freeze_v1.json"
    manifest_path = WORK / "reference_freeze_manifest_v1.json"
    if ratings_path.exists() or reference_path.exists() or manifest_path.exists():
        raise RuntimeError("refusing to overwrite existing reference outputs")
    write_json(ratings_path, {"schema": "ragin.evidence_support_ai_rater_reviews.v1", "rater_ids": list(rater_cases), "cases_by_rater": rater_cases})
    reference = {
        "schema": "ragin.evidence_support_ai_derived_reference.v1",
        "status": "AI_DERIVED_REFERENCE_FROZEN",
        "reference_type": "AI_DERIVED_MULTI_FAMILY_PANEL_MAJORITY",
        "human_ground_truth": False,
        "independent_model_consensus_claim": False,
        "source_packet_sha256": SOURCE_SHA,
        "annotation_input_freeze_sha256": digest_file(FREEZE_INPUTS),
        "annotation_protocol_sha256": digest_file(PROTOCOL),
        "annotation_prompt_sha256": digest_file(PROMPT),
        "model_catalog_sha256": digest_file(CATALOG),
        "rater_model_ids": [{"rater_id": rater, "model_id": model} for rater, model in RATERS],
        "aggregation": "field-wise majority (at least 2 of 3); ties and invalid/missing reviews are UNKNOWN",
        "case_count": len(candidate_reference),
        "candidate_count": sum(len(case["candidate_reviews"]) for case in candidate_reference),
        "resolved_candidate_count": resolved_candidates,
        "unknown_candidate_count": sum(review["label"] == "UNKNOWN" for case in candidate_reference for review in case["candidate_reviews"]),
        "resolved_bundle_count": resolved_bundles,
        "unknown_bundle_count": sum(bundle["label"] == "UNKNOWN" for bundle in bundle_reference),
        "candidate_panel_fleiss_kappa": fleiss_kappa(candidate_votes),
        "bundle_panel_fleiss_kappa": fleiss_kappa(bundle_votes),
        "rater_coverage_and_labels": rater_summary,
        "batch_validation": batch_status,
        "candidate_reference": candidate_reference,
        "bundle_reference": bundle_reference,
        "frozen_at_utc": now_utc(),
    }
    write_json(reference_path, reference)
    write_json(manifest_path, {
        "schema": "ragin.evidence_support_ai_reference_freeze_manifest.v1",
        "reference_sha256": digest_file(reference_path),
        "rater_reviews_sha256": digest_file(ratings_path),
        "call_manifest_sha256": digest_file(WORK / "call_manifest_v1.json"),
        "input_freeze_sha256": digest_file(FREEZE_INPUTS),
        "protocol_sha256": digest_file(PROTOCOL),
        "prompt_sha256": digest_file(PROMPT),
        "source_packet_sha256": SOURCE_SHA,
        "frozen_at_utc": now_utc(),
    })
    print(json.dumps({
        "reference_frozen": True, "cases": len(candidate_reference), "candidates": reference["candidate_count"],
        "resolved_candidates": resolved_candidates, "unknown_candidates": reference["unknown_candidate_count"],
        "resolved_bundles": resolved_bundles, "unknown_bundles": reference["unknown_bundle_count"],
        "candidate_panel_kappa": reference["candidate_panel_fleiss_kappa"],
        "bundle_panel_kappa": reference["bundle_panel_fleiss_kappa"], "reference_sha256": digest_file(reference_path),
    }, indent=2))


def record_run_amendment() -> None:
    verify_frozen_source()
    previous_amendment_path = WORK / "annotation_run_amendment_v1.json"
    amendment_path = WORK / "annotation_run_amendment_v2.json"
    if not previous_amendment_path.exists() or amendment_path.exists():
        raise RuntimeError("expected prior run amendment or amendment target is missing")
    freeze = json.loads(FREEZE_INPUTS.read_text(encoding="utf-8"))
    previous = json.loads(previous_amendment_path.read_text(encoding="utf-8"))
    if previous.get("input_freeze_sha256") != digest_file(FREEZE_INPUTS):
        raise RuntimeError("prior amendment refers to a different input freeze")
    if (WORK / "reference_freeze_v1.json").exists() or (WORK / "rater_reviews_v1.json").exists():
        raise RuntimeError("annotation output already exists; a pre-annotation amendment is no longer valid")
    amendment = {
        "schema": "ragin.evidence_support_ai_annotation_run_amendment.v2",
        "amended_at_utc": now_utc(),
        "input_freeze_sha256": digest_file(FREEZE_INPUTS),
        "prior_amendment_sha256": digest_file(previous_amendment_path),
        "protocol_sha256": digest_file(PROTOCOL),
        "prompt_sha256": digest_file(PROMPT),
        "model_catalog_sha256": digest_file(CATALOG),
        "runner_path": str(pathlib.Path(__file__).relative_to(ROOT)),
        "runner_sha256": digest_file(pathlib.Path(__file__)),
        "reason": "The first resumed attempt stopped at a safe request-byte comparison because it compared pretty-printed persisted JSON with its compact canonical hash. No new model request was sent after that guard failed.",
        "scope_change": "None. Model IDs, prompt, batch inputs, label schema, aggregation, and source packet are unchanged.",
        "recovery": "Compare persisted request bodies by canonical JSON bytes; retain provider-envelope classification and the two exact retry cap from amendment V1. Prior raw responses remain immutable.",
        "usable_annotation_outputs_before_amendment": 0,
    }
    write_json(amendment_path, amendment)
    print(json.dumps({
        "amendment_written": True,
        "previous_amendment_sha256": amendment["prior_amendment_sha256"],
        "runner_sha256": amendment["runner_sha256"],
        "amendment_sha256": digest_file(amendment_path),
    }, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=["prepare", "amend", "run", "freeze"])
    phase = parser.parse_args().phase
    try:
        {"prepare": prepare, "amend": record_run_amendment, "run": run_calls, "freeze": materialize_and_freeze}[phase]()
        return 0
    except Exception as error:
        print(f"BLOCKED: {type(error).__name__}: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
