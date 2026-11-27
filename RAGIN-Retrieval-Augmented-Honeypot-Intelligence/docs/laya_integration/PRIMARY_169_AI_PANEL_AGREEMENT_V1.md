# Primary 169 AI Panel Agreement V1

This document reports run-to-run self-consistency under blinded repeated inference. It does not report independent-model reliability, because all three primary annotations and the fourth adjudication used the same APMix model configuration, `claude-sonnet-4-6-free`, in fresh isolated contexts.

## Frozen scope

- Cases: 169 primary holdout cases.
- Input: the frozen behavior-only blind annotation source and independently shuffled packets.
- Primary runs: three fresh isolated APMix calls.
- Adjudication: one fresh isolated APMix call for every non-exact-3/3 case.
- Taxonomy, binary projection, uncertainty policy, aggregation rule, and acceptance gates were frozen before annotation.
- RAGIN A/B outputs, Laya decisions, Chrollo predictions, verifier outcomes, and effectiveness artifacts were not accessed.

## Multiclass agreement

| Primary runs | Exact agreement | Cohen kappa |
|---|---:|---:|
| 1 vs 2 | 0.852071 | 0.781417 |
| 1 vs 3 | 0.739645 | 0.558144 |
| 2 vs 3 | 0.757396 | 0.606731 |

Three-run Fleiss kappa: 0.652129.

Exact 3/3 cases: 116. Exact 2/3 cases: 49. Three-way disagreements: 4. Every non-exact case, including cases with UNCERTAIN, was sent to the fresh adjudication run; adjudication count: 53.

## Binary agreement

UNCERTAIN was excluded pairwise from binary agreement. The fixed projection was BENIGN to NEGATIVE and every concrete attack taxonomy label to POSITIVE.

| Primary runs | Jointly eligible | Binary agreement | Cohen kappa |
|---|---:|---:|---:|
| 1 vs 2 | 165 | 0.915152 | 0.831461 |
| 1 vs 3 | 165 | 0.787879 | 0.567189 |
| 2 vs 3 | 167 | 0.790419 | 0.591173 |

Binary Fleiss kappa on jointly eligible cases: 0.666168 across 165 cases.

## Primary-run distributions

| Label | Run 1 | Run 2 | Run 3 |
|---|---:|---:|---:|
| BENIGN | 88 | 76 | 108 |
| RECON | 43 | 53 | 50 |
| SUSPICIOUS | 2 | 4 | 2 |
| EXPLOITATION | 5 | 6 | 1 |
| PRIVILEGE_ESCALATION | 5 | 4 | 2 |
| DATA_ACCESS | 11 | 12 | 5 |
| PERSISTENCE | 5 | 5 | 0 |
| OTHER_ATTACK | 6 | 7 | 0 |
| UNCERTAIN | 4 | 2 | 1 |

## Final reference summary

The frozen reference contains 165 resolved concrete labels and 4 UNCERTAIN labels. Binary evaluable cases are 165, with 80 NEGATIVE and 85 POSITIVE. Both preregistered acceptance gates pass: resolved concrete labels are at least 150, and binary-evaluable cases are at least 145.

The resulting reference type is `SINGLE_MODEL_FAMILY_AI_DERIVED_ADJUDICATED_REFERENCE`, not human ground truth or a gold standard. The final reference was frozen before any primary effectiveness analysis.
