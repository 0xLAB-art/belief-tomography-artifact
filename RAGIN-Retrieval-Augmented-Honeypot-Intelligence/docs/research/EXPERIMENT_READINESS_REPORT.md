# EXPERIMENT READINESS REPORT — RAGIN causal ablation

**Date:** 2026-10-22
**Protocol:** `docs/research/CAUSAL_ABLATION_PROTOCOL.md` (design frozen v2)
**Design freeze:** `docs/research/design_freeze_v1.json` (v3; execution lock **INCOMPLETE**)
**Config manifest:** `configs/ablation/manifest_v2.json` (v1 preserved as a prior version)
**Provider spend this phase:** **$0** (no provider calls; no AWS, JEV, paid API, or model download)
**Bottom line:** **B0 is locally executable as a native transport. B1, B2, and B3 have the required local code paths but remain blocked on the frozen generator. B4 and B5 are NOT READY.** No arm has been executed, and no B1–B3 result is measured.

> **P0 SEMANTIC ACCEPTANCE REMAINS OPEN.** Passing characterization tests does
> not complete the requested P0 criteria. The following are still unresolved:
>
> 1. The existing verifier still admits a known unsupported no-evidence
>    file/privilege claim.
> 2. Wall-clock verifier deadlines are **NOT ESTABLISHED**; the timeout test is a
>    simulated raised exception.
> 3. The true LLM model arm has **not** been measured.
> 4. Egress isolation is **application-level only**, not a network sandbox.
>
> No statement in this report should be read as fully completed P0 or scientific
> readiness. The arm configs' generator settings are **PROPOSED_NOT_ENFORCED**,
> their commands are **STARTUP_WIRING_ONLY_NOT_EXPERIMENT**, their resource fields
> are **not** cgroup enforcement, and genuine model invocation plus decoding
> compliance remain **NOT ESTABLISHED**.

---

## 0. 2026-10-23 update — supersedes sections 1–2 where they conflict

This section is the current status. Everything below it is the 2026-10-22 report and is
kept for provenance. Nothing in this update claims an arm effect; **no arm has been run
and no generative model has been invoked.**

### 0.1 What changed since 2026-10-22

| Change | Evidence |
|---|---|
| Cowrie/RAGIN prompt and cwd aligned (`~`, not `/`) via a hash-pinned `llm/protocol.py` patch mounted into the RAGIN container only | `docs/research/PERSONA_ALIGNMENT_ERRATUM_20261023.md`; `scripts/persona_prompt_patch.py` |
| Deterministic templates aligned to the strict contract (`hostname*`, `uname*`, os-release) | `ragin/hisoka/deception.py`; 5/5 `SUPPORTED` in the run below |
| Transcript contract versioned; command echo now owned by the frontend under `v2` | `docs/research/TRANSCRIPT_CONTRACT_V2.md`; `docs/research/TRANSCRIPT_CONTRACT_AUDIT.md` |
| New real loopback evidence under contract `v2` | `docs/research/persona_alignment_20261023T054559Z/` (5/5 `SUPPORTED`, `served_payload_echo_turns: []`) |

### 0.2 B0–B3 executability (verified locally, no network)

