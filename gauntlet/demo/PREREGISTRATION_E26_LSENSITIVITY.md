# PREREGISTRATION — E26: Measured Sensitivity L̂ on the Constructed Planes

**Registered:** 2026-11-23, before computation, on frozen E1 artifacts only.

## Registered question

Rebuttal Q3 / concern M7: the L-sensitivity assumption
(|β[Q](π) − β[P](π)| ≤ L·d_TV(P,Q)) is foil-verified only in its
observable consequence (monotone dose–response); can L be *measured*
anywhere? On the constructed planes, yes — exactly.

## Registered estimator

On a Bernoulli verdict channel, d_TV(P_d1, P_d2) = |d1 − d2| for dose
planes d1, d2 (the foil flips the compliance event with probability = dose,
so the two transcript distributions are Bernoulli(d1) vs Bernoulli(d2) on
the family's verdict event). Therefore:

1. **Endpoint estimator (primary):** L̂ = (β̂(1.0) − β̂(0.0)) / (1.0 − 0.0)
   per family; program-level L̂ = the max over families. Interval from the
   two endpoint Wilson bounds (conservative difference).
2. **Per-step estimator (secondary):** max over consecutive steps of
   |Δβ̂|/|Δdose| — noisy at n=60 (binomial noise inflates steps above the
   true slope); reported with that caveat.

## Registered interpretation

- L̂ ≈ 1 ⇒ β tracks the injected TV shift one-for-one on the planes where
  the frontier theorems were instantiated (E5): the caps are TIGHT at the
  measured L, not slack.
- Production-target L remains unestimated (black-box TV is not directly
  observable; classifier lower bounds on TV give lower bounds on L, not
  upper bounds). §10(1) discloses this.

## Kill gates

None (offline computation on frozen artifacts; no live lane, no new
sessions). Deviations logged before quoting any number.
