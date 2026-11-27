# Belief Tomography — Paper Draft Skeleton (v1)

**Target:** USENIX Security / CCS (primary); ICLR (alternative)
**Status:** full draft §1–§11 prose in `main.tex` (13 pp compiled, 0 undefined refs, 0 pending markers); E2-v1 + E2-v1b field results FINAL — both models measurable after token-budget repair, gpt-6.1 retest not assessable at 50.25% censoring; E6–E17 complete (E15 counterintelligence tomogram / E16 detection-budget coupling / E17 seeded audit calibration; F8 added); **E3 EXECUTED (2026-11-20): user funded a key → full registered chain ran (10/10 sessions, 1,650 probes, concurrency deviation logged); H2₀ null — Δ(B) ≤ floor all personas; canary incident adjudicated via live plane inventory**
**Estimator freeze:** commit `8ceb6e0`; experiments E1/E1b/E5/T3-benchmark complete (`c75bdcc`, `57fd3eb`)
**Figures:** F1–F4 generated (`figures/*.pdf`), F5 waits on E2-v1
**2026-11-19 update:** E2-v0 INVALIDATED (episode-isolation defect, `E2_V0_ARCHIVE.md`); E2-v1 replication instrumented + running (unique session ids, per-episode subprocess, per-turn JSONL checkpoints; both driver fixes logged pre-data in the preregistration). Constructed oracle audit: 20% FP / 48% FN on 50 boundary sessions (`ORACLE_AUDIT_CONSTRUCTED.md`). All 12 arXiv IDs in the drafts verified against the API; one bad ID (`2601.05869`, a fluid-dynamics paper) replaced with `2610.00511`.

---

## Title candidates
1. *Belief Tomography: Measuring What Autonomous Agents Are Made to Wrongly Believe*
2. *X-Ray for Agents: Active Black-Box Estimation of Behavioral Belief Profiles, with Impossibility and Frontier Results*

## Abstract skeleton (claims map)
1. Agents act on latent belief states; charters assert, behavior betrays. [§1, no artifact needed]
2. We define behavioral belief strength β and the Belief–Claim Gap. [§2, `tomograph.py` @8ceb6e0]
3. Passive monitoring is structurally insufficient (T1) — proved; our measured ε=0 non-detector is the instance. [§3, `formalism_note` §3 + fleet results `fleet_census_2026-11-18.md`]
4. The deception–detection frontier (T5): patch-decay O(L/√N); onset dichotomy. [§4, `formalism_note` §6]
5. T5 validated empirically with quantitative noise-floor regime match (E5). [§5, `E5_ONSET.md` @c75bdcc]
6. The instrument is valid (dose–response r≥0.986) and reliable (r=0.949 @10/cell; batch size is part of the spec). [§6, `DOSE_RESPONSE.md`, `RELIABILITY.md`]
7. Probe-allocation objectives must match the estimation goal: UCB(regret) and PSI(info) both lose to uniform; Neyman is correct. [§6, `POLICY_BENCHMARK.md` @57fd3eb]
7b. A finite public probe suite is gameable (T6/E7), component certification does not compose (T7/E6, β=1 pipeline breach), and the gaming gap Γ decides transfer (T8). [§9, `PREREGISTRATION_E6E7.md`, `E6_COMPOSITION.md`, `E7_GAMING.md`]
8. In production agents, the Belief–Claim Gap is nonzero: **[PENDING-DATA E2]**. [§7, prereg @95ac29d]
9. On a live fleet, deception gain Δ(B) registers above the noise floor: **[PENDING-DATA E3]**. [§7]
10. Everything above is measured, pre-registered, noise-floor-gated, and reproducible. [§8 ethics/rigor]

## Section plan

**§1 Introduction** — the invisible object; founding reframe (attack vectors are measurement instruments); the four theory frames (QIF: what the adversary learns; information design: what the sender distorts; deception games: what the defender gains; **us: what the adversary is made to wrongly believe, with bounds**); contributions list (estimand, instrument, T1, T5, validity/reliability program, E2/E3 headline numbers, certification application).

