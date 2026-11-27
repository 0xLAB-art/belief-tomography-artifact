#!/usr/bin/env python3
"""Analysis for the v2 A/C workload (pre-registered in
docs/ARM_AB_PREREGISTRATION_V2_2026-10-28.md).

Endpoints:
  * primary   — turns survived, right-censored at the persona cap
                (Kaplan-Meier + log-rank; stratified bootstrap of the
                restricted-mean-survival difference)
  * secondary — bait capture: the attacker read a planted artifact and then
                attempted to reuse it (Fisher exact + bootstrap risk diff)
  * descriptive — wall-clock dwell, server response time, output size, depth

The v1 pilot is never pooled in: it answered a different question (a 300 s
transport ceiling), and its artifact stays as-is.

Usage:
  python3 scripts/field_attack_stats_v2.py
  python3 scripts/field_attack_stats_v2.py --check
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
PREREG = ROOT / "docs" / "ARM_AB_PREREGISTRATION_V2_2026-10-28.md"
ARM_A = ROOT / "results" / "field_attack" / "sessions_v2_armA.jsonl"
ARM_C = ROOT / "results" / "field_attack" / "sessions_v2_armC.jsonl"
OUT = ROOT / "results" / "field_attack" / "arm_v2_stats.json"
SEED = 20261028
ITERS = 10_000

READ_BAIT = re.compile(
    r"(\s|^)(cat|less|more|head|tail|grep|strings|xxd|cp|tar)\b.*"
    r"(\.dbpass|\.env\b|id_rsa|authorized_keys|\.ssh/|credentials|\.aws/|config\.json)",
    re.I,
)
# Credential-shaped content the surface itself returns. Commands echo into the
# transcript, so hits are counted on output lines only: a `cat .env` against a
# missing file is a read attempt, not an artifact.
ARTIFACT_PATTERNS = {
    "aws_access_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "aws_secret": re.compile(r"AWS_SECRET_ACCESS_KEY\s*=\s*\S+"),
    "private_key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "shadow_hash": re.compile(r"^root:\$[0-9a-z]", re.M),
    "db_password": re.compile(r"\bDB_(PASSWORD|PASSWD|PASS)\s*=\s*\S+", re.I),
    "env_assignment": re.compile(r"^[A-Z][A-Z0-9_]{2,}=\S+", re.M),
}


def artifact_hits(transcript: str) -> list[str]:
    body = "\n".join(line for line in transcript.splitlines() if not line.startswith("$ "))
    return [name for name, pattern in ARTIFACT_PATTERNS.items() if pattern.search(body)]


REUSE = re.compile(
    r"(^\s*ssh\s|^\s*scp\s|mysql\s|psql\s|curl\s+.*(-u|--user|-H\s*['\"]?Authorization)|"
    r"^\s*aws\s|export\s+AWS_|boto3|redis-cli\s+-a|ftp\s)",
    re.I,
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> list[dict]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    # A session that hit its wall-clock budget without failing is censored
    # data and keeps its turn log. A record that carries an error is a failed
    # session: the two turns it logged before the socket died are not evidence
    # about engagement and must not enter either arm.
    usable = [r for r in rows if not r.get("error")]
    # A resumed runner can append the same persona/run twice (a killed worker's
    # half-written session plus the retry). Keep the most complete record per
    # pair so a duplicate cannot inflate either arm.
    best: dict[tuple, dict] = {}
    for r in usable:
        key = (r.get("persona"), r.get("run_id"))
        if key not in best or len(r.get("log") or []) >= len(best[key].get("log") or []):
            best[key] = r
    return list(best.values())


def session_metrics(record: dict) -> dict:
    log = record.get("log") or []
    commands = [str(t.get("cmd", "")) for t in log]
    cap = int(record.get("cap") or len(commands))
    turns = len(commands)
    bait_idx = next((i for i, c in enumerate(commands) if READ_BAIT.search(c)), None)
    captured = bool(
        bait_idx is not None
        and any(REUSE.search(c) for c in commands[bait_idx + 1:])
    )
    hits = artifact_hits(str(record.get("transcript") or ""))
    servers = [t["server_s"] for t in log if t.get("server_s") is not None]
    thinks = [t["think_s"] for t in log if t.get("think_s") is not None]
    return {
        "persona": record.get("persona"),
        "run_id": record.get("run_id"),
        "cap": cap,
        "turns": turns,
        "censored": turns >= cap or bool(record.get("partial")),
        "bait_read": bait_idx is not None,
        "bait_capture": captured,
        "dwell_s": float(record.get("dwell_s") or 0.0),
        "server_s_mean": float(np.mean(servers)) if servers else None,
        "think_s_mean": float(np.mean(thinks)) if thinks else None,
        "output_chars_mean": float(np.mean([t.get("output_chars", 0) for t in log])) if log else 0.0,
        "unique_paths": len({p for c in commands for p in re.findall(r"/[\w./-]+", c)}),
        # Scripted continuation, used only when the attacker model returns
        # nothing usable. Recorded per session so a provider-heavy run cannot
        # be reported as a fully model-driven one.
        "fallbacks": int(record.get("fallbacks") or 0),
        "model_only": int(record.get("fallbacks") or 0) == 0,
        "artifacts": hits,
        "artifact_any": bool(hits),
    }


def km_curve(rows: list[dict]) -> list[dict]:
    """Kaplan-Meier survival over turns; censoring at the session's cap."""
    times = sorted({r["turns"] for r in rows} | {r["cap"] for r in rows})
    at_risk = len(rows)
    survival = 1.0
    curve = [{"t": 0, "survival": 1.0, "at_risk": at_risk}]
    for t in sorted(t for t in times if t > 0):
        events = sum(1 for r in rows if r["turns"] == t and not r["censored"])
        censored = sum(1 for r in rows if r["turns"] == t and r["censored"])
        if at_risk:
            if events:
                survival *= 1 - events / at_risk
        curve.append({"t": t, "survival": round(survival, 4), "at_risk": at_risk,
                      "events": events, "censored": censored})
        at_risk -= events + censored
    return curve


