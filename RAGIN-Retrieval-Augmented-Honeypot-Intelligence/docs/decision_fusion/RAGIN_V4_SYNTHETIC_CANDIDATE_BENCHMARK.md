# RAGIN V4.1 Synthetic Candidate Benchmark

## Scope and amendment

This artifact records the pre-execution V4.1 amendment and the isolated synthetic benchmark. It does not implement or modify the RAGIN serving path. V2/V3 artifacts, the exploratory 120, the primary 169, prior labels, prior predictions, and effectiveness outputs were not used.

The original V4 protocol proposed 72 development cases. Before any corpus, candidate output, or validation output existed, that design was amended to 192 development cases while retaining 96 validation cases. The amendment is recorded in [synthetic_benchmark_protocol_amendment_v1a.json](../../results/decision_fusion_v4/synthetic_benchmark_protocol_amendment_v1a.json), SHA256 `58c26221da29329fe7902bc03c9a1fe88d34217d2d07ff36438904ca144d35fe`.

The amendment targets 12 development cases and 6 validation cases per each of the 16 frozen strata. The validation corpus was generated only after candidate freeze and uses separate IDs, template prefixes, and validation-specific input variants.

## Isolated implementation

The benchmark-only implementation is in [benchmark.py](../../ragin/decision_fusion_v4/benchmark.py). It is not imported by the production pipeline. The gate accepts only the frozen `ragin.don.evidence_bundle.v4` structure and emits exactly the six frozen gate states.

The precedence is fail-closed: malformed or retrieval failure first; document integrity checks for provenance, sanitization, duplicates, and unresolved conflict; then no evidence; then query-coverage failure; finally valid evidence. Numeric `score` and `hybrid_score` fields are retained as metadata and are never used as a universal quality threshold.

Contract tests were added in [test_decision_fusion_v4.py](../../tests/unit/test_decision_fusion_v4.py). They cover malformed and missing fields, retrieval failure/degradation, no evidence, incomplete coverage, invalid or unknown provenance, unsanitized or unknown sanitization, duplicate IDs, inconsistent fingerprints, unresolved conflict, valid multi-document evidence, low-score relevant evidence, high-score irrelevant evidence, and the caller rule that no policy engine is invoked unless the gate is valid. Result: 4 tests passed.

## CORPORA

development: 192 (`V4D-0001` through `V4D-0192`)

validation: 96 (`V4V-0001` through `V4V-0096`)

disjoint: YES

The development freeze is [v4_development_corpus_freeze_v1.json](../../results/decision_fusion_v4/v4_development_corpus_freeze_v1.json), SHA256 `14fdc256e615ca2191bca5d5ec45240b6683d668e65ae1be4f349f317a5f8004`. The validation freeze is [v4_validation_corpus_freeze_v1.json](../../results/decision_fusion_v4/v4_validation_corpus_freeze_v1.json), SHA256 `ab78be8b82f6a5254336d5307e47cb4fb8b4340a498fd95f895c25f956a4f581`.

Every case contains a predeclared `SYNTHETIC_CONTRACT_ORACLE` with expected gate state, allowed strategies, supporting evidence IDs, forbidden strategies, and required baseline behavior. These are scenario-construction oracles, not real-world ground truth.

## EVIDENCE GATE

The development and validation gate results are in [v4_evidence_gate_development_results_v1.json](../../results/decision_fusion_v4/v4_evidence_gate_development_results_v1.json) and [v4_locked_validation_results_v1.json](../../results/decision_fusion_v4/v4_locked_validation_results_v1.json).

alignment:

- development: 192/192, 100%; Wilson 95% CI [98.04%, 100%]
- validation: 96/96, 100%; Wilson 95% CI [96.15%, 100%]

fail-safe recall:

- development: 84/84, 100%; Wilson 95% CI [95.63%, 100%]
- validation: 42/42, 100%; Wilson 95% CI [91.62%, 100%]

invalid pass-through:

- development: 0/84, 0%; Wilson 95% CI [0%, 4.37%]
- validation: 0/42, 0%; Wilson 95% CI [0%, 8.38%]

classification:

`ADVANCE_TO_REAL_PROTOTYPE` as an isolated deterministic contract gate. This is not authorization to wire the full serving path.

## DETERMINISTIC POLICY

The first-class baseline is `deterministic_v1`, using a finite ordered rule table over Chrollo structured features, Don classification/severity/tactics/TTPs, and vetted evidence references. Baseline fallback is the default.

strategy compatibility:

- development: 108/108, 100%; Wilson 95% CI [96.57%, 100%]
- validation: 54/54, 100%; Wilson 95% CI [93.36%, 100%]

catastrophic rate:

- development: 0/108, 0%; Wilson 95% CI [0%, 3.43%]
- validation: 0/54, 0%; Wilson 95% CI [0%, 6.64%]

