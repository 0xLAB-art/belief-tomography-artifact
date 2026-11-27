# RAGIN Task 3.8: CORE Private Migration Approval Packet

## Current state

CORE `i-062a400b300f4f9e4` remains in `subnet-0f8d7698fde97f83b` with private IPv4 `172.31.17.217` and public IPv4 `REDACTED_FLEET_HOST`. The subnet maps public addresses and the main route table sends `0.0.0.0/0` to the Internet Gateway. The primary ENI cannot be moved directly between subnets.

This is not private. A restrictive security group does not remove the public address, public-subnet mapping, or Internet Gateway route.

## Proposed target

Create a dedicated private subnet and route table in the existing VPC with only the VPC-local route. Launch a replacement CORE in that subnet without a public IPv4 address. Permit the authenticated EDGE service over the local VPC path and retain SSM as the administrative channel.

SSM cannot be assumed to survive removal of internet routing. Before cutover, choose and independently validate one of:
- SSM interface endpoints for the required Systems Manager services, with endpoint security groups restricted to the CORE management path; or
- another private operator-management path explicitly approved by the user.

Do not use a NAT Gateway solely to make this migration convenient without a separate cost approval.

## Exact approval requests

Approval is required for the following bounded changes:
1. Create a dedicated private subnet and route table in the existing VPC.
2. Create the minimum private management connectivity required for SSM if endpoints are selected.
3. Create a replacement CORE instance and encrypted root storage from a verified image or snapshot.
4. Execute a controlled cutover while retaining the existing CORE for rollback.

No request in this packet authorizes termination of the existing CORE, deletion of its volume, public application exposure, or a NAT Gateway.

## Cutover and rollback

1. Freeze writes and produce a manifest plus hashes of fiction state, audit state, configuration, and research files.
2. Validate the replacement management path before moving data.
3. Restore data and verify hashes, boot, SSM, SSH recovery, UFW, IMDSv2, and service certificates.
4. Validate the private mTLS contract from EDGE using the repaired certificate profile.
5. Change the EDGE-to-CORE service rule to the replacement private address/identity.
6. Cut over during a planned maintenance window. Estimated downtime after prerequisites are ready: approximately 30 to 90 minutes; endpoint and image preparation are additional lead time.
7. Keep the old CORE and original volume intact for the rollback window. If any health, data, SSM, or authentication check fails, direct operations back to the old instance and stop.

The current CORE remains unchanged pending explicit approval.

## Evidence note from this session

AWS API access was not available from this session. The VPC/subnet/route/IGW/NACL/VPC-endpoint/ENI state could not be re-queried live from this environment. The exact resource identifiers above are taken from the earlier recorded AWS evidence and must be re-verified with live AWS reads before any change is executed.

