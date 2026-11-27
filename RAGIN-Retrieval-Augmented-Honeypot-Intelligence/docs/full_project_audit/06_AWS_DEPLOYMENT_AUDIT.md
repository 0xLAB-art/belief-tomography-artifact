# 06 — AWS Deployment Audit

**Method:** Source-grounded inspection of infrastructure-as-code, deployment scripts, and configuration. No AWS API access confirmed in this audit session.

## 6.1 Historical AWS identifiers (NOT verified current)

| Component | Identifier | Detail |
|-----------|-----------|--------|
| CORE instance | i-062a400b300f4f9e4 | 172.31.17.217, API port 8443 |
| EDGE instance | i-05bc6aab0bd4260a7 | 172.31.35.203 |
| VPC | vpc-044a70ed680faff8b | — |
| Private subnet | subnet-07fae34b3db734bb2 | — |
| Private route table | rtb-04bf376f929483d4c | — |
| EIC endpoint | eice-023d2c69cb6690c48 | — |
| Region | eu-north-1 | Historical |

**Status:** ALL identifiers are HISTORICAL. No current AWS state verified. The git provenance record (verifier_integrity_provenance.json) was generated at commit f0c4042 with a dirty working tree — it does not reference any AWS state.

## 6.2 Deployment scripts

| Script | Purpose | Status |
|--------|---------|--------|
| `deploy.py` | Main deployment driver | READ (not executed) |
| `deploy.sh` | Shell deployment wrapper (1374 bytes) | READ |
| `deploy_field.sh` | Field deployment (14KB) | READ (not executed) |
| `field_provision.sh` | Field network provisioning (5.7KB) | READ (not executed) |
| `bootstrap_ragin_vm.sh` | VM bootstrap (2.9KB) | READ |
| `deploy_azure_containerapp.sh` | Azure deployment (10.7KB) | READ (not executed) |
| `deploy_azure_free_vms.sh` | Azure free VMs (14KB) | READ (not executed) |
| `provision_azure_field.sh` | Azure field provisioning (7.2KB) | READ (not executed) |
| `azure_healthcheck.sh` | Azure health check (2.7KB) | READ |
| `cti_audit_pilot.sh` | CTI audit pilot (1.5KB) | READ |
| `install_apmix_watch.sh` | APMix watch install (2.7KB) | READ |
| `install_zodiac_stack.sh` | Zodiac stack install (5.1KB) | READ |
| `run_zodiac_eval.sh` | Zodiac eval run (6KB) | READ |
| `he_foreground.sh` | Human eval foreground (1.4KB) | READ |
| `smoke_test.sh` | Smoke test (1.3KB) | READ |
| `field_smoke_local.sh` | Field smoke local (5.7KB) | READ |
| `field_smoke_ssh.py` | Field smoke SSH (9KB) | READ |
| `field_health_check.py` | Field health check (11KB) | READ |
| `start_services.sh` | Start services (1.1KB) | READ |

## 6.3 Docker Compose variants

| File | Services | Purpose |
|------|---------|---------|
| docker-compose.yml | gateway, chrollo, don, hisoka, jev, redis, prometheus, grafana, nginx, cowrie | Standard dev |
| docker-compose.prod.yml | (exists, 3KB) | Production variant |
| docker-compose.field.yml | (exists, 7.4KB, modified) | Field deployment |
| docker-compose.ci.yml | (exists, 732 bytes) | CI |
| docker-compose.test.yml | (exists, 571 bytes) | Test |
| docker-compose.ab.yml | (exists, 2.9KB) | A/B testing |
| docker-compose.canary.yml | (exists, 2.9KB) | Canary rollout |
| docker-compose.traditional.yml | (exists, 2.9KB) | Traditional honeypot baseline |
| docker-compose.vm.yml | (exists, 2.6KB) | VM mode |
| docker-compose.vm.cowrie.yml | (exists, 862 bytes) | VM + cowrie |
| Dockerfile.gateway | Rust gateway image | LLM gateway |
| Dockerfile.gateway.offline | Offline gateway | Offline mode |
| Dockerfile.python | Python service image | ragin-python:latest |

## 6.4 Intended vs actual distributed architecture

### Intended (from project docs + docker-compose.yml)

```
Internet → NGINX (TLS termination, auth map) → chrollo/don/hisoka/jev services (internal)
                                                         ↓
                                                   Redis (cache)
                                                         ↓
                                                 LLM Gateway (Rust)
                                                         ↓
                                            OpenCode CLI bridge / OpenRouter / Azure
                                                         
Cowrie (SSH honeypot) → server_v2 bridge (when RAGIN_BRIDGE_HOST configured)
```

### Actual (confirmed from source + Docker Compose)

