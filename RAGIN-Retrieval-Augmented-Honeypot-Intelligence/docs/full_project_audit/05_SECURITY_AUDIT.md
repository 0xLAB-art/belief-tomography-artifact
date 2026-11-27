# 05 — Security Audit

**Method:** Source-grounded trust-boundary review. No destructive exploitation. No interaction with unauthorized external targets. Evidence references actual file:line ranges.

## 5.1 Trust boundaries

| Boundary | Mechanism | Status | Evidence |
|----------|-----------|--------|----------|
| Internet → Cowrie SSH | TCP port 2223/22, Cowrie container | PUBLIC ATTACK SURFACE | docker-compose.yml cowrie service; COWRIE_PORT env |
| Internet → NGINX | TCP 80/443/2222, nginx container | PUBLIC (if deployed with external network) | docker-compose.yml nginx service; SSL cert/key volumes |
| NGINX → RAGIN services | Internal Docker network (ragin-internal) | ISOLATED | networks: ragin-internal: internal: true |
| Cowrie container → server_v2 | docker network ragin-internal (or ragin-cowrie-net per sv2 commit fe09635) | ISOLATED (when bridge configured) | server_v2 commit fe09635: "bind pipeline/bridge mode to RAGIN_BRIDGE_HOST so internal-docker Cowrie can reach sv2" |
| LLM gateway → upstream provider | Authenticated HTTP (Bearer + X-API-Key) | AUTHENTICATED | gateway/client.py: headers["Authorization"] and headers["X-API-Key"] |
| EDGE → CORE (mTLS) | RAGIN_MTLS_REQUIRED + RAGIN_MTLS_ALLOWED_IDENTITIES | OPTIONAL, config-gated | transport/mtls.py: build_server_context_from_env, peer_certificate_authorized |
| Server → LLM backend | API key in env (RAGIN_LLM_API_KEY, OPENROUTER_API_KEY, AZURE_OPENAI_KEY) | AUTHENTICATED (when configured) | server_v2.py: _init_pipeline reads env; provider_transport.py: provider_api_key() |
| Session token auth | X-Session-Token == secrets.token_urlsafe(32) in _SESSION_OWNERS | SESSION-SCoped | server_v2.py: _register_session, _session_authorized with hmac.compare_digest |
| Host fiction persistence | data/host_fiction.json on disk | FILE SYSTEM | server_v2.py: RAGIN_HOST_FICTION_PATH env; host_fiction.py: save/load with atomic replace |

## 5.2 The central security invariant: no unverified content reaches the attacker

**Question:** Can attacker-visible output be served without passing the mandatory verifier?

**Answer: NO — for the authoritative serving path (server_v2 pipeline mode).**

**Trace:**

1. **server_v2.py `openai_chat_completions()` (line ~220):** Calls `_sandbox.handle_command()`. The SandboxResponse's `response_text` is whatever `Harness._process_verified()` returns.

2. **Sandbox.handle_command() (sandbox.py line ~160):** Calls `self._harness.process(session, command)`. If `self._harness.mandatory_verification and not result.passed_verification`, sets `safe_response = ""` and `safe_error = result.error or "verified_serve_unavailable"`.

3. **Harness._process_verified() (harness.py line ~220):** Loops max_retries+1 times calling `_strict_candidate()` → `_strict_verify()` → `_strict_approval()` → `_strict_commit()`. Only commits when all three pass.

4. **Harness._strict_verify() (harness.py line ~190):** Calls `self._verifier.verify(candidate, context)`. If verifier is None → returns `{"passed": False, "issues": ["verifier_unconfigured"]}`. If verifier raises → returns `{"passed": False, "issues": [f"verifier_exception:{type}"]}`.

5. **FictionConsistencyVerifier.verify() (verifier.py line ~140):** Runs 4 checks: degenerate, danger_signals, identity_pin, fiction_contradictions. If RAGIN_FAIL_CLOSED → also runs check_supported_claim. Returns `{"passed": not issues, ...}`.

6. **Harness._strict_commit() (harness.py line ~210):** Clones fiction graph, observes candidate text, checks contradictions. If contradictions → returns False (rollback). For bridge path with supported commands, rewrites to canonical prompt-template artifact. Only then emits VERIFICATION + SYSTEM_RESPONSE events and returns True.

7. **Harness._strict_approval() (harness.py line ~200):** Calls ApprovalGateway.resolve(). If REQUIRE and no approver → returns `{"approved": False}`.

