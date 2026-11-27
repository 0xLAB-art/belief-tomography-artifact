# RAGIN AWS Live Recovery — Deployment State Matrix

Purpose: distinguish historical experiments, currently verified AWS state, and not-deployed components. This is not an approval to deploy.

**Staleness note (2026-10-26):** rows marked (superseded) predate the
`FIELD_REVIVAL_2026-10-25.md` deployment; that file is authoritative for the
listener/egress/PKI state. APPROVAL_REQUIRED rows remain pending decisions.

Legend:
- SOURCE_IMPLEMENTED: code/definition exists in the repository or on the instance
- LOCAL_TESTED: tested on the laptop/localhost only
- AWS_STAGING_DEPLOYED: deployed in AWS for a staged experiment
- AWS_CURRENTLY_VERIFIED: confirmed through live AWS reads or live SSM probes this session
- PRODUCTION_READY: meets production deployment bar
- APPROVAL_REQUIRED: change needs explicit approval before execution

---

## 1. Infrastructure

| Component | Status | Notes |
|---|---|---|
| CORE EC2 | AWS_CURRENTLY_VERIFIED | running m7i-flex.large in public subnet, public IPv4, SSM Online |
| EDGE EC2 | AWS_CURRENTLY_VERIFIED | running t3.micro in public subnet, public IPv4, SSM Online |
| VPC | AWS_CURRENTLY_VERIFIED | default VPC eu-north-1, 172.31.0.0/16 |
| Public subnets | AWS_CURRENTLY_VERIFIED | CORE and EDGE still in public subnets |
| Private subnet | AWS_CURRENTLY_VERIFIED | subnet-07fae34b3db734bb2 exists, private, eu-north-1a |
| Private route table | AWS_CURRENTLY_VERIFIED | rtb-04bf376f929483d4c exists, local-only, associated to private subnet |
| Internet gateway | AWS_CURRENTLY_VERIFIED | attached to VPC, used by main route table |
| EC2 Instance Connect Endpoint | AWS_CURRENTLY_VERIFIED | eice-023d2c69cb6690c48 in private subnet, state create-complete |
| Private CORE placement | APPROVAL_REQUIRED | desired state, not deployed |
| CORE in private subnet | APPROVAL_REQUIRED | not current |
| CORE no public IP | APPROVAL_REQUIRED | not current |
| Default NACL | AWS_CURRENTLY_VERIFIED | allow-all |
| Restrictive NACL | APPROVAL_REQUIRED | not deployed |

---

## 2. Storage

| Component | Status | Notes |
|---|---|---|
| CORE root EBS 40 GiB | AWS_CURRENTLY_VERIFIED | vol-0537ee06e67f63cc5, encrypted=false |
| EDGE root EBS 20 GiB | AWS_CURRENTLY_VERIFIED | vol-05925e722a36cd345, encrypted=false |
| Encrypted CORE root | APPROVAL_REQUIRED | not deployed |
| Encrypted EDGE root | APPROVAL_REQUIRED | not deployed |
| Snapshot/AMI migration | APPROVAL_REQUIRED | not executed |

---

## 3. Management and recovery

| Component | Status | Notes |
|---|---|---|
| SSM (CORE) | AWS_CURRENTLY_VERIFIED | Online, SSM send-command successful |
| SSM (EDGE) | AWS_CURRENTLY_VERIFIED | Online, SSM send-command successful |
| EIC private SSH path | AWS_CURRENTLY_VERIFIED | endpoint exists in private subnet |
| Operator SSH via EIC | AWS_CURRENTLY_VERIFIED | SG rules allow EIC endpoint -> CORE/EDGE SSH |
| SSM without public routing | APPROVAL_REQUIRED | not proven for no-public-IP CORE |
| Private provider inference path | APPROVAL_REQUIRED | not designed/verified for private CORE |
| Recovery from no-public-IP CORE | APPROVAL_REQUIRED | depends on management path choice |

---

## 4. Security groups and egress

