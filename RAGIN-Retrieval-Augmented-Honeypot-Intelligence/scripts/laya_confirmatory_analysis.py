"""Confirmatory analysis pipeline for the Laya-vs-Chrollo independent evaluation.

This tool refuses to run its confirmatory analysis unless genuine rater label
files exist under results/laya_research/rater_labels/. Synthetic/fixture labels
used by tests must NEVER be written to that directory.

Usage:

  .venv/bin/python scripts/laya_confirmatory_analysis.py [--dry-run]

  (no real labels present)  -> prints "REFUSING:" and exits 2
  (labels present)          -> prints/ writes results/laya_research/confirmatory_analysis.json
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results" / "laya_research"
LABELS_DIR = RESULTS / "rater_labels"
MANIFEST = RESULTS / "confirmatory_subset_manifest.json"
FROZEN = RESULTS / "confirmatory_frozen_predictions.jsonl"
OUT = RESULTS / "confirmatory_analysis.json"

TAXONOMY = [
    "BENIGN", "RECON", "SUSPICIOUS", "EXPLOITATION", "PRIVILEGE_ESCALATION",
    "DATA_ACCESS", "PERSISTENCE", "OTHER_ATTACK", "UNCERTAIN",
]
NEGATIVE = {"BENIGN"}
EXCLUDED = {"UNCERTAIN"}
POSITIVE = set(TAXONOMY) - NEGATIVE - EXCLUDED


class LabelsMissing(RuntimeError):
    """Raised when genuine rater labels are absent."""


def load_case_ids() -> list[str]:
    txt = (RESULTS / "confirmatory_case_ids.txt").read_text()
    return [ln.strip() for ln in txt.splitlines() if ln.strip()]


def load_frozen_predictions() -> dict[str, dict]:
    out = {}
    if not FROZEN.exists():
        return out
    for line in FROZEN.read_text().splitlines():
        if line.strip():
            rec = json.loads(line)
            out[rec["case_id"]] = rec
    return out


def load_rater_labels(raters=("r1", "r2", "r3")) -> dict[str, dict[str, str]]:
    """Load genuine rater label files; refuse non-human or non-conforming files.

    Accepts ONLY the schema written by scripts/laya_blind_annotation_workflow.py
    (``rater_id`` + ``labels`` rows + ``completed_at``). Files using an ad-hoc
    schema (e.g. an ``items`` list emitted programmatically by AI-rater tooling)
    are refused, as are files sharing one identical ``completed_at`` timestamp
    across supposedly independent raters.
    """
    loaded: dict[str, dict[str, str]] = {}
    completed_at: dict[str, str] = {}
    for rater in raters:
        path = LABELS_DIR / f"{rater}.json"
        if not path.exists():
            raise LabelsMissing(f"missing rater label file: {path}")
        doc = json.loads(path.read_text())
        if not isinstance(doc, dict):
            raise LabelsMissing(f"rater file {path.name} is not a JSON object")
        if "labels" not in doc:
            hint = " (found 'items' schema)" if "items" in doc else ""
            raise LabelsMissing(
                f"rater file {path.name} lacks the required 'labels' schema from "
                f"laya_blind_annotation_workflow.py{hint}; refusing non-human/"
                "programmatically generated label files"
            )
        if doc.get("rater_id") != rater:
            raise LabelsMissing(
                f"rater file {path.name} has rater_id={doc.get('rater_id')!r}, "
                f"expected {rater!r}"
            )
        done = doc.get("completed_at")
        if not isinstance(done, str) or not done.strip():
            raise LabelsMissing(
                f"rater file {path.name} has no completed_at timestamp; incomplete "
                "or unattested rater files are refused"
            )
        completed_at[rater] = done
        items = doc.get("labels") or []
        labels: dict[str, str] = {}
        malformed: list[str] = []
        for item in items:
            cid = item.get("case_id")
            label = item.get("label") or item.get("label_text")
            if cid is None:
                continue
            if label in (None, ""):
                malformed.append(cid)
                continue
            if str(label).upper() not in TAXONOMY:
                malformed.append(cid)
                continue
            labels[cid] = str(label).upper()
        if malformed:
            raise LabelsMissing(
                f"rater file {path.name} has empty/malformed labels for {len(malformed)} cases"
            )
        loaded[rater] = labels
    # Three independent humans cannot share one identical completion timestamp;
    # identical values are a hallmark of programmatically generated label files.
    inverted = {ts: r for r, ts in completed_at.items()}
    if len(inverted) != len(completed_at):
        dupes = sorted({ts for ts in completed_at.values()
                        if list(completed_at.values()).count(ts) > 1})
        raise LabelsMissing(
            f"identical completed_at across raters {sorted(completed_at)} "
            f"(timestamp(s) {dupes}); refusing programmatically generated labels"
        )
    return loaded


def require_full_coverage(loaded: dict[str, dict[str, str]], case_ids: list[str]) -> None:
    """Every confirmatory case must be labeled by every rater, or we refuse."""
    for rater, labels in loaded.items():
        missing = [cid for cid in case_ids if cid not in labels]
        if missing:
            raise LabelsMissing(
                f"rater {rater} is missing {len(missing)}/{len(case_ids)} confirmatory "
                f"cases (e.g. {missing[:10]}); partial label sets are refused so the "
                "analysis cannot silently shrink the evaluation set"
            )


def compute_blob(labels: dict[str, str], case_ids: list[str]) -> dict:
    counts = Counter(labels.get(cid) for cid in case_ids)
    blob = {
        "label_counts": dict(counts),
        "uncertain_cases": sorted(cid for cid in case_ids if labels.get(cid) == "UNCERTAIN"),
    }
    return blob


def pairwise_agreement(a: dict[str, str], b: dict[str, str], ids: list[str]) -> float:
    joined = [i for i in ids if i in a and i in b]
    if not joined:
        return 0.0
    agree = sum(1 for i in joined if a[i] == b[i])
    return agree / len(joined)


def fleiss_kappa(labels_by_rater: dict[str, dict[str, str]], ids: list[str], raters: list[str]) -> float:
    """Fleiss' kappa over a 9-category nominal scheme."""
    n = len(raters)
    if n < 2 or not ids:
        return 0.0
    cat_index = {c: i for i, c in enumerate(TAXONOMY)}
    total_units = 0
    p_i_sum = 0.0
    n_cat = [0] * len(TAXONOMY)
    for cid in ids:
        row = []
        for r in raters:
            lab = labels_by_rater[r].get(cid)
            if lab is not None:
                row.append(cat_index[lab])
        if len(row) != n:
            continue
        total_units += 1
        counts = [0] * len(TAXONOMY)
        for r in row:
            counts[r] += 1
            n_cat[r] += 1
        p_i = sum(c * (c - 1) for c in counts) / (n * (n - 1))
        p_i_sum += p_i
    if total_units == 0:
        return 0.0
    P_bar = p_i_sum / total_units
    N = total_units
    grand = n * N
    P_e = sum((c / grand) ** 2 for c in n_cat)
    if P_e == 1.0:
        return 1.0
    return (P_bar - P_e) / (1 - P_e)


