# Redactions in the public artifact deposit

Applied 2026-11-27, before publication of this repository. Every redaction is a
**one-token substitution of live-infrastructure identifiers**. No measured value,
transcript reply, verdict, or count is changed. The affected host field is
routing metadata: it identifies where E3 was run, and is never an input to any
reported number.

## Why

E3 probed the author's live deception fleet. The frozen records named the
fleet's public IP, and the deployment census named the fleet's public IPs and
AWS account. Publishing those would link a still-relevant honeypot endpoint to
the study and expose account-level infrastructure detail. The scientific record
does not need them.

## Substitutions

| Token | Replaced with |
|---|---|
| The live fleet's three public IPv4 addresses (EDGE, CORE, INTEL) | `REDACTED_FLEET_HOST` |
| The AWS account ID | `REDACTED_ACCOUNT` |
| The operator's two host addresses (laptop / home) | `REDACTED_OPERATOR_HOST` |

## Manifest-pinned files (frozen deposit)

These three files are covered by `ARTIFACT_MANIFEST.sha256`. Their manifest
entries are recomputed for the public bytes; the original frozen hashes are also
recorded as a trailing comment block inside the manifest itself.

| File | Frozen (original) SHA-256 | Public (redacted) SHA-256 |
|---|---|---|
| `gauntlet/demo/E3_RESULTS/E3_CHAIN.jsonl` | `dc5fb4eec8397628d121178a6985c80cf17a448afe12b576039c4bcab0b6c821` | `292f109c5e43c270c161fe0545588fc921ac21a7265a42d32f86f9b9dc239206` |
| `gauntlet/demo/E3_RESULTS_BASELINE/E3_CHAIN.jsonl` | `9f2007b6768d9be72eea6bd1d4e02fbe5923295ef56a554937b5d8de40e6651f` | `52c325303f98678c354c0f82eb3d933009a40f589c4f25379c6f11ece0181d90` |
| `gauntlet/demo/run_e3_deception_gain.py` | `bdd6cc8b08b416adf6cd86ebad1efa1f09e6605cd9177a521db63886b59a0c41` | `e19ec933215220ebfbe74bdc0d9d20f9e4ed8991f2b25057a9a2e8157200a8fd` |

In `run_e3_deception_gain.py` the substitution is the default value of
`RAGIN_ATTACK_HOST`; the environment override still takes precedence.

## Deployment artifacts (not manifest-pinned)

| File | Frozen (original) SHA-256 | Public (redacted) SHA-256 |
|---|---|---|
| `RAGIN-Retrieval-Augmented-Honeypot-Intelligence/results/fleet_census_2026-11-18.md` | `d5baefcd7c78ebf14e10e67c6deef656ceb34a63518624233a0812173ed05f7c` | `0f69575b2ba9fe38348192ce314a7e25faf364e267fbf104e24e21df683c53cc` |
| `RAGIN-Retrieval-Augmented-Honeypot-Intelligence/results/epk_frontier_gen1.json` | `6f17cc669c33c66aefcce5096f07f47b11b4a2c0d46bf6e04e74a08eded1d773` | `559cb41d88552de646d25a63a453523061fe393663e3b6c51d0993abe27572b3` |
| `RAGIN-Retrieval-Augmented-Honeypot-Intelligence/evidence/field/exit_evidence_2026-10-26.md` | redacted in this deposit | see `SUPPLEMENTARY_ASSETS.sha256` |

`exit_evidence_2026-10-26.md` additionally substitutes the operator's host
address with `REDACTED_OPERATOR_HOST`. Its private-range addresses (VPC,
docker bridge, metadata service) are not identifying and are retained.

`epk_frontier_gen1.json` names the host only inside its free-text `attacker`
metadata string; `fleet_census_2026-11-18.md` carries the fleet table, the
account ID, and the narrative that references them.

## Reconstruction

The unredacted originals are retained by the author and can be made available to
the editor or reviewers on request. All other files in this deposit are
byte-identical to the frozen deposit, which `./verify.sh` confirms against the
manifest.

## VPS field export (2026-11-27)

`vps-export/2026-11-27/` and the mirrored platform data contain **live
third-party attacker traffic** (Cowrie logs, pre-NAT connection records, and
attacker command text flowing through experiment artifacts). Before deposit:

- ~560,000 third-party public IP occurrences across the VPS export, platform
  session store, HF-2024 dataset copies, and RAGIN experiment artifacts were
  replaced by `attacker-<12 hex>` — a deterministic HMAC of the address under a
  key that is **not published**, so cross-file linkage is preserved but the
  addresses cannot be recovered from this deposit.
- The operator's host addresses → `REDACTED_OPERATOR_HOST`; the fleet's
  addresses → `REDACTED_FLEET_HOST`; the AWS account ID → `REDACTED_ACCOUNT`.
  These tokens are applied repo-wide, including inside JSON CIDR fields.
- Private, loopback, link-local, multicast, documentation-range, and
  public-resolver addresses are retained unchanged. Dotted-quad **version
  strings** in the MITRE/STIX corpora (e.g. `3.0.0.4`) are data values, not
  addresses, and are retained.
- Attacker-chosen usernames, commands, and canary interactions are retained
  unmodified: they are the measurement content, and no real credential is
  involved (the honeypot serves only fictional canaries).

`./verify.sh` verifies all 46,498 manifest entries against the scrubbed bytes.
