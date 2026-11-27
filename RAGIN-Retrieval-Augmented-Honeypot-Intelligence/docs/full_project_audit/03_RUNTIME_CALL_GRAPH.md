# 03 — Runtime Call Graph

**Scope:** Authoritative request flow from external ingress to attacker-visible response, with serve-path labeling.

## 3.1 Ingress paths

### Path A: Cowrie SSH → server_v2 bridge (field arm C, PRIMARY serving path)

1. Attacker opens SSH to Cowrie container (`COWRIE_PORT`, default 2223)
2. Cowrie terminates SSH, logs TTY/JSON events to `cowrie-data/` volume
3. Cowrie's LLM backend POSTs to `server_v2 /v1/chat/completions` with OpenAI-format `messages` array
4. `openai_chat_completions()` in server_v2.py:
   - Extracts last user message as `command` (or parses "The command to execute is:" from system prompt for EXEC path — live-smoke fix 2026-09-28)
   - Resolves session: `X-Session-Id` header wins; else `_resolve_bridge_session()` by transcript prefix; else fresh `cowrie-{timestamp}-{token}`
   - Calls `_sandbox.handle_command(source_ip, command, session_id)`
5. Sandbox routes to `Harness._process_verified(session, command)`
6. If `resp.error` is set → HTTP 503 `{"error": "verified_serve_unavailable"}` (FAIL SAFE — never unverified content)
7. If success → HTTP 200 OpenAI-format response with `X-Session-Id` and `X-Session-Token` headers
8. Field export: append to `RAGIN_FIELD_EXPORT_DIR/{session_id}.jsonl` (best-effort)

**Key property:** The bridge is the ONLY path by which SSH attackers receive content. Every byte served to an SSH client passes through `_strict_commit()` which verifies before committing.

### Path B: Direct HTTP API (server_v2 pipeline mode)

- `/api/session/create` → `Sandbox.create_session()` → returns session_id + token
- `/api/session/command` → `Sandbox.handle_command()` → returns verified response or 503
- `/api/session/wake` → `Harness.wake()` → resume crashed session
- `/api/session/{id}/context` → `Sandbox.get_session_context()`
- `/api/session/replay` → `Session.replay_since()`

All require `X-API-Key` (or `Authorization: Bearer`) match, plus `X-Session-Token` for session-scoped routes.

### Path C: Legacy server.py (DEPRECATED)

- `/api/classify` (chrollo), `/api/analyze` (don), `/api/assess` (jev) — functional
- `/api/deceive` (hisoka) → returns 410 "legacy unverified serving disabled"
- `/api/lure` → returns 410
- `/v1/chat/completions` → returns 410

**Verified fact:** `server.py:LEGACY_SERVING_DISABLED = True` at line ~51, and `_handle_deception()` raises `RuntimeError("legacy unverified serving disabled")` before any generation. The hisoka deceive and lure routes are hardcoded to 410.

### Path D: Standalone server_v2 (DISABLED)

- `create_app(mode="standalone")` → `raise RuntimeError("standalone mode is disabled; use the mandatory verified pipeline")`

## 3.2 Serve-path labels

The harness tracks where each served response came from:

| Serve path | Source | Verifier | When used |
|------------|--------|----------|-----------|
| `GENERATED_VERIFIED` | LLM draft that passed verification | FictionConsistencyVerifier + HostFictionVerifier | Normal case: deceiver generates, passes, approves, commits |
| `PROMPT_TEMPLATE_VERIFIED` | Bridge verifier artifact (canonical whoami/id/-un template) | Factored into bridge_verifier_artifact | SSH wire proof for supported commands on bridge path |
| `FALLBACK_VERIFIED` | Deterministic template fallback | FictionConsistencyVerifier (must pass) | After retry exhaustion or candidate rejection |
| `TEMPLATE_FALLBACK_VERIFIED` | HisokaAdapter-labeled template fallback | (propagated from adapter) | When gateway_fallback/unsafe_retry_fallback/template_anchored marked |

**Key detail (harness.py `_strict_commit`):** When the bridge path serves a `GENERATED_VERIFIED` candidate for a supported command (exact `id`, `id -un`, or `whoami`), the harness REWRITES `response_text` to the canonical prompt-template artifact from `_bridge_verifier_artifact()` and reclassifies to `PROMPT_TEMPLATE_VERIFIED`. This ensures the SSH wire never receives a potentially-empty or rejected LLM draft for these commands.

## 3.3 Verification chain (inner to outer)

