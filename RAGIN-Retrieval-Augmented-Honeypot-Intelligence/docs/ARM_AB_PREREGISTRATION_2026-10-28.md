# Pre-registration — A/B workload statistics (2026-10-28)

**Status:** written and committed to disk *before* the analysis script was run. Any deviation
after this point is recorded in the artifact's `deviations` block, not silently applied.

**Inputs (frozen):**
- `results/field_attack/sessions_armA_cowrie.jsonl` — 15 sessions, 5 personas × 3 runs
- `results/field_attack/sessions_armC_ragin.jsonl` — 15 sessions, 5 personas × 3 runs
- Both produced by `scripts/field_attack_driver.py` as **local self-play**, never the live field
  IP; arms share one host IP; surfaces differ by design (see `arm_comparison.json` caveats).

**Question.** On the same AI adversarial workload, does the RAGIN arm change (a) how long a
session survives, (b) how fast each turn is served, and (c) whether the attacker issues
commands aimed at planted credentials?

## Endpoints

| Tier | Endpoint | Unit | Why |
|---|---|---|---|
| Primary (confirmatory) | `dwell_s` | session | the paper's engagement claim |
| Secondary (confirmatory) | `turn_latency_s` (mean of non-null per-turn latencies) | session | the paper's detectability/latency claim |
| Secondary (confirmatory) | `bait_targeting` = 1 if the session issued ≥1 command matching planted-credential paths | session (binary) | attacker behaviour that is **not** surface-dependent |
| Descriptive (no test) | turns, output chars/turn, command-class counts | session | reported with intervals only |
| Descriptive, **not contrasted** | `sensitive_read_hits` from transcripts (`.env`, `.dbpass`, `AKIA…`, `id_rsa`) | arm | counts what each surface *returns*; different surfaces make a contrast invalid |

`turns` is reported but excluded from the confirmatory family: it is mechanically coupled to
`dwell_s` (same conversation) and would double-count one effect.

## Statistics

- **Interval:** percentile bootstrap, 10,000 resamples, seed `20261028`, **stratified by
  persona** (3 sessions per persona per arm, so every resample keeps the persona mix). Reported
  as the CI of the difference of means (C − A), two-sided 95%.
- **Test:** Mann–Whitney U, two-sided, exact for n=15/15; effect size = rank-biserial `r`.
  Binary endpoint: Fisher exact, two-sided.
- **Multiplicity:** Holm–Bonferroni across the **three** confirmatory endpoints. Descriptive
  endpoints carry CIs and no p-values; they are labelled descriptive in the paper.
- **Censoring:** a session is flagged `censored` if `turns` equals the driver's turn cap
  (observed max = 14). Dwell is therefore a truncated statistic; the artifact reports both the
  raw mean and a sensitivity mean re-computed with capped sessions at the median turn time.
- **Power statement:** post-hoc minimum detectable difference at 80% power / α=0.05 is
  simulated from the observed pooled SD and reported **labelled post hoc**; it is used only to
  size the "no measurable difference" sentence, never to claim equivalence.

## Decision rule (fixed now, applied whatever the numbers say)

1. **CI excludes 0 and Holm-adjusted p < 0.05** → the paper says "measurable difference at
   n=15/arm, direction X, CI […], rank-biserial r = …".
2. **CI includes 0** → the paper says "**no measurable difference at this sample size**" and
   reports the post-hoc MDE. It must **not** say "better", "directionally better", or
   "trending" anywhere.
3. **Bait targeting significant, dwell not** → the paper's treatment-effect sentence is the bait
   endpoint, with the dwell result reported as a bounded null. This is the expected shape and is
   an acceptable, honest outcome.
4. **Every endpoint reported**, including ones that favour the control arm. No endpoint gets
   dropped for being inconvenient; the artifact is the source of every number in §5.

## What this cannot establish

External validity. Both arms are local self-play against an LLM attacker; the field endpoint is
reported separately as real-but-scanner-grade traffic. No claim about human attackers is made
from this artifact.

## Artifact contract

`results/field_attack/arm_stats_bootstrap_v1.json`:

```
schema, generated_at, preregistration: {path, sha256},
inputs: {arm_a, arm_c, per-file sha256},
endpoints: {<name>: {tier, unit, point_a, point_c, diff, ci95, p_raw, p_holm, effect_size, n}},
bootstrap: {iterations, seed, strata},
censoring: {cap_turns, censored_a, censored_c, sensitivity},
power: {mde_posthoc, method},
descriptive: {...},
deviations: [...]
```

Schema pinned by `tests/unit/test_field_arm_stats.py`; `--check` mode recomputes and fails on
drift, matching the repo's "no number moves without its artifact" rule.
