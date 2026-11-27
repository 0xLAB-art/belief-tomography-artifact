# RAGIN Results Ledger — 2026-10-08

Canonical results ledger and provenance table for the RAGIN audit remediation plan
(`docs/superpowers/plans/2026-10-08-ragin-audit-remediation.md`, Task 4).

Every headline number below has exactly one source-of-truth artifact, one corpus/split,
one scorer definition, one execution mode, one provenance record, and a bounded allowed
interpretation. Artifacts that failed, are historical, or are provider-blocked are
classified but **cannot** be cited as current evidence.

Baseline git state at ledger creation: commit `f01a4a98d8fc0cdbf1f031d915385294675e3b1b`,
branch `main`. Two manuscript surfaces: `paper/main.tex` (full audit manuscript) and
`paper/sp2027.tex` (shorter rescue/submission surface); neither is submission-ready
(main.tex build was blocked on `algorithm.sty`; resolved 2026-10-08 by installing `texlive-science`, Task 7; both PDFs rebuilt from current sources on 2026-10-08, main.pdf 27 pp, sp2027.pdf 11 pp).

## 1. Canonical live-audit values (headline evidence)

Hard-review closure update (2026-10-08): the canonical `paper/sp2027.pdf` was
rebuilt after threat-model and claim-boundary integration and is now 12 pages
(SHA256 `fa05345b3b3eabf3c40810a84db2432a6b4c7e3a5ec4d4ac4cd269245ac89b0b`).
The earlier 11-page count above is retained as historical build provenance.

