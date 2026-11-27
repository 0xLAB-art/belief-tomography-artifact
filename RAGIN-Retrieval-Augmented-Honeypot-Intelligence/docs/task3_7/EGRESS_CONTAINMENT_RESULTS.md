# RAGIN Task 3.7: Egress Containment Results

## Verified baseline

At `2026-10-08T19:26:53Z`:

- CORE and EDGE SGs have one inbound rule each: TCP/22 from the operator `/32` `REDACTED_OPERATOR_HOST/32`.
- Both SGs still have all-protocol outbound `0.0.0.0/0`.
- The default NACL remains allow-all.
- UFW is active on both hosts with deny-incoming, operator-only SSH, and allow-outgoing.
- Host `OUTPUT` is ACCEPT and `FORWARD` is DROP through UFW.
- No Docker installation or attacker-facing container exists.
- The default route on both hosts reaches the Internet Gateway through the public subnets.
- IMDSv2 is required and the response hop limit is 1; the metadata endpoint remains enabled for the SSM role.

## Work performed and reverted

For private mTLS validation only, a temporary TCP/24443 SG reference from EDGE's SG to CORE's SG and a matching CORE UFW rule were created, tested, and removed. CloudTrail event history records the temporary rule window `2026-10-08T19:20:54Z` through `2026-10-08T19:26:33Z` (local event timestamps were `22:20:54` through `22:26:33` Africa/Cairo). Final SG and UFW readback contains no TCP/24443 rule.

No persistent egress rule was changed. This is deliberate: without a dependency inventory or private SSM endpoints, an outbound default-deny change could strand management and package recovery.

## Required future policy

| Path | Intended policy |
|---|---|
| EDGE -> CORE | Only the authenticated service port, private address, and dedicated SG identity |
| DNS | VPC resolver only, normally `172.31.0.2`, after host-path validation |
| SSM | HTTPS to the required regional services through a verified private endpoint path or explicitly approved temporary egress |
| Time | Approved NTP source only if required by the host |
| Package updates | Time-bounded maintenance allowlist, not permanent arbitrary egress |
| Metadata | Block attacker-controlled namespaces and future container paths; do not disable the endpoint until SSM replacement credentials work |
| Other internet destinations | Deny and alert |

For future Docker deployment, enforce policy in the host firewall and Docker's `DOCKER-USER` chain, test forwarding separately, never mount the Docker socket, and never rely on a security group alone for container-to-metadata or container-to-host isolation.

## Acceptance status

Arbitrary outbound denial is **INCOMPLETE**. No third-party target was contacted and no external scan was run. A future test must use owned endpoints and verify both allowed SSM/DNS traffic and denied arbitrary destinations before changing the default.
