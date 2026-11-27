# Step 4 Role Decision (2026-10-14)

## Decision

Composite outcome of the Step 4 decision table, bound to frozen evidence:

| Row | Finding | Verdict | Evidence |
|---|---|---|---|
| 1 | Deterministic judge is sufficient for the bounded task | **FALSE** | Against the Step 3 AI-derived reference: non-direct specificity 0.259, unsupported-admission rate 0.741 (640/864), crosswalk exact agreement 0.067, bundle exact agreement 0.410 with 69/117 sufficiency disagreements (`results/evidence_judge_real_data_ablation_v1/ai_reference_v2_2/locked_evaluation_addendum_v2_2_01.json`) |
| 2 | Judge has a measurable semantic-support gap | **TRUE (primary)** | Same source: 549/773 reference-IRRELEVANT and 91/91 reference-PARTIAL candidates admitted as SUPPORTED; on the fixture development cohort the judge also disagrees with fixture oracles on 15/66 candidates (all 8 adjacent, all 6 ambiguous-abstention, 1 unsupported) |
| 3 | Judge adds no identifiable value beyond the gate | **TRUE (preserved null)** | `results/evidence_judge_real_data_final_paired_audit_v1/final_paired_audit.json`: gate_decision_differences 0, candidate_ids_retained_differences 0, identical_gate_outcomes 120/120, `genuine_candidate_filtering_observed: false`, `sufficiency_gate_redundancy_observed: true`; the matched run did not record policy-visible evidence, so no downstream value is identifiable from frozen artifacts |
| 4 | Independent reference cannot be obtained | **FALSE** | Step 3 froze an AI-derived reference covering 120/120 cases and 947/947 candidates; accuracy was evaluated descriptively |

Composite action taken:

1. **Row 3 preserved as a null statement about the current stage.** The deterministic Evidence Judge + filter is not claimed as a contribution of the paper: on the frozen real-data cohort it changed no gate decision, no retained candidate set, and no outcome that was recorded. The stage stays optional behind its existing disabled-by-default adapter boundary.
2. **Row 2 activates the conditional Laya evidence-scoring task.** A measurable semantic-support gap exists, so the plan requires defining a new evidence-scoring task on development data distinct from all future evaluation cases and comparing the deterministic baseline with a candidate Laya scorer under a preregistered feasibility gate. This study is separately versioned as `results/evidence_judge_laya_scoring_v1/` and is not a tuning pass on the failed V3 strategy-selection task.
3. **Branch exit binds the outcome.** If the candidate scorer fails the frozen feasibility gate, the failure is archived, no scorer enters Step 6, and the paper continues on the validated deterministic/base system. If it passes, the scorer is implemented behind the disabled-by-default adapter boundary and enters Step 6 as conditional arm C only.

## Development data selection

- Cohort: the 60 frozen fixture scenarios of `results/evidence_judge_paired_validation_v1/frozen_paired_inputs.json` (SHA256 `5dc2717279a6003043bfd8c64c4b129e2ab31c36dfbf5aa04fa7a818462aa7ca`), 66 candidates, 10 preregistered categories covering irrelevant/adjacent evidence, partial support, contradictory sources, benign administration, ambiguous context, missing provenance, multi-command context, direct relevance, and unsupported claims.
- Distinctness: `historical_hf2024_used: false` — no overlap with the 120-case HF-2024 real cohort; fixture construction predates and does not read any Step 3 artifact. **Constraint recorded for Step 6: these 60 fixture cases and the HF-2024 family are both permanently excluded from any future evaluation cohort.**
- Truth: fixture oracles (`oracle_kind: deterministic_fixture_rule`, `human_ground_truth: false`) — deterministic construction rules, not AI labels, so the candidate scorer is judged against non-model ground truth.
- Comparator: the frozen deterministic judge outputs in `evidence_judge_paired_validation_v1/matched_arm_results.json` (SHA256 `d94d5bc01510b4c3e0286641e69ef7ba25351e6613c3fe8c1591a15664ca56da`).

## Deterministic comparator baseline on the development cohort

Computed from frozen artifacts only (no model call), using the preregistered oracle-extension mapping in `results/evidence_judge_laya_scoring_v1/preregistered_thresholds_v1.json`:

- Candidate exact agreement: **51/66 = 0.7727** (judge misses: all 8 `adjacent_insufficient`, all 6 `ambiguous_shell_command` abstentions, 1 `unsupported_behavior_claim`).
- Bundle exact agreement: **60/60 = 1.000** (ceiling; hence the scorer gate for bundles is non-inferiority, while the meaningful-gain gate sits at candidate level where headroom exists).

