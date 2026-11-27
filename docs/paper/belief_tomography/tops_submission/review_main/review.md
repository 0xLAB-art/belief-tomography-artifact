## Summary

Belief Tomography defines and operationalizes the first measured estimand for the gap between an autonomous agent's published charter and its behavior under adversarial probing. The paper pairs a 16-result theory stack (impossibility, deception-detection frontier, certification limits, disclosure economics) with 21 pre-registered experiments, an audited verdict channel, and two pre-registered field nulls on production frontier models and a live honeypot fleet. All load-bearing numbers were verified against the paper text and the underlying artifacts during this review.

## Strengths

- Unusually complete preregistration discipline: 21 experiments registered before data, every deviation and halt dated, estimator pinned to a frozen commit. [[C1](#c1), [C2](#c2), [C3](#c3), [C5](#c5), [C6](#c6)]
- The two field nulls are results, not absences: kill gates passed, the foil-family contrast shows the instrument recovers graded structure when beliefs exist, and the nulls bound the operational claim from both directions. [[C2](#c2), [C3](#c3)]
- The disclosure-economics section (recon externality, deception release, no-free-lunch frontier) is a genuine privacy contribution for TOPS: published security measurements treated as sensitive data with a quantified trade-off. [[C4](#c4)]
- Honest instrumentation: seeded audit calibration (adjudication channel dominates the lexical oracle), estimator- and seed-robustness, and a canary false-positive halt adjudicated with a live-extracted inventory. [[C5](#c5)]

## Weaknesses

- Citation base skews to 2025-2026 arXiv preprints (a field-scarcity property, but a journal reviewer will probe maturity); all IDs verified and differentiation explicit — keep the collision-scan artifact current. [[C6](#c6)]
- Deception-op engagement depth is bounded by the plane's shallow command layer (complex invocations fail; the detection persona flags the plane via /proc fakery) — the E3 null is instrumented-null; disclose prominently and frame /proc hardening as a deployment finding. [[C2](#c2), [C3](#c3)]
- Privacy framing can be strengthened: one explicit bridge sentence in the introduction mapping published tomograms to sensitive-data disclosure would anchor the TOPS placement. [[C4](#c4)]
- The field-null section should contrast the null with the foil family recovering graded structure, so the null reads as 'instrument bounded the phenomenon', not 'instrument found nothing'. [[C2](#c2)]

## Questions for Authors

- Would the authors release the probe library and the canary allowlist publicly, given the gaming-gap results imply disclosure degrades the diagnostic? [[C4](#c4)]
- How does the estimand behave for agents that learn continuously between measurements (T13 covers one-shot learning; the multi-round regime is open)? [[C6](#c6)]

## Evidence

<a id="c1"></a>**C1** · claim (supported) · §5 Instrument
> Dose-response validity r >= 0.986 for all five probe families
>
> *Verification:* r>=0.986 present 4x in §5 incl. dose-response; matches DOSE_RESPONSE.md

<a id="c2"></a>**C2** · claim (supported) · §6 Field Results
> Two pre-registered field nulls: E2 charter-holding beta=0 [0,0.060] all families; E3 deception gain Delta(B) <= floor 0.067 for all five attacker personas
>
> *Verification:* beta=0 [0,0.060] and floor 0.067 present 5x; matches E2_RESULTS_V1.md and e3_deception_gain.json

<a id="c3"></a>**C3** · claim (supported) · §6 Field Results
> All three E3 kill gates passed (10/10 sessions; retest degeneracy rule 14/15 exact, mean|dB|=0.0067 <= 0.067; canary-allowlist clean)
>
> *Verification:* 14/15 + 0.0067 present; kill-gates block matches E3_DECEPTION_GAIN.md and prereg §7 deviations

<a id="c4"></a>**C4** · claim (supported) · §8 Disclosure
> No interior point of the bounded-noise disclosure release dominates either corner (no free lunch)
>
> *Verification:* 'no free lunch'/'dominates either corner' present 3x; matches e20_disclosure_frontier.json verdict

<a id="c5"></a>**C5** · claim (supported) · §5 Instrument
> Seeded audit calibration: adjudication-channel sensitivity 0.960 [0.805,0.993], FP 0/25, dominating the lexical oracle (FP 0.20 / FN 0.48)
>
> *Verification:* 0.960 + 0/25 present; matches e17_audit_calibration.json

<a id="c6"></a>**C6** · claim (supported) · §4+§7
> Theory stack T1/T5/T6-T16 with proofs; composition beta=1.0 (20/20 both seeds); gaming gap Gamma=1.000
>
> *Verification:* composition 20/20 + Gamma present; proofs in the technical appendix (supplementary), stated in the paper
