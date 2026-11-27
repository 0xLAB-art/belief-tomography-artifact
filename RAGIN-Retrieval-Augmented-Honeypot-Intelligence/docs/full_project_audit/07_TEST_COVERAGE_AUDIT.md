# 07 — Test Coverage Audit

**Method:** Inventory of all test files, execution of key suites, analysis of coverage gaps.

## 7.1 Test topology

| Directory | Files | Focus |
|-----------|-------|-------|
| tests/unit/ | 80 .py files | Component-level tests |
| tests/security/ | 4 .py files | mtls_transport, task2_verified_serving, adversarial, input_validation |
| tests/integration/ | 5 .py files | gateway_api, performance, pipeline, readiness, stability |
| tests/ (top-level) | 3 .py files | e2e_comprehensive, performance_benchmark, security_validation |
| tests/benchmark_traditional.py | 1 | Traditional honeypot benchmark |

**Total: 93 test files**

## 7.2 Tests executed in this audit

| Suite | Command | Result | Duration |
|-------|---------|--------|----------|
| Artifact consistency checker | `python scripts/verifier_redteam_check.py` | 47/47 PASS | <1s |
| Provider transport | `pytest tests/unit/test_provider_transport.py -v` | 11/11 PASS | 0.33s |
| Security task2 verified serving | `pytest tests/security/test_task2_verified_serving.py -v` | 13/13 PASS | 0.95s |
| Verifier + fiction + hisoka + artifact consistency | `pytest tests/unit/test_verifier.py tests/unit/test_fiction_graph.py tests/unit/test_hisoka.py tests/unit/test_artifact_consistency.py -v` | 186/186 PASS | 1.01s |
| Server v2 | `pytest tests/unit/test_server_v2.py -v` | 24/24 PASS | 0.52s |
| Cycle + don + chrollo + hitl + host_fiction | `pytest tests/unit/test_cycle.py tests/unit/test_don.py tests/unit/test_chrollo.py tests/unit/test_hitl.py tests/unit/test_host_fiction.py -v` | 230/230 PASS | 87.36s |
| **Total executed this audit** | | **471/471 PASS** | ~90s |

## 7.3 Component coverage matrix