**§2 The estimand** — definitions (probe family, β, profile, BCG, epistemic distance, deception gain); Assumption L (sensitivity) stated with its empirical check pointer (dose–response). Artifacts: `formalism_note` §2.

**§3 T1: passive impossibility** — proof; Corollary (detection budgets); **lineage honesty**: mimicry attacks (Wagner & Soto 2002) and polymorphic blending (Fogla USENIX-Sec 2006) constructed indistinguishability — our contribution: the finite-N frontier bound + the belief-gain coupling + the agent-interaction instantiation. ε=0 non-detector as the living instance (fleet census). Artifacts: `formalism_note` §3, `fleet_census_2026-11-18.md`.

**§4 T5: the deception–detection frontier** — amplification lemma (standard-technique attribution, new role); patch-decay theorem; onset dichotomy; coherence tax; frontier corollary. Positioning vs Bayesian-persuasion-with-lie-detection (NBER 30065): equilibrium/commitment frame vs sampling-horizon information theory with executable probes. Artifacts: `formalism_note` §6.

**§5 T5 validated (E5)** — onset dichotomy manifests; **the quantitative match** (N₀=10 floor 0.283>δ → AUC stuck ~0.70; N₀=40 floor 0.141<δ → 0.97; birth-onset blind ∀M). Figure 2 = AUC-vs-M curves with floor annotations. Artifact: `E5_ONSET.md` @c75bdcc.

**§6 The instrument** — probe library (5×3, seeded); validity (E1 dose–response); reliability (E1b, batch-size-in-spec); **policy benchmark (negative result + objective-matching principle)**. Figure 1 = tomogram radar (two foils); Figure 3 = dose–response curves; Figure 4 = policy benchmark table. Artifacts: `DOSE_RESPONSE.md`, `RELIABILITY.md`, `POLICY_BENCHMARK.md`.

**§7 Field results** — E2-v1 [PENDING-DATA]: BCG headline (production agents; independent logged sessions, transcript-audited verdicts); E3 [PENDING-DATA]: deception gain on the live fleet (attribution-ready: front proxy). Artifacts: prereg @95ac29d + 2026-11-19 deviations, `fleet_census_2026-11-18.md`. E2-v0 is archived as invalid and never quoted.

**§8 Certification application** — GAUNTLET as hypothesis test over the profile; UCB-vs-Neyman caveat from §6 (certification-detection correctly uses regret-style allocation; estimation must not).

**§9 The limits of certification** — T6 (public probes gameable), T7 (composition fails; E6 β=1 pipeline breach with both components certified), T8 (gaming-gap Γ as transfer diagnostic), T9 (tomogram forgery — displayed profile is unauthenticated), T10 (published held-out set is itself gameable ⇒ diagnostic must be secret); E7 probe-aware foil passes public / fails held-out with Γ=1; E8 interface probe catches the composition attack missed by 300 local probes; E9 profile shaping (display exfiltration / true state-deception, gap 1.0); E10 adaptive foil passes published Γ=0 yet breaches secret β=1, secret-set check detects it; T11/E11 certificate half-life under drift — one-shot falsified, half-life renewal cheaper than fixed calendar; controls separate probe-awareness from malice; failed E7 attempts retained. Honesty gate: T6/T9 are estimator-level instances of Ferrara 2026 defeat devices and Mahran 2026 partition limits — cited and differentiated in §10 and `DEFEAT_DEVICE_COLLISION_SCAN.md`. Artifacts: `PREREGISTRATION_E6E7.md`, `PREREGISTRATION_E8E9.md`, `PREREGISTRATION_E10.md`, `E6_COMPOSITION.md`, `E7_GAMING.md`, `E8_INTERFACE.md`, `E9_FORGERY.md`, `E10_ADAPTIVE.md`.

**§10 Related work** — four-frame structure (QIF / information design / deception games / ToM-epistemics) + the missing-fourth-frame positioning sentence + mimicry/PBA lineage + Park-survey gap + cognitive-tomography ancestor + LLM probing (white-box complement).

