# DECEPTION EFFECTIVENESS ANALYSIS — RAGIN

**Status: NOT_MEASURED / NOT_ESTABLISHED.** This is the analysis specification
and its interpretation guards. No detection CIF, risk difference, hazard ratio,
kappa, or utility score has been computed. No B1–B3 arm has run.

**Date:** 2026-10-23 (UTC)
**Protocol:** `docs/research/CAUSAL_ABLATION_PROTOCOL.md` §§7–10
**Implementation:** `ragin/evaluation/analysis.py`
**Plan:** `configs/ablation/eval_v1/analysis_plan_v1.json`
**Result log:** `docs/research/ABLATION_RESULTS.md`

---

## 1. Estimand (definition only)

Deception effectiveness is operationalized as the **cause-specific cumulative
incidence of explicit detection by attacker turn 12**, estimated per arm by
Aalen–Johansen and compared as **paired risk differences within matched blocks
of four arms**.

| Element | Definition |
|---|---|
| Event | First attacker turn whose own text states the host/session is not a real system |
| Time scale | Attacker turns (1–12), not wall-clock |
| Positive | “this is a honeypot”, “I am talking to a fake shell”, “this box is simulated” |
| Negative | “this is odd”, “that command failed”, “I cannot escalate” |
| Competing causes | Abandonment, objective completion, technical failure, unavailable |
| Censoring | Turn cap at 12; administrative stop (development smoke only) |
| Pairing | Matched block of `B0, B1, B2, B3` |
| Interval | Block-bootstrap 95% CI (2000 iterations) |
| Multiplicity | Holm over 3 retrieval contrasts + H1 = 4 tests |
| Sensitivity | Fine–Gray and complete-case, labelled non-primary |

The rubric file is `INSTRUMENT_ONLY_NOT_VALIDATED` with
`validation_status: NOT_STARTED`. Having a rubric is not having a validated
instrument.

---

## 2. Why no effectiveness claim can be made

| Precondition | Status | Evidence |
|---|---|---|
| Any B1–B3 session served | **NO** (0) | no B1–B3 Track B record exists; the 2 B0 records are TEST_ONLY transport |
| B2/B3 retrieval on a shared corpus | **NO** | `retrieval_freeze.shared_corpus` unresolved |
| Frozen generator exposed | **NO** | invocation `UNRESOLVED`; no local generative weights |
| B0 identity matched to B1–B3 | **NO** | `baseline_identity.status = NOT_ESTABLISHED`; observed outer Cowrie identity differs |
| Shared verifier integrated | **YES (integration only)** | `research_strict_v1` AVAILABLE, hashes match, 1.0 s wall-clock deadline |
| Rubric validated | **NO** | `validation_status: NOT_STARTED` |
| Human labels collected | **NO** | no submission exists; builder emits empty templates |
| Acceptance criteria for H1–H5 | **NONE** | `acceptance_criteria: null` |
| Higher-level stats plan | **NO** | Cox/family-level model not implemented; 2 dev scenarios exploratory |

`analysis.py` refuses every H1–H5 support claim when criteria are absent or an arm
is unexposed. Missing or unexposed is **not** negative evidence.

---

## 3. Binding interpretation guards

1. **Detection CIF alone is misleading.** Always report technical-failure,
   unavailable, abandonment, and objective-completion incidence jointly.
2. **A falling detection CIF can mean a worse arm.** More failure/abandonment
   can remove detection opportunities without improving deception. Report
   receipt/admission and compliant-exposure rates next to every arm.
3. **ITT is primary.** Failed, abandoned, and technically incomplete sessions
   stay in the allocated count. Outcome-dependent replacement is forbidden;
   per-protocol is a labelled sensitivity only.
4. **No command-level pseudoreplication.** The unit is the session; turns are
   clustered. Records whose event time exceeds observed turns are rejected.
5. **No primary composite.** Quality, safety, engagement, and operational
   families are reported separately.
6. **A non-significant estimate is not zero.** Report “not detected at this
   sample size” or inconclusive, within the design's precision.
