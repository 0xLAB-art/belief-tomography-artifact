# RAGIN Task 3: AWS Current-State Audit

**Audit date:** 2026-10-08

**Disposition:** Instance-local state and the core EC2/VPC control-plane inventory are **VERIFIED** through the supplied SSH sessions and authorized AWS CLI. Effective IAM policy, independent external reachability, logging delivery, billing completeness, and deployment safety remain **UNVERIFIED**. These observations do not establish a safe deployment.

## Evidence boundary

The initial non-printing `aws sts get-caller-identity --query Account --output text` probe returned `rc=255` before the user refreshed the configured session. The user then authorized the configured `default` profile, after which the same identity check succeeded and the read-only EC2/VPC/IAM-adjacent API calls below completed. The SSH sessions used only read-only host commands and IMDS metadata reads. No credentials, private-key contents, or session tokens were printed or persisted.

The user-provided statement that two instances exist in `eu-north-1` is corroborated by the authorized AWS CLI inventory and the SSH/IMDS observations below.

## Verified through SSH read-only sessions

The following values were read from IMDSv2 and the host operating systems on 2026-10-08. Resource identifiers and addresses are retained here because they are necessary for the change-control record; no credential material was collected.

| Node | Instance ID | Type | AMI | AZ | VPC / subnet | Private / public IPv4 | Security group | Root volume observed |
|---|---|---|---|---|---|---|---|---|
| RAGIN-CORE | `i-062a400b300f4f9e4` | `m7i-flex.large` | `ami-0aba19e56f3eaec05` | `eu-north-1a` | `vpc-044a70ed680faff8b` / `subnet-0f8d7698fde97f83b` | `172.31.17.217` / `REDACTED_FLEET_HOST` | `launch-wizard-3` / `sg-03486d70769d21e4e` | 40 GiB ext4 root |
| RAGIN-EDGE | `i-05bc6aab0bd4260a7` | `t3.micro` | `ami-0aba19e56f3eaec05` | `eu-north-1b` | `vpc-044a70ed680faff8b` / `subnet-04d02e21747154d7a` | `172.31.35.203` / `REDACTED_FLEET_HOST` | `launch-wizard-4` / `sg-077b8f78668f4f646` | 20 GiB ext4 root |

Both hosts had a default route through their respective `172.31.x.1` gateway and an active `sshd` listener on `0.0.0.0:22` and `[::]:22`. This is direct evidence that the current administrative SSH surface is public-facing on both nodes; it is not Cowrie isolation.

| Host control | RAGIN-CORE | RAGIN-EDGE | Interpretation |
|---|---|---|---|
| Docker | Binary absent | Binary absent | No Cowrie/RAGIN container is currently evidenced by the host inspection. |
| UFW | `ufw status: inactive` | `ufw status: inactive` | Host UFW is not enforcing the intended policy. |
| iptables base policy | `INPUT/FORWARD/OUTPUT ACCEPT` | `INPUT/FORWARD/OUTPUT ACCEPT` | No default-deny host firewall was observed. |
| IMDSv2 | Token available | Token available | IMDS is reachable; negative metadata tests and hop-limit settings remain unverified. |
| IMDS IAM metadata | HTTP 404 | HTTP 404 | No role metadata was returned at inspection time; AWS profile attachment still needs control-plane verification. |
| SSM Agent | Snap installed and active | Snap installed and active | Agent presence is verified; Session Manager registration/connectivity is not. |
| CloudWatch Agent | Inactive | Inactive | No active CloudWatch agent was observed. |
| Public listener | Ubuntu `sshd` on 22 | Ubuntu `sshd` on 22 | Current EDGE is not a Cowrie endpoint. |

## Verified AWS control-plane state

The authorized `default` profile successfully read the following AWS resources in `eu-north-1` on 2026-10-08:

| Control | Observed state | Security meaning |
|---|---|---|
| VPC | Default VPC `vpc-044a70ed680faff8b`, CIDR `172.31.0.0/16`, Internet Gateway Block Mode `off` | Not a dedicated protected VPC. |
| Subnets | CORE `172.31.16.0/20`, EDGE `172.31.32.0/20`; both `MapPublicIpOnLaunch=true` | Both are public-addressing subnets; CORE is not a private-subnet placement. |
| Route table | Main table `rtb-0fb03d7badfcc25c6` associated with both target subnets; `0.0.0.0/0 -> igw-0168696c5dc43baee` | Both subnets have direct Internet Gateway routing. |
| CORE security group | `launch-wizard-3`: TCP/22 from one `/32` operator source; egress `0.0.0.0/0` all protocols | SSH is narrowed by SG, but CORE remains publicly addressed and unrestricted outbound. |
| EDGE security group | `launch-wizard-4`: TCP/22, TCP/80, TCP/443 from `0.0.0.0/0`; egress `0.0.0.0/0` all protocols | EDGE is broadly internet-exposed at the SG layer, including unused web ports. |
| Default NACL | `acl-0f6784f313451212c`, associated with both target subnets; ingress and egress rule 100 allow `0.0.0.0/0` all protocols | No subnet-level deny backstop exists. |
| VPC Flow Logs | None returned for the VPC | No verified network-flow evidence or alert source. |
| VPC endpoints | None returned for the VPC | SSM/private service access is not provided by VPC endpoints. |
| Instance profiles | No `IamInstanceProfile` in either instance description | No attached EC2 role was observed; SSM Agent is therefore not registered. |
| SSM | `describe-instance-information` returned no target instances | Agent presence on-host does not provide Session Manager access. |
| Root EBS | CORE `vol-0537ee06e67f63cc5`, 40 GiB gp3, `Encrypted=false`; EDGE `vol-05925e722a36cd345`, 20 GiB gp3, `Encrypted=false` | At-rest protection is absent on both roots. |
| CloudTrail trails | `describe-trails` returned an empty trail list | No account trail was configured in the inspected region/account; Event History status was not separately audited. |
| Cost Explorer | 2026-10-01 through 2026-10-09 unblended total returned USD `0.000000` | Billing data may lag; this is not a guarantee of zero future/current charges. |

## Repository evidence

| Question | What the repository proves | What remains unknown |
|---|---|---|
| Current EC2 instances | No current instance inventory artifact exists in the repository. | AWS control-plane state, tags, tenancy, launch details, and authoritative running-state record. SSH/IMDS values are recorded above. |
| Region and placement | The task specifies `eu-north-1`; repository files do not verify it. | Route-table target, IGW association, subnet public/private classification, and NACLs. VPC, subnet, AZ, and addresses are observed above through IMDSv2. |
| Current cloud deployment | `PROJECT_STATUS.md:1-10` describes the active Plan B stack as tailnet-only and the old AWS VPS deployment as historical. | Whether the user-created EC2 instances are empty, running, or hosting any RAGIN services. |
| AWS network boundary | No Terraform, CloudFormation, CDK, Pulumi, or AWS-specific provisioning file was found. | SG/NACL rules, VPC flow logs, network ACLs, peering, endpoints, and routes. |
| EDGE/CORE application split | `docker-compose.field.yml:49-160` is a one-host Docker bridge layout. Its `internal: true` network and comments are not an AWS subnet boundary. | Whether EDGE and CORE are actually separated at the VPC layer. |
| Administrative access | `scripts/field_provision.sh:14-24` proposes Tailscale-only host management for field endpoints. | Public Ubuntu SSH is confirmed on both nodes; SSM Agent is active, but registration and operator-only access are unverified. |
| Metadata and IAM | No AWS instance-profile or IMDS configuration is present in the repository. | Profile ARN/effective policies, IMDS hop limit/endpoint setting, and any control-plane permissions. IMDSv2 token availability is observed above. |
| Storage | The repository documents local Docker volumes and JSONL/session persistence, but not EC2 volumes. | EBS volume IDs, encryption/KMS keys, snapshots, and retention; root filesystem sizes/mounts are observed above. |
| Logging | Docker logging and application exports are described in `docker-compose.field.yml:36-40,143-146` and `docs/FIELD_ETHICS.md:26-35`. | CloudWatch agent was inactive on both hosts; log groups, VPC Flow Logs, delivery, encryption, retention, and alerting remain unknown. |
| Cost posture | Cost Explorer returned USD `0.000000` unblended for 2026-10-01 through 2026-10-09; public IPv4s and the `m7i-flex.large` remain cost-sensitive dependencies. | Billing lag, credits/free-tier treatment, future usage, and service-level charges. |