| # | Headline claim / number | Source artifact | Corpus / split | Scorer definition | Execution mode | Provenance | Status | Permitted claim |
|---|---|---|---|---|---|---|---|---|
| 1 | Grounding effect (paired RAG vs no-RAG): overall **+0.1539** composite (n=90, 30 rows × 3 suites), CI **[+0.0922, +0.2206]**; per-suite: technique +0.3167 [+0.1617, +0.48], actor +0.14 [+0.0833, +0.1967], deception +0.005 [−0.0467, +0.0567]; RAG avgs technique 0.95 / actor 0.85 / persona 0.833 vs no-RAG 0.633 / 0.71 / 0.828 | `results/bootstrap_ci.json` → `b4_baseline.paired_diff_ci`; per-row data in `results/b4_baseline_zodiac_20260922.json` | 30 held-out sessions from the B4 comparison workload | Paired bootstrap CI (10000 iters, seed 20260922) on per-scenario RAG−no-RAG score differences; scorers identical to live audit | Live campaign, 2026-09-22, `scripts/run_baseline_comparison.py` | `results/bootstrap_ci.json` generated 2026-09-22T18:01:11Z; re-derivation recorded under `headline_provenance` (uncitable 0.855 trace to deleted /tmp artifact replaced) | canonical | Paired quality delta of grounding on the same 30 scenarios; no cross-model pairing |
| 2 | Bootstrap CIs on the live audited campaign: composite **0.8796** (n=218, CI [0.8572, 0.9]); technique 0.9598 (n=123, [0.9476, 0.972]); actor 0.85 (n=35, [0.85, 0.85]); persona 0.7325 (n=60, [0.6738, 0.7883]); technique pass-rate Wilson 123/123 [0.9697, 1.0]; actor 35/35 [0.9011, 1.0]; persona 58/60 [0.8864, 0.9908] | `results/bootstrap_ci.json` → `live_audited`, `source: results/live_benchmark_zodiac_20260922.json` | 218-query live campaign (123 technique + 35 actor + 60 persona) | Wilson 95% for pass rates; percentile bootstrap (10000 iters, seed 20260922) for continuous means | Live, 2026-09-22 | Same as above; re-computed from persisted per-row bodies | canonical | Headline CI bounds for the version-of-record campaign |
| 3 | C1 adversarial re-query: **0 contradictions / 45** adversarial re-query turns (rate 0.0, Wilson upper 0.0787 < 0.10); **byte-identical determinism 45/45** (Wilson lower 0.9213 > 0.90); served-after-failed-verifier 0 | `results/bootstrap_ci.json` → `c1`; `results/graph_consistency_bench.json` | 9 probes × 5 repeats × adversarial prompts, stratum `deterministic`, persona `intermediate`; configurations `graph-full` etc. | Deterministic fiction-graph verifier; contradiction = predicate-level fact mismatch vs pinned per-session identity; determinism = byte-identical served transcript | Offline, deterministic, 0 LLM tokens | Generated 2026-09-26; `scripts/graph_consistency_bench.py` | canonical | Verifier rejects contradictions and replays are byte-identical; property claim, not an LLM-quality claim |
| 4 | C3 next-TTP steering: top-1 **0.50** (5/10, Wilson [0.2366, 0.7634]), top-3 **0.90** (9/10, [0.5958, 0.9821]), MRR 0.6667; steer hit 0.9, block-steer 0.9, bait-block 0.4; ablated steering 0.0 | `results/mtp_steering_eval.json`; CIs in `results/bootstrap_ci.json` → `c3` | 10 chain turns over deterministic chains (e.g. CH-cred-exfil, CH-web-exploit) | Offline ThreatMapper + template deceiver; top-k accuracy over predicted next-technique ID sets | Offline, deterministic | Generated 2026-09-22T10:44:46Z; `scripts/mtp_steering_eval.py` | canonical | Next-TTP prediction on 10 deterministic chains; resolution-bounded |
| 5 | Run-to-run stability: composite run A 0.8796 vs run B 0.8845, **Δ +0.0049**, mean-abs row diff 0.0265, pass agreement 0.9908, verdict `stable`; judge-audited panel: technique 0.9598→0.9598 (Δ 0.0), actor 0.85→0.85 (Δ 0.0), deception unchanged on audited rows | `results/stability_run1_vs_run2.json` (`composite`, `headline_metric_deltas`, `audited_panel`) | 218 paired rows (run A vs run2), per-suite paired rows 123/35/60 | Per-row paired comparison; audited panel splices judge-audited rows from `*_judgescored.json` | Live campaign twice (2026-09-22), offline comparison | Generated 2026-09-23T13:30:27Z; `scripts/compare_run_stability.py` | canonical | Stability of the version-of-record pair; not a claim about provider drift over time |
| 6 | Judge-panel audit correction: canary-bias magnitude 2.1 corrected (README headline: 1.35 corrected on the deception stratum), harness artifact reclassified, persona means corrected | `results/live_benchmark_judge_panel_corrected.json` | Live benchmark audited rows (persona stratum) | Judge re-score with bait-floor rationale (registered canary bait = correct deception outcome, floor 0.85) and harness reclassification | Offline re-score of persisted transcripts | Generated 2026-09-25; `scripts/rescore_judge_panel.py` | canonical | Corrected persona means; technique/actor unchanged |
| 7 | Verifier red-team (deterministic suite): `results/verifier_redteam.json` — 105 labeled cases (78 should-reject, 27 should-pass), precision 1.0, recall 1.0, 0 missed / 0 false-positive keys, all gates pass, verdict `pass`; supported-claims copy `results/verifier_redteam_supported_claims.json` — 123 cases (87/36), P 1.0 / R 1.0 | `results/verifier_redteam.json`; `results/verifier_redteam_supported_claims.json` | Keyed, labeled, per-check-targeted cases (`scripts/verifier_redteam_cases.py`), fresh FictionGraph per case | should_reject/should_pass labels; caught = rejected AND rejection names the targeted check | Offline, deterministic, 0 LLM calls, ~21–31 ms | Generated 2026-09-27 / 2026-09-28 | canonical | Verifier selectivity on labeled cases; complements campaign coverage, not a replacement |
| 8 | Verifier red-team, cross-family live: space-bunny P 0.9945→1.0, R 0.943→0.9585; deepseek P 1.0→1.0, R 0.9306→0.9827; llama-3.3-70b P 0.8862→0.9158, R 0.8757→0.8981 (post-P1 rescore, 0 new FPs, 0 regressed catches) | `results/verifier_redteam_cross_family.json` | Live LLM author families; 105-case deterministic suite at 1.0/1.0 per-check | Variant-level P/R over valid drafts, post-P1 verifier | Live (authoring), offline rescoring | Via `scripts/rescore_redteam_family.py`, `scripts/merge_llama33_matrix.py` | canonical | Verifier holds across three author families after P1 fix; bounded by live-authoring availability |
| 9 | Live campaign totals (version of record): 218 sessions, 132 TTPs detected (67 unique), 0 false positives, 0 unverified serves (serve-path tally GENERATED_VERIFIED 216 + FALLBACK_VERIFIED 2 in the model-coherent copy), 218/218 persona-correct, retention 1.0 | `results/live_benchmark_zodiac_20260922.json` | 218-query workload | Same scorers as §1–2 | Live, 2026-09-22 | Run dir 2026-09-22; engine recorded in file | canonical | Headline campaign totals |

