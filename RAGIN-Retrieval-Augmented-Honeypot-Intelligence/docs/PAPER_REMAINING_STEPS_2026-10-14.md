# RAGIN: Remaining Work toward the Paper

Date: 2026-10-14 (last updated 2026-10-15). Status: planning complete; Steps 1–6 executed and evidenced — Step 1 result archive audit and claim matrix, Step 2 baseline freeze and call-path map, Step 3 evidence-reference gate/freeze, Step 4 role decision, Step 5 working-system observability and correctness gaps, and Step 6 matched protocol/holdout freeze (see `docs/artifact_audit/`, `docs/baseline_freeze/`, and `results/step5_working_system_observability_v1/`, `results/step6_matched_evaluation_protocol_v1/`). Remaining execution steps (7–10) are pending unless explicitly marked otherwise. Planning and Step 6 freezing did not launch confirmatory arm experiments, deploy infrastructure, or revise manuscript sources.

## Objective and scope

Continue the paper by evaluating the complete result archive and the actual working RAGIN system. Establish what the RAG Evidence Judge contributes, and whether a separately validated Laya evidence-scoring task merits integration. Revise the paper after those evidence decisions are locked.

Working manuscript assumption: `paper/main.tex` and its included `paper/sections/` files are the full scientific manuscript. `paper/sp2027.tex` is a separate shorter surface. Use the full manuscript for evidence completeness first; adapt the shorter surface after the scientific content is settled. Venue-specific deadlines and formatting must be verified at the packaging stage.

## Current state that the plan must respect

| Workstream | Established | Remaining gap |
|---|---|---|
| Laya V2b decision layer | Frozen primary completed; no decision signal on the single-family AI-derived reference; no primary workflow uplift | Preserve as bounded negative evidence. It does not justify further tuning on the used 120/169 cases. |
| Laya V3 policy adaptation | Synthetic task adaptation failed its semantic gates | This checkpoint/task has no authorization from the recorded study gates to become the full post-retrieval policy. Evidence scoring is a different task and would require a separate study. |
| RAG Evidence Judge | Deterministic implementation and optional candidate filtering exist; Laya scoring adapter remains disabled | Real-data correctness lacks an independent reference; full downstream workflow was absent from the 120-case ablation. |
| Evidence Judge synthetic comparison | 60 frozen fixture cases; baseline 32 false admissions, judge zero under the fixture oracle | The oracle does not provide independent real-data accuracy. |
| Evidence Judge retrospective comparison | 120 cases, 947 candidate judgments, 523 retained candidates in each arm; gate outcomes identical in all pairs | Judge redundancy versus correct sufficiency remains unresolved. Post-hoc filtering changed zero evidence sets/gates. |
| V4 substantive runtime | Matched retrospective runs completed in deterministic/logistic policy arms | Policy quality was not evaluated; sparse substantive effects and incomplete commit metadata limit conclusions. These arms do not use Laya. |
| Base paper | Archived grounding, verification, consistency, Jev, scorer, and retrieval-engine evidence exist | Complete archive classification, current-code reproducibility, and a claim-by-claim reconciliation are still needed. |

Source anchors: `docs/PAPER_RESULTS_EVALUATION_2026-10-14.md`; `docs/evidence_judge/EVIDENCE_JUDGE_CONTRACT_V1.md`; `results/evidence_judge_real_data_final_paired_audit_v1/final_paired_audit.json`; `results/evidence_judge_filtering_impact_posthoc_v1/posthoc_report.md`; Laya and V4 frozen result reports.

## Step 1 — Complete the result audit and build one registry

**Action.** Inventory every artifact under `results/` and related evidence directories. Read each structured artifact, report, protocol, manifest, and freeze by experiment family. Account for raw outputs, annotations, analyses, smokes, aborted attempts, checkpoints, operational traces, and binary/figure artifacts. Use structured parsing and artifact inspection; record any unreadable or unresolved artifact explicitly.

**Outputs.** A complete file manifest with path, size, format, SHA256, experiment ID, source/producer, input cohort, execution mode, model identity where available, reference type, parent artifacts, and status. A master result registry assigns each experiment `paper-eligible`, `bounded/supporting`, `exploratory`, `synthetic-contract`, `reference-pending`, `historical/superseded`, `aborted/failed`, or `operational/provider-unavailable`. A claim matrix connects every manuscript number to a JSON key or file/line and its denominator.