| Component | Status | Notes |
|---|---|---|
| CORE SG ingress | AWS_CURRENTLY_VERIFIED | SSH from EIC SG + operator /32; tcp/8443 from EDGE /32 (temporary staging) |
| EDGE SG ingress | AWS_CURRENTLY_VERIFIED | SSH from EIC SG + operator /32 |
| CORE SG egress | AWS_CURRENTLY_VERIFIED | all -> 0.0.0.0/0 |
| EDGE SG egress | AWS_CURRENTLY_VERIFIED | all -> 0.0.0.0/0 |
| EIC management SG | AWS_CURRENTLY_VERIFIED | egress tcp/22 to CORE/EDGE SGs |
| Egress containment | APPROVAL_REQUIRED | not implemented at SG layer; host-layer RAGIN-EGRESS allowlist applied 2026-10-25 (FIELD_REVIVAL) — SG still all -> 0.0.0.0/0 |
| Temporary mTLS staging SG rule | AWS_CURRENTLY_VERIFIED | present on CORE SG; should be reviewed/removed per plan |
| UFW host rules | AWS_STAGING_DEPLOYED/AWS_CURRENTLY_VERIFIED_TO_BE_CONFIRMED | confirm current on both hosts with live SSM if needed |

---

## 5. Application and serving

| Component | Status | Notes |
|---|---|---|
| ragin.server_v2 on CORE | AWS_CURRENTLY_VERIFIED | running `python3 -m ragin.server_v2 --mode pipeline` |
| CORE listener | AWS_CURRENTLY_VERIFIED | tcp 172.31.17.217:8443 |
| CORE mTLS required | AWS_CURRENTLY_VERIFIED | RAGIN_MTLS_REQUIRED=1, allowed identity spiffe://ragin/edge |
| CORE certificate profile | AWS_CURRENTLY_VERIFIED | (superseded 2026-10-25: fresh 10y CA + 90d leafs per FIELD_REVIVAL) staged staging CA + leaf; short validity; see cert inventory evidence |
| EDGE mTLS client | AWS_CURRENTLY_VERIFIED | edge.crt/edge.key/ca.crt present; socat OpenSSL chain configured |
| Application API auth on CORE | SOURCE_IMPLEMENTED | RAGIN_REQUIRE_AUTH=1 in env; app-layer behavior not exercised live this session |
| Provider-backed generation | SOURCE_IMPLEMENTED / AWS_CURRENTLY_VERIFIED_AS_DISABLED_LOCAL_PROVIDER | CORE env uses disabled-local-provider; real provider route not proven live this session |
| Verifier serving path | SOURCE_IMPLEMENTED | code present; not exercise-verified live this session |
| Chrollo / Don / Hisoka | SOURCE_IMPLEMENTED | code present; not independently deployment-verified this session |
| Session persistence | SOURCE_IMPLEMENTED | code present; live durability not verified |
| Audit durability | APPROVAL_REQUIRED | not verified as durable/protected |
| Flow Logs / network telemetry | APPROVAL_REQUIRED | not configured |
| Laya optional inference | APPROVAL_REQUIRED | optional; not gateway-critical |

---

## 6. Deception plane

| Component | Status | Notes |
|---|---|---|
| Cowrie code/packages | SOURCE_IMPLEMENTED / AWS_CURRENTLY_VERIFIED | present on EDGE; twistd cowrie process observed |
| Cowrie runtime config | AWS_CURRENTLY_VERIFIED | /etc/ragin/cowrie.cfg present; backend=llm; redacted lines in evidence |
| EDGE loopback Cowrie SSH | AWS_CURRENTLY_VERIFIED | 127.0.0.1:2222 reachable from EDGE host side via socat |
| Public Cowrie exposure | AWS_CURRENTLY_VERIFIED_BLOCKED | no public listener (superseded 2026-10-25: FIELD_REVIVAL opened 2222/tcp as the sole public listener with ufw default-deny) |
| Cowrie container isolation | APPROVAL_REQUIRED | not deployed as isolated container boundary |
| Deception/admin plane split | APPROVAL_REQUIRED | not production-deployed |

---

## 7. Overall readiness

- Production ready: no.
- AWS staging deployed (partial): yes, for CORE listener + EDGE Cowrie/socat + mTLS config.
- Historical staging experiments: preserved as historical records, not current proof.
- Current authoritative state: see CURRENT_AWS_INVENTORY.md and LIVE_MTLS_ACCEPTANCE_RESULTS.md.
