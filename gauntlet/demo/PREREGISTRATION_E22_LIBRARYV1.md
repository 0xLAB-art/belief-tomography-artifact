# PREREGISTRATION — E22: Library-v1 Paraphrase Validation

**Registered:** 2026-11-22, before any E22 data was collected.
**Status:** closes paper limitation §10(2) (template diversity: v0 = one template
per (family, generation) cell).

## Registered question

Does the tomography instrument produce the same measurements when the probe
SURFACE text is paraphrased? If β̂ is a property of the agent's belief state
(and of the probe family's semantics), frozen semantic-preserving paraphrases
must reproduce the v0 dose–response validity and the v0 profile within
binomial noise. If they do not, the v0 single-template measurement is
wording-bound and the limitation is real.

## Frozen instrument (before data)

- Generator: `gauntlet/gauntlet/generator_v1.py` — 3 paraphrase variants
  (P1/P2/P3) per (family, generation) cell, hand-frozen strings, commit-pinned
  at run time. Paraphrases preserve attack semantics, foil trigger tokens,
  canary rendering (case-flip, split lines), and oracle payloads exactly;
  all other surface wording varies.
- Preflight (already executed, no E22 data): trigger-parity preflight on the
  deterministic naive foil at full dose — each variant must reproduce the v0
  breach pattern cell-for-cell (15/15), including the faithful reproduction of
  the v0 split-secret false negative at epistemic_echo g3. Result: P1/P2/P3
  parity 15/15 after two fix rounds (10 trigger-token defects found by the
  preflight and repaired; the preflight log is part of this registration).
- Estimator: frozen — Wilson score intervals, HeuristicJury (deterministic
  oracles), episode-level Bernoulli dose foil (DosedFoil), identical to E1.

## Protocol

For each variant in {v0 baseline, P1, P2, P3}: the full E1 dose–response grid —
5 dose levels {0, 0.25, 0.5, 0.75, 1.0} × 5 families × 3 generations × 20 probes
= 1,500 episodes per variant, 6,000 episodes total; seeds frozen (700+i per dose
as in E1; generator seed 1000 + di*97 + gen); local deterministic foil, no
network.

## Endpoints (registered)

1. **Primary (per variant):** the E1 validity bar — Pearson r ≥ 0.98 over the
   dose grid, Spearman ρ = 1.00, monotone, zero-dose clean, all five families.
2. **Secondary (paraphrase–v0 agreement):** per-cell |β̂_P − β̂_v0| over the 75
   (family, gen, dose) cells; report max and the fraction of cells exceeding
   2× the per-cell binomial SE.
3. **Secondary (cross-variant):** pairwise Pearson correlation between variant
   profiles over the 75 cells.

## Kill criteria / honest-reporting rules

- Any variant failing the primary bar → reported as semantic drift of that
  paraphrase; the variant is flagged in the artifact; NO re-rolling of
  paraphrases after seeing data.
- Agreement failures concentrated in specific cells → reported per cell (they
  localize which surface changes move the measurement).
- All outcomes (pass or fail) are quoted into the paper's limitations update.

## Deviations

Any deviation from this protocol is logged in this file with a timestamp
before the affected data is analyzed.

## Deviation log (actual run)

- 2026-11-22 pre-data: two runner crashes before any E22 episode (agreement-loop
  KeyError 'se'; merged-cell ZeroDivision from a redundant collapse step — the
  dose cells were already per-dose at n=60). Both fixed pre-data; no episode
  from the crashed runs was analyzed.
- Final run: 6,000 episodes, rc=0. PRIMARY PASS; paraphrase-v0 max|delta| = 0.000
  (0/75 cells over 2xSE); cross-variant Pearson = 1.000 everywhere.
- Note: exact-zero deltas are the paired-design expectation (matched Bernoulli
  seeds + trigger-preserving paraphrases on a deterministic foil), not a red flag.
