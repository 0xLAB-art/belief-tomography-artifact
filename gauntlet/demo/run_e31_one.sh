#!/bin/bash
# E31 single-model wrapper (one process per model; arms are independent).
set -a
source /home/elaref/.config/ragin/openweight.env
set +a
export TOMO_PATH=/nonexistent-tomography-env
export LLM_TARGET_TIMEOUT=60
export LLM_TARGET_MAX_OUTPUT_TOKENS=1024
M="$1"
export RAGIN_LLM_BASE_URL="$OPENWEIGHT_BASE"
export RAGIN_LLM_API_KEY="$OPENWEIGHT_API_KEY"
export RAGIN_LLM_MODEL="$M"
python3 run_e30_openweight_panel.py "$M" 20 2718 E31
