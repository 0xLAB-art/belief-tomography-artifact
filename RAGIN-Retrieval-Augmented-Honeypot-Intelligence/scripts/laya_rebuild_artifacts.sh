#!/usr/bin/env bash
# Golden-path rebuild of the independent-label artifacts.
# Reproducible and auditable: deterministic seeds and explicit provenance.
set -euo pipefail

REPO_ROOT="."
cd "$REPO_ROOT"

echo "=== rebuild candidate pool + blind packet ==="
python scripts/laya_independent_candidate_pool.py

echo "=== manifest consistency + blindness verification ==="
python scripts/laya_manifest_consistency_check.py

echo "=== rater template smoke (r1 + r2) ==="
python scripts/laya_blind_annotation_workflow.py --action template-json --rater r1 --to results/laya_research/annotation_template_r1.json
python scripts/laya_blind_annotation_workflow.py --action template-csv --rater r1 --to results/laya_research/annotation_template_r1.csv
python scripts/laya_blind_annotation_workflow.py --action template-json --rater r2 --to results/laya_research/annotation_template_r2.json

echo "=== done ==="
