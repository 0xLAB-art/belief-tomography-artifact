# RAGIN Audit Closure and Paper Release Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring the RAGIN project, result artifacts, documentation, and paper to an auditable release state without overstating what the current evidence establishes.

**Architecture:** Treat the repository as one evidence pipeline with four independently checkable surfaces: execution environment, canonical result artifacts, manuscript sources/builds, and project/release metadata. Repair and verify upstream evidence first, then synchronize the paper and documentation, while preserving separate labels for live audited results, provider-free rescue results, fallback/provider pilots, historical artifacts, and unsupported or failed experiments.

**Tech Stack:** Python 3 project with pytest, Ruff, mypy, Hugging Face/sentence-transformers cache, JSON/JSONL result artifacts, LaTeX/IEEEtran, TikZ/PGFPlots, `pdflatex`, `pdftotext`, Git, and the existing RAGIN test and artifact-consistency suite.

**Spec:** `docs/SP2027_AUDIT_2026-10-03.md`, the current repository state, the existing `results/` artifacts, and the audit findings recorded before this plan was created.

## Global Constraints

- Preserve the evidence boundary: compiling a PDF, passing Number Lock, or passing artifact-consistency tests does not prove scientific validity, causal identification, independent replication, or venue readiness.
- Do not present the provider-free rescue benchmark as evidence of adaptive-agent superiority; it is a held-out, provider-free classifier/behavior-floor rescue and self-consistency analysis.
- Do not claim live provider-backed results while `results/apmix_quota_status.json` reports catalog drift, missing requested models, and unprobed quota.
- Keep analysis-channel scores separate from served-text scores; report the scorer/echo-guard definition with every headline metric.
- Do not delete session data, cached models, historical artifacts, or generated outputs without explicit approval; quarantine or classify them instead.
- Preserve provenance, hashes, split definitions, train/test overlap checks, fallback status, and the distinction between canonical, historical, superseded, failed, and operational-trace artifacts.
- The canonical manuscript surface must be chosen explicitly; `paper/main.tex` and `paper/sp2027.tex` must not be silently treated as the same submission.
- Every changed source must be regenerated, rendered, and inspected at final publication scale before release claims are made.

## Review Focus

- Corrupt or unavailable ML dependencies: a clean sparse/BM25 fallback must not hide a broken default hybrid path; test both modes and record dependency state.
- Contradictory result prose: `results/jev_hard_subset.json` must agree with its counts and the manuscript; test the six informative rows, one assessed/rescued row, and five unavailable rows.
- Metric-definition leakage: served-text, analysis-channel, both-channel, and echo-guarded values must remain distinct in JSON, tables, captions, and prose.
- Manuscript drift: stale test counts, page counts, result references, labels, and generated PDFs must be caught by source checks plus a fresh LaTeX/PDF inspection.
- Provider/catalog drift: unavailable models and fallback-only pilots must never be converted into provider performance claims; test the blocked-release decision path.

---

## Current Baseline and Release Decision

The last audit found substantial internally reproducible evidence, but the project is not release/submission-ready. The closure work starts from these observed conditions and must remeasure them before changing anything:

- Full pytest: `9 failed, 1584 passed, 116 skipped`; all nine failures were `VectorStore`/`ThreatRAGEngine` failures caused by a zero-byte cached `all-MiniLM-L6-v2` `model.safetensors` blob.
- Sparse/BM25 targeted path: `tests/unit/test_don.py -k 'TestThreatRAGEngine'` passed 18 tests with `RAGIN_RAG_MODE=bm25`.
- Artifact-focused checks: 131 tests passed across artifact consistency, figure geometry, supported claims, verifier red-team, and two-channel metrics.
- Static checks on the changed RAG engine passed: Ruff, mypy, and `git diff --check`.
- Fresh `paper/main.tex` compilation is blocked by missing `algorithm.sty`; the existing PDF is 27 pages. The existing `paper/sp2027.pdf` is an 11-page rescue manuscript, but its fresh rebuild must be verified before release.
- `results/jev_hard_subset.json` contains six informative rows and one assessed/rescued Jev-arm row, while `resolution_statement` incorrectly says the stratum is empty.
- README, appendix, and `PROJECT_STATUS.md` contain stale test-count/page-count statements.
- The worktree contains tracked source/result/PDF changes and approximately 1,985 untracked files, mostly session outputs; no broad cleanup is authorized by this plan.
- `results/apmix_quota_status.json` records catalog drift, only `claude-sonnet-4-6-free` in the observed catalog, missing requested DeepSeek/Grok models, and unprobed quota.

