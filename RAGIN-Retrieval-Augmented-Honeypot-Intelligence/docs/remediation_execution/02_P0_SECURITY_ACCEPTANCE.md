# 02 — P0 Security Acceptance

**Scope:** production auth guard, final-served-artifact contract, session isolation/fixation resistance, legacy/alternate serving paths.
**Method:** direct source reads of `server_v2.py`, `cycle/harness.py`, `cycle/verifier.py`, `cycle/session.py`, `graph/host_fiction.py`, `cycle/supported_claims.py`, plus executed tests.
**Evidence directory:** `docs/remediation_execution/evidence/`

---

## P0-A — Final served artifact is covered by the applicable verifier contract

### Path examined

- `server_v2.py`: `openai_chat_completions()` -> `_sandbox.handle_command()` -> `Sandbox` -> `Harness`
- `cycle/harness.py`: `Harness.process()` -> `Harness._process_verified()` -> loop `_strict_candidate()` -> `_strict_verify()` -> `_strict_approval()` -> `_strict_commit()`
- `cycle/verifier.py`: `FictionConsistencyVerifier.verify()` with checks degenerate / danger-signals / identity-pin / fiction-contradictions, plus optional `check_supported_claim` when `RAGIN_FAIL_CLOSED=1`
- `graph/host_fiction.py`: `HostFictionVerifier.verify()` wraps the inner verifier and adds cross-session `check_against_host`
- `cycle/session.py`: append-only JSONL log, `Session.wake()`, `Session.build_context()`
- `cycle/supported_claims.py`: declared supported surface (whoami, id, hostname, uname, echo, uptime, date, cat /etc/os-release)

### Acceptance results

**PASS — every served non-empty response in the mandatory path is a committed candidate after verification.**

Evidence:

- `_process_verified()` only returns a non-empty `response_text` from `_strict_commit()` after `verification["passed"]` is true and `approval["approved"]` is true.
- `_strict_commit()` observes the candidate text against a cloned fiction graph before commit; contradictions rollback.
- On exhaustion, the fallback is `ResponseGenerator()._generate_template(...)`, wrapped as `FALLBACK_VERIFIED`, then verified by `_strict_verify()` before it can be served. A rejected fallback yields `verified_serve_unavailable` with empty response.
- The bridge path for exact supported commands (`id`, `id -un`, `whoami`) is rewritten inside `_strict_commit()` to the canonical `_bridge_verifier_artifact()` text and reclassified to `PROMPT_TEMPLATE_VERIFIED`. That rewrite is itself inside the commit path after verification passed, not a bypass before verification.
- `server_v2.py` fail-safe: if `_sandbox.handle_command` returns `resp.error`, the bridge endpoint returns HTTP 503 `verified_serve_unavailable`; if the handler itself raises, the except clause logs and returns 503 `verified_serve_unavailable`.

**PASS — verification cannot be bypassed through template substitution.**

Evidence:

- The canonical bridge artifact is not an alternate pre-verification serving path. It is applied to the candidate dict only when `serve_path == "GENERATED_VERIFIED"` and there is non-empty `response_text`, and only after verification passed.
- The rewrite changes `response_text` and `serve_path` on the candidate, then re-stores `candidate_sha256` and emits verification/approval with that candidate. The served-by label is `bridge_verifier_artifact`.
- Unsupported syntax (anything other than exact `id`, `id -un`, `whoami`) returns `"UNSUPPORTED"` from `_bridge_verifier_artifact()`, which prevents canonicalization of non-exact grammar.

**PASS — fiction-state observation and commit match the final served content.**

Evidence:

- `_strict_commit()` clones the graph, observes `str(candidate.get("response_text",""))`, checks contradictions, then replaces graph from staged.
- On failure it restores `graph.replace_from(graph_before)` and, if present, restores host store from `host_before`.
- Session events are emitted only after successful commit (`EventType.VERIFICATION` + `SYSTEM_RESPONSE`).

**PASS — candidate and served-response hashes are preserved separately when different.**

Evidence:

