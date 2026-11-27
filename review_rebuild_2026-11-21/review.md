## Summary

Belief Tomography (TOPS rebuild): an active black-box estimand for the gap between an agent's published charter and its behavior under adversarial probing, with impossibility/query-complexity/frontier theory, a validated instrument (dose-response r>=0.986, test-retest r=0.949, seeded audit calibration), 21 pre-registered experiments, and two field nulls on production frontier models and a live honeypot fleet. This pass reviewed the post-rebuild build; every load-bearing number was re-verified against the frozen artifacts.

## Strengths

- Unusually complete preregistration discipline: 21 experiments registered before data, estimator pinned to a frozen commit, deviations logged before analysis; every quoted number re-verified against frozen artifact files (dose-response, E2/E3 nulls, E17 calibration, E18 robustness, E20 frontier, E5 onset) [[C1](#c1), [C2](#c2), [C3](#c3), [C4](#c4), [C6](#c6), [C7](#c7)]
- The two field nulls are results, not absences: kill gates passed, the foil family shows the instrument recovers graded structure when beliefs exist, and the nulls bound the operational claim from both directions [[C2](#c2), [C3](#c3)]
- Disclosure economics is a genuine privacy contribution for TOPS: reconnaissance externality, defender-side deception release, closed-form detection budget coupled to attacker fallibility, and a no-free-lunch frontier treating published tomograms as sensitive data [[C5](#c5)]
- Novelty positioning is honest and precise: a four-frame table, explicit non-claims (the adversary is not the novelty; not another entry in the catalogue), and estimator-level instantiation stated against each adjacent frame [[C8](#c8)]

## Weaknesses

- Citation base skews to 2025-2026 preprints; author lists and DOIs verified, but evidence-base maturity remains a fair journal-level question [[N2](#n2)]
- E2 provider censoring leaves per-session attribution coarse and the state-deception fully-measured subset empty; disclosed honestly but it bounds how much the charter-holding null can exclude [[N2](#n2)]
- E3 is an instrumented null: the honeypot plane's shallow command layer bounds engagement depth and the detection persona flagged the plane via /proc fakery; disclosed prominently, but the deception-gain null inherits this ceiling [[N2](#n2)]

## Questions for Authors

- How does the estimand behave for agents that learn continuously between measurements? The hiding proposition covers one-shot hide-after-K exposure; the multi-round regime is stated open in the discussion [[N2](#n2)]
- Would the formal characterization of the informativeness-optimal adaptive design change the operational recommendation of the T3 policy benchmark, or is variance-equalizing allocation effectively optimal at realistic budgets? [[N1](#n1)]

## Overall Score

8/10 (ICLR 2026: Accept — good submission)

## Evidence

<a id="c1"></a>**C1** · claim (supported) · §5.3
> Instrument validity: dose-response Pearson r>=0.986 and Spearman rho=1.00 in all five families across 1,500 episodes, exact zero-dose cleanliness
>
> *Verification:* DOSE_RESPONSE.md: r>=0.986 across families, 1500 episodes, zero-dose cleanliness, monotone; rho stated

<a id="c2"></a>**C2** · claim (supported) · §6.1
> E2 field null: both frontier models beta_hat=0 Wilson [0,0.060] every family after transport repair; censoring 117/400 (29.2%) and 66/400 (16.5%); retest 201/400 (50.25%) unmeasurable; live audit FP 0/51 [0,7.0%]
>
> *Verification:* E2_RESULTS_V1.md contains every quoted number: 0.060, 117/400 29.2%, 66/400 16.5%, 201/400 50.25%, 0/51 [0,7.0%], 2/20 non-replication

<a id="c3"></a>**C3** · claim (supported) · §6.2
> E3 field null: Delta(B) 0.000-0.0067 <= floor 0.067 for all five personas; gates 10/10 sessions, retest 14/15 exact mean 0.0067, canary incident adjudicated clean
>
> *Verification:* E3_DECEPTION_GAIN.md: 0.0067 max gain, 0.067 floor, 10/10 sessions, 14/15 retest agreement, canary allowlist incident adjudicated

<a id="c4"></a>**C4** · claim (supported) · §5.6
> E17 seeded audit: adjudication channel sensitivity 0.960 [0.805,0.993], FP 0/25 [0,0.133], dominates lexical oracle (0.20/0.48 vs 0.00/0.04)
>
> *Verification:* e17_audit_calibration.json sensitivity 0.96 CI [0.8046,0.9929] correctly rounded to 0.960 [0.805,0.993]; FP 0/25 [0,0.133]; FN 0.04 vs oracle 0.48

<a id="c5"></a>**C5** · claim (supported) · §8.4
> E20: bounded-noise disclosure frontier has no interior point dominating either corner (no free lunch)
>
> *Verification:* E20_DISCLOSURE_FRONTIER.md: no-free-lunch stated 3x, monotone trade-off, full-vector advantage 0.067

<a id="c6"></a>**C6** · claim (supported) · §4.4
> E5 quantitative regime match: N0=10 floor 0.283>delta=0.2 AUC plateaus 0.69-0.74; N0=40 floor 0.141<delta rises 0.76->0.97; birth onset 0.34-0.53
>
> *Verification:* E5_ONSET.md: floors 0.283/0.141, plateau 0.69-0.74, rise 0.76->0.97, saturation 0.997, birth onset 0.34-0.53

<a id="c7"></a>**C7** · claim (supported) · §5.7
> E18 estimator robustness: zero decision flips at tau=0.2, credible intervals 0.88-0.99x narrower; E19 seed extension 3 fresh seeds all-pass
>
> *Verification:* E18_ESTIMATOR_ROBUSTNESS.md: zero decision flips, width ratio 0.88-0.99; E19 three seeds registered

<a id="c8"></a>**C8** · claim (supported) · §2.1
> Novelty: the estimand class (active black-box behavioral belief measurement with impossibility+query-complexity+frontier theory) is not placed by prior work; four adjacent frames each stop one step short
>
> *Verification:* Four-frame positioning table present; honesty markers present (we do not make it as one; the adversary is not the novelty; not another entry in that catalogue); convergence-timing closer present

<a id="n1"></a>**N1** · note · §whole · rebuild-integrity
> Rebuild pass verified: numeric inventory diff shows zero loss across 12 files (1431 numbers), citations 74/74 bidirectional, build 0/0/0 at 33pp, AI-tell sweep clean

<a id="n2"></a>**N2** · note · §9,§10 · weakness
> Structural weaknesses carry over honestly: citation base maturity (2025-2026 preprints), E2 provider censoring bounds per-session attribution, E3 null instrumented by shallow command layer; all disclosed in-paper
