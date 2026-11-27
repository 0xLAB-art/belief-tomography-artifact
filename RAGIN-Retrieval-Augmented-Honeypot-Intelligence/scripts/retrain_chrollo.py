#!/usr/bin/env python3
"""Retrain the Chrollo classifier on the multi-class dataset.

Loads data/training/sessions.jsonl, performs a stratified 80/20 split,
trains via ChrolloClassifier.train() (200 trees), evaluates on the
held-out 20%, and saves:

* the retrained model + scaler (models/chrollo/, existing single-class
  model backed up first),
* models/chrollo/training_manifest.json with real held-out metrics,
  confusion matrix, and dataset digest,
* data/training/{train,test}.jsonl splits for reproducibility.

Usage:
    python scripts/retrain_chrollo.py [--seed 42] [--data data/training/sessions.jsonl]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ragin.chrollo.classifier import ChrolloClassifier, _LABEL_MAP, _LABEL_INV
from ragin.chrollo.models import SessionLog, SkillLevel

REPO_ROOT = Path(__file__).resolve().parent.parent
MODEL_DIR = REPO_ROOT / "models" / "chrollo"
DATA_DIR = REPO_ROOT / "data" / "training"


def load_dataset(path: Path) -> tuple[list[tuple[SessionLog, SkillLevel]], str]:
    samples: list[tuple[SessionLog, SkillLevel]] = []
    records: list[str] = []
    with path.open() as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            label = SkillLevel(record.pop("skill_level"))
            session = SessionLog(**record)
            samples.append((session, label))
            records.append(line)
    digest = hashlib.sha256("\n".join(records).encode()).hexdigest()[:16]
    return samples, digest


def stratified_split(
    samples: list[tuple[SessionLog, SkillLevel]], test_frac: float, rng: np.random.Generator
) -> tuple[list, list]:
    by_class: dict[SkillLevel, list] = {}
    for sample in samples:
        by_class.setdefault(sample[1], []).append(sample)

    train, test = [], []
    for label, group in sorted(by_class.items(), key=lambda kv: kv[0].value):
        idx = rng.permutation(len(group))
        n_test = max(1, int(round(len(group) * test_frac)))
        test.extend(group[i] for i in idx[:n_test])
        train.extend(group[i] for i in idx[n_test:])
    return train, test


def confusion(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, dict[str, int]]:
    labels = sorted(_LABEL_MAP.values())
    matrix = { _LABEL_INV[t]: {_LABEL_INV[p]: 0 for p in labels} for t in labels }
    for t, p in zip(y_true, y_pred, strict=True):
        matrix[_LABEL_INV[int(t)]][_LABEL_INV[int(p)]] += 1
    return matrix


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--data", type=Path, default=DATA_DIR / "sessions.jsonl")
    ap.add_argument("--test-frac", type=float, default=0.2)
    ap.add_argument("--skip-cv", action="store_true", help="Skip cross-validation (fast smoke retrain)")
    args = ap.parse_args()

    if not args.data.exists():
        sys.exit(f"Dataset not found: {args.data}. Run scripts/generate_training_data.py first.")

    samples, digest = load_dataset(args.data)
    counts = Counter(label.value for _, label in samples)
    print(f"Loaded {len(samples)} sessions from {args.data} (digest {digest})")
    print(f"  class counts: {dict(sorted(counts.items()))}")

    rng = np.random.default_rng(args.seed)
    train, test = stratified_split(samples, args.test_frac, rng)
    print(f"  split: {len(train)} train / {len(test)} test")

    # Persist splits for reproducibility.
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for name, split in (("train.jsonl", train), ("test.jsonl", test)):
        with (DATA_DIR / name).open("w") as fh:
            for session, label in split:
                fh.write(json.dumps({**session.model_dump(mode="json"), "skill_level": label.value}) + "\n")

    classifier = ChrolloClassifier(model_path=MODEL_DIR / "rf_classifier.joblib")
    cv_folds = 0 if args.skip_cv else 5
    metrics = classifier.train(train, cv_folds=cv_folds if cv_folds else 1)
    if args.skip_cv:
        metrics.pop("accuracy", None)
        metrics.pop("accuracy_std", None)

    # Held-out evaluation.
    y_true = np.array([_LABEL_MAP[label] for _, label in test])
    y_pred = np.array([_LABEL_MAP[classifier.classify(s).skill_level] for s, _ in test])
    accuracy = float((y_true == y_pred).mean())

    per_class = {}
    for lvl in SkillLevel:
        mask = y_true == _LABEL_MAP[lvl]
        correct = int((y_pred[mask] == y_true[mask]).sum())
        per_class[lvl.value] = {
            "recall": round(correct / int(mask.sum()), 4) if mask.sum() else None,
            "support": int(mask.sum()),
        }

    cm = confusion(y_true, y_pred)

    # Backup existing model before overwrite.
    model_path = MODEL_DIR / "rf_classifier.joblib"
    if model_path.exists():
        backup = MODEL_DIR / "rf_classifier_single_class_backup.joblib"
        if not backup.exists():
            shutil.copy2(model_path, backup)
            print(f"Backed up previous model -> {backup.name}")

    classifier._save()  # persist retrained model + scaler

    manifest = {
        "retrained_at": datetime.now(timezone.utc).isoformat(),
        "dataset": {
            "source": str(args.data.relative_to(REPO_ROOT)),
            "sha256_16": digest,
            "total": len(samples),
            "class_counts": dict(sorted(counts.items())),
        },
        "split": {"train": len(train), "test": len(test), "test_frac": args.test_frac, "seed": args.seed},
        "hyperparameters": {
            "n_estimators": 200,
            "max_depth": 20,
            "min_samples_split": 5,
            "class_weight": "balanced",
            "random_state": 42,
        },
        "metrics": {
            "heldout_accuracy": round(accuracy, 4),
            "per_class_recall": per_class,
            "confusion_matrix": cm,
            "cv_accuracy": round(metrics.get("accuracy"), 4) if "accuracy" in metrics else None,
            "cv_std": round(metrics.get("accuracy_std"), 4) if "accuracy_std" in metrics else None,
        },
        "features": classifier.get_feature_importance(),
        "notes": (
            "Synthetic persona/mitre-grounded dataset (scripts/generate_training_data.py). "
            "Metrics are computed on a held-out stratified 20% split. Boundary confusion "
            "between adjacent tiers (novice<->intermediate, expert<->apt) is expected and "
            "honest. Supersedes the single-class artifact shipped earlier."
        ),
    }
    out = MODEL_DIR / "training_manifest.json"
    out.write_text(json.dumps(manifest, indent=2))

    print(f"\nHeld-out accuracy: {accuracy:.4f}  ({len(test)} sessions)")
    for lvl, stats in per_class.items():
        print(f"  {lvl:>12}: recall={stats['recall']}")
    print(f"Confusion matrix (rows=true, cols=pred): {json.dumps(cm)}")
    print(f"Manifest -> {out}")


if __name__ == "__main__":
    main()
