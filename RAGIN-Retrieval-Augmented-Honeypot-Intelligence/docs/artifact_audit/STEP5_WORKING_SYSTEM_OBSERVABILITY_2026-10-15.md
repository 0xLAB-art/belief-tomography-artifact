# Step 5 — Working-System Observability and Correctness Gaps

Date: 2026-10-15. Plan: `docs/PAPER_REMAINING_STEPS_2026-10-14.md` §Step 5.
Evidence root: `results/step5_working_system_observability_v1/` (frozen: `sha256_manifest.json`, 24 files).
Runner: `scripts/run_step5_working_system_observability_v1.py` (`run` / `audit` / `freeze`).
Focused tests: `tests/integration/test_step5_commit_observability_v1.py`.

## Subject

Exercise the complete active serving path — Don evidence export, judge/filter, gate, policy, substantive generator, mandatory verifier, HITL, commit, final serving — close the observability/correctness gaps that V4 exports exposed, and demonstrate the Step 5 gate: every served turn has an observable verifier/approval/commit disposition; fallback and no-op state events are explicit; missing commit metadata is never filled by inference; no unverified serve, unauthorized commit, unsafe evidence promotion, or arm-state leakage; response differences survive removal of decorative markers; focused tests plus a classified broad regression.

## Active path exercised (13 cases / 17 turns, 0 crashes, 0 expectation failures)

Real components end to end: `ChrolloAdapter` (real classifier, offline), `DonAdapter` → `build_evidence_bundle` (the real export path) → `DeterministicEvidenceJudge` / `filter_judged_evidence` → `EvidenceQualityGate` → `DeterministicPolicySelector` → `SubstantiveStrategyAdapter` + `StrategyAwareDeceptionGeneratorV1` → `FictionConsistencyVerifier`/`HostFictionVerifier` → `ApprovalGateway` → fiction/host commit with disk persistence → serving via `Harness.process` (16 turns) and `Sandbox.handle_command` (1 turn). Baseline case uses the real `ThreatRAGEngine` offline BM25 retrieval over `data/corpus/`; evidence-condition cases use controlled fixture documents through the real export/judge/gate/policy code (component identities recorded per record). Provider-unavailable is exercised with a closed gateway port.

| case | turns | gate_state / reason | strategy | outcome | served | commit dispositions (per attempt) |
|---|---|---|---|---|---|---|
| baseline_flags_off (judge/filter OFF, incl. Sandbox turn) | 3 | no policy stage (RAGIN_BASELINE) | n/a | VERIFIED_SERVED | yes | accepted |
| supported_evidence | 1 | VALID_EVIDENCE / validated_bundle | maximize_recon_surface | STRATEGY_CONSUMED_AND_SERVED | yes | accepted |
| partial_only_evidence (judge ON, filter OFF) | 1 | LOW_RELEVANCE / evidence_judge_insufficient | baseline | GENERATION_NOT_APPLICABLE | yes | accepted |
| irrelevant_evidence | 1 | NO_EVIDENCE / no_relevant_documents | baseline | GENERATION_NOT_APPLICABLE | yes | accepted |
| conflicting_evidence | 1 | UNRESOLVED_CONFLICT / evidence_judge_filter_conflicting | baseline | GENERATION_NOT_APPLICABLE | yes | accepted |
| missing_provenance | 1 | INVALID_PROVENANCE / invalid_or_unknown_provenance | baseline | GENERATION_NOT_APPLICABLE | yes | accepted |
| model_timeout (generator raises TimeoutError) | 1 | VALID_EVIDENCE / validated_bundle | maximize_recon_surface | SAFE_FALLBACK_SERVED | yes | not_attempted ×3 (`generation_failed:generator_exception:TimeoutError`), then accepted |
| malformed_output (candidate without response_text) | 1 | VALID_EVIDENCE / validated_bundle | maximize_recon_surface | SAFE_FALLBACK_SERVED | yes | not_attempted ×3 (`verification_failed`), then accepted |
| verifier_rejection (rejects every candidate incl. fallback) | 1 | VALID_EVIDENCE / validated_bundle | maximize_recon_surface | not served | no | not_attempted ×4, error `verified_serve_unavailable` |
| hitl_require_no_approval (REQUIRE, no approver) | 1 | VALID_EVIDENCE / validated_bundle | maximize_recon_surface | not served | no | not_attempted ×2 (`approval_not_granted`), error `verified_serve_unavailable` |
| fallback_invalid_evidence (malformed bundle) | 1 | RETRIEVAL_FAILURE / malformed_bundle | baseline | GENERATION_NOT_APPLICABLE | yes | accepted |
| persistence_restart (turns 1–2, restart, turn 3 via Sandbox) | 3 | VALID_EVIDENCE / validated_bundle | maximize_recon_surface | STRATEGY_CONSUMED_AND_SERVED | yes (all) | accepted |
| rejected_update_rollback (generator refuses commit) | 1 | VALID_EVIDENCE / validated_bundle | maximize_recon_surface | SAFE_FALLBACK_SERVED | yes | rejected ×3 (`generator_commit_rejected:synthetic_commit_rejected`), then accepted |

