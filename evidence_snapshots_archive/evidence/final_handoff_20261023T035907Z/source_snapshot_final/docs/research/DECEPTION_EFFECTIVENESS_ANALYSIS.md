# DECEPTION EFFECTIVENESS ANALYSIS — RAGIN

**Status: NOT_MEASURED / NOT_ESTABLISHED.** Analysis specification and
interpretation guards only. No detection CIF, risk difference, hazard ratio,
kappa, or utility score has been computed. No B1–B3 arm has run.

**Date:** 2026-10-23 (UTC) · **Protocol:** `CAUSAL_ABLATION_PROTOCOL.md` §§7–10 ·
**Implementation:** `ragin/evaluation/analysis.py` · **Plan:**
`configs/ablation/eval_v1/analysis_plan_v1.json` · **Result log:**
`ABLATION_RESULTS.md`.

---

## 1. Estimand (definition only)

Deception effectiveness = **cause-specific cumulative incidence of explicit
detection by attacker turn 12**, estimated per arm by Aalen–Johansen and compared
as **paired risk differences within matched blocks of four arms**.

| Element | Definition |
|---|---|
| Event | First attacker turn whose own text states the host/session is not real |
| Time scale | Attacker turns (1–12), not wall-clock |
| Positive | “this is a honeypot”, “fake shell”, “this box is simulated” |
| Negative | “this is odd”, “that failed”, “I cannot escalate” |
| Competing causes | Abandonment, objective completion, technical failure, unavailable |
| Censoring | Turn cap 12; administrative stop (development smoke only) |
| Pairing | Matched block of `B0, B1, B2, B3` |
| Interval | Block-bootstrap 95% CI (2000 iterations) |
| Multiplicity | Holm over 3 retrieval contrasts + H1 = 4 tests |
| Sensitivity | Fine–Gray and complete-case, labelled non-primary |

The rubric is `INSTRUMENT_ONLY_NOT_VALIDATED` with `validation_status:
NOT_STARTED`. Having a rubric is not having a validated instrument.

---

## 2. Why no effectiveness claim can be made

| Precondition | Status |
|---|---|
| Any B1–B3 session served | **NO** (0); the 2 B0 records are TEST_ONLY transport |
| B2/B3 retrieval on a shared corpus | **NO** — shared corpus/`top_k`/budget unresolved |
| Frozen generator exposed | **NO** — invocation `UNRESOLVED`; no local generative weights |
| B0 identity matched to B1–B3 | **NO** — `NOT_ESTABLISHED`; outer Cowrie identity differs |
| Shared verifier integrated | **YES (integration only)** — `research_strict_v1`, hashes match, 1.0 s wall clock |
| Rubric validated | **NO** — `validation_status: NOT_STARTED` |
| Human labels collected | **NO** — builder emits empty templates |
| Acceptance criteria | **NONE** — `acceptance_criteria: null` |
| Higher-level stats plan | **NO** — Cox/family model not implemented; 2 dev scenarios exploratory |

The analysis refuses every H1–H5 support claim when criteria are absent or an arm
is unexposed. Missing/unexposed is **not** negative evidence.

---

## 3. Binding interpretation guards

1. **Detection CIF alone is misleading.** Always report technical-failure,
   unavailable, abandonment, and objective-completion incidence jointly.
2. **A falling detection CIF can mean a worse arm.** More failure/abandonment can
   remove detection opportunities without better deception. Report
   receipt/admission and compliant-exposure rates next to every arm.
3. **ITT is primary.** Failed/abandoned/incomplete sessions stay in the allocated
   count; outcome-dependent replacement is forbidden. Per-protocol is a labelled
   sensitivity only.
4. **No command-level pseudoreplication.** Unit = session; turns are clustered.
   Event times beyond observed turns are rejected.
5. **No primary composite.** Quality, safety, engagement, operational families
   are reported separately.
6. **Non-significance is not zero.** Report “not detected at this sample size”
   or inconclusive, within design precision.
7. **No tuning on holdout/pilot.** Thresholds and the main-study target are fixed
   only in a separate, hashed preregistration addendum.
8. **Censoring is not an event.** Known answer: detection@1 + `ADMIN_CENSORED`@1
   + detection@2 ⇒ CIF(2)=1.0; replacing the censor with `TECHNICAL_FAILURE`@1
   ⇒ 2/3.

---

## 4. Not identifiable in this design

- **Pure “LLM effect” (B1 vs B0): NOT IDENTIFIABLE** — B1 adds RAGIN serving and
  the shared verifier.
- **Verification effect: NOT IDENTIFIABLE** — verifier held constant; B0 lacks it.
- **Retrieval-quality effect: NOT IDENTIFIABLE** — backend differs; no shared corpus.
- **Human-attacker effectiveness: NOT SUPPORTED** — no human data/ratings.
- **Generalization beyond the runtime / family level: NOT SUPPORTED** — one
  captured environment, block clusters only, 2 development scenarios.

**H1 is a system-package effect**, not a pure LLM effect. B0 is native Cowrie by
cached image ID, loopback-only, with no shared verifier. Until observed
user/OS/kernel/shell/hostname/cwd match, H1 is blocked because the contrast
confounds the package with host identity. The actual trace preserves the
contradiction (outer `root@svr04:/#` wrapping inner `webapp@web-srv-01`); it is
not stripped.

## 5. Decision layers and human instrument

B4 (rule-based decision) and B5 (fine-tuned Laya) are **NOT_STARTED**, independent
contrasts against B3, never pooled, and require B3 to execute first. **P2 decision
audit: NOT STARTED / conditional.** See `DECISION_LAYER_VALIDITY_REPORT.md`.

`ragin/evaluation/human_packet.py` builds a **blind** packet (arm labels stripped,
neutral hashed IDs, packet hashed before release). Detection requires an observed
attacker statement, else the item is `UNAVAILABLE`; suspicion is never inferred
from shell output; `source=HUMAN` is self-report, not identity proof; AI labels
cannot be submitted as human; ratings are never pre-filled; only agreement
(Cohen's κ / Krippendorff's α + disagreements) is reported.

**Human ratings are NOT_COLLECTED.** `build_packet` emits empty templates;
`TEST_ONLY_INSTRUMENT_SMOKE` is not human-validation data. Before labeling,
reconcile the packet's four-label rubric (`YES/NO/UNCERTAIN/UNAVAILABLE`) with the
contract-pinned three-label `detection_rubric_v1.json`.

## 6. After a real run

Only values from a frozen `analysis.json` produced by
`scripts/analyze_ablation_v1.py`: per-arm AJ CIF at turns 6 and 12 plus all
competing causes; paired risk differences with 95% bootstrap CIs and matched-block
counts; Holm-adjusted p-values over the 4-test family (or `INCOMPLETE`);
receipt/admission and compliant-exposure rates; event/censoring counts and
failure reasons; explicit `NOT_ESTABLISHED` where an arm is absent/unexposed.
Track A and TEST_ONLY smoke records never enter this analysis. Until then,
**deception effectiveness remains NOT_MEASURED**.
