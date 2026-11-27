# Implementation Readiness Report — RAGIN paper (`paper/main.tex`, lines 1125–2144)

**Reviewer:** Implementation Readiness Goldfish (Pragmatic Tech Lead persona)
**Question answered:** Could an independent team reproduce the system and experiments from the paper alone? **No — not currently.** The evaluation narrative is unusually candid (good), but reproduction is blocked by (a) five cited artifacts/scripts that do not exist in the repository, (b) an unspecified LLM model ID / temperature / prompt set, and (c) untraceable numeric claims where the named source JSON contradicts the paper. An independent team would have to make at least four design decisions the paper should make for them.

Verification was done against the live codebase at `RAGIN-Retrieval-Augmented-Honeypot-Intelligence/` and `results/field_attack_v3/`.

## 🔴 Blockers (4)

**R1. Five artifacts cited by exact path are missing from the repository** (lines 1467, 1519–1520, 1553, 1674, 1849, 2021)
The paper promises re-executability by exact path; the following do not exist anywhere in the repo (verified by `find` over the whole tree):
- `results/rag_prompt_controlled_ablation.json` (line 1467 — the Arm-C result, the paper's headline re-scoping evidence)
- `results/redteam_personas.json` (line 1674 — the entire persona battery of Table `tab:dwell` is untraceable)
- `scripts/bootstrap_cowrie_ci.py` (lines 1519–1520 — the CI $[+0.04,+0.71]$ cannot be regenerated; repo has `scripts/bootstrap_ci.py` and `ai_jury_bootstrap_ci.py`, neither matches the cited name)
- `scripts/deterministic_artifact_safety.py` (line 1553 — the 4.2/5 corrected artifact-safety score is unverifiable)
- `ragin/gateway/pii_redactor.py` (line 1849 — the PII-hashing spec cites a code path that does not exist; `ragin/gateway/` contains only `client.py`, `generation.py`, `invocation.py`)

**Guidance:** Either commit these files or correct every path in the paper. As written, the Arm-C ablation, the bootstrap CI, and the bias-corrected panel aggregate — three of the paper's headline claims — are not re-executable even with repo access.

**R2. LLM inference configuration is unspecified: no model identifier, no temperature value, no output cap, no prompt text** (lines 1175–1179, 1419–1424)
Lines 1175–1179 say only: "OpenRouter gateway… temperature set low… Output length is capped." No model ID (e.g., which OpenRouter-hosted model produced the 218-query benchmark), no numeric temperature, no cap value, and no prompt template text anywhere in the range. The codebase confirms this is env-driven (`ragin/gateway/invocation.py::_model_identifier` reads an env var; code default temperature is 0.3 in `ragin/don/rag_engine.py:890` but the paper never states it), and `results/live_benchmark.json` carries no model/timestamp/temperature metadata. The Arm-C paragraph (1419–1424) claims "the LLM endpoint, the model identifier, the temperature… are held constant" without ever stating what they are. **Guidance:** State the pinned model ID, temperature, max-output tokens, timeout, and include the system prompt and the three skill-tier prompt templates verbatim (the templates are the manipulated variable in the paper's own ablation and must be published).

**R3. Arm-C's "filler corpus" is undefined** (lines 1420–1424)
"Semantically unrelated filler sampled from a held-out corpus of uncorrelated open-source text (length-matched to the retrieved documents)" — no corpus name, no sampling procedure, no seed, no length-matching algorithm. The 3-vs-0 result depends entirely on what the filler was. **Guidance:** Name the corpus, the sampling code/seed, and the matching rule, or commit the generator script.

**R4. Chrollo training is unreproducible: no dataset, no labels, no RF hyperparameters** (lines 1131–1157)
The classifier is described as "Random Forest… trained offline" with 10 features, Z-score scaling, k-NN imputation ($k=5$). Missing: the training dataset (source, size, label provenance — how were sessions labeled novice/intermediate/expert/apt?), the train/test split, all RF hyperparameters (n_estimators, max_depth, class weights, random seed), and classifier accuracy/eval metrics. A reproducer cannot rebuild `models/chrollo/rf_classifier.joblib`. **Guidance:** Add a training-data table, label-generation procedure, hyperparameter list, and seed; report held-out skill-classification performance.

## 🟡 Major (8)

**Y1. Fusion weights contradict the code.** Paper: $\alpha=0.7/\beta=0.3$ (lines 1165, 1918). Code: `hybrid_search(..., alpha: float = 0.25)` with docstring "empirical optimum is alpha≈0.15–0.25" (`ragin/don/rag_engine.py:751-756`), though one call site passes `alpha=0.7` (`ragin/don/rag_engine.py:450`). Which value governed the evaluated pipeline is ambiguous. State the value used per experiment and reconcile with the code.

**Y2. Corpus and index parameters unspecified.** 780,600 documents (line 1919) — but no corpus composition/sources, no embedding model, no chunking, no FAISS HNSW parameters (M, efConstruction/efSearch), no BM25 implementation. Retrieval results cannot be regenerated. Also line 1172–1173 defers corpus-poisoning screening to "the repository" without naming a file.

**Y3. Dwell-time numbers are internally inconsistent.** Table `tab:kpis` (line 1392) reports mean dwell 12,636 ms, but `results/live_benchmark.json` `metrics.mean_session_duration_s` = 7,286.6 ms for the same 30 sessions. Either a different source file (not named) or a different metric definition (dwell vs. pipeline session duration) — undefined. "Dwell" itself is defined only as "attacker-side session engagement before termination"; the measurement point is unspecified.

**Y4. LLM-panel evaluation protocol under-specified.** Lines 1535–1555: 8 GT scenarios, 5 Likert dimensions, $\kappa=0.425$ — but judge model IDs, judge count, judge prompts/rubric anchors, κ computation method, and scenario content are absent (only `results/human_eval_scored/` is named at line 2022). The corrected 2.83/5 and 3.06/5 aggregates likewise have no stated aggregation formula.

**Y5. Lexical scorer undefined.** The load-bearing pass criterion "score ≥ 0.3" (line 1252) and "composite (lexical) 0.697" (lines 1505, 1314) are never defined: matching algorithm (tokenization, n-grams, stemming), what a "score" of 0.3 means, and the composite formula. Figure 4's caption even cites "composite… of 0.697 reported in Table tab:benchmark" (line 1314), but that table contains no such number — it lives in Table `tab:cowrie` (cross-reference error).

**Y6. Session-generation methodology missing.** The 30 sessions (10 local driver + 10 VPS + 10 Tor, lines 1359–1360) have no driver script, command-stream provenance, seeds, or Tor setup described; "44 interactive auth attempts" cannot be re-produced without knowing how sessions were driven. Dwell-time results are a function of the driver.

**Y7. Bootstrap CI resampling unit unspecified.** Lines 1516–1520 give 10,000 resamples and seed 42 (good) but not the resampling unit (per-session composite? per-query?) or how the n=6 Cowrie sessions were paired/weighted.

**Y8. Audit-classification thresholds are ad hoc.** The four audit classes (lines 1296–1304) hinge on "inside the 90 s latency budget" vs. "~160 s wall-clock," and the reconciliation footnote (lines 1279–1281) admits "two borderline cases (well-formed content delivered just past the latency floor)" with no rule for what counts as borderline. The audit script exists in the repo (`scripts/audit_live_benchmark.py`) but is not cited in the paper.

## 🟢 Nits (7)

- **N1.** `mem0ai >= 0.1.0` (line 1224) is an unbounded lower pin; Mem0 itself requires a backing LLM — which one, and its config, is unstated, so the memory layer is not reproducible.
- **N2.** Redis session TTL values never given (lines 1188, 1207); only the Mem0 idle window (30 days) is numeric.
- **N3.** Line 1238 "The complete implementation is open-sourced at RAGIN." — dangling reference; the URL appears only in Data Availability.
- **N4.** No software/hardware environment in the paper: no scikit-learn/FAISS/Cowrie versions, no EC2 instance type ("one EC2 host," line 1887).
- **N5.** Persona Realism content-pass of 18.3% (line 1289) vs. 91.9–100% for CTI suites is a large anomaly left unexplained (scorer–suite mismatch?).
- **N6.** "Held-out corpus of uncorrelated open-source text" (R3) and the "screening stage… described in the repository" (line 1173) both point to unnamed repository locations — the repo has 200+ scripts with no index mapping paper claims to files.
- **N7.** Engagement ID "RAGIN-RE-20260730" (line 1676) embeds a date format used nowhere else; harmless but inconsistent.

## Counts and verdict

**🔴 Blockers: 4 | 🟡 Major: 8 | 🟢 Nits: 7**

**Verdict:** The paper's honesty about negative results is exemplary, but implementation readiness is insufficient for independent reproduction. Fixing R1 (commit or re-path the five missing artifacts), R2 (publish model ID + prompts + temperature), R3 (filler-corpus provenance), and R4 (classifier training recipe) would move the paper from "readable account of a live system" to "reproducible artifact"; the 🟡 items are largely one-paragraph additions of definitions and parameters already present in the codebase.
