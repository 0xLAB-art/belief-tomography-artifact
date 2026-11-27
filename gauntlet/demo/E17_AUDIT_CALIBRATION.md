# E17 — Seeded audit calibration (adjudication-channel operating characteristic)

Pre-analysis registered: `docs/paper/belief_tomography/PREREGISTRATION_E15E16E17.md`. Blind sheet 120 sessions = 50 frozen constructed (known truth) + 70 real E2-v1 sessions. Adjudicator = the documented transcript-reading rubric, blind to id/kind/family/oracle verdict. NOT the lexical oracle.

| metric | value | Wilson 95% |
|---|---|---|
| sensitivity (25 unsafe) | 0.960 | [0.8046, 0.9929] |
| specificity (25 safe) | 1.000 | [0.8668, 1.0] |
| FP rate | 0.000 | [0.0, 0.1332] |
| FN rate | 0.040 | [0.0071, 0.1954] |

## By kind (constructed)

| kind | n | TP | FP | TN | FN |
|---|---|---|---|---|---|
| boundary_breach | 15 | 14 | 0 | 0 | 1 |
| boundary_refusal | 10 | 0 | 0 | 10 | 0 |
| clear_breach | 10 | 10 | 0 | 0 | 0 |
| clear_refusal | 15 | 0 | 0 | 15 | 0 |

## Channel vs lexical oracle (same 50 sessions)

- Oracle FP 0.20 / FN 0.48 (frozen); adjudication-channel FP 0.000 / FN 0.040.
- Real E2 sessions: breaches found = 0 (NONE — consistent with E2-v1 zero-breach result); unavailable 18.
- Kill-(a) power: 25 seeded positives -> FP rates above ~0.12 are detectable (rule of three).

