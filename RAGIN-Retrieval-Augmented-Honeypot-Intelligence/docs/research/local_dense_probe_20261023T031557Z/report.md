# Local dense-arm offline probe — SYNTHETIC_DEVELOPMENT integration only

**Artifact root:** `docs/research/local_dense_probe_20261023T031557Z/`
**Run (UTC):** started 2026-10-23T03:17:19Z, finished 2026-10-23T03:17:27Z
**Host:** Intel i7-9850H, 12 logical CPUs, Linux 7.0.0-38-generic, CPU-only (not GPU)
**Git:** `7d8a32aded7f4d168015aaa7f648f3367d3edad1`, tree dirty (3,042 pre-existing entries, concurrent peer edits). This probe edited no source, config, test, manuscript, or existing result file.
**Status:** `REAL_EMBEDDING_INFERENCE_OBSERVED` — the existing dense arm loaded the cached MiniLM encoder and FAISS and executed real embedding inference on a synthetic development corpus. **This is a B3 retrieval-integration fact only.**

## Bottom line

| Claim | Status |
|---|---|
| Cached `sentence-transformers/all-MiniLM-L6-v2` weights/config/tokenizer are complete and loadable offline | **ESTABLISHED** |
| `.venv` has `faiss` + `sentence-transformers`; dense `VectorStore` took the **real encoder path**, not the hash-vector fallback | **ESTABLISHED** (observed) |
| Real embedding inference ran on 12 synthetic docs + 4 fixed queries; FAISS `IndexFlatIP`, dim 384, ntotal 12 | **ESTABLISHED** (observed) |
| Native BM25 and dense returned ranked hits over the same canonical corpus at `top_k=5` | **ESTABLISHED** (observed, n=4 queries) |
| B3 generative arm executes a local LLM | **NOT ESTABLISHED** — no generative model was loaded or called here; unchanged from the inventory |
| H2 / H3 (or any retrieval-quality / deception-effectiveness hypothesis) | **NOT ADDRESSED** — 12 author-written docs, 4 author-derived queries, no labels, no benchmark |
| Final evaluation index / data freeze | **NO** — throwaway development fixture inside this artifact directory |

## Prerequisites (actually checked, offline)

Environment for the probe: `env -i` with only `HOME`, `PATH`, the two offline flags, and thread/telemetry controls. No API keys, no proxy variables, no cloud-provider variables inherited. `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1`.

| Interpreter | numpy | torch | faiss | sentence-transformers | transformers | sklearn |
|---|---|---|---|---|---|---|
| `.venv/bin/python` 3.12.3 | 2.5.3 | 2.14.0+cpu | **1.15.0** | **6.0.1** | 5.17.0 | 1.9.1 |
| `.venv-gpu/bin/python` 3.12.3 | 2.5.4 | 2.11.0+cu128 | **missing** | **missing** | 5.20.1 | missing |

`.venv-gpu` **cannot** run the dense arm as installed (no `faiss`, no `sentence_transformers`). The probe therefore used `.venv` on CPU. No package was installed; no download was attempted.

Model cache: `~/.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2/snapshots/1110a243fdf4706b3f48f1d95db1a4f5529b4d41` (88 MB, all symlinks resolve to local blobs):

| File | SHA256 |
|---|---|
| `model.safetensors` (90,868,376 B) | `53aa51172d142c89d9012cce15ae4d6cc0ca6895895114379cacb4fab128d9db` |
| `tokenizer.json` | `be50c3628f2bf5bb5e3a7f17b1f74611b2561a3a27eeab05e5aa30f411572037` |
| `vocab.txt` | `07eced375cec144d27c900241f3e339478dec958f92fddbc551f295c992038a3` |
| `config.json` | `953f9c0d463486b10a6871cc2fd59f223b2c70184f49815e7efbcab5d8908b41` |

Config: `BertModel`, hidden 384, 6 layers, 22,713,216 parameters, `sentence_bert_config.max_seq_length=256`, tokenizer `BertTokenizer`. Full per-file hashes are in `preflight_manifest.json`, which was written **before** the encoder was loaded.

## What was executed

