"""Analyze the recorded real-inference pilot into matched ablation evidence.

Reads results/laya_research/real_inference_cpu_pilot.jsonl (raw records from the
actual model run) and computes per-case paired metrics against trivial baselines
(always-benign and random with seed), writing
results/laya_research/matched_ablation_analysis.json.

Baselines from data only — B0: predict benign for every case; R0: seeded random
coin. These are lower bounds a real assessment provider must exceed; no
unverifiable claim is made about Chrollo/Hisoka deltas because the full
downstream pipeline was not exercised in this pilot.
"""
from __future__ import annotations

import json
import random
import statistics
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "results/laya_research/real_inference_cpu_pilot.jsonl"
OUT = REPO / "results/laya_research/matched_ablation_analysis.json"


def prf(tp: int, fp: int, tn: int, fn: int) -> dict:
    n = tp + fp + tn + fn
    acc = (tp + tn) / n if n else None
    prec = tp / (tp + fp) if (tp + fp) else None
    rec = tp / (tp + fn) if (tp + fn) else None
    f1 = (2 * prec * rec / (prec + rec)) if (prec is not None and rec is not None and prec + rec) else None
    spec = tn / (tn + fp) if (tn + fp) else None
    bal_acc = None
    if rec is not None and spec is not None:
        bal_acc = (rec + spec) / 2
    return {
        "tp": tp, "fp": fp, "tn": tn, "fn": fn, "n": n,
        "accuracy": acc, "precision": prec, "recall": rec, "f1": f1,
        "specificity": spec, "balanced_accuracy": bal_acc,
    }


def main() -> None:
    data = json.loads(SRC.read_text())
    records = data["records"]
    y = [r["y"] for r in records]
    p = [float(r["p_true"]) for r in records]  # noul P(true) from real weights

    n = len(records)
    n_pos = sum(y)
    n_neg = n - n_pos

    # Lay preds at 0.5
    lay_pred = [1 if v > 0.5 else 0 for v in p]
    lay_tp = sum(1 for q, t in zip(lay_pred, y) if q == 1 and t == 1)
    lay_fp = sum(1 for q, t in zip(lay_pred, y) if q == 1 and t == 0)
    lay_tn = sum(1 for q, t in zip(lay_pred, y) if q == 0 and t == 0)
    lay_fn = sum(1 for q, t in zip(lay_pred, y) if q == 0 and t == 1)
    lay = prf(lay_tp, lay_fp, lay_tn, lay_fn)

    # Brier + ECE (10 bins)
    brier = statistics.mean((v - t) ** 2 for v, t in zip(p, y))
    bins = [0.0] * 10
    bins_n = [0] * 10
    for v, t in zip(p, y):
        bidx = min(int(v * 10), 9)
        bins[bidx] += (v - t) ** 2
        bins_n[bidx] += 1
    ece = sum(
        (bins_n[i] / n) * (statistics.mean([ (vv - tt) ** 2 for vv, tt in zip(p, y) if min(int(vv*10),9)==i ]) if bins_n[i] else 0.0)
        for i in range(10)
    )

    # B0 always-benign
    b0_tp = b0_fp = 0
    b0_tn = n_neg
    b0_fn = n_pos
    b0 = prf(b0_tp, b0_fp, b0_tn, b0_fn)

    # R0 seeded random coin, 1000 draws for stability
    rng = random.Random(20261012)
    samples = []
    k_pos = sum(1 for v in bin(0, 0).split("x")) if False else None  # placeholder no-op
    draws = 1000
    for _ in range(draws):
        tp = fp = tn = fn = 0
        for t in y:
            q = 1 if rng.random() > 0.5 else 0
            if q == t:
                if t == 1:
                    tp += 1
                else:
                    tn += 1
            else:
                if t == 1:
                    fn += 1
                else:
                    fp += 1
        samples.append(prf(tp, fp, tn, fn))
    r0_acc_samples = [s["accuracy"] for s in samples]
    r0_bal_samples = [s["balanced_accuracy"] for s in samples]
    r0 = {
        "method": "seeded random coin (p=0.5), 1000 draws, seed 20261012",
        "accuracy_mean": statistics.mean(r0_acc_samples),
        "accuracy_std": statistics.stdev(r0_acc_samples),
        "balanced_accuracy_mean": statistics.mean(r0_bal_samples),
        "balanced_accuracy_std": statistics.stdev(r0_bal_samples),
    }

    lat = [r["latency_ms"] for r in records]
    out = {
        "model": data["summary"],
        "english_pinned_revision": data["revision"],
        "weights_sha256": data["weights_sha256"],
        "cases": n,
        "positives": n_pos,
        "negatives": n_neg,
        "configs": {
            "A_baseline_no_assessment": {
                "note": "no provider signal; classification falls back to Chrollo RF only",
                "assessment_accuracy": None,
            },
            "B_laya_enabled": lay,
            "B0_always_benign": b0,
            "R0_random": r0,
        },
        "probabilistic": {
            "brier": brier,
            "note_ece":
                "ECE computed per-bin on 10 equal-width bins over resulting probabilities; "
                "the checkpoint ships an invalid temperature for choice:11+ so laya itself "
                "warns probabilities/values may be uncalibrated (see laya router warning).",
            "ece_10bin": ece,
        },
        "latency_ms": {
            "p50": statistics.median(lat),
            "mean": statistics.mean(lat),
            "p95": sorted(lat)[int(0.95 * len(lat)) - 1],
            "load_route_first_call": data["summary"]["route_load_ms"],
        },
        "limitations": [
            "Pilot of %d synthetic cases; not a matched production population." % n,
            "Ground truth is by-construction labels, not historical Cowrie ground truth.",
            "Downstream effects on Hisoka/deception policy were not exercised in this pilot run; "
            "A-vs-B paired differences are limited to the assessment boundary itself.",
            "laya 0.4.2 warns this checkpoint ships invalid temperatures for some choice "
            "questions; probabilities should be treated as uncalibrated until temperature "
            "fitting is done on held-out cybersecurity data.",
        ],
    }

    OUT.write_text(json.dumps(out, indent=1, default=str))
    print("saved:", OUT)
    print(json.dumps({k: out["configs"][k] for k in ("B_laya_enabled", "B0_always_benign")}, indent=1))
    print("brier:", round(brier, 4), "ece:", round(ece, 4))


if __name__ == "__main__":
    main()
