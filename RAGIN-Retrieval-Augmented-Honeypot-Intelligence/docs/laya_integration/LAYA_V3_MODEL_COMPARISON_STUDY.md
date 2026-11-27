# Laya V3 Model Comparison Study

## Scope and scientific boundary

This is a frozen synthetic contract comparison between two checkpoints of the pinned Laya runtime. It is the separately versioned model/task comparison required by [laya_v3_task_adaptation_final_decision_v1.json](../../results/laya_decision_v3/laya_v3_task_adaptation_final_decision_v1.json) as the follow-up to the failed task-adaptation study (`required_followup`: "separately versioned model/task comparison or redesign study"). It is not the V3 pipeline, a real-world effectiveness study, or an accuracy evaluation. The comparison set is new synthetic material; no exploratory 120 cases, primary 169 cases, VAL-01..30 task-adaptation validation cases, prior labels, prior predictions, or prior model outputs were reused (the task-adaptation validation results file was referenced as context only). The synthetic oracle is a contract oracle created by scenario construction.

The frozen scope statement reads: "Synthetic contract comparison only; the oracles are not real-world ground truth and no claim is made about real-runtime policy quality. The bundle-subfolder route for typed-decisions is recorded; weight equivalence with the standalone convaiinnovations/laya-typed-decisions repository is not claimed."

The runtime was held constant: `laya 0.4.2`, `torch 2.14.0+cpu`, `transformers 5.17.0`, Python 3.12.3, CPU-only, Hugging Face offline. Only the checkpoint varied.

## Study version identity

| artifact | SHA256 |
|---|---|
| [protocol freeze](../../results/laya_decision_v3/laya_v3_model_comparison_protocol_freeze_v1.json) | `56e8e68a365fd87bb379963c0ea087869f9233bdf6d3646c93e054149af412e6` |
| [comparison set freeze](../../results/laya_decision_v3/laya_v3_model_comparison_validation_set_freeze_v1.json) | `58c8f056f87097039a62de53bf2b39cc2073b425abbffa2b248976a435cee10f` |
| [contract freeze](../../results/laya_decision_v3/laya_v3_task_adaptation_candidate_freeze_v1.json) | `c3fea3c979ed33b8831fcecee7e4ed8eea16bd9bf57bc23690071700c0feca9b` |
| frozen runner (`scripts/laya_v3_model_comparison_v1.py`) | `d872f849f7b019645208aa8a538ae8a89e90c1c899d32a66a2a3750adde11816` |
| [results](../../results/laya_decision_v3/laya_v3_model_comparison_results_v1.json) | `6069075f00638463456b0c4bf0f3642a2eb6c980469ed7325d7b84a9eaaaaa16` |
| [final decision](../../results/laya_decision_v3/laya_v3_model_comparison_final_decision_v1.json) | `0cb07352587ee1453e538ab53323c9d9f70dfc59112227ce2a5d2c55c071a36d` |

## Checkpoint pair

- Control (`english`): `convaiinnovations/laya@55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851`, `model.safetensors`, SHA256 `891102d372688fc2a094dac56a384bc537b87c63f21f9f3dac0be2b7cbc8d86c`, 842,609,210 bytes.
- Candidate (`typed-decisions`): same repository and revision, `model.safetensors`, SHA256 `4fa56de72383a9d3efa9cfa78955733c81b9fc8067a587ca4beb82c78107a24e`, 842,609,220 bytes.

Both digests were passed to the runtime Router for on-load verification.

## Frozen protocol

The research question was: "Under the frozen task-adaptation contract v1, does the typed-decisions checkpoint satisfy the frozen behavioral gates at a level comparable to the english checkpoint when both are run under one identical protocol on one new synthetic comparison set?"

The task-adaptation contract v1 was reused unchanged: three finite-choice questions (`evidence_state`, `strategy`, `evidence_ref`) over a deterministic serialization with canonical option order. Caller enforcement ran mechanically after each predict: `INSUFFICIENT` or `CONFLICTING` became ABSTAIN with `baseline`; `SUFFICIENT` with `NONE`, an invalid reference, or malformed answers became ABSTAIN; only `SUFFICIENT` with a valid supplied-document reference could become SELECT. Confidence was `UNCALIBRATED_DIAGNOSTIC_ONLY` and never overrode these rules.

