# Private CORE Migration Approval Packet

Status: BLOCKED FOR CUTOVER APPROVAL; no replacement or destructive storage operation was performed.

## Exact requested action

Create one temporary replacement CORE in the prepared private subnet `subnet-07fae34b3db734bb2`, with an encrypted root volume, the dedicated CORE security group, and access through the existing EC2 Instance Connect Endpoint `eice-023d2c69cb6690c48`. Preserve the current CORE instance and root volume unchanged until application, mTLS, persistence, management, and rollback tests pass.

## Impact and cost

This requires additional EC2 runtime and encrypted EBS/snapshot or image resources. It may incur hourly compute, EBS-month charges, snapshot storage, and cross-AZ data-transfer charges. Exact remaining credit balance was not exposed by the available CLI queries, so creation must wait for a current credit/price decision. No NAT Gateway or paid interface endpoint is proposed.

## Cutover and rollback

Inventory and copy only validated application/state data; verify hashes and ownership on the replacement; validate EIC SSH, SSM where available, mTLS from EDGE, persistence, and provider/fallback behavior; then make the smallest approved routing/target change. If any validation fails, restore the prior CORE target and keep the original instance running. Do not terminate or overwrite the original until an independent recovery window has passed.

## Remaining technical blocker

The current CORE remains public-addressed in an IGW-routed subnet. The EIC endpoint provides a private management path but does not change the current placement. Provider-backed generation also needs an explicitly approved, cost-bounded egress design after private placement; unrestricted EDGE relay is not acceptable.

## Fresh AWS verification

The 2026-10-09 read-only refresh confirmed EIC `eice-023d2c69cb6690c48` is `create-complete` in `subnet-07fae34b3db734bb2`, with the private route table containing only the VPC local route. CORE remains in `subnet-0f8d7698fde97f83b` with public IPv4 `REDACTED_FLEET_HOST`; its current SG still permits operator SSH and temporary EDGE `/32` TCP/8443 staging. CORE root `vol-0537ee06e67f63cc5` remains 40 GiB and unencrypted. Full evidence is in `evidence/aws_current_state_20261009.json`.