```
HisokaAdapter.generate_response()
  → AdaptiveDeceiver.generate_response()
    → (deterministic fast-paths: sudo, IMDS, SSH, sudo -l, credential bait, FS replay)
    → (optional LLM draft via ResponseGenerator._gateway → GatewayClient.generate())
    → DeceptionResponse
  → dict (with serve_path label)
  → Harness._strict_candidate()
    → candidate dict
  → Harness._strict_verify()
    → FictionConsistencyVerifier.verify()
      → _check_degenerate
      → _check_danger_signals (refusal/self-reference/secret patterns, 100+ regex patterns)
      → _check_identity_pin (whoami/id/hostname against pinned identity, answer-line aware)
      → _check_fiction_contradictions (FictionGraph.observe)
      → (if RAGIN_FAIL_CLOSED) check_supported_claim (whoami/id/uname/hostname/echo/uptime/date/os-release)
    → HostFictionVerifier.verify() (if passed session checks AND host store installed)
      → probe FictionGraph.observe → store.check_against_host (cross-session)
    → {passed, issues, confidence, deterministic, serve_path}
  → Harness._strict_approval()
    → ApprovalGateway.resolve() (risk_from_state → DefaultRiskBasedPolicy → AUTO/NOTIFY/REQUIRE)
    → ClaimedApprover / ConsoleApprover / null
    → {approved, level, reason}
  → Harness._strict_commit()
    → staged = graph.clone(); observed = staged.observe(text)
    → if contradictions: return False (rollback)
    → bridge_verifier_artifact rewrite (bridge path, supported commands)
    → host_store.mark_verified + promote_verified + save
    → emit VERIFICATION + SYSTEM_RESPONSE
    → return True
```

## 3.4 Fallback chain

When no candidate passes verification after max_retries+1 attempts:

1. `ResponseGenerator()._generate_template(skill, attacker_input, feedback, identity)` — deterministic template
2. Wrap as `fallback_candidate = {response_text, serve_path: FALLBACK_VERIFIED, fallback_served: True}`
3. Verify the fallback (must pass FictionConsistencyVerifier)
4. If passes → approval → commit (serve_path: FALLBACK_VERIFIED)
5. If fallback also rejected → `error = "verified_serve_unavailable"`, empty response_text

The fallback template is identity-bound (uses the pinned identity's prompt/user/host), so it passes identity-pin checks by construction.

## 3.5 Session lifecycle

```
Session.create() → emit SESSION_START → session_id = ses-{uuid4.hex[:16]}
  → Sandbox._sessions[session_id] = session
  → HTTP response: {session_id, status, session_token}

Session.handle_command() → _command_count += 1
  → if _command_count > max_commands (default 1000): session.close("max_commands_reached")
  → Harness.process(session, command)
  → emit METRIC

Session.close(reason) → emit SESSION_END → write {session_id}.meta.json
  → is_closed = True

Session.wake(session_id) → emit SESSION_RESUME → replay existing events
  → Used by /api/session/wake and Sandbox when session not in memory
```

**Durability:** Events are written with `f.flush()` + `os.fsync(f.fileno())` after each append. Session logs live in `data/sessions/{session_id}.jsonl` (default `RAGIN_SESSION_DIR`).

## 3.6 Auth chain

```
server_v2 middlewares (order matters):
  1. mtls_middleware (if RAGIN_MTLS_REQUIRED=1)
     → peer_certificate_authorized(peercert, RAGIN_MTLS_ALLOWED_IDENTITIES)
     → 403 if no matching identity
  2. auth_middleware
     → /health, /ready → bypass
     → _request_authorized(request):
       → if not REQUIRE_AUTH and not API_KEY: True
       → if API_KEY in _PLACEHOLDER_KEYS: False
       → X-API-Key == API_KEY: True
       → Authorization: Bearer <key> == API_KEY: True
       → else: False → 401
  3. timing_middleware (X-Response-Time header)

Session-scoped routes additionally check:
  _session_authorized(request, session_id):
    → if not REQUIRE_AUTH: True
    → X-Session-Token == _SESSION_OWNERS[session_id] (hmac.compare_digest): True
    → else: False → 403
```

**Critical config:** If `RAGIN_REQUIRE_AUTH=false` OR `API_KEY` is empty, auth is disabled. If `API_KEY` is set to a placeholder (`changeme`, `change_me`, `placeholder`, `change_me_backend_key`, `""`), `_validate_security_config()` raises `RuntimeError` at app creation (server_v2.py line ~107).
