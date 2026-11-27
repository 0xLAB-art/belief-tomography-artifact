# ABLATION RESULTS — RAGIN causal ablation

**Status: NOT_MEASURED.** No B1–B3 ablation arm has executed. No detection CIF,
risk difference, hazard ratio, agreement statistic, latency, token count, or cost
is reported here. All H1–H5 remain **NOT_ESTABLISHED**.

**Date:** 2026-10-23 (UTC)
**Protocol:** `docs/research/CAUSAL_ABLATION_PROTOCOL.md` (frozen design; this file is a living result log)
**Run contract:** `configs/ablation/eval_v1/run_contract_v1.json`
**Evidence root for this pass:** `evidence/final_handoff_20261023T035907Z/`
**Spend:** $0, 0 provider calls, 0 downloads, 0 public listeners.

---

## 1. What actually ran

| Run | Scope | Result | Artifact |
|---|---|---|---|
| B0 native smoke #1 | `TEST_ONLY` transport/control | 2 turns, `ADMIN_CENSORED`, no detection, exit 0 | `/tmp/opencode/ragin_b0_smoke_20261023_034743`; copied under `evidence/.../b0_smoke_raw/smoke_1_034743/` |
| B0 native smoke #2 | `TEST_ONLY` transport/control | 2 turns, `ADMIN_CENSORED`, no detection, live loopback listener `127.0.0.1:60889`, cleanup true, exit 0 | `/tmp/opencode/ragin_b0_smoke_20261023_034852`; copied under `evidence/.../b0_smoke_raw/smoke_2_034852/` |
| Track A dry run | frozen command trace | exit 0; 2 scenarios, 4 commands each | `evidence/.../track_a_dryrun.*` |
| Track B dry run | B0 environment check | exit 0; cached image only, no container started | `evidence/.../track_b_dryrun.*` |

Both raw smoke directories were copied byte-for-byte to the repository evidence
root and verified item-by-item (`b0_smoke_copy_verification.json`,
`all_identical=true`). The temporary originals were not rewritten. Smoke #1's
summary is preserved with its measured defect (`ssh_loopback_only=false`,
`listeners=[]` captured after cleanup); it is **not** listener evidence. Smoke #2
is the final live-listener record. The raw manifest includes both `summary.json`
files and excludes only itself (`b0_smoke_raw/RAW_OUTPUTS_SHA256_FINAL.json`).

These are **transport/control mechanics**, not an ablation and not model
inference. B0 remains identity-unmatched to the B1–B3 host fiction.

---

## 2. Allocation (design, not execution)

The frozen development allocation is **32 sessions**:

`2 scenarios × 2 scripted profiles × 2 seeds × 4 arms = 32`, turn cap **12**,
development split only. **Executed ablation sessions: 0 / 32.**
Calibration and holdout families are empty/pending. Only 2 development
scenarios exist, so bootstrap contrasts are diagnostic and **exploratory**, not
confirmatory.

B0 uses 8 of those slots; the 24 B1–B3 slots are blocked below. The allocation
sequence is frozen in `configs/ablation/eval_v1/allocation_sequence_v1.json` and
its hash is checked by preflight.

---

## 3. Arm and hypothesis status

| Arm | Treatment | Status | Reason |
|---|---|---|---|
| **B0** | Native Cowrie | `EXECUTABLE_LOCAL_TRANSPORT_ONLY` | Not a RAGIN arm; no generator, verifier, or retrieval effect |
| **B1** | Cowrie + frozen LLM, retrieval off | `NOT_READY` | Frozen model/prompt/price/invocation unresolved; runner not implemented |
| **B2** | B1 + BM25 | `NOT_READY` | Same generator blockers; B2 corpus unresolved |
| **B3** | B1 + dense | `NOT_READY` | Exact store and local embedding model unresolved; generator unresolved |
| **B4** | B3 + rule decision | `NOT_READY` | Rule table/decision contract not frozen |
| **B5** | B3 + fine-tuned Laya | `NOT_READY` | v12 checkpoint/contract mismatch |

| Hypothesis | Contrast | Status |
|---|---|---|
| **H1** | B1 vs B0 | **NOT_ESTABLISHED** — no B1 session; B0 has no shared verifier and is identity-unmatched. H1 is a **system-package effect**, never a pure LLM effect. |
| **H2a/H2b** | B2 vs B1, B3 vs B1 | **NOT_MEASURED** |
| **H3** | B3 vs B2 | **NOT_MEASURED** — no shared canonical corpus/doc-ID set/`top_k`/budget |
| **H4a/H4b** | B4 vs B3, B5 vs B3 | **NOT_STARTED** |
| **H5** | Utility summary | **NOT_ESTABLISHED** — no prespecified utility acceptance rule |

`scripts/run_ablation_track_b_v1.py` refuses every non-B0 arm with
“B1-B3 execution is not implemented in this development runner”. A design-valid
contract would not start a B1–B3 session.

---

## 4. Preflight result (actual)

`scripts/ablation_preflight_v1.py --env-check` returned **exit 2**:
`design.status=DESIGN_VALID` (no errors) and `execution_status=NOT_READY`
(**24 blockers**). The blockers are explicit and were not removed to force a
pass:

