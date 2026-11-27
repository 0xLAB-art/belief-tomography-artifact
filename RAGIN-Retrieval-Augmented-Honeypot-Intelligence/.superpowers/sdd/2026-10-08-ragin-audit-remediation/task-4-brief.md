### Task 4: Build the canonical results ledger and provenance table

**Files:**
- Create: `docs/RAGIN_RESULTS_LEDGER_2026-10-08.md`
- Inspect: `results/b4_baseline_zodiac_20260922.json`, `results/bootstrap_ci.json`, `results/graph_consistency_bench.json`, `results/stability_run1_vs_run2.json`, `results/external_baseline_model_coherent.json`, `results/two_channel_metrics.json`, `results/verifier_redteam*.json`, `results/benchmark_report.json`, `results/sp2027_rescue/`
- Modify only if required: artifact metadata/manifest files whose values are demonstrably inconsistent

**Interfaces:**
- Consumes: Task 1 classification and Task 3 corrected JEV artifact.
- Produces: a single table mapping each reported number to its file, split/corpus, scorer, execution mode, provenance, status, and permitted claim.

- [ ] **Step 1: Record canonical live-audit values.** Include the B4 baseline, bootstrap CIs, graph consistency, stability, verifier red-team, and the live audited composite with exact scorer definitions and corpus sizes.
- [ ] **Step 2: Record the two-channel distinction.** Preserve the difference between analysis-channel values (`cti_analysis_avg`), both-channel values, ordinary served-text values, and echo-guarded served-text values. Record that the echo-guarded served technique/actor values are much lower than the uncorrected served values.
- [ ] **Step 3: Record model-coherent baselines.** Keep bare `llm_unverified` and grounded/verified replay values as analysis evidence; state that the verifier paired delta is zero in that artifact and do not convert it into an independent causal claim.
- [ ] **Step 4: Exclude failed or non-canonical results from headline claims.** Mark `results/benchmark_report.json` (158/158 failures), stale human-evaluation directories, old Cowrie outputs, provider pilots, and fallback-only operational traces as non-headline evidence unless a separate analysis explicitly uses them.
- [ ] **Step 5: Add provenance checks.** Record hashes, timestamps, train/test overlap, fallback counts, and the exact scripts/configurations required to regenerate each canonical artifact.
- [ ] **Step 6: Verify ledger-to-artifact agreement.** Run the existing artifact-consistency and supported-claim tests, then manually inspect every headline row against its source JSON.

**Pass condition:** Every headline number has one source of truth and a bounded allowed interpretation; failed, historical, and provider-blocked artifacts cannot be mistaken for current evidence.

