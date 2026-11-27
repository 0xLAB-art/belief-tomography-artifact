# Pre-registration — E18, E19, E20 (the strengthening wave)

**Logged:** 2026-11-20, **before any E18/E19/E20 computation was performed.**
All three are offline; no API lane; the **frozen estimator (`8ceb6e0`) remains
the registered estimator for every existing endpoint** — nothing below revises
a registered number; the wave strengthens robustness and fills a named gap.
Parent registrations: `PREREGISTRATION_E2E3.md` (§7 deviations policy),
`PREREGISTRATION_E6E7.md`, `PREREGISTRATION_E8E9.md`, `PREREGISTRATION_E10.md`,
`PREREGISTRATION_E15E16E17.md`, `PREREGISTRATION_E14.md`.

## Novelty gate for E20 (deep-research round 6, verified 2026-11-20)

The DP machinery is standard (NIST SP 800-226 "Guidelines for Evaluating
Differential Privacy Guarantees", 2025; graph-DP literature; DP-for-graphs
caveats on correlated records). Two targeted searches found **no work that
applies bounded-noise (DP-style) disclosure to behavioral security profiles
with the attacker's reconnaissance advantage as the privacy loss and the
defender's ranking utility as the utility**. E14 explicitly declined to claim
an optimal disclosure mechanism ("registered defense: publish only the scalar
$U_{\max}$... we do not claim an optimal disclosure mechanism") — E20 is that
registered gap, now filled with an explicit mechanism and frontier. Machinery
ancestors (Laplace mechanism; graph-DP; NIST guidance) are cited; the object —
the disclosure frontier of a security tomogram — is new.

---

## 1. E18 — estimator robustness: hierarchical Bayes vs the frozen Wilson stack

**Gap.** The v0 protocol note promised "hierarchical Bayes in the paper"; every
registered number to date uses the pinned Wilson stack. A reviewer will ask
whether any headline inference is an artifact of the interval estimator.

**Design (pre-analysis on frozen data only).** Empirical-Bayes Beta-Binomial:
per cell, posterior $\mathrm{Beta}(\alpha+k,\ \beta+n-k)$; the hierarchical
prior $(\alpha,\beta)$ is fit by method of moments from the cell rates of the
same experiment's cells (partial pooling across cells within one experiment;
no cross-experiment pooling). Applied to: E1 dose–response cells, E2-v1b
(both models' 15-cell profiles), E4 profiles, E17 audit rates.

**Endpoints (registered):**
1. Agreement: every Wilson point estimate lies inside the corresponding 95%
   credible interval and vice versa (within CI overlap) — estimator-robustness
   of the point measurements.
2. Shrinkage: credible intervals narrower than Wilson intervals on exactly the
   cells where the hierarchical prior supports them; report the mean width
   ratio per experiment.
3. Decision flips: any certification/kill decision that flips under the
   credible lower bound vs the Wilson lower bound at the same tolerance
   ($\tau=0.2$ certification; the E2 β=0 nulls) — each flip is a
   **finding**, reported immediately and labeled as estimator sensitivity.
4. Verdict: "estimator-robust" iff zero flips on all registered decisions.

**Claim boundary:** this validates robustness and prototypes the v2
estimator; it does NOT change any registered number, and no artifact here
replaces a frozen-estimator artifact.

## 2. E19 — seed extension of the foil-harness experiments

**Gap.** E6/E7/E9/E10 ran at two seeds each. Seed-count is the cheapest
robustness lever and the most likely reviewer complaint ("2 seeds").

**Design.** Re-run the registered protocols **unchanged** at three new seeds
fixed before any run: **(131, 2026, 90210)**. Experiments covered:
`run_e6_composition.py`, `run_e7_gaming.py`, `run_e9_forgery.py`,
`run_e10_adaptive.py` (module-level `SEEDS` constants; outputs written to
`*_EXT.json`/`*_EXT.md` companions; the registered artifacts are preserved
byte-for-byte). E15/E16 Monte-Carlo re-seeds are a secondary check (their
primary endpoints are analytic/closed-form).

**Endpoints (registered):**
1. Every registered success condition of E6/E7/E9/E10 holds at **all three**
   new seeds → "seed-robust".
2. Any seed that fails a registered condition → reported as observed with the
   per-seed table; artifacts retained; a diagnosis entry is mandatory before
   any re-run.
3. Combined estimate: per-experiment headline quantities re-reported across
   all five seeds (original two + three new) as mean ± range.

**Kill criterion E19:** the extension does not gate any existing claim; it
strengthens or surfaces fragility. A fragility finding downgrades the
affected claim in the paper until diagnosed.

## 3. E20 — the disclosure frontier: bounded-noise release of a security profile

**Gap.** E14 showed the full profile is a targeting map (advantage
$A_{\mathrm{rec}}=0.067$ on the graded foil) and offered the scalar $U_{\max}$
as a defensive corner (advantage 0, but zero family information). No
mechanism existed between the corners.

**Design (pre-analysis on frozen E4 profiles, graded foil, MC $N=2000$ per
cell, seeded).** Release mechanism: per-cell Laplace noise,
$\tilde\beta_f = \mathrm{clip}(\hat\beta_f + \mathrm{Lap}(1/\varepsilon), 0, 1)$
— $\varepsilon$-DP-style bounded disclosure over the profile space
(neighboring profiles differing by ≤1 in one cell; L1 sensitivity 1).
Grid: $\varepsilon \in \{0.25, 0.5, 1, 2, 4, 8\}$ plus the two corners
($\varepsilon=\infty$ full release; the scalar $U_{\max}$).

**Endpoints (registered):**
1. Attacker advantage $A_{\mathrm{rec}}(\varepsilon)$ = success of
   $\arg\max_f \tilde\beta_f$ under the TRUE (held) profile minus the uniform
   mean — expected to decrease monotonically as $\varepsilon \to 0$.
2. Defender utility = Kendall $\tau$ between the released family ranking and
   the true ranking — expected to increase with $\varepsilon$.
3. The **disclosure frontier**: the Pareto set over
   (attacker advantage ↓, defender utility ↑); the corners marked.
4. **Registered success:** there exists $\varepsilon$ such that the noised
   release **dominates the scalar $U_{\max}$** (strictly positive defender
   utility at attacker advantage ≤ the scalar's 0) **and** dominates the full
   release (strictly lower advantage at utility ≥ full release's ranking
   quality minus noise tolerance). If instead the corners sit on the frontier
   (no dominating interior point), report that as the finding — the scalar is
   optimal in this model, and the paper says so.
5. DP statement (fixed before data): the guarantee is over the profile space
   with L1 sensitivity 1 per neighboring profile — a formal ε-DP release of
   the *profile*; it is NOT a DP guarantee over the underlying probe outcomes
   (aggregation already occurred), and the artifact states this boundary.

**Claim boundary:** decision analysis on frozen profiles with a seeded
attacker; the Laplace mechanism is standard machinery (cited); the new object
is the disclosure frontier of a behavioral security certificate.

---

## 4. Disclosures fixed before data

- All three offline; frozen data or newly seeded re-runs of registered
  protocols; estimator untouched (`8ceb6e0`); registered artifacts preserved
  byte-for-byte (E19 writes `*_EXT` companions).
- E18's prior is fit per-experiment from the same experiment's cells (no
  information leaks across experiments); the credible-interval geometry is
  reported alongside, not instead of, the Wilson geometry.
- E19's extension seeds were fixed in this document before any extension run.
- E20's $\varepsilon$ grid, attacker model, utility metric, and success
  conditions were fixed in this document before any noise draw.
- No deviation after this entry without a new dated entry; failed conditions
  retained per program rules.

## 5. Dated deviations

- **2026-11-20 (E20, pre-acceptance, attacker construct).** The registration
  did not specify the attacker's tie-break among equal released values. The
  first run used a deterministic low-index tie-break, which in the deep-noise
  regime (many cells clipped to 1.0) systematically selected low-index
  families and produced a spurious NEGATIVE attacker advantage
  (−0.084 at ε=0.25) — a construct artifact, not a deception effect.
  Operationalized before acceptance: the indifferent attacker picks
  uniformly at random among tied maxima. First-run artifacts retained as
  `e20_disclosure_frontier_FIRST_RUN_TIEBREAK_DEFECT.json` / `.md`.
- **2026-11-20 (E18, pre-acceptance, prior fallback).** The method-of-moments
  prior is undefined not only at degenerate variance but also under
  overdispersion (t ≤ 0 — E17's cell variance exceeds the binomial ceiling);
  both cases now fall back to Beta(1,1) with disclosure. Also: the verdict
  key was corrected to the registered test (zero DECISION flips), with
  interval agreement reported separately — continuous posteriors exclude
  exactly-zero cells by construction, so boundary-cell disagreement is a
  disclosed property, not a decision failure. No endpoint was recorded
  before these corrections.
- **2026-11-20 (E20, pre-acceptance, tau-b tie handling).** `kendall_tau_b`
  mishandled JOINT ties (pairs tied in both rankings were excluded from the
  numerator but not counted in the two denominators), so the identity check
  tau(profile, profile) returned 0.400 instead of 1.0 on the tied E4 profile
  ([0.333, 0.667×4]). Fixed; an identity self-check (`tau == 1.0`) is now an
  assertion that fails the run. Second retained pre-acceptance artifact:
  the tie-break-defect run above.
- **2026-11-20 (E3, mid-run, execution parallelism — no measurement change).**
  The sequential driver measures ~6.9 calls/min (lane latency ~7 s + inter-probe
  sleep), projecting ~3 h wall time for the remaining chain. Because every
  tomography probe is an independent, stateless lane call and the five persona
  pipelines are independent (separate SSH sessions), execution is switched to
  concurrent (probe threads capped at 6; persona pipelines concurrent; per-
  persona session turns remain internally serial). The registered probe SET per
  persona+seed is unchanged — resume from the JSONL checkpoints restores the
  exact completed set (baseline snapshotted to /tmp/e3_resume_baseline.txt
  before restart). No change to probes, oracles, seeds, endpoints, or kill
  gates. Deviation logged before the resumed run started.
