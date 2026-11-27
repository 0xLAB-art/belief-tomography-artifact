# RAGIN Task 3: Security-Group and IAM Policy

This is a proposed policy, not an applied AWS configuration. Actual rule IDs and instance profiles must be filled from an authorized read-only inventory before approval.

## Observed bindings before policy changes

AWS CLI inspection observed both nodes in `vpc-044a70ed680faff8b`, with `launch-wizard-3` (`sg-03486d70769d21e4e`) on CORE and `launch-wizard-4` (`sg-077b8f78668f4f646`) on EDGE. CORE allows TCP/22 from one `/32` operator source and all egress; EDGE allows TCP/22, 80, and 443 from `0.0.0.0/0` and all egress. The default NACL allows all ingress and egress. These are current rules, not the proposed policy below.

## Security groups

### `sg-ragin-edge`

| Direction | Protocol/port | Source/destination | Decision |
|---|---|---|---|
| Inbound | TCP/22 | `0.0.0.0/0` and approved IPv6 range only if required | Allow to EDGE public interface for Cowrie listener; host sshd must not bind this path |
| Inbound | Management | Overlay/SSM only | Allow only after operator path is proven; no public SSH admin rule |
| Inbound | All other | Any | Deny by absence |
| Outbound | TCP to CORE controller port | `sg-ragin-core` reference, private route | Allow only authenticated EDGE-to-CORE transport |
| Outbound | UDP/TCP 53 | VPC resolver or approved resolver | Allow only if needed for operation; log and rate-limit |
| Outbound | NTP | approved time source | Allow only if needed |
| Outbound | Other | Any | Deny by removing default allow-all egress; host/container firewall is also required |

### `sg-ragin-core`

| Direction | Protocol/port | Source/destination | Decision |
|---|---|---|---|
| Inbound | TCP/controller port | `sg-ragin-edge` only | Allow mTLS controller requests |
| Inbound | Management | operator overlay or SSM path only | Allow only after the alternate access path is verified |
| Inbound | All other | Any | Deny by absence |
| Outbound | LOCAL overlay | fixed authenticated peer or overlay interface | Allow when Laya is enabled; no attacker-originated route |
| Outbound | Logging/time/DNS | explicit AWS/VPC endpoints or approved destinations | Allow only what is needed and cost-approved |
| Outbound | Other | Any | Deny by default; do not add NAT merely to make providers convenient |

Do not use a wide CIDR rule between the zones when an SG reference is possible. SGs are stateful and cannot express every host/container policy; enforce the same intent with host firewall rules, Docker network configuration, and application authentication.

## Network ACL and host policy

Use NACLs as a coarse subnet backstop, not as the only policy. They are stateless, so return traffic must be explicitly considered. On each host, enforce default-deny inbound and narrow outbound policy with a tested firewall. `scripts/field_provision.sh:17-54` is an existing single-host starting point, not a substitute for this two-subnet policy; it currently defaults UFW outbound to allow and relies on DOCKER-USER rules.

## IAM instance profiles

Current `describe-instances` returned no `IamInstanceProfile` for either target, and `ssm describe-instance-information` returned no registered target. The installed SSM Agent is therefore not evidence of an operational management path. Any future profile must be explicitly approved, least-privilege, and validated before public SSH is removed.

| Principal | Required permissions | Must not have |
|---|---|---|
| EDGE instance role | Prefer none. If logs are required, write only to one pre-created CloudWatch log group/stream namespace. | `iam:*`, `ec2:*`, SG/VPC mutation, S3 broad access, Secrets Manager access, KMS decrypt, role passing, termination, snapshots |
| CORE instance role | Minimal CloudWatch write and, only if selected, SSM managed-instance permissions. | IAM/EC2/network mutation, broad S3, arbitrary KMS decrypt, provider-secret administration |
| Operator role | Separate human role for approved infrastructure changes and emergency isolation; MFA and short-lived credentials. | Permanent keys on either instance; shared application secrets |
| Local Laya operator/service | No AWS role by default. | AWS credentials copied to workstation services or model prompts |

If application secrets must be retrieved from AWS, use a resource-scoped secret and KMS key with an explicit deny for other resources. The free/credit-constrained baseline should avoid introducing Secrets Manager, NAT, or endpoint charges without approval; an encrypted operator-injected file or approved Parameter Store design must still have rotation and access evidence.

## Metadata and role rules

- Set `HttpTokens=required` and `HttpPutResponseHopLimit=1` on both instances unless a tested container design demonstrates why a different hop limit is unavoidable.
- Disable IMDS on EDGE if no AWS API is needed. If a role is present, remove it before field exposure or prove the minimum policy and container blocking.
- Never rely on IAM to stop SSRF from reaching metadata. Apply IMDS endpoint configuration plus host/container egress controls and negative tests.
- Disable IPv6 or apply equivalent explicit rules if IPv6 is not part of the tested design; an IPv4-only SG does not protect an open IPv6 path.

## Cost and lockout notes

Deleting default egress, removing public SSH, and changing metadata options can cause outage or operator lockout. Pre-stage an alternate operator session and capture the current rules before approval. No SG, IAM, route, or metadata changes were made in Task 3.
