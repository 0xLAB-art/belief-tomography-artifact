# Distributed architecture — verified current state

## Objective

Establish and verify the real operational components and communication boundaries for the RAGIN serving path, without enabling any attacker-facing public service.

## Target topology

```
INTERNAL TEST CLIENT
    ↓
COWRIE / EDGE
    ↓
AUTHENTICATED mTLS
    ↓
PRIVATE RAGIN CORE
    ↓
CHROLLO + DON + HISOKA
    ↓
GENERATOR
    ↓
DETERMINISTIC VERIFIER
    ↓
ACCEPTED RESPONSE
    ↓
COWRIE SSH OUTPUT
```

The optional Laya assessment provider is intentionally outside the authority of the deterministic verifier.

## Components identified in source and prior records

### Attacker-facing edge

- Cowrie SSH honeypot frontend
- EDGE host / container pair used for SSH-visible attacker interaction in prior local integration evidence

### Authenticated EDGE-to-CORE transport

- EDGE bridge path is meant to be authenticated and mTLS-constrained
- `ragin.transport.mtls` provides server-side context construction, peer-certificate identity extraction, and authorized-identity checks
- `server_v2.py` wires mTLS as an optional middleware behind `RAGIN_MTLS_REQUIRED` and `RAGIN_MTLS_ALLOWED_IDENTITIES`
- API-key auth is enforced through `_request_authorized` and the auth middleware unless disabled

### Core serving application

- `server_v2.py` is the current authoritative serving process for the full pipeline
- Pipeline path: Harness orchestrates Chrollo → Don → Hisoka, then verification, then accepted-state commit, then response
- Core contracts:
  - `ragin.cycle.harness.Harness`
  - `ragin.cycle.sandbox.Sandbox`
  - `ragin.cycle.session.Session`
  - `ragin.cycle.verifier.FictionConsistencyVerifier`
- Adapters used by `server_v2.py`:
  - `ChrolloAdapter`
  - `DonAdapter`
  - `HisokaAdapter`

### Chrollo, Don, Hisoka

- Chrollo: behavior classification
- Don: retrieval-grounded CTI
- Hisoka: generated deception responses
- These are implemented in `ragin/cycle/adapters.py` and/or their respective modules and invoked through the harness

### Verifier

- `FictionConsistencyVerifier` implements mandatory pre-serve checks before any deception response is served
- Designed as deterministic and dependency-free for the verification decision itself
- Fail mode: fail to serve, with deterministic fallback, not fail open

### Accepted-state only serving

- `server_v2.py` and `harness.py` distinguish accepted candidates from rejected/pending/unavailable outcomes
- Serving must not transmit a candidate that has not reached accepted state

### Session persistence and audit

- `Session` is an append-only, crash-safe JSONL event log
- `Sandbox` manages per-session state through the harness
- Event types cover lifecycle, attacker input, system response, pipeline stages, deception artifacts, threat modeling, and errors
- Field export path exists through `_FIELD_EXPORT` in `server_v2.py`

## Verified boundaries

### Authentication

- API key required unless explicitly disabled
- Placeholder/empty API keys are rejected while auth is enabled
- Session token ownership used for session-scoped access in `server_v2.py`

### mTLS

- mTLS is configurable but not assumed on by default
- Server context construction and peer-identity checks live in `ragin.transport.mtls`
- `peer_certificate_authorized` is an intersection check against allowed identities

### Generator isolation

- `scripts/opencode_proxy.py` builds a bounded completion request and runs the OpenCode CLI with a safe agent config
- Safe config denies all tool categories for the `ragin-safe` agent
- The proxy drops a broad set of provider/secret env vars from the child process
- `extract_assistant_text` only accepts structured assistant text events and enforces an output bound

### No attacker-facing public service in this stage

- No public Cowrie exposure
- No public CORE API exposure
- Public activation is not authorized in this stage

## Current reality against the target topology

| Path | Target | Verified from source | Verified from live access in this host moment |
|------|--------|----------------------|-----------------------------------------------|
| Test client → Cowrie/EDGE | Yes | Yes | Not reachable from this host at this moment |
| EDGE → CORE mTLS | Yes | Yes, code path exists | Not reachable from this host at this moment |
| CORE pipeline → Chrollo/Don/Hisoka | Yes | Yes | Not live-verified here right now |
| Generator → Verifier | Yes | Yes | Yes, locally runnable contracts exist |
| Accepted response → SSH output | Yes | Yes in design + session-record evidence | Live SSH-wire capture blocked from this host at this moment |

## What is real and what is still outstanding

### Real

- The source topology matches the intended authoritative serving path
- Authentication, mTLS wiring, generator bounds, verifier, and session persistence all have concrete local code
- Historical and recent session-record evidence exists for generated/fallback serving distinctions

### Still outstanding in this host moment

- Live EDGE and CORE are not reachable from this workstation right now
- A live, non-empty SSH-wire proof with captured transcript is therefore blocked here until the hosts are reachable
- Full CORE runtime E2E against a live authenticated CORE cannot be completed from this host at this moment

## Evidence files referenced

- Source: `ragin/server_v2.py`, `ragin/cycle/*`, `ragin/transport/mtls.py`, `scripts/opencode_proxy.py`, `scripts/opencode_cli_bridge_safe_config.json`
- Prior sprint records in `docs/72h_sprint/`
- Next-stage evidence target: `results/ssh_wire/`

## Notes

- This architecture verification is a local code + prior-evidence verification, not a claim that every live AWS path is reachable from this workstation right now.
- Any completion claim for A1/A2/A4 must eventually include live execution evidence when the hosts are accessible.