## 2. Two-channel distinction (analysis vs served text) — MUST NOT be collapsed

Source: `results/two_channel_metrics.json` (`channel_definitions`, `by_suite`,
`echo_guard_correction_2026_09_28`).

| Channel | Definition | cti_technique (n=123) | cti_actor (n=35) | deception (n=60) | Status | Permitted claim |
|---|---|---|---|---|---|---|
| `cti_analysis_avg` | What the Don pipeline **identified** (extracted TTPs/actors in analysis text); never served to attackers | 0.9598 | 0.85 | null (no analysis channel) | canonical (analysis evidence) | Intelligence-extraction quality of the pipeline |
| `served_text_avg` (both-channel stored scores are the max of served-text and CTI-analysis) | What the attacker actually **received** (response_text only), original pre-guard machine scoring | 0.5236 | 0.68 | 0.6492 | canonical as *uncorrected* reference; superseded for technique/actor | Served-text realism before echo guard |
| `both_max_avg` | max(served-text, CTI-analysis) per row | 0.9768 | 0.87 | null | supporting | Combined channel view; not the headline |
| Echo-guarded served-text | Same transcripts re-scored with the echo-guard rule (echo + fallback marker ⇒ 0); rows changed 97 | **cti_technique 0.0569**, **cti_actor 0.0**, deception 0.6492 (unchanged) | | | canonical correction (offline rescore, no live rerun) | **Echo-guarded served technique/actor values are much lower than the uncorrected served values** — serve-text technique/actor credit was largely an echo artifact; full guarded rerun requires a live 218-row pass |

Regeneration note: the echo-guarded served values come from an offline rescore of stored
transcripts (`results/vor_guarded_served_text_lower_bounds.json`, echo-zeroed bounds for
the Sep-22 version-of-record campaign; stored VOR scores are both-channel labels).
A fresh full two-channel run under the guarded scorers requires live LLM calls and is
**not** yet produced.

## 3. Model-coherent baselines (analysis evidence, not independent causal claims)

Source: `results/external_baseline_model_coherent.json` (all LLM arms on
`deepseek-v4-flash-free`, RAGIN_HISOKA_MODEL, regenerated 2026-09-27).

| Arm | Composite | cti_technique | cti_actor | deception | Rows | Serve paths | Note |
|---|---|---|---|---|---|---|---|
| cowrie | 0.0006 | 0.0 | 0.0 | 0.0017 | 218 | scripted | no LLM — unchanged from W1 |
| stateful_llm | 0.0704 | — | — | — | 218 | — | unchanged (already deepseek) |
| llm_unverified (bare) | 0.5018 | — | — | — | 218 | GENERATED_UNVERIFIED | analysis evidence |
| rag_no_verifier_repro | 0.6176 | 0.5236 | 0.68 | 0.6492 | 218 | GENERATED_UNVERIFIED 218 | grounded pipeline, verifier pass-through |
| ragin_full | 0.6176 | 0.5236 | 0.68 | 0.6492 | 218 | GENERATED_VERIFIED 216, FALLBACK_VERIFIED 2 | regenerated; was 0.8474 on Sep-22 model |
| ragin_hostfiction | 0.6176 | 0.5236 | 0.68 | 0.6492 | 218 | GENERATED_VERIFIED 213, FALLBACK_VERIFIED 5 | paired delta vs ragin_full 0.0000 over 218 rows |

- **Verifier paired delta is EXACTLY 0 on all 218 rows** in this artifact
  (ragin_full vs rag_no_verifier_repro under the same model): both served identical
  drafts; the verifier only gates (0 unverified serves). The paired difference of 0
  is quality parity plus the safety boundary — **do not convert it into an independent
  causal claim** about verifier quality improvement.
- Grounding contribution, same model: ragin_full vs llm_unverified = **+0.1158**
  composite (analysis evidence; the paired live B4 delta is +0.1539 under §1).
- Historical Sep-22 reference (unrecorded pre-deepseek gateway default):
  rag_no_verifier 0.8163, ragin_full_reference 0.8474 — **do not pair across the model
  boundary**. The `results/technique_rubric_diff_investigation.json` verdict (FALSE: the
  0.6176-vs-0.8474 gap was a scorer-channel artifact, not a deepseek regression) is
  the standing explanation.
