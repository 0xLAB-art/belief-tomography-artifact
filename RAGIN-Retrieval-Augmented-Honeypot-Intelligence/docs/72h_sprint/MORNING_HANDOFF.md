# Morning Handoff

### 1. Executive status

- PARTIAL. APMix is no longer the active local gateway selector. It is replaced by a loopback bridge that invokes the installed OpenCode CLI directly with a deny-all tool profile. `opencode/space-bunny-free` now passes a local generated-serving smoke test; current AWS CORE remains intentionally fallback-only.
- GENERATOR: WORKING in local controlled staging with `opencode/space-bunny-free`; AWS CORE remains fallback-only because its provider URL is intentionally disabled.

### 2. What is actually running

- CORE: `ragin-core-staging` on `172.31.17.217:8443`, mTLS/API-authenticated, Chrollo/Don/Hisoka pipeline initialized.
- EDGE: Cowrie 3.1.1 on internal bridge `ragin-cowrie-internal`, reached only through `127.0.0.1:2222`; mTLS forwarder is bound to the bridge gateway and host SSH/SSM remain separate.
- Local models: no Laya weights/runtime served; provider-neutral optional assessment adapter is fixture-tested; workstation GPU is a Quadro RTX 4000 with 8 GiB.
- Internal endpoints: CORE staging private IP only; public application/deception listeners closed.

### 3. End-to-end evidence

- Fresh current provider probe: `opencode/space-bunny-free`, deny-all profile, reported cost 0, 6,228 ms, 10 output tokens. The loopback bridge returned the generated response successfully.
- Bounded provider benchmark: 3 sessions, 0 pipeline errors, 90.36 seconds total; CTI technique and actor cases were `GENERATED_VERIFIED`, while the persona case was `TEMPLATE_FALLBACK_VERIFIED`. Raw report: `results/overnight_20261009/opencode_provider_limit1.json`; provenance: `evidence/opencode_provider_benchmark_20261009.json`.
- Local server_v2 pipeline: session `ses-872e6679aaf6466e`, command `echo SPACE_BUNNY_PIPELINE_PROBE`, response `SPACE_BUNNY_PIPELINE_PROBE`, `GENERATED_VERIFIED`, `FictionConsistencyVerifier`, accepted commit, candidate digest `93612c9609b931a3a206362632e108f742b58ffecbe40f7fe72d226e7a8a1157`.
- Provider-backed flow: controlled SSH -> isolated Cowrie -> EDGE bridge -> mTLS -> Chrollo/Don/Hisoka -> verifier -> Cowrie output. Session `ses-46a0642581094765`, command `echo generated42`, provider `claude-sonnet-4-6-free`, `GENERATED_VERIFIED`, verifier pass and accepted commit, candidate digest `470489c8ce7da2ba6b722652559fdb903a3781c2cee9fc8239c2b610a50c8736`.
- Current local OpenCode Cowrie flow: isolated bridge-network Cowrie 3.0.15 -> local RAGIN server -> `opencode/space-bunny-free`; command `true` visibly returned `webapp@web-srv-01:~$`, session `ses-7d4b10c6af0c4475`, `GENERATED_VERIFIED`, verifier accepted, candidate digest `ad6289a471e2af8418db17b29a2e794995534a2985ad93f8417c9b3e82f63939`. Evidence: `evidence/opencode_cowrie_local_e2e_20261009.json`.
- Fallback flow after secret removal: `TEMPLATE_FALLBACK_VERIFIED`, verifier pass, accepted commit. Provenance was corrected in `ragin/cycle/harness.py` and covered by a regression test.
- Evidence: `evidence/opencode_space_bunny_e2e_20261009.json`, `evidence/real_generation_provider_probe.json`, `evidence/real_generation_e2e.json`, `evidence/opencode_cli_bridge_validation_20261009.json`, and `evidence/cowrie_container_isolation.json`.

### 4. Tests

