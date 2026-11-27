# 01 — RAGIN Workspace Inventory

**Audit run:** 2026-10-10  
**Workspace root:** /home/elaref/Documents/research/ragin  
**Primary repo:** /home/elaref/Documents/research/ragin/RAGIN-Retrieval-Augmented-Honeypot-Intelligence  
**Git state:** main, 43 commits ahead of origin/main, dirty worktree (65 modified + many untracked)  
**Python:** 3.12.3, venv at .venv

## Directory structure

### Top-level workspace (`/home/elaref/Documents/research/ragin`)

| Path | Purpose | Status |
|------|---------|--------|
| `ragLegendre-Retrieval-Augmented-Honeypot-Intelligence/` | Primary git repo, full project | ACTIVE |
| `docs/` | Audit deliverables, next-stage plans, prior review docs | ACTIVE |
| `paper/` | TDSC manuscript (main.tex, figures/) + SP2027 paper (sp2027.tex) | ACTIVE, dirty |
| `graphify-out/` | Knowledge graph (graph.json 11M, 2026-09-27 build) | VERIFIED EXISTS |
| `scripts/` | Audit/utility scripts including verifier_redteam_check.py | ACTIVE |
| `ragLegendre/` | Stale narrow directory (empty/irrelevant) | UNINVENTORIED, likely stale |
| `.venv/` | Python virtual environment | ACTIVE |
| `ESWA-D-26-33173.pdf` | External paper reference (4.6MB) | BINARY, not inspected |
| `imc_vpn.pdf` | External reference (1.6MB) | BINARY, not inspected |
| `CLAUDE.md` | Project instructions (graphify rules) | READ |

### Primary repository (`RAGIN-Retrieval-Augmented-Honeypot-Intelligence/`)

#### Source packages (`ragin/`)

| Package | Role | Files | Notes |
|---------|------|-------|-------|
| `ragin/server.py` | Legacy HTTP server (Chrollo/Don/Hisoka/Jev standalone) | 1 | LEGACY — hisoka route returns 410 disabled |
| `ragin/server_v2.py` | Auth authoritative server (Harness pipeline + Session + Sandbox + Cowrie bridge) | 1 | ACTIVE — pipeline mode is default and standalone is disabled |
| `ragin/cycle/` | Intelligence cycle: Harness, Session, Sandbox, Verifier, HITL, adapters, provider_transport | 13 py + containment/ | ACTIVE CORE |
| `ragin/hisoka/` | Adaptive deception: deceiver, deception (ResponseGenerator), persona, memory, honeytokens, fs_ledger, models | 14 py | ACTIVE |
| `ragin/chrollo/` | Classifier: RF classifier, features, features_seq, models, pipeline, session_parser | 7 py | ACTIVE |
| `ragin/don/` | RAG engine: rag_engine, cti_corpus, vector_store, threat_mapper, models, pipeline, intel_corpus, lightrag_adapter, mitre_cti_loader, attack_heatmap, extended_cti_loader, graph | 15 py | ACTIVE |
| `ragin/graph/` | FictionGraph (session), HostFictionStore (host), mitre | 4 py | ACTIVE |
| `ragin/gateway/` | GatewayClient (shared HTTP for LLM backends) | 2 py | ACTIVE |
| `ragin/transport/` | mTLS transport (MTLSConfigError, build_server_context_from_env, peer_certificate_authorized) | 2 py | ACTIVE |
| `ragin/auth/` | RBAC | 1 py | UNINSPECTED DETAIL |
| `ragin/benchmark/` | Benchmark runners (core, cowrie_adapter, effectiveness, harness_bridge, honeygpt_benchmark, human_eval, human_eval_personas, run_benchmarks) | 8 py | RESEARCH |
| `ragin/decoys/` | Decoy services (base, http_service, manager, ssh_service, telnet_service) | 5 py | UNINSPECTED DETAIL |
| `ragin/intelligence/` | Adaptive response, evasion detector, models, skill_strategy | 4 py | UNINSPECTED DETAIL |
| `ragin/jev/` | Jev System One assessment (assessment, client, models, orchestration) | 4 py | ACTIVE (free zen gateway) |
| `ragin/monitoring/` | Alerts, audit, health, metrics | 4 py | ACTIVE |
| `ragin/rollout/` | Rollout manager, metrics, models | 4 py | UNINSPECTED DETAIL |
| `ragin/siem/` | SIEM connectors (connector, elasticsearch, splunk, syslog) | 4 py | UNINSPECTED DETAIL |
| `ragin/decision/` | Optional assessment | 2 py | UNINSPECTED DETAIL |
| `ragin/utils.py` | RateLimiter, CircuitBreaker, CostTracker, PromptTokenLimiter, _redact_pii | 1 | ACTIVE |
| `ragin/config/` | settings.yaml, alert_rules.yml, gateway.toml, nginx configs, grafana, rollout stages, docker-entrypoint-envsubst.sh | multiple | ACTIVE |
| `ragin/__init__.py` | Package init (lazy) | 1 | READ |

#### Tests (`tests/`)

