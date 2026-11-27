# AI Annotator Agreement Audit v2

## 1. Scope

This is a provenance correction and conservative reliability recomputation for six labeled AI-agent annotation runs over the same 120 cases. The three blank annotation packets are instrument-only files and do not enter any reliability statistic. This audit does not inspect Chrollo or Laya predictions, confidence/probability scores, model-disagreement flags, ground truth, or confirmatory evaluation results.

The six labels are AI-agent annotations. They are not human ground truth, and agreement does not establish correctness.

## 2. Provenance correction

The original manifest had nine entries: three blank packets and six labeled files. The legacy IDs `human_r1`, `human_r2`, and `human_r3` were misleading labels for labeled AI-agent files. The corrected manifest assigns immutable neutral IDs `agent_run_01` through `agent_run_06` and preserves each legacy ID only in a `previous_run_id` field.

The three `codex_*` outputs are tied by preserved execution evidence to model `gpt-5.6-luna`; this is recorded as `model_identity_provenance: OBSERVED`. The three former `human_*` source files have no independently preserved model/session evidence, so their model identity is `UNKNOWN` with `DERIVED_UNVERIFIED` provenance. The legacy timestamp is retained only as `DERIVED_UNVERIFIED` metadata; it is not claimed to be a machine-observed run time.

## 3. Why blank packets are not raters

`packet_r1`, `packet_r2`, and `packet_r3` contain 120 blank labels each. They define the annotation instrument but contribute no observations. Counting them as raters would introduce missing/blank values into agreement and would misstate the number of independent labeled runs. The v2 audit therefore classifies exactly three records as `INSTRUMENT_ONLY` and excludes them from all statistics.

## 4. Six labeled AI-agent runs

| run_id | previous_run_id | packet | model_identity | model provenance | cases |
|---|---|---|---|---|---|
| agent_run_01 | ai_r1 | r1 | gpt-5.6-luna | OBSERVED | 120 |
| agent_run_02 | ai_r2 | r2 | gpt-5.6-luna | OBSERVED | 120 |
| agent_run_03 | ai_r3 | r3 | gpt-5.6-luna | OBSERVED | 120 |
| agent_run_04 | human_r1 | r1 | UNKNOWN | DERIVED_UNVERIFIED | 120 |
| agent_run_05 | human_r2 | r2 | UNKNOWN | DERIVED_UNVERIFIED | 120 |
| agent_run_06 | human_r3 | r3 | UNKNOWN | DERIVED_UNVERIFIED | 120 |

All six runs contain exactly 120 case IDs, the case-ID sets match exactly, all labels are nonblank, and all labels belong to the nine-label taxonomy.

## 5. Pairwise multiclass agreement

All 15 combinations of the six labeled runs were recomputed with nominal Cohen's kappa over the nine-label taxonomy. `n` is always 120.

| pair | exact | rate | κ | binary n | excluded U | binary agree | binary rate | binary κ |
|---|---|---|---|---|---|---|---|---|
| agent_run_01 × agent_run_02 | 97 | 0.8083 | 0.645381 | 117 | 3 | 97 | 0.8291 | 0.6205 |
| agent_run_01 × agent_run_03 | 95 | 0.7917 | 0.594595 | 106 | 14 | 94 | 0.8868 | 0.721175 |
| agent_run_01 × agent_run_04 | 84 | 0.7000 | 0.400333 | 117 | 3 | 84 | 0.7179 | 0.328872 |
| agent_run_01 × agent_run_05 | 73 | 0.6083 | 0.363934 | 117 | 3 | 75 | 0.6410 | 0.320144 |
| agent_run_01 × agent_run_06 | 77 | 0.6417 | 0.302137 | 114 | 6 | 79 | 0.6930 | 0.283662 |
| agent_run_02 × agent_run_03 | 98 | 0.8167 | 0.696621 | 106 | 14 | 97 | 0.9151 | 0.804107 |
| agent_run_02 × agent_run_04 | 96 | 0.8000 | 0.661415 | 118 | 2 | 103 | 0.8729 | 0.730429 |
| agent_run_02 × agent_run_05 | 88 | 0.7333 | 0.604246 | 118 | 2 | 94 | 0.7966 | 0.602024 |
| agent_run_02 × agent_run_06 | 92 | 0.7667 | 0.611246 | 115 | 5 | 97 | 0.8435 | 0.669118 |
| agent_run_03 × agent_run_04 | 88 | 0.7333 | 0.532392 | 106 | 14 | 90 | 0.8491 | 0.628233 |
| agent_run_03 × agent_run_05 | 79 | 0.6583 | 0.49005 | 106 | 14 | 83 | 0.7830 | 0.56941 |
| agent_run_03 × agent_run_06 | 84 | 0.7000 | 0.483192 | 104 | 16 | 87 | 0.8365 | 0.606061 |
| agent_run_04 × agent_run_05 | 88 | 0.7333 | 0.596172 | 119 | 1 | 94 | 0.7899 | 0.593635 |
| agent_run_04 × agent_run_06 | 103 | 0.8583 | 0.749263 | 116 | 4 | 107 | 0.9224 | 0.829412 |
| agent_run_05 × agent_run_06 | 96 | 0.8000 | 0.698176 | 117 | 3 | 96 | 0.8205 | 0.648649 |

Exact agreement ranges from 0.6083 to 0.8583; mean is 0.7433 and median is 0.7333. The best pair is `agent_run_04 × agent_run_06`; the worst is `agent_run_01 × agent_run_05`.

## 6. Pairwise binary agreement