The release gate remains **blocked** until the tasks below produce fresh evidence and all required gates pass. A paper may be circulated as an explicitly labeled audit draft before then, but it must not be labeled submission-ready.

## File Map

| Surface | Files | Responsibility |
|---|---|---|
| Environment and execution | `.venv/`, `ragin/don/rag_engine.py`, `tests/unit/test_don.py`, project dependency/config files | Default hybrid path, explicit sparse/BM25 fallback, reproducible test execution |
| Evidence artifacts | `results/jev_hard_subset.json`, `results/two_channel_metrics.json`, `results/external_baseline_model_coherent.json`, `results/verifier_redteam*.json`, `results/sp2027_rescue/`, `results/apmix_quota_status.json` | Canonical result values, scorer definitions, rescue provenance, provider availability |
| Artifact validation | `tests/unit/test_artifact_consistency.py`, `tests/unit/test_supported_claims.py`, `tests/unit/test_two_channel_metrics.py`, `tests/unit/test_figure_geometry.py`, `tests/unit/test_verifier_redteam.py` | Machine-checkable consistency and claim boundaries |
| Manuscripts | `paper/main.tex`, `paper/sp2027.tex`, `paper/sections/*.tex`, `paper/two_channel_tables.tex`, `paper/main.pdf`, `paper/sp2027.pdf` | Full audit manuscript, S&P rescue manuscript, generated PDFs, tables, figures |
| Project documentation | `README.md`, `PROJECT_STATUS.md`, `docs/SP2027_AUDIT_2026-10-03.md`, `results/sp2027_rescue/README.md` | Reproduction instructions, status, scope, limitations, and rescue interpretation |
| Release hygiene | `MANIFEST.json` if present, Git status/diff, `graphify-out/graph.json`, a new release manifest/report | Provenance, dirty-worktree classification, generated-output boundary, final decision |

---

### Task 1: Freeze the audit baseline and classify the worktree

**Files:**
- Create: `docs/RAGIN_RELEASE_MANIFEST_2026-10-08.md`
- Inspect: `git status --short`, `git diff --stat`, `results/`, `data/sessions/`, `graphify-out/graph.json`
- Do not modify: existing session files, PDFs, results, or source code in this task

**Interfaces:**
- Consumes: current Git status, current commit SHA, existing audit document, result manifests/hashes, and file timestamps.
- Produces: a dated baseline that later tasks can compare against, including a classification of canonical, generated, historical, failed, provider-pilot, and unreviewed artifacts.

- [x] **Step 1: Record the exact baseline.** Capture the current commit SHA, branch, Git status counts, modified paths, untracked-path classes, Python/TeX tool versions, and the status of existing manifests.
- [x] **Step 2: Classify generated/session material without deleting it.** Mark session transcripts, PDFs, caches, old benchmark outputs, provider pilots, and rescue artifacts as `canonical`, `supporting`, `historical`, `failed`, `fallback-only`, `operational-trace`, or `unreviewed`.
- [x] **Step 3: Record the two manuscript surfaces.** State that `paper/main.tex` is the full audit manuscript and `paper/sp2027.tex` is the shorter rescue/submission surface until a release decision changes that designation.
- [x] **Step 4: Verify the manifest is reproducible.** Re-run the path/count/hash commands documented in the new manifest and confirm that they reproduce the recorded values without mutating the worktree.