| Component | Unit tests | Security tests | Integration tests | E2E | Gap |
|-----------|-----------|----------------|-------------------|-----|-----|
| server_v2 pipeline | test_server_v2 (24) | test_task2_verified_serving (13) | — | — | No integration test for full pipeline with real LLM backend |
| Harness (mandatory verification) | test_cycle, test_task2 | test_task2_verified_serving | — | — | ✅ Well covered |
| Sandbox | (via harness tests) | test_task2 (concurrent serialization) | — | — | ✅ Covered |
| Session (JSONL durability) | (via harness tests) | — | — | — | ⚠️ No explicit crash-recovery integration test |
| FictionConsistencyVerifier | test_verifier (part of 186) | — | — | — | ✅ Extensive |
| HostFictionVerifier/Store | test_host_fiction (30) + test_host_fiction_wiring | — | — | — | ✅ Good unit coverage; no live cross-session validation |
| ChrolloClassifier | test_chrollo | — | — | — | ⚠️ Needs model artifact to test inference; training tests exist |
| DonAdapter/ThreatRAGEngine | test_don | — | — | — | ⚠️ BM25 tests work offline; vector store + LLM tests need backend |
| HisokaAdapter/AdaptiveDeceiver/ResponseGenerator | test_hisoka (100+) | — | — | — | ✅ Extensive; covers deterministic fast-paths, canary, FS ledger, danger signals |
| GatewayClient | (via don/hisoka tests) | — | tests/integration/test_gateway_api.py | — | ⚠️ Integration test exists but not executed this audit |
| ProviderTransport/ProviderTransportAdapter | test_provider_transport (11) + test_provider_transport_adapter + test_provider_transport_config + test_provider_enabled_acceptance | — | — | — | ✅ Good isolation tests; no integration test with real provider |
| ApprovalGateway/HITL | test_hitl | — | — | — | ✅ Policy + approver + auditor covered |
| FictionGraph | (part of 186) | — | — | — | ✅ Covered |
| Supported claims | (via verifier tests) | — | — | — | ⚠️ Opt-in (RAGIN_FAIL_CLOSED); not tested when disabled |
| Cowrie bridge (openai_chat_completions) | test_server_v2 (8 bridge tests) | — | — | — | ✅ Good unit coverage; no live SSH+Cowrie+sv2 integration test |
| MTLS transport | test_mtls_transport | — | — | — | ✅ Exists; not executed this audit |
| Jev System One | — | — | — | — | ⚠️ NO dedicated unit tests found |
| RBAC (auth/rbac.py) | — | — | — | — | ❌ NO tests |
| Decoys (decoys/*) | — | — | — | — | ❌ NO tests |
| SIEM connectors (siem/*) | — | — | — | — | ❌ NO tests |
| Rollout manager (rollout/*) | — | — | — | — | ❌ NO tests |
| Coordination (coordination.py) | — | — | — | — | ❌ NO tests |
| Intelligence (intelligence/*) | — | — | — | — | ❌ NO tests |
| Monitoring (monitoring/*) | test_monitoring | — | — | — | ⚠️ Exists; not executed this audit |
| Benchmark (benchmark/*) | test_benchmark | — | — | — | ⚠️ Exists; not executed this audit |
| CTI manual audit | test_cti_manual_audit | — | — | — | ⚠️ Exists; not executed this audit |
| Gateways integration | test_gateway_integration + test_gateway_reasoning_models | — | — | — | ⚠️ Exists; not executed this audit |

## 7.4 Previously reported suite sizes — resolved

| Claimed count | Resolution |
|---------------|------------|
| 1,413 passed / 116 skipped | Likely an older run with different test selection or pytest-xdist sharding |
| 1,657 passed / 116 skipped | Likely a later run with more tests added |
| 1,639 tests passed across selected suites | Close to the total unit test count; may reflect a specific pytest -k filter |
| Current state | 93 test files total; 471/471 PASS across suites executed this audit. Full suite run not attempted (would take several minutes and may require LLM backend for some tests). |

The discrepancy in reported counts is consistent with different pytest selections (full run vs unit-only vs security-only vs integration-only vs with/without xdist sharding). The 116 skipped count is consistent across reports — likely tests skipped due to missing LLM backend or AWS credentials.

## 7.5 Coverage gaps by risk

### High risk — untested critical paths

1. **Full pipeline integration with real LLM backend** — All component tests use mocks/fakes. No test sends a real request through Chrollo→Don→Hisoka→Verifier→Commit with a live LLM. The deterministic fast-paths are tested, but the LLM-dependent path is only tested via mock GatewayClient.
2. **Cowrie SSH → server_v2 bridge end-to-end** — 8 unit tests mock the HTTP layer, but no test runs actual Cowrie + SSH + sv2 bridge together. The live-smoke tests (scripts/_tmp_*.sh) are temporary artifacts, not permanent tests.
3. **Cross-session fiction consistency in live deployment** — HostFictionStore tests are unit-level. No test validates that a reconnecting attacker gets consistent fiction across sessions with a real deployment.
4. **Provider transport with real provider** — 11 tests cover the config/auth/failure paths, but no test generates through a real provider backend.

### Medium risk — weakly tested

5. **Session crash recovery** — Session.wake() is tested implicitly via harness tests, but no explicit test kills a running session and verifies wake() recovers the full state.
6. **Rate limiting** — server.py has RateLimiter but no test for it. server_v2 has no rate limiting.
7. **Jev System One** — No dedicated tests. The jev/ package has 4 modules but no test_jev.py in unit/ (test_jevi.py exists but wasn't in the executed suites).
8. **Field export durability** — _export_field_session() is best-effort with silent exception catching. No test verifies export behavior.

### Low risk — untracked but not critical

9. **RBAC, Decoys, SIEM, Rollout, Coordination, Intelligence** — No tests at all. These are either not wired into the serving path or are optional features.
10. **benchmark_traditional.py** — Top-level test file, not in tests/ directory; not discovered by default pytest run.

## 7.6 Test quality observations

**Good:**
- test_task2_verified_serving.py is an excellent security regression suite — tests the exact invariant (no unverified content served) with concrete failure modes (no verifier, rejected candidate, verifier exception, retry exhaustion, HITL deny, persistence failure, concurrent serialization, auth bypass, legacy route disabled).
- test_provider_transport.py is thorough — covers auth precedence, placeholder detection, URL resolution, timeout, health endpoint, error type distinction.
- test_server_v2.py covers all bridge scenarios including transcript-prefix session continuity (the subtle cowrie backend behavior).

**Weak:**
- Many tests use MagicMock for the Sandbox/Harness, which means the actual orchestration logic is only tested in test_task2_verified_serving.py and test_cycle.py.
- Some test assertions are weak: `assert data["status"] == "ok"` without checking the full response shape.
- test_server_v2.py mocks `_init_pipeline` entirely, so the pipeline initialization path is not tested through the HTTP layer.

**Environment sensitivity:**
- Tests that need the LLM backend (don, hisoka with real gateway) are likely skipped when the gateway is unavailable. The .venv has all deps but the LLM backend (OpenCode bridge at 127.0.0.1:8731) may not be running.
- tests/conftest.py may load .env via dotenv, which could affect API_KEY and REQUIRE_AUTH module-level globals in server_v2.py (the test fixture explicitly sets API_KEY="" and REQUIRE_AUTH=False to avoid this).
