# E16 — Detection budget vs attacker probe-discrimination error (T16)

Pre-analysis registered: `docs/paper/belief_tomography/PREREGISTRATION_E15E16E17.md`. Public probes/family n_pub=60, noise floor 0.047, power target 0.95, Monte Carlo N=2000/cell, seed 27182. Offline decision analysis.

## Closed form — minimum held-out budget n_min(m) for 95% detection (m' = 0)

| attacker held-out misread rate m | per-probe breach prob 1-m | n_min |
|---|---|---|
| 0.02 | 0.98 | 1 |
| 0.05 | 0.95 | 1 |
| 0.1 | 0.9 | 2 |
| 0.2 | 0.8 | 2 |
| 0.3 | 0.7 | 3 |
| 0.5 | 0.5 | 8 |

## Monte Carlo detection rate (m' = 0), registered grid

| m | n | k_min | detection rate | closed-form power |
|---|---|---|---|---|
| 0.02 | 10 | 3 | 1.000 | 1.0 |
| 0.02 | 20 | 4 | 1.000 | 1.0 |
| 0.02 | 40 | 6 | 1.000 | 1.0 |
| 0.02 | 80 | 9 | 1.000 | 1.0 |
| 0.02 | 160 | 16 | 1.000 | 1.0 |
| 0.05 | 10 | 3 | 1.000 | 1.0 |
| 0.05 | 20 | 4 | 1.000 | 1.0 |
| 0.05 | 40 | 6 | 1.000 | 1.0 |
| 0.05 | 80 | 9 | 1.000 | 1.0 |
| 0.05 | 160 | 16 | 1.000 | 1.0 |
| 0.1 | 10 | 3 | 1.000 | 1.0 |
| 0.1 | 20 | 4 | 1.000 | 1.0 |
| 0.1 | 40 | 6 | 1.000 | 1.0 |
| 0.1 | 80 | 9 | 1.000 | 1.0 |
| 0.1 | 160 | 16 | 1.000 | 1.0 |
| 0.2 | 10 | 3 | 1.000 | 0.9999 |
| 0.2 | 20 | 4 | 1.000 | 1.0 |
| 0.2 | 40 | 6 | 1.000 | 1.0 |
| 0.2 | 80 | 9 | 1.000 | 1.0 |
| 0.2 | 160 | 16 | 1.000 | 1.0 |
| 0.3 | 10 | 3 | 0.999 | 0.9984 |
| 0.3 | 20 | 4 | 1.000 | 1.0 |
| 0.3 | 40 | 6 | 1.000 | 1.0 |
| 0.3 | 80 | 9 | 1.000 | 1.0 |
| 0.3 | 160 | 16 | 1.000 | 1.0 |
| 0.5 | 10 | 3 | 0.947 | 0.9453 |
| 0.5 | 20 | 4 | 1.000 | 0.9987 |
| 0.5 | 40 | 6 | 1.000 | 1.0 |
| 0.5 | 80 | 9 | 1.000 | 1.0 |
| 0.5 | 160 | 16 | 1.000 | 1.0 |

## One-sided regime (m' = m): public-probe breach is fatal

| m | m' | P(>=1 public breach in 60) |
|---|---|---|
| 0.02 | 0.02 | 0.7024 |
| 0.05 | 0.05 | 0.9539 |
| 0.1 | 0.1 | 0.9982 |
| 0.2 | 0.2 | 1.0000 |
| 0.3 | 0.3 | 1.0000 |
| 0.5 | 0.5 | 1.0000 |

## Evasion-feasibility frontier (m' = 0): required held-out budget

| m | n_min |
|---|---|
| 0.5 | 8 |
| 0.52 | 8 |
| 0.54 | 9 |
| 0.56 | 9 |
| 0.58 | 13 |
| 0.6 | 14 |
| 0.62 | 15 |
| 0.64 | 16 |
| 0.66 | 17 |
| 0.68 | 22 |
| 0.7 | 24 |
| 0.72 | 26 |
| 0.74 | 33 |
| 0.76 | 36 |
| 0.78 | 45 |
| 0.8 | 57 |
| 0.82 | 77 |
| 0.84 | 103 |
| 0.86 | 153 |
| 0.88 | 257 |
| 0.9 | 549 |
| 0.92 | 2057 |
| 0.94 | >4000 (undetectable at any feasible budget) |
| 0.96 | >4000 (undetectable at any feasible budget) |
| 0.98 | >4000 (undetectable at any feasible budget) |

## Verdict

- Closed-form n_min complete on grid: **True**
- n_min monotone in m: **True**
- MC matches closed form (3-sigma): **True**
- One-sided asymmetry confirmed: **True**

**E16 supported: True.** The attacker's own discrimination fallibility is the defender's detection resource: evasion of the gaming-gap diagnostic requires error-free one-sided discrimination of the public support; any misclassification toward breaching on a public probe fails the public certificate immediately, and the held-out budget needed for guaranteed detection diverges as the attacker's held-out recognition error approaches 1.

