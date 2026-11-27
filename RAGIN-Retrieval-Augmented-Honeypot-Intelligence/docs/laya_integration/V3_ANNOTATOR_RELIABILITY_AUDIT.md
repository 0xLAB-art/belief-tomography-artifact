# V3 Annotator Reliability Audit

## 1. Scope

This audit covers only three valid blinded AI-agent annotation runs over the frozen 120-case V3 set. It computes annotation agreement and descriptive agreement structure only.

## 2. V3 instrument status

The V3 instrument freeze is unchanged. The frozen case set contains 120 cases; packet hashes and case-ID hash were verified. No packet was modified.

## 3. Valid and invalid runs

Valid runs are `v3_agent_run_01`, `v3_agent_run_03`, and `v3_agent_run_04`. Run02 is invalid and quarantined for `PREDECLARED_BLINDNESS_BOUNDARY_VIOLATION`.

## 4. Raw metadata preservation and schema normalization

Raw metadata files were hashed and preserved. Original metadata remains unchanged. In the raw run04 metadata, `external_files_accessed: []` was normalized in a derived canonical record to Boolean `false` because the empty list contains zero accessed external files. This was schema normalization, not evidence alteration; semantic value did not change. No annotation was rerun and no labels were changed.

## 5. Procedural replacement of run02

Run04 replaced run02 for procedural reasons independent of label outcomes. Run02 is excluded from every statistic.

## 6. Label distributions

- `v3_agent_run_01`: BENIGN=90, RECON=1, SUSPICIOUS=19, EXPLOITATION=2, PRIVILEGE_ESCALATION=0, DATA_ACCESS=5, PERSISTENCE=1, OTHER_ATTACK=1, UNCERTAIN=1
- `v3_agent_run_03`: BENIGN=3, RECON=81, SUSPICIOUS=2, EXPLOITATION=8, PRIVILEGE_ESCALATION=5, DATA_ACCESS=10, PERSISTENCE=4, OTHER_ATTACK=0, UNCERTAIN=7
- `v3_agent_run_04`: BENIGN=49, RECON=42, SUSPICIOUS=2, EXPLOITATION=7, PRIVILEGE_ESCALATION=2, DATA_ACCESS=9, PERSISTENCE=2, OTHER_ATTACK=6, UNCERTAIN=1

## 7. Pairwise multiclass agreement

- `v3_agent_run_01__v3_agent_run_03`: exact=10/120, rate=0.083333, Cohen kappa=0.052677.
- `v3_agent_run_01__v3_agent_run_04`: exact=56/120, rate=0.466667, Cohen kappa=0.219671.
- `v3_agent_run_03__v3_agent_run_04`: exact=57/120, rate=0.475000, Cohen kappa=0.291870.

## 8. Pairwise binary agreement

- `v3_agent_run_01__v3_agent_run_03`: eligible=112/120, excluded_uncertain=8, agreement=29, rate=0.258929, Cohen kappa=0.016504.
- `v3_agent_run_01__v3_agent_run_04`: eligible=119/120, excluded_uncertain=1, agreement=78, rate=0.655462, Cohen kappa=0.368087.
- `v3_agent_run_03__v3_agent_run_04`: eligible=112/120, excluded_uncertain=8, agreement=67, rate=0.598214, Cohen kappa=0.070796.

## 9. Three-rater reliability

Multiclass Fleiss kappa is 0.077003 (observed=0.341667, expected=0.286744, N=120, exactly 3 raters). Binary Fleiss kappa is -0.022925 (observed=0.505952, expected=0.517025, eligible N=112, excluded N=8, exactly 3 raters).

## 10. Descriptive consensus structure

UNCERTAIN_HEAVY=1, EXACT_3_OF_3=8, BINARY_3_OF_3=21, MULTICLASS_2_OF_3=83, BINARY_2_OF_3=4, THREE_WAY_DISAGREEMENT=3; total=120. These are agreement categories, not truth labels.

## 11. Main disagreement surfaces

- `BENIGN <-> RECON`: 150 directed transitions.
- `DATA_ACCESS <-> SUSPICIOUS`: 15 directed transitions.
- `EXPLOITATION <-> SUSPICIOUS`: 10 directed transitions.
- `BENIGN <-> PRIVILEGE_ESCALATION`: 8 directed transitions.
- `RECON <-> SUSPICIOUS`: 6 directed transitions.
- `OTHER_ATTACK <-> SUSPICIOUS`: 6 directed transitions.
- `BENIGN <-> UNCERTAIN`: 5 directed transitions.
- `OTHER_ATTACK <-> RECON`: 5 directed transitions.
- `RECON <-> UNCERTAIN`: 5 directed transitions.
- `BENIGN <-> DATA_ACCESS`: 4 directed transitions.
- `BENIGN <-> EXPLOITATION`: 4 directed transitions.
- `BENIGN <-> PERSISTENCE`: 3 directed transitions.
- `SUSPICIOUS <-> UNCERTAIN`: 3 directed transitions.
- `PERSISTENCE <-> SUSPICIOUS`: 2 directed transitions.
- `PRIVILEGE_ESCALATION <-> SUSPICIOUS`: 2 directed transitions.

Top disagreement case IDs by number of disagreeing pairs:

`f2135da32462` (3/3 pairs), `f1aae1c198d1` (3/3 pairs), `cd05ba19d2bb` (3/3 pairs), `ad7b7844b156` (3/3 pairs), `a3b5b234a552` (3/3 pairs), `8b333b619d4a` (3/3 pairs), `7e590931dfa8` (3/3 pairs), `598ff01ec9e2` (3/3 pairs), `40b66d4845e6` (3/3 pairs), `284c37e21b6f` (3/3 pairs), `19595b9defea` (3/3 pairs), `0cefcd8a03b7` (3/3 pairs), `00dbac0794ca` (3/3 pairs), `fd65c582c594` (2/3 pairs), `fd10535f4e89` (2/3 pairs)

## 12. Limitations

All valid V3 raters are AI-agent runs; none is a human reference standard. Agreement is not correctness. No adjudication was performed, and descriptive categories must not be interpreted as ground truth.

## 13. What the annotations support

They support reproducible descriptions of label distributions, pairwise agreement, three-rater reliability, and disagreement surfaces among the three valid AI-agent runs.

## 14. What they do NOT support

They do not support a human ground-truth claim, model correctness, model comparison, or confirmatory evaluation. No predictions were inspected and no ground truth was created.

## 15. Freeze boundary

The annotation reliability artifacts are frozen before any model evaluation. No predictions were inspected. No annotation was rerun. No labels were changed. No confirmatory analysis was run.

## EXPLORATORY INSTRUMENT-EFFECT COMPARISON

The aggregate V2 audit reports multiclass Fleiss kappa 0.563442 and binary Fleiss kappa 0.609636, with broad pairwise exact-agreement range 0.6083 to 0.8583 and binary-agreement range 0.6410 to 0.9224. V3 reports multiclass Fleiss kappa 0.077003, binary Fleiss kappa -0.022925, exact-agreement range 0.0833 to 0.4750, and binary-agreement range 0.2589 to 0.6555. This comparison is descriptive and does not establish causality.

The V2 aggregate values were read only from `docs/laya_integration/AI_ANNOTATOR_AGREEMENT_AUDIT_V2.md`.

V3 BLINDED AI-ANNOTATOR RELIABILITY ESTABLISHED.
NO HUMAN GROUND TRUTH EXISTS.
NO CHROLLO-vs-LAYA CONFIRMATORY ANALYSIS HAS BEEN RUN.
