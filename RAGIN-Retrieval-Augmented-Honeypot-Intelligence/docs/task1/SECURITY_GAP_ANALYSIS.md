# Security Gap Analysis

Severity is assigned against the requested public honeypot and the claimed verified-serving research result. Findings are evidence-based; an absent implementation is reported as absent, not as a presumed exploit.

## P0: unsafe deployment or invalid security boundary

| ID | Finding | Evidence | Impact / required gate |
|---|---|---|---|
| P0-1 | The active field path does not enforce verification before serving. | `ragin/server_v2.py:554-578` creates `Harness` without a verifier; `ragin/cycle/harness.py:287-315` returns when verifier is absent; `ragin/cycle/sandbox.py:107-182` returns `response_text` without a passed check. Legacy direct serving is `ragin/server.py:122-171`. | A public deployment can serve generated text outside the deterministic safety contract. Block public exposure until one authoritative path has a mandatory fail-closed gate and tested fallback. |
| P0-2 | Proposed AWS EDGE/CORE separation is not implemented or represented as AWS infrastructure. | Main Compose publishes gateway, component, JEV, observability, nginx, and Cowrie ports; `ragin-internal` is only a Docker network (`docker-compose.yml`). No VPC/private subnet/SG/IaC for the named instances was found. | CORE may be publicly reachable and internal APIs/metrics/provider paths may be exposed. Require private CORE, restrictive SG/NACL, and controlled EDGE-to-CORE authentication before deployment. |
| P0-3 | Authentication can be disabled or left at a placeholder, and the Rust gateway has no visible request-authentication middleware. | `server.py:27,244-265,746-765`; `server_v2.py:108-125,650-679`; `docker-compose.field.yml:78,108,127`; `llm-gateway/src/main.rs:54-66` registers routes directly; `llm-gateway/config.toml:126-129` has `api_keys = {}` and wildcard CORS. | Publicly reachable control/generation routes could be unauthenticated or use shared placeholder credentials. Require mandatory service auth, fail-closed startup, restricted CORS, and separate operator auth. |

## P1: important correctness, reliability, reproducibility, or architecture issues