- **Model/generation:** `UNRESOLVED_MODEL`, `UNRESOLVED_PROMPT`,
  `UNRESOLVED_PROMPT_ID`, `UNRESOLVED_EFFECTIVE_GENERATION_CONFIG`,
  `BLOCKED_GENERATION_CONFIG`, `MODEL_EXPOSURE_NOT_ENFORCED`,
  `FALLBACK_NOT_DISABLED`, `MODEL_INVOCATION_UNAVAILABLE`.
- **Data/persona:** `UNRESOLVED_PERSONA`.
- **Corpus/retrieval:** `UNRESOLVED_SHARED_CORPUS_CONTENT`,
  `UNRESOLVED_SHARED_DOCUMENT_IDS`, `UNRESOLVED_RETRIEVAL_TOP_K`,
  `UNRESOLVED_RETRIEVAL_CONTEXT_BUDGET`, `UNRESOLVED_B3_STORE`,
  `UNRESOLVED_EMBED_MODEL`, `UNRESOLVED_B2_CORPUS`.
- **Attacker:** `PRIMARY_ATTACKER_UNRESOLVED`, `UNRESOLVED_ATTACKER_PROMPTS`.
- **Resources:** `RESOURCE_LIMITS_NOT_ENFORCED`.
- **B0:** `B0_BASELINE_IDENTITY_NOT_MATCHED`.
- **Higher-level statistics:** `HIGHER_LEVEL_STATS_NOT_IMPLEMENTED`,
  `UNRESOLVED_HIERARCHICAL_CLUSTER_COUNT`, `UNRESOLVED_ACCEPTANCE_CRITERIA`.
- **Contract:** `EXECUTION_LOCK_INCOMPLETE`.

Verification is the one integration that is no longer a blocker:
`research_strict_v1` is `AVAILABLE`, the actual source hashes match
(`strict_research.py 5cff1d…`, `verification_deadline.py 67dd7a…`), and the
wall-clock deadline is 1.0 s enforced by the core resolver. That does **not**
make the model ready.

---

## 5. Statistics and cost bounds

- **Censoring fixed.** Known-answer test: detection@1 + `ADMIN_CENSORED`@1 +
  detection@2 ⇒ CIF(2)=1.0; replacing the censor with `TECHNICAL_FAILURE`@1
  removes it from the risk set ⇒ CIF(2)=2/3. A censor is never an event.
- **Clustering.** Block clusters are `scenario × profile × seed` matched arms
  only. They do not model dependence across families/profiles; with 2
  development scenarios the bootstrap is diagnostic/exploratory.
- **Higher-level model absent.** Cause-specific Cox with block stratum,
  mixed-effects, and family-level hierarchical analysis are **not implemented**;
  only Aalen–Johansen CIF plus block bootstrap/permutation contrasts exist.
  An adequately powered family/cluster plan is required.
- **Availability matters.** Higher technical failure/abandonment can lower
  detection CIF without better deception. Detection is always reported jointly
  with competing causes and compliant-exposure rates. ITT is primary and
  unexposed/failed sessions are preserved, never zero-effect.
- **Retry bound (must be frozen/enforced before a pilot).** Native Hisoka has 1
  semantic retry (2 `generate` calls); the harness default has 2 retries (3
  candidate attempts) ⇒ up to **6 generate calls per turn**, before
  `transport_retries+1`. The 32-session design has 24 LLM sessions × 12 turns =
  288 LLM turns ⇒ up to **1728 × (r+1) generate calls**, plus 384 attacker
  turns and 64 evaluation calls, before controls. Usage fields that report
  `LAST_PROVIDER_REQUEST_ONLY` do not bound turn totals.

---

## 6. Supporting evidence (not arm results)

| Artifact | Establishes | Does not establish |
|---|---|---|
| `docs/research/p0_strict_joint_trace_20261023T034843Z/` | 24 scoped checks: real SSH, strict candidate verification, wall-clock deadline, HTTP 503 / no commit on unsupported `cat /etc/sudoers` | Full attacker-visible consistency (outer `root@svr04:/#` contradicts inner `webapp@web-srv-01`), model inference, arm effect |
| `docs/research/p0_strict_joint_trace_20261023T034216Z/` | Preserved FAIL (event metadata omitted) | A passing trace; do not reuse as evidence |
| `docs/research/local_dense_probe_20261023T031557Z*/` | Actual MiniLM+FAISS CPU inference on 12 synthetic development docs, 4 fixed queries | B3 arm, retrieval quality, deception, final cohort |
| `docs/research/generation_contract_v1/` | Opt-in decoding contract; legacy defaults preserved when off | A served model or controlled arm |
| This pass's preflight/dry-run/test logs | Infrastructure mechanics | Scientific validity |

No external model packet was executed; 4 synthetic requests were prepared by a
peer but require approval. The expected $0 is **not** billing-attested.

---

## 7. Result statement

Detection CIF, risk differences, kappa, latency, token use, cost, and all H1–H5
effects are **NOT_MEASURED / NOT_ESTABLISHED**. A missing or unexposed arm is
never negative evidence; a non-significant estimate is never zero.

A real result may only be written from a frozen `analysis.json` produced by
`scripts/analyze_ablation_v1.py` from frozen Track B records, with the plan and
record hashes recorded. Track A and TEST_ONLY smoke records are never pooled
with Track B.