The binary projection maps `BENIGN` to `NEGATIVE`, the seven attack-related labels to `POSITIVE`, and excludes `UNCERTAIN` whenever it occurs in either member of a pair. Thus `binary_n + excluded_uncertain = 120` for every pair; the binary denominator is not silently fixed at 120.

Binary agreement ranges from 0.6410 to 0.9224; mean is 0.8132 and median is 0.8291. The best pair is `agent_run_04 × agent_run_06`; the worst is `agent_run_01 × agent_run_05`.

## 7. Multi-rater reliability

Multiclass reliability uses Fleiss' kappa with all six fixed ratings per case: N = 120, observed agreement = 0.743333, expected agreement = 0.412068, Fleiss κ = 0.563442.

Binary reliability uses Option A: only cases where all six ratings are non-`UNCERTAIN` are retained. The eligible N is 104; 16 cases are excluded because at least one rating is `UNCERTAIN`. Observed agreement = 0.828205, expected agreement = 0.559911, Fleiss κ = 0.609636. This preserves the fixed six-rater assumption.

## 8. Strict consensus structure

The v2 exact-label view assigns each case to exactly one category in precedence order: strong six-of-six consensus, conservative binary consensus, strict exact-label majority, or high ambiguity. Binary consensus requires at least four non-`UNCERTAIN` ratings and unanimity on the binary side; therefore a pattern such as 2 `BENIGN` + 4 `UNCERTAIN` is not binary consensus.

### View A: exact-label strict consensus

| category | count |
|---|---|
| STRONG_CONSENSUS | 60 |
| BINARY_CONSENSUS | 6 |
| STRICT_MAJORITY | 41 |
| HIGH_AMBIGUITY | 13 |

The previous reported structure was `STRONG_CONSENSUS = 60`, `BINARY_CONSENSUS = 8`, `MAJORITY_ONLY = 52`, `HIGH_AMBIGUITY = 0`. The corrected structure is `60 / 6 / 41 / 13`. The former permissive majority bucket included cases without an exact label receiving at least four of six votes.

### View B: conservative binary-support consensus

This mutually exclusive binary view uses the same six-of-six strong bucket, requires at least four non-`UNCERTAIN` ratings for binary consensus, then counts remaining cases with a binary side receiving at least four of six ratings as binary strict majority.

| category | count |
|---|---|
| BINARY_STRONG_CONSENSUS | 60 |
| BINARY_CONSENSUS | 6 |
| BINARY_STRICT_MAJORITY | 44 |
| HIGH_AMBIGUITY | 10 |

## 9. Ambiguous cases

There are 13 `HIGH_AMBIGUITY` cases. They are preserved in `ai_rater_disagreement_map_v2.jsonl`, not removed or converted into truth labels. The audit records the following non-exclusive diagnostic reasons: `cross_binary_disagreement` = 12, `no_exact_label_at_least_4_of_6` = 11, `too_many_uncertain_for_binary_support` = 1. The case-level map retains all six labels, uncertainty counts, binary support counts, majority flags, and the final ambiguity category.

## 10. Run-to-run stability

Repeated-packet comparisons are reported as `RUN-TO-RUN ANNOTATION STABILITY`. The former `human_*` naming is not used as evidence of human annotation, and no unverified comparison is called cross-model stability.

| pair | exact | rate | binary n | excluded U | binary agree | binary rate | multiclass κ | binary κ | changed | model status |
|---|---|---|---|---|---|---|---|---|---|---|
| agent_run_01 × agent_run_04 | 84 | 0.7000 | 117 | 3 | 84 | 0.7179 | 0.400333 | 0.328872 | 36 | DERIVED_UNVERIFIED |
| agent_run_02 × agent_run_05 | 88 | 0.7333 | 118 | 2 | 94 | 0.7966 | 0.604246 | 0.602024 | 32 | DERIVED_UNVERIFIED |
| agent_run_03 × agent_run_06 | 84 | 0.7000 | 104 | 16 | 87 | 0.8365 | 0.483192 | 0.606061 | 36 | DERIVED_UNVERIFIED |

For the three repeated-packet pairs, model identity is `DERIVED_UNVERIFIED` because at least one member lacks independently supported model identity. The three `agent_run_01`/`02`/`03` within-Codex comparisons are separately retained as same-observed-model run-to-run comparisons; they do not establish correctness or generalize beyond these runs.

## 11. What these results DO support

- A reproducible description of agreement among six labeled AI-agent annotation runs on 120 shared cases.
- Conservative multiclass and fixed-rater binary reliability estimates with explicit `UNCERTAIN` handling.
- Identification and preservation of exact consensus, binary-supported consensus, strict exact majorities, and ambiguous cases.
- Descriptive run-to-run stability for repeated packet assignments.

## 12. What these results DO NOT support

- They do not establish human inter-rater reliability or create human ground truth.
- They do not establish that any annotation is correct.
- They do not justify majority-voting AI annotations into final truth.
- They do not support a model-specific or cross-model stability claim where model identity is unverified.
- They do not provide a Chrollo-vs-Laya prediction comparison or a confirmatory scientific result.

## 13. Freeze boundary before confirmatory analysis

This v2 reliability audit is frozen before any confirmatory labels or predictions are joined. No Chrollo/Laya prediction was inspected, no ground truth was created, and no confirmatory Chrollo-vs-Laya analysis was run. Ambiguous cases remain represented in the audit artifacts. The confirmatory scientific verdict remains **INCONCLUSIVE**.

The machine-generated freeze manifest is `results/laya_research/ai_rater_reliability_freeze_v2.json`. Do not modify it after confirmatory labels or predictions are joined.
