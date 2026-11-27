#!/usr/bin/env python3
"""Calibration analysis for the Chrollo classifier's confidence scores.

Answers the operational question: can the 0.85 escalation threshold be
trusted as "confidence means what it says"?

Outputs (over the fixed 400-session held-out set, via the production
classify() path on the shipped artifact):

* reliability curve (binned observed accuracy vs mean predicted
  confidence) + PNG plot,
* ECE (equal-mass 15-bin), MCE, Brier score, and overall accuracy vs
  mean confidence,
* a threshold-band table scanning s in [0.50, 1.00] in 0.05 steps:
  coverage, accuracy, cross-tier errors, and Wilson 95% CIs,
* per-class confidence/accuracy breakdown (the classifier's confidence
  is calibrated per the confusion structure, not per class),
* Platt scaling (logistic on log-prob margin) as a post-hoc reference,
  fitted on the training split via 5-fold OOF predictions -- reported
  but NOT shipped (no runtime change; the artifact stays as-is).

Usage:
    python scripts/calibrate_chrollo.py
"""

from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ragin.chrollo.classifier import ChrolloClassifier, _LABEL_INV, _LABEL_MAP
from ragin.chrollo.features import FEATURE_NAMES, FeatureExtractor
from ragin.chrollo.models import SessionLog, SkillLevel

REPO_ROOT = Path(__file__).resolve().parent.parent
MODEL_DIR = REPO_ROOT / "models" / "chrollo"
DATA_DIR = REPO_ROOT / "data" / "training"
RESULTS_DIR = REPO_ROOT / "results" / "model_quality"
TIERS = ["novice", "intermediate", "expert", "apt"]


def wilson_ci(correct: int, n: int, z: float = 1.96) -> tuple[float, float]:
    p = correct / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return center - half, center + half


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