| Arm | Actual code path | Model / checkpoint availability | Retrieval config | Verification | Deps present | Missing | Real inference locally? | Constraints |
|---|---|---|---|---|---|---|---|---|
| **B0** native Cowrie | Pinned image `sha256:710f1e46…a30cd459`, `backend=shell`, driven by `scripts/prove_cowrie_persona_alignment_v1.py` (native arm) or `scripts/run_p0_loopback_ssh_trace_v2.py` | none needed | `not_applicable` | none (native handlers, no RAGIN verifier) | docker (cached, `--pull=never`), `sshpass`, loopback | Native↔pinned-identity registration in preflight (`baseline_identity_status=NOT_ESTABLISHED`); `id` supplementary-group difference (native prints primary gid only) | **n/a (no model)** | Transport/control only; never an H1 comparison |
| **B1** Cowrie + LLM | `ragin/server_v2.py --mode pipeline` → `Harness` → `Hisoka.generate_response` (model branch), Cowrie `backend=llm`, `RAGIN_RAG_MODE=none` | **No generative weights locally.** `models/` (1.7 GB) holds Laya decision checkpoints (v3–v12) + Chrollo only; HF cache (2.6 GB) holds ModernBERT, kompress-v2, Laya, MiniLM — no chat/instruct model | `none` — no index built or searched | `research_strict_v1`, fail-closed, 1.0 s deadline | torch, transformers, sentence-transformers, faiss, onnxruntime | Frozen generator identity, effective decoding enforcement, prompt/codebook freeze, allocation lock | **BLOCKED** (`UNRESOLVED_MODEL`, `BLOCKED_GENERATION_CONFIG`, `MODEL_INVOCATION_UNAVAILABLE`) | Any provider use needs explicit approval + cost estimate; `v2` contract |
| **B2** B1 + BM25 | same, `RAGIN_RAG_MODE=bm25`, corpus `data/corpus` (2 files, 25 MB) | same as B1 | BM25 implemented in `ragin/don/rag_engine.py` (no `rank_bm25` dependency); sparse-only | same | same | B1 blockers + frozen shared corpus content/document-id set (`UNRESOLVED_B2_CORPUS`, `UNRESOLVED_SHARED_CORPUS_CONTENT`, `UNRESOLVED_SHARED_DOCUMENT_IDS`) | **BLOCKED** | same as B1 |
| **B3** B1 + dense RAG | same, `RAGIN_RAG_MODE=dense`, `RAGIN_VECTOR_STORE_PATH`, `RAGIN_EMBED_MODEL` | Encoder **is** local: MiniLM snapshot cached (`~/.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2`, 384-d); strict pending store hashes exist (`data/vector_store_bench`: 22,396 docs, dim 384) | dense-only, no BM25 fallback; exact store + local model required or the arm refuses to start | same | same + faiss | Exact frozen store artifact (`RAGIN_VECTOR_STORE_PATH` unresolved), frozen embed-model directory path (`UNRESOLVED_EMBED_MODEL`), generator | **BLOCKED** (`UNRESOLVED_B3_STORE`, `UNRESOLVED_EMBED_MODEL`) | same as B1; embedding inference itself was verified offline earlier |

`B4` and `B5` remain **NOT READY** (configs `b4_rule_decision.not_ready.json`,
`b5_finetuned_laya.not_ready.json`); the v12 Laya contract mismatch is unchanged.

### 0.3 Machine-readable preflight (run this phase)

```
.venv/bin/python scripts/ablation_preflight_v1.py --env-check --generation-contract
  exit status : 2
  ready       : false
  B0          : EXECUTABLE_LOCAL_TRANSPORT_ONLY
  blockers    : 25 codes, incl. UNRESOLVED_MODEL, BLOCKED_GENERATION_CONFIG,
                MODEL_EXPOSURE_NOT_ENFORCED, RESOURCE_LIMITS_NOT_ENFORCED,
                EXECUTION_LOCK_INCOMPLETE, UNRESOLVED_B2_CORPUS, UNRESOLVED_B3_STORE,
                UNRESOLVED_EMBED_MODEL, B0_BASELINE_IDENTITY_NOT_MATCHED
```

Effective-config detail recorded by the preflight: requested `temperature=0.0`,
`top_p=1.0`, `max_tokens=512`, `seed=0`; adapter supports `temperature`/`max_tokens` only
and currently hardcodes `temperature=0.7`, `max_tokens=4096`; `seed` and `top_p` are
unsupported. A model arm cannot be declared frozen until that gap is closed.

### 0.4 Status split

**Confirmed:** B0 runs end-to-end on loopback; the RAGIN arm authenticates, serves
verified responses, and its prompt/answers match the native persona for five commands;
the contract `v2` payload contains no duplicate echo; verification is mandatory on every
LLM arm and independent of the decision layer.

