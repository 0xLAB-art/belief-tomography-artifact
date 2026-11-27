# Overnight Execution Status

Checkpoint start observed: 2026-10-08T20:19:18Z  
Latest checkpoint: 2026-10-09T04:48:17Z
Working directory: `/home/elaref/Documents/research/ragin/RAGIN-Retrieval-Augmented-Honeypot-Intelligence`

## Running

- CORE staging: `ragin-core-staging`, private `172.31.17.217:8443`, mTLS required.
- EDGE forwarder: `socat-ragin.service`, loopback `127.0.0.1:18083`.
- EDGE Cowrie staging: `ragin-cowrie-staging`, internal bridge `ragin-cowrie-internal`, loopback-only host forward `127.0.0.1:2222`, Cowrie 3.1.1.
- SSH and SSM remain available on both existing instances.
- EIC endpoint: `eice-023d2c69cb6690c48`, `create-complete`, ENI `172.31.61.22`, same AZ as CORE.

## Tested

- CORE server startup, Chrollo/Don/Hisoka pipeline initialization, mTLS health/session/command/replay.
- Valid EDGE identity, missing client certificate, invalid API key, wrong/rogue identity cases.
- Controlled Cowrie `whoami` flow returned synthetic `webapp`, not the Ubuntu host shell.
- Fresh CORE SSH through EIC tunnel after the narrow UFW rule was added.
- Focused Python serving/mTLS tests: 42 passed.
- Provider-backed completion: catalog-listed `claude-sonnet-4-6-free`, HTTP 200, 4570.7 ms, 22 tokens; configured DeepSeek model was absent and not called.
- Provider-backed Cowrie-to-CORE request: session `ses-46a0642581094765`, `echo generated42`, `GENERATED_VERIFIED`, verifier accepted, candidate digest recorded.
- Fallback provenance regression fixed and deployed: fallback now records `TEMPLATE_FALLBACK_VERIFIED` rather than a generated label.
- Optional Laya boundary implemented as a fixture-tested typed adapter with bounded timeout and explicit `NO_SIGNAL`; no Laya weights or inference used.
- Existing graph benchmark run completed with `--limit 1`: three fallback-only sessions, no errors, and report saved under `evidence/controlled_benchmark_fallback_20261009.json`.
- Cowrie container checks: approved bridge forwarder reachable; host SSH, metadata, and external connectivity test blocked.
- Fresh 03:36Z container probe reproduced the same result: `172.29.0.1:18083` connected; EDGE host SSH, IMDS, and `1.1.1.1:443` blocked.
- GPU: Quadro RTX 4000, 8192 MiB, 7739 MiB free; Laya runtime not integrated.
- Post-restart CORE validation: container remained up, mounted session/fiction files remained present, and fresh EDGE mTLS `/health` returned `healthy` with the pipeline active.
- OpenCode replacement implemented as a local loopback CLI bridge; health/model-list checks passed, and the safe agent deny rules were inspected.
- `opencode/space-bunny-free` completed a bounded safe-profile request: 6,228 ms, 10 output tokens, reported cost 0.
- Local `server_v2` pipeline completed session `ses-872e6679aaf6466e` with `GENERATED_VERIFIED`, deterministic verifier acceptance, and persisted audit evidence. `ling-3.1-flash-free` and `big-pickle` remain blocked under the same profile; `exo-free` is deprecated.
- Isolated local Cowrie 3.0.15 bridge test completed: command `true` visibly returned `webapp@web-srv-01:~$`; session `ses-7d4b10c6af0c4475` recorded `GENERATED_VERIFIED`, verifier acceptance, candidate digest `ad6289a471e2af8418db17b29a2e794995534a2985ad93f8417c9b3e82f63939`, and a field export file.
- Temporary local UFW rule allowing only Docker bridge `172.17.0.0/16` to `8843/tcp` was removed after the test; local `8731`/`8843` listeners and the Cowrie container are now stopped.
- Bounded OpenCode provider benchmark completed in 90.36 seconds: CTI technique and CTI actor cases were `GENERATED_VERIFIED`; the persona case was `TEMPLATE_FALLBACK_VERIFIED`; three sessions, zero pipeline errors. Raw report: `results/overnight_20261009/opencode_provider_limit1.json`; redacted envelope: `evidence/opencode_provider_benchmark_20261009.json`.

## AWS and security boundary

- Current CORE still has a public address and IGW-routed placement; the EIC endpoint does not make CORE private.
- No public Cowrie, web listener, RAGIN API, NAT gateway, paid VPC endpoint, replacement instance, snapshot, or volume was created.
- AWS CLI read-only refresh restored on 2026-10-09: both instances running, both SSM Online, EIC create-complete, private route local-only, roots unencrypted, no VPC Flow Logs observed, and SG egress remains unrestricted.
- Cowrie no longer uses host networking; it uses an internal bridge, pinned digest, read-only root, dropped capabilities, no-new-privileges, and bounded memory/CPU/PIDs.
- Temporary CORE SG/UFW 8443 staging rule and EIC management rules are RAGIN-specific and reversible.
- Public reachability to CORE `8443` and EDGE `2222/18083` timed out from the workstation.
- OpenCode bridge binds only to `127.0.0.1:8731`; no public listener was started.
- The AWS reverse-tunnel attempt was rejected before any remote listener was created because CORE `sshd` reports `AllowTcpForwarding no`; no SSH configuration was changed.

## Worktree and evidence

- Existing user changes were preserved. Overnight additions are limited to staging transport/configuration, evidence, and these reports.
- Current focused regression/adapter suite: 36 passed; repository-wide suite was invoked after the harness fix without a reported failure.
- Evidence: `docs/72h_sprint/evidence/`.
- Current local Cowrie/OpenCode evidence: `evidence/opencode_cowrie_local_e2e_20261009.json`.
- Current provider benchmark evidence: `evidence/opencode_provider_benchmark_20261009.json`.
- Historical results were not rewritten or relabeled.
- OpenCode CLI bridge evidence: `evidence/opencode_cli_bridge_validation_20261009.json`.

## Blocked or incomplete

1. Private CORE cutover and encrypted root migration require a replacement/cutover decision and may require additional billable resources.
2. EDGE/CORE egress remains broader than the final allowlist; arbitrary-egress denial was not claimed.
3. Current CORE is public-addressed and roots are unencrypted; private/encrypted cutover remains blocked for approval and cost verification.
4. Laya adapter/inference and broad benchmark runs are deferred; current OpenCode generation is proven in local isolated Cowrie staging but is not yet a private AWS dependency.
5. Public exposure and field collection remain unauthorized.

## Exact next actions

1. Review the provider-backed and container-isolation evidence.
2. Keep the staging containers non-public while independent research work continues.
3. Approve a costed replacement/encrypted private CORE cutover only if desired; leave public listeners closed.
4. Keep `opencode/space-bunny-free` as the local controlled selector; retain verified fallback whenever the local bridge is unavailable.
5. Treat the new provider benchmark as bounded local staging evidence only; do not promote its scores to field-effectiveness claims.