def majority_vote(labels_by_rater: dict[str, dict[str, str]], ids: list[str], raters: list[str]) -> dict[str, dict]:
    out = {}
    for cid in ids:
        votes = [labels_by_rater[r][cid] for r in raters if cid in labels_by_rater[r]]
        if not votes:
            out[cid] = {"consensus": None, "agreement": 0, "raw_votes": []}
            continue
        counts = Counter(votes)
        winner, cnt = counts.most_common(1)[0]
        # Tie of top counts -> no strict majority consensus.
        top = counts.most_common()
        if len(top) > 1 and top[1][1] == top[0][1]:
            out[cid] = {"consensus": None, "agreement": cnt, "raw_votes": votes}
            continue
        out[cid] = {
            "consensus": winner if cnt / len(votes) > 0.5 else None,
            "agreement": cnt,
            "raw_votes": votes,
        }
    return out


def binary_projection(label: str | None) -> str:
    if label is None:
        return "excluded"
    if label == "BENIGN":
        return "negative"
    if label == "UNCERTAIN":
        return "excluded"
    return "positive"


def confusion(pred_pos: list[bool], truth_pos: list[bool]) -> dict:
    tp = fp = tn = fn = 0
    for p, t in zip(pred_pos, truth_pos):
        if p and t:
            tp += 1
        elif p and not t:
            fp += 1
        elif not p and not t:
            tn += 1
        else:
            fn += 1
    total = max(1, tp + fp + tn + fn)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    specificity = tn / (tn + fp) if tn + fp else 0.0
    fpr = fp / (fp + tn) if fp + tn else 0.0
    fnr = fn / (fn + tp) if fn + tp else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    balanced_acc = (recall + specificity) / 2
    return {
        "tp": tp, "fp": fp, "tn": tn, "fn": fn,
        "precision": precision, "recall": recall, "specificity": specificity,
        "fpr": fpr, "fnr": fnr, "macro_f1": f1, "balanced_accuracy": balanced_acc,
        "n": tp + fp + tn + fn,
    }