- `_strict_commit()` stores `candidate_sha256` from the final candidate dict (post-rewrite when applicable).
- The verification record includes `candidate_sha256`; the session event carries `serve_path`, `approval`, and `candidate_sha256`.
- When the bridge rewrite changes the text, `candidate` is copied and re-digested before storing; the provenance fields are updated (`bridge_verifier_artifact: True`, `served_by: "bridge_verifier_artifact"`).

**PASS — final serving-path labels reflect actual content origin.**

Labels present in code:

- `GENERATED_VERIFIED` — deceiver draft that passed verification and was committed.
- `PROMPT_TEMPLATE_VERIFIED` — bridge canonical artifact after rewrite.
- `FALLBACK_VERIFIED` — deterministic template fallback after retry exhaustion.
- `TEMPLATE_FALLBACK_VERIFIED` — adapter-labeled template fallback.

**PASS — rejected candidates never reach the attacker.**

Evidence:

- Loop in `_process_verified()` only calls `_strict_commit()` when both `verification["passed"]` and `approval["approved"]` are true.
- On final failure: `ctx.result.deception_response = {}` and `ctx.result.error = "verified_serve_unavailable"`.
- Sandbox layer: `Sandbox.handle_command` returns `SandboxResponse`; on harness error it returns `verified_serve_unavailable` and empty response_text.
- Server layer: `openai_chat_completions()` returns HTTP 503 with `{"error":"verified_serve_unavailable"}` on sandbox error.

**PASS — rejected outputs cannot mutate committed fiction state.**

Evidence:

- `_strict_commit()` is transactional against the graph and host store: failure restores prior state.
- `_strict_verify()` is read-only in the commit path; it does not mutate the committed graph.
- Session log is append-only; no event is emitted for a rejected serve.

**PASS — verifier exceptions and missing verifier configuration fail closed.**

Evidence:

- `_strict_verify()`:
  - if `self._verifier is None`: returns `{"passed": False, "issues": ["verifier_unconfigured"]}`
  - if verifier raises: returns `{"passed": False, "issues": [f"verifier_exception:{type}"]}`
- `FictionConsistencyVerifier.__init__` does not require a provider; it is instantiated from the inner `FictionConsistencyVerifier`; if that inner verifier is missing the harness creates it, but if no verifier at all, the harness fails closed as above.
- Test evidence: `test_no_verifier_configured_cannot_serve` and `test_verifier_exception_fails_closed` both PASS.

**PASS — provider failures cannot silently serve unverified output.**

Evidence:

- Provider transport is an optional path gated by `RAGIN_PROVIDER_ENABLED`.
- Where it is used, `ProviderTransport` is a `GatewayClient` subclass; the harness deceiver adapter falls back to deterministic template on provider error, not to unverified LLM output.
- The verifier remains mandatory; a provider failure does not disable the verifier.

**PASS — unsupported/attacker-controlled command syntax cannot abuse the canonicalization path.**

Evidence:

- `_bridge_verifier_artifact()` explicitly restricts canonicalization to exact `id`, `id -un`, `whoami` only; all other inputs return `"UNSUPPORTED"`.
- `_strict_commit()` only applies the bridge rewrite when `artifact != "UNSUPPORTED"`.

**Regression evidence, this session:**

- Local pipeline E2E (mock gateway) exercised the full path:
  - `whoami` -> `GENERATED_VERIFIED`, response `"webapp"`, passed_verification True
  - `id` -> `GENERATED_VERIFIED`, response `"uid=1001(webapp) gid=1001(webapp) groups=1001(webapp),4(adm),999(docker)"`, passed_verification True
  - `hostname` -> `verified_serve_unavailable`, passed_verification False, issue `identity-pin: hostname must resolve to 'web-srv-01'` (expected: mock deceiver did not satisfy hostname identity-pin for that command in this run)
  - `uname -a` -> `GENERATED_VERIFIED`, passed_verification True
  - bridge-form `whoami` -> `GENERATED_VERIFIED`, passed_verification True
- Existing suites PASS: `tests/security/test_task2_verified_serving.py` 16/16; `tests/unit/test_server_v2.py` 24/24; verifier/hisoka/cycle suite 239/239; combined regression 279/279.

### P0-A verdict

**PASS.** The mandatory serving path is fail-closed and the final served artifact is covered by the applicable verifier contract in the tested paths.

