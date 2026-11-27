# mTLS Authentication Results

## Controlled AWS staging

The CORE listener requires a client certificate chained to the staging CA and an allowed URI identity `spiffe://ragin/edge`. The EDGE forwarder presents the client certificate and separately sends the generated staging API key. The listener is bound to CORE's private address and the SG allows TCP/8443 only from EDGE's private `/32`.

| Case | Result | Evidence |
|---|---|---|
| Valid EDGE certificate and API key | PASS, HTTP 200 | `evidence/edge_to_core_verified_provenance.json` |
| Missing client certificate | PASS rejection, connection reset | `evidence/negative_boundary_tests.json` |
| Invalid API key | PASS rejection, HTTP 401 | `evidence/negative_boundary_tests.json` |
| Rogue CA / wrong identity | PASS rejection in local and staging boundary suite | focused 42-test run and prior local mTLS evidence |
| Public CORE 8443 reachability | PASS containment check, timeout | controlled workstation test |

The certificates are temporary staging credentials and private key material is not included in the repository evidence. No TLS verification or hostname/identity enforcement was disabled.

## Scope limit

The test validates the transport primitive and application boundary. It does not validate a migrated private CORE, production certificate rotation, or a public Cowrie deployment.
