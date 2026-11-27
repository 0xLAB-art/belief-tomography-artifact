# S&P 2027 Panel Round 3 — post-v3+fresh+ethics (2026-10-31)

| Judge | Persona | Verdict |
|---|---|---|
| A | Security Systems | weak rejected |
| B | Statistician | **rejected** (ethics absence + estimator inconsistency — both now FIXED) |
| C | Novelty Hawk | weak rejected |
| D | Statistician (re-review) | weak rejected |
| E | Methodology Advocate | **Borderline** (closest yet to accept) |

## Judge-caught defects — ALL FIXED (commit fe7e96ff)
1. Benign false-refusal rate 4/8 out-of-sample was selectively omitted → now disclosed in §5.2
2. Fresh no-RAG degenerate control (all 0.0) was framed as replication → withdrawn to honest "undiagnosed, version of record = archived"
3. v3 CI resampling unit disclosed (persona-stratum percentile, coarse support)
4. Ethics contradictions (closed-network vs public endpoint; no-IRB rationale) → repaired with no-IRB rationale + aggregate-only handling of the 2 external-attacker sessions
5. grok-4.7-free consensus judge named in provenance table

## The structural ceiling (unfixable before Nov 17, stated by all 5)
- No human labels anywhere (all 5); minimal fix identified: 40-case human-anchored stratified subsample at the benign/recon boundary (E's revision ask)
- Self-play throughout, free-tier, n=10 confirmatory, tailnet-only field
- Injection/poisoning declared-not-evaluated (containment argument present, unmeasured)

## Verdict trajectory across rounds
Round 1 (pre-v3): 4× weak rejected
Round 2 (post-v3+cross-family+oos): 3× weak rejected, 2× weak accepted
Round 3 (post-fresh+ethics+fixes): 3× weak rejected, 1× rejected (ethics-driven, now fixed), 1× Borderline — the Borderline is the highest grade yet from the hardest persona set
