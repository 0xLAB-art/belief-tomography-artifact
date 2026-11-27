# RUNTIME TRUTH AUDIT — RAGIN

**Audit date:** 2026-10-22
**Auditor:** single agent, `opencode/deepseek-v4.1-flash-free`
**HEAD at audit:** `7d8a32aded7f4d168015aaa7f648f3367d3edad1` (branch `main`)
**Phase:** 0 (forensic audit + pre-change baseline freeze), followed by a **bounded P0 fix pass** (§14) and one observed loopback SSH trace (§8.3, §14.4).
**Working tree state:** dirty — 24 tracked modifications, 2,976 untracked entries at audit start. No commit, reset, stash, checkout, clean, or history rewrite was executed. The 5 modified `data/sessions/*.jsonl` and 2 modified `results/*` files were never opened for content, copied, deleted, or re-labelled.

> **Revision note (v2).** This revision corrects several v1 inferences explicitly:
> 1. **JEV** has **zero treatment exposure** in the available A/B, so its effect is **NON-ESTIMABLE / NOT ESTABLISHED**. No "no routing value", "helps = REFUTED", or "does not hurt = supported" statement survives.
> 2. The empty dense store is **current source-path evidence only**. No historical campaign is claimed to have been BM25-only without its exact run config and raw retrieval trace. Historical result files are **not** relabelled or modified.
> 3. **B5 is a proposed arm in the user's protocol**, not a historical artifact. Its absence is expected and is not a false claim. B5 is **NOT READY** because only the upstream Laya checkpoint loads and the v12 contract is incompatible. No attribution of 0.880 to B5 was made and none is invented here.
> 4. **HTTP 503 is valid fail-closed behavior.** The defect was the docstring, not the status code. No synthetic unverified 200 is proposed. Cowrie's reaction to a 503 was not observed and is not asserted.
> 5. **Local SSH end-to-end does not require an external provider or a public listener.** It was executed (§8.3). Before it was executed, source reads and mock tests established only their corresponding internal boundaries — never full terminal end-to-end integrity.
> 6. The **human reference protocol exists** and is frozen pre-annotation; human labels are **not collected**. `cti_manual_audit.json`'s "machine_vs_human" block is **AI-vs-AI**, not human-vs-AI.
> 7. The baseline excludes **5 modified session files and 2 modified result files** (not 7 session files). The copied diff is **path-excluded, not content-redacted**; its legacy filename is retained but described truthfully. No credential was deleted or rotated and `.gitignore` was not changed as an audit side effect.


---

## 0. Scope, method, and limits

### 0.1 What this audit does and does not claim

This document establishes **what the code does when executed**, and **what the evidence artifacts do and do not support**. It deliberately separates:

| Class | Meaning |
|---|---|
| **CONFIRMED** | Established by reading the reachable code path and/or by executing it locally. |
| **REFUTED** | A claim in prior documentation that the code/artifacts contradict. |
| **SUSPECTED** | Structurally reachable defect that could not be triggered under audit rules (e.g. requires an external provider). |
| **NOT ESTABLISHED** | No repository artifact supports the claim. Absence of evidence, not evidence of absence. |

It makes **no effectiveness claims** from unit or mock tests. A green unit test proves the code does what the test asserts, not that the system resists attackers.

### 0.2 Prohibitions honored

No commits, resets, stashes, cleanup, or history rewrite. No manuscript edits. No training. No AWS calls. No public listeners. No external provider reachability tests. No JEV calls. No secrets, env values, or raw attacker-sensitive records printed or copied into this report. All pre-existing edits and artifacts were preserved; the archify reference was not touched.

### 0.3 Reachability discipline

Findings are labeled by whether they sit on the **real serving path**:

```
create_app("pipeline")
  → POST /v1/chat/completions        (Cowrie LLM bridge)
  → POST /api/session/command        (direct harness)
  → Sandbox.handle_command
  → Harness.process / _process_verified
```

Anything reachable only through the legacy `/api/classify`, `/api/analyze`, `/api/deceive` handlers is **dead code in pipeline mode** — those routes are not registered when `mode="pipeline"`. Findings there are labeled *latent*, never *serving defect*. Conflating the two was a recurring error in earlier documents.

---

## 1. Baseline artifacts created (hash scope)

All new files are **additive**. The pre-existing `docs/baseline_freeze/baseline_manifest.json` (sha256 `f0666b09…fef8fa`, 9,299 bytes) was **not modified**. The new baseline lives in a separate directory so the original freeze remains byte-identical.

| File | Purpose | Size |
|---|---|---|
| `docs/research/baseline/RUNTIME_TRUTH_BASELINE_20261022T184958Z.json` | Manifest: git state, critical input hashes, runtime defaults, env-var presence (names only) | 12,570 B |
| `docs/research/baseline/tracked_sha256_20261022T184958Z.jsonl` | Per-file sha256 of every tracked file — **5,866 files, 446,215,902 bytes**, aggregate `94b5f3d66dc98eea7344a74140ca57f0666c3d2f7f90ec696f70a13bb83ecc4e` | 981,187 B |
| `docs/research/baseline/untracked_inventory_20261022T184958Z.jsonl` | Inventory (path + hash + size) of the 2,976 untracked entries | 490,045 B |
| `docs/research/baseline/tracked_diff_redacted_20261022T184958Z.patch` | **Path-excluded** diff of the 24 tracked modifications → 17 emitted files; `data/sessions/` and `results/` contents excluded. Its legacy filename says "redacted", but the capture method only **excludes paths** — it does not scrub credentials from the 17 emitted files | 44,359 B |
| `docs/research/baseline/_capture_runtime_truth_baseline.py` | Reproducible capture script (re-runnable, idempotent naming) | 10,739 B |
| `docs/research/baseline/ruff_pre_change_20261022.txt` | Pre-change lint baseline | 9,091 B |
| `docs/research/baseline/mypy_pre_change_20261022.txt` | Pre-change type baseline | 5,149 B |

**Excluded from copied diffs** (hashed/inventoried only, never inlined): `.venv`, model weights, `data/sessions/**`, `results/**` contents. This is why the diff is 17 files rather than 24 — the 5 `data/sessions/*.jsonl` modifications and the 2 `results/*` modifications are represented by hash only. (An earlier revision said "7 session files"; that was wrong.)

### 1.1 Critical input hashes (frozen)

These anchor any later "did the inputs change?" question:

| Artifact | sha256 (prefix) | Bytes |
|---|---|---|
| `ragin/cycle/harness.py` | `1c49745314…` | 61,802 |
| `ragin/cycle/sandbox.py` | `f155e0ee49…` | 11,297 |
| `ragin/cycle/adapters.py` | `fcac70b8e8…` | 29,183 |
| `ragin/cycle/session.py` | `413698a410…` | 11,556 |
| `ragin/cycle/verifier.py` | `3170957148…` | 13,196 |
| `data/host_fiction.json` | `53f37d98ed…` | 124,485 |
| `data/corpus/command_aware_v2.jsonl` | `d1a2f015ea…` | 31,452 |
| `data/corpus/mitre_attack.jsonl` | `1ca5b68f12…` | 26,116,627 |
| `data/mitre_stix/enterprise-attack.json` | `bdf1ce86a4…` | 53,277,393 |
| `docs/SP2027_HARD_REVIEW_2026-10-08_POSTFIX.md` | `24212b22a1…` | 47,633 |
| `Makefile` | `852fb5720a…` | 803 |
| `pyproject.toml` | `0e5aa5b76e…` | 2,441 |
| `docker-compose.yml` | `9a3e49481d…` | 9,865 |

