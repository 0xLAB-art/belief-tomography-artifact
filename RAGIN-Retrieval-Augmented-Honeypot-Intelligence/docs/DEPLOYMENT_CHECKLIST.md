# RAGIN — Azure Live Deployment Checklist

Goal: run RAGIN as **live, real-world endpoints on Azure** (not simulation) —
the same stack that `docker compose up` runs locally, deployed to Azure
Container Apps, with the existing Cowrie ACI honeypot in front.

## Pre-Deployment

- [ ] All tests passing (345 tests passing, full suite)
- [ ] Docker images build locally (`docker compose build`)
- [ ] `AZURE_OPENAI_ENDPOINT` / `AZURE_OPENAI_KEY` set in `.env`
- [ ] `OPENROUTER_API_KEY` set for the gateway LLM route
- [ ] SSL certificates / HTTPS ingress configured for Container Apps
- [ ] Gateway started and reachable on its FQDN
- [ ] Redis started on the env-internal endpoint
- [ ] Error rate baseline recorded before deploy
- [ ] Cost tracking enabled (per-component budgets set)

## Deployment

- [ ] Resource group `ragin-honeypot-rg` exists (eastus)
- [ ] Log Analytics workspace `raginhoneypotlogs` exists
- [ ] ACR created (Basic) and admin-enabled
- [ ] `az acr build` pushes `ragin-python` (and `gateway`) images
- [ ] Container Apps environment `ragin-env` created
- [ ] `redis` deployed internal-only (no public ingress)
- [ ] `gateway` deployed (LLM router)
- [ ] `chrollo` orchestration deployed
- [ ] `don` RAG/threat-intel engine deployed
- [ ] `hisoka` deception engine deployed
- [ ] Secrets registered (`azure-openai-key`, `ragin-api-key`)
- [ ] Env vars reference secrets via `secretref:`

## Post-Deployment

- [ ] `/health` returns 200 on each public FQDN
- [ ] End-to-end deception probe succeeds (`whoami` → persona output)
- [ ] LLM telemetry flows to Log Analytics (verifier, HITL, TTP extractions)
- [ ] Cowrie ACI forwards to Container Apps ingress
- [ ] Prometheus / metrics export works
- [ ] Rollback path verified (`bash scripts/deploy_azure_containerapp.sh` idempotent)

## Sign-Off

- [ ] Stakeholder reviewed live endpoint behavior
- [ ] Security verification run (no leaked secrets in image layers)
- [ ] Final cost estimate reviewed and approved
- [ ] Sign-off recorded

## Current state (as of 2026-09-19)

| Resource | Type | Status |
|---|---|---|
| `ragin-honeypot-rg` | Resource group (eastus) | ✅ exists |
| `raginhoneypotlogs` | Log Analytics | ✅ exists |
| `ragin-cowrie-hp` | Container Instance (Cowrie SSH honeypot) | ✅ running at `attacker-f2ed9d9abd3f:2222,2223` |
| Container Apps env | `ragin-env` | created by deploy script |
| ACR | auto-named `raginhp####` | created by deploy script |

## Prerequisites

```bash
az login                       # account: rg-youseefhamdi329-8520 / ragin-honeypot-rg
cd RAGIN-Retrieval-Augmented-Honeypot-Intelligence
```

`.env` must contain (already set in this checkout):

```ini
AZURE_OPENAI_ENDPOINT=https://youseefhamdi329-7955-resource.services.ai.azure.com
AZURE_OPENAI_KEY=<key>
RAGIN_API_KEY=ragin-...        # generated; used by gateway/nginx auth
API_KEY=ragin-...              # same value; used by python components
```

## One-command deploy

```bash
bash scripts/deploy_azure_containerapp.sh
```

The script is idempotent and performs:

1. **ACR** (`Basic`, admin-enabled) — created if missing.
2. **Cloud builds** — `az acr build` builds `ragin-python` (and `gateway` if
   `Dockerfile.gateway` exists) *in Azure*, so no local Docker daemon needed.
3. **Container Apps environment** `ragin-env` in `ragin-honeypot-rg`.
4. Deploys (external = public HTTPS FQDN):
   - `redis` — internal only, no public ingress.
   - `gateway` — LLM router (only if `Dockerfile.gateway` exists).
   - `chrollo` — session orchestration.
   - `don` — RAG/threat-intel engine (`RAGIN_DON_MODEL`).
   - `hisoka` — deception engine (`RAGIN_HISOKA_MODEL`, timeout 300 s).
5. Secrets (`azure-openai-key`, `ragin-api-key`) registered as Container App
   secrets; env vars reference them via `secretref:`.

## Verify the live deployment

```bash
HISOKA_FQDN=$(az containerapp show -g ragin-honeypot-rg -n hisoka \
  --query properties.configuration.ingress.fqdn -o tsv)

curl -s "https://$HISOKA_FQDN/health"            # expect ok/200
az containerapp logs show -g ragin-honeypot-rg -n hisoka --follow
```

End-to-end deception probe against the public endpoint:

```bash
curl -s "https://$HISOKA_FQDN/" \
  -H "Authorization: Bearer $RAGIN_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"session_id":"probe-1","input":"whoami"}'
```

## How the stack talks

```
Internet ──> Cowrie ACI (22/2222)          # SSH/telnet interactions, real IPs
         └─> Container Apps HTTPS ingress  # chrollo / don / hisoka / gateway
                  │
                  ├──> Azure AI Foundry (qwen--qwen38-27b)  # LLM calls, egress
                  └──> redis (internal env-internal FQDN)   # shared state
```

- Components call **Azure directly** (low latency) and fall back to the
  internal gateway — same behavior as local compose.
- All LLM telemetry (verifier verdicts, HITL approvals, TTP extractions)
  flows to the existing Log Analytics workspace.

## Rebuild / redeploy after code changes

```bash
bash scripts/deploy_azure_containerapp.sh   # reruns az acr build + updates
```

## Cost control

- Container Apps scale to `--min-replicas 1`; set `--min-replicas 0` for dev.
- ACR Basic ≈ $5/mo; delete with `az acr delete -n <name> -g ragin-honeypot-rg`.
- Full teardown (⚠ also deletes the running Cowrie ACI):
  `az group delete -n ragin-honeypot-rg --yes --no-wait`

## Security notes

- `AZURE_OPENAI_KEY` is stored as a Container App **secret**, never as a
  plain env var or image layer.
- Only `chrollo/don/hisoka/gateway` get public ingress; `redis` is env-internal.
- `RAGIN_API_KEY` gates the public HTTP API (same key nginx used locally).
