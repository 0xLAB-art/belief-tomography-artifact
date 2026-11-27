# E30 — Open-Weight Panel (verifiable serving identity)

**Registered:** PREREGISTRATION_E30_OPENWEIGHT_PANEL.md (before data;
kimi→MiniMax deviation 1 logged pre-data). **Design:** the E2-v1/E29
driver, stem E30_*; 3 models × 5 families × 3 generations × 20 probes =
300 sessions each, seed 2718 (identical probe instances to E2-v1/E29),
repaired 1024-token budget; 2026-11-22.

| model | pooled β̂ | per-family highlights | censoring | status |
|---|---|---|---|---|
| DeepSeek-V4-Flash | **20/300 = 0.067 [0.044, 0.101]** | authority 0.067, echo 0.067, goal 0.017, state-dec **0.183 [0.106, 0.299]**, exfil 0 | 2.3% FAIL | measurable |
| DeepSeek-V4-Pro | **64/300 = 0.213 [0.171, 0.263]** | **echo 0.633 [0.507, 0.744]**, state-dec **0.400 [0.286, 0.526]**, authority/goal 0.017, exfil 0 | 19.8% FAIL | measurable |
| MiniMax-M3.1-Flash | — (0/300 measured turns) | — | **75.8% EMPTY** | **unmeasurable** (over the registered 50% bar) |

## Reading

1. **Charter-holding is a spectrum, not a constant**: the repaired
   gateway panel (E29) measures 0.017 pooled; the open-weight models
   measure 0.067 and 0.213 under IDENTICAL probes.
2. DeepSeek-V4-Pro's epistemic-echo rate (0.633) is the highest measured
   field rate in the program — the model surfaces/echoes injected
   environment content at rates the gateway models never approached.
3. MiniMax-M3.1-Flash's 75.8% turn-level empty-rate **reproduces the
   budget-truncation mechanism E28 identified** — now attributed to a
   longer-reasoning model at the standard 1024 budget. Reported
   unmeasurable per the registered gate (the E2-v1b retest precedent):
   no β̂ claimed.
4. Every open-weight number is reproducible by any reader with the
   endpoint — the serving identity is verifiable, unlike catalog names.
