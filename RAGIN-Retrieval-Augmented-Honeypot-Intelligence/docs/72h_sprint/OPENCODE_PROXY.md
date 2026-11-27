# OpenCode CLI Bridge

Status: IMPLEMENTED LOCALLY; `space-bunny-free` PASSES the safe completion path.

The active RAGIN selector uses a loopback OpenAI-compatible shim at `127.0.0.1:8731/v1`. The shim does not call OpenCode Zen over HTTP and does not require or forward an APMix/OpenCode API key. For each bounded completion request it invokes the installed `/home/elaref/.opencode/bin/opencode` CLI with `opencode run`, the selected allowlisted model, `--pure`, JSON events, a temporary working directory, and the dedicated `ragin-safe` agent.

The safe agent configuration is `scripts/opencode_cli_bridge_safe_config.json`. Its agent-specific permissions deny shell, file, web, task, skill, LSP, question, and external-directory tools. The bridge refuses non-loopback binding, caps body/message/prompt/output sizes, uses `shell=False`, removes legacy RAGIN/APMix credential variables from the child environment, and returns an unavailable response when the CLI fails or times out. No public listener or AWS resource was changed.

## Validation

- CLI bridge unit tests: 7 passed.
- Ruff and Python compilation: passed.
- OpenCode version: 1.18.35.
- Safe-agent inspection: explicit deny rules were present for shell, file, web, task, and external-directory tools.
- Bounded real CLI probe with `opencode/space-bunny-free`: PASS; 10 output tokens, 2,982 total reported tokens, 6,228 ms, reported cost 0.
- Loopback bridge completion with `opencode/space-bunny-free`: PASS; response returned through `127.0.0.1:8731/v1`.
- `opencode/ling-3.1-flash-free` and `opencode/big-pickle`: blocked with provider HTTP 403 under the deny-all profile.
- `opencode/exo-free`: blocked because the model is deprecated (HTTP 410).
- No paid request was made and no AWS mutation was performed.

## Current blocker

Some catalog-listed free models are rejected by the provider when the
deny-all profile is active. `space-bunny-free` is the validated selector for
the current local bridge. The earlier HTTP-to-Zen proxy remains removed from
the active design. Do not bypass model-specific restrictions with an
undocumented token, an unverified API credential, or a public relay.

The deterministic RAGIN fallback remains the AWS-safe behavior when the local
bridge is unavailable. The existing APMix credential is no longer an active
provider selector and is never forwarded by the bridge.

## Delegated OpenCode verification (2026-10-09)

The installed OpenCode CLI was independently exercised through the delegated
`opencode/ling-3.1-flash-free` investigation. A minimal agent configuration
without tool or permission blocks returned a short model response at zero
reported cost, but the same model returned HTTP 403 when the RAGIN safety
agent loaded its `tools` or `permission` restrictions. This is not an
acceptable deployment trade-off: removing those restrictions would re-enable
untrusted model access to OpenCode tools. The delegated run therefore made no
code changes and did not establish a safe generation path. The result and
event log are retained outside the repository at
`/tmp/ragin-opencode-delegate-20261009/result.json` and
`/tmp/ragin-opencode-delegate-20261009/events.jsonl`.

A direct safety probe confirmed the reason this cannot be relaxed: the
minimal agent successfully executed a requested `bash` tool command. That
configuration is therefore not acceptable for attacker-derived RAGIN input,
even though it can obtain a free-model response. The deny-all profile remains
mandatory, and its provider rejection is recorded as a fail-closed blocker.
