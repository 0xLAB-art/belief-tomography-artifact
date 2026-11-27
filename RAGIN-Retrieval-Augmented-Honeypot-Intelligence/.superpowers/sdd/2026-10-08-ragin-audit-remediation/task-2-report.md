# Task 2 Report — Repair and verify the default ML execution environment

## Status

Complete. The single zero-byte `all-MiniLM-L6-v2` `model.safetensors` artifact was
reacquired through the supported Hugging Face hub path (not deleted broadly, not
switched to a different model, default retrieval mode unchanged). The default hybrid
path now runs without the safetensors error, the explicit sparse path remains green and
semantically distinct, and the full suite is green.

## Changed files / cache

### Repository (only one file changed by this task)

- `tests/unit/test_don.py` — **+21 lines**, 5 new tests locking the retrieval-mode
  contract (default hybrid vs explicit sparse). Diff stat: `1 file changed, 21 insertions(+)`.
  - `test_rag_mode_default_selects_hybrid_path` (unset → `_vector_store is not None`)
  - `test_rag_mode_sparse_selects_bm25_path` parametrized over `bm25`, `sparse`, `offline`
    (`_vector_store is None`; dense search returns `[]`; sparse `hybrid_search` still returns a list)
  - `test_rag_mode_unknown_value_falls_back_to_hybrid` (unknown value must not disable retrieval)

### Preserved, untouched (pre-existing user change)

- `ragin/don/rag_engine.py` — already modified in the worktree before this task; it
  implements `RAGIN_RAG_MODE` (`bm25`/`sparse`/`offline` → sparse, default → hybrid).
  Not edited by this task. Diff stat unchanged (`git diff` shows only the pre-existing hunk).

### Environment cache (outside the repository)

- HF cache blob reacquired:
  `~/.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2/blobs/53aa51172d142c89d9012cce15ae4d6cc0ca6895895114379cacb4fab128d9db`
  - before: `0` bytes, mtime `2026-10-06 19:32`
  - after: `90,868,376` bytes; `sha256 == 53aa5117…28d9db` (matches the blob filename and
    the hub's `x-linked-etag`); all snapshot symlink targets resolve
- Snapshot revision: `1110a243fdf4706b3f48f1d95db1a4f5529b4d41` (`refs/main`), unchanged.
- No dependency, configuration, or setup-documentation file required a change; the default
  mode was not altered.

## Diagnosis (Step 1)

- Snapshot entry
  `snapshots/1110a243…/model.safetensors -> ../../blobs/53aa51172d142c89d9012cce15ae4d6cc0ca6895895114379cacb4fab128d9db`
  (symlink intact; the target blob was the sole zero-byte file; all other blobs intact).
- Model identifier: `all-MiniLM-L6-v2` (`RAGIN_EMBED_MODEL` default in
  `ragin/don/vector_store.py`), loaded by `SentenceTransformer` inside
  `VectorStore._ensure_initialized`.
- Reproduced failure (default hybrid, pre-repair):
  `safetensors._safetensors_rust.SafetensorError: Error while deserializing header: header too small`
  raised from `transformers/modeling_utils.py:343` via `safe_open(checkpoint_path)`.
  Pre-repair focused run: `tests/unit/test_don.py -k TestVectorStore` → **6 failed, 1 passed**.
- Reacquisition was reachable: `HEAD https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/resolve/main/model.safetensors`
  returned `302`, `x-linked-size: 90868376`, `x-linked-etag: "53aa51172d142c89d9012cce15ae4d6cc0ca6895895114379cacb4fab128d9db"`.

## Repair (Step 2)

Reacquired only the identified artifact through the supported hub path, pinned to the
existing snapshot revision:

```
.venv/bin/python -c "from huggingface_hub import hf_hub_download; hf_hub_download('sentence-transformers/all-MiniLM-L6-v2', 'model.safetensors', revision='1110a243fdf4706b3f48f1d95db1a4f5529b4d41', force_download=True)"
```

No broad cache deletion, no model substitution, no change to the default retrieval mode.
Post-repair integrity: size `90868376`, `sha256 == 53aa5117…28d9db`.

## Path coverage (Step 3)

The existing suite did **not** pin the `RAGIN_RAG_MODE` contract (it appeared only in
`ragin/don/rag_engine.py` and docs). A lock test was added to `tests/unit/test_don.py`.

TDD note: strict red→green was not possible because the production implementation
pre-existed as a preserved user change. Discriminating power was instead proven by loading
the **committed (HEAD) pre-change** `rag_engine.py` as an alternate module (no repo file
modified) and running the sparse assertion against it:

```
HEAD engine with RAGIN_RAG_MODE=bm25 -> _vector_store is None? False
=> HEAD would FAIL the new sparse lock test
```

The current working-tree engine passes the same assertion.

## Verification summary (Steps 4–5)

| Check | Command | Result |
|---|---|---|
| New mode-contract tests | `.venv/bin/pytest -q tests/unit/test_don.py -k rag_mode` | **5 passed**, 84 deselected (4.47s) |
| Focused DON, default hybrid | `.venv/bin/pytest -q tests/unit/test_don.py` | **89 passed**, 6 warnings (200.25s) |
| Focused DON, sparse | `RAGIN_RAG_MODE=bm25 .venv/bin/pytest -q tests/unit/test_don.py` | **89 passed**, 6 warnings (136.15s) |
| Full suite, default hybrid | `.venv/bin/pytest -q` | **1599 passed, 116 skipped, 0 failed**, 34 warnings (300.88s) |

- Baseline reconciliation: prior recorded state was `9 failed, 1585 passed, 116 skipped`
  (all nine `test_don.py` failures on the zero-byte blob, per Task 3). 9 recovered + 5 new
  tests = 1599 passed. The nine failure classes are gone.
- Static checks: `.venv/bin/ruff check tests/unit/test_don.py` → *All checks passed!*;
  LSP diagnostics on the changed file → *No diagnostics found*;
  `git diff --check -- tests/unit/test_don.py` → clean.
- Semantic distinctness (ad-hoc evidence, default/hybrid): `VectorStore.search("spearphishing email")`
  returns real dense hit `d1` (`score=0.3478`); in `RAGIN_RAG_MODE=sparse` the engine sets
  `_vector_store is None` and `search_threat_intel(...)` returns `[]`.
- Offline robustness of the repaired default path
  (`HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1`): dense search returns
  `[('d1', 0.6487)]` — the default hybrid path loads entirely from the repaired local
  snapshot with no network.

## Concerns

- The repair is an environment-state change (HF cache outside Git); it cannot be
  reconstructed from the repository alone. The exact reacquisition command and pinned
  revision are recorded above for reproducibility.
- `VectorStore._ensure_initialized` catches only `ImportError`. A future corrupt/missing
  blob raises `SafetensorError` and crashes the caller; there is no graceful degradation
  and no integrity check on load. This is pre-existing behavior and out of scope here —
  flag it for Task 10 as a robustness gap (a load-time size/hash check would fail fast and
  clear).
- Default `RAGIN_EMBED_MODEL` is the bare name `all-MiniLM-L6-v2`; `sentence-transformers`
  resolves it to the `sentence-transformers/all-MiniLM-L6-v2` repo. Fine, but pinning the
  fully-qualified id (and, optionally, a revision) in configuration would make the
  environment dependency explicit.
- The hub emitted an unauthenticated-request warning during first load; rate limits are
  ample and the cached snapshot makes subsequent offline loads clean.
- No README, `PROJECT_STATUS.md`, paper, results, or session file was touched. No secret,
  PII, or unrelated user change was altered.
