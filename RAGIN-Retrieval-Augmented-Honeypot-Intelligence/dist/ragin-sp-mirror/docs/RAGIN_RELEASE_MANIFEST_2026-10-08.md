# RAGIN Release Manifest — 2026-10-08 (Audit Baseline)

Dated baseline for the RAGIN audit remediation plan (`docs/superpowers/plans/2026-10-08-ragin-audit-remediation.md`).
Later tasks must compare against this manifest rather than inferring state from memory.
This task performed no deletion, reset, or cleanup; the dirty worktree is preserved as-is.

## 1. Git baseline

| Field | Value |
|---|---|
| Commit SHA | `f01a4a98d8fc0cdbf1f031d915385294675e3b1b` |
| Branch | `main` |
| Modified (` M`) paths | 18 |
| Untracked (`??`) paths | 1,986 |
| `git diff --stat` | 18 files changed, 986 insertions(+), 104 deletions(-) |

Modified paths (tracked surface):

- `data/sessions/sup-1.jsonl`, `sup-ctx.jsonl`, `sup-expert.jsonl`, `sup-rev.jsonl`, `sup-vote.jsonl`
- `paper/main.pdf`, `paper/main.tex`, `paper/sections/{appendix,conclusion,design,discussion,evaluation,introduction,two_channel_tables}.tex`
- `ragin/don/rag_engine.py`
- `results/apmix_probe_history.jsonl`, `results/apmix_quota_status.json`, `results/figure_geometry_audit.json`

Untracked path classes (by top-level prefix):

| Class | Count |
|---|---|
| `data/sessions/*.jsonl` (session transcripts, incl. `ses-*.jsonl`) | 1,977 |
| `paper/sp2027.pdf`, `paper/sp2027.tex` | 2 |
| `paper/sections/sp_appendix.tex`, `paper/sections/sp_evaluation.tex` | 2 |
| `scripts/sp2027_rescue_behavior_benchmark.py` | 1 |
| `results/sp2027_rescue/` (rescue benchmark package) | 1 |
| `results/external_baseline_cowrie_guarded_rerun_cowrie.json` | 1 |
| `docs/SP2027_AUDIT_2026-10-03.md` | 1 |
| `docs/superpowers/` (this plan/briefs/ledgers) | 1 |

Filesystem counts: `data/sessions/` holds 6,904 files on disk (only a subset surfaced via `git status` because much is ignored/tracked); `results/` holds 174 entries.

## 2. Toolchain versions (observed 2026-10-08)

| Tool | Version |
|---|---|
| System Python | 3.12.3 |
| `.venv` Python | 3.12.3 |
| pytest | 9.1.1 |
| ruff | 0.16.7 |
| mypy | 2.3.1 (compiled) |
| pdflatex | pdfTeX 3.141592653-2.6-1.40.25, TeX Live 2023/Debian |
| pdftotext | 24.02.0 |

## 3. Existing manifest/provenance state

- No top-level `MANIFEST.json` exists at repository root.
- `graphify-out/manifest.json` exists and maps tracked paths to mtime/hash entries; it was generated from an earlier source state (graph.json dated 2026-10-03 06:47:04) and is therefore **operational-trace only** — not current after the dirty worktree.
- `results/` contains the persisted benchmark JSONs this plan treats as evidence surfaces; each is classified below.

Key artifact hashes (sha256, observed 2026-10-08):

