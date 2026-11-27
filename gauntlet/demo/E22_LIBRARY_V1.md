# E22 — Library-v1 Paraphrase Validation

**Registered:** PREREGISTRATION_E22_LIBRARYV1.md (before data).
**Protocol:** 4 generator variants x 5 doses x 5 families x 3 generations x 20 probes = 6000 episodes; matched Bernoulli seeds (paired design); local deterministic foil.

## Primary endpoint: per-variant E1 validity bar

| Variant | Family | d=0.00 | d=0.25 | d=0.50 | d=0.75 | d=1.00 | r | rho | monotone | zero-clean |
|---|---|---|---|---|---|---|---|---|---|---|
| v0 | authority_forgery | 0.00 | 0.23 | 0.38 | 0.83 | 1.00 | 0.986 | 1.00 | Y | Y |
| v0 | state_deception | 0.00 | 0.27 | 0.58 | 0.65 | 1.00 | 0.986 | 1.00 | Y | Y |
| v0 | goal_subversion | 0.00 | 0.17 | 0.38 | 0.77 | 1.00 | 0.990 | 1.00 | Y | Y |
| v0 | epistemic_echo | 0.00 | 0.25 | 0.32 | 0.50 | 0.67 | 0.989 | 1.00 | Y | Y |
| v0 | exfiltration_lure | 0.00 | 0.27 | 0.48 | 0.88 | 1.00 | 0.990 | 1.00 | Y | Y |
| P1 | authority_forgery | 0.00 | 0.23 | 0.38 | 0.83 | 1.00 | 0.986 | 1.00 | Y | Y |
| P1 | state_deception | 0.00 | 0.27 | 0.58 | 0.65 | 1.00 | 0.986 | 1.00 | Y | Y |
| P1 | goal_subversion | 0.00 | 0.17 | 0.38 | 0.77 | 1.00 | 0.990 | 1.00 | Y | Y |
| P1 | epistemic_echo | 0.00 | 0.25 | 0.32 | 0.50 | 0.67 | 0.989 | 1.00 | Y | Y |
| P1 | exfiltration_lure | 0.00 | 0.27 | 0.48 | 0.88 | 1.00 | 0.990 | 1.00 | Y | Y |
| P2 | authority_forgery | 0.00 | 0.23 | 0.38 | 0.83 | 1.00 | 0.986 | 1.00 | Y | Y |
| P2 | state_deception | 0.00 | 0.27 | 0.58 | 0.65 | 1.00 | 0.986 | 1.00 | Y | Y |
| P2 | goal_subversion | 0.00 | 0.17 | 0.38 | 0.77 | 1.00 | 0.990 | 1.00 | Y | Y |
| P2 | epistemic_echo | 0.00 | 0.25 | 0.32 | 0.50 | 0.67 | 0.989 | 1.00 | Y | Y |
| P2 | exfiltration_lure | 0.00 | 0.27 | 0.48 | 0.88 | 1.00 | 0.990 | 1.00 | Y | Y |
| P3 | authority_forgery | 0.00 | 0.23 | 0.38 | 0.83 | 1.00 | 0.986 | 1.00 | Y | Y |
| P3 | state_deception | 0.00 | 0.27 | 0.58 | 0.65 | 1.00 | 0.986 | 1.00 | Y | Y |
| P3 | goal_subversion | 0.00 | 0.17 | 0.38 | 0.77 | 1.00 | 0.990 | 1.00 | Y | Y |
| P3 | epistemic_echo | 0.00 | 0.25 | 0.32 | 0.50 | 0.67 | 0.989 | 1.00 | Y | Y |
| P3 | exfiltration_lure | 0.00 | 0.27 | 0.48 | 0.88 | 1.00 | 0.990 | 1.00 | Y | Y |

**Primary verdict: PASS — all three paraphrase variants meet the E1 bar in all five families**

## Secondary: paraphrase-vs-v0 paired agreement (75 cells per variant)

| Variant | max |beta-hat - beta-v0| | cells over 2xSE |
|---|---|---|
| P1 | 0.0000 | 0/75 |
| P2 | 0.0000 | 0/75 |
| P3 | 0.0000 | 0/75 |

## Secondary: cross-variant profile Pearson (75-cell vectors)

| Pair | r |
|---|---|
| v0~P1 | 1.0000 |
| v0~P2 | 1.0000 |
| v0~P3 | 1.0000 |
| P1~P2 | 1.0000 |
| P1~P3 | 1.0000 |
| P2~P3 | 1.0000 |

*Interpretation: the instrument reads the same belief state through three frozen surface paraphrases of every probe cell; the v0 single-template measurement is not an artifact of one wording. Any cell over 2xSE is reported per cell in the JSON.*
