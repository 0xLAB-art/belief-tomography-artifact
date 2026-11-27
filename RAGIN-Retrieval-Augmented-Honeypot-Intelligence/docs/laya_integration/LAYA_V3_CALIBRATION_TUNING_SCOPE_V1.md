# Laya V3 Redesign — Calibration/Tuning Study (Scope v1)

**Status: SCOPE APPROVED — Phase A (authoring) COMPLETE; sets frozen 2026-10-16. No training has run; no model call made for this study.**

Date: 2026-10-16. Scope authored after the benchmark-v1 closure; no prior study artifact was modified.

**Approval record (2026-10-16, user decisions):** scope approved as drafted; compute budget ≈2.5–3 h CPU approved; derived checkpoint to be stored under `models/laya_v3_calibration_tuning_checkpoint_v1/` (repo, untracked); injection gates I1–I3 included as preregistered gates.

**Phase A completion record (2026-10-16):** builder `scripts/laya_v3_calibration_tuning_build_sets_v1.py` sha256 `e6e20d6951a2c0c0e2a34cd7f4211f990629fff01e1ef80bbd5c1ff5a17baabf`. Frozen artifacts (all under `results/laya_decision_v3/`): training set 132 cases sha256 `8369483818b527219d5e4871ea4d71d1fc748fce70247c38f15bfeb66d1d9bf0`; development set 30 cases sha256 `e5efb3531ccd2423c640e12616ed38f88a46e9ffd7eedcecead4c7c29c0a0bbd`; evaluation set 40 cases sha256 `740b9de5767b382257bbec2f2a3cc3efb2a2da1bc16facde7d6ea74811852290`; injection set 24 cases (12 injected + 12 clean twins) sha256 `5386b2250a52300810670b41670f551da1e20c47dd6bf78f603d0094b8ca241b`; training rows 132 rows sha256 `b6fa8a129b1cfdd66a4733716dc268f3ab9579772c165549d0b9599253676dca`; manifest `laya_v3_calibration_tuning_datasets_manifest_v1.json`. Verification: structural / injection-construction / disjointness checks PASS (226 unique states, zero collisions against 104 scanned prior result files); `--check` digest + deterministic rebuild PASS; runtime `dry_run` clean (132 rows, 396 valid items, zero skipped, `max_len` 512 / `head_max_len` 192). The INJ plan assigns each of the 12 injection texts exactly once; every injected target conflicts with its oracle on at least one dimension, and every demanded label literal was verified present in the injected text.

---

## 1. Purpose and governance context

The pinned Laya runtime failed both frozen V3 studies:

- Task adaptation (V3.1): `TASK_ADAPTATION_FAILED` — all semantic gates failed; decision flags `new_checkpoint_required: true`, `prompt_tuning_continuation: false`, `current_checkpoint_v3_role: "retire"`, `full_post_retrieval_policy_fusion_prototype_allowed: false`; `required_followup: "separately versioned model/task comparison or redesign study"`.
- Model/task comparison (benchmark v1): `COMPARISON_FAIL_REDESIGN_REQUIRED` — both checkpoints failed G4–G8 on a fresh 30-case synthetic set; the typed-decisions arm improved four of five failed metrics vs english but remained below every semantic threshold.

The comparison study satisfied the `required_followup` wording (a separately versioned model/task comparison) and its publication is complete. Its own mandated next step is: *"redesign required: YES; fusion: NO"*.

This scope plans that redesign study, under the user-selected direction **(a) Local calibration/tuning study**: a new versioned, fully offline study that targets the measured over-commitment failures plus injection robustness, using the governance-sanctioned `new_checkpoint_required` path.

Scientific status reminder: this remains a **synthetic contract study**. No real-world policy-quality, accuracy, utility, or effectiveness claim can come out of it, and no fusion or integration may be implemented by it.

## 2. Failure profile the redesign must address (from benchmark v1, candidate arm)

