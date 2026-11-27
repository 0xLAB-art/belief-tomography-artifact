# Don V2 + Substantive V4 Final Retrospective Evaluation

Experiment: `HF2024_DON_V2_SUBSTANTIVE_FINAL_V1`

This report describes a same-source, family-disjoint retrospective validation. It does not evaluate policy correctness, strategy superiority, deception effectiveness, or real-world attacker engagement.

## Protocol and holdout

The pinned HF-2024 corpus was filtered by source-group identity and normalized whole-sequence command-family identity against all three earlier HF-2024 holdouts. The remaining pool contained 919 unique eligible command families. The first 240 family keys under `SHA256(JSON([EXPERIMENT_ID, "family", family]))` were selected. One source-group record per selected family was chosen by the minimum `SHA256(JSON([EXPERIMENT_ID, "record", source_group_id]))`. No balancing, labels, policy outputs, retrieval outcomes, or expected responses were used.

The frozen holdout contains 240 unique case IDs, 240 unique source groups, 240 unique command families, and zero prior-family overlap. Source-group records are not asserted to be native SSH sessions. Prior commands were supplied as inert retrospective context; no captured command was executed.

## Execution

The actual path was `server_v2 -> Harness -> Chrollo -> Don V2 -> Evidence Gate -> V4 policy -> substantive Hisoka generator -> verifier/HITL -> accepted-only fictional-state commit`. All arms used `DON_COMMAND_AWARE_V2`, offline mode, provider-disabled mode, and no network or AWS operations.

| Arm | Records |
|---|---:|
| RAGIN_BASELINE | 240 |
| RAGIN_V4_SUBSTANTIVE_DETERMINISTIC | 240 |
| RAGIN_V4_SUBSTANTIVE_LOGISTIC | 240 |
| Total | 720 |

The sealed raw JSONL was checked for 720 records and 720 unique case-arm pairs before analysis. The raw freeze SHA256 is `2e674299280764e07b153a6dd8c693d714c154a1b28ee0b56700ac1fca3f6ede`.

## Evidence and policy observations

Each arm had 214 `VALID_EVIDENCE` and 26 `NO_EVIDENCE` cases, for 642 valid-gate records across the 720 arm records. The three arms were matched on the same input and Don configuration.

Don V2 produced eight unique evidence IDs and eight unique evidence-reference sets over the raw records, with 18 unique score sets. All records contained a query, context projection, top-k trace, and gate reason field. These are retrieval and runtime observations, not evidence of retrieval accuracy.

| Arm | Strategy distribution |
|---|---|
| Baseline | baseline 240 |
| Deterministic | baseline 240 |
| Logistic | baseline 26; low_intensity_administration 213; maximize_recon_surface 1 |

The deterministic arm selected baseline for all 240 cases. This is an observation about the frozen policy inputs and rules, not a correctness judgment. Logistic decisions varied only in 214 valid-gate cases, predominantly selecting `low_intensity_administration`.

## Behavioral comparisons

Response hashes changed in 0/240 baseline-versus-deterministic pairs, 1/240 baseline-versus-logistic pairs, and 1/240 deterministic-versus-logistic pairs. Applying the preregistered removal of only the prompt line and decorative strategy markers produced the same counts: 0/240, 1/240, and 1/240. Thus the one observed logistic difference was not explained away as a decorative suffix by the locked comparison.

Fictional-state-after hashes showed the same pairwise counts: 0/240, 1/240, and 1/240. Only one accepted fictional commit was directly observable in the exported generator metadata; 719 records had `NOT_VERIFIABLE` commit metadata in this raw export. No rejected commit was observed. Consequently, accepted-only commit integrity is verified for the one observable accepted event, but complete commit observability is not established for all records.

## Safety and operations

