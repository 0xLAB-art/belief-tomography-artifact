# RAGIN V4 Live-Capture Deployment Readiness

## Scope and frozen status

This is a read-only safety, cost, provenance, and deployment design audit. The readiness freeze and acquisition-start hashes verify, but no AWS or network change was made, no public port was opened, no real acquisition began, and no V4 policy or reference process ran.

The current AWS CLI session is expired. Therefore the live AWS state is `UNKNOWN`; the infrastructure statements below distinguish that from the last documented read-only inventory dated 2026-10-11.

## Current infrastructure

The last documented EDGE was a running `t3.micro` with public IPv4 `REDACTED_FLEET_HOST`, private address `172.31.35.203`, and SSM Online. Cowrie was observed through a host `twistd` process with configuration listening on `0.0.0.0:2222`, loopback/socat forwarding, and JSON logging. Ordinary `sshd` occupied `0.0.0.0:22`. The EDGE security group had management ingress but no public honeypot ingress. Consequently public Cowrie exposure is not established and TCP/22 cannot be opened until the operator-SSH conflict is resolved.

The last documented CORE was a running `m7i-flex.large` in a public subnet with a private listener on `172.31.17.217:8443`. CORE is not required for capture-only controlled Cowrie collection and should not be made public for this purpose. The existing private subnet, local-only route table, and EIC endpoint are useful for a later separately approved CORE migration, not a prerequisite here.

## Minimum public surface

The preferred final surface is one EDGE TCP/22 listener terminating in an isolated Cowrie service. Operator access must first be moved to a verified EIC/Tailscale-only path; public `sshd` must not share TCP/22 with Cowrie. Only TCP/22 should be public. No CORE, retrieval, decision, model, control, or management service should be public.

This is a proposed change only. It is not safe to add an SG rule while ordinary SSH remains on the public listener.

## Egress safety

The last documented EDGE and CORE security groups allowed all outbound protocols to `0.0.0.0/0`, and the default NACL was allow-all. The deployment must therefore add a host/container boundary before exposure: Cowrie receives default-deny NEW egress, explicit denial for `169.254.169.254`, private VPC ranges, CORE/control/operator services, and no outbound bridge in capture-only mode. IMDSv2 must remain required for any EC2 management use, but the honeypot must not be able to reach IMDS at all.

The existing Docker field design documents an internal network and DOCKER-USER rules, but the last documented EDGE used a host Cowrie process. That control cannot be assumed to protect the host process without an isolation change.

## Capture integration

The frozen `capture_v4` package can create and validate manifests, seal raw files, derive canonical records, apply privacy minimization, verify lineage, and append the metadata-only registry. The missing production hook is a native Cowrie session-close finalizer. It must segment one native session into an immutable raw artifact and run the sequence:

`native Cowrie session -> raw segment -> manifest -> raw hash -> privacy -> canonical record -> lineage verification -> registry`

The serving or decision path must not create provenance. Capture-only mode should not depend on CORE.

## Crash, rotation, and disk-full handling

Session-close finalization must use temporary files, flush/sync, and atomic rename. A restart must recover only from an immutable raw segment. Missing events, lost manifests, invalid timestamps, hash mismatch, privacy failure, or disk-full interruption produce an ineligible audit row. No manual repair may promote a record unless deterministic reconstruction from the immutable raw source succeeds.

## Storage

Using a conservative planning envelope of 520 attempted sessions, 10 MiB raw/session, 0.2 GiB manifests/canonical/registry, and 3 GiB rotation/OS overhead gives approximately 8–12 GiB. The last documented EDGE root was 20 GiB, but live free space is unknown. Collection must stop before free space falls below 8 GiB. This is a planning estimate, not a guarantee of capacity.

## Cost

The smallest design reuses the existing EDGE and proposes no new EC2, EBS, public IPv4, NAT Gateway, load balancer, or managed logging resource. Known incremental resource cost is therefore $0/day, $0/week, and $0/30 days; this excludes the existing EDGE bill, taxes/credits, and variable data transfer, which are unknown without a current account session. Historical repository pricing recorded `m7i-flex.large` at $0.0336/hour and gp3 at $0.08/GB-month, but those figures are not a current account quote. AWS publishes region-specific EC2 and EBS pricing and notes that listed instance prices are region-dependent; [EC2 On-Demand pricing](https://aws.amazon.com/ec2/pricing/on-demand/) and [EBS pricing](https://aws.amazon.com/ebs/pricing/) should be rechecked after reauthentication.

## Controlled-admin option

Up to 40 sessions may later be collected in a real isolated Linux environment using the same capture manifest and one native session per independence group. Routine legitimate categories may include service inspection, package inventory, filesystem/navigation checks, process/resource inspection, log inspection, and bounded network configuration inspection. No LLM generation, replay, benchmark fixture, semantic selection, or policy observation is permitted.

## Ethics and data handling

The proposal is consistent with the existing field ethics documentation: no retaliation, no active exploitation of visitors, no uncontrolled outbound capability, no production credentials, and collection limited to the authorized research boundary. Raw source IPs must not enter research artifacts; source clusters use keyed HMAC only. Credential material is redacted or keyed-hashed where necessary. Deployment controls still require live re-verification before approval.

## Required changes and rollback

The exact proposed changes, security rationale, cost impact, and rollback procedures are recorded in `v4_live_capture_proposed_changeset_v1.json`. No item was executed. The highest-risk changes are public EDGE exposure, operator SSH migration, egress isolation, and native Cowrie finalizer integration.

## Approval gate

`BLOCKED_FOR_LIVE_CAPTURE`.

Before any deployment, the user must explicitly approve public EDGE exposure, AWS/network or host-firewall changes, and the estimated cost boundary. Reauthentication is also required for a fresh AWS read-only audit.