| Directory | Count | Focus |
|-----------|-------|-------|
| `tests/unit/` | 80 .py files | Component-level: verifier, fiction graph, host fiction, hisoka, chrollo, don, cycle, harness, server_v2, hitl, provider_transport, adapters, supported_claims, artifact_consistency, etc. |
| `tests/security/` | 4 .py files | mtls_transport, task2_verified_serving, adversarial, input_validation |
| `tests/integration/` | 5 .py files | gateway_api, performance, pipeline, readiness, stability |
| `tests/test_e2e_comprehensive.py` | 1 | E2E |
| `tests/test_performance_benchmark.py` | 1 | Performance |
| `tests/test_security_validation.py` | 1 | Security validation |
| `tests/benchmark_traditional.py` | 1 | Traditional benchmark |

**Total test files: 92** (80 unit + 4 security + 5 integration + 3 top-level)

#### Scripts (`scripts/`)

Key scripts:
- `verifier_redteam_check.py` — artifact consistency checker (47 claims, PASS)
- `verifier_redteam_security_oracle.py` — security oracle (38KB, recently modified)
- `verifier_redteam.py`, `verifier_redteam_cases.py`, `verifier_harm_cases.py`, `verifier_harm_probe.py` — redteam harness
- `opencode_proxy.py` — OpenCode CLI bridge (loopback-only)
- `deploy.py`, `deploy.sh`, `deploy_field.sh`, `field_provision.sh` — deployment
- `cowrie_pipeline_bridge.py`, `drive_cowrie.py` — Cowrie integration
- `run_baseline_comparison.py`, `run_external_baseline.py` — baselines
- `bootstrap_ci.py`, `verifier_ci_cluster_bootstrap.py` — CI bootstrap
- `gen_sp_figures.py`, `audit_figure_geometry.py` — SP2027 figures
- `cti_manual_audit.py` — CTI audit (59KB)
- `human_blind_eval.py`, `run_human_eval.py` — human evaluation

#### Results (`results/`)

225 files across 17 subdirectories. Key artifacts:
- `verifier_redteam.json` — offline 105-case stratum (P=R=1.000)
- `verifier_redteam_live_deepseek-v4-flash-free.json` — 236 drafts, P=1.000, R=0.931
- `verifier_redteam_live.json` — 261 drafts, P=0.995, R=0.943
- `verifier_redteam_live_space-bunny-free_prefix.json` — pre-fix, P=0.994, R=0.942
- `verifier_artifacts_manifest.json` — SHA256 manifest of 4 artifacts
- `verifier_integrity_provenance.json` — provenance record (dirty repo, git f0c4042)
- `cti_manual_audit_corpus.json` — 766KB blinded corpus
- `external_baseline_*.json` — multiple baseline reruns
- `bootstrap_ci.json`, `derived_headline_values_2026-10-09.json` — derived metrics
- `host_fiction.json` (in data/) — 34KB host fiction store

#### Configuration

