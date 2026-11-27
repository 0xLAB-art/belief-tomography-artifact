# Research Program V2 — Maximum Novelty × Maximum Rigor

**Date:** 2026-11-18
**Mission:** one science — *the measurement science of autonomous agents' belief states* — with three instantiated programs sharing one instrument:
1. **Belief Tomography paper** (new field; this plan)
2. **IND-Deception** (S&P June 2027; T5 is now its theory core)
3. **GAUNTLET certification** (applied layer: hypothesis tests over profiles)

---

## 1. The novelty stack (ranked, with status)

| # | Contribution | Status | Why nobody has it |
|---|---|---|---|
| 1 | **T5: The deception–detection frontier** — amplification lemma, patch-decay theorem (gain O(L/√N) under detectability budget), onset dichotomy (known-onset deception capped by memorized reference N₀; birth-onset in-channel undetectable), coherence tax | **NEW — proved 2026-11-18** (formalism_note v0.2, 6pp, clean compile) | Deception literature measures engagement/propensity; no formal gain-vs-detectability tradeoff exists anywhere |
| 2 | T1 passive-observation impossibility (+ ε=0 non-detector as its living empirical instance) | proved (v0.1) | Monitors/detectors dominate the field; nobody states their structural limit |
| 3 | The estimand: behavioral belief strength β, Belief-Claim Gap, epistemic distance, deception gain Δ(B) | defined + implemented | Attack papers have no estimand; eval papers have no latent object |
| 4 | Attack vectors as measurement instruments (V1–V7 → probe families) | implemented (5×3 library) | The reframe is the field's founding move |
| 5 | Instrument validity program: dose–response (r ≥ 0.986, 1500 eps) + test–retest (r=0.949 @10 probes/cell; 4/cell fails) + noise floor | **built 2026-11-18** | Benchmarks never self-validate; cognitive tomography does — we import that discipline |
| 6 | Closed-loop certification = hypothesis test over the profile (GAUNTLET) | v0 running | Benchmarks are static; certification is a test with an allocation policy |

**The one-sentence field claim:** *agents' security beliefs are a measurable quantity, with a formal instrument, impossibility results bounding passive alternatives, and a theory (T5) governing the arms race between measurement and deception.*

## 2. The rigor infrastructure (standing rules — non-negotiable)

1. **Pre-registration before data** for every experiment (PREREGISTRATION_E2E3.md is the template; hypotheses, frozen estimators, power, kill criteria).
2. **Frozen analysis:** the estimator code is pinned by commit hash at registration time; estimator changes after data = documented deviation or withdrawal.
3. **Noise-floor gating:** no effect smaller than the instrument's measured noise floor (mean |Δβ| at the operating batch) is claimable, in any document, ever.
4. **Instrument spec includes batch size:** test–retest reliability is part of the instrument definition (4 probes/cell FAILS on stochastic targets, r=0.837; operating point ≥10/cell, r=0.949).
5. **Claims–evidence ledger from day one** (EGM discipline): every number in any draft maps to an artifact path + commit.
6. **Verdict-channel disclosure:** oracle + AI-judged lanes are separate and labeled; a human-verified subsample gates any jury-dependent headline.
7. **Kill criteria** (below) halt an experiment rather than invite motivated analysis.

## 3. Experiment ladder

| Exp | Question | Status | Gate |
|---|---|---|---|
| E1 dose–response | does β̂ track injected belief dose? | ✅ VALID (1500 eps, all families r≥0.986, zero-dose clean) | done |
| E1b test–retest | is the tomogram reproducible? | ✅ r=0.949 @10/cell; noise floor 0.067; 4/cell insufficient | done |
| E2 | is the Belief–Claim Gap nonzero in production agents? | preregistered; **unblocked** (OpenRouter lane; paid lane needs credits/rotation) | prereg §E2 |
| E3 | does deception gain Δ(B) register on the live fleet? | needs attack-team batch (driver ready) + pre/post tomography; **fleet now attribution-ready** (front proxy live) | prereg §E3 |
| E4 | does the profile-threshold test (GAUNTLET) separate hardened vs naive targets at the operating batch? | v0 demo positive; formalize with E1b noise floor | after E2 |
| **E5 (new)** | does T5's onset dichotomy manifest empirically? Attacker-tomographer with memorized reference (N₀>0) vs without (N₀=0) measuring detection advantage against a mid-session vs birth-onset plane | **designable offline with existing machinery** | design next |

## 4. T5 empirical validation (E5) — design sketch

- Plane: foil targets (known Q). Attacker side: the tomographer run in two modes — (a) with a memorized pre-onset reference batch, (b) without (birth onset).
- Measure: detection advantage (two-sample statistic between reference and fresh batch) and gain estimate error, as M grows.
- Prediction from T5: mode (a) detection → 1 for δ above the N₀ noise floor; mode (b) flat at chance for all M.
- This turns the paper's crown theorem into a falsifiable experiment on the same instrument — reviewers can rerun it.

## 5. Venue & sequencing

- **BT paper:** primary USENIX Security / CCS (measurement+theory), alternative ICLR (if the epistemics framing strengthens). Sections: estimand → T1 → T5 → instrument (E1/E1b) → E2 headline (BCG in production agents) → E3 (deception gain, live) → E5 (T5 validated) → certification as application.
- **IND-Deception paper:** T5 §arms + coherence tax replace the informal ladder narrative; S&P June 2027 per existing plan.
- **Sequencing rule:** E2 → E5 → E3 → draft. E3's fleet batch doubles as §5.6/5.7 evidence for BOTH papers.

## 6. Open dependencies

- Real-agent lane for E2: OpenRouter free tier works but is daily-capped; paid lane = credits or agentrouter key rotation (standing item).
- E3 needs one attack-team batch decision from the user (driver ready; fleet attribution-ready).
- Jury human-verification subsample for the verdict channel (κ gate 0.7) before any jury-dependent headline.
