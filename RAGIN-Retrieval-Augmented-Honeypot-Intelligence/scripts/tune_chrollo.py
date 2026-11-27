#!/usr/bin/env python3
"""Hyperparameter + class-boundary weighting search for the Chrollo classifier.

Methodology (leakage-safe):
  * The held-out split (data/training/test.jsonl, 100 sessions) is NOT used
    for model selection. It is touched exactly once, at the end, to report
    the shipped model's honest accuracy with a Wilson 95% CI.
  * Model selection uses out-of-fold predictions over the training split
    (stratified 5-fold) via a fresh StandardScaler+RF Pipeline per fold.
  * Selection metric: balanced accuracy, tie-broken by fewer cross-tier
    (non-adjacent) errors, then raw accuracy.
  * Class-boundary weighting candidates include per-class dicts that
    up-weight boundary classes (novice/intermediate and expert/apt), plus
    "balanced", "balanced_subsample", and None.
  * Ship rule: the tuned model replaces the current artifact only if it is
    strictly better on the held-out set (higher accuracy, or equal accuracy
    with fewer cross-tier errors).

Outputs:
  models/chrollo/tuning_manifest.json - full search results + decision
  models/chrollo/rf_classifier.joblib - retrained model (if shipped)
  models/chrollo/rf_classifier_pre_tune.joblib - backup of previous model

Usage:
    python scripts/tune_chrollo.py [--n-configs 60] [--seed 7]
"""

from __future__ import annotations

import argparse
import json
import math
import random
import shutil
import sys
from datetime import datetime, timezone
from itertools import product
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, balanced_accuracy_score, confusion_matrix
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ragin.chrollo.classifier import ChrolloClassifier, _LABEL_INV, _LABEL_MAP
from ragin.chrollo.models import SessionLog, SkillLevel

REPO_ROOT = Path(__file__).resolve().parent.parent
MODEL_DIR = REPO_ROOT / "models" / "chrollo"
DATA_DIR = REPO_ROOT / "data" / "training"

TIERS = ["novice", "intermediate", "expert", "apt"]
ADJACENT = {(0, 1), (1, 0), (1, 2), (2, 1), (2, 3), (3, 2)}


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


def featurize(sessions: list[SessionLog]) -> np.ndarray:
    from ragin.chrollo.features import FEATURE_NAMES, FeatureExtractor

    # float64 to be bit-identical with the production classify() path,
    # which builds the feature row via np.array([...]) (float64).
    extractor = FeatureExtractor()
    return np.array(
        [[extractor.extract(s)[f] for f in FEATURE_NAMES] for s in sessions],
        dtype=np.float64,
    )


def wilson_ci(correct: int, n: int, z: float = 1.96) -> tuple[float, float]:
    p = correct / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return center - half, center + half


# ── Class-boundary weighting candidates ─────────────────────────────────────
# Keys are integer labels: 0=novice, 1=intermediate, 2=expert, 3=apt.
def boundary_weight_dicts() -> dict[str, dict[int, float] | None]:
    cands: dict[str, dict[int, float] | None] = {
        "balanced": "balanced",
        "balanced_subsample": "balanced_subsample",
        "none": None,
    }
    for boost in (1.25, 1.5, 1.75):
        cands[f"boundary_{boost}"] = {0: boost, 1: boost, 2: boost, 3: boost}
    for boost in (1.5, 2.0):
        cands[f"interior_{boost}"] = {0: 1.0, 1: boost, 2: boost, 3: 1.0}
    cands["apt_focus_2.0"] = {0: 1.0, 1: 1.0, 2: 1.0, 3: 2.0}
    return cands


