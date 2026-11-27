# Task 6 Report — Synchronize reproduction counts, dates, and claims in project documentation

Date: 2026-10-08. Operator: Sisyphus (implementation worker for Task 6 only; no subagents
or reviewers dispatched, per instruction). Scope: documentation synchronization only —
`README.md`, `PROJECT_STATUS.md`, `paper/sections/appendix.tex`, and review of
`results/sp2027_rescue/README.md` / `docs/SP2027_AUDIT_2026-10-03.md`.

## Status

Complete. Documentation is numerically current (dated 2026-10-08), reproduction commands
are classified provider-free vs live with environment/mode/corpus/output paths, and
unbounded claim language ("independent", "submission-ready", "human evaluation",
"provider", "adaptive") was audited and bounded against
`docs/RAGIN_RESULTS_LEDGER_2026-10-08.md`. No result JSON, paper main/sp2027 source, PDF,
test, provider file, or session file was modified.

## Test-total ruling (required correction)

The brief's `1,709` collected total is **stale**. Tasks 2–3 added six verified tests
(Task 2: +5 `RAGIN_RAG_MODE` retrieval-mode lock tests in `tests/unit/test_don.py`;
Task 3: +1 JEV hard-subset consistency test in `tests/unit/test_artifact_consistency.py`).
The fresh, verified total used throughout is:

> **2026-10-08: `1,715 collected = 1,599 passed + 116 skipped + 0 failed`.**

Independently re-confirmed in this task: `.venv/bin/pytest --collect-only -q` →
`1715 tests collected in 2.35s`. The full-suite pass/skip/fail breakdown is Task 2's
verified rerun (`.venv/bin/pytest -q` → `1599 passed, 116 skipped, 0 failed`, reported in
`task-2-report.md` and `progress.md`). This correction is recorded in the README, the
appendix, PROJECT_STATUS §4.1, and here, so no surface quotes `1,709` as current.

## Changed files

