#!/bin/bash
# E31 wrapper: repaired chat budget (1024), one invocation per model,
# lane env from the protected file (never committed).
set -a
source /home/elaref/.config/ragin/openweight.env
set +a
export TOMO_PATH=/nonexistent-tomography-env
export LLM_TARGET_TIMEOUT=60
export RAGIN_LLM_MAX_OUTPUT_TOKENS=1024
export LLM_TARGET_MAX_OUTPUT_TOKENS=1024
for M in DeepSeek-V4-Flash DeepSeek-V4-Pro MiniMax-M3.1-Flash; do
  echo "=== E31 model: $M ==="
  export RAGIN_LLM_BASE_URL="$OPENWEIGHT_BASE"
  export RAGIN_LLM_API_KEY="$OPENWEIGHT_API_KEY"
  export RAGIN_LLM_MODEL="$M"
  python3 run_e30_openweight_panel.py "$M" 20 2718 E31
done
