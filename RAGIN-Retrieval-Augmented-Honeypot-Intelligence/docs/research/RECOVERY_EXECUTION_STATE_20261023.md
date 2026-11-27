# RAGIN Recovery Execution State — 2026-10-23

**Status: IN PROGRESS — trace PASS, but B0/B1–B3 matched pilot is NOT READY and B1–B3 model execution is NOT ESTABLISHED.**

The final strict loopback SSH trace passed its scoped checks on 2026-10-23, but an unresolved
attacker-visible cross-layer identity contradiction blocks readiness: the outer Cowrie frontend
shows `root@svr04:/#` while the RAGIN candidate claims `webapp@web-srv-01` / `uid=1001(webapp)`.
The strict verifier checks the RAGIN candidate only, not the outer Cowrie prompt. Candidate/served
hash agreement therefore does **not** establish full transcript identity consistency.

This document records the bounded verification/deadline work completed on 2026-10-23, the
preservation correction for unintended test appends, and the final trace evidence. The prior
readiness/freeze artifacts remain authoritative and unchanged.

## 1. Scope completed in this pass

### 1.1 Shared strict research verification profile

`ragin/cycle/strict_research.py` implements the opt-in `research_strict_v1` profile. It is
independent of the decision arm and is applied identically to every arm. The profile accepts only
the finite, predeclared v1 command/claim contract:

- `whoami`
- `id`, `id -u`, `id -un`, `id -g`, `id -gn`
- `hostname`, `hostname -f`, `hostname -s`
- `uname`, `uname -a`, `uname -r`, `uname -s`
- `cat /etc/os-release`, `cat /usr/lib/os-release`

`date` and `uptime` are intentionally excluded because their shapes are not pinned evidence.
The profile requires an authoritative pinned identity injected by the harness; there is no
`identity_for(skill)` fallback. Unsupported, malformed, compound, encoded, wrapper, extra, and
unknown commands fail closed. Prompt handling accepts only the exact pinned prompt echo for the
current command or the exact empty ready prompt. Strict issue strings are stable reason codes;
diagnostics carry counts/SHA-256, not raw commands or candidate lines.

The legacy default remains `legacy`; legacy behavior and its tests are preserved. Explicit
`Harness(..., verifier_profile=..., verifier_deadline_s=...)` overrides the environment.
Environment hooks are `RAGIN_VERIFIER_PROFILE=legacy|research_strict_v1` and
`RAGIN_VERIFIER_DEADLINE_S` (`0 < x <= 60`, research default `1.0`).

### 1.2 Wall-clock verifier deadline and full verdict schema

`ragin/cycle/verification_deadline.py` adds `DeadlineVerifier`:

- one lazily started **daemon** worker and one busy slot;
- repeated timeouts cannot spawn additional workers;
- the absolute deadline is fixed before the input snapshot;
- a worker records its monotonic finish time and the caller compares that recorded finish with the
  absolute deadline, so an `Event.wait` boundary race cannot admit a late `True`;
- late results are discarded and counted, never served or committed;
- new calls while the single slot is busy fail closed;
- `shutdown(wait=True)` joins at most 0.1 s;
- normalization and verifier exceptions are caught inside the worker's `try/finally`, so the busy
  slot is released and the event is set.

The deadline is **not** hard cancellation. A permanently stuck verifier keeps the single daemon slot
busy; callers then fail closed with `verifier_busy`. No preemption is claimed.

`_normalize_verdict` now validates the full documented verdict schema, not only the `passed`
literal. It rejects a non-bool `passed`, a missing/non-list `issues`, non-string issue members, and
a contradictory `passed: true` with non-empty `issues`. Malformed shapes fail closed with
`verifier_malformed_result`; the contradictory shape fails with `verifier_contradictory_result`.
Malformed issue values are not re-typed or propagated. This is covered by narrow regression tests.

Invalid policy values raise field-only `ValueError`s. Raw environment values are not interpolated
into the exception text, and conversion failures use `from None` so a secret-looking value cannot
appear through a chained cause.

