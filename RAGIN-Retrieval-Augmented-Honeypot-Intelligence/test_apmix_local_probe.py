#!/usr/bin/env python3
import os, sys, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
env_file = ROOT / ".env"

env = dict(os.environ)
if env_file.is_file():
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()

print("Loaded RAGIN_LLM_BASE_URL=", env.get("RAGIN_LLM_BASE_URL"))
print("Loaded RAGIN_LLM_API_KEY=", env.get("RAGIN_LLM_API_KEY"))
print("Loaded RAGIN_LLM_MODEL=", env.get("RAGIN_LLM_MODEL"))
print("Loaded RAGIN_HISOKA_MODEL=", env.get("RAGIN_HISOKA_MODEL"))
print("Loaded RAGIN_GENERATION_CONTRACT=", env.get("RAGIN_GENERATION_CONTRACT"))
print("Loaded EVAL_MODEL=", env.get("EVAL_MODEL"))

sys.path.insert(0, str(ROOT))
from ragin.gateway.client import GatewayClient
from ragin.gateway.generation import resolve_generation_config

g = GatewayClient()
snap = g.generation_snapshot()
cfg = resolve_generation_config()
print("GatewayClient snapshot=", json.dumps(snap, indent=2, sort_keys=True))
print("Resolved config sha256=", cfg.config_sha256 if cfg else None)
