#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from itertools import combinations
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results" / "laya_decision_v2"
WORK = Path("/home/elaref/Documents/research/ragin_primary169_claude_v1")
MODEL = "claude-sonnet-4-6-free"
TAXONOMY = ["BENIGN", "RECON", "SUSPICIOUS", "EXPLOITATION", "PRIVILEGE_ESCALATION", "DATA_ACCESS", "PERSISTENCE", "OTHER_ATTACK", "UNCERTAIN"]
ATTACK = {x: "POSITIVE" for x in TAXONOMY if x not in {"BENIGN", "UNCERTAIN"}}
ATTACK["BENIGN"] = "NEGATIVE"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def dump_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True) + "\n")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def extract_json(text: str) -> Any:
    text = text.strip()
    candidates = [text]
    m = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.I | re.S)
    if m:
        candidates.insert(0, m.group(1).strip())
    for candidate in candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass
    start = min([p for p in (text.find("["), text.find("{")) if p >= 0], default=-1)
    if start >= 0:
        for end in range(len(text), start, -1):
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                continue
    raise ValueError("API response did not contain parseable JSON")


def api_call(api_key: str, messages: list[dict[str, str]], max_tokens: int = 16000) -> tuple[str, dict[str, Any]]:
    body = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0,
        "max_tokens": max_tokens,
        "stream": False,
    }
    req = urllib.request.Request(
        "https://api.apmix.ai/v1/chat/completions",
        data=json.dumps(body, ensure_ascii=False).encode(),
        headers={
            "Authorization": f"Bearer {api_key}",
            "X-API-Key": api_key,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=900) as response:
            payload = json.loads(response.read())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        raise RuntimeError(f"APMix HTTP {exc.code}: {body[:1000]}") from exc
    choices = payload.get("choices") or []
    if not choices or not isinstance(choices[0].get("message"), dict):
        raise RuntimeError("APMix response had no chat completion message")
    content = choices[0]["message"].get("content", "")
    if isinstance(content, list):
        content = "".join(x.get("text", "") for x in content if isinstance(x, dict))
    return str(content), {"provider_model": payload.get("model"), "usage": payload.get("usage", {})}


def validate_primary(rows: Any, expected_ids: set[str], run_id: str) -> list[dict[str, str]]:
    if not isinstance(rows, list):
        raise ValueError(f"{run_id}: response is not a JSON array")
    seen: set[str] = set()
    out: list[dict[str, str]] = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError(f"{run_id}: non-object record")
        cid, label = row.get("case_id"), row.get("label")
        if not isinstance(cid, str) or cid not in expected_ids or cid in seen:
            raise ValueError(f"{run_id}: invalid/duplicate case_id")
        if label not in TAXONOMY:
            raise ValueError(f"{run_id}: invalid label {label!r}")
        rationale = row.get("brief rationale", row.get("rationale", row.get("notes", "")))
        if not isinstance(rationale, str):
            rationale = str(rationale)
        out.append({"case_id": cid, "label": label, "brief rationale": rationale[:1000], "annotator_run_id": run_id})
        seen.add(cid)
    if seen != expected_ids or len(out) != 169:
        raise ValueError(f"{run_id}: expected 169 exact IDs, got {len(out)}")
    return out


def primary_prompt(packet: list[dict[str, Any]], run_id: str) -> list[dict[str, str]]:
    system = """You are a blinded behavior annotator. Use only the evidence and neutral_context in the supplied packet. Do not use outside predictions, labels, provenance, or model outputs. Assign exactly one taxonomy label to every case. Return ONLY a valid JSON array with exactly one object per case, in the packet order, using keys case_id, label, brief rationale, annotator_run_id. Allowed labels: BENIGN, RECON, SUSPICIOUS, EXPLOITATION, PRIVILEGE_ESCALATION, DATA_ACCESS, PERSISTENCE, OTHER_ATTACK, UNCERTAIN. Use UNCERTAIN when evidence is insufficient or materially ambiguous. Do not infer maliciousness from technical vocabulary, Linux commands, security-tool names, case IDs, or dataset provenance alone. Rationale must be brief and behavior-based."""
    user = "ANNOTATOR RUN: " + run_id + "\nPACKET JSON:\n" + json.dumps(packet, ensure_ascii=False, separators=(",", ":"))
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def adjudication_prompt(packet: list[dict[str, Any]]) -> list[dict[str, str]]:
    system = """You are a fresh blinded adjudicator. Use only each case's evidence, neutral_context, and anonymized RATER_A/RATER_B/RATER_C labels. Do not infer which system produced a label and do not access outside predictions or outcomes. Return ONLY a valid JSON array with exactly one object per case, in packet order, using keys case_id, final_label, brief rationale. Allowed labels: BENIGN, RECON, SUSPICIOUS, EXPLOITATION, PRIVILEGE_ESCALATION, DATA_ACCESS, PERSISTENCE, OTHER_ATTACK, UNCERTAIN. Do not force resolution: use UNCERTAIN when evidence is insufficient or materially ambiguous. Apply the behavior-based taxonomy consistently."""
    user = "ADJUDICATION PACKET JSON:\n" + json.dumps(packet, ensure_ascii=False, separators=(",", ":"))
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def validate_adjudication(rows: Any, expected_ids: set[str]) -> list[dict[str, str]]:
    if not isinstance(rows, list):
        raise ValueError("adjudicator response is not a JSON array")
    seen: set[str] = set(); out = []
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("case_id"), str) or row["case_id"] not in expected_ids or row["case_id"] in seen:
            raise ValueError("invalid or duplicate adjudicator case_id")
        if row.get("final_label") not in TAXONOMY:
            raise ValueError("invalid adjudicator label")
        out.append({"case_id": row["case_id"], "final_label": row["final_label"], "brief rationale": str(row.get("brief rationale", row.get("rationale", "")))[:1000]})
        seen.add(row["case_id"])
    if len(out) != len(expected_ids) or seen != expected_ids:
        raise ValueError("adjudicator coverage is not exact")
    return out