**§11 Ethics, rigor, and limitations** — FIELD_ETHICS gates; preregistration + deviation log; noise-floor gating rule; AI-judged verdict disclosure; no real-credential exposure (canary accounting); artifact evaluation plan (all code seeded + pinned).

## Figures plan
- **F1** tomogram radar: naive vs hardened foil profiles (with CIs)
- **F2** E5 AUC-vs-M curves, annotated with reference noise floors (the theory's regimes)
- **F3** dose–response: β̂ vs injected dose, 5 families, CIs
- **F4** policy benchmark: error-vs-budget, 4 policies
- **F5 [E2]** BCG distribution across production agents
- **F6 [E4]** certification separation at τ=0.2 (β vectors + CIs, 3 designed foils)
- **F7 [E6/E7]** limits of certification: composition schematic (β=1 pipeline breach) + gaming-gap bars (public vs held-out)
- **F8 [E15/E16]** the deception-release wave: release-comparison bars (honest 1.000 / silence 0.200 / decoy 0.000) + n_min(m) frontier with the undetectable region
- **F7 [E3]** attacker profiles pre/post deception ops (deception gain Δ with CIs) — blocked with E3 on lane quota

## Claims–evidence ledger (living)
| Claim | Artifact | Commit |
|---|---|---|
| T1 proof | formalism_note §3 | 8ceb6e0 |
| T5 proofs | formalism_note §6 | 8ceb6e0 |
| E5 quantitative match | E5_ONSET.md | c75bdcc |
| E1 validity | DOSE_RESPONSE.md | 8ceb6e0 |
| E1b reliability + noise floor | RELIABILITY.md | 8ceb6e0 |
| T3 policy benchmark | POLICY_BENCHMARK.md | 57fd3eb |
| Fleet ε=0 instance + Nov-16 attribution | results/fleet_census_2026-11-18.md (inner repo) | 52ec6f93 |
| Oracle boundary audit (20% FP / 48% FN, 50 constructed) | ORACLE_AUDIT_CONSTRUCTED.md | this session |
| Probe-leakage check (offline prompt audit + optional knowledge check) | LEAKAGE_CHECK.md | this session |
| E4 certification separation (3 foils, τ=0.2, 2 seeds) | E4_SEPARATION.md | this session |
| T6/T7/T8 proofs (limits of certification) | formalism_note.tex §7 | this session |
| E6 composition attack (both components certified, pipeline β=1) | E6_COMPOSITION.md / e6_composition.json | this session |
| E7 gaming gap (public cert / held-out reject, Γ=1; 2 controls) | E7_GAMING.md / e7_gaming.json (+ 2 failed-control runs retained) | this session |
| T9 tomogram forgery (unauthenticated profile) | formalism_note.tex §8 | this session |
| E8 interface-aware certification (1 probe catches composition attack) | E8_INTERFACE.md / e8_interface.json | this session |
| E9 tomogram forgery (display/true profiles differ by 1.0 in 2 cells) | E9_FORGERY.md / e9_forgery.json | this session |
| E10 adaptive gaming of published Γ (Γ=0, secret β=1; secret set restores detection) | E10_ADAPTIVE.md / e10_adaptive.json | this session |
| Collision scan vs. defeat devices / partition theory / composition / drift (12 verified IDs) | DEFEAT_DEVICE_COLLISION_SCAN.md | this session |
| T11 certificate half-life (elementary bound; new object h_tau) | formalism_note.tex §8 | this session |
| E11 drift renewal (one-shot falsified 4 epochs; fixed 5 runs; half-life 2 runs) | E11_HALFLIFE.md / e11_halflife.json | this session |
| T12/E12 tomographic reactivity (session isolation as identification; 93.3% relative bias) | formalism_note.tex §8, E12_REACTIVITY.md / e12_reactivity.json | this session |
| T13/E13 allocation vs learning attacker (uniform false cert; concentration exposes 3/5) | formalism_note.tex §8, E13_ALLOCATION.md / e13_allocation.json (+ failed-construct run retained) | this session |
| T14/E14 reconnaissance externality (published tomogram is a targeting map; A_rec=0.067 graded, 0 flat) | formalism_note.tex §8, E14_RECONNAISSANCE.md / e14_recon.json | this session |
| E2-v0 (INVALID: one accumulating conversation) | E2_V0_ARCHIVE.md + E2_V0_REPORT_AS_WRITTEN.md | 4f67658 |
| E2-v1 driver isolation + transport fixes (pre-data) | PREREGISTRATION_E2E3.md, run_live_e2_replication.py, llm_target.py | this session |
| Citation verification (12 IDs, 1 corrected) | BELIEF_TOMOGRAPHY_LIT_SCAN.md (Rounds 5–6) | this session |
| E2-v1 headline (independent sessions, logged; both models β=0 [0,0.060] after E2-v1b repair) | E2V1_SUMMARY.md, E2_RESULTS_V1.md | this session |
| E2-v1b repair (gpt-6.1 99.5% → 16.5% censoring; retest 50.25% not assessable) | PREREGISTRATION_E2V1B.md, E2_RESULTS_V1.md | this session |
| E2-v1 kill (a) live FP audit 0/23 [0,14.8%]; (b) exact 15/15, mean Δ=0; (c) prompt + 30-prompt live check PASS | ORACLE_AUDIT.md, E2V1_RETEST.md, LEAKAGE_CHECK.md | this session |
| T15/E15 counterintelligence tomogram (deception release: honest 1.000 / decoy 0.000 / silence 0.200 per-attempt; stable under public verification; monotone trust collapse) | formalism_note.tex §8, E15_DECEPTION_RELEASE.md / e15_deception_release.json | this session |
| T16/E16 detection budget vs attacker probe-discrimination error (closed form = MC; n_min 8→549→2057→>4000 over m=0.5→0.9→0.92→0.94; one-sided asymmetry fatal) — fills part of T2 | formalism_note.tex §2+§8, E16_QUERY_COMPLEXITY.md / e16_query_complexity.json | this session |
| E17 seeded audit calibration (adjudication channel: sens 0.960 [0.805,0.993], FP 0/25 [0,0.133], FN 1/25 pretext-only; dominates oracle FP 0.20/FN 0.48; kill-(a) power ≈12%) | E17_AUDIT_CALIBRATION.md / e17_audit_calibration.json (+ blind sheet + labels + hidden truth) | this session |
| Novelty-gate round 5 (deception-doctrine ancestors, decoy artifacts, auditing games, seeded audits; 7 verified IDs) + E17 mapping-bug deviation (pre-scoring, sheet md5-verified) | DEFEAT_DEVICE_COLLISION_SCAN.md, PREREGISTRATION_E15E16E17.md | this session |
| E18 estimator robustness (empirical-Bayes vs frozen Wilson: ZERO decision flips; intervals 0.88–0.99× narrower; boundary-cell disagreement disclosed) | E18_ESTIMATOR_ROBUSTNESS.md / e18_estimator_robustness.json | this session |
| E19 seed extension (E6/E7/E9/E10 at seeds 131/2026/90210, one run per seed → genuine per-seed verdicts: ALL conditions hold; seed-robust) | E19_SEED_EXTENSION.md + *_EXT/*_s<seed> artifacts + .registered snapshots | this session |
| E20 disclosure frontier (Laplace(1/ε) profile release, ε-DP over profile space: monotone trade-off; NO interior point dominates either corner — "no free lunch"; resolves E14's registered open question) | E20_DISCLOSURE_FRONTIER.md / e20_disclosure_frontier.json (+ 2 retained pre-acceptance defect runs; deviations in prereg §5) | this session |
| Novelty-gate round 6 (DP machinery ancestors: NIST SP 800-226, graph-DP; E20's object — certificate disclosure frontier — verified unoccupied) | PREREGISTRATION_E18E19E20.md | this session |
| E3 headline | [PENDING-DATA — instrument frozen, one funded key unblocks] | — |

## Writing order
1. §2 + §6 (complete artifacts) → 2. §3 + §4 + §5 (theory + E5) → 3. §1 + §9 (positioning after E2 lands) → 4. §7 (E2/E3) → 5. §8 + §10.