**Pass condition:** The release manifest identifies every artifact class used by later tasks and makes no claim that an unreviewed or provider-blocked artifact is canonical evidence.

### Task 2: Repair and verify the default ML execution environment

**Files:**
- Modify only as required: dependency/configuration files and environment setup documentation
- Verify: `.venv/`, Hugging Face cache for `all-MiniLM-L6-v2`, `ragin/don/rag_engine.py`, `tests/unit/test_don.py`
- Test: `tests/unit/test_don.py` and the full pytest suite

**Interfaces:**
- Consumes: Task 1 baseline and the current zero-byte `model.safetensors` failure evidence.
- Produces: a working default hybrid path plus an explicitly documented sparse/BM25 fallback; both paths remain testable and semantically distinct.

- [x] **Step 1: Diagnose the cache without broad deletion.** Verify the snapshot symlink, target size, model identifier/revision, and whether the configured environment can reacquire the model. Record the exact failure if reacquisition is unavailable.
- [x] **Step 2: Repair only the identified model artifact or dependency.** Restore a complete pinned model snapshot through the project’s supported setup path; if network/model access is unavailable, leave the environment unchanged and record the blocker rather than silently switching the default.
- [x] **Step 3: Add/retain explicit path coverage.** Ensure `RAGIN_RAG_MODE=bm25`/`sparse`/`offline` selects the sparse path and the default continues to select hybrid retrieval; add a test only if the existing suite does not pin this contract.
- [x] **Step 4: Run the focused test matrix.** Run the affected DON tests once with the repaired default hybrid path and once with `RAGIN_RAG_MODE=bm25`.
- [x] **Step 5: Run the full suite.** Run `.venv/bin/pytest -q`; distinguish genuine code failures from environment/setup failures and preserve all failures in the release report.

**Pass condition:** The default hybrid path runs without the zero-byte model error, the explicit sparse path still passes, and the full suite is either green or has a newly evidenced, narrowly scoped blocker documented in Task 10.

### Task 3: Repair the JEV hard-subset artifact and lock its interpretation

**Files:**
- Modify: `results/jev_hard_subset.json`
- Modify if needed: `tests/unit/test_artifact_consistency.py`, `tests/unit/test_supported_claims.py`
- Synchronize later: `README.md`, `paper/sections/evaluation.tex`, `paper/sections/appendix.tex`, `results/sp2027_rescue/README.md`

**Interfaces:**
- Consumes: current JEV counts and the manuscript’s bounded six-row interpretation.
- Produces: one internally consistent artifact whose counts, resolution statement, tests, and paper prose all describe the same six informative rows.

- [x] **Step 1: Write a failing consistency assertion if none exists.** Assert `base_incorrect_informative == 6`, `len(informative_rows) == 6`, `jev_arm.assessed == 1`, `jev_arm.unavailable == 5`, and `jev_arm.rescued == 1` for the current corpus, while also asserting that the resolution text does not say the stratum is empty.
- [x] **Step 2: Replace only the contradictory resolution wording.** State that the informative stratum contains six rows, one Jev-arm row was assessed and rescued, and five Jev-arm rows were unavailable/refused under the recorded policy; preserve the bounded refusal/availability caveat.
- [x] **Step 3: Run the artifact and supported-claim tests.** Confirm the JSON and all claim extractors agree with the six-row interpretation.
- [x] **Step 4: Compare the artifact against the manuscript.** Confirm no section implies six successful Jev rescues, full provider coverage, or an empty hard subset.

**Pass condition:** The artifact, tests, README, and paper use the same six/one/five counts and explicitly avoid extrapolating from the single assessed row.

### Task 4: Build the canonical results ledger and provenance table

