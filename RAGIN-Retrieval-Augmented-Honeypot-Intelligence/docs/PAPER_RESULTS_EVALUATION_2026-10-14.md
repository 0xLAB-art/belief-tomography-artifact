# RAGIN Paper Results Evaluation — 2026-10-14

## Verdict

The paper should not present Laya as a successful decision layer or as a tested retrieval-grounded policy. The frozen V2b decision-layer study found no meaningful decision signal on its AI-derived reference and no gain on its preregistered workflow outcome. The later post-retrieval, RAG-grounded Laya work tested API behavior and synthetic task adaptation; the frozen adaptation validation failed every semantic gate. It did not implement or evaluate the proposed Laya-after-Don path in the working serving project.

There is a separate retrieval-conditioned V4 policy implementation and retrospective runtime evaluation in the repository. Those arms use deterministic or logistic selectors, not Laya, and their result reports explicitly leave policy correctness and effectiveness unevaluated. Keep those results separate from both the Laya experiments and the paper's graph-versus-BM25 retrieval-engine comparison.

## Correction: implemented RAG Evidence Judge path

The initial review omitted the separate Evidence Judge implementation and its results. `ragin/don/evidence_judge.py` implements `DeterministicEvidenceJudge`; `LayaScoringAdapter` is a disabled contract whose `score()` raises an error. `ragin/decision_fusion_v4/evidence_export.py` can invoke the judge after Don retrieval and optionally filter policy-visible evidence under separately controlled flags. This is an implemented RAG evidence-assessment path, even though it does not execute Laya inference.

The 60-case synthetic paired validation reported 32 fixture-defined false admissions in the baseline and zero with the judge (`results/evidence_judge_paired_validation_v1/comparison_summary.json`). Its oracle is a deterministic synthetic fixture, so the result cannot establish independent accuracy. The subsequent 120-case same-source retrospective ablation recorded 947 candidate judgments and identical gate outcomes in all 120 pairs; both arms retained 523 candidates. The final paired audit states `REAL_DATA_EVIDENCE_ACCURACY_NOT_EVALUATED` and `REFERENCE_UNAVAILABLE`. The filtering post-hoc replay found zero additional exclusions because all 231 non-supporting candidate labels were already outside the original relevant set.

The 120-case ablation explicitly did not run policy, generator, verifier, HITL, or commit. Its outstanding tasks are independently reviewing the frozen evidence, assessing whether the judge adds value beyond the gate, and testing the complete working path if that role is retained. This distinction is part of the remaining-work plan; the initial review should not be treated as an exhaustive evaluation of all project results.

## Laya result chain

| Stage | What was tested | Result | Evidence boundary |
|---|---|---|---|
| V2 exploratory matched A/B, N=120 | Real local Laya decision model versus baseline, using a single-model-family AI-derived adjudicated reference | Balanced accuracy 0.6003 on 114 eligible cases; accepted non-fallback rate 113/120 in both arms; paired delta 0, McNemar p=1.0; mean inference latency 1.61 s | Exploratory and reference-dependent. It is mixed evidence, not confirmation of decision value. See `docs/laya_integration/LAYA_DECISION_V2_EXPLORATORY_120_RESULTS.md`. |
| V2b frozen primary, N=169 (165 label-evaluable) | Fresh matched baseline/treatment execution with strategy delivery checks and locked reference join | Balanced accuracy 0.4934 (TP=18, TN=62, FP=18, FN=67); primary workflow rate 162/169 in both arms, delta 0, exact McNemar p=1.0; mean end-to-end latency 114.6 ms baseline versus 2094.9 ms treatment; strategy reached generation on 169/169 and changed the candidate/response on 162/169 | Strongest Laya decision-layer result, but reference is AI-derived from one model family, not human ground truth. It supports “no meaningful signal/no primary workflow change on this frozen study,” not a universal claim that Laya can never help. See `docs/laya_integration/LAYA_DECISION_V2B_LOCKED_PRIMARY_RESULTS.md` and its raw/freeze artifacts under `results/laya_decision_v2/`. |
| V3 API capability probe, 8 synthetic cases × 3 calls | Direct custom-question calls to the pinned Laya API with synthetic Don-like retrieval fields | Schema/allow-list/reference validity 24/24 and stable repeated outputs; it selected on weak, conflicting, or contradictory evidence and made unsupported strategy/reference choices | API expressiveness and contract behavior only. Synthetic inputs; no Don retrieval execution, prior holdout, effectiveness, or runtime integration. See `docs/laya_integration/LAYA_V3_POLICY_CAPABILITY_PROBE.md` and `results/laya_decision_v3/laya_v3_policy_capability_probe.json`. |
| V3.1 frozen task adaptation, 30 validation cases (42 calls including repeats) | Frozen custom evidence-state, bounded-strategy, and evidence-reference task | Structural gates passed 30/30; semantic alignment 13/30 (43.3%); required-abstain recall 6/10 (60%); inappropriate abstention 12/20 (60%); strategy compatibility 3/20 (15%); evidence-reference compatibility 6/20 (30%). Final status `TASK_ADAPTATION_FAILED`. | Synthetic contract-oracle results, not real-world accuracy or effectiveness. The documented decision says full post-retrieval policy implementation is not permitted on this checkpoint. See `docs/laya_integration/LAYA_V3_TASK_ADAPTATION_STUDY.md` and `results/laya_decision_v3/laya_v3_task_adaptation_final_decision_v1.json`. |

