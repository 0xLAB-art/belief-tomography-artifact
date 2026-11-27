# 10 — Priority Remediation Roadmap

**Method:** Dependency-aware prioritization of P0/P1/P2/P3 tasks. Each item has clear acceptance criteria. DO NOT implement these during the audit — this is a plan for future work.

## 10.1 P0 — Critical (fix before any production deployment)

### P0-1: Prevent RAGIN_REQUIRE_AUTH=false from disabling auth in production

**Problem:** When RAGIN_REQUIRE_AUTH=false (or unset to false) AND API_KEY is empty, server_v2.py:_request_authorized() returns True for all requests. There is no warning, no log, no guard.

**Acceptance criteria:**
1. server_v2.py emits a WARNING log when REQUIRE_AUTH is False and the server starts
2. server_v2.py emits a WARNING log when API_KEY is empty and REQUIRE_AUTH is False
3. docker-compose.yml does NOT set RAGIN_REQUIRE_AUTH=false (it should explicitly set it to "1" or leave it unset which defaults to enabled)
4. .env.example explicitly documents that RAGIN_REQUIRE_AUTH must be "1" or "true" in production
5. A test asserts that with REQUIRE_AUTH=False and API_KEY="", the auth middleware allows all requests (documenting the current behavior), AND a second test asserts that a future fix would reject this

**Dependency:** None — standalone change to server_v2.py.

### P0-2: Make the provider transport framework production-ready (if it will be used)

**Problem:** ProviderTransport is implemented and tested (11/11 PASS) but has no live provider configured. If the project intends to use a paid LLM provider in production, the provider transport needs: (1) a real provider URL + key, (2) timeout tuning, (3) retry policy review, (4) cost tracking integration, (5) circuit breaker integration with the existing hisoka circuit breaker.

**Acceptance criteria:**
1. A non-placeholder provider API key is configured in the deployment environment (NOT in the repo)
2. ProviderTransport.generate() succeeds against the live provider for a test prompt
3. The provider URL is reachable from the Docker network (ragin-internal → gateway → provider)
4. Provider errors are handled gracefully (fallback to deterministic template, not crash)
5. Cost tracking records provider costs (uses existing CostTracker in Hisoka)
6. The provider is NOT reachable from outside the Docker network (egress restricted to ragin-internal → gateway → provider)

**Dependency:** P0-1 (auth must be secure before adding a provider with credentials).

### P0-3: Wire server_v2 as a Docker Compose service (if the pipeline is the production path)

**Problem:** The standard docker-compose.yml runs server.py (legacy) for chrollo/don/hisoka/jev services. server_v2 (the auth-authoritative pipeline with mandatory verification) is NOT a Docker Compose service. If server_v2 is the intended production serving path, it needs a Docker service definition.

**Acceptance criteria:**
1. docker-compose.yml has a `pipeline` service (or renames an existing service) that runs `python -m ragin.server_v2 --mode pipeline`
2. The pipeline service is on ragin-internal network (isolated from internet)
3. The pipeline service can reach the gateway (on ragin-internal + ragin-external)
4. The Cowrie container can reach the pipeline service (RAGIN_BRIDGE_HOST configured, or a new ragin-cowrie-net network)
5. The pipeline service has RAGIN_API_KEY set (for auth middleware)
6. The pipeline service does NOT expose ports to the host directly (only accessible via NGINX or internal network)
7. Health check passes (/health returns 200 with harness=active)

**Dependency:** P0-1 (API key must be set), P0-2 (if provider transport is used).

## 10.2 P1 — High (fix before field deployment)

### P1-1: Add rate limiting to server_v2

**Problem:** server_v2 has no rate limiting middleware. server.py has it. If server_v2 is exposed without NGINX, it's vulnerable to request flooding.

