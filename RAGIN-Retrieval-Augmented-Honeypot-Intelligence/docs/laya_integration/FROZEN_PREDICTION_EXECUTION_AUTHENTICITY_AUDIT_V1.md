# Frozen Prediction Execution-Authenticity Audit V1

Date: 2026-10-13. Scope: provenance only. No model was rerun, no reference label was opened or joined, no prediction value was modified, no correctness metric was computed, and the manuscript was not edited.

## 1. Why the audit was triggered

The recovered 120-case subset showed a constant Chrollo `novice`/`0.5` pair, constant Laya `SIGNAL`/`noul`/severity-1/`recon` answers, and approximately 0.0001-0.0002 second latencies. Those are forensic indicators, not by themselves proof of fabricated output. The audit was triggered to trace the generator and distinguish model-backed execution from fixture, default, fallback, or unverified provenance.

## 2. Frozen artifact provenance

The three required pre-existing hashes matched exactly:

- `results/laya_research/frozen_predictions.jsonl`: `ca9f3c2c113da8e76b94627a1c2ebedcfc2261a4f1812667a6092d4ad785c106`.
- `results/laya_research/confirmatory_predictions_recovered_from_broad_pool_v1.jsonl`: `fa7f655705bc91f5f9a00b5851d4f54c08047a075576ba63b99e1c2373990bb6`.
- `results/laya_research/pre_reference_prediction_recovery_freeze_v1.json`: `db24992dc7ff5d99abd23800e9b607a70d7e313dbc66f442e6072d17b0827680`.

The prior recovery freeze was left unchanged. The recovered subset remains a deterministic selection artifact; this audit did not regenerate it.

## 3. 307-case output fingerprint

The broad pool contains 307 unique case IDs. All 307 rows have `chrollo_class=novice`, `chrollo_confidence=0.5`, `laya_status=SIGNAL`, `attack.noul=0.5`, `severity.score=1`, `stage.choice=recon`, and `disagreement_flag=true`. There is one complete Laya answer object and one advisory object. Including latency, there are two complete output tuples because 19 rows record 0.0001 seconds and 288 record 0.0002 seconds. Excluding case ID and latency, there is one substantive output tuple. The same degeneracy therefore extends beyond the recovered 120 cases to all 307 cases. This is descriptive only; no correctness interpretation was performed.

## 4. Chrollo execution path

The named runner's `run_chrollo_prediction` at `scripts/laya_frozen_runner.py:31-43` is explicitly TODO-marked and returns a literal `{"class": "novice", "confidence": 0.5}`. It does not import `ragin.chrollo.classifier`, construct a `SessionLog`, extract features, load a Random Forest, call `classify`, or record a model identity. The actual classifier at `ragin/chrollo/classifier.py:192-216` requires a loaded model and computes features and probabilities; the shown adapter exception path at `ragin/cycle/adapters.py:131-140` returns `novice` with confidence `0.0`, not the observed `0.5`. Thus the current named runner's source-level path is a hard-coded stub/default path. Because the runner is untracked and historically unbound to the artifact, the conservative historical classification is `INFERENCE_PROVENANCE_UNVERIFIED`.

## 5. Laya execution path

The named runner's `run_laya_prediction` at `scripts/laya_frozen_runner.py:45-68` constructs the entire typed answer object literally. It does not call `LayaAssessmentAdapter`, `LayaRuntime`, `Router`, a checkpoint loader, or a provider wrapper. The real local path exists separately: `ragin/decision/laya_runtime.py:130-237` initializes a revision-pinned Router and calls `Router.predict` at lines 174-185; `ragin/decision/optional.py:46-113` maps provider output and converts failures to `NO_SIGNAL`. No historical generator record connects that real path to `frozen_predictions.jsonl`. The source-level named-runner path is therefore a stub, while the historical artifact classification remains `INFERENCE_PROVENANCE_UNVERIFIED`.

## 6. Literal/default/fallback search

The exact observed literals are present in the named runner: `novice`/`0.5` at lines 39-42, `SIGNAL` and the typed Laya object at lines 53-65, `noul` at line 56, `recon` at line 57, severity `1` at line 60, and the advisory literal at lines 83-86. The runner has `TODO: replace with the actual ... call` comments at lines 38 and 50. The source search also found fixture-contract tests, the real runtime schema, and the Chrollo enum/fallback, but none is the source of the observed complete output tuple. The `0.0001` literal is the deliberate sleep at line 52; no exact `0.0002` source literal was found, and the 0.0002 values arise from rounded elapsed time. Non-null output is not verified real model inference.