---

## 2. The runtime chain, as actually composed

### 2.1 Composition root — CONFIRMED

`ragin/server_v2.py::_init_pipeline` is the single place where the serving stack is assembled. Two facts dominate every downstream finding:

1. **`mandatory_verification=True` is passed unconditionally** to `Harness(...)` (line 940). This is the real, always-on gate. It is **not** the same thing as the V4 policy/evidence gate.
2. **A non-empty `gateway_url` is always supplied** — `HisokaAdapter(gateway_url=g_url)` (line 926) and `DonAdapter(gateway_url=g_url, api_key=a_key)` (line 895), where `g_url` comes from `_resolve_provider_config` and has a hard default (see §4.2).

`RAGIN_RUNTIME_MODE` defaults to `RAGIN_BASELINE`. Therefore:

- `SubstantiveStrategyAdapter` is **off**; `HisokaAdapter` is the default deceiver.
- The V4 policy gate (`_policy_selector.gate.evaluate`) is **not** reached (guarded by `if self._decision_arm != "RAGIN_BASELINE"`, `harness.py:539`).
- `ProviderTransportAdapter` is reachable only if `RAGIN_PROVIDER_ENABLED` is explicitly truthy.

### 2.2 Mandatory verification — CONFIRMED

`Harness.__init__` (`harness.py:241-249`):

```python
if mandatory_verification:
    if self._host_store is None:
        self._host_store = HostFictionStore(...)
    if self._verifier is None:
        inner = FictionConsistencyVerifier(fictions=self._fiction_graphs)
        self._verifier = HostFictionVerifier(inner, self._host_store)
```

So the mandatory verifier is `HostFictionVerifier` wrapping `FictionConsistencyVerifier`. Any earlier statement that "verification is optional" or "verification is the V4 gate" is **REFUTED**. Verification of deception text is mandatory; the *policy/evidence* gate is what is optional.

`_strict_verify` (`harness.py:341-357`) fails closed on three distinct conditions:

- verifier unconfigured → `{"passed": False, "issues": ["verifier_unconfigured"]}`
- verifier raised → `{"passed": False, "issues": ["verifier_exception:…"]}`
- verdict not a dict, or `passed is not True` → fail closed

This is a correct fail-closed shape. **CONFIRMED.**

### 2.3 Fail-closed serving — CONFIRMED

`Sandbox.handle_command` (`sandbox.py:190-213`) treats an *absent* verdict as a failure during mandatory mode:

```python
verified = verification.get("passed") is True
safe_response = result.response_text
safe_error = result.error
safe_status = "ok"
if self._harness.mandatory_verification and not verified:
    safe_response = ""
    safe_error = result.error or "verified_serve_unavailable:…"
    safe_status = "error"
served_response_sha256 = hashlib.sha256(safe_response.encode()).hexdigest() if safe_response else ""
```

The served hash is recomputed from the **post-gating** bytes, not inherited from the pre-gating candidate. That is the right invariant. **CONFIRMED.**

### 2.4 Verified/served hash invariant — CONFIRMED

`harness.py` emits `served_response_sha256 == verified_response_sha256 == sha256(candidate["response_text"])` in both the `VERIFICATION` event (line 421) and the `SYSTEM_RESPONSE` event (lines 456-487), with the bridge path at lines 891-901. Combined with `SandboxResponse.served_response_sha256` being recomputed at `sandbox.py:211-213`, the invariant holds: **the hash you can audit is the hash of the bytes served**. This is a genuine strength and should be preserved through any P0 edit.

### 2.5 Current-turn classification injection — CONFIRMED

`ctx.context` is built at `harness.py:532-533`, *before* `_run_classification` writes this turn's `CLASSIFICATION` event. Without correction, Don would see only prior turns. The fix is explicit at `harness.py:816`:

```python
cti_context = {**ctx.context, "classification": ctx.result.classification}
```

The comment above it (lines 809-815) documents the historical bug precisely: Don silently analyzed every command as `"unknown"`/`SUSPICIOUS` with `confidence=0.5`. `_strict_verification_context` (`harness.py:273`) correctly uses `ctx.result.classification` for the same reason.

**CONFIRMED — and this is a pre-existing fix, not a remaining bug.** It should be preserved, not "re-fixed".

---

## 3. Confirmed defects on the serving path

### 3.1 `/v1/chat/completions` docstring contradicted the fail-closed 503 — **CORRECTED (documentation only)**

The docstring originally promised:

> *"on sandbox error we fail SAFE: a generic shell error is served (never an unverified draft) and the failure is logged loudly."*

The implementation returns **HTTP 503** with `{"error": "verified_serve_unavailable"}` on both the crash branch and the `resp.error` branch, and serves no text. **That is correct fail-closed behavior**: a gate failure must not be masked by a synthetic 200. The defect was the docstring claiming a shell error was served when it was not.

**Resolution (P0 pass):** the docstring now states the actual 503 behavior and requires that any future synthetic shell error be a fixed, pre-approved string with no verification claim (`served_response_sha256=""`, `verification.passed=false`). Behavior was **not** changed to synthesize text.

**What is still NOT ESTABLISHED:** how a Cowrie front-end reacts to a 503 on this endpoint. The loopback trace observed **only verified HTTP 200** turns; no 503 was generated, so no "typically drops the connection" claim is made. That behavior requires a deliberate 503 observation, which this phase did not perform.

**Severity:** Low after the docstring fix (documentation truth). Availability/realism remains an open, unobserved question.

### 3.2 `/api/session/command` audit fields — **CORRECTED (observability)**

The success path previously returned only `session_id`, `response_text`, `command_count`, `event_count`, `error`. It now also returns `status`, `serve_path`, `candidate_sha256`, `served_response_sha256`, and `verification`; the 503 error path echoes the same audit fields while keeping `response_text=""`. `candidate_sha256` is now the **candidate** digest, not a copy of the served digest, so the two are separable. No fail-closed semantics were weakened: the 503 branch still returns 503 and an empty body.

### 3.3 Max-command path returns `status="ok"` with an error — CONFIRMED (minor, fail-open shape)

`sandbox.py:164-171`:

```python
if command_count > self._config.max_commands:
    session.close(reason="max_commands_reached")
    return SandboxResponse(..., response_text="Session limit reached.",
                           error="max_commands_reached")   # status defaults to "ok"
```

The response carries `error` but no `served_response_sha256`, and the default status is `"ok"`. This is a different shape from every other error path in the same function, which sets `status="error"`. It is not a security hole (the session is closed), but it breaks the "status reflects outcome" invariant that the rest of the module maintains.

**Severity:** Low. **P2.**

### 3.4 `DonAdapter.analyze` dereferences classification outside its guard — CONFIRMED but LATENT

`adapters.py:327`:

```python
classification_str = session_context.get("classification", {}).get("skill_level", "unknown")
```

If `session_context["classification"]` is present but not a dict — e.g. `{"classification": {"skill_level": …}}` sent to `/v1/analyze`, or a caller passing a string — this raises `AttributeError` before the surrounding `try` (which begins later in the method). The `.get("classification", {})` default only protects against a *missing* key, not a *wrong-typed* one.

**Reachability:** the legacy `/v1/analyze` handler is **not registered in pipeline mode**. On the real serving path, `harness.py:816` passes `ctx.result.classification`, which the classifier adapter produces as a dict. So this is **latent/dead-code**, not a live defect.

