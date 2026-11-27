# RAGIN Task 3.6: Storage Encryption Status

## Final state

| Node | Root volume | Size/type | Encrypted | Evidence |
|---|---|---|---|---|
| CORE | `vol-0537ee06e67f63cc5` | 40 GiB gp3 | No | `describe-volumes` after hardening |
| EDGE | `vol-05925e722a36cd345` | 20 GiB gp3 | No | `describe-volumes` after hardening |

No destructive storage operation, snapshot, replacement volume, or instance cutover was performed.

## Required migration

Use an encrypted snapshot/restore or replacement-volume procedure: inventory mounts, preserve the original instance and volume, create an encrypted copy only in an approved cost window, validate boot/state/audit digests, test operator recovery, and cut over only after independent verification. Delete nothing until recovery evidence is complete.

Potential costs include snapshot storage, replacement volume storage, KMS usage, and data transfer. Encryption remains a P1/P0 deployment-readiness blocker for protected research evidence.