### What the current code actually does

The current `server_v2` request path constructs the verified Harness. Its Chrollo adapter can attach a Laya decision/assessment record when enabled, but this is the pre-Don classification seam. The proposed V3 order is different: Don first retrieves and freezes evidence, then Laya proposes a bounded policy. That post-retrieval Laya policy node is not implemented in the serving path.

Don's current adapter does emit an `evidence_bundle` (`ragin/cycle/adapters.py:323-430`). In a non-baseline V4 arm, Harness passes that bundle to `decision_fusion_v4`'s evidence gate and deterministic/logistic policy selector (`ragin/cycle/harness.py:461-476`). `ragin/decision_fusion_v4/config.py` names those arms `RAGIN_V4_DETERMINISTIC` and `RAGIN_V4_LOGISTIC`; there is no Laya selector in that contract. This is the working retrieval-conditioned project path, but it is not the proposed Laya integration.

The actual Laya mapper is called during Chrollo classification in the baseline arm (`ragin/cycle/adapters.py:150-180,219-234`). Hisoka's Jev strategy reader consumes `jev_assessment` (`ragin/hisoka/deception.py:2254` onward), while the active Laya event is named `laya_assessment`/`laya_decision`. Therefore the current server's advisory signal is not equivalent to a proven Jev-style downstream policy effect. V2b's offline matched experiment did deliver a strategy to generation, but it did not establish a useful outcome.

## Separate working-project V4 evidence

The V4 substantive report documents a matched execution of the working path over 240 family-disjoint retrospective records in three arms (720 total). All three arms completed; the decision/evidence runtime ran, but this is not Laya evidence.

- The evidence gate marked 234/240 V4 cases `LOW_RELEVANCE` and only 6/240 `VALID_EVIDENCE`.
- The deterministic arm selected baseline on all 240. The logistic arm selected `maximize_recon_surface` on six and baseline on 234.
- The raw response changed in 3/240 baseline/logistic pairs; substantive generator consumption was observed in only three V4 records. Commit metadata was not verifiable for 717/720 records.
- Verifier passed 720/720 and HITL auto-approved 720/720, but no human reviewed those retrospective records.
- The report explicitly says policy selection quality, retrieval accuracy, strategy superiority, and real-world attacker engagement were not evaluated.

The companion Don V2 report is another retrospective run of 240 inputs × three arms. It likewise finds the deterministic selector at baseline for all 240 and only one downstream response change in the logistic arm; it makes no policy-quality claim. These are runtime/behavioral observations, not validation that an Laya policy grounded in real Don evidence works.

Source reports: `docs/decision_fusion/RAGIN_V4_SUBSTANTIVE_FINAL_RESULTS.md` and `docs/decision_fusion/DON_V2_SUBSTANTIVE_FINAL_RESULTS.md`; raw freezes and records are under `results/decision_fusion_v4/`.

## Main paper evidence map

The current full manuscript is `paper/main.tex`, with evaluation claims in `paper/sections/evaluation.tex`. It contains no Laya claim. Its RQ4 covers Jev and graph-versus-BM25 retrieval; that retrieval-engine comparison is not a Laya decision-layer experiment.

