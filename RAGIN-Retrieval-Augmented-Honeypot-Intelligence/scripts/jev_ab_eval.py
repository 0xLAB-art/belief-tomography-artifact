#!/usr/bin/env python3
"""A/B eval: Supervisor routing WITHOUT Jev vs WITH Jev on known-label sessions.

Ground truth: sessions in data/training/test.jsonl carry a tier label
(novice/intermediate/expert/apt). Each tier's tradecraft implies a minimum
defensible risk posture:

    novice       -> low
    intermediate -> medium
    expert       -> high
    apt          -> critical

Risk levels are ordinal (low<medium<high<critical). A routing decision is
"correct" when it is not below the tier's floor. The ordinal underestimation
depth is the primary harm metric: RAGIN routing only escalates on higher risk,
so underestimating an APT is the costly failure mode; over-escalation costs
efficiency, not safety.

Usage:
    .venv/bin/python scripts/jev_ab_eval.py [--n 400] [--concurrency 6]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from dataclasses import asdict, is_dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ragin.chrollo.classifier import ChrolloClassifier  # noqa: E402
from ragin.chrollo.models import SessionLog  # noqa: E402
from ragin.chrollo.pipeline import ChrolloPipeline  # noqa: E402
from ragin.cycle.coordination import Supervisor  # noqa: E402
from ragin.jev.assessment import JevAssessor  # noqa: E402
from ragin.jev.orchestration import JevRoutingSignal, SupervisorJevMixin  # noqa: E402

# ── Ground truth mapping ────────────────────────────────────────────────────
TIER_FLOOR = {"novice": 0, "intermediate": 1, "expert": 2, "apt": 3}
RISK_ORDER = ["low", "medium", "high", "critical"]

# Free-tier pacing: zen 429s after ~40-50 rapid calls. Serialize Jev calls
# with a minimum interval, and retry rate-limited calls with backoff.
MIN_JEV_INTERVAL_S = 2.0
_jev_lock = asyncio.Lock()
_last_jev_call = 0.0


async def paced_assess(assessor: JevAssessor, ctx: dict):
    """assess_context with global pacing and 429/timeout backoff retry."""
    global _last_jev_call
    for attempt in range(4):
        async with _jev_lock:
            wait = MIN_JEV_INTERVAL_S - (time.monotonic() - _last_jev_call)
            if wait > 0:
                await asyncio.sleep(wait)
            _last_jev_call = time.monotonic()
        try:
            return await asyncio.to_thread(assessor.assess_context, ctx)
        except Exception as exc:
            msg = f"{type(exc).__name__}: {exc}"
            rate_limited = any(s in msg for s in ("429", "ReadTimeout", "Rate limit"))
            if rate_limited and attempt < 3:
                await asyncio.sleep(15 + attempt * 15)
                continue
            raise


def _jsonable(obj):
    if is_dataclass(obj) and not isinstance(obj, type):
        return asdict(obj)
    if isinstance(obj, dict):
        return {k: _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    if hasattr(obj, "value"):  # enums
        return obj.value
    return obj


def load_sessions(n: int) -> list[dict]:
    """Stratified sample: n/4 per tier, evenly spaced within each tier block."""
    path = ROOT / "data/training/test.jsonl"
    with open(path) as f:
        rows = [json.loads(line) for line in f]
    by_tier: dict[str, list[dict]] = {}
    for r in rows:
        by_tier.setdefault(r["skill_level"], []).append(r)
    per_tier = max(1, n // len(by_tier))
    picked: list[dict] = []
    for tier_rows in by_tier.values():
        stride = max(1, len(tier_rows) // per_tier)
        picked.extend(tier_rows[::stride][:per_tier])
    # Round-robin interleave tiers so a mid-run rate limit leaves balanced
    # coverage across tiers rather than exhausting only the first tier(s).
    tiers = sorted({r["skill_level"] for r in picked})
    queues = {t: [r for r in picked if r["skill_level"] == t] for t in tiers}
    out: list[dict] = []
    while any(queues.values()):
        for t in tiers:
            if queues[t]:
                out.append(queues[t].pop(0))
    return out


def make_supervisor():
    class JevSupervisor(SupervisorJevMixin, Supervisor):
        pass

    return JevSupervisor()


async def eval_one(
    row: dict,
    pipeline: ChrolloPipeline,
    supervisor,
    assessor: JevAssessor,
) -> dict:
    session_log = SessionLog.model_validate(row)
    tier = row["skill_level"]
    cmds = [c["command"] for c in row["commands"]]

    # 1) Chrollo classification (deterministic, no network)
    cls = pipeline.process_session(session_log)
    classification = {"skill_level": cls.skill_level.value, "confidence": cls.confidence}

    # 2) Baseline routing (no Jev) — real attacker behavior in context,
    #    same key the orchestrator uses (attacker_inputs).
    base_ctx = {
        "session_id": row["session_id"],
        "interaction_count": len(cmds),
        "attacker_inputs": cmds,
    }
    decision = supervisor.route(
        session_context=base_ctx,
        classification=classification,
        session_id="",
    )
    base_risk = decision.risk_level.value

    # 3) Jev signal (network) — the same call route_with_jev makes.
    jev_err = ""
    try:
        assessment = await paced_assess(assessor, base_ctx)
    except Exception as exc:
        assessment = None
        jev_err = f"{type(exc).__name__}: {exc}"

    signal = JevRoutingSignal(assessment)
    jev_risk = signal.risk_level or ""
    final_risk = signal.adjust_risk(base_risk)

    floor = TIER_FLOOR[tier]
    base_idx = RISK_ORDER.index(base_risk)
    final_idx = RISK_ORDER.index(final_risk)
    jev_idx = RISK_ORDER.index(jev_risk) if jev_risk else None

    return {
        "session_id": row["session_id"],
        "tier": tier,
        "truth_floor": RISK_ORDER[floor],
        "chrollo_label": cls.skill_level.value,
        "chrollo_conf": round(cls.confidence, 3),
        "base_risk": base_risk,
        "jev_risk": jev_risk,
        "final_risk": final_risk,
        "jev_attack": signal.is_attack,
        "jev_severity": (assessment.severity if assessment else None),
        "jev_kind": signal.attack_kind,
        "base_correct": base_idx >= floor,
        "final_correct": final_idx >= floor,
        "base_under": max(0, floor - base_idx),
        "final_under": max(0, floor - final_idx),
        "jev_alone_under": (max(0, floor - jev_idx) if jev_idx is not None else None),
        "jev_error": jev_err[:200],
    }


async def run_eval(n: int, concurrency: int) -> tuple[list[dict], dict]:
    rows = load_sessions(n)
    print(
        f"Loaded {len(rows)} labeled sessions; Jev base URL = "
        f"{os.environ.get('RAGIN_JEVI_BASE_URL', 'https://api.beatapi.io/v1')}"
    )

    pipeline = ChrolloPipeline(ChrolloClassifier())
    supervisor = make_supervisor()
    assessor = JevAssessor()
    if not assessor.enabled:
        raise SystemExit("Jev disabled (RAGIN_JEVI_ENABLED=0) — cannot run A/B")

    sem = asyncio.Semaphore(concurrency)
    done = 0
    results: list[dict] = []

    async def guarded(row: dict) -> dict:
        nonlocal done
        async with sem:
            try:
                r = await eval_one(row, pipeline, supervisor, assessor)
            except Exception as exc:
                r = {
                    "session_id": row.get("session_id", "?"),
                    "tier": row.get("skill_level", "?"),
                    "fatal_error": f"{type(exc).__name__}: {exc}",
                }
            done += 1
            if done % 25 == 0:
                print(f"  {done}/{len(rows)} done")
            return r

    results = list(await asyncio.gather(*[guarded(r) for r in rows]))
    return results, summarize(results)


def summarize(results: list[dict]) -> dict:
    valid = [r for r in results if "fatal_error" not in r]
    n = len(valid)
    if n == 0:
        return {"n": 0, "error": "no valid sessions"}

    ok_base = sum(r["base_correct"] for r in valid)
    ok_final = sum(r["final_correct"] for r in valid)

    def macro_under(key: str) -> float:
        per_tier = []
        for tier in TIER_FLOOR:
            sub = [r[key] for r in valid if r["tier"] == tier]
            per_tier.append((sum(sub) / len(sub)) if sub else 0.0)
        return sum(per_tier) / len(per_tier)

    escalations = sum(1 for r in valid if RISK_ORDER.index(r["final_risk"]) > RISK_ORDER.index(r["base_risk"]))
    base_under_by_tier = {
        tier: round(
            sum(r["base_under"] for r in valid if r["tier"] == tier)
            / max(1, sum(1 for r in valid if r["tier"] == tier)),
            4,
        )
        for tier in TIER_FLOOR
    }
    final_under_by_tier = {
        tier: round(
            sum(r["final_under"] for r in valid if r["tier"] == tier)
            / max(1, sum(1 for r in valid if r["tier"] == tier)),
            4,
        )
        for tier in TIER_FLOOR
    }

    return {
        "n": n,
        "fatal_errors": len(results) - n,
        "baseline_correct": ok_base,
        "baseline_acc": round(ok_base / n, 4),
        "with_jev_correct": ok_final,
        "with_jev_acc": round(ok_final / n, 4),
        "acc_delta": round((ok_final - ok_base) / n, 4),
        "mean_under_base": round(sum(r["base_under"] for r in valid) / n, 4),
        "mean_under_final": round(sum(r["final_under"] for r in valid) / n, 4),
        "macro_under_base": round(macro_under("base_under"), 4),
        "macro_under_final": round(macro_under("final_under"), 4),
        "macro_under_delta": round(macro_under("base_under") - macro_under("final_under"), 4),
        "mean_under_base_by_tier": base_under_by_tier,
        "mean_under_final_by_tier": final_under_by_tier,
        "jev_available": sum(1 for r in valid if r["jev_risk"]),
        "jev_errors": sum(1 for r in valid if r["jev_error"]),
        "escalations": escalations,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=400)
    ap.add_argument("--concurrency", type=int, default=6)
    args = ap.parse_args()

    results, summary = asyncio.run(run_eval(args.n, args.concurrency))

    out = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "config": {
            "n": args.n,
            "concurrency": args.concurrency,
            "ground_truth": "tier floor (novice=low, intermediate=medium, "
            "expert=high, apt=critical); correct = risk >= floor",
        },
        "summary": summary,
        "per_session": results,
    }
    out_path = ROOT / "results/jev_ab_eval.json"
    out_path.write_text(json.dumps(out, indent=1))
    print(f"\nSaved -> {out_path}")
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