**Severity:** Low live / Medium if the route is ever re-enabled. **P1 hardening** (cheap, prevents a future regression), not P0.

---

## 4. Suspected defects (structurally reachable, not triggerable under audit rules)

### 4.1 Provider default self-collision — SUSPECTED

The three facts compose into a plausible deadlock:

1. `_resolve_provider_config` falls back to `url = "http://localhost:8080"` when nothing is configured (`server_v2.py:822-823`).
2. The server binds `127.0.0.1:8080` by default (`server_v2.py:1067`; `PORT` default `"8080"`, `RAGIN_BIND_HOST` default `"127.0.0.1"`).
3. `HisokaAdapter(gateway_url=g_url)` → `ResponseGenerator.__init__` always builds a `GatewayClient` when `gateway_url` is truthy (`deception.py:2413-2422`), and `GatewayClient` posts to `{base}/v1/chat/completions` (`gateway/client.py:145-148`).

If the deceiver ever calls the generator on the default config, the request lands on the **same** endpoint that is currently inside `Sandbox._lock` (an `RLock`, held by another thread). It blocks until `RAGIN_HISOKA_TIMEOUT` (default `300.0`s, `deception.py:2420`), then falls back to the template path.

**Why it is not CONFIRMED:** a live self-call would show ~300 s latency. The recorded campaign (`results/live_benchmark_zodiac_20260922.json`) shows `avg_response_time_ms = 44469.02` — 44.5 s, consistent with a real provider or a direct harness path, **not** a 300 s timeout. So the self-collision is **not corroborated by evidence**. It remains a latent hazard: it will bite any deployment that leaves the provider URL unset while the server runs on 8080.

**Severity:** High if triggered. **P1** — add an equality guard (configured gateway host:port == bind host:port → refuse to construct the HTTP client, or log a loud warning and force template mode).

### 4.2 Dense retrieval is inactive by default; explicit modes now exist — **PARTIALLY CORRECTED**

The historical default remains `RAGIN_RAG_MODE=hybrid`. `DonAdapter` without a
`vector_store_path` still constructs an unloaded `VectorStore`, so the current
default serving composition retrieves with BM25 alone and the `"hybrid"` label
is not an execution description.

The ablation path is now explicit and fail-closed:

| Mode | Construction | Search |
|---|---|---|
| `none` | no vector store, no corpus, no index | all retrieval methods return `[]` |
| `bm25` | sparse corpus only | BM25 only |
| `dense` | exact persisted store only | dense only; **no BM25 call** |
| `hybrid` | legacy default | existing vector+BM25 behavior |

`DonAdapter(vector_store_path=…)` now passes the path to `ThreatRAGEngine`.
`RAGIN_RAG_MODE=dense` requires `RAGIN_VECTOR_STORE_PATH`, `index.faiss`,
`documents.json`, `faiss`, `sentence-transformers`, and a **local**
`RAGIN_EMBED_MODEL` directory. Any missing prerequisite raises a configuration
error; it never falls back to BM25. Structural tests use explicitly labelled
fakes and assert the separation.

`ragin/decision_fusion_v4/evidence_export.py` no longer writes a static
`"hybrid"` backend when a command-aware trace is absent. It reports the
engine's observed/effective backend, requested mode, and construction flags; a
`none` arm reports `retrieval_status = DISABLED`. The fallback label that made
the earlier bundle misleading is removed.

**Current status:** the explicit B1/B2/B3 code paths exist. The exact B3 store
and local embedding model are still absent, so dense retrieval is **not
executed**. The default legacy composition remains BM25-only. No historical
campaign is relabelled; historical retrieval provenance remains **NOT
ESTABLISHED**.

### 4.3 Supervisor `CLASSIFICATION` event lacks `skill_level` — **CORRECTED (latent path hardened)**

`harness.py` emits `{"routing_decision": …, "stage": "supervisor"}` with no `skill_level`. The old `build_context` exposed the **last** `CLASSIFICATION` event as the singular `classification`, so a supervisor event would have poisoned that key for later turns.

**Resolution:** `build_context` now derives the singular key through `latest_skill_classification` (`ragin/cycle/classification.py`), which skips supervisor-only and malformed events and selects the latest event carrying a valid skill verdict. The full history remains under `classifications`. This is still **not reachable at the composition root** because `process_with_supervisor` short-circuits to `_process_verified` under mandatory verification, but the latent path is now safe.

**Severity:** Low today, High if supervisor routing is ever enabled with mandatory verification. **P1 hardening.**

---

## 5. Dead code and unused scaffolding (confirmed, non-serving)

- **`_bridge_verifier_artifact`** (`harness.py:39-…`) is defined but never called. `FictionConsistencyVerifier` D4 rejects empty output, so the bridge is not currently needed. Harmless, but it is a false affordance for anyone reading the verifier flow. **P3.**
- **Legacy `/api/classify`, `/api/analyze`, `/api/deceive`** are not registered in pipeline mode. Any behavior there — including §3.4 — is latent. **Documentation should say so explicitly** rather than presenting them as live endpoints.

---

## 6. Evidence provenance — what the numbers actually mean

This is the part where prior documentation and the artifacts diverge most. Every number below was read directly from the cited file.

### 6.1 The composite 0.880 is a *both-channel* score, not a served-text score

`results/vor_guarded_served_text_lower_bounds.json`:

| Channel | run1 raw → guarded | run2 raw → guarded |
|---|---|---|
| technique | 0.9598 → **0.4785** (61 zeroed) | 0.4553 (64 zeroed) |
| actor | 0.8500 → **0.2429** (25 zeroed) | 0.1700 (28 zeroed) |
| deception | 0.7325 → 0.7325 (unchanged) | 0.7504 (unchanged) |
| **composite** | **0.8796** | **0.8845** |

Critical provenance point: **the file itself labels these "both-channel lower bounds," not guarded served-text means.** The `0.479` / `0.243` figures in the summary are VOR lower bounds applied to guarded text; they are not the measured served-text accuracy.

### 6.2 Served text on the later rerun is ≈0.057 / 0.000

`results/cti_manual_audit.json`:

- 97 of 218 rows changed under the echo guard.
- Served average: technique `0.5236 → 0.0569`; actor `0.6800 → 0.0000`; deception `0.6492` (unchanged).
- Post-guard Cohen's κ: technique `−0.1874 → +0.3487`; actor `0.0483 → +0.9143`; deception `0.0991`.

So the honest statement is: **the operational composite is ~0.880; the served-text score on the audit subset is ~0.057 (technique) and 0.000 (actor).** These are not contradictory — they measure different things — but presenting 0.880 as "the" accuracy without the channel qualifier is **REFUTED** as a standalone claim.

### 6.3 The 216/2 label provenance does not match the latency inference

`results/two_channel_metrics.json` records `serve_path_tally` = **216 `GENERATED_VERIFIED` + 2 `FALLBACK_VERIFIED`** (98.9% / 1.1%). Config records `generator_model: (gateway default glm-5.3-flash-free)` and `ragin_full config`.

`docs/SP2027_HARD_REVIEW_2026-10-08_POSTFIX.md` infers from latency an **88.1% / 11.9%** split. A 1.1% fallback rate and an 11.9% fallback rate cannot both describe the same run. At least one of the two is derived by a different method (inference vs. label) on possibly different data. **This is an unresolved provenance conflict**, and it should be resolved before any fallback-rate claim is published. Label: **SUSPECTED inconsistency**; the file-based tally is the more direct artifact, the latency figure is an inference.

