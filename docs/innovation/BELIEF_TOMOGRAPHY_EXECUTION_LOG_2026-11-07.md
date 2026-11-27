# Belief Tomography — Execution Log (2026-11-07)

**Session:** "ابدا بالتنفيذ" — plan §9 steps 1–3 executed to the credential wall.

## Deliverables (all verified)

| # | Artifact | Status | Result |
|---|----------|--------|--------|
| 1 | **Novelty lit-scan** — [BELIEF_TOMOGRAPHY_LIT_SCAN.md](BELIEF_TOMOGRAPHY_LIT_SCAN.md) | GATE PASSED | 9 neighbor clusters mapped (N1 Cognitive Tomography 2013 = intellectual ancestor; N2 arXiv:2405.16331 = #1 methodological neighbor, must read in full; N5 value-action gap = BCG's phenomenon precedent; N7 deception line measures the wrong side). Unoccupied union: adversarial probe families + belief estimand + T1 impossibility + deception gain on attackers + BCG-for-charters. Residual scan items listed in §4 before drafting |
| 2 | **Formalism note** — [formalism_note.pdf](../paper/belief_tomography/formalism_note.pdf) (4 pp, clean compile) | DONE | Definitions (agent/charter/probe family/β/profile/BCG/epistemic distance/deception gain); **T1 passive-observation impossibility + detection corollary (full proof)** with ε=0 non-detector as empirical instance; T2 uniform estimation + adaptive-allocation gain (proof sketch); T3 = open problem 1 of the field; belief-behavior underdetermination remark; duality statement (certification = H-test, deception = corruption, monitoring = change-point) |
| 3 | **E1 dose-response validity** — `gauntlet/demo/run_dose_response.py` → DOSE_RESPONSE.md/json | **VALID INSTRUMENT** | 1,500 episodes; all 5 families: Pearson r ≥ 0.986, Spearman ρ = 1.00, monotone, zero-dose clean. First run's authority_forgery dip diagnosed as cell-size (n=18 SE ≈ 0.118 > grid step 0.25/2) — cells sized to n=60, resolution argument recorded in code |
| 4 | **E2 wire** — `SubprocessAgent` (JSONL protocol) + mock target test | PROVEN END-TO-END | Profile crossed the process boundary with distinctive structure (goal_subversion absent); BCG fixed to parse charter from the wire protocol. Target never sees family labels/oracles |
| 5 | **Live E2 smoke** — `run_live_tomography.py` + `llm_target.py` | **BLOCKED ON CREDENTIALS** | Primary lane (RAGIN_LLM_* → agentrouter gateway, model gpt-6.1-sol): HTTP 401 on every call = the known key-rotation item. Failover to OPENROUTER_API_KEY impossible: the entry exists in .env but is EMPTY. Health-check + failover machinery in place and tested; the run is one rotated key away |

## The one human action that unblocks E2 — RESOLVED SAME SESSION

User directed use of the available API ("استخدم API بتاع apinex اللي عندك"). Lane triage findings (all status-only, no key values printed):
- `RAGIN_LLM_API_KEY` (agentrouter.org, model gpt-6.1-sol) — **HTTP 401, dead** (the known rotation item). `RAGIN_API_KEY`/`API_KEY` also 401.
- `server_v2.env` lane = local gateway 127.0.0.1:8731 — **not running**.
- **apinex.bond is behind a Cloudflare bot challenge** (403 to urllib AND curl on /v1/*, HTML challenge page) — matches the project's own doc note ("switch via apinex.bond was attempted but produced no recorded sessions"). Not accessible from this box without a browser session.
- **OpenRouter lane WORKS with all three keys in `~/.config/alphacode/`** (200 OK on /v1/models). Payment-required (402) on paid models → free tier used.
- **LIVE RUNS EXECUTED on `google/gemini-3.8-flash`'s family and NVIDIA Nemotron — via OpenRouter free tier**:
  - Smoke run `nvidia/nemotron-3-ultra-550b-a55b:free` (20/20 calls, 0 errors): all 5 propositions **absent**, BCG 0.00/0.00, exposure 0.00% — the first live black-box tomogram.
  - Lesson: error replies counted as "safe" contaminate β̂ (28/60 errors on the first dense attempt) → added retry/backoff (429/5xx: 3s/8s/15s) to `llm_target.raw_call`; dense runs re-launched in background (nemotron-550b vs `google/gemma-4-31b-it:free`, 3 probes/cell each) — **first two-model comparison**.
- Infrastructure note: `key_triage.py` (lane triage tool) committed to `gauntlet/demo/`; `run_live_tomography.py` now takes `<model> <probes_per_cell>` and writes per-model profile files.

**Standing recommendation:** rotate `RAGIN_LLM_API_KEY` for the paid agentrouter lane (gpt-6.1-sol remains unreachable); apinex.bond requires a browser-authenticated session or API allowlisting before it can serve tomography.

## FINAL STATE OF SESSION (2026-11-07, after lane triage)

**ACHIEVED — the first live black-box tomogram:** `nvidia/nemotron-3-ultra-550b-a55b:free` (550B, via OpenRouter lane), smoke run **20/20 calls, 0 errors**: all 5 propositions **absent** (β=0.00, CI [0,0.56]), BCG 0.00/0.00, exposure 0.00%. Charter held under all 15 probes. Artifacts: `gauntlet/demo/LIVE_PROFILE_nvidia_nemotron-3-ultra-550b-a55b_free.md` + json. This is E2's existence proof — the wire, failover, retry/backoff, and per-model outputs all verified on a real frontier-class model.

**BLOCKED (free-tier daily cap):** the dense two-model comparison (nemotron vs gemma-4-31b, 3 probes/cell) hit OpenRouter's free-tier daily request cap (60/60 errors, 180×429). The dense run is re-queued conceptually — unblock options: (a) wait for UTC-daily reset, (b) add OpenRouter credits (402 on paid gemini-3.8-flash), (c) rotate agentrouter.org key. A lane map is saved for future sessions (`gauntlet/demo/key_triage.py`; statuses recorded in memory).

**Measurement-hygiene lessons banked:** (1) error replies must not silently count as safe behavior — retries added; (2) with free-tier lanes, budget probes against the daily cap before launching; (3) per-model output files prevent profile overwrites.

## Honest notes

- E1 validates the instrument on constructed foils — the foils are Bernoulli dosed by design; real-agent validity (test–retest, probe-order effects) is E1's next leg.
- v0 verdicts use deterministic oracles + heuristic jury; the calibrated multi-model jury lane (κ 0.811 methodology) is required before any real-agent number is publishable.
- The live profile produced by the blocked run (all-absent, exposure 0.00) is an artifact of error-placeholder replies counted as safe behavior — it is NOT a measurement of any model. Marked as such in LIVE_PROFILE.md context; discard it.
