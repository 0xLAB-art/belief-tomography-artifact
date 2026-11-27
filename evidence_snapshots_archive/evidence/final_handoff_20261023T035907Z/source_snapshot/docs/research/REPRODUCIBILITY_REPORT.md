# REPRODUCIBILITY REPORT — RAGIN evaluation infrastructure v1

**Status: PARTIALLY REPRODUCIBLE.** The *infrastructure* is reproducible today.
The *experiment* is not: no B1–B3 arm can execute, so no experimental effect
exists to reproduce.

**Date:** 2026-10-23 (UTC)
**Scope:** `ragin/evaluation/`, `configs/ablation/eval_v1/`,
`scripts/ablation_*_v1.py`, `scripts/run_ablation_track_{a,b}_v1.py`,
`scripts/analyze_ablation_v1.py`, focused ablation tests.
**Working tree:** git `7d8a32a`, dirty; the evaluation/ablation files are
untracked (`?? ragin/evaluation/`, `?? configs/ablation/eval_v1/`,
`?? scripts/…ablation…`, `?? docs/research/…`). No commit was made in this pass.
**Evidence root:** `evidence/final_handoff_20261023T035907Z/`.

---

## 1. Reproducible now (verified this pass)

| Capability | Command | Observed |
|---|---|---|
| Run-contract preflight | `scripts/ablation_preflight_v1.py --env-check` | **exit 2**, `DESIGN_VALID`, `NOT_READY`, 24 explicit blockers |
| Track A dry run | `scripts/run_ablation_track_a_v1.py` | **exit 0**; 2 scenarios, 4 commands each |
| Track B B0 dry run | `scripts/run_ablation_track_b_v1.py --dry-run` | **exit 0**; cached image, no container started, no listener |
| Focused ablation tests | 6 files, pytest `-q` | **32 passed** (exit 0), isolated session dir |
| Scoped lint | `ruff check` on owned package/scripts/tests | **All checks passed** (exit 0) |
| B0 raw smoke copies | byte copy + SHA comparison | **all_identical=true** (7 + 9 files) |
| Raw smoke manifest | includes both `summary.json`, excludes self only | `RAW_OUTPUTS_SHA256_FINAL.json`, 16 entries |

Test command shape (unique env before imports, offline flags, no inherited
provider credentials/proxies):

```bash
RAGIN_SESSION_DIR=<unique-tmp> \
RAGIN_HOST_FICTION_PATH=<unique-tmp>/host_fiction.json \
RAGIN_PROVIDER_ENABLED=0 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
.venv/bin/python -m pytest \
  tests/unit/test_ablation_contract_v1.py \
  tests/unit/test_ablation_records_v1.py \
  tests/unit/test_ablation_analysis_v1.py \
  tests/unit/test_ablation_closed_loop_v1.py \
  tests/unit/test_ablation_human_packet_v1.py \
  tests/unit/test_ablation_release_manifest_v1.py -q
```

These tests establish **mechanical conformance**, not scientific validity. They
use fake transports/loopback fixtures and synthetic records. No scientific
readiness follows from a green test suite.

The test-contamination incident of 2026-10-23T03:23:25Z (five tracked
`data/sessions/sup-*.jsonl` files appended by a broad test run) is preserved in
`docs/research/test_contamination_20261023T033008Z/`. **Always redirect
`RAGIN_SESSION_DIR` before running tests.**

---

## 2. Still blocked (nothing to reproduce yet)

| # | Blocked item | Current value |
|---|---|---|
| 1 | Generator identity/revision/hash | `UNRESOLVED_FROZEN_GENERATOR`; no local generative weights |
| 2 | Generator price | `UNRESOLVED`; no provider cost measured |
| 3 | Prompt | `UNRESOLVED_FROZEN_PROMPT_V1`; hash unresolved |
| 4 | Persona | `data/host_fiction.json` exists; contract hash unresolved |
| 5 | Data/split seal | development only; calibration/holdout empty |
| 6 | B3 exact store | `UNRESOLVED_EXACT_STORE` |
| 7 | B3 embedding model | `UNRESOLVED_LOCAL_MODEL_DIR` |
| 8 | Primary LLM attacker | `primary_kind = UNRESOLVED`; prompts/tools unresolved |
| 9 | Verification integration | **RESOLVED as integration**: `research_strict_v1` AVAILABLE, source `5cff1d…`, deadline source `67dd7a…` |
| 10 | Verifier deadline | **IMPLEMENTED**: 1.0 s wall clock, `0 < x <= 60`, fail-closed single-busy daemon (not hard cancellation) |
| 11 | Resource limits | `PROPOSED_NOT_ENFORCED`; JSON fields are not cgroup/container limits |
| 12 | Execution lock | `INCOMPLETE` |
| 13 | B0 identity/OS matching | `NOT_ESTABLISHED`; observed outer Cowrie `root@svr04` ≠ inner `webapp@web-srv-01` |
| 14 | B2/B3 canonical corpus equality | content/doc-ID/`top_k`/budget all unresolved |
| 15 | Generation decoding compliance | contract exists but CLI bridge does not attest temperature/top_p/seed/token bound; `BLOCKED_GENERATION_CONFIG` |
| 16 | B1–B3 execution path | Track B runner refuses B1–B3 (“not implemented”) |
| 17 | Higher-level statistics | Cox/block stratum, mixed-effects, family-level model not implemented; 2 dev scenarios exploratory |
| 18 | Acceptance criteria | `analysis.acceptance_criteria = null` |

