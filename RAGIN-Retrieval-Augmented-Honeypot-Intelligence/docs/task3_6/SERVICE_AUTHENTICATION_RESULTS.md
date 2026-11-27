# RAGIN Task 3.6: Service Authentication Results

## Local primitive validation

An ephemeral loopback TLS test was run on the workstation using a temporary CA, CORE server certificate, authorized EDGE client certificate, and rogue client certificate. No key material was stored in the repository.

| Test | Result |
|---|---|
| Authorized mTLS client connects | PASS |
| CORE-side certificate trust and EDGE identity check | PASS |
| Rogue client certificate rejected | PASS |
| Request-size bound in test server | PASS at 8 KiB boundary |
| External target contact | None |

This validates the transport primitive only. No AWS service listener or RAGIN application was deployed, so no live EDGE-to-CORE application request was tested.

## Required deployment contract

The future CORE listener must bind to a private address, require mTLS, authorize the EDGE client identity separately from operator identity, cap request bodies, enforce deadlines/rate limits/bounded retries, and bind session operations to an authorized owner. A private Docker network or source IP is not authentication. Secrets/certificates must be generated outside source control, stored with restricted permissions, and rotated with overlapping trust during cutover.

The Rust gateway remains outside the serving dependency path until request authentication is implemented and independently tested. Laya is not integrated.