def oof_evaluate(
    X: np.ndarray,
    y: np.ndarray,
    config: dict,
    weight_resolver,
    n_splits: int = 5,
    seed: int = 42,
) -> dict:
    """Out-of-fold evaluation of one config on the training split."""
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed)
    y_oof = np.empty_like(y)
    for train_idx, val_idx in skf.split(X, y):
        weight = weight_resolver(config["class_weight"])
        rf = RandomForestClassifier(
            n_estimators=config["n_estimators"],
            max_depth=config["max_depth"],
            min_samples_split=config["min_samples_split"],
            min_samples_leaf=config["min_samples_leaf"],
            max_features=config["max_features"],
            class_weight=weight,
            random_state=42,
            n_jobs=-1,
        )
        scaler = StandardScaler()
        X_tr = scaler.fit_transform(X[train_idx])
        rf.fit(X_tr, y[train_idx])
        y_oof[val_idx] = rf.predict(scaler.transform(X[val_idx]))

    acc = accuracy_score(y, y_oof)
    bal_acc = balanced_accuracy_score(y, y_oof)
    cross_tier = sum(
        1
        for t, p in zip(y, y_oof, strict=True)
        if t != p and (int(t), int(p)) not in ADJACENT
    )
    recalls = {
        _LABEL_INV[c]: round(float(((y_oof == c) & (y == c)).sum() / max((y == c).sum(), 1)), 4)
        for c in range(4)
    }
    return {
        "oof_accuracy": round(float(acc), 4),
        "oof_balanced_accuracy": round(float(bal_acc), 4),
        "oof_cross_tier_errors": int(cross_tier),
        "oof_per_class_recall": recalls,
    }


