# Controlled End-to-End Test Results

## Controlled AWS staging path

The test used temporary CA/server/client certificates with explicit CA constraints, SKI/AKI, SAN, and EKU. CORE ran the actual `server_v2` pipeline on private `172.31.17.217:8443`, with `RAGIN_MTLS_REQUIRED=1`, exact URI SAN allowlisting, API-key authentication, and a mandatory-verification Harness. EDGE reached it through a loopback-only `socat` mTLS forwarder.

| Case | Result |
|---|---|
| Authorized EDGE SAN + API key | PASS, HTTP 200, verified response returned |
| Authorized SAN without API key | PASS, HTTP 401 |
| Wrong service SAN | PASS, HTTP 403 |
| Rogue CA | PASS, TLS handshake rejected |
| Missing client certificate | PASS, TLS handshake rejected |
| EDGE host -> CORE `/health` over mTLS | PASS, HTTP 200 |
| EDGE host -> CORE session/create + command/replay | PASS, HTTP 200; provenance events persisted |
| Cowrie loopback SSH `whoami` -> CORE | PASS; returned synthetic `webapp`, not Ubuntu shell |
| CORE public 8443 reachability | PASS closed, timeout from workstation |
| EDGE public 2222 reachability | PASS closed, timeout from workstation |
| EDGE public 18083 reachability | PASS closed, timeout from workstation |

Temporary certificates and listeners were removed. No key material was persisted in the repository.

## Regression gates

- Targeted mTLS, Task 2 serving, and server tests: **42 passed**.
- Full Python suite: **1,645 passed, 116 skipped, 34 warnings** in 141.21 seconds.
- Changed-file Ruff and Python compilation: **PASS**.
- Rust `cargo test --manifest-path llm-gateway/Cargo.toml --quiet`: **exit 0**, but no Rust test cases executed and no authentication pass is inferred.

## Not run or not passed

- No public RAGIN listener was deployed. A restricted staging listener is active on CORE private IP only.
- No public reachability or third-party scan was performed.
- Cowrie-to-CORE live request was performed through the loopback forwarder; evidence is `evidence/cowrie_to_core_e2e.json`.
- No arbitrary-egress denial test was performed because no attacker workload exists and no permanent egress policy was applied.
- No private-CORE cutover or encrypted-volume verification was attempted.