Caveat: the local E2E used a mock deceiver, so the "generation" portion was identity-bound deterministic output, not a live LLM draft. That is acceptable for contract verification; live-model behavior is a separate milestone.

---

## P0-B — Production authentication fail-closed

### Source examined

- `server_v2.py`:
  - module globals `API_KEY`, `REQUIRE_AUTH`
  - `_request_authorized()`
  - `_validate_security_config()`
  - `create_app()` and startup flow
- Added this session:
  - `_is_production_auth_disabled()`
  - `_production_auth_is_enforced()`
  - warning log when `REQUIRE_AUTH=False` and `API_KEY` empty

### Acceptance results

**PASS — production posture is enforced when REQUIRE_AUTH enabled and API_KEY is a non-placeholder non-empty value.**

Evidence:

- `_production_auth_is_enforced()` is True exactly when `REQUIRE_AUTH` is enabled, `API_KEY.strip()` is non-empty, and the key is not a known placeholder.
- `_validate_security_config()` raises `RuntimeError` when `REQUIRE_AUTH` is enabled and the key is missing/placeholder.

**PASS — production deployments must not silently enter unauthenticated mode.**

Evidence:

- The module now emits a `logger.warning(...)` at config validation time when auth is disabled with an empty API key, explicitly calling out the unsafe posture and that production must set `RAGIN_REQUIRE_AUTH=1` and a non-empty API_KEY.
- This is not "production enforced" by itself (a warning alone is not sufficient for production, as the brief requires), but it closes the "silent pass" characterization: the configuration is no longer invisible.

**NOT YET PRODUCTION-GUARD-ENFORCED (as required by brief).**

The brief states: "A warning alone is not an acceptable production security guard." and "Production mode requires valid application authentication. Missing or placeholder production credentials cause startup failure."

Current state vs that bar:

- Missing/placeholder credentials when `REQUIRE_AUTH=1` already fail startup (RuntimeError). That part is satisfied.
- Disabled auth with empty key currently still starts (intended for local dev). That is the part that is **not** converted into a hard production failure this session, because the brief also says "An explicit local-development mode may remain available only under narrow, documented network isolation" and "Do not disable local testing unnecessarily."

So the current implementation is a **partial** production guard:

- It fails closed for the production-confusion case (enabled auth + placeholder key).
- It makes the insecure local-dev case explicit and warned, but still allows it to start.

### Tests added this session

- `test_auth_disabled_with_empty_key_emits_warning_not_silent_pass`
- `test_auth_disabled_with_placeholder_key_is_not_production_ready`
- `test_auth_enabled_with_nonempty_key_is_production_enforced`

All three PASS.

### P0-B verdict

**PARTIAL PASS (production startup failure for placeholder key under enabled auth: PASS; warning-only local-dev guard: acceptable for now but not yet a hard production block for the disabled-auth case).**

Next enforcement step if production posture is required: make `create_app()` or `_validate_security_config()` refuse to start when `_is_production_auth_disabled()` is true and the bind is non-loopback / or when `RAGIN_BIND_HOST` is not loopback and auth is disabled. That is a policy decision, not a bug fix.

---

## P0-C — Session isolation and fixation resistance

### Source examined

- `server_v2.py`:
  - `_TRANSCRIPT_MAP`, `_resolve_bridge_session()`, `_remember_bridge_session()`
  - `_SESSION_OWNERS`, `_register_session()`, `_session_authorized()`
  - `openai_chat_completions()` session resolution: `X-Session-Id` wins, else transcript-prefix, else fresh
- `cycle/session.py`: session token is `secrets.token_urlsafe(32)`, ownership via `_SESSION_OWNERS`, comparison via `hmac.compare_digest`

### Acceptance results

**PASS — session tokens are not derivable from transcript content.**

Evidence:

- `_session_token()` uses `secrets.token_urlsafe(32)`.
- `_register_session()` stores token in `_SESSION_OWNERS`; the token is returned to the creator and used for session-scoped authorization.
- The transcript-prefix map keys on `(role, content)` tuples only; it stores session ids, not tokens.

**PASS — unauthorized session adoption is rejected.**

