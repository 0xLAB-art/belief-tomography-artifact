# Step 3 Completion Checklist (2026-10-14)

Step 3 is complete. This checklist binds every requirement of the Step 3 action, outputs, and gate in `docs/PAPER_REMAINING_STEPS_2026-10-14.md` to a verified artifact.

## Action requirements

| Requirement | Status | Evidence |
|---|---|---|
| Review candidate support and bundle sufficiency from the blinded 120-case packet, independently of judge/gate/policy outputs | Done | Frozen payloads contain only case/command/context/claim/candidate fields (0 key violations); no `judge`/`gate_state`/`arm_*` string in any run artifact; batch content field-identical to `blinded_reference_packet.json` (0 diffs) |
| Prefer two independent human reviewers; if only AI review is feasible, define a separate AI-derived reference with fixed identities, disclosure of dependence, restricted claims | Done (AI branch) | Human return directories empty (verified); `CODEX_REFERENCE_PROTOCOL_V2_2.md` frozen before calls; fixed reviewer `C1 = gpt-5.6-luna` via Codex CLI 0.162.1 strict output schema; `human_ground_truth=false`, `independent_consensus_claim=false` in the freeze |
| Record disagreements and adjudication; preserve UNKNOWN cases | Done under single-reviewer protocol | No adjudicator exists for one reviewer (disclosed in protocol); all 33 candidate and 3 bundle UNKNOWNs preserved and attributed to a cause in `field_level_error_report_v2_2_02.json`; no label repaired or guessed |
| Complete reviewer files with document citations | Done | 120/120 cases and 947/947 candidates in `reference_freeze_v2_2.json`; all 914 non-UNKNOWN candidate reviews carry source URL identical to the frozen candidate and 1-based paragraph indexes in range (0 bad, 0 missing) |

## Output requirements

| Output | Artifact |
|---|---|
| Reference protocol and annotation freeze | `results/evidence_judge_real_data_ablation_v1/ai_reference_v2_2/CODEX_REFERENCE_PROTOCOL_V2_2.md`, `input_freeze_v2_2.json` (120 cases / 947 candidates / 6 batches, prompt+protocol+schema+executor hashes locked, 2 executor amendments chained) |
| Complete reviewer files | `reference_freeze_v2_2.json` (SHA256 `85dfaf83972fa6131b51996f052c43a09a7eddb1f8e4949a8b3fa910281187f8`) + `reference_freeze_manifest_v2_2.json` + raw run provenance under `runs/C1/batch_01..06/` (request hash, stdout event stream, stderr, final message, normalized reviews) |
| Agreement/disagreement and adjudication records | Not applicable to a single reviewer (protocol section "Aggregation and reporting"); validation/normalization record: `run_manifest_v2_2.json` (6/6 schema-valid, 3 fully valid, 21 field errors) and `field_level_error_report_v2_2_02.json` (per-cause UNKNOWN attribution) |
| Final reference freeze | `reference_freeze_v2_2.json` + `reference_freeze_manifest_v2_2.json` (reference hash matches manifest; status `AI_DERIVED_REFERENCE_FROZEN`) |
| Locked analysis of the existing 120-case arms | `locked_evaluation_v2_2.json` (preliminary) and `locked_evaluation_addendum_v2_2_01.json` (final; SHA256 `2f400db4839ff7d560333e409a274f3f9761517cb8bbca7b05c9aa4140ca8c94`, case-cluster bootstrap on every rate); evaluator: `scripts/locked_evidence_support_evaluation_v2_2.py` (additive output, refuses overwrite) |

## Gate requirements

| Gate condition | Verification |
|---|---|
| Labels demonstrably blind to system outputs | Payload-key audit (0 violations), case-insensitive scan of all `runs/**` for `judge|gate_state|arm_a|arm_b` (0 matches), protocol exclusion list, packet fidelity 0 diffs |
| Complete under the protocol | 120/120 cases, 947/947 candidates, 120/120 bundles; every UNKNOWN attributed (`field_validation_error`: 21, `model_explicit_unknown`: 12 candidates, 3 bundles; 0 unattributed); reference exactly matches normalization (947 candidate + 120 bundle exact matches, 0 diffs) |
| Model/system labels cannot serve as the reference | Judge/Gate/arm outputs never entered any payload; the reference labels are AI-derived model labels only, disclosed as such and never called human ground truth |
| Case/source-family clustering where the sampling design supports it | Case-cluster bootstrap (10,000 reps, seed 20261014) on all rates; single HF-2024 source family recorded as `inference_limit` — between-family uncertainty is not estimable and is not claimed |
| Not used for confirmatory model selection on the same cases | Recorded in protocol, locked evaluation (`status: LOCKED_DESCRIPTIVE_ANALYSIS`), both audits, and the plan ledger |

## Decision answers (locked analysis)

Recorded in `docs/artifact_audit/STEP3_REFERENCE_FREEZE_AND_LOCKED_ANALYSIS_2026-10-14.md`: judge behaves as a permissive filter (recall 1.000, specificity 0.259, unsupported-admission rate 0.741); gate/retention identical across arms in 120/120 cases (zero-variance contrast, neither accuracy nor equivalence implied); remaining failures are topical IRRELEVANT admissions, PARTIAL promotion, bundle over-sufficiency (69/117 disagreements), 33+3 attributed UNKNOWNs, and unevaluated contradiction handling.

## Superseded artifacts in this step

- `docs/artifact_audit/STEP3_EVIDENCE_REFERENCE_GATE_2026-10-14.md` — pre-annotation pending audit, superseded by the freeze/analysis audit.
- `ai_reference_v1` / `ai_reference_v2` / `ai_reference_v2_2` — V1 provider failures, V2 format-pilot quarantine, and V2.1 all-UNKNOWN execution-failure record; none used as reference labels.
- `ai_reference_v2_2/locked_evaluation_v2_2.json` — preliminary analysis, superseded by the addendum.
- `ai_reference_v2_2/field_level_error_report_v2_2_01.json` — first report build had a cause-classification bug that left one coverage-incomplete candidate mislabeled `unattributed_structural_unknown`; superseded by `_02`, which attributes it to `field_validation_error` (the batch_03 coverage-incomplete error for `real-hf2024-053-5ba72ce231c9`). The `_01` file was retained, not overwritten.

## Reproduction

```
python scripts/evidence_support_codex_reference_v2_2.py prepare   # refuses to re-freeze
python scripts/evidence_support_field_report_v2_2_01.py report    # refuses to overwrite an existing report
python scripts/evidence_support_field_report_v2_2_01.py verify    # recomputes and diffs against the stored report
python scripts/locked_evidence_support_evaluation_v2_2.py         # refuses to overwrite an existing output
```
