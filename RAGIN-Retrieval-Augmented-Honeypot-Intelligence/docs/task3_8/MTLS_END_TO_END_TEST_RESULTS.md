# RAGIN Task 3.8: Private mTLS End-to-End Test Results

## Status

**BLOCKED — NO LIVE RE-VERIFICATION POSSIBLE FROM THIS SESSION / TEST PLAN RECORDED**

## Working evidence boundary

AWS API access was not available from this session:
- AWS CLI session expired; refresh from the terminal was not available.
- Root SSH was blocked from this environment.
- SSM Session Manager was not reachable from this environment.
- Local TCP/22 probes to the recorded public and private IPs returned filtered/closed, consistent with the prior operator-only ingress posture rather than an accessible listener.

Therefore this session cannot add new live EDGE-to-CORE mTLS evidence. The end-to-end test result below is a record of the last available evidence and the required retry boundary.

## Evidence available

From `docs/72h_sprint/evidence/aws_current_state_20261009.json` and the task3_6/task3_7 reports:
- CORE: `i-062a400b300f4f9e4`, `m7i-flex.large`, private `172.31.17.217`, public `REDACTED_FLEET_HOST`, SG `sg-03486d70769d21e4e`, IMDSv2 required with hop limit 1, SSM Online.
- EDGE: `i-05bc6aab0bd4260a7`, `t3.micro`, private `172.31.35.203`, public `REDACTED_FLEET_HOST`, SG `sg-077b8f78668f4f646`, IMDSv2 required with hop limit 1, SSM Online.
- Both SGs have only operator TCP/22 inbound; both SGs still have all-protocol outbound `0.0.0.0/0`.
- Default NACL allow-all.
- Both root EBS volumes unencrypted.
- No VPC Flow Logs or configured CloudTrail delivery observed.
- AWS cost explorer returned `0 USD` per returned day for the queried seven-day window ending 2026-10-08; this is an observation, not a future-cost guarantee.

## Last available mTLS result

From `docs/task3_7/PRIVATE_SERVICE_MTLS_VALIDATION.md`:
- Temporary private path reachable: PASS.
- Rogue client rejected by CORE `CERT_REQUIRED` server: PASS.
- Authorized client rejected by CORE `CERT_REQUIRED` server: FAIL.

Local primitive evidence from `docs/task3_6/SERVICE_AUTHENTICATION_RESULTS.md`:
- Local loopback mTLS primitive: authorized client passed, rogue client rejected, request-size bound valid at 8 KiB.
- No deployed application listener or request authorization existed.

## Required live retry matrix

Before mTLS can be marked PASS, the repaired certificate profile must pass a live private-path test from EDGE to CORE with the following cases:

| Case | Expected | Acceptance |
|---|---|---|
| Valid EDGE certificate, `service=ragin-edge`, well-formed request | Authorized service response | 200 with authorized-identity semantics |
| Valid certificate but `service=other-service` | Application authorization rejection | Non-200, service-identity-rejected |
| Trusted certificate with wrong identity `other-service` | Service identity rejection | Non-200, identity-rejected |
| Malformed request | Safe parse rejection | Non-200, malformed-rejected |
| Request larger than 8192 bytes | Bounded request rejection | Non-200, size-rejected |
| Rogue self-signed or untrusted CA certificate | TLS rejection | TLS alert, no application response |
| Missing client certificate | TLS rejection | TLS alert, no application response |
| Expired client certificate | TLS rejection | TLS alert, no application response |
| Wrong hostname / SAN on client verification | TLS rejection or fail-closed behavior | Rejection recorded |
| Request timeout, replayed request id, unauthorized session owner | Application rejection guards | Non-200, guard-rejected |

The temporary SG/UFW rule used for the test path must be removed after the test and read back.

## Interpretation

The prior authorized-case failure is documented and understood, not hidden. The certificate-profile cause is repaired in design. The live retry is still required before mTLS is marked PASS. The Rust gateway remains excluded from the serving path.