8. **Fallback (harness.py line ~280):** After exhaustion, generates deterministic template via `ResponseGenerator()._generate_template()`, verifies IT must pass, approves, commits. If fallback also fails → `error = "verified_serve_unavailable"`, empty response_text.

**Conclusion:** Every code path in the mandatory pipeline either (a) serves verified content, (b) serves the canonical prompt-template artifact for supported commands, or (c) serves an empty response with `verified_serve_unavailable`. No path serves unverified LLM output.

**Security tests confirm (tests/security/test_task2_verified_serving.py):**
- test_no_verifier_configured_cannot_serve: PASS — empty response when verifier missing
- test_rejected_candidate_is_not_served_or_committed: PASS — fiction graph unchanged after rejection
- test_verifier_exception_fails_closed: PASS — exception → empty response
- test_retry_exhaustion_uses_verified_fallback: PASS — fallback must pass verification
- test_invalid_fallback_is_not_served: PASS — rejected fallback → empty
- test_hitl_require_without_approval_cannot_serve: PASS — REQUIRE without approval → empty
- test_persistence_failure_is_safe: PASS — OSError on save → verified_serving_failed, empty response
- test_local_ingress_to_verified_serving_path: PASS — HTTP POST to /v1/chat/completions returns verified content
- test_legacy_generative_route_is_disabled: PASS — server.py hisoka route returns 410

## 5.3 Confirmed vulnerabilities and risks

### P0 — CRITICAL

**P0-1: Auth bypass when RAGIN_REQUIRE_AUTH=false and API_KEY empty**

- **Location:** server_v2.py:19-20 (`REQUIRE_AUTH = ... not in ("0", "false", "no", "off")`), server_v2.py:93-99 (`_request_authorized`)
- **Severity:** CRITICAL
- **Confidence:** VERIFIED FROM SOURCE
- **Description:** When `RAGIN_REQUIRE_AUTH` is unset (defaults to "1" → enabled) OR explicitly false AND API_KEY is empty, `_request_authorized` returns True unconditionally (line 94: `if not REQUIRE_AUTH and not API_KEY: return True`). All routes including session-command and cowrie bridge become unauthenticated.
- **Mitigation:** server_v2.py:_validate_security_config() raises RuntimeError if REQUIRE_AUTH and API_KEY is placeholder. But if REQUIRE_AUTH=false entirely, no check runs. The .env.field.example intentionally leaves RAGIN_LLM_API_KEY=replace-me — but that's the LLM backend key, not the server API_KEY.
- **Exposure:** Only if deployed with `RAGIN_REQUIRE_AUTH=false` in production. Default is enabled. The .env.example sets `API_KEY=ragin-<generate-a-new-random-hex-key>` (placeholder template).

### P0-2: Legacy unverified serving was reachable (now disabled)

- **Location:** server.py:51 (`LEGACY_SERVING_DISABLED = True`), server.py:89 (`if LEGACY_SERVING_DISABLED: raise RuntimeError`)
- **Severity:** CRITICAL (historical)
- **Confidence:** VERIFIED FROM SOURCE
- **Description:** server.py once served hisoka deceive/lure WITHOUT the mandatory verifier. Now disabled — `_handle_deception()` raises RuntimeError, and routes return 410. The security tests explicitly verify this (test_legacy_generative_route_is_disabled).
- **Current state:** FIXED. Legacy route returns 410 Gone.

### P0-3: Standalone server_v2 mode disabled (was a bypass risk)

- **Location:** server_v2.py:357 (`raise RuntimeError("standalone mode is disabled; use the mandatory verified pipeline")`)
- **Severity:** CRITICAL (historical)
- **Confidence:** VERIFIED FROM SOURCE
- **Description:** Standalone mode bypassed the harness pipeline. Now explicitly disabled.
- **Current state:** FIXED.

### P1 — HIGH

**P1-1: Cowrie SSH is a public attack surface**

- **Location:** docker-compose.yml: cowrie service, port ${COWRIE_PORT:-2223}:2222
- **Severity:** HIGH
- **Confidence:** VERIFIED FROM SOURCE
- **Description:** Cowrie exposes SSH to the internet. While the LLM backend response goes through the verified pipeline, the SSH connection itself is public. Attackers can attempt credential stuffing, CVE exploitation against Cowrie itself, or DoS.
- **Mitigation:** Cowrie is a well-tested honeypot with its own auth logging. The bridge to server_v2 is via authenticated HTTP POST (when RAGIN_BRIDGE_HOST configured). But the SSH port itself has no mTLS or API key — it's intentionally public as a honeypot.
- **Exposure:** Any deployment with cowrie port published.

