# Task 4 Report — Canonical results ledger and provenance table

## Status

Complete. `docs/RAGIN_RESULTS_LEDGER_2026-10-08.md` created; every headline number has
one source-of-truth artifact, bounded interpretation, and a failed/historical/provider
exclusion table.

## Changed files

- `docs/RAGIN_RESULTS_LEDGER_2026-10-08.md` (created)
- `.superpowers/sdd/2026-10-08-ragin-audit-remediation/task-4-report.md` (this report)

No JSON result artifact, README, paper, test, provider file, or session data was
modified. No source file was edited; Step 6's "modify only if required" branch was not
triggered — all inspected artifact metadata was internally consistent.

## What the ledger records

1. **Canonical live-audit values** — B4 paired grounding delta (+0.1539, CI
   [+0.0922, +0.2206], n=90), bootstrap CIs (composite 0.8796 n=218), C1 adversarial
   re-query (0 contradictions / 45, byte-identical determinism 45/45), C3 steering
   (top-1 0.50, top-3 0.90, MRR 0.6667), stability (Δ +0.0049, pass agreement 0.9908,
   judge-audited panel technique/actor Δ 0.0), judge-panel correction, verifier
   red-team (deterministic 105-case P 1.0/R 1.0; supported-claims 123-case),
   cross-family live red-team (space-bunny/deepseek/llama post-P1), and version-of-record
   totals (218 sessions, 132 TTPs, 0 FP, 0 unverified serves). Each row carries file,
   corpus/split, scorer definition, execution mode, provenance, status, permitted claim.
2. **Two-channel distinction** — `cti_analysis_avg` (0.9598/0.85) vs original served-text
   (0.5236/0.68) vs echo-guarded served (**0.0569/0.0**, deception 0.6492 unchanged,
   97 rows changed); both-max 0.9768/0.87. Echo-guarded values are much lower than the
   uncorrected served values; a full guarded rerun requires a live 218-row pass.
3. **Model-coherent baselines** — all-LLM-arms-on-deepseek-v4-flash-free table; bare
   `llm_unverified` 0.5018 and grounded/verified replay values kept as analysis evidence;
   **verifier paired delta is exactly 0 on all 218 rows**, explicitly marked not an
   independent causal claim; grounding +0.1158 same-model; Sep-22 historical reference
   (0.8163/0.8474) quarantined from cross-model pairing.
4. **JEV** — 12/13 real-log corrections, A/B Δ=0.0 (jev_available 0), hard-subset
   census (6 informative of 400, 1 rescued / 5 provider-refused, retry recovered 0).
   Task 3 `resolution_statement` repair honored; pre-Task-3 hash `884a63c2…` recorded
   for chaining, current hash `0721223c…` recorded.
5. **Rescue benchmark** — provider-free, 400 held-out sessions, 6,400 rows, skill
   accuracy 0.5356, coverage delta +0.2306 (CI [0.2159, 0.245]); risk-floor arm marked
   self-consistency diagnostic, not independent effectiveness.
6. **Exclusions** — `results/benchmark_report.json` (158/158 failed), `before_openrouter/`,
   stale human-eval variants, old Cowrie outputs, provider pilots (`hostfiction_provider_*`),
   apmix quota/probe operational traces, session JSONLs, stale graphify-out.
7. **Provenance** — sha256 (first 16) + mtime per artifact, exact regeneration commands,
   train/test overlap (`data/training/test.jsonl` sha256 `046d9b19…`), fallback-count
   tallies.

## Verification summary

- `pytest tests/unit/test_artifact_consistency.py tests/unit/test_supported_claims.py -q`
  → **44 passed** in 0.48s.
- Every §1–§5 row was manually inspected against the parsed source JSON during ledger
  authorship (values transcribed from JSON, not README/paper prose).
- Hash/timestamp spot re-verification: jev_hard_subset current `0721223c…` (mtime
  2026-10-08 07:47:43, post-Task-3), benchmark_report `3d86c9a9…`, sp2027 rescue
  `f6945dee…` — all reproduce via `sha256sum`.

## Concerns / notes

- `results/jev_hard_subset.json` hash differs from Task 1's manifest (`0721223c…` now vs
  `884a63c2…` pre-Task-3). Expected: Task 3 replaced the `resolution_statement` string.
  The ledger records both for provenance chaining.
- Echo-guarded served-text technique/actor (0.0569/0.0) is an offline rescore; the
  corresponding full live two-channel rerun under the guarded scorer remains unexecuted
  (provider-dependent, needs a 218-row live pass).
- `results/verifier_redteam.json` (105 cases) and
  `results/verifier_redteam_supported_claims.json` (123 cases) are both canonical but
  distinct case sets; the ledger lists both rather than merging them.
- The model-coherent `ragin_full` deception values (0.6492) match the two-channel
  served-text row because the Sep-27 deepseek rerun doubles as the two-channel run's
  generator configuration; no independent re-derivation was required.
- No test suite beyond the two artifact-consistency surfaces was run; this is a
  documentation/ledger task.
