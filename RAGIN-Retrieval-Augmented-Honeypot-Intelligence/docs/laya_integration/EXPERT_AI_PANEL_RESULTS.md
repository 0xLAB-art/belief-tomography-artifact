# Expert AI Panel Results

## Scope and source
The three completed annotation runs were ingested from the corrected authoritative root `/home/elaref/Documents/research/ragin_expert_panel_v1`. The earlier lookup under `results/laya_research/expert_ai_workspaces/` was a source-path resolution failure, not an annotation-integrity failure.

## Integrity
All three runs contain 120 packet cases and 120 unique annotations with matching ID sets, valid labels, nonblank notes, matching packet/output hashes, and valid access/blindness metadata. All are VALID. Three different AI model configurations were used; model identity is operator-attested.

## Label distributions
- expert_ai_01: {"BENIGN": 74, "DATA_ACCESS": 12, "EXPLOITATION": 8, "OTHER_ATTACK": 7, "PERSISTENCE": 1, "PRIVILEGE_ESCALATION": 1, "RECON": 17}
- expert_ai_02: {"BENIGN": 92, "DATA_ACCESS": 11, "EXPLOITATION": 3, "OTHER_ATTACK": 3, "PERSISTENCE": 1, "PRIVILEGE_ESCALATION": 1, "RECON": 1, "UNCERTAIN": 8}
- expert_ai_03: {"BENIGN": 91, "DATA_ACCESS": 11, "EXPLOITATION": 4, "OTHER_ATTACK": 9, "PERSISTENCE": 2, "PRIVILEGE_ESCALATION": 1, "RECON": 1, "UNCERTAIN": 1}

## Agreement
Pairwise multiclass statistics and transition tables are in `results/laya_research/expert_ai_panel_pairwise_multiclass.json`; Fleiss multiclass kappa is `0.600925956115`. Binary pairwise statistics are in `expert_ai_panel_pairwise_binary.json`; binary Fleiss kappa is `0.66122527367` over 112 fully eligible cases.

## Consensus structure
{"BINARY_2_OF_3": 5, "BINARY_3_OF_3": 3, "EXACT_2_OF_3": 21, "EXACT_3_OF_3": 88, "THREE_WAY_DISAGREEMENT": 2, "UNCERTAIN_HEAVY": 1}. AI-derived multiclass reference candidates: 88. AI-derived binary consensus candidates: 91. These are not ground truth or a gold standard.

## Disagreements
The dominant directed transition families are recorded in `expert_ai_panel_transition_analysis.json`. The disagreement map contains one row per case and no model identity.

## Adjudication
32 non-unanimous-exact cases are packaged in the blinded packet, CSV, instructions, and isolated workspace. Adjudication has not occurred.

## Freeze and limitations
The freeze artifact records source and derived hashes. Agreement does not establish correctness; model identity is operator-attested; no human ground truth exists; the AI-derived references remain reference-building/adjudication-stage; and no Chrollo/Laya predictions or confirmatory evaluation were accessed or run.

Scientific status: expert AI panel annotation is complete, but results are reference-building / adjudication-stage, not ground truth.
