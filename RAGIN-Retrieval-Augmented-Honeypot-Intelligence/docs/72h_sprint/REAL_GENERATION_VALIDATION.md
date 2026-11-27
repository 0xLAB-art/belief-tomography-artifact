# Real Generation Validation

Status: PASS for a controlled OpenCode provider-backed local staging request; AWS CORE runtime remains intentionally fallback-only.

Current selector update (2026-10-09): APMix is no longer the active selector. The local configuration now targets `opencode/space-bunny-free` through `scripts/opencode_proxy.py`, which invokes the installed OpenCode CLI rather than an HTTP provider API. `opencode/ling-3.1-flash-free` and `opencode/big-pickle` were rejected with HTTP 403 under the required deny-all profile; `opencode/space-bunny-free` succeeded with that profile.

## Provider evidence

The configured `deepseek-v4-flash-free` model was not present in the provider catalog and was not called. The catalog-listed `claude-sonnet-4-6-free` model was used for the bounded probe and the earlier controlled staging flow. The fresh probe returned HTTP 200 in 4143 ms with 28 total tokens. Provider usage afterward was 13,300 tokens used and 2,986,700 remaining on the reported free plan; top-up remaining was zero. Cost metadata was null, so the evidence relies on the provider's free-plan state, free model identifier, and zero top-up balance; no paid model was called. See [the provider pricing page](https://apmix.ai/pricing) and [provider API documentation](https://apmix.ai/docs).

## Verified staging result

Hisoka uses the existing `GatewayClient` abstraction through `HisokaAdapter`/`AdaptiveDeceiver`; the model selector is `RAGIN_HISOKA_MODEL`. The earlier historical staging flow used `claude-sonnet-4-6-free`; the current local controlled selector is `opencode/space-bunny-free`. CORE's live runtime was not left with a provider credential after either bounded test.

Session `ses-46a0642581094765` sent `echo generated42` through isolated Cowrie, the EDGE bridge, mTLS, and the CORE serving path. CORE recorded `GENERATED_VERIFIED`, `FictionConsistencyVerifier`, `passed=true`, `accepted=true`, and candidate digest `470489c8ce7da2ba6b722652559fdb903a3781c2cee9fc8239c2b610a50c8736`. The resulting text was visible in the controlled Cowrie session. This is the required provider-backed milestone, not a catalog-only check.

The provider secret was staged only for the bounded test, then removed from CORE runtime configuration. The current CORE environment points to an unavailable local provider and therefore runs verified fallback. No provider credential is present in the current runtime.

## Current OpenCode local pipeline result

With the deny-all agent active, the loopback bridge returned a genuine
`opencode/space-bunny-free` completion. A local `server_v2` pipeline then
processed `echo SPACE_BUNNY_PIPELINE_PROBE` through Chrollo, Don, Hisoka, the
mandatory deterministic verifier, and state commit. Session
`ses-872e6679aaf6466e` recorded `GENERATED_VERIFIED`,
`FictionConsistencyVerifier`, `passed=true`, `accepted=true`, attempt 1, and
candidate digest
`93612c9609b931a3a206362632e108f742b58ffecbe40f7fe72d226e7a8a1157`.
This is local controlled evidence, not public field data or proof that the
current AWS CORE has a permanent provider dependency.

## Current isolated Cowrie result

The local bridge was then exercised through an isolated Cowrie 3.0.15
container with no host port publication. Command `true` reached the local
`server_v2` listener, and the SSH-visible response was
`webapp@web-srv-01:~$`. Session `ses-7d4b10c6af0c4475` recorded
`GENERATED_VERIFIED`, `FictionConsistencyVerifier`, `passed=true`,
`accepted=true`, and candidate digest
`ad6289a471e2af8418db17b29a2e794995534a2985ad93f8417c9b3e82f63939`.
The run wrote the temporary field export and the container had bounded
memory/CPU/PID limits, read-only root, dropped capabilities, and no-new-
privileges. The temporary Docker-subnet firewall exception was removed after
the test and no `8731`/`8843` listener remained.

This proves the current OpenCode bridge can complete the generation and
verification path through an isolated Cowrie session locally. It does not
change the AWS CORE runtime, whose provider URL remains intentionally
disabled; the attempted AWS reverse tunnel was rejected by its hardened
`AllowTcpForwarding no` SSH policy.

Evidence: `evidence/opencode_cowrie_local_e2e_20261009.json`.

Redacted evidence is in `evidence/real_generation_provider_probe.json`,
`evidence/real_generation_provider_probe_20261009.json`,
`evidence/real_generation_e2e.json`, and
`evidence/opencode_space_bunny_e2e_20261009.json`.

## Failure handling

Provider absence remains a safe condition: the serving path uses bounded fallback and the verifier remains authoritative. The provider is not treated as a permanent deployment dependency until its model identity, quota, and operational cost are independently rechecked.
