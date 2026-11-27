# Pre-registration v2 — A/B workload with headroom (2026-10-28)

**Why a second study.** The v1 analysis (`arm_stats_bootstrap_v1.json`) is not a test of the
hypothesis; it is a test of a ceiling. 17 of 30 sessions ended at the 14-turn cap, and the arms
issued almost the same number of turns (12.4 vs 12.33). The only thing separating the arms was
wall-clock dwell, which decomposes as `turns × per-turn time`: the RAGIN arm answered faster
(8.2 s vs 16.9 s to first response), so its sessions were *shorter in seconds* while lasting the
*same number of turns*. Reporting that as an engagement difference would be a latency artifact.
v2 gives the endpoint headroom and removes the confound.

**Inputs.** Fresh sessions only. The v1 30 sessions stay in the artifact and in the paper as the
underpowered pilot; they are not pooled with v2 and not re-analysed under v2 endpoints.

## Design

| Item | v1 | v2 |
|---|---|---|
| Turn cap | 14 (per-persona 8–14) | **30** (novice 12, evasion 18, credential 25, recon 30, APT 30) |
| n | 15/arm (3 per persona) | **20/arm (4 per persona)** |
| Primary endpoint | dwell (s) | **turns survived** (latency-free) |
| Secondary | first-turn latency | **bait capture** (read a planted artifact *and* attempt to reuse it) |
| Descriptive | hits | dwell, server-side latency, depth (unique paths, privilege attempts) |
| Attacker brain | one model family | unchanged: same model, prompts, temperature for both arms |
| Order | A then C | **interleaved A/C per persona run**, seeded shuffle, to spread provider drift |

Arms: stock cowrie (A) vs cowrie + RAGIN loop (C), local compose (`docker-compose.field.yml`),
never the field IP, same caveats as v1 (shared host, different surfaces by design).

## Endpoints and tests

1. **Primary — turns survived.** Mann–Whitney U on uncensored turns + Kaplan–Meier with
   right-censoring at the persona cap; the log-rank test is the confirmatory statistic when
   censoring is non-trivial. Effect size: rank-biserial and the difference in restricted mean
   survival time. Bootstrap CI (10k, seed `20261028`, stratified by persona).
2. **Secondary — bait capture.** Session-level binary: the attacker read at least one planted
   artifact (`.dbpass`, `.env` with AWS-shaped keys, `id_rsa`) *and* then attempted to use it
   (e.g. `ssh`, `mysql`, `curl` with the captured value). Fisher exact + bootstrap CI of the
   risk difference. Coding rule is fixed here, before the run.
3. **Descriptive, no test.** Wall-clock dwell, server-side response latency measured at the
   driver (time from writing the command to first byte returned), output length, unique paths
   touched, privilege-escalation attempts, VERDICT rate.

**Multiplicity:** Holm across the two confirmatory endpoints. **No optional stopping:** the run
ends at 20 sessions per arm; interim looks are not analysed. Sessions that fail to connect are
logged and replaced up to 3 attempts, and the replacement count is reported.

## Decision rule

- **Turns: CI excludes 0** → "the RAGIN arm sustains the adversary N turns longer (CI …), with
  M of 20 stock sessions abandoning before the cap versus K of 20."
- **Turns: CI includes 0** → the paper reports a null **with headroom** ("at a 30-turn cap the
  arms are indistinguishable; the earlier 14-turn study could not have detected this"), and
  drops any engagement claim.
- **Bait capture significant** → this becomes the paper's treatment-effect sentence, because it
  is attacker behaviour rather than a surface property.
- **Either way**, v1 and v2 are both reported; v1 is labelled "pilot, ceiling-limited".

## What would make us stop rather than push

If v2 also returns a null, the paper's contribution stays the negative result and the verified
serving floor. Re-running with a larger cap or more personas until something turns significant
is explicitly out of bounds; a v3 would need a different mechanism (not a bigger n).

## Artifact contract

`results/field_attack/arm_v2_stats.json` — same schema family as v1 plus
`survival: {km_a, km_c, logrank_p, restricted_mean_a, restricted_mean_c}` and
`coding: {bait_capture_rule_sha256}`. `--check` mode recomputes and fails on drift.

## Amendment 1 — 2026-10-28 (before any v2 session was used)

Three implementation facts surfaced during the pilot and are fixed here, before data collection:

1. **Attacker brain.** The v1 provider (apmix free tier) is retired, so "unchanged model" is not
   available. A latency probe of the three exposed checkpoints (identical prompt, effort=low)
   gave gpt-6-astra 10–15 s, gpt-6.1-sol 17–35 s, and gpt-5.6-sol 5–128 s. v2 uses
   **gpt-6-astra, reasoning effort low**, env-overridable, recorded in every session record. The
   same model and effort serve both arms.
2. **Session lifetime.** Cowrie closes an interactive session at `[honeypot]
   interactive_timeout` (fallback **300 s**). That, not the turn cap, is the real ceiling behind
   v1's 67–335 s dwell range. v2 runs the arms with the timeout raised to 3600 s
   (`COWRIE_INTERACTIVE_TIMEOUT`), default unchanged for the field posture.
3. **Turn budget.** The attacker's Responses call carries `max_output_tokens=1200`: at 400 the
   reasoning trace sometimes consumed the whole budget and returned no message.

None of the endpoints, tests, n, or decision rules change.
