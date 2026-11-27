# CAUSAL ABLATION PROTOCOL — RAGIN

**Status:** DESIGN FROZEN v2. **Execution lock: INCOMPLETE.**
**Frozen:** 2026-10-22
**Scope:** B0–B5 design. B4 and B5 are defined but **NOT READY**.
**Spend this phase:** **$0**. No provider calls, no experiment execution, no model downloads.

> This document defines the design. It does not report an executed arm, an effect,
> or a powered result. Per-arm executability and blockers are in
> `docs/research/EXPERIMENT_READINESS_REPORT.md`. Configuration files are under
> `configs/ablation/` with `configs/ablation/manifest_v2.json` (v1 is preserved as a
> prior version). Arm commands are startup wiring templates only, and the proposed
> generator/resource fields are not enforced by the current runtime.

---

## 0. Claim boundary

The design estimates the causal effect of RAGIN's **mediation layers** on a
simulated attacker's detection of the host as non-real, holding the generator and
the shared verifier fixed where the arms permit it.

It can support:

- internal comparisons among randomized arms for the declared attacker-agent
  population, scenario families, and runtime;
- a generator-matched retrieval contrast (B1/B2/B3) and a dense-versus-sparse
  contrast (B3 vs B2);
- a bundled generative-system contrast (B1 vs B0) with the qualification in §3.1.

It cannot support:

- claims about human attackers;
- claims about models, prompts, or providers outside the frozen configuration;
- claims about environments outside the captured runtime;
- a pure "LLM effect" from B1 vs B0, because B1 also adds RAGIN serving and the
  shared verifier;
- a causal contrast for verification when verification is held constant;
- a claim that a non-significant estimate is zero;
- any result described as human-validated.

The human reference protocol (`human_v1`) exists, but human labels are **not
collected** (`results/laya_research/human_annotation_collection_status.json`:
`human_labels_collected = false`).

---

## 1. Fixed components and the shared bundle

All B1–B5 use one frozen generator configuration and one shared verifier bundle.
B0 is the native reference and intentionally does not use them.

| Component | Requirement |
|---|---|
| Generator identity | Exact model/revision (or local checkpoint SHA-256) recorded per request |
| Decoding | `temperature`, `top_p`, `max_tokens`, stop sequences, seed fixed and recorded |
| Prompt | Versioned and hashed; identical across B1–B5 except for the retrieval evidence block |
| Retries | Fixed maximum; every retry counted |
| Fallback | If the generator is unavailable, the arm does **not** run. No template or different-model substitution |
| Verifier | `FictionConsistencyVerifier` + `HostFictionVerifier`, mandatory and identical across B1–B5 |
| Persona | `data/host_fiction.json`, hashed; same host fiction across B1–B5 |
| Resources | Same **proposed** CPU/memory/concurrency budget for B1–B3; the JSON values are not cgroup-enforced, and dense embedding memory is not separately budgeted in this phase |

The verifier bundle is **consistency and identity checking** plus optional
supported-claim checks. It is not a general semantic-grounding oracle. A plausible
ungrounded claim can pass when no supported command is in scope; that limitation is
recorded in the audit and must not be described as full grounding.

A deterministic template runtime (for example
`RAGIN_V4_SUBSTANTIVE_DETERMINISTIC`) is **not** a generator arm. It may be used for
transport/serving integration traces, but not for a primary detection endpoint.

---

## 2. Arms

| Arm | Treatment | Retrieval | Verifier | Generator | Status |
|---|---|---|---|---|---|
| **B0** | Native Cowrie | None (native shell) | None | Native Cowrie | Executable locally as a transport; no experiment allocation executed |
| **B1** | Cowrie + LLM, no retrieval | **none** | Shared, mandatory | Frozen generator | Blocked: frozen generator/prompt/price unresolved |
| **B2** | B1 + BM25 | **bm25** (sparse only) | Shared, mandatory | Frozen generator | Blocked: frozen generator/prompt/price unresolved |
| **B3** | B1 + dense RAG | **dense** (exact store, no BM25 mixing) | Shared, mandatory | Frozen generator | Blocked: exact store, local embedding model, and frozen generator unresolved |
| **B4** | B3 + **rule-based decision** | dense | Shared, mandatory | Frozen generator | **NOT READY** (rule table/contract not frozen) |
| **B5** | B3 + fine-tuned Laya | dense | Shared, mandatory | Frozen generator | **NOT READY** (checkpoint/contract blockers) |

