#!/usr/bin/env python3
"""Deterministic rule-based reference labeler for the jury packet.

The AI jury (three GPT-family checkpoints) agrees with itself at kappa 0.81,
which answers "are the labels stable" but not "are they grounded". This script
adds a non-LLM reference: an ordered keyword classifier over the frozen
operational taxonomy, applied to the same 120 cases under the same class set.
Agreement between the jury majority and an explicitly-specified rule table is
a different kind of evidence from model-model agreement, and it can be audited
line by line.

The rule table is intentionally simple and is emitted verbatim in the
artifact; a low agreement is a finding about the taxonomy's operational
definitions, not a bug to be tuned away. No case is relabelled by hand.

Output: results/laya_research/ai_jury_oracle_v1/oracle_agreement.json
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / "results" / "laya_research" / "blind_annotation_confirmatory_v3.json"
JURY_DIR = ROOT / "results" / "laya_research" / "ai_jury_v1"
OUT_DIR = ROOT / "results" / "laya_research" / "ai_jury_oracle_v1"
OUT = OUT_DIR / "oracle_agreement.json"

MALICIOUS = {"RECON", "SUSPICIOUS", "EXPLOITATION", "PRIVILEGE_ESCALATION",
             "DATA_ACCESS", "PERSISTENCE", "OTHER_ATTACK"}

# The packet mixes three shapes: shell commands, knowledge questions about a
# technique, and noise. The rule table is structural first, lexical second,
# because a keyword list alone classified 71/120 cases as UNCERTAIN.
RULES_VERSION = "structural_v2"

COMMAND_HEADS = (
    "cat ", "ls", "find ", "grep ", "ps ", "ss ", "netstat", "id", "whoami", "uname",
    "docker ", "iptables", "systemctl", "crontab", "df ", "free", "env", "sed ",
    "awk ", "head ", "tail ", "curl ", "wget ", "python", "bash", "sh ", "sudo",
    "mysql", "psql", "redis-cli", "ssh ", "scp ", "select ",
)
QUESTION = ("what is", "what are", "explain", "how does", "how do", "describe",
            "what techniques", "why does", "is there", "can you explain")
SHOW_STATE = ("show me", "list all", "list the", "check if", "which processes",
              "what processes", "display", "print the")
CREDENTIAL_PATH = ("/etc/shadow", "/etc/passwd", ".env", "id_rsa", "authorized_keys",
                   ".dbpass", "credentials", "select * from", "or 1=1")
PERSIST_WRITE = ("crontab -e", "> /etc/cron", "systemctl enable", "authorized_keys >>",
                 "chmod +s", "useradd", "adduser")


def _is_noise(text: str) -> bool:
    stripped = text.strip()
    return (len(stripped) < 4 and " " not in stripped) or stripped.lower() == stripped * 1 and False


def oracle_label(case: dict) -> str:  # noqa: C901 - explicit ordered policy
    text = str(case.get("evidence", "")).strip()
    low = text.lower()
    if not text or (len(text) < 4 and " " not in text):
        return "UNCERTAIN"
    if "or 1=1" in low or "union select" in low:
        return "EXPLOITATION"
    if low.startswith(COMMAND_HEADS) or "\n" in text or " | " in text or "/etc/" in low:
        if any(p in low for p in PERSIST_WRITE):
            return "PERSISTENCE"
        if any(p in low for p in CREDENTIAL_PATH):
            return "DATA_ACCESS"
        return "RECON"
    if low.startswith(SHOW_STATE):
        return "RECON"
    if low.startswith(QUESTION):
        return "BENIGN"
    if any(p in low for p in ("exploit", "payload", "reverse shell", "cve-")):
        return "EXPLOITATION"
    return "UNCERTAIN"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()





def cohen_kappa(a: list[str], b: list[str]) -> float:
    n = len(a)
    if not n:
        return 0.0
    observed = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    expected = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / (n * n)
    if expected >= 1.0:
        return 1.0
    return (observed - expected) / (1 - expected)


def binary(label: str) -> str | None:
    if label in MALICIOUS:
        return "MALICIOUS"
    if label == "BENIGN":
        return "BENIGN"
    return None


def main() -> int:
    cases = json.loads(PACKET.read_text(encoding="utf-8"))
    jury: dict[str, dict[str, str]] = {}
    for path in sorted(JURY_DIR.glob("*.json")):
        if path.name.startswith("ai_jury_"):
            continue
        doc = json.loads(path.read_text(encoding="utf-8"))
        jury[path.stem] = {item["case_id"]: item["label"] for item in doc.get("items", [])}
    if len(jury) < 3:
        raise SystemExit(f"expected 3 jury files, found {sorted(jury)}")

    ids = [c["id"] for c in cases]
    oracle = {c["id"]: oracle_label(c) for c in cases}

    per_juror = {}
    for model, labels in jury.items():
        shared = [cid for cid in ids if cid in labels]
        exact = sum(oracle[cid] == labels[cid] for cid in shared) / len(shared)
        pairs = [(binary(oracle[cid]), binary(labels[cid])) for cid in shared]
        pairs = [(x, y) for x, y in pairs if x and y]
        kappa = cohen_kappa([x for x, _ in pairs], [y for _, y in pairs]) if pairs else 0.0
        per_juror[model] = {
            "cases": len(shared),
            "exact_agreement": round(exact, 4),
            "binary_cases": len(pairs),
            "binary_kappa": round(kappa, 4),
        }

    majority: dict[str, str] = {}
    ties = 0
    for cid in ids:
        votes = [labels[cid] for labels in jury.values() if cid in labels]
        top = Counter(votes).most_common()
        if len(top) > 1 and top[0][1] == top[1][1]:
            ties += 1
            majority[cid] = "UNCERTAIN"
        else:
            majority[cid] = top[0][0]

    exact_majority = sum(oracle[cid] == majority[cid] for cid in ids) / len(ids)
    pairs = [(binary(oracle[cid]), binary(majority[cid])) for cid in ids]
    pairs = [(x, y) for x, y in pairs if x and y]
    kappa_majority = cohen_kappa([x for x, _ in pairs], [y for _, y in pairs]) if pairs else 0.0

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "ragin.laya.ai_jury_oracle.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "lane": ("Non-LLM deterministic reference. Not a human study and not a "
                 "substitute for rater_labels/; reported alongside the AI jury."),
        "packet": {"path": str(PACKET.relative_to(ROOT)), "sha256": sha(PACKET),
                   "cases": len(ids)},
        "jury_files": {m: str((JURY_DIR / f"{m}.json").relative_to(ROOT)) for m in jury},
        "rules": {
            "version": RULES_VERSION,
            "command_heads": list(COMMAND_HEADS),
            "question_prefixes": list(QUESTION),
            "show_state_prefixes": list(SHOW_STATE),
            "credential_paths": list(CREDENTIAL_PATH),
            "persistence_writes": list(PERSIST_WRITE),
        },
        "oracle_distribution": dict(Counter(oracle.values())),
        "majority_distribution": dict(Counter(majority.values())),
        "majority_ties": ties,
        "agreement": {
            "oracle_vs_majority_exact": round(exact_majority, 4),
            "oracle_vs_majority_binary_kappa": round(kappa_majority, 4),
            "oracle_vs_majority_binary_cases": len(pairs),
            "per_juror": per_juror,
        },
    }
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload["agreement"], indent=1))
    print("oracle:", payload["oracle_distribution"])
    print("wrote", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