| ID | Finding | Evidence | Required follow-up |
|---|---|---|---|
| P1-1 | Verifier exceptions fail open when a verifier is configured. | `ragin/cycle/harness.py:287-315` records `passed=True` with an error; retry exceptions are caught and do not force fallback (`harness.py:617-668`). | Convert verifier failure to a rejected candidate and verified deterministic fallback; add fault-injection tests. |
| P1-2 | State can be mutated before verification in the LangGraph path. | `ragin/cycle/graph.py:260-320` calls fiction `.observe()` in generation; promotion is later in finalize (`graph.py:396-416`). | Use immutable pre-state plus transactional post-acceptance commit. |
| P1-3 | HITL and host-fiction capabilities are not wired into the active `server_v2` path. | `ragin/cycle/hitl.py:1-147,275-325`; `graph.py` contains approval/host-fiction logic; `server_v2._init_pipeline` builds Harness/Sandbox only. | Decide one serving path and wire/block the required approval and cross-session policy explicitly. |
| P1-4 | Session context/replay authorization is shared-key-only and absent when the key is empty. | `server_v2.py:108-125,227-263`; arbitrary session IDs are accepted by session routes. | Add session ownership/tenant authorization, opaque capabilities, redaction, and audit for reads. |
| P1-5 | Process-local session association is ambiguous and loses all mappings at its cap. | `server_v2.py:65-95` transcript-prefix map, 20,000-entry wholesale clear. | Use authenticated session IDs from EDGE, persistent bounded mapping, and explicit collision/expiry handling. |
| P1-6 | Public/placeholder service composition exposes a broad control plane. | `docker-compose.yml` publishes 8080-8084, 9090, 3000, nginx, and Cowrie across external/internal networks; production Compose does not remove these publications. | Separate observability/admin from EDGE; bind internal services privately and test from an attacker network namespace. |
| P1-7 | Rust gateway routes expose model catalog, cost, health, and metrics without an evident auth layer. | `llm-gateway/src/main.rs:54-66,89-127,130-138`; `config.toml:120-129`. | Protect non-health endpoints, restrict metrics listener, remove wildcard CORS, and test unauthenticated/authorized behavior. |
| P1-8 | Provider and prompt trust boundaries are incomplete. | Don has a selected intel sanitizer (`ragin/don/models.py:210-237`); Hisoka assembles context from attacker history/CTI/fiction/current input (`ragin/hisoka/deceiver.py:3011-3035`). No mandatory provenance/trust label is enforced across all retrieved data. | Treat all attacker/retrieved text as data, isolate instructions, record source IDs, and test prompt-injection/poisoned-retrieval cases. |
| P1-9 | Field egress/privacy controls are procedural and incomplete in code. | `scripts/field_provision.sh` applies host firewall rules only when run; `scripts/collect_field_data.py:192-232` groups and exports `attacker_ip`/`src_ip`/`ip` and sample IPs without hashing in the collector. | Make provisioning verifiable and idempotent in deployment; hash/minimize addresses before export and test no raw IP leaves EDGE. |
| P1-10 | Audit completeness is best effort rather than a serving invariant. | `server_v2.py:393-408` swallows field-export failures; session append has no file lock; provider failures can still return generic text. | Define mandatory audit fields and decide which audit failure blocks service versus degrades safely. |
| P1-11 | JEV is still deployed/configured against historical OpenCode defaults even though future execution must not depend on it. | `ragin/jev/client.py:1-211`; `docker-compose.yml:141-173`; `scripts/deploy_azure_containerapp.sh`; no Laya integration. | Isolate/retire the old deployment path without altering historical results; implement only after the provider-neutral contract is approved. |
| P1-12 | Evidence and test documentation drift from the current worktree. | README claims 1,715 tests (`README.md:13,127`); current collection is 1,743 and emits unknown-mark warnings. Many result/session artifacts are untracked. | Pin a clean evidence snapshot, manifest inputs/results, environment versions, and scorer versions before new claims. |
| P1-13 | Several published-looking scores have known scorer or ground-truth limitations. | `results/two_channel_metrics.json` records echo-guard changes; `scripts/cti_manual_audit.py`/`results/cti_manual_audit.json` use annotator/scorer procedures; rescue benchmark uses controller-defined `gold_risk`. | Keep claims diagnostic/bounded; rerun guarded served-text and independent-label evaluations before causal or human-reliability claims. |

## P2: maintenance, performance, or documentation

| ID | Finding | Evidence | Follow-up |
|---|---|---|---|
| P2-1 | Multiple overlapping servers and Compose variants make the authoritative path unclear. | `server.py`, `server_v2.py`, LangGraph pipeline, main/field/VM/zodiac Compose/scripts. | Mark supported versus historical paths and add a single architecture contract test. |
| P2-2 | Session event files use append/fsync but no multi-writer lock. | `ragin/cycle/session.py` emit/replay implementation. | Use one writer or locking/transactional storage. |
| P2-3 | Default observability credentials and broad metrics surfaces are unsafe as operational defaults. | Main Compose Grafana default `changeme`; metrics routes/listeners in server and gateway. | Require secret injection and private observability network. |
| P2-4 | Rust gateway circuit-breaker threshold is effectively disabled for normal operation. | `llm-gateway/config.toml:87-90` uses `failure_threshold = 1000000`. | Calibrate to bounded failure budgets and test provider exhaustion. |
| P2-5 | Unknown pytest `e2e` marks and stale README counts reduce audit signal. | Collection warnings and `README.md`. | Register marks and regenerate documentation from the current manifest. |

## Explicitly not proven by this audit

- Source inspection did not prove that the public Cowrie image gives an attacker the real host shell; it did prove that the repository lacks a demonstrated AWS boundary preventing such exposure.
- No live AWS state, public IP, security group, or deployed service was inspected because the task forbade AWS contact/modification.
- No secret values were read or disclosed.
- A passing deterministic red-team test is not evidence of end-to-end serving-time enforcement when the active server path omits the verifier.
