# Expert-AI Adjudicated Reference v1

## Scope and status

This document records the frozen `AI_DERIVED_ADJUDICATED_REFERENCE` for 120 cases in the RAGIN Laya integration workflow. The reference originates entirely from AI annotators. It is an expert-AI consensus reference and is not human ground truth, a gold standard, or independently verified truth.

Three distinct primary model configurations produced the panel annotations. The 88 cases with `EXACT_3_OF_3` agreement are retained with the exact panel taxonomy label under `EXACT_3_OF_3_PRIMARY_PANEL`. The remaining 32 cases were sent to one fourth AI configuration for blinded adjudication. That adjudication resolved 26 cases and left six cases `UNCERTAIN`.

Agreement among the three primary configurations and the fourth configuration's blinded adjudication do not establish objective truth. The six `UNCERTAIN` cases remain explicitly uncertain and are excluded from primary model-performance evaluation. No Chrollo or Laya prediction has been read in this workflow.

## Frozen counts

- Total cases: 120
- Exact 3/3 primary-panel cases: 88
- Blinded AI adjudication cases: 32
- Adjudicated concrete resolved cases: 26
- `UNCERTAIN`: 6
- `UNRESOLVED`: 0
- Primary metric eligible: 114

The primary-evaluable reference therefore contains 114 resolved cases. The binary projection maps `BENIGN` to `NEGATIVE`, all other resolved attack taxonomy labels to `POSITIVE`, and both `UNCERTAIN` and `UNRESOLVED` to `EXCLUDED`.

## Integrity and readiness

The adjudicator run is valid, with repository access, network access, external-file access, and blindness violation all recorded as false. The repository packet and adjudicator workspace packet have different raw serialization hashes but identical canonical case content, including the allowed labels, case-ID set, evidence, neutral context, and all RATER_A/RATER_B/RATER_C labels and notes. This is classified as `DELIVERY_PACKET_SERIALIZATION_DIFFERENCE`; it does not affect adjudication validity.

The reference is technically ready for locked model evaluation against this AI-derived reference. This readiness does not upgrade the reference to human ground truth. Confirmatory analysis has not been run, thresholds have not been changed after reference creation, and model predictions remain unread.
