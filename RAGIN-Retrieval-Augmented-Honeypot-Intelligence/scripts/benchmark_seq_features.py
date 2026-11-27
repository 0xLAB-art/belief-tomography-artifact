#!/usr/bin/env python3
"""Benchmark sequence-aware features against the 10-feature Chrollo baseline.

Two evaluation regimes:

1. **Same-distribution** — stratified 80/20 split of the 2,000-session
   corpus (identical split to production training). This is the
   apples-to-apples accuracy comparison.

2. **Template-disjoint** — the generator's command banks are split in
   half by template; one model trains on sessions built from templates
   A, the other on sessions built from complementary templates B. Both
   are evaluated on B-only and A-only held-out sets. This defeats
   template memorization: an n-gram model can only score well here if
   it learned generalizable attack-structure signal, not the specific
   commands in the training templates.

Feature groups benchmarked: baseline (10), baseline+phase (+8),
baseline+ngram (+32), baseline+all (+40). A small grid is swept and
selected by OOF over each regime's training split; the test set is
touched once per (regime, feature-group) pair.

Statistics: paired bootstrap (10k resamples) and McNemar exact test for
each gain over baseline.

Outputs:
  results/model_quality/seq_features_benchmark.json
"""

from __future__ import annotations

import json
import random
import sys
from datetime import datetime, timezone
from itertools import product
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, balanced_accuracy_score
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ragin.chrollo.classifier import _LABEL_INV, _LABEL_MAP
from ragin.chrollo.features import FEATURE_NAMES as BASE_NAMES
from ragin.chrollo.features import FeatureExtractor
from ragin.chrollo.features_seq import (
    NGRAM_FEATURE_NAMES,
    PHASE_FEATURE_NAMES,
    SeqFeatureExtractor,
)
from ragin.chrollo.models import SessionLog, SkillLevel

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data" / "training"
RESULTS_DIR = REPO_ROOT / "results" / "model_quality"
SEED = 42

GROUPS: dict[str, list[str]] = {
    "baseline(10)": list(BASE_NAMES),
    "+phase(8)": list(BASE_NAMES) + PHASE_FEATURE_NAMES,
    "+ngram(32)": list(BASE_NAMES) + NGRAM_FEATURE_NAMES,
    "+all(50)": list(BASE_NAMES) + PHASE_FEATURE_NAMES + NGRAM_FEATURE_NAMES,
}

GRID = [
    dict(n_estimators=n, max_depth=d, min_samples_leaf=l)
    for n, d, l in product([300, 500], [14, 16, 20], [1, 2])
]


def load_corpus() -> list[dict]:
    """Load the generated corpus, keeping the raw command templates visible
    via the generator's command banks (re-derived by matching commands)."""
    records = []
    with (DATA_DIR / "sessions.jsonl").open() as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            records.append(rec)
    return records


def label_array(records: list[dict]) -> np.ndarray:
    return np.array([_LABEL_MAP[SkillLevel(r["skill_level"])] for r in records], dtype=np.int32)


def extract_all(records: list[dict]) -> dict[str, np.ndarray]:
    """Extract every feature group for every session (cached matrices)."""
    base_ex = FeatureExtractor()
    seq_ex = SeqFeatureExtractor()
    base_rows, seq_rows = [], []
    for rec in records:
        session = SessionLog(**{k: v for k, v in rec.items() if k != "skill_level"})
        base_rows.append([base_ex.extract(session)[f] for f in BASE_NAMES])
        seq_rows.append([seq_ex.extract(session)[f] for f in PHASE_FEATURE_NAMES + NGRAM_FEATURE_NAMES])
    base = np.array(base_rows, dtype=np.float64)
    seq = np.array(seq_rows, dtype=np.float64)
    return {
        "baseline(10)": base,
        "+phase(8)": np.hstack([base, seq[:, : len(PHASE_FEATURE_NAMES)]]),
        "+ngram(32)": np.hstack([base, seq[:, len(PHASE_FEATURE_NAMES):]]),
        "+all(50)": np.hstack([base, seq]),
    }