| Paper result family | Current interpretation | Evidence status and boundary |
|---|---|---|
| RAG versus no-RAG grounding | Positive analysis-channel difference; technique +0.3167, actor +0.1400, persona +0.0050; overall +0.1539 | Paired 30-scenario comparison, CIs in `results/bootstrap_ci.json`; distinguish this from the graph-versus-BM25 engine comparison. The old served-text technique/actor signal is substantially affected by scorer echo and must not be collapsed into analysis quality. |
| Verified serving and fiction consistency | No unverified serves in the 218-row campaign; targeted deterministic tests provide property-specific evidence | Supports the declared test surfaces and checks, not broad attacker resistance or field effectiveness. |
| Served-text / scorer results | Keep analysis and served-text channels separate; echo-guarded technique/actor scores fell sharply | Existing results ledger records the correction and says a full guarded 218-row rerun has not been produced. |
| Jev routing | 13-log assessment result and 200-row ceiling comparison; informative hard subset is only six, with one live assessment/rescue and five provider-unavailable rows | Permitted conclusion is no measurable marginal effect at benchmark resolution, not general subsumption. The 5/6 unavailability makes provider coverage central. |
| Jev closed-loop replay | Bait exposure rose 4 to 9 across five clean pairs; dwell was 34 versus 33 | Directional, small-n, no power claim. Do not promote to established attacker-engagement benefit. |
| Graph retrieval versus BM25 | BM25 was significantly better on NDCG@10 and graph was not distinguishable on the other three metrics | Retrieval benchmark is 50 queries × 5 runs. Paper correctly states this as fold-down pressure only; a full verified-loop pipeline A/B/removal is still needed before claiming system-level removal. |
| Chrollo trajectory benchmark | Prefix accuracy increases as observed command history grows | Provider-free held-out replay. The risk-floor diagnostic is self-consistency, not independent security effectiveness. |
| Laya | Absent from the current paper's claims | V2b and synthetic V3 findings may support a bounded negative/failed-adaptation account, but not an efficacy claim. A proposed Laya+RAG working-system result does not exist. |

The underlying project ledger `docs/RAGIN_RESULTS_LEDGER_2026-10-08.md` is useful but predates the V2b primary, V3.1 adaptation result, and later V4 substantive reports. Treat it as the baseline registry, not the current complete snapshot. Its classifications of historical, failed, fallback-only, provider-blocked, and scorer-sensitive files remain important to prevent those rows from being mixed into headline results.

## Paper disposition

1. Keep the existing paper's RAG grounding result, verifier/consistency measurements, bounded Jev results, and retrieval-engine pricing distinct by estimand and evidence type.
2. Do not add a claim that Laya improves the working RAGIN project. The only post-retrieval Laya runs were synthetic contract probes; task adaptation failed before end-to-end implementation.
3. If Laya is discussed, describe V2b as a no-signal/no-workflow-gain result on an AI-derived reference, and V3.1 as a failed synthetic task-adaptation gate. State their limitations and keep them separate from Jev and V4.
4. Do not call the V4 deterministic/logistic runs “Laya,” and do not use them as evidence that Laya+RAG is functional.
5. The next admissible Laya experiment requires a separately versioned model/task redesign that first passes a frozen evidence-grounding/abstention contract. Only after that should an untouched real-runtime holdout compare the same working pipeline with and without post-Don Laya. Preserve identical Don evidence, Chrollo, Hisoka, verifier, HITL, and commit rules across arms; report policy correctness, abstention, latency, generator consumption, verified/fallback serves, and primary workflow outcome separately.

## Audit scope and limits

This review reconciles the two Laya frozen studies, the V3 design/probe/adaptation artifacts, current relevant runtime wiring, current main-paper result claims, the existing RAGIN results ledger, and the newer V4/Don V2 result reports. The repository contains thousands of historical and operational outputs; the 2026-10-08 ledger classifies the earlier result families and exclusions. This review does not re-run every historical experiment, independently reproduce every value in that ledger, re-label raw sessions, or establish paper/submission readiness. The working tree is heavily modified, so these findings refer to the observed 2026-10-14 snapshot.
