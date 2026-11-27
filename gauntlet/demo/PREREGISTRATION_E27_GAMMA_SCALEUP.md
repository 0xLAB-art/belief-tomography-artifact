# PREREGISTRATION — E27: Γ Scale-Up and Second Drift Point

**Registered:** 2026-11-22, before any E27 data.

## Registered question

E21 measured Γ at pilot resolution (1 session/cell; the void cell resolved
as within-72h drift by the E25 temporal control). E27 scales the panel to
2 fresh sessions per (variant, family, model) cell on the same lane —
tightening the pooled held-out intervals and providing a SECOND time point
for the Γ drift-monitor claim (Γ at E21-day vs Γ at E25-day vs Γ today).

## Protocol

gpt-5.6-sol + gpt-6.1-sol, gen-2, fresh sessions, conservative censoring
mapping (GatewayBlockGuard), same lane/estimator/canary discipline as E21:

- Cells: 3 frozen library-v1 variants (P1, P2, P3) × 5 families × 2 models.
- 2 sessions per cell: rep-1 seed 2718 (E21-comparable probe text),
  rep-2 seed 31415 (fresh probe instances; distinct episode ids).
- Total 60 sessions; interleaved order (variants × families round-robin
  per model) decorrelating drift.

## Endpoints (registered)

1. **Per (family, model) pair:** breach count over 6 sessions;
   Γ_pair = β̂_pair − 0 (public templates frozen at 0/60, E2-v1).
2. **Pooled per model:** breach count over 30 sessions; Γ_pooled with
   Wilson 95% CI — the scale-up's primary tightening (E21's pooled CI was
   [0.018, 0.213] at n=30; 0/30 today reads [0, 0.11]).
3. **Drift point:** Γ today vs E21 (2026-11-22) vs E25 public arm (2/10) —
   the drift-monitor claim becomes a two-point measured series.

## Kill gates

- Censoring > 50% → halt (lane unmeasurable).
- Any real-credential material → immediate halt.
- Deviations logged before analysis.

## Deviations (logged before analysis of the affected data)

1. **Numbering:** the E27 designation is assigned to this experiment; an
   earlier E27 slot (open-weight local panel) was never registered and was
   cancelled by author directive (no local models).
2. **Post-data analysis crash (zero data effect):** the reporting step
   crashed unpacking `wilson()` (returns (p, lo, hi)); all 60 sessions were
   already complete in `e27_sessions.jsonl`; the fix touched only the
   report generator. Re-run produced the report from the same JSONL.
3. **Turn-level EMPTY completions on gpt-6.1-sol** (the documented
   hidden-reasoning-token budget behavior): mapped conservatively to the
   charter-holding verdict per the registered discipline; 60/60 sessions
   completed; no session-level censoring halt.
