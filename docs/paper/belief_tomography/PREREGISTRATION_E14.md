# Pre-registration — E14 and T14 (the reconnaissance externality of a published tomogram)

**Logged:** 2026-11-19, **before any E14 computation was performed.**
**Data:** pre-existing, frozen `e4_separation.json` (E4, commit `0888540`).
This is a **pre-analysis** registration: the data was collected earlier for a
different endpoint (certification separation), and no reconnaissance quantity
has been computed from it before this entry. Offline; no API lane.

## Gap

Certificates are published (benchmarks, model cards, audit reports). A tomogram
is a vector of per-family breach probabilities $\hat\beta_f$ --- exactly the
information an attacker needs to choose which attack family to deploy. None of
the certification, defeat-device, or evaluation-limit literature treats the
*publication of the measurement* as an attack surface. Adjacent work on social
engineering exposure (Social-HUMINT, arXiv:2610.31573) profiles *humans* for
targeting; the analogous externality for agent security certificates is
unoccupied in our sweep.

## 1. T14 — Reconnaissance externality (proof obligation before computation)

Let an attacker choose a family $f$ without a tomogram (uniform choice) or with
the published profile (choose $\arg\max_f \hat\beta_f$). Let $\beta_f$ be the
true family breach probabilities. Then:

- uninformed success $= \frac{1}{K}\sum_f \beta_f$;
- informed success $= \beta_{f^*}$ for $f^*=\arg\max_f \hat\beta_f$;
- **reconnaissance advantage** $A_{\mathrm{rec}} = \beta_{f^*} - \frac{1}{K}\sum_f\beta_f \ge 0$.

With finite samples the inferred $f^*$ can be wrong, so we report a Wilson-bound
lower/upper range for $A_{\mathrm{rec}}$ using the published CIs. $A_{\mathrm{rec}}=0$
when the profile is flat (no targeting information); it is maximal when one
family carries all the risk.

**Claim boundary:** elementary decision analysis; not a new theorem. The new
object is $A_{\mathrm{rec}}$ as a *disclosure cost* of a security certificate,
and the minimax-certificate defense below.

**Defense (registered):** publish only the scalar
$U_{\max}=\max_f U_f$ (the worst-family upper confidence bound) instead of the
vector. The attacker then has no family ranking, so informed success reverts to
the uniform mean; the defender loses family-level allocation information. We
report the disclosure cost and this loss as the tradeoff; we do not claim an
optimal disclosure mechanism.

## 2. E14 — registered computation

**Data:** E4 foils `NaiveDummy`, `HardenedDummy`, `ResistantDummy`, seeds
$\{31337,71002\}$, batch 10/cell, from `e4_separation.json`.

**Endpoints (registered):**
1. For each foil and seed: mean $\hat\beta$ (uniform baseline) and
   $\max_f \hat\beta_f$ (informed choice), with the chosen family $f^*$.
2. $A_{\mathrm{rec}} = \max_f\hat\beta_f - \mathrm{mean}_f\hat\beta_f$.
3. A Wilson-bound sensitivity range: use $\min_f U_f$ and $\max_f U_f$ to bound
   the advantage under estimation uncertainty.
4. Minimax certificate: $U_{\max}=\max_f U_f$ for each foil; report the scalar
   and the resulting loss of family-level information (number of distinguishable
   families).

**Registered success:** $A_{\mathrm{rec}} > 0$ for the graded foil (non-flat
profile), $A_{\mathrm{rec}} = 0$ for the flat foils (naive/resistant), and the
minimax certificate is computable for all foils. Otherwise report as observed.

**Kill criterion E14:** do not claim the externality unless the graded foil's
advantage is strictly positive and both flat foils measure zero.

## 3. Disclosures fixed before data

- This is a decision-analysis result on **already-collected** E4 profiles, not
  a new behavioral measurement. Attack success is derived from the published
  $\hat\beta$, not measured against a live attacker.
- The E4 profiles use 10 probes/cell; the Bayesian/worst-case bounds are wider
  than the 20/cell E2 panel. No number is transferred to E2-v1.
- The lexical oracle's disclosed boundary behavior applies to the underlying
  E4 profiles; the reconnaissance computation inherits it.
- No deviation after this entry without a new dated entry.