**Files:**
- Create: `docs/RAGIN_RESULTS_LEDGER_2026-10-08.md`
- Inspect: `results/b4_baseline_zodiac_20260922.json`, `results/bootstrap_ci.json`, `results/graph_consistency_bench.json`, `results/stability_run1_vs_run2.json`, `results/external_baseline_model_coherent.json`, `results/two_channel_metrics.json`, `results/verifier_redteam*.json`, `results/benchmark_report.json`, `results/sp2027_rescue/`
- Modify only if required: artifact metadata/manifest files whose values are demonstrably inconsistent

**Interfaces:**
- Consumes: Task 1 classification and Task 3 corrected JEV artifact.
- Produces: a single table mapping each reported number to its file, split/corpus, scorer, execution mode, provenance, status, and permitted claim.

- [x] **Step 1: Record canonical live-audit values.** Include the B4 baseline, bootstrap CIs, graph consistency, stability, verifier red-team, and the live audited composite with exact scorer definitions and corpus sizes.
- [x] **Step 2: Record the two-channel distinction.** Preserve the difference between analysis-channel values (`cti_analysis_avg`), both-channel values, ordinary served-text values, and echo-guarded served-text values. Record that the echo-guarded served technique/actor values are much lower than the uncorrected served values.
- [x] **Step 3: Record model-coherent baselines.** Keep bare `llm_unverified` and grounded/verified replay values as analysis evidence; state that the verifier paired delta is zero in that artifact and do not convert it into an independent causal claim.
- [x] **Step 4: Exclude failed or non-canonical results from headline claims.** Mark `results/benchmark_report.json` (158/158 failures), stale human-evaluation directories, old Cowrie outputs, provider pilots, and fallback-only operational traces as non-headline evidence unless a separate analysis explicitly uses them.
- [x] **Step 5: Add provenance checks.** Record hashes, timestamps, train/test overlap, fallback counts, and the exact scripts/configurations required to regenerate each canonical artifact.
- [x] **Step 6: Verify ledger-to-artifact agreement.** Run the existing artifact-consistency and supported-claim tests, then manually inspect every headline row against its source JSON.

**Pass condition:** Every headline number has one source of truth and a bounded allowed interpretation; failed, historical, and provider-blocked artifacts cannot be mistaken for current evidence.

### Task 5: Decide and document the canonical manuscript surface

**Files:**
- Modify: `PROJECT_STATUS.md`
- Modify: `README.md`
- Modify: `docs/SP2027_AUDIT_2026-10-03.md` only if its status is stale
- Keep synchronized: `paper/main.tex`, `paper/sp2027.tex`, `paper/main.pdf`, `paper/sp2027.pdf`

**Interfaces:**
- Consumes: Task 4 results ledger and the two existing manuscript sources.
- Produces: an explicit status decision naming the full audit manuscript, the shorter rescue manuscript, and the one surface intended for any future submission package.

- [x] **Step 1: Compare source scopes.** List sections, experiments, appendices, figures, and result artifacts included by each manuscript; identify any result present in one but absent from the other.
- [x] **Step 2: Select a canonical release target.** Choose one of the two sources for the next release package and label the other as a companion audit/extended version; do not merge them by implication.
- [x] **Step 3: Update status language.** Replace stale page counts and ambiguous “paper ready” wording with dated, evidence-bounded status and the explicit fresh-build gate.
- [x] **Step 4: Add a source-of-truth note.** State which `.tex` file controls the release PDF, which files are generated, and how the companion manuscript is maintained.
- [x] **Step 5: Verify status consistency.** Search the repository for old page counts, old test counts, “submission-ready”, and references to the wrong manuscript surface; classify each remaining occurrence as current, historical, or to be updated.

**Pass condition:** A new reader can tell which paper is canonical, what the companion paper contains, and why neither is submission-ready until the fresh-build and evidence gates pass.

### Task 6: Synchronize reproduction counts, dates, and claims in project documentation

**Files:**
- Modify: `README.md`
- Modify: `PROJECT_STATUS.md`
- Modify: `paper/sections/appendix.tex`
- Review: `results/sp2027_rescue/README.md`, `docs/SP2027_AUDIT_2026-10-03.md`