### 1.3 Trace runner (executed; scoped PASS, identity blocker open)

`scripts/run_p0_loopback_ssh_trace_v2.py` is a new, additive runner. The frozen v1 runner is not
modified. v2 retains the three canonical positive turns (`whoami`, `id`, `uname -a`) and adds one
separate SSH session with a predeclared negative command (default `cat /etc/sudoers`, overridable
with `--negative-command`).

v2 records, rather than assumes:

- the positive turns' candidate/verified/served SHA-256 agreement and terminal bytes;
- the negative session's actual terminal bytes and frames;
- whether the server actually returned HTTP 503 for the negative request;
- whether the negative verification failed closed and whether any `SYSTEM_RESPONSE`/accepted
  state was produced;
- whether any fabricated `root ALL`/`Defaults env_reset` claim was observed.

A missing observed 503 or a served negative response makes the runner fail. The runner writes a v2
prelaunch manifest, summary, and artifact manifest under a fresh `--out` directory. Its internal
environment sets `RAGIN_SESSION_DIR`, `RAGIN_FIELD_EXPORT_DIR`, and
`RAGIN_HOST_FICTION_PATH` under that directory, so a run cannot append to `data/sessions`.

The runner was executed for the final strict trace at
`docs/research/p0_strict_joint_trace_20261023T034843Z` (raw exit 0, scoped status PASS), with the
first failed run preserved at `docs/research/p0_strict_joint_trace_20261023T034216Z`. The scoped
PASS does **not** clear the outer Cowrie identity contradiction described in the handoff supplement
`docs/research/P0_STRICT_JOINT_TRACE_HANDOFF_20261023T034843Z.md`.

### 1.4 Contamination correction

A broad test run appended test events at `2026-10-23T03:23:25Z` to five tracked
`data/sessions/sup-*.jsonl` files. The cause was tests constructing `Session("sup-*")` without an
explicit `session_dir`; `ragin/cycle/session.py` binds its default at import time.

The correction did **not** use Git `HEAD` and did **not** delete evidence:

- full contaminated bytes, exact suffix bytes, and post-restore copies are preserved under
  `docs/research/test_contamination_20261023T033008Z/`;
- every original prefix was accepted only after exact size + SHA-256 match against
  `docs/research/baseline/tracked_sha256_20261022T184958Z.jsonl`;
- only the verified prefix was restored; all five now match the frozen manifest exactly;
- the appended test-event suffix remains recoverable as a separate artifact.

The full conservation table, hashes, event metadata, and session-directory audit are in
`docs/research/test_contamination_20261023T033008Z/conservation_report.md`.

Two targeted test-isolation fixes prevent recurrence:

- `tests/unit/test_coordination.py`: all five `Session("sup-*")` constructions now use
  `session_dir=str(tmp_path)`;
- `tests/security/test_task2_verified_serving.py`: both default `Sandbox(harness=...)`
  constructions now use `SandboxConfig(session_dir=str(tmp_path / "sessions"))`.

## 2. Evidence and raw exits

All remaining focused test commands were run with unique paths set before interpreter import:

```bash
RAGIN_SESSION_DIR=/tmp/opencode/ragin_envcheck_20261023T033500Z/sessions \
RAGIN_HOST_FICTION_PATH=/tmp/opencode/ragin_envcheck_20261023T033500Z/host/host_fiction.json \
.venv/bin/python -m pytest \
  tests/unit/test_strict_research_profile.py \
  tests/unit/test_verification_deadline.py \
  tests/unit/test_verifier.py \
  tests/unit/test_supported_claims.py \
  tests/unit/test_host_fiction.py \
  tests/unit/test_host_fiction_wiring.py \
  tests/unit/test_coordination.py \
  tests/integration/test_strict_profile_harness.py \
  tests/integration/test_runtime_truth_p0_fixes.py \
  tests/security/test_task2_verified_serving.py \
  -q
```

