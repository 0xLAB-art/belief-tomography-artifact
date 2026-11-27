#!/usr/bin/env bash
# =============================================================================
# RAGIN — Plan A IP-less deploy: Azure free-tier VM + Tailscale
#
# NOTE (2026-09-22): Plan A is DORMANT — the Azure subscription is in
# ReadOnlyDisabledSubscription state (billing hold). Deployment will fail at
# the billing guard below until the subscription is reactivated. The active
# stack is Plan B (zodiac, tailnet-only, $0): scripts/install_zodiac_stack.sh.
#
# 1. Billing guard (honest fail if subscription compute is suspended)
# 2. NSG with NO inbound rules (nothing exposed to the internet)
# 3. VM1 (B2ats v2, x86, 2vCPU/1GB, 64GB) — cloud-init: swap + docker + Tailscale
#    join (auth key from .env) -> VM reachable only inside your tailnet
# 4. rsync local repo -> /opt/ragin over Tailscale (newest code, no GitHub auth)
# 5. Remote bootstrap: build + compose up + health
#
# Result: hisoka/don/chrollo/cowrie reachable at the VM's 100.x.x.x address
# from zodiac (and your other tailnet devices) only.
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
[[ -f "$PROJECT_DIR/.env" ]] && { set -a; source "$PROJECT_DIR/.env"; set +a; }

RG="${RAGIN_AZ_RG:-ragin-honeypot-rg}"
LOCATION="${LOCATION:-eastus}"
SSH_USER="${SSH_USER:-azureuser}"
SSH_KEY="${SSH_KEY_PATH:-$HOME/.ssh/id_ed25519.pub}"
VM1_NAME="${VM1_NAME:-ragin-vm1}"
NSG_NAME="${NSG_NAME:-ragin-vm-nsg}"
TS_AUTHKEY="${RAGIN_TAILSCALE_AUTHKEY:-}"
VM1_SIZE="Standard_B2ats_v2"          # x86, 2 vCPU, 1 GB RAM — free 750h/mo, 12 mo
UBUNTU_X86="Canonical:ubuntu-24_04-lts:server:latest"

log()  { printf '\033[1;34m[freevms]\033[0m %s\n' "$*"; }
fail() { printf '\033[1;31m[freevms] ERROR:\033[0m %s\n' "$*" >&2; exit 1; }

command -v az >/dev/null || fail "az CLI not found"
command -v rsync >/dev/null || fail "rsync not found locally"
[[ -n "$TS_AUTHKEY" ]] || fail "RAGIN_TAILSCALE_AUTHKEY missing from .env"
az account show >/dev/null 2>&1 || fail "Not logged in: az login"

# --- 1. Billing guard ------------------------------------------------------------
# READ APIs succeed even on disabled subscriptions — the only honest test is a
# real WRITE. Probe at resource-group level (always exists after group create).
az group show -n "$RG" >/dev/null 2>&1 || az group create -n "$RG" -l "$LOCATION" >/dev/null 2>&1 || true
WRITE_PROBE="$(az group update -n "$RG" --set tags.probe="ragin-$(date +%s)" -o none 2>&1 || true)"
if echo "$WRITE_PROBE" | grep -qi "ReadOnlyDisabledSubscription\|DisabledSubscription\|ManagedClusterSuspended"; then
  fail "SUBSCRIPTION DISABLED (read-only billing hold). Fix: Azure Portal -> Subscriptions -> 'Azure subscription 1' -> Reactivate / add payment method. Then re-run this script."
fi
log "Billing OK — subscription accepts writes"
az network nsg show -g "$RG" -n "$NSG_NAME" >/dev/null 2>&1 || az network nsg create -g "$RG" -n "$NSG_NAME" -l "$LOCATION" >/dev/null
az network nsg update -g "$RG" -n "$NSG_NAME" --remove-tags probe -o none >/dev/null 2>&1 || true

az group show -n "$RG" >/dev/null 2>&1 || { log "Creating RG $RG"; az group create -n "$RG" -l "$LOCATION" >/dev/null; }

# --- 2. NSG: created but deliberately EMPTY of inbound rules -----------------------
if ! az network nsg show -g "$RG" -n "$NSG_NAME" >/dev/null 2>&1; then
  log "Creating NSG $NSG_NAME (no inbound rules — tailnet-only access)"
  az network nsg create -g "$RG" -n "$NSG_NAME" -l "$LOCATION" >/dev/null
fi

# --- 3. VM1: no public IP, cloud-init = swap + docker + tailscale join --------------
CLOUD_INIT="$PROJECT_DIR/.ragin_cloudinit.yaml"
cat > "$CLOUD_INIT" <<YAML
#cloud-config
package_update: true
swap:
  filename: /swapfile
  size: "2147483648"
