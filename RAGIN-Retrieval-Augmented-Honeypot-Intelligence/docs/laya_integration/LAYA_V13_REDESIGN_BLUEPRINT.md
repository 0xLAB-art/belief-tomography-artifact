# Laya v13 redesign blueprint — adapter isolation + gradient surgery

Date: 2026-10-17. Status: **design only**. This document is produced under the
standing no-rerun constraint: nothing in it has been trained, evaluated, or
validated, and it does not change the frozen v12 classification
`TUNING_FAIL_REDESIGN_REQUIRED`
(`results/laya_decision_v4/laya_v12_balanced_allrows_gpu_redesign_v1_final_decision_v1.json`).
Implementing or evaluating this blueprint requires the user to explicitly lift
the no-rerun restriction. Citations: `R/` = `results/laya_decision_v4/`,
`P` = `R/laya_v12_balanced_allrows_gpu_redesign_v1_protocol_freeze_v1.json`,
`D` = `R/laya_v12_balanced_allrows_gpu_redesign_v1_final_decision_v1.json`.

## 1. Evidence recap (saved outputs only)

Failed gates (D:32-45, rules P:109-150): G4 0.7857 (<0.90), G5 0.125 (>0.10),
G7 0.2812 (<0.80), G8 0.7188 (<0.90), I2 0.1667 (>0.10). G6 passed at the
boundary (0.85). Facts relevant to causation:

1. State-only training is verified in the runner (`scripts/laya_v12_balanced_allrows_gpu_runner_v1.py:717`),
   yet strategy and reference predictions changed between arms — recorded in
   `docs/laya_integration/LAYA_V12_NO_RERUN_STATUS.md:20-31`.
2. The base control's strategy compatibility (0.3438) exceeds the candidate's
   (0.2812) (D:39,54): joint fine-tuning made strategy compatibility *worse*.
3. The coupling decomposition (`scripts/laya_v12_coupling_decomposition_v1.py`,
   saved-output only) isolates the causal contribution the audit left open:
   caller-rule coupling costs exactly 1 strategy case and 2 reference cases out
   of 32 sufficient cases. Even with *perfect* decoupling the raw rates are
   0.3125 (G7) and 0.7812 (G8) — both still below their thresholds.
   **Decoupling alone cannot rescue G7/G8; the dominant cause is genuine
   incompatible strategy/reference selection by the model.**
4. I2 shows 2/12 injected directives adopted (0.1667): the model follows
   in-evidence imperatives when they name answer-schema tokens.

Together these say: shared-encoder multi-head training with only state
supervision let the strategy/reference behavior drift (interference), and the
model has no learned insulation against directive text dressed as evidence.

## 2. Root-cause statement (honest scope)

Task interference is *consistent* with observations 1–3 and now its coupling
component is quantified, but the saved data alone cannot distinguish
(interference during training) from (inherently hard strategy/reference
mapping). Improving the model therefore requires a new experimental design,
not more analysis of the old run. This blueprint is that design.

## 3. v13 architecture (proposed, unimplemented)

### 3.1 Adapter isolation (stop the heads from fighting)
- Freeze the shared encoder. Attach **per-question adapter modules**
  (small low-rank adapters, one set per question id: `evidence_state`,
  `strategy`, `evidence_ref`) instead of fine-tuning the whole shared trunk.
  State updates then *cannot* overwrite strategy/reference features, because
  the frozen trunk is identical for all heads and each adapter trains on only
  its own question's loss.
- If any shared parameters must still move, apply **gradient surgery**:
  PCGrad-style projection — when the state gradient has negative cosine
  similarity with the strategy or reference gradient, project it out of the
  conflicting component before the step. This turns "state learning actively
  damages strategy/reference" from an unmeasured side effect into a per-step
  enforced constraint.
- Per-question gradient norms and cosine similarities are logged every step;
  they become the *leading indicator* that replaces post-hoc gate failure.

### 3.2 Supervision where the gates are (G4/G5)
- Loss re-weighting toward required-abstention recall (G4) and against
  inappropriate abstention (G5), or a decision-threshold chosen on the
  calibration split *before* freeze — thresholds set once, in the protocol,
  never tuned against the EV/INJ revealed labels.

### 3.3 Injection insulation (I2)
- Serve every case through the provenance-tagged evidence quarantine
  (`ragin/decision/evidence_quarantine.py`, 12/12 frozen directives
  neutralized, 0/525 clean fields touched) *plus* trained augmentation:
  synthetic directive sentences of the same meta-directive+schema-token class
  (not the 11 revealed strings) added to training evidence, with the label
  unchanged, so following in-evidence imperatives is directly penalized.

### 3.4 Serving contract (already built, design-only)
- The versioned retrieval-evidence adapter
  (`ragin/decision/retrieval_contract.py`) implements the frozen contract with
  decoupled per-question channels and mechanical caller-rule enforcement, and
  records raw + enforced views per request. It is inert until activation is
  explicitly authorized; wiring it changes behavior and must be evaluated as
  part of any v13 study.

### 3.5 Evaluation gate for v13 (new freeze, new protocol)
- A *new* protocol freeze with the same published thresholds (G4>=0.90,
  G5<=0.10, G6>=0.85, G7>=0.80, G8>=0.90, I2<=0.10), hash-pinned artifacts,
  one confirmatory run, primary/repeat separation, and the coupling
  decomposition reported alongside enforced metrics so coupling cost is visible
  rather than hidden.
- v12 remains the historical negative result; no retroactive re-scoring.

## 4. What would falsify this blueprint
- If adapter-isolated training with gradient surgery shows strategy/ref
  compatibility still flat at ~0.3, the cause is the mapping task itself
  (labels/allow-lists), and the next move is data/label redesign, not more
  isolation.
- If quarantine-plus-augmentation still adopts injected directives on a fresh
  (non-revealed) injection set, the detector, not the model, is the bottleneck.

## 5. Status and boundary
Nothing in this blueprint is trained, run, or validated. No frozen artifact,
gate, label, or prediction is touched by it. The honest bottom line is
unchanged: **v12 stands as `TUNING_FAIL_REDESIGN_REQUIRED`.** This document is
the pre-authorized design so that, the day the no-rerun restriction is lifted,
the v13 study can start from a frozen plan instead of an ad-hoc attempt.