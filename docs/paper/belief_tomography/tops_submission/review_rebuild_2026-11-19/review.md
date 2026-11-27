## Summary

Belief Tomography, rebuilt from scratch for ACM TOPS: a measured estimand for the gap between an agent's published charter and its behavior under adversarial probing, with 16 theorem-class results (impossibility, query complexity, deception-detection frontier, certification limits, disclosure economics) and 21 pre-registered experiments including two field nulls on production frontier models and a live honeypot fleet. This rebuild adds a numbered introduction with the previously unused tomogram figure, a four-frame positioning table, a new query-complexity subsection (Theorem 4.3 + Proposition 4.4) that repairs a dangling open-problem reference, LaTeX-ref theorem numbering with a full proofs appendix, relocation of the disclosure-frontier result to the disclosure section, and a verified bibliography (author lists and DOIs confirmed against sources). All load-bearing numbers re-verified against the frozen artifacts during this review.

## Strengths

- Unusually complete preregistration discipline: 21 experiments registered before data, estimator pinned to a frozen commit, every deviation and halt logged; every load-bearing number re-verified against the frozen artifact JSON/MD files during this review (dose-response r>=0.986, E2/E3 nulls, E17 audit calibration, E18 robustness, E20 frontier). [[C1](#c1), [C2](#c2), [C3](#c3), [C4](#c4), [C5](#c5), [C6](#c6), [C7](#c7)]
- The two field nulls are results, not absences: kill gates passed, the foil family shows the instrument recovers graded structure when beliefs exist, and the nulls bound the operational claim from both directions (targets hold charters; attackers hold operational beliefs). [[C2](#c2), [C3](#c3)]
- The disclosure-economics section is a genuine privacy contribution for TOPS: reconnaissance externality, defender-side deception release, a closed-form detection budget coupled to attacker fallibility, and a no-free-lunch disclosure frontier treating published tomograms as sensitive data. [[C5](#c5)]
- Theory completeness: every theorem-class result carries a resolving LaTeX number and a proof (Appendix A); the query-complexity result is now stated and referenced where it is used, replacing the dangling open-problem pointer of the previous build. [[C6](#c6), [N4](#n4)]

## Weaknesses

- Citation base skews to 2025-2026 preprints; author lists and DOIs are now verified, but maturity of the evidence base remains a fair journal-level question. [[N1](#n1)]
- E2 provider censoring leaves per-session attribution coarse and the state-deception family's fully-measured subset empty; the paper discloses this honestly, but it bounds how much the charter-holding null can exclude. [[N2](#n2)]
- E3 is an instrumented null: the honeypot plane's shallow command layer bounds engagement depth, and the detection persona flagged the plane via /proc fakery. Disclosed prominently, but the deception-gain null inherits this ceiling. [[N3](#n3)]
- Corollary 4.9 (the deception-detection frontier) is a framing corollary of Theorems 4.7-4.8 without a separate proof; its logical status could be made explicit to pre-empt a strict reviewer. [[N4](#n4)]

## Questions for Authors

- How does the estimand behave for agents that learn continuously between measurements? Proposition 7.8 covers one-shot hide-after-K exposure; the multi-round regime is stated as open. [[N3](#n3)]
- Would the formal characterization of the informativeness-optimal adaptive design (open problem after Proposition 4.4) change the operational recommendation of the Section 5.3 policy benchmark, or is variance-equalizing allocation effectively optimal at realistic budgets? [[N5](#n5)]

## Overall Score

8/10 (ICLR 2026: Accept — good submission)

## Evidence

<a id="c1"></a>**C1** · claim (supported) · §5.2
> Instrument validity: dose-response Pearson r>=0.986 and Spearman rho=1.00 in all five families, 1500 episodes, 60/cell
>
> *Verification:* dose_response.json pearson_r values 0.986/0.9863/0.9904/0.9889/0.9903 (min 0.986); DOSE_RESPONSE.md shows rho=1.00, monotone, zero-dose clean; 5x5 doses x 60 = 1500 arithmetic

<a id="c2"></a>**C2** · claim (supported) · §6.1
> E2 field null: both frontier models beta_hat=0 Wilson [0,0.060] every family after token repair; censoring 117/400 (29.2%), 66/400 (16.5%), retest 201/400 (50.25%) unmeasurable; live audit FP 0/51 [0,7.0%]
>
> *Verification:* E2_RESULTS_V1.md contains all: 0.060, 0/51, 117/400, 29.2, 66/400, 16.5, 201/400, 50.25, 27.5

<a id="c3"></a>**C3** · claim (supported) · §6.2
> E3 field null: Delta(B) 0.000-0.0067 <= floor 0.067 for all five personas; gates 10/10 sessions, retest 14/15 exact mean 0.0067, canary allowlist clean
>
> *Verification:* E3_DECEPTION_GAIN.md contains 0.0067, 0.067 floor, 10/10 sessions, 14/15 retest, canary allowlist incident

<a id="c4"></a>**C4** · claim (supported) · §5.5
> E17 seeded audit: adjudication channel sensitivity 0.960 [0.805,0.993], FP 0/25 [0,0.133], dominates oracle (0.20/0.48)
>
> *Verification:* e17_audit_calibration.json: sensitivity 0.960 CI [0.8046,...] rounds to [0.805,0.993], FP 0/25 CI [0,0.133]; MD states channel FP 0.000/FN 0.040 vs oracle 0.20/0.48

<a id="c5"></a>**C5** · claim (supported) · §8.4
> E20: bounded-noise disclosure frontier has no interior point dominating either corner (no free lunch)
>
> *Verification:* E20_DISCLOSURE_FRONTIER.md: 'no free lunch', monotone trade-off, full-vector advantage 0.067

<a id="c6"></a>**C6** · claim (supported) · §4.4
> E5 quantitative regime match: N0=10 floor 0.283>delta=0.2 AUC plateaus 0.69-0.74; N0=40 floor 0.141<delta rises 0.76->0.97; birth onset 0.34-0.53
>
> *Verification:* E5_ONSET.md: floors 0.283/0.141; AUC 0.691-0.74 plateau, 0.76->0.97 rise, birth onset 0.34-0.53

<a id="c7"></a>**C7** · claim (supported) · §5.6
> E18 estimator robustness: zero decision flips at tau=0.2, credible intervals 0.88-0.99x narrower
>
> *Verification:* E18_ESTIMATOR_ROBUSTNESS.md: zero decision flips, width ratio 0.88-0.99

<a id="n1"></a>**N1** · note · §2 · weakness
> W: citation base skews to 2025-2026 arXiv preprints (field-scarcity property; now with verified author lists and DOIs, but a journal reviewer will probe maturity)

<a id="n2"></a>**N2** · note · §6.1 · weakness
> W: E2 provider censoring leaves per-session attribution coarse and the state-deception family's fully-measured subset empty (disclosed as limitation; honest but bounds the null's strength)

<a id="n3"></a>**N3** · note · §6.2 · weakness
> W: E3 null is instrumented (plane's shallow command layer bounds engagement depth); disclosed prominently in §6.2, but reviewers will weigh it

<a id="n4"></a>**N4** · note · §4.3 · weakness
> Minor: Corollary 4.9 (deception-detection frontier) is a framing corollary of Thm 4.7-4.8 without a separate proof; acceptable but a strict reviewer may probe its logical status

<a id="n5"></a>**N5** · note · §4.2,§5.3 · open-problem
> The open problem after Proposition 4.4 leaves the informativeness-optimal adaptive design uncharacterized; the Section 5.3 benchmark shows uniform/Neyman beat UCB/PSI for estimation, leaving the optimality question practically relevant