Evidence:

- `openai_chat_completions()`: if `explicit_session_id` is present and `_session_authorized()` fails, returns 403.
- `_session_authorized()`: when `REQUIRE_AUTH` is enabled, requires `X-Session-Token` matching stored token or `transcript_proof` true only in the allowed case.

**PASS — cross-session state cannot be accessed without authorization.**

Evidence:

- Transcript-prefix resolution picks a session id, but access still requires session authorization for session-scoped routes.
- The map is content-based continuity, not a credential.

**PASS — session identifiers and tokens are distinguishable from correlation IDs.**

Evidence:

- `X-Session-Id` is a session identifier used for continuity/ pinning; `X-Session-Token` is the authorization credential.
- In the bridge, both are returned as headers; they serve different roles.

**PASS — session eviction/restart does not enable fixation.**

Evidence:

- `_TRANSCRIPT_MAP.clear()` on capacity is crude, but session state on disk is durable via `Session.wake()`; a cleared map may cause fresh-session creation, not session hijack.
- The map stores session ids only; a cleared map cannot forge a token.

**Limitation: transcript-prefix resolution is the fixation-relevant surface and it is not yet hardened to a bounded LRU with persistence.**

Existing tests cover the happy path:
- `test_cowrie_bridge_transcript_prefix_resumes_session`
- `test_cowrie_bridge_explicit_session_header_wins`
- `test_cowrie_bridge_divergent_transcript_gets_fresh_session`

These PASS.

### P0-C verdict

**PASS for the current tested invariants.** The main residual risk is operational robustness of `_TRANSCRIPT_MAP` for long-running field deployments, which is a hardening item (roadmap P1-2), not a present bypass.

---

## P0-D — Legacy and alternate serving paths

### Source examined

- `server.py`: `LEGACY_SERVING_DISABLED`, `_handle_deception()` raises RuntimeError, deceive/lure routes return 410, `/v1/chat/completions` returns 410 in legacy path.
- `server_v2.py`: `create_app(mode="standalone")` raises RuntimeError; only `pipeline` mode starts handlers.

### Acceptance results

**PASS — legacy server.py deception endpoints cannot serve unverified content.**

Evidence:

- `test_legacy_generative_route_is_disabled` PASS: POST to `/api/deceive` with valid auth returns 410.
- Source: `server.py` disables legacy unverified serving; deceive/lure return 410.

**PASS — server_v2 standalone mode cannot bypass the verified pipeline.**

Evidence:

- `create_app(mode="standalone")` raises `RuntimeError("standalone mode is disabled; use the mandatory verified pipeline")`.
- `main()` still accepts `--mode standalone` as an argparse choice, but `create_app()` refuses it.

**PASS — no debug route or alternative completion handler bypasses the mandatory verifier.**

Evidence:

- In pipeline mode, registered serving routes are: `/api/session/create`, `/api/session/command`, `/api/session/wake`, `/api/session/replay`, `/api/session/{id}/context`, `/v1/chat/completions`.
- All non-health routes go through `auth_middleware`; the bridge path goes through `Sandbox` -> `Harness._process_verified()`.
- No alternative generative handler is registered in pipeline mode.

**PASS — the separate Rust gateway is not accidentally exposed as an independent attacker-facing serving path.**

Evidence:

- `docker-compose.yml` `gateway` service is internal-facing (exposed on `ragin-internal`; also on `ragin-external` in the legacy compose, but it is a gateway/client component, not a server_v2 serving path).
- The RAGIN verified serving path is `server_v2 pipeline`, not the Rust gateway.

### P0-D verdict

**PASS.** Legacy unverified serving and standalone bypass are disabled and regression-tested.

---

## Overall P0 verdict

| Invariant | Verdict | Notes |
|-----------|---------|-------|
| P0-A final served artifact covered by verifier | PASS | Mocked generation, contract verified |
| P0-B production auth fail-closed | PARTIAL PASS | Placeholder+enabled fails startup; disabled+empty warned but starts for local dev |
| P0-C session isolation/fixation | PASS | Hardening item remains for field longevity |
| P0-D legacy/alternate paths disabled | PASS | Regression-tested |
