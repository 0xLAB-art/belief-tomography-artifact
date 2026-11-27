# Step 2: Working-system baseline and runtime map

Captured from `/home/elaref/Documents/research/ragin/RAGIN-Retrieval-Augmented-Honeypot-Intelligence` on 2026-10-14. This is a source and environment snapshot, not a claim that a server process was running or exercised.

## Frozen boundary

The repository was at `f0c4042c0eb2ee25854796b770ea440f0b5851b2` on branch `main`, with 5,430 Git porcelain entries at capture. These are user-owned dirty/untracked files and are preserved. `worktree_manifest.jsonl` records their paths, Git status, sizes, and SHA-256 values; the two snapshot files' own content hashes are excluded to avoid circular/stale digests. The accompanying `baseline_manifest.json` records hashes for runtime source/configuration, lockfiles, the serving retrieval corpus, host-fiction state, a supplementary MITRE STIX cache, process-level allowlisted feature variables, and the local Laya checkpoint.

The checked-in dependency lock is `uv.lock`. The project `.venv` interpreter reports the installed versions recorded in `baseline_manifest.json`; the shell's system Python is a different environment and is recorded separately. The local Laya checkpoint exists at the pinned Hugging Face revision and its SHA-256 matches the expected hash in `ragin/decision/laya_runtime.py`. The default sentence-transformer embedding model cache is also frozen there by Hugging Face revision and per-file hash; its `model.safetensors` asset is 90,868,376 bytes in this cache. These hashes establish local assets, not that either model was loaded or used by a running server. No model inference was run for this snapshot.

## Runtime request and result path

```text
POST /api/session/command
  -> session_command: JSON/session checks and session authorization
  -> asyncio.to_thread(_sandbox.handle_command, ...)
  -> Sandbox.handle_command / _handle_command_unlocked
  -> Harness.process
  -> mandatory _process_verified
      -> build session context
      -> ChrolloAdapter.classify -> classification event
      -> DonAdapter.analyze -> ThreatRAGEngine -> retrieval and evidence_bundle -> CTI event
      -> optional V4 EvidenceQualityGate/selector when decision arm is nonbaseline
      -> fiction identity/graph
      -> Hisoka/SubstantiveStrategy candidate generation
      -> strict verification -> ApprovalGateway -> accepted-only commit and serve
  -> SandboxResponse; suppress response and return 503 when required verification did not pass
```

Source anchors: `ragin/server_v2.py:321-364,729-800`; `ragin/cycle/sandbox.py:112-208`; `ragin/cycle/harness.py:450-560,924-945`; `ragin/cycle/adapters.py:150-245,309-430`.

The server initializes Chrollo, Don, the generator, a mandatory-verification Harness, and Sandbox in `_init_pipeline`. A request must carry an authorized session ID before the Sandbox route is invoked. Sandbox resumes/creates the session, increments its command count, invokes `Harness.process`, records timing, and returns only a verified response. The endpoint surfaces only response/session/count/error fields; detailed classification, CTI evidence, policy and verification traces are persisted in session events by the Harness.

Don always creates an evidence bundle on the normal adapter path. Hybrid retrieval is the code default; `RAGIN_RAG_MODE=bm25|sparse|offline` selects sparse-only retrieval. The default `RAGIN_CORPUS_PATH=data/corpus` loader reads both `data/corpus/mitre_attack.jsonl` and `data/corpus/command_aware_v2.jsonl` into its corpus index. The separate command-aware retriever is constructed only when `RAGIN_DON_RETRIEVAL_VERSION` equals `DON_COMMAND_AWARE_V2`; it reads `data/corpus/command_aware_v2.jsonl`. The baseline manifest hashes both active corpus files. It also hashes `data/mitre_stix/enterprise-attack.json` as a supplementary cache; that file is not a substitute for the serving corpus directory. `RAGIN_VECTOR_STORE_PATH` defaults to `data/vector_store`, and `RAGIN_EMBED_MODEL` defaults to `all-MiniLM-L6-v2`; both are recorded in resolved defaults. At baseline, Judge/filter flags are off, but the bundle still contains the retrieval and EvidenceQualityGate preview. Under a nonbaseline V4 arm, Harness reevaluates that bundle through the policy selector.

The direct `Harness` process methods (`process_with_supervisor` and `process_with_threat_modeling`) are not the public server route. They add supervisor/threat-model stages and are called by their own runners. `ragin/don/graph.py` is a separate corrective-RAG StateGraph around `ThreatRAGEngine`; it is not invoked by the `server_v2 -> Sandbox -> Harness` path. Evaluation scripts that construct `Harness` directly are likewise experiment paths and do not by themselves prove server-path behavior.

## Configuration resolution at capture

No allowlisted `RAGIN_*` feature override was present in the process that produced the snapshot. No live server process configuration was observed. The following is therefore the resolved **code default**, not an assertion about a deployed service:

| Concern | Server baseline resolution | Enabled/research route | Effect and boundary |
|---|---|---|---|
| Runtime mode / V4 selector | `RAGIN_RUNTIME_MODE` defaults to `RAGIN_BASELINE` | `RAGIN_V4_SUBSTANTIVE_DETERMINISTIC` or `RAGIN_V4_SUBSTANTIVE_LOGISTIC` selects the corresponding substantive strategy adapter and Harness decision arm | Server derives the arm from runtime mode and passes it explicitly. This takes precedence over `RAGIN_DECISION_ARM`, `RAGIN_V4_ENABLED`, and `RAGIN_V4_SELECTOR` in server initialization. Those resolver flags can affect direct component/Harness construction when no explicit arm is passed. V4 arms do not load Laya in Chrollo. |
| Evidence Judge | `RAGIN_EVIDENCE_JUDGE_ENABLED=0` | `1/true/yes/on` adds deterministic judge trace to Don's evidence bundle | `judge_bundle` defaults to `DeterministicEvidenceJudge`. This is a deterministic rules implementation, not an LLM/model inference. |
| Evidence filtering | `RAGIN_EVIDENCE_JUDGE_FILTERING_ENABLED=0` | `1/true/yes/on` judges and filters candidate IDs | Only `SUPPORTED` candidates passing provenance, sanitization, and conflict checks remain policy-visible. Filtering can change retrieval IDs/count before gate evaluation. |
| Laya decision | `RAGIN_LAYA_ENABLED=0`; model `english`, revision `55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851`, CPU device, and 30-second timeout are code defaults; expected checkpoint hash is recorded in the baseline manifest | Baseline arm plus enabled Laya constructs `LayaDecisionAdapter` and lazily calls the pinned local Laya runtime. `RAGIN_LAYA_EVAL_REQUIRE_REAL_MODEL=1` requires enabled model verification and fails startup on error | Laya decision is attached to Chrollo classification/session context. Hisoka reads `laya_decision` as a Jev-style signal and can use its selected response strategy to shape generation. It does not directly select served text, bypass strict verification/HITL, or commit state. The Laya scoring adapter in Evidence Judge remains disabled and raises if invoked. |
| Provider generation | `RAGIN_PROVIDER_ENABLED` unset/off, so `HisokaAdapter` | Explicit provider enablement in baseline mode selects authenticated `ProviderTransportAdapter` | Nonbaseline V4 mode uses `SubstantiveStrategyAdapter` instead of either baseline generator branch. Secrets were not read or recorded. |
| Retrieval backend | `RAGIN_RAG_MODE=hybrid`; `RAGIN_CORPUS_PATH=data/corpus`; `RAGIN_VECTOR_STORE_PATH=data/vector_store`; embedding model `all-MiniLM-L6-v2`; `DON_COMMAND_AWARE_V2` opt-in absent by default | Sparse-only mode uses BM25; exact V2 version enables command-aware retriever | Both files loaded from `data/corpus` and the embedding checkpoint's cached revision/assets are hashed in `baseline_manifest.json`. The default vector-store directory does not exist at capture, so the server builds its index in memory from the loaded corpus. Current in-process overrides are empty. |

## Result surfaces and claim boundaries

The public API response is the served response, while session-event traces carry intermediate predictions, retrieval/evidence, policy decisions, verifier outcomes, and commit/serve details. These are distinct outputs and should not be merged into one “result” field when evaluating the paper. Relevant event sources include `chrollo`, `don`, `v4-policy`, `verified-serving`, and `sandbox`. For a failed mandatory verification, Sandbox returns no response body and the endpoint responds with a 503 error.

The Laya decision contract is `ragin.laya_decision_v2.decision_event.v2`. Its pinned local runtime and checkpoint availability establish executable prerequisites only. They do not establish that inference occurred in a particular experiment or server process. The Evidence Judge `LayaScoringAdapter` is a separate placeholder (`enabled=False`, `calibrated=False`) and must not be represented as Laya model execution.

## Audit findings and prior-doc drift

- `docs/laya_integration/ACTIVE_RUNTIME_WIRING.md` describes the older advisory `laya_assessment` wiring and says the Harness does not change. Current `ragin/cycle/adapters.py` attaches `laya_decision` and `laya_assessment`; current Hisoka code consumes the decision signal. The old document is historical and must not be used as the current call-path authority.
- Server mode resolution pins the decision arm from `RAGIN_RUNTIME_MODE`, while `resolve_arm()` also supports `RAGIN_DECISION_ARM` and V4 flags for direct construction. A runner using a different constructor path can therefore resolve a different arm than the API server under the same environment.
- Empty process allowlisted environment means only that this snapshot process had no explicit values. Local dotenv files such as `.env` and `.env.field` and secrets were not read. `docker-compose.field.yml` references `.env.field`, so a separately launched field container may have a different environment.
- The hash manifest freezes the currently dirty source/results/data tree as it existed at capture. It does not make the artifacts scientifically valid, promote exploratory outputs, or supersede any prior freeze.

## Files

- `baseline_manifest.json`: revision, dirty-entry count, critical source/data/config hashes, Python environments, allowlisted feature values, and checkpoint availability/hash.
- `worktree_manifest.jsonl`: path-level Git status, file size and SHA-256 for current dirty/untracked paths. The manifest's self-entry is present without a content hash because that hash would be self-referential.
- `scripts/freeze_working_baseline.py`: rerunnable, additive snapshot generator. It writes only the two snapshot files and does not change tracked project data or clean the worktree.
