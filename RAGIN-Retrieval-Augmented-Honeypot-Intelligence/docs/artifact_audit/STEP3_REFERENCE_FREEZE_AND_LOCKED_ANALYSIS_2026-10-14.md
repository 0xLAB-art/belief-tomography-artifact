# Step 3 Reference Freeze and Locked Analysis Audit (2026-10-14)

## Decision

`REFERENCE_FROZEN_AI_DERIVED` and `LOCKED_DESCRIPTIVE_ANALYSIS_COMPLETE`. Step 3's reference gate is satisfied under the AI-derived branch of the plan: a single fixed-model, blinded evidence-support reference covering all 120 cases and 947 candidates is frozen with a hash manifest, and the locked evaluation of the already-frozen 120-case arms ran only after that freeze. The reference is explicitly not human ground truth and not independent consensus; all resulting metrics are descriptive for this already-used cohort.

This document supersedes the pending status recorded in `docs/artifact_audit/STEP3_EVIDENCE_REFERENCE_GATE_2026-10-14.md`, which correctly described the blank reviewer packet before any annotation existed.

## Reference construction

- Protocol: `results/evidence_judge_real_data_ablation_v1/ai_reference_v2_2/CODEX_REFERENCE_PROTOCOL_V2_2.md` (frozen before any V2.2 annotation call).
- Route: one fixed reviewer `C1 = gpt-5.6-luna` via `codex exec --ephemeral --json --output-schema`, run from `/tmp`, blinded batch over stdin.
- Earlier routes and their failures are preserved, not reused: `ai_reference_v1` (provider failures), `ai_reference_v2` (format pilot, quarantined), `ai_reference_v2_1` (12/12 calls returned no usable annotation; its all-UNKNOWN output is an execution-failure record, not a reference).
- Input freeze: `ai_reference_v2_2/input_freeze_v2_2.json` — 6 batches x 20 cases, 120 cases, 947 candidates, prompt/protocol/schema/executor hashes locked; two executor amendments recorded in `executor_amendment_v2_2*.json` (print-only defect after batch artifacts were durably written; no change to inputs, prompt, model, or validation).
- Run: `run_manifest_v2_2.json` — 6 scheduled, 6 recorded, 6 schema-valid, 3 fully valid calls; 21 field-level validation errors across 3 batches; affected fields normalized to `UNKNOWN`, never repaired or guessed.
- Reference freeze: `reference_freeze_v2_2.json` (SHA256 `85dfaf83972fa6131b51996f052c43a09a7eddb1f8e4949a8b3fa910281187f8`) plus `reference_freeze_manifest_v2_2.json`.

## Verification performed

- Reference file SHA256 matches `reference_freeze_manifest_v2_2.json` (`reference_sha256`): pass.
- Reference status/type: `AI_DERIVED_REFERENCE_FROZEN` / `SINGLE_FIXED_MODEL_AI_DERIVED_REVIEW`, `human_ground_truth=false`, `independent_consensus_claim=false`: pass.
- Coverage: 120 unique cases, 947 candidate reviews, 120 bundle reviews; no missing or misaligned case IDs against the arms or the paired comparison: pass.
- Blindness: every frozen batch payload contains only `case_id`, `observed_command`, `available_context`, `behavioral_claim`, `retrieved_candidates` (candidates only `doc_id`, `source`, `title`, `content`, `source_version`, `provenance_hash`); zero payload-key violations; a case-insensitive scan of all `ai_reference_v2_2/runs/**` for `judge|gate_state|arm_a|arm_b` returned no matches: pass.
- Packet fidelity: all 120 frozen batch cases are field-identical to `blinded_reference_packet.json` (0 differences across command/context/claim/candidates); packet SHA256 `975f24fca75b0deb8d930252294ddf729eff850d715f87dc8bcac0706c4aacb5` matches the frozen manifest: pass.
- Citation validity: all 914 non-`UNKNOWN` candidate reviews carry a `source` URL identical to the frozen candidate and 1-based paragraph indexes inside the cited document (blank-line paragraph definition used by the validator); 0 missing citations, 0 out-of-range indexes, 0 sources mismatched: pass.
- Hash gating of outcomes: the locked evaluator refuses to run unless `matched_arm_results.json` (`d67449c247741824c56d11548e39aca23e7ddaa9e578ce84706e7a7c84d0a572`) and `case_level_comparison.json` (`853d4295030ec04f22beee8c6342e71ccba35c586e8a3ec2f51555fcadc524f9`) match frozen values; both matched at execution time: pass.
- Execution usage (from preserved `turn.completed` events): 579,301 input tokens and 44,838 output tokens (8,584 reasoning) across the six calls, all through the authenticated local Codex route.

## Locked analysis outputs

