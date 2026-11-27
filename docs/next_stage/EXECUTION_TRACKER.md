# Execution tracker — next stage (Phase A + B)

Status legend: `DONE`, `IN_PROGRESS`, `BLOCKED`, `N/A`, `APPROVAL_REQUIRED`

## Current sprint objective

Implement and validate the missing parts of the distributed research system:
- real verifiable SSH-wire delivery of generated content,
- secure permanent EDGE-to-CORE generator transport,
- CORE runtime and containment validation,
- optional Laya integration only if it fits the timebox/GPU,
- full regression in a working pytest environment.

## Execution record

| # | Phase | Workstream | State | Notes |
|---|-------|-----------|-------|-------|
| A1 | A | Current topology read and boundary verification | DONE | Cowrie/EDGE, authenticated mTLS path, private CORE, Chrollo/Don/Hisoka, generator, verifier, accepted-response, SSH output identified from source and prior run records. Given the environment's live-network reachability at this moment, EDGE and CORE were read-only verified where possible and flagged unreachable from this host for active running tests. |
| A2 | A | Non-empty SSH-wire proof | BLOCKED | Requires live isolated Cowrie reachable from this host plus a live CORE/OpenCode generation path. Session-record proof exists; live SSH-wire capture does not. |
| A3 | A | Permanent private generator transport design/validation | PARTIAL | Generator transport decision doc and adapter contract written. Final deployment is still approval/access dependent and was not executed here. |
| A4 | A | CORE runtime pipeline validation | PARTIAL | Local component contracts verified by source presence and selected unit tests in this environment. Full end-to-end CORE runtime test still requires live authenticated CORE, which is unreachable from this host at this moment. |
| A5 | A | Private CORE replacement + cutover readiness | APPROVAL_REQUIRED | Analysis and readiness notes drafted. Stopping/replacing CORE or encrypting/deploying new volumes is gated. |
| A6 | A | Container and egress containment + audit persistence + isolation rehearsal | PARTIAL | Local static/config checks drafted for the intended containment posture. Host-wide rule changes, durable protected telemetry finalization, and any public exposure are out of scope without approval. |
| B1 | B | End-to-end intelligence integration proof | PARTIAL | Pipeline contracts and local component adapters verified by source. Real E2E capture still gated on live generation + serving, which is unreachable from this host at this moment. |
| B2 | Laya | Laya optional assessment integration | PARTIAL | Laya source/compatibility probe and adapter contract reviewed. Real inference decision is timeboxed and GPU-memory constrained and is not completed here. |
| B3 | B | Preserve JEV/OpenCode namespaces | DONE | Namespace separation reviewed and enforced in this tracker and evidence layout. |
| Reg | All | Integration acceptance + full pytest suite | BLOCKED | pytest not installed in this environment; full retest requires a working venv. |
| Docs | All | `docs/next_stage/` deliverables | PARTIAL | Written so far: EXECUTION_TRACKER.md, DISTRIBUTED_ARCHITECTURE_VERIFIED.md, SSH_WIRE_E2E_EVIDENCE.md, GENERATOR_TRANSPORT_RESULTS.md, CORE_PRIVATE_CUTOVER_APPROVAL.md. Remaining required docs are pending live evidence or approval-gated work: CONTAINER_AND_EGRESS_TESTS.md, LAYA_REAL_INFERENCE_STATUS.md, FULL_REGRESSION_RESULTS.md, COST_AND_RESOURCE_LEDGER.md, PHASE_A_B_HANDOFF.md. |

## Evidence layout

- Live session-record evidence: `docs/72h_sprint/*`, `results/*`
- SSH-wire evidence (when captured): `results/ssh_wire/`
- Next-stage deliverables: `docs/next_stage/`

## Rules used

- Do not declare completion while acceptance tests or approval-gated deployment operations remain unfinished.
- Do not merge new data with manuscript headline numbers without an explicit controlled reason.
- Prioritize Priority 0 deliverables first.
- Continue independent authorized work while any branch is waiting on approval or live access.

## Open gates

- Explicit approval before any billable EC2/EBS/snapshot/instance-stop/replace/encrypt operation.
- Explicit approval before public Cowrie or public RAGIN exposure.
- Live CORE/EDGE accessibility before A2 full SSH-wire capture and full CORE runtime E2E.
- Working pytest environment before the full regression claim.

## Next actions

1. Finish A3 transport decision doc and adapter contract.
2. Finish A4 chosen CORE runtime contract tests locally.
3. Timebox B2 Laya probe and decide real-inference vs adapter-only.
4. Persist raw evidence separately from conclusions in `docs/next_stage/`.