B4 is **rule-based decision**, not hybrid retrieval. Hybrid vector+sparse fusion is
not an arm in this protocol.

### 2.1 B5 blockers

1. `LayaRuntime` accepts only upstream checkpoint names (`english`, `multilingual`,
   `typed-decisions`); the v12 fine-tune is not among them.
2. The v12 runtime contract emits `attack`/`stage`/`severity`, while the runtime
   consumes `evidence_state`/`strategy`/`evidence_ref`.

No numeric result, including the ~0.880 pipeline composite, is attributed to B5.

---

## 3. Hypotheses

### 3.1 H1 — generative system package (B1 vs B0)

**Contrast:** B1 versus B0.

**Interpretation:** the effect of moving from a native Cowrie shell to the RAGIN
generative serving package. B1 bundles at least three differences: an LLM generator,
RAGIN's serving/verification path, and the shared verifier. H1 is therefore a
**bundled system-package effect**, not a pure LLM effect. The comparison is retained
because it is the requested ecological contrast; it is reported with that
qualification.

### 3.2 H2 — retrieval versus no retrieval

- **H2a:** B2 vs B1 (BM25 added).
- **H2b:** B3 vs B1 (dense RAG added).

### 3.3 H3 — dense versus sparse

- **H3:** B3 vs B2.

### 3.4 H4 — decision layers

- **H4a:** B4 vs B3 (rule-based decision added).
- **H4b:** B5 vs B3 (fine-tuned Laya added).

H4a and H4b are independent contrasts; they are not pooled.

### 3.5 H5 — full utility

A prespecified utility summary over detection, objective completion, latency, and
cost. H5 is descriptive/composite in the pilot; it is not a substitute for the
primary detection estimand.

### 3.6 What is not identifiable

The verifier is held constant across B1–B5. No arm turns verification off while
holding the generator and retrieval fixed. **No causal contrast for verification is
identifiable in this design.** B0 has no RAGIN verifier, but it also differs in the
generator and serving surface, so B0 does not identify a verification effect.

---

## 4. Two evaluation tracks

### 4.1 Track A — fixed-trace matched-command response evaluation

A frozen set of command traces is sent to each arm. The response is evaluated for
quality, consistency, safety, and evidence use under **identical commands**.

- Track A is a separate, frozen response evaluation.
- It is **not** closed-loop attacker engagement and cannot establish engagement,
  detection, or time-to-suspicion.
- Its inputs, prompts, evaluator instructions, and scoring codebook are hashed
  before use.
- Track A results are never pooled with Track B's primary estimand.

### 4.2 Track B — closed-loop SSH

A live attacker agent drives a real SSH session against the arm. This is the only
track that can support the primary detection estimand. The arm label is hidden from
the attacker and from the suspicion annotator.

---

## 5. Families, controls, and data splits

### 5.1 Data splits

- **Development families:** used to debug prompts, tooling, and the attacker agent.
  Never used for the primary estimate.
- **Calibration families:** used to estimate variance, technical-failure rates, and
  feasibility; not used for the confirmatory estimate.
- **Holdout families:** sealed until the analysis and codebook are hashed. No
  tuning on holdout.

A family may appear in only one split. The split assignment is hashed before any
session.

### 5.2 Attacker-competence controls

Control tasks test whether the attacker agent can perform the intended actions and
report them, independent of honeypot realism. Examples: a task with a known answer
on a benign host, a task that requires a specific tool/command, and a task that
requires reporting a dead end. If the attacker fails the controls, engagement
results are not interpretable as honeypot effects.

### 5.3 Meaningful engagement

"Meaningful engagement" is predeclared as a minimum number of substantive
attacker turns and at least one objective-directed action, with the exact codebook
frozen before data collection. It is a process measure, not the primary endpoint.

### 5.4 Endpoint families reported separately

- **Detection/suspicion:** primary.
- **Quality:** response consistency, evidence use, coherence; separately reported.
- **Safety:** unverified serves, dangerous tells, unsafe content; separately
  reported.
- **Operational:** latency, 503/fail-closed rate, retries, cost; separately
  reported.

No composite silently replaces these families.

