### Task 5: Decide and document the canonical manuscript surface

**Files:**
- Modify: `PROJECT_STATUS.md`
- Modify: `README.md`
- Modify: `docs/SP2027_AUDIT_2026-10-03.md` only if its status is stale
- Keep synchronized: `paper/main.tex`, `paper/sp2027.tex`, `paper/main.pdf`, `paper/sp2027.pdf`

**Interfaces:**
- Consumes: Task 4 results ledger and the two existing manuscript sources.
- Produces: an explicit status decision naming the full audit manuscript, the shorter rescue manuscript, and the one surface intended for any future submission package.

- [ ] **Step 1: Compare source scopes.** List sections, experiments, appendices, figures, and result artifacts included by each manuscript; identify any result present in one but absent from the other.
- [ ] **Step 2: Select a canonical release target.** Choose one of the two sources for the next release package and label the other as a companion audit/extended version; do not merge them by implication.
- [ ] **Step 3: Update status language.** Replace stale page counts and ambiguous “paper ready” wording with dated, evidence-bounded status and the explicit fresh-build gate.
- [ ] **Step 4: Add a source-of-truth note.** State which `.tex` file controls the release PDF, which files are generated, and how the companion manuscript is maintained.
- [ ] **Step 5: Verify status consistency.** Search the repository for old page counts, old test counts, “submission-ready”, and references to the wrong manuscript surface; classify each remaining occurrence as current, historical, or to be updated.

**Pass condition:** A new reader can tell which paper is canonical, what the companion paper contains, and why neither is submission-ready until the fresh-build and evidence gates pass.

