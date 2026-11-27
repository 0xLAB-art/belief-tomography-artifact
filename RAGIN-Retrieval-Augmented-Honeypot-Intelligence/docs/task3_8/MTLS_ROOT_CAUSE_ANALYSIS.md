# RAGIN Task 3.8: mTLS Root Cause Analysis

## Status

**BLOCKED — AUTHORIZED CLIENT CERTIFICATE REJECTED IN LIVE TEST / ROOT CAUSE REPAIRED BUT NOT YET READY VERIFIED**

## Reproduction from prior work

Task 3.7 performed a live private-path test from EDGE to CORE:
- Temporary listener on CORE private address `172.31.17.217:24443`.
- Temporary SG reference from EDGE SG to CORE SG and matching CORE UFW rule, both removed after the test.
- Python CORE-side `CERT_REQUIRED` mTLS server.

Result in `docs/task3_7/PRIVATE_SERVICE_MTLS_VALIDATION.md`:
- EDGE reached CORE over the temporary private path: PASS for the transport path.
- Rogue client rejected by the CORE `CERT_REQUIRED` server: PASS.
- Authorized EDGE client certificate **rejected** by the CORE server: **FAIL**.

The decisive diagnostic reported was:

```text
client: SSLCertVerificationError: Missing Authority Key Identifier
CORE:   SSLError: SSLV3_ALERT_CERTIFICATE_UNKNOWN
```

Host clocks were reported synchronized at the time of the test, so clock skew was not the cause.

## Root cause

The temporary CA and issued leaf certificates did not include a complete X.509 linkage and purpose profile. The observed failure is consistent with the issued certificates lacking proper authority/subject key identifier linkage and/or explicit CA constraints and extended key usage, so the validating peer rejected the chain rather than silently accepting an ambiguous issuer or purpose.

This is a certificate-profile defect. It is not a reason to weaken hostname verification, disable client certificate requirement, or relax trust-store validation.

## Repair design (not yet live-verified from this session)

The corrected profile should use:

- Self-signed test CA: `CA:TRUE`, bounded path length, explicit `keyCertSign` and `cRLSign`, with Subject Key Identifier and Authority Key Identifier present.
- CORE server certificate: `CA:FALSE`, explicit `serverAuth` EKU, SKI, AKI, and SANs covering the CORE private identity used by EDGE.
- EDGE client certificate: `CA:FALSE`, explicit `clientAuth` EKU, digital signature / key encipherment usage, SKI and AKI, and a stable service identity such as `ragin-edge`.
- Separate wrong-identity certificate trusted by the same CA but with identity other than `ragin-edge`.
- Separate expired certificate trusted by the same CA but with validity fully in the past.
- Separate rogue/self-signed certificate not trusted by the CORE trust store.

Hostname/SAN verification must be enforced on the client against the CORE identity, and the server must require a client certificate (`CERT_REQUIRED`).

Private keys must be mode-restricted and stored only in temporary or tightly permissioned directories outside the repository. No key material should be committed.

## Authorization boundary

TLS authentication and application authorization are separate layers:

1. TLS validates the chain, validity window, EKU, and server/client identities.
2. The service maps the authenticated client identity to the expected service name.
3. The request must name the same service and satisfy size, syntax, timeout, rate, and session-owner constraints.
4. Replay protection, session ownership, and application permissions remain mandatory in the real RAGIN service.

The Rust gateway remains excluded from the serving path until it independently implements the same fail-closed contract and negative tests.

## Evidence available from this session

AWS API access was not available from this session (expired CLI session; root SSH blocked; SSM unreachable from this environment). Live re-test of the repaired profile could not be run from this environment.

Therefore:
- Local mTLS primitive evidence from Task 3.6: **PASS** for the transport primitive only (authorized client passed, rogue client rejected in a loopback test).
- Live EDGE-to-CORE application mTLS: **BLOCKED**.
- The certificate-profile cause is understood and repaired in design; the repaired profile still requires a live verified test before mTLS can be marked PASS.

