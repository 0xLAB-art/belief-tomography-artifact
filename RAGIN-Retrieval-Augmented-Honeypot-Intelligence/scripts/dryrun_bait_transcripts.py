#!/usr/bin/env python3
"""Offline dry run — preview transcript quality for the 8 GT human-eval inputs.

Uses an unreachable gateway URL so the deterministic path (bait fast-paths +
templates) fires, exactly like the degraded mode the eval exercises. This is
free and instant — no LLM tokens are consumed.

Structural checks per scenario:
  - which deterministic path fired (bait fast-path family / generic template)
  - canary secrets served (honeytoken registered and detectable on replay)
  - fiction consistency (hostname/persona, no cloud/host identity clash)
  - regression: no leaked template placeholders ({{...}} / identity.get(...))
  - MITRE technique IDs surfaced in the transcript

NOTE: the deepseek wiring only affects the LIVE LLM path (non-bait scenarios);
this preview is the deterministic floor — the minimum quality the live eval
will see even if the LLM degrades mid-run.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ragin.benchmark.human_eval import SAMPLE_SCENARIOS
from ragin.cycle.adapters import HisokaAdapter

# Unreachable gateway → deterministic path (bait fast-paths / templates)
DEAD_GATEWAY = "http://127.0.0.1:1"

PLACEHOLDER_RX = re.compile(r"\{identity\.get|\{\{|\{[a-z_]+\.get\(")
MITRE_RX = re.compile(r"\bT\d{4}(?:\.\d{3})?\b")

# Families of deterministic response paths, detected by transcript markers.
# Chained/composed families first — their bodies embed the simpler ones.
BAIT_MARKERS = {
    "imds-chain": ("TOKEN=$(curl", "security-credentials", "X-aws-ec2-metadata-token"),
    "sqli-mysql-repl": ("mysql>", "authentication_string", "Welcome to the MySQL monitor"),
    "revshell-chain": ("sh-5.1$", "Connection received on 10.0.1.66", ".dbpass"),
    "priv-esc (sudo)": ("sudo -l", "NOPASSWD", "sudoers.d"),
    "shadow-dump": ("yescrypt", "$y$", "/etc/shadow"),
    "credential-hunt (.env/dbpass)": ("deploy.env", "DB_PASS_FILE", ".dbpass"),
    "imds": ("169.254.169.254", "iam/security-credentials", "AKIA"),
    "sudo fast-path": ("sudo:", "is not in the sudoers file", "sudoers"),
}


def classify_path(text: str) -> str:
    for family, markers in BAIT_MARKERS.items():
        hits = sum(1 for m in markers if m.lower() in text.lower())
        if hits >= 2:
            return family
    return "generic template"


def check_scenario(sc) -> dict:
    adapter = HisokaAdapter(gateway_url=DEAD_GATEWAY, api_key="dryrun-offline")
    session_id = f"dryrun-{sc.scenario_id}"
    ctx = {
        "session_id": session_id,
        "classification": {"skill_level": sc.expected_persona},
    }
    result = adapter.generate_response(sc.attacker_input, ctx)
    text = result["response_text"]
    return {
        "id": sc.scenario_id,
        "persona": sc.expected_persona,
        "path": classify_path(text),
        "text": text,
        "persona_used": result["persona_used"],
        "artifacts": result["artifacts_injected"],
        "engagement": result["engagement_score"],
        "leak": bool(PLACEHOLDER_RX.search(text)),
        "ttps": sorted(set(MITRE_RX.findall(text))),
        "adapter": adapter,
        "session_id": session_id,
    }


def main() -> int:
    print("=" * 78)
    print("OFFLINE DRY RUN — deterministic transcript preview (no LLM tokens)")
    print("=" * 78)

    results = [check_scenario(sc) for sc in SAMPLE_SCENARIOS]

    print(f"\n{'ID':<7} {'persona':<13} {'path fired':<30} {'canary':<7} {'leak':<5} {'MITRE IDs'}")
    print("-" * 78)
    for r in results:
        # Canary check: replay a served secret back through the engine
        canary = "n/a"
        eng = r["adapter"]._deceiver._honeytoken_engines.get(r["session_id"])
        if eng is not None:
            m = re.search(
                r"(?:password|secret|token)['\"]?\s*[:=]\s*['\"]?([A-Za-z0-9_!@#$%^&*.\-]{8,})",
                r["text"],
                re.I,
            )
            canary = "YES" if (m and eng.check_triggers({"input": m.group(1)})) else "no-cred-served"
        ttp_str = ",".join(r["ttps"]) or "—"
        leak_str = "LEAK!" if r["leak"] else "ok"
        print(f"{r['id']:<7} {r['persona']:<13} {r['path']:<30} {canary:<7} {leak_str:<5} {ttp_str}")

    leaks = [r for r in results if r["leak"]]
    # A bare `whoami` → "prompt + username" is protocol-correct minimalism
    # (padding it would itself be a tell) — only flag genuinely void output.
    empty = [r for r in results if len(r["text"].strip()) < 25]
    print("-" * 78)
    print(f"placeholder leaks: {len(leaks)}/8   near-empty transcripts: {len(empty)}/8")
    print(f"avg transcript length: {sum(len(r['text']) for r in results)//8} chars")

    print("\n" + "=" * 78)
    print("SAMPLE — GT-002 (the weakest scenario in the baseline eval)")
    print("=" * 78)
    gt2 = next(r for r in results if r["id"] == "GT-002")
    print(f"[persona={gt2['persona_used']} artifacts={gt2['artifacts']} engagement={gt2['engagement']:.2f}]")
    print(gt2["text"][:1200])

    return 1 if (leaks or empty) else 0


if __name__ == "__main__":
    raise SystemExit(main())
