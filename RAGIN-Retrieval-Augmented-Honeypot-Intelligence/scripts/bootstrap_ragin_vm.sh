#!/usr/bin/env bash
# =============================================================================
# RAGIN — in-VM bootstrap (run on the VM: sudo bash scripts/bootstrap_ragin_vm.sh)
# Code is expected at /opt/ragin (deployed via rsync), env at /etc/ragin.env.
# Cloud-init already created swap + docker; this script is idempotent fallback.
# =============================================================================
set -euo pipefail

log() { printf '\033[1;34m[bootstrap]\033[0m %s\n' "$*"; }

REPO_DIR="/opt/ragin"
[[ -d "$REPO_DIR/ragin" ]] || { log "FATAL: $REPO_DIR/ragin missing — run scripts/deploy_azure_free_vms.sh (rsync flow) first"; exit 1; }
cd "$REPO_DIR"

# --- 1. Swap fallback (cloud-init normally did this) ---------------------------
if ! swapon --show=NAME | grep -q swapfile; then
  log "Creating 2 GB swap (cloud-init fallback)"
  fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile >/dev/null && swapon /swapfile
  grep -q swapfile /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

# --- 2. Docker fallback ---------------------------------------------------------
command -v docker >/dev/null 2>&1 || { curl -fsSL https://get.docker.com | sh; }
systemctl enable --now docker >/dev/null 2>&1 || true

# --- 3. Env ---------------------------------------------------------------------
if [[ ! -f /etc/ragin.env ]]; then
  log "FATAL: /etc/ragin.env missing — deploy script pushes it, or create it with RAGIN_LLM_BASE_URL/RAGIN_LLM_API_KEY/RAGIN_API_KEY"
  exit 1
fi
set -a; source /etc/ragin.env; set +a
[[ "$RAGIN_LLM_API_KEY" == CHANGE_ME* ]] && log "WARNING: placeholder LLM key in /etc/ragin.env — LLM calls will fail"

# --- 4. Build + up ----------------------------------------------------------------
log "Building ragin-python:vm (slowest step — pip layer cached after first run)"
docker compose -f docker-compose.vm.yml build 2>&1 | tail -2

if [[ "${COMPOSE_WITH_COWRIE:-0}" == "1" ]]; then
  log "Starting stack WITH cowrie"
  docker compose -f docker-compose.vm.yml -f docker-compose.vm.cowrie.yml up -d 2>&1 | tail -3
else
  log "Starting core stack"
  docker compose -f docker-compose.vm.yml up -d 2>&1 | tail -3
fi

# --- 5. Health ----------------------------------------------------------------------
sleep 12
FAIL=0
for svc in 8081:chrollo 8082:don 8083:hisoka; do
  port="${svc%%:*}"; name="${svc##*:}"
  if curl -fsS --max-time 5 "http://localhost:$port/health" >/dev/null 2>&1; then
    log "OK: $name (:$port)"
  else
    log "UNHEALTHY: $name (:$port) — logs: docker compose -f docker-compose.vm.yml logs $name"
    FAIL=1
  fi
done
if [[ "${COMPOSE_WITH_COWRIE:-0}" == "1" ]] && nc -zvw2 localhost 2222 >/dev/null 2>&1; then
  log "OK: cowrie (:2222)"
else
  [[ "${COMPOSE_WITH_COWRIE:-0}" == "1" ]] && { log "UNHEALTHY: cowrie"; FAIL=1; }
fi

log "Done. Free-tier discipline: 750 h/mo per VM, 15 GB egress — both fine for eval duty."
exit $FAIL
