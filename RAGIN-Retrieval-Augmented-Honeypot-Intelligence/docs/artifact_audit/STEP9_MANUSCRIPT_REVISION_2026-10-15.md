# Step 9 — Manuscript Revision From the Locked Claim Matrix (Audit Record)

**Date:** 2026-10-15
**Plan:** `docs/PAPER_REMAINING_STEPS_2026-10-14.md`, Step 9
**Status:** Revision complete; final working state uncommitted in the worktree (commit decision pending at audit time)

## Requirements audited against

- **Order.** Methods and evaluation first; then design/implementation, discussion/limitations, introduction/contributions, conclusion, abstract. Shipped/default path and optional research variants described accurately; Laya V2b, failed V3 adaptation, deterministic judge, new scorer, and V4 policy studies kept as separate experiment identities.
- **Outputs.** Updated `paper/main.tex` and included sections; generated tables/figures sourced directly from locked artifacts; correct analysis-versus-served channels; model/reference disclosure; result/exclusion chronology; architecture figure showing only implemented behavior as active; the full paper before adapting `paper/sp2027.tex`.
- **Gate.** Every quantitative statement linked to the claim matrix; nulls, failure/abstention rates, denominators, provider unavailability, reference dependence, and deployment scope remain visible; no general fold-down claim, no live Laya benefit, no field effectiveness from the existing descriptive studies.

## Committed revision

| Commit | Scope |
|---|---|
| `17aed58` — Step 9: revise manuscript from the locked claim matrix | `sections/evaluation.tex` (155 changed lines), `sections/introduction.tex` (131), `sections/conclusion.tex` (54), `sections/discussion.tex` (37); `docs/artifact_audit/experiment_registry.json` (+39), `docs/artifact_audit/artifact_manifest.jsonl` (+7) |
| `ace5944` — Step 9 (amendment): refine appendix, background, design, two-channel tables | `sections/appendix.tex` (37), `sections/design.tex` (34), `sections/two_channel_tables.tex` (8), `sections/background.tex` (1) |

## Working-tree revision pass (uncommitted)

- `paper/main.tex`: retitled `The Intelligence Ladder: Pricing AI Mechanisms in a Verified Deception Honeypot` → `Verified Generative Deception: Serving-Time Safety for LLM Honeypots`; document class `[journal]` → `[conference,compsoc]`; author block and biography replaced by `Anonymous Submission`; abstract rewritten to the serving-time boundary (grounding buys intelligence, verification buys safe serving, the deterministic floor absorbs provider failure). Title, class, and author block match the `paper/sp2027.tex` venue surface.
- `paper/references.tex`: bibliography deduplicated 61→56 entries. Removed `sladic2025` (exact duplicate of `valeros2024` — same LLM-in-the-Shell work, arXiv self-version), `bachl2021`, `farasat2024a` (already uncited), `farasat2024b`, `sharafaldin2018` (flow-IDS/dataset padding whose only textual use was one removed clause).
- `paper/figures/{grounding,ladder,results}.tex`: plotted values now resolve through `paper/figures/generated_values.tex` (new, untracked — must ship with any commit of these figure changes).
- `paper/sections/evaluation.tex` (staged): `\S\ref{sec:judge-role}` → `\S\ref{sec:jeveval}`; removes the last undefined-reference warning.
- Untracked additions: `paper/figures/generated_values.tex`, `paper/main_final.txt`, `paper/sections/sp_{appendix,evaluation,related,threat_model}.tex`, `paper/sp2027.pdf`.

## Citation repair (this session)

Four undefined citations (`sladic2025`, `bachl2021`, `farasat2024b`, `sharafaldin2018`) originated from the removed bibliography entries and lived in `sections/related.tex`. Repairs, each kept to the smallest defensible change:

1. **Deployment-shape sentence** (Honeypot and Honeynet Architectures): the multi-sensor/containerized-honeynet observation is now presented as part of the survey catalog ("…cloud-native deployment~\cite{lopez2024}, from multi-sensor platforms … to containerized honeynets …"); both dead citations dropped. `lopez2024` verified (external check) to cover container-based and cloud deception deployment — the survey catalogs deployment contexts, container decoys, and orchestration frameworks.
2. **"GPT-driven SSH bots" sentence** (Generative Models in Deception): `kouremetis2024` → `valeros2024`. The sentence describes a language model answering as a live shell, which is exactly the LLM-in-the-Shell work; `kouremetis2024` remains cited in its three native occurrences.
3. **Behavioral-profiling clause** (CTI and Behavior Analysis): removed "both intrusion detection and" plus the three IDS citations (no anchor supports the combined claim; padding), keeping `lekssays2025` for honeypot-facing classification.

**Post-repair invariant (verified by exhaustive cross-audit):** 56 bibliography entries; the full paper cites 41 keys; the sp surface covers the remaining 15; zero undefined citations; zero defined-but-uncited entries; the shared `references.tex` builds clean in both surfaces.

## Artifact binding evidence

- **Figures:** `python scripts/gen_sp_figures.py --check` → `OK   paper/figures/generated_values.tex matches the artifacts` (exit 0), against `results/bootstrap_ci.json`, `results/stability_run1_vs_run2.json`, `results/b4_baseline_zodiac_20260922.json`, `results/model_quality/chrollo_calibration.json`, `results/sp2027_rescue/behavior_trajectory_benchmark.json`.
- **Two-channel tables:** auto-generated (`scripts/gen_two_channel_tables.py`), amended in `ace5944`; in-file provenance annotations (echo-guard corrections, kappas, row identities) trace to `results/cti_manual_audit.json` (present; keys include `echo_guard_correction`, `served_text_row_identity_vs_two_channel`). Full number-vs-registry comparison remains Step 10 scope per the plan.
- **Architecture figure:** depicts only implemented components (Chrollo classifier, Don hybrid RAG, fiction graph, generator, verifier, serve, ATT&CK predictor/bait steering, append-only audit log, HITL require-gate, deterministic fallback) — each matched to existing code modules; no research-only variants (Evidence Judge stage, Laya, V4 policy studies) appear as active. Audited; no change required.
- **Model/reference disclosure:** generator identities in table captions (`glm-5.3-flash-free`, `deepseek-v4-flash-free`); reference author `gpt-5.6-luna` via Codex CLI retained in evaluation text and the Step 3 protocol documents.
- **Gate sweep:** no "general fold-down" claim, no live-Laya benefit, and no field-effectiveness-from-descriptive-studies claim present; every "fold-down" occurrence is the audited ladder phenomenon/pressure or the hard-subset census.

## Build verification (final state)

- `paper/main.tex`: pdflatex ×2 → **28 pages, 0 errors, 0 undefined citations/references** (the pre-repair log carried the four undefined citations above).
- `paper/sp2027.tex` (untracked surface, shared bibliography): pdflatex ×2 → **15 pages, 0 errors, 0 undefined citations**.
- Residual-key grep across `paper/` for all removed keys: empty.

## Deferred / flagged for Step 10

1. `related.tex` "honeytoken-based attribution~\cite{valeros2024}" pairing remains unverified, and the bibliography contains no dedicated honeytoken source — flagged for Step 10 bibliography validation (do not silently re-point).
2. Full number-vs-registry comparison for all paper numbers (plan Step 10 action).
3. `sp2027` adaptation/finalization after the full paper, including venue-requirements verification.
4. Commit decision for the working-tree revision pass described above.