**Unresolved:** `id` supplementary groups differ from native; `v2` adoption is opt-in;
transport framing is asserted end-to-end only by the persona proof, not by the closed-loop
harness; preflight B0 identity registration is not satisfied by the new observation;
`results/apmix_probe_history.jsonl` and `results/apmix_quota_status.json` are rewritten by the
systemd user timer `ragin-apmix-watch.timer` (`scripts/check_apmix_catalog.py`, twice daily
09:00/21:00 local). It appends one honest probe row per run — currently
`catalog_http: 0` / `unreachable` / `not_probed`, because `.env` points
`RAGIN_LLM_BASE_URL` at `127.0.0.1:8731`, where nothing listens. Full provenance in
`APMIX_WRITER_PROVENANCE_AUDIT.md`; a correction to this report's first draft (which called
the rows synthetic and the writer unattributed) is recorded there. `results/` is not
byte-frozen for those two paths, and manifests mask them. No experiment artifact under
`data/`, `paper/`, or the rest of `results/` moved during this phase; the timer does not
touch them (its reseed side-effect is gated on a reachable catalog).

**Blocked:** B1, B2, B3 — no local generative model, no attested invocation, corpus/store
not frozen. B4, B5 — contract not ready. Human evaluation — no completed returns.
Decoding configuration is now traceable and client-enforced (`DECODING_CONTRACT_AUDIT.md`),
but no backend has honored it yet — that is unverified, not enforced, against a provider.

### 0.5 Status table for B0–B3 (2026-10-23 runtime-provenance phase)

Columns are what the current phase asked to be distinguishable. "Decoding compliance"
means configuration-level only; no live run has confirmed a backend honored it.

| Arm | Executable status | Model availability | Retrieval readiness | Decoding compliance | Served-output observability | Remaining blockers |
|---|---|---|---|---|---|---|
| **B0** native Cowrie | **Executable (transport only)** — pinned image cached, loopback verified | n/a (no model) | n/a | n/a (native shell has no decoding) | Serving boundary + terminal capture recorded per run; framing asserted by persona proof | Preflight `baseline_identity_status=NOT_ESTABLISHED`; `id` group-line differs from RAGIN persona |
| **B1** Cowrie + LLM | **BLOCKED** | **None locally** — `models/` holds Laya/Chrollo only; HF cache has encoders, no chat model | `RAGIN_RAG_MODE=none` configured and tested | **Config layer OK** (contract validates 0.0/1.0/512/seed0, wire truth recorded, publisher emits the artifact); **backend honor UNVERIFIED** | Payload hash + returned bytes asserted closed-loop; framing by sampling only | `UNRESOLVED_MODEL`, `MODEL_INVOCATION_UNAVAILABLE`, `UNRESOLVED_PROMPT_ID`, `MODEL_EXPOSURE_NOT_ENFORCED`, `FALLBACK_NOT_DISABLED`, effective-config artifact not yet recorded in the frozen contract |
| **B2** B1 + BM25 | **BLOCKED** | same as B1 | BM25 path implemented + tested; **corpus not frozen** (`UNRESOLVED_B2_CORPUS`) | same as B1 (configs asserted identical by test) | same as B1 | B1 blockers + corpus/document-id freeze |
| **B3** B1 + dense RAG | **BLOCKED** | Generator none; **encoder local** (MiniLM cached, 384-d) | dense path implemented + tested; **exact store/embed-model dir unresolved** (`UNRESOLVED_B3_STORE`, `UNRESOLVED_EMBED_MODEL`) | same as B1 | same as B1 | B1 blockers + store + embed-model freeze |

`B4`/`B5` remain NOT READY (unchanged). Nothing above is an arm effect: no arm has run.

---

## 1. Readiness by arm

