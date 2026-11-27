# ABLATION RESULTS — RAGIN causal ablation

**Status: NOT_MEASURED.** No B1–B3 arm executed. No detection CIF, risk
difference, hazard ratio, agreement statistic, latency, token count, or cost is
reported. All H1–H5 remain **NOT_ESTABLISHED**.

**Date:** 2026-10-23 (UTC) · **Protocol:** `CAUSAL_ABLATION_PROTOCOL.md` (frozen
design; this is a living result log) · **Contract:**
`configs/ablation/eval_v1/run_contract_v1.json` · **Evidence:**
`evidence/final_handoff_20261023T035907Z/` · **Spend:** $0, 0 provider calls,
0 downloads, 0 public listeners.

## 1. What actually ran

| Run | Scope | Result |
|---|---|---|
| B0 smoke #1 | `TEST_ONLY` transport | 2 turns, `ADMIN_CENSORED`, no detection, exit 0. Preserved with post-cleanup listener defect (`ssh_loopback_only=false`, `listeners=[]`) — not listener evidence |
| B0 smoke #2 | `TEST_ONLY` transport | 2 turns, `ADMIN_CENSORED`, no detection, live `127.0.0.1:60889`, cleanup true, exit 0 |
| Track A dry run | frozen trace | exit 0; 2 scenarios × 4 commands |
| Track B B0 dry run | environment check | exit 0; cached image, no container, no listener |

Both raw smoke directories were copied byte-for-byte and verified
(`b0_smoke_copy_verification.json`, `all_identical=true`, 7 + 9 files). Temporary
originals were not rewritten. The raw manifest includes both `summary.json`
files and excludes only itself. These are **transport/control mechanics**, not an
ablation and not model inference.

## 2. Allocation (design, not execution)

Frozen development allocation: `2 scenarios × 2 scripted profiles × 2 seeds ×
4 arms = 32`, turn cap 12. **Executed ablation sessions: 0 / 32.** Only 2
development scenarios exist; calibration and holdout are empty/pending. Bootstrap
contrasts are therefore diagnostic and **exploratory**, not confirmatory.

## 3. Arm and hypothesis status

| Arm | Treatment | Status | Reason |
|---|---|---|---|
| **B0** | Native Cowrie | `EXECUTABLE_LOCAL_TRANSPORT_ONLY` | Not a RAGIN arm; no generator/verifier/retrieval effect |
| **B1** | Cowrie + frozen LLM, no retrieval | `NOT_READY` | Model/prompt/price/invocation unresolved; runner missing |
| **B2** | B1 + BM25 | `NOT_READY` | Generator blockers; B2 corpus unresolved |
| **B3** | B1 + dense | `NOT_READY` | Exact store, embedding model, generator unresolved |
| **B4** | B3 + rule decision | `NOT_READY` | Rule table/decision contract not frozen |
| **B5** | B3 + fine-tuned Laya | `NOT_READY` | v12 checkpoint/contract mismatch |

| Hypothesis | Contrast | Status |
|---|---|---|
| **H1** | B1 vs B0 | **NOT_ESTABLISHED** — no B1 session; B0 lacks the shared verifier and is identity-unmatched. H1 is a **system-package effect**, never a pure LLM effect |
| **H2a/H2b** | B2 vs B1, B3 vs B1 | **NOT_MEASURED** |
| **H3** | B3 vs B2 | **NOT_MEASURED** — no shared corpus/doc-ID/`top_k`/budget |
| **H4a/H4b** | B4 vs B3, B5 vs B3 | **NOT_STARTED** |
| **H5** | Utility summary | **NOT_ESTABLISHED** — no prespecified acceptance rule |

The Track B runner refuses every non-B0 arm (“B1-B3 execution is not implemented
in this development runner”). A design-valid contract would not start B1–B3.

## 4. Preflight (actual)

`scripts/ablation_preflight_v1.py --env-check` returned **exit 2**:
`design.status=DESIGN_VALID` (no errors) and `execution_status=NOT_READY` with
**24 explicit blockers** — model/generation (8), data/persona (1), corpus (7),
attacker (2), resources (1), B0 identity (1), higher-level statistics (3),
execution lock (1). None was removed to force a pass; see
`SUPPLEMENT_20261023T035907Z_FROZEN_PROTOCOL_STATUS.md` §3 for the exact codes.

Verification is the one integration no longer blocked: `research_strict_v1` is
`AVAILABLE`, actual source hashes match (`strict_research.py 5cff1d…`,
`verification_deadline.py 67dd7a…`), and the 1.0 s wall-clock deadline is
enforced by the core resolver. That does **not** make the model ready.

## 5. Statistics and cost bounds

- **Censoring fixed.** Known answer: detection@1 + `ADMIN_CENSORED`@1 +
  detection@2 ⇒ CIF(2)=1.0; replacing the censor with `TECHNICAL_FAILURE`@1
  removes it from the risk set ⇒ 2/3. A censor is never an event.
- **Clustering.** Blocks are `scenario × profile × seed` matched arms only; they
  do not model dependence across families. With 2 development scenarios the
  bootstrap is diagnostic.
- **Higher-level model absent.** Cause-specific Cox with block stratum,
  mixed-effects, and family-level hierarchical analysis are not implemented;
  only Aalen–Johansen CIF plus block bootstrap/permutation contrasts exist.
- **Availability matters.** More technical failure/abandonment can lower
  detection CIF without better deception. Report competing causes and compliant
  exposure jointly; ITT is primary; unexposed/failed sessions are never zero.
- **Retry bound.** Native 1 semantic retry (2 calls) × harness 2 retries (3
  attempts) ⇒ up to 6 generate calls/turn before `transport_retries+1`. 24 LLM
  sessions × 12 turns = 288 turns ⇒ up to 1728 × (r+1) generate calls, plus 384
  attacker turns and 64 evaluation calls, before controls.
  `LAST_PROVIDER_REQUEST_ONLY` usage fields do not bound turn totals.

## 6. Supporting evidence (not arm results)

- `p0_strict_joint_trace_20261023T034843Z/`: 24 scoped checks — real SSH, strict
  candidate verification, 1.0 s deadline, HTTP 503/no commit on unsupported
  `cat /etc/sudoers`. Does not prove full attacker-visible consistency: outer
  `root@svr04:/#` contradicts inner `webapp@web-srv-01`.
- `p0_strict_joint_trace_20261023T034216Z/`: preserved FAIL (missing event
  metadata); never reuse as a passing trace.
- `local_dense_probe_20261023T031557Z*/`: real MiniLM+FAISS CPU inference on 12
  synthetic development docs, 4 fixed queries; no quality/deception claim, not
  the final cohort.
- `generation_contract_v1/`: opt-in decoding contract; legacy defaults when off.
  No local generative weights; the CLI bridge does not attest the hard bound.
- Preflight/dry-run/test logs in this evidence root: mechanics only.
- No external model packet was executed; 4 synthetic requests were prepared by a
  peer and need approval. Expected $0 is **not** billing-attested.

## 7. Result statement

Detection CIF, risk differences, kappa, latency, token use, cost, and all H1–H5
effects are **NOT_MEASURED / NOT_ESTABLISHED**. A missing/unexposed arm is never
negative evidence; non-significance is never zero. A real result may only be
written from a frozen `analysis.json` produced by `scripts/analyze_ablation_v1.py`
from frozen Track B records with plan and record hashes recorded. Track A and
TEST_ONLY smoke records are never pooled with Track B.
