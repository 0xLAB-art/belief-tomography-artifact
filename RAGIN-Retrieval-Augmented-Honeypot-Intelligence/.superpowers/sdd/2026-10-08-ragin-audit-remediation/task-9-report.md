# Task 9 report — Verify rescue-benchmark validity and limitations

Worker: Sisyphus (OpenCode), model `opencode/fledge-alpha-free`.
Date: 2026-10-08, verification pass completed 2026-10-08T06:14:00Z.
Repo state at verification: branch `main`, HEAD `f01a4a9` (`f01a4a98d8fc0cdbf1f031d915385294675e3b1b`), dirty worktree preserved (no reset/clean/push/merge performed).

## Scope

Task 9 only. Recomputed split integrity, prefix schedule, learning-curve
values, behavior-floor coverage, the self-consistency rule, and the
provider-contamination boundary from local provider-free inputs. No provider
calls, no secrets, no destructive operations, no further agents dispatched.

## Commands run and exact outputs

### 1. Split integrity / corpus hashes

```
sha256sum results/sp2027_rescue/behavior_trajectory_benchmark.json data/training/test.jsonl data/training/train.jsonl
```

```
f6945dee790432583a79a06e22589d96376e3bf76470fccb4b6149e89207b338  results/sp2027_rescue/behavior_trajectory_benchmark.json
046d9b19e868517e72c35ef1e9c4be9a910d3a3d0703ec3fecee494069d22b26  data/training/test.jsonl
e5bf8a71a78e331252f72ce437042f69cd88502e1d00f5c998e88ca75e132333  data/training/train.jsonl
```

Independent recomputation from the corpus files (not the artifact):

```
train 1600 test 400 overlap 0
```

Artifact self-report agrees: `corpus.n_test_sessions=400`,
`n_sessions_with_commands=400`, `train_test_id_overlap=0`,
`test_sha256=046d9b19…`, `train_sha256=e5bf8a71…`, skill distribution
{apt:100, expert:100, intermediate:100, novice:100}.

Session-level grouping: 6,400 artifact rows all keyed uniquely by
(session_id, prefix, arm); 400 distinct sessions; every (session, prefix)
appears in exactly one `skill_only` and one `behavior_floor` row.

### 2. Prefix schedule

`PREFIXES = (1, 2, 4, 8, 16, 32, 64, "all")` from the source script; each
prefix contributes 400 sessions per arm (400 × 8 × 2 = 6,400 rows). Every row
satisfies `len(commands_seen) == prefix_n` (asserted over all 6,400 rows).

### 3. Learning-curve values (skill_only arm, per prefix)

```
prefix   1:  skill_accuracy 0.25,   floor_coverage 0.15,   under_rate 0.85,  mean_depth 1.83
prefix   2:  skill_accuracy 0.25,   floor_coverage 0.15,   under_rate 0.85,  mean_depth 1.83
prefix   4:  skill_accuracy 0.2575, floor_coverage 0.15,   under_rate 0.85,  mean_depth 1.8275
prefix   8:  skill_accuracy 0.3125, floor_coverage 0.16,   under_rate 0.84,  mean_depth 1.7625
prefix  16:  skill_accuracy 0.56,   floor_coverage 0.3525, under_rate 0.6475, mean_depth 0.8775
prefix  32:  skill_accuracy 0.75,   floor_coverage 0.455,  under_rate 0.545,  mean_depth 0.6275
prefix  64:  skill_accuracy 0.95,   floor_coverage 0.6425, under_rate 0.3575, mean_depth 0.405
prefix all:  skill_accuracy 0.955,  floor_coverage 0.655,  under_rate 0.345,  mean_depth 0.3925
```

Aggregate `skill_only`: 3,200 prefix rows, 400 sessions, skill accuracy
0.5356, risk-floor coverage 0.3394, under-routing rate 0.6606, mean under
depth 1.1113, episode eventual floor coverage 0.655, median commands to floor
22.5, low-gold episode escalation 0.5333.

Aggregate `behavior_floor`: 3,200 prefix rows, 400 sessions, skill accuracy
0.5356, risk-floor coverage 0.57, under-routing rate 0.43, mean under depth
0.7119, episode eventual floor coverage 1.0, median commands to floor 16.0,
low-gold episode escalation 0.5333.

These match `docs/RAGIN_RESULTS_LEDGER_2026-10-08.md` §5 (skill accuracy
0.5356, floor coverage 0.3394, under-routing 0.6606, paired coverage delta
+0.2306, under-depth delta 0.3994) and `paper/sections/sp_evaluation.tex`
(`0.250` after one command → `0.750` after 32 → `0.950` after 64, final
`0.955`).

### 4. Paired deltas (behavior_floor − skill_only)

```
coverage_delta:  mean 0.2306, bootstrap CI [0.2159, 0.245]
under_depth_delta: mean 0.3994, bootstrap CI [0.3775, 0.4209]
```

### 5. Self-consistency boundary

