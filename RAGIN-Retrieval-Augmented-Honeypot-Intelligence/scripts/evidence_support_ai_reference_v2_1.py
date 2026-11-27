from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
from collections import Counter

import evidence_support_ai_reference_v2 as base


base.WORK = base.BASE / "ai_reference_v2_1"
base.MODELS = {
    "P1": "nvidia/nemotron-3-super-120b-a12b:free",
    "P2": "dots-studio/dots-3-note-preview:free",
}
base_build_body = base.build_body


def sha_file(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_structured_body(model: str, prompt: str, data: dict, max_tokens: int) -> dict:
    body = base_build_body(model, prompt, data, max_tokens)
    body["response_format"] = {"type": "json_object"}
    return body


base.build_body = build_structured_body


def prepare() -> None:
    base.prepare()
    freeze_path = base.WORK / "primary_input_freeze_v2.json"
    freeze = base.read_json(freeze_path)
    freeze["executor_path"] = str(pathlib.Path(__file__).relative_to(base.ROOT))
    freeze["executor_sha256"] = sha_file(pathlib.Path(__file__))
    freeze["api_response_format"] = {"type": "json_object"}
    freeze["disagreement_policy"] = "exact primary agreement is retained; any difference remains UNKNOWN"
    base.write_json(freeze_path, freeze)
    print(json.dumps({"executor_sha256": freeze["executor_sha256"], "input_freeze_sha256": sha_file(freeze_path)}, indent=2))


def verify_executor() -> dict:
    freeze = base.check_primary_freeze()
    if freeze.get("executor_sha256") != sha_file(pathlib.Path(__file__)):
        raise RuntimeError("V2.1 executor differs from its annotation input freeze")
    return freeze


def run_primary() -> None:
    verify_executor()
    base.run_primary()


def freeze_primary() -> None:
    verify_executor()
    base.freeze_primary()
    target = base.WORK / "primary_annotation_freeze_v2.json"
    primary = base.read_json(target)
    primary["executor_sha256"] = sha_file(pathlib.Path(__file__))
    primary["protocol_method"] = "V2.1 two-model agreement; every disagreement is UNKNOWN"
    base.write_json(target, primary)
    manifest_path = base.WORK / "primary_freeze_manifest_v2.json"
    manifest = base.read_json(manifest_path)
    manifest["primary_freeze_sha256"] = sha_file(target)
    manifest["executor_sha256"] = sha_file(pathlib.Path(__file__))
    base.write_json(manifest_path, manifest)
    print(json.dumps({"primary_freeze_sha256": sha_file(target), "executor_sha256": sha_file(pathlib.Path(__file__))}, indent=2))


def fleiss_kappa(rows: list[list[str]]) -> float | None:
    if not rows or len(rows[0]) < 2:
        return None
    categories = sorted({x for row in rows for x in row})
    n = len(rows[0])
    counts = [[row.count(category) for category in categories] for row in rows]
    p_i = [(sum(x * x for x in row) - n) / (n * (n - 1)) for row in counts]
    p_bar = sum(p_i) / len(p_i)
    p = [sum(row[i] for row in counts) / (len(counts) * n) for i in range(len(categories))]
    p_e = sum(x * x for x in p)
    return (p_bar - p_e) / (1 - p_e) if p_e != 1 else None


def freeze_reference() -> None:
    verify_executor()
    packet = base.verify_source()
    primary_path = base.WORK / "primary_annotation_freeze_v2.json"
    primary_manifest_path = base.WORK / "primary_freeze_manifest_v2.json"
    primary_manifest = base.read_json(primary_manifest_path)
    if sha_file(primary_path) != primary_manifest["primary_freeze_sha256"]:
        raise RuntimeError("primary review freeze hash mismatch")
    primary = base.read_json(primary_path)
    raters = primary["reviews_by_rater"]
    cases_out = []
    disagreements = []
    candidate_labels = Counter()
    bundle_labels = Counter()
    candidate_votes = []
    bundle_votes = []
    for case in packet["cases"]:
        case_id = case["case_id"]
        case_out = {"case_id": case_id, "candidate_reviews": [], "bundle_review": {}}
        for index, candidate in enumerate(case["retrieved_candidates"]):
            doc_id = candidate["doc_id"]
            p1 = raters["P1"][case_id]["candidate_reviews"][doc_id]
            p2 = raters["P2"][case_id]["candidate_reviews"][doc_id]
            labels = [p1["label"], p2["label"]]
            candidate_votes.append(labels)
            same = labels[0] == labels[1]
            label = labels[0] if same else "UNKNOWN"
            candidate_labels[label] += 1
            record = {
                "case_id": case_id, "candidate_index": index, "doc_id": doc_id,
                "label": label, "primary_labels": {"P1": labels[0], "P2": labels[1]},
                "disposition": "AGREED_UNKNOWN" if same and label == "UNKNOWN" else "AGREED_LABEL" if same else "DISAGREEMENT_RETAINED_UNKNOWN",
                "citations_and_rationales": [
                    {"rater_id": "P1", "source": p1.get("source"), "paragraph_indexes": p1.get("paragraph_indexes", []), "rationale": p1.get("rationale", "")},
                    {"rater_id": "P2", "source": p2.get("source"), "paragraph_indexes": p2.get("paragraph_indexes", []), "rationale": p2.get("rationale", "")},
                ],
            }
            case_out["candidate_reviews"].append(record)
            if not same:
                disagreements.append({"field": "candidate", "case_id": case_id, "candidate_index": index, "doc_id": doc_id, "P1": p1, "P2": p2, "final_label": "UNKNOWN", "adjudication_disposition": "UNRESOLVED_AI_PANEL_DISAGREEMENT"})
        p1b = raters["P1"][case_id]["bundle_review"]
        p2b = raters["P2"][case_id]["bundle_review"]
        bundle_vote = [p1b["label"], p2b["label"]]
        bundle_votes.append(bundle_vote)
        same = bundle_vote[0] == bundle_vote[1]
        label = bundle_vote[0] if same else "UNKNOWN"
        bundle_labels[label] += 1
        case_out["bundle_review"] = {
            "label": label, "primary_labels": {"P1": bundle_vote[0], "P2": bundle_vote[1]},
            "disposition": "AGREED_UNKNOWN" if same and label == "UNKNOWN" else "AGREED_LABEL" if same else "DISAGREEMENT_RETAINED_UNKNOWN",
            "citations_and_rationales": [{"rater_id": "P1", **p1b}, {"rater_id": "P2", **p2b}],
        }
        if not same:
            disagreements.append({"field": "bundle", "case_id": case_id, "P1": p1b, "P2": p2b, "final_label": "UNKNOWN", "adjudication_disposition": "UNRESOLVED_AI_PANEL_DISAGREEMENT"})
        cases_out.append(case_out)
    target = base.WORK / "reference_freeze_v2_1.json"
    if target.exists():
        raise RuntimeError("reference freeze already exists")
    reference = {
        "schema": "ragin.evidence_support_ai_derived_reference.v2.1",
        "status": "AI_DERIVED_REFERENCE_FROZEN",
        "reference_type": "AI_DERIVED_TWO_FAMILY_AGREEMENT_WITH_UNKNOWN_DISAGREEMENTS",
        "human_ground_truth": False,
        "independent_consensus_claim": False,
        "source_packet_sha256": base.SOURCE_SHA,
        "primary_freeze_sha256": sha_file(primary_path),
        "model_ids": base.MODELS,
        "case_count": len(cases_out),
        "candidate_count": sum(len(c["candidate_reviews"]) for c in cases_out),
        "candidate_label_counts": dict(sorted(candidate_labels.items())),
        "bundle_label_counts": dict(sorted(bundle_labels.items())),
        "candidate_unknown_count": candidate_labels["UNKNOWN"],
        "bundle_unknown_count": bundle_labels["UNKNOWN"],
        "candidate_exact_agreement": sum(a == b for row in candidate_votes for a, b in [row]),
        "candidate_agreement_total": len(candidate_votes),
        "candidate_fleiss_kappa": fleiss_kappa(candidate_votes),
        "bundle_exact_agreement": sum(row[0] == row[1] for row in bundle_votes),
        "bundle_agreement_total": len(bundle_votes),
        "bundle_fleiss_kappa": fleiss_kappa(bundle_votes),
        "disagreement_count": len(disagreements),
        "adjudication_rule": "No adjudicator; every disagreement remains UNKNOWN",
        "disagreement_and_adjudication_records": disagreements,
        "cases": cases_out,
        "frozen_at_utc": base.now_utc(),
    }
    base.write_json(target, reference)
    manifest_path = base.WORK / "reference_freeze_manifest_v2_1.json"
    base.write_json(manifest_path, {
        "schema": "ragin.evidence_support_ai_reference_freeze_manifest.v2.1",
        "reference_sha256": sha_file(target), "primary_freeze_sha256": sha_file(primary_path),
        "primary_call_manifest_sha256": sha_file(base.WORK / "primary_call_manifest_v2.json"),
        "input_freeze_sha256": sha_file(base.WORK / "primary_input_freeze_v2.json"),
        "protocol_sha256": sha_file(base.WORK / "AI_REFERENCE_PROTOCOL_V2.md"),
        "prompt_sha256": sha_file(base.WORK / "AI_PRIMARY_PROMPT_V2.txt"),
        "model_catalog_sha256": sha_file(base.WORK / "model_catalog_freeze_v2.json"),
        "executor_sha256": sha_file(pathlib.Path(__file__)),
        "source_packet_sha256": base.SOURCE_SHA,
        "frozen_at_utc": base.now_utc(),
    })
    print(json.dumps({
        "reference_frozen": True, "cases": len(cases_out), "candidates": reference["candidate_count"],
        "candidate_labels": reference["candidate_label_counts"], "bundle_labels": reference["bundle_label_counts"],
        "candidate_agreement": f"{reference['candidate_exact_agreement']}/{reference['candidate_agreement_total']}",
        "bundle_agreement": f"{reference['bundle_exact_agreement']}/{reference['bundle_agreement_total']}",
        "disagreements_retained_unknown": len(disagreements), "reference_sha256": sha_file(target),
    }, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=["prepare", "run-primary", "freeze-primary", "freeze-reference"])
    phase = parser.parse_args().phase
    actions = {"prepare": prepare, "run-primary": run_primary, "freeze-primary": freeze_primary, "freeze-reference": freeze_reference}
    try:
        actions[phase]()
        return 0
    except Exception as error:
        print(f"BLOCKED: {type(error).__name__}: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
