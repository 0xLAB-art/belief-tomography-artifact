#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="/home/elaref/Documents/research/ragin/RAGIN-Retrieval-Augmented-Honeypot-Intelligence"
VENV="$PROJECT_DIR/.venv"
API_KEY="$(grep -E '^API_KEY=' "$PROJECT_DIR/.env" | cut -d= -f2-)"
: "${API_KEY:?no API_KEY in .env}"
export PROJECT_DIR VENV API_KEY
export RAGIN_BIND_HOST=127.0.0.1
export RAGIN_LOG_LEVEL=INFO
export PYTHONUNBUFFERED=1
export GATEWAY_URL=http://127.0.0.1:8731/v1
export OPENROUTER_API_KEY="$API_KEY"
export RAGIN_LLM_BASE_URL=http://127.0.0.1:8731/v1
export RAGIN_LLM_API_KEY="$API_KEY"
export RAGIN_LLM_MODEL=opencode/space-bunny-free
export RAGIN_HOST_FICTION_PATH=/tmp/ragin-cowrie-test/host_fiction.json
export RAGIN_HOST_FICTION=1
export RAGIN_HOST_FICTION_POLICY=per_session
export RAGIN_FAIL_CLOSED=1
export RAGIN_FIELD_EXPORT_DIR=/tmp/ragin-field-export
mkdir -p "$RAGIN_FIELD_EXPORT_DIR"

echo "killing any prior 8083"
sudo fuser -k 8083/tcp 2>/dev/null || true
sleep 1

echo "starting server daemon"
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
  RAGIN_HOST_FICTION_PATH="$RAGIN_HOST_FICTION_PATH" \
  RAGIN_HOST_FICTION="$RAGIN_HOST_FICTION" \
  RAGIN_HOST_FICTION_POLICY="$RAGIN_HOST_FICTION_POLICY" \
  RAGIN_FAIL_CLOSED="$RAGIN_FAIL_CLOSED" \
  RAGIN_FIELD_EXPORT_DIR="$RAGIN_FIELD_EXPORT_DIR" \
  "$VENV/bin/python" -u -m ragin.server_v2 --mode pipeline --port 8083 \
  >/tmp/ragin-server-v2-8083.log 2>/tmp/ragin-server-v2-8083-err.log &
SPID=$!
echo "server pid=$SPID"

echo "waiting for health probe"
for i in $(seq 1 40); do
  if curl -sS -m 8 http://127.0.0.1:8083/health >/dev/null 2>&1; then
    echo "health-ok after ${i}s"; break
  fi
  sleep 1
done

run_completion() {
  local label="$1"
  local body="$2"
  echo "=== $label request body ==="
  printf '%s' "$body" >/tmp/ragin_completion_req.json
  cat /tmp/ragin_completion_req.json
  echo
  echo "=== $label request ==="
  curl -sS -m 90 -D /tmp/ragin_completion_headers.json \
    -H "Authorization: Bearer $API_KEY" \
    -H "Content-Type: application/json" \
    -X POST -d @/tmp/ragin_completion_req.json \
    http://127.0.0.1:8083/v1/chat/completions \
    -o /tmp/ragin_completion_resp.json
  echo "curl_exit=$?"
  echo "=== $label response headers ==="
  cat /tmp/ragin_completion_headers.json | sed -n '1,220p'
  echo
  echo "=== $label response body ==="
  cat /tmp/ragin_completion_resp.json | sed -n '1,220p'
  echo
}

BODY1='{"model":"opencode/space-bunny-free","messages":[{"role":"system","content":"You are a Linux SSH honeypot shell. Return only the raw command output, no commentary."},{"role":"user","content":"echo RAGIN_WIRE_PROOF_FIRST"}],"max_tokens":64,"temperature":0.0}'
BODY2='{"model":"opencode/space-bunny-free","messages":[{"role":"system","content":"You are a Linux SSH honeypot shell. Return only the raw command output, no commentary."},{"role":"user","content":"echo RAGIN_WIRE_PROOF_SECOND"}],"max_tokens":64,"temperature":0.0}'

run_completion "FIRST" "$BODY1"
run_completion "SECOND" "$BODY2"

echo "=== server log tail ==="
tail -n 60 /tmp/ragin-server-v2-8083-err.log 2>/dev/null | sed -n '1,200p'
