# Goldfish Codebase-Details Review — RAGIN paper `main.tex`, DetailedRange lines 1125–2144

**Scope:** `paper/main.tex` lines 1125–2144 (Implementation Details, Results, Discussion, back matter). **Codebase:** `RAGIN-Retrieval-Augmented-Honeypot-Intelligence/` (REPO below).
**Preliminary note:** `results/field_attack_v3/` is empty except an empty `claude_brain_supplementary/` subfolder. All actual evidence lives under `REPO/results/`.

## PART 1 — CLAIM-BY-CLAIM VERIFICATION (summary)

### Implementation Details (lines 1125–1238)
- **A1 Chrollo RF @ models/chrollo/rf_classifier.joblib, 4 skill levels** — VERIFIED (`ragin/chrollo/classifier.py:1,25,124,212-227`)
- **A2 10 features, 6 behavioral + 4 structural** — VERIFIED (`ragin/chrollo/features.py:43-56`)
- **A3 Z-score normalization** — VERIFIED (`classifier.py:16,93,153,168`)
- **A4 kNN imputation (k=5)** — MISMATCH. Zero `KNNImputer/SimpleImputer/n_neighbors` hits anywhere; features always emit floats (clamped zero-fill, `features.py:61-120`). Machinery documented but nonexistent.
- **A5 Don FAISS+BM25 hybrid, threat mapper, evidence citations** — VERIFIED (`ragin/don/rag_engine.py:751`, `vector_store.py:43-51`, `threat_mapper.py`)
- **A6 Fusion weights α=0.7/β=0.3** — MISMATCH (partial). Live call site passes alpha=0.7 (`rag_engine.py:450`) but canonical default is alpha=0.25 with docstring "empirical optimum ≈0.15–0.25" (`rag_engine.py:751-756`); `lightrag_adapter.py:264` defaults to 0.7. Internal inconsistency.
- **A7 FAISS HNSW (repeated line 1917)** — MISMATCH. `vector_store.py:51` uses `IndexFlatIP` (flat inner product); no HNSW anywhere.
- **A8 Corpus poisoning screening "in the repository"** — VERIFIED weakly (`rag_engine.py:93,729`, `don/pipeline.py:149`)
- **A9 OpenRouter gateway, temp low, output cap** — VERIFIED (`config/settings.yaml:4-6`, `gateway/client.py:374` temp 0.3, `don/models.py:194`). Nit: base URL is `api.tokenrouter.com`, pinned model `moonshotai/kimi-k3-free` — paper never pins it.
- **A10 Hisoka PersonaManager/ResponseGenerator/ArtifactInjector/EngagementTracker + Redis TTL** — VERIFIED (`ragin/hisoka/*`, `session_manager.py:24-28`)
- **A11 Mem0 memory layer, mem0ai>=0.1.0** — VERIFIED (`hisoka/memory.py:1,27`, `pyproject.toml:17`, mocked tests)
- **A12 Mem0 30-day idle-window aging** — MISMATCH. No idle-window/TTL config anywhere; only `retention_days: 90` for cost-tracking (`settings.yaml:207`).
- **A13 Stack: Cowrie Docker, Python 3.11, Redis, Prometheus** — VERIFIED with nit: `pyproject.toml:4` says >=3.10; tree artifacts are 3.12.

### Live Benchmark (1243–1347)
- **B1 218 queries/30 sessions, 123/35/60 suites, 91.9%/100%/18.3% content-pass, 13.0/5.7/3.3 quality-pass, 10.1% overall, 22/2/5/189 classes, 160.6s, 82/31 TTPs** — VERIFIED, but against `REPO/results/live_benchmark_audited.json`, NOT the file the paper cites. Every number reproduces to the digit.
- **B2 Attribution to `results/live_benchmark.json` (lines 1247, 1272, 2018)** — 🔴 MISMATCH. That file holds a DIFFERENT experiment: 30 queries/30 one-turn sessions, 7.29s mean, 5 TTPs. Data Availability says "261 queries" — the file holds 30.
- **B3 Tactic table `tab:tactics` per-row distribution** — UNVERIFIABLE. Endpoint totals verified (31 vs 5 via `cowrie_comparison.json`); no artifact generates per-tactic rows.

