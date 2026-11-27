# RAGIN Task 3.7: Private CORE Migration Plan

## Current verified state

Recorded `2026-10-08T19:26:53Z` from AWS CLI in `eu-north-1`:

| Property | RAGIN-CORE |
|---|---|
| Instance | `i-062a400b300f4f9e4` |
| Subnet / AZ | `subnet-0f8d7698fde97f83b` / `eu-north-1a` |
| Private / public IPv4 | `172.31.17.217` / `REDACTED_FLEET_HOST` |
| VPC | `vpc-044a70ed680faff8b` (default VPC) |
| Route | Main route table `rtb-0fb03d7badfcc25c6`, `0.0.0.0/0` to IGW `igw-0168696c5dc43baee` |
| Subnet addressing | `MapPublicIpOnLaunch=true` |
| Management | SSH operator `/32` and SSM Online |

CORE is therefore not private. A restrictive security group does not remove the public address, public subnet mapping, or Internet Gateway route.

```text
Current: Internet -> IGW -> public subnet -> CORE public IPv4
Target:  EDGE private path -> private subnet -> CORE, with no IGW route
                         \-> approved management path only
```

## Safe target

Use a dedicated private subnet and route table in the existing VPC. The private route table should contain only the VPC-local route until a separately approved management egress design exists. CORE should receive no public IPv4 address and should bind application listeners to its private interface only.

The existing primary ENI cannot be moved directly between subnets. The safe migration is a staged replacement or data-preserving relocation, not an in-place subnet edit.

## Options

| Option | Security | Cost | Availability / recovery | Decision |
|---|---|---|---|---|
| Replacement from a verified image or encrypted snapshot into a private subnet | Strong target state | New instance, storage, and possibly snapshot charges | Requires cutover and rollback window | Preferred, approval required |
| Temporary private subnet plus interface endpoints for SSM | Strong management boundary | Endpoint hourly and data charges; at least SSM service endpoints | Requires endpoint readiness before cutover | Defensible but cost review required |
| NAT Gateway for private management egress | Weaker egress boundary and recurring cost | Hourly plus data processing | Operationally simple, but poor fit for credit-constrained account | Not preferred |
| Keep CORE public with operator-only ingress | Interim containment only | No new resource | No cutover | Current interim state; not private |

No replacement instance, subnet, route table, endpoint, NAT gateway, snapshot, or storage change was created in Task 3.7.

## Executable cutover sequence

1. Freeze application writes and export a manifest plus hashes of fiction state, audit state, configuration, and service artifacts.
2. Obtain approval for the exact replacement instance, encrypted root volume/snapshot, subnet, route table, and management path.
3. Create the private subnet and dedicated route table in the existing VPC. Confirm no shared workload is attached.
4. Establish and independently test SSM or another private management path before moving data.
5. Build the replacement from a verified image or encrypted snapshot. Apply the dedicated CORE SG, IMDSv2, host firewall, service binding, and audit permissions.
6. Restore data, verify hashes, and run offline application and mTLS acceptance tests.
7. Permit only the authenticated EDGE service path from the dedicated EDGE identity. Do not open a public application port.
8. Cut over using a short, announced maintenance window. Keep the old CORE stopped or isolated only after recovery is verified; do not terminate it during the first rollback window.
9. Validate from an independent operator path, then record the new instance, ENI, routes, SGs, SSM status, and data manifest.

## Rollback

Before cutover, retain the existing CORE instance and its current network configuration. If health, data hashes, SSM, or service authentication fail, stop the cutover, restore the old route/SG state, and direct operators back to the existing instance. Termination is not part of the first rollback window.

The branch is **BLOCKED pending approval** because it needs a replacement or disruptive cutover and may need chargeable management infrastructure.
