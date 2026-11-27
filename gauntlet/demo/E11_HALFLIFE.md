# E11 — Certificate half-life under behavioral drift (T11)

Pre-registered: `docs/paper/belief_tomography/PREREGISTRATION_E11.md` (including the pre-data amendment), frozen `tomograph` at `8ceb6e0`.

True beta at epoch e = min(1, 0.05 e); tau = 0.2 (crossed at e=4).

| seed | epoch | beta_hat | Wilson U | half-life h_e | certified |
|---|---|---|---|---|---|
| 2718 | 0 | 0.000 | 0.060 | 2.80 | yes |
| 2718 | 1 | 0.050 | 0.137 | 1.26 | yes |
| 2718 | 2 | 0.100 | 0.202 | -0.03 | no |
| 2718 | 3 | 0.200 | 0.318 | -2.36 | no |
| 2718 | 4 | 0.200 | 0.318 | -2.36 | no |
| 2718 | 5 | 0.250 | 0.372 | -3.45 | no |
| 2718 | 6 | 0.350 | 0.476 | -5.53 | no |
| 2718 | 7 | 0.400 | 0.526 | -6.53 | no |
| 2718 | 8 | 0.400 | 0.526 | -6.53 | no |
| 99001 | 0 | 0.000 | 0.060 | 2.80 | yes |
| 99001 | 1 | 0.050 | 0.137 | 1.26 | yes |
| 99001 | 2 | 0.100 | 0.202 | -0.03 | no |
| 99001 | 3 | 0.200 | 0.318 | -2.36 | no |
| 99001 | 4 | 0.200 | 0.318 | -2.36 | no |
| 99001 | 5 | 0.250 | 0.372 | -3.45 | no |
| 99001 | 6 | 0.350 | 0.476 | -5.53 | no |
| 99001 | 7 | 0.400 | 0.526 | -6.53 | no |
| 99001 | 8 | 0.400 | 0.526 | -6.53 | no |

## Policies

| seed | policy | false certs | tomography runs |
|---|---|---|---|
| 2718 | one-shot | 4 | 1 |
| 2718 | fixed interval | 0 | 5 |
| 2718 | drift-aware | 0 | 2 |
| 99001 | one-shot | 4 | 1 |
| 99001 | fixed interval | 0 | 5 |
| 99001 | drift-aware | 0 | 2 |

**E11 supported: True.** A certificate asserted once and assumed valid forever is falsified by drift; a half-life renewal rule keeps the certificate valid with fewer measurements than a fixed calendar interval. Existence result on a deterministic foil with a *known* drift bound; in deployment the bound must be established by policy (e.g. model-change events), which we do not solve here.