| Arm | Ready? | What exists | What is missing |
|---|---|---|---|
| **B0** native Cowrie | **YES (transport only)** | Local Cowrie image ID `sha256:710f1e46…a30cd459`; loopback binding verified; native config `configs/ablation/b0_native_cowrie.json` | Nothing for a local descriptive transport run. It is not a RAGIN arm. |
| **B1** Cowrie + LLM, retrieval off | **NO (generator)** | Explicit `RAGIN_RAG_MODE=none`; no sparse/dense index is constructed or searched; shared mandatory verifier; config `b1_no_retrieval.json` | Frozen generator identity/prompt/price; codebook; allocation; host-fiction hash. No model is served. |
| **B2** B1 + BM25 | **NO (generator)** | Explicit `RAGIN_RAG_MODE=bm25`; sparse-only construction; config `b2_bm25.json` | Same generator/codebook/allocation blockers. |
| **B3** B1 + dense RAG | **NO (store + model + generator)** | Explicit `RAGIN_RAG_MODE=dense`; `DonAdapter(vector_store_path=…)` plumbing; exact-store/local-model fail-closed validation; dense-only path; config `b3_dense.json` | Exact `index.faiss` + `documents.json`, local embedding-model directory, generator, codebook, allocation. |
| **B4** B3 + **rule-based decision** | **NOT READY** | Definition/config `b4_rule_decision.not_ready.json` | Frozen rule table and decision contract. B4 is **not** hybrid retrieval. |
| **B5** B3 + fine-tuned Laya | **NOT READY** | Blockers recorded; config `b5_finetuned_laya.not_ready.json` | v12 checkpoint is not accepted by `LayaRuntime`; v12 emits `attack/stage/severity` while the runtime consumes `evidence_state/strategy/evidence_ref`. |

The 32-session bounded pilot in the protocol has **not** been allocated or executed.
B1–B3 use the **same proposed** CPU/memory/concurrency budget
(`B1_B3_SHARED_PROPOSED_BUDGET`). The budget is metadata, not cgroup or scheduler
enforcement; dense embedding memory is not separately budgeted in this phase.

---

## 2. What changed in the code paths

### 2.1 B1 retrieval-off is now an explicit mode

`ThreatRAGEngine` accepts four explicit modes:

| Mode | Construction | Search behavior |
|---|---|---|
| `none` | No `VectorStore`, no `IntelCorpus`, no index | `hybrid_search`, `search_threat_intel`, `keyword_search` return `[]` |
| `bm25` | Sparse corpus only | BM25 only; no vector store |
| `dense` | Exact persisted store only | Dense only; no BM25 call |
| `hybrid` | Legacy default | Existing vector+BM25 RRF behavior |

`offline`/`sparse` remain aliases for `bm25`, not for `none`. Structural tests in
`tests/integration/test_ablation_retrieval_modes.py` use explicitly labelled
fakes and confirm that `none` constructs no retriever and `dense` does not call
BM25.

### 2.2 B3 dense store is plumbed and fails closed

- `DonAdapter` now accepts `vector_store_path` and passes it to
  `ThreatRAGEngine`.
- `RAGIN_RAG_MODE=dense` requires `RAGIN_VECTOR_STORE_PATH` (or the constructor
  argument), an `index.faiss`, a `documents.json`, `faiss` +
  `sentence-transformers`, and `RAGIN_EMBED_MODEL` pointing at a **local model
  directory**. A missing prerequisite raises a configuration error; it does not
  fall back to BM25.
- The exact store and model remain absent. A real dense run is still
  model/store-blocked.

### 2.3 Retrieval provenance is observed, not static

`ragin/decision_fusion_v4/evidence_export.py` no longer writes a literal
`"hybrid"` backend when no command-aware trace exists. The bundle reports the
engine's observed `effective_backend`, `requested_mode`, construction flags, and
`backend_source`. An explicit `none` arm reports `retrieval_status =
"DISABLED"` and `usable_successful_retrieval = false`; it is not mislabelled as
a successful hybrid retrieval.

The engine now separates three things that were previously conflated:

- **requested/configured mode** (`requested_mode`, `configured_mode`);
- **data-bearing backend observed after store/corpus loading**
  (`effective_backend`): `hybrid` only when dense and sparse documents are both
  > 0, `bm25` when only sparse documents exist, `dense` when only dense
  documents exist, `none` when neither exists;
- **observed query execution** (`observed_query_execution`,
  `dense_query_observed`, `dense_query_returned_documents`), updated only when a
  dense query actually runs, never from initialization alone.

An empty dense half in a configured hybrid engine is therefore labelled `bm25`
(or `none` if the sparse half is also empty), not `hybrid`. For dense mode the
validated `RAGIN_EMBED_MODEL` directory is passed explicitly to `VectorStore`
instead of relying on the module-import constant, but encoder load and embedding
inference are still **NOT VERIFIED** (`encoder_binding =
EXPLICIT_VALIDATED_MODEL_DIR_NOT_RUNTIME_VERIFIED`). Initialization is reported
as `CONFIGURED_CAPABILITY_ONLY`; it is not a measured dense experiment.
In the evidence bundle, `DISABLED` is reserved for a requested/configured `none`;
an empty configured hybrid is reported as `EMPTY` (unavailable) instead.