reference compatibility:

- development: 108/108, 100%
- validation: 54/54, 100%

latency:

- validation mean 0.029 ms, median 0.027 ms, p90 0.034 ms

classification:

`ADVANCE_TO_REAL_PROTOTYPE` for the deterministic policy contract, subject to a future implementation review and a new untouched real holdout.

## LEARNED POLICY

selected family:

`multinomial_logistic_regression`, selected during development under the predeclared deterministic tie-break. Gradient-boosted trees were also evaluated during development but were not advanced.

strategy compatibility:

- development: 108/108, 100%; Wilson 95% CI [96.57%, 100%]
- validation: 54/54, 100%; Wilson 95% CI [93.36%, 100%]

catastrophic rate:

- development: 0/108, 0%; Wilson 95% CI [0%, 3.43%]
- validation: 0/54, 0%; Wilson 95% CI [0%, 6.64%]

reference compatibility:

- development: 108/108, 100%
- validation: 54/54, 100%

latency:

- validation mean 0.308 ms, median 0.282 ms, p90 0.365 ms

classification:

`ADVANCE_TO_REAL_PROTOTYPE` as the one model-based synthetic candidate, conditional on a future prototype implementation and new real holdout. Its trained artifact and exact feature/configuration freeze are recorded in [v4_candidate_freeze_v1.json](../../results/decision_fusion_v4/v4_candidate_freeze_v1.json), SHA256 `91679fac702d0ca8cd1dbecf3475133a5cf36f387d880c9f658fbabce78df73c`.

The shallow MLP was not advanced: `SHALLOW_MLP_NOT_ADVANCED_DUE_TO_SMALL_SYNTHETIC_TRAINING_REGIME`.

## LOCAL INSTRUCTION POLICY

model:

No candidate selected.

available: NO

strategy compatibility: NOT RUN

catastrophic rate: NOT RUN

reference compatibility: NOT RUN

latency: NOT RUN

classification:

`LOCAL_INSTRUCTION_CANDIDATE_UNAVAILABLE`.

The inventory found an Ollama executable and live endpoint, but only `:cloud` remote aliases were listed; no suitable downloaded local weights were found. The configured OpenAI-compatible local endpoint on port 8000 refused connection. No model was downloaded, no paid API was used, and no AWS resource was changed. See [local_instruction_model_inventory_v1.json](../../results/decision_fusion_v4/local_instruction_model_inventory_v1.json).

## NONINFERIORITY

learned vs deterministic:

PASS on the preregistered point-estimate rule: logistic strategy compatibility was not more than 5 percentage points lower and catastrophic rate was not more than 2 percentage points higher. Both were identical on the locked validation cases.

instruction vs deterministic:

NOT ESTABLISHED; no suitable local instruction model was available.

The confidence intervals are reported descriptively. Threshold decisions use the preregistered point estimates and do not claim that the small synthetic sample establishes real-world superiority.

## ADVANCEMENT

deterministic:

`ADVANCE_TO_REAL_PROTOTYPE`

model-based candidate:

`ADVANCE_TO_REAL_PROTOTYPE`: logistic regression only. Gradient-boosted trees and shallow MLP are not advanced; no instruction candidate is available.

The locked validation results are [v4_locked_validation_results_v1.json](../../results/decision_fusion_v4/v4_locked_validation_results_v1.json), SHA256 `eceb4f97a4a31368774e62400cf402f4f94dd81b077e999538195aac42ea829d`. The candidate decision record is [v4_candidate_selection_decision_v1.json](../../results/decision_fusion_v4/v4_candidate_selection_decision_v1.json), SHA256 `3cce28102c289442a1230e7ca6b65e2a8f4a575246272c6b62239272f9b37b56`.

Even though the synthetic gates pass, the full V4 serving path remains unimplemented. The next step, if separately authorized, is prototype implementation followed by a new untouched real holdout.

## LAYA

decision role:

`RETIRED`

reused:

`NO`

## SCIENTIFIC BOUNDARY

old 120 used:

`NO`

old 169 used:

`NO`

real effectiveness claim:

`NO`

full V4 serving implemented:

`NO`

RAGIN V4 SYNTHETIC DECISION-ENGINE BENCHMARK COMPLETE.
THE EVIDENCE GATE AND POLICY ENGINES WERE EVALUATED SEPARATELY.
AT MOST ONE MODEL-BASED POLICY WAS ADVANCED ALONGSIDE THE DETERMINISTIC BASELINE.
NO PRIOR RAGIN HOLDOUT OR EFFECTIVENESS RESULT WAS REUSED.
A NEW UNTOUCHED REAL HOLDOUT IS REQUIRED BEFORE ANY V4 EFFECTIVENESS CLAIM.