- Passed: current OpenCode CLI bridge unit suite 8 tests, focused 37-test proxy/optional-assessment/security/serving/mTLS run; local OpenCode server_v2 generated-serving path; local isolated Cowrie-to-RAGIN generated-serving path; prior full suite 1,645 passed; valid/missing/invalid mTLS/API cases; public reachability timeouts; fresh CORE EIC SSH; controlled fallback benchmark with 3 sessions and no errors.
- Failed/repaired: initial Cowrie tty directory and endpoint syntax; both fixed before final smoke.
- Skipped/incomplete: encrypted storage, private CORE cutover, public port-22 Cowrie, Laya inference, broad effectiveness benchmark, and complete host/Docker default-deny egress policy.
- Not executed: Rust gateway authentication tests; no Rust test cases existed in the prior cargo command.

### 5. AWS

- Resources: existing CORE/EDGE, prepared private subnet/route table, dedicated EIC endpoint `eice-023d2c69cb6690c48`, dedicated EIC SG `sg-05f6e3f406f0c9be2`, temporary CORE staging ingress. Fresh read-only AWS refresh confirms both instances running and both SSM nodes Online.
- Boundary: current CORE still public-addressed; application listener is private-bound and not publicly reachable. EDGE public deception port remains closed.
- Storage: both current roots remain unencrypted.
- Management: existing SSH and SSM work; CORE EIC tunnel succeeded after UFW source allow.
- Cost: Cost Explorer inspected range returned 0 USD; credit balance is not exposed/verified. EIC endpoint has no endpoint charge per AWS documentation, but cross-AZ transfer can cost.

### 6. Research

- New evidence: authenticated provider-backed serving, Cowrie isolated controlled smoke, mTLS negative cases, EIC private management, fixture-tested optional assessment `NO_SIGNAL` behavior, and a fallback-only three-session benchmark. The scorer audit confirms CTI technique/actor scores can come from internal Don analysis rather than attacker-visible text.
- The new provider benchmark is bounded local staging evidence; it does not establish AWS provider reachability, independent attacker labels, or field effectiveness.
- Files: `evidence/*.json`, `CORE_DEPLOYMENT_RESULTS.md`, `COWRIE_E2E_RESULTS.md`, `MTLS_AUTHENTICATION_RESULTS.md`.
- Limitations: fallback-backed staging, no public observations, no independent attacker labels, no Laya results.
- Measurement boundary: fallback CTI echo rows score 0.0 on served text; reported 0.850 CTI rows use the separate `served_text+cti_analysis_max` channel. Persona 0.800 is deterministic structured text. No statistical or behavioral claim is supported.
- Paper: no source or historical result modified; revision notes are prepared.

### 7. Blockers

- Technical: current CORE placement and unencrypted roots remain; `ling-3.1-flash-free` and `big-pickle` remain blocked under the safe profile, while `space-bunny-free` is validated locally; AWS CORE still has no provider-backed OpenCode path; final dependency-specific host/Docker egress policy remains incomplete.
- Evaluation: matched retrieval-ablation and provider-backed assessment-disabled arms remain unexecuted; current provider-backed evidence is one separate controlled workload.
- Cost/approval: private replacement/encrypted CORE cutover may need additional EC2/EBS/snapshot resources and planned downtime.
- Public exposure: no authorization exists; public Cowrie must remain closed.

### 8. What the user should approve next

- Exact action: one replacement CORE with encrypted root in `subnet-07fae34b3db734bb2`, preserving old CORE for rollback, followed by validated cutover.
- Estimated cost: temporary EC2 plus encrypted EBS/AMI/snapshot and any transfer; obtain current price/credit confirmation immediately before creation.
- Impact: planned cutover downtime; no impact before validation because old CORE remains.
- Rollback: keep old CORE, restore old target/SG, stop only failed replacement, and retain evidence.

### 9. Next 24-hour execution plan

- First: integrity checks and bounded post-restart health validation.
- Then: if approved, create and validate encrypted private replacement; otherwise execute matched local arms C/D/E without public exposure.
- Keep the OpenCode CLI bridge separate from the fallback runtime; do not relabel the prior APMix generation evidence as OpenCode evidence.
- Run controlled fault-injection/performance experiments, freeze evidence, and prepare a separate public-exposure decision packet.
