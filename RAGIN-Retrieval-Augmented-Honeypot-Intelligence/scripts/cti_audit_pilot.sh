#!/usr/bin/env bash
# Smoke pilot of the CTI manual audit chain (advisory #5) at --limit 2:
# collect → packet → annotate A → annotate B → score, then remove every
# artifact it created so the FULL run starts clean.
# Usage: bash scripts/cti_audit_pilot.sh
set -uo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python
FAIL=0

echo "== [1/5] collect --limit 2 =="
$PY scripts/cti_manual_audit.py collect --limit 2 || FAIL=1

echo "== [2/5] packet --limit 2 =="
$PY scripts/cti_manual_audit.py packet --limit 2 || FAIL=1

IDS=$($PY - <<'EOF'
import json
pk = json.load(open('results/cti_audit_packets.json'))
print(','.join(p['row_id'] for p in pk['packets']))
EOF
)
echo "pilot packets: $IDS"

echo "== [3/5] annotate A =="
rm -f results/cti_audit_annotations_A.json
$PY scripts/cti_manual_audit.py annotate --annotator A --only "$IDS" --batch 6 --budget-s 300 || FAIL=1

echo "== [4/5] annotate B =="
rm -f results/cti_audit_annotations_B.json
$PY scripts/cti_manual_audit.py annotate --annotator B --only "$IDS" --batch 6 --budget-s 300 || FAIL=1

echo "== [5/5] score =="
$PY scripts/cti_manual_audit.py score || FAIL=1

echo "== cleanup =="
rm -f results/cti_audit_packets.json results/cti_audit_packets.md \
      results/cti_audit_blinding_key.json results/cti_manual_audit.json \
      results/cti_audit_annotations_A.json results/cti_audit_annotations_B.json \
      results/cti_manual_audit_corpus_limit2.json \
      results/cti_manual_audit_corpus_checkpoint.json
echo "pilot done FAIL=$FAIL"
exit $FAIL
