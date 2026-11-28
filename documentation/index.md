# Belief–Claim Gap — Artifact Documentation

Complete research artifact repository for the manuscript

> **Measuring the Belief–Claim Gap: Disentangling Autonomous-Agent Beliefs from Security Certification**
>
> IEEE Transactions on Dependable and Secure Computing — submitted 2026.
> Single-anonymous review: the manuscript names its author; deposit commits
> use the anonymous `0xLAB-art` identity.

This repository is the **complete, self-contained deposit**: the frozen
experiment record, the full measurement-platform mirror, and the
**live-fleet honeypot data itself** — every file hash-pinned by two
SHA-256 manifests (the manuscript is distributed via IEEE).

## At a glance

| | |
|---|---|
| Registered experiments | 30 (E1–E31 registry; E24 retired void before registration) |
| Frozen deposit | 399 files, SHA-256 manifest, byte-exact verification |
| Full deposit | 399 + 46,481 hash-pinned files · ~1.2 GB |
| Manuscript | Not hosted here — distributed via IEEE; the ledger quotes every claim |
| Live-fleet data | 15,409 served sessions · 15,404 field records · 42,076 pre-NAT connections · full Cowrie logs (2026-10-08 → 11-27) |
| Headline audit | 230 oracle flags adjudicated: 118 refusal-quote FPs + 112 genuine canary echoes · blinded re-audit κ = 0.96 |

## Quick start

```bash
git clone https://github.com/0xLAB-art/belief-tomography-artifact.git
cd belief-tomography-artifact
./verify.sh                    # → 399 frozen + 46,481 supplementary files OK
bash checks/quick_counts.sh    # → reproduces the 230-flag audit + censoring table
```

## Where to go next

- [Verification](verifying.md) — run the manifest checks yourself
- [Repository map](repo_map.md) — what lives where
- [Ledger guide](guide.md) — how every printed number is checked
- [Experiment index](experiments_index.md) — the E1–E31 registry
- [Reviewer bundle](reviewer_bundle.md) — the shortest path to the headline numbers
- [Data & privacy](data_privacy.md) — the live-fleet export and every redaction
- [License](license.md) — Apache 2.0, whole repository
