# Erratum + reproduction wrapper — frozen local dense probe

**Applies to:** `docs/research/local_dense_probe_20261023T031557Z/` (immutable origin)
**This namespace:** `docs/research/local_dense_probe_20261023T031557Z_repro_v1/`
**Written (UTC):** 2026-10-23T03:38:32Z

## Defect in the origin artifact

The origin `report.md` ends with a "Reproduce" command that invokes
`docs/research/local_dense_probe_20261023T031557Z/probe.py` **in place**. Re-running it overwrites
`raw_results.json`, `preflight_manifest.json`, `network_audit.json`, `probe_stdout.txt`,
`probe_stderr.txt`, and `dense_store/`. That contradicts the artifact's frozen-evidence claim and
invalidates its own `sha256sums.txt` / `postrun_manifest.json`.

**The origin has NOT been modified or re-run.** Its 13 files verified `OK` against
`ORIGIN.sha256` at pinning time and again after the self-test below.

## Correction: use the wrapper, never the origin command

```bash
python3 docs/research/local_dense_probe_20261023T031557Z_repro_v1/reproduce.py --out /tmp/ragin_repro_<unique>
```

Guarantees enforced by `reproduce.py`:

1. `--out` is **required**; refuses if the path already exists (including a broken symlink).
2. Refuses an `--out` that is inside, equal to, or an ancestor of the origin namespace or this
   reproduction namespace — so it cannot write into evidence.
3. Verifies this namespace's `ORIGIN.sha256` against `frozen/origin_manifest.json`, verifies the
   frozen probe/fixture copies, and verifies every origin file read-only **before** any inference.
