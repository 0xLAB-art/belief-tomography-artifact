# Data & privacy

## The live-fleet export

`vps-export/2026-11-27/` is the raw record of the live honeypot deployment,
pulled from the instances over AWS SSM the same day as the freeze:

| Source | Instance | Contents |
|---|---|---|
| CORE | deception plane | 15,409 cumulative served-session event logs · 15,404 field records · `host_fiction.json` |
| EDGE | front end | 42,076 pre-NAT connection records (`proxy_connections.jsonl`) · full Cowrie log history (2026-10-08 → 11-27) |

Transfer integrity: tarball SHA-256s are recorded in
`vps-export/2026-11-27/EXPORT_MANIFEST.md`.

The census artifact reports **point-in-time counters** (3,413 CORE served
sessions on 2026-11-18); the export is the cumulative 2026-11-27 state of the
same planes.

## Redactions

All applied before publication; documented with original/public SHA-256 in
`REDACTIONS.md`.

- **~560,000 third-party public IP occurrences** across the VPS export,
  session store, dataset copies, and experiment artifacts →
  `attacker-<12 hex>`: a deterministic HMAC under a key that is **not
  published** — cross-file linkage preserved, addresses unrecoverable.
- **Operator addresses** → `REDACTED_OPERATOR_HOST`; **fleet addresses** →
  `REDACTED_FLEET_HOST`; the **AWS account ID** → `REDACTED_ACCOUNT`.
- Private, loopback, link-local, multicast, documentation-range, and
  public-resolver addresses are retained unchanged. Dotted-quad **version
  strings** in the MITRE/STIX corpora are data values, not addresses, and are
  retained.
- Attacker-chosen usernames, commands, and canary interactions are retained
  unmodified — they are the measurement content, and no real credential is
  involved (the honeypot serves only fictional canaries).

No measured value is affected: host fields are routing metadata, never inputs
to a reported number.

## Deliberately excluded (byte-level workspace diff)

| Excluded | Reason |
|---|---|
| `RAGIN-…/.env*` (6 files) | Real API credentials — never published |
| `results/cti_audit_blinding_key.json` | Unblinds the CTI annotator A/B study |
| `logs/health_monitor.log`, `gateway.tar` | Host-local log; 92 MB build artifact |
| `.venv/`, `models/` (1.7 GB weights), `graphify-out/` | Environment, binaries, cache |
| nested `.git/` | Internal history |
| `.mimosa/`, `.omo/`, `.archify/`, `.zcode/`, … | Agent-tool session state |

**Zero experiment artifacts, data files, or paper files remain outside the
deposit.**

## Anonymity

The repository is **anonymized for review**: README, documentation site,
citation file, and the entire git history carry no author identity. The author
is identified in the manuscript submission itself (single-anonymous venue).

## Ethics

All credentials in the deposit are fictional canaries that exist only inside
the deception engine. The live experiments ran on infrastructure the author
owns, with registered halt gates and no destructive command (manuscript ethics
declaration, §Limitations).
