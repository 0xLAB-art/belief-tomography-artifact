# RAGIN 72-Hour Sprint Status

Status timestamp: 2026-10-09T04:48:17Z

Elapsed sprint hours: UNKNOWN. No sprint start timestamp was supplied, so elapsed time is not fabricated.

## Completed

| Milestone | State | Evidence |
|---|---|---|
| AWS current-state refresh | PASS | `docs/task3_8/`, live CLI readback |
| Dedicated private CORE target | PASS | `subnet-07fae34b3db734bb2`, `rtb-04bf376f929483d4c`; local-only route; no public-IP mapping |
| Strict application mTLS boundary | PASS locally | `ragin/transport/mtls.py`, actual `server_v2` bridge test |
| CORE staging serving path | PASS | Live `server_v2` container on private `172.31.17.217:8443`; Chrollo/Don/Hisoka/Sandbox/Harness initialized |
| EDGE-to-CORE mTLS request | PASS | EDGE valid client certificate; health/session/command/replay evidence in `evidence/edge_to_core_verified_provenance.json` |
| Cowrie-to-CORE controlled smoke | PASS | Loopback Cowrie `127.0.0.1:2222` -> local mTLS forwarder -> CORE; `whoami` returned synthetic `webapp`; `evidence/cowrie_to_core_e2e.json` |
| Provider availability | PASS read-only | Configured `api.apmix.ai/v1`, `deepseek-v4-flash-free`; `/models` returned HTTP 200; no completion call in staging |
| OpenCode provider-backed local pipeline | PASS | `opencode/space-bunny-free` through deny-all CLI bridge; `server_v2` session `ses-872e6679aaf6466e`; `GENERATED_VERIFIED` evidence in `evidence/opencode_space_bunny_e2e_20261009.json` |
| Isolated Cowrie/OpenCode generated E2E | PASS locally | Bridge-network Cowrie 3.0.15 -> local `server_v2` -> OpenCode; session `ses-7d4b10c6af0c4475`, visible `webapp@web-srv-01:~$`, `GENERATED_VERIFIED`, `evidence/opencode_cowrie_local_e2e_20261009.json` |
| OpenCode provider-backed benchmark | LIMITED PASS | `--limit 1` report: 2 `GENERATED_VERIFIED`, 1 `TEMPLATE_FALLBACK_VERIFIED`, 3 sessions, 0 errors; `evidence/opencode_provider_benchmark_20261009.json` |
| Targeted serving/security tests | PASS | 42 passed |
| Repository Python tests | PASS | 1,645 passed, 116 skipped, 34 warnings |
| Rust gateway build/test command | LIMITED PASS | `cargo test` exit 0; no Rust test cases executed; authentication remains unimplemented |
| Public honeypot exposure | NOT DONE | No public Cowrie or RAGIN listener opened |
| CORE private management via EIC | PASS for current CORE | `eice-023d2c69cb6690c48`, ENI `172.31.61.22`; fresh SSH tunnel succeeded after exact UFW allow |

## Current blockers

1. Existing CORE remains public and on the IGW-routed subnet.
2. Existing CORE and EDGE roots remain unencrypted.
3. Private SSM management is not available in the new subnet without a paid endpoint, NAT, or another private overlay; EIC management is now available for CORE.
4. Staging runtime is deployed, but not a private CORE migration or production/public deployment.
5. Permanent egress/container isolation and durable protected telemetry are incomplete.
6. OpenCode generation is validated through an isolated local Cowrie path, but the bridge is not a permanent private CORE dependency; AWS runtime remains fallback-only until a private provider path is approved and deployed.
7. Ethics/privacy approval and public-exposure authorization are absent.
8. The provider benchmark is local staging evidence only; it does not establish AWS provider reachability or field effectiveness.

## Next executable action

Prepare one approval packet for private management plus replacement encrypted CORE cutover. Keep the current staging containers non-public; do not create replacement compute, storage snapshots, NAT, interface endpoints, or public exposure until that packet is approved.

## Resource and cost state

- Existing running compute: RAGIN-CORE and RAGIN-EDGE only.
- Sprint-created resources: one private subnet and one route table; no hourly service charge expected from these resource types.
- One EIC endpoint and one dedicated EIC security group were created; no NAT gateway, paid VPC endpoint, snapshot, volume, instance, load balancer, or public address was created in this sprint.
- Runtime changes are host-local: Docker packages/images, CORE staging container, EDGE Cowrie container, loopback mTLS forwarder, and temporary private CORE SG/UFW TCP/8443 rules.
- Cost Explorer returned zero daily unblended cost for 2026-10-01 through 2026-10-07; credit balance and delayed billing are not exposed by the used CLI query.

AWS mutations were the tagged private target subnet/route-table preparation at 2026-10-08T19:57:02Z–19:57:07Z UTC, the reversible CORE-only TCP/8443 ingress rule from `172.31.35.203/32` (`sgr-02f8c8986dc89b953`) for staging mTLS, and the dedicated EIC endpoint/SG created at 20:20Z. The EIC SG allows only TCP/22 to the two RAGIN SGs; CORE UFW has one matching endpoint-source SSH rule. No public honeypot ingress was opened.
