# REPRODUCIBILITY REPORT — RAGIN evaluation infrastructure v1

**Status: PARTIALLY REPRODUCIBLE.** The infrastructure is reproducible today;
the experiment is not, because no B1–B3 arm can execute and no effect exists.

**Date:** 2026-10-23 (UTC) · **Scope:** `ragin/evaluation/`,
`configs/ablation/eval_v1/`, `scripts/*ablation*_v1.py`, focused ablation tests ·
**Tree:** git `7d8a32a`, dirty (3066 status lines); owned files untracked; no
commit made · **Evidence:** `evidence/final_handoff_20261023T035907Z/`.

---

## 1. Reproducible now (verified this pass)

| Capability | Command | Observed |
|---|---|---|
| Preflight | `ablation_preflight_v1.py --env-check` | **exit 2**, `DESIGN_VALID`, `NOT_READY`, 24 blockers |
| Track A dry run | `run_ablation_track_a_v1.py` | **exit 0**; 2 scenarios × 4 commands |
| Track B B0 dry run | `run_ablation_track_b_v1.py --dry-run` | **exit 0**; cached image, no container/listener |
| Focused tests | 6 files, pytest `-q` | **32 passed** (exit 0) |
| Scoped lint | `ruff check` owned package/scripts/tests | **All checks passed** (exit 0) |
| B0 raw copies | byte copy + SHA comparison | **all_identical=true** (7 + 9 files) |
| Raw manifest | both `summary.json`, excludes self only | 16 entries |

Tests ran with a unique `RAGIN_SESSION_DIR` / `RAGIN_HOST_FICTION_PATH` set
**before imports**, `RAGIN_PROVIDER_ENABLED=0`, `HF_HUB_OFFLINE=1`,
`TRANSFORMERS_OFFLINE=1`, and provider/proxy variables removed. They establish
**mechanical conformance**, not scientific validity. Green tests do not imply
scientific readiness.

The 2026-10-23T03:23:25Z contamination incident (five tracked
`data/sessions/sup-*.jsonl` appended by a broad test run) is preserved in
`docs/research/test_contamination_20261023T033008Z/`. Always redirect
`RAGIN_SESSION_DIR` before running tests.

---

## 2. Still blocked (nothing to reproduce yet)

- **Generation:** model identity/revision/hash `UNRESOLVED`; price `UNRESOLVED`;
  prompt `UNRESOLVED_FROZEN_PROMPT_V1`; persona file exists but hash unresolved.
- **Data/splits:** development only; calibration and holdout empty.
- **B3:** exact store `UNRESOLVED_EXACT_STORE`; embedding model
  `UNRESOLVED_LOCAL_MODEL_DIR`.
- **Attacker:** `primary_kind=UNRESOLVED`; prompts/tools unresolved.
- **Verification:** integration **resolved** (`research_strict_v1` AVAILABLE,
  `5cff1d…`); wall-clock deadline **implemented** at 1.0 s (`0 < x <= 60`,
  fail-closed single-busy daemon, not hard cancellation).
- **Resources:** `PROPOSED_NOT_ENFORCED`; JSON is not cgroup/container enforcement.
- **Lock:** `EXECUTION_LOCK=INCOMPLETE`.
- **B0 identity:** `NOT_ESTABLISHED`; outer Cowrie `root@svr04` ≠ inner
  `webapp@web-srv-01`.
- **B2/B3:** corpus content/doc-ID/`top_k`/budget unresolved. This is a content
  question, not an index-byte question: the contract hashes sorted document IDs
  plus normalized content and rejects equal BM25/FAISS index bytes as proof.
- **Decoding compliance:** contract exists; CLI bridge does not attest
  temp/top_p/seed/token bound.
- **Execution path:** runner refuses B1–B3 (“not implemented”).
- **Statistics:** Cox/block stratum/mixed/family model not implemented;
  `acceptance_criteria = null`.

## 3. Generation reproducibility

- `temperature`: frozen `0.0`; legacy `0.7` when the opt-in contract is off.
- `max_tokens`: frozen `512`; legacy `4096` when off.
- `seed` / `top_p`: supported by the opt-in contract; legacy path unbounded.
- `fallback`: required `none`; template/static fallback still reachable.
- Retries: native semantic + harness retries; end-to-end turn bound not frozen.

`ragin/gateway/generation.py` is implemented/tested: opt-in
`RAGIN_GENERATION_CONTRACT=1` carries model, temperature, top_p, max_tokens,
optional explicit seed, and `max_retries` into the HTTP payload and records
digests; opt-out preserves legacy defaults. But **no generative weights exist
locally**, the CLI bridge only echoes the alias and does not attest the hard
bound, and invocation is `UNRESOLVED`. This is **not a controlled arm**.

Loopback is not local-weight evidence: the local Ollama daemon lists only
`:cloud` aliases (remote inference) and was not called.

**Retry/cost bound.** Native 1 semantic retry (2 calls) × harness 2 retries
(3 attempts) ⇒ up to 6 generate calls/turn before `transport_retries+1`. 24 LLM
sessions × 12 turns = 288 turns ⇒ up to **1728 × (r+1)** generate calls, plus 384
attacker turns and 64 evaluation calls, before controls. Every retry layer must
be frozen, enforced, and observed before a pilot. `LAST_PROVIDER_REQUEST_ONLY`
usage fields do not bound turn totals.

---

## 4. Environment and shared-core hashes

`.venv/bin/python` 3.12.3, CPU torch 2.14.0, faiss 1.15.0, ST 6.0.1;
`.venv-gpu` lacks `faiss`/`sentence-transformers`. Cowrie image
`sha256:710f1e…` (`pull: never`), loopback only. Spend $0, 0 provider calls,
0 downloads, 0 public exposure.

Shared-core hashes were **observed at manifest time**, not frozen:
`harness.py cd6122…`, `strict_research.py 5cff1d…`,
`verification_deadline.py 67dd7a…`, `generation.py 9e7601…`, `client.py
1a13ab…`, `hisoka/deception.py 8f8c9b…`. `deception.py` drifted after the P0
trace (`d30164…` at launch); do not claim the worktree equals the launch tree.

---

## 5. Release manifest (new namespace)

`docs/research/evaluation_infra_v1/releases/` is not used for this pass; the new
package is under `evidence/final_handoff_20261023T035907Z/releases/
evaluation_infra_v1_20261023T035907Z/` (immutable, mode `0444`). It preserves
configs, focused tests, owned source (in-repo plus a read-only snapshot of 31
files), five living docs, both raw B0 smoke directories, and observed shared-core
hashes. `model`, `prompts`, and `costs` are absent by fact ⇒ status
**INCOMPLETE by design**, not a readiness claim. Verification checked all 81
present artifacts; the only failures are the three absent categories. The release
manifest excludes itself, so there is no circular self-hash.

---

## 6. What “reproducible” means here

| Sense | Status |
|---|---|
| Re-run focused tests → same verdict | **YES** (offline, deterministic fakes) |
| Re-run analysis on same records → same numbers | **YES** (seeded, `20261023`) |
| Rebuild release package → matching hashes | **YES**, once the package exists |
| Re-run the raw B0 smoke without changing the runner | **YES**, but no more B0 smokes are authorized |
| Independent replication of an arm effect | **NO** — no arm has run |

A seed makes a computation repeatable; it does not make an unexecuted experiment
reproducible. **NOT_READY applies to the experiment, not the harness.**