def logrank(a: list[dict], c: list[dict]) -> dict:
    """Two-sample log-rank (Mantel-Cox) over turn times."""
    times = sorted({r["turns"] for r in a + c})
    observed = expected = variance = 0.0
    for t in times:
        at_a = sum(1 for r in a if r["turns"] >= t)
        at_c = sum(1 for r in c if r["turns"] >= t)
        n = at_a + at_c
        if n == 0:
            continue
        d_a = sum(1 for r in a if r["turns"] == t and not r["censored"])
        d_c = sum(1 for r in c if r["turns"] == t and not r["censored"])
        d = d_a + d_c
        if d == 0:
            continue
        observed += d_c
        expected += d * at_c / n
        if n > 1:
            variance += d * (at_c / n) * (1 - at_c / n) * (n - d) / (n - 1)
    chi2 = ((observed - expected) ** 2 / variance) if variance else 0.0
    return {
        "observed_c": round(observed, 3),
        "expected_c": round(expected, 3),
        "chi2": round(chi2, 4),
        "p": float(stats.chi2.sf(chi2, 1)) if variance else 1.0,
    }


def restricted_mean(curve: list[dict], horizon: int) -> float:
    """Area under the KM curve up to `horizon` (restricted mean survival)."""
    total = 0.0
    for prev, cur in zip(curve, curve[1:]):
        upper = min(cur["t"], horizon)
        if upper > prev["t"]:
            total += prev["survival"] * (upper - prev["t"])
    last = curve[-1]
    if last["t"] < horizon:
        total += last["survival"] * (horizon - last["t"])
    return total


def boot_turns(a: list[dict], c: list[dict], rng, iters: int) -> dict:
    personas = sorted({r["persona"] for r in a + c})
    diffs = np.empty(iters)
    for i in range(iters):
        ca, cc = [], []
        for p in personas:
            ra = [r["turns"] for r in a if r["persona"] == p]
            rc = [r["turns"] for r in c if r["persona"] == p]
            if not ra or not rc:
                continue
            ca.extend(rng.choice(ra, size=len(ra), replace=True))
            cc.extend(rng.choice(rc, size=len(rc), replace=True))
        diffs[i] = np.mean(cc) - np.mean(ca)
    point = float(np.mean([r["turns"] for r in c]) - np.mean([r["turns"] for r in a]))
    return {"diff": point,
            "ci95": [float(np.percentile(diffs, 2.5)), float(np.percentile(diffs, 97.5))]}