**Interfaces:**
- Consumes: Task 2 test totals, Task 4 ledger, and Task 5 manuscript decision.
- Produces: documentation that reports current commands and current observed totals without mixing historical snapshots with current validation.

- [x] **Step 1: Replace stale test totals.** Update README and appendix references to `1,709` collected tests only after the full suite has been rerun; if the suite remains blocked, report the last verified pass/fail/skip breakdown instead of inventing a green total.
- [x] **Step 2: Repair stale project status counts.** Replace the `1323 passed` and `17 pages` statements with dated status tied to the current artifacts and build result.
- [x] **Step 3: Audit reproduction commands.** Ensure commands specify the intended environment, mode, corpus, output path, and whether provider access is required; mark provider-free rescue commands separately from live/provider commands.
- [x] **Step 4: Audit claim language.** Search for “proves”, “independent”, “adaptive”, “submission-ready”, “human evaluation”, and “provider” and bound every occurrence to the evidence ledger.
- [x] **Step 5: Run documentation checks.** Run repository tests that parse supported claims and manually compare command/output pairs against the current files.

**Pass condition:** Documentation is numerically current, dated where state can drift, and does not promise provider access, human reliability, causal effect, or venue readiness that the evidence does not support.

### Task 7: Rebuild figures, tables, and manuscripts from active sources

**Files:**
- Modify as needed: `paper/main.tex`, `paper/sp2027.tex`, `paper/sections/*.tex`, `paper/two_channel_tables.tex`
- Regenerate: `paper/main.pdf`, `paper/sp2027.pdf`, and any figure/table outputs generated by the active build
- Verify: all active figure/table source files and labels

**Interfaces:**
- Consumes: Tasks 3–6 corrected artifacts, ledger, documentation, and canonical manuscript decision.
- Produces: PDFs whose text, tables, captions, citations, page counts, and figures are generated from the current source rather than stale binaries.

- [x] **Step 1: Repair the TeX environment.** Install or restore the project-supported package providing `algorithm.sty` and verify `kpsewhich algorithm.sty`, `kpsewhich algpseudocode.sty`, `kpsewhich IEEEtran.cls`, and required graphics packages resolve.
- [x] **Step 2: Update active sources only.** Synchronize result values, JEV wording, scorer definitions, test counts, limitations, and paper status in the `.tex` files selected by Task 5; do not hand-edit PDFs.
- [x] **Step 3: Build each active manuscript twice.** Run the repository’s LaTeX build command twice for `paper/main.tex` and `paper/sp2027.tex` as applicable, capturing logs and exit codes.
- [x] **Step 4: Inspect compilation diagnostics.** Check for missing references, undefined citations, overfull boxes, missing figures, duplicate labels, and accidental draft/status text.
- [x] **Step 5: Inspect rendered output.** Use `pdfinfo`/`pdftotext`, final-size page rendering, and the existing geometry checks; inspect all result tables, captions, algorithm boxes, and figures at publication scale.
- [x] **Step 6: Verify generated-output provenance.** Record source commit, build command, tool versions, PDF hashes, page counts, and build timestamps in the release manifest.

**Pass condition:** The selected manuscript builds from current sources with no unresolved TeX/reference/figure errors, its PDF text matches the ledger, and final-size visual inspection finds no clipped, unreadable, stale, or misleading element.

### Task 8: Close provider/catalog and reproduction blockers

**Files:**
- Review/update: `results/apmix_quota_status.json`, `results/apmix_probe_history.jsonl`, provider configuration/docs, `results/sp2027_rescue/README.md`
- Do not relabel: existing provider pilot outputs

**Interfaces:**
- Consumes: Task 4 evidence ledger and the recorded catalog drift/quota status.
- Produces: a reproducible provider status with a clear blocked/fallback-only decision and no unsupported provider comparison.

