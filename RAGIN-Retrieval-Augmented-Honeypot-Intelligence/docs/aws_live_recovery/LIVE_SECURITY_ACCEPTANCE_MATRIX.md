# RAGIN AWS Live Recovery — Live Security Acceptance Matrix

Purpose: one-line status per acceptance case, with the exact evidence reference and the reason for any non-PASS status. This matrix reflects the current execution session only; it does not merge historical Task 3.7 or 72-hour staging evidence.

Status legend:
- PASS: executed and satisfied
- PARTIAL: partially executed or stable but some sub-cases outstanding
- FAIL: executed and violated
- BLOCKED: not executed because approval, fixture, or certificate issues prevent it
- INCONCLUSIVE: executed but cannot be decisively interpreted
- NOT_EXECUTED: intentionally not attempted

---

## 1. Positive mTLS and application acceptance

| # | Case | Status | Evidence | Notes |
|---|------|--------|----------|-------|
| 1 | CORE server certificate validates against the correct CORE CA from the authorized EDGE client | PASS | `docs/aws_live_recovery/evidence/phase3_positive/` | OpenSSL verification from EDGE to CORE with `/etc/ragin/tls/edge.crt`, `/etc/ragin/tls/edge.key`, `/etc/ragin/tls/ca.crt` succeeded. |
| 2 | TCP connection to the actual CORE private listener (`172.31.17.217:8443`) succeeds | PASS | `docs/aws_live_recovery/evidence/phase3_positive/` and `docs/aws_live_recovery/evidence/phase3_tunnel_contract_correction_e2e.json` | Private TCP reachability confirmed. |
| 3 | Correct registered application route receives a valid request | PASS | `docs/aws_live_recovery/evidence/phase3_tunnel_contract_correction_e2e.json` and `docs/aws_live_recovery/evidence/phase3_positive/positive_probe_v2_parsed.json` | Correct route is `POST /ragin/v2/session/command`, served from hardened control routeset. |
| 4 | Application authentication required and accepted for the correct route | PARTIAL | `docs/aws_live_recovery/evidence/phase3_tunnel_contract_correction_e2e.json` and `docs/aws_live_recovery/evidence/phase3_positive/` | App auth header `Ragoin-Api-Key` is required and was accepted on the verified route; a full denied-for-missing credential negative demonstration is not yet in evidence for this session. |
| 5 | Authorized EDGE identity `spiffe://ragin/edge` is accepted | PARTIAL | `docs/aws_live_recovery/evidence/phase3_positive/` | mTLS acceptance succeeded for the authorized identity during this session; explicit identity-authorization versus chain-only acceptance is best confirmed together with the negative identity test. |
| 6 | Verifier controls the final served response | PASS | `docs/aws_live_recovery/evidence/phase3_tunnel_contract_correction_e2e.json` | Final response path is verifier-controlled. |
| 7 | Final response class for the bounded benign probe | PASS | `docs/aws_live_recovery/evidence/phase3_tunnel_contract_correction_e2e.json` | Served as `TEMPLATE_FALLBACK_VERIFIED` for the bounded echo probe; not a claim of live provider-backed generation. |
| 8 | Request/session correlation preserved | PARTIAL | `docs/aws_live_recovery/evidence/phase3_positive/` | Correlation identifiers generated and preserved for the v2 positive probe; full request/session ID presence depends on the specific probe output retained. |
| 9 | Genuine provider-backed generation claimed | NOT_EXECUTED | n/a | Not executed and not required for this mTLS acceptance test; no `GENERATED_VERIFIED` claim made. |

---

## 2. Negative mTLS and application tests

| # | Case | Status | Evidence | Notes |
|---|------|--------|----------|-------|
| 10 | Missing client certificate rejected | BLOCKED | n/a | Not demonstrated this session; earlier TLS-only negative probes were inconclusive and should not be counted as PASS. |
| 11 | Untrusted client certificate rejected | BLOCKED | n/a | No appropriate untrusted but syntactically valid negative fixture was used; nonexistent `-CAfile` is not a valid negative test. |
| 12 | Wrong service identity rejected when chain is otherwise trusted | BLOCKED | n/a | No independent fixture with a trusted chain but wrong URI identity was executed this session. |
| 13 | Invalid API authentication rejected | BLOCKED | n/a | Not executed this session for the v2 route. |
| 14 | Missing API authentication rejected | BLOCKED | n/a | Not executed this session for the v2 route. |
| 15 | Malformed JSON rejected | BLOCKED | n/a | Not executed this session. |
| 16 | Oversized request rejected against the active limit | BLOCKED | n/a | Active deployment limit is `RAGIN_MAX_REQUEST_BYTES=1048576`; not verified live this session. |
| 17 | Unauthorized session identity rejected | BLOCKED | n/a | Not executed this session. |
| 18 | Replayed/duplicated request identifier behavior | BLOCKED | n/a | Not executed this session; replay protection may not be fully implemented. |

---

## 3. Infrastructure and operational safety

| # | Case | Status | Evidence | Notes |
|---|------|--------|----------|-------|
| 19 | CORE listener binds only to the expected private address | PASS | SSM probe evidence in `evidence/` | CORE loopback `127.0.0.1:8443` refused; listener binds to `172.31.17.217:8443`. |
| 20 | mTLS required and allowed identity present | PASS | `DEPLOYMENT_STATE_MATRIX.md`, SSM inventory | `RAGIN_MTLS_REQUIRED=1`, allowed identity `spiffe://ragin/edge`. |
| 21 | Provider-backed generation enabled in current deployment | FAIL/INCONCLUSIVE | `DEPLOYMENT_STATE_MATRIX.md`, SSM inventory | Current CORE env uses `disabled-local-provider`; no live provider-backed generation proven this session. |
| 22 | `/run/ragin/tls` runtime path discrepancy resolved | FAIL | `CERTIFICATE_EXPIRY_AND_RESTART_SAFETY.md` | Discrepancy unresolved; restart safety not established. |
| 23 | Private CORE placement deployed | BLOCKED | `DEPLOYMENT_STATE_MATRIX.md` | Approval required; not deployed. |
| 24 | Encrypted root storage deployed | BLOCKED | `DEPLOYMENT_STATE_MATRIX.md` | Approval required; not deployed. |
| 25 | SSM survivability without public routing proven | BLOCKED | `DEPLOYMENT_STATE_MATRIX.md` | Not proven; management path choice not finalized. |

---

## 4. Overall acceptance

Live mTLS acceptance:
- Status: **PARTIAL**
- Satisfied: positive TLS acceptance, correct route reachability, verifier-controlled response, bounded benign application acceptance.
- Outstanding: verified negative mTLS and application rejection tests, runtime certificate path resolution, and explicit service-identity authorization confirmation for the current certificate versions.

Do not mark `LIVE_MTLS_PASS` until the outstanding negative cases are executed and preserved for the current certificate versions and application contract.

---

## 5. Evidence subtree

- `docs/aws_live_recovery/evidence/phase3_tunnel_contract_correction_e2e.json`
- `docs/aws_live_recovery/evidence/phase3_positive/`
- `docs/aws_live_recovery/evidence/ssm_*`
- `docs/aws_live_recovery/CERTIFICATE_EXPIRY_AND_RESTART_SAFETY.md`
- `docs/aws_live_recovery/PRIVATE_CORE_COST_AND_APPROVAL.md`

Do not delete or overwrite historical evidence without explicit approval.
