#!/usr/bin/env python3
"""Held-out attacker-trajectory benchmark for the S&P rescue experiment.

This benchmark is deliberately provider-free.  It evaluates the security
controller on 400 held-out attacker sessions from ``data/training/test.jsonl``
and compares the current behavior-aware Supervisor against a skill-only
ablation.  Each session is replayed at multiple prefixes, so the unit of
analysis is an attacker trajectory rather than an isolated scripted query.

The benchmark answers four questions that the original 218-row workload could
not answer:

* Does the controller reach the command-derived risk floor early in a session?
* Does the behavior floor reduce dangerous under-routing relative to skill-only
  routing?
* What is the false-escalation cost on benign sessions?
* Are the results reproducible with a disjoint train/test corpus?

No network, LLM, provider quota, or field deployment is used.  The output is a
new evidence artifact under ``results/sp2027_rescue`` and never overwrites a
version-of-record result.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ragin.chrollo.classifier import ChrolloClassifier  # noqa: E402
from ragin.chrollo.models import SessionLog  # noqa: E402
from ragin.chrollo.pipeline import ChrolloPipeline  # noqa: E402
from ragin.cycle.coordination import Supervisor  # noqa: E402

PREFIXES = (1, 2, 4, 8, 16, 32, 64, "all")
RISK_ORDER = ("low", "medium", "high", "critical")
RISK_INDEX = {name: i for i, name in enumerate(RISK_ORDER)}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def prefix_n(prefix: int | str, total: int) -> int:
    return total if prefix == "all" else min(int(prefix), total)


def gold_risk(commands: list[str]) -> str:
    """Use the controller's explicit hostile-behavior floor as gold severity.

    This is intentionally not the learned skill label.  It represents the
    minimum safety routing demanded by observed command evidence and therefore
    supports a paired under-routing audit.
    """
    floor = Supervisor._behavior_floor({"attacker_inputs": commands})
    return floor or "low"


def route(
    supervisor: Supervisor,
    classification: dict[str, Any],
    commands: list[str],
    *,
    behavior_aware: bool,
    session_id: str,
) -> dict[str, Any]:
    context: dict[str, Any] = {
        "session_id": session_id,
        "interaction_count": len(commands),
        "attacker_inputs": commands if behavior_aware else [],
    }
    decision = supervisor.route(
        session_context=context,
        classification=classification,
        session_id=session_id,
    )
    risk = decision.risk_level.value
    return {
        "risk": risk,
        "risk_index": RISK_INDEX[risk],
        "skill": classification["skill_level"],
        "confidence": classification["confidence"],
        "persona": decision.persona,
        "route": decision.route.value,
        "needs_voting": decision.needs_voting,
        "needs_expert": decision.needs_expert,
    }


def bootstrap_ci(values: list[float], seed: int, rounds: int = 4000) -> list[float | None]:
    if not values:
        return [None, None]
    rng = __import__("random").Random(seed)
    means: list[float] = []
    n = len(values)
    for _ in range(rounds):
        sample = [values[rng.randrange(n)] for _ in range(n)]
        means.append(sum(sample) / n)
    means.sort()
    return [round(means[int(0.025 * (rounds - 1))], 4), round(means[int(0.975 * (rounds - 1))], 4)]


def summarize_rows(rows: list[dict[str, Any]], arm: str) -> dict[str, Any]:
    arm_rows = [r for r in rows if r["arm"] == arm]
    n = len(arm_rows)
    if not n:
        return {"arm": arm, "n_prefix_rows": 0}
    adequate = [r["risk_index"] >= r["gold_index"] for r in arm_rows]
    under = [r["gold_index"] - r["risk_index"] for r in arm_rows]
    skill_correct = [r["skill"] == r["target_skill"] for r in arm_rows]
    low_gold = [r for r in arm_rows if r["gold_risk"] == "low"]
    false_high = [r for r in low_gold if r["risk_index"] > RISK_INDEX["low"]]
    by_prefix: dict[str, dict[str, Any]] = {}
    for prefix in PREFIXES:
        block = [r for r in arm_rows if r["prefix"] == prefix]
        if not block:
            continue
        block_adequate = [r["risk_index"] >= r["gold_index"] for r in block]
        block_under = [max(0, r["gold_index"] - r["risk_index"]) for r in block]
        block_skill = [r["skill"] == r["target_skill"] for r in block]
        by_prefix[str(prefix)] = {
            "n_sessions": len(block),
            "skill_accuracy": round(sum(block_skill) / len(block), 4),
            "risk_floor_coverage": round(sum(block_adequate) / len(block), 4),
            "under_routing_rate": round(sum(x > 0 for x in block_under) / len(block), 4),
            "mean_under_depth": round(sum(block_under) / len(block), 4),
        }
    return {
        "arm": arm,
        "n_prefix_rows": n,
        "n_sessions": len({r["session_id"] for r in arm_rows}),
        "skill_accuracy": round(sum(skill_correct) / n, 4),
        "risk_floor_coverage": round(sum(adequate) / n, 4),
        "under_routing_rate": round(sum(x > 0 for x in under) / n, 4),
        "mean_under_depth": round(sum(under) / n, 4),
        "max_under_depth": max(under),
        "low_gold_prefix_rows": len(low_gold),
        "low_gold_false_escalation_rate": round(sum(1 for r in false_high) / len(low_gold), 4) if low_gold else None,
        "prefixes": by_prefix,
    }


def episode_summary(rows: list[dict[str, Any]], arm: str) -> dict[str, Any]:
    """Collapse prefix rows to one value per session for clustered inference."""
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row["arm"] == arm:
            grouped[row["session_id"]].append(row)
    covered: list[float] = []
    safe_time: list[float] = []
    low_gold_escalations: list[float] = []
    for session_rows in grouped.values():
        session_rows.sort(key=lambda r: r["prefix_n"])
        covered.append(float(any(r["risk_index"] >= r["gold_index"] for r in session_rows)))
        target = session_rows[-1]["gold_index"]
        first = next((r for r in session_rows if r["risk_index"] >= target), None)
        safe_time.append(float(first["prefix_n"] if first else len(session_rows[-1]["commands_seen"])))
        if session_rows[-1]["gold_risk"] == "low":
            low_gold_escalations.append(float(any(r["risk_index"] > 0 for r in session_rows)))
    return {
        "n_sessions": len(grouped),
        "episode_eventual_floor_coverage": round(sum(covered) / len(covered), 4) if covered else None,
        "median_commands_to_floor": statistics.median(safe_time) if safe_time else None,
        "low_gold_episode_escalation_rate": (
            round(sum(low_gold_escalations) / len(low_gold_escalations), 4) if low_gold_escalations else None
        ),
        "coverage_bootstrap_ci": bootstrap_ci(covered, seed=20261003),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Provider-free held-out attacker trajectory benchmark")
    ap.add_argument("--test", default="data/training/test.jsonl")
    ap.add_argument("--train", default="data/training/train.jsonl")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--out", default="results/sp2027_rescue/behavior_trajectory_benchmark.json")
    args = ap.parse_args()

    test_path = ROOT / args.test
    train_path = ROOT / args.train
    test = load_jsonl(test_path)
    train = load_jsonl(train_path)
    if args.limit is not None:
        test = test[: args.limit]

    train_ids = {row["session_id"] for row in train}
    test_ids = {row["session_id"] for row in test}
    overlap = sorted(train_ids & test_ids)
    if overlap:
        raise SystemExit(f"train/test session overlap detected: {len(overlap)}")

    classifier = ChrolloClassifier()
    pipeline = ChrolloPipeline(classifier)
    rows: list[dict[str, Any]] = []
    episode_meta: list[dict[str, Any]] = []

    for raw in test:
        full_commands = [entry["command"] for entry in raw.get("commands", [])]
        if not full_commands:
            continue
        session_id = raw["session_id"]
        target = gold_risk(full_commands)
        episode_meta.append(
            {
                "session_id": session_id,
                "skill_label": raw.get("skill_level", ""),
                "n_commands": len(full_commands),
                "gold_risk": target,
                "tags": list(raw.get("tags", [])),
            }
        )
        for prefix in PREFIXES:
            n = prefix_n(prefix, len(full_commands))
            commands = full_commands[:n]
            truncated = dict(raw)
            truncated["commands"] = raw["commands"][:n]
            session = SessionLog.model_validate(truncated)
            result = pipeline.process_session(session)
            classification = {"skill_level": result.skill_level.value, "confidence": result.confidence}
            for arm, behavior_aware in (("skill_only", False), ("behavior_floor", True)):
                decision = route(
                    Supervisor(), classification, commands,
                    behavior_aware=behavior_aware, session_id=f"{session_id}:{prefix}:{arm}",
                )
                rows.append(
                    {
                        "session_id": session_id,
                        "prefix": prefix,
                        "prefix_n": n,
                        "commands_seen": commands,
                        "gold_risk": target,
                        "gold_index": RISK_INDEX[target],
                        "target_skill": raw.get("skill_level", ""),
                        "arm": arm,
                        **decision,
                    }
                )

    arm_summary = {
        arm: {
            "prefix_summary": summarize_rows(rows, arm),
            "episode_summary": episode_summary(rows, arm),
        }
        for arm in ("skill_only", "behavior_floor")
    }

    paired = []
    for left in rows:
        if left["arm"] != "skill_only":
            continue
        right_key = (left["session_id"], left["prefix"])
        right = next(
            r for r in rows
            if r["arm"] == "behavior_floor" and (r["session_id"], r["prefix"]) == right_key
        )
        paired.append(
            {
                "coverage_delta": float(right["risk_index"] >= right["gold_index"])
                - float(left["risk_index"] >= left["gold_index"]),
                "under_depth_delta": max(0, left["gold_index"] - left["risk_index"])
                - max(0, right["gold_index"] - right["risk_index"]),
            }
        )
    deltas = {
        name: {
            "mean": round(sum(item[name] for item in paired) / len(paired), 4) if paired else None,
            "bootstrap_ci": bootstrap_ci([item[name] for item in paired], seed=20261004),
        }
        for name in ("coverage_delta", "under_depth_delta")
    }

    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    artifact = {
        "artifact": "sp2027_rescue_behavior_trajectory_benchmark",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "method": {
            "provider_calls": False,
            "field_deployment": False,
            "unit_of_analysis": "held-out attacker session replayed at command prefixes",
            "gold_risk": (
                "controller-defined Supervisor._behavior_floor over observed commands; "
                "this is a self-consistency diagnostic, not independent attacker ground truth"
            ),
            "arms": {
                "skill_only": "learned Chrollo skill classification with no command-derived risk floor",
                "behavior_floor": "current Supervisor with deterministic command-derived risk floor",
            },
            "prefixes": list(PREFIXES),
            "bootstrap": {"rounds": 4000, "seed": 20261003, "paired_seed": 20261004},
        },
        "corpus": {
            "test_path": args.test,
            "train_path": args.train,
            "test_sha256": sha256_file(test_path),
            "train_sha256": sha256_file(train_path),
            "n_test_sessions": len(test),
            "n_sessions_with_commands": len(episode_meta),
            "train_test_id_overlap": len(overlap),
            "skill_distribution": dict(Counter(row["skill_label"] for row in episode_meta)),
            "gold_risk_distribution": dict(Counter(row["gold_risk"] for row in episode_meta)),
            "command_count": {
                "mean": round(statistics.mean(row["n_commands"] for row in episode_meta), 3) if episode_meta else None,
                "median": statistics.median(row["n_commands"] for row in episode_meta) if episode_meta else None,
                "min": min((row["n_commands"] for row in episode_meta), default=None),
                "max": max((row["n_commands"] for row in episode_meta), default=None),
            },
        },
        "arms": arm_summary,
        "paired_deltas": deltas,
        "rows": rows,
    }
    out.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"out": str(out), "corpus": artifact["corpus"], "arms": arm_summary, "paired_deltas": deltas},
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
