# RAGIN Task 3.8 Historical Discrepancy Resolution

## Question resolved
Earlier reports described live EDGE→CORE mTLS success, including authorized-client acceptance and negative tests. The current Task 3.8 record instead states that the authorized certificate was rejected during Task 3.7 and that the repaired profile was never live-retested.

## Evidence reviewed
- `docs/task3_8/*` (preserved, reconciled)
- `docs/task3_7/PRIVATE_SERVICE_MTLS_VALIDATION.md`
- `docs/task3_6/SERVICE_AUTHENTICATION_RESULTS.md`
- `docs/72h_sprint/MTLS_AUTHENTICATION_RESULTS.md`
- `docs/72h_sprint/evidence/edge_to_core_verified_provenance.json`
- `docs/72h_sprint/evidence/edge_to_core_e2e_summary.json`
- `docs/72h_sprint/evidence/negative_boundary_tests.json`
- `docs/72h_sprint/evidence/cowrie_to_core_e2e.json`
- `docs/72h_sprint/evidence/real_generation_e2e.json`
- `docs/72h_sprint/evidence/controlled_benchmark_fallback_20261009.json`
- `docs/72h_sprint/evidence/aws_current_state_20261009.json`
- `docs/RAGIN_RELEASE_MANIFEST_2026-10-08.md`
- `docs/RAGIN_RESULTS_LEDGER_2026-10-08.md`
- `docs/next_stage/EXECUTION_CLOSE_SSH_WIRE_AND_AWS_E2E_2026-10-09.md`
- AWS CLI auth check from this session: session expired; no live AWS reads or mutations performed.

## Findings
1. Two different mTLS stories are present in the repository and they do not describe the same test.
2. The Task 3.6 and Task 3.7 documents describe a deliberately limited private-path experiment with temporary certificates and an ephemeral Python `CERT_REQUIRED` server on `172.31.17.217:24443`. In that run, the generated authorized client certificate was rejected, with the server error context recorded as `Missing Authority Key Identifier` / `SSLV3_ALERT_CERTIFICATE_UNKNOWN`. The transport path itself was reached; the rogue client was rejected; the authorized case failed. Task 3.7 is explicit that the corrected profile still failed in the live Python test and that live application mTLS remained BLOCKED.
3. The later `docs/72h_sprint/MTLS_AUTHENTICATION_RESULTS.md` and its evidence files describe a different, later controlled staging setup with a CORE listener on `172.31.17.217:8443`, a `spiffe://ragin/edge` URI identity contract, a separately sent staging API key, EDGE loopback/Cowrie-fronted forwarding, and unit-style negative boundary results plus an end-to-end `GENERATED_VERIFIED` artifact. That material is bound to `2026-10-08` through `2026-10-09` timestamps and is documented as validating the transport primitive and an application boundary under a controlled staging profile; it explicitly does not claim a migrated private CORE, production certificate rotation, or public Cowrie exposure.
4. The `real_generation_e2e.json` file is timestamped `2026-10-09T03:20:00Z/2026-10-09T03:27:00Z` and asserts `GENERATED_VERIFIED` for a controlled SSH→Cowrie→EDGE bridge→mTLS→CORE serving path. That is a different claimed run from the Task 3.7 Python mTLS experiment.
5. This session could not independently re-verify either AWS state or a fresh live mTLS exchange. AWS CLI auth was expired, root SSH was blocked, and SSM Session Manager was not reachable from this environment. No secrets were exported, no certificates were regenerated, and no new AWS resources were touched.

## What is different across the records
- Different listener port and server implementation: Task 3.7 used an ephemeral Python server on `24443`; the 72h sprint material references `8443` and a broader pipeline/serving path.
- Different certificate identity contract: Task 3.6/3.7 used ad-hoc temporary CA/leaf profiles and reported the authorized-leaf rejection as the decisive failure; the 72h sprint material references `spiffe://ragin/edge` plus a separate API key.
- Different evidence footprint: Task 3.7 evidence is a negative authorized-case result inside the task docs. The 72h sprint evidence includes positive provenance JSON, a verified end-to-end summary, negative boundary results, and a controlled benchmark with `GENERATED_VERIFIED` and `TEMPLATE_FALLBACK_VERIFIED` serve paths.
- Different confidence boundary: the Task 3.7 record is internally consistent and does not claim the authorized case passed. The 72h sprint record asserts live acceptance in a controlled staging context, but that context is later and differently configured.

## Conclusion
- Historical live mTLS proof: DIFFERENT RUN. The repository does not contain a single consistent historical narrative. The older Task 3.7 record documents an authorized-case rejection in a restricted private test with temporary certificates. The later `docs/72h_sprint/` material documents a successful controlled staging acceptance under a different listener, port, identity contract, and evidence footprint. These are not the same run, certificate profile, or acceptance boundary.
- Current deployed mTLS state: BLOCKED from this session. Even if the later controlled-staging evidence is accepted as genuine for its own scope, this session could not refresh AWS authentication, could not re-read current CORE/EDGE/VPC/SG/volume/endpoint state, and could not execute or independently reproduce a live EDGE→CORE mTLS exchange from the current environment. No current deployment assertion can be verified here without live AWS read access.
- Exact remaining validation required: a live, currently authenticated EDGE→CORE mTLS acceptance/rejection test executed from inside the VPC with the correct current certificate profile and current CORE listener, with preserved raw HTTP/TLS results and correlation IDs, covering the authorized case plus the negative cases (missing cert, untrusted CA/self-signed, wrong identity, expired cert, oversized request, replay/idempotency and session-owner guards where applicable), followed by an explicit read-back that no temporary test rules, certs, or keys remain in the repository or in the environment.

## Preserved decisions
- The seven Task 3.8 documents in `docs/task3_8/` are preserved as reconciled records.
- No resolution was invented. The discrepancy is attributed to different runs/configurations/evidence scopes, not reconciled into a single corrected historical claim.
- No AWS resources were created, modified, rotated, or migrated. No CORE migration, encrypted EBS, private subnet, SSM endpoint, or public Cowrie activation was performed from this session.
- No Task 4 start and no public honeypot activation.

## Single next executable operation
When authorized AWS access is available, use the existing EDGE runtime identity to run one bounded live mTLS acceptance/rejection test from inside the VPC against the current CORE listener, preserve raw results and correlation IDs, and read back that no temporary test material remains.
