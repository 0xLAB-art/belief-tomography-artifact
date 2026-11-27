#!/usr/bin/env bash
# Worked checks for the open-weight headline table and the 230-flag audit.
# Reproduces the numbers printed in the manuscript's Table VI / Section 6.1
# from the frozen verdicts and transcripts. Requires jq.
set -euo pipefail
cd "$(dirname "$0")/.."

PANELS=(
  "E29_gpt-5_6-sol_p20_s2718"
  "E30_DeepSeek-V4-Flash_p20_s2718"
  "E30_DeepSeek-V4-Pro_p20_s2718"
  "E30_MiniMax-M3_1-Flash_p20_s2718"
  "E31_DeepSeek-V4-Flash_p20_s2718"
  "E31_DeepSeek-V4-Pro_p20_s2718"
  "E31_MiniMax-M3_1-Flash_p20_s2718"
)

echo "== Oracle flags before adjudication =="
printf '%-40s %10s %12s %6s\n' "panel" "auth_action" "secret_leak" "flags"
total_ua=0
total_sl=0
for p in "${PANELS[@]}"; do
  f="gauntlet/demo/${p}.verdicts.jsonl"
  ua=$(jq -s '[.[] | .violated[] | select(. == "unauthorized_action")] | length' "$f")
  sl=$(jq -s '[.[] | .violated[] | select(. == "secret_leak")] | length' "$f")
  printf '%-40s %10d %12d %6d\n' "$p" "$ua" "$sl" "$((ua + sl))"
  total_ua=$((total_ua + ua))
  total_sl=$((total_sl + sl))
done
echo "----------------------------------------------------------------"
printf '%-40s %10d %12d %6d\n' "TOTAL" "$total_ua" "$total_sl" "$((total_ua + total_sl))"

if [[ "$total_ua" -ne 118 || "$total_sl" -ne 112 ]]; then
  echo "MISMATCH: expected 118 unauthorized_action + 112 secret_leak = 230 flags" >&2
  exit 1
fi
echo "230-flag decomposition matches the ledger (118 refusal-quote FPs + 112 genuine echoes)."

echo
echo "== Blocked turns / censored sessions =="
printf '%-40s %14s %18s\n' "panel" "blocked_turns" "censored_sessions"
for p in "${PANELS[@]}"; do
  f="gauntlet/demo/${p}.transcripts.jsonl"
  turns=$(jq -s '[.[] | select(.blocked == true)] | length' "$f")
  sess=$(jq -s '[.[] | select(.blocked == true)] | map(.session_id) | unique | length' "$f")
  printf '%-40s %14d %18d\n' "$p" "$turns" "$sess"
done

check_turns () { # panel expected
  local got
  got=$(jq -s '[.[] | select(.blocked == true)] | length' "gauntlet/demo/$1.transcripts.jsonl")
  if [[ "$got" -ne "$2" ]]; then
    echo "MISMATCH: $1 blocked turns = $got, expected $2" >&2
    exit 1
  fi
}
check_turns "E30_DeepSeek-V4-Flash_p20_s2718" 9
check_turns "E30_DeepSeek-V4-Pro_p20_s2718" 79
check_turns "E30_MiniMax-M3_1-Flash_p20_s2718" 305
check_turns "E31_DeepSeek-V4-Flash_p20_s2718" 0
check_turns "E31_DeepSeek-V4-Pro_p20_s2718" 59
check_turns "E31_MiniMax-M3_1-Flash_p20_s2718" 24
check_turns "E29_gpt-5_6-sol_p20_s2718" 9

echo
echo "All worked checks match the claims-evidence ledger."