- [x] **Step 1: Recheck catalog/quota only within authorized project scope.** Record timestamp, catalog response, requested model availability, quota probe result, and error/status codes.
- [x] **Step 2: Keep the blocked branch explicit.** If requested models are absent or quota remains unprobed, mark provider-backed reruns blocked and retain the rescue benchmark as provider-free evidence only.
- [x] **Step 3: If models become available, run a controlled smoke check first.** Not applicable for this run: the catalog gate returned drift, so no requested model was available to verify.
- [x] **Step 4: Re-run provider experiments only after smoke verification.** Not run: provider reruns remain blocked and no smoke verification passed.
- [x] **Step 5: Update claims and release status.** Provider-backed findings may enter the ledger only with complete provenance; otherwise the release report must state that provider evidence is unavailable.

**Pass condition:** The repository never treats an unavailable model, HTTP 404/unknown model, empty catalog, or fallback trace as a provider result.

### Task 9: Verify rescue-benchmark validity and limitations

**Files:**
- Verify: `results/sp2027_rescue/behavior_trajectory_benchmark.json`, `results/sp2027_rescue/README.md`, `scripts/sp2027_rescue_behavior_benchmark.py`
- Modify if needed: rescue README, paper rescue sections, supported-claim tests

**Interfaces:**
- Consumes: Task 4 ledger and the provider-free rescue corpus/artifacts.
- Produces: an independently reproducible rescue result with explicit split and interpretation limits.

- [x] **Step 1: Recompute split integrity.** Verify 400 held-out test sessions, zero train/test ID overlap, session-level grouping, and the recorded prefix schedule.
- [x] **Step 2: Recompute learning-curve values.** Confirm the skill-only prefix accuracy values and behavior-floor coverage from the source script and artifact.
- [x] **Step 3: Verify the self-consistency boundary.** Confirm that Supervisor and evaluation use the same risk-floor rule where applicable; label the comparison as self-consistency, not independent effectiveness.
- [x] **Step 4: Verify no provider contamination.** Confirm provider pilot artifacts are not required for the rescue result and that fallback/provider traces are not counted as independent model evidence.
- [x] **Step 5: Synchronize rescue wording.** Ensure the paper and rescue README state that this is a benchmark rescue/learning-curve result, not field validation or proof of adaptive-agent superiority.

**Pass condition:** The rescue benchmark is reproducible from its provider-free inputs and its claims remain limited to held-out classification/behavior-floor evidence.

### Task 10: Run the final automated evidence and quality gates

**Files:**
- Verify: all changed source, test, result, documentation, and generated-paper files
- Create/update: `docs/RAGIN_RELEASE_REPORT_2026-10-08.md`

**Interfaces:**
- Consumes: completed outputs from Tasks 1–9.
- Produces: a dated pass/fail/blocked report with command output summaries and residual risks.

- [x] **Step 1: Run repository integrity checks.** Run `git diff --check` and confirm no accidental whitespace or conflict markers.
- [x] **Step 2: Run static checks.** Run the project Ruff and mypy commands used by the repository, including the changed RAG engine and any changed scripts; record the observed pre-existing and changed-file findings.
- [x] **Step 3: Run the full test suite.** Run `.venv/bin/pytest -q`; record passed, failed, skipped, warnings, duration, and exact failure classes.
- [x] **Step 4: Run artifact-focused checks.** Run artifact consistency, supported claims, figure geometry, verifier red-team, and two-channel metric tests.
- [x] **Step 5: Run both retrieval modes.** Run the targeted DON tests under default hybrid and explicit BM25/sparse mode; confirm their results are labeled separately.
- [x] **Step 6: Run paper checks.** Build selected manuscript(s), run `pdfinfo`/`pdftotext`, search logs/text for undefined references and stale claims, and compare PDF hashes/page counts with the release manifest.
- [x] **Step 7: Verify repository graph/provenance freshness.** The installed graphify CLI has no `update` command; the old graph is recorded as stale/excluded rather than treated as current or deleted.
- [x] **Step 8: Write the release decision.** Set status to `READY`, `AUDIT-DRAFT-ONLY`, or `BLOCKED`, with one evidence-backed reason per failed or unavailable gate; current status is `AUDIT-DRAFT-ONLY`.

