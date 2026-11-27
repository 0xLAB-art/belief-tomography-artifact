# RAGIN Task 3.6: Live Security Validation

## Read-only preflight results

| Test | Result | Evidence boundary |
|---|---|---|
| Both target instances exist and are running | PASS | AWS `describe-instances`; IDs and state recorded in `AWS_BEFORE_STATE.md` |
| Operator can reach both hosts | PASS | Supplied SSH paths opened read-only sessions; active source matched the existing CORE admin `/32` |
| EDGE public web listeners absent | PASS for host listeners only | `ss` showed no host 80/443 listener; SG still allowed those ports, so internet reachability was not independently scanned |
| EDGE is Cowrie, not Ubuntu sshd | FAIL | Public bind `0.0.0.0:22` and `[::]:22` belonged to Ubuntu `sshd`; Docker absent and Cowrie inactive |
| CORE is private | FAIL | Public IPv4, public-mapping subnet, and direct IGW default route |
| Host egress is restricted | FAIL | UFW inactive and iptables default ACCEPT on both hosts |
| IMDS is unreachable to a future attacker container | INCOMPLETE | Host IMDSv2 token obtained; no Docker/container test existed |
| SSM administration works | INCOMPLETE | Agent active, but AWS SSM managed-instance query returned no targets |
| Roots are encrypted | FAIL | Both attached root volumes report `Encrypted=false` |
| Flow/audit telemetry is protected | INCOMPLETE | No VPC Flow Logs/trails returned; CloudWatch agent inactive; restart durability not tested |

No external attack scan, public honeypot connection, upload, payload, or third-party target contact was performed.

## Approved EDGE SG batch validation

**Recorded UTC:** 2026-10-08T18:48:29Z (post-change readback)

| Check | Result | Evidence |
|---|---|---|
| SG attachment is EDGE-only | PASS | `sg-077b8f78668f4f646` was attached to exactly the RAGIN-EDGE ENI in the inspected result |
| Operator source confirmed | PASS | Current public IPv4 `REDACTED_OPERATOR_HOST` matched the intended `/32` and active EDGE SSH peer |
| Restricted SSH added before removal | PASS | TCP/22 `/32` rule was added and read back before public-rule removal |
| Fresh SSH before removal | PASS | Independent fresh connection returned `EDGE_FRESH_PRE_REVOKE ip-172-31-35-203` |
| Public rules removed | PASS | Only approved SG ingress mutation removed public TCP/22, TCP/80, and TCP/443 |
| Fresh SSH after removal | PASS | Independent fresh connection returned `EDGE_FRESH_POST_REVOKE ip-172-31-35-203` |
| Final inbound rules | PASS | Exactly TCP/22 from `REDACTED_OPERATOR_HOST/32`; no other IPv4, IPv6, or SG-reference ingress |
| Instance/health stability | PASS | EDGE remained running, attached to the approved SG, and instance/system status checks were `ok` |

This proves administrative ingress containment for the approved rule set. It does not prove Cowrie isolation, CORE privacy, egress control, metadata isolation, mTLS, or public-deployment readiness.

## Remaining live checks

After the exact SG batch is approved, run only these owned-resource checks:

1. Re-read the SG and confirm one inbound TCP/22 rule for the verified operator `/32`, with no 80/443 ingress and no public 22 ingress.
2. Open a fresh authorized SSH connection while the original session remains available.
3. Re-read instance state, ENI, SG attachment, and system/status checks.
4. Confirm no resource was created, replaced, stopped, or terminated.
5. Record the UTC result and any interruption in `CHANGE_AND_ROLLBACK_LOG.md`.

This will validate administration containment only. It will not establish Cowrie isolation, CORE privacy, egress control, metadata isolation, mTLS, or public-deployment readiness.

## Phase B SSM preflight

**Recorded UTC:** 2026-10-08T18:59:31Z

| Check | Result | Evidence |
|---|---|---|
| Instance profiles | FAIL / prerequisite missing | Both EC2 descriptions returned no `IamInstanceProfile` |
| SSM registration | FAIL / prerequisite missing | `describe-instance-information` returned an empty list for both IDs |
| SSM Agent | PASS for presence/service | Snap agent `3.3.4121.0`, service active on both hosts |
| Regional SSM HTTPS | PASS for reachability | Host probes and `ssm-cli` diagnostics reached SSM, SSMMessages, and EC2Messages |
| SSM credentials | FAIL | `ssm-cli` reported no EC2 instance role found on both hosts |
| Private endpoint path | NOT PRESENT | No VPC endpoints; current path uses direct internet egress |
| SSH continuity | PASS | Existing CORE and restricted EDGE SSH paths remain available |

## Post-approval SSM acceptance procedure

After explicit approval, create/attach only the documented role/profile, then:

1. Re-read IAM role/profile and both EC2 associations.
2. Poll `describe-instance-information` until both IDs are `Online` with recent ping times.
3. Run `aws ssm start-session --target i-062a400b300f4f9e4` and independently verify the CORE hostname/instance ID.
4. Run the same command for EDGE and verify its hostname/instance ID.
5. Terminate both sessions and confirm SSM status remains `Online`.
6. Re-test both existing SSH paths.

Agent installation, an attached role, or endpoint reachability alone is not a PASS.

## Final SSM result

The post-approval procedure passed for both nodes. `aws ssm start-session` using `AWS-StartInteractiveCommand` returned the expected IMDS instance ID and hostname for CORE and EDGE, each session exited successfully, both nodes remained `Online`, and fresh SSH access remained successful. This is direct Session Manager evidence, not an inference from configuration.
