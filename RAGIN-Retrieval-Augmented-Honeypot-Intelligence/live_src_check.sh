#!/bin/bash
set -euo pipefail
PROJECT_DIR="/home/elaref/Documents/research/ragin/RAGIN-Retrieval-Augmented-Honeypot-Intelligence"
cd "$PROJECT_DIR"
if [[ ! -f .venv/bin/python ]]; then
  echo "$(date -Iseconds) .venv/bin/python missing" >> /tmp/ragin_live_src_check.log
  exit 0
fi
if ! pgrep -f "uvicorn server_v2" >/dev/null; then
  echo "$(date -Iseconds) uvicorn not running" >> /tmp/ragin_live_src_check.log
  exit 0
fi
HASH_FILE="$PROJECT_DIR/.runtime/serve_hash.txt"
if [[ ! -s "$HASH_FILE" ]]; then
  echo "$(date -Iseconds) serve_hash.txt empty/missing" >> /tmp/ragin_live_src_check.log
  exit 0
fi
STORED=$(tr -d "[:space:]" < "$HASH_FILE")
if [[ -z "$STORED" ]]; then
  echo "$(date -Iseconds) stored hash empty" >> /tmp/ragin_live_src_check.log
  exit 0
fi
NOW=$(.venv/bin/python - "$STORED" <<'PY'
import hashlib, json, sys
from urllib.request import Request, urlopen
base="http://127.0.0.1:8731"
stored=sys.argv[1]
cases=[
  ("id -un", "webapp"),
  ("sudo -n cat /etc/shadow", None),
  ("aws sts get-caller-identity --output text", "169.254.169.254"),
]
out=[]
for cmd,needle in cases:
    try:
        req=Request(f"{base}/v1/chat/completions",
            data=json.dumps({"model":"gpt-3.5-turbo","messages":[{"role":"user","content":cmd}],"max_tokens":256}).encode(),
            headers={"Content-Type":"application/json"})
        with urlopen(req,timeout=20) as r:
            content=r.read()
        py=content.decode()
        now=hashlib.sha256(py.encode()).hexdigest()
        verdict="ok" if now==stored else "MISMATCH"
        fail=""
        if verdict!="ok":
            fail=f" stored={stored} now={now}"
        out.append(f"{cmd}\t{stored}\t{now}\t{verdict}{fail}" + (f"\tneedle={needle} present={(needle in py)}" if needle else ""))
    except Exception as e:
        out.append(f"{cmd}\t{stored}\tERR\tEXC\t{str(e)}")
print("\n".join(out))
PY
if [[ "$NOW" != "$STORED" ]]; then
  echo "$(date -Iseconds) HASH MISMATCH src=${STORED} live=${NOW}" >> /tmp/ragin_live_src_check.log
fi