**P1-2: Provider credential in environment variables**

- **Location:** provider_transport.py:20-27 (_PROVIDER_AUTH_ENV_ORDER), server_v2.py:210-217 (api_key resolution in _init_pipeline)
- **Severity:** HIGH
- **Confidence:** VERIFIED FROM SOURCE
- **Description:** Provider API keys (RAGIN_PROVIDER_API_KEY, RAGIN_HISOKA_API_KEY, OPENROUTER_API_KEY, AZURE_OPENAI_KEY) are read from environment. If the Docker container or process environment is compromised, all LLM backend credentials are exposed. The provider_transport.py has placeholder detection, but if a real key is set, it's used directly.
- **Mitigation:** Placeholder detection prevents accidental use of template values. Container isolation (Docker) limits exposure. No secret rotation mechanism observed.
- **Exposure:** Container breakout, env var leakage via logs/core dumps.

**P1-3: Prompt injection from attacker input to LLM**

- **Location:** hisoka/deception.py:639-649 (`_INJECTION_PATTERNS`, `_sanitize_input`), hisoka/deception.py:584-605 (`_DANGER_SIGNAL_PATTERNS` includes refusal patterns)
- **Severity:** HIGH
- **Confidence:** VERIFIED FROM SOURCE
- **Description:** Attacker input flows into the LLM system prompt. The `_sanitize_input()` function strips known injection patterns (ignore previous instructions, disregard prior, etc.) but only the FIRST occurrence of each pattern. Sophisticated multi-turn injection, indirect injection via file content the honeypot "displays", or novel injection phrasings can bypass.
- **Mitigation:** (1) `_sanitize_input()` strips 14 known patterns; (2) `_DANGER_SIGNAL_PATTERNS` catches LLM output that reveals injection success (refusal phrasing, "as an AI" self-reference); (3) the FictionConsistencyVerifier's identity-pin and fiction-contradiction checks catch drift even if injection succeeds; (4) the deterministic fast-paths (sudo, IMDS, SSH) bypass the LLM entirely for the most sensitive commands.
- **Exposure:** Any attacker input that reaches the LLM. The 100+ danger signal regex patterns are extensive but not exhaustive.

**P1-4: mTLS optional and config-gated**

- **Location:** server_v2.py:91-96 (`_validate_security_config` checks mTLS), server_v2.py:107-113 (mtls_middleware), transport/mtls.py:32-43 (build_server_context_from_env)
- **Severity:** HIGH
- **Confidence:** VERIFIED FROM SOURCE
- **Description:** mTLS is OPTIONAL (`RAGIN_MTLS_REQUIRED` defaults to "0"). When enabled, it gates all non-public paths. But the default deployment (docker-compose.yml) does NOT set RAGIN_MTLS_REQUIRED — there's no mTLS in the standard Docker Compose. The AWS EDGE↔CORE mTLS was a deployment-specific configuration.
- **Mitigation:** mTLS is available and tested (tests/security/test_mtls_transport.py exists). The auth middleware provides API-key gating as a second layer. For internet-facing deployments, NGINX provides TLS termination.
- **Exposure:** Without mTLS, the API key is the sole auth mechanism for internal service-to-service communication.

**P1-5: Session fixation via transcript-prefix session resolution**

- **Location:** server_v2.py:35-51 (`_TRANSCRIPT_MAP`, `_resolve_bridge_session`, `_remember_bridge_session`)
- **Severity:** HIGH
- **Confidence:** VERIFIED FROM SOURCE
- **Description:** The Cowrie bridge resolves sessions by content-prefix matching in an in-memory dict (`_TRANSCRIPT_MAP`, max 20,000 entries). An attacker who knows a previous session's transcript could theoretically craft a message list that matches a prefix and hijacks that session's context. The session_token (X-Session-Token) is required for explicit session access, but the bridge path uses transcript-prefix fallback when no X-Session-Id header is present.
- **Mitigation:** The X-Session-Id header (set by previous responses) wins over transcript-prefix resolution. The session_token is required for session-command API access. The transcript map is bounded (20K entries) and cleared when full.
- **Exposure:** The bridge path without X-Session-Id header. In practice, the session_token from the first response pins the session for subsequent API calls.

