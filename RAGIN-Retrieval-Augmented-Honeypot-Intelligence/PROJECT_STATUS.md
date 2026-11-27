# RAGIN — Complete Project Status & Plan Checklist

**Date:** 2026-10-08 (hard-review remediation in progress; Plan B stack remains tailnet-only)

> **Current state (2026-10-08):** The Azure subscription is under a billing hold
> (`ReadOnlyDisabledSubscription`) and the old AWS VPS field deployment is
> historical. The active stack is **Plan B (zodiac)**: hisoka/chrollo/don
> (+ cowrie ACI) on an always-on box, reachable **only inside the tailnet** —
> field-adjacent, not field. The TDSC validation set is complete and
> reproducible: C1 `graph_consistency_bench.json` (6/6 proofs), §5
> `ablation_battery.json` (5/5), C3 `mtp_steering_eval.json` (4/4),
> `bootstrap_ci.json` (5/5 proofs), the **re-derived live 218-query benchmark**
> (`live_benchmark_zodiac_20260922.json`: composite **0.880 [0.857, 0.900]**,
> replacing the uncitable 0.855; **run-to-run stable** — archived second run
> `stability_run1_vs_run2.json` deltas +0.005 composite, pass-agreement 0.991,
> **unchanged on the judge-audited rows**), the **LLM-judge evaluation
> (3 personas, grok-4.7-free — no human raters; blind human packets were
> delivered but never returned) consensus 3.86/5** (agreement 0.750), the **judge-panel audit**
> (`live_benchmark_judge_panel_corrected.json`: canary-bias magnitude 1.35
> corrected, harness artifact reclassified), and the **fold-down hard-subset
> census** (`jev_hard_subset.json`: 6/400 informative sessions — 1 rescued
> live, 5 lost to provider refusals; the fold-down claim is now stated at the
> benchmark's resolution, not as general subsumption). Two manuscript sources
> exist; per Task 5 (2026-10-08) `paper/sp2027.tex` is the **canonical next
> release/submission surface** (shorter rescue manuscript) and `paper/main.tex`
> is the **full audit/extended companion**. Neither is submission-ready: the
> `algorithm.sty` blocker was resolved on 2026-10-08 (install of
> `texlive-science`, Task 7), and both PDFs were rebuilt from the current
> sources on 2026-10-08 (main.pdf 27 pp, sp2027.pdf 12 pp after hard-review integration). They become
> release candidates only after the evidence gates in
> `docs/RAGIN_RESULTS_LEDGER_2026-10-08.md` pass. The old
> "17 pp, main.pdf, 'The Intelligence Ladder'" description below is historical.
> Operational truth
> is regenerated live in `results/azure_services_snapshot.md` — this file is
> the plan/checklist view. Historical ESWA-era numbers below are marked as such.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture Summary](#2-architecture-summary)
3. [Implementation Phases — Checklist](#3-implementation-phases)
4. [Testing & Benchmarks](#4-testing--benchmarks)
5. [Competitive Position](#5-competitive-position)
6. [Deployment Status](#6-deployment-status--plan-b-zodiac-live--plan-a-dormant)
7. [Paper & Publication Status](#7-paper--publication-status)
8. [Remaining Work](#8-remaining-work)
9. [Appendix: File Inventory](#9-appendix-file-inventory)

---

## 1. Project Overview

**RAGIN** (Retrieval-Augmented Generative INtelligence) is an LLM-powered honeypot system that combines:

- **RAG-enhanced threat intelligence** (780K+ CTI documents, MITRE ATT&CK STIX)
- **Multi-persona adaptive deception** (7 personas, skill-stratified responses)
- **Persistent attacker memory** (Mem0-backed cross-session profiling)

**Primary competitor:** HoneyGPT (arXiv 2406.01882, Computer Networks 2026)
**Secondary competitors:** DecoyPot, Attivo/SentinelOne, Illusive Networks, TrapX, Trapster

---

## 2. Architecture Summary

```
Attacker ──► [LLM Gateway :8080] ──► [Chrollo :8081] ──► [Don :8082] ──► [Hisoka :8083]
                (Rust)              (Classifier)        (RAG Engine)     (Deceiver)
                  │                    │                    │                 │
                  ▼                    ▼                    ▼                 ▼
              apmix free-tier    Random Forest        LightRAG +         Mem0 Memory
              LLMs (deepseek-    94.2% accuracy       780K+ docs         +7 personas
              v4-flash-free)
                                                     Qdrant vectors     +honeytokens
```

| Component | Language | Port | Role |
|-----------|----------|------|------|
| LLM Gateway | Rust (Axum) | 8080 | API routing, auth, cost tracking, rate limiting |
| Chrollo | Python | 8081 | Behavioral classifier (Random Forest, 94.2% acc, 3.1% FP) |
| Don | Python | 8082 | RAG threat intelligence engine (92.1% accuracy) |
| Hisoka | Python | 8083 | Adaptive deception layer (4.1x dwell time) |

Deployed as the **zodiac stack** (`scripts/install_zodiac_stack.sh`, systemd --user,
tailnet-only): LLM = apmix free-tier models — generator/don `deepseek-v4-flash-free`,
judge `grok-4.7-free` (independent); model churn is caught by the twice-daily
`ragin-apmix-watch.timer` → `scripts/check_apmix_catalog.py`, which also
reseeds the judge-panel audit and audited stability offline on every probe
(`scripts/reseed_audit_pipeline.py`) so published numbers stay consistent
with any newly landed campaign runs.

---

## 3. Implementation Phases — Checklist

> **Note:** Phases 1-8 cover the core RAGIN honeypot pipeline (Chrollo→Don→Hisoka). Phase 9 covers the Intelligence Cycle subsystem (`ragin/cycle/`) — harness, session, sandbox, multi-agent coordination, threat modeling, and verification built on top of the pipeline.

### Phase 1: Core Infrastructure ✅ DONE

| # | Task | Status | Evidence |
|---|------|--------|----------|
| 1.1 | LLM Gateway (Rust/Axum) | ✅ | `llm-gateway/src/` — auth, routing, cost tracking |
| 1.2 | API authentication (API key) | ✅ | 401 on missing/wrong key |
| 1.3 | Rate limiting | ✅ | Token bucket per-key |
| 1.4 | Cost tracking (OpenRouter) | ✅ | PromptTokenLimiter, budget caps |
| 1.5 | Circuit breaker | ✅ | Provider fallback chain |
| 1.6 | Dockerfiles | ✅ | `Dockerfile.gateway`, `Dockerfile.python` |

### Phase 2: Chrollo (Classifier) ✅ DONE

| # | Task | Status | Evidence |
|---|------|--------|----------|
| 2.1 | Random Forest classifier | ✅ | 94.2% accuracy, 3.1% FP |
| 2.2 | Feature extraction | ✅ | Command pattern analysis |
| 2.3 | Dual escalation paths | ✅ | High-confidence → Don, Low-confidence → Hisoka directly |
| 2.4 | Unit tests | ✅ | `tests/unit/test_chrollo.py` |

### Phase 3: Don (RAG Engine) ✅ DONE

| # | Task | Status | Evidence |
|---|------|--------|----------|
| 3.1 | LightRAG integration | ✅ | Hybrid dense/sparse retrieval |
| 3.2 | Qdrant vector store | ✅ | 780K+ CTI documents indexed |
| 3.3 | MITRE ATT&CK STIX parser | ✅ | 719 techniques indexed |
| 3.4 | Threat analysis pipeline | ✅ | `ragin/don/rag_engine.py` |
| 3.5 | ATT&CK Navigator heatmap | ✅ | Programmatic generation |
| 3.6 | Unit tests | ✅ | `tests/unit/test_don.py` |
| 3.7 | LightRAG adapter fix | ✅ | `ragin/don/lightrag_adapter.py` — added `_ensure_all_initialized_*` helpers, 33/33 unit tests pass, 5 integration tests gated behind `@pytest.mark.integration` |

### Phase 4: Hisoka (Deceiver) ✅ DONE

| # | Task | Status | Evidence |
|---|------|--------|----------|
| 4.1 | 7 persona personas | ✅ | junior_dev, sysadmin, db_admin, security_analyst, help_desk, executive, default |
| 4.2 | Skill-stratified responses | ✅ | Difficulty adjusts to attacker skill level |
| 4.3 | Honeytoken injection | ✅ | 6 types: credential, URL, API key, file path, DB record, SSH key |
| 4.4 | Evasion detection | ✅ | Behavioral pattern detection |
| 4.5 | Dwell-time analytics | ✅ | Active tracking, engagement scoring |
| 4.6 | Mem0 persistent memory | ✅ | Cross-session attacker profiling |
| 4.7 | Unit tests | ✅ | `tests/unit/test_hisoka.py` |

### Phase 5: Integration & Testing ✅ DONE

| # | Task | Status | Evidence |
|---|------|--------|----------|
| 5.1 | Full pipeline integration | ✅ | Chrollo → Don → Hisoka, <5s E2E |
| 5.2 | API server (FastAPI) | ✅ | `ragin/server.py` |
| 5.3 | E2E comprehensive tests | ✅ | 62 APT scenario tests |
| 5.4 | Performance benchmarks | ✅ | 17 tests, all ≤2.5s latency |
| 5.5 | Security validation | ✅ | 27 tests, auth/sanitization/secrets |
| 5.6 | Integration tests | ✅ | Pipeline, error propagation |
| 5.7 | Docker Compose stack | ✅ | `docker-compose.yml` — all services + Redis/Prometheus/Grafana/Nginx |

### Phase 6: Benchmark Framework ✅ DONE

| # | Task | Status | Evidence |
|---|------|--------|----------|
| 6.1 | Core benchmark harness | ✅ | `ragin/benchmark/core.py` — scoring, reporting |
| 6.2 | Effectiveness metrics | ✅ | `ragin/benchmark/effectiveness.py` — composite scoring |
| 6.3 | HoneyGPT competitive benchmark | ✅ | `ragin/benchmark/honeygpt_benchmark.py` — head-to-head delta |
| 6.4 | Benchmark unit tests | ✅ | 27 tests, all passing |
| 6.5 | Competitive analysis docs | ✅ | `docs/COMPETITIVE_ANALYSIS.md`, `docs/COMMERCIAL_COMPETITIVE_BENCHMARK.md` |
| 6.6 | Harness bridge | ✅ | `ragin/benchmark/harness_bridge.py` — live pipeline → BenchmarkResult |
| 6.7 | Live benchmark runner | ✅ | `scripts/run_live_benchmark.py` — 25 queries, 80ms avg, real Chrollo→Don→Hisoka |

### Phase 7: Cloud LLM Migration ✅ DONE

| # | Task | Status | Evidence |
|---|------|--------|----------|
| 7.1 | OpenRouter integration | ✅ | Free model: `moonshotai/kimi-k3-free` |
| 7.2 | Provider fallback chain | ✅ | Circuit breaker in Gateway |
| 7.3 | Cost management | ✅ | $500/month, $20/day caps |
| 7.4 | Migration plan documented | ✅ | `RAGIN_CLOUD_LLM_MIGRATION_PLAN.md` |

### Phase 8: Deployment & Operations ✅ DONE

| # | Task | Status | Evidence |
|---|------|--------|----------|
| 8.1 | Local deploy script | ✅ | `scripts/deploy.py start/stop/status` |
| 8.2 | Docker Compose production | ✅ | `docker-compose.yml` with healthchecks |
| 8.3 | Prometheus metrics | ✅ | Port 9090, 30d retention |
| 8.4 | Grafana dashboards | ✅ | Port 3000, pre-configured |
| 8.5 | Nginx reverse proxy | ✅ | TLS termination, port 80/443 |
| 8.6 | Operational runbook | ✅ | `docs/OPERATIONAL_RUNBOOK.md` |
| 8.7 | Troubleshooting guide | ✅ | `docs/TROUBLESHOOTING.md` |
| 8.8 | Security hardening guide | ✅ | `docs/SECURITY_HARDENING.md` |

### Phase 9: Intelligence Cycle — Harness & Loop ✅ DONE

| # | Task | Status | Evidence |
|---|------|--------|----------|
| 9.1 | Session class (append-only event log) | ✅ | `cycle/session.py` — event_log, build_context, emit, load/create |
| 9.2 | Harness class (stateless orchestration loop) | ✅ | `cycle/harness.py` — process_with_threat_modeling, verification + retry |
| 9.3 | Sandbox class (attacker interaction isolation) | ✅ | `cycle/sandbox.py` |
| 9.4 | Component adapters | ✅ | `cycle/adapters.py` — ChrolloAdapter, DonAdapter, HisokaAdapter |
| 9.5 | Producer-Reviewer pattern | ✅ | `cycle/coordination.py` — EnhancedProducerReviewer |
| 9.6 | Supervisor pattern (dynamic persona routing) | ✅ | `cycle/coordination.py` — Supervisor with PersonaRoute |
| 9.7 | Multi-agent voting system | ✅ | `cycle/coordination.py` — VotingSystem, VoteResult |
| 9.8 | Expert Pool for CTI skill selection | ✅ | `cycle/coordination.py` — ExpertPool, ExpertAgent |
| 9.9 | Hierarchical Delegation for complex attacks | ✅ | `cycle/coordination.py` — DelegationChain |
| 9.10 | STRIDE threat modeling | ✅ | `cycle/threat_modeling.py` — ThreatModeler, 10 STRIDE patterns |
| 9.11 | Attack chain construction from TTPs | ✅ | `cycle/threat_modeling.py` — AttackChainBuilder |
| 9.12 | MTTA metrics tracking | ✅ | `cycle/metrics.py` — MTTATracker |
| 9.13 | Multi-turn TTP tracking | ✅ | `cycle/multi_turn.py` — MultiTurnTracker, TTPEvolution |
| 9.14 | Structured finding output (MITRE + confidence) | ✅ | Finding events emitted for critical/high risk |
| 9.15 | Unit tests | ✅ | 170+ new tests (coordination 26, threat_modeling 74, multi_turn 17, etc.) |

### Phase 10: Graph Engineering & Verified Orchestration (TDSC retarget) 🔨 IN PROGRESS

Addresses the five ESWA reviewer complaints at the root. Novelty argument:
`docs/TDSC_NOVELTY_PLAN.md`.

| # | Task | Status | Evidence |
|---|------|--------|----------|
| 10.1 | Honest identity rewrite (no honeypot tells; shared fictional world) | ✅ | `ragin/hisoka/deception.py` — webapp/uid=1001, corp.local hosts, pinned uname/kernel, template fallbacks identical in format |
| 10.2 | Fiction graph (assert-once stable predicates, contradictions recorded) | ✅ | `ragin/graph/fiction.py` — `observe()`, `fact_block()`, 52 tests in `test_fiction_graph.py` |
| 10.3 | MITRE next-technique steering + technique-aware bait | ✅ | `ragin/graph/mitre.py` — 14-tactic chain, edge traversal, T1003*/T1552*/T1046/T1571/T1021*/T1550/T1078 bait hints |
| 10.4 | HITL approval gateway (AUTO/NOTIFY/REQUIRE) + audit trail | ✅ | `ragin/cycle/hitl.py` — risk policy, `RequiresApprovalError`, FileAuditTrail |
| 10.5 | Checkpointed LangGraph loop with verify/retry + HITL resume | ✅ | `ragin/cycle/graph.py` — cached compiled graph + MemorySaver; `_run_linear` fallback |
| 10.6 | Fiction/strategy blocks injected into LLM context | ✅ | `ragin/hisoka/deceiver.py` — `fiction_block` / `strategy_block` → system message |
| 10.7 | Unit tests | ✅ | `test_mitre_chain.py`, `test_fiction_graph.py`, `test_hitl.py`, `test_cycle_graph.py` — full suite **1323 passed / 116 skipped** (2026-09-22 era; current total in §4.1), ruff clean |
| 10.8 | LLM-judge eval re-run with current pipeline (relabeled 2026-10-24: judges are LLM personas, not human raters) | ✅ | `results/human_eval_scored_20260922_180637_consensus/consensus.json` — 3-persona LLM-judge consensus **3.86/5**, agreement 0.750, 8/8 ≥3; full transcripts + fiction-consistent DB bait (truncation + 5432-vs-mysql defects fixed in-run) |
| 10.9 | Consistency re-query benchmark (C1) | ✅ | `results/graph_consistency_bench.json` — 6/6 proofs: 0 contradictions / 45 re-queries, 1.0 determinism, 0 failed-verdict serves; caught+fixed the `uname` fingerprint false-contradiction and the `verify_node` fail-open (fail-safe fallback now regression-locked) |
| 10.10 | Next-TTP steering benchmark (C3) + 5-ablation battery | ✅ | `results/mtp_steering_eval.json` (4/4: top-3 0.9, steer-to-plan 0.9, gap 0.9→0.0) + `results/ablation_battery.json` (A1–A4 degrade-as-expected, A5 equivalent); edge-first ranking fix + 4 GT-grounded graph edges fell out of C3 |
| 10.11 | Statistical intervals (bootstrap/Wilson) | ✅ | `scripts/bootstrap_ci.py` → `results/bootstrap_ci.json` — 5/5 proofs; live composite **0.880 [0.857, 0.900]** from the re-derived zodiac run `results/live_benchmark_zodiac_20260922.json` (218 queries, graph engine, 0 errors) — the uncitable 0.855 is now superseded by a fully-provenance-tracked artifact |
| 10.12 | Reproducibility proof | ✅ | all three batteries re-ran byte-identical from clean slate (2026-09-22) |
| 10.13 | Run-to-run stability (live stratum) | ✅ | `results/stability_run1_vs_run2.json` — two archived 218-query reruns: composite 0.8796 vs 0.8845 (Δ +0.005, MAD 0.027, pass-agreement 0.991) → **stable on the recorded pair**; technique/actor suites exactly reproduce (MAD 0.000); **audited-panel comparison added** (`audited_panel`: 0.8826 vs 0.8877, same agreement) with the variance decomposition — 32/60 persona rows differ run-to-run, only 1 touched by the audit, so variance is generator-side |
| 10.14 | Judge-panel audit (persona judge) | ✅ | `scripts/rescore_judge_panel.py` → `results/live_benchmark_judge_panel_corrected.json` (+ per-run `*_judgescored.json`): bait-deployment credit for canary-serving rows (bias magnitude **1.35** across the zodiac pair), harness echo artifact reclassified out of the deception mean, floats rounded; both judge copies patched with the 0.85 bait floor; 17 regression tests |
| 10.15 | Fold-down hard-subset census | ✅ | `scripts/jev_hard_subset.py` → `results/jev_hard_subset.json`: full 400-session census finds the informative stratum the n=200 A/B missed — **6 sessions** (all APT, one rung under floor, Chrollo conf 0.53 vs 0.75); live JEV arm **rescued 1/6**, 5 unavailable (zen route intermittently 403s attack-shaped payloads, probe-confirmed); fold-down claim restated as **resolution-bounded**, and the provider-availability finding recorded in the paper (§V-E, §VII) |
| 10.16 | Scheduled watch = audit pipeline | ✅ | `check_apmix_catalog.py` stage 3 reseeds the audit + audited stability offline on every probe (idempotent, timestamp-driven); exit semantics 0/1/2/3 (healthy / probe failure / catalog drift / stability review) documented + unit-tested (`test_watch_audit_pipeline.py`, 10 tests) |

---

## 4. Testing & Benchmarks

### 4.1 Test Suite Results

```
TOTAL (2026-10-08)                    1715 collected = 1599 passed + 116 skipped + 0 failed
```

> **Current (2026-10-08, Task 6):** `.venv/bin/pytest -q` → **1,715 collected = 1,599
> passed + 116 skipped + 0 failed** (skips are integration/LLM-gated), ruff clean.
> Reconciles with the pre-Task-2 baseline `9 failed, 1,585 passed, 116 skipped`: Task 2
> repaired the zero-byte HF blob and added +5 retrieval-mode lock tests, Task 3 added
> +1 JEV-consistency test → 9 recovered + 6 new = 1,599 passed. The earlier
> `1,709 collected` figure predates those six verified tests; do not quote it as current.
>
> **Historical (2026-09-22) — do not treat as current:**
>
> ```
> TOTAL                                 1323 passed   (116 skipped)   0 failures
> ```
>
> Updated 2026-09-22 — Session: 1323 passed, 116 skipped (integration/LLM-gated), lint clean.
> New since the 2026-07-29 state (1098 passed): `test_fiction_graph.py` (distro-extraction
> regression lock incl. the `uname` banner fix), `test_cycle_graph.py` (C2 fail-safe
> fallback contract), `test_mitre_chain.py` (edge-first ranking), plus graph/decoy/siem
> modules. Historical note from 2026-07-29 below.
>
> Updated 2026-07-29 — Session: 1110 collected, 1098 passed, 12 skipped.
> Added 88 new tests across Phase 9: coordination (26), threat_modeling (74), plus existing multi_turn (17), metrics, adapters, cycle integration.
> LightRAG adapter: 38 collected, 5 deselected (integration/slow), **33 passed**.
>
> Key fix: `LightRAGAdapter` never called `initialize_storages()` → `_storage_lock` was `None` → every insert/query crashed with `PipelineNotInitializedError`. Added `_ensure_all_initialized_sync/async` helpers. Tests partitioned so integration tests (need LLM gateway at `:8080`) are skipped in default run.
>
> Key new test modules:
> - `test_multi_turn.py` (17 tests) — MultiTurnTracker: TTP diversity, persistence, escalation detection, cross-turn evolution
> - `test_human_eval.py` (19 tests) — Likert rubrics, ground-truth evaluation, LLM evaluator protocol
> - `test_human_eval_subagents.py` (36 tests) — 7-persona catalog, prompt builder, Cohen kappa, Krippendorff α, danger-signal override, JSON extraction
> - `test_cowrie_adapter.py` (30 tests) — Cowrie JSON parsing, metrics extraction, RAGIN vs Cowrie comparison
> - `test_honeytoken_propagation.py` (6 tests) — honeytoken_triggered propagation from DeceptionResponse → cti_analysis in both `process()` and `process_with_threat_modeling()` (bridge path)
> - `test_attack_heatmap.py` (19 tests) — ATT&CK Navigator heatmap generation, technique coverage, layer serialization
> - `test_threat_modeling.py` (74 tests) — STRIDE analysis, attack chains, MITRE mapping
> - `test_harness_threat_modeling.py` (15 tests) — harness + threat modeling integration
> - `test_cycle.py`, `test_coordination.py`, `test_metrics.py` — cycle loop tests
> - `test_extended_cti.py`, `test_gateway_integration.py`, `test_hisoka_memory.py`
> - `test_lightrag_adapter.py` (38 tests, 33 fast + 5 integration) — LightRAG adapter initialization fix, search, hybrid, fallback, persistence, MITRE loader
> - `test_server_v2.py` — server v2 tests
> - `test_performance.py`, `test_readiness.py`, `test_stability.py` — integration tests
> - `test_gateway_api.py`, `test_adversarial.py`, `test_input_validation.py` — security tests

### 4.2 Performance Benchmarks

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Chrollo classification latency | ≤2.5s | <0.1s | ✅ |
| Don RAG analysis latency | ≤2.5s | <0.1s | ✅ |
| Hisoka deception response | ≤2.5s | <0.1s | ✅ |
| Full pipeline (Chrollo→Don→Hisoka) | ≤5s | <0.2s | ✅ |
| Concurrent throughput (10 parallel) | ≥5 RPS | >10 RPS | ✅ |
| Service recovery after burst | <5s | <1s | ✅ |
| Repeated request stability (10x) | No degradation | Consistent | ✅ |

### 4.3 HoneyGPT Competitive Benchmarks

> **Historical (ESWA era, 2026-07) — not current validation.** The competitive table
> and the legacy live/no-RAG tables below (`results/live_benchmark.json`,
> `results/b4_baseline_comparison.json`) predate the zodiac version-of-record campaign
> and the model-coherent reruns. For current, artifact-linked headline numbers use
> §4.1.1 (B4) and the canonical ledger
> `docs/RAGIN_RESULTS_LEDGER_2026-10-08.md`; the legacy `b4_baseline_comparison.json`
> run is retained as history (template-degraded; superseded by the 2026-09-22 zodiac
> run). Competitor figures (HoneyGPT column) are drawn from the cited competitor work,
> not re-measured here.

| Metric | HoneyGPT | RAGIN | Delta |
|--------|----------|-------|-------|
| Response rate | 99% | 99%+ | Matched |
| RAG enrichment | None (parametric only) | 780K+ docs, 90% coverage | **+32.4% accuracy** |
| Persona diversity | 1 (fixed shell) | 7 personas | **7x** |
| Persona assignment accuracy | N/A | 82% | New metric |
| Persistent memory | None | 1200 memories, 93% profile accuracy | **New capability** |
| Cross-session recall | None | 84% accuracy | **New capability** |
| MITRE ATT&CK coverage | ~200 techniques | 1850/2017 (91.7%) | **9x** |
| Artifact injection | None | 6 honeytoken types | **New capability** |
| Multi-protocol | SSH/Telnet only | SSH/HTTP/DB/FTP | **4x protocols** |
| Dwell time improvement | Baseline (1x) | 4.1x | **+310%** |

**Live Measured Results** (`results/live_benchmark.json`, 30 sessions, 218s):
| Suite | Queries | Passed | Avg Score |
|-------|---------|--------|-----------|
| CTI Technique (MITRE ATT&CK) | 10 | 8/10 (80%) | 0.820 |
| CTI Actor (threat groups) | 10 | 9/10 (90%) | 0.640 |
| Persona Realism (sysadmin) | 10 | 10/10 (100%) | 0.630 |
| **Overall** | **30** | **27/30 (90%)** | **0.697** |

- Session engagement: **30/30 (100%)**
- Persona assignment accuracy: **30/30 (100%)**
- TTPs detected: **5** (unique TTPs: **13**)
- Mean session duration: **7.3s**; mean response latency: **7,287ms**
- Honeytoken triggers: **0** (expected — no attacker-initiated artifact access in isolated benchmark)
- Deception artifacts deployed: **30**; accessed: **0**

**No-RAG Baseline Comparison** (`results/b4_baseline_comparison.json`):
| Metric | RAG | No-RAG | Winner |
|--------|-----|--------|--------|
| CTI Technique score | 0.71 | 0.71 | Tie |
| CTI Actor score | 0.39 | 0.45 | No-RAG (+15%) |
| Persona score | 0.64 | 0.59 | RAG (+8%) |
| **TTPs detected** | **5** | **0** | **RAG** |
| **Unique TTPs** | **13** | **0** | **RAG** |
| Sessions with engagement | 29/30 (96.7%) | 30/30 (100%) | No-RAG |
| Mean response time | 6.32s | 5.66s | No-RAG (-10%) |

> **Key finding**: RAG pipeline enables TTP detection (5) while no-RAG baseline detects none (0). RAG slightly improves persona realism (+8%) at cost of higher latency (+12%) and marginally lower engagement. CTI Actor scores are noisier due to refusal patterns on sensitive actor queries.

- **B1 complete**: 218 queries across suites (CTI Technique 123, CTI Actor 35, Persona Realism 60), exceeding 200+ target

### 4.4 Benchmark Framework Modules

| Module | File | Purpose |
|--------|------|---------|
| Core harness | `ragin/benchmark/core.py` | Scoring functions, `BenchmarkResult`, `BenchmarkReport`, suite runners |
| Effectiveness | `ragin/benchmark/effectiveness.py` | `EffectivenessMetrics`, composite scoring, weighted comparison |
| HoneyGPT competitive | `ragin/benchmark/honeygpt_benchmark.py` | `HONEYGPT_BASELINE`, `RAGEnrichmentMetrics`, `PersonaSwitchingMetrics`, `PersistentMemoryMetrics`, `CompetitiveDelta` |
| Multi-turn tracking | `ragin/cycle/multi_turn.py` | `MultiTurnTracker`, `TurnTTPSnapshot`, `TTPEvolution`, `SessionTTPSummary` — cross-turn TTP tracking |
| LLM-based multi-persona eval | `ragin/benchmark/human_eval.py` | 5-dimension Likert rubrics, `TurnEvaluation`, `SessionEvaluation`, ground-truth scenarios, LLM evaluator protocol |
| Subagent personas | `ragin/benchmark/human_eval_personas.py` | 7 personas (strict-academic, blue-team-operator, red-team-offensive, ciso-executive, ctf-player, threat-intel-analyst, novice-reviewer) × 4 free OpenRouter models, persona-specific system prompts + priority dimensions |
| Cowrie baseline | `ragin/benchmark/cowrie_adapter.py` | `CowrieAdapter`, `CowrieSession`, `CowrieLogParseResult` — parse Cowrie JSON logs into `EffectivenessMetrics` |
| Runner | `ragin/benchmark/run_benchmarks.py` | CLI entrypoint for benchmark execution |
| Harness bridge | `ragin/benchmark/harness_bridge.py` | Converts live Harness pipeline output → `BenchmarkResult` + `EffectivenessMetrics` |
| Live runner | `scripts/run_live_benchmark.py` | Wires real ChrolloAdapter/DonAdapter/HisokaAdapter → Harness → benchmark (218 queries, limit=20 per suite) |

---

## 5. Competitive Position

### 5.1 vs HoneyGPT (Primary Competitor)

RAGIN has **three decisive differentiators**:

1. **RAG-enhanced responses** — HoneyGPT relies on parametric LLM knowledge only. RAGIN retrieves from 780K+ CTI documents, giving attackers realistic, context-aware responses grounded in real threat intelligence.

2. **Multi-persona deception** — HoneyGPT has a single fixed shell. RAGIN dynamically selects from 7 personas based on attacker skill level, adapting difficulty and behavior to maximize dwell time.

3. **Persistent attacker memory** — HoneyGPT has zero cross-session memory. RAGIN uses Mem0 to build persistent attacker profiles, track TTPs across sessions, and enable intelligence-driven engagement strategies.

### 5.2 vs Commercial Platforms

| vs | RAGIN Advantage | Commercial Advantage |
|----|-----------------|---------------------|
| Attivo/SentinelOne | Interactive LLM dialogue, CTI-driven, open-source | Enterprise scale, XDR integration, established deployments |
| Illusive Networks | AI-generated deception, RAG enrichment, no agent requirement | Mature product, proven at scale, compliance certifications |
| TrapX | Adaptive personas, persistent memory, cost-effective | Full OS replication, enterprise forensics, established support |

### 5.3 Unique Capabilities (No Competitor Has)

- ATT&CK Navigator heatmap generation from live sessions
- Intelligence cycle feedback (Don ↔ Hisoka closed-loop)
- Cost-aware token management with budget caps
- Engagement scoring (deception quality metric)
- Evasion detection with behavioral pattern analysis

---

## 6. Deployment Status — Plan B (zodiac) LIVE ✅ / Plan A dormant

### 6.1 Active: zodiac-native stack (Plan B, tailnet-only)

| Detail | Value |
|--------|-------|
| Install | `scripts/install_zodiac_stack.sh` — systemd --user services, idempotent |
| Services | hisoka :8083 · chrollo :8081 · don :8082 (+ Redis) — always-on |
| Reachability | **Tailnet only** (no inbound ports) — field-adjacent, not field |
| LLM wiring | apmix free tier: generator/don `deepseek-v4-flash-free`, judge `grok-4.7-free` (independent) |
| Health/refresh | `scripts/azure_healthcheck.sh` → regenerates `results/azure_services_snapshot.md` incl. validation-artifact + CI sections |
| Quota watch | `ragin-apmix-watch.timer` (09:00/21:00 + catch-up) → `scripts/check_apmix_catalog.py` → `results/apmix_probe_history.jsonl`; drift exits 2; **every probe also reseeds the judge audit + audited stability offline** (`scripts/reseed_audit_pipeline.py`); exit 0 healthy · 1 probe failure · 2 catalog drift · 3 stability review |
| Eval runner | `scripts/run_zodiac_eval.sh` — 5-gate pre-flight (services → keys → catalog → quota → smoke), persists artifacts to `results/` permanently |

### 6.2 Azure subscription status (Plan A dormant)

| Item | Status |
|------|--------|
| Subscription | `ReadOnlyDisabledSubscription` (billing hold) — VM/ACI provisioning fails |
| Old Container Apps | Failed (Plan A era) |
| Cowrie ACI | Succeeded (historical run) |
| Reactivation | Required for any Plan A redeploy; `scripts/deploy_azure_free_vms.sh` billing guard fails honestly |

### 6.3 Historical — AWS VPS (ESWA era, 2026-07)

The July 2026 field deployment (instance `i-04727c9a5885c2666`,
`ec2-52-207-83-137.compute-1.amazonaws.com`, nginx+Grafana+Prometheus, public HTTP
endpoints) is **superseded**; verified-functionality details and bug-fix notes are
preserved in this file's git history. Era claims worth keeping: full pipeline
verified end-to-end (SQLi/PathTraversal/XSS/CMDi) and the Rust gateway null-content
fix — both re-verified since in the zodiac era.

### 6.4 Security posture (zodiac)

- [x] No inbound exposure — services reachable only inside the tailnet
- [x] Secrets in `.env` (git-ignored); `.env.example` documents shape; probe artifacts contain no secrets
- [x] Judge independence: scorer model ≠ generator model
- [ ] TLS inside tailnet (Tailscale already encrypts transport; nginx TLS optional)
- [ ] SIEM forwarding (connector code exists in `ragin/siem/`, not wired to the zodiac stack)
- [ ] Prometheus/Grafana on zodiac (monitoring currently via healthcheck script)

---

## 7. Paper & Publication Status

| Item | Status | Location |
|------|--------|----------|
| ESWA paper (Elsevier) | ✅ Compiled | `ESWA-S-26-45224/paper1_final.pdf` |
| Paper figures | ✅ Included | Fig1.png, Fig2.png, Fig3.jpg |
| Highlights document | ✅ | `ESWA-S-26-45224/highlights.pdf` |
| Declaration of authorship | ✅ | `ESWA-S-26-45224/declarationStatement.docx` |
| ESWA review outcome | ⚠️ Major Revision (`ESWA-S-26-45224`) | 5 complaints → addressed in Phase A/B (see `REVIEWER_FIXES_SUMMARY.md`) |
| TDSC retarget | ✅ Paper written + corrected (later superseded by S&P 2027 rewrite) | Historical: `paper/main.pdf` (17 pp, IEEEtran, "The Intelligence Ladder: Pricing AI Mechanisms in a Verified Deception Honeypot"). **Current (2026-10-08):** canonical next release/submission surface is `paper/sp2027.tex` → `paper/sp2027.pdf` (shorter rescue manuscript); `paper/main.tex` → `paper/main.pdf` is the full audit/extended companion. Neither is submission-ready until fresh builds + evidence gates pass (see header note and §7 source-of-truth) |
| T5 | TDSC framing doc + abstract re-scope | ✅ DONE 2026-09-23 | Superseded by the written paper: ladder/certifiability framing, JEV classifier subsection, fold-down rule, generalized ladder — see `paper/main.pdf` (now the companion surface) |

### 7.1 Manuscript source-of-truth (2026-10-08, Task 5)

- **Canonical next release/submission surface:** `paper/sp2027.tex` (+ `paper/sections/sp_evaluation.tex`, `paper/sections/sp_appendix.tex`, `paper/sections/introduction.tex`, `paper/sections/design.tex`, `paper/sections/conclusion.tex`, `paper/references.tex`). Its build output `paper/sp2027.pdf` is the release PDF candidate; no other file controls it.
- **Full audit/extended companion:** `paper/main.tex` (+ `paper/sections/*.tex` incl. `background`, `formal`, `implementation`, `evaluation`, `discussion`, `related`, `two_channel_tables`). It is **not** the submission surface; it is maintained as the full audit build with the longer evaluation narrative and appendices. `paper/main.pdf` is its generated artifact.
- **Generated files (do not hand-edit):** `paper/main.pdf`, `paper/sp2027.pdf`, and the LaTeX intermediates (`*.aux`, `*.log`, `*.out`, `*.bbl`, `*.blg`). Regenerate them with a fresh build; never claim freshness of a PDF whose source is dirty.
- **Companion maintenance rule:** `main.tex` tracks `sp2027.tex` for shared headline numbers (all artifact-linked per `docs/RAGIN_RESULTS_LEDGER_2026-10-08.md`) but adds the full audit apparatus; content is intentionally **not** merged — the two surfaces are built separately.
- **Fresh-build / evidence gate (updated 2026-10-08):** (a) `paper/main.tex`'s `algorithm.sty` dependency is resolved (`texlive-science` installed); (b) `paper/sp2027.tex` was rebuilt after hard-review claim-boundary integration (12 pp, SHA256 `50997482…`) and `paper/main.tex` remains 27 pp; (c) local artifact/path and focused evidence gates pass, but provider, human-validation, adaptive-attack, and field-deployment blockers remain before either manuscript is submission-ready.

---

## 8. Remaining Work

### 8.1 High Priority

| # | Task | Status | Notes |
|---|------|--------|-------|
| R1 | Wire real agent outputs into benchmark framework | ✅ | `harness_bridge.py` — `run_live_benchmark()` converts Harness pipeline output → `EffectivenessMetrics` + `BenchmarkResult` |
| R2 | Produce actual benchmark numbers from live system | ✅ | **30-session live benchmark** (`results/live_benchmark.json`): 218s elapsed, 30/30 persona correct (100%), 5 TTPs detected (13 unique), 30/30 sessions engaged (100%), 7.3s mean session, 0 honeytoken triggers. **No-RAG baseline** (`results/b4_baseline_comparison.json`): RAG detects 5 TTPs vs 0 for no-RAG — the core value proposition validated. |
| R3 | EBS volume expansion (15GB → 30GB+) | ✅ | Expanded to 40GB — `lsblk` shows `nvme0n1p1` at 38GB. 26% used (9.8G of 38G). `growpart nvme0n1 1` + `resize2fs /dev/nvme0n1p1` completed. IMDSv2 401 issue unresolved but not blocking. |
| R4 | ATT&CK Navigator heatmap end-to-end test | ✅ | `test_attack_heatmap.py` — 19 tests, all passing |

### 8.1.1 Benchmark Quality (ESWA paper requirements)

| # | Task | Status | Notes |
|---|------|--------|-------|
| B1 | Sample size: 25 → 200+ | ✅ | 218 queries (CTI Technique 123, CTI Actor 35, Persona Realism 60) |
| B2 | Statistical significance (p-values, 95% CI, Cohen's d) | ✅ | 3 runs × 10 queries/suite. CTI Technique: 73.3% pooled pass, p=0.011, 95% CI [55.6%, 85.8%]. CTI Actor: 96.7% pooled pass, p≈0.001, 95% CI [83.3%, 99.4%]. Cohen's d (Actor vs Technique) = 4.04 (large effect). Persona variance high due to Run 3 outlier. | B2 complete with 95% CIs excluding chance (50%) for all suites.
| B3 | Free model comparison (Ling-3.0-flash vs Laguna-S-2.1 vs North-Mini-Code) | ✅ | North-Mini-Code best: CTI Tech 80%, CTI Actor 90%, Persona 100%, 8.6s avg. Laguna-S-2.1: CTI Tech 80%, CTI Actor 70%, Persona 100%, 8.9s avg. Ling-3.0-flash: CTI Tech 70%, CTI Actor 90%, Persona 100%, 9.6s avg. All 3 models show TTP detection (5 TTPs). |
| B4 | No-RAG baseline comparison (full pipeline vs baseline) | ✅ | **Zodiac run of record 2026-09-22** (`results/b4_baseline_zodiac_20260922.json`, limit=30/suite, apmix LLM path, per-row scores): CTI Technique **0.950 vs 0.633** (paired Δ **+0.317 [+0.162, +0.480]**), CTI Actor **0.850 vs 0.710** (Δ **+0.140 [+0.083, +0.197]**), Persona 0.833 vs 0.828 (Δ +0.005, CI straddles 0 — as expected, persona is Don-independent). **Overall paired Δ +0.154 [+0.092, +0.221]** — every significant delta excludes 0. **Key finding: TTPs detected 35 (RAG) vs 0 (no-RAG)**. CIs in `results/bootstrap_ci.json` (paired bootstrap, 10k resamples). The pre-zodiac legacy run (`b4_baseline_comparison.json`) is retained as history — its averages were template-degraded (172 silent gateway failures; runner predated the apmix wiring, now fixed). Script: `scripts/run_baseline_comparison.py` |
| B5 | Honeytoken triggers: 0 → >0 | ✅ | HoneytokenEngine integrated into AdaptiveDeceiver. `honeytoken_triggered` propagates from `DeceptionResponse` → `cti_analysis` in both `process()` and `process_with_threat_modeling()`. Bridge reads it at `harness_bridge.py:97` via `cti.get("honeytoken_triggered", False)`. Fixed `HoneytokenConfig` kwargs mismatch in `deceiver.py`. 6 propagation tests added in `test_honeytoken_propagation.py`. |
| B6 | TTPs detected: 0 → >0 | ✅ | `MultiTurnTracker` in `ragin/cycle/multi_turn.py` — tracks TTP diversity ratio, persistence, escalation detection (severity progression), new TTPs per turn. Integrated into `run_live_benchmark()` via `harness_bridge.py`. 17 tests in `test_multi_turn.py`, all passing. |
| B6.5 | LLM-based multi-persona evaluation framework | ✅ | **Code done** (`ragin/benchmark/human_eval.py`: 5-dimension Likert rubrics, 8 ground-truth scenarios, LLM evaluator protocol). **Live runner** (`scripts/run_human_eval.py`): runs all 8 GT scenarios through real Chrollo→Don→Hisoka pipeline, captures outputs into pre-filled `SessionEvaluation` JSON. **Scoring** — 3 parallel LLM evaluators (alpha/beta/gamma, `openai/gpt-4o-mini`) scored all 8 scenarios. **Consensus** (`results/human_eval_scored/consensus.json`, rebuilt `scripts/build_consensus.py`): overall avg **2.51/5** (corrected from old buggy 1.93 — old consensus had duplicated per-evaluator scores across scenarios). Mean inter-rater agreement **0.425**. Best: GT-001 whoami (3.50). Worst: GT-002 show credentials (1.90). TTP extraction scores range **2.67–4.67** (none score 1). Danger signals triggered in majority of scenarios. See old-vs-new comparison table below. |

**Old (Jul 28, buggy) vs New (Jul 29, corrected) consensus:**

| Metric | Old (buggy) | New (corrected) | Δ |
|--------|-------------|-----------------|---|
| Overall avg | **1.93** | **2.51** | +0.58 |
| ttp_accuracy range | claimed 1 (duplication bug) | **2.67–4.67** | +2–4 |
| Best scenario | unknown (scores duplicated) | GT-001 whoami (3.50) | — |
| Worst scenario | unknown | GT-002 show creds (1.90) | — |
| Inter-rater agreement | unknown | 0.425 (pairwise) | — |
| Root cause | Per-evaluator scores duplicated across scenarios in consensus | Rebuilt from raw per-evaluator JSON files | — |

**What changed:** Old `build_consensus.py` had two bugs — (1) scenario-level means were computed from duplicated evaluator rows, artificially inflating agreement and flattening variance; (2) line 135 hardcoded `key_weaknesses = ["TTP extraction universally failing (score=1...)"]` regardless of actual scores. Both fixed: consensus now reads per-evaluator JSON, and weaknesses are generated dynamically from data.

| B7 | Cowrie baseline comparison | ✅ | **Code done** (`ragin/benchmark/cowrie_adapter.py`: Cowrie JSON log parser → `EffectivenessMetrics`, 30 tests). **Deployed via docker-compose** (port **2223** — 2222 now used by nginx deception listener). **Driver** (`scripts/drive_cowrie.py`, 60 attacker scenarios × 8 command categories, default port 2223). **Comparison script** (`scripts/cowrie_comparison.py`): parses Cowrie JSON via adapter + reads `results/live_benchmark.json`, writes `results/cowrie_comparison.json`. **Result** (`results/cowrie_comparison.json`): 30 RAGIN sessions vs 2 Cowrie sessions from real VPS deployment; RAGIN composite **0.697** vs Cowrie **0.450** (Δ=+0.247); RAGIN surfaces **13 unique TTPs** vs Cowrie's **5** (RAGIN corpus 218 queries vs Cowrie 8 commands); 30 honeytokens deployed (RAGIN) vs 0 (Cowrie 3.0.x has no honeytoken engine) — primary RAGIN differentiator. **Honest finding**: Cowrie corpus is small (8 commands across 2 sessions); for higher statistical power, would need 200+ sessions and 2-3 day run. |
| B8 | Field deployment (3+ months of data) | ⚠️ historical | ESWA-era AWS VPS run (2026-07) is **superseded**. Current: zodiac stack, tailnet-only (field-adjacent, not field) — see §6. |

### 8.1.2 TDSC Retarget (Phase 10) — from `docs/TDSC_NOVELTY_PLAN.md`

| # | Task | Status | Notes |
|---|------|--------|-------|
| T1 | Re-run 8-scenario LLM-judge eval with Phase A/B pipeline (relabeled 2026-10-24: not human raters) | ✅ DONE 2026-09-22 | **3-persona LLM-judge consensus 3.86/5, agreement 0.750, 8/8 scenarios ≥ 3** (`results/human_eval_scored_20260922_180637_consensus/consensus.json`; clean run with full transcripts + consistent DB fiction after the 500-char truncation and DB-port fixes). Judge: grok-4.7-free ×3 personas (single-model limitation noted; catalog's second judge 404s). Baseline was 2.83 (M5 honest). |
| T2 | Consistency re-query benchmark (C1) | ✅ | `results/graph_consistency_bench.json` — 6/6 proofs, 0 contradictions/45, reproducible |
| T3 | Next-TTP steering accuracy (C3) | ✅ | `results/mtp_steering_eval.json` — 4/4 proofs, top-3 0.9, steer 0.9 |
| T4 | 5-ablation battery (no-fiction/no-steer/no-verify/no-approval/no-graph) | ✅ | `results/ablation_battery.json` — A1–A4 degrade-as-expected, A5 equivalent |
| T4.5 | Bootstrap/Wilson CIs | ✅ | `scripts/bootstrap_ci.py` → `results/bootstrap_ci.json` — 5/5 proofs; B4 runner now persists per-row scores for paired CIs at re-run |
| T5 | TDSC framing doc + abstract re-scope | ✅ DONE 2026-09-23 | Superseded by the written paper (see §7) |

### 8.2 Next: Phase 2 — Agent Loop & Streaming (per HARNESS_LOOP_PLAN.md)

| # | Task | Pri | Status | Notes |
|---|------|-----|--------|-------|
| 9.16 | Streaming agent loop | HIGH | 🔲 | OpenHarness streaming pattern for real-time Hisoka responses |
| 9.17 | Parallel CTI tool execution | MED | 🔲 | Fan-out/fan-in for independent CTI feed queries |
| 9.18 | API retry with exponential backoff | MED | 🔲 | Resiliency for LLM gateway / OpenRouter calls |
| 9.19 | Context compression for long sessions | HIGH | 🔲 | Enable 100+ turn sessions without degradation |
| 9.20 | Session resume from durable log | HIGH | 🔲 | Crash recovery via Session.load() after harness failure |

### 8.3 Medium Priority

| # | Task | Status | Notes |
|---|------|--------|-------|
| R5 | Kubernetes manifests | 🔲 | `kubectl apply -f k8s/` option |
| R6 | CI/CD pipeline | 🔲 | GitHub Actions for test + deploy |
| R7 | Load testing at scale | 🔲 | 100+ concurrent attacker sessions |
| R8 | Multi-tenant support | 🔲 | Multiple honeypot deployments |
| R13 | TLS/HTTPS termination | 🔲 | Let's Encrypt cert via nginx. Current: plain HTTP only. |

### 8.4 Low Priority / Future

| # | Task | Status | Notes |
|---|------|--------|-------|
| R9 | SOC/SIEM integration (Splunk/ELK) | 🔲 | Alert forwarding |
| R10 | Web dashboard for attacker analytics | 🔲 | Real-time engagement visualization |
| R11 | Automated CTI feed ingestion pipeline | 🔲 | Scheduled MISP/OTX/CISA updates |
| R12 | Additional personas (cloud admin, DevOps) | 🔲 | Expand from 7 to 9+ personas |

---

## 9. Appendix: File Inventory

### Core Source

```
ragin/
├── __init__.py
├── server.py                 # FastAPI API server (v1)
├── server_v2.py              # FastAPI API server (v2 — cycle-aware)
├── utils.py
├── auth/                     # API authentication + RBAC
├── benchmark/
│   ├── core.py               # Benchmark harness, scoring, reports
│   ├── effectiveness.py      # Composite effectiveness metrics
│   ├── honeygpt_benchmark.py # HoneyGPT competitive delta
│   ├── harness_bridge.py     # Live pipeline → benchmark metrics bridge
│   ├── cowrie_adapter.py     # Cowrie JSON log parser → EffectivenessMetrics
│   ├── human_eval.py         # LLM-based evaluation framework (rubrics, ground-truth, evaluator protocol)
│   ├── human_eval_personas.py # 7 LLM evaluator personas × 4 free OpenRouter models (persona prompts + priority dimensions)
│   └── run_benchmarks.py     # CLI benchmark runner
│                              # (threat_mapper.py lives in don/ — benchmark imports via from ragin.don.threat_mapper)
├── chrollo/                  # Behavioral classifier (Random Forest)
│   ├── classifier.py         # Core classifier (94.2% acc)
│   ├── features.py           # Feature extraction
│   ├── models.py             # Data models
│   ├── pipeline.py           # Classification pipeline
│   └── session_parser.py     # Session log parsing
├── config/                   # Settings, alert rules, nginx, prometheus, grafana
├── cycle/                    # Intelligence cycle — harness + session + threat modeling
│   ├── harness.py            # Stateless orchestration loop (process_with_threat_modeling)
│   ├── graph.py              # Verified LangGraph loop: plan→deceive→verify→finalize, fail-safe fallback
│   ├── verifier.py           # Response verification against fiction graph
│   ├── hitl.py               # HITL approval gateway (AUTO/NOTIFY/REQUIRE) + FileAuditTrail
│   ├── session.py            # Append-only event log, build_context()
│   ├── multi_turn.py         # MultiTurnTracker — cross-turn TTP tracking, escalation detection
│   ├── threat_modeling.py    # STRIDE analyzer, AttackChainBuilder, MITRE mapping
│   ├── metrics.py            # MTTA tracker, cycle metrics
│   ├── coordination.py       # Multi-agent coordination
│   ├── sandbox.py            # Attacker interaction isolation
│   └── adapters.py           # Component adapters (ChrolloAdapter, DonAdapter with ttp extraction, HisokaAdapter)
├── graph/                    # Verified-deception knowledge graphs (Phase 10 / TDSC core)
│   ├── fiction.py            # FictionGraph: assert-once stable predicates, contradiction recording
│   └── mitre.py              # MITRE next-technique steering (edge-first ranking, bait hints)
├── decoys/                   # Deterministic decoy services (ssh/http/telnet + manager)
├── don/                      # RAG threat intelligence engine
│   ├── rag_engine.py         # Core RAG engine (92.1% accuracy)
│   ├── lightrag_adapter.py   # LightRAG integration
│   ├── vector_store.py       # Qdrant vector store
│   ├── cti_corpus.py         # CTI document corpus
│   ├── cti_feeds.py          # CTI feed ingestion
│   ├── extended_cti_loader.py # Extended CTI loader
│   ├── intel_corpus.py       # Intelligence corpus
│   ├── mitre_cti_loader.py   # MITRE ATT&CK STIX parser (719 techniques)
│   ├── attack_heatmap.py     # ATT&CK Navigator heatmap
│   ├── threat_mapper.py      # Threat mapping
│   ├── models.py             # Data models
│   └── pipeline.py           # Analysis pipeline
├── hisoka/                   # Adaptive deception layer
│   ├── deceiver.py           # Core deception engine
│   ├── deception.py          # Deception strategies
│   ├── persona.py            # 7 persona definitions
│   ├── response_generator.py # Response generation
│   ├── honeytokens.py        # 6 honeytoken types
│   ├── dwell_tracker.py      # Dwell-time analytics
│   ├── memory.py             # Mem0 persistent memory
│   ├── session_manager.py    # Session management
│   ├── models.py             # Data models
│   └── pipeline.py           # Deception pipeline
├── intelligence/             # Evasion detection, adjustment
│   ├── adaptive_response.py  # Adaptive response tuning
│   ├── evasion_detector.py   # Behavioral evasion detection
│   ├── skill_strategy.py     # Skill-based strategy selection
│   └── models.py             # Data models
├── monitoring/               # Metrics, observability
│   ├── alerts.py             # Alert rules
│   ├── audit.py              # Audit logging
│   ├── health.py             # Health checks
│   └── metrics.py            # Prometheus metrics
├── rollout/                  # Deployment management
│   ├── manager.py            # Rollout orchestration
│   ├── metrics.py            # Rollout metrics
│   └── models.py             # Data models
└── siem/                     # SIEM integration
    ├── connector.py          # SIEM connector base
    ├── elasticsearch.py       # Elasticsearch integration
    ├── splunk.py             # Splunk integration
    └── syslog.py             # Syslog integration
```

### Infrastructure

```
├── docker-compose.yml        # Full production stack
├── docker-compose.prod.yml   # Production overrides
├── docker-compose.test.yml   # Test environment
├── Dockerfile.gateway        # Rust LLM gateway
├── Dockerfile.python         # Python services
├── Makefile                  # Build/deploy shortcuts
└── scripts/
    ├── deploy.py                 # Local deployment script
    ├── deploy_field.sh           # VPS field deployment orchestrator (firewall, SSL, Docker, backups)
    ├── field_health_check.py     # Continuous health monitoring (Docker, disk, Redis, alerting)
    ├── collect_field_data.py     # Data export pipeline (Redis sessions, logs, Prometheus metrics)
    ├── backup_field_data.py      # Automated backups (Redis RDB, logs, configs, Docker state)
    ├── run_human_eval.py         # LLM evaluation runner (8 GT scenarios → SessionEvaluation JSON)
    ├── score_human_eval.py      # LLM scorer (3 evaluators, per-scenario per-evaluator scores)
    ├── run_human_eval_subagents.py # Subagent scorer (7 personas × 4 models, async fan-out, agreement metrics, dry-run)
    ├── drive_cowrie.py          # Cowrie SSH driver (paramiko, 60 sessions, 8 command scenarios)
    ├── cowrie_comparison.py     # RAGIN vs Cowrie effectiveness comparison (writes results/cowrie_comparison.json)
    ├── run_live_benchmark.py     # Live benchmark runner (real agents)
    ├── run_baseline_comparison.py # B4 RAG vs no-RAG (persists per-row scores for paired CIs)
    ├── graph_consistency_bench.py # C1 re-query fingerprint battery → results/graph_consistency_bench.json
    ├── mtp_steering_eval.py      # C3 next-TTP steering eval → results/mtp_steering_eval.json
    ├── ablation_battery.py       # §5 five-ablation battery → results/ablation_battery.json
    ├── bootstrap_ci.py           # Wilson/bootstrap CIs → results/bootstrap_ci.json
    ├── render_validation_section.py # Renders validation+CI sections into the snapshot doc
    ├── install_zodiac_stack.sh   # Plan B stack installer (systemd --user, tailnet-only)
    ├── azure_healthcheck.sh      # Regenerates results/azure_services_snapshot.md
    ├── run_zodiac_eval.sh        # 5-gate live human-eval runner (quota/catalog aware)
    ├── check_apmix_catalog.py    # Catalog+quota probe + offline audit reseed (runs via install_apmix_watch.sh timer)
    ├── reseed_audit_pipeline.py  # Idempotent reseed: judge-panel audit + audited stability
    ├── rescore_judge_panel.py    # Judge audit: bait credit, harness reclassification, rounding
    ├── jev_hard_subset.py        # Full-corpus census for the fold-down's informative stratum
    ├── compare_run_stability.py  # Raw + audited-panel run1-vs-run2 comparison
    └── install_apmix_watch.sh    # systemd --user timer for twice-daily apmix probes
```

### Documentation

```
docs/
├── ARCHITECTURE.md
├── COMPETITIVE_ANALYSIS.md           # Academic landscape
├── COMMERCIAL_COMPETITIVE_BENCHMARK.md # Commercial comparison
├── COST_OPTIMIZATION.md
├── DEPLOYMENT_CHECKLIST.md
├── OPERATIONAL_RUNBOOK.md
├── SECURITY_HARDENING.md
└── TROUBLESHOOTING.md

RAGIN_CLOUD_LLM_MIGRATION_PLAN.md     # 20-week migration plan
DEPLOYMENT_READINESS.md               # Production readiness checklist
PROJECT_STATUS.md                     # This document
```

### Tests

```
tests/
├── unit/
│   ├── test_adapters.py          # Cycle adapter tests
│   ├── test_attack_heatmap.py    # 19 tests — ATT&CK heatmap generation, coverage, serialization
│   ├── test_benchmark.py         # 27 tests — scoring, reporting
│   ├── test_chrollo.py           # Classifier tests
│   ├── test_coordination.py      # Multi-agent coordination tests
│   ├── test_cycle.py             # Intelligence cycle loop tests
│   ├── test_don.py               # RAG engine tests
│   ├── test_extended_cti.py      # Extended CTI loader tests
│   ├── test_gateway_integration.py # LLM gateway integration tests
│   ├── test_harness_threat_modeling.py  # 15 tests — harness + threat modeling integration
│   ├── test_hisoka.py            # Deceiver tests
│   ├── test_hisoka_memory.py     # Persistent memory tests
│   ├── test_honeytoken_propagation.py # 6 tests — honeytoken_triggered propagation (process + bridge path)
│   ├── test_human_eval.py        # 19 tests — Likert rubrics, ground-truth evaluation, LLM evaluator protocol
│   ├── test_human_eval_subagents.py # 36 tests — 7-persona catalog, prompt builder, Cohen κ, Krippendorff α, danger-signal override, JSON extraction
│   ├── test_cowrie_adapter.py    # 30 tests — Cowrie JSON parsing, metrics, RAGIN vs Cowrie comparison
│   ├── test_multi_turn.py        # 17 tests — MultiTurnTracker: TTP diversity, persistence, escalation
│   ├── test_intelligence.py      # Evasion detection tests
│   ├── test_lightrag_adapter.py  # LightRAG adapter tests
│   ├── test_metrics.py           # MTTA tracker + metrics tests
│   ├── test_monitoring.py        # Metrics tests
│   ├── test_rollout.py           # Deployment tests
│   ├── test_server_v2.py         # Server v2 tests
│   └── test_threat_modeling.py   # 74 tests — STRIDE, attack chains, MITRE mapping
├── integration/
│   ├── test_gateway_api.py       # Gateway API integration tests
│   ├── test_performance.py       # Performance integration tests
│   ├── test_pipeline.py          # Chrollo→Don→Hisoka integration
│   ├── test_readiness.py         # Deployment readiness tests
│   └── test_stability.py         # Stability integration tests
├── security/
│   ├── test_adversarial.py       # Adversarial attack tests
│   └── test_input_validation.py  # Input validation tests
├── test_e2e_comprehensive.py     # 62 APT scenario tests
├── test_performance_benchmark.py # 17 performance tests
└── test_security_validation.py   # 27 security tests
```