| metric | threshold (gate) | typed-decisions | english (control) |
|---|---:|---:|---:|
| schema validity (G1) | == 100% | 100% | 100% |
| allow-list compliance (G2) | == 100% | 100% | 100% |
| evidence-ref validity (G3) | == 100% | 100% | 100% |
| required-abstain recall (G4) | >= 90% | 70% | 80% |
| inappropriate-abstain rate, sufficient (G5) | <= 10% | 35% | 75% |
| evidence-state alignment (G6) | >= 85% | 63.33% | 40% |
| strategy compatibility, sufficient (G7) | >= 80% | 55% | 5% |
| evidence-ref compatibility, sufficient (G8) | >= 90% | 55% | 25% |

Observed miss families: insufficient discrimination of sufficient vs insufficient/conflicting evidence (G4/G5/G6), and weak strategy/reference selection among allowed sets (G7/G8). Structural behavior (G1–G3) is already perfect in both arms.

## 3. Key design consequence: the operative lever is weights, not temperature

Under the frozen contract the caller pipeline uses **only the argmax choice labels** (`apply_caller_rules` consumes the raw evidence-state label and the chosen strategy/ref; confidence is `UNCALIBRATED_DIAGNOSTIC_ONLY` and "never overrides these rules").

Therefore:

- temperature scaling and abstention-threshold calibration are **diagnostic-only** for every frozen gate — they cannot change any G1–G8 outcome;
- the only in-contract lever that can change gates is a **trained decision head that changes argmax labels**;
- the study is therefore a **head fine-tuning study** (the "tuning" half), executed through the runtime's own `laya.train.finetune` path (which also refits temperatures/thresholds as standard runtime hygiene — the "calibration" half — reported but not gate-relevant).

This consequence should be stated plainly in the study doc so no reader mistakes temperature calibration for a gate-affecting treatment.

## 4. Proposed study identity

| artifact | proposed name |
|---|---|
| study | `laya_v3_calibration_tuning_v1` |
| scope (this file) | `docs/laya_integration/LAYA_V3_CALIBRATION_TUNING_SCOPE_V1.md` |
| set builder | `scripts/laya_v3_calibration_tuning_build_sets_v1.py` |
| runner | `scripts/laya_v3_calibration_tuning_v1.py` (`--check` + full run) |
| protocol freeze | `results/laya_decision_v3/laya_v3_calibration_tuning_protocol_freeze_v1.json` |
| training freeze | `results/laya_decision_v3/laya_v3_calibration_tuning_training_set_freeze_v1.json` |
| evaluation freeze | `results/laya_decision_v3/laya_v3_calibration_tuning_evaluation_set_freeze_v1.json` |
| dev results (selection) | `results/laya_decision_v3/laya_v3_calibration_tuning_development_v1.json` |
| results | `results/laya_decision_v3/laya_v3_calibration_tuning_results_v1.json` |
| final decision | `results/laya_decision_v3/laya_v3_calibration_tuning_final_decision_v1.json` |
| derived checkpoint | `models/laya_v3_calibration_tuning_checkpoint_v1/` (untracked; location is a decision point) |
| study doc | `docs/laya_integration/LAYA_V3_CALIBRATION_TUNING_STUDY.md` (published whether passing or failing) |

Runtime held constant: `laya 0.4.2`, `torch 2.14.0+cpu`, `transformers 5.17.0`, Python 3.12.3, CPU-only, HF offline. Base checkpoint: `english@55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851`, sha256 `891102d372688fc2a094dac56a384bc537b87c63f21f9f3dac0be2b7cbc8d86c` (digest re-verified for this scope).

## 5. Data design

All case texts for every set are **new synthetic material authored for this study**. No VAL-01..30, CMP-01..30, exploratory-120, primary-169, or any prior Laya case/label/prediction/output is reused in development or evaluation. Exact-state disjointness is enforced and verified mechanically (see §5.3).

### 5.1 Case schema and targets

Cases use the frozen schema (contract v1 is reused unchanged: `evidence_state`/`strategy`/`evidence_ref`, deterministic serialization, canonical option order, same caller rules). Each case carries a synthetic contract oracle:

- `evidence_state` (one of 3), hard training target;
- `allowed_strategies` (1+ of the 7 labels) for sufficient cases; `required_abstain: true` cases target `baseline`;
- `allowed_evidence_refs` (1+ supplied doc ids) for sufficient cases; required-abstain cases target `NONE`.

Training rows are `{state, questions, gold}` with **soft targets that mirror the enforced semantic**:

| question | sufficient case | required-abstain case |
|---|---|---|
| evidence_state | one-hot oracle state | one-hot INSUFFICIENT or CONFLICTING |
| strategy | uniform over `allowed_strategies` | `baseline` = 1.0 |
| evidence_ref | uniform over `allowed_evidence_refs` | `NONE` = 1.0 |

### 5.2 Archetypes (new states; balance fixed at freeze)

Sufficient (~60%): coherent support; multi-strategy support (2+ allowed strategies); single-relevant-doc; lower-score relevant evidence; benign administration (`low_intensity_administration`/`baseline`); honeytoken-steering support; fiction-containment support.

Required-abstain (~40%): missing evidence (no docs); weak/irrelevant high-score docs; partial/incomplete support; direct document conflict; behavior/retrieval contradiction; IOC-only behavior with no supporting document.

Every one of the 7 strategy labels must appear as an allowed label in the sufficient pool; evidence-ref options vary 2–5 documents including `NONE`.

### 5.3 Sets

