# RAGIN Task 3.7: Security Acceptance Matrix

Evidence timestamp: `2026-10-08T19:26:53Z` unless a row states otherwise.

| Control | Status | Direct evidence / limitation |
|---|---|---|
| Fresh authorized SSH to CORE | PASS | Independent SSH returned `CORE_SSH_OK` and the expected hostname |
| Fresh authorized SSH to EDGE | PASS | Independent SSH returned `EDGE_SSH_OK` and the expected hostname |
| Fresh SSM command to CORE | PASS | `RAGIN_FINAL_SSM=ip-172-31-17-217` |
| Fresh SSM command to EDGE | PASS | `RAGIN_FINAL_SSM=ip-172-31-35-203` |
| CORE private subnet/no public IPv4 | BLOCKED | CORE still has public IPv4 and direct IGW route; replacement/cutover required |
| CORE public application exposure | PASS for current empty service surface | No application listener exists; this is not proof of future isolation |
| EDGE unnecessary public ingress | PASS | Target SGs have only operator TCP/22; no 80/443 ingress |
| EDGE real shell replaced by Cowrie | INCOMPLETE | Ubuntu `sshd` remains; Cowrie/Docker not deployed by design |
| SG outbound containment | INCOMPLETE | Both target SGs remain all-protocol outbound to `0.0.0.0/0` |
| Host outbound containment | INCOMPLETE | UFW outgoing remains allow; dependencies are not fully inventoried |
| Future container metadata isolation | INCOMPLETE | Docker absent; no container test exists |
| IMDSv2/hop limit | PASS | Both instances: tokens required, endpoint enabled for SSM, hop limit 1 |
| Protected encrypted roots | FAIL | Both current root EBS volumes report `Encrypted=false` |
| Private mTLS transport | BLOCKED | Temporary private path worked; authorized Python mTLS certificate was rejected; no service deployed |
| Rogue mTLS credential rejection | PASS for ephemeral server | Rogue client was rejected; not a deployed application authorization test |
| Audit persistence/restart durability | INCOMPLETE | No RAGIN audit service deployed |
| Network telemetry | INCOMPLETE | No VPC Flow Logs or configured delivery trail observed |
| Emergency isolation rehearsal | INCOMPLETE | Runbook exists; live rehearsal would interrupt the only public/admin path |
| No unapproved resources | PASS | No EC2, subnet, route table, NAT, endpoint, snapshot, volume, or paid service was created |
| Public honeypot activation | PASS as prohibition | No Cowrie, Docker, RAGIN, Laya, or public honeypot was started |

The matrix does not authorize public exposure. Any `FAIL`, `INCOMPLETE`, or `BLOCKED` boundary remains a deployment blocker.