- Bare `llm_unverified` (0.5018) and grounded/verified replay values are retained as
  analysis evidence only.

## 4. JEV (top rung) evidence — bounded, provider-dependent

| Artifact | Key numbers | Status | Permitted claim |
|---|---|---|---|
| `results/jev_real_logs_eval.json` | 13 real Cowrie sessions; baseline_correct 0 → with_jev_correct 12 (**12/13 corrected**); endpoint typesafe-ai/jev | canonical for the 13-log audit | JEV corrects 12/13 real-log assessments; provider-dependent |
| `results/jev_ab_eval.json` | n=200, baseline_acc 1.0, with_jev_acc 1.0, acc_delta **0.0**, jev_available 0, jev_errors 0, mean_under_delta 0.0 | canonical | No benchmark-resolvable routing effect; Δ=0.0 at resolution ceiling |
| `results/jev_hard_subset.json` (Task 3 repaired) | corpus n=400 from `data/training/test.jsonl` (apt/expert/intermediate/novice ×100); ceiling base_correct 394, base_incorrect_informative **6** (all APT, under_depth 1); informative fraction 0.015; jev_arm assessed 1, unavailable 5, rescued 1, errors 0; retry measurement: 4 attempts/row, 20 s spacing, recovered 0, still_unavailable 5 | canonical under Task 3 repair (sha256 now recorded in §6) | The honest fold-down claim is **"no measurable effect at benchmark resolution"**, not general subsumption; the single rescued row must not be extrapolated; provider-refusal availability caveat stands |

`results/jev_hard_subset.json` hash reconciliation: Task 1 manifest recorded sha256
`884a63c2…` (mtime 2026-09-23) — that is the **pre-Task-3** value. Task 3 replaced only
the `resolution_statement` string, so the current canonical hash is the one recorded in
§6 below; the old hash is retained here for provenance chaining.

## 5. SP2027 rescue benchmark (bounded)

Source: `results/sp2027_rescue/behavior_trajectory_benchmark.json`, README in the same directory.

- Provider-free replay of 400 held-out sessions (`data/training/test.jsonl`, sha256
  `046d9b19…`; train sha256 `e5bf8a71…`) at 8 command prefixes; 6,400 rows.
- Arms: `skill_only` vs `behavior_floor`; skill accuracy 0.5356 (3200 prefix rows),
  risk-floor coverage 0.3394, under-routing rate 0.6606; paired coverage delta mean
  **+0.2306** (CI [0.2159, 0.245]); under-depth delta mean 0.3994 (CI [0.3775, 0.4209]).
- The independent result is the **Chrollo skill-classification learning curve**. The
  risk-floor comparison is explicitly a **self-consistency diagnostic** (its reference
  rule is implemented by the Supervisor) — **not** an independent effectiveness claim.
- `results/sp2027_rescue/hostfiction_provider_*` = excluded provider pilot (deterministic
  fallback after HTTP 404 `Unknown model`; empty catalog). Operational trace only.

## 6. Excluded / failed / historical / provider-blocked / fallback-only artifacts

| Artifact(s) | Classification | Why excluded from headline claims |
|---|---|---|
| `results/benchmark_report.json` | failed | 158/158 tests failed, avg_score 0.0, run 2026-07-29; retained for provenance only |
| `results/before_openrouter/` | historical | Pre-OpenRouter era outputs |
| `results/human_eval*` directories except `human_eval_scored_20260922_180637_consensus/` | historical / stale | Consensus directory is the only canonical human-eval surface (3.86/5, agreement 0.750, 8/8 above bar per README); other human_eval_scored_* variants are superseded runs |
| `results/cowrie_comparison.json`, `results/external_baseline_cowrie*` (except model-coherent copy), `results/external_baseline_cowrie_guarded_rerun_*` | historical / supporting | Older Cowrie outputs; guarded-rerun variant pending review; not headline |
| `results/apmix_quota_status.json`, `results/apmix_probe_history.jsonl` | operational-trace | Provider catalog drift / unprobed quota; blocks provider-backed claims. Task 8 recheck 2026-10-08T06:03:31Z (`scripts/check_apmix_catalog.py`, exit 2): catalog HTTP 200 lists only `claude-sonnet-4-6-free`; `deepseek-v4-flash-free` and `grok-4.7-free` still missing; quota `not_probed` |
| `results/sp2027_rescue/hostfiction_provider_*`, any `hostfiction_provider_pilot_*` | fallback-only / operational-trace | Deterministic fallback after provider 404; empty catalog; no provider-generated result inferred |
| `data/sessions/*.jsonl` (6,904 on disk; 1,977 untracked) | historical / operational-trace | Session transcripts; not canonical benchmark evidence without ledger mapping |
| `graphify-out/` (`graph.json` sha256 `818c4fb9…`, manifest.json) | operational-trace, stale | Generated 2026-10-03; stale vs dirty worktree; regenerate before use |
| `results/jev_dwell_replay_*` (v1–v7, chunk/llm variants), provider-refusal probes | historical / provider-blocked | Superseded replay attempts; quota 429 traces retained |
| `results/external_baseline_ragin_hostfiction_*checkpoint*.json`, `*limit*_checkpoint.json`, smoke variants | supporting / fallback | Checkpoints and smokes; not the version-of-record |

