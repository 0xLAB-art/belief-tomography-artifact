# Pre-Reference Prediction Recovery Audit v1

## Verdict

`REAL_OUTPUTS_RECOVERED_MAPPING_NOT_IDENTIFIABLE`.

The historical broad pool is an exact-hash-verified, pre-reference 307-row artifact. All 120 frozen confirmatory case IDs occur exactly once in it, and their Chrollo/Laya fields are populated. A deterministic pure subset was recovered without model inference or value transformation.

## Provenance

The broad-pool SHA256 is recorded in the pre-reference v2 instrument preservation manifest. Its hash matches the current file. The recorded manifest chronology precedes the v3 annotation freeze, panel reference construction, adjudication, and final reference freeze. The original 120-case confirmatory artifact remains unchanged and remains the historical null skeleton.

## Selection independence

The frozen subset manifest records prediction-blind stratified selection, `model_predictions_consulted = false`, and selection based on observable evidence-quality strata. The named selection script is only a specification stub, so the executed selection is documented but not independently reproducible from that script alone; no evidence was found that model outputs conditioned selection.

## Recovered outputs

The recovered 120 cases contain non-null Chrollo class/confidence, Laya SIGNAL/answer/latency, and the historical disagreement flag. Descriptive summaries are therefore identifiable. They remain reference-free and do not measure correctness.

## Semantics and policy boundary

Chrollo's native output is the skill/persona ontology `novice`, `intermediate`, `expert`, `apt`; no pre-outcome mapping to the frozen benign/positive endpoint was found. Laya's typed attack/stage/severity answer has no frozen binary crosswalk. The `<0.65` gate is preregistered exploratory, but no complete final prediction policy was frozen for gate inactive, SIGNAL, NO_SIGNAL, disagreement, malformed output, or final selection.

No reference correctness metrics, McNemar test, paired bootstrap, or comparative performance claim was computed. No post-hoc endpoint mapping or combination policy was invented.

## Recommended treatment

Laya remains an optional advisory engineering component. Report integration, coverage, latency, and frozen descriptive behavior, but make no claim that Laya outperforms Chrollo.

## Preserved invariants

- Existing `locked_ai_reference_evaluation_freeze_v1.json` was not modified.
- No model was rerun.
- No reference label was modified.
- No prediction value was transformed.
- No post-hoc endpoint mapping or combination policy was created.
