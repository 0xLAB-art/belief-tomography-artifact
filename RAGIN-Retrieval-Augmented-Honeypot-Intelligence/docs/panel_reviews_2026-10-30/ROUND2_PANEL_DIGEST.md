# S&P 2027 Hard Panel Round 2 — Post-v3 Confirmation (2026-10-31)

All five judges reviewed the CURRENT draft (with v3 confirmatory, cross-family jury, out-of-sample probe integrated).

## Verdicts

| Judge | Persona | Verdict |
|---|---|---|
| J1 | Measurement Skeptic | weak rejected |
| J2 | Systems Veteran | weak rejected |
| J3 | Novelty Hawk | weak rejected |
| J4 | Statistician | **weak accepted** |
| J5 | Methodology Advocate | **weak accepted** |

## Panel consensus: what the v3 result changed
- J4 verified 12+ numbers digit-for-digit (including v3 Fisher, κ CI/LOO, cross-family κ, out-of-sample) — **zero mismatches**.
- J5: "the one claim that survives the label-validity problem entirely" (the v3 yield is a deterministic transcript extraction, judge-independent).
- J4's provenance catch (brain label said claude in the artifact header while the paper text said gemini — the gemini switch never recorded a session) **is now fixed** (commit e79868ca): claude-sonnet-5-5@beatapi is the actual confirmatory brain, per on-disk sessions; Amendment 2 (gemini) withdrawn with failed-launch record.
- J1/J2/J3 re-state the structural ceiling: no human labels, free-tier self-play, thin field, n=10 confirmatory — the same bar they set for ANY paper in this subfield. None of it is fixable before Nov 17.

## The one cheap, decisive revision ALL five converge on (J5's ask, endorsed by J1/J4):
**Re-score the 90-pair grounding ablation + 218-row campaign with the disjoint-family juror and report the headline effects under that independent labeler.** If +0.154 survives de-correlation, W1 collapses for J1/J5. Feasible: the packet and juror exist; ~120 gated calls.

## Convergent post-submission asks
1. v3 internal decomposition (bait-without-generation control) — R3's decisive ask
2. Injection-containment experiment (R2)
3. Minimal human-labeled subset (R1's price)
4. Artifact mirror at review time

## Fixed from this round
- 2 text-corruption bugs (garbled threat-model row, truncated labels sentence) — judge-caught
- v3 brain provenance corrected to claude-sonnet-5-5@beatapi (judge-4 provenance catch — the gemini switch never recorded a session; Amendment 2 withdrawn with record)
- grok-4.7-free consensus judge named in provenance table

## Open minors
- Mimosa triage, azure artifacts, key rotation, B0–B5 post-submission
