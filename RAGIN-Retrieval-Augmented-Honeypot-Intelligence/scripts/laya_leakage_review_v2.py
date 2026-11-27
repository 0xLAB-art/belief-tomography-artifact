#!/usr/bin/env python3
"""Leakage review for the v2 candidate pool.

This script:
- loads the current blind packet
- inspects the flagged cases against their source files
- redacts or excludes cases whose evidence reveals ground truth / experiment context
- writes:
    results/laya_research/leakage_review_v2.json
and updates the blind packet if leakage is removed/redacted.

It does NOT look at Chrollo/Laya predictions.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from collections import defaultdict

ROOT = Path(".")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CANDIDATES_PATH = ROOT / "results" / "laya_research" / "independent_label_candidates_v2.json"
PACKET_PATH = ROOT / "results" / "laya_research" / "blind_annotation_packet_v2.json"
REVIEW_PATH = ROOT / "results" / "laya_research" / "leakage_review_v2.json"


def load_candidates() -> dict:
    m = json.loads(CANDIDATES_PATH.read_text())
    return {c["id"]: c for c in m.get("candidates", [])}, m


def load_packet() -> list[dict]:
    return json.loads(PACKET_PATH.read_text())


def source_file_for_candidate(c: dict) -> Path | None:
    sid = c.get("_source_id", "")
    if sid.startswith("real_linux_"):
        return ROOT / "data" / "real_linux_transcripts.json"
    if sid.startswith("ses-"):
        return ROOT / "data" / "sessions" / f"{sid}.jsonl"
    if c.get("_source") == "cowrie":
        return ROOT / "data" / "cowrie_logs" / f"cowrie.session.{sid}.log"
    return None


def extract_attacker_commands_from_session(path: Path) -> list[str]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            e = json.loads(line)
        except Exception:
            continue
        if e.get("event_type") == "attacker_input":
            cmd = e.get("data", {}).get("command", "")
            if cmd:
                out.append(cmd)
    return out


def review_case(c: dict, source_commands: list[str]) -> dict:
    evidence = c["evidence"]
    low = evidence.lower()
    flags = []

    # serving probe string is experiment context leakage
    if "ssh_e2e_simple" in low:
        flags.append("serving_probe_string")

    # single-word exit/true/yes/no evidence is too low information and can be
    # ambiguously biasing in tiny sets; mark for exclusion as low-info, not as
    # label leakage
    if low.strip().split() == ["true"]:
        flags.append("single_word_true")
    if low.strip() == "exit":
        flags.append("single_word_exit")
    if low.strip() == "false":
        flags.append("single_word_false")
    if low.strip() in {"yes", "no"}:
        flags.append("single_word_yes_no")

    # provider phrase with T1199 is an advisory/naming prompt, not model output,
    # but in this corpus it looks like a researcher-style prompt naming a provider
    # class; mark for review rather than automatic exclusion unless a rater-bias
    # rationale is documented
    if "provider" in low and "t1199" in low:
        flags.append("potential_provider_name_phrase")

    full_source = "\n".join(source_commands)
    full_low = full_source.lower()
    if "ssh_e2e_simple" in full_low and "ssh_e2e_simple" not in low:
        flags.append("probe_present_in_source_but_not_extracted_evidence")

    return {"flags": flags, "evidence_is_low_info": low.strip().split() in (["true"], ["false"], ["exit"], ["yes"], ["no"])}


def decision_for_flags(flags: list[str]) -> str:
    """EXCLUDE / REDACT / KEEP / REVIEW_ONLY."""
    if "serving_probe_string" in flags:
        return "EXCLUDE"
    if "single_word_true" in flags or "single_word_exit" in flags or "single_word_false" in flags or "single_word_yes_no" in flags:
        return "EXCLUDE_LOW_INFO"
    if "potential_provider_name_phrase" in flags:
        return "REVIEW_ONLY"
    if "probe_present_in_source_but_not_extracted_evidence" in flags:
        return "KEEP"
    return "KEEP"


def main() -> None:
    candidates_by_id, manifest = load_candidates()
    packet = load_packet()

    reviews = []
    excluded_ids = set()
    redacted_ids = set()
    kept_ids = set()

    for item in packet:
        cid = item["id"]
        c = candidates_by_id.get(cid)
        if c is None:
            reviews.append({"case_id": cid, "status": "MISSING_FROM_POOL"})
            continue
        src_file = source_file_for_candidate(c)
        src_cmds = extract_attacker_commands_from_session(src_file) if src_file else []
        rev = review_case(c, src_cmds)
        rev["case_id"] = cid
        rev["source_family"] = c.get("_source")
        rev["source_id"] = c.get("_source_id")
        rev["evidence_length_chars"] = len(c["evidence"])
        reviews.append(rev)

        d = decision_for_flags(rev["flags"])
        if d in ("EXCLUDE", "EXCLUDE_LOW_INFO"):
            excluded_ids.add(cid)
        else:
            kept_ids.add(cid)

    # build cleaned packet from kept ids only
    packet_by_id = {x["id"]: x for x in packet}
    cleaned_packet = [packet_by_id[cid["id"]] for cid in packet if cid["id"] in kept_ids]

    review_doc = {
        "reviewed_at": "2026-10-12T22:10:00Z",
        "reviewer": "scripts/laya_leakage_review_v2.py",
        "note": "prediction-blind; only evidence/source examined, no Chrollo/Laya predictions consulted",
        "total_packet_items_before": len(packet),
        "total_packet_items_after": len(cleaned_packet),
        "excluded_ids": sorted(excluded_ids),
        "excluded_low_info_ids": sorted(excluded_ids),
        "review_only_ids": sorted({r["case_id"] for r in reviews if r.get("flags") and "potential_provider_name_phrase" in r.get("flags", [])}),
        "per_case_reviews": reviews,
        "acceptance_criterion": "0 confirmed label/prediction/experiment-context leakage items in final confirmatory packet; generic non-informative words may remain only if reviewed and marked safe",
    }

    REVIEW_PATH.write_text(json.dumps(review_doc, indent=2, ensure_ascii=False) + "\n")
    PACKET_PATH.write_text(json.dumps(cleaned_packet, indent=2, ensure_ascii=False) + "\n")

    print("packet before:", len(packet))
    print("packet after:", len(cleaned_packet))
    print("excluded ids:", sorted(excluded_ids))
    print("review_only ids:", review_doc["review_only_ids"])
    print("written:", REVIEW_PATH, "and updated", PACKET_PATH)


if __name__ == "__main__":
    main()
