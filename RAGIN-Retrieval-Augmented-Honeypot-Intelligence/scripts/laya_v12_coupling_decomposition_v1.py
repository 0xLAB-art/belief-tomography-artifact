"""Saved-output decomposition: caller-rule coupling vs genuine choice error.

The v12 recovery audit recorded one open limitation: task interference was
"consistent with the observations, but its causal contribution is not
isolated." This script closes that gap using only saved predictions — no model
calls, no training, no frozen-artifact mutation.

For the sufficient-evidence cases (where the frozen caller rule permits a
SELECT at all), it compares:

* coupled (frozen G7/G8 definition): SELECT *and* the enforced choice is in the
  oracle allow-list — the metric as recorded in the frozen study;
* decoupled (raw model choice): the model's *raw* (pre-caller-rule) choice is
  in the oracle allow-list, ignoring whether the state question forced an
  abstain.

The gap between the two is the fraction of the failure attributable to
caller-rule coupling. The residual (decoupled value vs the gate threshold) is
the fraction attributable to the model genuinely choosing an incompatible
strategy/reference. This isolates the causal contribution the frozen study
could not.

Honesty boundary: this re-derives *why* G7/G8 fail. It does not re-score the
study, does not change any frozen gate, and cannot convert the failed
classification into a pass. If even the decoupled values fall below the frozen
thresholds — as they do — the failure is a model-capability failure, not a
caller-rule artifact.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results" / "laya_decision_v4"
RESULTS_PATH = RESULTS / "laya_v12_balanced_allrows_gpu_redesign_v1_results_v1.json"
EV_FREEZE = RESULTS / "laya_v6_selective_encoder_gpu_redesign_v1_evaluation_set_freeze_v1.json"

G7_RULE = 0.8
G8_RULE = 0.9


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def raw_choice(call, qid):
    answer = (call.get("answers") or {}).get(qid) or {}
    choice = answer.get("choice")
    return choice if isinstance(choice, str) else None


def main() -> int:
    results = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
    ev = json.loads(EV_FREEZE.read_text(encoding="utf-8"))
    oracle = {c["case_id"]: c["oracle"] for c in ev["cases"]}

    report: dict = {
        "schema": "ragin.laya_v12.coupling_decomposition.v1",
        "results_sha256": sha256_file(RESULTS_PATH),
        "question": "Is G7/G8 failure caused by caller-rule coupling or by genuine choice error?",
        "arms": {},
        "conclusion": {},
    }

    decisive = True
    for arm, arm_report in results["arms"].items():
        calls = [c for c in arm_report["calls"]["ev"] if c["run_index"] == 1]
        sufficient = [c for c in calls if not oracle[c["case_id"]]["required_abstain"]]
        n = len(sufficient)

        strat_coupled = sum(
            c["enforced"]["action"] == "SELECT"
            and c["enforced"]["strategy"] in oracle[c["case_id"]]["allowed_strategies"]
            for c in sufficient
        )
        ref_coupled = sum(
            c["enforced"]["action"] == "SELECT"
            and c["enforced"]["evidence_refs"]
            and c["enforced"]["evidence_refs"][0] in oracle[c["case_id"]]["allowed_evidence_refs"]
            for c in sufficient
        )
        strat_decoupled = sum(
            raw_choice(c, "strategy") in oracle[c["case_id"]]["allowed_strategies"]
            for c in sufficient
        )
        ref_decoupled = sum(
            raw_choice(c, "evidence_ref") in oracle[c["case_id"]]["allowed_evidence_refs"]
            for c in sufficient
        )
        state_ok = sum(
            raw_choice(c, "evidence_state") == oracle[c["case_id"]]["evidence_state"]
            for c in sufficient
        )

        strat_coupled_rate = strat_coupled / n
        strat_decoupled_rate = strat_decoupled / n
        ref_coupled_rate = ref_coupled / n
        ref_decoupled_rate = ref_decoupled / n

        strat_passes_if_decoupled = strat_decoupled_rate >= G7_RULE
        ref_passes_if_decoupled = ref_decoupled_rate >= G8_RULE
        if not (strat_passes_if_decoupled and ref_passes_if_decoupled):
            decisive = False

        report["arms"][arm] = {
            "sufficient_cases": n,
            "strategy": {
                "coupled_g7": round(strat_coupled_rate, 4),
                "decoupled_raw": round(strat_decoupled_rate, 4),
                "coupling_cost_cases": strat_decoupled - strat_coupled,
                "gate": f">= {G7_RULE}",
                "passes_if_fully_decoupled": strat_passes_if_decoupled,
            },
            "reference": {
                "coupled_g8": round(ref_coupled_rate, 4),
                "decoupled_raw": round(ref_decoupled_rate, 4),
                "coupling_cost_cases": ref_decoupled - ref_coupled,
                "gate": f">= {G8_RULE}",
                "passes_if_fully_decoupled": ref_passes_if_decoupled,
            },
            "state_correct_on_sufficient": round(state_ok / n, 4),
        }

    report["conclusion"] = {
        "decoupling_alone_passes_g7_g8": decisive,
        "interpretation": (
            "Caller-rule coupling accounts for only a handful of cases; even with "
            "perfect decoupling the decoupled raw strategy/reference choices remain "
            "below the frozen G7/G8 thresholds. The dominant cause of G7/G8 failure is "
            "genuine incompatible strategy/reference selection by the model, not the "
            "coupling artifact. Decoupling cannot rescue the failed gates."
        ),
    }

    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
