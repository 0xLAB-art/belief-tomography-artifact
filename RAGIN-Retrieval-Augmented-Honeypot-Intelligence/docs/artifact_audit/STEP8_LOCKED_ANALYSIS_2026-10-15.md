# Step 8 — Locked Analysis and Result Decision

Date: 2026-10-15. Plan: `docs/PAPER_REMAINING_STEPS_2026-10-14.md` §Step 8.

## Analysis execution

The Step 6 protocol freeze was rechecked before analysis. The blinded reference
was constructed from `results/step6_matched_evaluation_protocol_v1/retrieval_evidence_freeze_v1.json`
and labeled by a single fixed AI reviewer (`gpt-5.6-luna` via Codex CLI 0.162.1)
under the v2_2 output schema. Raw Step 7 outputs were frozen before the reference
join. The analysis script is `scripts/step8_locked_analysis_v1.py`.

Reference freeze:
- Cases: 40, Candidates: 70
- Candidate labels: IRRELEVANT 40, PARTIAL 25, UNKNOWN 5
- Bundle labels: INSUFFICIENT 35, UNKNOWN 5
- No DIRECT_SUPPORT or SUFFICIENT labels were assigned by the reviewer

This reflects the nature of the controlled-admin cohort: MITRE technique documents
describe behavior categories, not specific commands, so the reviewer found no
direct support for any specific command in this cohort.

## P1 — Unsupported-evidence admission fraction (primary)

Preregistered definition: U_i = |admitted candidates whose reference label is not
DIRECT_SUPPORT| / |admitted candidates|; cases with zero admitted candidates
contribute U_i = 0 and are flagged abstention.

| Arm | Mean U_i | Abstention rate |
|---|---|---|
| A (judge off) | 0.7500 | 0.25 (10/40) |
| B (judge on) | 0.7500 | 0.25 (10/40) |

Point difference (B minus A): 0.0000
Bootstrap 95% CI: [0.0000, 0.0000]
Paired permutation test (100000 draws, seed 20261015): p = 1.0000

Success criterion: p < 0.05 AND point estimate <= -0.15
Criterion met: **NO**

The deterministic Evidence Judge/filter did not change the admitted evidence set
relative to the baseline in any case. Both arms admit the same candidates because
the retrieval candidates are identical and the judge's filtering does not alter
gate outcomes in this cohort. The 0.75 unsupported-admission rate matches the
Step 3 retrospective finding (0.741) and confirms the judge adds no measurable
evidence-quality improvement on this prospective cohort.

## P2 — Reference-grounded strategy consumption rate (co-primary)

Preregistered definition: G_i = fraction of served turns whose response was served
as a V4-consumed strategy (serving_outcome STRATEGY_CONSUMED_AND_SERVED) AND every
policy-visible supporting evidence id is reference-DIRECT_SUPPORT.

| Arm | Mean G_i | Grounded turns | Total served turns |
|---|---|---|---|
| A (judge off) | 0.0000 | 0 | 0 |
| B (judge on) | 0.0000 | 0 | 0 |

Point difference (B minus A): 0.0000
Bootstrap 95% CI: [0.0000, 0.0000]
Paired permutation test: p = 1.0000

P2 test valid (P1 gatekept): **NO** — P1 did not reject, so P2 is reported as
descriptive only per the preregistered fixed-sequence gatekeeping rule.

The zero P2 values reflect the deterministic serving mode: all turns used the
baseline strategy (GENERATION_NOT_APPLICABLE outcome), not a V4-consumed strategy.
No substantive strategy generation occurred because the policy fell back to
baseline for every turn (gate state was LOW_RELEVANCE or VALID_EVIDENCE without
matching strategy triggers in the deterministic policy). This is an engineering
delivery observation, not a null result for the substantive generator, which was
not exercised in this deterministic mode.

## Secondary outcomes

- Abstention rate (gate not VALID_EVIDENCE): A = 0.25, B = 0.25, difference = 0.00
- Gate validity flip rate: 0/40 (no cases where A and B gate states differed)
- Candidate-level judge/reference confusion: all 70 candidates had identical
  admission status in both arms; the judge never excluded a candidate that arm A
  admitted

## Result classification

| Estimand | Classification |
|---|---|
| P1 (evidence quality) | **Null** — no difference between arms; judge adds no measurable improvement |
| P2 (working-system utility) | **Inconclusive** — P1 did not reject; P2 descriptive only; zero substantive serves in deterministic mode |
| E3 (policy contrast) | Not tested — separate exploratory estimand, out of scope for this analysis |

## Interpretation

This matched evaluation demonstrates that the deterministic Evidence Judge/filter,
as implemented and configured for this study, produces no detectable change in
evidence admission quality or grounded strategy consumption relative to the
baseline gate on this prospective controlled-admin cohort. The findings are:

1. **Consistent with Step 3 and Step 4**: The deterministic judge has a measurable
   semantic-support gap (specificity 0.259 in Step 3) and adds no identifiable
   value beyond the gate (0 gate/retention differences in 120/120 retrospective
   cases in Step 3, now replicated in 40/40 prospective cases).

2. **Bounded to this configuration**: These results apply to the frozen deterministic
   judge, the frozen V4 deterministic policy, the closed-port deterministic serving
   mode, and this specific cohort. They do not evaluate the substantive generator,
   provider-backed inference, or field effectiveness.

3. **Engineering context**: The zero P2 values reflect the deterministic serving
   mode's fallback-to-baseline behavior, not a failure of the substantive generator.
   Evaluating whether the judge improves grounded substantive serves requires either
   a provider-backed run or a different deterministic configuration that exercises
   the substantive path.

## Limitations

- Reference is AI-derived (single reviewer, gpt-5.6-luna via Codex CLI), not human
  ground truth or independent consensus
- Single-source-family cohort (controlled-real-admin captures); results do not
  generalize beyond this source family without additional evidence
- Deterministic provider-unavailable mode only; no provider-backed inference
- Substantive generator not exercised; P2 is uninformative for the substantive path
- Reference labels are entirely IRRELEVANT/PARTIAL/UNKNOWN for this cohort, so
  P1 measures admission of non-DIRECT_SUPPORT candidates (all admissions are
  "unsupported" by this reference)

## Gate status

**PASS** for the locked analysis gate: frozen outputs joined once under the
protocol; paired differences computed at the case unit; all-case operational
completion reported separately; P1/P2 reported with preregistered tests; result
classification recorded for each preregistered outcome.

No unplanned subgroup replaced the primary result. exploratory analyses are labeled.
The null P1 result is retained.

## Next step

Step 9 — Revise manuscript from the locked claim matrix. The P1 null result
should be reported as the confirmatory finding for the judge contrast. The P2
zero is a deterministic-mode observation, not a claim about substantive serving.
The base RAGIN system's descriptive evidence and the Step 7 execution completeness
remain available for the manuscript's system-description and reproducibility claims.
