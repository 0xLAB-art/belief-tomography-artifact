#!/usr/bin/env python3
"""Prediction-blind candidate quality audit for the Laya independent eval pool.

This script characterizes each of the 307 distinct candidates using only
observable evidence and provenance metadata. It must NOT consult Chrollo,
Laya, confidence, disagreement, or any model-prediction field when deciding
quality labels. It outputs a JSONL audit so later curation steps can be
reviewed independently of the confirmatory subset selection.

Output:
    results/laya_research/candidate_quality_audit.jsonl
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
POOL = REPO / "results/laya_research/independent_label_candidates_v2.json"
MANIFEST = REPO / "results/laya_research/annotation_manifest_v2.json"


# ══════════════════════════════════════════════════════════════════════════════
# Leakage terms
# ══════════════════════════════════════════════════════════════════════════════

# Phrases whose mere presence in a rater-facing transcript would reveal
# experiment state, served model, or ground-truth meta. These are NOT
# generic English stop words.
LEAKAGE_PHRASES = [
    "SERVER_SPACE_BUNNY",
    "SPACE_BUNNY_PIPELINE_PROBE",
    "PIPELINE_WIRE_PROOF",
    "RAGIN_WIRE_PROOF",
    "COWRIE_BACKEND",
    "SSH_WIRE_PROOF_OK",
    "RAGIN_VERIFIED_OK",
    "AUTH_OK",
    "WIRE_PROOF",
    "RAGIN_WIRE",
    "DIRECT_COWRIE_BACKEND",
    "DIRECT_SERVER_SPACE_BUNNY",
    # Experiment/serving markers found by manual review of the final packet:
    "SPACE_BUNNY",           # serving-path probe marker
    "DEFINITIVE_",           # timestamped experiment verification marker
    "final_evidence_ping",   # experiment verification marker
    "RAGIN",                 # system/experiment identity in rater-facing text
]


def flagged_leakage_terms(evidence: str) -> list[str]:
    """Return which leakage phrases appear in *evidence*."""
    out: list[str] = []
    for phrase in LEAKAGE_PHRASES:
        if phrase in evidence:
            out.append(phrase)
    return out


def has_generic_touch_terms(evidence: str) -> bool:
    """Mark whether the evidence contains generic English words that should
    not, by themselves, be treated as leakage."""
    lowered = evidence.lower()
    generic = ["true", "provider"]
    return any(word in lowered.split() for word in generic)


# ══════════════════════════════════════════════════════════════════════════════
# Text evidence quality
# ══════════════════════════════════════════════════════════════════════════════

def readable_char_ratio(text: str) -> float:
    """Approximate fraction of characters that are readable/printable-ish."""
    if not text:
        return 0.0
    return sum(1 for ch in text if ch.isprintable() or ch in "\n\r\t") / len(text)


def estimated_context_depth(evidence: str) -> str:
    """Coarse observable context-depth grain. This is NOT a semantic label.

    - SHALLOW  : single-command transcript, or < ~5 lines
    - MODERATE : several commands / multi-line system output
    - DEEP     : long transcript with interleaved prompt + output
    """
    lines = [ln for ln in evidence.splitlines() if ln.strip()]
    stripped_chars = len(" ".join(lines))

    if stripped_chars < 80:
        return "SHALLOW"
    if stripped_chars < 500:
        return "MODERATE"

    # deeper: more than ~12 non-trivial lines is a heuristic only
    if len(lines) >= 12 and stripped_chars >= 500:
        return "DEEP"

    return "MODERATE"


def command_like_line_count(evidence: str) -> int:
    """Rough count of lines that look like attacker commands rather than
    system output. This is an observable proxy for session richness only."""
    countable = 0
    for ln in evidence.splitlines():
        s = ln.strip()
        if not s:
            continue
        # Many honeypot transcripts have 'prompt$ cmd' style lines.
        if re.search(r"[$#>]\s+\S", s):
            countable += 1
            continue
        # bare commands that are short and not obviously output
        if re.match(r"^[a-zA-Z0-9/._-]+(\s+\S+)?$", s) and 2 <= len(s) <= 120:
            countable += 1
    return countable


def interpretability_score(evidence: str, context: str) -> str:
    """Coarse, observable interpretability score.

    - INTERPRETABLE : evidence looks like real commands / outputs a rater can
      map to behavior.
    - PARTIAL       : some structure but mostly noise, synthetic strings, or
      questions about technique definitions.
    - NOT_INTERPRETABLE : basically not usable (empty, pure noise, pure
      technique-definition questions).

    This is a prediction-blind evidence-quality proxy, NOT a security label.
    """
    stripped = evidence.strip()
    if not stripped or stripped.lower() in {"true", "exit", "test", "echo hi", "echo hello"}:
        return "NOT_INTERPRETABLE"

    lines = [ln for ln in stripped.splitlines() if ln.strip()]
    if not lines:
        return "NOT_INTERPRETABLE"

    # Pure question-only evidence about technique definitions is hard to security
    # label from transcript shape alone.
    question_answer_only = all(
        re.match(r"^(what|explain|describe|how|tell me|can you|show me|list|check|which)\b", ln.strip(), re.I)
        or ln.strip().startswith("true")
        for ln in lines
    )
    if question_answer_only and command_like_line_count(evidence) == 0:
        if len(lines) <= 2:
            return "NOT_INTERPRETABLE"
        return "PARTIAL"

    # presence of real-looking system output / prompt patterns is a positive
    # signal for interpretability.
    has_output_pattern = bool(
        re.search(r"(Filesystem|Mem:|Swap:|USER|PID|Netid|State|Local Address|drwx|total\s+\d+)", evidence)
    ) or bool(
        re.search(r"(\d+\.\d+\.\d+\.\d+|\d+\.\d+\.\d+\.\d+/\d+)", evidence)
    )

    if has_output_pattern or command_like_line_count(evidence) >= 2:
        return "INTERPRETABLE"

    if command_like_line_count(evidence) == 1:
        return "PARTIAL"

    return "PARTIAL"


def likely_contains_technique_definitions_only(evidence: str) -> bool:
    """Return True when the evidence is essentially a list of 'Explain Txxxx'
    style technique-definition prompts without concrete system behavior.

    This is a prediction-blind triage flag.
    """
    stripped = evidence.strip()
    if not stripped:
        return False
    lines = [ln.strip() for ln in stripped.splitlines() if ln.strip()]
    if not lines:
        return False

    technique_line_ratio = sum(
        1 for ln in lines
        if re.match(r"^(explain|describe|what is|how does)\b.*\bT\d{4}", ln, re.I)
    ) / max(1, len(lines))
    return technique_line_ratio >= 0.6 and len(lines) >= 2


# ══════════════════════════════════════════════════════════════════════════════
# Deduplication (determinism-friendly)
# ══════════════════════════════════════════════════════════════════════════════

def normalized_text(text: str) -> str:
    """Lightweight normalization for dedup sim: collapse whitespace, NFC, trim."""
    text = unicodedata.normalize("NFC", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def text_fingerprint(text: str) -> str:
    """A lightweight min-hash-adjacent deterministic fingerprint for clustering.

    Uses token-set-based hashing plus character bigram sketches for a stable
    similarity signal without importing heavy libs.
    """
    norm = normalized_text(text)
    tokens = set(re.findall(r"\w+", norm))
    token_key = ",".join(sorted(tokens))
    bigrams = set(norm[i:i+2] for i in range(len(norm) - 1))
    bigram_key = ",".join(sorted(bigrams))
    return token_key + " ||| " + bigram_key


def pairwise_similarity(a: str, b: str) -> float:
    """Sequence-matcher based similarity on normalized evidence."""
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, normalized_text(a), normalized_text(b)).ratio()


# ══════════════════════════════════════════════════════════════════════════════
# Quality classification
# ══════════════════════════════════════════════════════════════════════════════

def audit_one(c: dict) -> dict:
    """Audit a single candidate. No model predictions consulted."""
    evidence = c.get("evidence", "")
    context = c.get("context", "")
    stratum = c.get("_strata_hints", {})

    source = c.get("_source", "unknown")
    is_honeypot_source = bool(stratum.get("is_honeypot_source"))

    interp = interpretability_score(evidence, context)
    depth = estimated_context_depth(evidence)
    cmd_count = command_like_line_count(evidence)
    leakage_terms = flagged_leakage_terms(evidence)
    generic_touch = has_generic_touch_terms(evidence)
    tech_def_only = likely_contains_technique_definitions_only(evidence)
    readable = readable_char_ratio(evidence)

    # Exclusion logic
    exclusion_reason: str | None = None
    if leakage_terms:
        exclusion_reason = "leakage_phrase_in_evidence"
    elif not readable or evidence.strip().lower() in {
        "true", "exit", "test", "echo hi", "echo hello", "asdfjqyz", "bridge_ping",
        "fortune", "hostname", "ping_id_only", "uid", "ls", "ls\nls",
    }:
        exclusion_reason = "trivial_or_noise_only"
    elif tech_def_only and interp != "INTERPRETABLE":
        exclusion_reason = "technique_definitions_only_no_behavior"
    elif not evidence.strip():
        exclusion_reason = "empty_evidence"
    else:
        # keep everything else in the audit even if it is only low quality
        exclusion_reason = None

    # Quality banding (prediction-blind)
    quality: str
    if exclusion_reason:
        quality = "EXCLUDE"
    elif interp == "INTERPRETABLE" and depth in ("DEEP",) and cmd_count >= 2:
        quality = "HIGH"
    elif interp == "INTERPRETABLE" and cmd_count >= 1:
        quality = "MEDIUM"
    elif interp == "PARTIAL":
        quality = "LOW"
    else:
        quality = "LOW"

    return {
        "case_id": c["id"],
        "source_family": source,
        "is_honeypot_source": is_honeypot_source,
        "context_depth": depth,
        "evidence_length_chars": len(evidence),
        "evidence_length_lines": evidence.count("\n") + 1 if evidence else 0,
        "command_like_line_estimate": cmd_count,
        "readable_char_ratio": round(readable, 3),
        "interpretability": interp,
        "technique_definitions_only": tech_def_only,
        "quality_band": quality,
        "exclusion_reason": exclusion_reason,
        "leakage_terms": leakage_terms,
        "generic_touch_terms_present": generic_touch,
        "session_context_available": bool(context and context.strip()),
    }


# ══════════════════════════════════════════════════════════════════════════════
# Dedup clustering
# ══════════════════════════════════════════════════════════════════════════════

DEDUP_SIMILARITY_THRESHOLD = 0.86


def build_duplicate_clusters(pool_by_id: dict[str, dict]) -> list[dict]:
    """Group near-duplicates using deterministic pairwise similarity.

    For the small n=307 case set, pairwise is acceptable. We assign cluster
    ids so downstream curation can prefer one representative per cluster.

    Evidence text comes from the original pool (same as blind packet evidence
    for non-excluded cases), not from the quality audit summary.
    """
    ids = list(pool_by_id.keys())
    evidence = {cid: pool_by_id[cid]["evidence"] for cid in ids}

    n = len(ids)
    sim: dict[tuple[str, str], float] = {}
    for i in range(n):
        for j in range(i + 1, n):
            a, b = ids[i], ids[j]
            sim[(a, b)] = pairwise_similarity(evidence[a], evidence[b])

    # Union-find-style connected components above threshold
    parent: dict[str, str] = {cid: cid for cid in ids}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a_: str, b_: str) -> None:
        ra, rb = find(a_), find(b_)
        if ra != rb:
            parent[ra] = rb

    for (a, b), s in sim.items():
        if s >= DEDUP_SIMILARITY_THRESHOLD:
            union(a, b)

    clusters: dict[str, list[str]] = {}
    for cid in ids:
        root = find(cid)
        clusters.setdefault(root, []).append(cid)

    out: list[dict] = []
    for root, members in clusters.items():
        rep = members[0]
        out.append({
            "cluster_id": f"cluster-{hashlib.sha256(root.encode()).hexdigest()[:10]}",
            "representative_id": rep,
            "member_ids": sorted(members),
            "member_count": len(members),
            "max_pairwise_similarity": round(
                max(
                    (sim.get((min(x, y), max(x, y)), 0.0) for x in members for y in members if x != y),
                    default=0.0,
                ),
                3,
            ),
        })
    return out


# ══════════════════════════════════════════════════════════════════════════════
# Confirmatory subset construction (prediction-blind, stratified)
# ══════════════════════════════════════════════════════════════════════════════

def select_confirmatory_subset(
    audit: list[dict],
    clusters: list[dict],
    target_n: int = 120,
    min_n: int = 100,
    max_n: int = 150,
    seed: int = 20261012,
) -> dict:
    """Build a defensible confirmatory set using only evidence-quality signals.

    Rules:
    - Exclude all cases already flagged EXCLUDE.
    - One representative per duplicate cluster unless additional members have
      materially distinct evidence shape (we conservatively keep one per
      cluster for a clean confirmatory set).
    - Stratified sampling across observable evidence characteristics.
    - No model predictions consulted.
    """
    random = __import__("random")
    rng = random.Random(seed)

    cluster_map = {m: c["cluster_id"] for c in clusters for m in c["member_ids"]}
    rep_by_cluster = {c["cluster_id"]: c["representative_id"] for c in clusters}
    in_cluster = set(rep_by_cluster.values())

    # Apply exclusion + dedup to candidate pool
    eligible: list[dict] = []
    for row in audit:
        cid = row["case_id"]
        if row["quality_band"] == "EXCLUDE":
            continue
        if cid not in in_cluster:
            continue
        eligible.append(row)

    # Stratify
    strata: dict[str, list[dict]] = {}
    for row in eligible:
        key = (row["source_family"], row["context_depth"], row["interpretability"])
        strata.setdefault(key, []).append(row)

    # Greedy proportional allocation with floor guarantees for small strata
    allocated: dict[str, list[dict]] = {k: [] for k in strata}
    remaining_n = target_n

    # sort strata by size descending, allocate proportionally
    keys_sorted = sorted(strata.keys(), key=lambda k: len(strata[k]), reverse=True)
    total = len(eligible)

    # First pass: proportional
    alloc_counts: dict[str, int] = {}
    allocated_total = 0
    for k in keys_sorted:
        size = len(strata[k])
        prop = max(1, round(target_n * size / total)) if total else 0
        alloc_counts[k] = min(prop, size)
        allocated_total += alloc_counts[k]

    # Adjust down/up to fit target
    diff = allocated_total - target_n
    if diff > 0:
        # trim from largest strata first
        for k in keys_sorted:
            if diff <= 0:
                break
            can = min(alloc_counts[k] - 1, len(strata[k]) - 1)
            trim = min(can, diff)
            alloc_counts[k] -= trim
            diff -= trim
    elif diff < 0:
        need = -diff
        for k in keys_sorted:
            if need <= 0:
                break
            can = len(strata[k]) - alloc_counts[k]
            add = min(can, need)
            alloc_counts[k] += add
            need -= add

    # Now actually pick within each stratum, deterministically shuffled
    selected: list[dict] = []
    for k in keys_sorted:
        pool_k = list(strata[k])
        rng.shuffle(pool_k)
        chosen = pool_k[: alloc_counts[k]]
        selected.extend(chosen)
        allocated[k] = [c["case_id"] for c in chosen]

    # If we still don't have enough, relax cluster exclusivity temporarily by
    # adding next-best representative-adjacent members (only if needed to reach
    # min_n). This preserves blind selection semantics because we still never
    # inspect predictions.
    if len(selected) < min_n:
        extra_pool = [r for r in eligible if r["case_id"] not in {s["case_id"] for s in selected}]
        rng.shuffle(extra_pool)
        selected.extend(extra_pool[: max(0, min_n - len(selected))])

    # If we somehow exceed max_n, trim weakest quality first
    if len(selected) > max_n:
        order = {
            "LOW": 0,
            "MEDIUM": 1,
            "HIGH": 2,
        }
        selected_sorted = sorted(
            selected,
            key=lambda r: (order.get(r["quality_band"], 0), -r["evidence_length_chars"]),
        )
        selected = selected_sorted[:max_n]

    selected_ids = [r["case_id"] for r in selected]
    selected_set = set(selected_ids)

    # Quality distribution within selected set
    quality_dist = dict(Counter(r["quality_band"] for r in selected))
    source_dist = dict(Counter(r["source_family"] for r in selected))
    depth_dist = dict(Counter(r["context_depth"] for r in selected))

    # Duplicate cluster policy summary
    cluster_ids_in_selection = {cluster_map[cid] for cid in selected_ids if cid in cluster_map}

    return {
        "selection_version": "v1",
        "selection_timestamp": 0,  # filled by caller
        "selection_seed": seed,
        "total_candidates_before": len(audit),
        "excluded_count": len([r for r in audit if r["quality_band"] == "EXCLUDE"]),
        "selected_count": len(selected_ids),
        "source_distribution": source_dist,
        "quality_distribution": quality_dist,
        "context_depth_distribution": depth_dist,
        "duplicate_cluster_count_in_selection": len(cluster_ids_in_selection),
        "duplicate_cluster_policy": (
            "One representative per near-duplicate cluster was selected; "
            "no cluster contributed more than one case to the confirmatory set "
            "unless it was required to reach min_n."
        ),
        "selection_algorithm": (
            "Prediction-blind stratified selection over evidence quality + source + "
            "context depth, with proportional allocation and deterministic random shuffle "
            "seeded by selection_seed. Model predictions were NOT consulted."
        ),
        "blind_selection": True,
        "model_predictions_consulted": False,
        "strata_used": [
            f"{src}/{depth}/{interp}:{len(strata[(src, depth, interp)])}"
            for (src, depth, interp) in sorted(strata.keys())
        ],
        "selected_case_ids": sorted(selected_ids),
        "strata_allocation": allocated,
        "excluded_ids": sorted([r["case_id"] for r in audit if r["quality_band"] == "EXCLUDE"]),
        "soft_excluded_by_leakage": [r["case_id"] for r in audit if r["leakage_terms"]],
    }


# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    pool = json.loads(POOL.read_text())
    cands = pool["candidates"]
    manifest = json.loads(MANIFEST.read_text())

    audit_rows = [audit_one(c) for c in cands]

    out_dir = REPO / "results/laya_research"
    out_dir.mkdir(parents=True, exist_ok=True)

    # JSONL audit
    audit_path = out_dir / "candidate_quality_audit.jsonl"
    audit_path.write_text(
        "\n".join(json.dumps(r, sort_keys=True) for r in audit_rows) + "\n"
    )

    # NOTE: audit_rows intentionally do not include the raw evidence text; they
    # are an evidence-QUALITY summary computed without leaking prediction fields.
    # For dedup we go back to the original pool candidate evidence, which is the
    # same text already screened for leakage.
    pool_by_id = {c["id"]: c for c in cands}

    # Dedup clusters
    clusters = build_duplicate_clusters(pool_by_id)
    clusters_path = out_dir / "deduplication_clusters.json"
    clusters_path.write_text(json.dumps(clusters, indent=2) + "\n")

    # Summary snapshot
    quality_counts = dict(Counter(r["quality_band"] for r in audit_rows))
    excluded_ids = [r["case_id"] for r in audit_rows if r["quality_band"] == "EXCLUDE"]
    leakage_ids = [r["case_id"] for r in audit_rows if r["leakage_terms"]]

    # Sanity check: every pool candidate should map to exactly one pool row
    missing_in_pool = [cid for cid in {c["id"] for c in cands} if cid not in pool_by_id]
    if missing_in_pool:
        raise SystemExit(f"pool_by_id missing these case_ids: {missing_in_pool[:20]}")
    missing_evidence_in_pool = [cid for cid in pool_by_id if "evidence" not in pool_by_id[cid]]
    if missing_evidence_in_pool:
        raise SystemExit(f"pool candidates missing 'evidence' for these case_ids: {missing_evidence_in_pool[:20]}")

    summary = {
        "version": 1,
        "created_at": pool.get("created_at"),
        "created_by": "scripts/laya_candidate_quality_audit.py",
        "total_candidates": len(audit_rows),
        "quality_distribution": quality_counts,
        "excluded_count": len(excluded_ids),
        "excluded_ids": excluded_ids,
        "leakage_phrase_ids": leakage_ids,
        "dedup_cluster_count": len(clusters),
        "cluster_member_count_sum": sum(c["member_count"] for c in clusters),
        "dedup_threshold": DEDUP_SIMILARITY_THRESHOLD,
        "manifest_schema_hash": hashlib.sha256(
            json.dumps(manifest, sort_keys=True, default=str).encode()
        ).hexdigest(),
        "pool_meta": {
            "version": pool.get("version"),
            "n_distinct_candidates": pool.get("n_distinct_candidates"),
            "source_distribution": pool.get("source_distribution"),
        },
    }

    summary_path = out_dir / "candidate_quality_audit_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n")

    print("Wrote", audit_path)
    print("Wrote", clusters_path)
    print("Wrote", summary_path)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
