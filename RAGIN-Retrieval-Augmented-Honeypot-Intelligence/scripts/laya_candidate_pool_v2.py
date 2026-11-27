#!/usr/bin/env python3
"""Build expanded independent-label candidate pool v2 (maximally defensible pool).

Sources (in priority order):
1. data/cowrie_logs/ (historical controlled Cowrie sessions)
2. data/real_linux_transcripts.json (real admin-style transcripts)
3. data/sessions/*.jsonl (human_eval style sessions, attacker_input commands)

Output:
- results/laya_research/independent_label_candidates_v2.json
- results/laya_research/blind_annotation_packet_v2.json
- results/laya_research/annotation_manifest_v2.json

This script does NOT assign labels. It only builds a blinded, de-duplicated,
stratified candidate set from raw provenance-preserving material.

Leakage screening:
- Remove examples whose evidence contains obvious prompt-stuffing leakage
  tokens that would reveal evaluation context, e.g. the exact proof probe
  string used in serving validation.
- Flag words like "provider", "label", "true", "score" are NOT auto-rejected
  because they can appear in legitimate English cybersecurity text; instead
  only the specific serving probe string is excluded.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import re
import random
import time
from pathlib import Path
from collections import Counter

OUT_DIR = Path("results/laya_research")
OUT_DIR.mkdir(parents=True, exist_ok=True)

CANDIDATES_V2 = OUT_DIR / "independent_label_candidates_v2.json"
PACKET_V2 = OUT_DIR / "blind_annotation_packet_v2.json"
MANIFEST_V2 = OUT_DIR / "annotation_manifest_v2.json"

SALT = "ragin-laya-independent-eval-v2"
SEED = 20261012

# Specific serving-probe strings found to leak evaluation context.
EXCLUDED_EVIDENCE_TOKENS = [
    "SSH_E2E_SIMPLE_1791701077",
]


def opaque_id(seed: str) -> str:
    return hashlib.sha256(f"{SALT}:{seed}".encode()).hexdigest()[:12]


def contains_excluded_token(text: str) -> bool:
    low = text.lower()
    for token in EXCLUDED_EVIDENCE_TOKENS:
        if token.lower() in low:
            return True
    return False


def cowrie_pool() -> list[dict]:
    files = [
        Path("data/cowrie_logs/cowrie.json.1"),
        Path("data/cowrie_logs/cowrie.json.2026-07-28"),
        Path("data/cowrie_logs/cowrie.json.2.gz"),
        Path("data/cowrie_logs/cowrie.json.3.gz"),
    ]
    sessions: dict[str, list[dict]] = {}
    for f in files:
        if not f.exists():
            continue
        opener = gzip.open if f.suffix == ".gz" else open
        with opener(f, "rt", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                except Exception:
                    continue
                sid = ev.get("session") or ev.get("session_id")
                if sid and ev.get("eventid"):
                    sessions.setdefault(sid, []).append(ev)

    out = []
    for sid, evs in sessions.items():
        cmds, logins, connect, failed = [], [], None, []
        for e in evs:
            m = e.get("message") or ""
            if e.get("eventid") == "cowrie.session.connect":
                connect = m
            elif e.get("eventid") in ("cowrie.login.success", "cowrie.login.failed"):
                logins.append(m)
            elif e.get("eventid") == "cowrie.command.input":
                cmds.append(m)
            elif e.get("eventid") == "cowrie.command.failed":
                failed.append(m)
        if not cmds and not failed:
            continue
        used = cmds or failed
        transcript = "\n".join(
            c.replace("CMD: ", "", 1) if c.startswith("CMD:") else c for c in used
        )
        out.append(
            {
                "source": "cowrie",
                "source_id": sid,
                "session_index": None,
                "evidence": transcript,
                "context": (
                    f"Historical controlled Cowrie SSH session. Login: {'; '.join(logins) or 'none'}. "
                    f"Session connect: {'yes' if connect else 'no'}."
                ),
                "strata_hints": {
                    "is_honeypot_source": True,
                    "login_info": "; ".join(logins),
                },
            }
        )
    return out


def real_linux_pool() -> list[dict]:
    real = json.loads(Path("data/real_linux_transcripts.json").read_text())
    out = []
    for i, t in enumerate(real):
        txt = t.get("transcript", "")
        cmds = []
        for line in txt.splitlines():
            if line.strip() and "$" in line and "~" in line:
                mm = line.split("~", 1)
                r = mm[1] if len(mm) > 1 else ""
                if r.strip().startswith("$"):
                    cmds.append(r.strip()[1:].strip())
        if not cmds:
            continue
        out.append(
            {
                "source": "real_linux",
                "source_id": f"real_linux_{i}",
                "session_index": i,
                "evidence": txt,
                "context": "Real Linux administration-style transcript (sysadmin@srv-01).",
                "strata_hints": {
                    "is_honeypot_source": False,
                    "username": "sysadmin",
                },
            }
        )
    return out


def sessions_pool() -> list[dict]:
    files = sorted(Path("data/sessions").glob("*.jsonl"))
    out = []
    for p in files:
        try:
            lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        except Exception:
            continue
        cmds = []
        for line in lines:
            if not line.strip():
                continue
            try:
                e = json.loads(line)
            except Exception:
                continue
            if e.get("event_type") == "attacker_input":
                c = e.get("data", {}).get("command", "")
                if c:
                    cmds.append(c)
        if not cmds:
            continue
        transcript = "\n".join(cmds)
        out.append(
            {
                "source": "sessions",
                "source_id": p.name,
                "session_index": None,
                "evidence": transcript,
                "context": (
                    f"Existing SSH session transcript file with {len(cmds)} attacker command(s). "
                    "No model outputs or labels included in evidence."
                ),
                "strata_hints": {
                    "is_honeypot_source": False,
                    "file_name_hidden_from_raters": True,
                },
            }
        )
    return out


def normalize_evidence(evidence: str) -> str:
    lines = [l.rstrip() for l in evidence.splitlines()]
    collapsed = []
    for l in lines:
        if len(collapsed) >= 2 and l == collapsed[-1] == collapsed[-2]:
            continue
        collapsed.append(l)
    return "\n".join(collapsed)


def build_candidate(item: dict, pool_index: int) -> dict:
    evidence = normalize_evidence(item["evidence"])
    return {
        "id": opaque_id(f"{item['source']}:{item['source_id']}:{item.get('session_index', '')}"),
        "evidence": evidence,
        "context": item.get("context", ""),
        "_strata_hints": item.get("strata_hints", {}),
        "_source": item["source"],
        "_source_id": item["source_id"],
        "_pool_index": pool_index,
    }


def main() -> None:
    t0 = time.time()
    cowrie = cowrie_pool()
    real_linux = real_linux_pool()
    sessions = sessions_pool()

    candidates = []
    for pool, label in [(cowrie, "cowrie"), (real_linux, "real_linux"), (sessions, "sessions")]:
        for i, item in enumerate(pool):
            c = build_candidate(item, len(candidates))
            c["_pool_type"] = label
            candidates.append(c)

    # Leakage screen: exclude evidence containing serving-probe leakage tokens.
    screened = [c for c in candidates if not contains_excluded_token(c["evidence"])]

    seen: set[tuple[str, str]] = set()
    distinct = []
    for c in screened:
        key = (c["evidence"], c["context"])
        if key in seen:
            continue
        seen.add(key)
        distinct.append(c)

    random.seed(SEED)
    random.shuffle(distinct)

    packet = [
        {
            "id": c["id"],
            "evidence": c["evidence"],
            "context": c["context"],
        }
        for c in distinct
    ]

    manifest = {
        "version": 1,
        "created_at": t0,
        "created_by": "scripts/laya_candidate_pool_v2.py",
        "salt": SALT,
        "opaque_id_scheme": "sha256(salt:source:source_id:session_index)[:12]",
        "n_raw_candidates": len(candidates),
        "n_after_leakage_screen": len(screened),
        "n_distinct_candidates": len(distinct),
        "excluded_by_leakage_screen": len(candidates) - len(screened),
        "source_distribution": {
            "cowrie": sum(1 for c in distinct if c["_source"] == "cowrie"),
            "real_linux": sum(1 for c in distinct if c["_source"] == "real_linux"),
            "sessions": sum(1 for c in distinct if c["_source"] == "sessions"),
        },
        "strata_present": True,
        "schema": {
            "packet": {
                "id": "opaque case id",
                "evidence": "SSH/session evidence presented to raters (no model output, no labels, no arm names)",
                "context": "optional minimal preceding context needed to interpret the action",
            },
            "candidate_pool": {
                "note": "provenance/meta kept separately; not part of the blinded packet",
                "fields_hidden_from_raters": ["_source", "_source_id", "_pool_index", "_pool_type", "_strata_hints"],
            },
        },
        "candidates": distinct,
    }

    CANDIDATES_V2.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    PACKET_V2.write_text(json.dumps(packet, indent=2, ensure_ascii=False) + "\n")
    MANIFEST_V2.write_text(
        json.dumps(
            {
                "created_at": t0,
                "purpose": "annotation experiment manifest for Laya vs Chrollo independent evaluation",
                "packet": "blind_annotation_packet_v2.json",
                "candidate_pool": "independent_label_candidates_v2.json",
                "rater_templates_dir": "results/laya_research/rater_templates",
                "rater_labels_dir": "results/laya_research/rater_labels",
                "annotation_taxonomy": [
                    "BENIGN",
                    "RECON",
                    "SUSPICIOUS",
                    "EXPLOITATION",
                    "PRIVILEGE_ESCALATION",
                    "DATA_ACCESS",
                    "PERSISTENCE",
                    "OTHER_ATTACK",
                    "UNCERTAIN",
                ],
                "binary_projection": {
                    "BENIGN": "benign",
                    "RECON": "malicious",
                    "SUSPICIOUS": "malicious",
                    "EXPLOITATION": "malicious",
                    "PRIVILEGE_ESCALATION": "malicious",
                    "DATA_ACCESS": "malicious",
                    "PERSISTENCE": "malicious",
                    "OTHER_ATTACK": "malicious",
                    "UNCERTAIN": "excluded",
                },
                "adjudication_policy": {
                    "primary_rule": "majority vote where at least 2/3 agree",
                    "disagreement_rule": "retain all original labels, flag for adjudication, never rewrite original rater files",
                    "agreement_measures": [
                        "raw agreement",
                        "pairwise agreement",
                        "Fleiss kappa or equivalent",
                        "percentage UNCERTAIN",
                        "category-specific disagreement",
                    ],
                },
                "acceptance_rule": "proceed to primary comparison if enough adjudicated cases remain and agreement is defensible; otherwise classify as exploratory",
                "examples_dir": "results/laya_research/annotation_examples",
                "note": "Examples used in instructions must NOT be members of the evaluation set.",
                "leakage_screen": {
                    "excluded_tokens": EXCLUDED_EVIDENCE_TOKENS,
                    "reason": "remove obvious serving-probe leakage from evidence",
                },
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    )

    print("wrote", CANDIDATES_V2, PACKET_V2, MANIFEST_V2)
    print("raw candidates:", len(candidates))
    print("after leakage screen:", len(screened))
    print("distinct candidates:", len(distinct))
    print("source distribution:", manifest["source_distribution"])


if __name__ == "__main__":
    main()
