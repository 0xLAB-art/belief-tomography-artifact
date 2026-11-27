# EVALUATION INFRASTRUCTURE v1 — RAGIN ablation

**Status: DESIGN-VALIDATION INFRASTRUCTURE. EXECUTION NOT READY.**
This document describes what was built, what it enforces, and what it cannot do.
It is **not** an experiment report. No arm has executed.

**Date:** 2026-10-23
**Package:** `ragin/evaluation/` (side-effect free at import; no model, no
listener, no provider, no image pull)
**Configs:** `configs/ablation/eval_v1/`
**Contracts:** `configs/ablation/run_contract_v1.json`,
`configs/ablation/manifest_v2.json`
**Pre-change record:** `docs/research/evaluation_infra_v1/prechange_20261023/`

---

## 1. Why this layer exists

The protocol freezes a causal design; the infrastructure makes the design
*falsifiable and refusable*. It separates two questions that were previously
conflated:

| Question | Answered by | Current answer |
|---|---|---|
| Is the contract internally coherent? | `validate_design()` | **NO** — see §6 |
| Can a real run start now? | `evaluate_readiness()` | **NO** — 25 blockers |

A design can validate while execution is `NOT_READY`. Missing facts never become
ready by default and are never replaced by a mock
(`ragin/evaluation/ablation_contract.py:1-16`, `:983-991`).

---

## 2. Component map

| Module | Role | Enforces | Status |
|---|---|---|---|
| `ablation_contract.py` | Run contract + offline preflight | Arm modes, shared bundle equality, B0 image/loopback, allocation arithmetic, corpus identity, generation/verification/resource blockers | Works; design currently invalid (§6) |
| `records.py` | Session-record contract | Unit = session; ≤12 turns; hash integrity; `MOCK` only in `TEST_ONLY`; no `replace_of`; competing-cause consistency | Works |
| `attacker_policies.py` | Scripted policies + allocation | Matched blocks of four; refuses fake LLM/human policies | Works |
| `closed_loop.py` | Track B controller | Next command from previous served output; transport injected; failures preserved | Works; used only with fakes/test transport |
| `analysis.py` | Prespecified competing-risks analysis | ITT, Aalen–Johansen, paired block bootstrap, Holm, exposure gating | Works on synthetic records; no real records |
| `human_packet.py` | Blind packet + agreement hooks | Arm hidden; detection requires observed statement; no AI-as-human | Instrument only; no ratings |
| `release_manifest.py` | Immutable SHA-256 package | Complete-category requirement; strict failure; overwrite refusal | Works; no run package exists |

CLI entry points:

| Script | Purpose | Safety property |
|---|---|---|
| `scripts/ablation_preflight_v1.py` | Offline readiness report | Exit 3 = invalid design, 2 = not ready, 0 = ready |
| `scripts/run_ablation_track_b_v1.py` | B0 native Cowrie closed-loop smoke | `--i-understand-test-only`, ≤4 turns, `--pull=never`, loopback check, refuses B1–B3 |
| `scripts/run_ablation_track_a_v1.py` | Fixed-trace response runner | Dry run by default; loopback only; health gate; `analysis_eligible: False` |
| `scripts/analyze_ablation_v1.py` | Primary analysis | Refuses Track A, invalid sets, overwrite |
| `scripts/build_ablation_human_packet_v1.py` | Blind packet | No ratings generated |

---

## 3. Frozen design facts encoded in v1

### 3.1 Arms

| Arm | Retrieval | Verifier | Generator |
|---|---|---|---|
| **B0** | none (native shell) | **none** | native Cowrie |
| **B1** | `none` | shared, mandatory | frozen generator |
| **B2** | `bm25` | shared, mandatory | frozen generator |
| **B3** | `dense` | shared, mandatory | frozen generator |