- **Local Docker Compose:** 9 services defined, ragin-internal (internal: true) + ragin-external networks. NGINX exposes 80/443/2222. Cowrie exposes 2223. All RAGIN services on ragin-internal. Development-only.
- **server_v2 in Docker:** NOT a dedicated service in docker-compose.yml. The chrollo/don/hisoka services run `ragin.server` (legacy server.py), NOT server_v2. server_v2 is the auth-authoritative pipeline but is NOT wired into the standard Docker Compose as a service.
- **Field arm C (Cowrie bridge):** Requires RAGIN_BRIDGE_HOST env + internal Docker networking (commit fe09635 fixed binding for internal-docker Cowrie to reach sv2). Not confirmed active in any deployment.

### Critical gaps (from historical reports, re-assessed)

| Gap | Historical claim | Current status |
|-----|-----------------|----------------|
| CORE on public-addressed subnet | Historical: CORE may have been on public subnet | NOT VERIFIED — no AWS access |
| Root EBS volumes unencrypted | Historical: EBS encryption missing | NOT VERIFIED — no AWS access |
| AWS CORE may be fallback-only | Historical: CORE not primary | NOT VERIFIED |
| Permanent generator connectivity not proven | Historical: provider transport not live | CONFIRMED — provider_transport.py implemented and tested but no live provider configured |
| Final egress restrictions incomplete | Historical: container egress not fully restricted | CONFIRMED by source — docker-compose.yml has ragin-internal: internal: true (egress blocked) but ragin-external services can reach internet |
| Protected audit durability incomplete | Historical: audit trail durability | CONFIRMED by source — Session uses fsync, HostFictionStore uses atomic file replace, HITL FileAuditTrail uses append-only JSONL. All local filesystem, no cloud durability. |
| Public Cowrie activation not approved | Historical: public SSH not approved | CONFIRMED by source — Cowrie is in docker-compose.yml but COWRIE_PORT defaults to 2223 (not 22). No public Cowrie activation confirmed. |

## 6.5 Field deployment configuration

From `.env.field.example`:

- `RAGIN_FIELD_ARM=ragin` — which arm this endpoint serves
- `RAGIN_FIELD_SSH_BANNER=SSH-2.0-OpenSSH_8.9p1 Ubuntu-3ubuntu0.4` — synthetic decoy
- `RAGIN_LLM_BASE_URL=replace-with-approved-private-bridge/v1` — INTENTIONALLY UNRESOLVED placeholder
- `RAGIN_LLM_API_KEY=replace-me` — placeholder
- `RAGIN_LLM_MODEL=opencode/space-bunny-free` — free model
- `RAGIN_LLM_PROVIDER_HOST=replace-with-approved-private-bridge` — egress allowlist placeholder
- `RAGIN_IMAGE=ghcr.io/0xzodiac/the-intelligence-ladder:latest` — container image
- `COWRIE_LLM_API_KEY` — must equal backend's key for cowrie-llm frontend auth

**Key finding:** The field env template intentionally leaves the LLM bridge URL as an unresolved placeholder. The comment says: "the local loopback bridge cannot be addressed from a container without an explicitly approved private transport. Do not replace it with a paid provider by default." This confirms that field deployments require an explicit approval-gated private bridge — not a default public provider.

## 6.6 Egress architecture

From docker-compose.yml networks:
- `ragin-internal: driver: bridge, internal: true` — NO internet egress for chrollo, don, hisoka, jev, redis, prometheus, grafana, nginx, cowrie on this network
- `ragin-external: driver: bridge` — internet egress for NGINX, cowrie (both have ragin-external)

The LLM gateway (gateway service) is on BOTH networks — it can reach the internal RAGIN services AND the internet (for upstream LLM providers).

**Gatekeeper:** The gateway is the ONLY service that can reach the internet for LLM calls. All other RAGIN services are isolated behind ragin-internal. This is a sound egress restriction pattern.

## 6.7 What would be needed for full field deployment

1. ✅ Docker Compose (dev) — ready
2. ⚠️ Docker Compose (field) — .env.field must be filled with approved private bridge URL + key
3. ⚠️ server_v2 as a Docker service — not in standard compose; needs custom service definition
4. ⚠️ RAGIN_BRIDGE_HOST — must be set so Cowrie container can reach sv2
5. ⚠️ SSL certificates — ./ssl/cert.pem + ./ssl/key.pem required by NGINX (not in repo)
6. ⚠️ RAGIN_API_KEY — must be set in .env (required by nginx envsubst)
7. ⚠️ GRAFANA_ADMIN_PASSWORD — must be set
8. ⚠️ Private LLM bridge — must be approved and provisioned (not a paid provider by default)
9. ❌ AWS deployment — no current state verified; historical identifiers only
10. ❌ mTLS between EDGE and CORE — not in Docker Compose; requires certs + RAGIN_MTLS_REQUIRED + RAGIN_MTLS_ALLOWED_IDENTITIES