## Exact console/API verification checklist

Run this checklist from an explicitly authorized operator session. Save only redacted, least-necessary evidence: resource type, state, IDs if required for the change record, and rule summaries. Do not save credential material or full environment dumps.

1. **EC2 inventory:** EC2 Console → Instances → filter tags `Name=RAGIN-EDGE` and `Name=RAGIN-CORE`; record instance ID, state, type, AMI, AZ, VPC, subnet, public IPv4/DNS, private IPv4, IAM role, and launch template.
2. **Subnets/routes:** VPC Console → Subnets and Route Tables; record whether each subnet is public or private by route target, not by name. A public subnet has a route to an Internet Gateway; a private subnet has no direct IGW route.
3. **Security groups/NACLs:** record inbound and outbound rules, referenced SGs, IPv4/IPv6 ranges, and whether default allow-all egress remains.
4. **IGW and alternate paths:** record IGW, NAT Gateway, egress-only IGW, VPC peering, Transit Gateway, VPN, and endpoint routes.
5. **IAM:** record instance-profile names and effective policy summaries. Confirm neither instance can mutate IAM, SGs, routes, snapshots, or terminate itself. The current read returned no instance profile for either target, so verify whether SSM is intentionally unsupported or needs an approved least-privilege role.
6. **Metadata:** EC2 → Instance settings → Modify instance metadata options. Require IMDSv2, set hop limit to 1 unless a documented container exception is proven, and disable the endpoint on EDGE if its software has no AWS API need.
7. **EBS:** record encryption status, KMS key class, root/data volumes, mount points, and snapshot policy. Do not copy volume contents during this audit.
8. **Access:** record whether public TCP/22 exists. Confirm the administrative path independently before any SSH rule change; prefer SSM or an operator-only overlay.
9. **Logs:** confirm VPC Flow Logs, CloudTrail management events, EC2 system/application logs, and retention/alert destinations. The current read returned no VPC Flow Logs and no configured CloudTrail trails.
10. **Cost:** inspect Cost Explorer/Billing for NAT, public IPv4, interface endpoints, EBS, data transfer, and logging charges before approval.

## Evidence classification

- **Verified in this task:** repository source and documentation facts cited above; authorized AWS CLI identity; EC2/VPC/subnet/route/IGW/SG/NACL/volume/flow-log/endpoint/SSM/trail reads; IMDSv2-backed host observations; SSH listeners; host firewall status; Docker absence; SSM Agent presence; and Cost Explorer response.
- **Not verified:** effective IAM permissions beyond the absence of an instance profile, IMDS hop-limit enforcement from attacker-controlled containers, CloudWatch delivery, billing completeness, Session Manager registration beyond the empty API result, and application reachability from an independent external source.
- **Not a test result:** repository intent comments, Docker `internal: true`, historical deployment notes, or the presence of an SSM Agent without a verified Session Manager connection.

## Immediate risk conclusion

CORE is confirmed to be in a public-addressing subnet with a direct IGW route and public IPv4. EDGE has internet-wide SG ingress on 22/80/443 and exposes Ubuntu `sshd` on public TCP/22, not Cowrie. Both hosts show permissive host firewall defaults and no Docker runtime; both roots are unencrypted and no flow logs are configured. The system is not approved for field exposure. The highest-risk findings are public CORE reachability, public administrative SSH, unrestricted SG/NACL/host egress, reachable IMDS with hop limit 2, missing container isolation, and lack of a tested EDGE-to-CORE authenticated transport.