**B2/B3 equality is a content question, not an index-byte question.**
`ablation_contract.py` hashes sorted document IDs plus normalized content and
rejects equal BM25/FAISS index bytes as proof of equality. Shared `top_k` and
context budget are also required.

---

## 3. Generation reproducibility

| Field | Frozen proposal | Runtime reality |
|---|---|---|
| `temperature` | `0.0` | legacy default `0.7` when the opt-in contract is off |
| `max_tokens` | `512` | legacy default `4096` when off |
| `seed` | `0` | supported by the opt-in contract; legacy path has no bound |
| `top_p` | `1.0` | supported by the opt-in contract; legacy path has no bound |
| `fallback` | `none` | template/static fallback still reachable |
| Retries | bounded | native semantic retry + harness retries; end-to-end turn bound not frozen |

The native generation contract (`ragin/gateway/generation.py`) is implemented and
tested: opt-in `RAGIN_GENERATION_CONTRACT=1` carries model, temperature, top_p,
max_tokens, optional explicit seed, and `max_retries` into the HTTP payload and
records config digests. Opt-out preserves legacy defaults. But **no actual
generative model weights exist locally**, the CLI bridge only echoes the alias
and does not attest the hard bound, and the run contract’s invocation kind is
`UNRESOLVED`. Therefore this is **not a controlled arm**.

No offline inference may be claimed from a loopback URL: the local Ollama daemon
lists only `:cloud` aliases, which are remote inference and were not called.
Loopback proves transport locality, not local-weight inference.

**Retry/cost bound.** Native 1 semantic retry (2 calls) × harness default 2
retries (3 attempts) ⇒ up to 6 generate calls/turn before `transport_retries+1`.
32 sessions, 24 LLM sessions × 12 turns = 288 turns ⇒ up to 1728 × (r+1)
generate calls, plus 384 attacker turns and 64 evaluation calls, before controls.
Every retry layer must be frozen, enforced, and observed before a pilot. Usage
fields marked `LAST_PROVIDER_REQUEST_ONLY` do not bound turn totals.

---

## 4. Environment facts (one host)

| Item | Value |
|---|---|
| Interpreter | `.venv/bin/python` 3.12.3, CPU torch 2.14.0, faiss 1.15.0, ST 6.0.1 |
| `.venv-gpu` | no `faiss`, no `sentence-transformers`; cannot run the dense arm |
| Cowrie image | `sha256:710f1e4601a663ac8591f58a42b44e4cd3b7ea170c7e6cdb9e54c430a30cd459`, `pull: never` |
| B0 network | loopback only (`127.0.0.1`), `public=false` |
| Spend | $0, 0 provider calls, 0 downloads, 0 public exposure |

Shared-core hashes were **observed at manifest time**, not frozen:
`harness.py cd6122…`, `strict_research.py 5cff1d…`, `verification_deadline.py
67dd7a…`, `generation.py 9e7601…`, `client.py 1a13ab…`, `hisoka/deception.py
8f8c9b…`. `deception.py` drifted after the P0 trace (`d30164…` at launch); do not
claim the current worktree equals the trace launch tree.

---

## 5. Release manifest (new namespace)

A new infrastructure package is built under
`docs/research/evaluation_infra_v1/releases/<release-id>/` (immutable, mode
`0444`). It preserves: configs, focused tests, owned source bytes (in-repo plus a
read-only snapshot where feasible), living docs, both raw B0 smoke directories,
and the observed shared-core hashes. `model`, `prompts`, and `costs` are absent
by fact, so the package is **INCOMPLETE by design** — not a readiness claim. The
builder refuses an existing release namespace and recomputes every hash before
writing. The release manifest is separate from the raw-smoke manifest, so there
is no circular self-hash.

---

## 6. What “reproducible” means here

| Sense | Status |
|---|---|
| Re-run the focused tests and get the same verdict | **YES** (offline, deterministic fakes) |
| Re-run the analysis on the same records and get the same numbers | **YES** (seeded bootstrap/permutation, `seed=20261023`) |
| Rebuild the release package and match hashes | **YES**, once the package exists |
| Re-run the raw B0 smoke without changing the runner | **YES**, but no more B0 smokes are authorized |
| Independent replication of an arm effect | **NO** — no B1–B3 arm has run |

A seed makes a computation repeatable; it does not make an unexecuted experiment
reproducible. **NOT_READY applies to the experiment, not to the harness.**
