# E26 — Measured Sensitivity L̂ on the Constructed Planes

**Registered:** PREREGISTRATION_E26_LSENSITIVITY.md (before computation).
**Data:** frozen `dose_response.json` (E1; 5 families × 5 doses × n=60).
**Estimator:** on the Bernoulli verdict channel d_TV(P_d1,P_d2)=|d1−d2|, so
L̂ = Δβ̂/Δdose.

| family | L̂ (endpoint) | conservative interval | max step (noisy) |
|---|---|---|---|
| authority_forgery | 1.000 | [0.880, 1.000] | 1.800 |
| state_deception | 1.000 | [0.880, 1.000] | 1.400 |
| goal_subversion | 1.000 | [0.880, 1.000] | 1.534 |
| epistemic_echo | 0.667 | [0.480, 0.773] | 1.000 |
| exfiltration_lure | 1.000 | [0.880, 1.000] | 1.600 |

**Program L̂ = 1.00** (endpoint, max over families; conservative interval
[0.48, 1.00] — the epistemic-echo lower bound reflects the audited
dose-1 oracle error of that family (Fig. 1: the naive foil's echo cell
reads 2/3), not sub-linear sensitivity). Per-step slopes exceed 1 at
n=60 (binomial noise), as registered.

**Reading:** β tracks the injected TV shift one-for-one on the planes where
the frontier theorems are instantiated — the caps are TIGHT at the measured
L, not slack. Production-target L remains unestimated (§10(1)): black-box
TV is not directly observable, and classifier-discrimination lower bounds
on TV yield lower bounds on L, not upper bounds.