Result: **289 passed**, raw exit **0**. The aggregate SHA-256 of the `data/sessions` inventory was
identical before and after (`0dcb647984b7134ccc7f0a5a557db5f37dacc4e8facdf1d0d4297d61ce4b9328`),
so the isolated run did not append to the default session directory.

Additional focused evidence already obtained after the final schema normalization:

- `tests/unit/test_verification_deadline.py`: **35 passed**, exit 0.
- strict/deadline/harness plus verifier/supported-claim/host-fiction/runtime-truth set:
  **320 passed**, exit 0.
- serving/provenance/policy/runtime integration set: **156 passed, 2 skipped**, exit 0.
- after the rejection-VERIFICATION observability fix:
  `tests/integration/test_strict_profile_harness.py`,
  `tests/unit/test_strict_research_profile.py`, and
  `tests/unit/test_verification_deadline.py` -> **92 passed**, exit 0, using fresh
  `RAGIN_SESSION_DIR`/`RAGIN_HOST_FICTION_PATH`.

A broad `pytest tests/unit tests/integration` run is **not** used as acceptance evidence because it
caused the default-session append described above. Its raw result was **4 failed, 2061 passed,
22 skipped**; the four failures are in `tests/unit/test_don_v2.py` and report pre-existing
`IntelDocument.score <= 1` validation failures in the dirty Don path, unrelated to the
strict/deadline changes. The run is recorded as contaminated test evidence, not a project gate.

Mypy on the changed production/trace files reports one error at
`ragin/cycle/harness.py:642: "Exception" has no attribute "step5_commit_disposition"`. That line is
pre-existing dirty work, not introduced by the strict/deadline edits; no behavior change was made to
mask it.

## 3. P0 criterion status

| Criterion | Status | Evidence / boundary |
|---|---|---|
| Explicit shared strict profile, independent of arm | **IMPLEMENTED / TESTED** | `strict_research.py`; all-arm harness tests; 320/289-pass runs. Final joint trace still pending. |
| Finite predeclared command/claim contract, fail closed | **IMPLEMENTED / TESTED** | 15 commands; unsupported/compound/extra claims rejected; strict issue codes. Bounded to the contract, not a general Linux oracle. |
| Exact pinned prompt handling | **IMPLEMENTED / TESTED** | Exact current-command echo or exact empty ready prompt only; other prompt-like lines rejected. |
| Authoritative pinned identity, no skill fallback | **IMPLEMENTED / TESTED** | Harness injects `pinned_identity`; missing/unsupported distro fails closed. |
| Real wall-clock deadline, bounded worker | **IMPLEMENTED / TESTED** | Daemon worker, single busy slot, absolute finish check, late-result discard; 35 deadline tests. Not hard cancellation. |
| Full verdict schema validation | **IMPLEMENTED / TESTED** | Non-bool `passed`, malformed/missing/non-string issues, and `passed:true` with issues fail closed. |
| Invalid policy errors do not expose raw values | **IMPLEMENTED / TESTED** | Field-only messages; `from None`; secret-looking regression. |
| Three canonical positive SSH turns | **SCOPED PASS; IDENTITY BLOCKER OPEN** | `p0_strict_joint_trace_20261023T034843Z`; API candidate=verified=served hashes agree, but outer Cowrie `root@svr04:/#` contradicts inner `webapp@web-srv-01`. |
| Observed negative SSH session + actual HTTP 503 | **SCOPED PASS; AVAILABILITY COST OBSERVED** | One separate `cat /etc/sudoers` session; actual 503=1; no `SYSTEM_RESPONSE`; all four attempts `UNSUPPORTED_COMMAND`/`not_attempted`; frontend shows a blank `root@svr04:/#` prompt then closed connection. |
| Final frozen joint trace | **TRACE PASS; READINESS NOT READY** | Raw trace preserved and frozen; B0/B1–B3 matched pilot blocked by outer/inner identity contradiction until supported persona/config matching is validated separately. |
| B0/B1–B3 matched pilot | **NOT READY** | Full-frontend transcript contains `root@svr04` vs `webapp@web-srv-01` contradiction; candidate hashes do not cover prompts. Human/transcript quality must consume full stimulus, never strip contradictions. |
| B1–B3 model execution | **NOT ESTABLISHED** | No local open-weight generative LLM was found. Local Ollama has only `:cloud` aliases, which are not local inference. No model was downloaded or run. |
| Hard network egress isolation | **NOT ESTABLISHED** | Runner uses application-level provider disablement and loopback endpoints; no network namespace/firewall hard block. |
| Legacy session redaction | **STILL OPEN** | Prior readiness report's open item; not addressed here. |

