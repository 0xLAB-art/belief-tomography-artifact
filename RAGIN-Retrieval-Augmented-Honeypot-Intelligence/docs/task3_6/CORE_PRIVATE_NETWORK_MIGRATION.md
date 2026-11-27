# RAGIN Task 3.6: CORE Private-Network Migration

## Confirmed boundary

CORE is not private. Its ENI is in `subnet-0f8d7698fde97f83b` (`172.31.16.0/20`), the subnet maps public IPv4 addresses, the instance has a public IPv4, and the default route is through the attached IGW. A restrictive SG is not equivalent to a private subnet.

The primary ENI is subnet-bound. Do not attempt an in-place subnet move or detach the primary ENI from the running instance.

## Options

| Option | Security property | Cost | Downtime/recovery | Recommendation |
|---|---|---|---|---|
| A. Staged private replacement/restore | Strongest: no public IP and no IGW route for CORE; preserve current instance as rollback until verified | New subnet/temporary storage and any snapshots may incur charges; NAT Gateway is deliberately avoided | Planned cutover; state and boot validation required | Preferred if a private subnet can be reused or created under explicit approval |
| B. Interim SG isolation | Reduces inbound exposure while retaining current public-subnet risk | No direct SG fee | Low downtime, but does not remove IGW/public-addressing risk | Acceptable temporary containment only; not a private-boundary claim |
| C. Private management overlay / SSM | Keeps operator path independent of public SSH; SSM requires role/connectivity | SSM interface endpoints are recurring; overlay service may have cost; public IPv4 charges may remain until removed | Keep SSH until an independent session is demonstrated | Use as an access prerequisite, not as a substitute for private CORE placement |

## Proposed non-destructive migration sequence

1. Inventory all CORE mounts, application state, audit files, and boot dependencies without copying secrets.
2. Verify whether an existing subnet in this VPC has no IGW default route and is not shared with unrelated resources. If none exists, request approval for the minimum private-subnet resource; do not create it in this task.
3. Prepare an encrypted restore/replacement path and an authenticated EDGE-to-CORE transport. Do not terminate or modify the current CORE.
4. Validate the replacement in a non-public or isolated mode, including operator access, state integrity, mTLS, and negative internet reachability.
5. Cut over only in an approved window; retain the current instance and rollback path until acceptance evidence is complete.
6. Remove public addressing only after replacement access is independently verified. A stop/start or address reassignment is not itself proof of private placement.

No migration, subnet creation, snapshot, replacement instance, NAT gateway, endpoint, or termination was performed.
