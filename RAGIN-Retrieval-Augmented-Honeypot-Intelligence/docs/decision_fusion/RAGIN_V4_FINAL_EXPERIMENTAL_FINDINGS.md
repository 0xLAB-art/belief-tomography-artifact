# RAGIN V4 Post-fix final experimental findings

Experiment: `HF2024_POSTFIX_FAMILY_DISJOINT_V1`  
Status: additive forensic audit of frozen artifacts; no new execution was performed.

## Classification

- `BEHAVIORAL_INTEGRATION_EVALUATION_COMPLETE`
- `POLICY_CORRECTNESS_NOT_EVALUATED`
- `REAL_WORLD_ENGAGEMENT_NOT_EVALUATED`

## Scope and frozen inputs

The audit used only the sealed directory
`results/decision_fusion_v4/hf2024_postfix_family_disjoint_v1/`.

| Artifact | SHA256 |
|---|---|
| `raw_arm_outputs.jsonl` | `33278567cead415667dd63f7789b8bbb1d8c0061797dc7466304ad5d92d741db` |
| `reference_free_behavioral_analysis.json` | `f5c43113d42584ff56ae695e2207d71c6070c63366b408f39a12df8bd696bb62` |
| `raw_execution_freeze.json` | `63729ec18f1d93b566df901f1cab428ce3b5a022a332d043dbd75e1e4de341c8` |
| `holdout_freeze.json` | `73efbb94d9381dc9860a6e7003dcd7db2f3f21e76cde026f274638796d4176ae` |
| `implementation_environment_freeze.json` | `d855f0d39f495b293c0dac54b5cd8ba52b9b66766b9de4beaefc31b484ab86b9` |
| `protocol_freeze.json` | `ecbf19ce527f95265266cdcaafedb127f04845375311a7cf98b275c77a657961` |

The raw freeze contains 720 records: 240 baseline, 240 deterministic V4, and 240 logistic V4 records, matched over 240 case IDs. The candidate holdout contains 240 unique source groups and 240 unique normalized command families, with zero overlap with the prior-family exclusion set. The corpus is a same-source retrospective validation, not independent prospective field data.

## Response-difference audit

The audit compared response text within each matched case. Known strategy suffixes were removed in a secondary sensitivity analysis; no frozen record was altered.

| Matched comparison | Identical | Strategy-conditioned suffix only | Formatting only | Different template | Other/substantive | Changed after suffix removal |
|---|---:|---:|---:|---:|---:|---:|
| Baseline vs deterministic | 120 | 120 | 0 | 0 | 0 | 0/240 |
| Baseline vs logistic | 1 | 239 | 0 | 0 | 0 | 0/240 |
| Deterministic vs logistic | 2 | 238 | 0 | 0 | 0 | 0/240 |

Thus, 120/120, 239/239, and 238/238 raw response changes were additive strategy-conditioned suffixes. The response body and template selection remained unchanged in every non-identical pair. There were no observed substantive template changes, formatting-only changes, or strategy-driven template-ID changes in the matched comparisons. Representative redacted examples are:

- `...administration response...` versus the same text plus `[strategy suffix: administration request completed]`.
- `...lookup response...` versus the same text plus `[strategy suffix: service discovery: internal endpoints available]`.
- deterministic administration suffix versus logistic discovery suffix, with the common response body unchanged.

The sensitivity analysis removes only the exact static suffix markers implemented by the generator. It finds zero residual response changes in all comparisons. Therefore the frozen data verify generated-text changes, but do not support a claim of strategy-dependent substantive behavior.

## Strategy delivery and consumption

All 480 V4 records report `strategy_source = v4_policy_decision`.

- Delivered: 478/480.
- Not delivered: 2/480. Both are the same authorization fast-path case across the two V4 arms; the recorded serve path is `GENERATED_VERIFIED` and the selected strategy is `maximize_recon_surface`.
- Consumed: 359/480.
- Not consumed: 121/480. These are explicit V4 `baseline` selections: 120 deterministic records and 1 logistic record. They preserve baseline behavior and have no strategy-conditioned template operation. They are not counted as successful strategy consumption.

The 478 delivered records are 357 consumed plus 121 explicit baseline selections. No record was reclassified as consumed merely because a trace field was present. The one baseline authorization record with `template_id = NOT_VERIFIABLE` is reported as a missing trace, not as a template success.

## Policy behavior and evidence provenance

| Arm | Strategy distribution | Gate states | Fallback reasons |
|---|---|---|---|
| Baseline | baseline 240 | `NOT_APPLICABLE_BASELINE` 240 | `no_gateway` 239; `NOT_VERIFIABLE` 1 |
| Deterministic V4 | baseline 120; low-intensity administration 119; maximize recon surface 1 | `VALID_EVIDENCE` 239; `LOW_RELEVANCE` 1 | `no_gateway` 239; `fastpath` 1 |
| Logistic V4 | maximize recon surface 239; baseline 1 | `VALID_EVIDENCE` 239; `LOW_RELEVANCE` 1 | `no_gateway` 239; `fastpath` 1 |