Judge outputs matched the designed evidence conditions exactly (recorded per record): `SUFFICIENT/direct_behavior_support` [SUPPORTED]; `INSUFFICIENT/partial_support_only` [PARTIAL]; `INSUFFICIENT/no_substantive_support` [IRRELEVANT]; `CONFLICTING/supported_and_contradictory_evidence` [SUPPORTED, CONTRADICTORY]; missing provenance [UNKNOWN, gate INVALID_PROVENANCE]. Baseline provider block records `gateway_fallback=true`, `template_id=lookup`, `template_fallback_reason=no_gateway` (real provider-unavailable evidence). Persistence: `SESSION_RESUME` in turn 3, attacker inputs 1→3, pinned identity identical across restart, promoted host facts preserved. Rollback: before==after state hashes, generator visits 0, pending 0, on-disk host store byte-equal to the rolled-back in-memory store.

## Required evidence per turn (coverage: PASS, 0 missing across 17 records)

15 field groups × 17 records — all present or explicitly N/A with a recorded reason (state hashes on accepted/rejected commits are additionally enforced per attempt by INV08, all 17 records):

| field group | present | explicit N/A (reason) |
|---|---|---|
| correlated request/session/turn/case/arm IDs | 17 | 0 |
| source/config hashes (22 files + env + corpus + git head) | 17 | 0 |
| input/context hashes | 17 | 0 |
| retrieval query/corpus/document IDs | 16 | 1 (`bundle_missing_retrieval_section` — malformed bundle) |
| judge identity and outputs | 13 | 4 (3 × `judge_flags_off_explicit` baseline; 1 × `bundle_bypassed_export_path_malformed`) |
| before/after policy-visible evidence | 14 | 3 (baseline arm — no policy stage) |
| gate reason | 14 | 3 (baseline arm) |
| selected strategy | 14 | 3 (baseline arm) |
| generator consumption | 14 | 3 (baseline arm — no strategy generator) |
| generated and final served hashes | 17 | 0 |
| verification / retries / fallback | 17 | 0 |
| approval | 17 | 0 |
| commit dispositions (every attempt) | 17 | 0 |
| per-stage + end-to-end latency | 17 | 0 |
| provider/model identity + errors | 17 | 0 |

## Invariants (audit: PASS — 13/13 over 17 records)

