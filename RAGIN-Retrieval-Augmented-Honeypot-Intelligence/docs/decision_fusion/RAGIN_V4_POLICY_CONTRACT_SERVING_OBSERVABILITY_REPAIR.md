# RAGIN V4 Policy Contract and Serving Observability Repair

Development-only repair. No HF-2024 evaluation, model call, network operation, or historical artifact modification was performed.

## Reconciliation

The frozen raw records resolve the prior report contradiction. The one confirmed substantive invocation was:

| Case | Arm | Selected strategy | Action | Commit |
|---|---|---|---|---|
| `donv2-final-051-36e436ebc731` | `RAGIN_V4_SUBSTANTIVE_LOGISTIC` | `low_intensity_administration` | `discover` | `accepted` |

The earlier `maximize_recon_surface` statement was an audit-report error. The raw records contain 213 low-intensity selections, one maximize-recon selection, one confirmed consumed strategy, and one observable commit. The 212 other low-intensity cases have baseline-equivalent responses but no generator, served-path, candidate, or commit trace sufficient to classify their route.

## Policy contract audit

The actual deterministic policy consumes `don_analysis.tactics`, `don_analysis.ttps_seen`, `classification`, and `severity`; it does not consume evidence IDs directly. Its exact predicates are in `ragin/decision_fusion_v4/benchmark.py:317-342`, and feature extraction for logistic policy is in `benchmark.py:345-365`.

Fresh synthetic fixtures showed that valid tactic/TTP fields propagate correctly and select the expected frozen rules. No technique IDs were fabricated or relabeled. The contract audit therefore distinguishes:

- `FEATURES_MISSING_IN_ADAPTER`: not demonstrated on synthetic fixtures; live raw records did not preserve the full policy input fields.
- `FEATURE_SEMANTICS_INCOMPATIBLE`: confirmed as a vocabulary mismatch between common Don V2 evidence IDs and the deterministic predicate set.
- `POLICY_RULE_COVERAGE_GAP`: confirmed for the observed Don V2 IDs such as `T1059.004`, `T1070.004`, `T1082`, `T1083`, and `T1105`.
- `INTENDED_BASELINE_SELECTION`: confirmed for the frozen deterministic default branch when no predicate matches.

The frozen deterministic policy was not changed.

## Proposed coverage specification

`proposed_policy_coverage_specification_v1.json` is explicitly not activated. It preserves technique semantics, treats Unix shell and file deletion as insufficient by themselves, proposes reconnaissance handling for discovery techniques, and requires containment/instrumentation for transfer behavior. Invalid, contradictory, unsupported, or insufficient evidence remains baseline fail-safe.

## Serving observability

The substantive adapter now records selected strategy, policy provenance, gate state, actual generator invocation, consumption, candidate hash, state hashes, and explicit outcome. The Harness records verifier and HITL results per attempt, fallback reason, served path, served hash, and commit event/reason. Outcomes are constrained to:

- `STRATEGY_CONSUMED_AND_SERVED`
- `STRATEGY_CONSUMED_BUT_REJECTED`
- `SAFE_FALLBACK_SERVED`
- `GENERATION_NOT_APPLICABLE`
- `EXECUTION_FAILED`

Baseline runtime response generation was not altered. Invalid evidence remains fail-safe. Rejected candidates do not commit fictional generator state.

## Synthetic validation

The fresh synthetic validation passed 144 tests and failed 0. It covered policy feature propagation, true TTP semantics, all six strategies, invalid-evidence fallback, explicit outcome traces, accepted-only commit, verifier/HITL rollback, baseline regression, and zero shell-command execution.

## Frozen artifacts and hashes

Directory: `results/decision_fusion_v4/policy_contract_serving_observability_v1/`

- `case_reconciliation.json`: `63f13b1ef2b14d5052ff430975d4f10d01590dab6bf7a99958d401265b322cb0`
- `policy_contract_audit.json`: `4466c8fe816291bf0f8e05c7a872b11314559146e43fd1b4ff2b2e93bd41c137`
- `proposed_policy_coverage_specification_v1.json`: `6dee03158a1a5d44ff3b10729413c3c0c2947096d6da6cc1599229a6db1d494c`
- `synthetic_validation.json`: `0c7b8e747d57088066b5e3b330f53a239e383b6af3b58b3b4e1dcb4f43a1c7e2`
- `sha256_manifest.json`: `2b55fa69cdbfc9e97eaac4e1949e919b5727a4ccf427a809793451aaa06c856e`

Changed source hashes:

- `ragin/cycle/adapters.py`: `83fe4152db969af8c27fc55a6a531a49e229c5a5a00106a5b880d8c3ebde0256`
- `ragin/cycle/harness.py`: `98ff76913b279a7d052f348922c8de657d2486fdc9348b318c064345fdffcb42`
- `tests/integration/test_policy_contract_serving_observability_v1.py`: `e93de0455dfaa4df0ec11d3afb18b01350eaf2b3d3a1909f0a6585b03efdbd2a`

Historical raw SHA256 remains `2e674299280764e07b153a6dd8c693d714c154a1b28ee0b56700ac1fca3f6ede`.

## Final status

- REPORT CONTRADICTION RESOLVED: YES
- DON POLICY FEATURE PROPAGATION: PASS
- POLICY RULE COVERAGE: LIMITED
- NEW POLICY DESIGN REQUIRED: YES, proposed only and not activated
- LOGISTIC SERVING TRACE: COMPLETE for new synthetic executions; historical traces remain incomplete
- LOW-INTENSITY SEMANTICS: VERIFIED on synthetic fixtures; historical 212 cases remain NOT_VERIFIABLE
- BASELINE REGRESSION: PASS
- VERIFIER/HITL/COMMIT SAFETY: PASS
- TESTS PASSED/FAILED: 144/0
- FROZEN HISTORICAL ARTIFACTS UNCHANGED: YES

Classification: `POLICY_CONTRACT_AND_SERVING_TRACES_READY`.

This is a software-contract and observability readiness result only. It makes no effectiveness or policy-superiority claim.