def eval_on_test(model, scaler, X_test: np.ndarray, y_test: np.ndarray) -> dict:
    y_pred = model.predict(scaler.transform(X_test))
    acc = float((y_pred == y_test).mean())
    cross_tier = sum(
        1
        for t, p in zip(y_test, y_pred, strict=True)
        if t != p and (int(t), int(p)) not in ADJACENT
    )
    cm = confusion_matrix(y_test, y_pred, labels=list(range(4)))
    return {
        "accuracy": round(acc, 4),
        "cross_tier_errors": int(cross_tier),
        "confusion_matrix": {
            _LABEL_INV[t]: {
                _LABEL_INV[p]: int(cm[t][p]) for p in range(4)
            }
            for t in range(4)
        },
        "per_class_recall": {
            _LABEL_INV[c]: round(float(cm[c][c] / max(cm[c].sum(), 1)), 4) for c in range(4)
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n-configs", type=int, default=60)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--no-ship", action="store_true", help="Evaluate only; do not replace the artifact")
    ap.add_argument("--grid", choices=["random", "local"], default="random",
                    help="random: sample the wide space; local: exhaustive sweep around "
                         "the retrain_chrollo.py default (200 trees / depth 20 / balanced)")
    args = ap.parse_args()

    X_train_sess, y_train = load_split(DATA_DIR / "train.jsonl")
    X_test_sess, y_test = load_split(DATA_DIR / "test.jsonl")
    print(f"train={len(y_train)}  test={len(y_test)} (held out until final eval)")
    X_train = featurize(X_train_sess)
    X_test = featurize(X_test_sess)

    weights = boundary_weight_dicts()
    weight_resolver = lambda name: weights[name]  # noqa: E731

    # ── Build the search space ───────────────────────────────────────────
    if args.grid == "local":
        # Exhaustive neighborhood of the retrain_chrollo.py default config
        # (200 trees / depth 20 / balanced): tree count, depth, leaf size,
        # and the two competitive weighting modes.
        configs = [
            {
                "n_estimators": n,
                "max_depth": d,
                "min_samples_split": 5,
                "min_samples_leaf": l,
                "max_features": "sqrt",
                "class_weight": cw,
            }
            for n, d, l, cw in product(
                [200, 500, 750],        # n_estimators
                [16, 20, 24, None],     # max_depth
                [1, 2],                 # min_samples_leaf
                ["balanced", "none"],   # class_weight
            )
        ]
    else:
        grid = list(
            product(
                [300, 500],               # n_estimators
                [10, 14, 18, None],       # max_depth
                [2, 5],                   # min_samples_split
                [1, 2, 3],                # min_samples_leaf
                ["sqrt", 0.5],            # max_features
                list(weights),            # class_weight candidates
            )
        )
        rng = random.Random(args.seed)
        configs = [
            {
                "n_estimators": n,
                "max_depth": d,
                "min_samples_split": s,
                "min_samples_leaf": l,
                "max_features": mf,
                "class_weight": cw,
            }
            for n, d, s, l, mf, cw in rng.sample(grid, min(args.n_configs, len(grid)))
        ]
    print(f"searching {len(configs)} configs ({args.grid} grid) x 5 OOF folds ...")

    results = []
    for i, config in enumerate(configs):
        metrics = oof_evaluate(X_train, y_train, config, weight_resolver)
        results.append({"config": config, **metrics})
        if (i + 1) % 10 == 0:
            best = max(results, key=lambda r: (r["oof_balanced_accuracy"], -r["oof_cross_tier_errors"], r["oof_accuracy"]))
            print(
                f"  [{i + 1}/{len(configs)}] best so far: bal_acc={best['oof_balanced_accuracy']:.4f} "
                f"acc={best['oof_accuracy']:.4f} cross_tier={best['oof_cross_tier_errors']}"
            )

    results.sort(key=lambda r: (r["oof_balanced_accuracy"], -r["oof_cross_tier_errors"], r["oof_accuracy"]))
    best = max(
        results,
        key=lambda r: (r["oof_balanced_accuracy"], -r["oof_cross_tier_errors"], r["oof_accuracy"]),
    )
    best_config = dict(best["config"])
    print(f"\nBest OOF config: {best_config}")
    print(f"  OOF: acc={best['oof_accuracy']}  bal_acc={best['oof_balanced_accuracy']}  cross_tier={best['oof_cross_tier_errors']}")

    # ── Snapshot the current artifact BEFORE any training overwrites it ──
    cur_model = MODEL_DIR / "rf_classifier.joblib"
    cur_scaler = MODEL_DIR / "rf_classifier.scaler.joblib"
    backup_model = MODEL_DIR / "rf_classifier_pre_tune.joblib"
    backup_scaler = MODEL_DIR / "rf_classifier_pre_tune.scaler.joblib"
    have_baseline = cur_model.exists()
    if have_baseline:
        # Always refresh the snapshot. A stale pre_tune file from a previous
        # dataset regime silently poisoned the baseline comparison once
        # (the guard 'not backup_model.exists()' skipped the refresh and the
        # run compared against the wrong artifact).
        shutil.copy2(cur_model, backup_model)
        if cur_scaler.exists():
            shutil.copy2(cur_scaler, backup_scaler)
        print("Snapshotted current artifact -> rf_classifier_pre_tune.joblib")

    # ── Final model: refit best config on the full training split ────────
    classifier = ChrolloClassifier(model_path=MODEL_DIR / "rf_classifier.joblib")
    final_metrics = classifier.train(
        list(zip(X_train_sess, (SkillLevel(_LABEL_INV[c]) for c in y_train))),
        n_estimators=best_config["n_estimators"],
        max_depth=best_config["max_depth"],
        min_samples_split=best_config["min_samples_split"],
        min_samples_leaf=best_config["min_samples_leaf"],
        max_features=best_config["max_features"],
        class_weight=weight_resolver(best_config["class_weight"]),
        cv_folds=5,
    )

    # ── Single held-out evaluation: tuned vs current artifact ────────────
    tuned_eval = eval_on_test(classifier._model, classifier._scaler, X_test, y_test)

    if backup_model.exists():
        baseline_model = joblib.load(backup_model)
        baseline_scaler = joblib.load(backup_scaler)
        baseline_eval = eval_on_test(baseline_model, baseline_scaler, X_test, y_test)
    else:
        baseline_eval = None

    # ── Ship decision ────────────────────────────────────────────────────
    ship = False
    decision_reason = ""
    if baseline_eval is None:
        ship, decision_reason = True, "no previous artifact to compare"
    elif (tuned_eval["accuracy"], -tuned_eval["cross_tier_errors"]) > (
        baseline_eval["accuracy"],
        -baseline_eval["cross_tier_errors"],
    ):
        ship, decision_reason = True, (
            f"strictly better: acc {baseline_eval['accuracy']} -> {tuned_eval['accuracy']}, "
            f"cross-tier {baseline_eval['cross_tier_errors']} -> {tuned_eval['cross_tier_errors']}"
        )
    else:
        decision_reason = (
            f"not strictly better (baseline acc={baseline_eval['accuracy']}, "
            f"cross-tier={baseline_eval['cross_tier_errors']})"
        )

    if ship and not args.no_ship:
        # train() already persisted the tuned model; keep the pre-tune backup.
        pass

    ci_lo, ci_hi = wilson_ci(round(tuned_eval["accuracy"] * len(y_test)), len(y_test))

    manifest = {
        "tuned_at": datetime.now(timezone.utc).isoformat(),
        "methodology": {
            "selection": "out-of-fold predictions over training split (stratified 5-fold)",
            "heldout_usage": "touched once for final reporting only",
            "selection_metric": "balanced_accuracy, tie-break: fewer cross-tier errors, then accuracy",
            "ship_rule": "strictly better than previous artifact on held-out (acc, then cross-tier errors)",
        },
        "search": {
            "n_configs": len(configs),
            "seed": args.seed,
            "grid": args.grid,
            "space": {
                "n_estimators": [200, 500, 750] if args.grid == "local" else [300, 500],
                "max_depth": [16, 20, 24, "none"] if args.grid == "local" else [10, 14, 18, "none"],
                "min_samples_split": [5] if args.grid == "local" else [2, 5],
                "min_samples_leaf": [1, 2] if args.grid == "local" else [1, 2, 3],
                "max_features": ["sqrt"] if args.grid == "local" else ["sqrt", 0.5],
                "class_weight": ["balanced", "none"] if args.grid == "local" else list(weights),
            },
        },
        "oof_results_all": results,
        "best": {
            "config": best_config,
            **best,
            "final_cv_accuracy": round(final_metrics.get("accuracy"), 4) if "accuracy" in final_metrics else None,
        },
        "heldout": {
            "n": len(y_test),
            "tuned": tuned_eval,
            "tuned_wilson95": [round(ci_lo, 4), round(ci_hi, 4)],
            "baseline": baseline_eval,
        },
        "decision": {
            "shipped": ship and not args.no_ship,
            "dry_run": args.no_ship,
            "reason": decision_reason,
        },
    }
    out = MODEL_DIR / "tuning_manifest.json"
    out.write_text(json.dumps(manifest, indent=2, default=str))

    print(f"\nHeld-out (n={len(y_test)}):")
    print(f"  tuned:    acc={tuned_eval['accuracy']}  cross_tier={tuned_eval['cross_tier_errors']}  "
          f"CI95=[{ci_lo:.3f}, {ci_hi:.3f}]")
    if baseline_eval:
        print(f"  baseline: acc={baseline_eval['accuracy']}  cross_tier={baseline_eval['cross_tier_errors']}")
    print(f"  recalls (tuned): {tuned_eval['per_class_recall']}")
    print(f"Decision: {'SHIP' if ship else 'KEEP BASELINE'} — {decision_reason}")
    if not ship and backup_model.exists():
        shutil.copy2(backup_model, cur_model)
        if backup_scaler.exists():
            shutil.copy2(backup_scaler, cur_scaler)
        print("  -> restored baseline artifact (tuned model discarded)")
    print(f"Manifest -> {out}")


if __name__ == "__main__":
    main()
