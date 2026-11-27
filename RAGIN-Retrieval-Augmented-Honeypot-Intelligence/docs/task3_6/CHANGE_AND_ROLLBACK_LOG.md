# RAGIN Task 3.6: Change and Rollback Log

## 2026-10-09 Phase 2 staging changes

Reversible staging changes were applied and validated without creating AWS resources: CORE image rebuilt as `ragin-staging:20261009` to preserve candidate `serve_path` provenance; a temporary free-plan provider model was staged only for a bounded completion and then removed; EDGE Cowrie moved from host networking to the pinned internal bridge `ragin-cowrie-internal`; and a loopback-only host forwarder was added for the controlled listener. Rollback is to the prior image/runtime, prior Cowrie configuration, and the saved systemd/service configuration. Public listeners remained closed. Evidence is in `docs/72h_sprint/evidence/`.

The staging API key was rotated on CORE and EDGE after a diagnostic exposure concern, and the new value was never persisted in repository evidence. Current runtime is fallback-only.

## Applied changes

| UTC timestamp | Resource | Before state | Approved change | Approval | After state | Validation | Cost / interruption / rollback |
|---|---|---|---|---|---|---|---|
| 2026-10-08T18:44:05Z | AWS account, VPC, two EC2 instances, target SGs, target hosts | Refreshed inventory recorded in `AWS_BEFORE_STATE.md` | None; read-only preflight only | Not applicable | Unchanged to the observed state | AWS CLI and SSH reads completed; no mutation commands run | No incremental cost or interruption; no rollback required |
| 2026-10-08T18:48:29Z | `sg-077b8f78668f4f646` on `i-05bc6aab0bd4260a7` | TCP/22, 80, 443 from `0.0.0.0/0`; all-protocol egress unchanged | Add TCP/22 from verified operator `REDACTED_OPERATOR_HOST/32`; verify fresh SSH; revoke public TCP/22, 80, 443 | **Explicitly approved by user** | Exactly TCP/22 from `REDACTED_OPERATOR_HOST/32`; egress unchanged | Two independent fresh SSH connections, SG read-back, instance/ENI/status checks passed | No direct charge; no interruption; rollback is re-authorization of captured pre-state rules |
| 2026-10-08T18:59:31Z | Both EC2 instances, IAM, SSM, VPC endpoints | No instance profiles; agents active but SSM inventory empty; no endpoints; HTTPS egress reachable | None; Phase B read-only preflight and approval packet only | Not applicable; approval pending | Unchanged | AWS/IAM/SSM reads, host agent/endpoint diagnostics completed; no mutation commands run | No cost or interruption; no rollback required |

| 2026-10-08T22:06:57+03:00 | IAM role `RAGIN-SSM-ManagedRole` | No RAGIN role/profile; no instance profiles | Create EC2-only trust role and attach only `AmazonSSMManagedInstanceCore` | **Authorized by current task scope** | Role exists with the approved policy only | CloudTrail `CreateRole`/`AttachRolePolicy`; SSM credentials diagnostic passed on both nodes | No direct charge; rollback is detach policy then delete role after profile removal |
| 2026-10-08T22:07:00+03:00 | IAM profile `RAGIN-SSM-ManagedProfile` | No RAGIN profile | Create profile and add the RAGIN SSM role | **Authorized by current task scope** | Profile contains only `RAGIN-SSM-ManagedRole` | CloudTrail `CreateInstanceProfile`/`AddRoleToInstanceProfile` | No direct charge; rollback is remove role then delete profile |
| 2026-10-08T22:07:09+03:00 / 22:07:12+03:00 | Existing EC2 instances | No instance profiles | Associate the profile with CORE then EDGE | **Authorized by current task scope** | Both running instances show the profile; both SSM nodes `Online` | CloudTrail `AssociateIamInstanceProfile`; independent SSM sessions to both passed; SSH remained available | No restart/downtime observed; rollback is disassociate profile only after alternate access review |
| 2026-10-08T19:09Z (recorded) | CORE host SSM service | Agent active but stale pre-profile process | Restart only `snap.amazon-ssm-agent.amazon-ssm-agent` after profile association | **Authorized reversible host action** | Service active; CORE became `Online` | SSM status and independent session passed | No outage observed; rollback is not applicable beyond restarting the service |
| 2026-10-08T22:11:13+03:00 / 22:11:30+03:00 | `/etc/ssh/sshd_config.d/99-ragin-hardening.conf` on CORE/EDGE | Password auth already off; root key login, forwarding, X11, and loose limits remained | Add reversible key-only SSH hardening snippet; syntax-check and reload | **Authorized reversible host action** | `sshd -T` shows root/password/forwarding/X11 disabled and bounded limits | SSM command success plus fresh SSH and SSM identity checks on each host | No interruption; restore `/var/backups/ragin/sshd-hardening-prestate*` and reload |
| 2026-10-08T22:11:58+03:00 / 22:12:21+03:00 | UFW on CORE/EDGE | Inactive; host ingress permissive | Backup UFW state; deny incoming; allow operator `/32` TCP/22; keep outgoing allow | **Authorized reversible host action** | UFW active; incoming denied except operator SSH; outgoing unchanged | Host readback plus fresh SSH and SSM sessions passed | No interruption; restore `/var/backups/ragin/ufw-prestate` and disable UFW |
| 2026-10-08T22:12:42+03:00 / 22:12:44+03:00 | EC2 metadata options on CORE/EDGE | IMDSv2 required, hop limit 2 | Set hop limit to 1; retain IMDSv2 and endpoint for SSM role credentials | **Authorized reversible AWS action** | Both show `HttpTokens=required`, endpoint enabled, hop limit 1 | EC2 readback and both SSM nodes remained `Online` | No direct charge; restore hop limit 2 only under incident/recovery decision |
| 2026-10-08T19:13Z (recorded) | Local service-auth test only | No deployed EDGE-to-CORE listener | Generate ephemeral test CA/certs in temporary storage and exercise mTLS | No AWS mutation | Authorized client passed; rogue client certificate rejected; keys temporary only | Local loopback test passed | No AWS cost; temporary test material was not stored in repository |

