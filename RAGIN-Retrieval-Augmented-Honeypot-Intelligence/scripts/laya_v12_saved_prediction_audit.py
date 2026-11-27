"""Audit saved v12 predictions only: no model calls, training, or output rewrites."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results/laya_decision_v4"


def main():
    results = json.loads((RESULTS / "laya_v12_balanced_allrows_gpu_redesign_v1_results_v1.json").read_text())
    cases = json.loads((RESULTS / "laya_v6_selective_encoder_gpu_redesign_v1_evaluation_set_freeze_v1.json").read_text())["cases"]
    oracle = {case["case_id"]: case["oracle"] for case in cases}
    primary = {}
    for arm, report in results["arms"].items():
        calls = [call for call in report["calls"]["ev"] if call["run_index"] == 1]
        assert len(calls) == len(oracle) == len({call["case_id"] for call in calls})
        primary[arm] = {call["case_id"]: call for call in calls}
        sufficient = [call for call in calls if not oracle[call["case_id"]]["required_abstain"]]
        counts = {}
        for question, allowed in (("strategy", "allowed_strategies"), ("evidence_ref", "allowed_evidence_refs")):
            counts[question + "_raw_correct_on_sufficient"] = sum(
                call["answers"][question]["choice"] in oracle[call["case_id"]][allowed]
                for call in sufficient
            )
        counts["sufficient_cases"] = len(sufficient)
        counts["state_correct"] = sum(call["answers"]["evidence_state"]["choice"] == oracle[call["case_id"]]["evidence_state"] for call in calls)
        print(arm, json.dumps(counts, sort_keys=True))
    changes = {question: sum(primary["english"][cid]["answers"][question]["choice"] != call["answers"][question]["choice"] for cid, call in primary["tuning-candidate"].items()) for question in ("evidence_state", "strategy", "evidence_ref")}
    print("changed_predictions_vs_base", json.dumps(changes, sort_keys=True))


if __name__ == "__main__":
    main()
