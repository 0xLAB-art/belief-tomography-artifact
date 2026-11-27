#!/bin/bash
cd "$(dirname "$0")/.."
exec .venv/bin/python scripts/run_human_eval_parallel.py --output results/human_eval_full.json --workers 4