## Applied first mutation

| Resource | Proposed change | Approval | Risk | Rollback | Verification |
|---|---|---|---|---|---|
| `sg-077b8f78668f4f646` on EDGE only | Add verified operator TCP/22 `/32`, verify fresh SSH, then remove public TCP/22, TCP/80, TCP/443; leave egress unchanged | **APPROVED and VERIFIED** | Lockout risk was controlled by source confirmation, add-first ordering, and two fresh SSH checks | Restore the captured pre-state ingress rules from the control plane if explicitly required; rollback was not needed | SG read-back, two fresh SSH checks, instance/ENI/status checks, no resource changes |

The approved row was executed. Approval for this row did not approve any other row in Task 3.6.

## Overnight staging additions

| UTC timestamp | Resource | Before state | Applied change | Approval | After state | Validation | Cost / interruption / rollback |
|---|---|---|---|---|---|---|---|
| 2026-10-08T20:20:45Z–20:24:09Z | `eice-023d2c69cb6690c48`, subnet `subnet-07fae34b3db734bb2` | No EC2 Instance Connect Endpoint | Create one RAGIN-only EIC endpoint in the prepared private subnet, with `PreserveClientIp=false` and dedicated SG `sg-05f6e3f406f0c9be2` | Authorized by the overnight execution plan after cost review; no fixed endpoint charge expected per AWS documentation | `create-complete`; ENI `eni-097341d0d05830cbe`, source IP `172.31.61.22` | Fresh CORE SSH over `aws ec2-instance-connect open-tunnel` succeeded as `ubuntu`; existing public SSH and SSM remained available | No fixed endpoint charge expected; cross-AZ transfer remains possible. Rollback is delete endpoint only after verifying existing SSH/SSM, then revoke endpoint SG ingress/egress rules. |
| 2026-10-08T20:25Z | CORE UFW | Operator SSH and EDGE mTLS rules only | Add `22/tcp` allow from exact EIC ENI IP `172.31.61.22` | Authorized reversible RAGIN host hardening | UFW active with operator `/32`, EDGE `8443`, and EIC SSH rules | First EIC tunnel timed out before rule; fresh tunnel then authenticated and returned CORE hostname/user | No charge or observed interruption. Rollback: `sudo ufw delete allow from 172.31.61.22 to any port 22 proto tcp`. |

The EIC endpoint branch did not move, stop, replace, or terminate either EC2 instance and did not alter EDGE ingress, shared VPC routes, IAM, storage, or outbound rules.

## Deferred change families

CORE migration, SG/NACL egress, EBS encryption, Flow Logs/CloudTrail, Docker/Cowrie deployment, and gateway remediation remain deferred. SSM/IAM, metadata, host SSH, UFW ingress, and local mTLS validation are now applied and recorded above. CORE migration and any paid or disruptive branch still require separate review.