**Coverage gate.** Every inventoried file is assigned to an experiment or an explicit unresolved category. All paper numbers have a source and a bounded interpretation. No unresolved artifact is silently promoted. A format parse is recorded separately from scientific review. Include all Evidence Judge families omitted by the earlier review, all Laya/V4 studies, and the original paper families.

## Step 2 — Freeze the working-system baseline and experiment boundaries

**Action.** Capture the current dirty worktree as a provenance snapshot without discarding user changes: Git HEAD, tracked/untracked state, relevant source/configuration hashes, dependency versions, model checkpoints, retrieval corpus, feature flags, and runtime mode. Trace the actual `server_v2 -> Sandbox -> Harness` path and distinguish it from direct component and graph runners.

**Outputs.** Baseline implementation manifest; executable call-path map; resolved configuration table for baseline, Evidence Judge, filtering, V4 selector, and Laya flags. Specify which combination is the deployed/default baseline and which combinations are research arms.

**Gate.** Every future row can be bound to the same frozen source/environment. The Laya scoring placeholder cannot be reported as model execution. Prior frozen studies remain intact, and each new attempt receives a unique additive output directory.

## Step 3 — Establish an independent reference for evidence support

**Action.** Use the existing blinded 120-case Evidence Judge packet to assess the correctness of the already frozen retrospective observations. Review candidate support and bundle sufficiency independently of judge/gate/policy outputs. Prefer two independent human reviewers, record disagreements and adjudication, and preserve `UNKNOWN` cases. If only AI review is feasible, define a separate AI-derived reference with fixed identities, disclosure of dependence, and restricted claims; never call it human ground truth.

**Outputs.** Reference protocol and annotation freeze; complete reviewer files with document citations; agreement/disagreement and adjudication records; final reference freeze; locked analysis of the existing 120-case arms.

**Gate.** Labels are demonstrably blind to system outputs and complete under the protocol. Model/system labels cannot serve as the reference. The existing 120 cases are used for descriptive evaluation of the frozen study, not for selecting a new model and then claiming fresh confirmatory performance on the same cases. Candidate-level uncertainty uses case/source-family clustering where the sampling design supports it.

**Decision.** Determine whether the deterministic judge detects genuine unsupported evidence, whether it merely repeats the gate on this cohort, and which failure categories remain. Equal gate outcomes alone cannot establish either accuracy or equivalence.

## Step 4 — Decide the Evidence Judge and Laya roles

| Finding after reference evaluation | Next action |
|---|---|
| Deterministic judge is sufficient for the bounded task | Retain or simplify it according to measured value; proceed with full-system evaluation. Laya need not be part of the paper's critical path. |
| Judge has a measurable semantic-support gap | Define a new evidence-scoring task with development data distinct from all future evaluation cases. Compare the deterministic baseline with a candidate Laya scorer. |
| Judge adds no identifiable value beyond the gate | Preserve the null, keep the stage optional or remove it from the claimed contribution, and evaluate the base working system. |
| Independent reference cannot be obtained | Retain descriptive/runtime claims only and state accuracy is unevaluated. The full-system safety/reproducibility work can continue. |

**Conditional Laya task.** Judge whether each retrieved document directly supports the observed command/context and whether the bundle is sufficient. Keep provenance validation, label parsing, allowed document IDs, conflicts, and serving authority in deterministic code. This is a separately versioned evidence-scoring study, not another tuning pass on the failed V3 strategy-selection task.

**Feasibility gate.** Freeze questions, serialization/token bounds, output schema, abstention rules, model identity, and thresholds before new held-out validation. Test irrelevant/adjacent evidence, partial support, contradictory sources, benign administration, ambiguous context, missing provenance, truncation, timeouts, and malformed output. Require meaningful gains over the deterministic comparator and acceptable false-rejection/latency cost under preregistered thresholds. Those thresholds must be specified before calls, not inferred from observed results. An uncalibrated confidence field cannot override hard validity checks.