## 7. Provenance checks (hashes, timestamps, overlap, fallback counts, regeneration)

Observed 2026-10-08 (this ledger's verification pass):

| Artifact | sha256 (first 16) | mtime | Regeneration command |
|---|---|---|---|
| `results/b4_baseline_zodiac_20260922.json` | `8a95d5720874c6a1` | 2026-09-22 20:53:34 | `python scripts/run_baseline_comparison.py` |
| `results/bootstrap_ci.json` | `3ef548a59d80f77b` | 2026-09-22 21:01:11 | bootstrap recomputation over the Sep-22 runs (see `method` block; seed 20260922) |
| `results/graph_consistency_bench.json` | `e8f580f6b9d9b094` | 2026-09-26 19:52:34 | `python scripts/graph_consistency_bench.py` |
| `results/stability_run1_vs_run2.json` | `8d905c0b36f25cd1` | 2026-09-25 16:01:14 | `python scripts/compare_run_stability.py` |
| `results/external_baseline_model_coherent.json` | `2e1541eb226a3939` | 2026-09-27 17:52:09 | model-coherent W1 rerun under `RAGIN_HISOKA_MODEL=deepseek-v4-flash-free` |
| `results/two_channel_metrics.json` | `45b671689e3b1018` | 2026-09-28 11:16:59 | `python scripts/run_two_channel_metrics.py` (218-row live pass; echo-guarded served rescore is offline) |
| `results/verifier_redteam.json` | `8f19dde38c7ea5a2` | 2026-09-27 16:26:11 | `python scripts/verifier_redteam.py` (offline) |
| `results/verifier_redteam_supported_claims.json` | `60e6b599a610a307` | 2026-09-28 20:10:12 | supported-claims regeneration over `scripts/verifier_redteam_cases.py` |
| `results/benchmark_report.json` | `3d86c9a95af20117` | 2026-09-15 20:37:17 | historical; 158/158 failed — do not regenerate as headline |
| `results/jev_hard_subset.json` | `0721223c8bc741d1` | 2026-10-08 07:47:43 | `python scripts/jev_hard_subset.py` (post-Task-3 interpretation) |
| `results/live_benchmark_zodiac_20260922.json` | `fd2830976ea04134` | 2026-09-22 19:57:45 | `python scripts/run_live_benchmark.py` (run twice for stability pair) |
| `results/live_benchmark_judge_panel_corrected.json` | `4f98d122a41d5f71` | 2026-09-25 16:01:14 | `python scripts/rescore_judge_panel.py` |
| `results/ablation_battery.json` | `c89aa8e4476f794b` | 2026-09-26 19:52:53 | `python scripts/ablation_battery.py` |
| `results/mtp_steering_eval.json` | `59b54553bd57f792` | 2026-09-22 13:44:46 | `python scripts/mtp_steering_eval.py` |
| `results/jev_ab_eval.json` | `aa5d2c1d98ebf47a` | 2026-09-20 19:30:25 | JEV A/B evaluation (n=200, deterministic floor ceiling) |
| `results/sp2027_rescue/behavior_trajectory_benchmark.json` | `f6945dee79043258` | 2026-10-03 07:18:12 | `python scripts/sp2027_rescue_behavior_benchmark.py` (provider-free) |
| `results/jev_real_logs_eval.json` | `76fa8f933368e8e7` | 2026-09-20 19:57:06 | JEV real-log audit (13 Cowrie sessions) |
| `results/serve_provenance.json` | `8dfaf033c881ec0d` | 2026-09-23 18:30:04 | serve-path provenance split (verified-generation vs vetted fast-path) |
| `results/external_baseline_comparison.json` | `7e993235d3b93e03` | 2026-09-27 08:25:55 | four-arm W1 baseline, identical deterministic scorers |
| `results/external_baseline_cowrie.json` | `b8577efbb5bdd72f` | 2026-09-27 08:25:09 | Cowrie arm of W1 |
| `results/vor_guarded_served_text_lower_bounds.json` | `7017d8b1c3a8dcc6` | 2026-09-29 09:40:49 | offline echo-zeroed bounds over stored VOR previews |

Train/test overlap: the rescue benchmark and JEV hard-subset census both read
`data/training/test.jsonl` (400 sessions) held out from `data/training/train.jsonl`;
corpus sha256 values recorded inside the artifacts (`046d9b19…` test, `e5bf8a71…` train).
No session JSONL on disk is counted as benchmark evidence.

Fallback counts: model-coherent `ragin_full` serve-path tally GENERATED_VERIFIED 216 /
FALLBACK_VERIFIED 2 (hostfiction 213/5); two-channel run tally GENERATED_VERIFIED 216 /
FALLBACK_VERIFIED 2; serve provenance separates verified generation from vetted
deterministic fast-paths.

## 8. Verification (Step 6)

- Artifact-consistency tests: `pytest tests/unit/test_artifact_consistency.py -q`
  (AC1–AC5 banners, including Task 3's JEV counts/resolution lock).
- Supported-claim tests: `pytest tests/unit/test_supported_claims.py -q`
  (grading of the red-team artifacts and supported-claim consistency).
- Every headline row in §1–§5 was manually inspected against its source JSON field
  (this document's numbers are transcribed from the parsed JSON, not from README/paper
  text).

## 9. Non-claims

- This ledger records artifact-backed numbers and their bounded interpretations. It does
  **not** establish scientific validity, causal identification, independent replication,
  cross-model causal effects, or venue readiness.
- The echo-guarded served technique/actor correction is **not** a re-run; the full
  guarded two-channel campaign requires a live 218-row pass.
- Provider-blocked artifacts (apmix quota/catalog, hostfiction provider pilots, JEV
  retry-exhausted rows) are operational traces and cannot support provider-backed claims.
- As of the Task 8 recheck (2026-10-08T06:03:31Z, exit 2), the apmix catalog still
  lists only `claude-sonnet-4-6-free`; the wired `deepseek-v4-flash-free` /
  `grok-4.7-free` models are absent and quota is unprobed. Provider-backed reruns are
  blocked; the SP2027 rescue benchmark remains provider-free/fallback-only evidence.

---

## Addendum 2026-10-24 (post-audit corrections)

Recorded after the 2026-10-24 full verification audit (10 targets, independent
confirmer per non-clean verdict). Original rows above are preserved verbatim;
the corrections below supersede them where stated.

1. **bootstrap_ci.json hash.** The §7-recorded sha256 for
   `results/bootstrap_ci.json` is stale — the file was regenerated after this
   ledger was written. Current hash: `b929b76dd184d9f2…`. All counts claimed
   for it still hold inside the current file; note it holds **6 proofs (all
   passing)**, not "5/5" as sometimes quoted.
2. **§1 "deception unchanged on audited rows" is not supported.**
   `results/stability_run1_vs_run2.json` records deception 0.7433→0.7621 on
   audited rows (Δ +0.0187) and 0.7325→0.7504 raw — i.e. *relative* stability
   across runs, not "unchanged". Composite (+0.005) and pass-agreement (0.991)
   claims stand.
3. **§6 session counts superseded.** As of 2026-10-24:
   7,659 files under `data/sessions` (live directory, still growing); the
   earlier 6,904/1,977 figures are historical.
4. **Provider-blocked narrative outdated.** The latest
   `results/apmix_probe_history.jsonl` entries (2026-10-24) show
   `catalog_status: ok`, `quota_status: live`, `models_missing: []`. The
   Task 8 provider-blocked state no longer holds.
5. **graphify-out/graph.json** was regenerated (2026-10-23/24 AST updates);
   any §6 hash recorded for it is historical.
6. **Evaluation-chain labeling.** All "human eval"/"3-evaluator" references to
   the 3.86/5 consensus have been relabeled **LLM-judge evaluation (3 personas,
   grok-4.7-free)** — no human raters exist anywhere in the chain, and
   `results/human_eval_scored/consensus.json` is superseded (false provenance
   note corrected; see `results/human_eval_scored/CORRECTION.md`).
