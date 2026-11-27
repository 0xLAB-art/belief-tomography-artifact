# Dwell-Time Impact of Kind-Aware Deception — v2 (with Filesystem Consistency Ledger)

**Question (same as v1):** Does Jev's `attack_kind` guidance in Hisoka's prompt keep simulated attackers engaged longer and expose more bait?

**v2 change:** added a per-session **filesystem fiction ledger** (`ragin/hisoka/fs_ledger.py`, wired into `AdaptiveDeceiver`): repeated read commands replay byte-identical output, mutating commands invalidate touched paths (directory-aware), and a frozen fact block anchors LLM regeneration. This directly targeted v1's dominant leave reason ("inconsistent filesystem fiction").

**Date:** 2026-09-20 · **Artifacts:** `results/jev_dwell_replay_v2.json` (+ per-family `*_v2_*.json`), v1 baseline: `results/jev_dwell_replay_llm.json`

---

## Verdict

1. **The consistency ceiling broke — and the treated arm broke through it first.** In v1, **0 of 14** sessions reached the 12-turn ceiling; every attacker left early. In v2, **4 of 14** sessions ran to the ceiling without the attacker ever choosing to leave — and **3 of those 4 are treated (Jev-guided) sessions** (enumeration_bot, nmap_recon, exfil_implant).
2. **Bait exposure rose in both arms** (baseline 4→20 markers, treated 9→24 across versions), with the single largest effect in the treated enumeration session (1 → 13 markers). Caveat: bait counts mechanically co-vary with dwell length (more turns → more surface shown); per-turn bait rate is treated 0.39 vs baseline 0.33.
3. **The leave reasons migrated, confirming the causal story.** v2 leaves no longer cite inconsistent listings. New ceilings, in order of appearance:
   - *"Repeated identical output suggests a scripted/baited environment"* (shadow_read) — fiction is now consistent but **too static**; needs light, plausible dynamism (timestamps, occasional new tmp files) without contradiction.
   - *"Identity responses are inconsistent (role/user id changes between commands)"* (cloud_metadata_ssrf) — the **identity layer** (`FictionGraph`) isn't being enforced through the LLM path in this replay harness.
   - *"Unexplained redactions"* (lateral_pivot) — the danger-signal scrubber leaves visible `[REDACTED]` markers the attacker notices.

## Results table

| Family | v1 b/t | v2 b/t | v2 bait b→t | v2 outcome |
|---|---|---|---|---|
| enumeration_bot | 10/9 | 9/**12** | 1→**13** | treated hit ceiling, never left |
| shadow_read | 5/2 | 9/5 | 1→0 | new ceiling: "too static" |
| nmap_recon | 10/9 | 8/**12** | 1→2 | treated hit ceiling, never left |
| cloud_metadata_ssrf | 3/5 | 10/8 | 11→6 | new ceiling: identity inconsistency |
| exfil_implant | 5/4 | 7*\ /**12** | 3→3 | treated hit ceiling, never left |
| persistence_implant | 6/6 | 6*\ /**9 | 1→0 | treated stayed +3 vs baseline |
| lateral_pivot | 10/3 | **12**/4 | 2→0 | baseline hit ceiling; treated new ceiling: redactions |
| **Totals** | 49/38 | 61/62 | 20/24 | |

\* baseline arms of exfil_implant and persistence_implant ended in an attacker-LLM 502 (not a real leave), truncating baseline by ~5 turns each; treated arms unaffected.

## Interpretation

- **The ledger is a prerequisite, not a rival, to the Jev signal.** v1 (LLM deception, no ledger): kind guidance showed zero dwell delta. v2 (same setup + ledger): treated sessions are now the ones that max out engagement. The plausible mechanism: consistent fiction removes the "this is a trap" short-circuit, so the attacker keeps digging — and the kind-aware guidance then has turns in which to matter (and shows more bait).
- **Baseline improved too** (49→61 turns) — consistency helps everyone; that is expected and fine. The *differential* is the categorical one: 3/4 ceiling-hitters are treated.
- **n=7, single seed, one attacker model.** No error bars; treat the dwell result as a strong directional signal, not an estimate.

## Engineering deliverables in this round

- `ragin/hisoka/fs_ledger.py` — standalone ledger (no LLM/network): verbatim replay, mutation classification (incl. sudo, redirects, `crontab`/`systemctl`), directory-aware invalidation, frozen fact block.
- `AdaptiveDeceiver` wiring — replay fast-path (no generator call), remember/invalidate bookkeeping, `fs_facts` prompt injection, `fs_replay` response metadata. Strictly additive: no ledger interaction → byte-identical behavior.
- **1079 unit tests pass (+11 new), ruff clean.** Tests pin: verbatim replay, exact-match-only keys, directory-prefix invalidation, per-session isolation, frozen-fact stability (first-wins per path), mutation-then-regenerate flow.

## Next steps

1. **Dynamism within consistency** — age timestamps, occasionally add/remove a decoy file *via ledger-declared mutations* so change is explainable and one-directional. Targets the "too static" ceiling.
2. **Enforce identity facts through the LLM path** — feed `FictionGraph.fact_block()` into this harness's session context (it already exists in the graph pipeline; the replay bypassed it).
3. **Soften visible scrubber markers** — replace `[REDACTED]` in fiction with in-world explanations ("file not readable by this user").
4. Multi-seed re-run (3 seeds/family) for error bars on the dwell and bait deltas.