- Preliminary: `results/evidence_judge_real_data_ablation_v1/ai_reference_v2_2/locked_evaluation_v2_2.json`.
- Final (adds case-cluster bootstrap intervals on every rate and provenance fields): `locked_evaluation_addendum_v2_2_01.json`, SHA256 `2f400db4839ff7d560333e409a274f3f9761517cb8bbca7b05c9aa4140ca8c94`, `analysis_script_sha256` `40faa78569addc95d156a2e6b05580fdcd0513783604792de6b3b6877ae379c8`, `supersedes_preliminary_analysis_sha256` `33a962cd72e9682d2a0c5faadf7a634b5b41b07c53cfbe6881a2ad1ff0c78d27`. The evaluator writes to a new additive filename and refuses to overwrite an existing output.
- Reference candidate labels: 50 `DIRECT_SUPPORT`, 773 `IRRELEVANT`, 91 `PARTIAL`, 33 `UNKNOWN` (914 evaluable).
- Reference bundle labels: 47 `SUFFICIENT`, 70 `INSUFFICIENT`, 3 `UNKNOWN` (117 evaluable).
- Candidate metrics (case-cluster bootstrap, 10,000 replicates, seed 20261014):
  - Direct-support recall: 50/50 = 1.000 (CI 1.000–1.000).
  - Direct-support precision: 50/690 = 0.072 (CI 0.053–0.096).
  - Non-direct specificity: 224/864 = 0.259 (CI 0.206–0.313).
  - Binary accuracy: 274/914 = 0.300 (CI 0.241–0.357).
  - Unsupported-admission rate over non-direct evaluable: 640/864 = 0.741 (CI 0.687–0.794); admissions by reference label: 549 `IRRELEVANT`, 91 `PARTIAL`.
  - False-rejection rate over direct support: 0/50 = 0.000 (CI 0.000–0.000).
  - Crosswalk exact agreement: 61/914 = 0.067 (CI 0.048–0.087).
- Bundle: exact agreement 48/117 = 0.410 (CI 0.325–0.496); binary accuracy identical; confusion `NOT_SUFFICIENT|NOT_SUFFICIENT=1`, `NOT_SUFFICIENT|SUFFICIENT=69`, `SUFFICIENT|SUFFICIENT=47`.
- Paired arm descriptives: gate-state pairs `VALID_EVIDENCE|VALID_EVIDENCE=118`, `NO_EVIDENCE|NO_EVIDENCE=2`; retained candidate sets equal in 120/120 cases (523 retained per arm).

## Step 3 decision answers

1. **Does the deterministic judge detect genuine unsupported evidence?** Only weakly under this reference. It never rejects evidence the reference marks as direct support (recall 1.000), but it admits 74.1% of non-supporting candidates as `SUPPORTED`, including 549/773 reference-`IRRELEVANT` and 91/91 reference-`PARTIAL` candidates; specificity is 0.259. On this cohort the judge behaves as a permissive filter, not a detector of unsupported evidence.
2. **Does it merely repeat the gate?** At the gate level on this cohort, yes in effect: arm A and arm B produce identical gate states in all 120 cases and identical retained candidate sets (523 each). Equal gate outcomes alone establish neither accuracy nor equivalence — the reference comparison supplies the accuracy view (low specificity), and the zero-variance paired contrast provides no evidence of a gate-level effect either way.
3. **Which failure categories remain?** (a) Topical-but-unsupported admissions concentrated in `IRRELEVANT` candidates; (b) `PARTIAL` evidence promoted to full support with no partial-credit path in the Judge output; (c) bundle over-sufficiency — the system calls 116/117 evaluable bundles `SUFFICIENT` where the reference calls 70 insufficient (69 disagreements); (d) 33 candidate and 3 bundle `UNKNOWN`s produced by 21 field-level validation errors in three batches, retained as unknown rather than repaired; (e) no `CONTRADICTORY` label exists in either the Judge output or this reference, so contradiction handling remains unevaluated.

## Limits carried into Steps 4–8

- Single fixed AI reviewer (`gpt-5.6-luna`); correlated systematic error is possible; no inter-rater statistic exists or is claimed.
- The coordinator had seen aggregate descriptive summaries before annotation; the reviewer and every frozen payload exclude them and all Judge/Gate/arm outputs.
- All 120 cases are retrospective and come from one HF-2024 source family; case-cluster intervals condition on that family and do not estimate between-family uncertainty.
- These metrics are descriptive evaluation of an already-used cohort. They cannot be used for post hoc model selection presented as confirmatory performance, and this cohort cannot serve as a fresh holdout.

## Reproduction

```
python scripts/evidence_support_codex_reference_v2_2.py prepare   # already frozen; refuses to re-freeze
python scripts/locked_evidence_support_evaluation_v2_2.py         # refuses to overwrite an existing output
```
