# Investigation steps

Each step records which log entries it targeted, why they were picked at that moment, what was read or computed, and the log operations that resulted. The reading order is driven by the log — unsettled claims and open questions decide where to read next.

**8 steps.**

---

## Step 1 — Board formation: extract central claims from Abstract+§1-3

**Why now.** First iteration: log the paper's load-bearing claims before any targeted reading; establish Round-14 carryover questions since the manuscript is unrevised

**Action.** Read abstract (l.84-145), intro, RQs, contributions, Table 1 (l.162-370); extracted 13 central claims + panel-structure note

**Found.** Universal prereg claim verbatim in abstract/Table 1; onset-dichotomy theory claims restated as abstract-level results; open-weight spectrum clause present; no revision applied between rounds (mtimes)

**Log operations.**

- `add_claim C1-C13`
- `add_note N1`

---

## Step 2 — C2, C12, Q1, Q2, Q3 (chair's own pass on theory frontier, E5, field, certification, disclosure, rigor sections)

**Why now.** Chair must personally verify the two reject-grade defects Round-14 attributed to the unrevised manuscript (Thm onset (i)(a); ledger absence) and collect the exact persisted sentences for the board record

**Action.** Read theory.tex frontier subsection (l.802-937), E5 subsection (937-1009), field section (1190-1580), limitscert (1580-1930), disclosure (1930-2069), discussion+rigor+DA (2069-2300); re-derived the (i)(a) power boundary by hand; full-depth find for ledger/hash-chain artifacts

