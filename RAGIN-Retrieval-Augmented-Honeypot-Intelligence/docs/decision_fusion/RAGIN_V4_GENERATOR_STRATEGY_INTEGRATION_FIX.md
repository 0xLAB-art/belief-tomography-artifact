# RAGIN V4 Generator Strategy Integration Fix

Status: implementation freeze v1. This is a software correction, not an effectiveness experiment.

## Defect and correction

`DeceptionGraph.plan_node` and `generate_node` already carried the V4 `policy_decision` into the generation context. The defect was at `AdaptiveDeceiver.generate_response`: it derived `response_strategy` only from the legacy Jev/Laya signal. V4 decisions therefore reached context but not `ResponseGenerator.generate`, and the deterministic template path emitted identical matched bytes.

The generator boundary now recognizes only `RAGIN_V4_DETERMINISTIC` and `RAGIN_V4_LOGISTIC` as V4 arms. For those arms, `selected_response_strategy` is authoritative and legacy Jev/Laya fields cannot override it. Unsupported values fail closed to `baseline`. Non-V4 calls retain the existing Jev/Laya behavior. Gateway fallback and local-template paths preserve the selected strategy.

The six non-baseline frozen strategies are supported by existing safe template behavior: each appends a bounded, fabricated transcript suffix. No attacker input is executed, no real secret is exposed, and no infrastructure is altered.

## Traceability contract

The implementation records strategy source, selected strategy, delivery to the generator, template consumption, template ID, and fallback reason in synthetic V4 traces. Response hashes are computed exactly from returned response bytes. Verifier and commit fields are `NOT_RUN_SYNTHETIC_GENERATOR_ONLY` for generator-only fixtures; they are not inferred. The graph-level controlled tests retain mandatory deterministic verification, approval, retry, and accepted-only commit gates.

## Controlled validation

The focused suite passed 170 tests with zero failures. It covers unchanged baseline behavior, deterministic and logistic V4 delivery, Jev/Laya override prevention, unsupported-strategy fallback, invalid-evidence fallback, verifier/HITL requirements, inert command handling, all six template-conditioned strategies, and exact synthetic response-hash differences. These are wiring checks only and make no effectiveness or superiority claim.

## Freeze and provenance

Changed implementation paths and SHA256 values are recorded in [the machine-readable freeze](../../results/decision_fusion_v4/v4_generator_strategy_wiring_fix_v1.json). The existing holdout and raw execution freeze remain unchanged. The worktree is uncommitted, so commit status is `NOT_OBSERVABLE_UNCOMMITTED_WORKTREE`.

## Future-cohort feasibility

Metadata-only inspection excluded all 240 previously selected source groups and all 59 normalized ordered command-sequence families represented by them. Of 6,658 source sessions and 1,458 total normalized families, 1,399 new unique normalized command families remain across 1,489 sessions. No new cohort was selected and no arm was executed. Any future redesigned evaluation must be registered separately as post-hoc development followed by fresh validation.

## Final status

WIRING FIXED: YES  
POLICY ENGINE CHANGED: NO  
BASELINE REGRESSION: PASS  
V4 STRATEGY CONSUMED: PASS  
VERIFIER SAFETY: PASS  
TESTS PASSED: 170  
TESTS FAILED: 0  
NEW ELIGIBLE UNIQUE COMMAND FAMILIES: 1399  
EXISTING RAW FREEZE UNCHANGED: YES
