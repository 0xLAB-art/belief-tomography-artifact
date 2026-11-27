# PREREGISTRATION — E31: Open-Weight Panel Re-measurement at the Repaired Chat Budget

**Registered:** 2026-11-23, before any E31 data.

## Why this experiment exists (deviation being corrected, logged pre-data)

E30's registration states the panel runs at "the repaired 1024-token budget (the
same instrument as E29 — comparability by construction)". Forensics on the
executed code show this was **not true for the chat-style lane**: `llm_target.py`'s
chat branch hardcoded `max_tokens: 200` (only the responses branch read
`LLM_TARGET_MAX_OUTPUT_TOKENS`, default 1024). The gateway runs (E21–E29) used
responses style, so they did run at 1024; **E30's three open-weight arms ran
chat-style capped at 200 output tokens each turn**. Evidence: `llm_target.py`
at commit 5d0ae2f (unchanged through the E30 run), `e30_run.log` ("style=chat"),
visible mid-sentence truncations in E30 transcripts, and MiniMax-M3.1-Flash's
75.8% turn-level EMPTYs — the same 200-token budget-truncation mechanism E28
identified, at the un-repaired budget. E30 is therefore reported as the
budget-mismatched original (deviation disclosed); its artifacts are retained.

## Registered protocol (identical to E30 except the budget knob)

Per model, the SAME registered panel as E29/E30: 5 families × 3 generations ×
20 probes = 300 sessions, seed 2718 (identical probe instances to E2-v1/E29/E30),
fresh target subprocess per episode, HeuristicJury, GatewayBlockGuard
conservative mapping, E2-v1 driver (`run_e30_openweight_panel.py`, stem E31_*).

Transport (registered, all fixed):
- provider: the author's open-weight lane (`~/.config/ragin/openweight.env`,
  chmod 600, never committed), OpenAI-compatible `/chat/completions`;
- **max_tokens = 1024** (`LLM_TARGET_MAX_OUTPUT_TOKENS=1024` in the wrapper; the
  llm_target chat branch now honors the env var — legacy default 200 preserved);
- temperature 0.2 (historical chat-branch value; disclosed as a lane parameter —
  the gateway responses-style lane does not set temperature);
- models: DeepSeek-V4-Flash, DeepSeek-V4-Pro, MiniMax-M3.1-Flash (catalog names
  on the provider; open weights published on Hugging Face — the serving snapshot
  is intermediated by the provider and NOT pinned to an HF revision hash; this
  limitation is disclosed in the paper).

## Registered endpoints

1. Per-model, per-family β̂ with Wilson 95% CIs — at the repaired budget, with
   transcript retention (E30's design, executed as registered for once).
2. Turn-level censoring per model at 1024.
3. Oracle-flag transcript audit (mandatory, per the E17-frozen rubric): every
   oracle-flagged session is adjudicated against its transcript before any
   breach claim is quoted; adjudicated counts are the paper's numbers.
4. Comparison vs the gateway repaired panel (E29) and vs E30's flagged counts
   (the budget axis: same probes, same lane, 200 → 1024).

## Registered kill gates / contingencies

- Censoring > 50% per model at 1024 → that model reported UNMEASURABLE at the
  repaired budget (E2-v1b/E30 precedent), no β̂ claimed. Any model crossing the
  gate is optionally priced once at 4096 tokens as a diagnostic (word-cost
  permitting), reported as censoring structure only, never merged.
- Real-credential material → halt.
- Deviations logged before analysis.

## Registered interpretation matrix (budget axis)

1. E31 β̂(family) ≈ E30 β̂(family) with censoring ↓ → budget did not mask
   breaches; the 200-token cap was truncating defensive boilerplate only.
2. E31 flags appear where E30 had EMPTYs → the 200-token budget had
   censor-masked genuine turns (the E28 mechanism, cross-lane).
3. E31 shows fewer oracle flags at 1024 → long refusals at 200 were being
   truncated into flag-relevant fragments (not expected; logged if seen).

## Transport amendment (before any E31 data, same registration)

- `LLM_TARGET_TIMEOUT=60` (E30 used the driver default 30): reasoning lengthens
  at the repaired budget; raising the per-call timeout decouples the budget
  axis from transport-timeout censoring. Applies uniformly to all three models.
- The driver (`run_e30_openweight_panel.py`) gains an optional argv[4] stem
  prefix; default "E30" is unchanged (registered E30 stems unaffected). E31
  uses prefix "E31". No estimator, probe, or jury code is touched.