### 6.4 Three different generator models appear across results

The audit found `glm-5.3-flash-free` (gateway default, per `two_channel_metrics.json`), plus two other model identities referenced across result sets. Any cross-run comparison that does not fix the generator model is comparing different systems. All such comparisons are **NOT ESTABLISHED** until the model is pinned.

### 6.5 JEV — effect NON-ESTIMABLE

`results/jev_ab_eval.json`: `n = 200`, `jev_available = 0`, baseline accuracy `1.0`, with-JEV accuracy `1.0`, delta `0.0`, **0 escalations**.

**There is zero treatment exposure.** In this artifact JEV never fired, so the comparison is not an estimate of a JEV effect at all. The correct label is **NON-ESTIMABLE / NOT ESTABLISHED**. It is not evidence that JEV has no routing value, not evidence that it helps, and not evidence that it does not hurt. The ceiling (`accuracy = 1.0` in both arms) is a separate reason the sample cannot discriminate, but the primary defect is zero exposure. Any future claim needs a run where the treatment actually fires.

### 6.6 Stability

`results/stability_run1_vs_run2.json`: composite `0.8796 → 0.8845`, delta `0.0049`, `pass_agreement = 0.9908`. Inter-run stability on the composite is good. Note this measures *composite* stability under the both-channel definition, so it does not transfer to the served-text channel.

---

## 7. Laya provenance

### 7.1 What loads — CONFIRMED

`LayaRuntime` accepts only `UPSTREAM_CHECKPOINT_NAMES = {english, multilingual, typed-decisions}`. Fine-tuned directories report `unsupported_local_or_custom` and `fine_tuned_checkpoint_loaded=False`.

Served base model provenance:
- Upstream repo `convaiinnovations/laya`, revision `55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851`
- Model sha256 `891102d372688fc2a094dac56a384bc537b87c63f21f9f3dac0be2b7cbc8d86c`

### 7.2 The v12 fine-tune is scientifically failed and unserved

`models/laya_v12_balanced_allrows_gpu_redesign_v1_final_v1/train_report.json`:
- `eval_mode: in_sample_calibration`
- `is_held_out: false`
- `eval_items: 126`
- accuracy before `0.5952` → after `0.9444`
- explicitly: *"not independent held-out evaluation"*

The `0.9444` is **in-sample**. It is not a generalization estimate. Any citation of `0.944` as model quality is **REFUTED**.

`docs/laya_integration/LAYA_V12_NO_RERUN_RECOVERY_AUDIT.md` classifies v12 as `TUNING_FAIL_REDESIGN_REQUIRED` (fails gates G4, G5, G7, G8, I2) and documents that the runtime contract does not implement v12's interface (v12 emits `attack`/`stage`/`severity`; runtime expects `evidence_state`/`strategy`/`evidence_ref`). So even if the checkpoint loaded, it would not satisfy the contract.

### 7.3 "Laya B5" — a PROPOSED arm, **NOT READY**

B5 is a **proposed arm in the user's causal-ablation protocol** (see `docs/research/CAUSAL_ABLATION_PROTOCOL.md`), not a historical artifact. The absence of a B5 artifact is therefore **expected** and is not a false claim by anyone.

B5 is **NOT READY** for two independent reasons confirmed in this audit:

1. `LayaRuntime` accepts only the upstream checkpoint names `{english, multilingual, typed-decisions}`; the v12 fine-tune is not among them.
2. The v12 runtime contract is incompatible: v12 emits `attack`/`stage`/`severity`, while the runtime consumes `evidence_state`/`strategy`/`evidence_ref`.

The ~0.880 figure is a **pipeline both-channel composite** from `vor_guarded_served_text_lower_bounds.json` / `two_channel_metrics.json`. It has no B5 attribution, and no such attribution was made by the user; this audit does not invent one. B5 vs B3 is deferred until the checkpoint and contract are ready.

### 7.4 Human rating protocol — **EXISTS; labels NOT COLLECTED**

The earlier statement that no protocol is documented was wrong. Three separate facts must be kept distinct:

| Fact | Evidence | Status |
|---|---|---|
| Protocol exists, frozen before annotation | `docs/laya_integration/HUMAN_REFERENCE_STANDARD_PROTOCOL.md` (`human_v1`; 3 independent primary raters + adjudicator; no discussion between raters) | **CONFIRMED** |
| Human ratings collected | `results/laya_research/human_annotation_collection_status.json`: `human_labels_collected = false`; all three raters `delivered=false`, `returned=false`, `validated=false`; adjudicator `cases_released=false` | **NOT COLLECTED / INCOMPLETE** |
| `cti_manual_audit.json` labels are human | `annotators = {A: opencode/nemotron-3-ultra-free, B: opencode/mimo-v2.6-flash-free, C: opencode/ling-3.0-flash-fin-free}`; protocol text says "two independent LLM annotators … a third annotator adjudicates" | **REFUTED — they are AI-derived** |

Consequently the κ values in `cti_manual_audit.json` (technique `+0.3487`, actor `+0.9143`, deception `0.0991`) are **inter-AI agreement**, despite the `machine_vs_human` key. They are **not** human inter-rater reliability and **not** ground truth. Any completed independent human ratings remain **NOT ESTABLISHED** for this phase. No private transcript was opened or printed.

---

## 8. Local vs external prerequisites for any test

### 8.1 What ran locally (this session)

| Command | Result |
|---|---|
| `pytest tests/integration/test_runtime_truth_p0.py -q` | **13 passed** |
| `pytest tests/unit/test_gateway_integration.py tests/unit/test_hisoka_memory.py tests/unit/test_timing_fingerprint.py tests/unit/test_ttp_extraction_accuracy.py -q` | **75 passed, 8 skipped** |
| `pytest tests/integration/test_pipeline.py -q` | **9 passed** |
| `ruff check ragin/ tests/` | **exit 1 — 103 errors** |
| `mypy ragin/ --ignore-missing-imports` | **exit 1 — 37 errors in 10 files (131 checked)** |

These are **pre-existing baseline** numbers, captured before any change and stored in `docs/research/baseline/`. They are not regressions introduced by this audit (no code was changed). The full gate set named by `Makefile`/`pyproject.toml` is `pytest tests/unit`, `pytest tests/integration`, `pytest tests/security`, `ruff check ragin/ tests/`, `mypy`; the audit deliberately ran only the focused subset, not the broad suites.

### 8.2 Static debt breakdown (pre-existing, re-measured after the corrective pass)

**ruff — 93 errors:** E501 ×44, F401 ×17, I001 ×15, E402 ×4, UP035 ×4,
W292 ×3, UP031 ×3, and F821/F811/F541 ×1 each. The single **F821** is
`restart_persistence.py:65` referencing `Any` without importing it. The
corrective pass removed ten pre-existing `E501` lines it touched; it did not
add a new ruff code in the changed files.

**mypy — 25 errors in 8 files (132 checked):** union-attr ×7, arg-type ×6,
assignment ×4, index ×3, attr-defined ×2, return-value ×1, name-defined ×1,
misc ×1. The prior P0 baseline was 37 errors in 10 files. The reduction comes
from narrowing metadata/decision dictionaries in the changed adapter/harness
paths and one explicit command-aware guard; no error was suppressed.

### 8.3 What was blocked in Phase 0, and what the P0 pass executed