packages: [docker.io, docker-compose-v2, rsync, curl]
runcmd:
  - systemctl enable --now docker
  - sysctl -w vm.swappiness=20
  - echo 'vm.swappiness=20' > /etc/sysctl.d/90-ragin-swap.conf
  - curl -fsSL https://tailscale.com/install.sh | sh
  - tailscale up --authkey="$TS_AUTHKEY" --hostname=ragin-vm1 --accept-routes
YAML

if ! az vm show -g "$RG" -n "$VM1_NAME" >/dev/null 2>&1; then
  log "Creating $VM1_NAME ($VM1_SIZE, 64 GB disk, NO public IP, cloud-init: swap+docker+tailscale)"
  az vm create \
    -g "$RG" -n "$VM1_NAME" \
    --image "$UBUNTU_X86" \
    --size "$VM1_SIZE" \
    --admin-username "$SSH_USER" \
    --ssh-key-values "$SSH_KEY" \
    --nsg "$NSG_NAME" \
    --public-ip-address "" \
    --os-disk-size-gb 64 \
    --storage-sku Premium_LRS \
    --custom-data "$CLOUD_INIT" \
    -o none
else
  log "VM $VM1_NAME exists — skipping create"
fi
rm -f "$CLOUD_INIT"

# --- 4. Resolve the VM's tailnet IP (via local tailscale status) --------------------
log "Waiting for VM to join the tailnet..."
TS_IP=""
for i in $(seq 1 30); do
  TS_IP="$(tailscale status 2>/dev/null | awk '$2 == "ragin-vm1" {print $1; exit}' || true)"
  [[ -n "$TS_IP" ]] && break
  sleep 10
done
[[ -n "$TS_IP" ]] || fail "VM never appeared in tailnet — check tailscale up logs: az vm run-command invoke -g $RG -n $VM1_NAME --command-id RunShellScript --scripts 'tailscale status'"
log "VM joined tailnet: ragin-vm1 = $TS_IP"

# --- 5. Wait for tailscale SSH path, then rsync --------------------------------------
for i in $(seq 1 24); do
  if ssh -o StrictHostKeyChecking=accept-new -o ConnectTimeout=5 -o BatchMode=yes \
       "$SSH_USER@$TS_IP" 'docker info >/dev/null 2>&1 && swapon --show=NAME | grep -q swapfile' 2>/dev/null; then
    log "VM ready (docker + swap)"; break
  fi
  [[ "$i" == "24" ]] && fail "VM not ready over tailnet after 4 min — ssh $SSH_USER@$TS_IP to debug"
  sleep 10
done

log "Rsyncing repo to VM:/opt/ragin (over tailnet)"
rsync -az --delete \
  --exclude '.venv' --exclude '.git' --exclude 'node_modules' \
  --exclude '__pycache__' --exclude 'results/' --exclude 'logs/' \
  --exclude '.env' --exclude 'graphify-out' \
  "$PROJECT_DIR"/ "$SSH_USER@$TS_IP:/opt/ragin/"

# --- 6. Ship env + bootstrap ----------------------------------------------------------
log "Pushing /etc/ragin.env (LLM + API keys from local .env)"
ssh "$SSH_USER@$TS_IP" "sudo tee /etc/ragin.env > /dev/null" < <(
  grep -E "^(RAGIN_LLM_BASE_URL|RAGIN_LLM_API_KEY|RAGIN_API_KEY|RAGIN_DON_MODEL|RAGIN_HISOKA_MODEL|RAGIN_HISOKA_TIMEOUT)=" "$PROJECT_DIR/.env" | sort -u
  echo "COMPOSE_WITH_COWRIE=1"
)
ssh "$SSH_USER@$TS_IP" "sudo chmod 600 /etc/ragin.env"

log "Running bootstrap on VM (build + up + health)"
ssh "$SSH_USER@$TS_IP" "cd /opt/ragin && sudo bash scripts/bootstrap_ragin_vm.sh"

cat <<EOF

=============================================================================
  RAGIN is LIVE (Plan A, IP-less) — cost: Azure free tier where eligible
    tailnet IP : $TS_IP  (ragin-vm1)
    hisoka     : http://$TS_IP:8083   <- deception endpoint
    don        : http://$TS_IP:8082
    chrollo    : http://$TS_IP:8081
    cowrie     : $TS_IP:2222/2223 (tailnet-only — no internet attackers)
  Eval scripts: point RAGIN_*_URL at the addresses above (run from zodiac).
  SSH:          ssh $SSH_USER@$TS_IP
  Healthcheck:  bash scripts/azure_healthcheck.sh
=============================================================================
EOF
