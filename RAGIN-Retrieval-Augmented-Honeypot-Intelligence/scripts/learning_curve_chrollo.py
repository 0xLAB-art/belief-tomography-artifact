#!/usr/bin/env python3
"""Learning-curve study for the Chrollo classifier.

Trains the shipped configuration (500 trees / depth 16 / unweighted) on
growing stratified subsets of the 1,600-session training pool and
evaluates on the fixed 400-session held-out set, with multiple
subsample seeds per size. Fits a power law acc(n) = a - b * n^(-c) to
project the accuracy at 2x and 10x the current corpus and reports
whether more data would keep helping.

Outputs:
  results/model_quality/chrollo_learning_curve.png
  results/model_quality/chrollo_learning_curve.json

Usage:
    python scripts/learning_curve_chrollo.py [--reps 5]
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import curve_fit
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ragin.chrollo.classifier import _LABEL_INV, _LABEL_MAP
from ragin.chrollo.features import FEATURE_NAMES, FeatureExtractor
from ragin.chrollo.models import SessionLog, SkillLevel

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data" / "training"
RESULTS_DIR = REPO_ROOT / "results" / "model_quality"
SIZES = [100, 200, 400, 800, 1200, 1600]


def load_split(path: Path) -> tuple[list[SessionLog], np.ndarray]:
    sessions, labels = [], []
    with path.open() as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            labels.append(_LABEL_MAP[SkillLevel(record.pop("skill_level"))])
            sessions.append(SessionLog(**record))
    return sessions, np.array(labels, dtype=np.int32)


def wilson_ci(correct: int, n: int, z: float = 1.96) -> tuple[float, float]:
    p = correct / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return center - half, center + half


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reps", type=int, default=5)
    args = ap.parse_args()

    train_sessions, y_train = load_split(DATA_DIR / "train.jsonl")
    test_sessions, y_test = load_split(DATA_DIR / "test.jsonl")

    featurizer = FeatureExtractor()
    X_train = np.array([[featurizer.extract(s)[f] for f in FEATURE_NAMES] for s in train_sessions], dtype=np.float64)
    X_test = np.array([[featurizer.extract(s)[f] for f in FEATURE_NAMES] for s in test_sessions], dtype=np.float64)

    by_class = {c: np.where(y_train == c)[0] for c in range(4)}
    results = []
    for size in SIZES:
        per_size = []
        for rep in range(args.reps):
            rng = np.random.default_rng(1000 + rep)
            n_per_class = size // 4
            idx = np.concatenate([rng.choice(by_class[c], n_per_class, replace=False) for c in range(4)])
            scaler = StandardScaler()
            X_sub = scaler.fit_transform(X_train[idx])
            rf = RandomForestClassifier(
                n_estimators=500, max_depth=16, min_samples_split=5, min_samples_leaf=1,
                class_weight=None, random_state=42, n_jobs=-1,
            ).fit(X_sub, y_train[idx])
            acc = float((rf.predict(scaler.transform(X_test)) == y_test).mean())
            per_size.append(acc)
        mean_acc = float(np.mean(per_size))
        ci = wilson_ci(round(mean_acc * len(y_test)), len(y_test))
        results.append({
            "size": size,
            "reps": args.reps,
            "mean_accuracy": round(mean_acc, 4),
            "std": round(float(np.std(per_size)), 4),
            "min": round(min(per_size), 4),
            "max": round(max(per_size), 4),
            "wilson95": [round(ci[0], 4), round(ci[1], 4)],
        })
        print(f"n={size:>5}: acc={mean_acc:.4f} ± {np.std(per_size):.4f}  (min {min(per_size):.3f}, max {max(per_size):.3f})")

    # ── Power-law fit: acc(n) = a - b * n^(-c) ────────────────────────────
    ns = np.array([r["size"] for r in results], dtype=float)
    ys = np.array([r["mean_accuracy"] for r in results], dtype=float)

    def power_law(n, a, b, c):
        return a - b * n ** (-c)

    bounds = ([0.5, 0.0, 0.1], [1.0, 1.0, 3.0])
    p0 = [0.95, 1.0, 0.5]
    try:
        popt, _ = curve_fit(power_law, ns, ys, p0=p0, bounds=bounds, maxfev=10000)
        a, b, c = map(float, popt)
        projections = {
            "3200": round(float(power_law(3200, a, b, c)), 4),
            "10000": round(float(power_law(10000, a, b, c)), 4),
        }
        residual = float(np.sqrt(np.mean((power_law(ns, a, b, c) - ys) ** 2)))
        fit_note = f"acc(n) = {a:.3f} - {b:.2f} * n^-{c:.2f}  (RMSE {residual:.4f})"
    except RuntimeError:
        a = b = c = None
        projections = {}
        fit_note = "power-law fit did not converge"

    # ── Verdict ───────────────────────────────────────────────────────────
    # Noise floor: std of the largest-size repeats. Deltas smaller than this
    # are indistinguishable from subsample noise.
    noise = max(results[-1]["std"], results[-2]["std"], 0.005)
    last_gain = results[-1]["mean_accuracy"] - results[-2]["mean_accuracy"]
    prev_gain = results[-2]["mean_accuracy"] - results[-3]["mean_accuracy"]
    projected_2x = projections.get("3200")
    projected_gain_2x = (projected_2x - results[-1]["mean_accuracy"]) if projected_2x else None
    if abs(last_gain) < noise and abs(prev_gain) < noise:
        verdict = (f"plateaued: the curve is flat within noise (±{noise:.3f}) from "
                   f"n={results[-3]['size']}; more data of this generator would add "
                   f"≈{projected_gain_2x * 100:+.1f}pp at 2x and nothing operationally meaningful")
    elif projected_gain_2x is not None and projected_gain_2x < 0.01:
        verdict = (f"diminishing returns: last gain {last_gain * 100:+.1f}pp vs "
                   f"{prev_gain * 100:+.1f}pp before it; a 2x corpus projects only "
                   f"{projected_gain_2x * 100:+.1f}pp more")
    elif last_gain < prev_gain:
        verdict = (f"still climbing but slowing: last gain {last_gain * 100:+.1f}pp "
                   f"vs {prev_gain * 100:+.1f}pp; expect <1pp more from a 2x corpus")
    else:
        verdict = (f"still climbing: last gain {last_gain * 100:+.1f}pp "
                   f">= {prev_gain * 100:+.1f}pp; a 2x corpus should yield another "
                   "meaningful gain")

    # ── Plot ──────────────────────────────────────────────────────────────
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7, 4.4))
    stds = [r["std"] for r in results]
    ax.errorbar(ns, ys, yerr=stds, fmt="o-", color="#1f77b4", capsize=3,
                label=f"held-out accuracy (mean ± std over {args.reps} subsample seeds)")
    if a is not None:
        grid = np.geomspace(80, 10000, 200)
        ax.plot(grid, power_law(grid, a, b, c), "--", color="#d62728", lw=1,
                label=fit_note)
        for n_proj, y_proj in projections.items():
            ax.scatter([int(n_proj)], [y_proj], marker="x", color="#d62728", zorder=5)
    ax.axhline(ys[-1], color="gray", lw=0.5)
    ax.set_xscale("log")
    ax.set_xticks(SIZES + [3200, 10000])
    ax.set_xticklabels([str(s) for s in SIZES + [3200, 10000]])
    ax.set_xlabel("Training corpus size (sessions)")
    ax.set_ylabel("Held-out accuracy (n=400)")
    ax.set_title("Chrollo learning curve — 500 trees / depth 16 / unweighted")
    ax.legend(fontsize=8)
    fig.tight_layout()
    out_png = RESULTS_DIR / "chrollo_learning_curve.png"
    fig.savefig(out_png, dpi=150)
    plt.close(fig)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "config": {"n_estimators": 500, "max_depth": 16, "min_samples_split": 5,
                   "min_samples_leaf": 1, "class_weight": None, "random_state": 42},
        "eval_set": {"n": len(y_test), "source": "data/training/test.jsonl"},
        "curve": results,
        "power_law_fit": {"a": a, "b": b, "c": c, "note": fit_note,
                          "projections": projections},
        "verdict": verdict,
        "plot": str(out_png.relative_to(REPO_ROOT)),
    }
    out_json = RESULTS_DIR / "chrollo_learning_curve.json"
    out_json.write_text(json.dumps(report, indent=2))
    print(f"\nVerdict: {verdict}")
    print(f"Saved: {out_json.relative_to(REPO_ROOT)} and {out_png.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
