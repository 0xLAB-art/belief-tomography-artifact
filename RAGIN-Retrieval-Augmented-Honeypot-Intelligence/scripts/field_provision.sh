#!/usr/bin/env bash
# Field endpoint provisioning — firewall, egress lockdown, log rotation, cron.
# Run ONCE per field VPS after `docker compose -f docker-compose.field.yml up -d`.
# Idempotent. Requires root. Design doc: docs/FIELD_ETHICS.md + docs/SP2027_SUBMISSION_PLAN.md
#
# Usage: sudo bash scripts/field_provision.sh [cowrie|vanilla|ragin]
set -euo pipefail

ARM="${1:?usage: field_provision.sh [cowrie|vanilla|ragin]}"
[[ "$ARM" =~ ^(cowrie|vanilla|ragin)$ ]] || { echo "arm must be cowrie|vanilla|ragin" >&2; exit 1; }

echo "[*] provisioning field endpoint: arm=$ARM host=$(hostname)"

# ── 1. Inbound firewall: ONLY the honeypot listener + tailscale ─────────
# Tailscale interface (tailscale0) stays fully open for management SSH.
# Everything else: default-drop inbound, established/related accepted.
if command -v ufw >/dev/null; then
  ufw --force reset >/dev/null
  ufw default deny incoming
  ufw default allow outgoing
  ufw allow in on tailscale0
  ufw allow 22/tcp    comment 'honeypot SSH listener (arm service port)'
  ufw --force enable
  echo "[+] ufw: default-deny inbound, honeypot 22/tcp + tailscale0 open"
else
  echo "[!] ufw not found — configure nftables/iptables manually (see docs/FIELD_ETHICS.md)"
fi

# ── 2. Egress lockdown for honeypot containers (DOCKER-USER chain) ──────
# Ethics requirement: the honeypot must have NO outbound attack capability.
# Containers may answer only via their own listening socket; outbound NEW
# connections from the honeypot containers are dropped. DNS stays permitted
# for the RAGIN arms' LLM provider (documented, allowlisted by IP below is
# intentionally not hardcoded — resolve provider IP at provision time).
iptables -C DOCKER-USER -m state --state ESTABLISHED,RELATED -j ACCEPT 2>/dev/null || \
  iptables -I DOCKER-USER 1 -m state --state ESTABLISHED,RELATED -j ACCEPT

if [ "$ARM" = "ragin" ] || [ "$ARM" = "vanilla" ]; then
  # LLM provider egress: resolve the provider host once at provision time.
  PROVIDER_HOST="${RAGIN_LLM_PROVIDER_HOST:-api.apmix.ai}"
  PROVIDER_IPS=$(getent hosts "$PROVIDER_HOST" | awk '{print $1}' | sort -u)
  for ip in $PROVIDER_IPS; do
    iptables -C DOCKER-USER -p tcp -d "$ip" --dport 443 -j ACCEPT 2>/dev/null || \
      iptables -I DOCKER-USER 2 -p tcp -d "$ip" --dport 443 -j ACCEPT
  done
  echo "[+] DOCKER-USER: egress allowlisted to ${PROVIDER_HOST} (${PROVIDER_IPS}) :443 only"
else
  echo "[+] DOCKER-USER: cowrie arm — no outbound exceptions"
fi

# Drop everything else outbound from the internal bridge.
iptables -C DOCKER-USER -o br+ -m state --state NEW -j DROP 2>/dev/null || \
  iptables -I DOCKER-USER 3 -o br+ -m state --state NEW -j DROP
echo "[+] DOCKER-USER: all other NEW outbound connections from honeypot nets dropped"

# ── 3. Docker log rotation already bounded by compose (50m x 30) ────────
# ── 4. Daily collection cron: 03:17 UTC, hashed-IP export off-host ─────
CRON_LINE="17 3 * * * cd $(pwd) && /usr/bin/env python3 scripts/collect_field_data.py --days 1 --outdir data/field/export >> data/field/collect.log 2>&1"
CRON_FILE=/etc/cron.d/ragin-field-collect
echo "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" > "$CRON_FILE"
echo "$CRON_LINE" >> "$CRON_FILE"
chmod 600 "$CRON_FILE"
echo "[+] cron: daily 03:17 UTC collection -> data/field/export (see collect_field_data.py --days 1)"

# ── 5. Record provenance of this endpoint ────────────────────────────────
cat > "data/field/${ARM}-endpoint.json" <<EOF
{
  "arm": "${ARM}",
  "provisioned_at": "$(date -Iseconds)",
  "hostname_fingerprint": "$(hostname | sha256sum | cut -c1-12)",
  "ufw_enabled": true,
  "egress": "$( [ "$ARM" = cowrie ] && echo none || echo "llm-provider-443-only" )",
  "public_listener": "22/tcp",
  "management": "tailscale0 only",
  "source_ip_policy": "hashed at collection; raw IPs never leave host"
}
EOF
echo "[+] endpoint provenance: data/field/${ARM}-endpoint.json"
echo "[*] done. Verify: ufw status && iptables -L DOCKER-USER -n --line-numbers"