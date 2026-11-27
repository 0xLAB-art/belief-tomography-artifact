# 07 — Next Execution Plan

**Status at session end:** Phase 0 reconciliation done, P0 security acceptance done, deployable pipeline service defined + image built, local-mock E2E run done and evidence captured, AWS state not verified.

**Principle:** continue in dependency order; do not jump to AWS before the local verified pipeline is running and the remaining P0/P1 items are resolved.

---

## 07.1 Already completed this session

- Reconciled audit contradictions (R0.1–R0.6) and wrote corrections.
- Verified the final-served-artifact contract against source and tests.
- Added production-auth warning + enforcement helpers + 3 regression tests.
- Confirmed legacy/standalone bypass paths are disabled and regression-tested.
- Added `pipeline` service to `docker-compose.yml` and built the image.
- Ran a local-mock E2E through the mandatory verification path and captured correlated evidence.

---

## 07.2 Immediate next work (before any AWS or field work)

### 1. Make the pipeline a running local stack

Acceptance:
- `docker compose up -d pipeline redis gateway` starts cleanly in an isolated env.
- `docker compose ps` shows pipeline healthy.
- `/health` returns 200 with `harness: active`.

 blockers already seen this session:
- nginx hard interpolation blocked `up` when `RAGIN_API_KEY` unset. Already softened for local runs. Confirm the stack now starts.
- Gateway healthcheck uses curl; confirm gateway healthcheck endpoints match what the compose assumes.

If the stack starts, the next step is to expose a loopback-only path and exercise `/v1/chat/completions` over HTTP with a mocked backend, then with the real gateway if available.

### 2. Close the P0-B production guard question explicitly

Decision needed:
- Either allow local-dev disabled-auth to keep starting (with warning), or
- Add a hard startup refusal for disabled auth when bind is non-loopback / or when deployed outside documented isolated local posture.

If the hard refusal is chosen, add the corresponding regression test and document the local-dev exception precisely.

### 3. Harden `_TRANSCRIPT_MAP` for field longevity (P1-2)

Acceptance:
- bounded LRU-style eviction instead of full clear,
- configurable max size,
- document that `X-Session-Id` is the preferred pinning mechanism,
- session continuity survives restarts via disk-backed sessions.

### 4. Add a live HTTP ingress test for the pipeline service

This is the next proof after the mock runner: start the pipeline container, POST to its `/v1/chat/completions` from the host or another container, and correlate request id, session id, verifier decision, approval, serve_path, and served digest.

Do not claim a full Cowrie SSH integration until Cowrie is attached and an SSH session is actually exercised.

---

## 07.3 After local pipeline is running and HTTP-ingress proven

### 5. Cowrie bridge integration (real SSH path)

Acceptance:
- Cowrie attached to same internal network,
- `RAGIN_BRIDGE_HOST=pipeline`,
- an SSH session reaches the bridge,
- the served output is correlated to a verifier decision and approval.

### 6. Provider path decision

If a provider will be used in deployment:
- configure a non-placeholder provider key out of repo,
- exercise provider transport through the pipeline,
- confirm fail-closed behavior on provider error,
- confirm no unverified fallback becomes the serving path.

If no provider will be used: keep the deterministic fast-path + template fallback posture and document it.

### 7. Rate limiting for server_v2 (P1-1)

Acceptance:
- rate limit middleware on server_v2,
- health/ready exempt,
- bridge endpoint rate-limited,
- test for throttling.

---

## 07.4 AWS readiness (only after credentials available)

1. Re-authenticate AWS CLI (separate authorization step; not assumed).
2. Run read-only inventory:
   - instance state/type for CORE and EDGE,
   - EBS encryption,
   - public/Elastic IP status,
   - security groups,
   - route table/subnet placement,
   - IAM roles,
   - SSM reachability,
   - any existing paid services.
3. Build the approval packet from actual current state (see 06_AWS_READINESS_AND_APPROVAL.md outline).
4. Do not execute paid/disruptive changes without explicit approval.

---

## 07.5 Research and paper items (separate from deployment)

These are important but not part of the deployment remediation track:

- Full test suite run (1837 collected; execute and record pass/skip/fail).
- CTI manual audit and human eval reproducibility checks.
- Chrollo classifier artifact and metrics verification.
- SP2027 rescue benchmark and overnight 20261009 artifacts — inspect before relying on them.
- deception.py maintainability split (P2-5) — large effort, depends on stable baseline.

---

## 07.6 Prioritized next milestone

**Next milestone:** running local verified pipeline with HTTP ingress proof and the P0-B production guard decision made.

Success criteria for that milestone:
- `pipeline` service starts and stays healthy in Compose.
- `/health` reports `harness: active`.
- A non-Cowrie HTTP request to `/v1/chat/completions` is correlated end to end.
- P0-B guard policy is explicitly decided and regression-tested.
- AWS remains untouched until credentials and read-only inventory exist.

Do not declare the RAGIN project complete at that point. The later workstreams — permanent AWS generator connectivity, private encrypted CORE migration, security field readiness, Laya real inference, full research experiments — remain separate.