def agreement(primary: list[list[dict[str, str]]]) -> dict[str, Any]:
    labels = [{r["case_id"]: r["label"] for r in rows} for rows in primary]
    ids = sorted(labels[0])
    def coh(a: list[str], b: list[str]) -> float:
        n = len(a); agree = sum(x == y for x, y in zip(a, b)) / n
        cats = set(a) | set(b)
        pa = sum(a.count(c) * b.count(c) for c in cats) / (n * n)
        return (agree - pa) / (1 - pa) if pa != 1 else 1.0
    pairs = []
    for i, j in combinations(range(3), 2):
        a = [labels[i][cid] for cid in ids]; b = [labels[j][cid] for cid in ids]
        eligible = [(x, y) for x, y in zip(a, b) if x != "UNCERTAIN" and y != "UNCERTAIN"]
        pairs.append({"runs": [i + 1, j + 1], "multiclass_exact_agreement": sum(x == y for x, y in zip(a, b)) / len(a), "multiclass_cohen_kappa": coh(a, b), "binary_jointly_eligible_N": len(eligible), "binary_agreement": sum(ATTACK[x] == ATTACK[y] for x, y in eligible) / len(eligible) if eligible else None, "binary_cohen_kappa": coh([ATTACK[x] for x, y in eligible], [ATTACK[y] for x, y in eligible]) if eligible else None})
    def fleiss(matrix: list[list[str]], categories: list[str]) -> float:
        n, k = len(matrix), len(matrix[0]); m = len(categories)
        props = [[sum(row[r] == c for r in range(k)) for c in categories] for row in matrix]
        p_i = [sum(v * (v - 1) for v in row) / (k * (k - 1)) for row in props]
        p_bar = sum(p_i) / n; p_cat = [sum(row[c] for row in props) / (n * k) for c in range(m)]; p_e = sum(x * x for x in p_cat)
        return (p_bar - p_e) / (1 - p_e) if p_e != 1 else 1.0
    multiclass_matrix = [[labels[r][cid] for r in range(3)] for cid in ids]
    binary_rows = [[ATTACK[labels[r][cid]] for r in range(3)] for cid in ids if all(labels[r][cid] != "UNCERTAIN" for r in range(3))]
    exact3 = sum(len({labels[r][cid] for r in range(3)}) == 1 for cid in ids)
    exact2 = sum(sorted(Counter(labels[r][cid] for r in range(3)).values()) == [1, 2] for cid in ids)
    return {"schema": "ragin.primary_169.run_to_run_agreement.v1", "terminology": "RUN_TO_RUN_SELF_CONSISTENCY_UNDER_BLINDED_REPEATED_INFERENCE", "statistical_independence_claimed": False, "N": 169, "pairwise": pairs, "multiclass_fleiss_kappa": fleiss(multiclass_matrix, TAXONOMY), "binary_fleiss_kappa_jointly_eligible": fleiss(binary_rows, ["NEGATIVE", "POSITIVE"]) if binary_rows else None, "binary_jointly_eligible_N": len(binary_rows), "exact_3_of_3": exact3, "exact_2_of_3": exact2, "three_way_disagreement": 169 - exact3 - exact2, "uncertain_per_run": [sum(v == "UNCERTAIN" for v in d.values()) for d in labels], "label_distribution_per_run": [dict(sorted(Counter(d.values()).items())) for d in labels]}


