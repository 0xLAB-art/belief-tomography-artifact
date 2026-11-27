#!/usr/bin/env python3
"""Jev A/B on REAL Cowrie honeypot sessions (non-synthetic traffic).

Unlike scripts/jev_ab_eval.py (synthetic tiers), real sessions have no
tier labels. Ground truth here is a documented expert severity map for
the 13 captured sessions (they are small and individually readable).
Primary question: does Jev change/correct risk decisions on traffic the
behavior-floor patterns were NOT tuned against?

Routing paths compared (identical to production wiring):
  baseline : Chrollo (ngram) -> Supervisor.route (behavior floor included)
  with_jev : same + JevRoutingSignal.adjust_risk()

Usage:
  RAGIN_JEVI_BASE_URL=https://ai-gateway.vercel.sh/typesafe/v1 \
  RAGIN_JEVI_API_KEY=<vck key> RAGIN_JEVI_MODEL=typesafe-ai/jev \
  .venv/bin/python scripts/jev_real_logs_eval.py
"""

from __future__ import annotations

import asyncio
import gzip
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ragin.chrollo.classifier import ChrolloClassifier  # noqa: E402
from ragin.chrollo.models import CommandEntry, SessionLog  # noqa: E402
from ragin.cycle.coordination import Supervisor  # noqa: E402
from ragin.jev.assessment import JevAssessor  # noqa: E402
from ragin.jev.orchestration import JevRoutingSignal  # noqa: E402

RISK_ORDER = ["low", "medium", "high", "critical"]
COWRIE_DIR = ROOT / "data/cowrie_logs"

# Expert severity labels for the captured sessions, keyed by a behavioral
# fingerprint (the sessions repeat verbatim across captures).
def expert_label(cmds: list[str]) -> tuple[str, str]:
    """Return (expert_risk, family) for a real session."""
    blob = "\n".join(cmds)
    if "169.254.169.254" in blob:
        return "high", "cloud-metadata SSRF (credential theft)"
    if "nc " in blob and ("/home/" in blob or "curl -d @-" in blob):
        return "critical", "exfil + implant exec"
    if "authorized_keys" in blob or ("crontab" in blob and "backdoor" in blob):
        return "critical", "persistence implant"
    if "ssh " in blob and ("ssh-keyscan" in blob or "scp" in blob):
        return "high", "lateral movement pivot"
    if "nmap" in blob or ("netstat" in blob and "ss -" in blob):
        return "medium", "network scanning"
    if "/etc/shadow" in blob:
        return "high", "credential access (shadow read)"
    if set(cmds) >= {"whoami", "id", "uname -a"}:
        return "medium", "automated enumeration bot"
    return "medium", "uncategorized"


def load_real_sessions() -> list[dict]:
    sessions: dict[str, dict] = {}
    paths = [
        COWRIE_DIR / "cowrie.json.1",
        COWRIE_DIR / "cowrie.json.2026-07-28",
        COWRIE_DIR / "cowrie.json.2.gz",
        COWRIE_DIR / "cowrie.json.3.gz",
    ]

    for p in paths:
        if p.suffix == ".gz":
            with gzip.open(p, "rt") as fh:
                lines = fh.readlines()
        else:
            with open(p) as fh:
                lines = fh.readlines()
        for line in lines:
            if not line.strip():
                continue
            e = json.loads(line)
            sid = e.get("session")
            if not sid:
                continue
            s = sessions.setdefault(sid, {"commands": [], "times": []})
            if e.get("eventid") == "cowrie.command.input":
                ts = e.get("timestamp")
                try:
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00")) if ts else datetime.now(timezone.utc)
                except Exception:
                    dt = datetime.now(timezone.utc)
                s["commands"].append(e.get("input", ""))
                s["times"].append(dt)

    out = []
    for sid, s in sessions.items():
        if not s["commands"]:
            continue
        out.append({"session_id": f"cowrie-{sid[-8:]}", **s})
    return out


