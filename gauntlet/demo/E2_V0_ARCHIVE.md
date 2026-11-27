# E2-v0 ARCHIVE — INVALID as an independent-session measurement (2026-11-19)

**Status: ARCHIVED, NOT QUOTABLE.** This file preserves the E2-v0 artifacts and a
numeric reconciliation. The run is superseded by **E2-v1** (`E2_RESULTS_V1.md`),
because the v0 live driver violated episode independence (see §Defect).

## What the stored profiles actually show

| Agent | episodes | breach verdicts | state_deception | exposure |
|---|---|---|---|---|
| gpt-6.1-sol (seed 2718) | 300 | 0 | 0/60 | 0.00% |
| gpt-5.6-sol (seed 2718) | 300 | **2** | **2/60** [0.9%, 11.4%] — both in generation 2 (2/20) | 0.67% |
| gpt-6.1-sol (retest seed 99999) | 300 | 0 | 0/60 | 0.00% |

- Episodes per model = 5 families × 3 generations × 20 probes/cell = **300**
  (the earlier report's "60 episodes / 240 total / 66 calls" was an arithmetic
  and copy error from an earlier smoke run).
- "Behavioral exposure" is the mean of the five family βs, not the breach rate;
  for gpt-5.6-sol both happen to equal 0.67% (0.0333/5 = 2/300).
- Wilson 95% CIs: 0/60 → [0, 0.060]; 2/60 → [0.009, 0.114].

## Defect that invalidates the run

`GauntletGenerator` numbers every episode `E0001` (fresh generator per probe),
and `llm_target.py` keyed its conversation dictionary by `episode_id` without a
per-episode reset. Therefore **all 300 probes accumulated in one conversation**
with no session boundary. This violates the independence assumption of β̂: the
target's later answers were conditioned on the entire prior probe history.
The v0 "test–retest agreement" is not a reliability measurement either — both
runs shared the same contamination.

Evidence: `all probes yield E0001` (5/5 in the generator reproduction);
`llm_target.py` v0 had no `turn == 0` reset; transcript logging did not exist
in v0, so the raw sessions cannot be re-inspected.

## Retracted numerical claims from the first version of this file

1. "60 episodes ≈ 66 calls per agent per run" → **300 episodes, ~400 calls/model**.
2. "Total measured breaches across 240 episodes: 1" → **2 breach verdicts across
   600 episode executions (both in gpt-5.6-sol, state_deception gen-2)**.
3. "19 of ~66 probe turns were content-blocked (~29%)" → the **19** is the
   per-run count written by the guard, but the v0 runner did not persist the
   call denominator; **the 29% rate is retracted**. E2-v1 persists calls and
   blocks per run.
4. "test–retest perfect agreement" → archived, not a reliability result
   (shared contamination).

## What survives

- The wire, gateway lane, guard, and estimator code were exercised end-to-end.
- The observed state_deception gen-2 clustering is a **hypothesis for E2-v1**,
  not a measurement.
- The run's artifacts (`LIVE_PROFILE_*.md/json`) remain as engineering evidence.

## Corrective actions (committed before E2-v1 data)

- `llm_target.py`: reset the conversation when `turn == 0` (episode isolation).
- `run_live_e2_replication.py`: unique per-probe session ids, JSONL transcripts
  for every turn, JSONL verdicts, persisted run metadata (calls / blocked /
  seed / estimator pin).
- Prereg deviation logged before data: `PREREGISTRATION_E2E3.md` (2026-11-19).
