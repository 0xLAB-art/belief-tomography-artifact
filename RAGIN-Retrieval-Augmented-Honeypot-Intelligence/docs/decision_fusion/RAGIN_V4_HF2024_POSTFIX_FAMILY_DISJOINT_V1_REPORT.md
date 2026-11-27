# RAGIN V4 HF-2024 Post-Fix Family-Disjoint Validation

Experiment: `HF2024_POSTFIX_FAMILY_DISJOINT_V1`  
Classification: `POSTFIX_EXECUTION_COMPLETED` / `POSTFIX_BEHAVIORAL_ANALYSIS_COMPLETED`  
Primary policy effectiveness: `NOT_EVALUATED`

## Scope and freeze

This was a same-dataset, retrospective, reference-free behavioral validation of the corrected V4 strategy-to-generator wiring. No reference judge, model download, external inference, paid API, AWS operation, network change, attacker-command execution, policy retraining, threshold tuning, or generator modification was used during execution.

The corrected implementation was frozen before execution. Git HEAD was `f0c4042c0eb2ee25854796b770ea440f0b5851b2`. The complete worktree diff hash recorded in the freeze was `cb757c9b7013de2c643435b192d254e8b0be7a43c99ff17283542833726c6d8c`. The code-version marker was `V4_GENERATOR_STRATEGY_WIRING_FIX_V1`.

The corrected source hashes were verified:

- `ragin/hisoka/deceiver.py`: `a56e78e3d1a8e89e8edec73c86d073e6e29d8725a2dda0689ace40e045bfc420`
- `ragin/hisoka/deception.py`: `a9eb0f46cdd54d1a691c692ff9f893f9fbff413e2b5ab23a666ab0d88ef1bbb8`
- Logistic policy artifact: `4056337ad6a41132a73a89fc0ef3b18cf41b10086bb0f25f7e6fc953bbd0a6a8`

The focused pre-execution suite passed 170/170 tests. The separately labeled smoke test passed baseline preservation, V4 policy delivery, template consumption, verifier acceptance, no verifier bypass, and no external generation call. Smoke records were excluded from the evaluation.

## New holdout

The pinned HF-2024 dataset contained 6,658 source sessions and 1,458 normalized ordered command-sequence families. Excluding all 240 prior source groups and their 59 represented normalized families left 1,399 eligible unique families across 1,489 sessions. Exactly 240 families and exactly one source-group record per family were selected by the frozen SHA256 rules.

- Unique case IDs: 240
- Unique source groups: 240
- Unique command families: 240
- Previous-family overlap: 0
- Synthetic/replay selection: excluded
- Selection: no semantic balancing or cherry-picking

The holdout is observational retrospective evidence from the same dataset, not independent prospective field data.

## Execution

All 720 records were sealed successfully:

- Baseline: 240/240
- Deterministic: 240/240
- Logistic: 240/240
- Total: 720/720

The repository pipeline was used with offline Don retrieval, the deterministic local Hisoka template runtime, deterministic verification, and automatic approval. The environment reported the existing FAISS/sentence-transformers absence and used local NumPy brute-force retrieval; no installation or network access occurred.

## Behavioral analysis

Gate states:

- Baseline: `NOT_APPLICABLE_BASELINE` 240
- Deterministic: `VALID_EVIDENCE` 239, `LOW_RELEVANCE` 1
- Logistic: `VALID_EVIDENCE` 239, `LOW_RELEVANCE` 1

Strategy distributions:

- Baseline: `baseline` 240
- Deterministic: `baseline` 120, `low_intensity_administration` 119, `maximize_recon_surface` 1
- Logistic: `baseline` 1, `maximize_recon_surface` 239

Strategy disagreement was 120/240 baseline-vs-deterministic, 239/240 baseline-vs-logistic, and 238/240 deterministic-vs-logistic.

Wiring traceability across 480 V4 records was incomplete by design and is reported rather than repaired:

