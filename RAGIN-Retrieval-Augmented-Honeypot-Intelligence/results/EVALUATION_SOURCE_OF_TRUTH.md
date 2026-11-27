# Evaluation Source of Truth — decision ledger (2026-11-05)

Purpose: one place defining which artifact backs every evaluation number the
papers (S&P 2027 / TDSC / ESWA) may cite. Rule after the 2026-11-05 EGM audit:
**no number may appear in any paper unless a committed artifact on disk derives
it.** This file is that mapping. Written by the post-EGM hardening campaign.

## 1. LLM-judge panel consensus (was "human eval 2.51/5, κ=0.425" — RETIRED)

- **Authoritative artifact: `results/human_eval_scored_20260922_180637_consensus/consensus.json`**
  (declared authoritative by `results/human_eval_scored/CORRECTION.md`, 2026-10-24 audit;
  embedded scores match its evaluator files 24/24).
  - Model: `grok-4.7-free`, 3 persona judges (alpha/beta/gamma), 8 GT scenarios, 5 dimensions.
  - Overall mean **3.86 / 5** (computed: 3.862), inter-rater agreement **0.750**,
    8/8 scenarios ≥ 3, 5/8 ≥ 4, min GT-005 = 3.0, max GT-006 = 4.2.
  - Per-scenario consensus overall: 4.1, 4.2, 4.0, 3.9, 3.0, 4.2, 3.4, 4.1.
  - Per-dimension means (computed from the artifact):
    deception 3.666, persona 3.667, ttp_accuracy 4.625, engagement 4.041, artifact_safety 3.375.
- **Second judge family (cross-model robustness check): `results/human_eval_scored_v2/consensus.json`**
  (model `qwen--qwen38-27b`, 2026-07-29): mean **2.83/5**, agreement **0.675**, 1/8 scenarios ≥ 3.
  This is a *different judge run with a different model*, NOT "the same run minus
  one dimension". The cross-model spread (3.86 grok vs 2.83 qwen) is itself a
  finding and must be disclosed as judge-family sensitivity.
- **Retired numbers (must not appear in any paper):** 2.51/5, κ=0.425,
  "pilot 1.91 with smaller judge pool" (both runs used 3 evaluators),
  "deterministic artifact-safety 4.2/5" (no artifact; superseded by the
  artifact_safety dimension mean 3.375 above), and the aggregate "3.06/5"
  (does not recompute from its own stated components).
- **Framing:** these are LLM-judge evaluations. No human rater scored any
  scenario anywhere in this repository (per CORRECTION.md scope note; the blind
  human packets in `results/human_blind/` were never answered).

## 2. Cowrie head-to-head (was "n=6, composite 0.317, Δ+0.380" — RETIRED)

- **Regenerated 2026-11-05** via `scripts/cowrie_comparison.py` from the
  committed merged log **`data/cowrie_logs/cowrie_merged.json`** (deduplicated
  union of all committed rotated logs: `cowrie.json.1`, `cowrie.json.2026-07-28`,
  `cowrie.json.2.gz`, `cowrie.json.3.gz`; 225 unique JSON events).
- **Artifact: `results/cowrie_comparison.json`** (paths self-contained and
  re-runnable: `.venv/bin/python scripts/cowrie_comparison.py --cowrie data/cowrie_logs/cowrie_merged.json`).
- **Actual numbers:**
  - Sessions: RAGIN 30 vs Cowrie **16** (not 2, not 6).
  - Engagement: 0.960 vs **0.812** (Δ +0.147).
  - Unique TTPs: **13 vs 10** (Δ +3).
  - Honeytokens deployed: 30 vs 16 (Cowrie has no honeytoken engine; counted as
    its session count by the adapter's metric contract).
  - Composite: 0.697 vs **0.412** (Δ **+0.284**).
- **Provenance caveats that MUST ride with the numbers in any paper:**
  1. All 16 Cowrie sessions originate from `172.17.0.1` (the local Docker
     bridge / driver). **No external-attacker Cowrie session exists in any
     committed log.** The previously claimed "6 sessions incl. 2 from real
     attacker [real-attacker-source-A]" (REVIEWER_FIXES_SUMMARY.md) does not reproduce
     from committed data and is retired.
  2. The comparison is therefore a driver-generated-baseline comparison, and
     the paper must label it as such (same honesty standard as the RAGIN-side
     driver sessions).
  3. n=16 vs 30; bootstrap CIs must resample sessions (not queries).

## 3. Live benchmark (218 queries / 30 sessions)

- **Artifact: `results/live_benchmark_audited.json`** (raw rows in
  `results/live_benchmark_full.json`). Every `tab:benchmark` number derives
  from this file: 218 scored results (123 CTI / 35 actor / 60 persona),
  content-pass 113/123 = 91.9%, 35/35 = 100.0%, 11/60 = 18.3%; quality-pass
  16/123 = 13.0%, 2/35 = 5.7%, 2/60 = 3.3%; classes 22 GROUNDED / 2 REFUSAL /
  5 EMPTY / 189 TIMEOUT; mean session duration 160.6039 s; ttps_detected 82,
  unique 31.
- **`results/live_benchmark.json` is a DIFFERENT experiment** (30 one-turn
  sessions, 7.29 s, 5 TTPs) and is the correct source ONLY for the RAGIN-side
  ablation arm (5 TTPs / 13 unique) and the Cowrie comparison above. Paper
  citations must name the exact file per table.

## 4. Known-unbacked numbers (retired unless an artifact is committed)

- Campaign KPIs (261 queries, 44 auth attempts, dwell 12,636/13,290/9,366–21,021 ms,
  10+10+10 egress mix): **no artifact anywhere**; exist only as prose in the
  ESWA response letter. `results/ALL_RESULTS_VS_ESWA_PAPER.md` already flags
  this axis "re-deployment pending". Until re-deployment, papers must not cite
  these numbers.
- Tactic-per-row distribution of `tab:tactics` (TA0043=4/1, …): no generating
  artifact. Retire per-row rows; keep only artifact-backed endpoint totals
  (31 unique RAGIN vs 5 unique Cowrie).
- Arm-C prompt-controlled ablation per-dimension scores (0.68/0.41/0.55): no
  artifact. Regeneration scheduled (see campaign Phase C) — commit
  `results/rag_prompt_controlled_ablation.json` before citing.
- Corpus scale "780,600 documents": no artifact; on-disk LightRAG graph store
  has 75,151 doc-status entries. Papers must cite the verifiable figure or the
  index build artifact, not the aspirational one.
- Chrollo tree count: text said 500, Algorithm 1 said 200. **Verified from the
  shipped model (`models/chrollo/rf_classifier.joblib`, loaded via joblib):
  `n_estimators = 300`.** Every paper must say 300 (or retrain; do not cite
  either old number).
- PII hashing: `ragin/utils.py::hash_ip` is plain SHA-256(ip+static_salt) with
  committed default `"ragin-ip-v1"`. Any paper claim of HMAC / per-record salt /
  `ragin/gateway/pii_redactor.py` is false until the code is fixed (scheduled:
  campaign Phase A4).