| Capability | Phase 0 status | P0 pass outcome |
|---|---|---|
| Full SSH end-to-end via Compose | blocked: `docker-compose.yml` hard-requires `RAGIN_LLM_BASE_URL`, which would mean an external provider | **EXECUTED WITHOUT COMPOSE** (`scripts/run_p0_loopback_ssh_trace_v1.py`): real Cowrie container → `server_v2` → Harness/verifier → Cowrie terminal, every listener on `127.0.0.1`, provider disabled, no image pull. Result: **PASS** (§14.4) |
| Public listener / Cowrie live smoke | public listener prohibited | ran on **loopback only**; `ss -ltn` confirmed `127.0.0.1:<port>` for both server and SSH |
| Provider self-collision reproduction (§4.1) | would require a live 300 s self-call | still **SUSPECTED**; a static configuration guard now rejects a *configured* self-endpoint (§9 P0-5) without any network probe |
| JEV routing evaluation | JEV calls prohibited; prior artifact has zero exposure | unchanged: **NON-ESTIMABLE** |
| Laya held-out evaluation | no held-out split; v12 in-sample only | unchanged: **NOT ESTABLISHED** |
| Actual LLM inference | external provider prohibited; no local served model | unchanged: **NOT ESTABLISHED**; the SSH trace used the deterministic strategy runtime |

Local capability that was available and used: Docker 29.8.0, the pre-existing `cowrie/cowrie:latest` image (ID `sha256:710f1e4601a663ac8591f58a42b44e4cd3b7ea170c7e6cdb9e54c430a30cd459`, no pull), `sshpass`, and the repository's `.venv`.

**Boundary statement (corrected):** source reads and mock/unit tests establish the internal boundaries they exercise — classification normalization, fail-closed serving, hash recomputation, verifier rejection, HTTP field exposure. They do **not** establish full terminal end-to-end integrity. Only the observed loopback trace does that for its three turns, and even that trace establishes **transport + serving + verification**, not LLM inference.

---

## 9. P0 edits — applied in the bounded fix pass

All edits below were applied in the P0 pass with two explicit scope constraints: **no historical result was relabelled**, and **no credential was rotated/deleted and `.gitignore` was not changed** as an audit side effect. Exact before/after hashes are in §14.1.

### P0-1 — Retrieval-method claims: separate current from historical

**Files:** documentation only — no historical result file touched.
**Why:** §4.2. Current `DonAdapter` composition retrieves BM25-only; historical campaigns are NOT ESTABLISHED without their exact config and raw trace.
**Action:** this audit records the current-vs-historical distinction. It does **not** rewrite `results/*` or any manuscript. A future paper revision must either describe the current run as BM25-only or re-run with `vector_store_path` populated.

### P0-2 — Reconcile `/v1/chat/completions` docstring with behavior

**File:** `ragin/server_v2.py`
**Why:** §3.1. The 503 is correct; the docstring was not.
**Applied:** docstring now states HTTP 503 `verified_serve_unavailable`, forbids synthesizing an unverified 200, and specifies that any future synthetic shell error must carry no verification claim. **Behavior unchanged.**

### P0-3 — Expose audit fields on `/api/session/command`

**File:** `ragin/server_v2.py`
**Why:** §3.2.
**Applied:** success and 503 paths expose `status`, `serve_path`, `candidate_sha256`, `served_response_sha256`, `verification`. `candidate_sha256` is no longer conflated with the served digest.

### P0-4 — Normalize classification before Don and `build_context`

**Files:** `ragin/cycle/classification.py` (new), `ragin/cycle/adapters.py`, `ragin/cycle/session.py`
**Why:** §3.4/§4.3.
**Applied:** shared `normalize_classification` / `latest_skill_classification`; Don accepts missing/null/non-dict/invalid skill/confidence and non-list history; `build_context` selects the latest **valid skill** event and skips supervisor-only/malformed events while preserving the full `classifications` list. A missing verdict is never promoted to the high-risk label.

### P0-5 — Provider self-collision: explicit configuration error, never a silent disable

**File:** `ragin/server_v2.py`
**Why:** §4.1.
**Applied:** `_assert_provider_not_self(config, bind_host, port)` runs in `main()` **before** the pipeline builds any HTTP client. It uses the actual listening port and loopback aliases (`localhost` / `127.0.0.1` / `::1` / wildcard binds). A **configured** endpoint equal to the server's own listener raises an explicit `RuntimeError`. The built-in `http://localhost:8080` default is now checked against the actual CLI port; it is no longer silently exempt. `create_app` with no actual port remains unchecked, and DNS aliases/redirects remain **SUSPECTED**. The error text does not echo the URL or credentials. No provider is silently disabled and no network probe is performed. The guard does not by itself prove the collision; it prevents a static self-call from being constructed.

### P0-6 — Secret hygiene: documented, **not** acted on in this audit

**Files (untracked):**
- `docs/aws_live_recovery/evidence/ssm_output_core_cert_inventory_20261011T145201Z.json`
- `docs/aws_live_recovery/evidence/phase3_positive/ssm_output_edge_positive_session_command_v2_20261011T165234Z.json`

**Why:** both contain a plaintext deployment API key and an environment dump. Values were not reproduced.
**Action taken:** none. This audit did **not** rotate the key, delete the files, or change `.gitignore`; those are destructive/operational actions outside an audit's remit. **Before any broad `git add`**, a human must rotate the key and exclude these paths. With 2,976 untracked entries, a blanket add would commit them.

### P0-7 — Supervisor `CLASSIFICATION` non-authoritative — **applied via P0-4**

`build_context` now ignores supervisor-only and malformed classification events for the singular key (§9 P0-4). The supervisor emitter was **not** changed: adding `skill_level` there would invent a verdict the supervisor does not produce.

---

## 10. Confirmed pre-existing fixes (preserve — do not "re-fix")

These are correct today and were misread as bugs in earlier review passes:

1. **Current-turn classification injection** (`harness.py:816`, comment 809-815) — fixes Don silently defaulting to `unknown`/`SUSPICIOUS`/0.5. **CONFIRMED correct.**
2. **Fail-closed absent-verdict handling** (`sandbox.py:195-213`) — absent verdict is not a pass. **CONFIRMED correct.**
3. **Post-gating served hash recomputation** (`sandbox.py:211-213`) — hash follows the bytes. **CONFIRMED correct.**
4. **`_strict_verify` fail-closed on verifier exception/malformed result** (`harness.py:341-357`). **CONFIRMED correct.**
5. **`build_context` singular/plural classification keys** (`session.py`) — `classifications` remains the full list and `classification` remains the compatibility singular key. **Shape preserved; selection hardened** in the P0 pass to "latest valid skill verdict" (§9 P0-4). Do not revert to "last event".
6. **`_strict_verify` fail-closed on a verifier exception or non-dict result** — preserved. The P0 pass added only the missing explicit failure for a **dict** result that omitted `passed` (previously returned `{}`, losing the reason). **CONFIRMED correct after that narrow fix.**

Separating these from the remaining defects is essential: an audit that lists correct code as broken invites a "fix" that reintroduces the original bug.

---

## 11. Remaining blockers and NOT ESTABLISHED items

