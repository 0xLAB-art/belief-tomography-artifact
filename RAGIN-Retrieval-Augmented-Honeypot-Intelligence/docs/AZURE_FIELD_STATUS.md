# Azure Field Endpoint Provisioning — Status & Runbook

**Date:** 2026-09-26 | **Session close 2026-09-29:** conversion to
pay-as-you-go instructed (trial exhausted — see update below); at session
close ARM still reported Disabled / FreeTrial / limit-On after ~10 min of
retries, so **no field VM exists yet**. Resume: `--probe` → three arms per
`docs/AZURE_TAILSCALE_WALKTHROUGH.md` → per-arm smoke gates.
**Decision (Q3):** user chose "check az containers first" — result below.

## Current state (verified from CLI)

| Item | Value |
|---|---|
| Subscription | `8110178a-4797-4682-88b1-3aa5db08b521` ("Azure subscription 1") |
| `az account show` (cached) | `state: Enabled` — **misleading**: local CLI cache |
| Backend write probe (`az container start`) | **`ReadOnlyDisabledSubscription`** — subscription still under billing/read-only hold |
| Existing container | `ragin-cowrie-hp` (eastus, 1 core/1.5 GB, Succeeded, **Stopped**), FQDN `raginhpew.eastus.azurecontainer.io`, ports 2222/2223 — port probe **times out** (stopped) |
| Resource groups | `ragin-honeypot-rg` (eastus), `rg-youseefhamdi329-8520` (qatarcentral) |
| CLI session | cleared by agent during debugging (`az account clear` was a mistake) — needs `az login` |

**Conclusion:** the subscription still requires **manual re-enable** in the
Azure portal (Cost Management → subscription → re-enable, or free-tier spend
limit reset). No CLI/API write will succeed until a human does that.

> **Click-by-click walkthrough:** see `docs/AZURE_TAILSCALE_WALKTHROUGH.md`
> (Phase A reactivation → Phase B Tailscale keys → Phase C provisioning →
> Phase D verification). It supersedes the CLI snippets below.

## What the user must do (5 minutes, portal only)

> **2026-09-29 update (from ARM, exact):** the subscription is a
> **free-trial** subscription (`quotaId: FreeTrial_2014-09-01`) with the
> **spending limit ON** and state **Disabled** — i.e. the trial credit or
> 30-day window is exhausted. For this quota type there is no plain
> "Reactivate" button: the re-enable path is **Upgrade/Convert to
> pay-as-you-go** on the subscription page, which removes the spend limit.
> Cost consequence: billing becomes real immediately after conversion
> (free-tier service allowances for the first 12 months still apply where
> eligible; static IPs bill from day 1 — see the walkthrough's budget
> note, ≈ $26/mo all-in for three always-on B1s arms).

1. Sign in at portal.azure.com → Subscriptions → "Azure subscription 1".
2. Follow the **Upgrade to pay-as-you-go** / conversion prompt on the
   disabled-subscription banner (requires a valid payment method).
3. Verify reactivation by reloading the subscription overview (state must be
   *Active* — not merely the CLI's cached "Enabled"), then re-run
   `bash scripts/provision_azure_field.sh --probe`.

## What is already automated once re-enabled

Everything is prepared; the re-enable is the only manual gate:

```bash
# 1. Re-authenticate (agent session was cleared)
az login
az account set --subscription 8110178a-4797-4682-88b1-3aa5db08b521

# 2. Probe write access (deploy_azure_free_vms.sh has an honest billing guard)
bash scripts/deploy_azure_free_vms.sh --dry-run

# 3a. Restart the historical Cowrie ACI (arm A) — it is Stopped but intact
az container start -g ragin-honeypot-rg -n ragin-cowrie-hp
az container show -g ragin-honeypot-rg -n ragin-cowrie-hp \
  --query "{state:instanceView.state, fqdn:ipAddress.fqdn, ip:ipAddress.ip}" -o json

# 3b. Provision arms B (vanilla-LLM) and C (RAGIN) per the field package:
#   - docker-compose.field.yml (three-arm layout, one arm per endpoint)
#   - scripts/field_provision.sh <arm>  (firewall + egress lockdown + cron)
#   - .env.field.example -> .env.field  (per-endpoint values)
#   - docs/FIELD_ETHICS.md              (must be complete BEFORE going public)
```

## Important ACI caveat for arms B/C

The RAGIN/vanilla arms need the repo image + `.env.field` (LLM key) at deploy
time. `deploy_azure_free_vms.sh` / `deploy_azure_containerapp.sh` already
produce the image; ACI free allowance (as of 2026) is effectively pay-as-you-go
(~$0.000011/s for 1 core/1.5 GB ≈ **$8.6/mo per always-on container**) — three
endpoints ≈ **$26/mo**, cheaper than equivalent VPSes. Confirm the current
ACI pricing page before committing; if the free-grant semantics changed,
fall back to 2–3 Hetzner/DO VPSes at the documented specs.

## Timeline pressure (Q1 = A: RQ4 stays headline)

Field data must start accruing by **2026-10-10** to reach ~30 days before the
2026-11-08 write-up freeze. If Azure re-enable stalls past **2026-10-03**,
pivot to cheap VPSes the same day — the compose/provision/ethics package is
provider-agnostic by design.
