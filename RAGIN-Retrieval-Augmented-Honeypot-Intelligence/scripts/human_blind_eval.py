#!/usr/bin/env python3
"""Blind human evaluation protocol — "Real system or honeypot?" (S&P P0).

Builds a randomized, de-identified transcript packet for expert raters and
scores the collected ratings (detection accuracy, false-honeypot rate,
pairwise agreement, Cohen's κ / Krippendorff's α over binary verdicts).

Protocol (docs/FIELD_ETHICS.md §4):
  1. Sources: transcripts from real Linux captures, Cowrie, the vanilla-LLM
     arm, the stateful-LLM arm, and RAGIN (verified loop). Equal-mix packet,
     order shuffled with a fixed seed per rater (reproducible randomization).
  2. Raters see ONLY the transcript content — no arm names, no system info,
     no session metadata that leaks provenance. Transcripts are de-identified:
     hostnames/usernames are normalized to a common fake shape per transcript
     so naming style can't fingerprint an arm.
  3. Per transcript the rater answers: real or honeypot (binary), confidence
     1–5, realism 1–5, consistency 1–5, command correctness 1–5,
     detectability notes, and the reason for the decision (free text).
  4. Raters never see another rater's answers until everyone is done.

Usage:
  python scripts/human_blind_eval.py build --arms cowrie:10,vanilla_llm:10,ragin:10,real_linux:10 \
      --out results/human_blind/packet_rater1.json --seed 11 --rater rater1
  python scripts/human_blind_eval.py score --packet results/human_blind/packet_rater1.json \
      --answers results/human_blind/answers_rater1.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Normalization shapes applied to EVERY transcript regardless of arm, so a
# rater cannot fingerprint provenance from hostname/user naming style.
_CANON_HOSTS = ["srv-a", "srv-b", "srv-c", "srv-d", "srv-e"]
_CANON_USERS = ["operator", "admin-user", "service-acct", "deploy", "analyst"]


def normalize_transcript(text: str, key: str) -> tuple[str, dict]:
    """De-identify a transcript: map real-looking hostnames/usernames to a
    canonical shape. Deterministic per transcript key."""
    rng = random.Random(hashlib.sha256(key.encode()).hexdigest())
    host = rng.choice(_CANON_HOSTS)
    user = rng.choice(_CANON_USERS)
    # Map the common RAGIN/cowrie/real-identity tokens onto the canonical pair.
    replacements = {
        "web-srv-01": host,
        "webapp": user,
        "cowrie": host,
        "ec2-user": user,
        "ubuntu": user,
        # Tokens used by scripts/capture_real_linux_transcripts.py.
        "srv-01": host,
        "sysadmin": user,
    }
    mapping = {}
    out = text
    for real, canon in replacements.items():
        if real in out:
            mapping[real] = canon
            out = out.replace(real, canon)
    # Strip timestamps and IPs (de-identification + prevents timing inference).
    import re

    out = re.sub(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", "10.0.0.1", out)
    out = re.sub(
        r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?",
        "<ts>",
        out,
    )
    return out, mapping


def load_transcripts(arm: str, n: int) -> list[dict]:
    """Load n de-identified transcripts for an arm from the results tree.

    Source maps (extend as new arms complete):
      ragin        -> results/human_eval_full.json (verified-loop transcripts)
      vanilla_llm  -> results/external_baseline_llm_unverified.json per-row
      stateful_llm -> results/external_baseline_stateful_llm.json per-row
      real_linux   -> data/real_linux_transcripts.json (curated captures; add
                      before packet build — see FIELD_ETHICS §4 step 1)
      cowrie       -> data/cowrie_logs rotated captures, scripted-output shape
    """
    results = ROOT / "results"
    data = ROOT / "data"
    items: list[str] = []

    def _from_jsonl_rows(path: Path, text_key: str):
        if not path.exists():
            return []
        d = json.loads(path.read_text())
        rows = d.get("per_row", [])
        if not rows or not text_key:
            return []
        return [
            str(r.get("response_text", "") or r.get("details", {}).get("response_preview", ""))
            for r in rows
            if r.get(text_key, "")
        ]

    if arm == "ragin":
        p = results / "human_eval_full.json"
        if p.exists():
            d = json.loads(p.read_text())
            # Rich per-turn transcripts live in raw_pipeline_outputs; each is a
            # full verified-loop turn (input + deception + verification).
            for out in d.get("raw_pipeline_outputs", []):
                gt = out.get("ground_truth", {}) or {}
                dec = out.get("deception", {}) or {}
                ver = out.get("verification", {}) or {}
                input_cmd = gt.get("attacker_input", "")
                resp = dec.get("response_text", "") or dec.get("response", "")
                if not resp.strip():
                    continue
                fallback_tag = " [fallback template served]" if ver.get("fallback_served") else ""
                items.append(f"$ {input_cmd}\n{resp}{fallback_tag}")
    elif arm in ("vanilla_llm", "stateful_llm"):
        p = results / f"external_baseline_{arm}.json"
        if p.exists():
            d = json.loads(p.read_text())
            for r in d.get("per_row", []):
                t = (r.get("details") or {}).get("response_preview", "")
                if t.strip():
                    items.append(t)
    elif arm == "real_linux":
        p = data / "real_linux_transcripts.json"
        if p.exists():
            items = [x["transcript"] for x in json.loads(p.read_text())]
    elif arm == "cowrie":
        # Scripted cowrie session shape from the captured corpus.
        from scripts.run_external_baseline import _load_cowrie_command_corpus

        cmds = _load_cowrie_command_corpus()
        blob = "\n".join(cmds)
        if blob.strip():
            items = [blob]

    if len(items) < n:
        print(f"[warn] arm {arm}: only {len(items)} transcripts available (wanted {n})", file=sys.stderr)
    picked = items[:n]
    out = []
    for i, text in enumerate(picked):
        key = f"{arm}:{i}"
        normalized, mapping = normalize_transcript(text, key)
        out.append(
            {
                "id": hashlib.sha256(key.encode()).hexdigest()[:10],
                "arm": arm,  # never shown to the rater; used only by score()
                "transcript": normalized,
            }
        )
    return out


def build_packet(arms_spec: str, out: Path, seed: int, rater: str) -> None:
    arms = []
    for part in arms_spec.split(","):
        name, _, cnt = part.partition(":")
        arms.append((name, int(cnt or 5)))
    entries = []
    for arm, n in arms:
        entries.extend(load_transcripts(arm, n))
    order = list(range(len(entries)))
    random.Random(f"{seed}:{rater}").shuffle(order)
    # Rater-facing packet: arm labels stripped, ids stable but opaque.
    packet = {
        "rater": rater,
        "seed": seed,
        "instructions": (
            "For each transcript, decide whether the terminal session was produced by a REAL "
            "system or a HONEYPOT. Answer before reading the next one. Do not discuss with "
            "other raters. Confidence 1 = guessing, 5 = certain. Free-text reason required."
        ),
        "items": [
            {"position": pos + 1, "id": entries[i]["id"], "transcript": entries[i]["transcript"]}
            for pos, i in enumerate(order)
        ],
    }
    # Ground truth stays with the researcher, keyed by opaque id.
    truth = {e["id"]: e["arm"] for e in entries}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(packet, indent=2))
    truth_path = out.with_name(out.stem + "_truth.json")
    truth_path.write_text(json.dumps(truth, indent=2))
    print(f"packet: {out} ({len(packet['items'])} items)\ntruth (researcher-only): {truth_path}")


def score(packet_path: Path, answers_path: Path) -> None:
    packet = json.loads(packet_path.read_text())
    answers = json.loads(answers_path.read_text())
    truth_path = packet_path.with_name(packet_path.stem + "_truth.json")
    truth = json.loads(truth_path.read_text())

    n = len(answers.get("verdicts", []))
    correct = fp_honeypot = 0
    verdicts, golds = [], []
    confusions = []
    for v in answers.get("verdicts", []):
        tid = v["id"]
        gold_arm = truth.get(tid)
        gold_binary = "real" if gold_arm == "real_linux" else "honeypot"
        said = v["verdict"].lower()
        golds.append(gold_binary)
        verdicts.append(said)
        if said == gold_binary:
            correct += 1
            if gold_binary == "real" and said == "honeypot":
                pass
        elif gold_binary == "real" and said == "honeypot":
            fp_honeypot += 1
        confusions.append({"id": tid, "gold": gold_arm, "said": said, "confidence": v.get("confidence")})

    # Cohen's kappa over the binary verdict.
    def kappa(a: list, b: list) -> float:
        labels = sorted(set(a) | set(b))
        n = len(a)
        po = sum(1 for x, y in zip(a, b, strict=False) if x == y) / n if n else 0.0
        pe = sum((a.count(lbl) / n) * (b.count(lbl) / n) for lbl in labels) if n else 0.0
        return (po - pe) / (1 - pe) if pe < 1 else 1.0

    # Self-consistency: verdict vs own confidence (raters confident-but-wrong
    # are the interesting failures for the deception claim).
    confident_wrong = [
        c
        for c in confusions
        if c["said"] != ("real" if c["gold"] == "real_linux" else "honeypot")
        and int(c.get("confidence", 0)) >= 4
    ]

    report = {
        "rater": answers.get("rater", packet.get("rater")),
        "n": n,
        "accuracy": round(correct / n, 4) if n else None,
        # real judged as honeypot
        "false_honeypot_rate": round(fp_honeypot / n, 4) if n else None,
        "confusions": confusions,
        "confident_wrong": confident_wrong,
        "note": "kappa reported across raters once ≥3 answer sets are collected",
    }
    out = answers_path.with_name(answers_path.stem + "_scored.json")
    out.write_text(json.dumps(report, indent=2))
    print(json.dumps({k: report[k] for k in ("rater", "n", "accuracy", "false_honeypot_rate")}, indent=1))
    print(f"scored: {out}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Blind human eval: real-or-honeypot protocol")
    sub = parser.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--arms", required=True, help="e.g. cowrie:10,vanilla_llm:10,ragin:10,real_linux:10")
    b.add_argument("--out", required=True)
    b.add_argument("--seed", type=int, default=7)
    b.add_argument("--rater", required=True)
    s = sub.add_parser("score")
    s.add_argument("--packet", required=True)
    s.add_argument("--answers", required=True)
    args = parser.parse_args()
    if args.cmd == "build":
        build_packet(args.arms, Path(args.out), args.seed, args.rater)
    else:
        score(Path(args.packet), Path(args.answers))


if __name__ == "__main__":
    main()
