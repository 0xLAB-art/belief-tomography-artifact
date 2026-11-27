#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="/home/elaref/Documents/research/ragin/RAGIN-Retrieval-Augmented-Honeypot-Intelligence"
VENV="$PROJECT_DIR/.venv"
OPENCODE_BIN="/home/elaref/.opencode/bin/opencode"
OPENCODE_SAFE_CONFIG="$PROJECT_DIR/scripts/opencode_cli_bridge_safe_config.json"
export PROJECT_DIR VENV OPENCODE_BIN OPENCODE_SAFE_CONFIG

echo "killing any prior 8731"
sudo fuser -k 8731/tcp 2>/dev/null || true
sleep 1

echo "starting opencode proxy daemon"
env \
  VENV="$VENV" \
  OPENCODE_BIN="$OPENCODE_BIN" \
  OPENCODE_SAFE_CONFIG="$OPENCODE_SAFE_CONFIG" \
  OPENCODE_ALLOWED_MODELS="opencode/space-bunny-free" \
  OPENCODE_PROXY_TIMEOUT_S=90 \
  "$VENV/bin/python" -u "$PROJECT_DIR/scripts/opencode_proxy.py" \
  >/tmp/ragin-opencode-proxy.out 2>/tmp/ragin-opencode-proxy.err &
PPID=$!
echo "proxy pid=$PPID"

echo "waiting for proxy health"
for i in $(seq 1 30); do
  if curl -sS -m 8 http://127.0.0.1:8731/health >/dev/null 2>&1; then
    echo "proxy-health-ok after ${i}s"; break
  fi
  sleep 1
done

echo "=== proxy /health ==="
curl -sS -m 15 http://127.0.0.1:8731/health | sed -n '1,220p'
echo
echo "=== proxy /v1/models ==="
curl -sS -m 15 http://127.0.0.1:8731/v1/models | sed -n '1,220p'
echo

echo "=== proxy direct completion request body ==="
printf '{"model":"opencode/space-bunny-free","messages":[{"role":"system","content":"You are a text-only completion backend. Return only the final assistant response text, no commentary."},{"role":"user","content":"echo PROXY_WIRE_PROOF_DIRECT"}],"max_tokens":64,"temperature":0.0}' >/tmp/ragin_proxy_completion_req.json
cat /tmp/ragin_proxy_completion_req.json
echo

echo "=== proxy direct completion ==="
curl -sS -m 90 -D /tmp/ragin_proxy_completion_headers.txt \
  -H "Content-Type: application/json" \
  -X POST -d @/tmp/ragin_proxy_completion_req.json \
  http://127.0.0.1:8731/v1/chat/completions \
  -o /tmp/ragin_proxy_completion_resp.json
echo "curl_exit=$?"
echo "=== proxy response headers ==="
cat /tmp/ragin_proxy_completion_headers.txt | sed -n '1,220p'
echo
echo "=== proxy response body ==="
cat /tmp/ragin_proxy_completion_resp.json | sed -n '1,220p'

echo "=== proxy log tail ==="
tail -n 30 /tmp/ragin-opencode-proxy.err 2>/dev/null | sed -n '1,120p'