### Operational Campaign (1349–1409)
- **C1 261 queries, 44 auth, dwell 12,636/13,290/9,366–21,021 ms, 10+10+10, 2 external attackers** — UNVERIFIABLE as data. Numbers exist only in `RESPONSE_LETTER_ESWA-S-26-45224.md:200-234`. No JSON/JSONL artifact contains them. `REPO/results/ALL_RESULTS_VS_ESWA_PAPER.md:29` itself flags this axis "Paper leads here ❌ (re-deployment pending)".

### Ablation (1411–1479)
- **D1 Arm-C results + `results/rag_prompt_controlled_ablation.json`** — UNVERIFIABLE / artifact missing (`find -name "*prompt_controlled*"` = nothing). TTP counts corroborated by response-letter prose only.
- **D2 RAG arm 5 TTPs/13 unique** — VERIFIED (`live_benchmark.json` metrics, `cowrie_comparison.json`).

### Cowrie head-to-head (1481–1530)
- **E1 Paper: Cowrie n=6, engagement 33.3%, composite 0.317, Δ+0.380** — 🔴 MISMATCH. Committed `cowrie_comparison.json`: n=2, engagement 1.0, composite 0.45, Δ+0.247. Only the RAGIN side matches. The 6-session update is described in `REVIEWER_FIXES_SUMMARY.md:89-118` but was never written into the JSON.
- **E2 CI [+0.04,+0.71], seed 42, via `scripts/bootstrap_cowrie_ci.py`** — MISMATCH. Script does not exist; `scripts/bootstrap_ci.py` uses seed 20260922 on a different quantity; no artifact carries the interval.

### LLM-Panel (1532–1599)
- **F1 Consensus 2.51/5, κ=0.425, Table `tab:panel` rows** — 🔴 MISMATCH. Cited `human_eval_scored/consensus.json` computes to 1.913 with different rows, carries "PROVENANCE CORRECTION 2026-10-24" and `CORRECTION.md` saying "Do not cite this directory" (0/14 rows match evaluators). The corrected 2.51/0.425 rebuild documented in `PROJECT_STATUS.md:485-499` is NOT on disk.
- **F2 Pilot 1.91/5 κ≈0.725 "smaller judge pool"** — MISMATCH: same 3 evaluators (alpha/beta/gamma) both runs; 1.91 is the older run, not a smaller pilot.
- **F3 7 evaluation roles "novice/intermediate/expert/apt + 3 persona variants"** — MISMATCH: actual evaluator personas are defender/reviewer roles (blue-team-operator, ciso-executive, ctf-player, novice-reviewer, red-team-offensive, strict-academic, threat-intel-analyst).
- **F4 Bias-corrected 2.83** — VERIFIED with caveat (`human_eval_scored_v2/consensus.json` = 2.83; recomputed 4-dim = 2.844) but it is a different judge run (qwen-38-27b), not "the same run minus one dimension" as framed.
- **F5 Deterministic 4.2/5, aggregate 3.06/5, script `scripts/deterministic_artifact_safety.py`** — UNVERIFIABLE + arithmetic inconsistency: script missing; (4×2.83+4.2)/5 = 3.104 ≠ 3.06.

### Red team / persona battery (1601–1727)
- **G1 Engagement RAGIN-RE-20260730, tells (301/169-byte, 0.003s, 2222, static 401), novice ~3 turns, advanced ~7** — VERIFIED (`attacker_report.md`, `attacker_log.jsonl`)
- **G2 `results/redteam_personas.json`, dwell 11.7/39.3/63.4s, uname continuity** — UNVERIFIABLE / artifact missing; response-letter prose only.

