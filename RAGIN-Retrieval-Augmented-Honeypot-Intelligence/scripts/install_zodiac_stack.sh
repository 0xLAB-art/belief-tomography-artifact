#!/usr/bin/env bash
# =============================================================================
# RAGIN — zodiac-native stack (the $0 "private cloud")
#
# Novel solution to the Azure billing hold: the researcher's own workstation
# IS the infrastructure. 12 cores / 15 GB RAM (20x the planned free VM),
# native redis, and Tailscale already joined — services bind to the tailnet
# IP only, so nothing is exposed to the internet and nothing costs money.
#
#   hisoka  : http://REDACTED_OPERATOR_HOST:8083   (deception endpoint, public paths)
#   don     : http://REDACTED_OPERATOR_HOST:8082   (X-API-Key required)
#   chrollo : http://REDACTED_OPERATOR_HOST:8081   (X-API-Key required)
#
# User services (NOT system scope): no sudo needed beyond the tailscale group.
# Idempotent: safe to re-run; systemd units are overwritten in place.
# =============================================================================
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$PROJECT_DIR/.venv"
TS_IP="$(tailscale ip -4 2>/dev/null | head -1 || true)"
SERVICE_USER="${SUDO_USER:-$USER}"

[[ -n "$TS_IP" ]] || { echo "[FATAL] tailscale not up — run: sudo tailscale up"; exit 1; }
[[ -x "$VENV/bin/python" ]] || { echo "[FATAL] venv missing at $VENV"; exit 1; }

# --- env for the services (from project .env, plus bind host) -------------------
# NOTE: ragin/server.py reads API_KEY (not RAGIN_API_KEY) for auth — map it.
ENV_FILE="$PROJECT_DIR/.env.ragin-stack"
{
  grep -E "^(RAGIN_LLM_BASE_URL|RAGIN_LLM_API_KEY|RAGIN_DON_MODEL|RAGIN_HISOKA_MODEL|RAGIN_HISOKA_TIMEOUT)=" "$PROJECT_DIR/.env" || true
  API_KEY_VAL="$(grep -E '^API_KEY=' "$PROJECT_DIR/.env" | cut -d= -f2-)"
  [[ -n "$API_KEY_VAL" ]] || API_KEY_VAL="$(grep -E '^RAGIN_API_KEY=' "$PROJECT_DIR/.env" | cut -d= -f2-)"
  echo "API_KEY=$API_KEY_VAL"
  echo "RAGIN_BIND_HOST=$TS_IP"
  echo "RAGIN_LOG_LEVEL=INFO"
} | sort -u > "$ENV_FILE"
chmod 600 "$ENV_FILE"
echo "[ok] env file: $ENV_FILE"

# --- redis: reuse the system instance -------------------------------------------
if [[ "$(redis-cli ping 2>/dev/null || true)" == "PONG" ]]; then
  echo "[ok] redis already running (system service)"
else
  echo "[setup] starting redis"
  sudo systemctl enable --now redis-server >/dev/null 2>&1 || sudo systemctl enable --now redis >/dev/null 2>&1
fi

# --- systemd user units -----------------------------------------------------------
UNIT_DIR="$HOME/.config/systemd/user"
mkdir -p "$UNIT_DIR"
if ! id -nG "$SERVICE_USER" | grep -qw tailscale; then
  echo "[setup] adding $SERVICE_USER to tailscale group (bind <1024 not needed; ports are 808x)"
fi

make_unit() {
  local name="$1" port="$2" component="$3"
  cat > "$UNIT_DIR/ragin-${name}.service" <<EOF
[Unit]
Description=RAGIN ${component} component (zodiac-native, tailnet-only)
After=network-online.target redis-server.service
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=$PROJECT_DIR
EnvironmentFile=$ENV_FILE
ExecStart=$VENV/bin/python -m ragin.server --component ${component} --port ${port}
Restart=on-failure
RestartSec=5
# 1 GB VM plan said 512MB/component; zodiac has 15 GB — cap generously anyway
MemoryMax=1500M
MemoryHigh=1200M

[Install]
WantedBy=default.target
EOF
}

make_unit chrollo 8081 chrollo
make_unit don     8082 don
make_unit hisoka  8083 hisoka

systemctl --user daemon-reload
systemctl --user enable --now ragin-chrollo.service ragin-don.service ragin-hisoka.service

# --- linger: keep user services alive after logout ---------------------------------
sudo loginctl enable-linger "$SERVICE_USER" 2>/dev/null || loginctl enable-linger "$SERVICE_USER" 2>/dev/null || echo "[warn] linger not enabled — services stop at logout"

# --- health ---------------------------------------------------------------------------
sleep 6
FAIL=0
for svc in 8081:chrollo 8082:don 8083:hisoka; do
  port="${svc%%:*}"; name="${svc##*:}"
  if curl -fsS --max-time 5 "http://$TS_IP:$port/health" >/dev/null 2>&1; then
    echo "[ok] $name healthy at http://$TS_IP:$port"
  else
    echo "[FAIL] $name — logs: journalctl --user -u ragin-${name}.service -n 30"
    FAIL=1
  fi
done

cat <<EOF

=============================================================================
  RAGIN zodiac-native stack: $([ $FAIL -eq 0 ] && echo LIVE || echo PARTIALLY UP)
    tailnet address : $TS_IP (zodiac)  — reachable from your tailnet only
    hisoka          : http://$TS_IP:8083  (/api/deceive, /api/lure, /v1/chat/completions)
    don             : http://$TS_IP:8082  (/api/analyze — X-API-Key)
    chrollo         : http://$TS_IP:8081  (/api/classify — X-API-Key)
    redis           : localhost:6379 (shared with local dev)

  Eval wiring (add to .env):
    RAGIN_HISOKA_URL=http://$TS_IP:8083
    RAGIN_DON_URL=http://$TS_IP:8082
    RAGIN_CHROLLO_URL=http://$TS_IP:8081

  Ops:
    systemctl --user status|restart|stop ragin-{chrollo,don,hisoka}
    journalctl --user -u ragin-hisoka.service -f
    bash scripts/azure_healthcheck.sh   (snapshot doc)
=============================================================================
EOF
exit $FAIL