def main() -> None:
    # ── Load data + shipped artifact ─────────────────────────────────────
    test_sessions, y_test = load_split(DATA_DIR / "test.jsonl")
    train_sessions, y_train = load_split(DATA_DIR / "train.jsonl")

    clf = ChrolloClassifier(model_path=MODEL_DIR / "rf_classifier.joblib")
    if clf._model is None:
        sys.exit("No shipped model found — run scripts/retrain_chrollo.py first.")

    order = [0, 1, 2, 3]  # classes_ is sorted, so proba columns align with 0..3

    # Production-path predictions on the held-out set: confidence and full
    # probability vector via the same scaled features classify() uses.
    featurizer = FeatureExtractor()
    X_test = np.array(
        [[featurizer.extract(s)[f] for f in FEATURE_NAMES] for s in test_sessions],
        dtype=np.float64,
    )
    proba_test = clf._model.predict_proba(clf._scaler.transform(X_test))
    conf_test = proba_test.max(axis=1)
    y_pred = np.array(order)[proba_test.argmax(axis=1)]
    correct = (y_pred == y_test)

    # Sanity: the vectorized path must agree with the production classify().
    # classify() rounds confidence to 4 decimals, so allow half-a-ulp there.
    for s, p_vec, p_cls in zip(test_sessions[:5], proba_test[:5], conf_test[:5], strict=True):
        res = clf.classify(s)
        assert res.skill_level.value == _LABEL_INV[int(np.argmax(p_vec))], "path mismatch"
        assert abs(res.confidence - p_cls) <= 5e-5, f"confidence mismatch {res.confidence} vs {p_cls}"

    # ── Reliability curve (equal-mass bins) ──────────────────────────────
    n_bins = 15
    qs = np.quantile(conf_test, np.linspace(0, 1, n_bins + 1))
    bins = []
    for i in range(n_bins):
        lo, hi = qs[i], qs[i + 1]
        mask = (conf_test >= lo) & (conf_test <= hi) if i == n_bins - 1 else (conf_test >= lo) & (conf_test < hi)
        n_b = int(mask.sum())
        if n_b == 0:
            continue
        acc_b = float(correct[mask].mean())
        conf_b = float(conf_test[mask].mean())
        ci = wilson_ci(int(correct[mask].sum()), n_b)
        bins.append({
            "bin": i + 1, "range": [round(lo, 4), round(hi, 4)], "n": n_b,
            "mean_confidence": round(conf_b, 4), "accuracy": round(acc_b, 4),
            "wilson95": [round(ci[0], 4), round(ci[1], 4)],
            "gap": round(conf_b - acc_b, 4),
        })

    # Equal-mass ECE: sum over bins of (n_b/N) * |acc_b - conf_b|
    ece = sum(b["n"] / len(y_test) * abs(b["gap"]) for b in bins)
    mce = max(abs(b["gap"]) for b in bins)
    brier = float(np.mean(np.sum((proba_test - np.eye(4)[y_test]) ** 2, axis=1)))

    overall_acc = float(correct.mean())
    mean_conf = float(conf_test.mean())

    # ── Threshold-band scan ───────────────────────────────────────────────
    threshold_scan = []
    for tau in np.arange(0.50, 1.0001, 0.05):
        mask = conf_test >= tau - 1e-9
        n_t = int(mask.sum())
        entry = {
            "threshold": round(float(tau), 2),
            "n": n_t,
            "coverage": round(n_t / len(y_test), 4),
            "accuracy": round(float(correct[mask].mean()), 4) if n_t else None,
        }
        if n_t:
            ci = wilson_ci(int(correct[mask].sum()), n_t)
            entry["wilson95"] = [round(ci[0], 4), round(ci[1], 4)]
            xt = 0
            for t, p in zip(y_test[mask], y_pred[mask], strict=True):
                if t != p and abs(int(t) - int(p)) > 1:
                    xt += 1
            entry["cross_tier_errors"] = xt
        threshold_scan.append(entry)

    # ── Per-class confidence vs accuracy ─────────────────────────────────
    per_class = {}
    for c in range(4):
        mask = y_test == c
        per_class[_LABEL_INV[c]] = {
            "n": int(mask.sum()),
            "accuracy": round(float(correct[mask].mean()), 4),
            "mean_confidence": round(float(conf_test[mask].mean()), 4),
            "mean_gap": round(float(conf_test[mask].mean() - correct[mask].mean()), 4),
        }

    # ── Platt scaling reference (fitted on training-split OOF preds) ─────
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    oof_conf, oof_correct = [], []
    featurizer = FeatureExtractor()
    X_train = np.array([[featurizer.extract(s)[f] for f in FEATURE_NAMES] for s in train_sessions], dtype=np.float64)
    for tr_idx, va_idx in skf.split(X_train, y_train):
        scaler = StandardScaler()
        X_tr = scaler.fit_transform(X_train[tr_idx])
        rf = RandomForestClassifier(
            n_estimators=500, max_depth=16, min_samples_split=5, min_samples_leaf=1,
            class_weight=None, random_state=42, n_jobs=-1,
        ).fit(X_tr, y_train[tr_idx])
        proba_va = rf.predict_proba(scaler.transform(X_train[va_idx]))
        oof_conf.extend(proba_va.max(axis=1).tolist())
        oof_correct.extend((proba_va.argmax(axis=1) == y_train[va_idx]).astype(int).tolist())
    oof_conf = np.array(oof_conf)
    oof_correct = np.array(oof_correct, dtype=float)
    # Platt: logistic regression of correctness on logit(conf) clipped.
    eps = 1e-6
    logits = np.log(np.clip(oof_conf, eps, 1 - eps) / np.clip(1 - oof_conf, eps, 1 - eps)).reshape(-1, 1)
    platt = LogisticRegression(max_iter=1000).fit(logits, oof_correct)
    platt_a, platt_b = float(platt.coef_[0][0]), float(platt.intercept_[0])
    # Test-side calibrated curve using the same transform.
    test_logits = np.log(np.clip(conf_test, eps, 1 - eps) / np.clip(1 - conf_test, eps, 1 - eps)).reshape(-1, 1)
    platt_test_conf = platt.predict_proba(test_logits)[:, 1]
    platt_bins = []
    qs_p = np.quantile(platt_test_conf, np.linspace(0, 1, n_bins + 1))
    for i in range(n_bins):
        lo, hi = qs_p[i], qs_p[i + 1]
        mask = (platt_test_conf >= lo) & (platt_test_conf <= hi) if i == n_bins - 1 else (platt_test_conf >= lo) & (platt_test_conf < hi)
        if mask.sum() == 0:
            continue
        platt_bins.append({
            "mean_calibrated": round(float(platt_test_conf[mask].mean()), 4),
            "accuracy": round(float(correct[mask].mean()), 4),
        })
    ece_platt = sum(
        abs(b["mean_calibrated"] - b["accuracy"]) / n_bins for b in platt_bins
    )

    # ── Plot: reliability curve + threshold scan ─────────────────────────
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.4))
    ax1.plot([0, 1], [0, 1], "k--", lw=1, label="perfect")
    ax1.plot([b["mean_confidence"] for b in bins], [b["accuracy"] for b in bins],
             "o-", color="#1f77b4", label="Chrollo (15 equal-mass bins)")
    ax1.plot([b["mean_calibrated"] for b in platt_bins], [b["accuracy"] for b in platt_bins],
             "s--", color="#d62728", ms=4, label="Platt-calibrated (reference)")
    ax1.axvline(0.85, color="#2ca02c", ls=":", lw=1.5)
    ax1.annotate("escalation\nthreshold 0.85", xy=(0.85, 0.55), fontsize=8, color="#2ca02c", ha="center")
    ax1.set_xlabel("Mean predicted confidence")
    ax1.set_ylabel("Observed accuracy")
    ax1.set_title("Reliability curve (held-out n=400)")
    ax1.legend(fontsize=8, loc="upper left")
    ax1.set_xlim(0.4, 1.02)
    ax1.set_ylim(0.4, 1.02)

    taus = [t["threshold"] for t in threshold_scan]
    ax2.plot(taus, [t["coverage"] for t in threshold_scan], "o-", color="#ff7f0e", label="coverage")
    ax2.plot(taus, [t["accuracy"] if t["accuracy"] is not None else np.nan for t in threshold_scan],
             "s-", color="#1f77b4", label="accuracy")
    ax2.axvline(0.85, color="#2ca02c", ls=":", lw=1.5)
    ax2.set_xlabel("Escalation threshold s")
    ax2.set_ylabel("Fraction of sessions")
    ax2.set_title("Coverage vs accuracy by threshold")
    ax2.legend(fontsize=8)
    fig.tight_layout()
    out_png = RESULTS_DIR / "chrollo_calibration.png"
    fig.savefig(out_png, dpi=150)
    plt.close(fig)

    # ── Manifest ──────────────────────────────────────────────────────────
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": "models/chrollo/rf_classifier.joblib",
        "heldout": {"n": len(y_test), "source": "data/training/test.jsonl"},
        "summary": {
            "accuracy": round(overall_acc, 4),
            "mean_confidence": round(mean_conf, 4),
            "confidence_minus_accuracy": round(mean_conf - overall_acc, 4),
            "ece_15bin_equal_mass": round(ece, 4),
            "mce": round(mce, 4),
            "brier_multiclass": round(brier, 4),
            "ece_platt_reference": round(ece_platt, 4),
            "platt_coefficients": {"a": round(platt_a, 4), "b": round(platt_b, 4)},
            "note": "Platt scaling fitted on training-split OOF predictions; reference only, not shipped.",
        },
        "reliability_bins": bins,
        "threshold_scan": threshold_scan,
        "per_class": per_class,
        "plot": str(out_png.relative_to(REPO_ROOT)),
    }
    out_json = RESULTS_DIR / "chrollo_calibration.json"
    out_json.write_text(json.dumps(report, indent=2))

    print(f"Accuracy={overall_acc:.4f}  mean confidence={mean_conf:.4f}  gap={mean_conf - overall_acc:+.4f}")
    print(f"ECE(15 bins, equal-mass)={ece:.4f}   MCE={mce:.4f}   Brier={brier:.4f}")
    print(f"Platt reference ECE={ece_platt:.4f}  (a={platt_a:.2f}, b={platt_b:.2f})")
    print("\nThreshold scan:")
    print("  tau   n    coverage  accuracy  wilson95          cross-tier")
    for t in threshold_scan:
        if t["n"]:
            print(f"  {t['threshold']:.2f}  {t['n']:>4}  {t['coverage']:.2f}      {t['accuracy']:.4f}    "
                  f"[{t['wilson95'][0]:.3f}, {t['wilson95'][1]:.3f}]   {t.get('cross_tier_errors', '-')}")
        else:
            print(f"  {t['threshold']:.2f}    0    0.00      -")
    print(f"\nPer-class (confidence vs accuracy):")
    for lvl, st in per_class.items():
        print(f"  {lvl:>12}: acc={st['accuracy']:.2f}  conf={st['mean_confidence']:.2f}  gap={st['mean_gap']:+.2f}")
    print(f"\nSaved: {out_json.relative_to(REPO_ROOT)} and {out_png.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