### Reliability / back matter (1729–2144)
- **H1 1,098 tests passed / 12 skipped** — VERIFIED (dated snapshot 2026-07-29; current suite 1,285 — date-stamp needed)
- **H2 PII: HMAC-SHA256 per-deployment key + 16-bit per-record salt in `ragin/gateway/pii_redactor.py`; no cleartext IPs** — 🔴 MISMATCH. File does not exist. Actual: `ragin/utils.py:20-32` = plain SHA-256(ip + static salt) with hardcoded committed default salt `"ragin-ip-v1"`. Cleartext attacker IPs appear in committed docs (e.g., REVIEWER_FIXES_SUMMARY.md, response letter).
- **H3 Rust gateway circuit breaker** — VERIFIED (`llm-gateway/src/config.rs:12`, `metrics.rs:38`)
- **H4 Defense layer: token bucket, budget caps, scanner matcher, LRU cache** — VERIFIED
- **H5 Designed 2,650ms budget vs live 160.6s** — VERIFIED (`docs/VPS_LOCAL_WORK_SUMMARY.md:161`, audited file)
- **H6 Corpus 780,600 docs** — UNVERIFIABLE. Only in self-referential review docs; on-disk LightRAG store = 75,151 docs, corpus ~25MB.
- **H7/H8 GitHub + Zenodo DOI, Apache-2.0** — VERIFIED (external)

## PART 2 — FINDINGS BY PRIORITY

- **F-1 🔴** Benchmark numbers attributed to the wrong artifact (`main.tex:1247,1272,2018-2019` vs `live_benchmark.json` holding a different 30-query run). Fix: re-point to `live_benchmark_audited.json`/`live_benchmark_full.json`.
- **F-2 🔴** Cowrie table contradicts its cited artifact (n=6/0.317/Δ+0.380 in paper; n=2/0.45/Δ+0.247 on disk).
- **F-3 🔴** LLM-panel headline 2.51/κ=0.425 not re-derivable; cited artifact self-repudiates ("Do not cite this directory"); corrected rebuild not committed; role taxonomy misdescribed; 4.2/3.06 arithmetic doesn't close.
- **F-4 🔴** PII-hashing spec describes code that does not exist; actual is plain SHA-256 with committed static salt; cleartext IPs in committed docs.
- **F-5 🟡** Four claimed reproduction paths broken (missing `rag_prompt_controlled_ablation.json`, `redteam_personas.json`, `bootstrap_cowrie_ci.py`, `deterministic_artifact_safety.py`).
- **F-6 🟡** kNN imputation (k=5) claimed; no imputer exists.
- **F-7 🟡** Mem0 30-day idle window not implemented.
- **F-8 🟡** FAISS HNSW mischaracterization (code uses IndexFlatIP) + α=0.7/β=0.3 weight instability.
- **F-9 🟡** Campaign KPIs (261 queries, dwell stats, egress mix) have no data artifact; repo itself flags "re-deployment pending".
- **F-10 🟡** Tactic table `tab:tactics` per-row distribution has no generating artifact.
- **F-11 🟢** Corpus 780,600 docs no artifact backing (on-disk 75,151).
- **F-12 🟢** "Python 3.11" vs pyproject >=3.10 / tree 3.12.
- **F-13 🟢** Model `moonshotai/kimi-k3-free` via tokenrouter proxy unpinned in paper.
- **F-14 🟢** Test-count snapshot 2026-07-29 (1,098) vs current 1,285 — date-stamp.
- **F-15 🟢** Content-pass numbers reproduce from audited rows, not the pre-audit `live_benchmark_full.json` — one clarifying sentence needed.

## VERIFICATION SCORECARD

| Verdict | Count |
|---|---|
| VERIFIED | 16 claim clusters |
| MISMATCH | 7 (4 Blocker-level) |
| UNVERIFIABLE | 6 |

**Findings: 🔴 4 (F-1…F-4) · 🟡 7 (F-5…F-10 + A6) · 🟢 5 (F-11…F-15)**

**Overall:** The quantitative core of the benchmark section is impressively reproducible — every number in Table `tab:benchmark` re-derives to the digit from `live_benchmark_audited.json`, and Chrollo/Hisoka/gateway implementation claims match the code closely. The Blockers are provenance failures, not arithmetic ones: the paper cites the wrong file, cites files/scripts never committed, and headlines a panel score whose on-disk artifact self-declares corrupted and computes to 1.91. Fix is mechanical but mandatory before submission: re-point every artifact path, commit the missing JSON/scripts (or delete references), correct the PII spec to match `utils.py`, and either commit or retract the 2.51 consensus rebuild.
