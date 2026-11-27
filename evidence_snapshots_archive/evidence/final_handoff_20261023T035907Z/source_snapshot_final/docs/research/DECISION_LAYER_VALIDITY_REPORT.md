# DECISION-LAYER VALIDITY REPORT — B4 / B5

**Status: NOT_STARTED (P2 conditional). No validity claim is made.** This is a
gate definition, not evidence that B4, B5, Laya, or any decision component works.

**Date:** 2026-10-23 (UTC) · **Arms:** B4 (rule decision on B3), B5 (fine-tuned
Laya on B3) · **Dependency:** valid B0–B3 first; they are not valid/measured.
**Blocker configs:** `configs/ablation/b4_rule_decision.not_ready.json`,
`configs/ablation/b5_finetuned_laya.not_ready.json`.

---

## 1. Why there is no result

| Precondition | Status |
|---|---|
| B3 executable (store + embedding model + frozen generator) | **NO** |
| B3 measured under the primary estimand | **NO** |
| B4 rule table frozen and hashed | **NO** |
| B4 decision contract tested | **NO** |
| B5 checkpoint accepted by the runtime | **NO** |
| B5 output contract compatible with the runtime | **NO** |
| Any B4/B5 session | **NO** (0) |

The analysis returns `NOT_ESTABLISHED` for H4 while B3 is not ready. This report
therefore contains no effect size, comparison, rating, or validity verdict.
**P2 decision audit: NOT STARTED / conditional on valid B0–B3.**

---

## 2. Blockers

**B5.** `LayaRuntime` accepts only `english`, `multilingual`, `typed-decisions`;
the v12 fine-tune is not among them. The v12 runtime emits `attack`/`stage`/
`severity`, while the runtime consumes `evidence_state`/`strategy`/`evidence_ref`.
No number (including the older ~0.880 pipeline composite) is attributable to B5.

**B4.** Rule-based decision, not hybrid retrieval. Its rule table and decision
contract are not frozen, so B4 has no defined treatment. Hybrid vector+sparse
fusion is not an arm in this protocol.

---

## 3. Validity conditions (all required before any B4/B5 evaluation)

### 3.1 Inherited from B0–B3

- [ ] B3 executes with a resolved generator and applied frozen decoding
      (`BLOCKED_GENERATION_CONFIG` cleared).
- [ ] B2/B3 share canonical corpus content, document-ID set, `top_k`, budget.
- [x] Shared verifier integrated (`research_strict_v1` AVAILABLE), source hashes
      recorded, wall-clock deadline enforced by the core resolver.
- [ ] B3 estimand estimable with complete matched blocks and an adequate
      family/cluster plan.
- [ ] Acceptance criteria for availability/utility prespecified (currently null).

### 3.2 B4-specific

- [ ] Rule table frozen, versioned, SHA-256 recorded.
- [ ] Decision contract tested (ordering, precedence, tie-breaking, refusal).
- [ ] B4 differs from B3 **only** by the decision layer.
- [ ] Decision consumption observable per turn (`decision_consumed`,
      `STRATEGY_UPDATE` reference), never inferred from configuration.
- [ ] Rules not tuned on calibration or holdout data.

### 3.3 B5-specific

- [ ] v12 checkpoint accepted by `LayaRuntime`, or an explicit adapter with a
      migration contract.
- [ ] Field mapping `attack/stage/severity` ↔
      `evidence_state/strategy/evidence_ref` resolved and tested.
- [ ] Checkpoint SHA-256 recorded and loadable offline.
- [ ] Inference determinism documented.
- [ ] B5 differs from B3 **only** by the Laya layer.

### 3.4 Analysis

- [ ] Separate hashed preregistration addendum for H4a and H4b.
- [ ] Multiplicity family updated; H4a/H4b are independent and never pooled.
- [ ] `acceptance_criteria` populated.
- [ ] No composite utility score substitutes for the detection estimand.
- [ ] Higher-level model (Cox/block stratum, family dependence) implemented and
      powered, not only the local AJ + bootstrap summary.

---

## 4. Threats to test explicitly

| Threat | Check |
|---|---|
| Confounded bundle | Arms differ only in the declared layer; shared-bundle hash equality |
| Label leakage | `blind_arm_labels: true`; blind packet IDs |
| Decision-vs-generation conflation | Record `generation_kind` and `decision_consumed` separately |
| Verifier constant | Do not claim a verification effect |
| Holdout reuse | Split seal verified before analysis |
| Small-pilot over-reading | No power claim; no optional stopping |
| Version drift | Hash every treatment artifact; refuse on mismatch |

Shared-field equality for B1–B3 is enforced in
`ragin/evaluation/ablation_contract.py`. No equivalent B4/B5 check exists yet
because their treatments are undefined.

---

## 5. Read-only rule

1. This document may not be edited to add a B4/B5 result before the gate opens.
2. No B4/B5 number may be quoted in any manuscript or abstract.
3. No decision-layer component may be described as “validated”.
4. Any future result must come from a frozen `analysis.json` plus a release
   manifest with the B4/B5 treatment hash recorded.

**Status:** decision-layer evaluation **NOT_STARTED**; validity
**NOT_ESTABLISHED**; gate **CLOSED**. Decision-layer human ratings
**NOT_COLLECTED**.
