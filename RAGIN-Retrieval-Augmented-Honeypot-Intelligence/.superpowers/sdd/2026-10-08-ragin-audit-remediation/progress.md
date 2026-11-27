# SDD ledger — plan: docs/superpowers/plans/2026-10-08-ragin-audit-remediation.md

## Execution context

- Executor: OpenCode delegated workers using the explicitly requested `opencode/fledge-alpha-free` model.
- Workspace ruling: operate in the current dirty worktree because a clean worktree would omit the existing audited source/result state; never reset, clean, push, merge, or overwrite unrelated user changes.
- Baseline before delegation: branch `main`, commit `f01a4a98d8fc0cdbf1f031d915385294675e3b1b`, 18 modified/staged-or-modified paths and 1,986 untracked paths at setup.
- Required evidence boundary: no submission-ready or scientific-validity claim follows merely from a build, test, or Number Lock result.

## Pre-flight interface scan

| Area | Producer | Consumer | Finding / ruling |
|---|---|---|---|
| Worktree classification | Task 1 manifest | Tasks 2–11 | Must classify existing dirty/generated/session files before any release decision; no deletion authorized. |
| Environment totals | Task 2 hybrid/sparse verification | Task 6 docs, Task 10 gates | Documentation may use current totals only after a fresh full-suite run; otherwise report the blocker. |
| JEV artifact | Task 3 corrected JSON/tests | Tasks 4, 6, 7, 10 | Six informative rows, one assessed/rescued Jev row, five unavailable rows must remain identical across all surfaces. |
| Results ledger | Task 4 | Tasks 5–11 | Ledger is the source of truth for headline numbers, scorer definitions, provenance, and permitted claims. |
| Manuscript choice | Task 5 | Tasks 6–11 | `paper/main.tex` and `paper/sp2027.tex` remain separate until one is explicitly selected as canonical. |
| Provider status | Task 8 | Tasks 4, 5, 7, 10 | Catalog drift/unprobed quota blocks provider-backed claims; fallback/provider pilots stay operational-trace only. |
| Rescue benchmark | Task 9 | Tasks 4–7, 10 | Held-out/provider-free learning-curve and behavior-floor evidence only; no adaptive-superiority claim. |
| Generated PDFs/graph | Task 7 | Tasks 10–11 | Rebuild/regenerate after source changes; stale PDFs/graph output cannot be treated as current. |

## Plan-text self-consistency scan

| Task | Own files vs. steps | Result |
|---|---|---|
| 1 | Creates dated release manifest and records current state | Consistent |
| 2 | Repairs environment and verifies both retrieval modes | Consistent; no source change required unless setup contract is missing |
| 3 | Corrects JEV JSON and locks it with existing/new assertions | Consistent |
| 4 | Creates results ledger from canonical artifacts and exclusions | Consistent |
| 5 | Names canonical manuscript and updates status/source-of-truth docs | Consistent |
| 6 | Synchronizes counts, dates, commands, and claim language | Consistent; depends on Task 2/4 outputs |
| 7 | Rebuilds active TeX sources and generated PDFs | Consistent; depends on Tasks 3–6 |
| 8 | Rechecks provider state without promoting blocked pilots | Consistent |
| 9 | Rechecks rescue split and bounded interpretation | Consistent |
| 10 | Runs final automated/PDF/provenance gates and writes release report | Consistent; depends on Tasks 1–9 |
| 11 | Reconciles final worktree and handoff | Consistent; final gate |

## Delegation log

### Task 1: complete

- Worker: OpenCode `opencode/fledge-alpha-free`.
- Changed: `docs/RAGIN_RELEASE_MANIFEST_2026-10-08.md`; worker report at `.superpowers/sdd/2026-10-08-ragin-audit-remediation/task-1-report.md`.
- Independent verification: manifest exists; `git diff --check -- docs/RAGIN_RELEASE_MANIFEST_2026-10-08.md` passed; report records baseline, artifact classes, toolchain, stale graph/PDF state, and provider blockers.
- Result: Task 1 complete; no source, result, session, or PDF artifact was modified.

