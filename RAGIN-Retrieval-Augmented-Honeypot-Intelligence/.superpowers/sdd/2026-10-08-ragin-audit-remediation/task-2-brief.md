### Task 2: Repair and verify the default ML execution environment

**Files:**
- Modify only as required: dependency/configuration files and environment setup documentation
- Verify: `.venv/`, Hugging Face cache for `all-MiniLM-L6-v2`, `ragin/don/rag_engine.py`, `tests/unit/test_don.py`
- Test: `tests/unit/test_don.py` and the full pytest suite

**Interfaces:**
- Consumes: Task 1 baseline and the current zero-byte `model.safetensors` failure evidence.
- Produces: a working default hybrid path plus an explicitly documented sparse/BM25 fallback; both paths remain testable and semantically distinct.

- [ ] **Step 1: Diagnose the cache without broad deletion.** Verify the snapshot symlink, target size, model identifier/revision, and whether the configured environment can reacquire the model. Record the exact failure if reacquisition is unavailable.
- [ ] **Step 2: Repair only the identified model artifact or dependency.** Restore a complete pinned model snapshot through the project’s supported setup path; if network/model access is unavailable, leave the environment unchanged and record the blocker rather than silently switching the default.
- [ ] **Step 3: Add/retain explicit path coverage.** Ensure `RAGIN_RAG_MODE=bm25`/`sparse`/`offline` selects the sparse path and the default continues to select hybrid retrieval; add a test only if the existing suite does not pin this contract.
- [ ] **Step 4: Run the focused test matrix.** Run the affected DON tests once with the repaired default hybrid path and once with `RAGIN_RAG_MODE=bm25`.
- [ ] **Step 5: Run the full suite.** Run `.venv/bin/pytest -q`; distinguish genuine code failures from environment/setup failures and preserve all failures in the release report.

**Pass condition:** The default hybrid path runs without the zero-byte model error, the explicit sparse path still passes, and the full suite is either green or has a newly evidenced, narrowly scoped blocker documented in Task 10.