## 4. Local generative model inventory

Read-only inventory is preserved at
`docs/research/p0_continuation_20261023T030050Z/local_generator_inventory/`. Summary:

- No local open-weight generative LLM checkpoint was found.
- `127.0.0.1:11434` exposes Ollama aliases marked `:cloud`; those require a cloud provider and
  are **not** local inference.
- Local assets are Laya encoder/scoring models, Chrollo Random Forest, and encoder caches.
- Hardware: Intel i7-9850H, 12 logical CPUs, 15 GiB RAM, NVIDIA Quadro RTX 4000 8 GiB, CUDA 13.2;
  no `vllm` or `llama.cpp`; no GGUF/GGML files found.

A future B0–B3 pilot must load and verify a pinned local checkpoint explicitly. Nothing in this
report establishes model execution.

## 5. Handoff: final joint trace (executed; packaging deferred)

The final combined strict trace was executed on 2026-10-23. It is preserved at
`docs/research/p0_strict_joint_trace_20261023T034843Z` with the failed precursor at
`docs/research/p0_strict_joint_trace_20261023T034216Z`. The original command form was:

```bash
.venv/bin/python scripts/run_p0_loopback_ssh_trace_v2.py \
  --out docs/research/p0_strict_joint_trace_20261023T034843Z \
  --negative-command 'cat /etc/sudoers'
```

The runner itself sets fresh per-run session/export/host-fiction paths under `--out`, uses the
cached Cowrie image ID with `--pull=never`, binds all listeners to `127.0.0.1`, disables the
provider and Laya, strips credentials, and records prelaunch source hashes.

Required observations before a PASS is claimed:

- all three positive turns: strict `SUPPORTED`, deadline enforced, candidate/verified/served SHA
  agreement, terminal bytes matching the served SHA;
- exactly one negative input in a separate session;
- negative verification fail-closed (`UNSUPPORTED_COMMAND` or `MALFORMED_INPUT`);
- no negative `SYSTEM_RESPONSE` / accepted state;
- **actual** HTTP 503 observed for the negative request;
- no fabricated `root ALL`/`Defaults env_reset` in negative terminal or served text.

Observed on the final run: all three positives passed the scoped checks; the negative produced one
actual HTTP 503, no `SYSTEM_RESPONSE`, four `UNSUPPORTED_COMMAND` verdicts, all `not_attempted`, and
no accepted commit. The raw negative frontend then showed the outer prompt alone and closed the
connection. That blank-prompt behavior is the measured availability cost.

**Readiness blocker:** the outer Cowrie frontend renders `root@svr04:/#` while the RAGIN response
claims `webapp@web-srv-01` / `uid=1001(webapp)`. Strict verification checks the RAGIN candidate, not
the outer prompt. Full-frontend transcript quality therefore fails even though candidate hashes
agree. The matched B0/B1–B3 pilot remains **NOT READY** until a supported Cowrie persona/config
matching the pinned RAGIN identity is validated separately. Do not rewrite Cowrie behavior after the
fact or relax the runner to make the stream look consistent; preserve the actual raw bytes.

If any observation differs, preserve the failed artifact directory and do not relax the grammar or
the serving invariants to force a pass.

## 6. Linked artifacts