| Artifact | sha256 | mtime |
|---|---|---|
| `results/jev_hard_subset.json` | `884a63c266ebaa54f3b628e992b9803ce1bb724490eaaee5a2e795f7f6ebf2ab` | 2026-09-23 18:22:01 |
| `results/apmix_quota_status.json` | `9814c13453b8e1df77e4a5a51c02e5facd222d778c2b8623ae61852da2907796` | 2026-10-07 21:03:00 |
| `results/apmix_probe_history.jsonl` | `d17ff28e8ab528ead7860b8ff24cec1429dff235d39e5dd5ced8de9070bf98a7` | 2026-10-07 21:03:00 |
| `results/sp2027_rescue/behavior_trajectory_benchmark.json` | `f6945dee790432583a79a06e22589d96376e3bf76470fccb4b6149e89207b338` | 2026-10-03 07:18:12 |
| `graphify-out/graph.json` | `818c4fb9d0c97df15e4d1d3914fd8257bd4d75d15395ba0ff7593aeb42cdec4f` | 2026-10-03 06:47:04 |
| `paper/main.pdf` | `f464bb95347ee40329aa5604042a70b22ab9479467023a46e00d5e6f25cc39b0` | 2026-10-03 06:44:56 |
| `paper/sp2027.pdf` | `e8373d538cc2ed78af6b9c660ff4e526a7309c2b9035d491eb690a134a8a53d7` | 2026-10-03 07:19:42 |
| `docs/SP2027_AUDIT_2026-10-03.md` | `dba4077f08e513e1837f3333029d2c64cb95232c4e8e90adca96f93373abf54a` | 2026-10-03 07:19:28 |
| `results/benchmark_report.json` | `3d86c9a95af201171935f35b5bb473614bbc6da842443cab44be5bfec44e65d4` | 2026-09-15 20:37:17 |

## 4. Artifact classification (no deletion; classify only)

| Path / class | Classification | Rationale |
|---|---|---|
| `results/b4_baseline_zodiac_20260922.json`, `results/bootstrap_ci.json`, `results/graph_consistency_bench.json`, `results/stability_run1_vs_run2.json`, `results/two_channel_metrics.json`, `results/verifier_redteam*.json`, `results/live_benchmark_zodiac_20260922.json`, `results/live_benchmark_judge_panel_corrected.json`, `results/ablation_battery.json`, `results/mtp_steering_eval.json`, `results/jev_ab_eval.json`, `results/human_eval_scored_20260922_180637_consensus/` | `canonical` | Headline evidence referenced by README/paper; must agree with the future results ledger. |
| `results/jev_hard_subset.json` | `canonical` (under Task 3 repair) | Counts/interpretation must be synchronized to six informative / one rescued / five unavailable. |
| `results/external_baseline_model_coherent.json`, `results/external_baseline_comparison.json`, `results/external_baseline_hostfiction*` | `supporting` | Model-coherent analysis evidence; verifier paired delta is zero; not independent causal evidence. |
| `results/sp2027_rescue/` (`behavior_trajectory_benchmark.json`, `README.md`, smoke variants) | `canonical` for the rescue benchmark only; never adaptive-superiority evidence | Provider-free, held-out benchmark rescue; bounded interpretation. |
| `results/apmix_quota_status.json`, `results/apmix_probe_history.jsonl` | `operational-trace` | Provider catalog drift / unprobed quota blocks any provider-backed claim. |
| `results/hostfiction_provider_pilot_*`, `results/sp2027_rescue/hostfiction_provider_*` | `fallback-only` / `operational-trace` | Provider-blocked pilots; not headline evidence. |
| `results/benchmark_report.json` (158/158 failures), `results/before_openrouter/` | `failed` / `historical` | Failed-run record; retained for provenance, not headline claims. |
| `results/cowrie_comparison.json`, `external_baseline_cowrie*`, `results/external_baseline_cowrie_guarded_rerun_cowrie.json` | `historical` / `supporting` | Older Cowrie outputs; guarded-rerun variant is a fresh artifact pending Task 4 review. |
| `data/sessions/*.jsonl` (6,904 on disk; 1,977 untracked) | `historical` / `operational-trace` session material | Transcripts and operational traces; never delete; not canonical benchmark evidence without ledger mapping. |
| `data/sessions/sup-*.jsonl` (modified) | `operational-trace` | Supervisor/vote transcripts; modified but unverified in this task. |
| `paper/main.pdf`, `paper/main.tex` | `canonical` manuscript surface (full audit manuscript) | Full audit manuscript; current PDF is stale relative to dirty `main.tex` until Task 7 rebuilds. |
| `paper/sp2027.tex`, `paper/sp2027.pdf`, `paper/sections/sp_*.tex` | `canonical` rescue/submission surface (shorter) | Shorter rescue manuscript; distinct surface until a release decision changes the designation. |
| `graphify-out/` (`graph.json`, `manifest.json`, `graph.html`, cache) | `operational-trace` | Stale generated project map; regenerate at final gate. |
| `docs/SP2027_AUDIT_2026-10-03.md` | `supporting` | Existing audit document; status must be checked for staleness by Task 5. |
| `docs/superpowers/` | `supporting` | This plan, briefs, and ledgers. |
| PDFs/caches under HF cache and `.venv/` | `fallback-only` environment | Must be repaired/verified by Task 2; not evidence artifacts. |

