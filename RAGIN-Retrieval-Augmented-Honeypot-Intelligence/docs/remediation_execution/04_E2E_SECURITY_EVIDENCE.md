# 04 — E2E Security Evidence

**Scope:** correlated request/session/serve-path evidence for the verified pipeline path, using the local-mock E2E run this session.
**Evidence artifact:** `docs/remediation_execution/evidence/local_pipeline_evidence.json`
**Auxiliary artifacts:** session JSONL files under `docs/remediation_execution/evidence/sessions/`, host fiction `docs/remediation_execution/evidence/host_fiction.json`, field export dir `docs/remediation_execution/evidence/field/`

---

## 04.1 Run identity and correlation anchors

- `ssh_session_id`: `ssh-ses-492cec922134`
- `ssh_visibility_id`: `ssh-vis-1791691766-847a7e`
- Run script: `scripts/run_local_pipeline_e2e.sh`
- Env: `docs/remediation_execution/evidence/run.env`

These are the correlation IDs for this run. The `ssh_visibility_id` is the run-level trace identifier; the `ssh_session_id` is the logical SSH session anchor used across the bridge-shaped commands.

---

## 04.2 Records

Five records were produced. All went through the same `Harness._process_verified()` path with a mock deceiver.

### Record 1 — whoami

- via: cowrie-bridge
- command: whoami
- session_id: `ssh-ses-492cec922134-cowrie-bridge-1791691766654`
- response_text: `webapp`
- passed_verification: True
- serve_path: GENERATED_VERIFIED
- candidate_sha256: `2c66f372a6c929fe685806cb8c3039123427268466673bc705c5089ac843883d`
- approval: auto-approved (low risk)
- error: none

### Record 2 — id

- via: cowrie-bridge
- command: id
- session_id: `ssh-ses-492cec922134-cowrie-bridge-1791691766677`
- response_text: `uid=1001(webapp) gid=1001(webapp) groups=1001(webapp),4(adm),999(docker)`
- passed_verification: True
- serve_path: GENERATED_VERIFIED
- candidate_sha256: `fef584204c1a7d5bcb5914ef943fecf7b5ddbfe16729b215f0a87fe4b9997bb1`
- approval: auto-approved (low risk)
- error: none

### Record 3 — hostname (failed closed)

- via: cowrie-bridge
- command: hostname
- session_id: `ssh-ses-492cec922134-cowrie-bridge-1791691766696`
- response_text: (empty)
- passed_verification: False
- serve_path: None
- candidate_sha256: None
- verification issues: `identity-pin: hostname must resolve to 'web-srv-01'`
- error: verified_serve_unavailable
- approval: (empty)

This is the expected fail-closed result for this mock deceiver shape: the generated text did not satisfy the hostname identity-pin, so the harness did not serve it.

### Record 4 — uname -a

- via: cowrie-bridge
- command: uname -a
- session_id: `ssh-ses-492cec922134-cowrie-bridge-1791691766715`
- response_text: `webapp@web-srv-01:~$ uname -a\nwebapp\nwebapp@web-srv-01:~$`
- passed_verification: True
- serve_path: GENERATED_VERIFIED
- candidate_sha256: `0225d1ff232362080afee2dfce5c3c045ac78fa8b96dadef1a2af9f4a7224ed3`
- approval: auto-approved (low risk)
- error: none

### Record 5 — bridge message form whoami

- via: (bridge record, no `command` field; last user message = whoami)
- bridge_messages_count: 2
- bridge_last_user_message: whoami
- session_id: `ssh-ses-492cec922134-bridge-1791691766733`
- response_text: `webapp`
- passed_verification: True
- serve_path: GENERATED_VERIFIED
- candidate_sha256: `2c66f372a6c929fe685806cb8c3039123427268466673bc705c5089ac843883d`
- approval: auto-approved (low risk)
- error: none

---

## 04.3 Verification decisions

- verifier: FictionConsistencyVerifier
- deterministic: True on all records
- accepted: True on the four served records
- serve_paths across records: `GENERATED_VERIFIED, GENERATED_VERIFIED, None, GENERATED_VERIFIED, GENERATED_VERIFIED`
- candidate_sha256s across records: 4 distinct non-null digests, one None for the failed record

This shows the verifier was the gate on every record and the gate decided serve vs not-serve.

---

## 04.4 Approval decisions

- All served records: `approved: true`, level `auto`, reason `auto-approved (low risk)`, decided_by `gateway:auto`
- Failed record: no approval object (serve did not occur)

This shows the HITL/auto gate was also evaluated on every served record and the failed record never reached approval-commit.

---

## 04.5 SSH-visible responses

- whoami: `webapp`
- id: `uid=1001(webapp) gid=1001(webapp) groups=1001(webapp),4(adm),999(docker)`
- hostname: (empty — safe transport error path, not content)
- uname -a: transcript-shaped output including prompt line and answer
- bridge whoami: `webapp`

Every non-empty SSH-visible response in this run carried a `GENERATED_VERIFIED` serve_path and a passed verification decision.

---

## 04.6 Session durability evidence

- Session logs were written to `docs/remediation_execution/evidence/sessions/` as append-only JSONL.
- Sample session file: `ses-660f09d735f640a9.jsonl`
- Host fiction file: `docs/remediation_execution/evidence/host_fiction.json` (created/updated by the run)
- Field export dir: `docs/remediation_execution/evidence/field/`

This confirms the durable log path is live for the pipeline code in this shape.

---

## 04.7 What this proves

- The pipeline can serve verified content through the bridge-shaped path with a mock deceiver.
- The verifier and approval gates are exercised on every record.
- The fail-closed path for an unsatisfied identity-pin is exercised and produces `verified_serve_unavailable`.
- Durable session/host-fiction/field paths are exercised.

---

## 04.8 What this does not prove

- It does not prove live LLM generation behavior; the deceiver was mocked to identity-bound deterministic output.
- It does not prove the full Compose stack serving path over HTTP from Cowrie SSH; that requires a live stack and is left for the next milestone.
- It does not prove provider-backed generation; no live provider was used.
- It does not prove operational session-map longevity under load; that is a separate hardening item.