- Verifier: 720/720 passed; 0 verifier failures and 0 recorded safety violations.
- HITL: 720/720 automatic approvals; 0 human reviews.
- Captured commands executed: 0.
- External generation calls: false in all raw records.
- Evidence queries, context projections, top-k results, relevance/provenance fields, and gate reason codes were recorded for all 720 records.
- Missing fields were retained as `NOT_VERIFIABLE`; no missing commit or generator metadata was imputed.
- Mean latency was 161.311 ms baseline, 164.650 ms deterministic, and 170.468 ms logistic.

The broad-suite result was 1717 passed, 22 failed, and 10 errors. The failures/errors were pre-existing and outside this execution path: absent optional `mem0`, missing gateway and vector-store fixtures, unrelated Laya label-directory residue, and a verifier-red-team fixture lacking a `should_pass` cohort. The Don V2, policy, substantive generator, verifier, and runtime-path tests used for this study passed. These broad-suite issues were not repaired or used to alter the study.

## Interpretation and limitations

Verified: Don V2 was active in the matched runtime; command-aware retrieval traces were present; the evidence gate and policy stages ran; the substantive runtime was invoked; mandatory verifier/HITL stages passed; and no captured commands were executed.

Observed: deterministic policy output collapsed to baseline on this cohort. Logistic policy output varied, but downstream substantive response/state differences were observed in only 1/240 matched pairs. The result does not establish policy quality, retrieval accuracy, strategy superiority, or attacker engagement.

The corpus is retrospective and drawn from the same HF-2024 source as earlier studies, despite family-disjoint selection. It has no independent reference labels for evidence quality or policy correctness. Automatic HITL approval and incomplete commit metadata limit conclusions about serving and commit behavior. The raw export also does not support claims about native SSH session boundaries.

## Reproducibility and hashes

Frozen artifacts:

- `results/decision_fusion_v4/don_v2_substantive_final_v1/holdout_freeze.json` SHA256 `c2f7ee9a33dca7a48ab29558388bed4b9ee95027db225c73e43144b61a9fffd5`
- `results/decision_fusion_v4/don_v2_substantive_final_v1/protocol_freeze.json` SHA256 `becf06ed6b1c1f15beee94b7448d7a145304dda07b9288740f020de1b58b2e90`
- `results/decision_fusion_v4/don_v2_substantive_final_v1/implementation_environment_freeze.json` SHA256 `933b70bd0b4ceea902962cd1bdf143987b9693d6ad43c709869e49cdf0b32591`
- `results/decision_fusion_v4/don_v2_substantive_final_v1/raw_execution_records.jsonl` SHA256 `2e674299280764e07b153a6dd8c693d714c154a1b28ee0b56700ac1fca3f6ede`
- `results/decision_fusion_v4/don_v2_substantive_final_v1/raw_execution_freeze.json` SHA256 `227baf315d16ad08cdac1baed73fd1a8cd3338f7676132d30f699017b875a0c5`
- `results/decision_fusion_v4/don_v2_substantive_final_v1/locked_behavioral_analysis.json` SHA256 `6c52aa58a25008f38a7c5f69d9e716f7abffb9fe1b4310f9a631c282a809c0be`
- `results/decision_fusion_v4/don_v2_substantive_final_v1/sha256_manifest.json` SHA256 `bebfe2d7672d441f06a267e083bcc9023a1a7289c203bbeb3f40019bc920fb2e`

Implementation inputs include Don V2 freeze `703013c412e8ba1e1e7f000c8a46e1baf958485aea6fb78e38329ee64a7e36b9`, substantive integration freeze `5a20a15da37830ef41d1d21da706a211e8247fdaa7723cdd3f606be9a5054fe5`, generator `3c1e0c9f85510adc17758c4f4aded547c57fca8c7aa69fea209790315fdbdae2`, Don V2 source `2c349665b18b7ddd14f86ba33bc95e0b58c6503a0f2a634b8380b571c494da25`, and command-aware corpus `d1a2f015eae91c91702fa9ccc5cdbdb8a074d7cb05e62d93208a30919cb242f4`.

Classification: `DON_V2_SUBSTANTIVE_EVALUATION_COMPLETED`.

No policy superiority, effectiveness, accuracy, or real-world attacker-engagement claim is made.
