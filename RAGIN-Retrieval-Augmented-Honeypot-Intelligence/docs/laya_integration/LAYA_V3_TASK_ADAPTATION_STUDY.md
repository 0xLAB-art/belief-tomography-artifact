# Laya V3.1 Task Adaptation Study

## Scope and scientific boundary

This is a synthetic task/contract adaptation study for the pinned Laya runtime. It is not the V3 pipeline, a real-world effectiveness study, or an accuracy evaluation. No exploratory 120 cases, primary 169 cases, prior labels, prior predictions, baseline/treatment outputs, or effectiveness artifacts were used. The synthetic oracle is a contract oracle created by scenario construction.

The checkpoint was held constant: `laya 0.4.2`, `english@55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851`, SHA256 `891102d372688fc2a094dac56a384bc537b87c63f21f9f3dac0be2b7cbc8d86c`. The runtime was CPU-only.

## Development

Development used 24 newly constructed synthetic cases. The cases covered recon, credential access, persistence, benign administration, exploitation, data access, compatible supporting documents, irrelevant high-score documents, weak or missing evidence, direct conflict, behavior/retrieval contradiction, incomplete behavior, and lower-score relevant evidence.

Three contract iterations were recorded before validation:

| iteration | strategy order | raw evidence-state agreement | caller required-abstain recall | inappropriate abstain |
|---|---|---:|---:|---:|
| v1_verbose | canonical | 16/24 | 24/24 | 17/24 |
| v2_reordered | reverse canonical | 12/24 | 24/24 | 17/24 |
| v3_semantic | canonical | 8/24 | 24/24 | 17/24 |

The selected candidate was v1 because it had the highest raw evidence-state agreement. This selection occurred before validation and did not use validation results. The selected candidate was then frozen; no further tuning was performed.

The exact candidate is recorded in [laya_v3_task_adaptation_candidate_freeze_v1.json](../../results/laya_decision_v3/laya_v3_task_adaptation_candidate_freeze_v1.json), SHA256 `c3fea3c979ed33b8831fcecee7e4ed8eea16bd9bf57bc23690071700c0feca9b`.

## Frozen task contract

The model answered three finite-choice questions over a deterministic JSON serialization:

1. `evidence_state`: `SUFFICIENT`, `INSUFFICIENT`, or `CONFLICTING`.
2. `strategy`: the seven bounded strategy labels.
3. `evidence_ref`: one supplied document ID or `NONE`.

The serialized input contained only `session.current_input`, the bounded behavior fields, Don analysis fields, and sorted retrieval documents containing `doc_id`, `title`, `content_excerpt`, `source`, and `retrieval_score`. No free-form retrieval prose or unsupported fields were added.

The caller enforced semantic authority. `INSUFFICIENT`, `CONFLICTING`, invalid references, `SUFFICIENT + NONE`, and malformed outputs became `ABSTAIN` with `baseline`. Only `SUFFICIENT` plus a valid supplied reference could become `SELECT`. Laya confidence was recorded as `UNCALIBRATED_DIAGNOSTIC_ONLY` and did not override these rules. The option order was frozen to the canonical order.

## Untouched synthetic validation

The validation set contains 30 new synthetic cases and was frozen before any validation call. It is recorded in [laya_v3_task_adaptation_validation_set_freeze_v1.json](../../results/laya_decision_v3/laya_v3_task_adaptation_validation_set_freeze_v1.json), SHA256 `1a5fc96cdd5e7cf90d3cf5d4765f84de1e125a5fc2d2aebe6aa542cc868ac596`.

There was one initial inference call per validation case. A preregistered six-case repeatability subset received three total calls per case, yielding 30 initial calls and 12 additional repeat calls. Repeated outputs were stable for all six subset cases.

## Validation results

The structural contract was satisfied:

- schema validity: 30/30 (100%);
- allow-list compliance: 30/30 (100%);
- evidence-reference validity: 30/30 (100%);
- malformed-output rate: 0/30 (0%).

