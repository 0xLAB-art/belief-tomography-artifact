### Task 1: Freeze the audit baseline and classify the worktree

**Files:**
- Create: `docs/RAGIN_RELEASE_MANIFEST_2026-10-08.md`
- Inspect: `git status --short`, `git diff --stat`, `results/`, `data/sessions/`, `graphify-out/graph.json`
- Do not modify: existing session files, PDFs, results, or source code in this task

**Interfaces:**
- Consumes: current Git status, current commit SHA, existing audit document, result manifests/hashes, and file timestamps.
- Produces: a dated baseline that later tasks can compare against, including a classification of canonical, generated, historical, failed, provider-pilot, and unreviewed artifacts.

- [ ] **Step 1: Record the exact baseline.** Capture the current commit SHA, branch, Git status counts, modified paths, untracked-path classes, Python/TeX tool versions, and the status of existing manifests.
- [ ] **Step 2: Classify generated/session material without deleting it.** Mark session transcripts, PDFs, caches, old benchmark outputs, provider pilots, and rescue artifacts as `canonical`, `supporting`, `historical`, `failed`, `fallback-only`, `operational-trace`, or `unreviewed`.
- [ ] **Step 3: Record the two manuscript surfaces.** State that `paper/main.tex` is the full audit manuscript and `paper/sp2027.tex` is the shorter rescue/submission surface until a release decision changes that designation.
- [ ] **Step 4: Verify the manifest is reproducible.** Re-run the path/count/hash commands documented in the new manifest and confirm that they reproduce the recorded values without mutating the worktree.

**Pass condition:** The release manifest identifies every artifact class used by later tasks and makes no claim that an unreviewed or provider-blocked artifact is canonical evidence.

