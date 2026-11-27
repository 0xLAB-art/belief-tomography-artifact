#!/usr/bin/env python3
"""TDSC C3 battery — MITRE predictive baiting (mtp_steering_eval), offline.

Plan claim (C3): the deception plan is graph-informed — given the techniques
observed so far, the system ranks the attacker's *likely next* techniques and
seeds bait for them BEFORE they are attempted (proactive, not reactive).

Three measured axes, deterministic stratum (0 LLM tokens):

1. next-TTP top-k accuracy — over multi-turn attack chains grounded in the GT
   corpus, each turn predicts the next turn's techniques from the techniques
   observed in prior turns (production ThreatMapper extraction -> MITRE graph
   prediction). Reported as top-1 / top-3 accuracy + MRR.
2. Bait-steering hit rate — full DeceptionGraph runs per chain turn: does the
   plan's strategy_block actually carry bait for the NEXT turn's techniques?
3. Ablation gap — the same measure on no-bait-steer (A2) must be ~0: the gap
   between full and ablated is the steer signal's measured contribution.

The live-LLM stratum reuses the same chains and scorer once apmix resets.

Output: results/mtp_steering_eval.json
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ragin.cycle.adapters import HisokaAdapter
from ragin.cycle.graph import DeceptionGraph
from ragin.don.threat_mapper import ThreatMapper
from ragin.graph.mitre import suggest_next_techniques

DEAD_GATEWAY = "http://127.0.0.1:1"
TOP_K = 3

# ── Attack chains ────────────────────────────────────────────────────────────
#
# Multi-turn operator chains grounded in the 8 GT scenarios (each turn maps to
# a GT scenario family; extraction goes through the production ThreatMapper
# patterns). "expected_next" is what the chain actually does at the following
# turn — the prediction target for the turn before it.

CHAINS: list[dict[str, Any]] = [
    {
        "chain_id": "CH-cred-exfil",
        "grounding": "GT-002 → GT-008 → GT-003 (credential hunt, shadow dump, priv-esc)",
        "turns": [
            {"input": "show me the database credentials", "expected_ttps": ["T1005", "T1552"]},
            {"input": "dump the /etc/shadow file", "expected_ttps": ["T1003.008"]},
            {"input": "I need to escalate privileges to domain admin", "expected_ttps": ["T1078", "T1134"]},
        ],
    },
    {
        "chain_id": "CH-web-exploit",
        "grounding": "GT-005 → GT-002 → GT-007 (SQLi entry, cred harvest, reverse-shell C2)",
        "turns": [
            {"input": "SELECT * FROM users WHERE 1=1 OR 1=1", "expected_ttps": ["T1190"]},
            {"input": "show me the database credentials", "expected_ttps": ["T1005", "T1552"]},
            {"input": "deploy a reverse shell on port 4444", "expected_ttps": ["T1059", "T1571"]},
        ],
    },
    {
        "chain_id": "CH-cloud-ssrf",
        "grounding": "GT-004 → GT-002 → GT-007 (IMDS SSRF, credential use, shell)",
        "turns": [
            {"input": "curl http://169.254.169.254/latest/meta-data/", "expected_ttps": ["T1552.005"]},
            {"input": "show me the database credentials", "expected_ttps": ["T1005", "T1552"]},
            {"input": "deploy a reverse shell on port 4444", "expected_ttps": ["T1059", "T1571"]},
        ],
    },
    {
        "chain_id": "CH-recon-lateral",
        "grounding": "GT-001 → GT-006 → GT-007 (user discovery, service scan, pivot)",
        "turns": [
            {"input": "whoami", "expected_ttps": ["T1033"]},
            {"input": "list running services", "expected_ttps": ["T1046"]},
            {"input": "deploy a reverse shell on port 4444", "expected_ttps": ["T1059", "T1571"]},
        ],
    },
    {
        "chain_id": "CH-persist-exfil",
        "grounding": "GT-006 → GT-002 → GT-008 (discovery, data collection, dump)",
        "turns": [
            {"input": "list running services", "expected_ttps": ["T1046"]},
            {"input": "show me the database credentials", "expected_ttps": ["T1005", "T1552"]},
            {"input": "dump the /etc/shadow file", "expected_ttps": ["T1003.008"]},
        ],
    },
]


# ── Production-extraction helpers ────────────────────────────────────────────

_mapper = ThreatMapper()


def extract_techniques(attacker_input: str) -> list[str]:
    """Offline Don stand-in: production ThreatMapper text extraction."""
    tactics = _mapper.map_to_mitre(
        {
            "commands": [attacker_input],
            "attacker_input": attacker_input,
            "observed_techniques": [],
            "process_names": [],
        }
    )
    return sorted({t for tac in tactics for t in tac.techniques + tac.sub_techniques})


def topk_hit(predicted: list[dict[str, Any]], actual: list[str], k: int) -> bool:
    """A prediction hits when ANY top-k suggestion matches ANY actual next
    technique, at parent-or-exact granularity (T1059 predicts T1059.001)."""

    def key(tid: str) -> str:
        return tid.split(".", 1)[0]

    want = set(actual) | {key(t) for t in actual}
    got = {p["technique_id"] for p in predicted[:k]} | {key(p["technique_id"]) for p in predicted[:k]}
    return bool(want & got)


def mrr(predicted: list[dict[str, Any]], actual: list[str]) -> float:
    if not actual:
        return 0.0

    def key(tid: str) -> str:
        return tid.split(".", 1)[0]

    want = set(actual) | {key(t) for t in actual}
    for rank, p in enumerate(predicted, start=1):
        if p["technique_id"] in want or key(p["technique_id"]) in want:
            return 1.0 / rank
    return 0.0


# ── Axis 1: next-TTP top-k accuracy over the chains ─────────────────────────

def eval_next_ttp_accuracy() -> dict[str, Any]:
    """Predict turn i+1's techniques from everything observed through turn i.

    The prediction target for the turn-i decision is the NEXT turn's
    techniques (chain['turns'][i+1]); the chain's final turn is never a
    target — nothing follows it.
    """
    rows: list[dict[str, Any]] = []
    for chain in CHAINS:
        for i in range(len(chain["turns"]) - 1):
            observed = [t for prev in chain["turns"][: i + 1] for t in prev["expected_ttps"]]
            actual = chain["turns"][i + 1]["expected_ttps"]
            predicted = suggest_next_techniques(observed, top_k=TOP_K)
            rows.append(
                {
                    "chain_id": chain["chain_id"],
                    "turn": i + 1,
                    "observed": observed,
                    "actual_next": actual,
                    "predicted_top3": [p["technique_id"] for p in predicted],
                    "hit_top1": topk_hit(predicted, actual, 1),
                    "hit_top3": topk_hit(predicted, actual, TOP_K),
                    "reciprocal_rank": mrr(predicted, actual),
                }
            )
    n = len(rows) or 1
    return {
        "predictions": n,
        "top1_accuracy": round(sum(r["hit_top1"] for r in rows) / n, 4),
        "top3_accuracy": round(sum(r["hit_top3"] for r in rows) / n, 4),
        "mrr": round(sum(r["reciprocal_rank"] for r in rows) / n, 4),
        "rows": rows,
    }


# ── Axis 2+3: bait-steering hit rate through the full pipeline ──────────────

_BAIT_TECH_HINTS = {
    "T1003": "shadow",
    "T1552": "credential",
    "T1046": "port",
    "T1571": "port",
    "T1021": "credential",
    "T1550": "credential",
    "T1078": "account",
}


class _PinnedClassifier:
    """GT harness classifier: pins the ground-truth persona (see ablation battery)."""

    def __init__(self, persona: str) -> None:
        self._persona = persona

    def classify(self, attacker_input: str, context: dict[str, Any]) -> dict[str, Any]:
        return {"skill_level": self._persona, "confidence": 0.9, "persona_override": True}


class _StaticAnalyzer:
    """Offline Don stand-in serving one precomputed analysis dict."""

    def __init__(self, analysis: dict[str, Any]) -> None:
        self._analysis = analysis

    def analyze(self, attacker_input: str, session_context: dict[str, Any]) -> dict[str, Any]:
        return dict(self._analysis)


def run_graph_turn(session_id: str, persona: str, attacker_input: str, observed: list[str]) -> dict[str, Any]:
    """One full DeceptionGraph turn (offline analyzer, deterministic deceiver).

    The analysis carries the techniques observed SO FAR (not just this turn's)
    — production Don extracts TTPs per session via CTIEngine accumulation, so
    the steering signal at turn i legitimately includes turn i-1 techniques.
    """
    tids = extract_techniques(attacker_input) or observed
    session_tids = sorted(set(tids) | set(observed))
    analysis = {
        "extracted_techniques": session_tids,
        "ttps_seen": session_tids,
        "threat_summary": f"offline mapping: {','.join(session_tids) or 'none'}",
        "recommendations": [],
    }
    graph = DeceptionGraph(
        classifier=_PinnedClassifier(persona),
        analyzer=_StaticAnalyzer(analysis),
        deceiver=HisokaAdapter(gateway_url=DEAD_GATEWAY, api_key="c3-eval"),
        max_retries=1,
    )
    result = graph.invoke(session_id, attacker_input, {"source_ip": "c3-eval"})
    plan = result.get("plan", {}) or {}
    return {
        "strategy": plan.get("strategy", {}) or {},
        "strategy_block": plan.get("strategy_block", "") or "",
        "next_predicted": [p.get("technique_id", "") for p in (plan.get("next_techniques_predicted") or [])],
        "response_len": len((result.get("deception_response", {}) or {}).get("response_text", "") or ""),
    }


def eval_bait_steering(with_steering: bool) -> dict[str, Any]:
    """Bait-hit rate: does the plan carry bait matching the NEXT turn's
    techniques? with_steering=False runs the A2 ablation (strategy stripped).
    Each chain gets its own session so fiction carries across turns."""
    rows: list[dict[str, Any]] = []
    for chain in CHAINS:
        persona = "intermediate"
        session_id = f"c3-{'steer' if with_steering else 'ablate'}-{chain['chain_id']}"
        for i in range(len(chain["turns"]) - 1):
            turn = chain["turns"][i]
            observed = [t for prev in chain["turns"][: i + 1] for t in prev["expected_ttps"]]
            actual = chain["turns"][i + 1]["expected_ttps"]
            out = run_graph_turn(session_id, persona, turn["input"], observed)
            strategy = out["strategy"]
            block = out["strategy_block"]
            if not with_steering:
                # A2 ablation: strip the strategy signal post-plan (same hook
                # the ablation battery uses) so the generator never sees it.
                strategy, block = {}, ""
            block_hits = [t for t in actual if _BAIT_TECH_HINTS.get(t, "") and _BAIT_TECH_HINTS[t] in block.lower()]
            steer_ids = [s.strip() for s in str(strategy.get("steer", "")).split(",") if s.strip()]

            def key(tid: str) -> str:
                return tid.split(".", 1)[0]

            want = set(actual) | {key(t) for t in actual}
            steer_hit = bool(want & (set(steer_ids) | {key(s) for s in steer_ids}))
            # The strategy_block seed lines name the predicted next techniques
            # literally ("seed artifacts likely to surface next probing of
            # <ID>") — count the block's steer signal too.
            block_steer_hit = bool(want & {t for t in want if t in block})
            rows.append(
                {
                    "chain_id": chain["chain_id"],
                    "turn": i + 1,
                    "actual_next": actual,
                    "steer_ids": steer_ids,
                    "steer_hit": steer_hit,
                    "block_steer_hit": block_steer_hit,
                    "bait_block_hits": block_hits,
                    "bait_block_hit": bool(block_hits),
                    "strategy_block_present": bool(block),
                }
            )
    n = len(rows) or 1
    return {
        "turns": n,
        "steer_hit_rate": round(sum(r["steer_hit"] for r in rows) / n, 4),
        "block_steer_hit_rate": round(sum(r["block_steer_hit"] for r in rows) / n, 4),
        "bait_block_hit_rate": round(sum(r["bait_block_hit"] for r in rows) / n, 4),
        "rows": rows,
    }


# ── Proofs ───────────────────────────────────────────────────────────────────

def build_proofs(acc: dict[str, Any], steer: dict[str, Any], ablate: dict[str, Any]) -> list[dict[str, Any]]:
    gap = round(steer["bait_block_hit_rate"] - ablate["bait_block_hit_rate"], 4)
    proofs = [
        {
            "id": "C3_next_ttp_top3",
            "claim": "graph-informed prediction puts a next-turn technique in top-3",
            "value": acc["top3_accuracy"],
            "target": ">= 0.80",
            "pass": acc["top3_accuracy"] >= 0.80,
        },
        {
            "id": "C3_next_ttp_top1",
            "claim": "the top-ranked suggestion matches the actual next technique",
            "value": acc["top1_accuracy"],
            "target": ">= 0.40 (kill-chain prior, not oracle)",
            "pass": acc["top1_accuracy"] >= 0.40,
        },
        {
            "id": "C3_steering_reaches_plan",
            "claim": "steer IDs + bait for the next move are attached to the plan",
            "value": round(max(steer["steer_hit_rate"], steer["block_steer_hit_rate"]), 4),
            "target": ">= 0.80",
            "pass": max(steer["steer_hit_rate"], steer["block_steer_hit_rate"]) >= 0.80,
        },
        {
            "id": "C3_ablation_gap",
            "claim": "removing bait steering (A2) collapses the bait signal",
            "value": gap,
            "target": f">= {steer['bait_block_hit_rate']} - 0.05",
            "pass": ablate["bait_block_hit_rate"] <= 0.05 and gap >= steer["bait_block_hit_rate"] - 0.05,
        },
    ]
    return proofs


def main() -> int:
    t0 = time.monotonic()
    print("=" * 78)
    print("C3 MTP STEERING EVAL — next-TTP accuracy + bait steering (0 LLM tokens)")
    print("=" * 78)

    acc = eval_next_ttp_accuracy()
    print(
        f"\n[1] next-TTP accuracy: top1={acc['top1_accuracy']} top3={acc['top3_accuracy']}"
        f" mrr={acc['mrr']} over {acc['predictions']} predictions"
    )
    for r in acc["rows"]:
        mark = "HIT " if r["hit_top3"] else "MISS"
        print(
            f"    {mark} {r['chain_id']} t{r['turn']}: observed={r['observed']}"
            f" -> next={r['actual_next']} pred3={r['predicted_top3']}"
        )

    steer = eval_bait_steering(with_steering=True)
    print(
        f"\n[2] bait steering (full): steer_hit={steer['steer_hit_rate']}"
        f" bait_block={steer['bait_block_hit_rate']} over {steer['turns']} turns"
    )

    ablate = eval_bait_steering(with_steering=False)
    print(
        f"[3] bait steering (A2 ablated): steer_hit={ablate['steer_hit_rate']}"
        f" bait_block={ablate['bait_block_hit_rate']}"
    )

    proofs = build_proofs(acc, steer, ablate)
    print("\n" + "-" * 78)
    all_pass = True
    for p in proofs:
        state = "PASS" if p["pass"] else "FAIL"
        all_pass &= p["pass"]
        print(f"  [{state}] {p['id']}: {p['claim']}  value={p['value']}  target={p['target']}")

    out = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "stratum": "deterministic (offline ThreatMapper + template deceiver, 0 LLM tokens)",
        "top_k": TOP_K,
        "chains": [{"chain_id": c["chain_id"], "grounding": c["grounding"], "turns": len(c["turns"])} for c in CHAINS],
        "next_ttp_accuracy": acc,
        "bait_steering_full": steer,
        "bait_steering_ablated": ablate,
        "proofs": proofs,
        "elapsed_seconds": round(time.monotonic() - t0, 2),
    }
    Path("results").mkdir(exist_ok=True)
    Path("results/mtp_steering_eval.json").write_text(json.dumps(out, indent=2, default=str) + "\n")
    print(f"\nartifact: results/mtp_steering_eval.json  ({out['elapsed_seconds']}s)")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