**Branch exit.** If the scorer fails this gate, archive the failure and continue the paper using the validated deterministic/base system. If it passes, implement it behind the existing disabled-by-default adapter boundary and include it as a conditional arm in Step 6.

## Step 5 — Close the working-system observability and correctness gaps

**Action.** Exercise the complete active path through Don evidence export, judge/filter, gate, policy, substantive generator, mandatory verifier, HITL, commit, and final serving. Close gaps exposed by V4 exports before a new scientific run.

**Required evidence per turn.** Correlated request/session/turn/case/arm IDs; source/config hashes; input/context hashes; retrieval query/corpus/document IDs; judge identity and outputs; before/after policy-visible evidence; gate reason; selected strategy; generator consumption; generated and final served hashes; verification/retries/fallback; approval; accepted/rejected/no-op commit with reason and state hashes; per-stage/end-to-end latency; provider/model identity and errors when applicable.

**Required scenarios.** Baseline feature flags OFF, supported evidence, irrelevant/partial-only evidence, conflicting evidence, missing provenance, model timeout/malformed output where applicable, verifier rejection, HITL REQUIRE without approval, fallback, persistence/restart, and rejected-update rollback. Verify that policy-visible evidence and consumed strategy match the trace, and that response differences survive removal of decorative markers.

**Outputs and gate.** Focused unit/integration/security results and a recorded broad regression run with failures classified. Every served turn has an observable verifier/approval/commit disposition. Record fallback and no-op state events explicitly; missing commit metadata is not filled by inference. No unverified serve, unauthorized commit, unsafe evidence promotion, or arm-state leakage is admissible. Resolve failures on the tested path before running Step 7; document unrelated pre-existing failures separately.

**Status (2026-10-15).** Complete. 13 scenarios / 17 turns through the full active path (Chrollo → Don export/judge/filter → gate → V4 policy → substantive generator → mandatory verifier → HITL → commit → serving, incl. one Sandbox serving-layer turn) with per-turn evidence records; required-evidence coverage, all scenario expectations and all 13 admissibility invariants PASS; fallback and no-op commits explicit, no `NOT_VERIFIABLE` commit metadata; 6 new focused tests green; broad regression recorded with zero new failures vs the pre-change baseline, the one on-path regression resolved at root cause (commit exceptions fail closed). Evidence: `docs/artifact_audit/STEP5_WORKING_SYSTEM_OBSERVABILITY_2026-10-15.md`; `results/step5_working_system_observability_v1/` (frozen via `sha256_manifest.json`).

## Step 6 — Freeze a matched full-system evaluation protocol

**Arms.** A: baseline Don plus current gate. B: identical Don evidence plus deterministic Evidence Judge/filter and the same gate. C: same evidence plus a validated Laya scorer and frozen filter/gate, only if Step 4 passes. Keep the selected policy, generator, verifier, HITL, and state initialization identical within each intended contrast. A separate V4 deterministic/logistic policy comparison requires its own estimand and must not be mixed into the judge contrast.

**Data.** Prefer a separately acquired controlled/prospective source. Otherwise disclose the retrospective source and enforce source-group, normalized-family, exact-input, and clone-lineage disjointness from every used Laya, V4, and Evidence Judge cohort. Inspect exclusions before selection; freeze selection independently of judge outputs. Do not silently reuse the old 120/169 Laya or 120 judge cases as a new confirmatory holdout. Choose sample size through a stated effect target and paired power/precision analysis rather than reusing a convenient count.

**Outcomes.** For evidence quality, preregister unsupported-evidence admissions as the primary target against the blinded reference, with false-rejection/abstention tradeoffs. For a working-system utility claim, define a separately justified served-output or workflow primary outcome sensitive to the proposed change. Do not automatically reuse accepted-non-fallback rate when earlier studies demonstrate a ceiling. Include response quality/consistency, policy correctness when referenced, strategy consumption, fallback/retries, safety, latency, and operational completion as distinct secondary measures.

**Freeze gate.** Hash-lock source, data, retrieval evidence, questions/models, thresholds, primary/secondary outcomes, exclusions, missingness, statistical tests, clustering, multiplicity, seed, and execution/abort policy before confirmatory calls. Construct the independent reference under blinding. Preregister how provider failures and interrupted attempts are reported; raw outputs precede outcome joins.

