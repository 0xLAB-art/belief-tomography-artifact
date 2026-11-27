#!/usr/bin/env python3
"""Retrain Chrollo on the baseline+ngram feature set.

Uses the *existing* production split (data/training/train.jsonl +
data/training/test.jsonl, identical to the 0.8875-accuracy baseline run)
so the comparison is apples-to-apples. Backs up the current model before
overwriting, persists a features.joblib sidecar, and writes an updated
training manifest with per-tier recall.

Output: models/chrollo/rf_classifier.joblib (+ .scaler/.features sidecars)
        models/chrollo/training_manifest.json (feature_set: baseline+ngram)
"""

from __future__ import annotations

import json
import shutil
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ragin.chrollo.classifier import _LABEL_INV, _LABEL_MAP, ChrolloClassifier
from ragin.chrollo.models import SessionLog, SkillLevel

REPO_ROOT = Path(__file__).resolve().parent.parent
MODEL_DIR = REPO_ROOT / "models" / "chrollo"
DATA_DIR = REPO_ROOT / "data" / "training"


def load(path: Path) -> list[tuple[SessionLog, SkillLevel]]:
    samples = []
    with path.open() as fh:
        for line in fh:
            if line.strip():
                rec = json.loads(line)
                label = SkillLevel(rec.pop("skill_level"))
                samples.append((SessionLog(**rec), label))
    return samples


def main() -> None:
    t0 = time.time()
    train = load(DATA_DIR / "train.jsonl")
    test = load(DATA_DIR / "test.jsonl")
    print(f"train={len(train)} test={len(test)}")
    print(f"  train class counts: {dict(sorted(Counter(lb.value for _, lb in train).items()))}")

    model_path = MODEL_DIR / "rf_classifier.joblib"
    backup = MODEL_DIR / "rf_classifier_pre_ngram.joblib"
    if model_path.exists() and not backup.exists():
        shutil.copy2(model_path, backup)
        if backup.with_suffix(".scaler.joblib").exists():
            shutil.copy2(model_path.with_suffix(".scaler.joblib"), backup.with_suffix(".scaler.joblib"))
        print(f"Backed up baseline model -> {backup.name}")

    clf = ChrolloClassifier(model_path=model_path, feature_set="baseline+ngram")

    # Small grid mirroring scripts/benchmark_seq_features.py: selection by CV
    # on the training split only; held-out is touched once at the end.
    grid = [
        dict(n_estimators=500, max_depth=16, min_samples_leaf=1),
        dict(n_estimators=500, max_depth=16, min_samples_leaf=2),
        dict(n_estimators=500, max_depth=20, min_samples_leaf=1),
        dict(n_estimators=300, max_depth=16, min_samples_leaf=2),
    ]
    best_metrics, best_cfg = None, None
    for cfg in grid:
        m = clf.train(train, cv_folds=5, class_weight=None, **cfg)
        print(f"  cfg={cfg} -> CV {m['accuracy']:.4f} ± {m['accuracy_std']:.4f}")
        if best_metrics is None or m["accuracy"] > best_metrics["accuracy"]:
            best_metrics, best_cfg = m, cfg
    print(f"Best config: {best_cfg}")
    # Final fit with the selected config (train() re-saves the artifact).
    metrics = clf.train(train, cv_folds=5, class_weight=None, **best_cfg)
    print(f"CV accuracy: {metrics['accuracy']:.4f} ± {metrics['accuracy_std']:.4f}")

    y_true = np.array([_LABEL_MAP[label] for _, label in test])
    y_pred = np.array([_LABEL_MAP[clf.classify(s).skill_level] for s, _ in test])
    acc = float((y_true == y_pred).mean())
    print(f"Held-out accuracy (n={len(test)}): {acc:.4f}  [baseline was 0.8875]")

    per_class = {}
    for lvl in SkillLevel:
        mask = y_true == _LABEL_MAP[lvl]
        correct = int((y_pred[mask] == y_true[mask]).sum())
        per_class[lvl.value] = round(correct / int(mask.sum()), 4) if mask.sum() else None
    print(f"Per-tier recall: {per_class}")

    # Confusion matrix (adjacent-tier drift check)
    tiers = ["novice", "intermediate", "expert", "apt"]
    cm = {t: {p: 0 for p in tiers} for t in tiers}
    for t, p in zip(y_true, y_pred, strict=True):
        cm[_LABEL_INV[int(t)]][_LABEL_INV[int(p)]] += 1
    print("Confusion (rows=true):")
    for t in tiers:
        print(f"  {t:14s} {cm[t]}")

    manifest = {
        "retrained_at": datetime.now(timezone.utc).isoformat(),
        "feature_set": "baseline+ngram",
        "n_features": len(clf._feature_names),
        "dataset": {
            "source": "data/training/sessions.jsonl",
            "total": len(train) + len(test),
            "class_counts": dict(sorted(Counter(lb.value for _, lb in train + test).items())),
        },
        "split": {"train": len(train), "test": len(test), "seed": 42},
        "hyperparameters": {
            **best_cfg,
            "class_weight": None,
            "random_state": 42,
            "selected_by": "5-fold CV on train split (grid mirroring "
            "scripts/benchmark_seq_features.py)",
        },
        "metrics": {
            "heldout_accuracy": round(acc, 4),
            "cv_accuracy": round(metrics["accuracy"], 4),
            "cv_std": round(metrics["accuracy_std"], 4),
            "per_tier_recall": per_class,
            "confusion_matrix": cm,
        },
        "benchmark_evidence": (
            "results/model_quality/seq_features_benchmark.json — baseline+ngram "
            "was the only feature family improving all three regimes "
            "(+6.0pp same-distribution p=1.2e-7; +3.9pp template-disjoint; "
            "+3.7pp strict bank-disjoint), while +phase/+all degraded the "
            "strict regime (overfit)."
        ),
        "notes": (
            "Supersedes the 10-feature baseline artifact. Adjacent-tier "
            "confusion remains expected; severity underestimation is further "
            "mitigated at the routing layer by the Supervisor behavior floor."
        ),
    }
    (MODEL_DIR / "training_manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"Done in {time.time() - t0:.0f}s — manifest updated.")


if __name__ == "__main__":
    main()
