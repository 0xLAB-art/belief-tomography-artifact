# v12 no-rerun recovery — executed repairs and independent recomputation

Date: 2026-10-17. This document records the engineering work completed under
the no-rerun constraint after ``LAYA_V12_NO_RERUN_RECOVERY_AUDIT.md`` and
``LAYA_V12_NO_RERUN_STATUS.md``. No training, inference, or confirmatory
evaluation was run. All frozen weights, labels, gates, predictions, and
reports are byte-identical (results SHA256
``140cbf58ce9b42b6e92519cc1b289a767d8d87f42b7a6447c79669b82c9c63a8``;
verified again by the recomputation script below).

**The v12 outcome is unchanged: `TUNING_FAIL_REDESIGN_REQUIRED`.** None of the
repairs below changes any saved prediction, gate value, or classification, and
none of them upgrades the failed checkpoint to a validated pass.

## Repairs implemented (audit findings 1–4 now closed)

| # | Audit finding | Repair | Files |
|---|---|---|---|
| 1 | Malformed `stage.choice` (unhashable) escaped the fail-safe boundary | Membership test requires a string before stage lookup; unhashable values normalize to unknown | `ragin/decision/laya_decision.py` |
| 2 | Finite-but-out-of-domain probabilities/confidence/severity accepted | Bounded-number validation: attack probability and confidence in [0, 1], severity in [0, 3]; booleans, NaN, infinities rejected | `ragin/decision/laya_decision.py` |
| 3 | Per-request executors let timed-out callables pile up unboundedly | Shared `BoundedWorker` (`ragin/decision/bounded_worker.py`): one process-wide executor, semaphore-bounded admission, explicit `busy` outcome routed to baseline fallback / `NO_SIGNAL`; the slot is held until the callable actually finishes (released exactly once via done-callback), so a timeout can never widen the concurrency bound. No thread cancellation is claimed. | `ragin/decision/bounded_worker.py`, `laya_decision.py`, `optional.py` |
| 4 | Recorded `input_sha256` hashed the pre-truncation state while the model saw truncated text; both truncators could exceed the advertised bound by 3 characters | Shared `bound_state()` (`ragin/decision/state_bounds.py`) counts the `...` marker inside the bound; used by both adapters and the runtime; decision events now record `source_state_sha256`, `effective_input_sha256`, `input_truncated`, and truncation policy/lengths in provenance | `ragin/decision/state_bounds.py`, `laya_decision.py`, `optional.py`, `laya_runtime.py` |

## Verification

- New synthetic regression tests (no model, no network):
  `tests/unit/test_laya_bounded_worker.py` — bound-state invariants, admission
  bounding under concurrency, timeout-holds-slot-then-recovers, busy fallback
  at both adapter seams, source/effective digest separation.
- Targeted suites: 53 passed (`test_laya_bounded_worker.py`,
  `test_laya_payload_domains.py`, `test_laya_decision_v2.py`,
  `test_optional_assessment.py`).
- Full `tests/unit`: 1724 passed. The remaining 2 failures and 9 errors
  (gateway `sample_gateway_config` fixture, TTP-extraction fixtures,
  `rater_labels` on-disk state, verifier-oracle cohort labels) reproduce on a
  pristine tree with all changes stashed and are recorded in earlier regression
  baselines; they are unrelated to these repairs.

## Independent gate recomputation (pure data)

``scripts/laya_v12_independent_gate_recompute_v1.py`` re-derives every
G1–G8 / I1–I3 gate from the saved primary (run_index 1) predictions using its
own schema parsing, caller-rule, and metric implementations, cross-checking
per-call flags, recorded metrics, failed-gate lists, the final decision, and
the results-file SHA256 against the frozen protocol/decision artifacts.

Result: **AGREE** (exit 0) — zero mismatches. Both arms reproduce exactly:
candidate fails G4 (0.7857 < 0.9), G5 (0.125 > 0.1), G7 (0.2812 < 0.8),
G8 (0.7188 < 0.9), and I2 (0.1667 > 0.1); the recorded classification
`TUNING_FAIL_REDESIGN_REQUIRED` is independently reproduced. This confirms the
recorded arithmetic; it does not alter the outcome.

## Boundary statements

- The runtime repairs are safety/provenance engineering. They do not establish
  behavioral performance for the v12 checkpoint, and the optional decision
  path remains unvalidated for deployment.
- The earlier "untouched heads" explanation for strategy/reference drift was
  retracted: the saved predictions support task interference through the
  shared encoder/scorer, but do not isolate its causal contribution.
- Any future behavioral validation requires the user to explicitly lift the
  no-rerun restriction; nothing here authorizes it.