### 2.4 Observability and verification boundaries

- Each serving attempt now carries bounded, minimized candidate text. The
  minimizer runs **before** truncation; raw-byte SHA-256 remains the independent
  integrity value.
- The per-turn METRIC trace carries bounded served text and an actual
  `STRATEGY_UPDATE` event reference (`event_id`, event SHA-256, selected fields).
  It is not inferred from a configured default.
- Model identity remains truthful: unobserved generator identity is
  `SOURCE_DEFAULT_NOT_OBSERVED` or `CONFIGURED_NOT_OBSERVED`, with
  `runtime_model = null`. No template runtime is labelled as an observed model.
- `FictionConsistencyVerifier` still does **not** require external evidence for
  an arbitrary file/privilege claim. A characterization test records that a
  plausible ungrounded `/etc/sudoers`-style response can pass. This is a
  coverage boundary, not a grounding guarantee.
- The `TimeoutError` regression is a **simulated raised exception**, not
  wall-clock deadline enforcement. No deadline is established.

### 2.5 B1–B3 configs are proposed metadata, not executable model experiments

The B1/B2/B3 JSON files now use one proposed budget and explicitly separate
proposal from enforcement:

- Decoding fields `temperature=0, max_tokens=512, seed=0, top_p=1` are
  `PROPOSED_NOT_ENFORCED`. The current Hisoka generation path requests
  `temperature=0.7`, `max_tokens=4096` (`ragin/hisoka/deception.py:3129-3133`),
  does not expose `seed` or `top_p`, and can serve template/static fallback
  paths (`ragin/hisoka/deceiver.py`, deterministic fallback branches).
- `fallback=none` is `PROPOSED_NOT_ENFORCED`: fallback paths exist in the
  runtime and are not disabled by these config files.
- `command` is `null`; a `command_template` records non-executed wiring with
  `: "${VAR:?required}"` guards for provider/store/model variables. Its status is
  `STARTUP_WIRING_ONLY_NOT_EXPERIMENT`. It does not invoke a frozen model.
- `resources` (cpu=1, memory_mb=2048, gpu=false, same for B1–B3) are
  `PROPOSED_NOT_ENFORCED`; they are not cgroup/container limits.
- Genuine model invocation and decoding compliance are **NOT ESTABLISHED**.

B4 remains the requested rule-based decision arm and B5 remains the requested
fine-tuned Laya arm; both are `NOT_READY` with their blockers unchanged.

### 2.6 Self-endpoint guard

`_assert_provider_not_self` now applies at the CLI's actual listen port,
including the built-in `http://localhost:8080` default. Its error message does
not interpolate the URL, and provider URL logs/health payloads are stripped of
userinfo and query tokens. The check remains static equality only: DNS aliases,
container hostnames, and redirects are not detected. `create_app` callers with
no actual port are not checked.

---

## 3. What is verified now

### 3.1 Prior-pass focused tests (raw exit codes preserved)

| Command | Result | Exit |
|---|---|---|
| `pytest tests/integration/test_runtime_truth_p0_fixes.py tests/integration/test_ablation_retrieval_modes.py tests/integration/test_runtime_truth_p0.py tests/unit/test_verifier.py tests/unit/test_host_fiction.py tests/unit/test_host_fiction_wiring.py tests/unit/test_server_v2.py tests/unit/test_cycle.py tests/unit/test_metrics.py -q` | **232 passed** | 0 |
| `pytest tests/security/test_task2_verified_serving.py tests/integration/test_pipeline.py -q` | **28 passed** | 0 |

Total: **260 passed, 0 failed**. Environment: `HF_HUB_OFFLINE=1`,
`TRANSFORMERS_OFFLINE=1`.

The new or expanded coverage includes:

- explicit `none`/`bm25`/`dense`/`hybrid` construction and search separation;
- dense configuration failure for missing store/model;
- observed retrieval backend in the evidence bundle;
- redaction-before-truncation and credential/authorization forms;
- bounded candidate/served text and decision-event references;
- self-endpoint default collision plus credential-free error text;
- ungrounded-claim coverage gap and simulated verifier timeout.

### 3.1.1 Final bounded review tests (this pass)

| Command | Result | Exit |
|---|---|---|
| `pytest tests/integration/test_ablation_retrieval_modes.py tests/integration/test_runtime_truth_p0_fixes.py tests/integration/test_runtime_truth_p0.py tests/unit/test_capture_v4.py tests/unit/test_don.py::TestVectorStore tests/unit/test_don.py::TestThreatRAGEngine::test_rag_mode_unknown_value_falls_back_to_hybrid -q` | **101 passed** (35.61 s) | 0 |
| `ruff check ragin/don/rag_engine.py ragin/don/vector_store.py ragin/decision_fusion_v4/evidence_export.py tests/integration/test_ablation_retrieval_modes.py` | **All checks passed** | 0 |

This run includes the new parametrized provenance cases
(`empty-hybrid-dense-populated-sparse`, `hybrid-both-empty`), the unchanged
`test_rag_mode_unknown_value_falls_back_to_hybrid` regression, and the existing
privacy/P0/retrieval suites listed above. No model was loaded, downloaded, or
queried; no provider socket was opened.

The regression was fixed rather than excluded: an unknown `RAGIN_RAG_MODE` value
again constructs the legacy hybrid path, while `requested_mode` preserves the raw
unknown value and `configured_mode` records `hybrid`. The evidence bundle now
distinguishes an intentional `requested_mode=none` (`DISABLED`) from a configured
hybrid whose dense and sparse halves are both empty (`EMPTY`, unavailable), and a
test pins that distinction.

**Separately reported supervisor evidence (not reproduced by this pass):** an
independent supervisor run reported **269 passed in 4.78 s**, including
`tests/unit/test_capture_v4.py`. That figure is attributed to the supervisor and
is not merged into this pass's gate evidence above.

### 3.2 Static gates

| Gate | Result | vs prior Phase 0 baseline |
|---|---|---|
| `ruff check` on the 10 changed/new files | **All checks passed** | clean |
| `ruff check ragin/ tests/` | **93 errors** | prior baseline 103; 10 fewer, no new in changed files |
| `mypy ragin/ --ignore-missing-imports` | **25 errors in 8 files (132 checked)** | prior baseline 37 in 10 files; 12 fewer, no new in changed files |

The remaining ruff/mypy findings are pre-existing (for example
`restart_persistence.py` F821 and the `provider_transport.py`/`benchmark.py`
typing issues). No pre-existing failure was hidden or suppressed. The full
`ruff ragin/ tests/` and `mypy ragin/` gates were **not** rerun in the final
bounded pass; their documented debt is unchanged, and only the scoped ruff check
listed in §3.1.1 is claimed for this pass.

`graphify update .` was also run after the code changes. It completed with exit
0 using AST-only extraction (no LLM/provider call) and rebuilt `graphify-out/`
with 13,605 nodes, 27,331 edges, and 663 communities. It is not an experiment
gate and its output is not a runtime claim.

### 3.3 Observed loopback SSH trace (real transport)

Final run: `docs/research/p0_loopback_trace_20261022T200948Z/`.

| Item | Observed value |
|---|---|
| Result | **PASS** |
| Run id | `20261022T200948Z-671386` |
| Server / SSH ports | `60627` / `32885` (dynamic, 127.0.0.1) |
| Listeners (`ss -ltn`) | `127.0.0.1:60627`, `127.0.0.1:32885` only |
| Cowrie image | `sha256:710f1e4601a663ac8591f58a42b44e4cd3b7ea170c7e6cdb9e54c430a30cd459` |
| Cowrie endpoint | `tcp:32885:interface=127.0.0.1` |
| Terminal stdout | 305 bytes, sha256 `97877eea921f48d111013f95f67761bf17ec553c436a7a2be34fbd2806d41be4` |
| Event counts | 3 `attacker_input`, 3 `system_response`, 3 `verification`, 3 `metric`, 3 `response_generate`, 3 `strategy_update` |
| Verification | **3/3 passed**; all serves `GENERATED_VERIFIED` |
| Candidate / verified / served hashes | **3/3 agree per turn** |
| Terminal matching | **3/3** served texts found after their echo at distinct offsets: `36→44`, `95→99`, `212→222` |
| HTTP bridge | **3/3** `POST /v1/chat/completions` with 200 |
| Provider calls | **0** |
| Generator | deterministic strategy runtime (`RAGIN_V4_SUBSTANTIVE_DETERMINISTIC`) |
| LLM inference | **NOT ESTABLISHED** |
| Dense retrieval | **NOT USED** (`RAGIN_RAG_MODE=none`) |

