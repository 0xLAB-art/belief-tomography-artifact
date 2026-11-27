# Dwell-Time Impact of Jev Kind-Aware Deception — LLM Replay Report

**Question:** Does injecting Jev's `attack_kind` signal into Hisoka's deception prompt keep simulated attackers engaged longer (dwell time) and expose more bait?

**Date:** 2026-09-20 · **Artifacts:** `results/jev_dwell_replay_llm.json` (+ per-family `results/jev_dwell_replay_llm_*.json`)

---

## Verdict (honest, up front)

1. **Dwell time: no measurable improvement.** Clean paired delta = **34 → 33 turns** across 5 error-free family pairs (−1 turn, noise). Kind-aware guidance did **not** keep the simulated attacker in the box longer.
2. **Bait exposure: positive signal.** Bait markers surfaced to the attacker rose **4 → 9 (+125%)** with kind-aware guidance — the guidance makes Hisoka answer recon convincingly and seed more touchable surface. n=5, no statistical power, but directionally supports the design intent.
3. **The real finding: response consistency, not deception style, is the binding constraint.** In *both* arms, nearly every leave reason cites **inconsistent fictional filesystem state** ("`/var/tmp` listing changed between identical commands", "contents differ across turns"). A cautious attacker — simulated or real — reads inconsistency as a trap signal. Fixing consistency is higher-leverage than any prompt-level deception strategy.

## Setup

- **Closed-loop replay:** LLM attacker (`deepseek-v4.1-flash-free`) follows each real Cowrie family's recorded playbook, then improvises or leaves; Hisoka (LLM-backed, `gemini-2.5-flash-free` via apmix) answers each command.
- **A/B:** baseline = persona prompt only; treated = persona + Jev attack-kind guidance (recorded assessments from `results/jev_real_logs_eval.json`). Same narrative-sanitized attacker context in both arms.
- **Verification gates added after two failed designs:**
  - **Canary gate** — nonce-echo probe proves the Hisoka LLM path is live before any run (an earlier "gateway" deceiver silently template-fell-back: `glm-5.3-flash-free` 404s on apmix, and the A/B was vacuous — 18/18 byte-identical responses).
  - **Path instrumentation** — every artifact records gateway vs template calls. This run: **87 gateway / 2 template (97.8% LLM-backed)**.
  - **Narrative sanitizer** — apmix's upstream filter 502s on imperative-`cat`+sensitive-path combinations; the attacker LLM's context is rendered as a past-tense, redacted narrative *identically in both arms* (fairness preserved; raw transcript stays in Hisoka's own inputs).

## Per-family results

| Family | Kind | Base turns | Treated turns | Bait b→t | Notes |
|---|---|---:|---:|---|---|
| enumeration_bot | scanning | 10 | 9 | 1→3 | clean pair |
| shadow_read | scanning | 5 | 2 | 0→0 | **treated arm cut by attacker-LLM 502 — not a real leave** |
| nmap_recon | scanning | 10 | 9 | 1→4 | clean pair |
| cloud_metadata_ssrf | scanning | 3 | 5 | 1→1 | clean pair |
| exfil_implant | exploit | 5 | 4 | 1→0 | clean pair |
| persistence_implant | persistence | 6 | 6 | 0→1 | clean pair |
| lateral_pivot | scanning | 10 | 3 | 0→0 | **treated arm cut by attacker-LLM 502 — not a real leave** |
| **Totals (all 7)** | | **49** | **38** | **4→9** | totals inflated by 2 invalid treated arms |
| **Totals (5 clean pairs)** | | **34** | **33** | 4→9 (see per-row) | the honest paired comparison |

All sessions ended in an early `LEAVE` (max 12 turns never reached); no leave before turn 3 in any valid arm.

## Why the template-mode A/B was discarded

`results/jev_dwell_replay.json` (template Hisoka) is **invalid as an A/B**: the Jev guidance is injected into the LLM prompt, and template mode never calls the LLM — so "treated" responses were byte-identical to baseline (verified 18/18). Its ±turn deltas were pure sampling noise. Kept on disk for provenance only; superseded by this run.

## Caveats

- **n=7 families, 5 clean pairs** — zero statistical power for the dwell delta; the bait-exposure direction is suggestive only.
- **Two treated arms terminated by infrastructure** (attacker-LLM 502), not by the attacker's decision; excluded from clean totals.
- **Simulated attacker ≠ live attacker.** DeepSeek-following-a-playbook is a reasonable cautious-attacker proxy, but leave thresholds are its own, not a human's.
- **2/89 Hisoka responses** fell back to templates despite the canary (post-retry path).
- Bait-marker counting is lexical; for the kinds actually run (scanning/persistence) the guidance text contains no marker words, so the treated-vs-baseline bait delta is not prompt leakage — but `exploit` guidance contains "staging" and would contaminate that kind's count in future runs.
- gemini-2.5-flash-free at temp 0.7 regenerates fiction per turn without a shared state ledger → the inconsistency the attacker keeps detecting is partly **model sampling**, partly missing session-fact persistence.

## Recommended next steps (in order of expected leverage)

1. **Session-consistency layer for Hisoka** — sticky per-session filesystem fiction (same listing for the same command within a session; persistent timestamps/paths). Directly targets the #1 leave reason in both arms. Then re-run this A/B: only on a consistent fiction can deception *style* show its effect.
2. **Re-run this A/B with n≥3 seeds per family** and only error-free pairs, to put error bars on the bait-exposure signal.
3. Consider feeding Jev severity (not just kind) to modulate bait richness for high-severity sessions.
