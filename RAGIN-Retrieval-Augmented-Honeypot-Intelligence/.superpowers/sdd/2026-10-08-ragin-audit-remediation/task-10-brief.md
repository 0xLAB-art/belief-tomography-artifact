### Task 10: Run the final automated evidence and quality gates

**Files:**
- Verify: all changed source, test, result, documentation, and generated-paper files.
- Create/update: `docs/RAGIN_RELEASE_REPORT_2026-10-08.md`.

**Required gates:**
1. Run `git diff --check` and scan changed/released text for conflict markers or accidental whitespace.
2. Run the project Ruff and mypy commands used by the repository, including changed RAG engine and changed scripts; record exact outcomes and distinguish pre-existing/environment issues.
3. Run `.venv/bin/pytest -q`; record passed, failed, skipped, warnings, duration, and exact failure classes. Do not weaken/delete tests.
4. Run artifact-focused checks: artifact consistency, supported claims, figure geometry, verifier red-team, and two-channel metric tests. Record commands and outputs.
5. Run targeted DON checks under default hybrid and explicit BM25/sparse mode; keep the modes separately labeled.
6. Rebuild or revalidate selected manuscripts, run `pdfinfo`/`pdftotext`, inspect logs for undefined references/stale claims, and compare PDF hashes/page counts with the release manifest.
7. Check graph/provenance freshness. If `graphify-out/graph.json` is used as a project map, regenerate it after the final source state using the project-supported command; otherwise record it as stale and excluded, without deleting it.
8. Write `docs/RAGIN_RELEASE_REPORT_2026-10-08.md` with dated pass/fail/blocked results, exact evidence, residual risks, and one final status: `READY`, `AUDIT-DRAFT-ONLY`, or `BLOCKED`. Given the current provider/catalog and evidence-gate state, do not claim READY unless new evidence actually clears every gate.

**Constraints:**
- Work only on Task 10; preserve unrelated dirty/session changes.
- Do not run provider campaigns, handle secrets, reset/clean/delete files, or relabel historical/provider/fallback artifacts.
- Do not dispatch further agents.
- Keep the report evidence-bounded: tests/builds prove only their stated checks, not scientific validity or venue readiness.

**Pass condition:** Every gate has a command, observed result, timestamp, and owner/surface; no `READY` status is issued while a required gate is blocked.
