#!/usr/bin/env python3
"""Build consensus.json from per-evaluator scored JSON files.

Reads evaluator-alpha.json, evaluator-beta.json, evaluator-gamma.json
from results/human_eval_scored/, computes per-scenario consensus means/ranges/
agreement, and writes a fresh consensus.json with correct data.

The old consensus.json (Jul 28) had a duplication bug — per-evaluator scores
were identical across all 8 scenarios. The per-evaluator files (Jul 29) contain
the correct varying scores. This script fixes the consensus.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

SCORED_DIR = Path(os.environ.get("CONSENSUS_SCORED_DIR", "results/human_eval_scored"))
EVALUATORS = ["evaluator-alpha", "evaluator-beta", "evaluator-gamma"]
DIMS = ["deception", "persona", "ttp_accuracy", "engagement", "artifact_safety"]


def load_evaluator(eid: str) -> dict:
    path = SCORED_DIR / f"{eid}.json"
    return json.loads(path.read_text())


def compute_consensus() -> dict:
    # Load all 3 evaluator files
    evals = {eid: load_evaluator(eid) for eid in EVALUATORS}

    # Build scenario index: scenario_id -> {evaluator_id -> scenario_data}
    scenario_map: dict[str, dict] = {}
    for eid, data in evals.items():
        for sc in data["scenarios"]:
            sid = sc["scenario_id"]
            scenario_map.setdefault(sid, {})[eid] = sc

    scenario_ids = sorted(scenario_map.keys())
    sessions = []

    for sid in scenario_ids:
        per_ev = scenario_map[sid]

        # Collect scores per dimension across evaluators
        dim_values: dict[str, list[int]] = {d: [] for d in DIMS}
        danger_signals: list[bool] = []
        exact_agreements = 0

        for eid in EVALUATORS:
            sc = per_ev[eid]
            scores = sc["scores"]
            for d in DIMS:
                dim_values[d].append(scores[d])
            danger_signals.append(sc.get("danger_signal_triggered", False))

        # Compute statistics
        mean_scores = {}
        score_ranges = {}
        consensus_scores = {}
        for d in DIMS:
            vals = dim_values[d]
            mean_scores[d] = round(sum(vals) / len(vals), 2)
            score_ranges[d] = max(vals) - min(vals)
            consensus_scores[d] = round(mean_scores[d])

        # Exact agreement: all 3 evaluators gave identical score for a dimension
        for d in DIMS:
            if len(set(dim_values[d])) == 1:
                exact_agreements += 1
        exact_agreement_rate = round(exact_agreements / len(DIMS), 3)

        # Consensus overall = mean of mean_scores
        consensus_overall = round(sum(mean_scores.values()) / len(DIMS), 1)

        # Danger signal consensus = majority
        danger_consensus = sum(danger_signals) > len(danger_signals) / 2

        # Per-evaluator block
        per_evaluator = {}
        for eid in EVALUATORS:
            sc = per_ev[eid]
            per_evaluator[eid] = {
                "scores": sc["scores"],
                "danger_signal_triggered": sc.get("danger_signal_triggered", False),
                "rationale": sc.get("rationale", {}),
                "elapsed_s": sc.get("elapsed_s", 0),
            }

        # Pick pipeline_output and ground_truth from first evaluator (they're identical)
        first = per_ev[EVALUATORS[0]]
        sessions.append(
            {
                "scenario_id": sid,
                "consensus_scores": consensus_scores,
                "mean_scores": mean_scores,
                "score_ranges": score_ranges,
                "consensus_overall": consensus_overall,
                "exact_agreement_rate": exact_agreement_rate,
                "danger_signal_consensus": danger_consensus,
                "evaluator_count": len(EVALUATORS),
                "per_evaluator": per_evaluator,
                "pipeline_output": first.get("pipeline_output", {}),
                "ground_truth": first.get("ground_truth", {}),
            }
        )

    # Compute overall summary
    overall_means = [s["consensus_overall"] for s in sessions]
    mean_consensus = round(sum(overall_means) / len(overall_means), 2)

    agreement_rates = [s["exact_agreement_rate"] for s in sessions]
    mean_agreement = round(sum(agreement_rates) / len(agreement_rates), 3)

    scenarios_above_3 = sum(1 for m in overall_means if m >= 3.0)
    scenarios_below_2 = sum(1 for m in overall_means if m < 2.0)

    # Collect pipeline_output and ground_truth for key weakness/strength analysis
    gt_texts = []
    for s in sessions:
        gt = s.get("ground_truth", {})
        po = s.get("pipeline_output", {})
        gt_texts.append(
            {
                "sid": s["scenario_id"],
                "overall": s["consensus_overall"],
                "scenario_text": f"GT scenario {s['scenario_id']}: {gt.get('attacker_input', '?')[:60]}",
                "persona_used": po.get("persona_used", "?"),
                "ttps_extracted": po.get("ttps_extracted", []),
                "ttps_expected": gt.get("expected_ttps", []),
                "danger_consensus": s["danger_signal_consensus"],
            }
        )

    # Identify best/worst scenarios
    sorted_by_score = sorted(gt_texts, key=lambda x: x["overall"])
    worst = sorted_by_score[0] if sorted_by_score else None
    best = sorted_by_score[-1] if sorted_by_score else None

    key_weaknesses: list[str] = []
    key_strengths = []

    if worst:
        key_weaknesses.insert(0, f"{worst['scenario_text']} rated lowest at {worst['overall']:.2f}")

    # Data-derived narratives — NEVER hardcode claims here. The Jul 2026
    # consensus bug was exactly this: canned weakness/strength strings that
    # contradicted the scores they sat next to.
    artifact_scores = [s["mean_scores"].get("artifact_safety", 0) for s in sessions if s.get("mean_scores")]
    n_as_le2 = sum(1 for v in artifact_scores if v <= 2)
    if artifact_scores and n_as_le2 > len(artifact_scores) / 2:
        key_weaknesses.append(
            f"Artifact safety rated ≤2 in {n_as_le2}/{len(artifact_scores)} scenarios (danger-signal bias suspected)"
        )
    else:
        key_strengths.append(
            f"Artifact safety rated ≥3 in {len(artifact_scores) - n_as_le2}/{len(artifact_scores)} scenarios"
        )

    persona_scores = [s["mean_scores"].get("persona", 0) for s in sessions if s.get("mean_scores")]
    n_persona_le2 = sum(1 for v in persona_scores if v <= 2)
    if persona_scores and n_persona_le2 > len(persona_scores) / 2:
        key_weaknesses.append(f"Persona consistency rated ≤2 in {n_persona_le2}/{len(persona_scores)} scenarios")
    elif persona_scores:
        n_ok = len(persona_scores) - n_persona_le2
        key_strengths.append(f"Persona consistency rated ≥3 in {n_ok}/{len(persona_scores)} scenarios")

    if best:
        key_strengths.append(f"{best['scenario_text']} rated best at {best['overall']:.2f}")
    strong = [x for x in sorted_by_score if x["overall"] >= 4.0]
    if strong:
        key_strengths.append(f"{len(strong)}/{len(sorted_by_score)} scenarios rated 4+/5")

    result = {
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "total_scenarios": len(scenario_ids),
            "evaluators": EVALUATORS,
            "model": "openai/gpt-4o-mini",
            "builder": "scripts/build_consensus.py",
            "note": "Rebuilt from per-evaluator JSON files. Old consensus (Jul 28) had duplication bug.",
        },
        "overall_summary": {
            "mean_consensus_score": mean_consensus,
            "mean_inter_rater_agreement": mean_agreement,
            "scenarios_above_3": scenarios_above_3,
            "scenarios_below_2": scenarios_below_2,
            "key_weaknesses": key_weaknesses,
            "key_strengths": key_strengths,
        },
        "evaluation_sessions": sessions,
    }

    return result


def main() -> None:
    global SCORED_DIR
    ap = argparse.ArgumentParser(description="Build consensus.json from per-evaluator scored files")
    ap.add_argument("--scored-dir", default=str(SCORED_DIR), help="Dir containing evaluator-*.json")
    ap.add_argument("--model", default="qwen--qwen38-27b (Azure AI Foundry)", help="Model name recorded in meta")
    ap.add_argument("--label", default="", help="Short label appended to meta.note")
    args = ap.parse_args()

    SCORED_DIR = Path(args.scored_dir)

    consensus = compute_consensus()
    consensus["meta"]["model"] = args.model
    if args.label:
        consensus["meta"]["note"] += f" | {args.label}"

    # Preserve protocol and rubrics from old consensus if it exists
    old_path = SCORED_DIR / "consensus.json"
    if old_path.exists():
        old = json.loads(old_path.read_text())
        consensus["protocol"] = old.get("protocol", "")
        consensus["rubrics"] = old.get("rubrics", [])

    out_path = SCORED_DIR / "consensus.json"
    out_path.write_text(json.dumps(consensus, indent=2))
    print(f"Wrote {out_path}")
    print(f"  {len(consensus['evaluation_sessions'])} scenarios")
    print(f"  Overall mean: {consensus['overall_summary']['mean_consensus_score']:.2f}")
    print(f"  Mean inter-rater agreement: {consensus['overall_summary']['mean_inter_rater_agreement']:.3f}")


if __name__ == "__main__":
    main()
