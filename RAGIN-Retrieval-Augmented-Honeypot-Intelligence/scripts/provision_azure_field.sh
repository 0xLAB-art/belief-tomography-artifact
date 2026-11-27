#!/usr/bin/env bash
# provision_azure_field.sh — one Azure FREE-TIER VM per field arm.
#
# Free-tier math (VERIFY in the portal before relying on it):
#   VM:      Standard_B1s (1 vCPU / 1 GiB) — 750 free hours/month for 12 months
#            on free-account subscriptions. NOTE: the 750 h is ONE POOL per
#            subscription, not per VM: 3 always-on B1s VMs burn 3 x 730 =
#            2190 h, so ~1460 h bill (~$15/mo at B1s list). Options: run the
#            field window inside the 30-day $200 credit, run arms in sequence,
#            or accept ~$26/mo all-in. B1s RAM (1 GiB) fits cowrie (~256 MB)
#            and the backends (measured gateway-served pipeline fits in
#            512 MB RSS).
#   Disk:    Premium SSD P6 64 GiB free for 12 months (use --os-disk-size-gb 64).
#   Public IP: Standard SKU static ≈ $3.6/mo each — the one REAL cost
#            (~$11/mo for three). Basic SKU is retired for new deployments.
#   Bandwidth: first 100 GB/mo free — far above honeypot egress needs
#            (egress is firewall-locked to the LLM provider :443 anyway).
#   Total:   ≈ $11/mo, $0 compute. If any arm's 750 h allowance is exceeded
#            (e.g. redeploy churn), B1s list ≈ $4–9/mo — still under budget.
#
# PREREQUISITES (all three are human gates):
#   1. Subscription ACTIVE (portal → Subscriptions → Reactivate). The script
#      probes writes first and fails honestly on ReadOnlyDisabledSubscription.
#   2. Tailscale auth keys created (3 single-use) — printed/rotated by you.
#   3. An SSH public key for the deploy user (~/.ssh/id_ed25519.pub).
#
# Ethics gates (docs/FIELD_ETHICS.md §2) are enforced by field_provision.sh
# AFTER compose up; this script only provisions the VM and prints next steps.
#
# Usage:
#   bash scripts/provision_azure_field.sh <arm> <location>   # arm: cowrie|vanilla|ragin
#   bash scripts/provision_azure_field.sh --probe            # write-probe only
#
# Per-arm results (VM name, public IP) are appended to
# results/azure_field_endpoints.json (git-ignored pattern: it is runtime
# state; the PRIVATE ops log holds the record of truth).

set -euo pipefail

SUB="${AZURE_SUBSCRIPTION_ID:-8110178a-4797-4682-88b1-3aa5db08b521}"
RG="ragin-field-rg"
ADMIN="azureuser"
SSH_KEY_FILE="${AZURE_FIELD_SSH_PUBKEY:-$HOME/.ssh/id_ed25519.pub}"
VM_SIZE="Standard_B1s"
IMAGE="Ubuntu2204"
DISK_GB=64

arm="${1:-}"; location="${2:-}"
fail() { echo "FAIL: $*" >&2; exit 1; }

# The write-probe needs a VALID location: with an empty -l, az group create
# fails for the wrong reason and the disabled-subscription guard below would
# never see the real error (false PROBE PASS).
if [ "$arm" = "--probe" ] && [ -z "$location" ]; then
  location="eastus2"
fi

az account set --subscription "$SUB" 2>/dev/null || fail "az login needed (az login; az account set --subscription $SUB)"

# ── Honest billing guard: probe a WRITE before anything else ────────────────
WRITE_PROBE="$(az group create -n "$RG-probe" -l "$location" 2>&1 || true)"
if echo "$WRITE_PROBE" | grep -qi "ReadOnlyDisabledSubscription\|DisabledSubscription"; then
  fail "SUBSCRIPTION DISABLED (billing hold). Fix in portal: Subscriptions -> 'Azure subscription 1' -> Reactivate, then re-run."
fi
az group delete -n "$RG-probe" --yes --no-wait >/dev/null 2>&1 || true
[ "$arm" = "--probe" ] && { echo "PROBE PASS: subscription accepts writes."; exit 0; }