## Step 7 — Demonstrate the actual ingress, then execute the complete study

**Ingress proof.** Run an isolated local stack. Exercise the actual HTTP chat endpoint and an SSH client through Cowrie. Correlate the bytes received by the client with the final served digest, verifier, approval, and commit event. An HTTP/component replay is not sufficient evidence of the SSH wire path.

**Study execution.** Run every frozen case/arm with isolated sessions, fictional state, and caches governed by the protocol. Captured commands remain inert input. Record both deterministic and provider-backed modes honestly; a real-model claim requires demonstrated model inference and generator availability. Preserve unsuccessful rows and provider failures. For an interrupted run, follow the frozen resume/restart rule and keep the aborted attempt separate; never assemble a successful study from selected failures or incompatible versions.

**Completion gate.** Exact case/arm coverage, unique case-arm pairs, immutable raw output, input symmetry, model identity, retrieval symmetry where required, manipulation delivery, complete trace coverage, and safety invariants all reconcile. Freeze the raw results before scoring or tuning. External cloud/deployment changes, if later needed, are a separate concrete authorization step.

## Step 8 — Perform one locked analysis and decide the result

**Action.** Join frozen outputs and references once under the protocol. Compute paired differences and uncertainty at the correct observation unit. Report all-case operational completion separately from reference-evaluable and model-available denominators. Keep engineering delivery, evidence correctness, policy correctness, served quality, and attacker-engagement claims distinct.

**Outputs.** Machine-readable metrics; per-case comparisons; reference sensitivity; error taxonomy; latency/cost tradeoffs; safety/coverage reconciliation; a result classification of positive, null, negative, or inconclusive for each preregistered outcome. Update the master registry and claim matrix with exact paths, keys, denominators, and hashes.

**Gate.** No unplanned subgroup replaces the primary result. Exploratory analyses are labeled and do not tune the frozen study. If the judge is redundant or Laya adds cost without benefit, that conclusion is retained. Absent human/adversarial field evidence limits engagement claims even if a local matched study succeeds.

## Step 9 — Revise the manuscript from the locked claim matrix

**Order.** Methods and evaluation first; then design/implementation, discussion/limitations, introduction/contributions, conclusion, and abstract. Describe the shipped/default path and optional research variants accurately. Keep Laya V2b, failed V3 adaptation, deterministic judge, new scorer, and V4 policy studies as separate experiment identities.

**Outputs.** Updated `paper/main.tex` and included sections; generated tables/figures sourced directly from locked artifacts; correct analysis-versus-served channels; model/reference disclosure; result/exclusion chronology; revised architecture figure showing only implemented behavior as active. Use the full paper for scientific completeness before adapting `paper/sp2027.tex`.

**Gate.** Every quantitative statement is linked to the claim matrix. Every claimed contribution is supported by the appropriate experiment. Nulls, failure/abstention rates, denominators, provider unavailability, reference dependence, and deployment scope remain visible. Do not claim a general fold-down, live Laya benefit, or field effectiveness from the existing descriptive studies.

## Step 10 — Review, reproduce, and package

**Action.** Review scientific validity and code/artifact reproducibility; fix substantiated findings. Rebuild figures/tables and LaTeX from the frozen sources, inspect rendered pages, validate bibliography/citations, and compare all paper numbers against the registry. Verify current venue requirements using authoritative sources before layout/submission packaging.

**Outputs.** Final review report; reproduced artifact/build manifest; portable source/data instructions; figure/table and manuscript checks; explicit unresolved limitations and readiness decision. Submission or external publication is a later authorized action, not implied by this plan.

**Final gate.** The paper is internally reproducible and scientifically bounded, all promised claim-supporting experiments are complete or their claims removed, the relevant runtime checks pass or their limits are explicit, and the final package meets the selected venue's current requirements. A successful build alone cannot satisfy this gate.

## Execution order and immediate next task

Critical path: Step 1 archive/claim reconciliation -> Step 2 baseline freeze -> Step 5 runtime trace/correctness closure -> Step 6 protocol freeze -> Step 7 complete execution -> Step 8 locked analysis -> Steps 9–10 manuscript and final review.

