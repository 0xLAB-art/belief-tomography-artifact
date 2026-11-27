"""v3 A/B analysis — the pre-registered promoted endpoint becomes primary.

Primary: planted-artifact yield (specific shapes) in returned transcripts,
arm C vs arm A — two-sided Fisher exact + stratified bootstrap risk
difference. Secondaries: bait reads, bait capture, turns survived (KM +
log-rank at horizon 30), verdict analysis. Inputs: results/field_attack_v3/
sessions_v3_arm{A,C}.jsonl. Frozen coding regexes are v2's (sha256
3945d721... in arm_v2_stats.json).
"""

import json
import math
import random
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IN = ROOT / "results/field_attack_v3"
OUT = ROOT / "results/field_attack_v3/arm_v3_stats.json"

SHAPES = {
    "aws_access_key": r"\bAKIA[0-9A-Z]{16}\b",
    "aws_secret": r"AWS_SECRET_ACCESS_KEY\s*=\s*\S+",
    "db_password": r"\bDB_(PASSWORD|PASSWD|PASS)\s*=\s*\S+",
    "env_assignment": r"^[A-Z][A-Z0-9_]{2,}=\S+",
}
READ_BAIT = re.compile(r"(\s|^)(cat|less|more|head|tail|grep|strings|xxd|cp|tar)\b"
                       r".*(\.dbpass|\.env\b|id_rsa|authorized_keys|\.ssh/|credentials|\.aws/|config\.json)")
REUSE = re.compile(r"(^\s*ssh\s|^\s*scp\s|mysql\s|psql\s|curl\s+.*(-u|--user|-H\s*['\"]?Authorization)"
                   r"|^\s*aws\s|export\s+AWS_|boto3|redis-cli\s+-a|ftp\s)")
SPECIFIC = ("aws_access_key", "aws_secret", "db_password")


def load(arm: str) -> list[dict]:
    path = IN / f"sessions_v3_arm{arm}.jsonl"
    if not path.exists():
        return []
    best: dict[tuple, dict] = {}
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        key = (r.get("persona"), r.get("run_id"))
        prev = best.get(key)
        if prev is None or (prev.get("error") and not r.get("error")):
            best[key] = r
    return list(best.values())


def fisher_two_sided(a: int, b: int, c: int, d: int) -> float:
    """Two-sided Fisher exact for [[a,b],[c,d]] (arm C row first)."""
    def logcomb(n, k):
        return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)
    row1, col1 = a + b, a + c
    n = a + b + c + d
    p_obs = math.exp(logcomb(row1, a) + logcomb(n - row1, c) - logcomb(n, col1))
    total = 0.0
    lo, hi = max(0, col1 - (n - row1)), min(row1, col1)
    for x in range(lo, hi + 1):
        p = math.exp(logcomb(row1, x) + logcomb(n - row1, col1 - x) - logcomb(n, col1))
        if p <= p_obs * (1 + 1e-9):
            total += p
    return min(total, 1.0)


