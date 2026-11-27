# 04 — Component Status Matrix

**Legend:** IMPLEMENTED / INTEGRATED / TESTED / DEPLOYED / EXPERIMENTALLY_VALIDATED — each stage is independently assessed.

## 4.1 Core pipeline components

| Component | File | IMPLEMENTED | INTEGRATED | TESTED | DEPLOYED | EXPERIMENTALLY VALIDATED | Notes |
|-----------|------|-------------|------------|--------|----------|--------------------------|-------|
| server_v2 (pipeline) | ragin/server_v2.py | ✅ | ✅ | ✅ 13/13 security + 24/24 unit | ✅ Docker (docker-compose.yml: not a dedicated service — runs as part of field arm) | ✅ SSH wire proof | Default mode; standalone disabled at runtime |
| server (legacy) | ragin/server.py | ✅ | ⚠️ partial | ❌ legacy untested | ✅ Docker (chrollo/don/hisoka/jev services) | ⚠️ hisoka route disabled | LEGACY — hisoka deceive/lure return 410; only chrollo/don/jev standalone work |
| Harness | ragin/cycle/harness.py | ✅ | ✅ | ✅ 230+13 PASS | ✅ | ✅ Ablation (no-verify, no-fiction, no-bait, no-graph, no-approval) | Stateless orchestration; _process_verified is the mandatory path |
| Sandbox | ragin/cycle/sandbox.py | ✅ | ✅ | ✅ concurrent serialization test | ✅ | ✅ | Thread-safe (RLock); command limits; session watch |
| Session | ragin/cycle/session.py | ✅ | ✅ | ✅ (via harness tests) | ✅ | ✅ 6932 session files on disk | Append-only JSONL with fsync; crash-safe wake |
| FictionConsistencyVerifier | ragin/cycle/verifier.py | ✅ | ✅ | ✅ 186 PASS (incl. verifier tests) | ✅ | ✅ Redteam: P=1.000 offline, P=0.995 live, R=0.943 live | 4 check layers + optional fail-closed supported claims |
| HostFictionVerifier | ragin/graph/host_fiction.py | ✅ | ✅ | ✅ 30 PASS (test_host_fiction) | ✅ | ⚠️ Not yet validated in live field deploys | Cross-session consistency; per_session policy default |
| HostFictionStore | ragin/graph/host_fiction.py | ✅ | ✅ | ✅ wiring tests | ✅ data/host_fiction.json exists (34KB, untracked) | ⚠️ | Persists to disk; rollback on commit failure |
| FictionGraph | ragin/graph/fiction.py | ✅ | ✅ | ✅ (part of 186) | ✅ | ✅ | Session-scoped fact graph; dependency-free |
| ChrolloAdapter | ragin/cycle/adapters.py | ✅ | ✅ | ✅ (via cycle tests) | ✅ | ✅ | Wraps ChrolloClassifier |
| ChrolloClassifier | ragin/chrollo/classifier.py | ✅ | ✅ | ✅ test_chrollo | ✅ (if model artifact present) | ✅ 0.8875 held-out acc (n=400, Wilson CI [0.853,0.914]) | RF 500 trees max_depth=16; needs joblib model + scaler |
| DonAdapter | ragin/cycle/adapters.py | ✅ | ✅ | ✅ test_don | ✅ | ✅ | Wraps ThreatRAGEngine |
| ThreatRAGEngine | ragin/don/rag_engine.py | ✅ | ✅ | ✅ test_don | ✅ | ✅ | BM25 + vector + optional LightRAG + optional LLM report |
| HisokaAdapter | ragin/cycle/adapters.py | ✅ | ✅ | ✅ test_hisoka (100+ tests) | ✅ | ✅ | Wraps AdaptiveDeceiver; propagates serve_path labels, honeytoken_triggered, metadata |
| AdaptiveDeceiver | ragin/hisoka/deceiver.py | ✅ | ✅ | ✅ test_hisoka | ✅ | ✅ | Top-level orchestrator; persona + scenario + canary + circuit breaker + cost tracker |
| ResponseGenerator | ragin/hisoka/deception.py | ✅ | ✅ | ✅ test_hisoka | ✅ | ✅ | LLM draft + deterministic fast-paths (sudo, IMDS, SSH, sudo -l, credential bait, FS replay) + post-processing (danger scrubbing, transcript styling) |
| GatewayClient | ragin/gateway/client.py | ✅ | ✅ | ✅ (via don/hisoka tests) | ✅ | ✅ | Shared HTTP; auth headers, WAF path rewrite, reasoning_effort=low, retry on empty content |
| ProviderTransport | ragin/cycle/provider_transport.py | ✅ | ✅ | ✅ 11/11 PASS | ⚠️ not yet (requires provider URL+key) | ❌ | GatewayClient subclass; fails closed when unauthenticated |
| ProviderTransportAdapter | ragin/cycle/provider_transport.py | ✅ | ✅ | ✅ (via provider transport tests) | ⚠️ not yet | ❌ | Injects ProviderTransport into ResponseGenerator._gateway; routes to deterministic fallback on provider error |
| ApprovalGateway | ragin/cycle/hitl.py | ✅ | ✅ | ✅ test_hitl | ✅ | ✅ Ablation (noapproval) | Risk-based policy: AUTO/NOTIFY/REQUIRE; ClaimedApprover for unattended, ConsoleApprover for interactive |
| Supported claims | ragin/cycle/supported_claims.py | ✅ | ✅ (opt-in RAGIN_FAIL_CLOSED) | ✅ (via verifier tests) | ⚠️ opt-in | ⚠️ | Fail-closed completeness on whoami/id/uname/hostname/echo/uptime/date/os-release |

