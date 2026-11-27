# RAGIN Task 3.6: EBS and Audit Protection

## Storage baseline

| Node | Root volume | Size/type | Encryption | Delete on termination |
|---|---|---|---|---|
| CORE | `vol-0537ee06e67f63cc5` | 40 GiB gp3 | `false` | `true` |
| EDGE | `vol-05925e722a36cd345` | 20 GiB gp3 | `false` | `true` |

Both roots are in-use and unencrypted. No in-place encryption was attempted.

## Safe encryption strategy

Use a documented encrypted snapshot/restore or replacement-volume cutover: inventory mounts and boot configuration, create an encrypted copy only after approval, validate checksums and boot behavior in an isolated path, preserve the original volume/instance for rollback, and cut over in a planned window. Do not delete the original until application state, audit records, operator access, and recovery have been independently verified.

Snapshots and replacement volumes can incur storage and transfer charges. KMS use may also have account-specific costs. A reported zero Cost Explorer value is not a guarantee of zero future charges.

## Protected evidence design

CORE should own append-only session/audit state with restricted operator access. Each record should include a session ID, UTC timestamp, event type, redacted command/input, candidate provenance, verifier decision, fallback transition, state-commit result, service/model versions, and error details without secrets. Use a hash chain or equivalent tamper-evident manifest and preserve a protected copy before restart or isolation.

Source addresses should be collected only under an approved ethics/privacy protocol, with access restriction, retention limits, redaction, and a documented lawful basis. Public attacker observation must remain separate from controlled synthetic benchmarks and historical result files.

## Current telemetry gaps

No VPC Flow Logs were returned; no configured CloudTrail trail was returned; CloudWatch Agent was inactive on both hosts; protected audit delivery and restart durability were not demonstrated. Enabling logging destinations, retention, or endpoints requires a separate cost and IAM approval.