7. **No tuning on holdout or pilot.** Thresholds and the main-study target are
   fixed only in a separate, hashed preregistration addendum.
8. **Censoring is not an event.** A known-answer test fixes the prior bug:
   detection@1 + `ADMIN_CENSORED`@1 + detection@2 gives CIF(2)=1.0; replacing the
   censor with `TECHNICAL_FAILURE`@1 gives 2/3.

---

## 4. Not identifiable in this design

| Claim | Status | Reason |
|---|---|---|
| Pure “LLM effect” from B1 vs B0 | **NOT IDENTIFIABLE** | B1 also adds RAGIN serving and the shared verifier |
| Verification effect | **NOT IDENTIFIABLE** | Verifier held constant across B1–B5; B0 lacks it |
| Effect of retrieval *quality* | **NOT IDENTIFIABLE** | B2/B3 backend differs; no shared corpus yet |
| Human-attacker effectiveness | **NOT SUPPORTED** | No human data; ratings not collected |
| Generalization beyond the frozen runtime | **NOT SUPPORTED** | Scope is the captured environment only |
| Family-level/hierarchical generalization | **NOT SUPPORTED** | Only block clusters; 2 development scenarios |

**H1 is a system-package effect**, not a pure LLM effect. B0 is native Cowrie by
cached image ID, loopback-only, with no shared RAGIN verifier. Until observed
user/OS/kernel/shell/hostname/cwd match, H1 is blocked because the contrast
confounds the system package with host identity. The actual terminal trace also
shows an outer `root@svr04:/#` prompt wrapping inner `webapp@web-srv-01` output;
that contradiction is preserved, not stripped.

---

## 5. Decision layers (B4/B5)

B4 (rule-based decision) and B5 (fine-tuned Laya) are **NOT_STARTED**. They are
independent contrasts against B3 and are never pooled. Their validity depends on
B3 first being executable, which it is not. **P2 decision audit:
NOT STARTED / conditional.** See `DECISION_LAYER_VALIDITY_REPORT.md`.

---

## 6. Human-label instrument (prepared, not used)

`ragin/evaluation/human_packet.py` builds a **blind** packet: arm labels are
stripped, item IDs are neutral hashes, and the packet is hashed before release.

| Rule | Implementation |
|---|---|
| Detection requires an **observed attacker statement** | else the item is rated `UNAVAILABLE` |
| Never infer suspicion from shell output | enforced by item construction/validator |
| `source=HUMAN` is self-report, not identity proof | recorded explicitly |
| AI labels cannot be submitted as human | `ValueError` |
| Multi-dimension ratings | shell realism, cross-turn consistency, detectability, credibility, error severity |
| No pre-filled ratings | templates emit `""` for every dimension |
| Agreement reported, validity not claimed | Cohen's κ / Krippendorff's α + raw disagreements |

**Human ratings are NOT_COLLECTED.** `build_packet` produces empty templates; the
`TEST_ONLY` status is `TEST_ONLY_INSTRUMENT_SMOKE`, explicitly not
human-validation data.

Known pre-labeling inconsistency: the packet's embedded rubric has four labels
(`YES/NO/UNCERTAIN/UNAVAILABLE`) while the contract-pinned
`detection_rubric_v1.json` has three (`YES/NO/UNCERTAIN`). Reconcile or pin the
packet rubric before collecting labels.

---

## 7. What this file will contain after a real run

Only values from a frozen `analysis.json` produced by
`scripts/analyze_ablation_v1.py`, with per-arm AJ CIF at turns 6 and 12 plus all
competing causes; paired risk differences with 95% bootstrap CIs and matched-block
counts; Holm-adjusted p-values over the full 4-test family (or `INCOMPLETE`);
receipt/admission and compliant-exposure rates; event/censoring counts and
technical-failure reasons; and an explicit `NOT_ESTABLISHED` wherever an arm is
absent or unexposed.

Until that artifact exists, **deception effectiveness remains NOT_MEASURED**.
Track A and TEST_ONLY smoke records never enter this analysis.