Protocol integrity: the runner verified the SHA256 of the contract freeze, the comparison set, and the protocol itself before any model call, and both checkpoint digests were verified on load; any mismatch aborts. Arm order was `english` then `typed-decisions`, with router unload and garbage collection between arms.

Boundaries: no commit without explicit user authorization; no post-hoc threshold, case, or definition changes (any change requires new versioned files and a fresh full run); single run of the frozen study with results published whether passing or failing; no fusion or integration implementation in this study; no real-runtime holdout or deployment claim.

## Untouched synthetic comparison set

The set contains 30 new synthetic cases (20 sufficient, 10 required-abstain), authored for this comparison and frozen before any model-comparison call. Oracles were written before inference and are synthetic contract oracles, not real-world truth labels.

Execution: 30 primary calls per arm plus a preregistered six-case repeatability subset (CMP-01, CMP-03, CMP-05, CMP-09, CMP-14, CMP-18) at three total runs per case, yielding 42 calls per arm and 84 calls total. Metrics are computed over primary calls only; repeat calls are used only for repeatability and latency descriptives. Single run, window 2026-10-16T04:39:26Z to 04:47:54Z. No call was retried for behavioral reasons and no call was dropped.

## Comparison results

The structural contract was satisfied by both arms:

- schema validity: 30/30 (100%);
- allow-list compliance: 30/30 (100%);
- evidence-reference validity: 30/30 (100%).

The semantic contract was not satisfied by either arm:

- candidate (`typed-decisions`): evidence-state alignment 19/30 (63.33%); required-abstain recall 7/10 (70%); inappropriate-abstain rate on sufficient cases 7/20 (35%); strategy compatibility 11/20 (55%); reference compatibility 11/20 (55%);
- control (`english`): alignment 12/30 (40%); required-abstain recall 8/10 (80%); inappropriate-abstain rate 15/20 (75%); strategy compatibility 1/20 (5%); reference compatibility 5/20 (25%).

Repeatability was stable for all six subset cases in both arms (enforced outputs identical across all three runs).

Case-level misses (independently recomputed): the candidate missed required abstention on CMP-18, CMP-19, and CMP-29, and inappropriately abstained on CMP-04, CMP-05, CMP-06, CMP-07, CMP-09, CMP-20, and CMP-25. The control missed required abstention on CMP-19 and CMP-29, and inappropriately abstained on fifteen cases (CMP-02, CMP-04, CMP-05, CMP-06, CMP-07, CMP-08, CMP-09, CMP-10, CMP-13, CMP-21, CMP-22, CMP-23, CMP-24, CMP-25, CMP-26).

A case-level note: CMP-18 is a candidate-only miss where the raw evidence-state was `SUFFICIENT` against a `CONFLICTING` oracle, so the frozen caller rules (which operate on the raw model state) enforced SELECT. This is the frozen design's expected semantics, not a harness defect; CMP-19 and CMP-29 are the same miss family shared by both arms.

Latency was descriptive only (42 calls per arm). Candidate: mean 5395.80 ms, median 5028.53 ms, p90 7055.58 ms, minimum 2756.94 ms, maximum 10455.81 ms. Control: mean 6698.14 ms, median 4992.16 ms, p90 9590.62 ms, minimum 2573.14 ms, maximum 55029.51 ms (the control maximum includes first-call weight-load overhead). Stored p90 values use linear interpolation; a nearest-rank recomputation yields slightly higher values and remains descriptive-only.

## Preregistered gate assessment

| gate | threshold | typed-decisions | english | result |
|:---|:---:|---:|---:|---|
| G1 schema validity | == 100% | 100% | 100% | PASS / PASS |
| G2 allow-list compliance | == 100% | 100% | 100% | PASS / PASS |
| G3 evidence-reference validity | == 100% | 100% | 100% | PASS / PASS |
| G4 required-abstain recall | >= 90% | 70% | 80% | FAIL / FAIL |
| G5 inappropriate-abstain rate on sufficient cases | <= 10% | 35% | 75% | FAIL / FAIL |
| G6 evidence-state contract alignment | >= 85% | 63.33% | 40% | FAIL / FAIL |
| G7 strategy compatibility on sufficient cases | >= 80% | 55% | 5% | FAIL / FAIL |
| G8 evidence-reference compatibility on sufficient cases | >= 90% | 55% | 25% | FAIL / FAIL |