def mcnemar(b_c: int, b_w: int) -> dict:
    """Simple exact-ish McNemar (chi2 with continuity correction) given contingency cells."""
    total = b_c + b_w
    if total == 0:
        return {"statistic": 0.0, "p_value": 1.0}
    import math
    stat = (abs(b_c - b_w) - 1) ** 2 / (b_c + b_w) if (b_c + b_w) else 0.0
    # --- too small to fold into chi2; do a simple exact binomial p-value
    def binom_cdf(k, n, p=0.5):
        return sum(math.comb(n, i) * (p ** i) * ((1 - p) ** (n - i)) for i in range(k + 1))
    if total == 0:
        p_value = 1.0
    else:
        k = min(b_c, b_w)
        p_value = min(1.0, 2 * binom_cdf(k, total))
    return {"statistic": stat, "p_value": p_value, "b_c": b_c, "b_w": b_w}


def paired_correctness(preds: dict[str, dict], truth_binary: dict[str, str]) -> dict:
    cells = {"both_correct": 0, "chrollo_only": 0, "laya_only": 0, "both_wrong": 0}
    corrections = harms = 0
    for cid, tb in truth_binary.items():
        p = preds.get(cid)
        if p is None:
            continue
        chrollo_pos = truth_literal_to_binary(p.get("chrollo_output"))
        laya_pos = truth_literal_to_binary(p.get("laya_answer"))
        if chrollo_pos is None or laya_pos is None:
            continue
        ch_correct = chrollo_pos == tb
        la_correct = laya_pos == tb
        if ch_correct and la_correct:
            cells["both_correct"] += 1
        elif ch_correct:
            cells["chrollo_only"] += 1
            corrections += 1
        elif la_correct:
            cells["laya_only"] += 1
            harms += 1
        else:
            cells["both_wrong"] += 1
    return {
        "table": cells,
        "laya_corrections_vs_chrollo": cells["laya_only"],
        "laya_harms_vs_chrollo": cells["chrollo_only"],
        "net_corrections": cells["laya_only"] - cells["chrollo_only"],
    }


def truth_literal_to_binary(vlu) -> str | None:
    """Interpret 'malicious'/'benign'-style literals as binary strings."""
    if vlu is None:
        return None
    s = str(vlu).strip().lower()
    if s in ("malicious", "pos", "positive", "true", "1"):
        return "positive"
    if s in ("benign", "neg", "negative", "false", "0"):
        return "negative"
    return None


