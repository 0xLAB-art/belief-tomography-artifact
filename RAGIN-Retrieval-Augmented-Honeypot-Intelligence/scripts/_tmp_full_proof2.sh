#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="/home/elaref/Documents/research/ragin/RAGIN-Retrieval-Augmented-Honeypot-Intelligence"
VENV="$PROJECT_DIR/.venv"
OPENCODE_BIN="/home/elaref/.opencode/bin/opencode"
OPENCODE_SAFE_CONFIG="$PROJECT_DIR/scripts/opencode_cli_bridge_safe_config.json"
API_KEY="$(grep -E '^API_KEY=' "$PROJECT_DIR/.env" | cut -d= -f2-)"
: "${API_KEY:?no API_KEY in .env}"
export PROJECT_DIR VENV OPENCODE_BIN OPENCODE_SAFE_CONFIG API_KEY
export RAGIN_BIND_HOST=127.0.0.1
export RAGIN_LOG_LEVEL=INFO
export PYTHONUNBUFFERED=1
export GATEWAY_URL=http://127.0.0.1:8731/v1
export OPENROUTER_API_KEY="$API_KEY"
export RAGIN_LLM_BASE_URL=http://127.0.0.1:8731/v1
export RAGIN_LLM_API_KEY="$API_KEY"
export RAGIN_LLM_MODEL=opencode/space-bunny-free
export RAGIN_HISOKA_MODEL=opencode/space-bunny-free
export RAGIN_HOST_FICTION_PATH=/tmp/ragin-cowrie-test/host_fiction.json
export RAGIN_HOST_FICTION=1
export RAGIN_HOST_FICTION_POLICY=per_session
export RAGIN_FAIL_CLOSED=1
export RAGIN_FIELD_EXPORT_DIR=/tmp/ragin-field-export
export OPENCODE_ALLOWED_MODELS=opencode/space-bunny-free
export OPENCODE_PROXY_TIMEOUT_S=90
mkdir -p "$RAGIN_FIELD_EXPORT_DIR"

echo "=== PHASE 0: kill prior listeners ==="
sudo fuser -k 8731/tcp 2>/dev/null || true
sudo fuser -k 8083/tcp 2>/dev/null || true
sleep 1

echo "=== PHASE 1: start opencode proxy daemon ==="
"$VENV/bin/python" -u "$PROJECT_DIR/scripts/opencode_proxy.py" \
  >/tmp/ragin-opencode-proxy.out 2>/tmp/ragin-opencode-proxy.err &
PROXY_PID=$!
echo "proxy pid=$PROXY_PID"
for i in $(seq 1 40); do
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

echo "=== PHASE 2: direct proxy completion (proves gateway alive + model match) ==="
printf '{"model":"opencode/space-bunny-free","messages":[{"role":"system","content":"You are a text-only completion backend. Return only the final assistant response text, no commentary."},{"role":"user","content":"echo PROOF_DIRECT"}],"max_tokens":64,"temperature":0.0}' >/tmp/ragin_proxy_completion_req.json
curl -sS -m 90 -D /tmp/ragin_proxy_completion_headers.txt \
  -H "Content-Type: application/json" \
  -X POST -d @/tmp/ragin_proxy_completion_req.json \
  http://127.0.0.1:8731/v1/chat/completions \
  -o /tmp/ragin_proxy_completion_resp.json
echo "direct_proxy_curl_exit=$?"
echo "=== direct proxy response headers ==="
cat /tmp/ragin_proxy_completion_headers.txt | sed -n '1,220p'
echo
echo "=== direct proxy response body ==="
cat /tmp/ragin_proxy_completion_resp.json | sed -n '1,220p'
echo

echo "=== PHASE 3: start authoritative pipeline daemon (with RAGIN_HISOKA_MODEL set) ==="
env \
  API_KEY="$API_KEY" \
  RAGIN_BIND_HOST="$RAGIN_BIND_HOST" \
  RAGIN_LOG_LEVEL="$RAGIN_LOG_LEVEL" \
  PYTHONUNBUFFERED="$PYTHONUNBUFFERED" \
  GATEWAY_URL="$GATEWAY_URL" \
  OPENROUTER_API_KEY="$OPENROUTER_API_KEY" \
  RAGIN_LLM_BASE_URL="$RAGIN_LLM_BASE_URL" \
  RAGIN_LLM_API_KEY="$RAGIN_LLM_API_KEY" \
  RAGIN_LLM_MODEL="$RAGIN_LLM_MODEL" \
  RAGIN_HISOKA_MODEL="$RAGIN_HISOKA_MODEL" \
  RAGIN_HOST_FICTION_PATH="$RAGIN_HOST_FICTION_PATH" \
  RAGIN_HOST_FICTION="$RAGIN_HOST_FICTION" \
  RAGIN_HOST_FICTION_POLICY="$RAGIN_HOST_FICTION_POLICY" \
  RAGIN_FAIL_CLOSED="$RAGIN_FAIL_CLOSED" \
  RAGIN_FIELD_EXPORT_DIR="$RAGIN_FIELD_EXPORT_DIR" \
  "$VENV/bin/python" -u -m ragin.server_v2 --mode pipeline --port 8083 \
  >/tmp/ragin-server-v2-8083.log 2>/tmp/ragin-server-v2-8083-err.log &
PIPE_PID=$!
echo "pipeline pid=$PIPE_PID"
for i in $(seq 1 40); do
  if curl -sS -m 8 http://127.0.0.1:8083/health >/dev/null 2>&1; then
    echo "pipeline-health-ok after ${i}s"; break
  fi
  sleep 1
done
echo "=== pipeline /health ==="
curl -sS -m 15 http://127.0.0.1:8083/health | sed -n '1,220p'
echo

echo "=== PHASE 4: pipeline completion (authoritative GENERATED_VERIFIED path) ==="
printf '{"model":"opencode/space-bunny-free","messages":[{"role":"system","content":"You are a Linux SSH honeypot shell. Return only the raw command output, no commentary."},{"role":"user","content":"echo PIPELINE_WIRE_PROOF"}],"max_tokens":64,"temperature":0.0}' >/tmp/ragin_pipeline_completion_req.json
curl -sS -m 120 -D /tmp/ragin_pipeline_completion_headers.txt \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -X POST -d @/tmp/ragin_pipeline_completion_req.json \
  http://127.0.0.1:8083/v1/chat/completions \
  -o /tmp/ragin_pipeline_completion_resp.json
echo "pipeline_curl_exit=$?"
echo "=== pipeline response headers ==="
cat /tmp/ragin_pipeline_completion_headers.txt | sed -n '1,220p'
echo
echo "=== pipeline response body ==="
cat /tmp/ragin_pipeline_completion_resp.json | sed -n '1,220p'
echo

echo "=== PHASE 5: logs (proxy + pipeline) ==="
echo "--- proxy log tail ---"
tail -n 15 /tmp/ragin-opencode-proxy.err 2>/dev/null | sed -n '1,60p'
echo "--- pipeline log tail ---"
tail -n 40 /tmp/ragin-server-v2-8083-err.log 2>/dev/null | sed -n '1,160p'