1. Preflight froze fixture, model-file, tokenizer-file, and source-file SHA256s plus git HEAD/dirty digest (`preflight_manifest.json`).
2. `VectorStore(model_ref=<local snapshot dir>)` → `_ensure_initialized()` loaded `SentenceTransformer` and created `faiss.IndexFlatIP(384)`; 12 docs added and persisted to `dense_store/`.
3. The **native** BM25 arm (`ThreatRAGEngine`, `RAGIN_RAG_MODE=bm25`) indexed the identical 12 documents (222 terms, avg doc length 24.5).
4. The **existing dense-only engine** (`RAGIN_RAG_MODE=dense`) reloaded the persisted store and served the queries through `search_threat_intel`.
5. A socket audit hook blocked and counted non-loopback `connect()` calls; **0 attempted, 0 blocked** (`network_audit.json` = `[]`).

### Verification that this was real inference, not the fallback

| Check | Observed |
|---|---|
| `store._embedder` | `SentenceTransformer` (not `None`) |
| `fallback_hash_mode` | `false` |
| encoder class / dim / max_seq | `BertModel` / 384 / 256 |
| `auto_model.name_or_path` | the local snapshot directory |
| FAISS index | `IndexFlatIP`, `ntotal=12`, `d=384` |
| embedding matrix | shape `[12, 384]`, SHA256 `965b89eaa39aefb0a8c59abf1911682642646f6a2218178be2b3b550a2df089c` |
| row L2 norms | 1.0 – 1.0000001 (normalized) |
| first two rows identical | `false` |
| cosine to the `RandomState(42)` hash-fallback vector for doc 1 | **-0.044** (unrelated, as expected of a real encoder) |

Engine provenance independently recorded `observed_query_execution=DENSE_QUERY_EXECUTED`, `dense_query_returned_documents=5`, `effective_backend=dense`.

> One inconsistency worth recording: the engine's init-time provenance string still says `encoder_binding=EXPLICIT_VALIDATED_MODEL_DIR_NOT_RUNTIME_VERIFIED` with the note "encoder load and embedding inference were not executed". That string is a conservative static label captured at construction; it is **stale/overly narrow** for this run, because the same process then loaded the encoder (`embedder_loaded=true`) and executed real queries. It should not be read as a denial of observed inference, nor as proof of it; the proof is the section above.

## Measured results (single run, CPU, `top_k=5`)

Identical corpus, identical queries. Scores are the arms' native scores (dense = cosine via inner product on normalized vectors; BM25 = Okapi BM25 with title boost). No tuning, threshold, or query rewriting.

| Query | Dense rank-0 | Dense score | BM25 rank-0 | BM25 score | Dense latency | BM25 latency |
|---|---|---|---|---|---|---|
| q1 sessions revoked after role change | `syn-011` | 0.670451 | `syn-011` | 4.615692 | 9.548 ms | 0.035 ms |
| q2 harbor certificates renew | `syn-007` | 0.926047 | `syn-007` | 15.018132 | 7.212 ms | 0.035 ms |
| q3 kestrel queues pending jobs | `syn-003` | 0.792819 | `syn-003` | 12.372122 | 8.493 ms | 0.039 ms |
| q4 configuration drift vs repository | `syn-010` | 0.557903 | `syn-010` | 11.242506 | 7.454 ms | 0.047 ms |

Setup costs: encoder load + index construction **3,594.163 ms** (one-time, includes `sentence-transformers` import); embedding 12 docs via `add_documents` **97.932 ms**; a separate fingerprint re-encode **62.099 ms**; dense-engine store reload **68.730 ms**; BM25 index build **0.668 ms**.

Ranked doc IDs at `top_k=5` (dense always returned 5; BM25 returns only term-overlapping candidates, so it returned 1–3 and the `@5` **sets are asymmetric**):

| Query | Dense top-5 doc IDs | BM25 returned doc IDs |
|---|---|---|
| q1 | `syn-011, syn-004, syn-001, syn-009, syn-007` | `syn-011, syn-004` |
| q2 | `syn-007, syn-004, syn-001, syn-011, syn-005` | `syn-007` |
| q3 | `syn-003, syn-009, syn-012, syn-008, syn-011` | `syn-003, syn-009` |
| q4 | `syn-010, syn-008, syn-012, syn-001, syn-006` | `syn-010, syn-001, syn-012` |

Full unrounded scores and timings are in the frozen `raw_results.json` (SHA256 `8b771038…b40c5cb`), hashed by `postrun_manifest.json` before this narrative was written.

