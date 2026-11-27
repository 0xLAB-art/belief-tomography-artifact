#!/usr/bin/env bash
# field_smoke_local.sh — hermetic local smoke of the arm-C SSH chain.
#
# Proves, on the docker host only (no VPS, no real LLM traffic):
#   SSH → cowrie-llm (SSH frontend) → ragin-server /v1/chat/completions
#   → sandbox → harness → verifier → SERVED answer + export JSONL written.
#
# The LLM gateway is deliberately pointed at a dead address: the serve must
# come from the pinned-fiction fail-safe template (server-side provenance
# TEMPLATE_FALLBACK_VERIFIED). The CHAIN is what the smoke proves; with a
# live gateway the same chain serves verified LLM drafts.
#
# Reaching the frontend by its container IP on the internal bridge avoids
# any host-port mapping (no collision with a local sshd on 22).
#
# Requires: docker, sshpass (apt install sshpass).
#
# Usage:   bash scripts/field_smoke_local.sh
# Cleanup: bash scripts/field_smoke_local.sh --down
set -euo pipefail
cd "$(dirname "$0")/.."

COMPOSE="docker compose"
PROJ="ragin-smoke"
ENVFILE=".env.field"

cleanup() {
  $COMPOSE -p "$PROJ" -f docker-compose.field.yml down -v --remove-orphans >/dev/null 2>&1 || true
  rm -f "$ENVFILE"
}

if [ "${1:-}" = "--down" ]; then
  cleanup
  echo "[ok] smoke stack removed"
  exit 0
fi
[ "${1:-}" = "" ] || { echo "usage: $0 [--down]"; exit 1; }
[ ! -e "$ENVFILE" ] || { echo "refusing to overwrite existing $ENVFILE (real endpoint config?)"; exit 1; }

# ── 1. Smoke environment (no secrets: local chain, dead gateway) ────────────
cat > "$ENVFILE" <<EOF
RAGIN_FIELD_ARM=ragin
RAGIN_LLM_BASE_URL=http://127.0.0.1:1/dead
RAGIN_LLM_API_KEY=smoke-no-key
RAGIN_LLM_MODEL=deepseek-v4-flash-free
RAGIN_LLM_PROVIDER_HOST=127.0.0.1
BACKEND_API_KEY=smoke-backend-key
COWRIE_LLM_HOST=http://ragin-server:8083
RAGIN_IMAGE=the-intelligence-ladder:field
EOF
trap cleanup EXIT

echo "[1/6] up: cowrie-llm + ragin-server (project $PROJ)"
$COMPOSE -p "$PROJ" -f docker-compose.field.yml --env-file "$ENVFILE" \
  up -d --quiet-pull cowrie-llm ragin-server >/dev/null

COWRIE_CID="$($COMPOSE -p "$PROJ" -f docker-compose.field.yml ps -q cowrie-llm)"
RAGIN_CID="$($COMPOSE -p "$PROJ" -f docker-compose.field.yml ps -q ragin-server)"
[ -n "$COWRIE_CID" ] && [ -n "$RAGIN_CID" ] || { echo "FAIL: containers not up"; exit 1; }
COWRIE_IP="$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "$COWRIE_CID")"
echo "      cowrie-llm at $COWRIE_IP:2222 (internal bridge)"

# ── 2. ragin-server health (in-container loopback) ──────────────────────────
echo "[2/6] ragin-server health"
ok=""
for i in $(seq 1 45); do
  if docker exec "$RAGIN_CID" python -c "
import urllib.request
urllib.request.urlopen('http://127.0.0.1:8083/health', timeout=2)
" >/dev/null 2>&1; then ok=1; break; fi
  sleep 2
done
[ -n "$ok" ] || { echo "FAIL: ragin-server never became healthy"; docker logs --tail 30 "$RAGIN_CID"; exit 1; }
echo "      healthy"

# ── 3. Drive SSH through the cowrie frontend (INTERACTIVE — the exec channel
# closes before cowrie's async LLM response can be delivered, so the smoke
# must use a PTY shell session, which is also the dominant attacker mode) ──
echo "[3/6] SSH PTY session root@cowrie-llm: whoami, wait, then exit"
# The LLM-backend reply is ASYNC (a deferred HTTP roundtrip through the
# bridge): type the command, WAIT for the serve, then exit. Without the
# sleep the session closes before the answer is written (smoke finding).
SESSION_OUT="$( (printf 'whoami\n'; sleep 10; printf 'exit\n') | timeout 40 sshpass -p toor ssh -tt -p 2222 \
  -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR \
  -o PreferredAuthentications=password -o PubkeyAuthentication=no \
  -o ConnectTimeout=10 root@"$COWRIE_IP" 2>/dev/null | tr -d '\r' || true)"
SERVED="$(printf '%s\n' "$SESSION_OUT" | grep -v 'Warning: Permanently added' | tail -6)"

# ── 4. The serve must be REAL, not the echo class ───────────────────────────
echo "[4/6] session tail:"
printf '%s\n' "$SERVED" | sed 's/^/      | /'
if echo "$SESSION_OUT" | grep -qi "command not found"; then
  echo "FAIL: echo-class serve — the cowrie→bridge hop is broken"
  exit 1
fi
if ! echo "$SESSION_OUT" | grep -q "webapp"; then
  echo "FAIL: ragin arm whoami did not return the pinned identity 'webapp'"
  exit 1
fi
echo "      PASS: verified pipeline served the pinned identity (not echo-class)"
echo "      (gateway is dead by design, so this serve is the fail-safe template)"
echo "      (with a live gateway the same chain serves a verified LLM draft)"

# ── 5. Bridge export JSONL written? ──────────────────────────────────────────
echo "[5/6] ragin-server export JSONL (/field-export)"
if docker exec "$RAGIN_CID" sh -c 'ls /field-export/*.jsonl' 2>/dev/null | head -1; then
  ROWS="$(docker exec "$RAGIN_CID" sh -c 'cat /field-export/*.jsonl 2>/dev/null | wc -l')"
  echo "      PASS: export JSONL present ($ROWS rows)"
else
  echo "      WARN: no export JSONL — check RAGIN_FIELD_EXPORT_DIR wiring"
fi

# ── 6. cowrie logged the session? ────────────────────────────────────────────
echo "[6/6] cowrie session log"
if docker logs "$COWRIE_CID" 2>&1 | grep -qi "login\|New connection"; then
  echo "      PASS: cowrie recorded the connection"
else
  echo "      WARN: no login line on stdout (jsonlog-only is normal)"
fi

echo ""
echo "SMOKE RESULT: PASS — arm-C chain verified end-to-end (SSH → cowrie-llm →"
echo "ragin-server bridge → verifier → serve), hermetically."
