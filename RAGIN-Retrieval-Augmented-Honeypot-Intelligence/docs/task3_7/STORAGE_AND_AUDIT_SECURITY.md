# RAGIN Task 3.7: Storage and Audit Security

## Current evidence

At `2026-10-08T19:26:53Z`, both attached roots report unencrypted:

| Host | Volume | Type / size | Encryption |
|---|---|---:|---|
| CORE | `vol-0537ee06e67f63cc5` | gp3 / 40 GiB | `Encrypted=false` |
| EDGE | `vol-05925e722a36cd345` | gp3 / 20 GiB | `Encrypted=false` |

No snapshot, replacement volume, or encrypted migration was performed. In-place EBS encryption is not an available safe operation for these attached roots.

## Required migration

1. Inventory and hash the data that must survive; exclude caches and rebuildable packages.
2. Create an encrypted snapshot or encrypted replacement only after approval of the one-time storage charge and downtime window.
3. Restore into a replacement root in the same AZ, preserving ownership, permissions, boot configuration, and application data.
4. Validate the manifest, boot, SSM, SSH, host firewall, and service state while the original remains available.
5. Cut over only after an independent recovery path is verified. Retain the original for rollback, then dispose of it only under a separate approved retention decision.

This requires a potentially disruptive instance/storage operation and is **BLOCKED pending approval**. The current unencrypted roots are a security FAIL for protected research state.

## Future audit boundary

CORE should store fiction state, session state, verifier decisions, fallback transitions, model/service versions, and failure events under a dedicated service account with restrictive permissions. Audit records should include a session identifier and event time, avoid raw secrets, minimize source-address precision, and use rotation plus a protected copy or tamper-evident manifest.

Research exports must separate public attacker observations from controlled synthetic benchmarks. Raw uploads and credentials must not be copied into the repository. Retention, redaction, operator access, ethics review, and incident preservation must be decided before field collection.

Audit restart durability is **INCOMPLETE** because no RAGIN service or persistent evidence pipeline is deployed. No historical Task 1 or Task 2 evidence was modified.
