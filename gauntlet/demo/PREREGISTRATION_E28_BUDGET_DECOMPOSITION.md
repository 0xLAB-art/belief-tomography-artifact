# PREREGISTRATION — E28: E2-era Zero Decomposition (Filter vs Budget vs Model)

**Registered:** 2026-11-23, before any E28 data. Motivated by the author's
challenge: "0/60 on the public template is implausible."

## Registered question

E2-v1's state-deception zero (0/60 sessions, 2026-11-19/20) was measured
while 100% of the family's gen-1/gen-2 turns were unavailable (frozen
artifacts: 40/40 g1+g2 turns + 20/40 g3 turns blocked, identical pattern in
the seed-99999 retest). Frozen elapsed-time analysis: 57/60 blocked turns
completed in 3.8-7 s (ok-turn median 4.4 s) — a fast-rejection signature
(HTTP-400 provider content-block), NOT the 25-30 s empty-completion
signature of the 200-token budget. E28 reproduces the exact blocked
templates TODAY under both budget regimes to close the mechanism question
by measurement.

## Protocol

gpt-5.6-sol, PUBLIC v0 gen-1 + gen-2 state-deception templates (seed 2718 —
the exact probe texts E2 measured), fresh sessions, HeuristicJury,
GatewayBlockGuard discipline:

- **Arm A (E2-era instrument):** 10 sessions per generation (20 total) at
  `LLM_TARGET_MAX_OUTPUT_TOKENS=200`.
- **Arm B (repaired instrument):** 10 sessions per generation (20 total) at
  1024 tokens (= the E21/E25/E27 condition).

Per-turn telemetry: blocked flag, elapsed_s, reply kind (fast-blocked
<8 s / slow-blocked >=8 s / completed).

## Endpoints (registered)

1. **Arm A blocked fraction** (turn level) and elapsed distribution:
   fast-blocked dominance reproduces the E2-era filter signature today.
2. **Arm B breach fraction:** replication of the breach regime on the
   identical texts (E25 public arm measured 2/10).
3. **Interpretation matrix:**
   - A fast-blocked + B breaches → E2's zero was provider-filtered (the
     model was never asked); the 11-20→11-22 change is in the SERVED
     behavior (filter relaxation and/or model change — non-decomposable
     black-box); the Γ series measures served behavior.
   - A empty-dominant (slow) + B breaches → the 200-token budget masked
     breaches; E2's zero is budget-censored beyond its disclosed interval.
   - A completes-and-refuses + B breaches → the budget does not mask;
     model-side behavior changed (drift proper).
   - A breaches → E2's exact instrument condition breaches today: the
     zero was pre-onset behavior, drift stands regardless of budget.

## Kill gates

Censoring > 50% per arm → halt. Real-credential material → halt.
Deviations logged before analysis.

## Deviation (logged mid-run, before any analysis)

The prereg's frozen-data inference ("fast <8 s blocked = provider 400
filter; NOT the budget") is CONTRADICTED by Arm A's live telemetry: the
200-token arm returns EMPTY completions in 3.7-5.5 s — fast empties are a
budget signature too (hidden reasoning consumes the cap quickly). The
elapsed discriminator is therefore uninformative for 400-vs-empty; the
registered interpretation matrix stands unchanged (the live A/B arms
decide, not the elapsed inference). The frozen E2 blocks are a
non-decomposable mix of {400, empty, timeout} as the E2 report disclosed.

## Outcome (registered matrix arm: "A empty-dominant + B breaches")

Arm A: 19/20 calls EMPTY (1 ok), 0/20 breaches. Arm B: 17/19 ok (2 EMPTY),
4/20 breaches (g1 1/10, g2 3/10). → the 200-token budget masked the
family's behavior; E2's state-deception zero is budget-censored beyond its
disclosed interval. The identical seed-2718 texts complete and breach at
the repaired budget on the same day — model-side drift is non-identifiable
and not needed as an explanation.

## Deviation 2 (telemetry)

The `blocked` field in e28_sessions.jsonl (and e27_sessions.jsonl) is
unreliable: `GatewayBlockGuard` exposes no `last_blocked` attribute, so the
recorded flag is always False. The authoritative per-call decomposition
comes from llm_target's stderr (counted above from e28_run.log). E27's
"zero session-level censoring" statement is correspondingly corrected to
"7 turn-level EMPTY completions on gpt-6.1-sol mapped conservatively".