- **B0 is identified only by a cached image ID**
  (`sha256:710f1e46…a30cd459`), with `pull: never` and loopback-only binding
  (`b0_native_cowrie.json`; validated at `ablation_contract.py:342-363`, `:844-888`).
  B0 is a **local transport**, not a RAGIN arm.
- **B1/B2/B3 modes are exact** (`ablation_contract.py:51`, `:280-283`). An
  unknown mode falls back to legacy hybrid, never to `none`.
- **H1 (B1 vs B0) is a system-package effect.** B0 has no shared RAGIN
  verifier and its identity/OS may differ from the pinned B1–B3 host fiction.
  Unmatched environments cannot support H1
  (`run_contract_v1.json: b0_native.baseline_identity`).

### 3.2 Tracks

- **Track A** — fixed frozen command traces; response evaluation only. It
  cannot establish engagement, detection, or time-to-suspicion
  (`track_a_frozen_v1.json`).
- **Track B** — closed-loop SSH; the only track that supports the primary
  estimand. Next command is a function of the observed served output; fixed
  replay is rejected (`closed_loop.py:1-11`).
- **Scripted policies are `SCRIPTED_POLICY` integration controls.** They test
  harness mechanics and are never a primary attacker
  (`attacker_policies.py:1-9`). The primary attacker is `UNRESOLVED`.

### 3.3 Analysis invariants

- ITT primary; per-protocol labelled sensitivity (`analysis.py:508-525`).
- Competing risks at turn 12: detection, abandonment, objective completion,
  technical failure, unavailable (`analysis.py:21-25`).
- `TURN_CAP` is censoring, never an event (`analysis.py:126-129`).
- No outcome-dependent replacement (`records.py:239-244`).
- No command-level pseudoreplication (session unit, `analysis.py:96-116`).
- No primary composite (`analysis.py:919`).
- Non-significance ≠ zero (`analysis.py:917`).

### 3.4 Generation

Proposed `temperature=0, max_tokens=512, seed=0, top_p=1` is
`PROPOSED_NOT_ENFORCED`. The runtime requests `temperature=0.7`,
`max_tokens=4096`, does not expose `seed`/`top_p`, and retains template
fallback. The preflight must keep reporting **`BLOCKED_GENERATION_CONFIG`** until
an effective-config artifact with applied decoding and a require-model-exposure
flag is present (`ablation_contract.py:466-547`). A loopback endpoint is not
proof of offline inference (`:604-641`).

### 3.5 Human packet

Blind instrument only: neutral IDs, arm hidden, hashed before release,
`source=HUMAN` explicitly a **self-report, not identity proof**. Detection is
`UNAVAILABLE` unless an observed attacker statement exists. Ratings cover shell
realism, cross-turn consistency, detectability, credibility, and error severity.
**No rating is auto-filled and none has been collected**
(`human_packet.py:111-217`).

### 3.6 Release package

SHA-256 immutable manifest over `git, source, configs, model, data, prompts,
seeds, costs, latency, raw_served`. **Any missing required file in a category
marks the package `INCOMPLETE`; a strict build fails** and does not write
(`release_manifest.py:158-161`, `:199-202`).

---

## 4. Verification evidence collected this pass

| Check | Result |
|---|---|
| Five evaluation unit-test modules | **25 passed, exit 0** (`RAGIN_SESSION_DIR` redirected to `/tmp`) |
| Preflight, offline | exit 3, `DESIGN_INVALID`, 25 blockers |
| Config hashes vs `prechange_20261023/source_hashes.txt` | match for B0–B5 and `manifest_v2.json` |
| `detection_rubric_v1.json` vs contract `rubric_sha256` | match (`05393f64…d8ff`) |
| `track_a_frozen_v1.json` vs contract hash | match (`103699a6…657d`) |
| `track_b_scenarios_v1.json` vs contract hash | match (`1b506a22…e4f8`) |
| `allocation_sequence_v1.json` vs contract hash | match (`faa1a60d…5614`) |

