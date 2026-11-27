#!/usr/bin/env python3
"""Prediction-blind candidate quality audit.

Reads the v2 candidate pool and produces:
- results/laya_research/candidate_quality_audit.jsonl

This script must NOT consult Chrollo/Laya predictions, disagreement flags,
or confidence when deciding inclusion. It only looks at source/evidence quality.
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
OUT_PATH = ROOT / "results" / "laya_research" / "candidate_quality_audit.jsonl"


def load_candidates() -> list[dict]:
    m = json.loads(CANDIDATES_PATH.read_text())
    return m.get("candidates", [])


def shasum(x: str) -> str:
    return hashlib.sha256(x.encode()).hexdigest()


def evidence_length_categories(evidence: str) -> dict:
    lines = [l for l in evidence.splitlines() if l.strip()]
    return {
        "evidence_length_chars": len(evidence),
        "evidence_length_lines": len(lines),
        "evidence_length_nonblank_tokens_approx": len(re.findall(r"\S+", evidence)),
    }


def session_depth_categories(evidence: str, context: str) -> dict:
    lines = [l for l in evidence.splitlines() if l.strip()]
    multi_cmd = len(lines) > 1
    dup_ratio = 0.0
    if lines:
        counts = {}
        for l in lines:
            counts[l] = counts.get(l, 0) + 1
        dup_ratio = max(counts.values()) / len(lines)
    return {
        "multi_line_evidence": multi_cmd,
        "duplicate_line_ratio": round(dup_ratio, 3),
        "looks_like_single_probe": multi_cmd is False or dup_ratio >= 0.7,
    }


def interactive_interpretability_score(evidence: str, context: str, source: dict) -> dict:
    """Return interpretability signals without using model predictions."""
    text = evidence
    low = text.lower()
    cmd_like_lines = [l for l in evidence.splitlines() if re.search(r"[a-zA-Z0-9_$/.\-]+\s", l)]
    has_executable_command_shape = len(cmd_like_lines) > 0
    attack_phrases = [
        "reverse shell",
        "privilege",
        "escalat",
        "exfiltrat",
        "credential",
        "shadow",
        "passwd",
        "sudo",
        "ssh",
        "scp",
        "curl",
        "wget",
        "nmap",
        "dump",
        "backdoor",
        "persist",
        "key",
        "token",
        "secret",
        "database credentials",
        "lsa",
        "ntds",
        "sam",
    ]
    has_attack_phrase = any(p in low for p in attack_phrases)
    informational = any(
        low.startswith(p)
        for p in ["what is", "explain", "describe", "how does", "show me", "can you", "i need"]
    )
    return {
        "has_executable_command_shape": has_executable_command_shape,
        "command_line_count": len(cmd_like_lines),
        "has_attack_phrase": has_attack_phrase,
        "looks_informational": informational,
        "context_available": bool(context.strip()),
    }


def near_duplicate_key(evidence: str, context: str) -> str:
    norm = re.sub(r"\s+", " ", evidence).strip().lower()
    return shasum(norm[:1000] + context[:200])


def main() -> None:
    candidates = load_candidates()
    clusters: dict[str, list[dict]] = defaultdict(list)
    rows = []
    exclusions = 0

    for i, c in enumerate(candidates):
        evidence = c["evidence"]
        context = c.get("context", "")
        source = c.get("_source", "unknown")
        source_id = c.get("_source_id", "")

        le = evidence_length_categories(evidence)
        sd = session_depth_categories(evidence, context)
        ii = interactive_interpretability_score(evidence, context, c)

        info = ii
        looks_like_single_probe = info.get("looks_like_single_probe", False)

        low_ev = evidence.lower()
        leak_flags = []
        if "ssh_e2e_simple" in low_ev:
            leak_flags.append("serving_probe_string")
        if "provider" in low_ev and "t1199" in low_ev:
            leak_flags.append("potential_provider_context_word")
        if low_ev.strip().split() == ["true"]:
            leak_flags.append("single_word_true_evidence_low_info")
        if low_ev.strip() == "exit":
            leak_flags.append("single_word_exit_evidence_low_info")

        if c.get("context", "").lower().startswith("existing ssh session transcript file with 0 attacker command"):
            leak_flags.append("empty_context")

        if not info["has_executable_command_shape"] and info["looks_informational"] and le["evidence_length_lines"] <= 2:
            suitability = "LOW"
            reason = "short informational/advisory prompt with little behavior evidence"
        elif info["has_executable_command_shape"] and le["evidence_length_lines"] >= 2 and not looks_like_single_probe:
            suitability = "HIGH"
            reason = "multi-line behavior evidence with executable command shape"
        elif info["has_executable_command_shape"] or info["has_attack_phrase"]:
            suitability = "MEDIUM"
            reason = "interpretable but limited context/depth"
        else:
            suitability = "LOW"
            reason = "insufficient interpretable behavior evidence"

        if "serving_probe_string" in leak_flags:
            suitability = "EXCLUDE"
            reason = "contains serving probe string that can reveal experiment context"

        dk = near_duplicate_key(evidence, context)
        cluster_id = f"cluster_{dk[:12]}"
        clusters[cluster_id].append(c)

        row = {
            "case_id": c["id"],
            "source_family": source,
            "source_id": source_id,
            "pool_index": i,
            "context_depth": len(context.strip()),
            "evidence_length_chars": le["evidence_length_chars"],
            "evidence_length_lines": le["evidence_length_lines"],
            "evidence_length_nonblank_tokens_approx": le["evidence_length_nonblank_tokens_approx"],
            "multi_line_evidence": sd["multi_line_evidence"],
            "duplicate_line_ratio": sd["duplicate_line_ratio"],
            "looks_like_single_probe": sd["looks_like_single_probe"],
            "has_executable_command_shape": info["has_executable_command_shape"],
            "command_line_count": info["command_line_count"],
            "has_attack_phrase": info["has_attack_phrase"],
            "looks_informational": info["looks_informational"],
            "context_available": info["context_available"],
            "annotation_suitability": suitability,
            "exclusion_reason": reason if suitability == "EXCLUDE" else None,
            "leakage_flags": leak_flags,
            "session_context_available": info["context_available"],
        }
        rows.append(row)
        if suitability == "EXCLUDE":
            exclusions += 1

    cid_map = {c["id"]: cid for cid, members in clusters.items() for c in members}
    for row in rows:
        row["duplicate_cluster_id"] = cid_map.get(row["case_id"])

    cluster_sizes = {cid: len(members) for cid, members in clusters.items()}
    for row in rows:
        row["duplicate_cluster_size"] = cluster_sizes.get(row["duplicate_cluster_id"], 1)

    with OUT_PATH.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    counts = {
        "HIGH": 0,
        "MEDIUM": 0,
        "LOW": 0,
        "EXCLUDE": 0,
    }
    for row in rows:
        counts[row["annotation_suitability"]] += 1

    print("audit rows:", len(rows))
    print("suitability counts:", counts)
    print("EXCLUDE count:", exclusions)
    print("distinct duplicate clusters:", len(clusters))
    print("clusters with size > 1:", sum(1 for s in cluster_sizes.values() if s > 1))
    print("written:", OUT_PATH)


if __name__ == "__main__":
    main()
