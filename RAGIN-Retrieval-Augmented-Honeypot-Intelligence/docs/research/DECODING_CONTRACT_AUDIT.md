# DECODING CONTRACT AUDIT — 2026-10-23

Status: **CONFIGURATION LAYER VERIFIED AND TRACEABLE; END-TO-END COMPLIANCE STILL BLOCKED.**

This audit answers Priority 2 of the runtime-provenance phase: trace the
decoding configuration from each planned arm to the actual generation backend,
make supported parameters explicit and traceable, stop implying that
unsupported parameters took effect, and separate what is implemented, what is
tested, and what is unverified.

**Non-claims.** No provider was contacted, no model or weights were loaded, no
image was pulled, and no inference happened during this phase. A passing unit
test here proves configuration plumbing only. It is *not* evidence that a
backend honors `top_p`/`seed`, and it is not evidence of deception quality.

## 1. The complete path, arm by arm

| Arm | Requested decoding | Path to the backend |
|---|---|---|
| **B0** native Cowrie | none (native shell) | `configs/ablation/b0_native_cowrie.json` — `generator.decoding: null`. B0 has no LLM and therefore no decoding contract; it is the H1 bundle, not a decoding arm. |
| **B1** Cowrie + LLM | `temperature 0.0, top_p 1.0, max_tokens 512, seed 0` (`PROPOSED_NOT_ENFORCED`) | `b1_no_retrieval.json` → `RAGIN_RAG_MODE=none` → Hisoka `ResponseGenerator._generate_via_gateway` (`ragin/hisoka/deception.py:3400-3472`) → `GatewayClient.generate` (`ragin/gateway/client.py`) → `/v1/chat/completions` |
| **B2** B1 + BM25 | same as B1 (asserted by test) | identical serving path; retrieval differs only in `RAGIN_RAG_MODE=bm25` |
| **B3** B1 + dense RAG | same as B1 (asserted by test) | identical serving path; retrieval differs only in `RAGIN_RAG_MODE=dense` |

The three LLM arms share one serving path, so "decoding consistent across
comparable arms" reduces to one contract, not three. A new test
(`test_b1_b2_b3_agree_on_decoding_and_runtime_defaults`) locks the arm configs
to each other and to the frozen run contract so they cannot drift silently.

The frozen run contract (`configs/ablation/eval_v1/run_contract_v1.json`,
`generation.decoding`) requests exactly `0.0 / 1.0 / 512 / seed 0` and records
`status: PROPOSED_NOT_ENFORCED`. That status was accurate when written and is
now only half true — see §2.

## 2. Verified: two paths exist, and which one is active is explicit

**Legacy path (contract disabled — the current default).**
`ResponseGenerator._generate_via_gateway` sends
`{"temperature": 0.7, "max_tokens": 4096}` (`deception.py:3472`) with no
`top_p` and no `seed`. This is the documented historical behavior; it is now
asserted by `test_hisoka_legacy_call_site_requests_0_7_4096` so it cannot
change unnoticed. Two additional legacy behaviors were confirmed and are now
recorded in the observation rather than living only in code comments:

- the empty-content retry **inflates** `max_tokens` to
  `min(12800, max(1024, max_tokens*4))` (`client.py:455-460`), recorded as
  `cot_retry_decoding`;
- extension fields (e.g. `reasoning_effort: "low"` injected for
  reasoning-model identifiers on calls ≤ 2048 tokens, `client.py:317-326`)
  reach the wire without being part of the contract digest — now listed in
  `payload_extension_fields`.

**Contract path (opt-in).**
`RAGIN_GENERATION_CONTRACT=1` + `RAGIN_GEN_*` (or
`RAGIN_GENERATION_CONFIG_PATH`) resolves a validated `GenerationConfig`
(`ragin/gateway/generation.py`). When active:

- every request carries the contract's `temperature`, `max_tokens`, `top_p`
  and — only when explicitly seeded — `seed` (`client.py:274-331`);
- conflicting per-call overrides raise `GenerationConfigError` instead of
  silently winning (`client.py:278-292`);
- the empty-content retry replays the **identical** decoding (no budget
  inflation), asserted by `test_contract_retry_replays_identical_decoding`;
- an enabled-but-invalid contract raises at construction
  (`test_hisoka_unresolved_contract_refuses_instead_of_falling_back`).

**Seed/top_p honesty.** `top_p` and `seed` are supported by *RAGIN's client*;
whether the backend honors them is **unverified** (no provider call is
authorized in this phase). The contract refuses to exist without an explicit
seed declaration (`EXPLICIT` / `EXPLICITLY_OMITTED` /
`EXPLICITLY_UNSUPPORTED`), and an unsupported seed is provably absent from the
serialized payload (`test_unsupported_seed_is_absent_from_the_wire`). Nothing
in RAGIN now implies an unsupported parameter took effect: the observation
records the decoding fields actually serialized (`decoding_wire_fields`), the
extension keys actually serialized (`payload_extension_fields`), and the retry
payload actually sent (`cot_retry_decoding`) — `client.py:61-71, 357-359,
401-402, 460`. When the transport drops extensions after a 400 and retries,
the wire-truth fields and the request digest are recomputed over the payload
that actually succeeded (`client.py:395-404`).

## 3. Implemented this phase