**Found.** CONFIRMED persists: (i)(a) prints 'delta>=rho_0 -> detection >=1-beta_d once M>>delta^-2' which is the 50% boundary condition, not 95% power; Def sens calls the TV-Lipschitz identity 'empirically checkable' and E26/L_hat=1.00 'measures' it; §4.4 calls a four-cell scheme 'registered' with plateaus 0.69-0.74 above chance treated as matches; Table 1 caption + §9 print universal prereg claims; E21 'registered before data' sentence verbatim; ethics 'no third-party system was probed or attacked' twice while §6 probes gateway production models; ledger/hash-chain vouched 3x and absent (chair's own find); 'same probe text' representation bridge (§6 E21, §9(3)) conflicts with 'held-out paraphrases P1-P3' for E21/E27 flags; E31 registration claim is consistent (18:21 vs 18:45 per artifacts)

**Log operations.**

- `update_claim C2 invalid`
- `update_claim C12 invalid`
- `add_question Q1-Q3`

---

## Step 3 — Reference layer, related-work coverage (chair pass)

**Why now.** Round-14 flagged ref-garbling; chair re-verifies from the compiled .bbl because unrevised manuscripts carry unrevised bibliographies

**Action.** Enumerated all 74 bibitems; read volkov2024 and nberlie entries in full; grepped for sleeper/hubinger/qcd/sprt/bandit

**Found.** Reworr garbled + out-of-alphabetical-order bbl entry (hand-edited bbl); 'Wen Min' should be Weicheng Min; Sleeper Agents uncited while intro's motivating example is that paper; QCD/SPRT/bandit literatures uncited under novelty claims for monitoring/allocation. Alignment Faking properly cited.

**Log operations.**

- `add_note N2`

---

## Step 4 — N2,Q1

**Why now.** Slice requires ethics-vs-artifact consistency

**Action.** Will grep data/ gauntlet/ for fleet/EPK/session records

**Found.** pending

**Log operations.**

- `add_note`
- `add_question`

---

## Step 5 — C3, C5, C6, C7, Q1, Q2 (theory_hawk + gatekeeper_hawk integration)

**Why now.** Specialist reports landed; chair integrates verified findings into the log: theory hawk recomputed (i)(a)/Table 2/Def 4.5/Prop 7.3/estimand from scratch; gatekeeper re-verified prereg mtimes/git-diffs and the E5 registration text

**Action.** Parsed theory_hawk Tasks 1-7 and gatekeeper_hawk Tasks 1-26; spot-checked quoted line numbers against the manuscript sources; identified two new reject-grade items (E2/E3 direction inversion; retroactive date edits in E27/E29 registration files)

**Found.** (1) Thm onset (i)(a) false at registered cells (best TPR 0.788-0.852<0.95); Table 2 middle rows contradict printed theorem within the same page; appendix prints p-delta sign error; (ii) circular. (2) Def 3.3 estimand is not what any field estimator computes (lexical HeuristicJury; FN 12/25=48%; mandatory non-literal audit never fires on zero positives). (3) E5 four-cell scheme unregistered; registered dichotomy falsified at 2.5/4 cells; result inside registration file. (4) Universal prereg claim contradicted for E21/E22/E26/E27/E28/E29/E20/E15/E16 with git-objective retroactive date edits for E27/E29; 25/5 split post-hoc; Holm dropped silently. (5) E2/E3 registered directional primaries (H1 BCG>0 on >=6 agents; H2 Delta(B)>floor) refuted and remarketed as 'pre-registered nulls'; panel 2 not >=6. (6) Verified-correct: Thm 4.1/4.3/Lem 4.6/4.7(iii)/Cor 4.9/7.1/7.4/7.5, Props halflife/reactivity/alloc, Prop budget grid reproduces exactly; Wilson intervals all compute; E25/E30/E31 timings clean.

**Log operations.**

- `update_claim C3 invalid, C5 invalid, C6 weak, C7 weak, C2 invalid-upgraded, C10 invalid, C13 weak, C1 supported`
- `resolve_question Q1 Q2`
- `add_note N4`

---

## Step 6 — C4, C8, C9, C11 + empirics integration

**Why now.** Empirics hawk landed: recompute every load-bearing number from frozen artifacts; identify new bookkeeping defects; chair integrates

**Action.** Parsed empirics Tasks A-F; cross-checked verdicts against manuscript field.tex/instrument.tex; verified a random subset of its counts myself (E31 Pro 43/300 etc.); performed user-requested disk cleanup between reports (505MB->15GB free) without touching any frozen artifact

**Found.** Empirical spine fully reproduces: 65+ printed values all exact to the digit; 118/112 audit decomposition independently re-verified mechanically (112/112 canary-verbatim regex; 118/118 refusal-style human-read, zero affirmative compliance). NEW round-15 defects: canned censored-turn replies contradict the 'every turn logged' claim (F4, ~594 turns across E2v1/E29/E30/E31); non-blind author-side adjudication undisclosed in manuscript (B3); fig:cert caption conflates n=18 pilot with n=30 E4 run (C5); Wilson mislabeled exact [0,7.0%] vs CP 5.7% (F3); E18 'uniformly narrower' false (F2); 1,230/1,640 not reconstructible (F5). Caption-pool misdefinition on Table 6 materially wrong (Pro 0.350-vs-0.143); E30 Pro 74.67% < 80% bar undisclosed; E31 censoring fractions at tau-boundary undisclosed.

**Log operations.**

- `update_claim C4 supported, C9 weak, C11 supported, C8 weak`
- `add_note N5`

---

## Step 7 — C14-C30, Q3, Q4 (fresh-eyes slice: whole-paper read, figures-via-captions, ethics/venue, instrument+related verification)

**Why now.** Round-15 slice asks for >=50% new findings with file:line evidence

**Action.** Read all sections/*.tex end-to-end (main.tex, sections/introduction...conclusion, appendix, platform_appendix); extracted every printed ratio/CI and recomputed Wilson bounds; read gauntlet/demo artifacts E2-E5, E11-E31 MD+JSON; read figure generation scripts make_fig_beta_foils.py, make_fig3_radar.py, figdata/*.dat; searched repo for EPK/census/ledger/jury artifacts; read data/field/ragin telemetry and RAGIN fleet census + epk_frontier_gen1-3.json; verified references.tex entries for the 8 task-listed works; label/ref sweep via python

**Found.** NEW: Fig 1 caption propagates an n=18 pilot accounting (12/18, 90-trial Wilson CIs) under an E4 section whose registered artifact is n=30 (20/30 echo); make_fig_beta_foils.py back-solves trial counts (round(beta*18)); E17 hides 18/70 unavailable adjudications; E26 per-family L-hat misquoted as 1.00 (echo 0.667); tab:widths drops the M=5 AUC 0.918 selectively; Fig 2 at-chance claim vs 0.339; S4.1 EPK zero-detection claim rests on 4 censored gen-3 sessions (cap not reached); tab:openweight pooled definition contradicts audit composition; E3 summary artifact holds E23 numbers (14/15+0.0067 come from BASELINE only); acks thank fleet operators vs author-ownership claims; E26 prereg header date 2026-11-23 vs mtime/DA 2026-11-22 and opens Rebuttal Q3/concern M7; E23 counted confirmatory though post-anomaly; E26 in Field layer though constructed-plane; agentharm2025 stray SaTML fragment + aisandbagging2024 year mismatch; 5 notation collisions (rho, c, m, K, B); related-work characterizations unverifiable from deposit, evaldrift2026 title collides with the none-defines-a-horizon novelty claim; honeypot ethics has no TOU/consent/legal-basis text and fleet census shows real-attacker mass is one machine prober; E29 artifact date self-contradiction. RECONCILED exactly: E17/dose/retest/T3/E11-E22/E25/E27/E28/E2/E29/E30/E31 numbers, E-count arithmetic, Wilson CIs, no broken refs

**Log operations.**

- `add_claim C14-C30`
- `update_claim C14-C30 statuses`
- `resolve_question Q3 Q4`
- `add_note N6`

---

## Step 8 — Full board integration: fresh-eyes report (22 new defects)

**Why now.** Final specialist report lands; log the new claims and settle them, resolve Q3, then finalize

**Action.** Integrated fresh_unicorn findings: E3 summary-artifact mismatch, E23/E26 class contradictions, E26 per-family-vs-max misstatement, tab:widths selective range-cut, notation collisions, ethics ownership contradiction, EPK overclaim, figure conflation trio, agentharm2025 stray fragment, aisandbagging key mismatch; corrected its erroneous Clopper-Pearson dissent (CP=5.7% for 0/51, verified: 1-0.05^(1/51)=0.057)

**Found.** 22 new defects confirmed with evidence; no binary files accessed; the review now covers every section and every theorem

**Log operations.**

- `add_claim C34`
- `update_claim C31,C32,C33,C34 invalid`
- `resolve_question Q3`
- `outline summary+strengths+11 weaknesses+minors+7 questions`
- `score 2`

---