Strategy agreement was 120/240 between baseline and deterministic, 1/240 between baseline and logistic, and 2/240 between deterministic and logistic. The distributions show a deterministic concentration in baseline/low-intensity administration and a logistic concentration in maximize-recon-surface. This is a descriptive strategy-collapse/limited-variation finding, not an accuracy judgment.

For each V4 arm, all 239 `VALID_EVIDENCE` records had nonempty valid document references and the references were internally consistent with the recorded valid-document set: 239/239. The one `LOW_RELEVANCE` record per V4 arm is the evidence-gate fallback case and has no valid evidence bundle. No source-reference integrity failure was observed within the recorded evidence fields.

## Safety and trace limitations

- Verifier status was passed for 720/720 records, with zero verifier failures and zero recorded deterministic-false verifier outcomes. This verifies the recorded local verifier result, not external deployment safety.
- HITL records show 720/720 automatic approvals, 0/720 human reviews, and no manual intervention.
- Commit events are `NOT_VERIFIABLE` for 720/720 records. No commit was inferred from approval or response delivery.
- External generation calls were false for all 720 records; attacker commands were not executed.
- Two V4 generation fast-path bypasses were observed as described above.
- Full Don/Chrollo retrieval and upstream trace detail was not retained in the compact raw freeze. This prevents independent reconstruction of every upstream retrieval/gating step.

Accordingly, verifier-pass and no-external-call/no-command-execution are observed invariants of this freeze. Serving completion, infrastructure commit behavior, and complete upstream evidence provenance remain unverified where the trace says `NOT_VERIFIABLE`.

## Scientific interpretation

### A. Verified software integration

The V4 policy decision is recorded as the authoritative strategy source for all 480 V4 records. In 478 records it was delivered to the generator; 359 records consumed a non-baseline strategy-conditioned template operation. Legacy Jev/Laya fields did not override the recorded V4 source in this experiment.

### B. Verified changes in generated response text

Compared with baseline, 120/240 deterministic and 239/240 logistic responses changed at the raw-hash/text level. The forensic audit shows that all of these changes were the known static strategy suffixes. After removal of those markers, changed responses were 0/240 for both comparisons.

### C. Strategy-dependent substantive behavior

Not supported by this freeze. No residual body, formatting, or template-selection change remained after removing the decorative strategy suffixes.

### D. Policy decision correctness

Not evaluated. No independent labels, judge, or ground-truth endpoint was used, and ATT&CK labels were not treated as reference truth. Higher or lower strategy-change counts do not establish policy correctness or superiority.

### E. Real-world attacker engagement

Not evaluated. This is a retrospective dataset replay through a deterministic local template runtime, with no live attacker, network, AWS, Cowrie, or infrastructure operation.

## Paper-ready results-section draft

We conducted a family-disjoint retrospective validation using 240 newly selected normalized command families from the pinned HF-2024 corpus. Three matched arms produced 720 sealed records: baseline, deterministic V4, and logistic V4. The V4 decision was the recorded authoritative strategy source for all 480 V4 records. It reached the generator in 478 records and was consumed by a non-baseline strategy-conditioned template in 359 records; 121 records explicitly selected baseline behavior, and two records followed a recorded authorization fast path.

Relative to baseline, response text changed in 120/240 deterministic cases and 239/240 logistic cases. A forensic comparison attributed all observed changes to static strategy suffixes: 120/120, 239/239, and 238/238 changed matched pairs were suffix-only for baseline/deterministic, baseline/logistic, and deterministic/logistic comparisons, respectively. After removing those exact suffix markers, residual response changes were 0/240 in every comparison. Thus this experiment verifies end-to-end wiring and observable additive text changes, but does not demonstrate substantive strategy-dependent behavior, policy correctness, deception quality, attacker engagement, or logistic superiority.

All 720 recorded verifier outcomes passed, all 720 HITL records were automatically approved, and no human review occurred. These are recorded runtime invariants rather than evidence of unobserved serving or commit behavior: commit events were not verifiable, two V4 fast paths bypassed strategy delivery, and full Don/Chrollo traces were not retained. The same-source retrospective design and absence of independent reference labels further limit external validity and correctness claims.

## Threats to validity

The cohort is retrospective and drawn from the same HF-2024 source corpus, so it is not independent field evidence. Family exclusion reduces direct leakage from the prior holdout but does not remove all corpus-level dependence. The highly concentrated strategy distributions limit variation for comparing strategies. The response effect is implemented as static suffix text, so raw response-hash changes overstate behavioral distinctness. Compact traces omit full upstream retrieval and commit observations. Automatic HITL approvals are not human review. No independent reference labels were available; policy correctness and real-world engagement therefore remain untested.

## Reproducibility and freeze manifest

Sampling and execution rules are frozen in `holdout_freeze.json`, `protocol_freeze.json`, and `raw_execution_freeze.json`; implementation and environment are frozen in `implementation_environment_freeze.json`. The raw and analysis SHA256 values above are required inputs to this report. The companion JSON audit contains the complete manifest, exact denominators, audit classifications, and output hashes.

Unresolved blocker: none for the requested additive forensic audit. The limitations above are deliberate trace and study-design boundaries, not execution failures.