case "$arm" in
  cowrie|vanilla|ragin) ;;
  *) fail "usage: $0 <cowrie|vanilla|ragin> <location>   (or --probe)";;
esac
[ -f "$SSH_KEY_FILE" ] || fail "SSH pubkey not found at $SSH_KEY_FILE"

# Distinct locations per arm are REQUIRED (separate IP prefixes; the study
# controls for endpoint/IP effects). Refuse to co-locate.
PREFIX_DIR="results/azure_field_prefixes"
mkdir -p "$PREFIX_DIR"
if [ -f "$PREFIX_DIR/$arm" ]; then
  fail "arm '$arm' already provisioned (see $PREFIX_DIR/$arm). Delete the VM first if intentional."
fi
for f in "$PREFIX_DIR"/*; do
  [ -e "$f" ] || continue
  prev="$(cat "$f")"
  if [ "$prev" = "$location" ]; then
    fail "location '$location' already used by arm '$(basename "$f")' — pick a DIFFERENT region (IP-prefix separation)."
  fi
done
echo "$location" > "$PREFIX_DIR/$arm"

VM="field-$arm"
SSH_KEY="$(cat "$SSH_KEY_FILE")"

# cloud-init with the deploy key templated in (no secrets beyond the pubkey)
CLOUDINIT="$(mktemp)"
sed "s|__RAGIN_DEPLOY_SSH_KEY__|$SSH_KEY|" scripts/cloudinit_field.yaml > "$CLOUDINIT"

echo "[+] Creating $VM ($VM_SIZE) in $location ..."
az vm create \
  --resource-group "$RG" --name "$VM" \
  --image "$IMAGE" --size "$VM_SIZE" \
  --admin-username "$ADMIN" \
  --ssh-key-values "$SSH_KEY_FILE" \
  --custom-data "$CLOUDINIT" \
  --os-disk-size-gb "$DISK_GB" \
  --public-ip-sku Standard \
  --public-ip-address-allocation static \
  -o json > "/tmp/$VM-create.json"

IP="$(jq -r '.publicIpAddress' "/tmp/$VM-create.json")"
echo "$IP" > "$PREFIX_DIR/$arm.ip"
rm -f "$CLOUDINIT" "/tmp/$VM-create.json"

# NSG: ONLY port 22 open (honeypot listener is inside Docker, mapped by
# compose); management moves behind Tailscale post-provision.
az vm open-port --resource-group "$RG" --name "$VM" --port 22 --priority 1001 >/dev/null

# Record for the ops log (NO secrets here).
jq -n --arg arm "$arm" --arg vm "$VM" --arg ip "$IP" --arg loc "$location" \
  '{arm:$arm, vm:$vm, public_ip:$ip, location:$loc, provisioned_at:(now|todate)}' \
  >> results/azure_field_endpoints.jsonl

cat <<EOF

[+] $VM up. Public IP: $IP  (recorded in results/azure_field_endpoints.jsonl)

NEXT (per docs/FIELD_LAUNCH_CHECKLIST.md §1 — ~20 min):
  1. Wait ~2 min for cloud-init, then from the tailnet/ssh:
     ssh $ADMIN@$IP 'cloud-init status --wait && tail -5 /opt/ragin/README.txt'
  2. Tailscale (YOU hold the keys):
     ssh $ADMIN@$IP 'curl -fsSL https://tailscale.com/install.sh | sh'
     ssh $ADMIN@$IP 'sudo tailscale up --ssh --authkey <YOUR_SINGLE_USE_KEY>'
  3. rsync repo:  rsync -az --exclude .git --exclude data/sessions ./ $ADMIN@$IP:/opt/ragin/repo/
  4. On the VM: cp .env.field.example .env.field  # fill per-arm values
     docker compose -f docker-compose.field.yml --env-file .env.field up -d <arm services>
     sudo bash scripts/field_provision.sh $arm
  5. Smoke gate:  .venv/bin/python scripts/field_smoke_ssh.py --host $IP --arm $arm
EOF
