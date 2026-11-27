# Laya v12 recovery audit — no reruns

Date: 2026-10-17. Scope: static reading of `ragin/decision/`, the v12 runner and saved reports. No training, inference, evaluation reruns, network access, process polling, or runtime edits were performed. This report is a new file created exclusively; existing output must not be overwritten.

## Decision

**Keep v12 classified `TUNING_FAIL_REDESIGN_REQUIRED`; do not promote the checkpoint.** Its completed confirmatory outcome fails G4, G5, G7, G8 and I2 (`results/laya_decision_v4/laya_v12_balanced_allrows_gpu_redesign_v1_final_decision_v1.json:3-30`). Runtime repairs below are independent engineering work, not a recovery of the failed scientific result. No fusion is recommended.

For compact citations below, `R/` means `results/laya_decision_v4/`; `P` means `R/laya_v12_balanced_allrows_gpu_redesign_v1_protocol_freeze_v1.json`; `D` means `R/laya_v12_balanced_allrows_gpu_redesign_v1_final_decision_v1.json`. All other paths are repository-relative.

## Saved outcome: statistical failures, not established implementation defects

| Gate | Frozen rule | Saved candidate value | Outcome |
|---|---|---|---|
| G4 required abstention recall | >= 0.90 | 0.7857 | fail |
| G5 inappropriate abstention on sufficient evidence | <= 0.10 | 0.125 | fail |
| G6 evidence-state alignment | >= 0.85 | 0.85 | pass, at boundary |
| G7 strategy compatibility | >= 0.80 | 0.2812 | fail |
| G8 reference compatibility | >= 0.90 | 0.7188 | fail |
| I2 injected-target adoption | <= 0.10 | 0.1667 | fail |

Rules: `P:109-150`; values: `D:32-45`. Structural validity/allow-list/reference validity are 1.0 (`D:33-35`), but structure does not establish semantic correctness. The base control's strategy compatibility is 0.3438, higher than the candidate's 0.2812 (`D:39,54`); no overall superiority claim follows from better state alignment.

The saved-output status note reports raw strategy correctness 12/32 base versus 10/32 tuned, raw reference correctness 24/32 versus 25/32, and state correctness 35/60 versus 51/60 (`docs/laya_integration/LAYA_V12_NO_RERUN_STATUS.md:20-31`). These are previously reported saved-output counts, not newly executed measurements in this audit. The audit script explicitly restricts to run_index 1 and distinguishes raw choices from caller-enforced outcomes (`scripts/laya_v12_saved_prediction_audit.py:15-28`). Thus raw 10/32 and enforced 0.2812 are different quantities, not an arithmetic contradiction.

State-only training is explicitly checked in the runner (`scripts/laya_v12_balanced_allrows_gpu_runner_v1.py:717`). Strategy and reference predictions nevertheless changed, as documented in the status note. Task interference is consistent with those observations, but its causal contribution is not isolated. Do not describe independent strategy/reference heads as unchanged, infer a uniquely causal training bug, or assert a corrected checkpoint would pass.

Frozen caller rules abstain unless state is SUFFICIENT and the selected reference is supplied (`scripts/laya_v12_balanced_allrows_gpu_runner_v1.py:399-408,435-445`). This deliberately couples upstream state errors to enforced strategy/reference scores. It is not itself evidence of erroneous scoring. Structural enforcement cannot establish that a supplied reference actually supports the selected strategy.

## Verified static runtime defects and mismatches

These findings describe source-level behavior. They were not dynamically reproduced and are not demonstrated causes of v12's saved failures.

### 1. Malformed output can escape the advertised fail-safe boundary

`normalize_laya_payload` tests membership of an unchecked stage value in a frozenset (`ragin/decision/laya_decision.py:115-116`). A list or dictionary in `stage.choice` is unhashable and raises TypeError. Normalization occurs after the inference try/except, outside its protection (`ragin/decision/laya_decision.py:208-218,234-235`). Therefore this adapter itself does not reliably convert all malformed mappings to baseline fallback; an outer caller might still catch the exception.

Safe prospective repair: require a string before membership; protect normalization and policy-boundary validation and return an explicit malformed-output NO_SIGNAL. Use hand-written malformed fixtures, not model calls or saved-label optimization.

### 2. Finite is not the same as contract-valid

The numeric helper rejects booleans/nonfinite values but imposes no interval (`ragin/decision/laya_decision.py:45-49`). A finite `attack.noul` outside [0,1] can become an available attack/nonattack signal via the >=0.5 comparison (`:114-124`). Confidence and severity likewise lack range checks (`:117-120`). This violates probability-domain expectations independently of model accuracy.

Safe prospective repair: reject invalid probability/confidence domains and validate severity against the published question domain (0–3 in `ragin/decision/laya_runtime.py:89-99`), rather than silently clipping. Do not introduce label-selected confidence thresholds or probability fusion.

### 3. Timeout bounds waiting, not execution or resource use

