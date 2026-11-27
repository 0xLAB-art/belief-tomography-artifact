# LAYA Decision Model V2b Primary Raw Execution

This record documents the chronology and procedural boundary of the final
primary 169-case blind matched A/B execution. It is a raw-execution record,
not an effectiveness analysis.

## Chronology

1. V2 preregistration established the frozen Laya decision policy, matched
   arms, holdout selection, and deferred effectiveness analysis.
2. The exploratory 120-case execution was retained as exploratory only.
3. The initial inert-treatment manipulation was identified as a structural
   failure because the selected strategy did not reach the generator.
4. The V2a implementation correction established the strategy-consumption
   path and the lossless long-input transport amendment.
5. The first blind primary execution attempt began from case 1.
6. That attempt completed 100 matched pairs and stopped at the long-input
   procedural boundary; its outputs remain preserved as aborted artifacts and
   were not used as primary results.
7. No reference labels were accessed or created, and no effectiveness
   analysis was run for the aborted attempt.
8. A CommandEntry semantic audit established that one full attacker command
   cannot represent the long transcript without violating the normal command
   boundary.
9. The V2b correction moved the full evaluation representation to
   `SessionLog.raw_log`, with a frozen 16,384-character bound and no lossy
   transformation.
10. Before model execution, the V2b run verified the frozen hashes, exact
    holdout IDs, real Laya runtime identity, arm isolation, and 169/169
    lossless input representations.
11. The complete 169-case execution restarted from case 1 under one uniform
    V2b implementation. Baseline and treatment were run in fresh per-case
    session directories with state reset between arms and cases.
12. Raw baseline outputs, treatment outputs, Laya decision events, structural
    completion, and manipulation-delivery artifacts were frozen after 169/169
    pairs completed.
13. Only after the raw execution freeze was verified, the blind annotation
    source and blindness audit were created.

## Procedural outcome

- Planned cases: 169
- Baseline completed: 169
- Treatment completed: 169
- Previous V2a pairs reused: no
- Reference labels accessed: no
- Reference labels created: no
- Effectiveness metrics computed: no
- McNemar run: no
- Bootstrap run: no
- Raw execution freeze: `results/laya_decision_v2/primary_169_raw_execution_freeze_v2b.json`
- Blind annotation source: `results/laya_decision_v2/primary_169_blind_annotation_source_v2b.json`
- Blindness audit: `PASS_NO_MATERIAL_LEAKAGE`

The preserved aborted attempt is procedural history only and is not merged
with, resumed into, or interpreted as part of the V2b primary results.
