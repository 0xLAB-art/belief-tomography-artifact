# RAGIN — Hard IEEE S&P Review (post-revision audit)

**Review date:** 2026-10-08 (second round, same day as `SP2027_HARD_REVIEW_2026-10-08.md`)
**Submission surface audited:** `paper/sp2027.tex` → `sections/{introduction,sp_threat_model,design,sp_evaluation,conclusion,sp_appendix}.tex` + `references.tex`; compiled `paper/sp2027.pdf`, 12 pages, `sp2027.log` clean (0 errors, 0 undefined references).
**Manuscript state:** post-fix. `sp2027.tex`, `sp_threat_model.tex`, `sp_evaluation.tex`, `sp_appendix.tex`, `introduction.tex`, `background.tex`, `conclusion.tex`, `two_channel_tables.tex` were rewritten 09:57–10:01 today, *after* the 09:46 prior review. HEAD = `f01a4a9`.
**Extended companion:** `paper/main.tex` + `paper/sections/*.tex` (27 pp, author-identified) — read only for context, not judged as the submission.

## Provenance of this audit (disclosed, not hidden)

The intended 5-seat panel (Journal-Fit, Methodology, Security Domain, Systems/Reproducibility, Devil's Advocate) was dispatched and **all seven delegated runs failed** on provider quota (`APIError: The usage limit has been reached`, primary model `openai/gpt-6-astra` and fallback `openai/gpt-5.6-sol`, attempts 1 and 2). This audit was therefore produced as a **single-auditor pass with direct tool verification**, not a role-separated panel. Consequence you must weigh: there is no cross-model or cross-role corroboration here, and correlated blind spots are possible. Every number below was recomputed from disk artifacts by the auditor, not taken from the paper's prose.

**Read-only confirmed:** no manuscript, artifact, script, or config file was modified. No test suite was executed. No git mutation.

---

## Decision

**Major Revision** (borderline Reject). The revision round genuinely fixed the two structural defects that were blockers in the 09:46 review — the threat model is now a real section with an explicit property/evidence/nonclaim table, and the paired grounding experiment now has a persisted, audited pairing contract whose CIs reproduce exactly. Those are the two things I said were unfixable without new experiments, and they were fixed.

What remains is narrower and more tractable than a rejection, but it is not cosmetic: **the paper's headline capability numbers and the paper's own scorer audit describe two different surfaces, and only one of them is disclosed.** The version-of-record campaign (Table `tab:live`, composite 0.880) carries echo-contaminated both-channel scores whose guarded correction — computed by the authors and present in the release — is **0.479 technique / 0.243 actor, and is not disclosed anywhere in the submitted paper.** The 0.057 / 0.000 figures the paper does report come from a *different, later re-run under a different generator model*. That substitution, plus a latency-inferred serve-path split that contradicts the label-based provenance by ~11×, is what stands between this submission and an Accept.

---

## What the revision round actually fixed

| Prior finding (09:46) | Status | Evidence from this audit |
|---|---|---|
| F1 threat model absent / under-specified | **FIXED** | New `sp_threat_model.tex`; `tab:threat-boundary` maps property → attacker pressure → evidence → explicit nonclaim; host compromise / container escape / provider compromise / operator collusion placed outside the certified property. |
| F2 paired ablation not auditable | **FIXED, verified** | `scripts/bootstrap_ci.py:146-201` implements a real `pairing_audit` (exact key-set equality, duplicate detection, suite-membership equality, never positional). `results/bootstrap_ci.json` records `ok:true`, `symmetric_set:true`, `suite_membership_ok:true`, 90/90 unique per arm. I independently confirmed: sets equal, 90 unique names each arm, only **14/90 rows in identical position** — so pairing by name is necessary and correct. All four reported CIs reproduce exactly (below). |
| F3 reproduction surface / artifact paths | **PARTIALLY FIXED** | All 11 `\path{}` targets in `sp_appendix.tex` **exist on disk** (verified individually). Still no artifact locator in the anonymous version, so a reviewer cannot obtain any of it. |
| F4 headline mixes served-text and analysis channels | **PARTIALLY FIXED — new problem created** | Abstract now says "we do not claim a clean served-intelligence gain" and `tab:baseline-served-text` is captioned "raw served-text composites". But the abstract still carries `+0.116` computed from those raw composites, and the audit corpus's guarded numbers are substituted for the version-of-record rows' guarded numbers (see N1, N2). |
| F5 quality validation is single-model | **DISCLOSED, UNRESOLVED** | `sp_evaluation.tex:114-121` now states plainly it is "within-model consistency, not human inter-annotator agreement" and "no human study is claimed". Correctly demoted; still no human validation. |
| F6 baselines / related work insufficient | **NOT FIXED** | Worse than before: the submitted surface has **7 in-text citations, all in the introduction**, zero in design/evaluation/conclusion, and **no related-work section at all**. |
| F7 adaptive ladder does not show security benefit | **FIXED BY DEMOTION** | `sp_threat_model.tex:54-58` labels the ladder and rescue benchmark "exploratory controller diagnostics"; `sp_evaluation.tex:168-176` states the trajectory audit's risk floor "uses the controller's own explicit hostile-pattern rule as its reference" and is "not used as a headline security gain". Honest. |
| F8 external validity too narrow | **PARTIALLY FIXED** | Deployment is tailnet-only; I confirmed **no field VM has ever existed** (`docs/AZURE_FIELD_STATUS.md`: "no field VM exists yet", subscription `ReadOnlyDisabledSubscription`). Paper no longer implies field data. |

---

## Verified-claims ledger

Recomputed by the auditor from disk. `bootstrap_ci.json` was written 09:55 today; artifacts verified byte-level via `json.load`.

### CONFIRMED — reproduce exactly

| Paper claim | Location | Artifact value | Verdict |
|---|---|---|---|
| Technique +0.317 [+0.162,+0.480] | `sp_evaluation.tex:37` | `paired_diff_ci.cti_technique` = +0.3167 [0.1617, 0.4800], n=30 | **CONFIRMED** |
| Actor +0.140 [+0.083,+0.197] | `:38` | `cti_actor` = +0.1400 [0.0833, 0.1967], n=30 | **CONFIRMED** |
| Persona +0.005 [-0.047,+0.057] | `:39` | `deception` = +0.0050 [-0.0467, 0.0567], n=30 | **CONFIRMED** |
| Overall +0.154 [+0.092,+0.221] | `:41` | `overall` = +0.1539 [0.0922, 0.2206], n=90 | **CONFIRMED** |
| RAG/No-RAG means 0.950/0.633, 0.850/0.710, 0.833/0.828 | `:37-39` | `rag_avgs` / `no_rag_avgs` identical | **CONFIRMED** |
| Live: technique 0.960, actor 0.850, persona 0.733, composite 0.880 | `:75-78` | `stability_run1_vs_run2.json` run_a = 0.9598 / 0.85 / 0.7325 / 0.8796 | **CONFIRMED** |
| 218 sessions engaged, 218/218 persona assignments correct | `:58-59` | `sessions_with_engagement` 218, `persona_correct_assignments` 218/218 | **CONFIRMED** |
| 132 detections, 67 unique techniques | `:52` | `ttps_detected` 132, `ttps_detected_unique` 67 | **CONFIRMED** |
| Stability +0.005, 0.991 agreement | `:178-180` | composite 0.8796→0.8845 (Δ 0.0049), `pass_agreement` 0.9908 | **CONFIRMED** |
| Technique/actor strata "reproduce exactly"; persona MAD 0.096 | `:180` | both suites `mean_abs_row_diff` 0.0, `pass_agreement` 1.0; deception MAD 0.0962 | **CONFIRMED** |
| Ladder 0.001 / 0.070 / 0.502 / 0.618 / 0.618 / 0.618 | `:135-140` | `external_baseline_model_coherent.json`: 0.0006 / 0.0704 / 0.5018 / 0.6176 / 0.6176 / 0.6176 | **CONFIRMED** |
| Grounding adds +0.116 over bare LLM | `:146`, abstract | 0.6176 − 0.5018 = +0.1158 | **CONFIRMED arithmetically** (but see N2 — both operands are unguarded raw composites) |
| Cross-family P/R/CI, all three families | `:95-97` | space-bunny 89/261 P 1.000 R 0.9585 [.9204,.9788]; deepseek 80/236 P 1.000 R 0.9827 [.9503,.9941]; llama 94/281 P 0.9158 R 0.8981 [.8492,.9324] | **CONFIRMED** |
| 105-case suite perfect; 78 reject + 27 pass | `:98`, `:104` | `verifier_redteam.json`: 78 should_reject / 27 should_pass, P=R=1.0, `all_gates_pass` | **CONFIRMED** |
| Echo audit: 97/218 rows, technique 0.524→0.057, actor 0.680→0.000, deception unchanged | `:150-152` | `cti_manual_audit_corpus.json`: 97 changed; technique 0.5236→0.0569; actor 0.6800→0.0000; deception 0.6492→0.6492 | **CONFIRMED** |
| Analysis channel unchanged 0.960 / 0.850 | `:153` | `cti_analysis` means 0.9598 / 0.8500 pre and post guard | **CONFIRMED** |
| 45 re-queries, zero contradictions; top-3 0.9 | `:56`, `intro:167` | proofs `CI_c1_contradiction_upper_below_10pct` (0/45), `CI_c3_top3` (9/10) | **CONFIRMED** |
| All 11 appendix artifact paths resolve | `sp_appendix.tex` | all EXISTS | **CONFIRMED** |

### NOT DISCLOSED IN THE PAPER (exists in the release, absent from the submission)

| Value | Artifact | Why it matters |
|---|---|---|
| **VOR guarded lower bounds: technique 0.4785 (run1) / 0.4553 (run2); actor 0.2429 / 0.170** | `results/vor_guarded_served_text_lower_bounds.json` | These are the echo-guarded bounds **for the very rows that populate Table `tab:live`**. The paper reports only the pooled re-run collapse (0.057 / 0.000). This is the single most important omission in the submission — see N1. |
| 61 echo rows (technique) and 25 (actor) in the VOR run | same artifact | Quantifies how much of the version-of-record campaign is template echo. |
| 216 `GENERATED_VERIFIED` + 2 `FALLBACK_VERIFIED` | `cti_manual_audit_corpus.json`, `external_baseline_model_coherent.json` (`ragin_full`) | Label-based serve-path provenance for the same configuration, contradicting the paper's latency-derived 88.1/11.9 — see N3. |
| Ladder arms served 218/218 `GENERATED_UNVERIFIED` (no-verifier) vs 216 verified (full) | `external_baseline_model_coherent.json` | The verifier's actual behavioural footprint on the workload: it rejected **zero** drafts. |
| `verifier_contribution_same_model`: `composite_delta` 0.0, `paired_mean_row_delta` 0.0 | same | Byte-identical served text across the verified and unverified arms — the safety gate is a no-op on this workload. See N6. |
| Generator model differs per artifact | `historical_reference_sep22` = "unrecorded (gateway default, pre-deepseek pin)"; ladder = `deepseek-v4-flash-free`; audit corpus config = "gateway default glm-5.3-flash-free" | Three headline artifacts, three generators. See N4. |

---

## Findings

Severity is against IEEE S&P acceptance, not against a workshop.

### N1 — CRITICAL — The headline capability table and the paper's own scorer audit describe different surfaces, and the version-of-record correction is withheld

**Anchors:** `sp_evaluation.tex:65-81` (Table `tab:live`) vs `:150-152`; `results/vor_guarded_served_text_lower_bounds.json`; `results/cti_manual_audit_corpus.json` (`config.generator_model`).

Table `tab:live` reports technique **0.960**, actor **0.850**, persona 0.733, composite **0.880**, all from `live_benchmark_zodiac_20260922.json`. The caption correctly says this is a "both-channel" measure. The authors' own offline echo guard, applied to *those rows*, yields technique **0.4785** and actor **0.2429** (run 1), 0.4553 / 0.170 (run 2) — roughly a 50% collapse, with 61+25 and 64+ rows identified as template echo respectively.

What the paper reports instead is 0.524→0.057 and 0.680→0.000. Those come from `cti_manual_audit_corpus.json`, which is a **fresh re-run under `glm-5.3-flash-free`**, not the archived version-of-record rows. The two are related (same workload, same rubric, equal scores on the audited surface) but they are not the same surface, and the re-run collapses *further*. A reader of the submission sees a dramatic correction and reasonably concludes the version-of-record numbers are near-zero; the paper never says the dramatic correction was measured on a different run, and never reports the ~0.48 / ~0.24 figures at all.

Compounding it: `results/vor_guarded_served_text_lower_bounds.json` states in its own `what` field that stored VOR scores are BOTH-channel and that the preview-truncated re-scoring yields "a lower bound on the BOTH-channel composite after the echo correction, not a guarded served-text mean" — i.e. even 0.4785 is a *lower bound*, not the guarded served-text mean. The true guarded value for those rows is lower still and was never computed.

**Remedy (all four, or the finding stands):** (a) report the VOR guarded bounds 0.479/0.455 and 0.243/0.170 next to Table `tab:live`, labelled as lower bounds; (b) state explicitly that the 0.057/0.000 figures are from a re-run under a different generator model, not the VOR rows; (c) stop presenting 0.960/0.850 as capability figures anywhere, including the abstract's grounding sentence; (d) either persist full served text for the VOR rows and recompute a true guarded mean, or permanently label Table `tab:live` as a both-channel operational score and never compare it to served-text or analysis numbers.

### N2 — CRITICAL — The abstract's `+0.116` is computed from the exact metric the paper proves is invalid, and its guarded counterpart is not computable from the release

**Anchors:** `paper/sp2027.tex:57-60`; `sp_evaluation.tex:131-143`; `results/external_baseline_model_coherent.json`.

The abstract states: "In a same-model archived served-text comparison, grounding adds +0.116 composite over a bare LLM." Table `tab:baseline-served-text` is captioned "values are raw served-text composites", and `sp_evaluation.tex:150-152` then shows that raw served-text technique (0.524) and actor (0.680) scores collapse to 0.057 and 0.000 under the echo guard — a 89% and 100% reduction. So the two operands of the paper's only served-text causal delta are the two numbers the paper demonstrates are almost entirely artefact.

This cannot be repaired by recomputation: `external_baseline_model_coherent.json` is an 8 KB summary (arm-level means, no row bodies, no served text), so the guarded differential for the ladder is **not derivable from the released artifacts**. The extended companion already knows this and says so; the submitted paper does not.

**Remedy:** remove `+0.116` from the abstract, or restate it as an archived raw-served-text comparison explicitly invalidated by the project's own audit. If a served-text grounding number is wanted, re-run the ladder arms with full served-text persistence under the guarded scorer and report that. Do not ship a headline number that the paper's own §Evaluation invalidates eight paragraphs later.

### N3 — MAJOR — Serve-path provenance is reported from a latency inference that contradicts the label-based provenance by ~11×

**Anchors:** `sp_evaluation.tex:60-63`; `introduction.tex:180-182`; `results/serve_provenance.json`; `results/cti_manual_audit_corpus.json`.

`sp_evaluation.tex:60` reports "Latency provenance estimates 88.1% verified-generation and 11.9% vetted deterministic serves in run 1 (87.2/12.8% in run 2)". `results/serve_provenance.json` reveals the method: `"latency split: gateway round-trip dominates any LLM-in-the-loop turn; vetted fast-paths complete well under 4 s"` at `threshold_ms: 4000`. It is a **classifier on wall-clock time**, not a provenance label.

The released provenance labels for the same 218-row workload under the same `ragin_full` configuration are **216 `GENERATED_VERIFIED` + 2 `FALLBACK_VERIFIED`** (99.1% / 0.9%) — agreeing across two independent artifacts, with 213+5 when host fiction is on. The paper's own submission plan records that the latency-derived split was adopted *because* the template-dominated rows were miscounted as verified; the label-based count is the one the code now stamps, and it disagrees by an order of magnitude in the vetted-deterministic bucket.

The introduction goes further and states the inference as fact: "a latency-derived serve-path provenance analysis attributes 88% of serves to verified generation with zero fallback serves."

**Remedy:** make the label-based count primary (it exists, it is stamped per row, it is in two artifacts); demote the latency inference to a footnote with its 4 s threshold and its failure mode stated; fix `introduction.tex:180-182` to stop attributing 88% of serves to verified generation.

### N4 — MAJOR — Three headline artifacts were produced by three different generator models, undisclosed

**Anchors:** `sp_evaluation.tex:15-19`; `results/external_baseline_model_coherent.json` (`historical_reference_sep22.generator_model`), `results/cti_manual_audit_corpus.json` (`config.generator_model`).

The paper describes "one free-tier provider" with "the generator and judge us[ing] different model families". In fact: the version-of-record campaign ran on an **unrecorded gateway default** (explicitly "pre-deepseek pin"); the ladder ran on `deepseek-v4-flash-free`; the scorer audit re-ran on `glm-5.3-flash-free`. Table `tab:live`, Table `tab:baseline-served-text`, and the echo-guard correction are three different generators.

This is exactly the cross-model contamination the authors already caught and corrected once — `external_baseline_model_coherent.json`'s `motivation` field documents that mixing generator models "inflated the grounded arms' technique scores" and required regenerating the whole W1 table. The same discipline has not been applied to the VOR campaign or to the audit corpus relative to each other.

**Remedy:** add a one-line model provenance table (artifact → generator model → gateway → date), and state that the VOR campaign's generator was not recorded. This is a disclosure obligation, not an experiment.

### N5 — MAJOR — The novelty claim cannot be assessed: no related work, 7 citations, 54 uncited references

**Anchors:** `paper/sp2027.tex:78-85` (no `\input` of any related-work file); `sections/introduction.tex` (all 7 `\cite` commands); `references.tex` (61 `\bibitem`s); `paper/sections/related.tex` exists in the companion and is **not** included.

`sp2027.tex` inputs introduction, threat model, design, evaluation, conclusion, references, appendix. There is no related-work section; `design.tex`, `sp_evaluation.tex`, `conclusion.tex`, `sp_threat_model.tex` and `sp_appendix.tex` contain **zero** citations. All in-text citations are in the introduction and number seven (`lopez2024`, `ibm2024`, `crowdstrike2026`, `reworr2024`, `ganguli2022`, `bai2022`, `greshake2023`). Because `references.tex` is a manual `thebibliography`, **all 61 entries render** — the submitted PDF's reference list is ~90% uncited work, including `spitzner2002` (honeypot fundamentals), `valeros2024` ("LLM in the Shell: Generative Honeypots"), `xue2024` (BadRAG), `kouremetis2024` (Mirage), `zheng2024`, `shi2024` (optimization-based prompt injection). Not one is engaged in the submitted text.

An S&P reviewer cannot determine what is new. This is a desk-reject-grade gap at a top-tier venue, independent of any experimental issue.

**Remedy:** add a related-work section (~1 page) organised as a positioning matrix against: LLM/generative honeypots, LLM-in-the-shell honeypots, deception-framework surveys and fidelity metrics, prompt-injection and jailbreak attack/defence, retrieval poisoning and attribution, guardrail/verifier/runtime-enforcement architectures, and retrieval-engine comparisons. Cite the entries already collected in `references.tex` and delete or `\nocite`-suppress the rest.

### N6 — MAJOR — "Verification buys safe serving" has no harm-avoidance measurement anywhere in the paper

**Anchors:** `sp2027.tex:57-60` (abstract), `sp_evaluation.tex:145-149`; `results/external_baseline_model_coherent.json` → `regenerated_claims.verifier_contribution_same_model`.

The paper's central thesis has three parts: grounding buys intelligence, verification buys safe serving, the deterministic floor absorbs provider failure. Parts one and three have measurements. Part two does not:

- The verifier arm and the no-verifier arm produced **byte-identical served text on all 218 rows** (`composite_delta` 0.0, `paired_mean_row_delta` 0.0; the artifact's own mechanism note explains the gate is not in the prompt and the fiction seeds match).
- On that workload the verifier rejected **zero** drafts (216 `GENERATED_VERIFIED`, 2 vetted deterministic).
- The only evidence for the gate is `verifier_redteam.json` — 105 self-authored cases (78 reject / 27 pass) — and the 123-case suite, which is self-authored by the same authors.

There is no experiment in which a harmful draft is generated, the verifier catches it, and the harm is shown to be prevented in a live serve. "Verified serving" is therefore a design property demonstrated on the authors' own specification examples, not a measured security outcome.

**Remedy:** either add one experiment that shows harm prevention on the live path (inject/induce N drafts that *would* violate the fiction or leak, show the gate rejecting each and the fallback serving instead, with the counterfactual "what would have been served"), or restate the claim as: the gate is a deterministic filter whose coverage is characterised on self-authored suites, and its incremental effect on the evaluated workload was zero. Both are publishable; the current wording is not.

### N7 — MAJOR — The verifier recall CIs are Wilson intervals over draft-clustered data, computed with a different method than the one the paper declares

**Anchors:** `sp_evaluation.tex:10-11`, `:91-101`; `results/verifier_redteam_cross_family.json` (`wilson95` fields).

`sp_evaluation.tex:10-11` declares the method: "paired confidence intervals use 10,000-resample percentile bootstrap over scenario-level differences." That is correct for Table `tab:b4` (verified above) and for the live campaign. It is **not** the method behind Table `tab:verifier-cross-family`: those CIs are Wilson score intervals (`wilson95.recall` etc.) computed over `valid_drafts` — 281 drafts across 94 cases for llama, 261/89, 236/80. Drafts within a case are not independent (several variants per case, per the artifacts' own "per-draft rescore with per-case dedup" history), so a binomial interval on the draft count is too narrow. The llama recall CI `[.849,.932]` should be materially wider under a cluster bootstrap.

**Remedy:** compute recall/precision CIs by cluster bootstrap over cases, state the unit of resampling in the caption, and correct the blanket method sentence so it does not describe the verifier table.

### N8 — MODERATE — The threat model claims prompt-injection coverage backed by a single case

**Anchors:** `sp_threat_model.tex:37-39`; `results/verifier_redteam_supported_claims.json`.

Table `tab:threat-boundary` row "Supported claims" declares the attacker pressure as "**Prompt injection** and unsupported command answers" and the evidence as "123 supported-claim cases and cross-family authored-draft stress test". I tallied the 123-case suite's categories: `D` 47, **`evasion` 46**, `I` 13, `C` 12, `D-` 10, `I-` 10, `SC` 9, `SC-` 7, `C-` 7, `D+` 4, `E` 2, `SCx-` 2, **`injection` 1**.

Prompt injection — an attacker class the threat model explicitly places in scope at `sp_threat_model.tex:6-8` ("inject instructions through commands or retrieved content") — is represented by **one** case in the cited evidence. The threat model also puts CTI/retrieval poisoning in that same clause; there is no poisoning evaluation in the release at all.

**Remedy:** either add injection and poisoning cases (indirect injection via command text and filenames reaching the retrieval query; poisoned CTI changing the fiction) or move both out of the declared in-scope attacker set and say so. Declaring an attacker class and then citing n=1 evidence for it is worse than not declaring it.

### N9 — MODERATE — The "fail-closed completeness" property covers eight commands

**Anchors:** `ragin/cycle/supported_claims.py:274-283`; `sp_threat_model.tex:38`.

The declared surface is `_HANDLERS = {whoami, id, hostname, uname, echo, uptime, date, cat}`, with `cat` narrowed by `_OS_RELEASE_PATH_RE` to `/etc/os-release` and `/usr/lib/os-release` only. `supported_command()` returns `None` for everything else, and `check_supported_claim()` returns `[]` — **no completeness requirement at all** outside those eight commands. The threat model states the nonclaim honestly ("Closed-surface recall only"), but the introduction's contribution bullet advertises "a completeness-verifying supported-claim gate measured at precision and recall 1.0 over a 123-case suite" with no surface size attached, and the abstract calls the 105-case suite "perfect" with no qualifier at all.

**Remedy:** state "8-command declared surface" in the abstract and contribution bullet wherever the 1.0 figures appear, and add the open-ended recall caveat to the abstract sentence rather than only to §Evaluation.

### N10 — MODERATE — The danger gate is a style-tell detector, and the case suite is dominated by style tells

**Anchors:** `ragin/cycle/verifier.py:55-63`; `results/verifier_redteam.json` (`categories`).

`_check_danger_signals` fires on `_contains_danger_signal(text)` plus a regex for `as an ai|assistant|language model` and `i cannot assist`. The 105-case suite allocates 51 of 78 reject cases to the `danger` check, and one sampled case is `E-empty` (empty response). The gate detects *tells and refusal phrasing*, which is genuinely important, but a fluent, confident, semantically harmful draft with no tell sails through — and the identity/consistency checks are per-turn against the fiction graph the system itself authored, so a globally coherent lie is not caught by construction.

**Remedy:** say what the danger gate does and does not detect, and add one category of "coherent but harmful" drafts (no tell, on-fiction, leaks a real secret or an off-script capability) to show where the gate's coverage actually ends. Reporting the boundary is worth more than the 1.0.

### N11 — MINOR — Estimand/weighting mismatch between the ablation and the deployed workload

**Anchors:** `sp_evaluation.tex:20-22` vs `:65-81`.

The ablation is balanced 30/30/30, so `+0.154` is a balanced-stratum mean difference. Table `tab:live`'s 0.880 is workload-weighted over 123/35/60 (56%/16%/27%). The two composites are not the same estimand and the paper does not say so. **Remedy:** one sentence fixing the estimand, or report the deployment-weighted ablation difference.

### N12 — MINOR — No multiplicity control across three strata plus overall

**Anchors:** `sp_evaluation.tex:33-44`.

Four intervals are reported with no adjustment and no discussion. The two positive intervals are far from zero, so the conclusion survives any reasonable correction, but the persona null and the overall are read as if pre-registered. **Remedy:** state that no correction is applied and why it is immaterial, or apply Holm.

### N13 — MINOR — Figure values are hand-written, not generated

**Anchors:** `paper/figures/results.tex:33-44,72-75`; `figures/ladder.tex:32`; `figures/grounding.tex:18-32`.

Every plotted number is a literal in the figure source (`0.9598`, `0.8500`, `0.7325`, `0.8796`, `+0.154`, `0.8875→0.9550`). `figures/ladder.tex:4` even says "all values are hardcoded here only". They currently match the artifacts — I checked — but nothing prevents drift, and `scripts/gen_two_channel_tables.py` regenerates tables only. `figures/results.tex` also plots the both-channel numbers with **no channel label**, while Table `tab:live`'s caption carries one. **Remedy:** generate figure data from artifacts in the same script that generates the tables, and label the channel in the figure.

### N14 — MINOR — Two different 0.955 values, one unexplained

**Anchors:** `introduction.tex:138-139` ("routing accuracy rises from 0.8875 to 0.9550") vs `sp_evaluation.tex:170-171` ("Final Chrollo skill accuracy is 0.955").

The introduction prices the routing rung at 0.9550; the evaluation reports 0.955 for a trajectory-audit endpoint. If these are one measurement the intro should cite it; if two, they need separate labels. **Remedy:** disambiguate.

### N15 — MINOR — No artifact locator means none of the above is checkable by a reviewer

**Anchors:** `sp_appendix.tex:5-16`; `introduction.tex:185-186`.

The appendix promises repository paths and the anonymous version "omits a public artifact locator". Every claim in this audit — including the N1 omission — was discoverable only because I had the tree. **Remedy:** provide an anonymous mirror (as the companion already promises) or state in the paper that the artifact will be released on acceptance, and soften "headline numbers traceable to persisted result files" accordingly.

---

## Devil's Advocate CRITICAL issues, adjudicated visibly

**DA-1 (CRITICAL) — the verifier is inert on the evaluated workload.** Adjudicated **VALIDATED**. `verifier_contribution_same_model` records `paired_mean_row_delta` exactly 0 across 218 rows and 216 `GENERATED_VERIFIED` / 2 vetted, i.e. the gate changed nothing that was served. The safety claim rests entirely on self-authored suites. Carried as N6. This alone blocks Accept.

**DA-2 (CRITICAL) — the served-text grounding gain is an artefact.** Adjudicated **VALIDATED, and worse than the paper concedes**. The echo guard removes 89% of the technique score and 100% of the actor score on the ladder arms, and the version-of-record rows' own guarded bounds (0.479 / 0.243) are withheld. Carried as N1 and N2.

**DA-3 (MAJOR, rejected as a blocker, retained as framing guidance) — the paper's own ladder says "don't use the LLM".** Multiple intelligent rungs fold down: routing "was removed from serving after deterministic fixes reproduced its decision floor" (`sp_evaluation.tex:164-165`), BM25 beats the graph index on NDCG (`:165-166`), the rescue controller is subsumed. A hostile reading is that the honest conclusion is "prefer determinism", which would be a different and arguably more valuable paper. Adjudication: **not a defect** — the fold-down results are disclosed, they are the most intellectually honest content in the evaluation, and the "certifiability axis" framing is consistent with them. The problem is only that the abstract still sells generative value (+0.116, "grounding buys intelligence") that the served-text channel does not support. Carried inside N2; no separate roadmap item.

**DA-4 (MAJOR) — novelty is unreadable.** Adjudicated **VALIDATED**. N5.

---

## Claim-boundary table (wording the current evidence supports)

| Claim as written | Status | Defensible wording now |
|---|---|---|
| Grounding lifts analysis-channel composite +0.154 [+0.092,+0.221] (abstract, Table `tab:b4`) | **Fully supported** — pairs audited, per-row persisted, CIs reproduce bit-for-bit | Keep as is. Strongest result in the paper. |
| 35 TTP detections spanning 21 techniques vs 0 without retrieval | Supported | Keep. |
| Live composite 0.880 / technique 0.960 / actor 0.850 | Supported **as a both-channel operational score**; served-text capability ≈0.06/0.00 on the audited re-run, ≤0.479/0.243 lower bound on VOR rows | Must carry the channel label, the guard result, and the VOR bound at every appearance. |
| "Grounding adds +0.116 over a bare LLM" (abstract) | **Not supported as served-text capability** | Delete, or state "archived raw served-text comparison, invalidated by the project's own echo audit; guarded differential not computable from the release". |
| "Verification buys safe serving" | Design property, unmeasured on this workload | "The gate rejected no draft in the 218-row workload; its coverage is characterised on self-authored deterministic suites, and its incremental effect on the evaluated workload was zero." |
| 88% of serves are verified generation | Inferred from latency, contradicted by labels | "Persisted provenance labels record 216/218 verified-generation on this configuration; a latency-based cross-check estimates 88/12 at a 4 s threshold." |
| 105-case suite perfect / 123-case suite P=R=1.0 | Supported on self-authored suites over an 8-command surface | Add "self-authored, closed surface" to the abstract. |
| Persona realism 3.86/5 | Within-model diagnostic | Keep current wording — it is already correctly bounded. |
| Stable across runs (+0.005, 0.991) | Supported | "Reproducibility on a fixed deterministic scenario set; measures template and scorer stability as much as system stability." |
| Timing fingerprintable at AUC 0.983 | Supported, under-disclosed in consequence | Pair it explicitly with the mitigation status (0.551 padded) in the threat model. |
| System reproducible | Partial | "All claims are backed by persisted artifacts in the author repository; reviewer access depends on the anonymised mirror." |

---

## Revision roadmap (non-ranking)

**P0 — required before this can be accepted**
1. Resolve N1: disclose the VOR guarded lower bounds (0.479/0.455 technique, 0.243/0.170 actor) beside Table `tab:live`, state that the 0.057/0.000 figures are from a re-run under a different generator model, and stop using 0.960/0.850 as capability numbers.
2. Resolve N2: remove or heavily caveat `+0.116` in the abstract.
3. Add the related-work section and cut the bibliography to what is cited (N5).
4. Resolve N6: add one live harm-prevention experiment, or restate "verification buys safe serving" as a design property with zero measured incremental effect.
5. Fix the serve-path accounting (N3) and add the model-provenance table (N4).

**P1 — required for the security argument to hold**
6. Move prompt injection and CTI poisoning into the evaluated set at a defensible n, or out of the declared attacker scope (N8).
7. Recompute verifier recall/precision CIs by cluster bootstrap over cases and correct the method sentence (N7).
8. State the 8-command declared surface in the abstract wherever P=R=1.0 appears (N9), and add a "coherent but harmful" draft category to bound the danger gate (N10).

**P2 — hygiene**
9. Generate figure data from artifacts and label the channel in `figures/results.tex` (N13).
10. Disambiguate the two 0.955 values (N14); fix the estimand sentence (N11); note the absence of multiplicity control (N12).
11. Publish the anonymous mirror (N15).

---

## Scorecard

| Dimension | Score (0-100) | Δ vs 09:46 | Basis |
|---|---:|---:|---|
| Security relevance | 74 | −4 | Real problem, but the certified property is narrower than the framing and the verifier's incremental effect is zero on the evaluated workload. |
| Novelty | 34 | −34 | No related work, 7 citations, 54 uncited references — novelty is unassessable, not merely weak. |
| Significance | 60 | −3 | Honest fold-down results are valuable; no field or adversarial-traffic evidence. |
| Technical quality | 70 | +12 | Architecture is real, code is disciplined, the pairing audit and CI machinery are genuinely good. |
| Methodological validity | 61 | +23 | Pairing and CI provenance now verify exactly; destroyed by the undisclosed VOR correction, the channel-mixed abstract number, and the clustered Wilson intervals. |
| Reproducibility | 55 | +13 | All artifact paths resolve and the paired CIs re-derive; but no locator, no guarded ladder recomputation, archived-only live numbers. |
| Clarity | 68 | −4 | Much more candid than the prior round; the abstract still carries a number the paper invalidates. |
| **Overall** | **58** | **+13** | Major Revision. |

---

## What this paper gets right (no manufactured balance)

1. **The revision round closed two hard blockers honestly.** The threat-model section with an explicit property/evidence/nonclaim table, and the pairing audit with persisted per-row scores and a documented seed, are exactly what the prior round demanded. Both verify.
2. **The self-audit is the best thing in the paper.** Discovering that your own machine scorer credits technique IDs inside echoed query text, correcting 97/218 rows, and reporting a κ improvement from −0.187 to +0.349 is a genuine contribution to measurement practice, and it is disclosed against the authors' interest.
3. **The fold-down results are reported against interest.** Routing removed from serving, BM25 beating the graph index, the self-referential risk floor declared self-referential and excluded from headline claims. Reviewers should reward this.
4. **The closed-surface nonclaims are specific and correct** — not "limited evaluation" hand-waving but named boundaries with the evidence attached.
5. **The code is disciplined.** Fail-closed direction on internal errors, seed offsets made process-stable, a pairing audit that refuses positional matching, provenance labels stamped per serve with a test for each label. These are the marks of people who have been audited before.
6. **Every appendix artifact path resolves.** The prior round's most concrete reviewer-friction defect is fixed.

---

## Closure ledger — author response, 2026-10-08 (added after the audit)

The manuscript was revised against this audit the same day. Build evidence: `pdflatex` ×3, exit 0, **14 pages** (bibliography starts p. 12, so **11 text pages** against the 13-page limit; 14 total against the 18-page cap), **0 undefined references, 0 citation warnings, 0 errors, 0 overfull hboxes**. All 56 bibliography entries are now cited in the body (was 7 of 61).

| # | Finding | Status | What changed |
|---|---|---|---|
| N1 | VOR guarded bounds withheld; two audit surfaces conflated | **CLOSED** | Table `tab:live` gains a `Guarded LB` column (0.479 / 0.243 / 0.733, composite ≤0.511) with a caption stating these are floors computed on the archived rows, not the guarded mean. Abstract, contribution bullet, Figure 2 caption, conclusion, and §Evaluation now all carry the bounds and state that the 0.057/0.000 figures come from a separate re-run under a third generator. |
| N2 | Abstract `+0.116` built on the invalidated channel | **CLOSED** | Removed from the abstract. Retained only in §Evaluation and the conclusion, each with an explicit non-reading ("we do not read the `+0.116` as a served-capability result"; "archived, unguarded, and not reproducible under the guard"). Ladder caption states the guarded equivalent is not computable from the release. |
| N3 | Serve-path split from a 4 s latency inference | **CLOSED** | Label-based provenance is primary (216 `GENERATED_VERIFIED` / 2 `FALLBACK_VERIFIED`, no fail-safe substitution). The 88.1/11.9 latency split is demoted to a sensitivity note that states the disagreement. The introduction's "88% of serves" bullet is replaced with the label count. |
| N4 | Three headline artifacts, three unlogged generators | **CLOSED** | New Table `tab:provenance` maps every measured surface to its generator and gateway, including two `not logged (pre-pin gateway default)` rows. Prose states no number is compared across rows. |
| N5 | No related work; 54 of 61 refs uncited | **CLOSED** | New §4 Related Work with five subsections (honeypot foundations; generative honeypots; runtime enforcement and red-teaming; RAG grounding *and the attacks we do not yet resist*; LLM-as-judge) ending in an explicit positioning paragraph. 5 genuinely relevant entries added to the text (`wang2024`, `orbinato2022`, `alsaheel2021`, `ward2025`, `li2026dissonances`); 5 off-topic entries removed (`bachl2021`, `farasat2024a/b`, `sharafaldin2018`, and `sladic2025`, an arXiv duplicate of the cited `valeros2024`). Introduction's roadmap updated. |
| N6 | Safety claim unmeasured | **CLOSED, with new evidence** | New §"What the gate prevented" paragraph reports the pooled triage across all three author families — **540 of 778 generated drafts rejected, 32 admitted, 17 of 206 benign drafts refused (pooled P 0.970 / R 0.944)** — and decomposes the one fully attributed family (llama: 122 danger-signal, 38 identity-pin, 28 fiction-contradiction rejections). It states plainly that the verified and no-verifier arms are byte-identical on all 218 rows, so the gate changed no draft there. Abstract and conclusion rewritten to match. |
| N7 | Wilson intervals over draft-clustered data | **CLOSED** | New `scripts/verifier_ci_cluster_bootstrap.py` resamples **cases** (10,000 iterations, unit = case, seed recorded) and replaces every draft-level interval. Measured effect: the intervals really were too narrow — llama precision widens from `[.869,.947]` to `[.858,.962]`, llama recall to `[.848,.943]`, space-bunny recall to `[.926,.985]`, and deepseek recall now reaches 1.000. A pooled row (778 drafts, stratified by family) is added: P 0.970 `[.949,.987]`, R 0.944 `[.922,.965]`. The method sentence now distinguishes the three estimators instead of claiming one. The script asserts its own aggregation against the published per-family counts and exits non-zero on disagreement. |
| N8 | Prompt-injection coverage backed by n=1 | **CLOSED by withdrawal** | The property table no longer credits injection; it names the eight-command surface and states "no demonstrated prompt-injection or retrieval-poisoning resistance". New prose: injection is represented by two battery cases and **the verifier missed both**; retrieval poisoning is not evaluated at all. |
| N9 | Fail-closed completeness covers 8 commands | **CLOSED** | The eight commands are enumerated in the property table and the number is attached to every claim of P=R=1.0 (abstract, contribution bullet, threat model). |
| N10 | Danger gate detects style tells | **CLOSED, with a worse number than expected** | New `scripts/verifier_harm_probe.py` + `scripts/verifier_harm_cases.py` score a purpose-built corpus: 7 fluent, tell-free, on-fiction but harmful drafts, paired with 5 benign twins on the same file surfaces. Measured against the real serving-path verifier: **recall 0.571 (4 of 7 stopped), precision 1.000 (0 of 5 benign refused)**, identical under both fail-closed settings because the inputs sit outside the declared eight-command surface. The four stops were a plaintext application credential, a bearer-token dotenv file, a leaked persona configuration (danger gate), and an internal-topology dump (consistency layer, via an unmentioned hostname). **The three that reached the wire: a PEM private key in an unmatched format, an off-script offensive tool advertised in `/usr/local/bin`, and an attacker-supplied credential echoed in normalized `postgres://` form.** Reported in the abstract, in a dedicated §"Where the gate's coverage ends", and in the threat-model nonclaim, which now says a fluent on-fiction secret disclosure is not detected in general. |
| N11 | Estimand / weighting mismatch | **CLOSED** | Setup states the ablation estimates a balanced-stratum mean, that it is not the deployment-weighted composite of Table `tab:live`, and that no multiplicity correction is applied. |
| N12 | No multiplicity control | **CLOSED** | Folded into the same sentence, with the reason it is immaterial stated. |
| N13 | Figures hand-coded; no channel label | **CLOSED — and it had already drifted** | New `scripts/gen_sp_figures.py` writes `paper/figures/generated_values.tex` from five artifacts; `results.tex`, `grounding.tex` and `ladder.tex` now resolve every plotted number through it, and `--check` fails when the committed values are stale. The generator immediately caught live drift: Figure 2's persona error bar still carried `0.0573` while `bootstrap_ci.json` had been regenerated to `0.0587` — an invisible stale error bar under the previous scheme. `scripts/audit_figure_geometry.py` now injects the generated definitions into its standalone render, so the geometry audit inspects the same drawing the paper builds. The channel label was added to Figure 2's caption in the previous pass. |
| N14 | Two unexplained 0.955 values | **CLOSED** | Both are now sourced: 0.8875 is the whole-session held-out classifier accuracy (`results/model_quality/chrollo_calibration.json`, n=400) and 0.955 is the same corpus at the trajectory replay's full prefix (`behavior_trajectory_benchmark.json`, prefix `all`, n=400). RQ4 states they are "the same corpus under two measurement procedures, not an intervention delta". |
| N15 | No artifact locator | **PARTIAL — needs an action outside the repo** | Paper side closed: the appendix states the release ships on artifact acceptance, that this submission carries no locator, that the paths resolve only against the released tree, and that reviewers should not treat the numbers as independently reproduced without it; the contribution bullet's "traceable" claim is softened accordingly. **The anonymised mirror itself is still a human action and is not done.** |

### What the response did not do, stated plainly

One item remains genuinely open: the **anonymised artifact mirror** (N15). Everything else in the finding list is now either fixed with new computation or closed by withdrawing the claim. Two gaps are disclosed rather than closed, which is the honest available move on the current timeline: **prompt-injection resistance** and **retrieval-poisoning resistance** are declared unevaluated, and the induced-draft battery's two injection cases are reported as misses.

Two findings got worse under scrutiny and are disclosed as such. The audit under-reported that **both** prompt-injection cases in the live draft battery are false negatives; that is now in the abstract, the evaluation, and the threat model. And the N10 probe returned **4 of 7** rather than a comfortable number: the serving-time gate stops a fluent, tell-free, on-fiction secret disclosure less than two times in three, missing a PEM private key, an off-script offensive capability, and a normalized credential echo. That is the paper's most important negative result and it is stated in the abstract rather than buried.

### A definitional subtlety the cluster bootstrap exposed

The first version of `verifier_ci_cluster_bootstrap.py` disagreed with the published counts on llama: it computed 12 false positives where the artifact reports 17. The cause is a definitional choice, not a bug in either number. A benign draft that the gate **rejects at all** is operationally a false positive — it gets swapped to the fallback and the deception degrades — but five of those rejections did not name a targeted check, so a `caught`-based tally silently reclassified them as true negatives and understated the precision loss. The script now counts rejections, reproduces the published 185/21/17/58 exactly, and asserts that agreement before reporting any interval.

### Verification evidence for this pass

- Full suite: **1622 passed, 116 skipped, 0 failed** (298 s).
- `scripts/verifier_redteam_check.py`: **47/47 artifact-consistency checks PASS**. The canonical 105-case artifact is untouched — still `n_cases 105`, `verdict pass`, `all_gates_pass true` — so the new probe is additive and did not weaken the existing suite.
- `scripts/gen_sp_figures.py --check`: figure values match the artifacts.
- `scripts/verifier_ci_cluster_bootstrap.py --check`: aggregation matches the published per-family counts.
- `sp2027.pdf`: 14 pages, bibliography from p. 12 (**11 text pages**), 0 undefined references, 0 citation warnings, 0 errors, 0 overfull boxes, **56/56 references cited**.
- One regression was introduced and fixed during this pass: the standalone figure-geometry audit failed on `ladder` and `results` because their new `\input` dependency does not resolve in an isolated render. `scripts/audit_figure_geometry.py` now injects the generated definitions, and the y-axis coordinate helpers were reverted to plain integers since they are geometry rather than data.