## Feasibility gate

Frozen before any candidate-scorer call in `results/evidence_judge_laya_scoring_v1/` (protocol, thresholds, prompt, output schema, blind batches, probes, and their hashes). Preregistered numeric gates, scorer identity, serialization/token bounds, abstention rules, and the robustness matrix are recorded there. The outcome section of this document is completed by `feasibility_decision_v1.json` after the run.

## Outcome

**Verdict: FAIL — the candidate scorer does not pass the frozen feasibility gate.** `results/evidence_judge_laya_scoring_v1/feasibility_decision_v1.json` (SHA256 `f42c9bb09c5d1c4bb773070424e4046995472e231239ed15cb59f3ed6057f63b`). The full study directory is the archived failed-attempt record.

Runner (`gpt-5.6-luna`, Codex CLI 0.162.1, strict output schema, 3 frozen blind batches of 20 fixture cases; thresholds preregistered before any call in `preregistered_thresholds_v1.json`) — 4 of 13 gates failed:

| Gate | Required | Achieved | Deterministic baseline | Result |
|---|---|---|---|---|
| Candidate exact agreement | ≥55/66 | 46/66 = 0.697 | 51/66 = 0.773 | FAIL (worse than comparator) |
| Bundle exact agreement | ≥59/60 | 41/60 = 0.683 | 60/60 = 1.000 | FAIL |
| Direct-support false rejection | ≤2/28 | 13/28 = 0.464 | 0/28 | FAIL |
| Natural candidate coverage | ≥49/54 | 47/54 = 0.870 | — | FAIL |
| Abstention (ambiguous candidate/bundle, missing provenance) | ≥5/6 each | 6/6, 6/6, 6/6 | — | PASS |
| Truncation probes / malformed / timeout selftests | 2/2 UNKNOWN, both true | 2/2, true, true | — | PASS |
| Schema validity / field-error rate | 3/3, ≤0.10 | 3/3, 0.056 (7/126) | — | PASS |
| Latency (mean ≤30 s/case; per-call ≤900 s) | — | 0.83 s/case; 28.6 s max | — | PASS |

Failure modes, from the frozen normalized outputs: (a) over-abstention — 12 candidate and 6 bundle UNKNOWNs where fixtures expect determinate labels (5 adjacent→UNKNOWN, 1 direct→UNKNOWN, 1 unsupported→UNKNOWN, 6 bundle INSUFFICIENT→UNKNOWN); (b) over-`PARTIAL` on genuinely direct evidence — 12/28 oracle-DIRECT_SUPPORT candidates (4 direct, 4 benign-administrative, 4 multi-command) scored PARTIAL; (c) consequent bundle under-sufficiency — 13/22 oracle-SUFFICIENT bundles scored INSUFFICIENT. The scorer's abstention and robustness behavior was exemplary on every designed probe; its deficiency is exactly the one the deterministic comparator does not have: it will not commit to direct support when the evidence is direct.

Sensitivity note: the `adjacent_insufficient` PARTIAL-vs-IRRELEVANT oracle choice is arguable; the scorer emitted 3 PARTIAL and 5 UNKNOWN on those 8 candidates, so crediting IRRELEVANT instead would reduce candidate agreement (43/66), not improve it. Under either mapping the scorer is below the comparator and far below the gate, and the direct-support false-rejection gate fails at 13/28 regardless. The verdict does not hinge on the arguable mapping.

Provenance notes: the deterministic baseline was recomputed inside the evaluate phase from the frozen dev artifacts and matched the preregistered counts exactly (51/66, 60/60, 0/28); one runner crash after batch 1's completed call was recovered by validating the preserved `final_message.json` (flagged `recovered_after_runner_crash` in `run_manifest_v1.json`, executor change versioned in `executor_amendment_v1.json`, inputs/prompt/thresholds untouched); the recovered call's wall time was not reconstructible and is recorded as null — the latency gate passes with the other two calls alone by a wide margin.

**Branch consequences (binding for Step 6):**
1. No candidate scorer enters Step 6. There is no conditional arm C; Step 6 defines arms A and B only.
2. The deterministic Evidence Judge stage remains optional behind its disabled-by-default adapter, unclaimed as a contribution (Row 3 null preserved), and remains on the validated deterministic/base path.
3. `results/evidence_judge_laya_scoring_v1/` is preserved intact as the failed-attempt record: protocol, preregistered thresholds, probe, freeze, executor amendment, blind batches, raw calls, normalized reviews, robustness probes, and the decision file.
4. The 60 fixture cases and the HF-2024 family remain permanently ineligible as future evaluation data.
