# 09 — Technical Debt

**Method:** Source-grounded identification of dead code, duplication, design defects, and maintainability risks. Each item tagged with severity and evidence.

## 9.1 Dead code and disabled paths

### D1: Legacy server.py hisoka route (returns 410)

- **File:** ragin/server.py:207, 177
- **Severity:** LOW
- **Description:** The `/api/deceive` and `/api/lure` routes are registered but return 410. The `_handle_deception()` function still exists and is called by the 410 handler — dead code path. The `openai_chat_completions` and `lure` functions in server.py are also dead (return 410).
- **Impact:** Minor — the routes exist for backward compatibility but are effectively removed. The code still needs maintenance if someone re-enables legacy serving.

### D2: server_v2 standalone mode (raises RuntimeError)

- **File:** ragin/server_v2.py:357
- **Severity:** LOW
- **Description:** `create_app(mode="standalone")` raises RuntimeError. The `--mode standalone` argparse choice still exists and the `_init_component()` function still exists. Dead end.
- **Impact:** Minor — prevents accidental use of unverified standalone mode (intentional), but the code is maintained dead weight.

### D3: Legacy classify/analyze/deceive handlers in server_v2 pipeline mode (unused)

- **File:** ragin/server_v2.py:307-360 (classify, analyze, deceive handlers)
- **Severity:** LOW
- **Description:** These handlers are defined in server_v2.py but NOT registered in pipeline mode (create_app pipeline mode only registers /api/session/* and /v1/chat/completions). They are dead code in pipeline mode. They exist for backward compatibility with server.py but are unreachable.
- **Impact:** Low — dead code that could confuse maintainers. The analyze handler imports DonAdapter inline, creating a dependency that's never used in pipeline mode.

### D4: LEGACY_SERVING_DISABLED constant in server.py

- **File:** ragin/server.py:51
- **Severity:** LOW
- **Description:** Global constant that gates the entire deception path. Now permanently True. The `_handle_deception()` function (server.py:87-140) is the legacy path — never called.
- **Impact:** Low — the function is dead but still exists. The response_cache, _lure_rate_limiter, and scanner detection in server.py are also dead.

### D5: Stale `ragLegendre/` directory

- **File:** /home/elaref/Documents/research/ragin/ragLegendre/ (or similar)
- **Severity:** LOW
- **Description:** A narrow directory at the workspace root that appears to be from a prior agent. Not part of the git repo. Likely stale.
- **Impact:** Low — just clutter.

### D6: Temporary scripts in scripts/_tmp_* and run/strace_*

- **Files:** scripts/_tmp_*.sh, scripts/_tmp_*.py, scripts/_tmp_*.err, scripts/_tmp_*.out, run/strace_server.*, run/setsid_test.out, run/mock.out
- **Severity:** LOW
- **Description:** Temporary artifacts from recent debugging runs. Not part of the repo.
- **Impact:** Low — clutter. Should be cleaned up or .gitignored.

### D7: harness.py.bak20261010 backup

- **File:** ragin/cycle/harness.py.bak20261010
- **Severity:** LOW
- **Description:** Backup of pre-modification harness. Useful as reference but should not persist indefinitely.
- **Impact:** Low — could be confused with active code.

### D8: Unused imports and modules

- **File:** ragin/cycle/coordination.py (imported optionally in multiple places with try/except)
- **Severity:** MEDIUM
- **Description:** The coordination module (Supervisor, ExpertPool, VotingSystem, DeceptionReviewer, etc.) is imported optionally in cycle/__init__.py, harness.py (HAS_COORDINATION flag), and harness.py process_with_supervisor/process_with_threat_modeling. If the module is not installed, all coordination features are silently disabled. There are NO tests for the coordination path.
- **Impact:** Medium — a significant chunk of functionality (supervisor routing, expert dispatch, voting, enhanced review, attack chain building, MTTA tracking) is optionally available with no test coverage and no clear indication to the user whether it's active.

## 9.2 Duplication

### D9: Duplicate identity definitions

- **Files:** ragin/hisoka/deception.py:44-91 (_IDENTITIES), ragin/graph/fiction.py (identity derivation from identity_for()), ragin/graph/host_fiction.py (host identity pinning)
- **Severity:** MEDIUM
- **Description:** The 5 persona identities are defined once in deception.py but the pinned identity is used in 3 places: (1) deception.py persona system prompt, (2) fiction.py session graph seed, (3) host_fiction.py host identity pin. If an identity changes, 3 files must be updated. The HostFictionStore adds a 4th identity concept (host-level pin) that can override the per-skill identity.
- **Impact:** Medium — identity drift risk. The authorization policy (deception.py:93-107) is a separate single-source-of-truth for privilege fiction, which is good, but the base identity is not similarly centralized.

### D10: Duplicate verifier logic — FictionConsistencyVerifier + HostFictionVerifier + supported_claims

- **Files:** ragin/cycle/verifier.py, ragin/graph/host_fiction.py (HostFictionVerifier), ragin/cycle/supported_claims.py
- **Severity:** MEDIUM
- **Description:** Three verification layers that compose but have overlapping concerns. The identity-pin check is in FictionConsistencyVerifier._check_identity_pin() and the supported_claim handler for whoami/id also checks the identity. The fiction contradiction check is in FictionConsistencyVerifier._check_fiction_contradictions() and HostFictionVerifier checks cross-session contradictions. The layering is correct but the boundaries could be clearer.
- **Impact:** Medium — understanding the full verification chain requires reading 3 files. The bridge_verifier_artifact in harness.py adds a 4th layer (canonical template for supported commands on the bridge path).

### D11: Duplicate gateway client patterns

- **Files:** ragin/gateway/client.py (GatewayClient), ragin/hisoka/deception.py (ResponseGenerator uses GatewayClient), ragin/don/rag_engine.py (ThreatRAGEngine uses GatewayClient), ragin/cycle/provider_transport.py (ProviderTransport extends GatewayClient)
- **Severity:** LOW
- **Description:** GatewayClient is the shared HTTP client. All callers use it correctly. ProviderTransport is a clean subclass. No duplication — this is good design. Documenting it as a strength.

## 9.3 Design defects

### D12: server_v2 has no rate limiting

- **File:** ragin/server_v2.py (no rate_limit_middleware)
- **Severity:** MEDIUM
- **Description:** server.py has rate_limit_middleware (60 req/min) and lure_rate_limiter (12 req/min). server_v2 has NO rate limiting. If server_v2 is exposed without NGINX, it's vulnerable to request flooding.
- **Impact:** Medium — depends on deployment. For honeypot use, attackers are self-rate-limited. For API use, this is a real gap.

### D13: _TRANSCRIPT_MAP is a crude in-memory session resolution

- **File:** ragin/server_v2.py:35-42
- **Severity:** MEDIUM
- **Description:** Session continuity for the Cowrie bridge is resolved by content-prefix matching in an in-memory dict. This works but is fragile: (1) the dict can grow to 20K entries, (2) clearing is crude (full clear), (3) the key is the full message tuple which could be large, (4) there's no persistence — a server restart loses all session continuity.
- **Impact:** Medium — for long-running field deployments, this could cause memory pressure and session continuity loss on restart. The X-Session-Id header (set by previous responses) is the proper session pinning mechanism, but the bridge path falls back to transcript-prefix when no header is present.

### D14: Async/sync boundary in server_v2 handlers

- **File:** ragin/server_v2.py (all handlers are async, but they call `asyncio.to_thread()` for blocking work)
- **Severity:** LOW
- **Description:** The handlers correctly use asyncio.to_thread() for CPU-bound work (Harness.process, Sandbox.handle_command). However, some paths (field export in _export_field_session) are sync file I/O inside an async handler. This is acceptable for low-volume field export but could block the event loop under high load.
- **Impact:** Low — field export is best-effort and exceptions are caught. The blocking window is small (append to JSONL).

### D15: Module-level globals in server_v2.py

- **File:** ragin/server_v2.py:19-34 (API_KEY, REQUIRE_AUTH, _harness, _sandbox, _component, _SESSION_OWNERS, _TRANSCRIPT_MAP)
- **Severity:** MEDIUM
- **Description:** server_v2.py uses module-level globals for shared state. This is a common pattern for aiohttp apps but makes testing fragile — the test fixtures must save and restore globals (see test_server_v2.py fixture which saves orig_harness, orig_sandbox, orig_component, orig_comp_name, orig_api_key, orig_require_auth). The _SESSION_OWNERS dict and _TRANSCRIPT_MAP are particularly problematic — they persist across test runs if not cleaned.
- **Impact:** Medium — test isolation requires careful global management. In production, this is acceptable for a single-process server.

### D16: Hardcoded prompt templates in deception.py

- **File:** ragin/hisoka/deception.py:15-41 (_SYSTEM_PROMPT_PREAMBLE), 109-126 (_IDENTITY_BLOCK_TEMPLATE), 154-167 (_ROLE_PROMPTS)
- **Severity:** LOW
- **Description:** The system prompt, identity block, and role prompts are hardcoded as Python string constants. They're extensive (the preamble alone is 26 lines) and embedded in the source. If prompt tuning is needed, it requires code changes.
- **Impact:** Low — the prompts are carefully engineered and tested. Externalizing them to templates would add flexibility but also complexity. The settings.yaml references template dirs (ragin/prompt/templates) that may not exist.

### D17: settings.yaml references non-existent template paths

- **File:** ragin/config/settings.yaml:28-53 (PROMPT_ENGINEERING.template_dir = "ragin/prompt/templates")
- **Severity:** LOW
- **Description:** The settings.yaml references template directories (ragin/prompt/templates, ragin/prompt/few_shots) that likely don't exist in the repo. The actual prompts are hardcoded in deception.py.
- **Impact:** Low — the settings.yaml is for the LLM gateway config, not the hisoka prompts. The template_dir setting may be for a different component or future use.

## 9.4 Configuration drift

### D18: .env.example vs .env.field.example vs settings.yaml — three config layers

- **Files:** .env.example, .env.field.example, settings.yaml, docker-compose.yml
- **Severity:** MEDIUM
- **Description:** Configuration is spread across 4 files with overlapping concerns:
  - .env.example: API_KEY, RAGIN_LLM_BASE_URL, RAGIN_LLM_API_KEY, RAGIN_LLM_MODEL, service ports, budget, Jev config
  - .env.field.example: field-specific (RAGIN_FIELD_ARM, RAGIN_FIELD_SSH_BANNER, RAGIN_LLM_BASE_URL=replace-with-approved-private-bridge, RAGIN_IMAGE)
  - settings.yaml: cloud LLM migration config (OpenRouter, model router, prompt engineering, response validation, cost tracking, observability, security, local fallback)
  - docker-compose.yml: service definitions, env var injection, network config
- **Impact:** Medium — it's unclear which file takes precedence for which setting. The settings.yaml has OPENROUTER_API_KEY: "${OPENROUTER_API_KEY}" which looks like envsubst syntax, but the file is read by `_load_config()` in server_v2.py as raw YAML (yaml.safe_load), which would NOT expand the `${...}` placeholder. This could be a latent bug — the config says to use the env var but the YAML loader doesn't expand it.

### D19: RAGIN_LLM_BASE_URL default in .env.example is loopback

- **File:** .env.example:11 (RAGIN_LLM_BASE_URL=http://127.0.0.1:8731/v1)
- **Severity:** MEDIUM
- **Description:** The default LLM base URL is the local OpenCode bridge at loopback. This works for local development but would NOT work in a Docker container (127.0.0.1 inside the container is the container itself, not the host). The field env template correctly uses replace-with-approved-private-bridge.
- **Impact:** Medium — developers running Docker Compose with the default .env.example values would get gateway connection errors. The docker-compose.yml services set RAGIN_LLM_BASE_URL from the env (which must be provided).

## 9.5 Missing safeguards

### D20: No secret scanning in CI (gitleaks config exists but not confirmed running)

- **File:** .gitleaks.toml (exists, 2.2KB)
- **Severity:** LOW
- **Description:** A gitleaks config exists but it's unclear if it's run in CI. The .github/workflows/ci.yml was modified this session — need to check if gitleaks is in the workflow.
- **Impact:** Low — the repo has no committed secrets (API keys are placeholder templates). But a gitleaks scan in CI would catch accidental commits.

### D21: No pre-commit hook for secrets or linting (config exists but not confirmed installed)

- **File:** .pre-commit-config.yaml (exists, 369 bytes)
- **Severity:** LOW
- **Description:** A pre-commit config exists but may not be installed. The .venv has ruff and mypy. The Makefile has lint and typecheck targets.
- **Impact:** Low — linting is available but not enforced at commit time unless pre-commit is installed.

### D22: bandit report exists but not in CI

- **File:** bandit-report.json (exists, 63KB, untracked)
- **Severity:** LOW
- **Description:** A bandit security scan was run and saved. The Makefile has a security-scan target that runs scripts/security_scan.sh. Not confirmed in CI.
- **Impact:** Low — security scanning is available but not automated.

## 9.6 Observability gaps

### D23: server_v2 metrics endpoint is a placeholder

- **File:** ragin/server_v2.py:363-365 (metrics handler returns {"status": "metrics placeholder"})
- **Severity:** LOW
- **Description:** The /metrics endpoint in server_v2 returns a placeholder. server.py has a real Prometheus metrics endpoint (using prometheus_client). server_v2's metrics are not implemented.
- **Impact:** Low — monitoring is available via server.py's services in Docker Compose. server_v2 is not a Docker Compose service, so its metrics gap doesn't affect the deployed stack.

### D24: No structured logging configuration for server_v2

- **File:** ragin/server_v2.py:347-349 (logging.basicConfig with basic format)
- **Severity:** LOW
- **Description:** server_v2 uses basic logging configuration. server.py uses the same. No JSON logging, no structured fields. The settings.yaml OBSERVABILITY section (json format, jaeger tracing) is for the LLM gateway, not the RAGIN servers.
- **Impact:** Low — acceptable for a honeypot service. Structured logging would help with field data collection but the current approach works.

## 9.7 Maintainability risks

### D25: deception.py is very large (3195 lines)

- **File:** ragin/hisoka/deception.py (3195 lines)
- **Severity:** MEDIUM
- **Description:** The file contains: system prompt preamble, 5 identity definitions, authorization policy, 10+ identity helper functions, cloud identity overrides, 5 role prompts, persona configs, 4 fake config templates, 14 injection patterns, 6 transcript structure patterns, transcript styling helpers (5 functions), 20+ refusal signal patterns, 15+ maskable secret patterns, 10+ secret signal patterns, danger signal patterns, prose tell patterns (5 complex patterns), quote normalization, danger signal checking, secret scrubbing (partial). This is a lot of logic in one file.
- **Impact:** Medium — the file is carefully engineered and extensively tested, but it's a maintainability risk. The regex patterns alone (100+ patterns across multiple tuples) are hard to review and extend. Splitting into deception_core.py, danger_patterns.py, secret_patterns.py, prompt_templates.py would improve maintainability.

### D26: Extensive regex pattern tuples with no documentation of what each pattern catches

- **File:** ragin/hisoka/deception.py:639-758 (_INJECTION_PATTERNS, _REFUSAL_SIGNAL_PATTERNS, _MASKABLE_SECRET_PATTERNS, _SECRET_SIGNAL_PATTERNS, _DANGER_SIGNAL_PATTERNS, _PROSE_TELL_PATTERNS)
- **Severity:** MEDIUM
- **Description:** The pattern tuples are extensive but each pattern is a raw regex with no docstring explaining what attack it catches, what family it belongs to, or what live red-team finding motivated it. The patterns have inline comments referencing live red-team findings (V3, V5, V6, V7, V8, V9, V10, V12, V13, V14, V15, V16, V17, V18, V19, V21, V22), but the mapping from pattern to finding is implicit.
- **Impact:** Medium — a security reviewer trying to understand what attacks are caught (and what's not) would need to trace each pattern. The patterns are well-motivated (each has a finding reference) but the catalog is not searchable or categorized.

### D27: No typed config validation

- **File:** ragin/config/settings.yaml, .env.example
- **Severity:** LOW
- **Description:** Configuration is read from YAML and environment variables with no schema validation. A typo in a config key silently becomes a missing setting. The settings.yaml has a complex nested structure (MODEL_ROUTER, PROMPT_ENGINEERING, RESPONSE_VALIDATION, COST_TRACKING, OBSERVABILITY, SECURITY, LOCAL_FALLBACK) that's read by `_load_config()` but not validated against a schema.
- **Impact:** Low — the config is mostly used for LLM gateway settings, not the core serving path. The critical settings (API_KEY, RAGIN_REQUIRE_AUTH, RAGIN_MTLS_*) are read directly from env with validation in server_v2.py.

## 9.8 Summary of debt by severity

| Severity | Count | Items |
|----------|-------|-------|
| HIGH | 1 | D13: _TRANSCRIPT_MAP crude session resolution (field-deploy risk) |
| MEDIUM | 8 | D9 (duplicate identities), D10 (duplicate verifier layers), D12 (no rate limiting in sv2), D13 (transcript map), D15 (module globals), D18 (config drift), D19 (loopback default), D25 (large deception.py), D26 (undocumented patterns) |
| LOW | 14 | D1, D2, D3, D4, D5, D6, D7, D11, D14, D16, D17, D20, D21, D22, D23, D24, D27 |
| GOOD (strength) | 2 | D11 (clean GatewayClient hierarchy), (settings.yaml OBSERVABILITY for gateway) |
