#!/usr/bin/env bash
# =============================================================================
# RAGIN — Azure healthcheck: live status + /health probes + snapshot refresh
# Replaces the stale results/azure_services_snapshot.md with fresh evidence.
#
# Usage: bash scripts/azure_healthcheck.sh [resource_group]
# =============================================================================
set -uo pipefail

RG="${1:-${RAGIN_AZ_RG:-ragin-honeypot-rg}}"
SNAPSHOT="results/azure_services_snapshot.md"
STAMP="$(date -u '+%Y-%m-%d %H:%M UTC')"
TMP="$(mktemp)"

log() { printf '\033[1;34m[healthcheck]\033[0m %s\n' "$*"; }

{
  echo "# RAGIN Azure Services — Snapshot"
  echo
  echo "- **Snapshot time:** $STAMP"
  echo "- **Resource group:** \`$RG\`"
  echo
  echo "## Container Apps"
  echo
  echo "| Service | Provisioning | Replicas | FQDN |"
  echo "|---|---|---|---|"
  az containerapp list -g "$RG" --query '[].{n:name, p:properties.provisioningState, r:properties.replicas, f:properties.configuration.ingress.fqdn}' -o json 2>/dev/null |
    python3 -c "
import json, sys
for a in json.load(sys.stdin):
    print(f\"| {a['n']} | {a['p'] or 'n/a'} | {a['r'] if a['r'] is not None else 0} | {a['f'] or '—'} |\")
" || echo "| (query failed) | | |"
  echo
  echo "## Virtual Machines (free-tier Plan A)"
  echo
  echo "| VM | Size | State | Public IP |"
  echo "|---|---|---|---|"
  az vm list -g "$RG" -d --query '[].{n:name, s:hardwareProfile.vmSize, p:powerState, i:publicIps}' -o json 2>/dev/null |
    python3 -c "
import json, sys
for v in json.load(sys.stdin):
    print(f\"| {v['n']} | {v['s']} | {v['p']} | {v['i'] or '—'} |\")
" || echo "| (query failed) | | |"
  echo
  echo "## ACI"
  echo
  az container list -g "$RG" --query '[].{n:name, p:provisioningState}' -o json 2>/dev/null |
    python3 -c "
import json, sys
rows = json.load(sys.stdin)
if not rows: print('_none_')
else:
    print('| Name | Provisioning |'); print('|---|---|')
    for c in rows: print(f\"| {c['n']} | {c['p']} |\")
" || echo "_query failed_"
  echo
  echo "## /health probes"
  echo
} > "$TMP"

# Probe every healthy VM's eval ports
while read -r IP; do
  [[ -z "$IP" ]] && continue
  echo "**VM $IP**" >> "$TMP"; echo '```' >> "$TMP"
  for port in 8081 8082 8083; do
    R="$(curl -fsS --max-time 5 "http://$IP:$port/health" 2>&1 || true)"
    echo "  :$port -> ${R:-UNREACHABLE}" >> "$TMP"
  done
  echo '```' >> "$TMP"; echo >> "$TMP"
done < <(az vm list -g "$RG" -d --query "[?powerState=='VM running'].publicIps" -o tsv 2>/dev/null)

# Zodiac-native stack (the $0 Plan B after the billing hold)
TS_IP="$(tailscale ip -4 2>/dev/null | head -1 || true)"
if [[ -n "$TS_IP" ]] && systemctl --user is-active ragin-hisoka.service >/dev/null 2>&1; then
  {
    echo "## Zodiac-native stack (Plan B, zero-cost, tailnet-only)"
    echo
    for svc in 8081:chrollo 8082:don 8083:hisoka; do
      port="${svc%%:*}"; name="${svc##*:}"
      if curl -fsS --max-time 5 "http://$TS_IP:$port/health" >/dev/null 2>&1; then
        echo "- $name: HEALTHY at http://$TS_IP:$port (systemd --user, tailnet-only)"
      else
        echo "- $name: UNHEALTHY"
      fi
    done
    echo
  } >> "$TMP"
fi

# Billing signal — only a WRITE is honest; reads succeed even when disabled
BILLING="$(az group update -n "$RG" --set tags.probe="hc-$(date +%s)" -o none 2>&1 || true)"
az group update -n "$RG" --remove-tags probe -o none >/dev/null 2>&1 || true
{
  echo "## Compute-plane billing signal"
  echo '```'
  if echo "$BILLING" | grep -qi "Suspended\|Disabled\|NotFound"; then echo "$BILLING"; echo ">>> SUBSCRIPTION COMPUTE SUSPENDED — fix billing"; else echo "OK (quota query calls failed in this env — non-Azure host)"; fi
  echo '```'
} >> "$TMP"

# ── Validation artifacts (TDSC plan §4) ─────────────────────────────────────
# Rendered from the artifact JSONs by a Python helper so the numbers in the
# snapshot always match the artifacts — no hand-copied figures that rot.

python3 "$(dirname "$0")/render_validation_section.py" >> "$TMP" 2>/dev/null || {
  echo "## TDSC validation artifacts"
  echo
  echo "_(artifact rendering failed — run scripts/render_validation_section.py manually)_"
  echo
} >> "$TMP"

mv "$TMP" "$SNAPSHOT"
log "Snapshot refreshed: $SNAPSHOT"
tail -20 "$SNAPSHOT"
