#!/usr/bin/env python3
"""Offline blinded annotation workflow for the independent Laya evaluation.

This script does NOT fabricate human labels. It only:

 1. Loads the blinded packet (results/laya_research/blind_annotation_packet.json).
 2. Optionally reseeds the item order for a fresh annotator copy (deterministic
    seed per rater so the same rater can regenerate the same order, but different
    raters get different orders unless they explicitly share a seed).
 3. Emits an annotation template the rater fills by hand (JSON or CSV).
 4. Stores per-rater labels under results/laya_research/rater_labels/<rater>.json
    when the rater supplies them via a JSON file or programmatic input.
 5. Keeps the truth/manifest (independent_label_candidates.json) separate and
    never exposes it to raters.

Annotation schema (compact, cybersecurity SSH-task oriented):

  BENIGN
  RECON
  SUSPICIOUS
  EXPLOITATION
  PRIVILEGE_ESCALATION
  DATA_ACCESS
  OTHER_ATTACK
  UNCERTAIN

Binary mapping (derived later for evaluation, NOT shown to raters):

  BENIGN            -> benign
  RECON             -> malicious
  SUSPICIOUS        -> malicious (uncertain leaning malicious)
  EXPLOITATION      -> malicious
  PRIVILEGE_ESCALATION -> malicious
  DATA_ACCESS       -> malicious
  OTHER_ATTACK      -> malicious
  UNCERTAIN         -> unresolved (do not collapse silently)

The rater file schema:

  {
    "rater_id": "r1",
    "annotation_version": 1,
    "started_at": "...",
    "completed_at": "...",
    "order_seed": 12345,
    "labels": [
      {"case_id": "...", "label": "BENIGN", "notes": "...", "timestamp": "..."},
      ...
    ],
    "notes": "...",
    "interrupted": false
  }

Inter-rater agreement is computed only after labels are collected, in a
separate evaluation step, never here.
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import time
from datetime import datetime, timezone
from pathlib import Path

PACKET_PATH = Path("results/laya_research/blind_annotation_packet.json")
CANDIDATES_PATH = Path("results/laya_research/independent_label_candidates.json")
RATER_LABELS_DIR = Path("results/laya_research/rater_labels")
RATER_LABELS_DIR.mkdir(parents=True, exist_ok=True)

VALID_LABELS = [
    "BENIGN",
    "RECON",
    "SUSPICIOUS",
    "EXPLOITATION",
    "PRIVILEGE_ESCALATION",
    "DATA_ACCESS",
    "OTHER_ATTACK",
    "UNCERTAIN",
]

BINARY_MAP = {
    "BENIGN": "benign",
    "RECON": "malicious",
    "SUSPICIOUS": "malicious",
    "EXPLOITATION": "malicious",
    "PRIVILEGE_ESCALATION": "malicious",
    "DATA_ACCESS": "malicious",
    "OTHER_ATTACK": "malicious",
    "UNCERTAIN": "unresolved",
}


def load_packet() -> list[dict]:
    if not PACKET_PATH.exists():
        raise FileNotFoundError(f" blind packet not found: {PACKET_PATH}")
    data = json.loads(PACKET_PATH.read_text())
    if not isinstance(data, list):
        raise ValueError("blind_annotation_packet.json must be a JSON array of packets")
    for item in data:
        if "id" not in item or "evidence" not in item:
            raise ValueError(f" packet missing required fields: {item}")
    return data


def annotate_sheet(packet: list[dict], order_seed: int | None, rater_id: str) -> dict:
    """Produce an annotation template (deterministic per rater)."""
    rng = random.Random(order_seed if order_seed is not None else int(time.time()) % 1_000_000)
    order = list(range(len(packet)))
    rng.shuffle(order)

    version = 1
    started_at = datetime.now(timezone.utc).isoformat()
    sheet = {
        "rater_id": rater_id,
        "annotation_version": version,
        "started_at": started_at,
        "completed_at": None,
        "order_seed": rng.randint(0, 1_000_000) if order_seed is None else order_seed,
        "labels": [],
        "notes": "",
        "interrupted": False,
    }
    for idx in order:
        item = packet[idx]
        sheet["labels"].append(
            {
                "rank": len(sheet["labels"]) + 1,
                "case_id": item["id"],
                "evidence_preview": item["evidence"][:200].replace("\n", " "),
                "label": "",
                "notes": "",
                "timestamp": None,
            }
        )
    return sheet, order


def emit_json_template(sheet: dict, out_path: Path) -> None:
    out_path.write_text(json.dumps(sheet, indent=2, ensure_ascii=False) + "\n")


def emit_csv_template(sheet: dict, out_path: Path) -> None:
    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "rank", "case_id", "evidence_preview", "label", "notes", "timestamp"
        ])
        for row in sheet["labels"]:
            w.writerow([
                row["rank"], row["case_id"], row["evidence_preview"],
                row["label"], row["notes"], row["timestamp"] or ""
            ])


def load_rater_labels(path: Path) -> dict:
    data = json.loads(path.read_text())
    required = {"rater_id", "annotation_version", "labels"}
    missing = required - set(data.keys())
    if missing:
        raise ValueError(f" rater label file missing fields: {missing}")
    for row in data["labels"]:
        if "case_id" not in row or "label" not in row:
            raise ValueError(f" label row missing case_id/label: {row}")
        if row["label"] and row["label"] not in VALID_LABELS:
            raise ValueError(f" invalid label for {row.get('case_id')}: {row['label']}")
    return data


def store_rater_labels(rater_id: str, sheet: dict, completed: bool) -> Path:
    now = datetime.now(timezone.utc).isoformat()
    sheet["completed_at"] = now if completed else sheet.get("completed_at")
    sheet["interrupted"] = not completed
    out_path = RATER_LABELS_DIR / f"{rater_id}.json"
    out_path.write_text(json.dumps(sheet, indent=2, ensure_ascii=False) + "\n")
    return out_path


def rater_label_summary(rater_id: str) -> dict:
    path = RATER_LABELS_DIR / f"{rater_id}.json"
    if not path.exists():
        raise FileNotFoundError(f" no labels stored for rater {rater_id}")
    data = load_rater_labels(path)
    counts: dict[str, int] = {l: 0 for l in VALID_LABELS}
    unresolved = 0
    for row in data["labels"]:
        if not row["label"]:
            unresolved += 1
            continue
        counts[row["label"]] += 1
    return {
        "rater_id": data["rater_id"],
        "annotation_version": data["annotation_version"],
        "n_items": len(data["labels"]),
        "n_labeled": sum(counts.values()),
        "n_unresolved": unresolved,
        "label_counts": counts,
        "binary_counts": {
            "benign": counts["BENIGN"],
            "malicious": counts["RECON"] + counts["SUSPICIOUS"]
            + counts["EXPLOITATION"] + counts["PRIVILEGE_ESCALATION"]
            + counts["DATA_ACCESS"] + counts["OTHER_ATTACK"],
            "unresolved": counts["UNCERTAIN"] + unresolved,
        },
    }


def main() -> None:
    p = argparse.ArgumentParser(
        description="Blinded annotation workflow for independent Laya evaluation"
    )
    p.add_argument(
        "--action",
        choices=["template-json", "template-csv", "store", "summary", "list-raters"],
        required=True,
        help="workflow action",
    )
    p.add_argument("--rater", default="r1", help="rater identifier")
    p.add_argument("--order-seed", type=int, default=None, help="deterministic item order seed")
    p.add_argument("--input", default=None, help="path to a filled rater JSON to store")
    p.add_argument("--to", default=None, help="output template path")
    args = p.parse_args()

    packet = load_packet()

    if args.action in ("template-json", "template-csv"):
        sheet, order = annotate_sheet(packet, args.order_seed, args.rater)
        out = Path(args.to) if args.to else Path(f"annotation_template_{args.rater}.json")
        if args.action == "template-json":
            emit_json_template(sheet, out)
            print(f"wrote JSON template: {out}  (rater={args.rater}, items={len(packet)})")
            print("labels left blank for the human rater to fill.")
        else:
            emit_csv_template(sheet, out)
            print(f"wrote CSV template: {out}  (rater={args.rater}, items={len(packet)})")
        return

    if args.action == "store":
        if not args.input:
            raise SystemExit(" --input required for store")
        data = load_rater_labels(Path(args.input))
        if data["rater_id"] != args.rater:
            raise SystemExit(f" rater_id mismatch: file={data['rater_id']} vs --rater={args.rater}")
        path = store_rater_labels(args.rater, data, completed=True)
        print(f"stored rater labels: {path}")
        return

    if args.action == "summary":
        print(json.dumps(rater_label_summary(args.rater), indent=2))
        return

    if args.action == "list-raters":
        raters = sorted(p.stem for p in RATER_LABELS_DIR.glob("*.json"))
        print("raters with stored labels:", raters if raters else "(none yet)")
        return


if __name__ == "__main__":
    main()
