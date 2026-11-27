# RAGIN Code Audit — 2026-09-15

Scope: `ragin/` (21,426 LOC, 80 modules), `tests/` (1,111 tests), `models/`, `results/`, config.
Verification: venv with core deps; full pytest run; ruff; bandit; model artifact inspection.

## Test status

| Suite | Before fixes | After fixes |
|---|---|---|
| Full suite (1,111 tests) | 973 passed / **32 failed** / 106 skipped | **995 passed / 0 failed** / 116 skipped |
| ruff (ragin/) | 1 error | **clean** |
| bandit (-ll) | 7 medium findings | addressed or documented (S-4..S-6) |

Remaining 63 ruff findings are pre-existing style debt in `tests/` only (PT011 broad raises, B017, F841, N801, B007) — no production impact.

Failures decompose exactly:
- 20 × `test_hisoka_memory.py` — `ModuleNotFoundError: mem0` (dep declared in pyproject but not installed in audit env)
- 9 × `test_gateway_api.py` — e2e tests hit `localhost:8080` unconditionally; **Burp Suite was listening** on this machine and returned HTML → cryptic JSON decode failures. No reachability/skip guard.
- 3 × `test_readiness.py` — `.env.example` lacks `OPENROUTER_API_KEY`, `API_KEY`, `GRAFANA_ADMIN_PASSWORD` (only `RAGIN_API_KEY`, which nothing in Python reads).

## A. Paper-vs-artifact integrity findings (highest severity)

**A1. "150 behavioral features" is false against code, model, and data — it is 10.**
- `ragin/chrollo/features.py`: `FEATURE_NAMES` = exactly 10 features.
- Shipped model `models/chrollo/rf_classifier.joblib`: `n_features_in_ = 10` (scaler too).
- `results/human_eval_full.json`: every `features_used` lists the same 10 names.
- The paper claimed "150 behavioral features in 5 categories" (9 places) with a fabricated category-count table. Corrected to 10 features / 2 families, with the table rebuilt from `FEATURE_NAMES`.

**A2. Shipped classifier is single-class: `classes_ = [3]` (APT only).**
- `predict()` always returns 3 → every session is classified "apt" with `predict_proba` confidence ≈ 1.0.
- The "skill-stratification" component cannot stratify with this artifact. Retraining is out of scope here; the honest fix is a load-time warning + README note, not a fabricated multi-class model.
- **RESOLVED (follow-up session):** retrained on a newly generated synthetic four-tier dataset — see "A2 resolution" below.

**A3.** (fixed earlier in paper) phantom artifact citations; persona count 7 → 5.

## B. Security findings

**S-1. Auth header mismatch — GatewayClient can never authenticate to RAGIN's own server.**
- Servers (`server.py:240`, `server_v2.py:62`) check `X-API-Key`.
- `GatewayClient` sends only `Authorization: Bearer`.
- Any internal component pointed at the RAGIN gateway with `API_KEY` set gets 401. Fix: send both headers.

**S-2. `.env.example` documents `RAGIN_API_KEY`, which no Python code reads; missing the 3 vars the readiness test requires.**

**S-3. E2E tests have no skip guard** — they fail confusingly when the port is occupied by an unrelated service (observed: Burp).

**S-4. `0.0.0.0` binds**: `server.py:682`, `server_v2.py:458` (management API — should default to loopback), `decoys/base.py:30` (decoy listener — intentional, keep).

**S-5. CTI loaders `urlopen()` URLs without scheme validation** (`mitre_cti_loader.py:42`, `extended_cti_loader.py:301`) — SSRF-adjacent; validate https.

**S-6. `hash_ip()` uses a hardcoded static salt** (`ragin-ip-v1`) — offline brute-force of small IP space is trivial. Allow secret via env, keep default for reproducibility.

**S-7. bandit B108 `/tmp/deploy` in honeytoken decoy paths — false positive (decoy string, not a real temp path). No action.**

## C. Functional bugs

**F-1. BM25 index is never built in production.** `_build_index()` is called only from tests; `ThreatRAGEngine.__init__` loads the corpus + vector store but never indexes documents → `keyword_search()` and the keyword half of `hybrid_search()` always return []. The "hybrid RAG" is vector-only in practice. Fix: build the index from the loaded corpus at init.

**F-2. `analyze()` discards the built LLM context.** `self._build_context(intel_hits)` result is unused; `generate_report()` never sees the retrieved intel documents either — the R in RAG never reaches the LLM in this path. Fix: thread intel context into `generate_report`.

**F-3. `PersonaManager.select` docstring says four personas; there are five** (`advanced` missing) — paper was already corrected to five; docstring now matches.

**F-4. `CostTracker._compute_cost` annotated `tuple | float` but returns float only** — cosmetic.

