### Task 6: Synchronize reproduction counts, dates, and claims in project documentation

**Files:**
- Modify: `README.md`
- Modify: `PROJECT_STATUS.md`
- Modify: `paper/sections/appendix.tex`
- Review: `results/sp2027_rescue/README.md`, `docs/SP2027_AUDIT_2026-10-03.md`

**Interfaces:**
- Consumes: Task 2 test totals, Task 4 ledger, and Task 5 manuscript decision.
- Produces: documentation that reports current commands and current observed totals without mixing historical snapshots with current validation.

- [ ] **Step 1: Replace stale test totals.** Update README and appendix references to `1,709` collected tests only after the full suite has been rerun; if the suite remains blocked, report the last verified pass/fail/skip breakdown instead of inventing a green total.
- [ ] **Step 2: Repair stale project status counts.** Replace the `1323 passed` and `17 pages` statements with dated status tied to the current artifacts and build result.
- [ ] **Step 3: Audit reproduction commands.** Ensure commands specify the intended environment, mode, corpus, output path, and whether provider access is required; mark provider-free rescue commands separately from live/provider commands.
- [ ] **Step 4: Audit claim language.** Search for “proves”, “independent”, “adaptive”, “submission-ready”, “human evaluation”, and “provider” and bound every occurrence to the evidence ledger.
- [ ] **Step 5: Run documentation checks.** Run repository tests that parse supported claims and manually compare command/output pairs against the current files.

**Pass condition:** Documentation is numerically current, dated where state can drift, and does not promise provider access, human reliability, causal effect, or venue readiness that the evidence does not support.