### Task 3: complete

- Worker: OpenCode `opencode/fledge-alpha-free`.
- Changed: `results/jev_hard_subset.json` and `tests/unit/test_artifact_consistency.py`; worker report at `.superpowers/sdd/2026-10-08-ragin-audit-remediation/task-3-report.md`.
- TDD evidence: the new JEV consistency assertion failed before the wording fix because `resolution_statement` contained `stratum is empty`; after the fix, the focused suite passed.
- Independent verification: `git diff --check -- results/jev_hard_subset.json tests/unit/test_artifact_consistency.py` passed; `.venv/bin/pytest -q tests/unit/test_artifact_consistency.py tests/unit/test_supported_claims.py` → `44 passed`.
- Result: Task 3 complete. Full suite remains blocked by the known nine `test_don.py` failures from the zero-byte Hugging Face safetensors cache, which belongs to Task 2.

### Task 2: complete

- Worker: OpenCode `opencode/fledge-alpha-free`.
- Changed: `tests/unit/test_don.py` (+5 mode-contract tests); preserved the pre-existing `ragin/don/rag_engine.py` mode implementation. Repaired only the external Hugging Face blob for the pinned `all-MiniLM-L6-v2` revision; no broad cache deletion or model substitution.
- Independent verification: repaired blob size `90,868,376` bytes and SHA-256 matched the blob name; `git diff --check` passed; mode lock tests → `5 passed`; full `.venv/bin/pytest -q` → `1599 passed, 116 skipped, 34 warnings`.
- Result: Task 2 complete. Default hybrid and explicit BM25 paths are both green; the nine baseline safetensors failures are resolved.

### Task 4: complete

- Worker: OpenCode `opencode/fledge-alpha-free`.
- Changed: `docs/RAGIN_RESULTS_LEDGER_2026-10-08.md`; worker report at `.superpowers/sdd/2026-10-08-ragin-audit-remediation/task-4-report.md`.
- Independent verification: `git diff --check -- docs/RAGIN_RESULTS_LEDGER_2026-10-08.md` passed; `.venv/bin/pytest -q tests/unit/test_artifact_consistency.py tests/unit/test_supported_claims.py` → `44 passed`.
- Result: Task 4 complete. Ledger includes canonical live values, scorer/channel separation, model-coherent evidence, JEV six/one/five bounds, provider-free rescue limits, exclusions, hashes, timestamps, and regeneration commands.
- Residual caveat preserved: echo-guarded served-text technique/actor values are an offline rescore and require a future live 218-row guarded rerun for fresh campaign evidence.

### Task 5: complete

- Worker: OpenCode `opencode/fledge-alpha-free`.
- Changed: `README.md`, `PROJECT_STATUS.md`, and the untracked `docs/SP2027_AUDIT_2026-10-03.md` addendum; worker report at `.superpowers/sdd/2026-10-08-ragin-audit-remediation/task-5-report.md`.
- Decision: `paper/sp2027.tex`/`paper/sp2027.pdf` is the canonical next release/submission surface; `paper/main.tex`/`paper/main.pdf` is the full audit/extended companion. They remain separate and neither is submission-ready.
- Independent verification: `git diff --check` passed; status/source-of-truth wording and the missing `algorithm.sty` gate are present across all three docs; no paper source, PDF, result, or test file was changed.

### Ruling before Task 6

- The plan/Task-6 brief says to update documentation to `1,709` collected tests, but Tasks 2–3 added six verified tests. The fresh full-suite total is now `1,599 passed + 116 skipped = 1,715 collected`; Task 6 must use `1,715` (and the dated `1,599/116/0` breakdown), not the stale pre-change `1,709`. Cost if wrong: documentation would immediately contradict the verified suite and make later provenance checks fail.

