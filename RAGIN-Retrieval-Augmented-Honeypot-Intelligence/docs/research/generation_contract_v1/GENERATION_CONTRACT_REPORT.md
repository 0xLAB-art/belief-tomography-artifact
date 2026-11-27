# Generation contract v1 — implementation and preflight report

**Status: IMPLEMENTED, OFFLINE-ONLY, NOT INFERENCE.** 2026-10-23 (UTC).

No model was invoked. No bridge, server, proxy, or cloud resource was started.
No external provider or experiment API was contacted. All runner tests use a
loopback fixture. **Provider experiment calls made by this work: 0. Actual LLM
inference: none.**

## 1. What is implemented

- **Native HTTP generation contract** (peer-owned production code, not rewritten
  here): opt-in `RAGIN_GENERATION_CONTRACT`; sends `model`, `temperature`,
  `top_p`, `max_tokens`, and an explicit `seed`/`seed_status`; transport-only
  `max_retries`; contract-observed metadata keys; legacy defaults preserved when
  the contract is off.
- **Bounded external-preflight runner** (`scripts/preflight_generation_contract_v1.py`):
  validates a frozen packet offline, and only with an exact approval digest
  performs at most four loopback generation POSTs against the already-running
  CLI bridge.
- **Approval packet** (`external_preflight_v1/`): four synthetic, self-contained
  lab payloads; one allowlisted free-route model; loopback-only route; no paid
  fallback; deny-all agent configuration.
- **Focused tests** (`tests/unit/test_preflight_generation_contract_v1.py`):
  16 offline tests over packet tampering, approval gating, raw-body preservation,
  attempt accounting, malformed responses, cost signals, and overwrite refusal.

The two bridge files remain **unedited**: `scripts/opencode_proxy.py` and
`scripts/opencode_cli_bridge_safe_config.json`.

## 2. Native HTTP contract vs the CLI bridge

| Property | Native HTTP transport | Existing OpenCode CLI bridge |
|---|---|---|
| `model` sent | yes | yes (allowlisted alias) |
| `temperature` / `top_p` | sent and enforceable | **not supported / not sent** |
| `seed` | sent when explicitly supplied | **unsupported / not sent** |
| `max_tokens` | hard request bound | prompt text only |
| response model | provider-reported candidate | **echo of requested alias** (`BRIDGE_ECHO_ONLY`) |
| retries | transport retries configurable and observable | CLI internal retry **`NOT_ATTESTED`** |
| usage | final provider request fields | bridge timing only; CLI cost/usage **not attested** |
| admissible for B1/B2/B3 | only with frozen config | **never** |

The bridge serializes `messages` into one CLI prompt. It can establish request
traversal and text return only. It cannot establish controlled decoding,
independent model identity, internal call counts, or billing.

## 3. Preflight contract enforced by the runner

- **Exactly ≤ 4 HTTP generation POSTs, 0 retries**, one model, loopback only.
  One additional loopback `GET /v1/models` is metadata, not generation.
- **Approval binding is one-way**: `packet_sha256` covers the full canonical
  manifest (sorted-key compact UTF-8) **except** `packet_sha256` itself. The
  manifest embeds the runner/bridge/safe-config hashes; the runner never embeds
  the manifest digest.
- **Exact payload bytes** are sent (`data=<frozen bytes>`), with only `model`,
  `messages`, and `max_tokens` permitted.
- **Deny-all agent config** is validated (`tools["*"] is false`,
  `permission["*"] == "deny"`), not assumed from prompt text.
- **Raw HTTP bodies and SHA-256** are preserved for success, error status, and
  non-JSON responses in a fresh create-only `<output>.raw/` namespace.
- **Attempts are counted before send**, so a failed POST receipt records
  `attempt: 1` and `http_generation_requests_sent: 1`.
- **Strict stable aborts** on non-2xx, non-JSON, malformed completion shape,
  missing/empty content, model echo mismatch, models allowlist mismatch, or
  bridge unavailability.
- **Explicit cost/billing/paid-route signals abort.** Hidden provider charges are
  not observable; `cost_usd` stays `null` with
  `cost_availability: NOT_ATTESTED`. Expected cost is `$0` on the free alias but
  is a configuration expectation, not a receipt. No paid fallback exists.
- **Never overwrites**: receipt uses `open(..., "x")`; raw namespace uses
  `mkdir(exist_ok=False)`.