The semantic contract was not satisfied:

- evidence-state contract alignment: 13/30 (43.33%);
- required-abstain recall: 6/10 (60%);
- inappropriate-abstain rate on sufficient cases: 12/20 (60%);
- strategy compatibility on sufficient cases: 3/20 (15%);
- evidence-reference compatibility on sufficient cases: 6/20 (30%).

The latency distribution was descriptive only: mean 3948.17 ms, median 3854.98 ms, p90 4744.24 ms, minimum 2329.0 ms, and maximum 5131.37 ms.

The complete aggregate result is recorded in [laya_v3_task_adaptation_validation_results_v1.json](../../results/laya_decision_v3/laya_v3_task_adaptation_validation_results_v1.json). These metrics are SYNTHETIC CONTRACT ALIGNMENT measurements. They are not real-world accuracy, utility, safety, or effectiveness claims.

## Preregistered gate assessment

| gate | threshold | observed | result |
|---|---:|---:|---|
| schema validity | 100% | 100% | PASS |
| allow-list compliance | 100% | 100% | PASS |
| evidence-reference validity | 100% | 100% | PASS |
| required-abstain recall | >=90% | 60% | FAIL |
| inappropriate-abstain rate on sufficient cases | <=10% | 60% | FAIL |
| evidence-state contract alignment | >=85% | 43.33% | FAIL |
| strategy compatibility on sufficient cases | >=80% | 15% | FAIL |
| evidence-reference compatibility | >=90% | 30% | FAIL |

The structural gates passed, but the semantic failures are major and affect the core evidence-grounded policy role. The final classification is therefore `TASK_ADAPTATION_FAILED`, not `TASK_ADAPTATION_PARTIALLY_VALID`. The current checkpoint should be retired from the V3 decision role; prompt-tuning should not continue indefinitely. A separately versioned model/task comparison or redesign study is required.

## DEVELOPMENT

synthetic cases: 24

iterations: 3; v1 selected and frozen before validation

selected contract: three finite-choice questions with deterministic evidence serialization, canonical option order, caller-side semantic abstention, and uncalibrated diagnostic confidence

## CANDIDATE FREEZE

path: `results/laya_decision_v3/laya_v3_task_adaptation_candidate_freeze_v1.json`

SHA256: `c3fea3c979ed33b8831fcecee7e4ed8eea16bd9bf57bc23690071700c0feca9b`

## VALIDATION

N: 30 initial cases; 42 total calls including 12 preregistered repeats

schema valid: 100% (30/30)

allow-list valid: 100% (30/30)

evidence refs valid: 100% (30/30)

evidence-state alignment: 43.33% (13/30)

required-abstain recall: 60% (6/10)

inappropriate-abstain rate: 60% (12/20)

strategy compatibility: 15% (3/20 sufficient cases)

reference compatibility: 30% (6/20 sufficient cases)

## LATENCY

mean: 3948.17 ms

median: 3854.98 ms

p90: 4744.24 ms

## SUCCESS GATES

schema: PASS

abstention: FAIL

evidence-state: FAIL

strategy: FAIL

references: FAIL

## FINAL CLASSIFICATION

TASK_ADAPTATION_FAILED

## NEXT STEP

full V3 prototype allowed: NO

new checkpoint required: YES

The current checkpoint is not suitable for the V3 policy role. Run a separately versioned model/task redesign or comparison study before any full POST_RETRIEVAL_POLICY_FUSION implementation. Any subsequent real evaluation must use a new untouched holdout.

LAYA V3 TASK ADAPTATION STUDY COMPLETE.
THE CURRENT CHECKPOINT WAS EVALUATED ON A FROZEN UNTOUCHED SYNTHETIC VALIDATION SET.
NO PRIOR RAGIN HOLDOUT OR EFFECTIVENESS RESULT WAS USED.
FULL V3 IMPLEMENTATION IS AUTHORIZED ONLY IF THE PREREGISTERED CONTRACT GATES PASS.
