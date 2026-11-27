# E15 — Counterintelligence tomogram: deception release (T15)

Pre-analysis registered: `docs/paper/belief_tomography/PREREGISTRATION_E15E16E17.md`. Attacker budget B=120, Monte Carlo N=2000, seed 31337. True behavior = E9 held profile; published = E9 display profile. Decision analysis on frozen data, not a behavioral measurement.

## ShapingFoil (seed 2718)

| policy | expected attacker success |
|---|---|
| uniform | 24.0000 |
| honest_argmax | 120.0000 |
| decoy_argmax | 0.0000 |
| decoy_proportional | 0.0000 |
| public_verifier_v0.2 | 0.0000 |
| public_verifier_v0.5 | 0.0000 |
| heldout_verifier_p0.0 | 0.0000 |
| heldout_verifier_p0.5 | 12.0000 |
| heldout_verifier_p1.0 | 24.0000 |

- deception gain (argmax): **120.0000** (honest 120.000 → decoy 0.000)
- deception gain (proportional): 120.0000
- stable under public verification: True; monotone collapse in p_ho: True

## ShapingFoil (seed 99001)

| policy | expected attacker success |
|---|---|
| uniform | 24.0000 |
| honest_argmax | 120.0000 |
| decoy_argmax | 0.0000 |
| decoy_proportional | 0.0000 |
| public_verifier_v0.2 | 0.0000 |
| public_verifier_v0.5 | 0.0000 |
| heldout_verifier_p0.0 | 0.0000 |
| heldout_verifier_p0.5 | 12.0000 |
| heldout_verifier_p1.0 | 24.0000 |

- deception gain (argmax): **120.0000** (honest 120.000 → decoy 0.000)
- deception gain (proportional): 120.0000
- stable under public verification: True; monotone collapse in p_ho: True

## HonestFoil (seed 2718)

| policy | expected attacker success |
|---|---|
| uniform | 24.0000 |
| honest_argmax | 120.0000 |
| decoy_argmax | 120.0000 |
| decoy_proportional | 120.0000 |
| public_verifier_v0.2 | 96.0000 |
| public_verifier_v0.5 | 60.0000 |
| heldout_verifier_p0.0 | 120.0000 |
| heldout_verifier_p0.5 | 72.0000 |
| heldout_verifier_p1.0 | 24.0000 |

- deception gain (argmax): **0.0000** (honest 120.000 → decoy 120.000)
- deception gain (proportional): 0.0000
- stable under public verification: False; monotone collapse in p_ho: False

## HonestFoil (seed 99001)

| policy | expected attacker success |
|---|---|
| uniform | 24.0000 |
| honest_argmax | 120.0000 |
| decoy_argmax | 120.0000 |
| decoy_proportional | 120.0000 |
| public_verifier_v0.2 | 96.0000 |
| public_verifier_v0.5 | 60.0000 |
| heldout_verifier_p0.0 | 120.0000 |
| heldout_verifier_p0.5 | 72.0000 |
| heldout_verifier_p1.0 | 24.0000 |

- deception gain (argmax): **0.0000** (honest 120.000 → decoy 120.000)
- deception gain (proportional): 0.0000
- stable under public verification: False; monotone collapse in p_ho: False

## Verdict

- ShapingFoil decoy misdirects (gain > 0): **True**
- HonestFoil control gain zero: **True**
- Verification stability (public suite): **True**
- Monotone trust collapse in p_ho: **True**

**E15 supported: True.**

