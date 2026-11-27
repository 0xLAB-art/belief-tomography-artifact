# RAGIN V4 HF-2024 Reference-Free Results

## 1. Execution completeness

The frozen holdout contains 240 cases and the raw JSONL contains 720 records: 240 each for `RAGIN_BASELINE`, `RAGIN_V4_DETERMINISTIC`, and `RAGIN_V4_LOGISTIC`. Case IDs, source-group IDs, and input hashes align across all three arms. No experiment was rerun during analysis.

Verified hashes:

- Holdout: `ee47336121f45a50259ac54bce84ea59ebb2ecdb5cd0b6f507690a7f346d435e`
- Raw execution freeze: `1a634f471741d67f7d5c53e5454f0114ff91ff37d7a8b9cfe602f1c58e19fe59`
- Raw JSONL: `9ce230723661eac84c4b30fdd98970374a815b8fe8762fe180ba8bc1db687afd`

## 2. Actual components executed

Chrollo and Don were executed through the frozen `DeceptionGraph` runner path. The compact raw records do not retain per-record classifier payloads or full retrieval traces, so those details are only partially independently verifiable. The Evidence Quality Gate executed for both V4 arms: 480/480 V4 records were `VALID_EVIDENCE`. The baseline arm recorded `NOT_APPLICABLE_BASELINE`.

Both V4 policy selectors executed for 240 cases each. Hisoka executed for all 720 cases using the repository's deterministic template/fast-path; no external generation call occurred. The deterministic `FictionConsistencyVerifier` executed for all 720 records.

## 3. Gate and policy distributions

Gate states were `VALID_EVIDENCE=480` and `NOT_APPLICABLE_BASELINE=240`. Deterministic strategies were {'low_intensity_administration': 213, 'baseline': 27}. Logistic strategies were {'maximize_recon_surface': 240}.

Supporting evidence references were present for 240 deterministic and 240 logistic decisions, with all emitted references belonging to the recorded valid-document IDs. The baseline arm emitted no V4 evidence references.

## 4. Matched response comparison

Every arm pair produced identical response hashes for all 240 matched cases:

- Baseline vs deterministic: 240 equal, 0 different
- Baseline vs logistic: 240 equal, 0 different
- Deterministic vs logistic: 240 equal, 0 different

Selected strategies differed substantially: baseline/deterministic agreed in 27/240 cases, baseline/logistic in 0/240, and deterministic/logistic in 0/240. Verification and serve-path outcomes were identical in every pair.

Latency was descriptive only. Mean/median/p90/p95 milliseconds were: baseline 99.594/96.935/110.076/113.954, deterministic 100.692/98.756/110.582/117.568, and logistic 101.844/99.363/113.027/116.105.

## 5. Template fallback audit

The result is classification A: the frozen local template path ignored the selected V4 strategy when producing response bytes. `DeceptionGraph.plan_node` constructed a V4 strategy block and `generate_node` passed the policy decision through context. However, `AdaptiveDeceiver.generate_response` derives its response strategy from the Jev/Laya signal, not from V4 `policy_decision`; therefore `ResponseGenerator.generate(response_strategy=...)` received no V4 strategy. The response hashes confirm this: all matched responses were identical despite policy differences.

All 720 records were marked `TEMPLATE_FALLBACK_VERIFIED`. This is a provenance and system-behavior observation, not a quality judgment.

## 6. Verifier and safety results

The verifier passed 720/720 records using `FictionConsistencyVerifier` with deterministic checks. All approvals were automatic; no human HITL interrupt occurred. The compact freeze has no explicit commit-event or full retrieval-trace records, so commit-level violation counts and complete retrieval invocation traces are `NOT_VERIFIABLE` from the saved compact output. No policy-to-verifier bypass evidence was observed.

A verifier pass is not evidence of deception quality, security effectiveness, or attacker engagement.

## 7. Dataset limitations

The 240 selected source-IP groups contain 59 exact and normalized command-sequence families. Six families are repeated; 187/240 selected groups belong to repeated families, and the largest family contains 153 groups. `session_id` is an anonymized source-IP-group identifier, not a native SSH session identifier. Dependence and source clustering therefore limit independence claims.

## 8. Conclusion boundary

Established: execution completeness, recorded gate/policy behavior, exact matched response equality, deterministic template fallback, verifier outcomes, and safety-trace limitations.

Not established: policy effectiveness, Logistic or Deterministic superiority, strategy quality, deception quality, attacker engagement, security improvement, blinded-reference compatibility, or native-session generalization. No reference or locked-effectiveness freeze was created.

Classifications:

- `EXECUTION_COMPLETED`
- `REFERENCE_FREE_ANALYSIS_COMPLETED`
- `PRIMARY_POLICY_EFFECTIVENESS_NOT_EVALUATED`

Machine-readable analysis: `results/decision_fusion_v4/v4_hf2024_reference_free_execution_analysis_v1.json`
