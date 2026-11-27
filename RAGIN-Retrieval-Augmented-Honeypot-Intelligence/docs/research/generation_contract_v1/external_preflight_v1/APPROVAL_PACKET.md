# External-preflight approval packet — generation contract v1

**Status: DRAFT / NOT EXECUTED.** No provider was contacted. No bridge or server
was started. This file requests approval; it is not a run report.

- Packet version: `external-preflight-v1`
- Packet digest: `795a28bd70b92220cecece2b4eb3f38d7baa207d7d9cb37a1c69048e566a9893`
- Proposed model (only): `opencode/deepseek-v4.1-flash-free`
- Route: existing loopback OpenCode CLI bridge, `scripts/opencode_proxy.py`,
  `127.0.0.1:8731`
- Hard HTTP request cap: **4** total generation requests, **0** retries
- Expected provider cost: **$0** on the configured free route; no paid fallback
- Scientific status after a successful preflight: **model exposure observed for
  one bounded free-route call path**, not a controlled decoding arm

## 1. Decision requested

Approve **one** bounded provider-exposure preflight:

1. start the existing loopback bridge with an allowlist containing **only**
   `opencode/deepseek-v4.1-flash-free`;
2. send the four frozen synthetic payloads once each;
3. record the raw HTTP responses and model-echo fields;
4. stop immediately on the first failure or cost/route inconsistency.

This packet does **not** authorize B1, B2, or B3. Those remain blocked.
Current arm names (no arm-selection decision is made here):

- **B2 = Cowrie + LLM + BM25**
- **B3 = Cowrie + LLM + dense RAG**

The approval digest binds the **entire canonical manifest** except `packet_sha256`
itself: route, single model, request budget, decoding claims, data-sharing flags,
tool-denial metadata, payload hashes, and the immutable source hashes. The manifest
embeds the runner hash; the runner never embeds the manifest digest (one-way binding).

A preflight run makes **one loopback metadata `GET /v1/models`** (not a generation
request) followed by at most **4 generation POSTs**. Only the POSTs count against the
hard cap.

## 2. What this preflight can and cannot establish

**Can establish (at most):**

- a synthetic request can traverse the existing loopback bridge;
- the configured free model alias returns assistant text;
- the exact bytes shared with the upstream route are the frozen payloads below;
- the bridge echoes the requested model alias.

**Cannot establish:**

- that `temperature`, `top_p`, or `seed` were honoured;
- that `max_tokens` was a hard decoding bound;
- an independent upstream provider model identity;
- the number of upstream provider calls made internally by the CLI;
- zero cost from provider billing or quota metadata;
- any B1/B2/B3 decoding-controlled or model-draft-used scientific claim.

The existing bridge is therefore **not full-contract-compatible**. Do not infer
contract compatibility from the fact that `model`, `messages`, and `max_tokens`
appear in an HTTP request body.

## 3. Frozen payloads

Each file is the exact byte sequence the runner sends (`data=<file bytes>`,
`Content-Type: application/json`, no reserialization).

| # | File | Synthetic command | `max_tokens` | Bytes | SHA-256 |
|---|---|---|---|---|---|
| 1 | `payloads/req_01_uname.json` | `uname -a` | 256 | 694 | `bc640dcf9080b6dd916420ce4a37e418139db86651e3738a8de955aa012eca30` |
| 2 | `payloads/req_02_whoami.json` | `whoami` | 64 | 691 | `2ef70f6761cf098be76ab679d0d8bbc15c25b047edbf8ed1bbceeadade274946` |
| 3 | `payloads/req_03_ss.json` | `ss -tlnp` | 256 | 694 | `b093b3b9cc2eed57f923bf7a7e7ec5ed37beae40ded4832cddc7d858ebb365e0` |
| 4 | `payloads/req_04_os_release.json` | `cat /etc/os-release` | 256 | 705 | `938be6db654ffd3056ea06a4899613e76210afe0a18b9f360c12a3750cba1eca` |

Every payload contains one synthetic system instruction and one synthetic lab
command. They contain no repository files, session logs, personal data,
credentials, private addresses, or external evidence. The only hostname is
`lab-node-01.example.test` (reserved `.example.test` domain).

## 4. Decoding and source identities

| Field | Value | Attestation |
|---|---|---|
| `model` | `opencode/deepseek-v4.1-flash-free` | allowlisted by `OPENCODE_ALLOWED_MODELS` |
| `temperature` | not sent | unsupported by bridge |
| `top_p` | not sent | unsupported by bridge |
| `seed` | not sent | `EXPLICITLY_UNSUPPORTED` |
| `max_tokens` | prompt text only | capped at 4096 by bridge prompt text; not a hard decoding bound |
| response `model` | expected echo of requested alias | `BRIDGE_ECHO_ONLY`; not independent provider identity |
| generation contract | inactive | `RAGIN_GENERATION_CONTRACT` must remain unset for this preflight |

The bridge's response `model` field is constructed from the request. It is not a
provider-attested identity. Record it as `BRIDGE_ECHO_ONLY`, never as
`PROVIDER_REPORTED`.

Immutable source identities bound by the packet digest:

| Role | Path | Bytes | SHA-256 |
|---|---|---|---|
| bridge | `scripts/opencode_proxy.py` | 9983 | `db1c7e01378c10017fa44503beb117a0acbb20365d6cc5eda83ff79111ebceb6` |
| safe config | `scripts/opencode_cli_bridge_safe_config.json` | 684 | `348059ab6b9ec19e94747aa494be5cdb1f717ba00c2d0b6f3989888c1742c40b` |
| runner | `scripts/preflight_generation_contract_v1.py` | 26070 | `5c4e913f6a8d2fe2fcce4f922bf84eb85d11e73d47cf0ec38dde71108dd243a8` |