async def main() -> None:
    rows = load_real_sessions()
    print(f"Real Cowrie sessions with commands: {len(rows)}")

    clf = ChrolloClassifier()
    sup = Supervisor()
    assessor = JevAssessor()
    if not assessor.enabled:
        raise SystemExit("Jev disabled")

    results = []
    for r in rows:
        cmds = r["commands"]
        sl = SessionLog(
            session_id=r["session_id"],
            start_time=r["times"][0] if r["times"] else datetime.now(timezone.utc),
            commands=[
                CommandEntry(timestamp=t, command=c)
                for t, c in zip(r["times"], cmds, strict=False)
            ],
        )
        cls = clf.classify(sl)
        classification = {"skill_level": cls.skill_level.value, "confidence": cls.confidence}

        ctx = {
            "session_id": r["session_id"],
            "interaction_count": len(cmds),
            "attacker_inputs": cmds,
        }
        decision = sup.route(session_context=ctx, classification=classification, session_id="")
        base_risk = decision.risk_level.value

        # Jev (network) — same call the mixin makes
        jev_risk, jev_sev, jev_kind, jev_attack, err = "", None, "", None, ""
        try:
            assessment = assessor.assess_context(ctx)
        except Exception as exc:
            assessment, err = None, f"{type(exc).__name__}: {exc}"
        if assessment is not None:
            sig = JevRoutingSignal(assessment)
            jev_risk = sig.risk_level or ""
            jev_sev = assessment.severity
            jev_kind = sig.attack_kind
            jev_attack = sig.is_attack
        final_risk = sig.adjust_risk(base_risk) if assessment is not None else base_risk

        truth, family = expert_label(cmds)
        results.append({
            "session_id": r["session_id"],
            "family": family,
            "expert_risk": truth,
            "n_cmds": len(cmds),
            "chrollo": f"{cls.skill_level.value}@{cls.confidence:.2f}",
            "base_risk": base_risk,
            "jev_risk": jev_risk,
            "final_risk": final_risk,
            "jev_severity": jev_sev,
            "jev_kind": jev_kind,
            "jev_attack": jev_attack,
            "base_at_truth": (
                RISK_ORDER.index(base_risk) >= RISK_ORDER.index(truth)
                if base_risk in RISK_ORDER else None
            ),
            "final_at_truth": (
                RISK_ORDER.index(final_risk) >= RISK_ORDER.index(truth)
                if final_risk in RISK_ORDER else None
            ),
            "error": err[:160],
        })
        time.sleep(1.0)  # gentle pacing on the gateway

    # ── Report ──────────────────────────────────────────────────────────
    print(f"\n{'family':44s} {'truth':9s} {'chrollo':16s} {'base':9s} {'jev':9s} {'final':9s}")
    print("-" * 105)
    for r in results:
        flag = ""
        if not r["base_at_truth"]:
            flag = "  <-- base MISS"
        if r["base_at_truth"] != r["final_at_truth"]:
            flag += " JEV-CHANGED"
        print(f"{r['family'][:43]:44s} {r['expert_risk']:9s} {r['chrollo']:16s} "
              f"{r['base_risk']:9s} {r['jev_risk'] or '-':9s} {r['final_risk']:9s}{flag}")

    ok_base = sum(1 for r in results if r["base_at_truth"])
    ok_final = sum(1 for r in results if r["final_at_truth"])
    print(f"\nat/above expert severity: baseline {ok_base}/{len(results)}  ->  with-Jev {ok_final}/{len(results)}")

    out = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "endpoint": {
            "base_url": os.environ.get("RAGIN_JEVI_BASE_URL", "https://api.beatapi.io/v1 (default)"),
            "model": os.environ.get("RAGIN_JEVI_MODEL", "jev-1.14-free (default)"),
        },
        "n_sessions": len(results),
        "baseline_correct": ok_base,
        "with_jev_correct": ok_final,
        "per_session": results,
    }
    (ROOT / "results/jev_real_logs_eval.json").write_text(json.dumps(out, indent=1))
    print("Saved -> results/jev_real_logs_eval.json")


if __name__ == "__main__":
    asyncio.run(main())
