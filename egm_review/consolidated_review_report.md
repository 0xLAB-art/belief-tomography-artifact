# Consolidated EGM Review Report — RAGIN Project

**Elephant-Goldfish Model review, uninterrupted full flow (Stages 5, 6, 7, 9; Stage 8 folded into this synthesis).**
**Target:** `paper/main.tex` (2144 lines) as the project's authoritative design+results artifact, cross-checked against the live codebase `RAGIN-Retrieval-Augmented-Honeypot-Intelligence/`.
**Reviewers (Goldfish, fresh-context):** zoom-out, comprehension, design critic, structural validator, style editor, implementation-readiness, codebase-details auditor.
**Date:** 2026-11-05

## Raw findings across stages

| Stage | Reviewer | 🔴 | 🟡 | 🟢 | Total |
|---|---|---|---|---|---|
| 5 | zoom-out | 3 | 10 | 5 | 18 |
| 6 | comprehension | 4 | 12 | 12 | 28 |
| 7 | design critic | 5 | 11 | 4 | 20 |
| 7 | structural | 2 | 8 | 7 | 17 |
| 7 | style | 7 | 14 | 12 | 33 |
| 9 | implementation-readiness | 4 | 8 | 7 | 19 |
| 9 | codebase-details | 4 | 7 | 5 | 16 |
| | **Raw total** | **29** | **70** | **52** | **151** |

## Consolidated action items (deduplicated)

### 🔴 BLOCKERS — 8 consolidated (must resolve before any submission)

**C1. The paper claims what was not measured: the deception loop is not wired to the external attack surface.**
Sources: design B1, zoom-out #1. `main.tex:245-253` admits it; abstract/Fig.3/Table 1 sell the opposite. Every dwell/engagement/deception claim is against driver-authored sessions, and 86.7% LLM timeouts mean the closed loop cannot physically close. → Re-scope the contribution to what exists: RAG-grounded CTI analysis pipeline + offline deception-capability study; mark the C3→attacker edge as not-wired in figures.

**C2. Provenance failure: the paper cites artifacts that are wrong, missing, or self-repudiating.**
Sources: codebase F-1..F-5, impl-readiness R1, zoom-out. Concretely:
- All Table `tab:benchmark` numbers live in `live_benchmark_audited.json`; the cited `live_benchmark.json` holds a *different* 30-query run (`main.tex:1247,1272,2018`).
- Cowrie table (n=6, 0.317, Δ+0.380) contradicts on-disk `cowrie_comparison.json` (n=2, 0.45, Δ+0.247).
- LLM-panel headline 2.51/κ=0.425: the cited `human_eval_scored/consensus.json` computes to 1.913 and carries a "Do not cite this directory" correction; the corrected rebuild is not committed; 3.06 aggregate doesn't recompute from the paper's own components ((4×2.83+4.2)/5=3.104).
- Five cited files/scripts do not exist: `results/rag_prompt_controlled_ablation.json`, `results/redteam_personas.json`, `scripts/bootstrap_cowrie_ci.py`, `scripts/deterministic_artifact_safety.py`, `ragin/gateway/pii_redactor.py`.
→ Mechanical but mandatory: re-point every path, commit or retract.

**C3. The PII/privacy specification describes code that does not ship.**
Sources: codebase H2, impl-readiness R1. Paper: HMAC-SHA256 + per-deployment key + 16-bit per-record salt in `gateway/pii_redactor.py`. Actual (`ragin/utils.py:20-32`): plain SHA-256 with a *committed* static default salt `"ragin-ip-v1"`; cleartext attacker IPs appear in committed docs. Correctness + ethics-statement problem.

**C4. Unreconciled headline numbers (the paper contradicts itself).**
Sources: comprehension R1-R4, style blockers, design N1/N3, impl-readiness Y3.
- TTP counts for the same 30 sessions: 31 unique vs 13 vs 5 (three incompatible framings).
- Chrollo described three incompatible ways: 4-class skill predictor vs Algorithm 1's binary P(malicious) vs Hisoka's rule-based tier assignment; "five personas" vs 3 tiers vs 4 classes.
- Latency multiplier: stated 158×/160×; 160,603/2,650 ≈ 61×.
- Trees: 500 (line 595) vs 200 (Algorithm 1). Corpus: 780,000+ vs 780,600 vs on-disk 75,151.
- Dwell: 12,636 ms (paper `tab:kpis`) vs 7,286.6 ms (`live_benchmark.json`) for "the same" sessions — and the campaign KPIs (261 queries, 44 auth, dwell stats) have **no data artifact at all**; the repo itself flags this axis "re-deployment pending".
- "Top-15 feature importances" for a 10-feature model.

**C5. Composite effectiveness 0.697 is undefined and conflated with IQS; the deception suite it headlines fails at 18.3%.**
Sources: zoom-out #3, comprehension R4, design M7, impl-readiness Y5, style. Score ≥ 0.3 lexical criterion undefined; wrong table cross-reference in Fig. 4 caption; per-suite reporting shows Persona-Realism (the actual novel capability) is the weakest measured suite while the composite is dominated by CTI suites Cowrie cannot even attempt.

**C6. Chrollo's circular evaluation: trained and validated on sessions generated from its own feature-defining pattern families.**
Sources: design B3, zoom-out. The 0.89 accuracy measures generator self-agreement; the 0.85 escalation gate inherits it. Must be a first-class limitation + one real-corpus OOD probe.