**F-5. Startup never warns when `API_KEY` is unset** (auth silently disabled in prod posture). Fix: one warning at boot.

## Fix plan applied (this commit)

1. `.env.example`: add `OPENROUTER_API_KEY`, `API_KEY`, `GRAFANA_ADMIN_PASSWORD` (keeps `RAGIN_API_KEY` as nginx alias).
2. `GatewayClient`: send `X-API-Key` alongside `Authorization: Bearer`.
3. `test_gateway_api.py`: module-level skip when `/health` not reachable.
4. `server.py` / `server_v2.py`: bind via `RAGIN_BIND_HOST` (default `127.0.0.1`), warn when `API_KEY` empty.
5. CTI loaders: https-only scheme check.
6. `rag_engine.py`: build BM25 index from corpus at init; pass intel context into `generate_report`.
7. `deception.py`: docstring five personas; `hash_ip` salt override via `RAGIN_IP_SALT`.
8. `classifier.py`: loud warning when a single-class model is loaded.
9. `utils.py`: `_compute_cost` annotation.
10. Paper (`../paper/main.tex`): all "150-feature" claims corrected to 10 (feature table rebuilt from `features.py`); 100-tree → 200-tree per shipped model.

## D. A2 resolution — multi-class retrain (follow-up)

The single-class artifact is superseded. The classifier is now genuinely four-class.

**New dataset (`data/training/`).** The docstring had promised "500 labelled sessions across
four skill tiers"; no such data existed anywhere in the repo (verified: `data/sessions/` are
LLM-harness interaction logs, `data/cowrie_logs/cowrie.json` contains zero command events).
`scripts/generate_training_data.py` now produces them honestly:

- 500 sessions, 125 per tier (novice / intermediate / expert / apt), seeded and reproducible
  (manifest records SHA-256 of `sessions.jsonl`).
- Command banks grounded in `FeatureExtractor`'s own pattern families (recon, scan, exploit,
  privesc, persistence, lateral, creds, exfil, anti-forensics, compile) so every feature fires
  from real command semantics.
- Per-tier profiles: session length (6–14 → 50–90 commands), Dirichlet-jittered category mix,
  lognormal inter-command delays (novice CV≈0.22 → apt CV≈0.09). Adjacent tiers overlap by
  construction; the class-conditional means in `data/training/manifest.json` show the
  monotone structure (persistence 0.02→0.12→0.47→0.71, lateral 0→0→0.35→0.76).

**Training (`scripts/retrain_chrollo.py`).**

- Stratified 80/20 split (400/100), `ChrolloClassifier.train()` with 200 trees,
  `class_weight=balanced`.
- **Leakage fix in `classifier.train()`:** CV previously ran on data standardized with
  statistics fitted on all samples. CV now runs through a `Pipeline(StandardScaler, RF)` so
  each fold fits its own scaler. Also fixed `np.bincount(y).min()` → min over *present*
  classes (single-class-present training sets previously produced NaN CV).
- Old single-class model preserved at `models/chrollo/rf_classifier_single_class_backup.joblib`.

**Real metrics (held-out 20%, `models/chrollo/training_manifest.json`).**

| Tier | Recall |
|---|---|
| novice | 0.84 |
| intermediate | 0.80 |
| expert | 0.76 |
| apt | 0.88 |

Held-out accuracy **0.82**; confusion is strictly adjacent-tier (novice↔intermediate,
expert↔apt; zero cross-tier errors). These are synthetic-data numbers on a semantic task —
the manifest says so explicitly; no benchmark accuracy is claimed.

**Tuning follow-up.** `scripts/tune_chrollo.py` ran a leakage-safe search (60 configs ×
5 OOF folds on the training split; held-out set touched once): shipped config is
**500 trees / depth 14 / leaf 2 / unweighted → 0.84 held-out** (recalls
0.84/0.80/0.80/0.92, zero cross-tier errors, Wilson 95% CI [0.76, 0.90]). Notable: all
class-boundary weighting candidates (boundary/interior/apt-focus boosts, balanced variants)
underperformed unweighted; the gain came from shallower trees with more estimators.
Also fixed en route: tuning featurization was float32 vs production float64, flipping one
borderline session — eval now bit-identical to the `classify()` path.

**Scale-up to 2,000 sessions (final state).** (Figures in the subsections above are
historical records of the 500-session regime; this block is the current state.) Corpus
regenerated at 500/tier (seed 42;
the first 125/tier are a superset-preserving prefix of the original draws), re-split
1600/400, baseline retrained at 0.8825, then tuned. Two pipeline defects were caught and
fixed during the scale-up:

1. **Stale snapshot poisoning** — `tune_chrollo.py` only created its `pre_tune` backup
   `if not backup.exists()`, so a leftover artifact from the 500-session regime became the
   "baseline" for two tuning runs. Worse, that old model had been trained on the sessions
   that are now inside the new test pool → its 0.895 "baseline" score was **train-test
   contamination**, not skill. Snapshot logic now always refreshes.
2. **Restore-after-keep clobber** — when the ship rule said KEEP BASELINE, the script
   copied the stale snapshot back over the freshly retrained true baseline. The disk could
   end up holding neither the baseline nor the tuned model.

After the fixes, the clean run ships **500 trees / depth 16 / unweighted → 0.8875
held-out** (n=400, Wilson 95% CI [0.853, 0.914]; recalls 0.91/0.89/0.85/0.90; zero
cross-tier errors), strictly better than the 0.8825 default-config baseline. Verified live
through `classify()` on the persisted artifact; 850/850 unit tests pass. The earlier
"balanced" default is mathematically equivalent to unweighted at equal per-class counts.
Artifacts: `models/chrollo/rf_classifier.joblib` (+scaler, +`training_manifest.json`,
+`tuning_manifest.json`), splits in `data/training/{train,test}.jsonl`, pre-scale backup in
`models/chrollo/_pre_scale_backup/`.

**Model-quality analyses (follow-up).**

- **Calibration** (`scripts/calibrate_chrollo.py` →
  `results/model_quality/chrollo_calibration.{json,png}`): confidence is mildly
  underconfident — mean confidence 0.8196 vs accuracy 0.8875 (gap −0.068), 15-bin
  equal-mass ECE 0.071, MCE 0.218, multiclass Brier 0.176. Underconfidence is the safe
  direction for a threshold: the sweep is monotone and at s ≥ 0.85 coverage is 52% with
  accuracy 0.9806 (Wilson 95% [0.951, 0.992]) and zero cross-tier errors. Platt reference
  (fitted on train-split OOF) halves ECE to 0.039 — optional post-hoc improvement, not
  shipped; the runtime artifact is unchanged. Verdict: **the 0.85 escalation threshold is
  conservative and trustworthy; no change made.**
- **Learning curve** (`scripts/learning_curve_chrollo.py` →
  `results/model_quality/chrollo_learning_curve.{json,png}`): curve is flat within noise
  from n=800 on (0.887±0.007 → 0.885±0.004 → 0.8865±0.003 at 1,600); power-law fit
  (RMSE 0.006) projects ≈+1.0pp at a 2× corpus, ≈+1.9pp at 10×. Verdict: **the 10-feature
  representation, not data volume, is the binding constraint** — further gains need richer
  features, not more synthetic sessions. An earlier "still climbing" verdict from a
  noise-blind heuristic was caught and fixed before the results were used.

**Sequence-aware feature prototype (follow-up).** `ragin/chrollo/features_seq.py` adds
8 session-phase features + 32 hashed command n-gram buckets; `scripts/benchmark_seq_features.py`
benchmarks them vs the 10-feature baseline across three regimes (OOF-selected model grid,
test touched once per group, paired bootstrap + McNemar):

| Group | Same-dist | 1st-cmd disjoint | Strict bank-disjoint |
|---|---|---|---|
| baseline(10) | 0.8850 | 0.8799 | 0.8500 |
| +phase(8) | +1.0pp n.s. | +1.8pp n.s. | **−10.2pp p<0.001** |
| +ngram(32) | **+6.0pp p<0.001** | **+3.9pp p=0.035** | **+3.7pp p=0.017** |
| +all(50) | +5.0pp p<0.001 | +4.9pp p=0.013 | −6.8pp p=0.001 |

Verdict: **n-grams generalize across fully disjoint template pools** (real attack-structure
signal; recommended for production integration). **Phase-position features are a template
artifact** — OOF 0.92 → test 0.75 collapse in the strict regime — and poison the combined
model; do not ship. Caveat: all numbers are synthetic-corpus numbers; re-validate on real
session data before production claims. `tests/unit/test_features_seq.py` 10/10; suite
860/860. Results: `results/model_quality/seq_features_benchmark.json`.

**LangGraph RAG orchestration (follow-up).** `ragin/don/graph.py` adds a corrective-RAG
StateGraph over the existing Don primitives:

```
decompose (LLM, heuristic fallback) → retrieve (parallel hybrid per sub-query,
fused+deduped) → grade (per sub-query×doc; LLM or lexical-overlap fallback)
→ check sufficiency (EVERY sub-query covered) → rewrite (bounded, REWRITE_ROUNDS=2)
→ compose
```

- **LLM-optional by design**: decompose/grade/rewrite each fall back to deterministic
  heuristics; all LLM calls flow through `ThreatRAGEngine._call_gateway` (PII redaction,
  circuit breaker, budget, token limiter unchanged). The graph itself does no I/O.