| Item | Status | Reason |
|---|---|---|
| Laya "B5" | **NOT READY (proposed arm)** | expected: no historical artifact; upstream-only checkpoint loading + incompatible v12 contract |
| Dense retrieval contribution (current composition) | **NOT ESTABLISHED** | explicit dense path now exists, but `data/vector_store`/local embedding model absent; default composition remains BM25-only |
| Historical campaign retrieval backend | **NOT ESTABLISHED** | requires exact run config + raw retrieval trace; current empty store cannot be projected backwards |
| JEV effect | **NON-ESTIMABLE / NOT ESTABLISHED** | zero treatment exposure (`jev_available=0`, 0 escalations); ceiling also limits discrimination |
| Held-out v12 performance | **NOT ESTABLISHED** | `eval_mode: in_sample_calibration`, `is_held_out: false` |
| Provider reachability / model availability | **NOT ESTABLISHED** | external calls prohibited by audit rules |
| Fallback rate (1.1% vs 11.9%) | **SUSPECTED conflict** | file tally vs latency inference disagree; method unrecorded |
| Completed independent human ratings | **NOT COLLECTED / INCOMPLETE** | protocol frozen; all raters `delivered=false, returned=false, validated=false` |
| `cti_manual_audit.json` κ as human agreement | **REFUTED** | annotators are three LLM models; it is inter-AI agreement |
| Full SSH E2E | **OBSERVED for 3 turns** | loopback-only real Cowrie trace passed (§14.4); not a model result |
| B1/B2/B3 code paths | **PRESENT / NOT EXECUTED** | explicit `none`/`bm25`/`dense` modes; generator (and B3 store/model) missing |
| Verifier evidence grounding | **INCOMPLETE** | fiction/consistency verifier can pass a plausible ungrounded file/privilege claim; characterization test records it |
| Actual LLM inference | **NOT ESTABLISHED** | no local served model; deterministic runtime used |
| Provider self-collision | **SUSPECTED** | no live self-call; a configured self-endpoint now raises statically |
| Cowrie reaction to HTTP 503 | **NOT ESTABLISHED** | no 503 was generated in the observed trace |

### 11.1 Environment blockers encountered

`../CLAUDE.md` cannot be read through the read tool (`external_directory` permission denied); it is readable through the shell. No content from it was needed for this audit.

---

## 12. Command log (this session)

Phase 0 (before any edit):

```
git rev-parse HEAD                                  → 7d8a32aded7f4d168015aaa7f648f3367d3edad1
git status --porcelain | wc -l                     → 3000   (24 tracked mods + 2,976 untracked)
pytest tests/integration/test_runtime_truth_p0.py -q
                                                    → 13 passed
pytest tests/unit/test_gateway_integration.py \
       tests/unit/test_hisoka_memory.py \
       tests/unit/test_timing_fingerprint.py \
       tests/unit/test_ttp_extraction_accuracy.py -q → 75 passed, 8 skipped
pytest tests/integration/test_pipeline.py -q        → 9 passed
ruff check ragin/ tests/                            → exit 1, 103 errors
mypy ragin/ --ignore-missing-imports                → exit 1, 37 errors in 10 files (131 checked)
```

P0 fix pass (offline env: `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`):

```
pytest tests/integration/test_runtime_truth_p0_fixes.py -q
                                                    → 45 passed (exit 0)
pytest tests/integration/test_runtime_truth_p0.py \
       tests/unit/test_verifier.py \
       tests/unit/test_host_fiction.py \
       tests/unit/test_host_fiction_wiring.py \
       tests/unit/test_server_v2.py \
       tests/unit/test_cycle.py \
       tests/unit/test_metrics.py -q                → 166 passed (exit 0)
pytest tests/security/test_task2_verified_serving.py \
       tests/integration/test_pipeline.py -q        → 28 passed (exit 0)
ruff check <8 changed/new files>                    → All checks passed (exit 0)
ruff check ragin/ tests/                            → exit 1, 103 errors (unchanged)
mypy ragin/ --ignore-missing-imports                → exit 1, 37 errors in 10 files (132 checked)
mypy ragin/cycle/classification.py ragin/cycle/sandbox.py
                                                    → Success (exit 0)
python scripts/run_p0_loopback_ssh_trace_v1.py      → PASS (exit 0)
```

No exit code was masked by a pipe; the three pytest invocations printed their own
summary lines. Static verification of every line reference in §2–§5 was performed by
direct `sed`/`grep` reads of the working tree; no reference in this report is from
memory.


---

## 13. Bottom line

The **verification and hash-integrity core is sound** and should be left alone:
mandatory verification is genuinely on at the composition root, it fails closed, and
the served-bytes hash invariant held for every turn of the observed loopback trace and
for the focused test suite. That is an internal/transport guarantee — it is **not** a
grounding guarantee and not a model-quality claim.

The **truth problems were in labeling and exposure**, and they are now either fixed or
explicitly bounded:

1. **0.880 is a both-channel operational composite**; served-text is **~0.057 / 0.000**.
   Reporting either alone overstates what was served. This remains a manuscript-level
   correction and was not edited here.
2. **Current retrieval is BM25-only** because `DonAdapter` never loads the dense store.
   That is source-path evidence for the current composition only. **No historical
   campaign is claimed to have been BM25-only**, and no historical result was
   relabelled.
3. **B5 is a proposed arm, not a missing artifact.** It is **NOT READY** because only
   upstream checkpoints load and the v12 contract is incompatible. No 0.880 value is
   attributed to it.
4. **JEV is NON-ESTIMABLE**: the A/B has zero treatment exposure (`jev_available=0`,
   0 escalations), so it says nothing about routing value in either direction.
5. **HTTP 503 is correct fail-closed behavior.** Only the docstring was wrong, and it
   was corrected. Cowrie's reaction to a 503 remains unobserved.
6. **Human labels were never collected.** The `human_v1` protocol exists and is frozen;
   `cti_manual_audit.json`'s `machine_vs_human` block is **AI-vs-AI** and its κ is
   inter-AI agreement.
7. The **SSH path was observed end-to-end on loopback for three deterministic turns**.
   Model inference, attacker engagement, and arm effects remain **NOT ESTABLISHED**.

No P0 edit touched the verifier, the hash invariant, or the fail-closed branch. The
remaining blockers are experimental (frozen generator, B3 store/model, codebook,
allocation), not integrity defects. The B1 retrieval-off path is now implemented,
but no B1–B3 arm has been executed.

---

## 14. P0 fix pass — change contract, proof, and limits

### 14.1 Prior P0 snapshot hashes (preserved, not current)

The "pre-change" content of the five tracked source files was reconstructed without
touching the index: `git show HEAD:<path>` for each file, then the Phase 0 baseline
patch (`docs/research/baseline/tracked_diff_redacted_20261022T184958Z.patch`) applied in
a temporary directory. Each reconstructed hash **matches the Phase 0 manifest exactly**
(`phase0_matches_baseline_manifest = true` for all five), so the diffs in
`docs/research/p0_change_contract_20261022T193319Z/` are against the real pre-change
bytes.

