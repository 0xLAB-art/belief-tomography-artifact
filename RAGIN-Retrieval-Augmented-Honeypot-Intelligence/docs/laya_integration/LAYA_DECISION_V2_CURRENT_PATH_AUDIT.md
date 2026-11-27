# LAYA_DECISION_MODEL_V2 Current Path Audit

Date: 2026-10-13

## Verdict

`REAL_LAYA_ADVISORY_ONLY`

The current `server_v2` path can invoke the real local Laya runtime when
`RAGIN_LAYA_ENABLED=1`, but the resulting `laya_assessment` is only attached to
the Chrollo classification event. It is not consumed by the authoritative
Hisoka strategy path, the verifier, authorization, HITL approval, or commit
gate. With Laya disabled, the current path preserves the baseline branch and
avoids the Laya inference call.

## Authoritative call graph

1. `ragin.server_v2:session_command` (lines 322-346) validates the request and
   calls `Sandbox.handle_command` in a worker thread.
2. `ragin.cycle.sandbox:Sandbox.handle_command` (lines 112-119) serializes
   access and delegates to `_handle_command_unlocked`; lines 166-169 call
   `Harness.process`.
3. `ragin.cycle.harness:Harness.process` (lines 824-830) selects the mandatory
   verified path because `server_v2:_init_pipeline` constructs `Harness` with
   `mandatory_verification=True` (lines 780-787).
4. `Harness._process_verified` (lines 401-417) emits the attacker input,
   rebuilds session context, runs classification, runs Don CTI analysis, and
   then generates a candidate.
5. `ragin.cycle.adapters:ChrolloAdapter.classify` (lines 69-129) calls the
   native Chrollo classifier and then `laya_assessment_mapper`.
6. `laya_assessment_mapper` (lines 19-60) checks the Laya flag, obtains the
   shared `LayaRuntime`, calls `LayaAssessmentAdapter.assess`, and attaches
   either `laya_assessment` with `SIGNAL` or `NO_SIGNAL` to the classification
   payload.
7. `ragin.decision.laya_runtime:LayaRuntime` (lines 130-186) lazily creates a
   revision-pinned `laya.Router` and calls `Router.predict`; this is real model
   inference in the project venv, not the historical fixture runner.
8. `Harness._run_cti_lookup` (lines 555-570) calls `DonAdapter.analyze`; the
   result is recorded as a CTI lookup event.
9. `Harness._strict_candidate` (lines 271-290) calls the Hisoka deceiver with
   the enriched context; `_enrich_context` (lines 512-517) includes the full
   classification payload, including the advisory Laya field.
10. Hisoka's existing decision reader,
    `ragin.hisoka.deception:_jev_signal_from_context` (lines 2214-2249), reads
    `jev_assessment` only. It does not read `laya_assessment`, so current Laya
    output does not select a response strategy.
11. `Harness._strict_verify` (lines 292-305) invokes the configured
    deterministic verifier. Under the server path this is the mandatory
    `HostFictionVerifier`, which wraps `FictionConsistencyVerifier`
    (`ragin.cycle.harness` lines 230-238; `ragin.graph.host_fiction` lines
    111-149).
12. On a passing verification and approval, `_strict_commit` is the only
    accepted-state commit/serve path. Failed candidates retry or use the
    verified fallback; the Sandbox returns an empty/error response when no
    verified serve exists (lines 184-217 of `sandbox.py`).

## Answers to the audit questions

| Question | Trace-backed answer |
|---|---|
| Where is real Laya initialized? | Lazily in `LayaRuntime._get_router`, reached through `laya_assessment_mapper`; the `ChrolloAdapter` constructor also creates an unused optional adapter object when enabled. |
| Is real Laya invoked today? | Yes, when the flag is enabled and Chrollo classification reaches the mapper; it calls `LayaRuntime.infer -> Router.predict`. |
| Does Laya change a workflow branch today? | No. `laya_assessment` is not consumed by the existing `jev_assessment` strategy reader. |
| Is it metadata/advisory-only? | Yes. It is attached to the classification payload and event; failures become `NO_SIGNAL`. |
| Does enabling/disabling change downstream behavior today? | No branch or commit/verifier behavior. It changes whether inference/latency and the classification metadata are present. |

## Safety boundary observed

The current path does not give Laya control over `FictionConsistencyVerifier`,
`HostFictionVerifier`, authorization, HITL approval, direct serving, or the
accepted-only state commit. V2 retains these boundaries and adds only the
pre-generation response-strategy seam.
