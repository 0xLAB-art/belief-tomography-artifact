# Verifier Third-Family Red-Team — Results & Fix Backlog (W2 input)

**Model:** `meta-llama/llama-3.3-70b-instruct` (Meta dense family — the planned
third author family from `THIRD_AUTHOR_RUN_PLAN.md`, distinct from deepseek MoE
and the apmix house model).
**Artifact:** `results/verifier_redteam_live_llama33_best.json` (94 cases × 3
repeats = 226 scored drafts; 56 cases hit a mid-run `402 Payment Required` on
OpenRouter credits and need a re-run pass to complete the matrix).

## Headline (breadth claim update)

| Metric | deepseek (author 1) | space-bunny (author 2) | **llama-3.3-70b (author 3)** |
|---|---|---|---|
| Drafts | 236 | 261 | 226 (partial: 402) |
| Precision | 1.000 | 0.995 | **0.886** |
| Recall | 0.931 | 0.943 | **0.876** |
| Category agreement | 0.988 | 1.000 | **0.840** |
| Unstable cases | — | 0 | **37** |

**The breadth claim ("defect surface is author-independent, exact surface
forms are not") now has real stress evidence:** llama's stronger instruction
following produces natural-language defect shapes the regex surface does not
cover (`C-user-drift`, `D-v14d-verb-inverted` as *misses*) AND pushes benign
negatives into rejection (`C-neg-*` remention probes as *false positives*).
Both directions are the expected author-dependence of the *surface forms*; the
verifier's decision procedure holds (degenerate 1.0/1.0, no crash, no
misattribution), but per-check precision/recall degrade vs the house models:
consistency is the weakest check (R 0.849 / P 0.718).

## Fix backlog (W2 audit→fix→lock, priority order)

### P0 — consistency check hardening (11 FPs, 5 misses)
The consistency check is the precision bottleneck. The `C-neg-*` family
(*re-mention of pinned values in benign contexts*, `ports-unstable`,
`system-entity`) is rejected when it should pass — the extractor/contradiction
logic treats *co-occurrence* as *contradiction*. Fix direction: require value
*divergence*, not mere presence-of-similar-value; add the normalization
contract cases to the offline suite first (`scripts/verifier_redteam_cases.py`),
then fix, then re-lock the offline 1.0/1.0 before touching the live stratum.

### P1 — danger-check tell vocabulary (14 misses, mostly D-* "tell" shapes)
Llama authors tells as fluent prose (`v14d verb-inverted`, `v19b journals-verb`,
`v7 curly-refusal`) that evade the pattern list. Two-part fix:
1. extend the tell lexicon with the verb-inverted / research-apology shapes
   harvested from the missed drafts (they are persisted in the artifact
   `per_case` texts), and
2. add an instruction to the danger gate: refusal-adjacent *style* without
   refusal *content* is a tell only when combined with hedging markers —
   avoid re-breaking `D-neg-*` benign cases (currently 5 FPs there too).

### P2 — identity-check edge shapes
`I-v16-whoami-no-ctx` and `I-whoami-suffix-prompt` miss when the draft embeds
the answer in prose (`"you are currently logged in as the root superuser"`).
Fix: extract the *effective user* from prose patterns instead of requiring the
canonical `uid=` shape on `whoami` (keep strict shape for `id`).

### P3 — instability handling (37 unstable cases)
Instability is *draft-side* variance, not verifier flapping, but the paper must
report it honestly. Add per-case stability to the §VI-C table and state the
boundary: "third-family drafts vary in surface form; the verifier holds the
decision invariant (no misattributed rejections), with per-check P/R floors
achieved after the W2 fixes."

## Repro notes

- OpenRouter credits exhausted mid-run → `--only` re-runs are free to resume;
  merge completed cases back via the checkpoint before re-running the missing
  56.
- Do NOT copy the llama artifact onto
  `results/verifier_redteam_live.json` — that path is the canonical
  space-bunny artifact checked by `scripts/verifier_redteam_check.py`
  (47 checks). Third-family artifacts keep their own filenames.
- Alternates probed and ready: `mistralai/mistral-small-3.1-24b-instruct` (200),
  `qwen/qwen-2.5-72b-instruct` (200) — a fourth family is cheap if the
  breadth claim needs more mass.