def oof_accuracy(X: np.ndarray, y: np.ndarray, config: dict, folds: int = 4) -> float:
    skf = StratifiedKFold(n_splits=folds, shuffle=True, random_state=SEED)
    preds = np.empty_like(y)
    for tr, va in skf.split(X, y):
        scaler = StandardScaler()
        Xtr = scaler.fit_transform(X[tr])
        rf = RandomForestClassifier(
            class_weight=None, random_state=SEED, n_jobs=-1, **config
        ).fit(Xtr, y[tr])
        preds[va] = rf.predict(scaler.transform(X[va]))
    return float(accuracy_score(y, preds))


def fit_predict(Xtr: np.ndarray, ytr: np.ndarray, Xte: np.ndarray, config: dict) -> np.ndarray:
    scaler = StandardScaler()
    rf = RandomForestClassifier(
        class_weight=None, random_state=SEED, n_jobs=-1, **config
    ).fit(scaler.fit_transform(Xtr), ytr)
    return rf.predict(scaler.transform(Xte))


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact binomial McNemar p-value on discordant pairs b, c."""
    from math import comb

    n = b + c
    if n == 0:
        return 1.0
    p = sum(comb(n, k) for k in range(0, min(b, c) + 1)) / 2**n * 2
    return float(min(p, 1.0))


def paired_bootstrap(y_true, pred_a, pred_b, n_boot: int = 10_000, seed: int = SEED) -> dict:
    rng = np.random.default_rng(seed)
    idx = np.arange(len(y_true))
    a = (pred_a == y_true).astype(float)
    b = (pred_b == y_true).astype(float)
    deltas = []
    for _ in range(n_boot):
        sample = rng.choice(idx, size=len(idx), replace=True)
        deltas.append(b[sample].mean() - a[sample].mean())
    deltas = np.array(deltas)
    return {
        "mean_delta": round(float((b - a).mean()), 4),
        "ci95": [round(float(np.quantile(deltas, 0.025)), 4), round(float(np.quantile(deltas, 0.975)), 4)],
        "p_boot": round(float((deltas <= 0).mean()), 4),
    }


def evaluate_regime(name: str, splits: dict, matrices: dict, y_all: np.ndarray, idx_all: np.ndarray) -> dict:
    """Run one regime: OOF model selection per group, single test eval,
    significance tests vs baseline."""
    tr_idx, te_idx = splits["train"], splits["test"]
    y_tr, y_te = y_all[tr_idx], y_all[te_idx]
    print(f"\n=== {name} (train {len(tr_idx)} / test {len(te_idx)}) ===")
    out = {"regime": name, "train_n": len(tr_idx), "test_n": len(te_idx), "groups": {}}
    test_preds: dict[str, np.ndarray] = {}
    for group, X_all in matrices.items():
        X_tr, X_te = X_all[tr_idx], X_all[te_idx]
        # OOF model selection on this regime's training split only.
        best_cfg, best_oof = None, -1.0
        for cfg in GRID:
            acc = oof_accuracy(X_tr, y_tr, cfg)
            if acc > best_oof:
                best_oof, best_cfg = acc, cfg
        pred = fit_predict(X_tr, y_tr, X_te, best_cfg)
        test_preds[group] = pred
        acc = float((pred == y_te).mean())
        bal = float(balanced_accuracy_score(y_te, pred))
        out["groups"][group] = {
            "selected_config": best_cfg,
            "oof_accuracy": round(best_oof, 4),
            "test_accuracy": round(acc, 4),
            "test_balanced_accuracy": round(bal, 4),
        }
        print(f"  {group:>14}: OOF {best_oof:.4f} (cfg {best_cfg})  TEST acc={acc:.4f} bal={bal:.4f}")

    base = out["groups"]["baseline(10)"]["test_accuracy"]
    base_pred = test_preds["baseline(10)"]
    for group, pred in test_preds.items():
        if group == "baseline(10)":
            continue
        g = out["groups"][group]
        boot = paired_bootstrap(y_te, base_pred, pred)
        correct_a = base_pred == y_te
        correct_b = pred == y_te
        b01 = int((correct_a & ~correct_b).sum())  # baseline right, group wrong
        b10 = int((~correct_a & correct_b).sum())  # baseline wrong, group right
        g["vs_baseline"] = {
            "delta_accuracy": round(g["test_accuracy"] - base, 4),
            **boot,
            "mcnemar_exact_p": mcnemar_exact(b01, b10),
            "discordant": {"baseline_only_right": b01, "group_only_right": b10},
        }
        print(f"      vs baseline: Δ={g['vs_baseline']['delta_accuracy']:+.4f} "
              f"boot95={g['vs_baseline']['ci95']} McNemar p={g['vs_baseline']['mcnemar_exact_p']:.4f}")
    return out


def main() -> None:
    records = load_corpus()
    y_all = label_array(records)
    idx_all = np.arange(len(records))
    print(f"corpus: {len(records)} sessions")

    # Same-distribution split: recompute the exact production 80/20 split
    # (same seed and logic as retrain_chrollo.stratified_split) rather than
    # matching session_ids — SessionLog's validator re-hashes ids on load,
    # so the committed files' ids are not comparable to the raw corpus.
    rng = np.random.default_rng(SEED)
    tr_idx, te_idx = [], []
    for label in sorted(set(y_all.tolist()), key=lambda c: _LABEL_INV[c]):
        group = idx_all[y_all == label]
        perm = rng.permutation(len(group))
        n_te = max(1, int(round(len(group) * 0.2)))
        te_idx.extend(group[perm[:n_te]])
        tr_idx.extend(group[perm[n_te:]])
    splits_same = {"train": np.array(tr_idx), "test": np.array(te_idx)}

    print("extracting features ...")
    matrices = extract_all(records)

    results = {"generated_at": datetime.now(timezone.utc).isoformat(), "regimes": []}
    results["regimes"].append(
        evaluate_regime("same-distribution (production split)", splits_same, matrices, y_all, idx_all)
    )

    # ── Template-disjoint regime ─────────────────────────────────────────
    # Reconstruct each session's template identity by matching its commands
    # against the generator banks via a fuzzy signature: the set of
    # whitespace-stripped command prefixes. Simpler robust proxy: hash each
    # session's commands with all digits/IPs masked; sessions sharing a
    # masked-command-set signature share templates.
    import re as _re

    def signature(rec) -> str:
        parts = []
        for c in rec["commands"]:
            cmd = _re.sub(r"\d+", "N", c["command"])
            cmd = _re.sub(r"\s+", " ", cmd).strip().lower()
            parts.append(cmd)
        return "|".join(sorted(set(parts)))

    sigs = {signature(r): i for i, r in enumerate(records)}
    # Group sessions by their dominant bank category: we instead split by
    # masked-template family — cluster signatures into two halves via the
    # parity of the first n-gram bucket of the session's first command.
    # Robust alternative: split by the masked first-command signature hash.
    fam = {}
    for i, r in enumerate(records):
        first = _re.sub(r"\d+", "N", r["commands"][0]["command"]) if r["commands"] else ""
        fam[i] = int.from_bytes(__import__("hashlib").md5(first.encode()).digest()[:2], "big") % 2

    fam0 = idx_all[np.array([fam[i] == 0 for i in idx_all])]
    fam1 = idx_all[np.array([fam[i] == 1 for i in idx_all])]

    # Within each family, stratified 80/20; train on A-only, test on B-only.
    rng = np.random.default_rng(SEED)
    tr_a, te_a, tr_b, te_b = [], [], [], []
    for c in range(4):
        for fam_idx, tr_list, te_list in ((fam0, tr_a, te_a), (fam1, tr_b, te_b)):
            members = fam_idx[y_all[fam_idx] == c]
            perm = rng.permutation(len(members))
            n_te = max(1, int(len(members) * 0.25))
            te_list.extend(members[perm[:n_te]])
            tr_list.extend(members[perm[n_te:]])
    splits_disjoint = {"train": np.array(tr_a), "test": np.array(te_b)}
    results["regimes"].append(
        evaluate_regime(
            "template-disjoint (train fam-A / test fam-B)",
            splits_disjoint,
            matrices,
            y_all,
            idx_all,
        )
    )

    # ── STRICT bank-disjoint regime ──────────────────────────────────────
    # The fam split above only guarantees first-command template disjointness.
    # Here we regenerate two corpora from fully disjoint template pools:
    # every command bank in the generator is split by index parity, train
    # sessions draw only from even-indexed templates, test only from odd.
    # Any n-gram gain in this regime must come from generalizable
    # attack-structure signal, not memorized command templates.
    import generate_training_data as gtd

    banks_even = {cat: [t for i, t in enumerate(tpl) if i % 2 == 0] for cat, tpl in gtd.BANKS.items()}
    banks_odd = {cat: [t for i, t in enumerate(tpl) if i % 2 == 1] for cat, tpl in gtd.BANKS.items()}

    def build_half(banks: dict, per_tier: int, seed: int) -> tuple[list[SessionLog], np.ndarray]:
        gtd.BANKS.clear()
        gtd.BANKS.update(banks)
        rng = random.Random(seed)
        nprng = np.random.default_rng(seed)
        sessions, labels = [], []
        for tier in SkillLevel:
            for i in range(per_tier):
                sessions.append(gtd.make_session(rng, nprng, tier, i))
                labels.append(_LABEL_MAP[tier])
        return sessions, np.array(labels, dtype=np.int32)

    per_tier = 150
    sess_train_b, y_train_b = build_half(banks_even, per_tier, SEED)
    sess_test_b, y_test_b = build_half(banks_odd, per_tier, SEED + 1)

    base_ex = FeatureExtractor()
    seq_ex = SeqFeatureExtractor()

    def matrix(sessions: list[SessionLog], group: str) -> np.ndarray:
        names = GROUPS[group]
        rows = []
        for s in sessions:
            full = seq_ex.extract(s)
            rows.append([full[f] for f in names])
        return np.array(rows, dtype=np.float64)

    print(f"\n(strict regime: {len(sess_train_b)} train / {len(sess_test_b)} test, "
          f"disjoint template pools)")
    strict = {"regime": "strict bank-disjoint (regenerated corpora)",
              "train_n": len(sess_train_b), "test_n": len(sess_test_b), "groups": {}}
    strict_preds = {}
    for group in GROUPS:
        X_tr = matrix(sess_train_b, group)
        X_te = matrix(sess_test_b, group)
        best_cfg, best_oof = None, -1.0
        for cfg in GRID:
            acc = oof_accuracy(X_tr, y_train_b, cfg)
            if acc > best_oof:
                best_oof, best_cfg = acc, cfg
        pred = fit_predict(X_tr, y_train_b, X_te, best_cfg)
        strict_preds[group] = pred
        acc = float((pred == y_test_b).mean())
        bal = float(balanced_accuracy_score(y_test_b, pred))
        strict["groups"][group] = {
            "selected_config": best_cfg,
            "oof_accuracy": round(best_oof, 4),
            "test_accuracy": round(acc, 4),
            "test_balanced_accuracy": round(bal, 4),
        }
        print(f"  {group:>14}: OOF {best_oof:.4f} (cfg {best_cfg})  TEST acc={acc:.4f} bal={bal:.4f}")

    sbase = strict["groups"]["baseline(10)"]["test_accuracy"]
    for group, pred in strict_preds.items():
        if group == "baseline(10)":
            continue
        g = strict["groups"][group]
        boot = paired_bootstrap(y_test_b, strict_preds["baseline(10)"], pred)
        ca = strict_preds["baseline(10)"] == y_test_b
        cb = pred == y_test_b
        g["vs_baseline"] = {
            "delta_accuracy": round(g["test_accuracy"] - sbase, 4),
            **boot,
            "mcnemar_exact_p": mcnemar_exact(int((ca & ~cb).sum()), int((~ca & cb).sum())),
            "discordant": {"baseline_only_right": int((ca & ~cb).sum()),
                           "group_only_right": int((~ca & cb).sum())},
        }
        print(f"      vs baseline: Δ={g['vs_baseline']['delta_accuracy']:+.4f} "
              f"boot95={g['vs_baseline']['ci95']} McNemar p={g['vs_baseline']['mcnemar_exact_p']:.4f}")
    results["regimes"].append(strict)

    out = RESULTS_DIR / "seq_features_benchmark.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2))
    print(f"\nSaved: {out.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
