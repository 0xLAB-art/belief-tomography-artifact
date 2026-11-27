#!/usr/bin/env python3
"""Build the independent-label candidate pool and blinded annotation packet.

Provably model-free: reads only raw Cowrie logs + real_linux_transcripts.json,
normalizes SSH transcripts, strips all model/prediction/class metadata, assigns
opaque IDs, shuffles, and writes two artifacts:

  results/laya_research/independent_label_candidates.json  (full manifest,
    includes provenance META held separate from raters)
  results/laya_research/blind_annotation_packet.json       (packets only,
    shuffled, no class labels, no model outputs, no provenance metadata)

The blind packet is what a human rater sees. The candidates manifest keeps the
provenance/later-truth mapping in a separate file so it can be disclosed ONLY
after labels are collected, for evaluation.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import random
import re
import time
from pathlib import Path


CANDIDATES_OUT = Path("results/laya_research/independent_label_candidates.json")
PACKET_OUT = Path("results/laya_research/blind_annotation_packet.json")


def cowrie_sessions() -> dict[str, dict]:
    cowrie_files = [
        Path("data/cowrie_logs/cowrie.json.1"),
        Path("data/cowrie_logs/cowrie.json.2026-07-28"),
        Path("data/cowrie_logs/cowrie.json.2.gz"),
        Path("data/cowrie_logs/cowrie.json.3.gz"),
    ]
    sessions: dict[str, list[dict]] = {}
    for f in cowrie_files:
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

    idx: dict[str, dict] = {}
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
        idx[sid] = {
            "connect": connect,
            "logins": logins,
            "cmds": cmds,
            "failed": failed,
        }
    return idx


def real_linux_transcripts() -> list[dict]:
    real_path = Path("data/real_linux_transcripts.json")
    real = json.loads(real_path.read_text())
    out: list[dict] = []
    for i, t in enumerate(real):
        txt = t.get("transcript", "")
        lines = [l for l in txt.splitlines() if l.strip()]
        cmds: list[str] = []
        for l in lines:
            if "$" in l and "~" in l:
                mm = l.split("~", 1)
                r = mm[1] if len(mm) > 1 else ""
                if r.strip().startswith("$"):
                    cmds.append(r.strip()[1:].strip())
        if not cmds:
            continue
        out.append({"index": i, "transcript": txt, "commands": cmds})
    return out


def opaque_id(seed: str, salt: str) -> str:
    return hashlib.sha256(f"{salt}:{seed}".encode()).hexdigest()[:10]


def build_items(cowrie_idx: dict[str, dict], real_items: list[dict]) -> list[dict]:
    items: list[dict] = []
    for sid, info in cowrie_idx.items():
        cmds = info["cmds"]
        if not cmds:
            cmds = info["failed"]
        if not cmds:
            continue
        transcript = "\n".join(c.replace("CMD: ", "", 1) for c in cmds)
        seed = f"cowrie:{sid}"
        items.append(
            {
                "packet": {
                    "id": opaque_id(seed, SALT),
                    "evidence": transcript,
                },
                "meta": {
                    "provenance": "cowrie",
                    "source_id": sid,
                    "order_index": len(items),
                    "login_summary": "; ".join(info["logins"]),
                    "failed_cmds": info["failed"],
                },
            }
        )

    for it in real_items:
        seed = f"real_linux:{it['index']}"
        items.append(
            {
                "packet": {
                    "id": opaque_id(seed, SALT),
                    "evidence": it["transcript"],
                },
                "meta": {
                    "provenance": "real_linux",
                    "source_id": f"real_linux_{it['index']}",
                    "order_index": len(items),
                    "commands_extracted": it["commands"],
                },
            }
        )
    return items


SALT = "ragin-laya-independent-eval-candidates"


def main() -> None:
    CANDIDATES_OUT.parent.mkdir(parents=True, exist_ok=True)

    cowrie_idx = cowrie_sessions()
    real_items = real_linux_transcripts()
    items = build_items(cowrie_idx, real_items)

    # deterministic shuffle for reproducibility of the blind packet layout
    random.seed(20261012)
    random.shuffle(items)

    manifest = {
        "version": 1,
        "created_at": time.time(),
        "created_by": "scripts/laya_independent_candidate_pool.py",
        "n_items": len(items),
        "provenance_counts": {
            "cowrie": sum(1 for it in items if it["meta"]["provenance"] == "cowrie"),
            "real_linux": sum(1 for it in items if it["meta"]["provenance"] == "real_linux"),
        },
        "opaque_id_scheme": "sha256(salt:source_kind:source_id)[:10]",
        "salt": SALT,
        "schema": {
            "packet": {
                "id": "opaque case id",
                "evidence": "SSH transcript presented to raters (plain text; no class labels, no model outputs, no provenance metadata)",
            },
            "meta": "PROVENANCE ONLY — held separate from raters; not shown in the annotation packet; may be disclosed after labels are collected for evaluation only",
        },
        "items": items,
    }
    CANDIDATES_OUT.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    )

    packet = [it["packet"] for it in items]
    PACKET_OUT.write_text(
        json.dumps(packet, indent=2, ensure_ascii=False) + "\n"
    )

    print(f"wrote {CANDIDATES_OUT} and {PACKET_OUT}")
    print("n_items:", len(items))
    print("cowrie:", manifest["provenance_counts"]["cowrie"])
    print("real_linux:", manifest["provenance_counts"]["real_linux"])
    print("sample ids:", [it["packet"]["id"] for it in items[:5]])
    print("sample evidence preview:", items[0]["packet"]["evidence"][:120])


if __name__ == "__main__":
    main()
