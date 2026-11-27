#!/usr/bin/env bash
set -euo pipefail
echo "SCRIPT: launching child pid soon"
"$VENV/bin/python" -u -m ragin.server_v2 --mode pipeline --port 8083 >/tmp/ragin-server-v2-8083.log 2>/tmp/ragin-server-v2-8083-err.log &
PID=$!
echo "SCRIPT: child pid=$PID"
sleep 2
if kill -0 "$PID" 2>/dev/null; then
  echo "SCRIPT: child still alive"
else
  echo "SCRIPT: child already gone"
fi
wait "$PID" || true
echo "SCRIPT: child exited rc=$?"