The runner now writes a pre-launch manifest (`run_manifest.prelaunch.json`) with
git HEAD, dirty state, source/config hashes, image ID, ports, command list, and
environment policy **before** launch. The environment is built from an allow-list
rather than `os.environ.copy()`, so inherited provider/cloud credentials and
proxies are not passed to the server. The Cowrie container is started from the
image ID, not the mutable tag.

Prior runs are retained: `p0_loopback_trace_20261022T192721Z/` (PASS),
`…192018Z` (PASS), and `…191828Z_FAILED` (retained failure). The new
`…200948Z` run is the final run for this pass.

**What the trace establishes:** real SSH transport from a real Cowrie container
to `server_v2`, real request handling, real hash recomputation, real verifier
passage, and verbatim delivery of the served bytes to the terminal, with exact
3-command/3-event cardinality and observed decision-event references.

**What it does not establish:** model inference, attacker engagement, suspicion
dynamics, dense retrieval, or the effect of any arm.

### 3.4 Egress and isolation boundary (honest statement)

- All listeners were confirmed loopback-only.
- The container used Docker host networking because the server is bound to
  loopback only. Therefore a network-namespace egress block was **not**
  applied. Hard egress blocking would require host firewall/namespace work and
  is not claimed.
- A shared `--network none` namespace was assessed but not used: the local
  `ragin-python` image has no SSH client/sshpass, and the Cowrie image has no
  `/bin/sh` or paramiko. Injecting host binaries would require loader/library
  mounts; host firewall changes were out of bounds.
- Isolation is application-level: provider disabled, every configured inference
  endpoint points at a closed loopback port, deterministic runtime, proxy
  variables cleared, `--pull=never`.
- This prevents the trace from contacting a provider by configuration; it is
  **not** a network sandbox.

### 3.5 P0 semantic acceptance remains open

These are remaining requested P0 criteria. They are **not** completed by passing
characterization tests:

| P0 item | Status |
|---|---|
| Unsupported no-evidence file/privilege claim | **OPEN** — the existing verifier admits a known plausible ungrounded claim (characterization test records it) |
| Wall-clock verifier deadline | **NOT ESTABLISHED** — the timeout regression raises a simulated exception; no clock-based deadline is enforced |
| True LLM model arm | **NOT MEASURED** — only deterministic strategy/trace paths were observed |
| Egress isolation | **APPLICATION-LEVEL ONLY** — provider disabled and endpoints pointed at a closed loopback port; no network-namespace/firewall sandbox |
| Legacy raw session stores | **NOT CLAIMED REDACTED** — current legacy raw session stores are not asserted to be redacted by this pass |

No statement here asserts fully completed P0 or scientific readiness.

---

## 4. Prerequisite checklist before the pilot

| # | Prerequisite | Status |
|---|---|---|
| 1 | Frozen generator identity, decoding, seed, price | **MISSING** |
| 2 | B1 retrieval-off path | **DONE** (`RAGIN_RAG_MODE=none`, structural tests) |
| 3 | B3 exact store + hash + local embedding model + path plumbing | **PARTIAL**: plumbing/fail-closed done; store/model/hash missing |
| 4 | Shared mandatory verifier source hash frozen | **DONE** |
| 5 | Suspicion codebook + attacker prompts hashed | **MISSING** |
| 6 | Allocation seed/sequence hashed before first session | **MISSING** (design defined) |
| 7 | Budget cap + technical-failure stop rule | **MISSING** |
| 8 | Blinding dry run | **MISSING** |
| 9 | Holdout untouched until main-study addendum | **DONE** (no holdout used) |
| 10 | Versioned B0–B3 configs + design freeze manifest | **DONE** (`configs/ablation/`, `manifest_v2.json`, `design_freeze_v1.json` v3) |
| 11 | B4 rule table/contract | **MISSING** (NOT READY) |
| 12 | B5 checkpoint/v12 contract | **MISSING** (NOT READY) |