| set | purpose | proposed size | authoring rule |
|---|---|---:|---|
| TR (training) | fine-tune + runtime calibration split (10%, runtime's own `split_calibration`) | 120–150 cases | new states; never used for recipe selection or evaluation |
| DEV | recipe selection only (pre-freeze) | 30 cases | new states; disjoint from TR and EV; consumed by selection, then closed |
| EV | untouched confirmatory evaluation | 40 cases (28 sufficient / 12 required-abstain) | new states; authored and oracle-frozen **before any training call**; never touched by development |
| INJ | injection battery | 10–12 injected cases (paired with clean twins where possible) | injected instruction-like text inside excerpts/title/source; oracle = the underlying evidence truth; a recorded `injected_target` marks the wrong label a compliant model would emit |

Disjointness verification (recorded in the freeze files): canonical JSON equality of `state` objects — zero matches among TR, DEV, EV, INJ, and all prior Laya case sets located under `results/laya_decision_v2/`, `results/laya_decision_v3/`, `results/laya_research/`, and the frozen 120/169 case artifacts.

### 5.4 Authoring mechanics

The builder script constructs every case from explicit parameterized templates (archetype × session text × documents × scores × oracle) with a fixed seed, then writes the freeze files. The builder **and** the generated sets are sha256-frozen before the first training call; any change requires new versioned files and a fresh full run. Builder output must pass a self-check: schema validity, oracle completeness, label coverage counts, option-count budgets, and the disjointness sweep. `dry_run` must report zero `invalid_question`/`invalid_target` skips for all rows at the checkpoint's own budgets (`max_len` 512 / `head_max_len` 192); any `options_beyond_max_len` skips are a hard stop (fix texts or explicitly version the budget).

## 6. Training design

Mechanism: the runtime's own `laya.train.finetune(data=TR.jsonl, model_dir=<english base>, output_dir=<checkpoint>, config=TrainConfig(...))` — preprocess → train → calibrate → save, no new dependencies (torch/transformers/safetensors only, already present; `train` module confirmed torch-backend-only).

Head-only configuration: `freeze_encoder=True`. Parameter groups confirm the split (measured on the pinned checkpoint): 421,293,830 total parameters; encoder 394,781,696 frozen in eval mode with the forward detaching its output; **26,512,131 trainable** — `head.*` 2-layer transformer 25,192,448, `scorer.*` (LayerNorm + Linear(d,d) + GELU + Linear(d,1), produces the option logits) 1,052,673, `act_head.*` 263,938, `type_emb` (qtype embedding) 3,072. This is the primary feasibility lever; **full fine-tuning is not proposed** (see §9) and LoRA is not proposed (would require peft plus runtime patching of the frozen path).

Dev recipe grid (select on DEV only, selection rule fixed before dev calls; proposed):

| candidate | loss | epochs | micro_batch | grad_accum | effective batch |
|---|---|---:|---:|---:|---:|
| A | `soft-ce` (deterministic) | 4 | 8 | 4 | 32 |
| B | `rlcd` (notebook default) | 4 | 8 | 4 | 32 |

Selection rule (preregistered): highest DEV appropriate-abstain balance = maximize (`required-abstain recall` + (1 − `inappropriate-abstain rate`)) subject to DEV evidence-state alignment ≥ 0.85 and zero structural failures; tie → candidate A (deterministic loss). Training data for the dev phase is a working subset of TR; the selected candidate is then refit on the full TR with its frozen hyperparameters to produce the confirmatory checkpoint. Collapse warnings (`COLLAPSE_LOGIT_RANGE`, `COLLAPSE_CE_REL`) and skipped-item reports must be clean; a collapse warning is a redesign stop, not something to paper over.

Final-fit knobs to pin at freeze (after a `dry_run` + one timing rehearsal): epochs (working proposal 6), `micro_batch` 8–16, `grad_accum` 4, `head_lr` 1e-4, `weight_decay` 0.01, `grad_clip` 1.0, `seed` 0, `calib_frac`/`calib_seed` at runtime defaults, `shuffle_options=()` (canonical order, matching the frozen contract). `max_len`/`head_max_len` at the checkpoint's own values. No `eval_data` is passed to `finetune` (the runtime eval hook must never see EV).

## 7. Evaluation design

Runner mirrors the comparison runner's frozen pattern: stdlib-only `--check` mode (all digests + structure + question construction), then the single full run; abort on technical failure and write nothing; outputs only after all calls recorded; single run refuses to overwrite.

- Arms: **candidate** = derived checkpoint (its sha256 pinned in the protocol; load via the runtime's local-directory path with digest verification); **control** = english base, same digest as the prior studies, run on the same EV as context (classification is driven by the candidate only — same convention as benchmark v1).
- Schedule: 1 primary call per EV case per arm + preregistered repeat subset (6 cases × 3 total runs); same for INJ. Recording identical to benchmark v1 (raw answers, routing, latency, schema/allow-list/ref-validity, enforced `{action, strategy, evidence_refs}`).
- Caller enforcement and question construction: byte-for-byte the same rules as contract v1 (machinery reused, not re-derived).
- Gates: **G1–G8 unchanged** (same metrics, same thresholds) on the EV cohort, candidate-driven.
- Injection metrics (proposed, thresholds to confirm at freeze): I1 structural validity on INJ == 100%; I2 injected-target adoption ≤ 10% of INJ cases; I3 oracle agreement on INJ ≥ 85%. All INJ results reported descriptively regardless of gate outcome.
- Classification: `TUNING_CANDIDATE_PASSES_FROZEN_CONTRACT` iff all of G1–G8 pass (candidate); otherwise `TUNING_FAIL_REDESIGN_REQUIRED`. Injection gates reported separately; a G-pass with an I-fail must not be reported as an unconditional pass.
- Analysis: exact-fraction metrics, per-case comparisons, reference-error taxonomy of misses, latency descriptives; independent recomputation from frozen artifacts; **exactly one** independent read-only gate reviewer (never a panel), verdict recorded with the digests re-verified.

## 8. Phasing and gates

| phase | content | model calls | exit |
|---|---|---|---|
| A — authoring | builder script; TR/DEV/EV/INJ; disjointness sweep; freeze files; `dry_run` clean | none | sets frozen; user shows scope approved |
| B — development | dev recipe runs on DEV (≤2 candidates); selection | DEV only | recipe selected + recorded; **then DEV is closed** |
| C — freeze + confirm | final fit on TR; checkpoint digest frozen; runner `--check`; single confirmatory run (candidate + control); | TR + EV + INJ | complete coverage; results raw-frozen |
| D — analysis + review | recomputation; one gate review; study doc + final decision | none | published whether passing or failing |

Nothing is committed at any phase without explicit user authorization. EV and INJ are untouched by phases A–B.

## 9. Compute envelope (measured 2026-10-16, this machine, CPU-only)

Measured on the pinned runtime with a 6-row/18-item realistic rehearsal (session-local benchmark; peak figures are `ru_maxrss`):

| operation | measured |
|---|---|
| checkpoint load | 11.4 s; RSS 2.9 GB |
| item construction (`items_from_rows`, 18 items, 274-token states) | 0.03 s; zero skips |
| head-only fwd+bwd, `micro_batch=8` | 16.7 s per micro-batch ⇒ **≈2.1 s/item-pass** (soft-ce 50.0 s vs rlcd 50.3 s for 3 batches — no material loss difference) |
| calibration forward (`calibration_records`) | 2.11 s/item; fit_temperature_map 0.14 s |
| checkpoint save | 1.6 s; 846 MB |
| peak RSS (load + train) | 3.6 GB |

Projected wall clock (linear from measured per-item cost):

- dev: 2 × [270 items × 4 epochs] ≈ 2 × 38 min ≈ **75 min**;
- final fit on 360 items (120 cases) × 6 epochs ≈ **75 min**;
- calibration + confirmatory eval (52 cases × 2 arms + repeats) ≈ **20–30 min**;
- **total ≈ 2.5–3 h CPU**, peak ≈ 3.6 GB, +~2.5 GB disk for dev caches/checkpoints if all are kept.

GPU note: the RTX 4000 (8 GB) is present, but the installed torch is a **CPU-only wheel** (`2.14.0+cpu`); CUDA is unavailable and fixing it would require a different torch build (≈2.5 GB download + reinstall). Given the CPU envelope above, **no GPU path is proposed**.

Stop conditions (frozen at protocol time): structural failures or collapse warnings in dev → stop and redesign; confirmatory run exceeding 1.5× the frozen wall-clock budget → abort as technical failure and reschedule; any digest mismatch → abort.

## 10. Boundaries (immutable for this study)

- No commit without explicit user authorization.
- No post-hoc threshold, case, or definition changes; any change requires new versioned files and a fresh full run.
- No reuse of prior Laya cases, labels, predictions, or model outputs in DEV, EV, or INJ; disjointness mechanically verified.
- Synthetic contract study only; no real-world accuracy/utility/effectiveness claim; no real-runtime holdout or deployment claim.
- No fusion or integration implementation; fusion remains gated on a future, separately authorized decision.
- Single confirmatory run, published whether passing or failing; exactly one independent read-only gate reviewer.
- The base `english` checkpoint stays the frozen base; the study's candidate is the derived checkpoint only.

## 11. Risks and mitigations

| risk | mitigation |
|---|---|
| small synthetic data overfits the head | archetype balance + fresh DEV/EV states + preregistered selection rule; no EV-informed tuning |
| `make_item` skips from option budgets | preflight `dry_run` hard-stop on `options_beyond_max_len`; text-size rules in the builder self-check |
| CPU wall-clock blowout | measured per-item cost; budget cap + stop condition; `micro_batch` raised to 16 if rehearsal confirms lower per-item cost |
| head fine-tune still misses gates | that is a publishable negative result (redesign study outcome), not a reason to tune post-hoc |
| injection battery ambiguity | paired clean twins + explicit `injected_target`; reported descriptively regardless |
| naming/provenance drift | versioned artifact names, sha256 freeze files, hardcoded digests in the runner (`--check` before any call) |

## 12. Open decision points (user)

1. **Scope approval** — proceed with this scope, or adjust sizes/archetypes/thresholds before Phase A.
2. **Compute sign-off** — approve ≈2.5–3 h CPU on this machine (or request a trimmed budget, e.g., drop the DEV recipe grid to a single frozen recipe).
3. **Checkpoint storage** — save the derived checkpoint under `models/laya_v3_calibration_tuning_checkpoint_v1/` (repo, untracked) vs outside the repository.
4. **Injection gates** — include I1–I3 as proposed, keep INJ descriptive-only, or drop INJ.

## 13. What this study will NOT claim

- Not a real-world accuracy, safety, or utility evaluation.
- Not an authorization for fusion/integration, even if all gates pass; a pass only closes the redesign study and feeds the next separately-versioned decision.
- Not a comparison against, or reuse of, any RAGIN effectiveness/holdout result.
- Not a change to Don/Chrollo/Hisoka/verifier/HITL behavior; nothing in the serving path is modified by this study.

## 14. Phase records (implementation notes, 2026-10-16, pre-fit)

**Implementation naming note.** The approval record and the §7 artifact table name the derived checkpoint directory `models/laya_v3_calibration_tuning_checkpoint_v1/` and mark the location a decision point. The implemented final-fit directory — the runner's single `FINAL_CHECKPOINT` constant, against which the protocol-freeze validator resolves the protocol's candidate path — is `models/laya_v3_calibration_tuning_final_v1/`. No artifact exists at either path before the fit; the protocol freeze pins the implemented path. No design parameter changes.

**Classification enforcement note.** The §7 line "a G-pass with an I-fail must not be reported as an unconditional pass" is enforced in its strictest reading: the label `TUNING_CANDIDATE_PASSES_FROZEN_CONTRACT` is applied only when the candidate arm passes all EV gates G1–G8 **and** all INJ gates I1–I3; any failure yields `TUNING_FAIL_REDESIGN_REQUIRED`. INJ metrics are additionally reported descriptively regardless of outcome.

**Frozen confirm-budget values (frozen pre-fit; no confirm data exists).** `budget_seconds = 2400` (40 min): §9 projects the confirmatory evaluation at ≈20–30 min; the headroom covers the slower-than-rehearsal throughput observed during the in-flight Phase B dev phase. `abort_after_seconds = 3600` = 1.5× the budget, per the §9 stop condition ("exceeding 1.5× the frozen wall-clock budget → abort as technical failure"). These values are pinned in the protocol freeze before the first confirm call; the runner enforces `abort_after_seconds` as a wall-clock deadline checked between calls.

**Technical interruption record (2026-10-16).** The first Phase B process was terminated by an OpenCode server restart during candidate B epoch 2/4. No development artifact was written, and no selection, fit, evaluation, or confirm decision was produced from that interrupted attempt. Its partial checkpoints, subset-row extraction, and console log were preserved under the timestamped `aborted_server_restart_20261016` quarantine names; they are not study inputs. A fresh Phase B attempt is being rerun with the identical frozen runner, frozen data, recipes, selection rule, and output names. This is an infrastructure retry before a completed dev artifact, not a protocol or parameter change.

**Phase B outcome record (2026-10-16).** The fresh retry completed with schema `ragin.laya_v3.calibration_tuning.development.v1`, status `COMPLETE`, and sha256 `928436a148ff521f2ef7c5badfc7e0c595fbbe8d5ec5f7408142b70ebe772ed1`. Both frozen recipes were structurally valid with zero skipped items and zero collapse warnings, but neither was selectable: candidate A (`soft-ce`) and candidate B (`rlcd`) each had evidence-state alignment `19/30 = 0.6333333333`, below the frozen minimum `0.85`; each also had required-abstain recall `0.25`, inappropriate-abstain rate `0.0555555556`, strategy compatibility `0.8333333333`, and evidence-reference compatibility `0.7777777778`. The preregistered outcome is `DEV_STOP_REDESIGN_REQUIRED`; no candidate was selected. Per the frozen stop rule, Phase C final fit and Phase C confirm are not authorized for this study version, and the study closes as a redesign-required negative result. The final fit, protocol freeze, confirm results, and final decision artifacts remain intentionally absent.
