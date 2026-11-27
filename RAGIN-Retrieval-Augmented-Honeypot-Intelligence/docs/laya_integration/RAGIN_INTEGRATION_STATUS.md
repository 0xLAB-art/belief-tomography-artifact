# RAGIN Integration Status (Laya optional assessment)

Date: 2026-10-12.

## Files changed / added

| file | change |
|---|---|
| `ragin/decision/laya_runtime.py` | NEW — real local inference runtime: lazy `Router` build, offline-first, revision-pinned, Jev-wire-compatible payload |
| `ragin/chrollo/pipeline.py` | `process_with_jev` now serves the optional assessment from Laya when `RAGIN_LAYA_ENABLED=1`; Jev stays the default when disabled |
| `tests/unit/test_optional_assessment.py` | existing fixture contract tests, still green |
| `tests/integration/test_laya_real_model.py` | NEW — 4 model-backed integration tests (real weights, skip if missing) |
| `scripts/laya_real_inference_pilot.py` | NEW — reproduces the real inference pilot |
| `scripts/laya_ablation_analysis.py` | NEW — recomputes ablation metrics from raw records |

Adapter class reused unchanged: `ragin/decision/optional.py::LayaAssessmentAdapter`
(existing file; this session wired a real provider behind it rather than duplicating it).

## Architecture placement

```
SSH session / command
  → Chrollo classification
  → optional assessment  ← RAGIN_LAYA_ENABLED=1 serves this via LayaRuntime (local, in-process)
  │                         (Jev endpoint remains the provider when the flag is 0)
  → Don intelligence
  → Hisoka generation (unchanged; Laya never generates)
  → mandatory deterministic verifier (unchanged)
  → HITL where required (unchanged)
  → accepted commit → served response
```

Laya never: generates attacker-visible output, replaces Hisoka, replaces
FictionConsistencyVerifier or HostFictionVerifier, mutates fiction state, introduces a
serving route, or bypasses HITL. Failure of the assessment block returns the
classification unchanged (advisory path catches everything).

## Behavior contract

- `RAGIN_LAYA_ENABLED` defaults to `0`: pipeline behavior is byte-identical to baseline
  (unit suite confirms; the flag gate returns `None` and Jev path is untouched).
- `RAGIN_LAYA_ENABLED=1`: successful inference attaches an advisory
  `jev_assessment` dict with `provider: "laya"`; the typed answers are the same
  noul/choice/score schema Jev produced, so downstream consumers need no change.
- Any failure (missing weights, import error, invalid output, timeout) →
  `NO_SIGNAL` with the error recorded; never interpreted as benign/malicious.
- Timeouts: `RAGIN_LAYA_TIMEOUT_S` (default 30 s) enforced via the adapter's
  ThreadPoolExecutor contract.
- Env knobs: `RAGIN_LAYA_MODEL` (default `english`), `RAGIN_LAYA_REVISION`
  (default `55cf4c4…`), `RAGIN_LAYA_DEVICE` (default `cpu`).

## Test categories (distinct, as required)

1. **Fixture contract tests** (`tests/unit/test_optional_assessment.py`): 3 passed —
   enabled-vs-disabled, timeout→NO_SIGNAL, malformed provider→NO_SIGNAL.
2. **Model-backed integration tests** (`tests/integration/test_laya_real_model.py`):
   4 passed — real weights load, real forward pass through the runtime and adapter,
   provenance/revision assertions, env gate behavior. Skips cleanly when the weights or
   package are absent.
3. **Full regression**: `tests/unit` 1556 passed, 1 failed —
   `test_verifier_redteam_security_oracle::test_oracle_validate_passes`. Verified
   pre-existing and unrelated: fails identically on a stashed clean tree
   (oracle fixture lacks a `should_pass` cohort; modified oracle script is part of an
   earlier session's uncommitted work, not this session's changes).

## What is still open

- `server_v2.py` does not yet expose a Laya toggle through its own config surface
  (the pipeline seam is the integration point this session; server wiring was not
  changed to keep the diff minimal).
- Cowrie/history-derived evaluation set with independent labels (see
  MATCHED_ABLATION_RESULTS.md limitations).
