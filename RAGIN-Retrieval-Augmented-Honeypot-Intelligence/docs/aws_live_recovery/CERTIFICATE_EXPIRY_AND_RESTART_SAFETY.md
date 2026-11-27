# RAGIN AWS Live Recovery — Certificate Expiry and Restart Safety

Status: certificate renewal PREPARED; no rotation executed.

---

## 1. Current certificate validity

Verified itemized expirations referenced from prior live inventory:

- EDGE client certificate: `2026-10-11T20:13:50Z`
- Staging CA: `2026-10-11T20:13:49Z`

Current UTC assumption for this document: approximately `2026-10-11T20:22Z`.

Time remaining on the current staged materials: already expired or within minutes of expiry under the current UTC assumption. Treat the current staging CA and EDGE client certificate as **expired or about to expire** for any further reliance.

Impact:

- Any new EDGE-to-CORE mTLS operation that depends on the current staging CA or current EDGE client certificate is at risk or already broken.
- A positive or negative test that works today cannot be assumed to work after the current staging materials lapse.
- Do not claim a valid authenticated session using an expired certificate.

CORE certificate expiry must be independently confirmed live before it can be stated precisely. The current document marks it `CHECK_REQUIRED_LIVE` rather than asserting a value.

---

## 2. Expected expiry impact

If the staging CA lapses first:

- The CORE trust store that validates the EDGE client certificate through the staging CA can lose trust in the current client certificate.
- EDGE may still present the client certificate, but CORE may no longer accept it.

If the EDGE client certificate lapses:

- Even with a valid CA, an expired client certificate should not be presented as a live authenticated identity.

Operational impact:

- Current live mTLS acceptance results in this session were obtained while the credentials were treated as live; those results remain as executed evidence, but future retries may fail on the same certificate material.
- Any further meaningful live acceptance test should either use currently valid credentials or be explicitly framed as retrying under renewed credentials.

---

## 3. Runtime TLS path discrepancy

Previous inventory reported that CORE runtime environment references:

- `/run/ragin/tls/server.crt`
- `/run/ragin/tls/server.key`
- `/run/ragin/tls/ca.crt`

but that a runtime TLS directory did not exist at the time of inspection.

That discrepancy is still open. Possible explanations that must be resolved before a restart is attempted:

- The paths are stale environment values that do not reflect where the running process actually loaded its certificates.
- The service loaded certificates earlier and is now running without them present at the documented paths.
- The runtime filesystem namespace differs from the namespace inspected during the last SSM probe.
- A symlink, bind mount, or tmpfs path exists that was not captured.
- A future restart may fail because the expected TLS files are missing or are expected at the wrong paths.

Current status:

- Runtime loading behavior: `UNRESOLVED`
- Restart safety: `DO_NOT_RESTART_WITHOUT_RESOLUTION`

Do not restart CORE to investigate this. Resolve the live loading path and startup configuration before any restart.

---

## 4. Safe renewal plan

This plan is prepared only. It is not authorized and not executed.

1. Confirm current CORE certificate expiry live and record exact UTC values.
2. Confirm current EDGE client certificate and CA status live.
3. Decide the renewal authority:
   - Continue with the existing trusted staging CA if it is still within policy and acceptable, or
   - Replace with an approved CA if the staging CA is no longer acceptable.
4. Issue renewed materials with a proper staging validity period, not an unexplained three-day lifetime.
5. Ensure CORE server certificate includes the expected serverAuth EKU and the expected SAN or subject identity for CORE.
6. Ensure EDGE client certificate includes the expected clientAuth EKU and the expected URI identity `spiffe://ragin/edge`.
7. Preserve SKI/AKI linkage and CA constraints as required by the signing workflow.
8. Place renewed files with correct ownership and permissions.
9. Deploy renewed files atomically per host, without exposing secrets in command output.
10. Verify the service reload or restart loads the renewed materials correctly:
    - listener starts
    - mTLS still accepts the authorized EDGE identity
    - negative cases still reject unauthorized clients
11. If anything fails, roll back to the last known-good materials and confirm service recovery.
12. Before and after renewal, do not print private keys or full credential material in any report or command output; preserve only sanitized fingerprints, expiry, and validation metadata.

---

## 5. Restart safety tests

Before any restart, confirm:

- The actual certificate paths loaded by the running service are known.
- The systemd or process-manager startup configuration references the correct paths.
- Renewed files are in place and readable by the service identity.
- The listener binds to `172.31.17.217:8443` after restart.
- A positive EDGE-to-CORE mTLS probe still succeeds.
- A missing-client-cert probe still does not yield a successful authenticated application response.

Rollback acceptance tests:

- Restore the previous known-good certificate material.
- Restart or reload the service.
- Confirm the previous positive and negative behavior is restored.

---

## 6. Exact requested authorization

Requested approvals:

1. Confirm whether renewal or replacement is required for the current staging CA and EDGE client certificate.
2. Approve the renewal/replacement approach and validity period.
3. Approve any change to the CORE trust store or client identity configuration.
4. Approve the specific bounded SSM operations needed to place, verify, and roll back renewed materials.
5. Approve any required service reload or restart, only after the runtime TLS path discrepancy is resolved.

Do not issue, deploy, rotate, or replace certificates without explicit approval for the exact operation.

---

## 7. Restart and rollback acceptance

Restart acceptance:

- Known certificate paths
- Verified startup configuration
- Verified private key and CA files present with correct permissions
- Verified listener bind on the expected private address
- Verified positive mTLS acceptance from the authorized EDGE identity
- Verified negative rejection of unauthorized clients

Rollback acceptance:

- Ability to return to the previous known-good materials
- Ability to recover service state after rollback
- Verified restored behavior matches the last accepted state

---

## 8. Evidence to preserve for any future renewal

- Current UTC time at decision time
- CORE leaf expiry
- EDGE leaf expiry
- CA expiry and constraints
- SANs and URI identities
- EKU and Key Usage
- Public certificate fingerprints
- Trust-store paths
- Runtime loading status
- Service startup configuration reference
- Renewal command metadata and SSM command IDs if used
- Any rollback executed and its result

Do not preserve private keys, key material, or credential fragments in evidence.
