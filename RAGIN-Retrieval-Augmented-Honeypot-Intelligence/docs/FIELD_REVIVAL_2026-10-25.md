# Field Revival Record — 2026-10-25

The two AWS instances (idle since Oct 9 with zero data) were revived into a live
field deployment. This file records the configuration drift applied.

## Live topology (verified end-to-end)

```
Attacker ──SSH──► REDACTED_FLEET_HOST:2222 (EDGE, t3.micro)
                    │ ufw: default-deny, only 2222/tcp + mgmt allowed
                    │ socat 0.0.0.0:2222 → 172.29.0.2:2222 (cowrie container)
                    │ socat 172.29.0.1:18083 ──mTLS──► CORE:8443
                    ▼
RAGIN CORE (m7i-flex.large): docker `ragin-core-staging` (image ragin-staging:v4-intel-proj)
  - code: wave-2 hardened (commit eea364d3, shipped via S3 tarball)
    + intel wiring (49a153ea) + pool-projection fix (871301d8, layered rebuild
      FROM ragin-staging:v4-intel)
  - command: python3 -m ragin.server_v2 --mode pipeline
  - provider: apmix claude-sonnet-4-6-free (auth=configured, verified in boot log)
  - verification: mandatory; host fiction per_session

RAGIN INTEL (REDACTED_FLEET_HOST): cve-mcp intel plane — host python services
  - :8000 `/opt/iv/bin/python service.py` + :8765 `/opt/intel/service.py`
  - both answer {"status":"ok","plane":"intel"} (verified via SSM)
```

## Changes applied (config drift vs Oct 9 state)

| Item | Before | After |
|---|---|---|
| Code on CORE | Oct 9 image (pre-hardening) | `ragin-staging:v4` = eea364d3 (all 27 findings fixed) |
| Intel wiring on CORE | not wired | `v4-intel` → `v4-intel-proj` = 49a153ea + 871301d8 (live CVE enrichment reaches the evidence bundle) |
| mTLS PKI | Expired 2026-10-11 | Fresh CA (10y) + 90d leafs, CN/SAN per role, 3072-bit RSA |
| LLM path | blackholed `127.0.0.1:9` | apmix `/v1` with model claude-sonnet-4-6-free |
| EDGE egress | unrestricted | RAGIN-EGRESS: allowlist only (DNS/NTP/metadata/CORE:8443/docker-bridge/root:443); IPv4+IPv6 |
| CORE egress | unrestricted | same allowlist pattern |
| EDGE ufw | active default-deny (blocked 2222!) | 2222/tcp allowed as the sole public listener |
| Public admin SSH (22) | open from REDACTED_OPERATOR_HOST | **closed** — management via SSM only (FIELD_ETHICS gate) |
| /app/data paths | missing on host | created; container binds /opt/ragin/data ✓ (were already correct) |
| Cowrie listener | socat bound 127.0.0.1 only | rebound 0.0.0.0:2222 |

## Verification evidence

- Boot log: `Pipeline initialized: Chrollo → Don → Evidence Gate → Policy → Hisoka
  (verification=mandatory, provider=https://api.apmix.ai/v1 auth=configured)`
- External SSH handshake from a foreign network: host key ED25519 presented,
  password prompt reached (`ssh -p 2222 bogususer@REDACTED_FLEET_HOST`)
- Cowrie log `cowrie.json`: 0 → 27 events within minutes of exposure (first session
  recorded 2026-10-25T04:10Z)
- Intel E2E inside the running container (2026-10-26): nginx-banner session →
  4 live NVD hits → 4 CVE docs in `intel_documents` **and** in the evidence
  bundle (`E2E_RESULT: PASS`; before the `871301d8` projection fix: 0 CVEs).

## Operational notes

- Incident during rollout: a blanket ip6tables DROP on EDGE severed the SSM agent
  channel (recovered by EC2 reboot — rules are non-persistent). Egress rules now
  mirror the IPv4 allowlist on IPv6 with root:443 preserved for the agent.
- Deployment plumbing kept in S3 bucket `ragin-field-deploy-eun1` (tarballs +
  presigned-GET delivery; the git push path is blocked by pack size from the
  consolidation snapshot).
- Certificates expire ~2027-01-23: rotation reminder set for early January.
- Data path: cowrie.json (EDGE) → daily collection per `scripts/collect_field_data.py`
  (hashed IPs; raw IPs never leave the host — FIELD_ETHICS §3).
