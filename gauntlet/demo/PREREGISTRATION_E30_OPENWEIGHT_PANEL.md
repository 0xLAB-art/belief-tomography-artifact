# PREREGISTRATION — E30: Open-Weight Panel (verifiable models)

**Registered:** 2026-11-22, before any E30 data. Closes the program's
largest remaining reproducibility gap: the gateway panels address
catalog names whose serving snapshots are not independently verifiable.
E30 runs the SAME registered panel on three open-weight (openly served)
models that anyone with the API endpoint can address.

## Protocol

The E2-v1/E29 driver (`run_e30_openweight_panel.py`, stem E30_*), per
model: 5 families × 3 generations × 20 probes = 300 sessions, seed 2718
(identical probe instances to E2-v1/E29), fresh target subprocess per
episode, HeuristicJury, GatewayBlockGuard discipline, repaired 1024-token
budget (the same instrument as E29 — comparability by construction).

Models (author-supplied lane, chat-style, chat completions API):
1. DeepSeek-V4-Flash
2. DeepSeek-V4-Pro
3. kimi-k3.1-pro

Lane endpoint and key stored outside the repository
(~/.config/ragin/openweight.env, chmod 600, never committed).

## Endpoints (registered)

1. Per-model, per-family β̂ with Wilson 95% CIs — the first panels whose
   serving identity is verifiable by any reader.
2. Turn-level censoring per model (reasoning-token budget interaction
   expected to vary; the repaired 1024 budget applies to all).
3. Comparison vs the gateway repaired panel (E29): do the open-weight
   models hold their charters like the gateway-catalog models, and where
   do they breach?

## Kill gates

Censoring > 50% per model → that model reported unmeasurable (the
E2-v1b retest precedent), no reliability claim. Real-credential material
→ halt. Deviations logged before analysis.

## Deviation 1 (pre-data)

kimi-k3.1-pro is replaced by MiniMax-M3.1-Flash (author directive:
kimi's measured latency ~70 s/call projects ~8 h for the panel; MiniMax
smoke-tested at ~5 s/call on the same lane). Final model list:
DeepSeek-V4-Flash, DeepSeek-V4-Pro, MiniMax-M3.1-Flash.
Also logged: the first launch attempt hit the WRONG endpoint (the
project .env's stale RAGIN_LLM_* values overrode the wrapper's process
env; llm_target's fallback branch now honors process env and argv model);
the truncated one-session artifacts were deleted before any real data.

## Deviation 2 (logged 2026-11-23, post-data, pre-analysis — see E31's registration)

The executed E30 runs used the chat-style transport with a **hardcoded 200-token
`max_tokens` cap**, not the registered "repaired 1024 budget": the chat branch of
`llm_target.py` did not read `LLM_TARGET_MAX_OUTPUT_TOKENS` (only the
responses-style branch did). Consequences: the three E30 arms ran at 200 output
tokens (replies visibly truncate mid-sentence; MiniMax-M3.1-Flash's 75.8%
turn-level EMPTYs are the E28 budget-truncation mechanism at the un-repaired
budget, not a 1024-budget reasoning effect). E30's numbers are reported as
measured-under-200 with this deviation disclosed; the registered re-measurement
at the repaired budget is **E31** (PREREGISTRATION_E31_OPENWEIGHT_REPAIRED.md,
registered 2026-11-23 before data). Temperature 0.2 (chat-branch historical
value) is disclosed as a lane parameter.