- **INV01** every declared scenario expectation observed (gate state, outcome, dispositions — proves each scenario exercised its intended condition).
- **INV02** every served turn: verifier passed + accepted, HITL approved, commit disposition `accepted` (no unverified serve).
- **INV04** no commit accepted without a passing verifier verdict and approved HITL on that attempt (no unauthorized commit).
- **INV05** policy refs ⊆ gate-valid IDs; non-VALID gate never consumes a strategy or selects non-baseline; VALID gate selects one (no unsafe evidence promotion).
- **INV06** baseline records carry no V4 policy stage/engine; V4 records carry exactly their own arm's policy stage (no arm-state leakage).
- **INV07** gate-valid IDs, judge-filter visible IDs, policy-visible before/after, bundle SHA (record vs policy `evidence_bundle_sha256`), build-time gate preview vs policy-time re-evaluation, and consumed strategy all agree.
- **INV08** every attempt has an explicit disposition (`accepted`/`rejected`/`not_attempted`) with reason; accepted/rejected carry before/after graph state hashes consistent with the state-effect label (`state_changed` / `no_op_state_unchanged` / `not_committed`).
- **INV09** fallback turns carry an explicit fallback reason; no-op commits are labeled explicitly and consistently.
- **INV10** no attempt leaves commit metadata as the `NOT_VERIFIABLE` sentinel (nothing filled by inference).
- **INV11** baseline vs supported-evidence responses still differ after stripping the first (decorative) line: stripped SHA256 `4f3d2c5a…` vs `9019e919…`.
- **INV12** restart continuity (SESSION_RESUME, turn count, identity/fact persistence, served with full dispositions).
- **INV13** rejected update: fiction restored (before==after), host restored **and persisted to disk**, generator untouched, fallback commit accepted.
- **INV14** a non-served turn records an explicit error and never leaves an accepted commit.

All 15 explicit no-op state events are recorded as `no_op_state_unchanged` with equal state hashes (req-0001…req-0010, req-0013…req-0017); no commit in these scenarios changed fiction state — the seeded identity plus template responses establish no new fiction facts. Both other dispositions are represented: rejected (rollback case) and not_attempted (verifier/HITL/timeout cases).

## Observability gaps closed (`ragin/cycle/harness.py`)

1. **Explicit commit disposition per attempt.** `_strict_commit` now returns a disposition dict (`committed`, `commit_event`, `commit_reason`, `commit_state_effect`, `commit_graph_before_sha256/after`) instead of a bare bool; every attempt path — accepted, generator-rejected, approval-denied, verification-failed, generation-failed, fallback — writes `commit_event`/`commit_reason` explicitly. The `NOT_VERIFIABLE` sentinel no longer survives a resolved turn (INV10).
2. **State hashes on every commit.** Fiction-graph digests (canonical SHA256 of `FictionGraph.summary()`) recorded before/after each commit transaction; the labels are checked against the hashes, so no-op vs changed vs rolled-back is machine-verifiable. Also surfaced in `result.verification` (turn-level, not just attempt-level).
3. **Rejected-commit rollback is persisted.** The host store was promoted and saved before the generator commit; a rejection restored memory but left the promoted state on disk (a restart could resurrect the rejected update). The rollback branch now re-saves `host_fiction_path`; proven by INV13 (`host_file_matches_memory=true`).
4. **Fallback attempt trace emitted after its dispositions.** The fallback `RESPONSE_GENERATE` event previously fired before verifier/HITL/commit ran, so events could not show why the fallback served or failed; it now fires once, after, carrying the full disposition set.
5. **Provider/generator errors surfaced.** `_serving_attempt` records `generation_error` (e.g. `generator_exception:TimeoutError`), so a generation failure is distinguishable from a verification failure in the trace.
6. **Honest serve labeling.** Metadata-less candidates (baseline/Hisoka arm) were labeled `STRATEGY_CONSUMED_AND_SERVED` by default — a V4 claim on a baseline turn. Now `VERIFIED_SERVED`.
7. **Fail-closed commit exceptions with recorded evidence.** A commit-time exception (host promote/persist — durability unknown) restores state, attaches the explicit rejected disposition (with hashes) to the exception, records the attempt trace to the event log, best-effort discards the pending candidate, and aborts the turn with `verified_serving_failed` — never a fallback serve after a durability failure. A *clean* generator rejection (`committed=false`) still fail-safes to the verified fallback template (SAFE_FALLBACK_SERVED), with the rollback persisted.
8. **Discard cleanup hardened.** A failing best-effort `commit_candidate(..., verifier_passed=False)` cleanup is suppressed so it cannot destroy turn observability or block the fallback path.

## Focused tests (6 new, all passing)