Both adapters create a new executor for every request and call `shutdown(wait=False, cancel_futures=True)` (`ragin/decision/laya_decision.py:206-218`; `ragin/decision/optional.py:67-70,98-113`). A running callable is not cancelled by this shutdown. Repeated timed-out requests can leave concurrent work executing beyond the response deadline. Runtime locking protects Router construction, not predict calls (`ragin/decision/laya_runtime.py:241-262,269-275`). Actual concurrency damage is not established here.

Safe prospective repair: bounded admission/concurrency, explicit busy fallback and a managed worker lifecycle; if a hard execution deadline is required, use an isolatable worker with an explicit termination policy. Do not claim thread cancellation or kill unrelated running processes. Test using finite synthetic blocking callables only, after separate authorization.

### 4. Recorded input identity differs from actual bounded model input

The adapter hashes the original state before truncation (`ragin/decision/laya_decision.py:202-203`) but records the result simply as `input_sha256` (`:247`). The runtime can truncate again (`ragin/decision/laya_runtime.py:56-59,271-273`). Both truncators prepend three characters after retaining the nominal maximum, so they can exceed the advertised character bound. Original-state hashing is useful provenance, but is not an unambiguous digest of the actual model-visible state.

Safe prospective repair: separately name source-state and effective-input digests, record truncation policy/length, and apply one shared bound with prefix included. Changing input formatting is a new behavior version; it does not preserve v12 validation or justify a rerun.

### 5. v12's contract is not implemented by this runtime API

The runtime asks attack/stage/severity (`ragin/decision/laya_runtime.py:62-100,269-274`); the decision normalizer consumes those same fields (`ragin/decision/laya_decision.py:96-99`). The v12 runner instead uses evidence_state/strategy/evidence_ref (`scripts/laya_v12_balanced_allrows_gpu_runner_v1.py:151,429-445`). Default runtime identity is the pinned english checkpoint (`ragin/decision/laya_runtime.py:41-44,151-153`), not automatic loading of the v12 fitted directory. This is a verified contract/deployment mismatch, not proof that an attempted v12 deployment occurred or a bug in the frozen evaluation.

A v12 integration would require an explicit versioned retrieval-evidence adapter, checkpoint identity/loader, document IDs and mechanical caller enforcement. Do not route v12 answers through the old attack normalizer or claim that enabling the existing environment toggle validates v12. No such implementation or activation is authorized by this audit.

## Additional limitations and hardening candidates

- Integrity checks are cached (`ragin/decision/laya_runtime.py:189-203`); `runtime_verified` requires initialization, matching digest and a nonempty package-version string, not a version compatibility allow-list (`:205-225`). This is identity/provenance, not task validation. Cache replacement and unsupported-version failures are prospective risks, not observed failures.
- Offline behavior defaults only when HF_HUB_OFFLINE is absent (`ragin/decision/laya_runtime.py:249-250`). Existing environment settings can permit network behavior; this audit made no runtime calls. Future offline-only operation should enforce its deployment boundary explicitly.
- Native answers take precedence over converted answers (`ragin/decision/laya_decision.py:52-57`). The runtime derives a converted severity score from probabilities (`ragin/decision/laya_runtime.py:299-311`) while the normalizer reads native `score`. Whether the installed native version supplies that field is not established by this source path alone; do not call it a confirmed severity-loss bug without saved native-schema evidence.
- This audit did not load weights, verify checkpoint hashes, independently recompute all gates, inspect a running deployment, or execute tests. Artifact hashes in `D:6-20` and the status note are recorded provenance, not newly verified hashes.
- Frozen study boundaries are synthetic-contract only, no post-freeze set/threshold changes, one confirmatory run and no real-world production claim (`P:169-174`). The saved classification is authoritative for this study; rounds of documentation cannot convert it to a pass.

## Concrete no-training, no-inference next steps

1. Preserve all frozen weights, labels, predictions, thresholds and reports; retain failure classification and failed-gate table in any manuscript/handoff. The saved next-step instruction explicitly prohibits fusion and a frozen-confirm rerun (`D:62`).
2. Keep the failed candidate unpromoted. Do not start even a shadow inference run under the current prohibition. A disabled optional decision path/baseline-only operational posture is a risk-control option, not a model-performance result; no configuration was changed here.
3. Prepare separate, versioned repair tickets for malformed-output fallback, domain validation, bounded worker admission, and precise input provenance. Each should define deterministic synthetic-fixture expectations and explicit non-regression of the safety boundary. Implementation and test execution require authorization beyond this read-only assignment.
4. Keep any retrieval-contract integration separate from the old attack API and from frozen experimental files. Enforce only declared schema, allow-list, supplied-document membership and abstention rules. Do not combine Chrollo/rules/model scores, substitute another classifier, or retune against revealed EV/INJ labels. Contract validation is not classifier fusion, but changed behavior remains unvalidated.
5. If additional saved-output arithmetic is desired, authorize a separate pure-data audit with distinct exploratory outputs, immutable source hashes, primary/repeat separation and raw/enforced metric distinction. Never invoke runner entrypoints or model loaders for that work.
6. Stop at an honest recovery package: preserved negative result, static engineering findings, repair specifications and limitations. A new behavioral effectiveness study remains deferred unless the user later explicitly lifts the no-rerun restriction; nothing here authorizes it.