Steps 3–4 resolve the Evidence Judge/Laya branch and must finish before including that branch in the confirmatory protocol. They may proceed independently of local runtime trace fixes. The base RAGIN evaluation and paper can continue if a Laya candidate fails or an evidence-reference claim remains unavailable.

**First execution task:** complete the archive-wide result registry and claim matrix, beginning with the Evidence Judge families omitted from the previous review. Report the exact coverage, unresolved provenance, and the evidence needed to settle the paper's remaining claims before implementing or launching a new experiment.

## Progress ledger

- [x] Current architecture and source/result navigation documents saved.
- [x] Laya V2b/V3 and V4 distinctions reviewed; Evidence Judge omission corrected in the review memo.
- [x] Remaining-work plan saved.
- [x] Step 1 — Complete archive-wide result registry and claim matrix. Hash-bound inventory covers 2,473 files under `results/` and `evidence/`; 2,424 JSON/JSONL/CSV files parsed successfully (including one whole-JSON document with a `.jsonl` suffix), 43 text files readable, and 6 binaries hash-classified; claim matrix and paper-to-artifact discrepancies saved under `docs/artifact_audit/`.
- [x] Step 2 — Freeze current baseline and runtime configuration. Snapshot: `docs/baseline_freeze/baseline_manifest.json` and `docs/baseline_freeze/worktree_manifest.jsonl`; server call-path, output boundaries, resolved code defaults, and configuration-precedence audit: `docs/baseline_freeze/runtime_call_path_and_config.md`. The dirty worktree was preserved; no model call or test was run.
- [x] Step 3 — Freeze an AI-derived evidence-support reference and evaluate existing judge outputs. Reference: single fixed reviewer `gpt-5.6-luna` (Codex CLI, strict output schema) over six frozen blind 20-case batches, all 120 cases / 947 candidates covered, 914 candidate and 117 bundle labels evaluable with valid document+paragraph citations, 33/3 `UNKNOWN` retained. Reference freeze and manifest: `results/evidence_judge_real_data_ablation_v1/ai_reference_v2_2/reference_freeze_v2_2.json` (+ manifest); protocol: `CODEX_REFERENCE_PROTOCOL_V2_2.md`. Locked analysis: `locked_evaluation_v2_2.json` and final `locked_evaluation_addendum_v2_2_01.json` (case-cluster bootstrap), run only after hash-gating the frozen arm and paired-comparison files. Headline descriptives: direct-support recall 1.000, specificity 0.259, unsupported-admission rate 0.741, bundle exact agreement 0.410, gate states and retained sets identical across arms in 120/120 cases. Not human ground truth, not independent consensus; retrospective single-source-family cohort, descriptive only. Audits: `docs/artifact_audit/STEP3_EVIDENCE_REFERENCE_GATE_2026-10-14.md` and `docs/artifact_audit/STEP3_REFERENCE_FREEZE_AND_LOCKED_ANALYSIS_2026-10-14.md`; field-level error/UNKNOWN attribution: `ai_reference_v2_2/field_level_error_report_v2_2_02.json` (all 33 candidate and 3 bundle UNKNOWNs attributed: 21 field-validation errors, 12+3 model-explicit); requirement-by-requirement closure: `docs/artifact_audit/STEP3_COMPLETION_CHECKLIST_2026-10-14.md`.
- [x] Step 4 — Decide judge role and conditional Laya scorer feasibility. Decision: judge has a measurable semantic-support gap (specificity 0.259, unsupported-admission 0.741 vs the Step 3 reference) and adds no identifiable value beyond the gate (0 gate/retention differences in 120/120 cases) — stage stays optional, unclaimed, behind the disabled-by-default adapter. Conditional Laya evidence-scoring feasibility study frozen and run under `results/evidence_judge_laya_scoring_v1/` (60 fixture dev cases with deterministic fixture oracles, preregistered thresholds, `gpt-5.6-luna` candidate scorer): **FAIL** — candidate agreement 46/66 (below comparator 51/66), bundle 41/60 (below 60/60), direct-support false rejection 13/28; abstention and robustness gates all passed. Branch exit executed: no scorer enters Step 6 (no arm C), failure archived intact. Audit: `docs/artifact_audit/STEP4_ROLE_DECISION_2026-10-14.md`. The 60 fixture cases and the HF-2024 family are permanently ineligible as future evaluation data.
- [x] Step 5 — Close full-system trace and correctness gaps. Complete; evidence and audit: `docs/artifact_audit/STEP5_WORKING_SYSTEM_OBSERVABILITY_2026-10-15.md`.
- [x] Step 6 — Freeze new matched evaluation protocol and untouched holdout. Complete; evidence and freeze: `docs/artifact_audit/STEP6_MATCHED_EVALUATION_PROTOCOL_2026-10-15.md` and `results/step6_matched_evaluation_protocol_v1/`.
- [x] Step 7 — Prove ingress and complete all case/arm executions. Deterministic HTTP study is raw-frozen at 80/80 unique pairs, and the isolated Cowrie SSH wire proof correlates client bytes to the served digest, verifier, approval, policy, and accepted commit. Completion gate: PASS. Provider-backed inference and external deployment remain explicitly out of scope. Evidence: `docs/artifact_audit/STEP7_EXECUTION_2026-10-15.md`, `scripts/run_step7_ingress_proof_v1.py`, `scripts/audit_step7_completion_gate_v1.py`, and `results/step7_full_system_evaluation_v1/`.
- [x] Step 8 — Lock analysis and update claim decisions. Deterministic judge contrast on 40-case prospective cohort: P1 null (both arms 0.7500 unsupported-admission, p=1.0000, criterion not met), P2 descriptive only (P1 did not reject; zero substantive serves in deterministic mode). Reference: gpt-5.6-luna via Codex CLI, 40 cases/70 candidates, no DIRECT_SUPPORT labels. Analysis: `results/step8_locked_analysis_v1/locked_analysis_result_v1.json`; audit: `docs/artifact_audit/STEP8_LOCKED_ANALYSIS_2026-10-15.md`. Result: judge adds no measurable evidence-quality improvement on this cohort, consistent with Step 3/4 findings. P2 zero reflects deterministic fallback-to-baseline serving, not substantive generator evaluation.
- [x] Step 9 — Revise manuscript and scientific figures/tables. Committed revision in the prescribed order: `17aed58` (evaluation, introduction, conclusion, discussion + experiment-registry/manifest updates) and `ace5944` (appendix, background, design, two-channel tables). Working-tree revision pass (uncommitted as of this audit): the paper is retitled `Verified Generative Deception: Serving-Time Safety for LLM Honeypots` on the anonymous IEEEtran conference/compsoc build — matching the sp2027 venue surface — with a rewritten abstract stating the serving-time boundary (grounding buys intelligence, verification buys safe serving, the deterministic floor absorbs provider failure); the bibliography is deduplicated 61→56 entries (exact-duplicate `sladic2025` merged into `valeros2024`; uncited/flow-IDS padding entries removed), leaving zero undefined citations and zero defined-but-uncited entries across the full-paper and sp2027 surfaces. Citation repair in `related.tex`: the deployment-shape sentence re-anchors to `lopez2024` (verified container/cloud-deception coverage), `valeros2024` is restored to the GPT-driven SSH-bot sentence, and the unsupported intrusion-detection clause is removed. Figures resolve plotted values through `paper/figures/generated_values.tex` (`scripts/gen_sp_figures.py --check` passes against the five locked artifacts); two-channel tables annotate provenance to `results/cti_manual_audit.json`; the architecture figure is audited as implemented-behavior-only. Builds: full paper 28 pages, sp2027 15 pages, both 0 errors / 0 undefined citations. Audit: `docs/artifact_audit/STEP9_MANUSCRIPT_REVISION_2026-10-15.md`.
- [x] Step 10 — Final review, reproduction, and package. Complete; independent read-only gate review returned **READY** (pass 2) after the two pass-1 NOT READY items were fixed and re-verified; 11-file hash record 11/11; no commit or submission action taken. Audit: `docs/artifact_audit/STEP10_REVIEW_AND_PACKAGING_2026-10-15.md`.