### Task 6: complete

- Worker: OpenCode `opencode/fledge-alpha-free`.
- Changed: `README.md`, `PROJECT_STATUS.md`, `paper/sections/appendix.tex`; worker report at `.superpowers/sdd/2026-10-08-ragin-audit-remediation/task-6-report.md`.
- Independent verification: `git diff --check` passed; `.venv/bin/pytest --collect-only -q` → `1715 tests collected`; focused artifact/supported-claim tests → `44 passed`.
- Result: current totals, provider-free/live commands, corpus/output paths, historical labels, and bounded claim language are synchronized. The 1,709 figure remains only as an explicit historical reconciliation sentence.

### Task 7: complete

- Worker: OpenCode `opencode/fledge-alpha-free`; report at `.superpowers/sdd/2026-10-08-ragin-audit-remediation/task-7-report.md`.
- Changed: regenerated `paper/main.pdf` and `paper/sp2027.pdf`; updated status/provenance in `README.md`, `PROJECT_STATUS.md`, `docs/SP2027_AUDIT_2026-10-03.md`, `docs/RAGIN_RESULTS_LEDGER_2026-10-08.md`, and `docs/RAGIN_RELEASE_MANIFEST_2026-10-08.md`. No PDF was hand-edited and no `.tex` source change was needed.
- Environment: installed Debian `texlive-science`; independent `kpsewhich` resolves `algorithm.sty`, `algpseudocode.sty`, `IEEEtran.cls`, `graphicx.sty`, `booktabs.sty`, `caption.sty`, `subcaption.sty`, and `hyperref.sty`.
- Worker build evidence: `pdflatex -interaction=nonstopmode -halt-on-error` run twice per manuscript from `paper/`, all four builds exit 0. `main.pdf` is 27 pages, 442,777 bytes, SHA-256 `03c1067e184ae0e185019e6e24037cbc6d243ebd894621678bbb6eb40f708b22`; `sp2027.pdf` is 11 pages, 285,769 bytes, SHA-256 `26086903aa1882c971a97dbfdca96ca8be7acd5bda4556f4887cc29bfbb96079`.
- Independent verification: hashes, page counts, PDF text sentinels, dependency resolution, and `git diff --check` reproduced; both logs have zero undefined references/citations, duplicate labels, missing figures, and overfull boxes. Manual final-size inspection of title pages, Algorithm 1, the two-channel table, paired ablation table, and inline figures found no clipping or unreadable elements.
- Result: Task 7 complete. The fresh-build gate is cleared, but neither manuscript is submission-ready because the ledger evidence gates and provider-backed rerun blockers remain open.

### Task 8: complete

- Worker: OpenCode `opencode/fledge-alpha-free`; report at `.superpowers/sdd/2026-10-08-ragin-audit-remediation/task-8-report.md`.
- Recheck: `.venv/bin/python scripts/check_apmix_catalog.py` at `2026-10-08T06:03:31Z` returned exit 2. Catalog HTTP 200 listed only `claude-sonnet-4-6-free`; wired `deepseek-v4-flash-free` and `grok-4.7-free` were missing. Quota remained `HTTP 0`, `not_probed` because the catalog gate failed.
- Changed: the project probe refreshed `results/apmix_quota_status.json` and appended `results/apmix_probe_history.jsonl`; `results/sp2027_rescue/README.md` and `docs/RAGIN_RESULTS_LEDGER_2026-10-08.md` now carry the dated blocked-branch evidence.
- Independent verification: JSON status equals the latest history row; catalog/status/missing-model assertions passed; `git diff --check` passed; no smoke check or experiment was run, and no provider pilot was relabeled.
- Result: Task 8 complete. Provider-backed reruns remain blocked; the SP2027 rescue benchmark remains provider-free, held-out, fallback-only evidence, and unavailable/404/fallback artifacts cannot support provider comparison claims.

