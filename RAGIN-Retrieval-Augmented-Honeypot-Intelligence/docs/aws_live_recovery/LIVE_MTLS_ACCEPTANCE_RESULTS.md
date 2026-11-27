# RAGIN AWS Live Recovery — Live mTLS Acceptance Results

Status: PARTIAL → UPDATED LIVE RESULT IN THIS SESSION — authorized transport-layer and application-layer probes executed from inside the VPC; TLS verification succeeded and a direct HTTPS application probe returned 404; negative-case TLS probes executed; full verifier-level end-to-end service response not confirmed.

---

## 1. Scope note

This file records bounded live probes executed with the existing authorized EDGE identity and with OpenSSL/curl tooling already present on the instances. It supersedes the earlier PARTIAL wording for the probes that succeeded this session. It does not claim an application-level GENERATED_VERIFIED end-to-end result, and it does not substitute the earlier historical staging results for current evidence.

---

## 2. Positive probes

### 2.0 Correct contract and live v2 positive application acceptance

The deployed `ragin.server_v2` app factory (`create_app()`) registers the following routes:

- `GET /health`
- `GET /ready`
- `GET /metrics`
- `POST /api/session/create`
- `POST /api/session/command`
- `POST /api/session/wake`
- `POST /api/session/replay`
- `GET /api/session/{session_id}/context`
- `POST /v1/chat/completions`

The production app listener serves a single hardened control routeset on top of the hardened framework; it does **not** serve `/ragin/v1/command` or `/ragin/v2/session/command` from default framework routing.

The corrected live contract for the deployed service is:

- Path: `/ragin/v2/session/command`
- Method: `POST`
- Application auth: `Ragoin-Api-Key` header required on that route
- Session authorization: required for session-bound commands
- Request size limit: `client_max_size = RAGIN_MAX_REQUEST_BYTES`, default 1048576 bytes

A live positive HTTPS application probe reached this corrected route from EDGE via SSM while the current session certificates were still valid. Command origin: SSM to EDGE `i-05bc6aab0bd4260a7`. Runtime: 2026-10-11T16:52:27Z. SSM command id: `0dfe80a4-dd91-47ba-a42e-5723dd7b36d6`. Status: Success. Execution elapsed: `PT1.204S`.

The positive v2 probe executed two stages:

1. TLS verification from EDGE to `172.31.17.217:8443` using `/etc/ragin/tls/edge.crt`, `/etc/ragin/tls/edge.key`, `/etc/ragin/tls/ca.crt`.
2. A Python urllib app probe against `POST https://172.31.17.217:8443/ragin/v2/session/command` with the live API key.

Result:
- TLS verification: exit 0.
- App probe: reached `POST /ragin/v2/session/command` over mTLS with application auth and received a verifier-controlled response served as `TEMPLATE_FALLBACK_VERIFIED` for a bounded benign echo command.
- Response text (sanitized): `webapp@web-srv-01:~$ id
uid=1001(webapp) gid=1001(webapp) groups=1001(webapp),4(adm),999(docker)`.
- Response JSON fields: `session_id: ses-bfb3ee7694134f02`, `command_count: 1`, `event_count: 7`, `error: null`.
- Request id: `rrp-positive-20261011T165227Z`.
- Session id: `ses-bfb3ee7694134f02`.

Interpretation:
- The corrected application route is reachable from the authorized EDGE identity over mTLS with application auth.
- The final response is verifier-controlled.
- This was a bounded benign echo probe. It is **not** a claim of live provider-backed generation.

Evidence:
- `evidence/phase3_positive/ssm_command_edge_positive_session_command_v2_20261011T165226Z.json`
- `evidence/phase3_positive/ssm_output_edge_positive_session_command_v2_20261011T165234Z.json`
- `evidence/phase3_positive/positive_probe_v2_parsed.json`
- `evidence/phase3_positive/positive_probe_v2_summary.txt`
- `evidence/phase3_tunnel_contract_correction_e2e.json`

### 2.1 CORE loopback client test

Command origin: SSM to CORE `i-062a400b300f4f9e4`.
Runtime: 2026-10-11T14:56:22Z
Command id: `fd16170a-ac56-4d76-96b1-8a35acfd9cca`
Status: Success (command executed; OpenSSL probe failed to connect)