| File | Purpose |
|------|---------|
| `.env.example` | Template env (API_KEY, RAGIN_LLM_BASE_URL=http://127.0.0.1:8731/v1, loopback-test key) |
| `.env.field.example` | Field endpoint template (RAGIN_FIELD_ARM, synthetic credentials only, replace-with-approved-private-bridge) |
| `settings.yaml` | Cloud LLM config (OpenRouter, model router, prompt engineering, response validation, cost tracking, observability, security, local fallback) |
| `docker-compose.yml` | 9 services: gateway, chrollo, don, hisoka, redis, jev, prometheus, grafana, nginx, cowrie |
| `docker-compose.prod.yml`, `.field.yml`, `.ci.yml`, `.test.yml`, `.ab.yml`, `.canary.yml`, `.traditional.yml`, `.vm.yml`, `.cowrie.yml` | Environment variants |

#### Documentation

| File | Purpose |
|------|---------|
| `README.md` | Project overview (dirty) |
| `PROJECT_STATUS.md` | Status tracking (dirty, 54KB) |
| `CODE_AUDIT.md` | Previous code audit (17KB) |
| `DEPLOYMENT_READINESS.md` | Deployment readiness (5.6KB) |
| `HARNESS_LOOP_PLAN.md` | Harness loop design (18KB) |
| `RAGIN_CLOUD_LLM_MIGRATION_PLAN.md` | Cloud LLM migration (6.8KB) |
| `RESPONSE_LETTER_ESWA-S-26-45224.md` | Reviewer response letter (17KB) |
| `REVIEW_ESWA-S-26-45224_RAGIN.md` | Reviewer report (32KB) |
| `REVIEW_TIFS_Intelligence-Ladder.md` | TIFS review (13KB) |
| `REVIEWER_FIXES_SUMMARY.md` | Reviewer fixes (10KB) |
| `SUPERVISOR_REVIEW_BRIEF.md` | Supervisor review (5KB) |
| `TDSC_COVER_LETTER.md` | TDSC cover letter (5KB) |
| `docs/RAGIN_RELEASE_*_2026-10-08.md` | Release manifest/report/ledger/threat model |
| `docs/SP2027_*_2026-10-0*.md` | SP2027 audit and hard reviews |
| `docs/next_stage/`, `docs/task1-3*/`, `docs/superpowers/` | Planning dirs |

## Git status summary

**Branch:** main  
**HEAD:** f0c4042 (2026-10-10 06:42:55 +0300)  
**Ahead of origin/main:** 43 commits  
**Modified (selected):** server.py, server_v2.py, harness.py, sandbox.py, verifier.py, adapters.py, supported_claims.py, graph.py, fiction.py, host_fiction.py, deception.py, rag_engine.py, cycle/graph.py, benchmark/core.py, docker-compose.yml, .env.example, .env.field.example, paper/main.tex (+ all sections), paper/figures/*.tex, ci.yml, tests/unit/* (many), scripts/verifier_redteam_check.py  
**Untracked (selected):** provider_transport.py, containment/, transport/, decision/, harness.py.bak20261010, data/host_fiction.json, data/sessions/ses-* (6932 files), results/artifact_manifest_2026-10-09.json, results/derived_headline_values_2026-10-09.json, results/verifier_*.json, results/sp2027_rescue/, results/overnight_20261009/, run/, scripts/opencode_proxy.py, scripts/verifier_ci_*.py, scripts/verifier_harm_*.py, scripts/verifier_redteam_security_oracle.py, services/mock_provider.py, tests/security/test_mtls_transport.py, tests/security/test_task2_verified_serving.py, tests/unit/test_provider_transport*.py, tests/unit/test_opencode_proxy.py, tests/unit/test_validate_release_artifacts.py, tests/unit/test_verifier_redteam_security_oracle.py, paper/sp2027.tex, paper/sp2027.pdf, paper/sections/sp_*.tex, live_src_check.sh, evidence/

## Inspection coverage ledger

### Fully read (substantive)
- ragin/server.py
- ragin/server_v2.py
- ragin/cycle/__init__.py
- ragin/cycle/harness.py
- ragin/cycle/sandbox.py
- ragin/cycle/verifier.py
- ragin/cycle/adapters.py
- ragin/cycle/session.py
- ragin/cycle/hitl.py (truncated)
- ragin/cycle/provider_transport.py
- ragin/cycle/supported_claims.py
- ragin/hisoka/deception.py (lines 1-1098 of 3195)
- ragin/hisoka/deceiver.py (truncated)
- ragin/chrollo/classifier.py
- ragin/don/rag_engine.py
- ragin/gateway/client.py
- ragin/graph/fiction.py
- ragin/graph/host_fiction.py
- ragin/transport/mtls.py
- ragin/utils.py (not read — inferred from imports)
- config/settings.yaml
- .env.example
- .env.field.example
- docker-compose.yml
- pyproject.toml
- requirements-runtime.txt
- Makefile
- scripts/verifier_redteam_check.py
- results/verifier_artifacts_manifest.json
- results/verifier_integrity_provenance.json
- tests/unit/test_server_v2.py
- tests/unit/test_provider_transport.py
- tests/unit/test_artifact_consistency.py
- tests/security/test_task2_verified_serving.py

### Tested by execution (PASS)
- scripts/verifier_redteam_check.py — 47/47 PASS
- tests/unit/test_provider_transport.py — 11/11 PASS
- tests/security/test_task2_verified_serving.py — 13/13 PASS
- tests/unit/test_verifier.py + test_fiction_graph.py + test_hisoka.py + test_artifact_consistency.py — 186/186 PASS
- tests/unit/test_server_v2.py — 24/24 PASS
- tests/unit/test_cycle.py + test_don.py + test_chrollo.py + test_hitl.py + test_host_fiction.py — 230/230 PASS

### Selectively inspected / not fully read
- ragin/hisoka/deception.py (lines 1099-3195 unread — contains _scrub_danger_signals completion, ResponseGenerator class, deterministic fast-paths)
- ragin/hisoka/deceiver.py (truncated — AdaptiveDeceiver.generate_response body)
- ragin/cycle/hitl.py (truncated after ApprovalGateway — DefaultRiskBasedPolicy body unread)
- ragin/auth/rbac.py, ragin/decoys/*, ragin/intelligence/*, ragin/jev/*, ragin/monitoring/*, ragin/rollout/*, ragin/siem/*, ragin/decision/* — UNINSPECTED
- ESWA-D-26-33173.pdf, imc_vpn.pdf — binary, not inspected
- data/sessions/ses-* (6932 files) — not inspected individually
- All result JSON files except the 4 verifier redteam artifacts + manifest + provenance + derived_headline_values

### Known stale/unused
- `ragin/server.py` — hisoka routereturns 410; legacy serving disabled
- `ragin/server_v2.py` standalone mode — disabled at runtime (`raise RuntimeError`)
- `ragLegendre/` — stale narrow directory (likely from a prior agent)
- `harness.py.bak20261010` — backup of pre-modification harness
- `scripts/_tmp_*` — temporary scripts from recent runs
- `run/strace_server.*` — strace output from server debug