The execution lock remains **INCOMPLETE** because items 1, 3 (store/model), 5,
6, 7, 8, and the associated hashes are absent.

---

## 5. What is executable today

| Comparison | Executable? | Note |
|---|---|---|
| B0 vs B1 / B2 / B3 | **NO** | frozen generator missing; B3 store/model missing |
| B1 vs B2 | **NO** | frozen generator missing |
| B2 vs B3 | **NO** | frozen generator and exact dense store/model missing |
| B0 standalone (descriptive) | **YES** | loopback Cowrie; no RAGIN arm |
| Deterministic integration trace | **YES** | executed at `…200948Z`; not an arm |
| Retrieval-mode structural tests | **YES** | labelled fakes; no inference/download |
| Verifier / fail-closed / hash tests | **YES** | 260 focused tests |

This phase can truthfully claim **integration readiness of the serving,
verification, retrieval-mode, and observability paths**, not **experimental
readiness of the ablation**.

---

## 6. Spend and prohibited actions

- Provider calls: **0**. Cost: **$0**.
- Model downloads: **0**.
- AWS / JEV / paid API / external experiment provider: **not used**.
- Public binding: **not used**; all listeners loopback.
- Training: **not run**.
- Manuscript: **not edited**.
- No commit, reset, stash, checkout, clean, or history rewrite.
- No evidence deletion or rotation; `.gitignore` unchanged.
- No fabricated freeze timestamp: the config manifest v2 uses actual UTC time at
  generation; the prior v1 `frozen_utc` is preserved and labelled fabricated.
- Final additive review manifest: `docs/research/FINAL_REVIEW_MANIFEST_*.json`
  (created after the last edit; reports link to it by path, not by embedded hash).

---

## 7. Go / no-go

**Go for B0 only**, as a standalone descriptive baseline, if a local loopback run
is approved.

**No-go for B1–B3** until:

1. a generator is frozen and served (or a local model is approved with a
   recorded hardware cost);
2. the B3 exact store, local embedding model, and hashes exist (the code path is
   completed);
3. the codebook, attacker prompts, allocation seed, and budget cap are frozen;
4. the execution lock in `docs/research/design_freeze_v1.json` (v3) is complete;
5. genuine model invocation and decoding compliance are demonstrated, not
   proposed.

**No-go for B4** until the rule table/contract is frozen. **No-go for B5** until
the checkpoint and v12 contract blockers are resolved.

Any paid provider call or public listener requires explicit human approval and
is outside this phase.

## Verified smoke trace (2026-10-23)

One focused safety-gated verification was performed. The working directory ended in a not-run state because a rotated serving credential was not confirmed installed in the project's local generation-authoritative credential position prior to the provider call.

Verified without a live provider request:

- Endpoint resolved by the serving client: `https://api.apmix.ai/v1`.
- Model selected by the serving client: `claude-sonnet-4-6-free`.
- Generation contract enabled: yes.
- Contract resolution source: environment variables.
- Decoding payload the client would send: `temperature=0.0`, `max_tokens=512`, `top_p=1.0`, seed explicitly omitted, transport retries 0.

Not verified this run:

- A live provider request.
- Raw model output, verified/fallback candidate, and served client output from the real serving path.
- Independent B2 and B3 readiness.

Safety state:

- The project `.env` file is currently untracked and was not modified by this session.
- The local generation-authoritative key variable was placeholder-only at the time of the run.
- Other provider keys may still be present in the surrounding shell environment; this note records that fact without emitting values.

Evidence file: `results/solo_apmix_smoke_probe.jsonl` and `docs/research/APMIX_SMOKE_SAFETY_GATE_REPORT_2026-10-23.md`.