4. Copies the byte-frozen `probe.py` + fixtures into the fresh `--out` and re-hashes them there.
5. Runs the child with a sanitized, credential-free, offline environment
   (`HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, no proxies/API keys/provider vars; the driver's
   socket audit hook blocks non-loopback `connect()`).
6. Records `<out>/origin_hashes.json`, `<out>/run_status.json`, `<out>/invariant_check.json`,
   and seals the run with `<out>/result_sha256.txt` (excludes itself).
7. Preserves failures: a crashed child leaves `raw_results.json` absent, records `returncode`,
   and still seals whatever was produced.

The generated launcher pins the driver's repo root (the frozen driver derives `ROOT` from its
depth, which is wrong for an arbitrary `--out`).

## Frozen content archived here

| Path | SHA256 |
|---|---|
| `frozen/probe.py` | `f596ec2eae2d5b74bbb55e8a177fabf33e556082962ac9dda422d4070b285ed0` |
| `frozen/fixtures/corpus/documents.jsonl` | `8de2ea4c534c3f1c2782f0cd581e2698d631fd49f37eaaa2eeb0c1974bcdcfd0` |
| `frozen/fixtures/queries.json` | `49c2a24c56e446e6320718ef0f33a6ac32565f34082e89a6b60e65dd6028ffdd` |
| `ORIGIN.sha256` (byte copy of origin sums) | `246dec1b600b96e631d05c43d0b8ba8ce73f8ad6be032f459a3ae34edc9bd463` |

`frozen/origin_manifest.json` pins the origin's run identity (started 2026-10-23T03:17:19Z, git
`7d8a32ad…`, pre-fix source hashes, model weight hash `53aa5117…128d9db`) and all 13 origin file
hashes.

## Source drift disclosed

| Item | SHA256 |
|---|---|
| `ragin/don/rag_engine.py` at origin run / pre-fix snapshot | `3c12fc58b2dda62c4f54c717b38f9cbd9f143408e8da1280d840e5e75f2564ae` |
| same file after the provenance correction (below) | `ded5ede13c6804988a9136b190bf4e59f17da50aab19202046018d616054e905` |

The pre-edit file is archived byte-identically at
`snapshots/rag_engine.pre_provenance_fix.py`. A re-run therefore executes current working-tree
sources, not the exact origin source. Because the correction only changes provenance strings
after a dense query, the deterministic retrieval content should still match; the wrapper checks
that content, never raw output hashes or timings.

## Provenance correction in `ragin/don/rag_engine.py`

The origin run exposed a stale claim: after a real dense query returned 5 documents,
`retrieval_provenance.encoder_binding` still read
`EXPLICIT_VALIDATED_MODEL_DIR_NOT_RUNTIME_VERIFIED` with the note "encoder load and embedding
inference were not executed". Init-time conservatism is correct, but leaving it after observed
inference understates what happened.

Minimal fix (no retrieval behavior change): a new `_observed_dense_store_state()` inspects the
store only after `search_threat_intel` returns, and the binding is upgraded **only from evidence**:

| Observed | `encoder_binding` | `encoder_inference_claim` |
|---|---|---|
| documents returned + encoder object loaded | `LOCAL_ENCODER_RUNTIME_VERIFIED` | `OBSERVED_REAL_ENCODER_DENSE_QUERY` |
| documents returned + store initialised with no encoder | `HASH_FALLBACK_EMBEDDINGS_OBSERVED` | `OBSERVED_HASH_FALLBACK_DENSE_QUERY` |
| documents returned + store state unobservable (test double) | unchanged (conservative) | `NOT_OBSERVABLE_AT_STORE` |
| no documents returned | unchanged (conservative) | `NO_DOCUMENTS_NO_INFERENCE` |

`encoder_observed` records `store_class`, `embedder_loaded`, `embedder_class`, `dimension`,
`index_class`, `index_ntotal`, and `observability`. Fallback is never labelled as encoder
inference, and an empty result is never treated as proof that encoding ran.

Focused test: `tests/unit/test_rag_engine_dense_provenance.py` (4 tests, fakes only). Existing
retrieval tests ran offline with unique `RAGIN_SESSION_DIR` / `RAGIN_HOST_FICTION_PATH`:
**182 passed** (`test_rag_engine_dense_provenance`, `test_ablation_retrieval_modes`,
`test_retrieval_contract`, `test_serve_provenance`, `test_don`, `test_lightrag_adapter`).

## Wrapper self-test evidence (`selftest_20261023T033749Z/`)

Run at 2026-10-23T03:37:49Z into a fresh `/tmp` path, origin read-only:

- origin files checked: 13, mismatches: **0**;
- child returncode 0, wall 6.6 s, `raw_results.json` present;
- deterministic invariants: **all pass** — status `REAL_EMBEDDING_INFERENCE_OBSERVED`,
  `fallback_hash_mode=false`, `IndexFlatIP`, ntotal 12, dim 384,
  embedding-matrix SHA `965b89ea…a2df089c` (identical to origin), BM25 terms 222,
  rank-0 doc IDs identical for both arms on all 4 queries, 0 blocked connects;
- after the fix, dense provenance reports
  `encoder_binding=LOCAL_ENCODER_RUNTIME_VERIFIED`,
  `encoder_observed={store_class: VectorStore, embedder_loaded: true, embedder_class:
  SentenceTransformer, dimension: 384, index_class: IndexFlatIP, index_ntotal: 12,
  observability: OBSERVED_REAL_ENCODER}`.

An earlier self-test run failed in the **wrapper's launcher** (runpy globals copy left the driver
`ROOT` at `/`): returncode 1, `raw_results.json` absent, origin untouched. That failure is what
motivated the `__globals__` pin; it is recorded here rather than hidden, and it demonstrates the
wrapper's failure-preservation path.

## Claim boundary (unchanged)

The wrapper reproduces an **integration smoke test** on 12 synthetic documents and 4 author-derived
queries. It is not a retrieval benchmark, not B3's generative arm, not deception-effectiveness
evidence, and cannot establish H2/H3. No network, provider call, download, install, training,
or commit was performed.
