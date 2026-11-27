# Task 1 Report — Freeze the audit baseline and classify the worktree

## Status

Complete. Created `docs/RAGIN_RELEASE_MANIFEST_2026-10-08.md`; no source, session, PDF, or results files modified.

## Changed files

- `docs/RAGIN_RELEASE_MANIFEST_2026-10-08.md` (created)
- `.superpowers/sdd/2026-10-08-ragin-audit-remediation/task-1-report.md` (this report)

## What was recorded in the manifest

1. **Git baseline** — commit `f01a4a98d8fc0cdbf1f031d915385294675e3b1b`, branch `main`, 18 modified paths, 1,986 untracked paths at baseline (1,986 → 1,986 classes: 1,977 `data/sessions/*.jsonl`; rest are `paper/sp2027.*`, `paper/sections/sp_*`, rescue script/results, cowrie rerun JSON, audit doc, `docs/superpowers/`), `git diff --stat` = 18 files changed, 986 insertions(+), 104 deletions(-).
2. **Toolchain** — Python 3.12.3 (system and `.venv`), pytest 9.1.1, ruff 0.16.7, mypy 2.3.1, pdflatex TeX Live 2023 (pdfTeX 3.141592653-2.6-1.40.25), pdftotext 24.02.0.
3. **Manifest/provenance state** — no top-level `MANIFEST.json`; `graphify-out/manifest.json` + `graph.json` are stale (2026-10-03) and classified operational-trace only.
4. **Artifact classification** — canonical (live-audit JSONs, JEV artifact under Task 3 repair, rescue benchmark as bounded evidence), supporting (model-coherent baselines, audit doc, sp2027 rescue README), historical/failed (`results/benchmark_report.json` 158/158 failures, `results/before_openrouter/`, cowrie outputs), fallback-only/operational-trace (provider pilots, apmix quota/probe, sessions on disk), PDF/graph outputs marked stale until rebuild.
5. **Two manuscript surfaces** — `paper/main.tex` = full audit manuscript; `paper/sp2027.tex` = shorter rescue/submission surface until a release decision changes it; neither is submission-ready (main.tex build blocked on `algorithm.sty`; PDFs predate dirty sources).
6. **Reproducibility commands** — exact `git`/`sha256sum`/`wc`/version commands documented and re-run; all reproduced (untracked count 1986 → 1987 explained by the manifest file itself).

## Verification summary

- `git rev-parse HEAD` → `f01a4a98d8fc0cdbf1f031d915385294675e3b1b` ✓
- `git branch --show-current` → `main` ✓
- `git status --short | awk '{print $1}' | sort | uniq -c` → `18 M`, `1987 ??` (baseline 1986 + this manifest) ✓
- `git diff --stat | tail -1` → `18 files changed, 986 insertions(+), 104 deletions(-)` ✓
- `ls data/sessions | wc -l` → 6904; `ls results | wc -l` → 174 ✓
- sha256 re-checks: `results/jev_hard_subset.json` `884a63c2…`, `results/apmix_quota_status.json` `9814c134…`, `graphify-out/graph.json` `818c4fb9…` ✓
- `python3 --version` → 3.12.3; `.venv/bin/pytest --version` → 9.1.1; `pdflatex --version` → TeX Live 2023 ✓
- Manifest hash commands reproduce; worktree otherwise unmutated.

## Concerns / notes

- Untracked count shifts by +1 because `docs/RAGIN_RELEASE_MANIFEST_2026-10-08.md` is itself untracked; the manifest documents this explicitly.
- `graphify-out/graph.json` is stale relative to the dirty worktree — must be regenerated before it is treated as current (Task 10 Step 7).
- `paper/main.tex` fresh build remains blocked by missing `algorithm.sty` (Task 7); PDFs are stale.
- `results/apmix_quota_status.json` still reports catalog drift/unprobed quota — provider-backed claims remain blocked (Task 8).
- No test suite was run in this task; it is a documentation/manifest-only change. Static evidence = the shell verification outputs above.