**Acceptance criteria:**
1. server_v2.py has a rate_limit_middleware (similar to server.py's)
2. The middleware is added to the middleware list in create_app()
3. Health/ready endpoints are exempt from rate limiting
4. A test asserts that rapid requests from the same IP are throttled
5. The default rate limits are documented (suggested: 60 req/min general, 12 req/min for the bridge endpoint)

**Dependency:** None — standalone change.

### P1-2: Fix _TRANSCRIPT_MAP session resolution for long-running field deploys

**Problem:** The in-memory dict grows to 20K entries then clears entirely. No persistence across restarts. For long-running field deployments with many sessions, this causes memory pressure and session continuity loss.

**Acceptance criteria:**
1. Session continuity survives a server_v2 restart (sessions persist on disk via Session.wake())
2. The transcript map uses a bounded LRU eviction (not a full clear when full)
3. The transcript map size is configurable (RAGIN_TRANSCRIPT_MAP_MAX env)
4. A test simulates 20K+ sessions and asserts memory stays bounded
5. Document that X-Session-Id header is the preferred session pinning mechanism (transcript-prefix is a fallback for Cowrie's LLM backend which doesn't send session headers)

**Dependency:** None — standalone change to server_v2.py.

### P1-3: Centralize persona identity definitions

**Problem:** The 5 persona identities are defined in deception.py but used in 3+ places (deception.py, fiction.py, host_fiction.py). If an identity changes, multiple files must be updated.

**Acceptance criteria:**
1. A single source of truth for persona identities (could be deception.py _IDENTITIES, or a new config file)
2. fiction.py and host_fiction.py import from the central source (not duplicate the values)
3. A test asserts that the identity used by fiction.py matches the identity in deception.py for each skill level
4. The authorization policy (_AUTHORIZATION_POLICY in deception.py) remains the single source of truth for privilege fiction (it already is)

**Dependency:** None — refactoring change.

### P1-4: Document and test the full verification chain end-to-end

**Problem:** The verification chain spans 4 components (FictionConsistencyVerifier, HostFictionVerifier, supported_claims, bridge_verifier_artifact in harness.py). The boundaries are clear in code but not documented for reviewers.

**Acceptance criteria:**
1. A single document (or diagram) shows the full verification chain with the order of checks and what each check does
2. A test sends a candidate through the full chain (all 4 layers) and asserts the correct serve_path label is set
3. The documentation clarifies when each layer is active (e.g., HostFictionVerifier only when host_store is installed, supported_claims only when RAGIN_FAIL_CLOSED=1, bridge_verifier_artifact only on the bridge path for supported commands)

**Dependency:** P1-3 (centralized identities helps clarify the identity-pin check).

### P1-5: Add rate limiting and request size limits to the Cowrie bridge endpoint

**Problem:** The /v1/chat/completions endpoint in server_v2 has no rate limiting and the request size limit (RAGIN_MAX_REQUEST_BYTES=1MB default) applies to all endpoints. A malicious Cowrie backend (or attacker who compromises Cowrie) could send large payloads.

**Acceptance criteria:**
1. The /v1/chat/completions endpoint has a specific rate limit (suggested: match the lure rate limiter, 12 req/min per IP)
2. The endpoint enforces the request size limit (already does via RAGIN_MAX_REQUEST_BYTES)
3. A test asserts that rate limiting applies to the bridge endpoint
4. Log rate limit violations for field monitoring

**Dependency:** P1-1 (rate limiting infrastructure).

## 10.3 P2 — Medium (fix before paper submission or major release)

### P2-1: Run the full test suite and record results

**Problem:** This audit ran 471 tests across 6 suites. The full suite (93 files, including integration and e2e) was not run. Previous reports of 1413/1657/1639 passed suggest a larger suite exists but the selection is unclear.

**Acceptance criteria:**
1. Run `pytest tests/ -v --tb=short` with the .venv and record the full result (pass/fail/skip counts)
2. Identify which tests are skipped and why (missing LLM backend, AWS credentials, etc.)
3. Fix any failing tests (not weaken assertions)
4. Record the full result in the audit output

**Dependency:** An LLM backend (OpenCode bridge) running locally for tests that need it. AWS credentials for AWS-dependent tests (if any).

### P2-2: Verify CTI manual audit and human eval reproducibility

**Problem:** The CTI manual audit (766KB corpus, 3 blinded annotators) and human eval (multiple scored dirs) are key paper claims but were not verified in this audit.

**Acceptance criteria:**
1. Run cti_manual_audit.py (or the relevant script) and verify the corpus produces the reported annotations
2. Run human_blind_eval.py and verify the scored results match the paper's claims
3. Check that the blinding key (cti_audit_blinding_key.json) properly blinds annotator identities
4. Verify annotator agreement metrics (if reported in the paper)

**Dependency:** The CTI corpus and human eval data are present. The scripts need to be run. No LLM backend needed for the audit corpus (it's already labeled).

### P2-3: Verify Chrollo classifier artifact and metrics

**Problem:** The classifier's reported 0.8875 accuracy (Wilson CI [0.853, 0.914]) needs verification against the model artifact and benchmark_report.json.

**Acceptance criteria:**
1. The model artifact (models/chrollo/rf_classifier.joblib) exists and is loadable
2. Run benchmark_core.py (or the relevant script) and verify the accuracy matches
3. Check that the training manifest (training_manifest.json) and tuning manifest (tuning_manifest.json) are consistent with the reported metrics
4. Verify the feature set (baseline vs baseline+ngram) matches what's reported

**Dependency:** The model artifact and training data. The benchmark scripts may need an LLM backend for some evaluations.

### P2-4: Clean up temporary files and stale artifacts

**Problem:** scripts/_tmp_* (14 files), run/strace_server.* (13 files), run/setsid_test.out, run/mock.out, ragLegendre/ directory, harness.py.bak20261010, bandit-report.json — all untracked temporary or stale files.

**Acceptance criteria:**
1. All _tmp_* files are deleted or moved to a temp/ directory
2. run/strace_server.* files are deleted (they're debug artifacts from a specific run)
3. ragLegendre/ is deleted if it's stale (verify it's not needed first)
4. harness.py.bak20261010 is deleted or moved to a backups/ directory
5. bandit-report.json is moved to a scans/ directory or deleted (it's a one-time scan artifact)

**Dependency:** None — cleanup only.

### P2-5: Split deception.py into focused modules

**Problem:** deception.py is 3195 lines with 100+ regex patterns, 20+ functions, and 5 major concerns (prompt templates, identities, danger patterns, secret patterns, prose tell patterns, scrubbing). This is a maintainability risk.

**Acceptance criteria:**
1. deception.py is split into: deception_core.py (ResponseGenerator, persona selection, scenario identity, deterministic fast-paths), danger_patterns.py (all pattern tuples + matching functions), prompt_templates.py (system prompt, identity block, role prompts, persona configs), identity_policy.py (identities, authorization policy, _id_line, _sudo_text_for, etc.)
2. All existing tests still pass after the split (the hisoka tests import from deception — they need to be updated to import from the new modules)
3. No behavior change — the split is purely organizational
4. Import order and circular dependencies are resolved (deception_core imports danger_patterns, not the other way)

**Dependency:** P2-1 (test results give confidence the split doesn't break anything).

### P2-6: Document the configuration hierarchy

**Problem:** Settings are spread across .env.example, .env.field.example, settings.yaml, and docker-compose.yml with unclear precedence.

**Acceptance criteria:**
1. A document (or README section) lists every configuration variable, its source (env var, YAML key, docker-compose env), its default, and its purpose
2. The precedence order is documented (env var > YAML > default)
3. The settings.yaml `${...}` placeholder expansion issue is documented (yaml.safe_load does NOT expand these — they're passed through as literal strings)
4. A diagram shows which component reads which config source

**Dependency:** None — documentation only.

## 10.4 P3 — Low (continuous improvement)

### P3-1: Add tests for untested components

**Problem:** RBAC, Decoys, SIEM, Rollout, Coordination, Intelligence, Monitoring (partial) have no or limited tests.

**Acceptance criteria:**
1. At least one test per untested component (smoke test level)
2. The coordination path (if used) has tests for Supervisor routing, ExpertPool dispatch, VotingSystem voting
3. The SIEM connectors have tests for the connection/parsing logic (mocking the external service)

**Dependency:** P2-1 (full test run gives the baseline).

### P3-2: Add mTLS to Docker Compose (if EDGE↔CORE pattern is needed)

**Problem:** The Docker Compose doesn't configure mTLS. The mTLS code is implemented and tested (test_mtls_transport.py) but not wired into the compose file.

**Acceptance criteria:**
1. docker-compose.prod.yml (or a new docker-compose.mtls.yml) configures RAGIN_MTLS_REQUIRED=1
2. The mTLS certificates are generated (or mounted) for the server and clients
3. RAGIN_MTLS_ALLOWED_IDENTITIES is set to the allowed service identities
4. A test asserts that a client without a valid certificate gets 403

**Dependency:** Certificate generation/management infrastructure.

### P3-3: Add structured logging to server_v2

**Problem:** server_v2 uses basic logging. Structured JSON logging would help with field data collection and monitoring.

**Acceptance criteria:**
1. server_v2 logging outputs JSON with structured fields (timestamp, component, session_id, request_id, etc.)
2. The log format is configurable (JSON vs human-readable via RAGIN_LOG_FORMAT env)
3. A test asserts that log output contains the expected fields

**Dependency:** None — standalone change.

### P3-4: Add secret scanning to CI

**Problem:** .gitleaks.toml exists but it's unclear if gitleaks runs in CI. .github/workflows/ci.yml was modified this session.

**Acceptance criteria:**
1. .github/workflows/ci.yml includes a gitleaks step (or a separate security workflow)
2. The gitleaks scan runs on every push and pull request
3. Secret findings block the CI run (or at least post a warning)

**Dependency:** P2-4 (cleanup temporary files first — some _tmp_* files might contain secrets from recent runs).

### P3-5: Externalize prompt templates

**Problem:** The system prompt, identity block, and role prompts are hardcoded in deception.py. The settings.yaml references template dirs that don't exist.

**Acceptance criteria:**
1. Prompt templates are externalized to files (Jinja2 or plain text) in ragin/prompt/templates/
2. deception.py reads the templates from files (with a fallback to the hardcoded defaults for backward compatibility)
3. The settings.yaml template_dir setting works (points to the actual template directory)
4. A test asserts that the prompts are loaded from files and match the expected content

**Dependency:** P2-5 (splitting deception.py makes this easier).

## 10.5 Roadmap summary

| Priority | Task | Effort | Dependency | Acceptance criteria count |
|----------|------|--------|------------|---------------------------|
| P0 | P0-1: Prevent auth disable in production | Small | None | 5 |
| P0 | P0-2: Provider transport production-ready | Medium | P0-1 | 6 |
| P0 | P0-3: Wire server_v2 as Docker service | Medium | P0-1, P0-2 | 7 |
| P1 | P1-1: Add rate limiting to server_v2 | Small | None | 5 |
| P1 | P1-2: Fix _TRANSCRIPT_MAP for field deploys | Medium | None | 5 |
| P1 | P1-3: Centralize persona identities | Small | None | 4 |
| P1 | P1-4: Document full verification chain | Small | P1-3 | 3 |
| P1 | P1-5: Rate limit + size limit on bridge endpoint | Small | P1-1 | 4 |
| P2 | P2-1: Run full test suite | Medium | LLM backend | 4 |
| P2 | P2-2: Verify CTI + human eval reproducibility | Medium | None | 4 |
| P2 | P2-3: Verify Chrollo classifier artifact | Small | Model artifact | 4 |
| P2 | P2-4: Clean up temporary files | Small | None | 5 |
| P2 | P2-5: Split deception.py | Large | P2-1 | 4 |
| P2 | P2-6: Document config hierarchy | Small | None | 4 |
| P3 | P3-1: Tests for untested components | Large | P2-1 | 3 |
| P3 | P3-2: Add mTLS to Docker Compose | Medium | Cert infra | 4 |
| P3 | P3-3: Structured logging for server_v2 | Small | None | 3 |
| P3 | P3-4: Secret scanning in CI | Small | P2-4 | 3 |
| P3 | P3-5: Externalize prompt templates | Medium | P2-5 | 4 |

**Total: 19 tasks, 5 P0, 5 P1, 6 P2, 5 P3**

**Immediate next steps (this week):**
1. P0-1: Add auth warning logs to server_v2.py
2. P2-4: Clean up temporary files
3. P2-1: Run the full test suite and record results

**Before any field deployment:**
1. P0-1, P0-3: Auth must be secure, server_v2 must be the Docker service
2. P1-1, P1-2: Rate limiting and session resolution must be field-ready
3. P1-4: The verification chain must be documented for reviewers

**Before paper submission:**
1. P2-1: Full test suite results recorded
2. P2-2, P2-3: CTI + human eval + classifier claims verified against artifacts
3. P1-4: Verification chain documented
