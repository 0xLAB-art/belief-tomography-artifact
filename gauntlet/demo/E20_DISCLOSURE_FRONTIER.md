# E20 — The disclosure frontier (bounded-noise release of a security profile)

Pre-analysis registered: `docs/paper/belief_tomography/PREREGISTRATION_E18E19E20.md`. Frozen E4 profile (HardenedDummy, seed 31337); Laplace(1/eps) per cell, MC N=2000, seed 90210; attacker = argmax of the released profile; utility = Kendall tau-b vs the true ranking (0 if undefined). The DP guarantee is over the PROFILE space (L1 sensitivity 1 per neighboring profile), not over the underlying probe outcomes — disclosed boundary.

## Corners

| release | attacker advantage | Kendall tau | top-1 recovery |
|---|---|---|---|
| full vector (eps=inf) | 0.067 | 1.000 | 0.248 |
| scalar Umax | 0.000 | 0.000 | 0.200 |

## Noised releases (the trade-off curve)

| eps | attacker advantage | Kendall tau | top-1 recovery |
|---|---|---|---|
| 0.25 | 0.0068 | 0.040 | 0.199 |
| 0.5 | 0.0098 | 0.055 | 0.210 |
| 1.0 | 0.0210 | 0.134 | 0.229 |
| 2.0 | 0.0315 | 0.214 | 0.214 |
| 4.0 | 0.0477 | 0.352 | 0.240 |
| 8.0 | 0.0628 | 0.537 | 0.243 |

## Verdict

- Advantage monotone decreasing in noise: **True**
- Utility monotone increasing in eps: **True**
- Interior points dominating the scalar: **none**
- Interior points dominating the full release: **none**

**E20 outcome: corners on frontier: no free lunch — the scalar Umax is optimal against the argmax attacker, and the noised family traces the trade-off curve between the corners**

