# Conditional Laya Evidence-Scoring Feasibility Protocol V1

Status: frozen before any candidate-scorer model call.

## Purpose and scope

This is the conditional evidence-scoring study activated by the Step 4 decision table (measurable semantic-support gap). It compares the frozen deterministic comparator (`EVIDENCE_JUDGE_V1`) with one fixed candidate scorer on development data that is distinct from every future evaluation cohort. It is a separately versioned evidence-scoring study, not a tuning pass on the failed V3 strategy-selection task. Outcome binding: `docs/artifact_audit/STEP4_ROLE_DECISION_2026-10-14.md`.

## Task

For each development case, score every retrieved candidate document for direct support of the specific behavioral claim under the observed command and available context (`DIRECT_SUPPORT`, `PARTIAL`, `IRRELEVANT`, `CONTRADICTORY`, `UNKNOWN`), and label bundle sufficiency (`SUFFICIENT`, `INSUFFICIENT`, `CONFLICTING`, `UNKNOWN`). Provenance validation, label parsing, allowed document IDs, conflict handling, and any serving authority remain in deterministic code; the scorer output can never promote evidence past the gate.

## Development data (frozen)

- Source: `results/evidence_judge_paired_validation_v1/frozen_paired_inputs.json`, SHA256 `5dc2717279a6003043bfd8c64c4b129e2ab31c36dfbf5aa04fa7a818462aa7ca`.
- 60 fixture scenarios, 66 candidates, 10 preregistered categories; `historical_hf2024_used: false`.
- Truth: fixture oracles (case level, `oracle_kind: deterministic_fixture_rule`) plus the candidate-level oracle extension frozen in `preregistered_thresholds_v1.json`. No AI-generated labels are used as truth in this study.
- Comparator outputs: `results/evidence_judge_paired_validation_v1/matched_arm_results.json`, SHA256 `d94d5bc01510b4c3e0286641e69ef7ba25351e6613c3fe8c1591a15664ca56da`.
- Exclusion rule recorded for Step 6: these 60 cases and the HF-2024 family are permanently ineligible as future evaluation data.

## Blindness

Each scorer request contains only: `case_id`, `command`, `preceding_commands`, `claimed_behavior`, and candidates as `doc_id`, `title`, `content`, `source`, `source_version`, `provenance_status`. Excluded: category, fixture oracle/transform fields, behavior tags, command patterns, conflict status, benign-administrative flag, retrieval traces, comparator outputs, and every Step 3 artifact. The scorer never sees the thresholds file.

## Fixed candidate scorer

| Field | Frozen value |
|---|---|
| Model identity | `gpt-5.6-luna` |
| Interface | Codex CLI `0.162.1`, `codex exec --ephemeral --json --skip-git-repo-check --output-schema` |
| Working directory | `/tmp` (outside the repository) |
| Input channel | blinded batch over standard input |
| Prompt | `SCORER_PROMPT_V1.txt` (includes abstention rules) |
| Output schema | `output_schema_v1.json`, strict; no confidence field permitted |
| Call schedule | 3 consecutive batches of 20 cases; one call per batch; no prompt or model edits after freeze |
| Request bound | at most 300,000 characters per request |
| Output bound | at most 16,384 completion tokens |
| Call timeout | 900 seconds; a timeout, malformed output, or invalid field normalizes affected decisions to `UNKNOWN` and is retained in the record |

The same model family produced the Step 3 reference for the unrelated real cohort; that creates no circularity here because truth in this study is deterministic fixture construction, not model output.

## Validation rules (deterministic)

Candidate review valid iff: label in the allowed set; for non-`UNKNOWN`, at least one integer paragraph index in `1..paragraph_count(content)` and a rationale of 1–8 words; for `UNKNOWN`, empty indexes and a 1–8 word rationale. Bundle review valid iff: label in the allowed set; supporting/conflicting indexes are integers inside candidate range; rationale of 1–12 words. Paragraphs are maximal non-empty line blocks separated by blank lines. Missing, duplicate, out-of-range, or invalid fields become `UNKNOWN` with the fixed filler rationale; coverage gaps are recorded as validation errors. Every gate-relevant statistic is computed only after this normalization.

## Preregistered gates

All numeric gates are frozen in `preregistered_thresholds_v1.json`, written before any scorer call, with the deterministic comparator baseline (candidate 51/66, bundle 60/60, direct false rejection 0/28) computed from frozen artifacts only. Pass rule: every gate passes.

## Robustness matrix

| Condition | Test | Required outcome |
|---|---|---|
| Irrelevant / adjacent evidence | fixture categories `irrelevant_retrieval_candidate`, `adjacent_insufficient` | inside candidate agreement and coverage gates |
| Partial support | `partial_support` | inside candidate agreement gate |
| Contradictory sources | `contradictory_documents` | candidate + bundle agreement gates |
| Benign administration | `benign_administrative_behavior` | candidate agreement and false-rejection gates |
| Ambiguous context | `ambiguous_shell_command` | candidate and bundle UNKNOWN at least 5/6 each |
| Missing provenance | `missing_provenance` | candidate UNKNOWN at least 5/6; gate remains deterministic |
| Truncation | two frozen probes with truncated candidate content | candidate UNKNOWN 2/2 |
| Timeout | simulated call timeout through the harness degradation path | all affected decisions `UNKNOWN` |
| Malformed output | invalid JSON through the harness degradation path | all affected decisions `UNKNOWN` |
| Confidence handling | schema forbids confidence/probability fields | hard validity checks unaffected by any model self-assessment |

## Analysis and branch exit

The evaluate phase recomputes and asserts the comparator baseline from frozen artifacts, scores the normalized candidate output against the fixture-derived oracle, applies every preregistered gate, and writes `feasibility_decision_v1.json` with a `PASS` or `FAIL` verdict exactly once (additive, no overwrite). PASS implements the scorer behind the existing disabled-by-default adapter boundary and specifies conditional arm C for Step 6. FAIL archives this directory as the failed-attempt record, leaves the deterministic stage optional and unclaimed, and Step 6 proceeds without arm C.
