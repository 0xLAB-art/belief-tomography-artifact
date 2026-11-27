#!/usr/bin/env python3
"""Build the final blind annotation package for the confirmatory set.

Phases 6, 8, 9 in one deterministic pass:

- blind_annotation_confirmatory.json : human-visible packet (case_id,
  evidence, context only). No source, no provenance, no predictions.
- confirmatory_provenance_private.json : private provenance manifest kept
  OUTSIDE the rater packet (source family, quality band, cluster, strata).
- rater_packets/r{1,2,3}.json (+ .csv) : three true-blind packets, same case
  set, independently randomized order per rater, embedded schema, empty
  label fields.
- confirmatory_frozen_predictions.jsonl : prediction rows for ONLY the
  frozen confirmatory case IDs, extracted from the pre-existing frozen
  predictions file (no model re-run), hashed before any labels exist.
- Re-hashes gating_preregistration.json after reconciliation.

Prediction separation guarantee: the rater packets are built exclusively
from blind_annotation_confirmatory.json; prediction rows are joined into a
separate file that raters never see.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import random
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RES = REPO / "results/laya_research"

CASE_IDS = RES / "confirmatory_case_ids.txt"
POOL = RES / "independent_label_candidates_v2.json"
AUDIT = RES / "candidate_quality_audit.jsonl"
CLUSTERS = RES / "deduplication_clusters.json"
FROZEN = RES / "frozen_predictions.jsonl"
GATING = RES / "gating_preregistration.json"

BLIND_PACKET = RES / "blind_annotation_confirmatory.json"
PROVENANCE = RES / "confirmatory_provenance_private.json"
RATER_DIR = RES / "rater_packets"
CONF_PRED = RES / "confirmatory_frozen_predictions.jsonl"

RATER_SEEDS = {"r1": 202610121, "r2": 202610122, "r3": 202610123}

SCHEMA = {
    "taxonomy": [
        "BENIGN", "RECON", "SUSPICIOUS", "EXPLOITATION",
        "PRIVILEGE_ESCALATION", "DATA_ACCESS", "PERSISTENCE",
        "OTHER_ATTACK", "UNCERTAIN",
    ],
    "label_field": "label",
    "notes_field": "notes",
    "instructions_path": "docs/laya_integration/INDEPENDENT_LABELING_PROTOCOL.md",
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    case_ids = [ln.strip() for ln in CASE_IDS.read_text().splitlines() if ln.strip()]
    case_id_set = set(case_ids)

    pool = json.loads(POOL.read_text())
    pool_by_id = {c["id"]: c for c in pool["candidates"]}
    audit_by_id = {
        json.loads(line)["case_id"]: json.loads(line)
        for line in AUDIT.read_text().splitlines() if line.strip()
    }
    clusters = json.loads(CLUSTERS.read_text())
    case_to_cluster = {
        m: c["cluster_id"] for c in clusters for m in c["member_ids"]
    }

    missing = [cid for cid in case_ids if cid not in pool_by_id]
    if missing:
        raise SystemExit(f"confirmatory ids missing from pool: {missing}")

    # ── Phase 6: blind packet (human-visible only) ──────────────────────────
    blind = []
    for cid in case_ids:
        c = pool_by_id[cid]
        blind.append({
            "case_id": cid,
            "evidence": c["evidence"],
            "context": c.get("context", ""),
        })
    BLIND_PACKET.write_text(json.dumps(blind, indent=2) + "\n")

    # ── private provenance manifest (never in rater packet) ─────────────────
    prov = {
        "created_at": int(time.time()),
        "created_by": "scripts/laya_confirmatory_packet.py",
        "note": "PRIVATE. Not part of any rater-visible artifact.",
        "case_ids_hash_sha256": sha256_file(CASE_IDS),
        "cases": [],
    }
    for cid in case_ids:
        a = audit_by_id.get(cid, {})
        prov["cases"].append({
            "case_id": cid,
            "source_family": a.get("source_family"),
            "quality_band": a.get("quality_band"),
            "context_depth": a.get("context_depth"),
            "interpretability": a.get("interpretability"),
            "duplicate_cluster_id": case_to_cluster.get(cid),
            "is_honeypot_source": a.get("is_honeypot_source"),
            "pool_source_id": pool_by_id[cid].get("_source_id"),
            "leakage_terms": a.get("leakage_terms", []),
        })
    PROVENANCE.write_text(json.dumps(prov, indent=2) + "\n")

    # ── Phase 8: three blinded rater packets ────────────────────────────────
    RATER_DIR.mkdir(parents=True, exist_ok=True)
    for rater, seed in RATER_SEEDS.items():
        rng = random.Random(seed)
        order = list(blind)
        rng.shuffle(order)
        packet = {
            "rater": rater,
            "schema": SCHEMA,
            "case_count": len(order),
            "blinding_note": (
                "Case IDs are opaque. Evidence and context only. No provenance, "
                "no predictions, no truth labels. Fill 'label' for every case "
                "using the taxonomy in the instructions; leave 'notes' empty or "
                "add short justification."
            ),
            "cases": [
                {
                    "case_id": row["case_id"],
                    "evidence": row["evidence"],
                    "context": row["context"],
                    "label": "",
                    "notes": "",
                }
                for row in order
            ],
        }
        out = RATER_DIR / f"{rater}.json"
        out.write_text(json.dumps(packet, indent=2) + "\n")

        # CSV equivalent
        csv_buf = io.StringIO()
        writer = csv.writer(csv_buf)
        writer.writerow(["case_id", "evidence", "context", "label", "notes"])
        for row in packet["cases"]:
            writer.writerow([row["case_id"], row["evidence"], row["context"], "", ""])
        (RATER_DIR / f"{rater}.csv").write_text(csv_buf.getvalue())

    # ── Phase 9: frozen predictions for the confirmatory set only ───────────
    frozen_rows = []
    seen = set()
    for line in FROZEN.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        cid = row.get("case_id")
        if cid in case_id_set:
            frozen_rows.append(row)
            seen.add(cid)
    missing_preds = sorted(case_id_set - seen)
    if missing_preds:
        raise SystemExit(f"missing frozen predictions for: {missing_preds}")

    with CONF_PRED.open("w") as fh:
        for row in frozen_rows:
            fh.write(json.dumps(row, sort_keys=True) + "\n")

    conf_pred_hash = sha256_file(CONF_PRED)

    # ── Phase 10: re-hash gating preregistration after reconciliation ───────
    gating_hash = sha256_file(GATING)

    attestation = {
        "created_at": int(time.time()),
        "confirmatory_case_ids_sha256": sha256_file(CASE_IDS),
        "blind_packet_sha256": sha256_file(BLIND_PACKET),
        "confirmatory_frozen_predictions_sha256": conf_pred_hash,
        "confirmatory_frozen_predictions_rows": len(frozen_rows),
        "gating_preregistration_sha256": gating_hash,
        "rater_packet_hashes": {
            r: sha256_file(RATER_DIR / f"{r}.json") for r in RATER_SEEDS
        },
        "human_labels_exist": False,
        "note": (
            "All hashes recorded BEFORE any human labels exist. The rater "
            "packets contain no prediction or provenance fields by construction."
        ),
    }
    (RES / "confirmatory_package_attestation.json").write_text(
        json.dumps(attestation, indent=2) + "\n"
    )

    print("Wrote", BLIND_PACKET, f"({len(blind)} cases)")
    print("Wrote", PROVENANCE)
    for r in RATER_SEEDS:
        print("Wrote", RATER_DIR / f"{r}.json", "and", RATER_DIR / f"{r}.csv")
    print("Wrote", CONF_PRED, f"({len(frozen_rows)} rows)")
    print("confirmatory_frozen_predictions sha256:", conf_pred_hash)
    print("gating_preregistration sha256:", gating_hash)
    print("Wrote", RES / "confirmatory_package_attestation.json")


if __name__ == "__main__":
    main()