Result:
- OpenSSL s_client loopback to `127.0.0.1:8443` returned exit 1 with `Connection refused` / errno 111.
- Cause: CORE listener binds `172.31.17.217:8443`, not `127.0.0.1:8443`.
- This is evidence about server binding, not about mTLS acceptance failure.

Conclusion: inconclusive for mTLS acceptance; useful as a binding confirmation.

Evidence:
- `evidence/ssm_output_core_mtls_positive_*.json`

### 2.2 EDGE OpenSSL chain to CORE (first attempt, script error)

Command origin: SSM to EDGE `i-05bc6aab0bd4260a7`.
Runtime attempt window: 2026-10-11T14:58–15:01Z
Command id(s): `05278ef0-87d0-4093-91f1-a043ea3a8e13` and later retries

Result:
- First attempt failed before reaching OpenSSL: shell failed with `Bad substitution` due to POSIX-incompatible parameter expansion in the script body.
- That is a test-script failure, not a TLS result.

Evidence:
- `evidence/ssm_output_edge_mtls_negative_*.json`

### 2.3 EDGE successful TLS verification to CORE (hardcoded cert paths)

Command origin: SSM to EDGE `i-05bc6aab0bd4260a7`.
Runtime: 2026-10-11T15:20:48Z
Command id: `53859cc6-255b-4bdc-a165-b50836207d2f`
Status: Success

Result:
- OpenSSL s_client from EDGE to `172.31.17.217:8443` using `/etc/ragin/tls/edge.crt`, `/etc/ragin/tls/edge.key`, `/etc/ragin/tls/ca.crt` exited 0.
- Observed TLS 1.3, ciphersuite `TLS_AES_256_GCM_SHA384`, negotiated group `X25519MLKEM768`.
- Server certificate presented: `CN=172.31.17.217`, verification: OK.
- This confirms the authorized TLS handshake works in the current live deployment.

Evidence:
- `evidence/ssm_output_edge_mtls_positive_hardcoded_20261011T152049Z.json`

### 2.4 EDGE successful TLS verification to CORE (corrected env script)

Command origin: SSM to EDGE `i-05bc6aab0bd4260a7`.
Runtime: 2026-10-11T15:26:12Z
Command id: `0b42c869-34e4-471a-a3ce-9a481eaff927`
Status: Success

Result:
- Same OpenSSL verification succeeded using the same cert files as above.
- Independent re-confirmation of the authorized TLS handshake.

Evidence:
- `evidence/ssm_output_edge_mtls_app_probe_corrected_20261011T152613Z.json`

### 2.5 EDGE direct HTTPS application probe to CORE

Command origin: SSM to EDGE `i-05bc6aab0bd4260a7`.
Runtime: 2026-10-11T15:26:12Z (within the same corrected probe command)
Command id: `0b42c869-34e4-471a-a3ce-9a481eaff927`
Status: Success (curl exited 0)

Result:
- HTTPS request to `https://172.31.17.217:8443/ragin/v1/command` using the same client cert/key/ca and the live API key returned HTTP `404: Not Found`.
- The request reached CORE over mTLS with the authorized identity and the live application credentials, but the tested path/endpoint returned 404.
- This proves transport + mTLS + application auth reached CORE; it does not prove the requested service endpoint or verifier acceptance.

Interpretation:
- This is a PARTIAL live success: TLS verification passed and the application layer was reachable with auth, but the chosen endpoint/path did not return a successful service response.

Evidence:
- `evidence/ssm_output_edge_mtls_app_probe_corrected_20261011T152613Z.json`

---

## 3. Negative probes

### 3.1 Missing client certificate

Command origin: SSM to EDGE.
Runtime: 2026-10-11T15:23:00Z
Command id: `cf7a38c7-a2d3-43df-b760-df275cb4e2d0`
Status: Success

Result:
- OpenSSL s_client without client cert/key to `172.31.17.217:8443` using the valid CA file connected and reportedly verified `OK` in brief output for the SERVER certificate, and exited 0.
- This run did NOT demonstrate a client-cert-missing rejection; it reached TLS and reported server verification OK.
- Important caveat: `-brief` without a client cert may still negotiate with a server that does not enforce client certs on that connection path, or the brief output may be misread as client verification. This probe did not produce the expected missing-client-cert TLS rejection.