- Strategy delivered to generator: 478/480
- Strategy consumed by template: 359/480
- Two V4 authorization fast paths consumed the strategy suffix without invoking `ResponseGenerator`.
- The remaining non-consumed V4 records selected `baseline`, whose existing behavior has no strategy-conditioned suffix.
- One baseline authorization fast path had `template_id=NOT_VERIFIABLE`.

Matched response hashes changed:

- Baseline vs deterministic: 120/240
- Baseline vs logistic: 239/240
- Deterministic vs logistic: 238/240

Template-ID changes were 1/240 for baseline-vs-deterministic, 1/240 for baseline-vs-logistic, and 0/240 for deterministic-vs-logistic. Therefore the corrected policy strategy changed served response bytes in this retrospective runtime; this is a behavioral observation, not an effectiveness or superiority result.

## Safety and observability

- Verifier: 720/720 passed; 0 failed; deterministic verifier false count 0.
- HITL: 0 human interrupts; 720 automatic/gateway approval records.
- Commit trace: `NOT_VERIFIABLE` for 720/720 compact records.
- External generation calls: false for all records.
- Attacker commands executed: false for all records.
- Recorded errors: none.
- Matched mean latency: baseline 136.134 ms, deterministic 143.699 ms, logistic 140.545 ms.
- Missing evidence bundle hashes: baseline-only 240 records, consistent with the baseline arm not producing V4 evidence bundles.

## Limitations

This is reference-free behavioral validation from the same retrospective dataset. It does not evaluate policy accuracy, strategy quality, deception quality, attacker engagement, security improvement, or superiority. The V4 gate was nearly all `VALID_EVIDENCE`, with one `LOW_RELEVANCE` case per V4 arm. The deterministic and logistic distributions are highly concentrated in a few strategies. Two V4 fast paths bypassed the generator boundary, and baseline-selected V4 fallbacks do not have strategy-conditioned template consumption; these are reported trace limitations. Commit events are not retained in the compact raw records. The interrupted first smoke attempt is preserved separately as an aborted procedural record and was not merged.

## Additive freeze artifacts

All artifacts are under [the postfix freeze directory](../../results/decision_fusion_v4/hf2024_postfix_family_disjoint_v1/):

- implementation/environment freeze: `implementation_environment_freeze.json`, SHA256 `d855f0d39f495b293c0dac54b5cd8ba52b9b66766b9de4beaefc31b484ab86b9`
- holdout freeze: `holdout_freeze.json`, SHA256 `73efbb94d9381dc9860a6e7003dcd7db2f3f21e76cde026f274638796d4176ae`
- protocol freeze: `protocol_freeze.json`, SHA256 `ecbf19ce527f95265266cdcaafedb127f04845375311a7cf98b275c77a657961`
- complete raw records: `raw_arm_outputs.jsonl`, SHA256 `33278567cead415667dd63f7789b8bbb1d8c0061797dc7466304ad5d92d741db`
- raw execution freeze: `raw_execution_freeze.json`, SHA256 `63729ec18f1d93b566df901f1cab428ce3b5a022a332d043dbd75e1e4de341c8`
- reference-free analysis: `reference_free_behavioral_analysis.json`, SHA256 `f5c43113d42584ff56ae695e2207d71c6070c63366b408f39a12df8bd696bb62`
- candidate-pool audit: `candidate_pool_audit.json`, SHA256 `eb1c7914220cd2b5997c171b6042edd6b7d170b2bbada45c0d167400f5b02fc9`
- synthetic smoke: `synthetic_smoke.json`, SHA256 `7948abb77b24f8f719cdcf3197c2a7069aab674056e00b51ede77c3743e46a66`
- SHA256 manifest: `sha256_manifest.json`
- aborted initial smoke attempt: `aborted_attempt_freeze.json`, SHA256 `908ccae199ca4be47a9744df189e82664be1d529a95c035e8bcc33120b48e51d`

Previous V4 and HF-2024 freezes remain preserved and were not rerun, relabeled, or overwritten.
