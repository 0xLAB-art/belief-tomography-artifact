# EARLY COORDINATION — generation contract interface (v1)

Status: **IMPLEMENTED, NOT INFERENCE** — 2026-10-23 (UTC). The native HTTP
generation contract and the bounded external-preflight runner are implemented and
offline-tested. No model was invoked, no provider was contacted, and no B1/B2/B3
arm is executable or decided. Legacy defaults remain in force when the contract
is off. Names below are stable; the eval owner can wire against them.

## Pure local helper (no model, no network)

`ragin/gateway/generation.py`

```python
from ragin.gateway.generation import (
    GenerationConfig, GenerationConfigError,
    resolve_generation_config, require_model_exposure,
)

cfg = resolve_generation_config()             # None when the contract is off
cfg = resolve_generation_config(explicit=c)   # native interface (wins)
snapshot = cfg.snapshot()                     # credential-free effective config
digest = cfg.config_sha256                    # canonical config digest
```

`resolve_generation_config()` returns `None` when
`RAGIN_GENERATION_CONTRACT` is not truthy and no explicit object is passed.
When the contract is enabled but unresolved/invalid it raises
`GenerationConfigError` (field names only; no values, paths, URLs, or keys).

## Opt-in activation and exact env names

| Env var | Required when | Meaning |
|---|---|---|
| `RAGIN_GENERATION_CONTRACT` | to enable | `1/true/yes/on` activates enforcement. Unset/0 = legacy defaults. |
| `RAGIN_GENERATION_CONFIG_PATH` | no | JSON object path; wins over individual vars. |
| `RAGIN_GEN_MODEL` | yes | Caller-chosen model id (no hardcoded model/provider). |
| `RAGIN_GEN_TEMPERATURE` | yes | Finite, `0.0 <= t <= 2.0`. |
| `RAGIN_GEN_MAX_TOKENS` | yes | Integer `1..131072`. |
| `RAGIN_GEN_TOP_P` | yes | Finite, `0.0 < p <= 1.0`; always sent on the wire. |
| `RAGIN_GEN_SEED` | one of | Integer seed; sent on the wire. |
| `RAGIN_GEN_SEED_STATUS` | one of | `EXPLICITLY_OMITTED` or `EXPLICITLY_UNSUPPORTED` when no seed. Must be declared before the run. |
| `RAGIN_GEN_MAX_RETRIES` | yes | Integer `0..3`; retries replay the identical payload. |
| `RAGIN_REQUIRE_MODEL_EXPOSURE` | to enable mode | `1/true/yes/on` enables require-model-exposure mode. |

JSON file keys are exactly: `model`, `temperature`, `max_tokens`, `top_p`,
`seed`, `seed_status`, `max_retries`. Unknown keys are refused.

## Enforcement points

- `GatewayClient(generation_config=cfg)` (or `ProviderTransport(...,
  generation_config=cfg)`) — every generated HTTP request carries
  `model`, `temperature`, `max_tokens`, `top_p`, and (when explicit) `seed`.
  A conflicting `model=` argument raises `GenerationConfigError`. A retry
  replays the same decoding; contract mode never inflates `max_tokens`.
- `GatewayClient.generation_snapshot()` — pure local introspection, safe for
  health wiring (no URL/key/prompt).
- `ProviderTransport.health()` — legacy keys unchanged; adds
  `"generation": snapshot` **only** when the contract is active.
- `ResponseGenerator` (Hisoka serving generator) resolves the env contract and
  consumes it; its `meta` carries the observation in contract/exposure mode.

## Metadata keys (generator-level)

Contract-active keys: `generation_contract_version`,
`generation_config`, `generation_config_sha256`, `generation_request_digest`,
`requested_model`, `provider_reported_model`, `model_identity_status`,
`model_invocation_attempted`, `model_invocation_succeeded`,
`model_response_received`, `model_draft_used_in_candidate`,
`raw_model_draft_sha256`, `raw_model_draft_text`,
`postprocessed_candidate_sha256`, `postprocessed_candidate_text`,
`final_generation_sha256`, `final_generation_source`,
`generation_failure_reason`, usage fields, `cost_usd=None`,
`cost_availability="NOT_MEASURED"`.

Exposure-mode keys: `model_exposure_requested`, `model_exposure_mode`,
`model_exposure_status`, `protocol_compliant`, `exposure_failure_reason`,
`treatment_available`, `exposure_eligible`.

Status values: `MODEL_DRAFT_USED`, `MODEL_CALLED_DRAFT_NOT_USED`,
`NOT_EXPOSED_DETERMINISTIC_FASTPATH`, `MODEL_REQUIRED_UNAVAILABLE`,
`MODEL_CALL_FAILED`.

## Not established

No generative local weights exist on this host. The Ollama loopback endpoint
lists cloud aliases only and was NOT called. Actual model invocation and
scientific exposure remain **NOT_ESTABLISHED / externally blocked**. All
tests are mocked or loopback-fixture only and are never measurements.

## Transport and retry caveats (do not infer controlled decoding)

The existing OpenCode CLI bridge (`scripts/opencode_proxy.py`) serializes HTTP
messages into one CLI prompt. It does **not** pass `temperature`, `top_p`, or
`seed`; `max_tokens` changes prompt text only; the response `model` echoes the
requested alias (`BRIDGE_ECHO_ONLY`); and CLI internal provider retries/cost are
`NOT_ATTESTED`. The bridge is therefore suitable only for a bounded request-
traversal/text-return **exposure preflight**, never for B1/B2/B3 scientific
generation. Native HTTP transport is required for the decoding contract.

Budgeting native generation requires every retry layer:
`GenerationConfig.max_retries` bounds **transport** retries only. Hisoka's
semantic strict retry can issue 2 generation calls per candidate, and the
Harness default `max_retries=2` permits 3 candidate attempts, so a turn can make
up to **6 generate calls before transport retry**. A 24-session × 12-turn pilot
is 288 turns, i.e. up to **1728 generation calls × (transport_retries + 1)**,
before attacker/evaluator calls. The frozen pilot is **NOT READY** until every
retry layer is budgeted. When multiple semantic calls occur, usage fields
describe the **last provider request only**, not turn totals. Current arm names
are **B2 = Cowrie + LLM + BM25** and **B3 = Cowrie + LLM + dense RAG**; no arm
decision is made here.
