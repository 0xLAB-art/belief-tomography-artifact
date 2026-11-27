# Chrollo vs Laya Locked AI-Reference Evaluation v1

## Status

`ANALYSIS_NOT_IDENTIFIABLE`.

This is a locked evaluation against the frozen `AI_DERIVED_ADJUDICATED_REFERENCE`. The authoritative 120-case confirmatory prediction artifact has a valid pre-reference SHA256 and exact case-ID alignment, but every Chrollo and Laya model-output field is null. The broader 307-case pool was not substituted, no model was rerun, no label was changed, and no endpoint mapping was invented.

## A. Directly measured

- Reference: 120 total cases; 114 resolved/evaluable; 6 `UNCERTAIN`; 0 `UNRESOLVED`.
- Resolved binary distribution: 92 `NEGATIVE`, 22 `POSITIVE`.
- Reference type: `AI_DERIVED_ADJUDICATED_REFERENCE`; `human_ground_truth = false`.
- Prediction provenance: pre-reference hash and chronology verified for `results/laya_research/confirmatory_frozen_predictions.jsonl`.
- Prediction/reference alignment: exact 120-case ID match, no duplicates, no missing IDs, no unexpected IDs.
- Prediction content: 120/120 null Chrollo outputs, confidences, Laya statuses, Laya answers, and latencies.

## B. Statistical comparison support

None. There is no valid mapped Chrollo prediction, no valid mapped Laya `SIGNAL`, and therefore no shared prediction subset. Exact McNemar and paired bootstrap are not statistically identifiable from this artifact.

## C. What this does not support

It does not support Chrollo performance metrics, conditional Laya performance, a Laya correction/harm estimate, an exact p-value, a paired delta, an end-to-end gated-policy metric, or any claim of Laya advantage. It does not establish human ground truth, gold-standard truth, equivalence, or open-world security performance.

## D. Abstention and missingness

Missing `laya_status` is reported as missing, not as `NO_SIGNAL` and not as `NEGATIVE`. Consequently observed `SIGNAL = 0`, observed `NO_SIGNAL = 0`, missing status = 114 on the eligible subset, and coverage is not identifiable.

## E. Gate findings

The strict gate `Chrollo confidence < 0.65` remains `PREREGISTERED_EXPLORATORY`. No confidence values are present, so gate-active and gate-inactive counts and rates are not identifiable. A routing threshold is not a final combination rule; the pre-existing artifacts explicitly do not freeze one.

## F. Latency

No frozen Laya latency values are recorded in the authoritative artifact. Latency summaries are therefore not identifiable; cold-start versus warm-start behavior is not inferred.

## G. Reference-source sensitivity

The requested strata are reported in `reference_source_sensitivity_v1.json`: exact-3/3 primary-evaluable N = 88, blinded-AI-adjudication primary-evaluable N = 26 (32 source cases including 6 `UNCERTAIN`), and combined primary-evaluable N = 114. All model metrics remain not identifiable because model outputs are absent.

## H. Limitations

- The reference is AI-derived, not human ground truth.
- Three AI models plus one AI adjudicator created the reference.
- The resolved set is class-imbalanced (92 negative, 22 positive); raw accuracy is secondary and balanced accuracy would be primary if predictions existed.
- Six cases were excluded as `UNCERTAIN`.
- Laya signal coverage cannot be estimated from missing statuses.
- The `<0.65` gate is preregistered exploratory absent stronger independent justification.
- Absence of a pre-frozen combination rule prevents post-hoc end-to-end policy claims.
- Any future bootstrap independence would be case-level unless a defensible cluster structure is explicitly available.
- The study does not establish open-world security performance.
- The authoritative prediction artifact is a frozen skeleton rather than populated model predictions; the 307-case broad pool was not used.

## Scientific classification

`ANALYSIS_NOT_IDENTIFIABLE`: the fixed reference is available and integrity-verified, but the authoritative confirmatory prediction artifact contains no evaluable model outputs or pre-registered binary mappings.

## Freeze invariants

- `predictions_rerun = false`
- `reference_modified = false`
- `threshold_changed = false`
- `post_hoc_combination_rule_created = false`
- `reference_type = AI_DERIVED_ADJUDICATED_REFERENCE`
- `human_ground_truth = false`