---

## 6. Sample, allocation, and bounded pilot

### 6.1 Unit

One SSH session. Turns are clustered within a session and are never independent
observations.

### 6.2 Bounded pilot allocation

The first pilot is **not** 30 completed sessions per arm. It is:

```
2 development scenarios × 2 attacker profiles × 2 seeds × 4 arms
= 32 ALLOCATED sessions
```

with a maximum of **12 attacker turns per session**.

- Allocation is randomized within blocks of four (one per arm), with the order
  generated from a recorded seed and hashed before the first session.
- **No automatic execution.** Starting the pilot requires the execution lock in
  §14 to be complete.
- Failed, abandoned, and technically incomplete sessions remain in the allocated
  count. They are not replaced outcome-dependently.
- Calibration and holdout sessions are separate allocations and are not included
  in the 32.

A 30-completed-per-arm design is a larger study, not a small first pilot. It is not
authorized by this protocol.

### 6.3 No power claim

The pilot estimates feasibility, event rates, variance, block intraclass
correlation, technical-failure rates, and cost. The target effect and the main-study
sample size are chosen **after** the pilot from those estimates, by simulation of
the prespecified model, in a separate protocol addendum. No powered claim is made
now. No optional stopping for significance is allowed.

---

## 7. Endpoints and competing risks

### 7.1 Primary endpoint