**Pass condition:** Every gate has a command, observed result, timestamp, and owner/surface; no “ready” status is issued while a required gate is blocked.

### Task 11: Final worktree and handoff review

**Files:**
- Verify: `docs/RAGIN_RELEASE_MANIFEST_2026-10-08.md`, `docs/RAGIN_RESULTS_LEDGER_2026-10-08.md`, `docs/RAGIN_RELEASE_REPORT_2026-10-08.md`, all changed files
- Review: `git status --short`, `git diff --stat`, generated-output list, secret scan output if already supported by the project

**Interfaces:**
- Consumes: all previous task outputs and the exact final Git state.
- Produces: a handoff that an independent reviewer can reproduce without guessing which files or results are authoritative.

- [x] **Step 1: Reconcile all plan checkboxes.** Every task is `completed`, `blocked`, or explicitly deferred with a reason; no silent omissions remain.
- [x] **Step 2: Review the diff by surface.** Inspect source, tests, artifacts, documentation, paper, and generated outputs separately; verify no unrelated user changes were overwritten.
- [x] **Step 3: Verify no secret/PII leakage.** Run the project-approved check over changed/released files and record any intentionally retained redacted test material.
- [x] **Step 4: Verify the handoff commands.** A fresh operator can run the documented environment setup, tests, artifact checks, and paper build from the plan/report.
- [x] **Step 5: Deliver the final decision.** Report what is ready, what remains blocked, the exact evidence, and the next smallest action; do not call the project submission-ready unless every required gate passed.

**Pass condition:** The final handoff is reproducible, bounded, and honest about every remaining missing requirement.

## Definition of Done

- [x] The current worktree baseline and artifact classifications are recorded.
- [x] The default hybrid environment is repaired and verified, or its exact external blocker is recorded; the sparse/BM25 fallback remains explicitly tested.
- [x] The JEV six/one/five contradiction is fixed and test-locked.
- [x] A results ledger maps every headline number to source, scorer, corpus, provenance, and permitted claim.
- [x] One manuscript is explicitly canonical and the companion manuscript is explicitly labeled.
- [x] README, status, appendix, rescue documentation, and paper prose agree on counts, dates, scopes, and limitations.
- [x] Active LaTeX sources rebuild into inspected PDFs with no unresolved references, missing packages, stale values, or figure/table defects.
- [x] Provider/catalog drift is either resolved with controlled provenance or remains visibly blocked; fallback-only outputs are not promoted.
- [x] Rescue benchmark split integrity and self-consistency limitations are independently rechecked.
- [x] Full tests, targeted retrieval-mode tests, static checks, artifact checks, PDF checks, and provenance checks are recorded.
- [x] Final release status is one of `READY`, `AUDIT-DRAFT-ONLY`, or `BLOCKED`, with no unsupported submission claim.

## Self-Review Record

- **Spec coverage:** Tasks 1–11 cover environment failures, result contradiction, artifact provenance, scorer definitions, rescue benchmark validity, provider drift, stale documentation, manuscript synchronization, LaTeX/PDF validation, worktree hygiene, and final release gating.
- **Step scan:** Each step names one observable action or one verification outcome; broad phrases such as “fix the issue” are replaced with exact files, values, commands, or pass conditions.
- **Type/contract consistency:** The results ledger is the shared interface for manuscript, documentation, and release decisions; Task 5 defines the canonical manuscript before Task 7 rebuilds it; Task 2 defines the test totals used by Task 6.
- **Review focus coverage:** Each five-part failure mode above has an owning task and a verification step.
- **Proportion:** The plan records decisions and checks needed by an executor without prescribing implementation bodies or inventing new scientific results.