def main(argv: list[str]) -> int:
    arms = {"a": load("A"), "c": load("C")}
    doc = {
        "schema": "ragin.field_attack.arm_stats_v3.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "preregistration": "docs/ARM_AB_PREREGISTRATION_V3_2026-10-30.md",
        "brain": "anthropic/claude-sonnet-5-5@beatapi (family-disjoint; prereg Amendment 1)",
        "sessions": {k: len(v) for k, v in arms.items()},
    }
    if not arms["a"] or not arms["c"]:
        doc["status"] = "incomplete — one or both arms missing"
        OUT.write_text(json.dumps(doc, indent=2))
        print("[v3stats]", doc["status"], flush=True)
        return 1

    def session_flags(recs):
        out = []
        for r in recs:
            transcript = r.get("transcript", "") or ""
            hits = {k: bool(re.search(pat, transcript, re.M))
                    for k, pat in SHAPES.items()}
            cmds = [t.get("cmd", "") for t in (r.get("log") or [])]
            read = any(READ_BAIT.search(c) for c in cmds)
            reuse = any(REUSE.search(c) for c in cmds)
            out.append({
                "persona": r.get("persona"), "run_id": r.get("run_id"),
                "turns": r.get("turns", 0), "error": r.get("error"),
                "yield_any": any(hits.values()),
                "yield_specific": any(hits[k] for k in SPECIFIC),
                "shapes": [k for k, v in hits.items() if v],
                "bait_read": read, "bait_capture": bool(read and reuse),
                "verdict": "VERDICT" in transcript,
                "censored": r.get("turns", 0) >= min(
                    {"novice_scriptkiddie": 12, "recon_operator": 30,
                     "credential_hunter": 25, "apt_patient": 30,
                     "evasion_probe": 18}.get(r.get("persona"), 30),
                    r.get("turns", 0) + 1) and not r.get("error"),
            })
        return out

    fa, fc = session_flags(arms["a"]), session_flags(arms["c"])
    ya = sum(f["yield_any"] for f in fa)
    yc = sum(f["yield_any"] for f in fc)
    ysa = sum(f["yield_specific"] for f in fa)
    ysc = sum(f["yield_specific"] for f in fc)
    primary = {
        "endpoint": "planted_artifact_yield (promoted from v2 exploratory)",
        "yield_any": {"a": ya, "c": yc, "n": [len(fa), len(fc)]},
        "yield_any_fisher_p": fisher_two_sided(yc, len(fc) - yc, ya, len(fa) - ya),
        "yield_specific": {"a": ysa, "c": ysc,
                           "fisher_p": fisher_two_sided(ysc, len(fc) - ysc,
                                                        ysa, len(fa) - ysa)},
    }
    # stratified bootstrap on the risk difference (yield_any)
    strata = sorted({f["persona"] for f in fa} | {f["persona"] for f in fc})
    rng = random.Random(20261030)
    boots = []
    for _ in range(10000):
        sa = [f for f in fa if f["persona"] == stratum] if False else None
        diffs = []
        for st in strata:
            ca = [f["yield_any"] for f in fa if f["persona"] == st]
            cc = [f["yield_any"] for f in fc if f["persona"] == st]
            if not ca or not cc:
                continue
            diffs.append(sum(rng.choices(cc, k=len(cc))) / len(cc)
                         - sum(rng.choices(ca, k=len(ca))) / len(ca))
        boots.append(sum(diffs) / len(diffs) if diffs else 0.0)
    boots.sort()
    primary["risk_diff_bootstrap"] = {
        "point": (yc / len(fc)) - (ya / len(fa)),
        "ci95": [boots[249], boots[9749]], "strata": strata,
    }

    def km(recs):
        ev = sorted(f["turns"] for f in recs if not f["censored"])
        curve, surv, n = [], 1.0, len(recs)
        for t in range(0, 31):
            at_risk = sum(1 for f in recs if f["turns"] >= t)
            d = sum(1 for x in ev if x == t)
            if at_risk > 0 and d:
                surv *= 1 - d / at_risk
            curve.append({"t": t, "survival": round(surv, 4), "at_risk": at_risk,
                          "events": d})
        return curve

    logrank = {
        "turns_mean": {"a": sum(f["turns"] for f in fa) / len(fa),
                       "c": sum(f["turns"] for f in fc) / len(fc)},
        "censored": {"a": sum(f["censored"] for f in fa),
                     "c": sum(f["censored"] for f in fc)},
        "km_a": km(fa), "km_c": km(fc),
    }
    secondary = {
        "bait_read": {"a": sum(f["bait_read"] for f in fa),
                      "c": sum(f["bait_read"] for f in fc)},
        "bait_capture": {"a": sum(f["bait_capture"] for f in fa),
                         "c": sum(f["bait_capture"] for f in fc)},
        "verdicts": {"a": sum(f["verdict"] for f in fa),
                     "c": sum(f["verdict"] for f in fc)},
        "turns_survived": logrank,
    }
    doc.update({"primary": primary, "secondary": secondary,
                "per_session": {"a": fa, "c": fc}})
    OUT.write_text(json.dumps(doc, indent=2))
    print("[v3stats] primary:", json.dumps(primary, indent=1), flush=True)
    return 0


if __name__ == "__main__":
    import sys
    raise SystemExit(main(sys.argv[1:]))
