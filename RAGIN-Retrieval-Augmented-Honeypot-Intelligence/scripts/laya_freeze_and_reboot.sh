#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

echo "=== rebuild v2 pool artifacts ==="
python scripts/laya_candidate_pool_v2.py

echo "=== rebuild blind packet from manifest ==="
python scripts/laya_manifest_consistency_check.py

echo "=== rebuild rater templates r1/r2/r3 ==="
mkdir -p results/laya_research/rater_templates results/laya_research/annotation_examples
python scripts/laya_blind_annotation_workflow.py --action template-json --rater r1 --to results/laya_research/rater_templates/r1.json
python scripts/laya_blind_annotation_workflow.py --action template-json --rater r2 --to results/laya_research/rater_templates/r2.json
python scripts/laya_blind_annotation_workflow.py --action template-json --rater r3 --to results/laya_research/rater_templates/r3.json

echo "=== run frozen prediction skeleton (no labels) ==="
python scripts/laya_frozen_runner.py --out results/laya_research/frozen_predictions.jsonl

echo "=== fresh targeted pytest provenance ==="
python -m pytest tests/unit/test_server_v2_laya_config.py tests/unit/test_server_v2_laya_runtime_no_second_path.py tests/unit/test_optional_assessment.py tests/security/ -q >/tmp/target_final.out 2>&1
echo "target_exit=$?"

echo "=== oracle provenance (untouched) ==="
python -m pytest tests/unit/test_verifier_redteam_security_oracle.py -q >/tmp/oracle_final.out 2>&1
echo "oracle_exit=$?"

echo "=== done ==="