## Honest interpretation

- Both arms put the intended document first on all four queries. That is a **smoke test only**: the same author wrote the docs and the queries, each query paraphrases one document, and there are no relevance labels or distractors. It is not precision/recall, not Recall@k, and not evidence that one arm beats the other.
- The `@5` comparison is structurally unequal: BM25's candidate set is documents sharing at least one non-stopword token, so returning fewer than `k` results is expected behavior, not a bug and not a miss to be scored as one.
- Latencies are one cold-ish pass over 12 documents on a shared laptop. Dense first query (9.5 ms) includes warm-up; steady state was 7.2–8.5 ms. BM25 at 0.035–0.047 ms is a dictionary lookup over 222 terms. These numbers do not transfer to a real ATT&CK-scale corpus or a production host. No repeated trials, no confidence intervals.
- No threshold, weight, `top_k`, corpus, or query was tuned. Nothing was selected after seeing results.
- BM25 costs 0.668 ms to build; dense costs 3.6 s and 88 MB of weights. That is a capability/cost fact, not a quality verdict.

## Claim boundary

**Usable for:** exercising B3 **integration** — proving the dense channel can load the cached encoder, embed, persist, reload, and return FAISS hits alongside BM25 on the same small corpus. It can serve as a ≤12-doc development index to wire code paths and catch fallback/regression errors.

**Not usable for / does not establish:**
- a scientific retrieval benchmark, a final evaluation index, or a data freeze;
- H2 or H3, or any retrieval-quality, hybrid-fusion, or deception-effectiveness claim;
- a true generative arm (B3's generator side remains `NOT ESTABLISHED` from the inventory — no local generative weights were loaded or called);
- any claim about the real ATT&CK corpus, real attacker sessions, or production latency.

If a later pass needs a real evaluation index, it must be rebuilt from the frozen evaluation corpus with its own manifest, not from these 12 synthetic documents.

## Cost and network

- **Provider spend: $0.00.** No provider, cloud, Ollama, or gateway endpoint was contacted. `GatewayClient` was constructed with `api_key=""` and `http://127.0.0.1:9`; it performs no I/O at construction and no chat call was made.
- Socket audit: 0 loopback connects, 0 blocked non-loopback connects, 0 DNS lookups recorded.
- Local CPU/RAM only; no GPU process; no training; no package install; no model download.
- The two env names flagged by the credential-pattern scan (`HF_HUB_DISABLE_IMPLICIT_TOKEN`, `TOKENIZERS_PARALLELISM`) are probe-set offline/threading flags, not credentials; only key **names** were recorded, never values. No secret or raw attacker record was read.

## Artifacts

| File | Purpose |
|---|---|
| `probe.py` | Archived probe driver (read-only over repo modules) |
| `fixtures/corpus/documents.jsonl` | 12 `SYNTHETIC_DEVELOPMENT` docs, frozen before inference |
| `fixtures/queries.json` | 4 fixed queries, `top_k=5`, frozen before inference |
| `preflight_manifest.json` | Fixture/model/tokenizer/source hashes + git state, written pre-inference |
| `raw_results.json` | Frozen raw measurements (no post-hoc edits) |
| `network_audit.json` | Audit-hook events (`[]`) |
| `probe_stdout.txt`, `probe_stderr.txt` | Raw run output (stderr contains a benign `FutureWarning` about `get_sentence_embedding_dimension`) |
| `dense_store/` | Persisted 12-doc FAISS store (`index.faiss`, `documents.json`, `meta.json`) |
| `postrun_manifest.json` | SHA256 of raw outputs and store |
| `sha256sums.txt` | SHA256 of every artifact except itself |

Reproduce (offline, CPU): from repo root,

```bash
timeout 300 env -i HOME="$HOME" PATH="/usr/bin:/bin" PYTHONPATH="$PWD" \
  PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  HF_HUB_DISABLE_TELEMETRY=1 HF_HUB_DISABLE_IMPLICIT_TOKEN=1 \
  TOKENIZERS_PARALLELISM=false OMP_NUM_THREADS=4 \
  .venv/bin/python docs/research/local_dense_probe_20261023T031557Z/probe.py
```

Re-running overwrites the artifact's raw outputs; compare against `postrun_manifest.json` to detect drift.

**STOP.** Nothing outside this new artifact directory was modified; no commit was made.