- Prior readiness report: `docs/research/EXPERIMENT_READINESS_REPORT.md`
- Causal protocol: `docs/research/CAUSAL_ABLATION_PROTOCOL.md`
- Final trace handoff (actual status, raw stream, identity blocker, drift):
  `docs/research/P0_STRICT_JOINT_TRACE_HANDOFF_20261023T034843Z.md`
- Final trace frozen manifest:
  `docs/research/P0_STRICT_JOINT_TRACE_20261023T034843Z_FROZEN_MANIFEST.json`
- Failed precursor frozen manifest:
  `docs/research/P0_STRICT_JOINT_TRACE_20261023T034216Z_FAILED_FROZEN_MANIFEST.json`
- Raw final trace directory: `docs/research/p0_strict_joint_trace_20261023T034843Z/`
- Raw failed precursor directory: `docs/research/p0_strict_joint_trace_20261023T034216Z/`
- Pre-edit snapshot and local inventory:
  `docs/research/p0_continuation_20261023T030050Z/`
- Test-contamination preservation and conservation report:
  `docs/research/test_contamination_20261023T033008Z/`
  - `conservation_report.md`
  - `prefix_verification.json`
  - `restored_sha256.json`
  - `contaminated/`, `suffix/`, `restored/`
  - `session_inventory_after.jsonl`
  - `not_in_20261022T184958Z_inventory.jsonl`
  - `handoff_hashes.json`
  - `artifact_manifest.json`
- Strict profile: `ragin/cycle/strict_research.py`
- Deadline/verdict validation: `ragin/cycle/verification_deadline.py`
- Verifier integration: `ragin/cycle/verifier.py`
- Harness policy/pinned identity: `ragin/cycle/harness.py`
- Host-fiction profile delegation: `ragin/graph/host_fiction.py`
- Joint trace runner: `scripts/run_p0_loopback_ssh_trace_v2.py`
- Focused tests: `tests/unit/test_strict_research_profile.py`,
  `tests/unit/test_verification_deadline.py`,
  `tests/integration/test_strict_profile_harness.py`

## 7. Boundary

This is a continuation state, not a claim that the full experiment plan is ready. The final
positive/negative SSH trace is **PASS on its scoped checks**, but B0/B1–B3 matched pilot readiness
is **NOT READY** because the attacker-visible Cowrie prompt contradicts the inner RAGIN identity.
B1–B3 model execution remains **NOT ESTABLISHED**. No manuscript claims are made. `graphify update .`
was deferred until evaluation finished; the one required AST-only update is now
recorded in the recovery-final supplement below.

## 8. Recovery-final supplement (2026-10-23T04:29Z)

The current bounded validation package is
`docs/research/recovery_final_20261023T042900Z/FINAL_HANDOFF.md`. It contains a
66-path current-byte archive, focused 86-test regression, scoped Ruff evidence,
the AST-only graph update log, the final strict loopback trace, and copied
supervisor 489-test evidence. The final trace passed all scoped checks:
three positive commands and one negative command, loopback listeners, actual
HTTP 503, no accepted negative commit, candidate/served correspondence, and
cleanup. Post-trace source verification remained 66/66 with no changed or
missing entries.

The bounded persona proof is
`docs/research/persona_alignment_20261023T042600Z/summary.json`: exactly two
SSH sessions and five commands per session. Native Cowrie matched the declared
persona; the RAGIN frontend retained the `webapp@web-srv-01:/$` mismatch and
unsupported commands failed closed. This is an explicit blocker, with raw
frontend bytes preserved.

The prior trace's blank prompt followed the runner's normal stdin/EOF teardown;
it is an observed terminal behavior and availability cost, not evidence that
the server caused a disconnect. The final strict trace similarly records
terminal bytes and cleanup without assigning an unsupported causal mechanism.

`graphify update .` is complete once in this supplement's evidence log. The
external four-request synthetic preflight remains draft and unexecuted; no
provider calls or model inference occurred. B1–B3, human ratings, higher-level
statistics, and B5/JEV remain **NOT READY/NOT ESTABLISHED**.