## 7. Latency timing semantics

The timer starts at `scripts/laya_frozen_runner.py:51`, then sleeps for 0.0001 seconds and constructs the hard-coded object, and ends at line 66 with four-decimal rounding. It excludes checkpoint loading, tokenization, Router execution, model forward inference, and adapter parsing. The correct classification is `FIXTURE_EXECUTION_LATENCY`. It is not safe to call the recorded values model-inference latency.

## 8. Historical generator version

The current repository HEAD is `f0c4042c0eb2ee25854796b770ea440f0b5851b2`, committed 2026-10-10, but no association with the artifact is established. The runner and broad artifact are untracked, `git log --follow` has no history for either, and no generator hash or checkpoint manifest is recorded. Filesystem times show the runner mtime before the broad artifact mtime, but this is chronology evidence only and not a cryptographic binding. The exact historical generator version therefore cannot be established.

## 9. Comparison with separate real-inference evidence

Existing separate evidence documents a real local Laya path: `docs/laya_integration/REAL_MODEL_INFERENCE_RESULTS.md:3-16` records Laya 0.4.2, a checkpoint blob hash, revision `55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851`, CPU execution, and raw records in `results/laya_research/real_inference_cpu_pilot.jsonl`. The documented real path has route/load/infer and warm timings in seconds, and the raw records contain varied typed answers. `results/laya_research/paired_comparison.json:17-31` also records provider `laya`, `SIGNAL`, `laya_execution_proven=true`, and millisecond-scale latencies. This supports a separate real integration, but differences alone do not classify the frozen artifact; the missing historical generator binding is the decisive limitation.

## 10. Authenticity classification

- Chrollo: `INFERENCE_PROVENANCE_UNVERIFIED`. The current named runner's Chrollo path is a verified hard-coded stub, but historical source identity is not bound to the freeze.
- Laya: `INFERENCE_PROVENANCE_UNVERIFIED`. The current named runner's Laya path is a verified hard-coded typed stub; separate real Laya artifacts are not proof of this freeze's generator.
- Complete artifact: `INFERENCE_PROVENANCE_UNVERIFIED`.

These classifications do not claim that the bytes are fabricated. They state that model-backed execution is not historically verifiable, while the inspected current named runner provides strong source-level evidence of a stub path.

## 11. Superseded interpretation

`results/laya_research/pre_reference_prediction_recovery_interpretation_amendment_v1.json` supersedes the word `REAL` in the prior interpretation for authenticity purposes only. The prior recovery freeze remains unchanged. The amendment records `REAL_OUTPUTS_RECOVERED_MAPPING_NOT_IDENTIFIABLE` as the previous classification and `INFERENCE_PROVENANCE_UNVERIFIED` as the new conservative classification.

## 12. Manuscript-safe claims

The manuscript may state that a separate real Laya integration path exists if it cites that path's own checkpoint, revision, runtime, and raw-run evidence. It may describe the frozen file as a hash-verified, reference-free artifact with non-null typed fields and may describe this audit's finding that the named runner is a placeholder/stub. It may not use the frozen file for verified model-behavior, model coverage, or latency claims. The policy is recorded in `results/laya_research/laya_manuscript_evidence_policy_v1.json`.

## 13. Claims that must not appear

Do not report the frozen file as model performance, 100% SIGNAL as real Laya coverage, 0.0001-0.0002 seconds as model latency, the frozen Laya answer distribution as real inference behavior, or novice/0.5 as measured trained-Chrollo behavior. Do not report 100% activation of a 0.65 confidence gate as a substantive Chrollo finding. Do not claim Laya outperforms Chrollo or provides a statistically significant correction benefit.

## 14. Final Laya disposition

`OPTIONAL_ADVISORY_PROVENANCE_UNVERIFIED`. Laya remains outside the main paper's effectiveness claims on this frozen artifact. Separate real-integration evidence may be discussed only as a separately identified optional advisory engineering path. No endpoint mapping, combination policy, threshold tuning, or model rerun was performed.

## Explicit boundary

Non-null output != verified real model inference.