The candidate arm failed five of the eight frozen gates (G4, G5, G6, G7, G8); the control arm failed the same five gates. Classification is driven by the candidate arm, and the final classification is `COMPARISON_FAIL_REDESIGN_REQUIRED`, not `CANDIDATE_PASSES_FROZEN_CONTRACT`. The candidate improved four of the five failed semantic metrics relative to the control but remained below every semantic threshold; required-abstain recall was lower than the control's.

These metrics are SYNTHETIC CONTRACT ALIGNMENT measurements. They are not real-world accuracy, utility, safety, or effectiveness claims.

## Redesign-only conclusion

The final decision's next step (verbatim): "Candidate failed at least one frozen gate. Redesign-only conclusion: no fusion; publish the failing gates with this same study version."

This document is that publication, bound to the study version identity listed above. No fusion or integration implementation was performed, and none is authorized by this study; a redesign under new versioned files is required before any further decision-layer work, and any subsequent evaluation must use a fresh full run.

## Independent verification

- An independent recomputation reproduced every reported quantity from the frozen artifacts (per-call flags and enforcement, both arms' metrics, gates, failed-gate lists, repeatability, latency summaries, and the classification); all checks passed with zero failures.
- One independent read-only gate review (per governance, exactly one reviewer) audited the frozen artifacts, the recomputation, and the digest chain; verdict APPROVE with zero blocking issues. All six study digests were re-verified byte-identical on 2026-10-16; no frozen artifact was modified after the run.

## STUDY

laya_v3_model_comparison_v1 (frozen protocol)

## CHECKPOINT PAIR

control english sha256 `891102d372688fc2a094dac56a384bc537b87c63f21f9f3dac0be2b7cbc8d86c` (842,609,210 bytes)

candidate typed-decisions sha256 `4fa56de72383a9d3efa9cfa78955733c81b9fc8067a587ca4beb82c78107a24e` (842,609,220 bytes)

repository: `convaiinnovations/laya@55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851`

## EXECUTION

single frozen run; 30 primary calls per arm plus 12 repeat calls (six-case subset at three runs) = 42 calls per arm, 84 total

window: 2026-10-16T04:39:26Z to 04:47:54Z

repeatability: stable for all six subset cases in both arms

## RESULTS

schema/allow-list/reference validity: 100% both arms

typed-decisions: alignment 63.33%; required-abstain recall 70%; inappropriate abstain 35%; strategy compatibility 55%; reference compatibility 55%

english: alignment 40%; required-abstain recall 80%; inappropriate abstain 75%; strategy compatibility 5%; reference compatibility 25%

## SUCCESS GATES

structural (G1-G3): PASS both arms

required-abstain recall (G4): FAIL both arms

inappropriate abstain (G5): FAIL both arms

evidence-state alignment (G6): FAIL both arms

strategy compatibility (G7): FAIL both arms

reference compatibility (G8): FAIL both arms

## FINAL CLASSIFICATION

COMPARISON_FAIL_REDESIGN_REQUIRED

## NEXT STEP

fusion: NO

redesign required: YES

Candidate failed at least one frozen gate. Redesign-only conclusion: no fusion; publish the failing gates with this same study version.

LAYA V3 MODEL COMPARISON STUDY COMPLETE.

BOTH CHECKPOINTS WERE EVALUATED ON A FROZEN UNTOUCHED SYNTHETIC COMPARISON SET.

NO PRIOR RAGIN HOLDOUT OR EFFECTIVENESS RESULT WAS USED.

FULL POST_RETRIEVAL_POLICY_FUSION IMPLEMENTATION REMAINS UNAUTHORIZED; A REDESIGN STUDY IS REQUIRED.