def fisher_capture(a: list[dict], c: list[dict]) -> dict:
    table = [[sum(r["bait_capture"] for r in c), len(c) - sum(r["bait_capture"] for r in c)],
             [sum(r["bait_capture"] for r in a), len(a) - sum(r["bait_capture"] for r in a)]]
    odds, p = stats.fisher_exact(table, alternative="two-sided")
    risk_c = table[0][0] / len(c) if c else 0.0
    risk_a = table[1][0] / len(a) if a else 0.0
    return {"table_c_a_true_false": table, "odds_ratio": float(odds),
            "risk_c": round(float(risk_c), 3), "risk_a": round(float(risk_a), 3),
            "risk_diff": round(float(risk_c - risk_a), 3), "p_raw": float(p)}


def boot_artifact_diff(a: list[dict], c: list[dict], rng, iters: int) -> dict:
    aa = np.array([1.0 if r["artifact_any"] else 0.0 for r in a])
    cc = np.array([1.0 if r["artifact_any"] else 0.0 for r in c])
    diffs = np.empty(iters)
    for i in range(iters):
        sa = rng.choice(aa, size=len(aa), replace=True)
        sc = rng.choice(cc, size=len(cc), replace=True)
        diffs[i] = sc.mean() - sa.mean()
    return {"risk_a": round(float(aa.mean()), 3), "risk_c": round(float(cc.mean()), 3),
            "diff": round(float(cc.mean() - aa.mean()), 3),
            "ci95": [round(float(np.percentile(diffs, 2.5)), 3),
                     round(float(np.percentile(diffs, 97.5)), 3)]}


def describe(rows: list[dict]) -> dict:
    def mean(key):
        vals = [r[key] for r in rows if r[key] is not None]
        return round(float(np.mean(vals)), 2) if vals else None

    return {
        "sessions": len(rows),
        "censored": sum(1 for r in rows if r["censored"]),
        "turns_mean": mean("turns"),
        "dwell_mean_s": mean("dwell_s"),
        "server_s_mean": mean("server_s_mean"),
        "think_s_mean": mean("think_s_mean"),
        "bait_read": sum(1 for r in rows if r["bait_read"]),
        "bait_capture": sum(1 for r in rows if r["bait_capture"]),
        "sessions_model_only": sum(1 for r in rows if r["model_only"]),
        "turn_fallbacks": sum(r["fallbacks"] for r in rows),
        "sessions_with_artifact": sum(1 for r in rows if r["artifact_any"]),
    }