`tests/integration/test_step5_commit_observability_v1.py`: accepted-commit disposition + graph hashes; verifier-rejected → `not_attempted:verification_failed` with not-evaluated HITL; HITL REQUIRE → `not_attempted:approval_not_granted`, no serve; generator-commit rejection → rollback persisted to disk + fallback served; commit exception → fail closed with recorded disposition; multi-attempt turns give every attempt a disposition.

Targeted set (new + Step 3/4/5 integration + cycle/policy/serve-provenance + verified-serving security): **100 passed**. Focused suite (`tests/unit tests/integration tests/security`): `24 failed, 1852 passed, 11 skipped, 37 warnings, 15 errors` — every failure pre-existing (see classification).

## Broad regression, recorded and classified

| run | file | summary |
|---|---|---|
| baseline (pre-change, captured earlier this session) | `tests/regression_baseline_prechange.txt` | 24 failed, 1847 passed, 116 skipped, 15 errors |
| post-change full suite | `tests/regression_post.txt` | 24 failed, 1853 passed, 116 skipped, 15 errors |
| post-change focused set | `tests/focused_post.txt` | 24 failed, 1852 passed, 11 skipped, 15 errors |

Classification (`tests/failure_classification.json`): **zero new failures, zero resolved** — the failing test IDs are 1:1 identical to the pre-change baseline; +6 passed = the 6 new Step 5 tests. Pre-existing failures are grouped and unrelated to the tested path: hisoka_memory (22), readiness metrics (2), TTP extraction fixtures (8 errors), pipeline integration (5 errors), gateway config (2 errors), Laya confirmatory (1), verifier red-team oracle (1). Exit code 1 on both runs is due solely to these pre-existing failures.

**Regression found and resolved on the tested path (not suppressed).** The first commit-exception implementation converted exceptions into recoverable rejections, so a disk-full failure could fall through to a fallback serve — caught by `tests/security/test_task2_verified_serving.py::test_persistence_failure_is_safe` (new failure vs baseline). Root cause fixed at the source (exceptions fail closed, disposition recorded then re-raised — gap 7 above); the security test passes, and the final regression diff shows zero new failures.

## Artifacts

| path | contents |
|---|---|
| `results/step5_working_system_observability_v1/turn_records.jsonl` | 17 per-turn evidence records (full schema above) |
| `…/run_manifest.json` | protocol, scenarios, source/config/corpus hashes, git head, crashes, expectation failures |
| `…/audit/evidence_coverage.json` | per-field coverage (PASS) |
| `…/audit/invariants.json` | 13 invariants + violations (PASS) |
| `…/audit/expectations.json` | 17 scenario expectation checks (PASS) |
| `…/tests/*` | baseline + post regression outputs, focused output, `failure_classification.json` |
| `…/sessions/<case>/*.jsonl` | durable session event logs incl. restart resume |
| `…/host_store/*.json` | host fiction files incl. rollback-persisted store |
| `…/sha256_manifest.json` | SHA256 of all 24 files |

## Limitations (stated, not inferred)

- Evidence-condition cases use controlled fixture documents; the export, judge, filter, gate, policy, generator, verifier, HITL and commit code is real (component identities recorded per record). The baseline case uses the real corpus/engine offline.
- Only the deterministic policy arm is exercised (the required scenarios do not arm-specify); logistic arm selection is Step 6 protocol territory.
- Per-stage latency is measured at event boundaries (`since_prev_ms` in each record) plus `total_time_ms`/sandbox `processing_time_ms` — not in-process timers.
- Provider behavior is exercised as gateway-unavailable (closed port); no live model provider was called.
- Per-session fiction graphs and generator state are in-memory by design (fresh graph under policy `per_session`); durable across restart are the event log, pinned identity, promoted host facts and verified flags — recorded as such in the persistence record.
- No commit in these scenarios changed fiction state (all accepted commits are explicit no-ops); `state_changed` commits were not observed here.

## Gate status

Step 5 outputs complete: all 11 required scenarios exercised with per-turn evidence, coverage/expectations/invariants PASS, focused tests green, broad regression recorded with zero new failures classified, the single on-path regression resolved at its root cause. Ready for Step 6.