**Test gap:** there are **no** unit tests for `ablation_contract.py` or for the
three CLI runners. They were exercised only by direct invocation. This is a
known coverage gap, not a passing gate.

---

## 5. Allocation and split status

| Item | Value |
|---|---|
| Blocks | 8 |
| Expected sessions | 32 (2 scenarios × 2 profiles × 2 seeds × 4 arms) |
| Turn cap | 12 |
| Seed | 20261023 |
| Sequence hash | `b7640447…7d55` |
| Development families | `dev-lab-recon-01`, `dev-lab-credential-01` |
| Calibration / holdout | **empty** |
| Holdout sealed | true |

The allocation is frozen and hashed, but **no session has been allocated or
run**. The sequence itself is development-only and is not a main-study
allocation.

---

## 6. Known contradictions (must be resolved before execution)

1. **The design validator currently rejects the shipped B0 config.**
   `validate_design()` errors when B0 declares *any* `retrieval` key
   (`ablation_contract.py:285-286`), but
   `configs/ablation/b0_native_cowrie.json` declares
   `retrieval: {"mode": "not_applicable"}`. Result: `DESIGN_INVALID` and exit
   **3**, not the exit **2** ("DESIGN_VALID but NOT_READY") documented in
   `scripts/ablation_preflight_v1.py:1-14`. Either the validator or the B0
   config must change; this document does not decide which.

2. **The verification seam exists in code but is not consumed by the contract.**
   `ragin/cycle/strict_research.py` and
   `ragin/cycle/verification_deadline.py` implement `research_strict_v1` and a
   wall-clock deadline, yet `run_contract_v1.json` still records
   `integration_status: PENDING_CORE_INTEGRATION` and
   `deadline.enforcement: SIMULATED_EXCEPTION_ONLY`. Execution is correctly
   blocked, but the contract is stale relative to the core code.

3. **Rubric label sets differ.** The run contract pins
   `detection_rubric_v1.json` (labels `YES/NO/UNCERTAIN`), while
   `human_packet.DEFAULT_RUBRIC` adds `UNAVAILABLE` and extra rules. The packet
   rubric is not the contract rubric. Reconcile before labeling.

4. **Midnight timestamps in new eval configs.** `analysis_plan_v1.json`,
   `detection_rubric_v1.json`, `track_a_frozen_v1.json`, and
   `track_b_scenarios_v1.json` use `created_utc: 2026-10-23T00:00:00Z`, the same
   fabricated-precision pattern that `manifest_v2.json` explicitly disowns
   ("no midnight rounding"). They should carry actual UTC times.

5. **Readiness report names an earlier "final" trace.** It calls
   `p0_loopback_trace_20261022T200948Z` the final run, but a later PASS artifact
   `p0_loopback_trace_20261022T202850Z` exists. Both are transport traces; the
   label is stale.

None of these contradictions creates a measured result. They are reasons
execution stays blocked.

---

## 7. Claim boundary

**Supported by v1:** the evaluation paths are wired, refuse unresolved inputs,
preserve failures, reject Track A from the primary analysis, and encode the
frozen estimand. Integration readiness of serving/verification/retrieval-mode/
observability is bounded by the readiness report.

**Not supported by v1:** any arm effect, any detection CIF, any agreement
statistic, any latency or cost measurement, any human validation, any
decision-layer validity, any claim of offline generative inference.

**No B1–B3 measurement exists.** Smoke status is **SMOKE_NOT_RUN**; the ablation
is `NOT_READY`.

---

## 8. Change control

- `configs/ablation/*` and `ragin/evaluation/*` are **untracked** in git at the
  time of writing; there is no commit to define a frozen version.
- This document pass edited **docs only**. No code, test, config, script, or
  manifest was modified.
- Any change to an arm, endpoint, horizon, codebook, or model requires a new
  protocol version (`v3`) with a written reason and a new hash
  (`CAUSAL_ABLATION_PROTOCOL.md` §14).