def main() -> int:
    key = os.environ.get("APMIX_API_KEY")
    if not key:
        raise SystemExit("APMIX_API_KEY is required")
    raw_freeze = RESULTS / "primary_169_raw_execution_freeze_v2b.json"
    blind_source = RESULTS / "primary_169_blind_annotation_source_v2b.json"
    if sha256(raw_freeze) != "45e1de7624116fda5ea33a4082d37b47db65d20bee172e90d1a29a2f8e597758":
        raise SystemExit("raw freeze hash mismatch")
    source_doc = load_json(blind_source)
    source = source_doc.get("rows", []) if isinstance(source_doc, dict) else source_doc
    if source_doc.get("n") != 169 or len(source) != 169:
        raise SystemExit("blind source is not N=169")
    expected_ids = {str(x["case_id"]) for x in source}
    packet_paths = [WORK / f"expert_ai_0{i}" / f"expert_ai_0{i}.json" for i in range(1, 4)]
    primary: list[list[dict[str, str]]] = []
    for i, path in enumerate(packet_paths, 1):
        packet_doc = load_json(path)
        packet = packet_doc.get("rows", []) if isinstance(packet_doc, dict) else packet_doc
        if {str(x["case_id"]) for x in packet} != expected_ids or len(packet) != 169:
            raise SystemExit(f"packet {i} mismatch")
        raw, meta = api_call(key, primary_prompt(packet, f"expert_ai_0{i}"))
        (WORK / f"expert_ai_0{i}" / "RAW_API_RESPONSE.txt").write_text(raw)
        rows = validate_primary(extract_json(raw), expected_ids, f"expert_ai_0{i}")
        out = RESULTS / f"primary_169_expert_ai_0{i}_annotations_v1.jsonl"
        out.write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows))
        dump_json(RESULTS / f"primary_169_expert_ai_0{i}_runtime_v1.json", {"run_id": f"expert_ai_0{i}", "model": MODEL, "api_base_url": "https://api.apmix.ai/v1", "temperature": 0, "max_tokens": 16000, "fresh_isolated_context": True, "provider_response_model": meta.get("provider_model"), "usage": meta.get("usage", {}), "output_sha256": sha256(out), "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
        primary.append(rows)
    agr = agreement(primary)
    dump_json(RESULTS / "primary_169_ai_panel_agreement_v1.json", agr)
    ids = sorted(expected_ids)
    maps = [{r["case_id"]: r["label"] for r in rows} for rows in primary]
    by_id = {str(x["case_id"]): x for x in source}
    candidates = []
    for cid in ids:
        labs = [m[cid] for m in maps]
        if len(set(labs)) != 1:
            candidates.append({"case_id": cid, "evidence": by_id[cid]["evidence"], "neutral_context": by_id[cid].get("neutral_context", ""), "RATER_A": labs[0], "RATER_B": labs[1], "RATER_C": labs[2]})
    candidates.sort(key=lambda x: hashlib.sha256(f"404:{x['case_id']}".encode()).hexdigest())
    cand_path = RESULTS / "primary_169_adjudication_candidate_manifest_v1.json"
    dump_json(cand_path, candidates)
    adj_packet_path = WORK / "adjudicator_01" / "adjudication_packet.json"
    dump_json(adj_packet_path, candidates)
    packet_freeze = {"schema": "ragin.primary_169.adjudication_packet_freeze.v1", "candidate_count": len(candidates), "packet_sha256": sha256(adj_packet_path), "adjudicator_model": MODEL, "fresh_isolated_context": True, "primary_outcomes_frozen": True, "RAGIN_effectiveness_outcomes_inaccessible": True}
    dump_json(RESULTS / "primary_169_adjudication_packet_freeze_v1.json", packet_freeze)
    raw_adj, meta = api_call(key, adjudication_prompt(candidates))
    (WORK / "adjudicator_01" / "RAW_API_RESPONSE.txt").write_text(raw_adj)
    adj_rows = validate_adjudication(extract_json(raw_adj), {x["case_id"] for x in candidates}) if candidates else []
    adj_out = RESULTS / "primary_169_adjudicator_01_output_v1.jsonl"
    adj_out.write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in adj_rows))
    dump_json(RESULTS / "primary_169_adjudicator_01_runtime_v1.json", {"model": MODEL, "api_base_url": "https://api.apmix.ai/v1", "temperature": 0, "max_tokens": 16000, "fresh_isolated_context": True, "provider_response_model": meta.get("provider_model"), "usage": meta.get("usage", {}), "output_sha256": sha256(adj_out), "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
    adj_map = {x["case_id"]: x["final_label"] for x in adj_rows}
    final, binary = [], []
    for cid in ids:
        labs = [m[cid] for m in maps]
        exact = len(set(labs)) == 1
        label = labs[0] if exact else adj_map[cid]
        src = "EXACT_3_OF_3_PRIMARY_RUNS" if exact else "BLINDED_AI_ADJUDICATION"
        rec = {"case_id": cid, "label": label, "source": src, "reference_type": "SINGLE_MODEL_FAMILY_AI_DERIVED_ADJUDICATED_REFERENCE"}
        final.append(rec)
        binary.append({"case_id": cid, "binary_label": ATTACK[label] if label != "UNCERTAIN" else "UNCERTAIN", "multiclass_label": label, "source": src, "reference_type": rec["reference_type"]})
    final_path = RESULTS / "primary_169_ai_derived_reference_v1.json"
    binary_path = RESULTS / "primary_169_ai_derived_binary_reference_v1.json"
    dump_json(final_path, final); dump_json(binary_path, binary)
    concrete = sum(x["label"] != "UNCERTAIN" for x in final)
    uncertain = 169 - concrete
    summary = {"total": 169, "exact_3_of_3": agr["exact_3_of_3"], "adjudicated": len(candidates), "UNCERTAIN": uncertain, "resolved_concrete": concrete, "binary_evaluable": concrete, "multiclass_distribution": dict(sorted(Counter(x["label"] for x in final).items())), "binary_distribution": dict(sorted(Counter(x["binary_label"] for x in binary).items())), "resolved_gate": concrete >= 150, "binary_gate": concrete >= 145}
    dump_json(RESULTS / "primary_169_ai_derived_reference_summary_v1.json", summary)
    freeze = {"schema": "ragin.primary_169.ai_derived_reference_freeze.v1", "reference_type": "SINGLE_MODEL_FAMILY_AI_DERIVED_ADJUDICATED_REFERENCE", "annotation_instrument_freeze_sha256": sha256(RESULTS / "primary_169_annotation_instrument_freeze_v1b.json"), "primary_outputs": [sha256(RESULTS / f"primary_169_expert_ai_0{i}_annotations_v1.jsonl") for i in range(1, 4)], "agreement_sha256": sha256(RESULTS / "primary_169_ai_panel_agreement_v1.json"), "adjudication_candidate_manifest_sha256": sha256(cand_path), "adjudication_packet_freeze_sha256": sha256(RESULTS / "primary_169_adjudication_packet_freeze_v1.json"), "adjudicator_output_sha256": sha256(adj_out), "reference_sha256": sha256(final_path), "binary_reference_sha256": sha256(binary_path), "summary_sha256": sha256(RESULTS / "primary_169_ai_derived_reference_summary_v1.json"), "reference_policy_changed_after_annotations": False, "aggregation_rule_changed": False, "binary_projection_changed": False, "uncertainty_rule_changed": False, "acceptance_threshold_changed": False, "panel_substitution_occurred_before_annotations": True, "distinct_model_families": 1, "model": MODEL, "provider": "APMix", "api_base_url": "https://api.apmix.ai/v1", "statistical_independence_claimed": False, "RAGIN_outputs_accessed_during_reference_construction": False, "effectiveness_results_accessed_during_reference_construction": False, "effectiveness_metrics_computed": False, "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    freeze_path = RESULTS / "primary_169_ai_derived_reference_freeze_v1.json"
    dump_json(freeze_path, freeze)
    print(json.dumps({"primary_runs": [169, 169, 169], "exact_3_of_3": agr["exact_3_of_3"], "adjudicated": len(candidates), "resolved": concrete, "uncertain": uncertain, "binary_evaluable": concrete, "freeze_sha256": sha256(freeze_path)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
