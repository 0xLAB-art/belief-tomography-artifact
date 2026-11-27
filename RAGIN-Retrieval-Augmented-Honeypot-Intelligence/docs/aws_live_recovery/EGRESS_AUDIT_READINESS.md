# RAGIN AWS Live Recovery — Egress and Audit Readiness

Status: LIVE_READY partial — current state verified; containment and durable audit still approval-required.

---

## 1. Current egress state

Verified this session:
- CORE SG egress: all protocols to `0.0.0.0/0`
- EDGE SG egress: all protocols to `0.0.0.0/0`
- Default NACL: allow-all inbound and outbound
- No custom restrictive NACL observed
- No VPC endpoints observed
- No Flow Logs observed

Implication:
- Instances can still reach internet endpoints by default.
- Private CORE placement without a management path would cut off general internet access, but that is intended only for the replacement, not today’s public instances.

Current SSM reachability:
- SSM is Online for both instances today.
- SSM reachability currently depends on the existing network posture; it is not proven to survive private placement without separate design.

Sources:
- `CURRENT_AWS_INVENTORY.md`
- security group and route table evidence under `evidence/`

---

## 2. Host application egress relevant to migration

CORE current relevant paths:
- mTLS listener on `172.31.17.217:8443`
- Provider gateway URL configured to `http://127.0.0.1:9` in env
- Provider models set to `disabled-local-provider` in env

Migration concern:
- If production later needs provider-backed generation, provider egress must be designed separately and approved separately.
- A private CORE without provider egress will only serve the local/disabled-provider posture, which is not provider-backed generation.

Recommendation:
- Do not assume provider connectivity from private placement.
- Define provider destinations, ports, and allowlist before any default-deny change that would affect them.

---

## 3. Audit readiness state

Verified artifacts present:
- CORE: `/etc/ragin/server.env`, `/etc/ragin/tls/*`
- EDGE: `/etc/ragin/cowrie.cfg`, `/etc/ragin/api.key`, `/etc/ragin/tls/*`
- Running services: CORE server_v2, EDGE Cowrie + socat chain
- Cowrie JSON log path configured to `/cowrie/cowrie-git/var/log/cowrie/cowrie.json`

Gaps:
- No durable protected audit log destination verified for production retention
- No Flow Logs verified
- No CloudTrail delivery configuration verified for durable long-term protected audit
- No verified tamper-evident copy or retention policy verified for production

Recommendation:
- Treat audit durability as approval-required for production, not completed.

---

## 4. Egress change safety rule

Do not apply broad egress changes that could disconnect SSM or administrative access.
If testing requires changes, produce a bounded change request instead of a blanket default-deny.

---

## 5. Temporary staging rule to review

Currently verified on CORE SG:
- `tcp/8443 from 172.31.35.203/32` with description `RAGIN-EDGE temporary mTLS staging`

This should be reviewed for removal or conversion to a permanent application rule only after the permanent service contract is verified.

---

## 6. Remaining blocking items

- Egress containment: not implemented
- Flow Logs: not configured
- Durable protected audit: not verified
- Private management path that survives no-public-IP placement: not proven
- Provider egress design: not approved
- Public exposure: not approved
