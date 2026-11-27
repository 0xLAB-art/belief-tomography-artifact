# VPS export — 2026-11-27

Pulled from the live fleet over AWS SSM (port-forwarded SSH), same-day as the
artifact freeze.

| Source | Instance | Remote path | Contents |
|---|---|---|---|
| CORE | `i-062a400b300f4f9e4` (m7i-flex.large) | `/opt/ragin/data` | `sessions/` — **15,409** served-session event logs (cumulative); `field/ragin/` — **15,404** served-session records; `host_fiction.json` |
| EDGE | `i-05bc6aab0bd4260a7` (t3.micro) | `/opt/ragin` | `proxy_connections.jsonl` — **42,076** pre-NAT connection records; `cowrie-var/` — Cowrie logs, 2026-10-08 → 2026-11-27 |

Transfer integrity: SHA-256 of the tarballs as built on the instances —
`core_export.tgz` `895d753dea58d3013c43b389b1f1463b9362068e71f64cae88e6452d88b8ea0a`,
`edge_export.tgz` `a4527a331aec871954e4e4c8d1fe4b4a4fa986504bdd8b698c84f0360bf4008b`.

## Redaction applied before deposit

- Every third-party public IP address is replaced by `attacker-<12 hex>` — a
  deterministic HMAC of the address under a key that is **not** published, so
  session linkage is preserved but the addresses cannot be recovered from this
  deposit.
- The operator's host addresses and the fleet's own addresses are replaced by
  `REDACTED_OPERATOR_HOST` / `REDACTED_FLEET_HOST`; the AWS account ID by
  `REDACTED_ACCOUNT`.
- Private, loopback, link-local, and documentation-range addresses are retained
  unchanged (they identify nothing external).

## Relation to the paper

The census artifact (`RAGIN-Retrieval-Augmented-Honeypot-Intelligence/results/fleet_census_2026-11-18.md`)
reports the point-in-time counters (3,413 CORE served sessions on 2026-11-18);
this export is the cumulative 2026-11-27 state of the same planes. Sessions
carry `event_type`, timestamps, `verification_passed`, and `serve_path` fields
but no client-identifying address after scrubbing.
