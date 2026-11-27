# RAGIN Task 3.7: AWS Cost and Cutover Plan

## Observed cost state

Cost Explorer returned `0 USD` for each daily unblended-cost entry in the queried seven-day window ending `2026-10-08`. This is an observation, not a guarantee of Free Tier coverage, future zero cost, or absence of delayed billing.

Task 3.7 created no EC2 instance, EBS volume, snapshot, NAT gateway, VPC endpoint, public address, load balancer, database, or paid monitoring resource. Temporary security-group and UFW rules were removed.

## Cost-sensitive choices

| Change | Direct cost expectation | Operational risk |
|---|---|---|
| Private subnet and route table in the existing VPC | No hourly service charge by themselves | Does not provide SSM egress or private management alone |
| Replacement `m7i-flex.large`/root storage | New EC2 and EBS charges during overlap; snapshot/storage charges if used | Cutover and rollback complexity |
| SSM interface endpoints | Hourly per endpoint/AZ plus data processing; requires a cost check before creation | Strong private management path, but recurring cost |
| NAT Gateway | Hourly plus data-processing charges | Recurring cost and broad egress path; not suitable without explicit approval |
| Encrypted snapshots/volumes | Snapshot or additional-volume storage charges | Data-preservation and downtime risk |

AWS pricing must be rechecked at approval time using the official [PrivateLink pricing](https://aws.amazon.com/privatelink/pricing/) and [NAT Gateway pricing](https://docs.aws.amazon.com/vpc/latest/userguide/nat-gateway-pricing.html) pages. No paid resource is approved by this document.

## Approval-gated cutover packet

Before implementation, provide the exact subnet CIDR, route table, replacement instance/storage identifiers, management path, monthly and overlap cost, maintenance window, lockout risk, rollback, and independent verification commands. Approval must explicitly cover replacement compute/storage and any SSM endpoints or NAT.

The least-cost defensible sequence is: prepare a private subnet and route table, prove a private management path, create an encrypted replacement only after approval, restore and hash-verify data, validate SSM/SSH and service authentication, cut over, and retain the old instance for rollback. CORE must not be made unreachable merely to test the design.