1. **Wire-truth instrumentation** (`ragin/gateway/client.py`): the observation
   now distinguishes configured decoding from serialized decoding, and records
   the retry payload. Behavior unchanged; the trace can no longer imply that a
   dropped extension or an inflated retry budget was the configured request.
2. **Effective-config publisher**
   (`scripts/publish_effective_generation_config_v1.py`): the ablation
   preflight blocks with `UNRESOLVED_EFFECTIVE_GENERATION_CONFIG` /
   `BLOCKED_GENERATION_CONFIG` until a third owner publishes a pure
   applied-decoding/model-exposure artifact. This script is that publisher: it
   resolves the same validated module the serving client uses, refuses to
   publish when the applied decoding differs from the frozen contract
   (exit 3), refuses when the contract is not activated (exit 2), refuses to
   overwrite an existing artifact without `--force`, opens no socket, and
   carries its non-claims inside the artifact.
   Self-test against the frozen contract's requested decoding (recorded, not
   installed):
   `RAGIN_GENERATION_CONTRACT=1 RAGIN_GEN_MODEL=lab/publisher-selftest
   RAGIN_GEN_TEMPERATURE=0.0 RAGIN_GEN_MAX_TOKENS=512 RAGIN_GEN_TOP_P=1.0
   RAGIN_GEN_SEED=0 RAGIN_GEN_MAX_RETRIES=1 RAGIN_REQUIRE_MODEL_EXPOSURE=1
   .venv/bin/python scripts/publish_effective_generation_config_v1.py
   --out /tmp/effcfg_selftest.json` → **exit 0**, applied decoding
   `0.0/1.0/512/seed 0`, artifact sha256
   `e77fb73a9daddec09d3d74479e49c0ec932cad15d6dcb01021b2d72dbae2514d`.
   The artifact was written to `/tmp` deliberately: recording it into the
   frozen run contract is a *decision* for the arm owner, not a side effect of
   a self-test. Note that the artifact digest includes `published_utc`, so each
   publication hashes differently even with identical decoding; the run
   contract must pin the digest of the artifact actually in force (re-running
   the publisher without a contract change and pinning the new digest is
   expected to be a no-op decision, not a compliance event).

## 4. Tested vs unverified

| Claim | Status | Evidence |
|---|---|---|
| Contract values reach the serialized payload unchanged | **Tested (offline)** | `tests/unit/test_decoding_contract_v1.py` (wire capture on monkeypatched `requests.post`) |
| Unsupported seed is absent from the wire | **Tested (offline)** | same file |
| Legacy call site requests exactly 0.7/4096, no top_p/seed | **Tested (offline)** | same file |
| Contract retry replays identical decoding; legacy retry inflates and records it | **Tested (offline)** | same file |
| B1/B2/B3 configs agree on decoding and on runtime defaults | **Tested (local files)** | same file |
| Publisher artifact satisfies the preflight's effective-config consumption | **Tested (offline)** | same file |
| Backend honors `temperature=0.0` / `max_tokens=512` / `top_p` / `seed` | **UNVERIFIED** | requires an authorized live run; the apmix catalog probe has been unreachable since 2026-10-08 (`APMIX_WRITER_PROVENANCE_AUDIT.md`) |
| Frozen generator identity, prompt, weights, price | **UNVERIFIED** | `UNRESOLVED_MODEL`, `UNRESOLVED_PROMPT_ID` remain open |
| That any decoding choice improves deception | **NOT MEASURED** | out of scope for this phase; no causal claim exists |

## 5. Remaining blockers for decoding compliance (B1–B3)

Clearing the decoding layer does **not** make B1–B3 executable. The frozen run
contract still (correctly) blocks on, in `_check_generation` order:
`UNRESOLVED_EFFECTIVE_GENERATION_CONFIG` (until the artifact's path+sha256 is
recorded by the arm owner), `MODEL_EXPOSURE_NOT_ENFORCED` (the
`exposure_contract.require_model_exposure` flag is still false in the frozen
contract), `FALLBACK_NOT_DISABLED` (the generator still exposes a
template/static fallback while the contract demands `fallback: none`),
`UNRESOLVED_PROMPT_ID`, and `MODEL_INVOCATION_UNAVAILABLE` (no local weights,
no attested invocation). Each is a real gate; none was relaxed here.

## 6. Commands and exit codes (this phase)

| Command | Exit |
|---|---|
| `.venv/bin/python -m pytest -q tests/unit/test_decoding_contract_v1.py tests/integration/test_served_output_integrity_v1.py` | 0 (21 passed) |
| `scripts/publish_effective_generation_config_v1.py --out /tmp/effcfg_selftest.json` (env above) | 0 |
| `ruff check` on all changed/new files | 0 |

## 7. What a compliant B1–B3 run must record per request

1. the contract snapshot (`config_sha256`) and its source;
2. `decoding_wire_fields` — the decoding actually serialized;
3. `payload_extension_fields` — every non-contract field that reached the wire;
4. `cot_retry_decoding` when a retry occurred;
5. the provider's reported model identity (`provider_reported_model`) and, for
   model arms, the observed weights identity — the exposure contract.

Until 5 exists for a real backend, decoding compliance is a configuration
property, not a measured one, and must not be described as enforced against
the provider.
