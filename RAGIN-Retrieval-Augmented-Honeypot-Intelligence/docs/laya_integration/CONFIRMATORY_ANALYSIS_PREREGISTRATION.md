# Confirmatory Analysis Preregistration

Status: locked before human labels are collected. This document defines
analysis only; it does not contain human labels or case-level model output.

## Reference eligibility

The primary binary comparison is confirmatory only when at least 100 of 120
cases have a resolved human reference and at least 90 cases remain
evaluable after the locked binary projection. The model outputs must have
been frozen before reference creation, and no threshold or decision rule
may change after labels. Below 100 resolved cases, binary comparison is
exploratory. Multiclass results are descriptive for resolved cases and are
exploratory as a model comparison below 90 resolved multiclass references.

`UNCERTAIN` is unresolved/excluded from primary binary evaluation until
adjudication. `UNRESOLVED` has no forced label. Every exclusion is counted.

## Locked projection

`BENIGN` maps to `NEGATIVE`. `RECON`, `SUSPICIOUS`, `EXPLOITATION`,
`PRIVILEGE_ESCALATION`, `DATA_ACCESS`, `PERSISTENCE`, and `OTHER_ATTACK`
map to `POSITIVE`. `UNCERTAIN` is unresolved/excluded until adjudication.

## Endpoints

Primary binary metric: balanced accuracy.

Secondary binary metrics: accuracy, macro-F1, precision,
recall/sensitivity, specificity, FPR, FNR, and confusion matrix.

Multiclass metrics where applicable: macro-F1, per-class precision,
per-class recall, and confusion matrix. Report all `UNCERTAIN` and
`UNRESOLVED` exclusions explicitly.

## Paired comparison

Compare Chrollo and Laya on the same human-reference-labeled case IDs with
McNemar. Let `C` be Chrollo wrong/Laya correct and `H` be Chrollo
correct/Laya wrong. Report `C`, `H`, `C+H`, exact two-sided p-value when
the discordant count is small, and the absolute paired accuracy
difference. Non-significance is not equivalence.

## Bootstrap

Use paired bootstrap with 10,000 replicates. Resample the same case IDs
jointly for the human reference and both model results. Report 95%
percentile confidence intervals for balanced accuracy, accuracy, macro-F1,
sensitivity, specificity, and paired metric differences. Cluster bootstrap
is a sensitivity analysis only if verified session groups are available;
none may be invented.

## Gated policy

Preserve the existing invocation gate: Chrollo confidence < 0.65. Do not
optimize it on human labels. Unless independently justified with
development data, gated-policy results are labeled `PREREGISTERED
EXPLORATORY`, not primary confirmatory evidence.

## Non-execution rule

No endpoint, paired test, bootstrap, threshold tuning, model execution, or
model/reference join is run during this preregistration handoff.
