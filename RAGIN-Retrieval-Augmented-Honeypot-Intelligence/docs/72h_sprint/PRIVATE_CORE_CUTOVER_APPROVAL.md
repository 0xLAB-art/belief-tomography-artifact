# Private CORE Cutover Approval Packet

## Current state

CORE remains `i-062a400b300f4f9e4`, with public IPv4 `REDACTED_FLEET_HOST` and its original IGW-routed subnet. The prepared private subnet is `subnet-07fae34b3db734bb2` in eu-north-1a. It is not current CORE placement.

## Requested future action

Create or launch a replacement CORE with encrypted root storage and no public IPv4 in the prepared subnet, validate EIC/SSM management and private EDGE-to-CORE mTLS, then cut over only after data and application validation. Preserve the current CORE unchanged until acceptance.

## Why approval is required

The branch may require a second EC2 instance, AMI/snapshot or temporary storage, temporary overlap, downtime, and data-transfer/storage charges. It is disruptive and the exact current credit balance is not available from the CLI inspection.

## Expected impact and rollback

- Expected downtime: a planned application cutover window; exact duration depends on migration method.
- Cost: temporary EC2 hours plus any encrypted EBS/AMI/snapshot storage and possible transfer; quantify immediately before execution.
- Lockout risk: private management must be tested through EIC before removing the old path.
- Rollback: keep old CORE running and its volumes intact; restore the old SG/application route, stop only the replacement, and revert the EDGE target to the old private address.
- Verification: EIC SSH, SSM Online where supported, application health, valid/invalid mTLS, end-to-end Cowrie smoke, data hashes, and public reachability denial.

No replacement, snapshot, volume migration, stop, terminate, or public exposure was performed overnight.
