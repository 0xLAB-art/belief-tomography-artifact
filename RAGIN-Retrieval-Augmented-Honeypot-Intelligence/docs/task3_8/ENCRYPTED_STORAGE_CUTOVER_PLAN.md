# RAGIN Task 3.8: Coordinated Encrypted Storage Cutover

## Current storage state

| Host | Current root | Size | Encryption |
|---|---|---:|---|
| CORE | `vol-0537ee06e67f63cc5` | 40 GiB gp3 | `false` |
| EDGE | `vol-05925e722a36cd345` | 20 GiB gp3 | `false` |

No in-place encryption was attempted. Existing roots remain attached and intact.

These values are taken from the earlier recorded AWS evidence and must be re-verified with live AWS reads before any change is executed. AWS API access was not available from this session.

## Recommended coordinated CORE sequence

Use one replacement CORE cutover to solve both private placement and encrypted storage:

1. Inventory and hash required data; exclude caches and rebuildable packages.
2. Create an encrypted snapshot or encrypted image using an approved KMS key and retention period.
3. Launch the replacement in the approved private subnet with encrypted root storage.
4. Restore state and compare manifests, ownership, permissions, service configuration, and audit records.
5. Validate SSM, SSH recovery, IMDSv2, host firewall, private mTLS, and application startup.
6. Cut over without deleting the old instance or volume.
7. Retain the original through the recovery window, then make a separate retention/deletion decision.

## Cost and disruption

- One-time costs: snapshot or image storage, temporary overlap, and any encrypted replacement volume.
- Recurring costs: replacement EC2 and EBS usage; SSM interface endpoints if selected for private management.
- No NAT Gateway, load balancer, database, or paid monitoring is required by this plan.
- Expected maintenance downtime after preparation: approximately 30 to 90 minutes, subject to restore and validation time.
- Rollback requires the original instance and volume to remain available and the operator path to remain tested.

## EDGE separate step

EDGE encryption should be handled later as a separate low-risk replacement or encrypted-root migration. Do not combine EDGE encryption with public honeypot activation or Cowrie deployment. Preserve the existing operator SSH and SSM paths until the replacement is independently validated.

## Evidence note from this session

AWS API access was not available from this session. Volume ids, encryption state, and pricing must be re-verified with live AWS reads before any snapshot, replacement volume, or replacement instance is created. No snapshot, replacement volume, replacement instance, or KMS key was created during this session.

This plan is **DESIGNED / NOT DEPLOYED** and requires approval for snapshots, replacement storage, replacement compute, KMS usage, and downtime.