### Task 9: complete

- Worker: OpenCode `opencode/fledge-alpha-free`; brief and report at `.superpowers/sdd/2026-10-08-ragin-audit-remediation/task-9-brief.md` and `task-9-report.md`.
- Independent verification: 400 held-out test sessions; 1,600 train sessions; zero train/test ID overlap; 6,400 unique session/prefix/arm rows; eight prefixes with 400 sessions per arm; `len(commands_seen) == prefix_n` for every row; artifact SHA-256 `f6945dee790432583a79a06e22589d96376e3bf76470fccb4b6149e89207b338`.
- Reproduction: worker reran `scripts/sp2027_rescue_behavior_benchmark.py` to a temporary output; corpus, arm summaries, paired deltas, and all 6,400 rows matched the committed artifact exactly. The provider-free method flag is false for provider calls and field deployment.
- Interpretation: `gold_risk` matched `Supervisor._behavior_floor` on 0/400 mismatches; the paper and README correctly call this a self-consistency diagnostic, not independent effectiveness, field validation, or adaptive-agent-superiority evidence.
- Result: Task 9 complete. Rescue claims remain limited to held-out classification/behavior-floor evidence; provider pilots remain excluded/fallback-only.

### Task 10: complete

- Worker: OpenCode `opencode/fledge-alpha-free`; report created at `docs/RAGIN_RELEASE_REPORT_2026-10-08.md`.
- Passing gates: `git diff --check`; conflict-marker scan; full `.venv/bin/pytest -q` (`1599 passed, 116 skipped, 0 failed, 34 warnings`); focused artifact/claim/geometry/red-team/two-channel tests (`132 passed`); default hybrid DON (`89 passed`) and explicit BM25 DON (`89 passed`); PDF hashes/pages/log/text sentinels match the Task 7 manifest.
- Blocked/failing gates: repository Ruff has 67 pre-existing script findings and one changed-file `PT001` at `tests/unit/test_artifact_consistency.py:53`; mypy has five pre-existing errors in unmodified files, while changed `ragin/don/rag_engine.py` passes; graphify CLI has no `update` command and `graphify-out/graph.json` remains stale/excluded; provider catalog drift remains from Task 8.
- Independent verification: release report contains one final status and all required evidence strings; report diff check is clean.
- Result: Task 10 complete with final status **AUDIT-DRAFT-ONLY**. No `READY` claim is permitted while provider, static-check, and graph freshness gates remain open.

### Task 11: complete

- Delegated OpenCode Task 11 stalled in an extended wait without producing a report; the main worker completed the bounded handoff review locally and recorded this explicitly in `.superpowers/sdd/2026-10-08-ragin-audit-remediation/task-11-report.md`.
- Worktree review: branch `main`, HEAD `f01a4a98d8fc0cdbf1f031d915385294675e3b1b`, 23 modified tracked paths and 1,991 untracked paths; existing session/OpenCode/rescue/generated material preserved and classified, not deleted or promoted.
- Narrow remediation: changed test `tests/unit/test_artifact_consistency.py` Ruff `PT001` fixed from `@pytest.fixture()` to `@pytest.fixture`; focused file test -> `17 passed`; `.venv/bin/ruff check tests/unit/test_artifact_consistency.py` -> `All checks passed`.
- Security scan: `bash scripts/security_scan.sh` exit 0 with Bandit report of 30 existing code-pattern findings (20 low, 10 medium); dependency scanners unavailable; no secret/token/PII value copied into the handoff. `bandit-report.json` preserved as supporting scan output.
- Release report updated with Task 11 addendum; status remains **AUDIT-DRAFT-ONLY** because provider drift, stale graph output, pre-existing static findings, Bandit warnings, and evidence/venue-readiness limits remain.
- Result: Task 11 complete; final handoff is bounded and reproducible, with no unsupported submission-ready claim.