**C7. Latency economics make "real-time interactive deception" infeasible on the evaluated path — and the design omits its own dominant cost.**
Sources: design B2/B5, zoom-out #2. Live ~160.6 s vs 2,650 ms designed budget; 86.7% OpenRouter timeouts vs the paper's own red-team "timing analysis" tell; the corrective-RAG LangGraph loop (the actual dominant term) is absent from Table 4 and the complexity analysis. The designed budget describes a configuration ("cached warm retrieval, local LLM endpoint") never deployed.

**C8. Venue/template mismatch: the manuscript is Elsevier `elsarticle`, not IEEE S&P 2027 format.**
Sources: structural blocker, comprehension, style. CrediT/competing-interest backmatter, one-column layout. Also: Ethical Statement buried unnumbered after Acknowledgments; Threat Model misplaced as a Related Work subsection; duplicated bibitem ("LLM in the Shell" cited as two works); Figure 3 cited before Figure 2.

### 🟡 MAJOR — 14 consolidated

1. **Reproducibility gap for the LLM stack** (impl-readiness R2/R3): no model ID (code pins `moonshotai/kimi-k3-free` via a tokenrouter proxy the paper calls "OpenRouter"), no temperature (code: 0.3), no prompts (the ablation's manipulated variable!), no filler-corpus provenance for Arm-C.
2. **Chrollo training recipe absent** (impl-readiness R4): no dataset source, label provenance, split, RF hyperparameters, or classifier accuracy.
3. **Retrieval stack misdescribed** (codebase F-8, A6/A7): code uses `IndexFlatIP`, paper says HNSW twice; fusion α=0.7 vs code default 0.25 with conflicting docstring.
4. **Infrastructure arithmetic doesn't close** (design B4): 780.6k×768×4B ≈ 2.4 GB dense index + 8 services on 2 vCPU/3.7 GB; no quantization discussion.
5. **Attacker-writable Mem0 memory with no poisoning defense** (design M4) — second-order persistent prompt injection; also the claimed 30-day idle window is not implemented (codebase F-7).
6. **Escalation gate starves sub-threshold sessions** (design M2): s ≥ 0.85 gate leaves everything else as a passive honeypot.
7. **Threat model excludes the adaptive adversary while the whole artifact is public** (design M5) — every threshold and SafeFallback string is in the repo.
8. **No LLM-honeypot baseline** (design M8): Arm-C exists (3-vs-0) and should be a headline baseline; without it the +0.380 delta mostly measures "has an LLM".
9. **Statistical power** (design M9, impl-readiness Y7): headline delta over 6 Cowrie sessions, no CI over sessions; bootstrap resampling unit unspecified.
10. **Table 1 capability matrix overstates evaluation** (design M6): κ=0.425 single-run LLM judge ≠ "supported and evaluated"; poisoning "defense" is one unit test.
11. **Cost-exhaustion defense is per-IP limiting + fixed cap** (design M3): no $/session model, no attacker/defender asymmetry analysis — for a honeypot-economics paper.
12. **Campaign KPIs unverifiable** (codebase F-9/F-10): tactic-table per-row distribution and campaign aggregates exist only as response-letter prose.
13. **Validation harness cannot exercise the real failure mode** (design M10): offline unit tests only; no chaos test against the live inference path.
14. **Corpus composition** (design M11): 64% IP-reputation records, useless for command-level grounding; no per-source retrieval precision.

### 🟢 NITS — 12 consolidated
Typo cluster ("steprequired", ").Upon", "regimes,and", doubled-colon title); kNN imputer claimed but nonexistent; Mem0 pin unbounded + backing LLM unstated; Redis TTLs unstated; Python 3.11 vs >=3.10/3.12; test-count snapshot (1,098 vs current 1,285) needs date-stamping; dangling "open-sourced at RAGIN" reference; complexity claims loosely stated (O(N) BM25, O(log N) HNSW without build/memory terms); self-praise lexicon ("candid/honest/inflated" grading its own virtue — 7 sites); 6 sentences >40 words + passive chains; undefined-at-first-use terms (Chrollo/Don/Hisoka at line 176, Arm-C, ECE, CV, OOF, honeytokens); "held-out corpus"/"screening stage" pointing to unnamed repo locations (200+ unindexed scripts).

## What the reviewers confirmed as solid

- Every number in Table `tab:benchmark` and the audit breakdown re-derives **to the digit** from `live_benchmark_audited.json` (218 queries, 91.9/100/18.3, 22/2/5/189, 160.6 s, 82/31).
- Chrollo/Hisoka/gateway implementation claims (features, scaler, model file, persona manager, circuit breaker, defense layer) match the code closely.
- Structural hygiene is mechanically clean: 132 \refs resolve, zero duplicate labels, all 47 bibitems cited, all figures exist.
- The paper's candid negative-result accounting (10.1% grounded, falsified external-deception claim) is repeatedly named its best feature — and should be the spine, not damage control.
- External artifacts verified: public GitHub repo, resolving Zenodo DOI, Apache-2.0.

## Recommended fix order

1. C2+C3 (provenance + PII) — mechanical, highest leverage, ~a day of artifact reconciliation.
2. C4 (number reconciliation) — pick one value per fact, source every table row from a committed JSON.
3. C1+C7 (framing re-scope) — decide: analyst-facing CTI pipeline paper vs interactive-deception paper; the repo's own `sp2027-sections/design.tex` "Intelligence Ladder" framing already contains the honest version and the missing scripted-template baseline rung.
4. C5+C6 (metric definitions + circularity limitation) — definitions and one paragraph each.
5. C8 (IEEE template migration + structural moves) — done once, before the next compile.
6. Majors in the order: 1, 2, 3, 8 (cheap, definition-level) → 9, 10 (analysis reruns) → 4, 5, 6, 7, 11, 12, 13, 14 (design-section additions or explicit limitations).
