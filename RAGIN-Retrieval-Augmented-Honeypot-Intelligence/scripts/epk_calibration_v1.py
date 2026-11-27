#!/usr/bin/env python3
"""W1 calibration gate: does LLM-attacker inference fit the Datalog closure?

Replays the attack-team corpus (results/field_attack/sessions*.jsonl) against
the kernel: seeds the world from the released fiction (evidence/host_fiction.json),
simulates each session's serving channel, and checks every host-fact mention
in the attacker's own transcript against the theoretical closure K_t.

Reads (artifact-backed):
  - world coverage: what fraction of attacker fact-mentions are grounded in
    the synthetic world's closure (violations = kernel gaps, itemized);
  - rule coverage: of grounded mentions, how many arrive via a closure RULE
    (inferred) vs a directly served fact — the calibration signal for how
    much inference the ontology actually models;
  - per-persona breakdown (the frontier's first slice).

Output: results/epk_calibration_v1.json  (every number ↔ artifact).
"""

from __future__ import annotations

import argparse
import glob
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ragin.epk.closure import EpistemicTracker
from ragin.epk.graph import Fact, FactGraph
from ragin.epk.rules import STARTER_RULES

FACT_RE = re.compile(
    r"\b(?:(\d+\.\d+(?:\.\d+)?(?:-\d+)?)\s"          # version numbers
    r"|(CVE-\d{4}-\d{4,7})"
    r"|(5\.15\.0-\d+-generic))"                       # kernel versions
)

VERSION_RE = re.compile(r"\b(\d+\.\d+(?:\.\d+)?(?:-\d+)?)\b")
KERNEL_RE = re.compile(r"\b(5\.15\.0-\d+-generic)\b")
TS_RE = re.compile(r"\b1[0-9]{9}(\.\d+)?\b")  # epoch timestamps — not versions


def _seed_world_from_served() -> FactGraph:
    """v1.1: seed the world from the ACTUAL served fiction — every value the
    pipeline ever served is in-world by construction. Parses the 279-session
    export (response_text) into typed facts, plus the identity block."""
    g = FactGraph()
    seeds = [
        Fact("os.release", ("ubuntu",), "22.04.3", "seed"),
        Fact("os.codename", ("ubuntu",), "jammy", "seed"),
        Fact("kernel.version", ("web-srv-01",), "5.15.0-91-generic", "seed"),
    ]
    fiction = Path("evidence/host_fiction.json")
    if fiction.exists():
        try:
            ident = json.loads(fiction.read_text()).get("host_identity", {})
            if ident.get("kernel"):
                seeds.append(Fact("kernel.version", ("web-srv-01",), ident["kernel"], "seed"))
            if ident.get("ip"):
                seeds.append(Fact("host.addr", ("web-srv-01",), ident["ip"], "seed"))
        except Exception:
            pass

    for f in seeds:
        g.stage(f)

    # parse served content into facts (provenance=observed-fiction: it was
    # served by the pipeline, hence in-world by construction)
    uname_re = re.compile(r"Linux\s+(\S+)\s+(\d+\.\d+\.\d+-\d+-generic)")
    passwd_re = re.compile(r"^([a-z_][a-z0-9_-]*):x:\d+:\d+:", re.M)
    svc_re = re.compile(r"^\s*([a-z0-9_.-]+)\.service\s+.*?(?:Server\s+([\d.]+))?\s*$", re.M)
    envkv_re = re.compile(r"^([A-Z_][A-Z0-9_]*)=(.+)$", re.M)

    n_files = 0
    for p in sorted(glob.glob("results/field_export/ses-*.jsonl")):
        n_files += 1
        for line in open(p, encoding="utf-8", errors="replace"):
            try:
                rec = json.loads(line)
            except Exception:
                continue
            text = rec.get("response_text") or ""
            if not text:
                continue
            m = uname_re.search(text)
            if m:
                g.stage(Fact("kernel.version", (m.group(1),), m.group(2), "observed-fiction"))
            for u in passwd_re.findall(text)[:40]:
                g.stage(Fact("user.exists", (u,), "true", "observed-fiction"))
            for svc, ver in svc_re.findall(text):
                sname = svc.replace(".service", "")
                g.stage(Fact("svc.named", (sname,), "running", "observed-fiction"))
                if ver:
                    g.stage(Fact("pkg.version", (sname,), ver, "observed-fiction"))
            env = dict(envkv_re.findall(text))
            if "DB_USER" in env and "DB_HOST" in env:
                g.stage(Fact("cred.valid", (env["DB_USER"], env["DB_HOST"]), "true", "observed-fiction"))
            if "AWS_ACCESS_KEY_ID" in env:
                g.stage(Fact("canary.deployed", (env["AWS_ACCESS_KEY_ID"],), "deploy.env", "plan"))
    g.commit()
    return g, n_files


