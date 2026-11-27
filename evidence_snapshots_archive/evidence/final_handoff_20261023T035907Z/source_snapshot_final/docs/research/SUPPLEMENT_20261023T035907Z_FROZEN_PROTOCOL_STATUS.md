# SUPPLEMENT — frozen protocol status after 2026-10-23 recovery

**Version:** `20261023T035907Z`
**Purpose:** versioned supplement to the three frozen reports. It does **not**
edit or replace them; it records which of their statements are now superseded and
what remains true.

- `docs/research/RUNTIME_TRUTH_AUDIT.md`
- `docs/research/CAUSAL_ABLATION_PROTOCOL.md`
- `docs/research/EXPERIMENT_READINESS_REPORT.md`

**Package status:** `INCOMPLETE_BY_DESIGN`. **Pilot status:** `NOT_READY`.
**H1–H5:** none established. **Human ratings:** `NOT_COLLECTED`.

---

## 1. Design allocation vs execution

The protocol allocates **32 development sessions**:
`2 scenarios × 2 scripted profiles × 2 seeds × 4 arms`, turn cap 12. This is a
**DESIGN allocation, not executed data**.

| Split | Families | Executed sessions |
|---|---|---|
| Development | 2 scenarios (`dev-lab-recon-01`, `dev-lab-credential-01`) | **0 / 32** ablation sessions |
| Calibration | none yet | 0; pending |
| Holdout | none yet, sealed flag true | 0; pending |

The only runs that occurred are **two authorized `TEST_ONLY` B0 native transport
smokes** (2 turns each, `ADMIN_CENSORED`, no detection). They are not ablation
sessions, not model inference, and not matched to B1–B3. No further B0 smoke is
authorized.

---

## 2. Corrections to superseded statements

| Earlier statement (frozen docs) | Current fact (this pass) |
|---|---|
| Verification integration `PENDING`, source hash unresolved | `research_strict_v1` is `AVAILABLE`; actual `strict_research.py` `5cff1d…` and `verification_deadline.py` `67dd7a…` match the contract |
| Deadline `SIMULATED_EXCEPTION_ONLY`, seconds `null` | Wall-clock deadline 1.0 s implemented and enforced by the core resolver (`0 < x <= 60`); fail-closed single-busy daemon, **not** hard cancellation |
| Preflight `DESIGN_INVALID`, 25 blockers | Preflight **exit 2**: `DESIGN_VALID` + `NOT_READY` with 24 explicit blockers (design is coherent; execution is not) |
| “No smoke output exists” | Two B0 `TEST_ONLY` smokes exist, preserved byte-for-byte; #1 summary has the post-cleanup listener defect, #2 is the final live-listener record |
| 5 test modules / 25 tests | 6 focused ablation modules / **32 passed** in this pass (mechanical conformance only) |
| Runtime decoding is hardcoded only | Opt-in generation contract now supports temperature/top_p/max_tokens/seed/max_retries and records digests; legacy 0.7/4096 remains when off. The CLI bridge still does not attest the hard bound, so no controlled arm is ready |
| No B0 listener evidence | #2 observed live `LISTEN 127.0.0.1:60889`, cleanup true; #1 listener fields are defective and are not evidence |

Everything else that the frozen audit/protocol/readiness reports say about
unresolved model, prompt, corpus, attacker, resources, B0 identity mismatch, and
the closed H1–H5 gates remains true unless corrected above.

---

## 3. Current blocker freeze (24)

`DESIGN_VALID` does not mean ready. The explicit blockers are:

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
- **Higher-level stats:** `HIGHER_LEVEL_STATS_NOT_IMPLEMENTED`,
  `UNRESOLVED_HIERARCHICAL_CLUSTER_COUNT`, `UNRESOLVED_ACCEPTANCE_CRITERIA`.
- **Contract:** `EXECUTION_LOCK_INCOMPLETE`.

No unresolved field was dropped to make the design pass. If a future design is
genuinely invalid, the preflight must return `DESIGN_INVALID` (exit 3) rather
than masking it.

---

## 4. Retry and cost bounds (corrected)

The prior simplified cost did **not** bound current runtime. Freeze all layers
before a pilot:

- native Hisoka: 1 semantic retry = up to 2 `generate` calls per turn;
- harness default: 2 retries = up to 3 candidate attempts;
- combined: up to **6 generate calls per turn**, before `transport_retries+1`;
- 32-session design: 24 LLM sessions × 12 turns = 288 turns ⇒ up to
  **1728 × (r+1) generate calls**, plus 384 attacker turns and 64 evaluation
  calls, before controls.

Usage fields that report `LAST_PROVIDER_REQUEST_ONLY` are per-provider-request,
not turn totals, and must not be used as a campaign cost bound.

---

## 5. External calls and spend

- No provider, AWS, JEV, download, install, training, public listener, or public
  exposure occurred.
- A peer prepared 4 synthetic external packet requests. They were **NOT
  EXECUTED** and require explicit approval. The expected $0 is **not**
  billing-attested.
- The local Ollama daemon exposes only `:cloud` aliases (remote inference) and
  was not called. No local generative weights exist.
- The P0 strict joint trace is real SSH + native Cowrie + strict candidate
  verification + HTTP 503 / no commit on the unsupported negative command. It is
  not model inference and not a matched pilot.

---

## 6. Decision and human-evaluation labels

- **P2 decision audit (B4/B5):** `NOT_STARTED / CONDITIONAL` on valid B0–B3.
  H4a/H4b are not measured; B4/B5 are `NOT_READY`.
- **Human ratings:** `NOT_COLLECTED`. No prefilled or synthetic human ratings
  exist. `source=HUMAN` is self-report, not identity proof; uniqueness, canary
  hashes, valid detections and ratings are required before any human claim.
  The packet/rubric label-set mismatch must be reconciled first.

---

## 7. Open readiness blockers (not relaxed)

- Matched B0/B1–B3 pilot: **NOT READY**.
- Attacker-visible identity consistency: **CONTRADICTION OPEN** — outer Cowrie
  `root@svr04:/#` wraps inner `webapp@web-srv-01`; the strict verifier checks the
  candidate only. Full SSH raw stimulus is retained for human/quality metrics;
  contradictions are not stripped.
- B1–B3 model execution: **NOT ESTABLISHED**; runner not implemented.
- Higher-level statistics: **NOT IMPLEMENTED**; 2 development scenarios are
  exploratory, not confirmatory.
- Hard network egress isolation: **NOT ESTABLISHED** (application-level loopback
  disablement only).

**Claim boundary:** this supplement establishes status and provenance only. It
does not establish any arm effect, deception effectiveness, decision-layer
validity, human effectiveness, or scientific readiness.
