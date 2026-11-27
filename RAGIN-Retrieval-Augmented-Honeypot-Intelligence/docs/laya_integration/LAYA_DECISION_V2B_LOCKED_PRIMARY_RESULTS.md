# Laya Decision V2b Locked Primary Results

## 1. Study chronology

The study chronology was: exploratory 120; inert-treatment manipulation failure; V2a repair; aborted V2a primary attempt; V2b input-representation repair; complete fresh 169-case restart; raw outputs frozen; reference constructed blind; one-time locked join.

## 2. Frozen design

The V2b freeze hash was verified as `4e3e463ca1031d77fd8b518cb7008724ca91b17c8b4154f999addcc0ae8019c5`. The primary holdout was N=169. The reference is a `SINGLE_MODEL_FAMILY_AI_DERIVED_ADJUDICATED_REFERENCE` from three blinded repeated `claude-sonnet-4-6-free` APMix runs plus one fresh blinded adjudication run. Run-to-run consistency is not independent-model reliability.

## 3. Raw execution provenance

The raw execution freeze hash was verified as `45e1de7624116fda5ea33a4082d37b47db65d20bee172e90d1a29a2f8e597758` with baseline=169 and treatment=169. No model was rerun. The old V2a partial output was not reused.

## 4. Reference construction provenance

The reference freeze hash was verified as `ef4ba4fc7db2bfa685a06ae824496d4132c944f49be79b784c9104d2bb6ff3b5`. It contains 165 concrete labels, 4 UNCERTAIN labels, 80 NEGATIVE, and 85 POSITIVE. UNCERTAIN cases were excluded only from truth-dependent decision metrics.

## 5. Single-model-family limitation

The reference uses one model family and one API model configuration. Repeated fresh runs may share correlated systematic errors; agreement is run-to-run consistency, not independent-model agreement.

## 6. Decision-level results

N=165; TP=18; TN=62; FP=18; FN=67. Balanced accuracy=0.493382; accuracy=0.484848; sensitivity=0.211765; specificity=0.775000; precision=0.500000; F1=0.297521; MCC=-0.016016; FPR=0.225000; FNR=0.788235.
Real Laya decision availability=169/169; NO_SIGNAL=0; evaluated coverage=165/165.

## 7. Workflow primary result

The preregistered primary was accepted_non_fallback_response_rate. Baseline=162/169 (0.958580); treatment=162/169 (0.958580); absolute delta=0.000000; relative delta=0.000000.
Paired cells: A=162, B=0, C=0, D=7; discordant N=0; exact two-sided McNemar p=1.000000.

## 8. Secondary workflow results

Secondary metrics were retained as secondary and report arm values and paired treatment-minus-baseline differences in the machine-readable workflow artifact. They include verifier first-pass acceptance, total verifier rejections, generation retries, fallback, HITL, fiction and host-fiction rejection, controlled failure, end-to-end latency, Laya incremental latency, decision paths, and response strategies.

## 9. Paired statistics

Paired case-level bootstrap: 10000 replicates, 95% percentile intervals, deterministic seed 20261014. Session-cluster bootstrap was not used because no reliable pre-frozen nontrivial session grouping was available.

## 10. Manipulation delivery

Strategy reached generator=169/169; generation input changed=169/169; candidate changed=162/169; response changed=162/169. These are delivery checks, not quality judgments.

## 11. Safety invariants

Verifier bypasses=0; unauthorized commits=0; direct Laya serving=0; baseline Laya invocations=0; arm-state leakage=0.

## 12. Latency

Baseline E2E mean/p50/p90/p95 ms=114.609/116.631/126.228/130.379; treatment=2094.928/1890.312/2275.917/2851.976. Laya inference mean/p50/p90/p95 ms=1974.792/1767.868/2154.527/2726.294. Laya inference is reported separately because it is not assumed to be wholly represented inside the E2E timer contract.

## 13. Sensitivity analysis

Reference-source sensitivity was computed without changing the pooled primary result. Exact-3/3 stratum N=115; adjudicated stratum N=50.

## 14. Limitations

The primary reference is AI-derived and single-model-family, not human ground truth or a gold standard. The workflow result is a matched observational execution comparison on this frozen holdout; latency and provider determinism require the stated timer and execution-contract caveats.

## 15. Allowed manuscript claims

Decision classification: `PRIMARY_DECISION_SIGNAL_NO_SIGNAL`. Workflow classification: `PRIMARY_WORKFLOW_NO_MEANINGFUL_CHANGE`. Strongest defensible decision claim: The frozen Laya decision layer showed no meaningful attack/non-attack decision signal on the AI-derived adjudicated reference. Strongest defensible workflow claim: The Laya decision layer altered generation strategy but did not improve the preregistered primary workflow acceptance outcome.
