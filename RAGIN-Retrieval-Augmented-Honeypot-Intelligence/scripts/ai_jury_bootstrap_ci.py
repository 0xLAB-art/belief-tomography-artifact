"""Bootstrap 95% CI on the AI-jury Fleiss kappa + leave-one-juror-out check.

Resamples the 120 existing case labels from results/laya_research/ai_jury_v1/
(no API calls). Outputs results/laya_research/ai_jury_bootstrap_ci/ with a
manifest and a JSON summary: percentile CI on multiclass kappa, kappa for each
2-juror subset, and Po/Pe decomposition (9-class and binary collapse).
"""

import hashlib
import json
import random
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V1 = ROOT / "results/laya_research/ai_jury_v1"
OUT = ROOT / "results/laya_research/ai_jury_bootstrap_ci"
MODELS = ["gpt-5.6-sol", "gpt-6-astra", "gpt-6.1-sol"]
TAXONOMY = [
    "BENIGN", "RECON", "SUSPICIOUS", "EXPLOITATION", "PRIVILEGE_ESCALATION",
    "DATA_ACCESS", "PERSISTENCE", "OTHER_ATTACK", "UNCERTAIN",
]
BINARY = {"BENIGN": "benign"} | {c: "attack" for c in TAXONOMY if c != "BENIGN"}
N_RESAMPLE = 10_000
SEED = 42


def fleiss(labels_by_rater, ids, cats=None):
    cats = cats or TAXONOMY
    idx = {c: i for i, c in enumerate(cats)}
    n_raters = len(labels_by_rater)
    n_items = len(ids)
    cat_counts = [[0] * len(cats) for _ in range(n_items)]
    for j, cid in enumerate(ids):
        for lab in labels_by_rater.values():
            cat_counts[j][idx[lab[cid]]] += 1
    totals = n_raters * n_items
    p_i = [sum((c * (c - 1)) for c in row) / (n_raters * (n_raters - 1))
           for row in cat_counts]
    p_bar = sum(p_i) / n_items
    col_tot = [sum(row[i] for row in cat_counts) / totals for i in range(len(cats))]
    p_e = sum(c * c for c in col_tot)
    if p_e == 1.0:
        return 1.0, p_bar, p_e
    return (p_bar - p_e) / (1 - p_e), p_bar, p_e


def main():
    labels = {}
    packet_sha = None
    for m in MODELS:
        doc = json.loads((V1 / f"{m.replace('/', '_')}.json").read_text())
        labels[m] = {i["case_id"]: i["label"] for i in doc["items"]}
        if packet_sha is None:
            packet_sha = doc.get("packet_sha256")
    ids = sorted(set.intersection(*[set(l) for l in labels.values()]))
    assert len(ids) == 120, f"expected 120 shared cases, got {len(ids)}"

    rng = random.Random(SEED)
    k_full, po, pe = fleiss(labels, ids)

    def kappa_resample():
        sample = [ids[rng.randrange(len(ids))] for _ in range(len(ids))]
        return fleiss(labels, sample)[0]

    boots = sorted(kappa_resample() for _ in range(N_RESAMPLE))
    ci = [boots[int(0.025 * N_RESAMPLE) - 1], boots[int(0.975 * N_RESAMPLE) - 1]]

    loo = {}
    for m in MODELS:
        sub = {k: v for k, v in labels.items() if k != m}
        loo[m] = fleiss(sub, ids)[0]

    binary = {m: {cid: BINARY[v] for cid, v in l.items()} for m, l in labels.items()}
    BINARY_CATS = ["benign", "attack"]
    kb_full, bpo, bpe = fleiss(binary, ids, cats=BINARY_CATS)
    boots_b = sorted(
        fleiss(binary, [ids[rng.randrange(len(ids))] for _ in range(len(ids))],
               cats=BINARY_CATS)[0]
        for _ in range(N_RESAMPLE))
    bci = [boots_b[int(0.025 * N_RESAMPLE) - 1], boots_b[int(0.975 * N_RESAMPLE) - 1]]

    OUT.mkdir(parents=True, exist_ok=True)
    summary = {
        "schema": "ragin.ai_jury.bootstrap_ci.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "n_cases": len(ids), "n_resamples": N_RESAMPLE, "seed": SEED,
        "fleiss_kappa_multiclass": k_full, "ci95": ci, "po": po, "pe": pe,
        "leave_one_juror_out": loo,
        "fleiss_kappa_binary": kb_full, "binary_ci95": bci, "binary_po": bpo, "binary_pe": bpe,
        "note": "case-level resampling of existing v1 labels; no new model calls",
    }
    (OUT / "bootstrap_ci_summary.json").write_text(json.dumps(summary, indent=2))
    manifest = {
        "inputs": {m: str((V1 / f"{m.replace('/', '_')}.json").relative_to(ROOT))
                   for m in MODELS},
        "seed": SEED, "n_resamples": N_RESAMPLE,
        "run_at": summary["generated_at"],
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
