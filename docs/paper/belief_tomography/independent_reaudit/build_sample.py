"""Build the blinded independent re-adjudication sample for the E29/E30/E31
oracle-flag audit (the paper's 230-flag headline).

Design
  * Universe: every session the deterministic lexical oracle flagged in the
    six frozen panels (E29, E30 Flash/Pro, E31 Flash/Pro/MiniMax) = 230.
  * Strata: panel x oracle flag (11 non-empty strata).
  * Sample: 20% per stratum, minimum 1, largest-remainder rounding.
  * Blinding: the coder sheet carries a pseudonymous item id, the oracle flag,
    and the raw probe/environment/reply turns. It carries NO panel, model,
    session id, author label, or author evidence sentence.
  * The key (id -> panel/session/author label) is written separately and is
    sealed: coders never receive it.

Usage:
  python3 build_sample.py [--demo DIR] [--out DIR] [--seed N]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
from collections import defaultdict
from pathlib import Path

PANELS = [
    ("E29", "E29_gpt-5_6-sol_p20_s2718"),
    ("E30-Flash", "E30_DeepSeek-V4-Flash_p20_s2718"),
    ("E30-Pro", "E30_DeepSeek-V4-Pro_p20_s2718"),
    ("E31-Flash", "E31_DeepSeek-V4-Flash_p20_s2718"),
    ("E31-Pro", "E31_DeepSeek-V4-Pro_p20_s2718"),
    ("E31-MiniMax", "E31_MiniMax-M3_1-Flash_p20_s2718"),
]


def load_panel(demo: Path, stem: str):
    """Return {session_id: {'family','turns':[...] ,'violated':[...]}}."""
    transcripts = defaultdict(list)
    with (demo / f"{stem}.transcripts.jsonl").open() as fh:
        for line in fh:
            r = json.loads(line)
            transcripts[r["session_id"]].append(r)
    out = {}
    with (demo / f"{stem}.verdicts.jsonl").open() as fh:
        for line in fh:
            r = json.loads(line)
            if not r.get("violated"):
                continue
            turns = sorted(transcripts.get(r["session_id"], []), key=lambda t: t["turn"])
            out[r["session_id"]] = {
                "family": r["family"],
                "violated": list(r["violated"]),
                "turns": [
                    {
                        "probe": t.get("adversary", ""),
                        "environment": t.get("environment", ""),
                        "reply": t.get("reply", ""),
                    }
                    for t in turns
                ],
            }
    return out


def largest_remainder(counts: dict, total: int) -> dict:
    quota = {k: total * v / sum(counts.values()) for k, v in counts.items()}
    alloc = {k: max(1, int(q)) for k, q in quota.items()}
    while sum(alloc.values()) > total:
        k = max((k for k in alloc if alloc[k] > 1), key=lambda k: alloc[k] - quota[k])
        alloc[k] -= 1
    while sum(alloc.values()) < total:
        k = max(quota, key=lambda k: quota[k] - alloc[k])
        alloc[k] += 1
    return alloc


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", default="/home/elaref/Documents/research/ragin/gauntlet/demo")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent))
    ap.add_argument("--seed", type=int, default=20261127)
    args = ap.parse_args()

    demo, out = Path(args.demo), Path(args.out)
    rng = random.Random(args.seed)

    strata: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for panel, stem in PANELS:
        for sid, rec in sorted(load_panel(demo, stem).items()):
            for flag in rec["violated"]:
                strata[(panel, flag)].append(
                    {"panel": panel, "session_id": sid, "family": rec["family"],
                     "flag": flag, "turns": rec["turns"]}
                )

    univ = sum(len(v) for v in strata.values())
    assert univ == 230, f"flag universe {univ} != 230"
    target = round(0.20 * univ)
    alloc = largest_remainder({k: len(v) for k, v in strata.items()}, target)

    picked: list[dict] = []
    for key, n in sorted(alloc.items()):
        picked.extend(rng.sample(strata[key], n))
    rng.shuffle(picked)

    key_rows, blind_rows = [], []
    for i, rec in enumerate(picked, 1):
        rid = f"R{i:02d}"
        author = "false_positive" if rec["flag"] == "unauthorized_action" else "genuine"
        key_rows.append({
            "id": rid, "panel": rec["panel"], "session_id": rec["session_id"],
            "family": rec["family"], "uint_flag": rec["flag"], "author_label": author,
        })
        blind_rows.append({
            "id": rid, "oracle_flag": rec["flag"],
            "turns": rec["turns"],
        })

    sample = out / "sample_blind.jsonl"
    key = out / "key_author_labels.jsonl"
    sample.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in blind_rows))
    key.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in key_rows))

    meta = {
        "seed": args.seed,
        "universe": univ,
        "sample_size": len(blind_rows),
        "allocation": {f"{p}|{f}": n for (p, f), n in sorted(alloc.items())},
        "stratum_sizes": {f"{p}|{f}": len(v) for (p, f), v in sorted(strata.items())},
        "sha256_sample_blind": hashlib.sha256(sample.read_bytes()).hexdigest(),
        "sha256_key": hashlib.sha256(key.read_bytes()).hexdigest(),
        "blinding": "coder sheet has id, oracle flag, raw turns only; no panel/model/session/label",
    }
    (out / "sample_meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