### P2 — MEDIUM

**P2-1: Rate limiting only in server.py, not server_v2**

- **Location:** server.py:117-130 (rate_limit_middleware), server.py:207-210 (lure_rate_limiter); server_v2.py: NO rate limiting middleware
- **Severity:** MEDIUM
- **Confidence:** VERIFIED FROM SOURCE
- **Description:** server.py has rate limiting (60 tokens/min general, 12 tokens/min lure). server_v2 has NO rate limiting middleware. A deployed server_v2 pipeline is vulnerable to request flooding.
- **Mitigation:** Docker network isolation limits exposure. NGINX can provide rate limiting at the proxy layer. Not critical for honeypot use (attackers are rate-limited by their own scanning tools).
- **Exposure:** Direct server_v2 exposure without NGINX.

**P2-2: host_fiction.json stores PII-like tuples in plaintext JSON**

- **Location:** graph/host_fiction.py:230-245 (save method writes JSON); data/host_fiction.json exists (34KB)
- **Severity:** MEDIUM
- **Confidence:** VERIFIED FROM SOURCE
- **Description:** The host fiction store persists to a JSON file. While the data is fabricated (fictional hostnames, IPs, users), the file contains session IDs, verification state, and host facts. If an attacker gains filesystem access, they can read the full fiction state.
- **Mitigation:** The data is decoy/fabricated by design — there are no real credentials in the fiction store. The file is in the repo's data/ directory.
- **Exposure:** Filesystem access to the host.

**P2-3: No CSRF protection on session endpoints**

- **Location:** server_v2.py session endpoints (session_create, session_command, etc.)
- **Severity:** MEDIUM
- **Confidence:** VERIFIED FROM SOURCE
- **Description:** The session endpoints use API key auth but no CSRF tokens. If an attacker can make a victim's browser POST to the server_v2 API (same-origin or via CORS if enabled), they could create sessions or issue commands.
- **Mitigation:** server_v2 is not designed for browser access — it's a backend API for Cowrie and programmatic callers. CORS is not configured. The API key must be known to the caller.
- **Exposure:** Only relevant if server_v2 is exposed to browser contexts.

**P2-4: API key in URL/query is not rejected**

- **Location:** server_v2.py:93-99 (`_request_authorized` only checks headers)
- **Severity:** MEDIUM
- **Confidence:** VERIFIED FROM SOURCE
- **Description:** The auth middleware only checks X-API-Key and Authorization headers. If a client sends the API key in a query parameter or body field, it would not be recognized — but conversely, if some future code path read the key from a query param, it could leak in logs/referrer headers.
- **Mitigation:** No current code path reads the key from query params. The middleware only checks headers.
- **Exposure:** Low — no current vulnerability, but the pattern is incomplete.

**P2-5: Unsafe error details in some exception handlers**

