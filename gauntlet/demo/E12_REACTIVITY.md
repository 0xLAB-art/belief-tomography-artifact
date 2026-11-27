# E12 — Tomographic reactivity (shared context changes the estimand)

Pre-registered: `docs/paper/belief_tomography/PREREGISTRATION_E12.md`, logged before data. Frozen `tomograph` at `8ceb6e0`. This reconstructs the mechanism that invalidated E2-v0; it does NOT rehabilitate any v0 number.

| seed | mode | max family beta | in-context breaches |
|---|---|---|---|
| 2718 | independent | 0.500 | 1 |
| 2718 | shared | 0.033 | 2 |
| 99001 | independent | 0.500 | 1 |
| 99001 | shared | 0.033 | 2 |

| seed | bias | relative bias | supported |
|---|---|---|---|
| 2718 | 0.467 | 93.3% | True |
| 99001 | 0.467 | 93.3% | True |

**E12 supported: True.** A shared conversation changes the measured belief profile: the independent-session estimand is recovered under reset, while the shared-context estimator converges on a different, context-conditioned quantity. Session isolation is therefore an identification condition, not an engineering nicety. Constructed deterministic foil; the observer-effect analogy to other measurement sciences is acknowledged and novelty is claimed only for the estimator-level bias and its identification condition.