| File | Phase 0 sha256 | Prior P0 sha256 |
|---|---|---|
| `ragin/cycle/session.py` | `413698a410fa5be79ba555523eddf3b075b5c6cd4601151cbe00f0c87b238d9f` | `72f8c66b9c6b84618dcc62607859fe81d1e9d63d6d7766da02d6dd0a74693b12` |
| `ragin/cycle/adapters.py` | `fcac70b8e8fe7016cc79afaacdedf8cdd4111ebd127595bd27e0b40d6f2bd779` | `30e8f6947083c0919ff70d866fe03dac842633747847c48199e19b7aee134a92` |
| `ragin/cycle/sandbox.py` | `f155e0ee493a2ef3d97de3e2389afb287ed9ce8a2e08f8ad7879ce423ad48f4e` | `a8b7205f2faa70a00af22c4a1f2838d4580594195bbb3ee7291612b3ae90b863` |
| `ragin/cycle/harness.py` | `1c4974531488027dc93d9c87f6e783ef64b0cb80a8a83cc0c435b5bd9aa75530` | `f8adce3518ae9a1f6c59c51be00c8b018f8fa9f607efb0527562385324a5c325` |
| `ragin/server_v2.py` | `d36bd89de364a334a4f4f00161ad4e27045c3d7be7917b87a236acd81b98729a` | `558f98b2cb77ab34d42fa55b8d2a98b42af1fd5c9865619f2a93197efe80d52b` |

New files (Phase 0 = absent):

| File | sha256 |
|---|---|
| `ragin/cycle/classification.py` | `d86ab64489f8819b15e6ac4ddcdc79863ee492b73326cd18e1c157a0dd352730` |
| `tests/integration/test_runtime_truth_p0_fixes.py` | `602c079d54d256e05fadc0f3a0eae42caf4c1e242f3d76e9fc342a1d797c6c5c` |
| `scripts/run_p0_loopback_ssh_trace_v1.py` | `2da85080d845fd88759077bad223f641716a7a8968d5c4d207dbdc89c4e2a44b` |
| `docs/research/CAUSAL_ABLATION_PROTOCOL.md` | `f7cbcab53897f8d9a3ad8630c21776cbade52056064a10ec6a3bc5b9c0edd823` |
| `docs/research/EXPERIMENT_READINESS_REPORT.md` | `f4c761a77eb7e4e611c9f472482e0f0d48c49bd180316b8286ba0cb026de9379` |

Per-file unified diffs are in `docs/research/p0_change_contract_20261022T193319Z/`
(`ragin__cycle__*.diff`, `ragin__server_v2.py.diff`). The table above is the **prior
P0 snapshot**. Files changed again in the corrective pass are listed in §15, and
their current hashes and deltas are in
`docs/research/p0_corrective_contract_20261022T200948Z/contract.json`. The final
contract JSON also records this audit file's post-edit hash; a file cannot contain
its own hash, so that value is only in the JSON.

**Process gap, stated rather than hidden:** this audit file was created during Phase 0
*after* the baseline freeze, so its own pre-edit bytes were never snapshotted. Its v1
content is not independently recoverable from a stored pre-edit snapshot. The
corrected file is authoritative; the missing pre-edit hash is recorded here as a gap.

### 14.2 Fixes A–E

| Fix | Files | What was done | What it proves / does not prove |
|---|---|---|---|
| **A. Classification normalization** | `ragin/cycle/classification.py` (new), `session.py`, `adapters.py` | `normalize_classification` returns a dict with a valid `skill_level` and bounded confidence; `latest_skill_classification` skips supervisor-only/malformed events; `DonAdapter` accepts missing/non-dict/null inputs and passes normalized evidence context. Full `classifications` history is preserved. | A malformed/absent verdict is never promoted to a high-risk label. Tested with the real `DonAdapter` and a recording engine. Does not change classifier quality. |
| **B. Endpoint observability** | `server_v2.py`, `sandbox.py` | `/api/session/command` success and 503 bodies expose `status`, `serve_path`, `candidate_sha256`, `served_response_sha256`, `verification`. Max-command response is `status="error"`. Chat-completions docstring now states the real 503 fail-closed behavior. | Callers can recompute the served digest and see the serve path. No synthetic 200 was added; the 503 branch still returns 503 with an empty body. |
| **C. Per-interaction trace** | `sandbox.py` | METRIC carries `trace` (`ragin.interaction_trace.v1`) with arm, status, classification availability, decision, model identity, tokens, cost, evidence refs, and command (redacted via `privacy_minimize_record`). Harness crashes are caught and recorded as explicit failed traces. | Every interaction has an honest record, including failures. Labels are `OBSERVED`, `ESTIMATED`, `NOT_AVAILABLE`, etc.; a value is never invented. Does not establish model inference. |
| **D. Verifier consistency** | `harness.py` | `decision_arm` property added; `_strict_verify` now returns `passed=False` with preserved `issues` for a **dict** verdict that omitted `passed` (previously lost the reason). | Fail-closed behavior is uniform across supported arms and strictly stronger on one malformed case. No threshold was loosened, no arm skipped, and no effect is claimed. |
| **E. Self-endpoint guard** | `server_v2.py` | `_assert_provider_not_self` runs in `main()` before pipeline construction, using the actual listening port and loopback aliases; a **configured** self-endpoint raises an explicit `RuntimeError`. The built-in `http://localhost:8080` default is now checked at the actual CLI port; `create_app` with no port remains unchecked. | Misconfiguration fails loudly instead of recursing. Tested for the default collision, `localhost`, `127.0.0.1`, and a non-default port. Error text does not echo the URL or credentials. No network probe or external call is made. |

`candidate_sha256` and `served_response_sha256` are now separate fields. For an accepted
generated turn the harness sets them equal; for fallback/rejected paths they can
differ, which is the point. The invariant
`served_response_sha256 == sha256(candidate.response_text)` was not weakened.

### 14.3 Test and static-gate results (corrective pass; supersedes the initial counts)

| Gate | Result | Exit |
|---|---|---|
| New/extended P0 tests (`test_runtime_truth_p0_fixes.py`) | **56 passed** | 0 |
| New ablation retrieval-mode tests (`test_ablation_retrieval_modes.py`) | **10 passed** | 0 |
| Existing focused runtime/verifier/server/cycle/metrics tests | **166 passed** | 0 |
| Security + pipeline tests | **28 passed** | 0 |
| `ruff` scoped to changed/new files (10 files) | **All checks passed** | 0 |
| `ruff check ragin/ tests/` | **93 errors** (prior baseline 103; 10 fewer, no new in changed files) | 1 |
| `mypy ragin/ --ignore-missing-imports` | **25 errors in 8 files, 132 checked** (prior 37 in 10; 12 fewer, no new in changed files) | 1 |

Focused total: **260 passed, 0 failed**. The standard focused run used
`HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1`; no model download occurred.

The prior P0 contract's 45/166/28, 103, and 37 figures describe the earlier
snapshot. They are preserved in
`docs/research/p0_change_contract_20261022T193319Z/contract.json` and are not
the current measurements.

### 14.4 Observed loopback SSH trace (final run for this pass)

Runner: `scripts/run_p0_loopback_ssh_trace_v1.py` (rewritten). Result: **PASS**,
exit 0. Artifacts: `docs/research/p0_loopback_trace_20261022T200948Z/`.