## 4.2 Supporting components

| Component | IMPLEMENTED | INTEGRATED | TESTED | Notes |
|-----------|-------------|------------|--------|-------|
| Jev System One (JevAssessor) | ✅ | ✅ | ✅ (via server tests) | Free zen gateway (opencode.ai/zen/v1, key="public"); additive classification signal; RAGIN_JEVI_ENABLED=1 by default |
| PersonaManager | ✅ | ✅ | ✅ (via hisoka tests) | 5 personas (novice/intermediate/expert/advanced/apt) |
| ArtifactInjector | ✅ | ✅ | ✅ (via hisoka tests) | Bait credentials, lateral movement facts, filesystem artifacts |
| HoneytokenEngine | ✅ | ✅ | ✅ (via hisoka tests) | Canary-bound credentials; value-based trigger matching; per-session namespace |
| FilesystemLedger | ✅ | ✅ | ✅ (via hisoka tests) | Per-session FS fiction; deterministic replay; mutation invalidation |
| HisokaMemory | ✅ | ⚠️ lazy import (mem0ai) | ⚠️ | Cross-session attacker history enrichment; optional |
| CircuitBreaker | ✅ (utils.py) | ✅ | ✅ (via hisoka/don tests) | threshold=5, timeout_s=60; used by Hisoka and Don |
| CostTracker | ✅ (utils.py) | ✅ | ⚠️ | Daily/monthly/per-request budgets; used by Hisoka and Don |
| PromptTokenLimiter | ✅ (utils.py) | ✅ | ⚠️ | 32K max prompt tokens; used by Hisoka and Don |
| RateLimiter | ✅ (utils.py) | ✅ (server.py only) | ⚠️ | Used by server.py for lure + general rate limiting; NOT used by server_v2 |
| RBAC (auth/rbac.py) | ⚠️ | ❌ | ❌ | UNINSPECTED — not referenced in server_v2 or server.py auth paths |
| Decoys (decoys/*) | ⚠️ | ❌ | ❌ | UNINSPECTED — decoy service managers not wired into auth flow |
| SIEM connectors (siem/*) | ⚠️ | ⚠️ | ❌ | UNINSPECTED — elasticsearch/splunk/syslog connectors, likely optional |
| Rollout manager (rollout/*) | ⚠️ | ❌ | ❌ | UNINSPECTED — rollout stages in config/rollout/ but manager not wired |
| Coordination (cycle/coordination.py) | ⚠️ | ⚠️ | ❌ | UNINSPECTED — imported optionally in harness `__init__` with try/except; Supervisor/ExpertPool/VotingSystem/DeceptionReviewer etc. |

## 4.3 Deployment status

| Artifact | Status | Evidence |
|----------|--------|----------|
| Docker Compose (dev) | ✅ DEPLOYED (local) | docker-compose.yml: 9 services, ragin-internal + ragin-external networks |
| Docker Compose (prod) | ⚠️ exists | docker-compose.prod.yml — not confirmed running |
| Docker Compose (field) | ⚠️ exists | docker-compose.field.yml — .env.field.example requires replace-with-approved-private-bridge |
| Docker Compose (CI) | ✅ | docker-compose.ci.yml (732 bytes) |
| Docker Compose (canary/ab/traditional/vm) | ⚠️ exists | Variant files present |
| AWS CORE instance | ❌ NOT VERIFIED | Historical i-062a400b300f4f9e4; no current AWS access confirmed |
| AWS EDGE instance | ❌ NOT VERIFIED | Historical i-05bc6aab0bd4260a7 |
| OpenCode CLI bridge | ✅ local only | scripts/opencode_proxy.py — loopback-only; config at scripts/opencode_cli_bridge_safe_config.json |
| NGINX gateway | ✅ Docker | docker-compose.yml nginx service; requires RAGIN_API_KEY + SSL certs (./ssl/) |
| Prometheus/Grafana | ✅ Docker | docker-compose.yml; grafana admin password from env (default changeme in .env.example) |
| Redis | ✅ Docker | docker-compose.yml; appendonly yes, 256mb maxmemory |
| Cowrie | ✅ Docker | docker-compose.yml; port 2223; cowrie-data volume; NOT connected to server_v2 bridge in dev compose (that requires RAGIN_BRIDGE_HOST + internal Docker networking) |

## 4.4 Research validation status

| Experiment | Status | Artifacts | Validation |
|------------|--------|-----------|------------|
| Verifier redteam (offline) | ✅ VALIDATED | verifier_redteam.json (105 cases) | P=R=1.000; 47/47 artifact checks PASS; zero FPs/FNs |
| Verifier redteam (live deepseek) | ✅ VALIDATED | verifier_redteam_live_deepseek-v4-flash-free.json (236 drafts) | P=1.000, R=0.931, agreement 0.988; artifact checks PASS |
| Verifier redteam (live space-bunny post-fix) | ✅ VALIDATED | verifier_redteam_live.json (261 drafts) | P=0.995, R=0.943, agreement 1.000; artifact checks PASS |
| Verifier redteam (live space-bunny pre-fix) | ✅ VALIDATED | verifier_redteam_live_space-bunny-free_prefix.json | P=0.994, R=0.942, agreement 1.000; artifact checks PASS |
| Chrollo classifier | ✅ VALIDATED | models/chrollo/ (if present) | 0.8875 accuracy, Wilson CI; benchmark_report.json |
| CTI manual audit | ✅ VALIDATED | cti_manual_audit_corpus.json (766KB), cti_audit_annotations_*.json | Blinded annotator packets; cti_manual_audit.json |
| Human blind eval | ✅ VALIDATED | results/human_blind/, human_eval_scored*/ | human_blind_eval.py |
| External baselines | ✅ VALIDATED | external_baseline*.json (multiple reruns) | run_external_baseline.py; includes cowrie_guarded_rerun |
| Ablation battery | ✅ VALIDATED | ablation_battery.json + 5 ablation_audit_*.jsonl | ablation_battery.py |
| JEV hard subset | ✅ VALIDATED | jev_hard_subset.json | 6 informative rows; 1 assessed, 5 unavailable, 1 rescued |
| Two-channel metrics | ✅ VALIDATED | cross_session_consistency_bench.json, two_channel_metrics.py | gen_two_channel_tables.py |
| Bootstrap CI | ✅ VALIDATED | bootstrap_ci.json | bootstrap_ci.py |
| SP2027 rescue benchmark | ⚠️ recent | results/sp2027_rescue/, sp2027_rescue_behavior_benchmark.py | Recently added; not yet cross-checked |
| Overnight 20261009 | ⚠️ recent | results/overnight_20261009/ | Recently added; not yet inspected |

## 4.5 Gaps: implemented but not integrated/tested/deployed

1. **ProviderTransportAdapter** — implemented and tested in isolation (11/11 PASS), but NOT integrated into any live deployment (requires RAGIN_PROVIDER_ENABLED=1 + valid provider URL+key)
2. **HostFictionStore/HostFictionVerifier** — implemented and unit-tested, but cross-session consistency NOT yet validated in live field deployments (only local tests)
3. **RAGIN_FAIL_CLOSED** — supported_claims.py implemented, but opt-in via env var; NOT enabled by default
4. **RBAC (auth/rbac.py)** — exists but NOT wired into server_v2 or server.py auth
5. **Decoys (decoys/*)** — implemented but NOT integrated into serving path
6. **SIEM connectors** — implemented but NOT confirmed wired
7. **Coordination layer (Supervisor/ExpertPool/VotingSystem)** — implemented but only optionally imported; NOT in mandatory verification path
8. **RateLimiter in server_v2** — server.py uses RateLimiter for lure/general; server_v2 does NOT have rate limiting middleware
9. **standalone server_v2 mode** — DISABLED at runtime (RuntimeError)
10. **Legacy hisoka route in server.py** — DISABLED (410)