def gate_frozen(preds: dict[str, dict], threshold: float = 0.65) -> dict:
    activated = sum(1 for p in preds.values()
                    if p.get("chrollo_confidence") is not None
                    and float(p["chrollo_confidence"]) < threshold)
    return {
        "threshold": threshold,
        "gate_activated_count": activated,
        "gate_activation_rate": activated / max(1, len(preds)),
        "expected_extra_latency_ms_p50": None,
        "expected_extra_latency_ms_p95": None,
    }


def run() -> dict:
    case_ids = load_case_ids()
    raters = ["r1", "r2", "r3"]
    labels_by_rater = load_rater_labels(raters)
    require_full_coverage(labels_by_rater, case_ids)
    preds = load_frozen_predictions()

    # ---- inter-rater quality
    pairs = [(raters[i], raters[j]) for i in range(len(raters)) for j in range(i + 1, len(raters))]
    pairwise = {f"{a}-vs-{b}": pairwise_agreement(labels_by_rater[a], labels_by_rater[b], case_ids)
                for a, b in pairs}
    raw_agreement = sum(
        1 for cid in case_ids
        if len({labels_by_rater[r][cid] for r in raters if cid in labels_by_rater[r]}) == 1
    ) / max(1, len(case_ids))
    kappa = fleiss_kappa(labels_by_rater, case_ids, raters)
    uncertain_rate = sum(1 for cid in case_ids
                         if labels_by_rater["r1"].get(cid) == "UNCERTAIN") / max(1, len(case_ids))

    # ---- consensus (majority vote; all raw labels preserved)
    consensus = majority_vote(labels_by_rater, case_ids, raters)
    truth_binary = {cid: binary_projection(v["consensus"]) for cid, v in consensus.items()}

    # ---- per-model classification metrics on adjudicatable cases
    adjudicable = [cid for cid in case_ids if truth_binary[cid] in ("positive", "negative")]
    chrollo_pred, laya_pred = [], []
    chrollo_truth, laya_truth = [], []
    for cid in adjudicable:
        p = preds.get(cid)
        if p is None:
            continue
        ch_correct_side = truth_literal_to_binary(p.get("chrollo_output"))
        la_correct_side = truth_literal_to_binary(p.get("laya_answer"))
        if ch_correct_side is None or la_correct_side is None:
            continue
        chrollo_pred.append(ch_correct_side == "positive")
        chrollo_truth.append(truth_binary[cid] == "positive")
        laya_pred.append(la_correct_side == "positive")
        laya_truth.append(truth_binary[cid] == "positive")

    report = {
        "n_cases": len(case_ids),
        "n_raters": len(raters),
        "raw_agreement": raw_agreement,
        "pairwise_agreement": pairwise,
        "fleiss_kappa": kappa,
        "uncertain_rate_r1": uncertain_rate,
        "label_blobs": {r: compute_blob(labels_by_rater[r], case_ids) for r in raters},
        "consensus_majority": {cid: v["consensus"] for cid, v in consensus.items()},
        "n_adjudicable_binary": len(adjudicable),
        "metric_status": (
            "NOT_IDENTIFIABLE_NO_MAPPED_PREDICTIONS" if not chrollo_pred and not laya_pred
            else "OK"
        ),
        "chrollo_metrics": confusion(chrollo_pred, chrollo_truth) if chrollo_pred else None,
        "laya_metrics": confusion(laya_pred, laya_truth) if laya_pred else None,
        "paired_correctness": paired_correctness(preds, truth_binary),
        "gate_summary": gate_frozen(preds),
        "mcnemar_binary": None,
    }
    cells = report["paired_correctness"]["table"]
    report["mcnemar_binary"] = mcnemar(cells["laya_only"], cells["chrollo_only"])
    return report


def main() -> int:
    try:
        report = run()
    except LabelsMissing as e:
        print(f"REFUSING: {e}", file=sys.stderr)
        print("No human-label join may be simulated; analysis is refused until genuine "
              "per-rater label files land in results/laya_research/rater_labels/.", file=sys.stderr)
        return 2
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(f"WROTE {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