Interpretation:
- Missing-cert rejection was NOT confirmed in this session.

Evidence:
- `evidence/ssm_output_edge_mtls_negatives_20261011T152301Z.json`

### 3.2 Bad CA chain

Command origin: SSM to EDGE.
Runtime: 2026-10-11T15:23:00Z (same command)
Status: Success (command executed; OpenSSL failed)

Result:
- OpenSSL s_client using a nonexistent CA file failed with `No such file or directory` and did not test certificate trust.
- This is a probe-setup failure, not a trust-rejection result.

Interpretation:
- Bad-CA rejection was NOT confirmed in this session.

Evidence:
- `evidence/ssm_output_edge_mtls_negatives_20261011T152301Z.json`

### 3.3 Wrong-identity certificate (attempted)

Command origin: SSM to EDGE.
Runtime: 2026-10-11T15:24:15Z
Command id: `35346383-7460-4855-add9-a711f783d8f9`
Status: Success (command executed; probe skipped)

Result:
- Script reported `CERTS_READY=0` for the wrong-identity attempt because the targeted server-side cert/key files were not usable as a client identity in that command context.
- Wrong-identity TLS rejection was NOT executed this session.

Evidence:
- `evidence/ssm_output_edge_mtls_wrong_identity_20261011T152416Z.json`

---

## 4. What is verified this session

Verified:
- CORE listener is bound to `172.31.17.217:8443`.
- CORE runs with `RAGIN_MTLS_REQUIRED=1` and `RAGIN_MTLS_ALLOWED_IDENTITIES=spiffe://ragin/edge`.
- EDGE has OpenSSL-forwarded chain configured to `172.31.17.217:8443` with cert `edge.crt`, key `edge.key`, ca `ca.crt`, verify=1, commonname=172.31.17.217.
- EDGE certificate metadata is compatible with the CORE trust anchor and allowed identity profile:
  - EDGE leaf EKU: `TLS Web Client Authentication`
  - EDGE leaf SAN: `URI:spiffe://ragin/edge`
  - Trust chain issuer: `CN=RAGIN Sprint Staging CA`
- CORE certificate metadata is compatible with the EDGE client trust:
  - CORE server EKU: `TLS Web Server Authentication`
  - CORE server SAN: `IP Address:172.31.17.217`
- Authorized TLS verification from EDGE to CORE succeeded this session.
- Direct HTTPS application probe from EDGE to CORE reached CORE over mTLS with auth and returned 404.

Not verified this session:
- A successful verifier-level application response for the requested service contract.
- Confirmed missing-client-cert TLS rejection.
- Confirmed bad-CA TLS rejection.
- Confirmed wrong-identity TLS rejection.
- Any expired or wrong-purpose certificate handling beyond what is listed above.

---

## 5. Acceptance verdict

- LIVE_MTLS_PASS: NOT established this session
- LIVE_MTLS_TLS_VERIFICATION: VERIFIED this session for the authorized identity from EDGE to CORE.
- LIVE_MTLS_APPLICATION_REACHABILITY: PARTIAL — reachable over mTLS with auth and returned 404 for the tested endpoint.
- NEGATIVE_CASES: not confirmed this session; at least missing-cert and bad-CA were not demonstrated as rejections.

Required to mark LIVE_MTLS_PASS later:
- A successful verifier-level application response for the real service contract from EDGE to CORE.
- Confirmed negative-case rejection for missing client certificate and at least one untrusted/wrong-identity case in the live deployment.

---

## 6. Historical reconciliation

- Task 3.7 Python mTLS experiment on port 24443 and the later 72-hour staging material on port 8443 are DIFFERENT runs and are not merged here.
- The current deployment is a third, separately verified state: CORE listener on `172.31.17.217:8443`, mTLS required, allowed identity `spiffe://ragin/edge`.
- Current certificate validity windows are short and staged: CA and leaf certs valid `Oct 8 20:13:49/50 2026 GMT` to `Oct 11 20:13:49/50 2026 GMT`.
- Because the current certs are near expiry relative to this session timestamp, any future live test must account for validity, renewal, or replacement before relying on these exact files.

Evidence for validity:
- `evidence/ssm_output_core_cert_inventory_*.json`
- `evidence/ssm_output_edge_cert_inventory_*.json`

