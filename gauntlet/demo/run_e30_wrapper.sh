#!/bin/bash
# E30 wrapper: one invocation per model, lane env from the protected file.
set -a
source /home/elaref/.config/ragin/openweight.env
set +a
export TOMO_PATH=/nonexistent-tomography-env
for M in DeepSeek-V4-Flash DeepSeek-V4-Pro MiniMax-M3.1-Flash; do
  echo "=== E30 model: $M ==="
  export RAGIN_LLM_BASE_URL="$OPENWEIGHT_BASE"
  export RAGIN_LLM_API_KEY="$OPENWEIGHT_API_KEY"
  export RAGIN_LLM_MODEL="$M"
  python3 run_e30_openweight_panel.py "$M" 20 2718
done