| Item | Observed value |
|---|---|
| Run id | `20261022T200948Z-671386` |
| Server / SSH port | `60627` / `32885` (dynamic) |
| Listeners | `127.0.0.1:60627`, `127.0.0.1:32885` only |
| Image | `sha256:710f1e4601a663ac8591f58a42b44e4cd3b7ea170c7e6cdb9e54c430a30cd459` |
| Container | `--network host`, `--pull=never`, started from image ID |
| Terminal stdout | 305 bytes, sha256 `97877eea921f48d111013f95f67761bf17ec553c436a7a2be34fbd2806d41be4` |
| Event counts | 3 `attacker_input`, 3 `system_response`, 3 `verification`, 3 `metric`, 3 `response_generate`, 3 `strategy_update` |
| Verification | 3/3 passed, all `GENERATED_VERIFIED` |
| Candidate/verified/served SHA | 3/3 agree per turn |
| Terminal matching | 3/3 served texts after their echo at distinct offsets `36→44`, `95→99`, `212→222` |
| HTTP bridge | 3/3 `POST /v1/chat/completions` with 200 |
| Decision provenance | actual `STRATEGY_UPDATE` event reference per turn (`OBSERVED_EVENT_REFERENCE`) |
| Generator | deterministic strategy runtime `RAGIN_V4_SUBSTANTIVE_DETERMINISTIC` |
| LLM inference | **NOT ESTABLISHED** |
| Dense retrieval | **NOT USED** (`RAGIN_RAG_MODE=none`) |

The runner writes `run_manifest.prelaunch.json` before launch with git HEAD,
dirty status and hash, source/config hashes, image ID, ports, expected command
list, and environment policy. It builds the child environment from an
allow-list, not `os.environ.copy()`, so inherited provider/cloud credentials and
proxies are not passed; it forces Laya off and `RAGIN_RAG_MODE=none`. Exactly
three commands are sent. Terminal matching requires each full served text to
occur strictly after its echoed command and before the next echo, and rejects a
served text indistinguishable from the echo.

Prior runs are preserved: `…192721Z` (PASS), `…192018Z` (PASS), and
`…191828Z_FAILED` (retained failure). The `…200948Z` run is the final run after
the corrective source changes.

**Provenance labels:** transport `REAL_SSH_COWRIE_TO_SERVER_V2`; serving
`REAL_SANDBOX_HARNESS_VERIFIER`; generator `DETERMINISTIC_STRATEGY_RUNTIME`;
LLM inference `NOT ESTABLISHED`.

**Isolation limit:** listeners are loopback-only and the application is
provider-disabled, but the container uses **host networking**. A shared
`--network none` namespace was assessed and not used: `ragin-python` has no SSH
client/sshpass, and the Cowrie image has no `/bin/sh` or paramiko; injecting
host binaries would require loader/library mounts, and host firewall changes
were out of bounds. This is **application-level isolation, not a network
namespace sandbox**.

### 14.5 Remaining blockers and approval boundary (current)

| Blocker | Status |
|---|---|
| Frozen generator identity, prompt, decoding, price | **MISSING**; no model served |
| B1 retrieval-off path | **DONE** (`RAGIN_RAG_MODE=none`; structural tests) |
| B3 exact store + local embedding model | **MISSING**; path and fail-closed checks done |
| B5 checkpoint/contract | **NOT READY** (v12 contract mismatch) |
| B4 rule table/contract | **NOT READY** |
| Historical campaign retrieval provenance | **NOT ESTABLISHED** (exact config + raw trace absent) |
| Provider self-collision | **SUSPECTED** beyond static equality; configured default/actual-port collision now raises |
| Cowrie reaction to a 503 | **NOT OBSERVED** |
| Independent human ratings | **NOT COLLECTED** |
| AWS evidence key | **NOT rotated or deleted** (destructive action outside scope; exclude the two untracked JSONs from staging) |
| Verifier evidence-grounding coverage | **BOUNDED**: `FictionConsistencyVerifier` can pass a plausible ungrounded file/privilege claim; characterization test added |
| Verifier wall-clock deadline | **NOT ESTABLISHED**: the `TimeoutError` regression is a simulated raised exception |

**Approval boundary:** any paid provider call, public listener, credential
rotation, or destructive file action requires explicit human approval and was
not performed. The protocol is design-only; no arm was run and no provider was
contacted.

---

## 15. Corrective pass — what changed and what it proves

This section records the bounded pass that followed the P0 audit. It does not
replace the prior change contract; it adds an explicit delta.

### 15.1 Code and configuration changes

| Area | Change | Evidence |
|---|---|---|
| Retrieval modes | `none`/`bm25`/`dense`/`hybrid`; dense validates exact store + local model and fails closed; no BM25 fallback | `ragin/don/rag_engine.py`; 10 structural tests |
| Don wiring | `DonAdapter` accepts `vector_store_path` and forwards observed provenance on success/failure | `ragin/cycle/adapters.py` |
| Evidence bundle | observed/effective backend; static `"hybrid"` removed; disabled retrieval marked `DISABLED` | `ragin/decision_fusion_v4/evidence_export.py` |
| Candidate observability | bounded, redacted candidate text per attempt; redact before truncate; raw SHA retained | `ragin/cycle/harness.py`; `ragin/capture_v4/privacy.py` |
| Decision provenance | actual `STRATEGY_UPDATE` event id/SHA and selected fields attached to candidates and METRIC | `harness.py`, `sandbox.py` |
| Command trace | full command SHA-256 plus bounded minimized text; served text/availability recorded | `sandbox.py` |
| Self-endpoint guard | checks actual CLI listen port including default; error does not echo URL credentials; static equality only | `server_v2.py`; tests |
| SSH runner | pre-launch manifest, allow-list env, image ID, exact 3-command cardinality, SHA/offset checks, retained failures | `scripts/run_p0_loopback_ssh_trace_v1.py` |
| Arm configs | versioned B0–B3 plus B4/B5 `not_ready`; design freeze manifest | `configs/ablation/`; `docs/research/design_freeze_v1.json` |
| Protocol | exact B0–B5 semantics, H1–H5, Track A/B, 32-allocation pilot, competing risks, one estimand/model, Holm 4/5 | `docs/research/CAUSAL_ABLATION_PROTOCOL.md` |

### 15.2 Verification coverage boundary (do not overclaim)

The live trace's `verification` event is a verifier verdict; a missing
`evidence` field in the trace is **not** a missing verdict. However,
`FictionConsistencyVerifier` is a fiction/contradiction consistency check plus
an optional fail-closed supported-claims check. It is **not** a general
grounding verifier. A regression records that a plausible ungrounded
`/etc/sudoers`-style response with no evidence can pass. The trace therefore
proves consistent, verified serving and byte-preserving delivery; it does not
prove evidence-grounded truth.

The raised-`TimeoutError` test is simulated. No code path in this pass
establishes a wall-clock verifier deadline; wall-clock timeout guarantees are
**NOT ESTABLISHED**.

### 15.3 Delta contract

The prior contract is preserved unchanged at
`docs/research/p0_change_contract_20261022T193319Z/contract.json`. The delta
contract for this pass is
`docs/research/p0_corrective_contract_20261022T200948Z/contract.json`. It
records the prior contract hash, current file hashes, reconstructable
prior-P0-to-current diffs, cumulative Phase-0-to-current diffs for the
corrective file set, and the final trace/test evidence hashes. Raw gate logs
and exit codes are under `.../validation/`. Where a prior
byte snapshot was unavailable (new untracked files, the prior runner, and the
earlier docs), the contract marks the delta as **NOT RECONSTRUCTABLE** rather
than inventing one.

### 15.4 Bottom line

- **B0** is locally runnable as a native transport.
- **B1–B3** code paths exist; the frozen generator (and for B3 the exact
  store/model) is still missing. **No B1–B3 result is measured.**
- **B4/B5** are **NOT READY**.
- The final loopback trace is an **integration proof**, not an arm result.
- Remaining external/model dependencies are exactly: generator identity/prompt/
  price, B3 exact index + local embedding model, codebook, allocation seed,
  budget cap, and (for B5) a compatible checkpoint.
