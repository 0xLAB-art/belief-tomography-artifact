#!/usr/bin/env python3
"""Frozen prediction/evaluation skeleton for Laya vs Chrollo.

Design goal: accept final blinded/adjudicated labels later WITHOUT changing the
prediction logic. Ground truth is joined only after predictions are frozen.

This skeleton is intentionally minimal and conservative. It does not invent
combination rules after seeing outcomes.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

ROOT = Path(".")
if str(ROOT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(ROOT))

OUT_DIR = ROOT / "results" / "laya_research"
PACKET_PATH = OUT_DIR / "blind_annotation_packet_v2.json"


def load_packet() -> list[dict]:
    if not PACKET_PATH.exists():
        raise FileNotFoundError(PACKET_PATH)
    return json.loads(PACKET_PATH.read_text())


def run_chrollo_prediction(evidence: str) -> dict:
    """Placeholder for the frozen Chrollo prediction path.

    In the real evaluation this should call the same Chrollo code path used
    in serving, but here it must be implemented before labels exist and
    should not depend on later label-driven tuning.
    """
    # TODO: replace with the actual frozen Chrollo call.
    return {
        "class": "novice",
        "confidence": 0.5,
    }


def run_laya_prediction(evidence: str, timeout_s: float = 30.0) -> dict:
    """Placeholder for the frozen Laya prediction path.

    Returns SIGNAL or NO_SIGNAL plus the Laya answer payload and latency.
    """
    # TODO: replace with the actual frozen Laya runtime/infer call.
    t0 = time.perf_counter()
    time.sleep(0.0001)
    result = {
        "status": "SIGNAL",
        "answer": {
            "attack": {"type": "noul", "noul": 0.5, "confidence": 0.5},
            "stage": {"type": "choice", "choice": "recon", "probabilities": {"recon": 0.5}},
            "severity": {
                "type": "score",
                "score": 1,
                "confidence": 0.5,
                "legend": {"0": "no impact", "1": "suspicious but contained", "2": "clear attack activity", "3": "high-impact attack in progress"},
                "probabilities": {"0": 0.5, "1": 0.5},
            },
        },
        "latency_s": round(time.perf_counter() - t0, 4),
    }
    return result


def advise_from_laya(laya_result: dict, chrollo_result: dict) -> dict:
    """Define explicitly how advisory Laya changes a decision for C/D arms.

    This must be defined BEFORE reporting C/D results. A placeholder is included
    here as the structural hook; the real policy must be documented and frozen.
    """
    # Placeholder:
    # - If Laya is NO_SIGNAL, advisory has no effect.
    # - If Laya is SIGNAL, advisory may be used to flag disagreement for later
    #   adjudication; it does not automatically overwrite Chrollo here.
    if laya_result["status"] != "SIGNAL":
        return {"advisory_applied": False, "advisory_effect": "none"}
    return {
        "advisory_applied": True,
        "advisory_effect": "flag_for_adjudication",
        "note": "final combination rule must be frozen before C/D reporting",
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Frozen Laya vs Chrollo prediction skeleton")
    p.add_argument("--out", type=Path, default=OUT_DIR / "frozen_predictions.jsonl")
    p.add_argument("--laya-timeout", type=float, default=30.0)
    args = p.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    packet = load_packet()

    out_rows = []
    for item in packet:
        evidence = item["evidence"]
        chrollo = run_chrollo_prediction(evidence)
        laya = run_laya_prediction(evidence, timeout_s=args.laya_timeout)
        advise = advise_from_laya(laya, chrollo)

        out_rows.append(
            {
                "case_id": item["id"],
                "chrollo_class": chrollo["class"],
                "chrollo_confidence": chrollo["confidence"],
                "laya_status": laya["status"],
                "laya_answer": laya.get("answer"),
                "laya_latency_s": laya["latency_s"],
                "disagreement_flag": laya["status"] == "SIGNAL",
                "advisory": advise,
            }
        )

    with args.out.open("w", encoding="utf-8") as f:
        for row in out_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print("wrote frozen predictions:", args.out, "rows:", len(out_rows))


if __name__ == "__main__":
    main()
