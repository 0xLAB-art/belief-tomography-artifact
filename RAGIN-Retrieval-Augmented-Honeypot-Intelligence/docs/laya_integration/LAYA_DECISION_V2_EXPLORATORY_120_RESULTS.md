# REAL Laya Decision Model V2: Exploratory 120-Case Matched A/B Evaluation

**EXPLORATORY ONLY.** This is not a primary confirmatory result and the
reference is **AI_DERIVED_ADJUDICATED_REFERENCE**, not human ground truth.

## Scope and frozen boundary

The evaluation used the frozen `LAYA_DECISION_MODEL_V2` policy and native
Laya decision rule. The policy SHA256 is `95b29d203cf2e149ec4d0dc8ff740f4525b245d04ad575de476361e4854ec8e9`. The native
attack decision remained `attack_probability >= 0.5`; no threshold, stage
mapping, retry budget, metric, outcome judge, or case selection was changed.

The control was `RAGIN_BASELINE`; the treatment was
`RAGIN_LAYA_DECISION`. Inputs were the exact existing 120-case evidence/context
fields, represented only by hashes in the input manifest and never joined to
reference labels before all arm outputs and treatment decision events were
frozen. The execution path used local sparse retrieval and deterministic
template/fast-path generation. No paid API, AWS mutation, public honeypot, or
uncontrolled target was used.

## Decision-level results

Reference eligible N: **114**; excluded `UNCERTAIN`: **6**. Treatment signal
available on eligible cases: **114**;
NO_SIGNAL/unavailable among eligible: **0**.
Coverage was **1.0000** of eligible cases
and **0.9500** of all 120 cases.

| Metric | Value |
|---|---:|
| TP | 8 |
| TN | 77 |
| FP | 15 |
| FN | 14 |
| Balanced accuracy | 0.6002964426877471 |
| Accuracy | 0.7456140350877193 |
| Sensitivity / recall | 0.36363636363636365 |
| Specificity | 0.8369565217391305 |
| F1 | 0.3555555555555555 |
| MCC | 0.19725869939638668 |
| FPR | 0.16304347826086957 |
| FNR | 0.6363636363636364 |

Brier/ECE were withheld because native Laya `noul` is not assumed to be a
calibrated document-level probability under the frozen metric gate.

Source and attack-class sensitivity strata are recorded in
`exploratory_120_decision_sensitivity.json` without outcome-driven selection.

## Workflow primary outcome

`accepted_non_fallback_response_rate`:

- Baseline: **0.9416666666666667** (113/120)
- Treatment: **0.9416666666666667** (113/120)
- Absolute delta: **0.0**
- Relative delta: **0.0**

Exact two-sided McNemar on the paired case outcome: B baseline-only success =
**0**, C treatment-only success = **0**, discordant N =
**0**, p = **1.0**.

Secondary rates, denominators, verifier rejections, retries, fallback, HITL,
fiction checks, controlled failures, latency, and provider determinism are in
`exploratory_120_workflow_metrics.json` and
`exploratory_120_paired_statistics.json`.

## Routing and runtime

Treatment branches: `LAYA_ATTACK_STRATEGY` = **24**,
`LAYA_NON_ATTACK_STRATEGY` = **96**,
`BASELINE_NO_SIGNAL` = **0**. The treatment branch
changed from the baseline strategy on **120/120**
cases (**1.0**).

The real runtime was `laya 0.4.2`, model `english`, CPU,
checkpoint `55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851` with SHA256 `891102d372688fc2a094dac56a384bc537b87c63f21f9f3dac0be2b7cbc8d86c`, via
`ragin.decision.laya_runtime:LayaRuntime.infer -> laya.Router.predict`.
Per-case Laya latency N = **120**, mean = **1613.592 ms**,
p50 = **1245.9409999999998 ms**, p90 = **2668.5801 ms**, p95 =
**2948.3932499999996 ms**, min = **1019.754 ms**, max =
**7733.151 ms**, standard deviation = **986.9572905241253 ms**.
Model initialization was enforced before the first matched case. A separate
wall-time measurement for that one-time load was not captured; per-case values
therefore report `LayaRuntime.infer` latency under the runtime contract and do
not include the one-time model load.

## Failure and safety analysis

Laya exceptions: **0**; timeouts:
**0**; malformed/low-confidence outputs:
**0**; NO_SIGNAL: **0**.
All unavailable cases preserved baseline strategy. Deterministic verifier
bypasses = **0**, unauthorized state commits = **0**, direct Laya serving
events = **0**.

## Exploratory interpretation

Classification: **EXPLORATORY_MIXED_SIGNAL**. This descriptive classification considers
both decision-level quality and the workflow primary outcome, without defining
a new success threshold after seeing results. It does not authorize changing
the frozen policy or interpreting the AI-derived reference as human truth.

## Primary holdout decision

Decision: **PROCEED_WITH_FROZEN_POLICY**. The 169-case primary holdout remains
unevaluated, unlabeled, and untouched. No policy or threshold tuning occurred.

## Artifact manifest

- Pre-run integrity: `results/laya_decision_v2/exploratory_120_pre_run_integrity.json`
- Input manifest: `results/laya_decision_v2/exploratory_120_input_manifest.json`
- Decision events: `results/laya_decision_v2/exploratory_120_laya_decisions.jsonl`
- Decision metrics: `results/laya_decision_v2/exploratory_120_decision_metrics.json`
- Workflow metrics: `results/laya_decision_v2/exploratory_120_workflow_metrics.json`
- Paired statistics: `results/laya_decision_v2/exploratory_120_paired_statistics.json`
- Evaluation freeze: `results/laya_decision_v2/exploratory_120_evaluation_freeze_v2.json`

