#!/usr/bin/env bash
# Wait for both v2 arms to reach the pre-registered 20 sessions, then write
# results/field_attack/arm_stats_v2.json exactly once.
#
# Runs detached from the agent session so the analysis still lands if the
# session ends mid-collection. Progress goes to /tmp/v2_watch.log.
set -uo pipefail

cd "$(dirname "$0")/.." || exit 1

A=results/field_attack/sessions_v2_armA.jsonl
C=results/field_attack/sessions_v2_armC.jsonl

count_pairs() {
  python3 - "$1" <<'PY'
import json, sys

pairs = set()
try:
    handle = open(sys.argv[1], encoding="utf-8")
except FileNotFoundError:
    print(0)
    raise SystemExit
for line in handle:
    line = line.strip()
    if not line:
        continue
    record = json.loads(line)
    if record.get("partial") or not record.get("error"):
        pairs.add((record.get("persona"), record.get("run_id")))
print(len(pairs))
PY
}

while true; do
  a=$(count_pairs "$A")
  c=$(count_pairs "$C")
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) A=$a/20 C=$c/20" >> /tmp/v2_watch.log
  if [ "${a:-0}" -ge 20 ] && [ "${c:-0}" -ge 20 ]; then
    .venv/bin/python scripts/field_attack_stats_v2.py >> /tmp/v2_watch.log 2>&1
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) stats written" >> /tmp/v2_watch.log
    break
  fi
  sleep 300
done