- **Pipeline wiring**: `DonPipeline(use_graph=…)` defaults on, env kill-switch
  `RAGIN_DON_GRAPH=0`, and any graph exception falls back to legacy `analyze()`.
  `ThreatRAGEngine.analyze_graph()` exposes the path directly; the graph's composed,
  graded context flows to `generate_report()` through the same `_last_intel_context`
  channel as before.
- **Bugs caught by tests**: (1) conditional-edge deadlock — on exhausted rewrites the
  router sent the graph back to `retrieve` forever (GraphRecursionError); now composes
  when sufficient OR out of retries, plus an explicit recursion-limit cap. (2) The
  sufficiency criterion was total relevant docs; now per-sub-query coverage (every
  decomposed information-need must be satisfied) — which also correctly fixed the
  triggering semantics the first test asserted.
- **Benchmark** (deterministic mode, 27-doc synthetic CTI corpus with distractor topics):
  P@5 parity with legacy (1.00 vs 1.00 — corpus too small to differentiate); compound
  queries decompose correctly (`'ssh brute force' / 'lateral movement smb'`); absent-topic
  queries terminate boundedly (rounds=2, ~3ms overhead); ~2ms/graph-pass overhead;
  zero unhandled failures. With an LLM key the graph adds relevance grading and LLM
  query rewriting on top (not benchmarkable offline).
- `tests/unit/test_don_graph.py` 10/10; suite 870/870. `pyproject.toml`: langgraph>=0.2.

**Full-corpus benchmark (follow-up; partial — LLM panel quota-blocked).**
`scripts/benchmark_fullcorpus_graph.py` loads the real retrieval corpus
(22,396 LightRAG/ATT&CK-derived docs from `data/benchmark_lightrag/kv_store_full_docs.json`,
6.2 MB) into the engine's BM25+vector stores and runs 10 ATT&CK-derived analysis queries
through legacy vs graph. Engine LLM pointed at OpenRouter free tier via GatewayClient's
OpenAI compatibility.

**Critical bug found by the benchmark (fixed):** when the gateway is down,
`ThreatRAGEngine._call_gateway` returns bracketed error placeholders as *strings*
("[Report generation failed: 401 …]"). `_ask_llm` passed them through as model output, so
`_llm_grade` saw a string containing no "relevant" and **silently graded every document
0.0 → zero relevant docs → empty context**, while the trace claimed degraded=False.
`_ask_llm` now maps placeholder matches to None (forcing deterministic fallbacks);
regression tests in `TestErrorPlaceholderGuard` (suite 872/872). A second latent bug
(error placeholders becoming sub-queries after LLM decompose failure) was fixed in the
same pass for `_llm_decompose`/`_llm_rewrite`.

**Results with LLM quota exhausted (degraded-mode graph, still meaningful):**

- Query decomposition works on real queries (e.g. splits "lateral movement via SMB and
  remote services" → ['lateral movement via SMB', 'remote services']).
- Degraded-mode grading (lexical overlap) now passes all docs that share query terms:
  the graph's precision@5 equals legacy where retrieval is sane (0.40/0.40 LSASS,
  1.00/1.00 exfiltration) and diverges where BM25 term-frequency dominates
  (0.60→0.00 on one query) — the graded path's value needs the LLM online to judge.
- Latency: legacy ≈72 ms vs graph ≈207 ms mean per query (degraded mode; LLM grading adds
  more). Context volume comparable (≈2.9 vs ≈3.1 KB).
- **LLM panel grading (3 judges, κ) not completed**: the OpenRouter free tier's daily
  quota (50 req/day) was exhausted by probing (~14:00 UTC 2026-09-16; resets 00:00 UTC).
  Also learned: most free models are reasoning-style and return `content=null` with
  small max_tokens — the GatewayClient's null-content retry mitigates, and non-reasoning
  free models (`nvidia/nemotron-3-super-120b-a12b`, `poolside/laguna-s-2.1`,
  `inclusionai/ling-3.0-flash-vl`, `cohere/north-mini-code`) verified working for
  single-integer rubric replies. Rerun after quota reset:
  `python scripts/benchmark_fullcorpus_graph.py` (panel section runs automatically;
  judge models already set to verified non-reasoning free models).

**Paper updated to match.** §5.1 now describes the corpus and reports 0.82 held-out
accuracy with the per-tier recalls, replacing the unverifiable "calibrated against a
standardized testbed" sentence; Algorithm 1's "100 trees" → 200 trees (was already
inconsistent with the text's own 200-tree claim).

**Verification.** `tests/unit/test_chrollo.py` 62/62; full unit suite 850/850; live
`classify()` over the persisted model reproduces held-out recalls exactly
(`classes_ = [0 1 2 3]`).