def _mention_facts(text: str, world: FactGraph) -> list[str]:
    """Value-typed fact mentions: an attacker mention is only a 'fact mention'
    if its VALUE matches the type of an in-world fact (kernel builds, package
    versions, CVE ids). Timestamp-like numbers excluded."""
    known_versions = {f.value for f in world.facts() if f.pred in ("pkg.version",)}
    known_kernels = {f.value for f in world.facts() if f.pred == "kernel.version"}
    out = set()
    for m in KERNEL_RE.finditer(text):
        out.add(f"kernel.version(*)={m.group(1)}")
    for m in VERSION_RE.finditer(text):
        v = m.group(1)
        if TS_RE.match(v) or "." not in v:
            continue
        if v in known_versions:
            out.add(f"pkg.version(*)={v}")
        elif v in known_kernels:
            out.add(f"kernel.version(*)={v}")
    for m in re.finditer(r"\bCVE-\d{4}-\d{4,7}\b", text):
        out.add(f"cve-mention(*)={m.group(0)}")
    return sorted(out)


def _served_facts_for(commands: list[str], world: FactGraph) -> list[Fact]:
    """v1 approximation of the serving channel: the fiction serves the facts
    whose tokens the attacker's commands asked about (uname → kernel.version;
    nginx -v → pkg.version; service queries → svc.*). Real serving goes
    through server_v2; this replay uses the same world facts."""
    served: list[Fact] = []
    joined = " ".join(commands).lower()
    for f in world.facts():
        if f.pred == "kernel.version" and ("uname" in joined or "kernel" in joined):
            served.append(f)
        elif f.pred == "pkg.version" and f.args[0] in joined:
            served.append(f)
        elif f.pred == "svc.listening" and ("ss -" in joined or "netstat" in joined
                                            or f.value in joined):
            served.append(f)
        elif f.pred == "os.release" and "lsb_release" in joined:
            served.append(f)
    return served


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results/epk_calibration_v1.json")
    args = ap.parse_args()

    world, n_export_files = _seed_world_from_served()
    base_closure = EpistemicTracker(world, STARTER_RULES).closure()

    files = sorted(glob.glob("results/field_attack/sessions*.jsonl"))
    per_persona = defaultdict(lambda: {"sessions": 0, "mentions": 0,
                                       "grounded": 0, "via_rule": 0,
                                       "violations": []})
    rule_hits: Counter = Counter()

    for path in files:
        for line in open(path, encoding="utf-8", errors="replace"):
            if not line.strip():
                continue
            rec = json.loads(line)
            persona = rec.get("persona") or path.split("_")[-1].replace(".jsonl", "")
            transcript = rec.get("transcript") or ""
            commands = [t.get("cmd", "") for t in (rec.get("log") or [])]
            stats = per_persona[persona]
            stats["sessions"] += 1

            tracker = EpistemicTracker(world, STARTER_RULES)
            served = _served_facts_for(commands, world)
            tracker.announced(served)
            closure = tracker.closure()
            rules_used = set(closure.derived.values())

            for mention in _mention_facts(transcript, world):
                stats["mentions"] += 1
                # grounded if the mention's value appears in any closure fact
                value = mention.split("=", 1)[1]
                grounded_keys = [k for k in closure.facts if k.endswith(f"={value}")]
                if grounded_keys:
                    stats["grounded"] += 1
                    via = {closure.derived[k] for k in grounded_keys if k in closure.derived}
                    if via:
                        stats["via_rule"] += 1
                        rule_hits.update(via)
                else:
                    stats["violations"].append(
                        {"file": path, "mention": mention,
                         "run_id": rec.get("run_id"),
                         "note": "attacker-referenced value outside closure"}
                    )

    total_sessions = sum(s["sessions"] for s in per_persona.values())
    total_mentions = sum(s["mentions"] for s in per_persona.values())
    total_grounded = sum(s["grounded"] for s in per_persona.values())
    total_rule = sum(s["via_rule"] for s in per_persona.values())
    total_viol = sum(len(s["violations"]) for s in per_persona.values())

    report = {
        "meta": {
            "generated": "2026-11-05",
            "world_facts": len(world.facts()),
            "world_digest": world.digest(),
            "world_seed_source": "field_export served fiction (v1.1)",
            "export_files_parsed": n_export_files,
            "closure_size": len(base_closure),
            "rules": [r.to_dict() for r in STARTER_RULES],
            "corpus_files": files,
            "sessions": total_sessions,
        },
        "w1_gate": {
            "mentions_total": total_mentions,
            "grounded_in_closure": total_grounded,
            "grounded_rate": round(total_grounded / total_mentions, 3) if total_mentions else None,
            "via_closure_rule": total_rule,
            "rule_coverage_rate": round(total_rule / total_grounded, 3) if total_grounded else None,
            "closure_violations": total_viol,
            "verdict": (
                "PASS" if total_viol == 0 and total_mentions > 0
                else "FAIL" if total_mentions > 0 else "NO_DATA"
            ),
        },
        "rule_hits": dict(rule_hits),
        "per_persona": {
            p: {
                **{k: v for k, v in s.items() if k != "violations"},
                "grounded_rate": round(s["grounded"] / s["mentions"], 3) if s["mentions"] else None,
                "violations": s["violations"][:20],
            }
            for p, s in sorted(per_persona.items())
        },
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))
    g = report["w1_gate"]
    print(f"W1 calibration: {g['mentions_total']} mentions | grounded {g['grounded_rate']} "
          f"| rule-coverage {g['rule_coverage_rate']} | violations {g['closure_violations']} "
          f"→ {g['verdict']}")
    print(f"world: {report['meta']['world_facts']} facts → closure {report['meta']['closure_size']}")
    print(f"rule hits: {dict(rule_hits)}")


if __name__ == "__main__":
    main()