Gold risk is defined as `Supervisor._behavior_floor({"attacker_inputs": commands})`.
Recomputed against all 400 `data/training/test.jsonl` sessions: artifact
`gold_risk` matches `Supervisor._behavior_floor` with **0/400 mismatches**.
The `behavior_floor` arm's routing calls the same `Supervisor._behavior_floor`
through `Supervisor._compute_risk` (verified in
`ragin/cycle/coordination.py`); the `skill_only` arm passes empty
`attacker_inputs`. The independent result is therefore the Chrollo
skill-classification learning curve only. The risk-floor comparison is a
self-consistency diagnostic — same rule on both sides — and must not be
cited as independent effectiveness.

### 6. Provider contamination boundary

Artifact `method.provider_calls=false`, `method.field_deployment=false`.
Inputs are `data/training/test.jsonl` + `data/training/train.jsonl` +
local Chrollo classifier; no network or provider key involved. The
`results/sp2027_rescue/hostfiction_provider_*` artifacts remain classified
excluded/fallback-only (deterministic fallback after HTTP 404 `Unknown
model`; Task 8 recheck 2026-10-08T06:03:31Z exit 2: catalog lists only
`claude-sonnet-4-6-free`, quota `not_probed`). They are not required by the
rescue result and are not counted as independent model evidence.

### 7. Independent reproduction via source script

```
time .venv/bin/python scripts/sp2027_rescue_behavior_benchmark.py --out /tmp/sp2027_rescue_check.json
# real 5m19.832s, user 4m38.037s, sys 0m27.722s, exit=0
```

Regenerated artifact compared field-by-field against the committed artifact:

```
corpus equal: True
arms equal: True
paired_deltas equal: True
rows match: True 6400 6400
```

`/tmp/sp2027_rescue_check.json` sha256
`b5f43bab5414d371f0c4cccfa0864768b415d5f5c2680dbb97a7b8eeb8c1d532`.
The committed artifact is byte-for-byte equivalent in every compared field —
the rescue benchmark is reproducible from provider-free inputs.

### 8. Claim-limit wording sync check

- `results/sp2027_rescue/README.md` states: provider-free replay of 400
  held-out sessions, independent result = Chrollo skill-classification
  learning curve, risk-floor comparison explicitly a self-consistency
  diagnostic, hostfiction provider pilots excluded, Task 8 blocked-branch
  evidence present.
- `paper/sections/sp_evaluation.tex` states the trajectory audit is not an
  independent deception-effectiveness result, the risk-floor diagnostic is
  controller-self-referential, it is not used as a headline security gain,
  field traffic/human raters remain future validation targets, and the
  adaptive routing rung was removed.
- `paper/sections/sp_appendix.tex` repeats: risk-floor diagnostic is
  explicitly self-referential and not an independent effectiveness claim;
  provider-backed reruns are not required.
- `paper/sections/discussion.tex` and `paper/evaluation.tex` retain the
  bounded fold-down wording (no dwell gain, Δ=0.0 resolution-bounded).
- Ledger `docs/RAGIN_RESULTS_LEDGER_2026-10-08.md` §5 and §9 already state
  provider-free/held-out/fallback-only status, no field validation, no
  adaptive-superiority claim.

No stale rescue wording was found, so no README/paper/test wording edits
were required for synchronization.

### 9. Focused test battery

```
.venv/bin/pytest -q tests/unit/test_artifact_consistency.py tests/unit/test_supported_claims.py
```

```
44 passed in 0.48s
```

`git diff --check` across the worktree: clean (no whitespace errors).

## Files changed by Task 9

- Created: `.superpowers/sdd/2026-10-08-ragin-audit-remediation/task-9-report.md` (this file).
- No other file was modified. Pre-existing dirty-worktree state (README.md, PROJECT_STATUS.md, paper/main.tex, sections, ragin/don/rag_engine.py, results/apmix_*, results/jev_hard_subset.json, tests/unit/test_artifact_consistency.py, tests/unit/test_don.py, data/sessions/*.jsonl, untracked .omo/ and ses-* artifacts) is preserved untouched.
- Scratch artifact `/tmp/sp2027_rescue_check.json` (outside the repo) retained for audit.

## Residual limitations

- The risk-floor reference rule is implemented by the same Supervisor that
  the `behavior_floor` arm exercises; the comparison is self-consistency,
  not independent effectiveness, and must be cited that way.
- Gold risk is the controller-defined deterministic floor, not independent
  attacker ground truth; the benchmark does not establish field validity.
- No adaptive-agent superiority claim is supported: the rescue result is a
  held-out classification/behavior-floor learning-curve measurement on
  provider-free inputs.
- Provider-backed claims remain blocked (catalog drift exit 2, quota
  `not_probed`); `hostfiction_provider_*` artifacts are
  excluded/fallback-only operational traces.
- Reproduction of the committed artifact required ~5m20s on this machine;
  determinism held for corpus/arms/paired deltas and all 6,400 rows, but
  wall-clock reproduction cost is non-trivial.
- The rescue artifact file itself was not regenerated in place (kept at its
  committed hash `f6945dee…` with mtime 2026-10-03 07:18:12 +0300); the
  equivalence check was done against a `/tmp` copy to avoid mutating the
  canonical artifact.