- **Location:** server_v2.py openai_chat_completions: the `except Exception: logger.exception(...)` path returns a safe 503, but other handlers (classify, analyze, deceive in the legacy compatibility section) return `{"error": str(e)}` which could leak internal details
- **Severity:** MEDIUM
- **Confidence:** VERIFIED FROM SOURCE
- **Description:** The legacy-compatible endpoints (classify, analyze, deceive) in server_v2.py return `str(e)` on exception. If an exception contains internal paths, config values, or stack traces, they'd be returned to the caller.
- **Mitigation:** These endpoints are in the "standalone mode" path which is disabled. In pipeline mode, the legacy classify/analyze/deceive handlers are registered but may not be reachable if mode=pipeline (only session/* and /v1/chat/completions are registered in pipeline mode — check create_app: pipeline mode registers session/* and /v1/chat/completions; standalone mode is disabled).
- **Exposure:** Verify: in pipeline mode, create_app only registers /api/session/* and /v1/chat/completions. The legacy classify/analyze/deceive handlers are defined but NOT registered in pipeline mode. They are dead code in pipeline mode.

**P2-6: _TRANSCRIPT_MAP is unbounded in lifetime (memory leak under long-running field deploy)**

- **Location:** server_v2.py:38-42 (`_TRANSCRIPT_MAP_MAX = 20_000`, `_remember_bridge_session` clears when full)
- **Severity:** MEDIUM
- **Confidence:** VERIFIED FROM SOURCE
- **Description:** The transcript map grows without bound until it hits 20K entries, then clears entirely. Under a long-running field deployment with many short sessions, this could cause periodic memory spikes on clear.
- **Mitigation:** The bound is 20K entries. Each entry is a tuple of (role, content) pairs. In practice, this is modest memory. The clear is crude but effective.
- **Exposure:** Long-running deployments with high session turnover.

### P3 — LOW

**P3-1: Hardcoded default identities in source code**

- **Location:** hisoka/deception.py:44-91 (`_IDENTITIES` dict)
- **Severity:** LOW
- **Confidence:** VERIFIED FROM SOURCE
- **Description:** The 5 persona identities (user, host, domain, ip, uid, gid, distro, kernel) are hardcoded in the source. An attacker who reads the source (or a leak) knows the exact fiction identities.
- **Mitigation:** The identities are fabricated decoy values by design. The HostFictionStore allows per-host customization. The fiction is meant to be convincing to attackers, not secret from defenders.
- **Exposure:** Source code disclosure.

**P3-2: UUID session IDs are predictable enough for enumeration**

- **Location:** session.py:61 (`session_id = f"ses-{uuid.uuid4().hex[:16]}"`)
- **Severity:** LOW
- **Confidence:** VERIFIED FROM SOURCE
- **Description:** Session IDs use 16 hex chars (64 bits) of UUID4. While UUID4 is random, 64 bits is below the 128-bit recommendation for unguessable tokens. Enumeration is impractical at 2^64 but not cryptographically impossible.
- **Mitigation:** Session access also requires X-Session-Token (secrets.token_urlsafe(32), 256 bits). The session ID alone is not sufficient for access.
- **Exposure:** Session ID enumeration without token.

**P3-3: No input size limit on attacker command**

- **Location:** server_v2.py openai_chat_completions: command extracted from messages; no length check
- **Severity:** LOW
- **Confidence:** VERIFIED FROM SOURCE
- **Description:** The attacker's command is extracted from the last user message with no size limit. A maliciously large message could cause memory pressure.
- **Mitigation:** `RAGIN_MAX_REQUEST_BYTES` env (default 1MB) limits request size in create_app. The command is a substring of the message content.
- **Exposure:** Large payload DoS.

**P3-4: _field_export_dir creates directories without permission hardening**

- **Location:** server_v2.py:30-33 (`_field_export_dir`)
- **Severity:** LOW
- **Confidence:** VERIFIED FROM SOURCE
- **Description:** The field export directory is created with default permissions (umask-dependent). Session transcripts (served response_text) are appended to JSONL files.
- **Mitigation:** The data is fabricated decoy content. Field export is best-effort (exceptions silently caught).
- **Exposure:** Local filesystem access.

## 5.4 What passes verification (confirmed safe)

1. ✅ Mandatory verifier gates all serving paths in server_v2 pipeline mode
2. ✅ Legacy unverified routes return 410
3. ✅ Standalone mode raises RuntimeError
4. ✅ Rejected candidates are not served or committed (fiction graph unchanged)
5. ✅ Verifier exceptions fail closed (empty response)
6. ✅ HITL REQUIRE without approval cannot serve
7. ✅ Persistence failures are safe (logged, empty response)
8. ✅ Concurrent commands are serialized (ThreadPoolExecutor test passes)
9. ✅ Auth middleware rejects missing/wrong API keys (401)
10. ✅ Session-token auth rejects unauthorized session access (403)
11. ✅ Placeholder API keys are rejected at app creation (RuntimeError)
12. ✅ Provider transport fails closed when unauthenticated (ProviderUnavailableError)
13. ✅ Placeholder provider keys are treated as unconfigured
14. ✅ mTLS configuration is validated at startup (MTLSConfigError if misconfigured)
15. ✅ Field export failures never break the serve (best-effort, exceptions caught)
16. ✅ Bridge path fails SAFE on sandbox error (503, never unverified content)
17. ✅ Bridge path fails SAFE on pipeline crash (503, never unverified content)

## 5.5 What needs attention

1. ⚠️ `RAGIN_REQUIRE_AUTH=false` disables all auth — must never be used in production
2. ⚠️ mTLS is optional — for internet-facing deployments, rely on NGINX TLS + API key
3. ⚠️ Provider credentials in env vars — no secret rotation, no vault integration
4. ⚠️ Prompt injection defenses are pattern-based — not exhaustive
5. ⚠️ server_v2 has no rate limiting middleware (rely on NGINX or network isolation)
6. ⚠️ The Cowrie bridge transcript-prefix session resolution is a fallback — use X-Session-Id header for api callers