1. **`README.md`**
   - Tests badge: `Tests-1,466 passing` → `Tests-1,715 collected`.
   - "Reproducing the paper": rewrote the command block with an explicit **environment**
     line (Python 3.10+ venv, `pip install -e ".[test]"`, corpora `data/` +
     `data/training/`, outputs to `results/`) and split commands into **provider-free**
     (offline, 0 tokens) and **live** (requires `.env` provider key) groups. Added the
     provider-free rescue command `scripts/sp2027_rescue_behavior_benchmark.py`
     (400 held-out sessions, `data/training/test.jsonl`). Refreshed the count comment to
     `1,715 collected = 1,599 passed + 116 skipped + 0 failed (2026-10-08)` and added
     output-artifact paths per command.
   - (Task 5's manuscript-status block/companion wording preserved verbatim.)

2. **`PROJECT_STATUS.md`**
   - §4.1 Test Suite Results: added a **Current (2026-10-08)** top block
     (`1715 collected = 1599 passed + 116 skipped + 0 failed`) with the reconciliation
     and an explicit "do not quote `1,709` as current" note; relabeled the `1323 passed`
     block as **Historical (2026-09-22)**.
   - §10.7 row: annotated the `1323 passed / 116 skipped` cell as "2026-09-22 era;
     current total in §4.1".
   - §4.3 HoneyGPT Competitive Benchmarks: added a **Historical (ESWA era, 2026-07)** banner
     so the legacy competitor table and the legacy `live_benchmark.json` /
     `b4_baseline_comparison.json` tables are not read as current validation; point to
     §4.1.1 (B4) and the ledger.
   - The `17 pp` / "The Intelligence Ladder" statements remain marked historical
     (header note + §7 TDSC row, inherited from Task 5); no current `17 pages` claim remains.

3. **`paper/sections/appendix.tex`**
   - `lst:repro` caption now states which steps are provider-free (1, 5–7) vs live (2–4).
   - Step 0 comment adds the corpus/output locations; `# 1,469 tests` →
     `# 1,715 collected = 1,599 passed + 116 skipped + 0 failed`.
   - Added the provider-free rescue replay command
     (`scripts/sp2027_rescue_behavior_benchmark.py`).
   - Step 2 marked "(requires provider key)", step 3 "(…; live)", step 4
     "(live authoring; single judge model)", step 5 "(offline)".
   - Bounded claim language: "independent corroboration" → "cross-run corroboration";
     "three independent evaluator runs" → "three evaluator runs" (the within-model /
     single-judge clarification already follows in Appendix C).

### Reviewed, intentionally unchanged

- `results/sp2027_rescue/README.md` — already correctly bounded (provider-free replay;
  independent result is the Chrollo learning curve; risk-floor is a self-consistency
  diagnostic, not an independent effectiveness claim). Matches ledger §5. No edit needed.
- `docs/SP2027_AUDIT_2026-10-03.md` — Task 5's 2026-10-08 addendum already marks the
  "both LaTeX builds compile" claim and the pytest counts as stale/historical and
  Task-6-owned. Kept as a dated history surface; no current counts are quoted from it.

## Verification summary

| Check | Command | Result |
|---|---|---|
| Test collection (fresh) | `.venv/bin/pytest --collect-only -q` | **1715 tests collected** |
| Supported-claim + artifact-consistency tests | `.venv/bin/pytest -q tests/unit/test_artifact_consistency.py tests/unit/test_supported_claims.py` | **44 passed** (0.30s) |
| Artifact-claim gate (audit doc gate) | `.venv/bin/python scripts/verifier_redteam_check.py` | **PASS: all 47 artifact-consistency checks hold** |
| Diff whitespace/conflict check | `git diff --check -- README.md PROJECT_STATUS.md paper/sections/appendix.tex` | clean (exit 0) |
| Reproduction scripts exist | 14/14 referenced scripts present | all OK |
| Reproduction output artifacts exist | 9/9 referenced artifacts present | all OK |
| Residual stale count scan | `grep -E "1,466\|1,469\|1,709"` on the three files | only the intentional explanatory `1,709` reconciliation sentence remains |

### Step 4 claim-language search (keyword → disposition)

- **proves** — no occurrence in README/PROJECT_STATUS/appendix (`test_supported_claims.py`
  and the ledger already gate this class); appendix uses "proofs" only for the
  deterministic C1 proof stratum (ledger §1 row 3, canonical).
- **independent** — bound: appendix "independent corroboration" → "cross-run
  corroboration"; "three independent evaluator runs" → "three evaluator runs"
  (single-judge within-model measure already stated in Appendix C). Remaining
  occurrences are ledger-backed (two independent executions = the stability pair, ledger
  §1 row 5; judge model independent of generator family = stated limitation, ledger §4).
- **adaptive** — descriptive product/rung labels only (README ladder "Adaptive
  kind-awareness"; PROJECT_STATUS component descriptions); no unbounded adaptive-superiority
  claim; the Jev rung is explicitly resolution-bounded (ledger §4).
- **submission-ready** — all occurrences are **negative** gates (README status block;
  PROJECT_STATUS header/§7.1). No affirmative claim.
- **human evaluation / human eval** — README no longer uses "human"; appendix uses
  "consensus study (live authoring; single judge model)" and Appendix C states it is
  within-model consistency, not inter-annotator agreement (ledger §9 / README consensus
  row). PROJECT_STATUS human-eval rows are dated 2026-09-22 with the single-judge
  limitation noted.
- **provider** — every occurrence is either operational (apmix wiring, provider-refusal
  availability caveat) or a "requires provider key" command marker; no provider access is
  promised. Provider-blocked artifacts stay operational-trace per ledger §6.

## Concerns

1. `docs/SP2027_AUDIT_2026-10-03.md` and `docs/SP2027_SUBMISSION_PLAN.md` remain
   untracked era docs; both still carry old counts/build claims. The audit file is
   annotated as stale/historical; the submission plan is left as an era log (not a status
   surface). If a future task wants a single authoritative status surface, these should be
   explicitly frozen or redirect to the ledger.
2. `paper/sections/appendix.tex` still references artifacts not present in the ledger §1
   (`live_benchmark_audited.json`, `stat_eval/summary.json`, `timing_fingerprint_rocauc.json`,
   `external_baseline_cowrie_guarded_rerun.json`, `cross_session_consistency_bench.json`).
   These are paper apparatus owned by Task 7 (TeX rebuild) / Task 10 (release gates); this
   task did not alter them. The `verifier_redteam_cross_family.json` index row is a
   pre-existing uncommitted change (preserved, not authored here).
3. The full `pytest -q` pass/skip/fail breakdown is reused from Task 2's verified rerun
   (the suite takes ~5 min). This task re-confirmed the *collection* total (1,715) and ran
   the documentation-parsing suites; it did not re-run the full suite, per the brief's
   allowance to report the last verified breakdown.
4. The README/appendix "provider-free" classification is command-level; `score_human_eval.py`
   is marked live because authoring the transcripts requires the gateway even though the
   final consensus fusion (`build_consensus.py`) is offline.

## Boundaries honored

Only `README.md`, `PROJECT_STATUS.md`, and `paper/sections/appendix.tex` were modified
(all explicitly in the brief's Modify list). No result JSON, paper main/sp2027 source
(`paper/main.tex`, `paper/sp2027.tex`, other `paper/sections/*`), PDF, test, provider, or
session file was changed; no existing user change was reverted, reset, cleaned, or
overwritten. `git status --short` shows only these three files added to the pre-existing
dirty set.
