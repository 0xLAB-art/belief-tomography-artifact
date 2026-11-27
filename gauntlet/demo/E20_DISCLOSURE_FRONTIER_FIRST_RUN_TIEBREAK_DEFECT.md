# E20 — The disclosure frontier (bounded-noise release of a security profile)

Pre-analysis registered: `docs/paper/belief_tomography/PREREGISTRATION_E18E19E20.md`. Frozen E4 profile (HardenedDummy, seed 31337); Laplace(1/eps) per cell, MC N=2000, seed 90210; attacker = argmax of the released profile; utility = Kendall tau-b vs the true ranking (0 if undefined). The DP guarantee is over the PROFILE space (L1 sensitivity 1 per neighboring profile), not over the underlying probe outcomes — disclosed boundary.

## Corners

| release | attacker advantage | Kendall tau | top-1 recovery |
|---|---|---|---|
| full vector (eps=inf) | 0.067 | 0.400 | 1.000 |
| scalar Umax | 0.000 | 0.000 | 0.200 |

## Noised releases (the trade-off curve)

| eps | attacker advantage | Kendall tau | top-1 recovery |
|---|---|---|---|
| 0.25 | -0.0844 | 0.016 | 0.272 |
| 0.5 | -0.0558 | 0.036 | 0.274 |
| 1.0 | -0.0263 | 0.086 | 0.298 |
| 2.0 | 0.0103 | 0.173 | 0.285 |
| 4.0 | 0.0453 | 0.351 | 0.253 |
| 8.0 | 0.0630 | 0.536 | 0.245 |

## Verdict

- Advantage monotone decreasing in noise: **True**
- Utility monotone increasing in eps: **True**
- Interior points dominating the scalar: **[0.25, 0.5, 1.0]**
- Interior points dominating the full release: **[8.0]**

**E20 outcome: interior dominance found**

