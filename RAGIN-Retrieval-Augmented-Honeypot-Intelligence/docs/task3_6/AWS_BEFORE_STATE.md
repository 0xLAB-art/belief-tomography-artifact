# RAGIN Task 3.6: AWS Before-State Inventory

**Inspection timestamp:** 2026-10-08T18:44:05Z
**Region:** `eu-north-1`
**Scope:** read-only AWS CLI and read-only SSH inspection. No AWS or host mutation was performed.

## Evidence boundary

The AWS CLI used the configured `default` profile and returned an STS assumed-role identity (`AccountFullAccessRole`). Credential values were not printed or persisted. The identity is privileged and should not be treated as a least-privilege deployment identity. The current STS ARN was not copied into this artifact.

Both supplied SSH paths were usable before any proposed access-control change. The SSH source observed in the established sessions matched the existing CORE administration `/32`; the literal address is intentionally not repeated here.

## EC2 inventory

| Node | Instance | State/type | AMI/AZ | VPC/subnet | Subnet CIDR / public mapping | Private / public IPv4 | ENI / SG | Root volume |
|---|---|---|---|---|---|---|---|---|
| CORE | `i-062a400b300f4f9e4` | running / `m7i-flex.large` | `ami-0aba19e56f3eaec05` / `eu-north-1a` | `vpc-044a70ed680faff8b` / `subnet-0f8d7698fde97f83b` | `172.31.16.0/20` / map public `true` | `172.31.17.217` / `REDACTED_FLEET_HOST` | `eni-01b8030cd6c9e377d` / `sg-03486d70769d21e4e` | `vol-0537ee06e67f63cc5`, 40 GiB gp3, encrypted `false` |
| EDGE | `i-05bc6aab0bd4260a7` | running / `t3.micro` | `ami-0aba19e56f3eaec05` / `eu-north-1b` | `vpc-044a70ed680faff8b` / `subnet-04d02e21747154d7a` | `172.31.32.0/20` / map public `true` | `172.31.35.203` / `REDACTED_FLEET_HOST` | `eni-05e4944a0b96a8fa0` / `sg-077b8f78668f4f646` | `vol-05925e722a36cd345`, 20 GiB gp3, encrypted `false` |

Neither instance has an attached IAM instance profile. Both have `SourceDestCheck=true`. Both use IMDSv2-required metadata options, but the endpoint remains enabled and the hop limit is `2`.

## Network and control-plane state

| Control | Observed state | Security meaning |
|---|---|---|
| VPC | Default VPC `172.31.0.0/16`, internet-gateway block mode `off` | Not a purpose-built isolated research VPC |
| Internet gateway | `igw-0168696c5dc43baee` attached and available | Direct internet path exists |
| Route table | Main `rtb-0fb03d7badfcc25c6`; local route plus `0.0.0.0/0 -> igw-0168696c5dc43baee` | Both default-VPC subnets inherit a direct IGW route; CORE is not private |
| Default NACL | `acl-0f6784f313451212c`, associated with both target subnets and another subnet | Rule 100 allows all ingress and egress; do not edit without shared-resource analysis |
| CORE SG | `launch-wizard-3` / `sg-03486d70769d21e4e`; TCP/22 from one operator `/32`; all egress | Inbound is narrow but public-subnet placement remains |
| EDGE SG | `launch-wizard-4` / `sg-077b8f78668f4f646`; TCP/22, 80, 443 from `0.0.0.0/0`; all egress | Internet-wide administration/web exposure |
| SG attachment check | Each target SG was found on exactly its corresponding target ENI in the inspected result | The proposed EDGE SG rule change is not shared with another inspected ENI |
| VPC Flow Logs | None returned for the VPC | No network-flow evidence currently configured |
| VPC endpoints | None returned for the VPC | SSM private access is not provisioned |
| CloudTrail trails | None returned by `describe-trails` | No configured trail was observed in this account/region; Event History was not treated as equivalent |
| SSM registration | `describe-instance-information` returned an empty list for both IDs | Session Manager access is not established |
| Cost Explorer | Daily unblended amount was `0 USD` for 2026-10-01 through 2026-10-07 | Useful observation only; billing lag, credits, and future charges remain possible |

## Host inspection

| Node | SSH/listeners | Firewall | Runtime / deception | Management/logging |
|---|---|---|---|---|
| CORE | Ubuntu `sshd` on `0.0.0.0:22` and `[::]:22`; current operator session established | UFW inactive; iptables policies INPUT/FORWARD/OUTPUT `ACCEPT`; nftables ruleset empty in the inspected output | Docker command absent; Cowrie inactive | SSM snap service active; CloudWatch agent inactive |
| EDGE | Ubuntu `sshd` on `0.0.0.0:22` and `[::]:22`; current operator session established | UFW inactive; iptables policies INPUT/FORWARD/OUTPUT `ACCEPT`; nftables ruleset empty in the inspected output | Docker command absent; Cowrie inactive | SSM snap service active; CloudWatch agent inactive |

Both hosts returned an IMDSv2 token. The instance IAM-info endpoint returned HTTP 404, consistent with no attached instance profile, but this is not a substitute for an effective IAM policy review. No application or public web listener was observed on EDGE; public TCP/22 nevertheless reaches the real Ubuntu SSH daemon.

## Not established by this preflight

Independent external negative reachability tests, effective IAM permissions, CloudWatch delivery, a Session Manager login, metadata behavior from a future container, protected audit storage, emergency isolation, and the Rust gateway authentication contract remain unverified. No public honeypot listener was opened.
