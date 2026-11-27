# RAGIN Task 3: Security Acceptance Test Plan

This plan separates offline/local checks from live AWS checks. A configuration file, failed connection, or absent response is not sufficient evidence of a passed security test.

## Offline checks executed in Task 3

| Check | Procedure | Result |
|---|---|---|
| Repository, SSH, and AWS inventory | Read Task 1/2 reports and inspect Compose, Dockerfiles, deployment scripts, gateway source/config, AWS/IaC file inventory; connect to both supplied hosts and query their AWS resources with read-only commands | PASS for scoped inventory; remaining control-plane properties are listed below |
| AWS credential safety | Run non-printing `aws sts get-caller-identity --query Account --output text` availability check | NOT AVAILABLE (`rc=255`); no identity output retained |
| Shell syntax | `bash -n scripts/field_provision.sh` | PASS |
| Compose rendering | Copied `docker-compose.field.yml` and `.env.field.example` to a temporary directory, materialized the example as `.env.field`, and ran `docker compose --env-file ... config --quiet`; no services started | PASS (`rc=0`). Direct repository-path rendering is intentionally blocked because the required local `.env.field` is absent. |
| Secret exposure scan | Inspect only names and tracked configuration; do not print `.env` values or private keys | No secret values were printed; repository contains historical/example secret-shaped test fixtures that are not deployment credentials |
| Rust auth review | Read `llm-gateway/src/main.rs` and `config.toml` | FAIL as design gate: no demonstrated route authentication; gateway excluded from field path |

## Live AWS checks required after approval

| ID | Security property | Positive evidence | Current status |
|---|---|---|---|
| T3-01 | Internet cannot reach CORE application ports | Authorized external probes time out/deny; SG/VPC Flow Logs corroborate | INCOMPLETE: CORE SG exposes only TCP/22 to one `/32`, but the subnet has a direct IGW route and no independent external negative test was performed |
| T3-02 | Public 22 reaches Cowrie, not Ubuntu shell | Controlled external session plus listener/bind evidence | **FAIL / deployment gate:** supplied SSH reached Ubuntu `sshd`; host listener map shows public `0.0.0.0:22`; Docker/Cowrie was absent |
| T3-03 | Unauthenticated CORE request rejected | mTLS and application-auth negative test | NOT RUN |
| T3-04 | Session replay/context authorization | Arbitrary ID and wrong capability fail; owner succeeds | NOT RUN live; local Task 2 tests cover application contract |
| T3-05 | EDGE cannot read metadata/credentials | Metadata negative test, no role, container env/mount review | **FAIL / incomplete:** IMDS endpoint enabled with `HttpPutResponseHopLimit=2`; IMDSv2 token was obtainable; no IAM role metadata returned; no container test possible because Docker was absent |
| T3-06 | Attacker cannot control Docker/host | Container inspect, socket/capability/mount review, controlled non-destructive input | NOT DEPLOYED: Docker was absent; no containment pass can be claimed |
| T3-07 | Egress restricted | Denied arbitrary destination, allowed CORE path, firewall counters | **FAIL / deployment gate:** both hosts showed UFW inactive and iptables `INPUT/FORWARD/OUTPUT ACCEPT` |
| T3-08 | Authorized operations remain available | SSM/overlay login and CORE retrieval before/after quarantine | PARTIAL: public SSH works and SSM Agent is active, but `describe-instance-information` returned no target instances; Session Manager/overlay access was not verified |
| T3-09 | Laya disconnection cannot bypass verification | Disable LOCAL service; observe `NO_SIGNAL` and safe fallback/failure | NOT RUN; Laya not implemented |
| T3-10 | Gateway failure does not expose secrets | Internal-only failure test with redacted error response | NOT RUN live; Task 2 app tests cover provider failure at Python boundary |
| T3-11 | Audit survives restart | Restart only after protected copy; compare chained record counts/digests | NOT RUN |
| T3-12 | Emergency isolation | Apply quarantine SG/stop EDGE from independent operator path; preserve evidence | NOT RUN |

## Test safety

Use only owned instances and controlled test accounts. Do not scan the Internet, use attack payloads, execute uploads, or contact attacker-controlled destinations. A public listener is not opened as part of Task 3.
