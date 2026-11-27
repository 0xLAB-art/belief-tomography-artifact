"""Lane triage: find a working apmix/LLM lane across the project's env files.

Prints ONLY lane labels and HTTP outcomes — never key values or full URLs.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "RAGIN-Retrieval-Augmented-Honeypot-Intelligence"
ENV_FILES = [ROOT / ".env", ROOT / "run" / "server_v2.env"]


def load_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def ping(base: str, key: str, model: str) -> str:
    """Return 'OK', 'HTTP <code>', or exception type name."""
    if not (base and key and model):
        return "SKIP (incomplete)"
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": "ping"}],
                       "max_tokens": 5}).encode()
    req = urllib.request.Request(
        f"{base.rstrip('/')}/chat/completions", data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
        n = len(data.get("choices", []))
        return f"OK (choices={n})"
    except urllib.error.HTTPError as e:
        return f"HTTP {e.code}"
    except Exception as e:
        return type(e).__name__


def main() -> None:
    envs = {str(p): load_env(p) for p in ENV_FILES}
    main_env = envs[str(ENV_FILES[0])]
    srv_env = envs[str(ENV_FILES[1])]
    base_main = main_env.get("RAGIN_LLM_BASE_URL", "")
    base_srv = srv_env.get("RAGIN_LLM_BASE_URL", "") or srv_env.get("GATEWAY_URL", "")
    model_main = main_env.get("RAGIN_LLM_MODEL", "")
    model_srv = srv_env.get("RAGIN_LLM_MODEL", "") or srv_env.get("RAGIN_DON_MODEL", "")

    lanes = [
        ("L1 main.env RAGIN_LLM_*", base_main, main_env.get("RAGIN_LLM_API_KEY", ""), model_main),
        ("L2 main.env base+RAGIN_API_KEY", base_main, main_env.get("RAGIN_API_KEY", ""), model_main),
        ("L3 main.env base+API_KEY", base_main, main_env.get("API_KEY", ""), model_main),
        ("L4 server_v2 RAGIN_LLM_*", base_srv, srv_env.get("RAGIN_LLM_API_KEY", ""), model_srv),
        ("L5 server_v2 GW+API_KEY", base_srv, srv_env.get("API_KEY", ""), model_srv),
        ("L6 main.env OPENROUTER", "https://openrouter.ai/api/v1", main_env.get("OPENROUTER_API_KEY", ""), "openai/gpt-4o-mini"),
        ("L7 server_v2 OPENROUTER", "https://openrouter.ai/api/v1", srv_env.get("OPENROUTER_API_KEY", ""), "openai/gpt-4o-mini"),
    ]
    for label, base, key, model in lanes:
        print(f"{label:34s} -> {ping(base, key, model)}")


if __name__ == "__main__":
    main()
