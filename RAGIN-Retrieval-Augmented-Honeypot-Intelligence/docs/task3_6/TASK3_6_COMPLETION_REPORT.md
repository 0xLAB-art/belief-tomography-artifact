# RAGIN Task 3.6 Completion Report

## Status

**PARTIAL — APPROVED CHANGES VERIFIED**

The required read-only preflight and approval-ready remediation plan are complete. The explicitly approved EDGE inbound security-group batch was applied and independently validated. The AWS environment is not safe for public honeypot exposure.

## Initial security posture

- Both instances are running in the default VPC with public-addressing subnets and a direct IGW default route.
- CORE has a public IPv4 and narrow SSH ingress, but it is not in a private-subnet boundary.
- EDGE has internet-wide TCP/22, 80, and 443 ingress; public TCP/22 reaches real Ubuntu `sshd`, not Cowrie.
- Docker and Cowrie were absent at inspection time; no public deception service is deployed.
- Both hosts have inactive UFW and permissive iptables base policies. AWS egress and the shared default NACL are allow-all.
- Both root EBS volumes are unencrypted. No VPC Flow Logs or configured CloudTrail trails were observed. SSM registration is absent despite an active agent.
- IMDSv2 is required, but the endpoint is enabled and hop limit 2. Neither instance has an IAM profile.
- Rust gateway request authentication remains unresolved and is excluded from the future field dependency path.

## Changes actually performed

Only the approved inbound change to EDGE security group `sg-077b8f78668f4f646` was performed: TCP/22 was restricted to the verified operator `REDACTED_OPERATOR_HOST/32`, and public TCP/22, TCP/80, and TCP/443 were revoked. Egress was unchanged. No route, NACL, IAM, metadata, EBS, host-firewall, Docker, or application mutation occurred. No public port was opened and no container was deployed.

## Confirmed improvement

EDGE administrative ingress is no longer internet-wide, and the unused public web ingress rules are removed. Two independent fresh SSH connections succeeded after the rule sequence, and final SG read-back contains exactly the operator TCP/22 `/32` rule. There was no observed service interruption and no direct AWS charge.

## Phase B SSM administration status

The Phase B preflight at 2026-10-08T18:59:31Z found both SSM agents active at version `3.3.4121.0`, all three required regional HTTPS endpoints reachable, and no instance profiles or SSM managed-node registrations. The approved role/profile was then created and associated, CORE's SSM agent was restarted, and both nodes became `Online`. Independent Session Manager identity checks and existing SSH checks passed. The final role/profile evidence is in `AWS_ADMIN_IDENTITY_AND_SSM.md`.

## Verification and access

The AWS identity was an assumed `AccountFullAccessRole` session; no secrets were printed. EDGE remains accessible through the restricted SSH path. CORE SSH access was not changed. Both hosts remained running and healthy by the inspected status checks.

The daily Cost Explorer result for the inspected period was `0 USD`; this is not a guarantee of free operation. Potential future costs include public IPv4, snapshots/replacement EBS, CloudWatch/Flow Logs, KMS, SSM interface endpoints, and any replacement networking or compute.

## Remaining blockers

### P0

1. EDGE is not an isolated Cowrie deception endpoint; real Ubuntu SSH remains reachable through the public address from the restricted operator source.
2. CORE is not private and has a public address/direct IGW path.
3. EDGE/CORE authenticated private transport and Rust gateway disposition are unresolved.

### P1

1. Egress, metadata/container boundaries, protected audit delivery, and encrypted storage are not implemented or verified. SSM administration and host incoming controls are now operational.
2. Emergency isolation and rollback have not been demonstrated.

## Task 4 and public-exposure readiness

Task 4 must not start automatically. Task 4 prerequisites include approved and independently verified Session Manager access to both nodes, a decision on CORE private migration, authenticated EDGE-to-CORE transport, hardened host/container policy, protected audit storage, ethics/privacy approval for field collection, and the full live acceptance test set.

Public honeypot exposure is **not approved** and remains blocked.
