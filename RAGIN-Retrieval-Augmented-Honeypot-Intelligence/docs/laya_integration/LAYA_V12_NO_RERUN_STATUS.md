# v12: preserved outcome and no-rerun work boundary

Execution of the permitted recovery work (verified repairs, regression tests,
independent gate recomputation) is recorded in
``LAYA_V12_NO_RERUN_RECOVERY_EXECUTION.md``. The recomputation agrees with
every recorded gate and the fail classification; the outcome below is
unchanged.

## Outcome

The development recipe was selected, final fit completed, and the single
confirmatory run completed 216 calls. The confirmatory classification is
`TUNING_FAIL_REDESIGN_REQUIRED`. This is not a successful decision-layer
validation or a production deployment authorization.

Candidate EV metrics: alignment 0.85; required-abstain recall 0.7857;
inappropriate abstention 0.125; strategy compatibility 0.2812; reference
compatibility 0.7188. Structural metrics are 1.0. Injection target adoption
is 0.1667; injection oracle agreement is 0.875.

## Verified diagnosis

`scripts/laya_v12_saved_prediction_audit.py` reads existing predictions only.
Its output distinguishes raw task performance from caller enforcement:

| Saved prediction count | Base | Tuned |
|---|---:|---:|
| Correct evidence states / 60 | 35 | 51 |
| Correct raw strategy choices on sufficient cases / 32 | 12 | 10 |
| Correct raw reference choices on sufficient cases / 32 | 24 | 25 |

Strategy predictions changed on 24/60 cases and references on 27/60.
Laya's `DecisionModel` uses a shared encoder, transformer head, and scorer;
state-only supervision does not leave separate strategy/reference heads
untouched. The previous explanation that those heads stayed at their base
behavior was incorrect. The saved predictions support task interference,
but do not isolate its causal contribution from other training changes.

## Post-audit saved-output decomposition and design-only artifacts

All saved-output only; no frozen artifact, gate, label, or prediction changed.

- `scripts/laya_v12_coupling_decomposition_v1.py` quantifies how much of G7/G8
  failure is the caller-rule coupling described above versus genuine choice
  error: coupling costs 1 strategy case and 2 reference cases out of 32
  sufficient cases; the *decoupled raw* rates are 0.3125 (G7) and 0.7812 (G8),
  both still below their frozen thresholds. Decoupling alone therefore cannot
  rescue G7/G8; the dominant cause is incompatible strategy/reference
  selection. This narrows — it does not remove — the open causality question:
  coupling is now isolated, other training changes are not.
- `ragin/decision/evidence_quarantine.py` (+`tests/unit/test_evidence_quarantine.py`):
  serving-path input quarantine keyed on directive structure, neutralizing
  12/12 frozen injection directives while touching 0/525 clean evidence fields.
- `ragin/decision/retrieval_contract.py` (+`tests/unit/test_retrieval_contract.py`):
  the explicit versioned retrieval-evidence adapter audit finding 5 said an
  integration would require — decoupled per-question fail-safe decoding,
  mechanical frozen caller-rule enforcement, quarantine integration, and an
  activation-boundary test keeping it unwired from the live paths. It is inert
  until explicitly constructed; wiring it would be new unvalidated behavior.
- `LAYA_V13_REDESIGN_BLUEPRINT.md`: design-only v13 plan (adapter isolation,
  gradient surgery) requiring the no-rerun restriction to be lifted before any
  implementation or evaluation.

## User constraint: no reruns

No further training, inference, or confirmatory reruns are authorized by the
current instruction. Existing frozen artifacts, labels, gates, weights and
predictions must remain unchanged. Do not optimize a replacement rule against
the revealed EV/INJ labels and call it confirmatory evidence.

Permitted remaining work: static integration review, saved-output analysis,
verified code-defect repairs with targeted regression tests, independent gate
recomputation, and an honest study report. Any modified system remains
unvalidated for behavioral performance unless new evaluation is subsequently
authorized. A failed checkpoint cannot be converted into a validated pass by
documentation, routing, confidence changes, or a fail-closed guard.

## Provenance

- Results SHA256: `140cbf58ce9b42b6e92519cc1b289a767d8d87f42b7a6447c79669b82c9c63a8`
- Decision SHA256: `b8b78e2a9f48b8c811540a01cb75128c40bb93d8ea114edd6aa5598f2a6718ba`
- Final weights SHA256: `ee7501a34323cf6f26e68209eedca8f5cd275a187a83cc687714bfa2824b3ac5`

The source artifacts are under `results/laya_decision_v4/` with prefix
`laya_v12_balanced_allrows_gpu_redesign_v1_`.
