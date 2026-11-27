#!/usr/bin/env python3
"""Phase 3 per-arm comparison for the AI adversarial workload.

Compares two attack-driver runs (plan line: "Repeat the workload per arm
(cowrie-only vs RAGIN) for the comparison section"). Session-record schema is
the driver's: {persona, run_id, started, turns, dwell_s, log[], transcript}.

Metrics are computed symmetrically over both arms from the transcripts and
per-turn logs only:

  * structure: ok/err sessions, turns (total/mean), dwell (mean/median),
    command count, mean output chars, mean turn latency
  * command classes (regex buckets over the issued commands): recon,
    credential-probe, mutation/download, evasion, other
  * sensitive-read hits (regex over transcripts): /etc/shadow, id_rsa,
    .env/.dbpass, AWS access-key shape

Honesty labels emitted with the artifact:
  * local self-play endpoints (never the live field IP) — run provenance
  * arms share one host IP (endpoint-confound caveat)
  * honeytoken/artifact surfaces differ per arm by design, so hit counts are
    descriptive of each arm's surface, not a controlled contrast

Usage:
  python3 scripts/field_arm_comparison.py \
      results/field_attack/sessions_armA_cowrie.jsonl \
      results/field_attack/sessions_armC_ragin.jsonl
"""

from __future__ import annotations

import json
import re
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "results" / "field_attack" / "arm_comparison.json"

COMMAND_CLASSES: dict[str, re.Pattern[str]] = {
    "recon": re.compile(
        r"^\s*(ls|cat|find|whoami|id|uname|hostname|ps|top|netstat|ss|ifconfig|ip|"
        r"df|free|env|pwd|date|w|who|history)\b"
    ),
    "credential_probe": re.compile(
        r"(/etc/shadow|/etc/passwd|\.ssh|id_rsa|sudo\b|su\b|creds?|\.env|\.dbpass|"
        r"credential|token|apikey|api_key|password)"
    ),
    "mutation_download": re.compile(
        r"^\s*(wget|curl|apt|apt-get|yum|dnf|pip|npm|gcc|cc|make|chmod|chown|rm|mv|"
        r"cp|crontab|nc|ncat|bash\s+-i|python[23]?\s+-c)\b"
    ),
    "evasion": re.compile(r"^\s*(unset|history\s+-c|alias|clear|sed\s+-i.*\.bash_history)"),
}

SENSITIVE_READS: dict[str, re.Pattern[str]] = {
    "etc_shadow": re.compile(r"/etc/shadow"),
    "private_key": re.compile(r"id_rsa|BEGIN (RSA |OPENSSH )?PRIVATE KEY"),
    "env_file": re.compile(r"\.env\b"),
    "dbpass": re.compile(r"\.dbpass"),
    "aws_access_key": re.compile(r"AKIA[0-9A-Z]{16}"),
}


def classify(command: str) -> str:
    """First matching bucket in specificity order (credential > evasion >
    mutation > recon), else other."""
    for name in ("credential_probe", "evasion", "mutation_download", "recon"):
        if COMMAND_CLASSES[name].search(command):
            return name
    return "other"


def arm_summary(records: list[dict]) -> dict:
    ok = [r for r in records if not r.get("error")]
    err = [r for r in records if r.get("error")]
    turns = [r.get("turns", 0) for r in ok]
    dwell = [float(r.get("dwell_s") or 0.0) for r in ok]
    commands = [t.get("cmd", "") for r in ok for t in r.get("log", [])]
    out_chars = [
        t.get("output_chars", 0) for r in ok for t in r.get("log", [])
    ]
    latencies = [
        t.get("latency_s") for r in ok for t in r.get("log", []) if t.get("latency_s")
    ]
    class_counts: dict[str, int] = {"other": 0}
    for name in COMMAND_CLASSES:
        class_counts[name] = 0
    for cmd in commands:
        class_counts[classify(cmd)] += 1
    transcripts = "\n".join(r.get("transcript", "") for r in ok)
    hits = {
        name: len(pattern.findall(transcripts))
        for name, pattern in SENSITIVE_READS.items()
    }
    personas: dict[str, int] = {}
    for r in ok:
        personas[r.get("persona", "?")] = personas.get(r.get("persona", "?"), 0) + 1
    return {
        "sessions_ok": len(ok),
        "sessions_err": len(err),
        "turns_total": sum(turns),
        "turns_mean": round(statistics.mean(turns), 2) if turns else 0.0,
        "dwell_mean_s": round(statistics.mean(dwell), 1) if dwell else 0.0,
        "dwell_median_s": round(statistics.median(dwell), 1) if dwell else 0.0,
        "commands_total": len(commands),
        "output_chars_total": sum(out_chars),
        "turn_latency_mean_s": round(statistics.mean(latencies), 2) if latencies else None,
        "command_classes": class_counts,
        "sensitive_read_hits": hits,
        "sessions_per_persona": personas,
    }


def compare(path_a: Path, path_b: Path) -> dict:
    def load(p: Path) -> list[dict]:
        return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]

    return {
        "schema": "ragin.field_attack.arm_comparison.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "arms": {
            "A_cowrie_only": {"source": str(path_a), **arm_summary(load(path_a))},
            "C_ragin": {"source": str(path_b), **arm_summary(load(path_b))},
        },
        "caveats": [
            "local self-play endpoints, never the live field IP (run provenance)",
            "arms share one host IP: endpoint-confound caveat vs the field design",
            "deception surfaces differ per arm by design; sensitive-read hit counts "
            "describe each arm's surface, not a controlled same-surface contrast",
        ],
    }


def main(argv: list[str]) -> int:
    a = Path(argv[1]) if len(argv) > 1 else ROOT / "results" / "field_attack" / "sessions_armA_cowrie.jsonl"
    b = Path(argv[2]) if len(argv) > 2 else ROOT / "results" / "field_attack" / "sessions_armC_ragin.jsonl"
    out = Path(argv[3]) if len(argv) > 3 else DEFAULT_OUT
    payload = compare(a, b)
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    for name, arm in payload["arms"].items():
        print(
            f"{name}: ok={arm['sessions_ok']} err={arm['sessions_err']} "
            f"turns={arm['turns_total']} dwell_mean={arm['dwell_mean_s']}s "
            f"cmds={arm['commands_total']}"
        )
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))