The two bridge files are frozen for this preflight and must remain unedited. The
runner re-hashes both, plus itself, immediately before any transport object exists.

## 5. Data sharing (exact description)

The runner sends **only** the four frozen JSON payload files. The bridge:

1. validates the model against `OPENCODE_ALLOWED_MODELS`;
2. serializes the `messages` array into one plain-text prompt;
3. invokes the local OpenCode CLI with `--pure --format json --agent ragin-safe`
   inside a fresh temporary directory;
4. passes that prompt to the configured free-route provider;
5. returns the assistant text as an OpenAI-shaped completion.

The upstream provider receives the synthetic prompt text and may log or retain it
under its own terms. RAGIN does not control or attest provider-side retention.
No RAGIN session store, graph, host-fiction file, result artifact, or manuscript
is read by the payload builder.

Credential-bearing environment names are removed from the CLI child environment
by the existing bridge (`RAGIN_LLM_API_KEY`, `*_API_KEY`, `OPENCODE_CONSOLE_TOKEN`,
and related names). The runner itself reads no credential value and must not
print environment contents.

## 6. Tool denial (configuration-enforced)

Tool denial is not prompt-only. The bridge launches the CLI with:

- `OPENCODE_CONFIG=scripts/opencode_cli_bridge_safe_config.json`
- `--agent ragin-safe`
- `tools: {"*": false}`
- `permission: {"*": "deny", "bash": "deny", "edit": "deny", "read": "deny",
  "write": "deny", "webfetch": "deny", "websearch": "deny", ...}`
- a fresh temporary `--dir`, `stdin=DEVNULL`, fixed timeout.

The prompt also says “do not call tools” as defence in depth, but the enforced
control is the agent configuration and `--agent` selection.

## 7. Cost and abort conditions

Expected cost is **$0** because the only allowlisted alias is a free-route model
and no paid fallback is configured. The bridge does not expose provider billing
or quota attestation, so `$0` is a **configuration expectation**, not a measured
receipt. The CLI may retry internally and that count is **NOT_ATTESTED**; zero
hidden provider charges are not observable from the bridge response.

Expected wall time: 4 × 120 s HTTP transport bound plus bridge/CLI startup and
prompt overhead; plan for several minutes and do not parallelize. The runner
never retries an HTTP request, and a failed POST still counts as attempt 1.

Abort before or during the run if any of the following is observed:

- `OPENCODE_ALLOWED_MODELS` contains anything other than the single proposed
  model, or contains a paid/unknown alias;
- the bridge's `/v1/models` response does not list exactly the proposed model;
- any payload hash, byte count, or packet digest does not match this manifest;
- any payload contains a field other than `model`, `messages`, `max_tokens`;
- any response is non-2xx, malformed, empty, or contains an `error` object;
- any response reports a model different from the requested alias;
- any cost, quota, billing, or paid-route signal appears;
- the runner would exceed 4 HTTP generation requests or attempt a retry;
- the bridge is not bound to `127.0.0.1` / `::1`.

On abort: stop, write a failure receipt, do not retry with another model, and do
not substitute a paid route.

## 8. Bounded runner and readiness

Dry-run validation (offline; safe to run during review):

```bash
.venv/bin/python scripts/preflight_generation_contract_v1.py \
  --dry-run \
  --packet docs/research/generation_contract_v1/external_preflight_v1/REQUEST_MANIFEST.json
```

Start the existing bridge (NOT executed; requires approval):

```bash
OPENCODE_ALLOWED_MODELS='opencode/deepseek-v4.1-flash-free' \
OPENCODE_PROXY_HOST=127.0.0.1 \
OPENCODE_PROXY_PORT=8731 \
OPENCODE_BIN=/home/elaref/.opencode/bin/opencode \
.venv/bin/python scripts/opencode_proxy.py
```

Execute the four frozen requests (NOT executed; requires approval and the
packet digest):

```bash
.venv/bin/python scripts/preflight_generation_contract_v1.py \
  --execute \
  --packet docs/research/generation_contract_v1/external_preflight_v1/REQUEST_MANIFEST.json \
  --approval-sha256 795a28bd70b92220cecece2b4eb3f38d7baa207d7d9cb37a1c69048e566a9893 \
  --output docs/research/generation_contract_v1/external_preflight_v1/receipts/run_<UTC>.json
```

The output path and its sibling `<output>.raw/` namespace are opened create-only
(`x` / `exist_ok=False`); an existing receipt or raw namespace is never overwritten.

Readiness at packet time:

- offline packet validation: **PASS (pending human review)**
- focused runner tests: **16 passed** (loopback fixture only; not inference)
- bridge running: **NO**
- provider requests made: **0**
- model exposure: **NOT_ESTABLISHED**
- B1 / B2 / B3: **BLOCKED**

## 9. Scientific-use block

Until a transport exists that enforces decoding and attests provider identity and
retry/cost behaviour, this route may be used only for the bounded exposure
preflight above. It must not be used to generate B1, B2, or B3 treatment
responses, and no preflight output may be counted as a model-draft-used
treatment observation. Current arm names are **B2 = Cowrie + LLM + BM25** and
**B3 = Cowrie + LLM + dense RAG**; this packet makes no arm decision.

## 10. Approval record

- [ ] Reviewer confirms packet digest and payload hashes
- [ ] Reviewer confirms only the free model is allowlisted
- [ ] Reviewer confirms no paid fallback
- [ ] Reviewer confirms tool denial is configuration-enforced
- [ ] Reviewer approves the 4-request exposure preflight only
- [ ] Reviewer explicitly does **not** approve B1–B3

Approved by: ____________________  Date (UTC): __________

Approval is invalid if the packet digest, payload hashes, model alias, or request
cap is changed.