## 5. Manuscript surfaces (recorded 2026-10-08)

- `paper/main.tex` (+ `paper/sections/*.tex`, `paper/two_channel_tables.tex` in `paper/sections/`) is the **full audit manuscript**.
- `paper/sp2027.tex` (+ `paper/sections/sp_appendix.tex`, `paper/sections/sp_evaluation.tex`) is the **shorter rescue/submission surface** until a release decision changes that designation.
- Neither surface is submission-ready: the `algorithm.sty` blocker was resolved on 2026-10-08 by installing `texlive-science` (Task 7), and both PDFs were rebuilt from the current sources on 2026-10-08 (main.pdf 27 pp, sp2027.pdf 11 pp). Submission-readiness still requires the ledger §8 evidence gates.
- Task 7 provenance (2026-10-08): build command `pdflatex -interaction=nonstopmode -halt-on-error <main|sp2027>.tex` run twice per manuscript from `paper/`; `paper/main.pdf` sha256 `03c1067e184ae0e185019e6e24037cbc6d243ebd894621678bbb6eb40f708b22`, 27 pages, 442,777 bytes; `paper/sp2027.pdf` sha256 `26086903aa1882c971a97dbfdca96ca8be7acd5bda4556f4887cc29bfbb96079`, 11 pages, 285,769 bytes. Logs: no undefined references/citations, no duplicate labels, no overfull boxes; one benign `T1/ptm/m/scit` font-shape substitution warning and underfull-vbox/badness notices only. `kpsewhich` resolves `algorithm.sty`, `algpseudocode.sty`, `IEEEtran.cls`, `graphicx.sty`, `booktabs.sty`, `caption.sty`, `subcaption.sty`, `hyperref.sty` after `texlive-science` install.

## 6. Reproducibility commands (re-run values must match)

```bash
cd /home/[anonymised-user]/Documents/research/ragin/RAGIN-Retrieval-Augmented-Honeypot-Intelligence
git rev-parse HEAD                      # expect f01a4a98d8fc0cdbf1f031d915385294675e3b1b
git branch --show-current               # expect main
git status --short | awk '{print $1}' | sort | uniq -c   # expect: 18 M, 1987 ?? (1,986 at baseline + this manifest)
git diff --stat | tail -1               # expect 18 files changed, 986 insertions(+), 104 deletions(-)
ls data/sessions | wc -l                # expect 6904
ls results | wc -l                      # expect 174
sha256sum results/jev_hard_subset.json  # expect 884a63c2...
sha256sum results/apmix_quota_status.json  # expect 9814c134...
sha256sum graphify-out/graph.json       # expect 818c4fb9...
python3 --version                       # expect Python 3.12.3
.venv/bin/pytest --version              # expect pytest 9.1.1
pdflatex --version | head -1            # expect pdfTeX 3.141592653-2.6-1.40.25, TeX Live 2023/Debian
```

All of the above were re-run after writing this manifest and reproduced the recorded values (untracked count moved 1986 → 1987 solely because this manifest is itself a new untracked file; modified count and all hashes unchanged). No worktree mutation occurred beyond adding this manifest.

## 7. Non-claims

- No build, test, or Number Lock result establishes scientific validity, causal identification, independent replication, or venue readiness.
- No unreviewed or provider-blocked artifact (`fallback-only`, `operational-trace`, `historical`, `failed`) is canonical evidence.
- Provider-backed results remain blocked while `results/apmix_quota_status.json` reports catalog drift and unprobed quota.
