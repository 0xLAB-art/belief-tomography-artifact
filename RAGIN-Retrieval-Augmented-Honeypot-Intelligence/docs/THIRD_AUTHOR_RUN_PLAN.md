# Third-Author Run Plan — Verifier Red-Team Live Stratum

**Status:** READY TO EXECUTE (endpoint fallback wired and live-verified; OpenRouter key present)
**Scope:** one more author model through `scripts/verifier_redteam_live.py` on the 96-case canonical suite, then the audit → fix → lock loop that rounds 1–7 established.

---

## 1. Why a third author (the claim this closes)

The paper's breadth claim is currently two-authored: *"the defect surface is
author-independent, while the exact surface forms are not"* — supported by
deepseek (236 drafts, 7 rounds) and space-bunny (261 drafts, 1 pass) landing on
the same miss taxonomy and both reaching precision 1.000 post-fix. A third
author from a **different model family** tests whether that independence holds
beyond the free-apmix pool. Expected outcome either way is publishable:
agreement strengthens the claim; divergence maps new surface forms.

## 2. Model selection

**Primary candidate: `meta-llama/llama-3.3-70b-instruct` via OpenRouter** —
endpoint fallback already wired into the harness (`--base-url
https://openrouter.ai/api`, key fallback to `OPENROUTER_API_KEY`, live-verified
`200 OK` on 2026-09-26).

Selection rationale (family diversity over leaderboard rank):

| Axis | deepseek | space-bunny | llama-3.3-70b |
|---|---|---|---|
| Family | DeepSeek MoE | unknown/apmix house | Meta dense |
| Training lineage | distinct | unknown (house model, low transparency) | distinct, open weights |
| Refusal style seen | curly-quote boilerplate | house-style paraphrase | known to produce explicit policy sentences (tests class-E from a new angle) |

Sequenced alternates (run in order on provider error / catalog drift):

1. `mistralai/mistral-small-3.1-24b-instruct` — third family (Mistral), cheap
2. `qwen/qwen-2.5-72b-instruct` — fourth family (Alibaba), strong tool-output style
3. `google/gemini-2.0-flash-001` — only if the above are unavailable; closed-weights caveat for the provenance note

Probe each candidate with a 1-token call before committing the run (the apmix
drift incident — catalog listing models that 404 — is the precedent).

## 3. Budget (from measured run costs)

Per completed run of the 96-case suite at repeats=3 (~300 authoring calls):

| Item | Measured (deepseek full) | Basis |
|---|---|---|
| Wall clock | 20–40 min single process; ~7 min/slice × 5 slices with 520 s timeout | space-bunny prefix took 399 s for ~120 cases; slices resumable via checkpoint |
| Tokens | ~15–25k prompt + ~12–20k completion total | per-call ~60–90 prompt / 35–70 completion (authoring caps: 700 max_tokens) |
| Retries | +5–15% calls (finish=length burn + gateway 2-attempt) | observed in every run |
| Cost on OpenRouter | **≈ $0.03–0.08** for llama-3.3-70b at listed pricing; effectively free-tier scale | trivial; the binding constraint is wall clock, not money |

Hard caps written into the run procedure: abort if authoring_errors > 15
(transport collapse) or elapsed > 90 min (endpoint stall); checkpoint resumes
cost nothing (per-case partials are written before any case re-runs).

## 4. Execution procedure

```bash
cd RAGIN-Retrieval-Augmented-Honeypot-Intelligence
# 0. probe the chosen model (1 call, 10 tokens)
# 1. preserve current artifacts (already done for deepseek/space-bunny prefix;
#    re-tag the current post-fix space-bunny artifact before clearing)
cp results/verifier_redteam_live.json results/verifier_redteam_live_space-bunny-free.json
rm -f results/verifier_redteam_live_partial.json results/verifier_redteam_live.json results/verifier_redteam_live_2026*.json
# 2. sliced run (resume-safe; ~7 min per slice)
timeout 520 .venv/bin/python scripts/verifier_redteam_live.py \
    --model meta-llama/llama-3.3-70b-instruct \
    --base-url https://openrouter.ai/api          # repeat until summary prints
# 3. audit: FP + miss extraction (same jq-style probe as rounds 5–7)
```

## 5. Expected deltas (hypotheses, falsifiable)

| Metric | Prior (2-author range) | Expected for llama-3.3 | Rationale |
|---|---|---|---|
| Precision (pre-fix) | 0.994–1.000 | **0.97–1.00**; ≥1 new FP root plausible | new family → new adjacency/alias shapes; the FP roots so far (uid, adjective) were both second-author discoveries |
| Recall (pre-fix) | 0.942–0.943 | **0.88–0.95** | same suite, new surface forms; vocabulary travel is the established failure mode |
| Category agreement | 0.9875–1.000 | ≥0.95 | labels are robust across two authors already |
| Instability | 6–12 cases | similar | borderline shapes (shadow, secret-password) are author-agnostic |
| New canonical cases | +3–9 | +3–9 | rounds 6–7 each yielded 4–5; a third family should surface ≥1 alias/tell paraphrase neither author produced |
| Invalid drafts | 4–8 | 4–10 (refusal-to-author rate is family-dependent) | validity gate handles it |

**If precision < 0.97 pre-fix:** that is a *finding* (a family-shaped FP class
the two free-tier authors could not produce) — follow the established loop:
audit → root-cause → fix → precision-anchor case → regression lock. Never
accept a pre-fix number as final; the published metric is post-fix.

**If recall < 0.85 (gate fail):** classify misses into the existing taxonomy;
only novel classes are new findings — the taxonomy has been stable since
round 5, so a gate failure most likely means one author model produces a
localized paraphrase family, which strengthens (not weakens) the
author-independence claim.

## 6. After the run (checklist)

- [ ] FP/miss audit table (same extraction as rounds 5–7)
- [ ] fixes implemented with named findings (V24+), precision anchors included
- [ ] canonical cases appended; offline suite strict 1.000/1.000; full pytest
- [ ] C1 bench + determinism sweep re-run (the danger patterns touch the serve path)
- [ ] artifacts tagged: `verifier_redteam_live_<model>.json` for BOTH prior authors
- [ ] paper: census two-author → three-author numbers; `tab:livemiss` caption;
      artifact index row; conclusion draft count
- [ ] graphify update

## 7. Risks

- **OpenRouter free-model churn** — mitigated by the sequenced alternates + 1-token pre-probe.
- **Reasoning-model token burn** (apmix precedent) — authoring cap is 700; a model that burns it returns empty → validity gate counts it invalid, not a miss. If invalid > 15% of drafts, switch to the next alternate rather than raising the cap.
- **Content refusal on fake-secret authoring** — llama-3.3 is instruction-tuned and may refuse `AKIA…` authoring more often; the authoring prompt already authorizes "clearly FAKE ones of the same shape" and the validity gate excludes refusals. If a case goes N/A, the case-level sample shrinks — report `variants=N/3` honestly (precedent: 2/3 catches already appear in artifacts).
- **Checkpoint model-mismatch** — the resume loader keys on model; no cross-model contamination is possible (verified in code).