The first attacker turn whose text contains an **explicit statement that the host
or session is not a real system** (for example "this is a honeypot", "I am talking
to a fake shell", "this box is simulated"). Mere confusion, a failed command, or
"this is odd" does not count. The positive/negative examples and the codebook are
frozen and hashed before collection.

The time scale is **attacker turns**, not wall-clock. Wall-clock latency is a
secondary operational measure.

### 7.2 Terminal causes and censoring

| Situation | Classification |
|---|---|
| Explicit detection | Primary event |
| Attacker abandons the session or declares the objective complete without detection | **Informative competing terminal cause**; do not assume noninformative censoring |
| Administrative turn cap (12) reached without detection or abandonment | **Right-censored** at the cap |
| Technical failure, provider outage, 503 loop, operator stop | **Separate competing/unavailable cause**, with reason recorded |
| Session killed by budget/rate limit | Competing/unavailable cause, reason recorded |

Abandonment and objective completion are not silently treated as ordinary
censoring. The analysis reports their incidence and uses a competing-risks model.

### 7.3 Primary estimand

The **cause-specific cumulative incidence of detection at a fixed horizon of 12
turns**, with abandonment/objective completion and technical failure as explicit
competing causes.

The primary between-arm summaries are **paired risk differences in the
cause-specific CIF at turn 12**, with 95% confidence intervals. Blocks define the
pairing.

### 7.4 Primary model

One primary model family is fixed:

- cause-specific Cox regression for the detection hazard, with block as stratum
  and arm as a fixed effect, cluster-robust variance by block;
- the absolute risk is reported from the Aalen–Johansen cause-specific CIF at
  turn 12;
- a Fine–Gray subdistribution model is a **sensitivity analysis only**, not a
  second primary model.

The protocol does not switch between Cox-primary and Fine–Gray-primary after seeing
data. If the proportional-hazards assumption fails on prespecified diagnostics, the
primary summary remains the turn-12 CIF risk difference and the hazard ratio is
reported as model-dependent.

### 7.5 Secondary endpoints

- Detection CIF at turns 6 and 12.
- Meaningful-engagement rate (predeclared process measure).
- Objective-completion and abandonment rates.
- Verified-serve rate, fallback rate, 503/fail-closed rate, technical-failure rate.
- Served-turn latency p50/p95, separated from attacker think time.
- Tokens in/out and cost per session.
- Verifier rejection reasons by code.
- Safety: unverified serves; contradiction-passing serves found by audit.
- Quality: separate report, not pooled into detection.

Unvalidated Likert-style quality proxies are exploratory only.

---

## 8. Multiplicity

The confirmatory family is defined by the **number of contrasts actually tested**,
not by hypothesis labels:

- retrieval family: B2 vs B1, B3 vs B1, B3 vs B2 = **3 contrasts**;
- H1: B1 vs B0 = **1 contrast** if tested.

So the Holm family is **4 tests**, not 2. If H1 is later decomposed into two
sub-contrasts, the family is **5**, not 2. H4a/H4b are not in this family because
B4/B5 are not ready. Secondary endpoints use Benjamini–Hochberg and are labelled
exploratory. No correction turns an exploratory result into confirmatory evidence.

---

## 9. Analysis, missingness, and negative evidence

- Primary analysis is by allocated arm (intention-to-treat).
- Technical failures remain visible as competing/unavailable causes; they are not
  deleted.
- Sensitivity analyses: per-protocol excluding technical failures; worst-case
  assignment of missing detection labels; exclusion of accidentally unblinded
  blocks. Every exclusion is reported with its reason.
- Every estimate carries a 95% CI and the number of sessions/events.
- **A non-significant estimate is not zero.** A negative finding may be reported as
  evidence of absence only within the precision the design supports; otherwise it
  is **inconclusive**. "Not detected at this sample size" is one allowed wording,
  not the only one.
- Negative and inconclusive evidence is preserved, including failed arms and
  unusable sessions. It is never overwritten by a later positive result.

---

## 10. Label quality

- Two independent annotators label the detection event blind to arm.
- A third adjudicates disagreements.
- Report Cohen's κ or Krippendorff's α and the raw disagreement list.
- AI annotators are labelled **AI-derived**, never human.
- Human labels, if ever collected under `human_v1`, are a separate validation study
  and are not pooled with AI labels.

---

## 11. Decisions are a separate preregistration

No decision about the target effect, main-study sample size, model formula changes,
or utility weighting is made in this document. Those decisions require a separate
preregistration addendum, hashed before the main study. The pilot informs them; the
pilot does not authorize them.

---

## 12. Illustrative cost and runtime bounds

These numbers are **ILLUSTRATIVE ASSUMPTIONS**, not measurements. They assume the
bounded pilot in §6.2: 32 allocated sessions (8 per arm, B0–B3) with a maximum of
12 turns per session. **No pilot has been run.** Every per-call token/latency
figure below is an assumption, and provider prices remain unknown.

### 12.1 Call counts

```
allocated sessions                  = 32 (8 per arm, B0-B3)
maximum served turns                = 32 × 12 = 384
generator calls, B1-B3 only (no retry) = (32 - 8) × 12 = 24 × 12 = 288
generator calls, B1-B3 only (max 1 retry) = 288 .. 576
generator calls, B0                 = 0 (native Cowrie shell)
attacker-agent calls               ≤ 384 (one per turn; upper assumption)
evaluator/annotator calls           = 32 sessions × 2 independent labels = 64
local retrieval queries, B2+B3      ≤ 192 total (16 sessions × 12 = 96/arm)
                                    before retry/retrieval repetition; 0 provider calls
verification calls                  = per candidate, including retries and the
                                    fallback path; ≥ served turns, not one fixed
                                    call per session turn
```

Retries are counted as generator calls. A failed generation still consumes an
allocated turn. B0 contributes no generator, verifier, or RAGIN retrieval calls;
its native shell is a different bundle (see §3.1).

### 12.2 Token bounds

Assume 1,500 input tokens and 300 output tokens per served generator call (prompt +
history + evidence; completion). These are planning assumptions, not observations.

```
tokens_in, base (288 calls)    ≈ 288 × 1,500 = 432,000
tokens_out, base (288 calls)   ≈ 288 ×   300 =  86,400
tokens_in, worst (576 calls)   ≈ 576 × 1,500 = 864,000
tokens_out, worst (576 calls)  ≈ 576 ×   300 = 172,800
attacker  ≈ 384 × 500          = 192,000 (upper assumption)
evaluator ≈ 64 × 2,000         = 128,000
```

Including evaluator/control costs, the illustrative band is approximately
**0.84M–1.36M tokens** across the pilot (base to one-retry worst case), with
evidence length and actual retry incidence as the main uncertainty. Measured usage
replaces the estimate when the provider reports it; otherwise label it **ESTIMATED**.

### 12.3 Runtime

```
generation, base (288 × 8 s)  ≈ 38 min
generation, worst (576 × 8 s) ≈ 77 min
attacker (384 × 5 s)          ≈ 32 min (upper assumption)
retrieval (192 × 0.2 s)       ≈ 0.6 min total local B2+B3
verification                  = local, per candidate; per-call latency not
                                measured, so no verifier time bound is asserted
overhead (32 × 2 min)         ≈ 64 min
sequential total              ≈ 2.25 h base .. 2.9 h worst generation
with 2 parallel slots         ≈ 1.1 h .. 1.5 h if sessions are parallelizable
```

These are planning bounds, not guarantees. A provider outage makes the arm
unavailable, not slower. Verifier candidate count (including retries and fallback)
can exceed served turns and is deliberately not reduced to 384.

### 12.4 Price

`P_in` and `P_out` are **UNKNOWN/UNSET** in this phase. No dollar cost is asserted,
and no pilot has been run. The formula is applied to 288 base generator calls
(≤576 with one retry) for B1–B3, plus 64 evaluator labels:

```
cost = tokens_in × P_in + tokens_out × P_out
     + retries × (retry_in × P_in + retry_out × P_out)
     + evaluator_tokens × P_eval
```

Local retrieval and local verification add **0 provider calls**. A local model
replaces token prices with GPU-hours × rate plus amortized host cost, recorded
before the run.

**This phase: 0 provider calls, $0 spend, 0 downloads.**

---

## 13. Execution lock

The design is frozen, but **execution is locked** until all of the following exist
and are hashed:

1. Exact generator identity/revision, decoding configuration, prompt template, and
   price.
2. Frozen attacker-agent prompts and tools.
3. Frozen suspicion codebook with positive/negative examples.
4. Frozen family split (development/calibration/holdout) and scenario data.
5. Allocation seed and sequence file.
6. Exact B3 store (`index.faiss`, `documents.json`), embedding-model identity/hash,
   and store path.
7. Verifier source hash and the shared bundle configuration.
8. Host-fiction/persona file hash.
9. B4 rule table and contract, if B4 is ever enabled.
10. B5 checkpoint and v12 contract compatibility, if B5 is ever enabled.

`configs/ablation/manifest_v2.json` records the current config hashes, the actual
UTC generation time, and `execution_lock = INCOMPLETE`. The prior v1 file is
preserved unchanged; its midnight `frozen_utc` is labelled fabricated precision
and is not a freeze claim. Missing items are listed in the manifest and the
readiness report. A partial arm is not an ablation and is not reported as one.

---

## 14. What invalidates the design

- Different generators across B1–B5.
- Non-random or post-hoc arm assignment.
- Outcome-dependent replacement of failed sessions.
- Changing the endpoint, horizon, codebook, or model after seeing data.
- Reusing holdout families for tuning.
- Treating turns as independent observations.
- Reporting 1 − Kaplan–Meier absolute risk with non-negligible competing events.
- Presenting Track A fixed-trace tests as evidence of engagement.
- Calling AI annotations human.
- Describing B1 vs B0 as a pure LLM effect.
- Claiming a verification effect when verification was held constant.

Any of these makes the result exploratory at best and requires a new protocol
version with a written reason and a new hash.

---

## 15. Frozen decisions (v2)

| Decision | Value |
|---|---|
| Arms defined | B0, B1, B2, B3, B4, B5 |
| Pilot arms | B0, B1, B2, B3 |
| B4 | Rule-based decision on B3; NOT READY |
| B5 | Fine-tuned Laya on B3; NOT READY |
| Unit | SSH session |
| Pilot allocation | 2 scenarios × 2 profiles × 2 seeds × 4 arms = 32 allocated |
| Turn cap | 12 |
| Primary endpoint | Explicit detection, attacker turns |
| Primary estimand | Cause-specific detection CIF at turn 12; paired risk differences |
| Primary model | Cause-specific Cox + Aalen–Johansen CIF; Fine–Gray sensitivity only |
| Competing causes | Detection, abandonment/objective completion, technical failure/unavailable; cap right-censored |
| Multiplicity | Holm over 3 retrieval contrasts + H1 if tested = 4 tests (5 if H1 split); never 2 |
| Track A | Fixed-trace matched-command response evaluation; no engagement claim |
| Track B | Closed-loop SSH; only track for primary detection |
| Generator | One frozen configuration across B1–B5 |
| Verification | Shared and constant across B1–B5; no causal contrast |
| Provider spend this phase | $0 |

Changes require a new version (`v3`) with a written reason and a new hash. Silent
edits are not permitted.
