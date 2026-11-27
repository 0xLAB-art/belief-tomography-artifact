### Task 11: Final worktree and handoff review

**Files:**
- Verify: `docs/RAGIN_RELEASE_MANIFEST_2026-10-08.md`, `docs/RAGIN_RESULTS_LEDGER_2026-10-08.md`, `docs/RAGIN_RELEASE_REPORT_2026-10-08.md`, all Task 1–10 reports, and all changed/released files.
- Review: `git status --short`, `git diff --stat`, generated-output list, and project-approved secret/PII scan output.

**Required work:**
1. Reconcile every plan checkbox and execution-ledger task as complete, blocked, or explicitly deferred with a reason; no silent omissions.
2. Review the diff by surface: source, tests, results, documentation, paper, generated outputs, session/OpenCode material; verify unrelated user changes were not overwritten.
3. Run the project-approved secret/PII check over changed/released files if available. Record only redacted findings and classify intentionally retained test/session material; never copy secrets/tokens into the report.
4. Verify the handoff commands: environment setup, current full test total, focused artifact checks, retrieval modes, rescue reproduction, provider status check, and paper build. Confirm paths and status wording are reproducible.
5. Check release-report consistency with the final worktree and preserve the final decision `AUDIT-DRAFT-ONLY` unless every required gate is genuinely cleared. Do not call the project submission-ready.

**Narrow remediation allowed:** If `tests/unit/test_artifact_consistency.py:53` still has the one changed-file Ruff `PT001` style error, replace only `@pytest.fixture()` with `@pytest.fixture`, rerun that focused test and changed-file Ruff, and update the release report/ledger with the result. Do not modify pre-existing lint/mypy issues or change semantics.

**Constraints:**
- Work only on Task 11; preserve unrelated dirty/session changes.
- No reset, clean, delete, commit, push, provider campaign, credential handling, or relabeling of historical/provider/fallback artifacts.
- Do not dispatch further agents.
- Create `.superpowers/sdd/2026-10-08-ragin-audit-remediation/task-11-report.md` with exact status counts, surfaces reviewed, scan commands/results, command reproducibility, residual risks, and the final decision.

**Pass condition:** An independent operator can reproduce the documented audit-draft state without guessing which artifacts are authoritative, and every remaining blocker is explicit.