## 4. Packet identity

- Packet digest: `795a28bd70b92220cecece2b4eb3f38d7baa207d7d9cb37a1c69048e566a9893`
- Model (only): `opencode/deepseek-v4.1-flash-free`
- Binding: `SHA256_OF_CANONICAL_MANIFEST_EXCLUDING_PACKET_SHA256`
- Immutable sources: runner `5c4e913f…43a8`, bridge `db1c7e01…ceb6`,
  safe config `348059ab…2c40b`
- Current arm names (no decision): **B2 = Cowrie + LLM + BM25**,
  **B3 = Cowrie + LLM + dense RAG**
- Estimated wall time: 4 × 120 s transport bound plus CLI startup/prompt
  overhead; do not parallelize.

## 5. Retry-budget caveat (frozen pilot not ready)

`GenerationConfig.max_retries` is **transport-only**. Hisoka's semantic strict
retry can issue 2 generation calls per candidate, and the Harness default
`max_retries=2` permits 3 candidate attempts. Therefore a turn can make
**≤ 6 `generate` calls before transport retry**.

A 24-LLM-session × 12-turn pilot is 288 turns → up to **1728 generation calls ×
(transport_retries + 1)**, before attacker/evaluator calls. The frozen pilot is
**NOT READY** until every retry layer is budgeted. When multiple semantic calls
occur, usage fields describe the **last provider request only**, not the turn
total.

## 6. Verification (offline, this run)

Command shape: fresh interpreter, unique `RAGIN_SESSION_DIR` /
`RAGIN_HOST_FICTION_PATH`, `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`,
provider credentials/proxies unset, `NO_PROXY` limited to loopback.

- `54 passed` — `tests/unit/test_preflight_generation_contract_v1.py` (16) plus
  `tests/unit/test_generation_contract_v1.py` (38), 9.87 s.
- Dry run: exit 0, digest above, `generation_requests=4`, `retries=0`,
  `provider_calls=0`.
- `ruff check` on the runner and new test: exit 0.
- Prior evidence reported by peers (not rerun in this pass): 276 focused
  generation tests passed; supervisor independently combined 489 tests across
  25 files, passed (`/tmp/ragin-supervisor-combined-l4jv9l5q`).

The 16 preflight tests cover: real-packet dry run; manifest digest tamper;
payload byte tamper; immutable-source hash tamper; missing immutable sources;
non-loopback endpoint rejected even when resealed; no approval ⇒ no HTTP;
successful exact-byte send and raw preservation; failed POST counted as attempt
1 with no retry; non-JSON abort; malformed completion shape; zero-cost field
passes; explicit cost signal aborts before request 2; allowlist mismatch aborts
before POST; existing receipt refusal; existing raw-namespace refusal.

## 7. Known limits

- The CLI bridge cannot support B1/B2/B3 decoding or model-draft-used claims.
- Upstream CLI/provider retry count, quota, and billing are not observable.
- Model identity is `BRIDGE_ECHO_ONLY`, not provider-attested.
- The 120 s timeout is a transport bound, not a latency measurement.
- Raw bodies and receipts are local evidence; they must not be presented as
  scientific observations.
- Any edit to the runner, bridge, safe config, manifest, or payloads invalidates
  the approval digest.
- This packet makes **no arm-selection decision** and authorizes **no external
  call** until a human approval record exists.

## 8. Artifacts

| Artifact | Path |
|---|---|
| Runner | `scripts/preflight_generation_contract_v1.py` |
| Focused tests | `tests/unit/test_preflight_generation_contract_v1.py` |
| Packet manifest | `docs/research/generation_contract_v1/external_preflight_v1/REQUEST_MANIFEST.json` |
| Approval packet | `docs/research/generation_contract_v1/external_preflight_v1/APPROVAL_PACKET.md` |
| Interface/status | `docs/research/generation_contract_v1/INTERFACE.md` |
| Raw evidence (logs, hashes) | `docs/research/generation_contract_v1/evidence/20261023T040343Z/` |

The evidence namespace contains the raw pytest stdout, dry-run stdout, ruff
output, exit codes, source hashes, packet-artifact hashes, and a new
`EVIDENCE_MANIFEST.sha256` computed from those raw files. It deliberately does
**not** hash peer-modified shared runtime files as a final release.