def build(a_path: Path, c_path: Path) -> dict:
    a = [session_metrics(r) for r in load(a_path)]
    c = [session_metrics(r) for r in load(c_path)]
    horizon = min(max(r["cap"] for r in a + c), 30)
    rng = np.random.default_rng(SEED)

    curve_a, curve_c = km_curve(a), km_curve(c)
    lr = logrank(a, c)
    boot = boot_turns(a, c, rng, ITERS)
    cap_fisher = fisher_capture(a, c)
    art = boot_artifact_diff(a, c, rng, ITERS)
    art_table = [[sum(r["artifact_any"] for r in c), len(c) - sum(r["artifact_any"] for r in c)],
                 [sum(r["artifact_any"] for r in a), len(a) - sum(r["artifact_any"] for r in a)]]
    _, art_p = stats.fisher_exact(art_table, alternative="two-sided")
    holm = sorted([("turns_logrank", lr["p"]), ("bait_capture", cap_fisher["p_raw"])],
                  key=lambda kv: kv[1])
    adjusted = {}
    running = 0.0
    for i, (name, p) in enumerate(holm):
        running = max(running, min(1.0, p * (len(holm) - i)))
        adjusted[name] = running

    return {
        "schema": "ragin.field_attack.arm_stats_v2.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "preregistration": {"path": str(PREREG.relative_to(ROOT)), "sha256": sha(PREREG)},
        "inputs": {
            "arm_a": {"path": str(a_path.relative_to(ROOT)), "sha256": sha(a_path)},
            "arm_c": {"path": str(c_path.relative_to(ROOT)), "sha256": sha(c_path)},
            "sessions": {"a": len(a), "c": len(c)},
        },
        "coding": {
            "read_bait": READ_BAIT.pattern,
            "reuse": REUSE.pattern,
            "sha256": hashlib.sha256((READ_BAIT.pattern + REUSE.pattern).encode()).hexdigest(),
        },
        "bootstrap": {"iterations": ITERS, "seed": SEED, "strata": "persona"},
        "primary": {
            "endpoint": "turns_survived",
            "horizon": horizon,
            "logrank": lr,
            "p_holm": adjusted["turns_logrank"],
            "significant_holm": adjusted["turns_logrank"] < 0.05,
            "turns_bootstrap": boot,
            "restricted_mean_a": round(restricted_mean(curve_a, horizon), 2),
            "restricted_mean_c": round(restricted_mean(curve_c, horizon), 2),
            "km_a": curve_a,
            "km_c": curve_c,
        },
        "secondary": {
            "endpoint": "bait_capture",
            "fisher": cap_fisher,
            "p_holm": adjusted["bait_capture"],
            "significant_holm": adjusted["bait_capture"] < 0.05,
        },
        "exploratory": {
            "endpoint": "surface_artifact_yield",
            "status": "exploratory, not pre-registered: a property of the returned "
                      "surface, not a treatment effect on attacker behaviour",
            "patterns": {name: pattern.pattern for name, pattern in ARTIFACT_PATTERNS.items()},
            "sessions_with_artifact": {
                "a": sum(1 for r in a if r["artifact_any"]),
                "c": sum(1 for r in c if r["artifact_any"]),
            },
            "difference": art,
            "fisher_p": float(art_p),
            "by_pattern": {
                name: {"a": sum(1 for r in a if name in r["artifacts"]),
                       "c": sum(1 for r in c if name in r["artifacts"])}
                for name in ARTIFACT_PATTERNS
            },
        },
        "descriptive": {"arm_a": describe(a), "arm_c": describe(c)},
        "per_session": {
            "arm_a": [{k: r[k] for k in ("persona", "run_id", "turns", "cap", "censored", "bait_capture")} for r in a],
            "arm_c": [{k: r[k] for k in ("persona", "run_id", "turns", "cap", "censored", "bait_capture")} for r in c],
        },
        "decision_rule": "docs/ARM_AB_PREREGISTRATION_V2_2026-10-28.md §Decision rule",
    }


def sanitize(payload: dict) -> dict:
    clean = json.loads(json.dumps(payload))
    clean.pop("generated_at", None)
    return clean


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm-a", type=Path, default=ARM_A)
    parser.add_argument("--arm-c", type=Path, default=ARM_C)
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv[1:])

    payload = build(args.arm_a, args.arm_c)
    if args.check:
        if not args.out.exists():
            print(f"missing artifact: {args.out}", file=sys.stderr)
            return 1
        if sanitize(json.loads(args.out.read_text())) != sanitize(payload):
            print(f"drift: {args.out} does not match a fresh recomputation", file=sys.stderr)
            return 1
        print(f"ok: {args.out} reproduces")
        return 0

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    p, s = payload["primary"], payload["secondary"]
    print(f"turns: A={payload['descriptive']['arm_a']['turns_mean']} "
          f"C={payload['descriptive']['arm_c']['turns_mean']} logrank p={p['logrank']['p']:.4f} "
          f"(holm {p['p_holm']:.4f})")
    print(f"bait capture: A={s['fisher']['risk_a']} C={s['fisher']['risk_c']} "
          f"p_raw={s['fisher']['p_raw']:.4f} (holm {s['p_holm']:.4f})")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
