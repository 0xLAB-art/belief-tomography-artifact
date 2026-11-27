# RAGIN Task 3.7: Private Service mTLS Validation

## Scope

No RAGIN application, Rust gateway, Docker, Cowrie, Laya, or public listener was deployed. The test used an ephemeral server on CORE's private address `172.31.17.217:24443` and an ephemeral client on EDGE. Temporary certificates were generated outside the repository and removed after each attempt.

The test path temporarily added TCP/24443 from the EDGE SG to the CORE SG and a matching CORE UFW rule. Both were removed; final readback shows only operator SSH ingress.

## Results

| Test | Result | Evidence boundary |
|---|---|---|
| EDGE reaches CORE private address over temporary SG/UFW path | PASS for the ephemeral test path | Private listener accepted connections during the controlled test window |
| Authorized mTLS client accepted by CORE-side Python `CERT_REQUIRED` server | FAIL | Server rejected the generated client certificate; no deployed service exists |
| Rogue client rejected by CORE-side Python `CERT_REQUIRED` server | PASS | Server emitted rejection and the client returned non-zero |
| OpenSSL authorized handshake | PASS in an earlier primitive | Not sufficient as an acceptance test because the paired rogue client was not rejected by that invocation |
| Live application mTLS | INCOMPLETE | No application listener or request authorization layer is deployed |

The authorized failure is not being hidden. The first generated profile lacked sufficient certificate-purpose extensions; a corrected profile still failed in the live Python test and requires diagnosis before reuse. The result is therefore not a working service boundary.

## Required implementation before deployment

- A dedicated private service identity for EDGE and a CORE trust store.
- mTLS with explicit server and client certificate purpose, private-key permissions, rotation, and revocation/replacement procedure.
- Request authorization after TLS: service identity, session ownership, request size, timeout, replay/context checks, and rate limits.
- Fail-closed behavior for missing, expired, untrusted, or wrong-purpose certificates.
- Negative tests for no certificate, rogue CA, wrong EKU, expired certificate, oversized request, replayed request, and unauthorized session.

The Rust gateway remains outside the serving path until the same authentication and negative-test criteria pass independently. This branch is **BLOCKED** for deployment, while the cleanup and containment controls are verified.
