# Task 7 report — Rebuild figures, tables, and manuscripts from active sources

Date: 2026-10-08 (Africa/Cairo). Worker: Sisyphus (orchestrator, single-session; no further agents dispatched).

## Files changed

| File | Change |
|---|---|
| `docs/RAGIN_RELEASE_MANIFEST_2026-10-08.md` | §5 manuscript-surfaces status updated (algorithm.sty resolved; both PDFs rebuilt 2026-10-08, main.pdf 27 pp / sp2027.pdf 11 pp; still not submission-ready). Added Task 7 provenance bullet with command, tool versions, sha256, page counts, sizes, and log findings. |
| `docs/RAGIN_RESULTS_LEDGER_2026-10-08.md` | Header note updated: `algorithm.sty` blocker resolved 2026-10-08 via `texlive-science` install (Task 7); both PDFs rebuilt from current sources. |
| `docs/SP2027_AUDIT_2026-10-03.md` | Stale build-status note replaced: blocker resolved 2026-10-08 (Task 7); both manuscripts rebuilt; still not submission-ready until evidence gates pass. |
| `README.md` | Manuscript-status blockquote updated: blocker resolved, both PDFs rebuilt 2026-10-08 (27 pp / 11 pp); still not submission-ready until evidence gates pass. |
| `PROJECT_STATUS.md` | Two status surfaces updated identically (header blockquote + §Fresh-build/evidence gate line: partially cleared — a) resolved, b) rebuilt, c) §8 evidence gates still open). |
| `paper/main.pdf` | Regenerated from current `paper/main.tex` via pdflatex ×2 (2026-10-08 08:53:40 +0300, 442,777 bytes, 27 pages). |
| `paper/sp2027.pdf` | Regenerated from current `paper/sp2027.tex` via pdflatex ×2 (2026-10-08 08:53:53 +0300, 285,769 bytes, 11 pages). |
| `paper/main.log`, `paper/sp2027.log`, `paper/main.aux/.out/.bbl`, `paper/sp2027.aux/.out` | Build byproducts regenerated. |

No paper `.tex` source needed edits: Task 6 had already synchronized `paper/sections/appendix.tex` to the 1,715-test evidence (`1,715 collected = 1,599 passed + 116 skipped + 0 failed`), and the figure/table sources (`paper/sections/*.tex`, `paper/sections/sp_*.tex`) already matched the results ledger. No PDFs were hand-edited. All unrelated user changes (data/sessions JSONL, `results/apmix_*`, graphify-out, etc.) were preserved; no reset/clean/push/merge.

## Commands and exact outcomes

1. `kpsewhich algorithm.sty algpseudocode.sty IEEEtran.cls graphicx.sty booktabs.sty caption.sty subcaption.sty hyperref.sty` — initially only IEEEtran.cls and graphics packages resolved; `algorithm.sty`/`algpseudocode.sty` missing.
2. `sudo apt-get install -y texlive-science` (via `sudo -n` with interactive fallback) — installed TeX Live science bundle; `kpsewhich` then resolves `algorithm.sty` (algorithms bundle), `algpseudocode.sty` (algorithmicx bundle). Script-created format refresh completed; no other package touched. Non-destructive, project-supported (Debian TeX Live package).
3. Build 1: `cd paper && pdflatex -interaction=nonstopmode -halt-on-error main.tex` — exit 0, `Output written on main.pdf (27 pages, 442777 bytes)`.
4. Build 2 (same command) — exit 0, identical page count/size; log stable.
5. Build 1: `pdflatex -interaction=nonstopmode -halt-on-error sp2027.tex` — exit 0, `Output written on sp2027.pdf (11 pages, 285769 bytes)`.
6. Build 2 — exit 0, identical.
7. Diagnostics: `grep` of both logs for `undefined/missing/duplicate/multiply` → only one benign `LaTeX Font Warning: Font shape T1/ptm/m/scit undefined` per log (font substitution); zero undefined references, zero undefined citations, zero duplicate labels, zero missing figures, **zero overfull boxes**; only underfull-vbox/badness notices (normal justification).
8. `pdfinfo`: main.pdf / sp2027.pdf producer `pdfTeX-1.40.25`, creation 2026-10-08 08:53:38/08:53:51 EEST, 27/11 pages.
9. `pdftotext` + grep: ledger values present in both texts (`+0.116` ×3, `105-case`, `12/13`, `132`, `+0.154`×7 combined hits per manuscript); main.pdf text carries the 1,715/1,599/116 appendix line; sp2027 carries the same bounded claims but its appendix has no pytest count line (pre-existing source design, not an error).
10. Visual QA: `pdftoppm -png -r 110` rendered all pages of both PDFs; inspected main.pdf p1 (title), p10 (Algorithm 1 box), p17 (TABLE 7 two-channel metrics), p5 (figure-text reference), and sp2027.pdf p1 (title/abstract), p7 (TABLE 1 paired grounding ablation). See Visual QA observations.
11. Status-doc greps: no `1709`/`1,709` remnants in any paper source; `submission-ready` language only in the non-claim sense; README/PROJECT_STATUS/ledger/audit updated as above.
12. `git diff --check -- README.md PROJECT_STATUS.md` — clean.

## Hashes / page counts / tool versions

| Item | Value |
|---|---|
| `paper/main.pdf` sha256 | `03c1067e184ae0e185019e6e24037cbc6d243ebd894621678bbb6eb40f708b22` |
| `paper/sp2027.pdf` sha256 | `26086903aa1882c971a97dbfdca96ca8be7acd5bda4556f4887cc29bfbb96079` |
| Pages | main.pdf 27; sp2027.pdf 11 |
| Size | main.pdf 442,777 B; sp2027.pdf 285,769 B |
| Build mtimes | main.pdf/main.log 2026-10-08 08:53:40 +0300; sp2027.pdf/sp2027.log 2026-10-08 08:53:53 +0300 |
| pdflatex | pdfTeX 3.141592653-2.6-1.40.25 (TeX Live 2023/Debian) |
| pdftotext | 24.02.0 |
| System/.venv Python | 3.12.3 |
| pytest | 9.1.1 |
| algorithm.sty source | `/usr/share/texlive/texmf-dist/tex/latex/algorithms/algorithm.sty` (texlive-science) |
| algpseudocode.sty source | `/usr/share/texlive/texmf-dist/tex/latex/algorithmicx/algpseudocode.sty` (texlive-science) |

## Visual QA observations

- main.pdf p1: clean two-column IEEEtran layout; no clipping/overlap; Times-like serif; abstract and index terms legible.
- main.pdf p10 (Algorithm 1, Verified-serve loop): frame rules intact, 19 numbered lines, no clipped text; dense but readable at publication scale; right-side comments fit within the box.
- main.pdf p17 (TABLE 7, two-channel metrics): columns aligned, caption complete and legible; caption is long/dense (10 lines, small-caps) but not clipped; en-dash placeholders render.
- sp2027.pdf p1: title/abstract/index terms clean; ledger-consistent numbers in abstract (`+0.154`, CI `[+0.092, +0.221]`, `+0.116`, `105-case`, cross-family P 0.916–1.000 / R 0.898–0.983, Δ +0.005 / 0.991 agreement).
- sp2027.pdf p7 (TABLE 1, paired grounding ablation): caption complete, values aligned, no overflow; readable.
- No visible clipped, stale, or misleading element found on inspected pages. Figures in both manuscripts are inline TikZ (the single `\includegraphics` in `paper/sections/design.tex` is commented out), so figure rendering is reproducible from source by the same build.

## Unresolved blockers

- Ledger §8 evidence gates (fresh full-suite pytest rerun under the dated totals, supported-claim grading, manual JSON spot-checks) are **not re-run in this task**; both manuscripts therefore remain **not submission-ready** even though the build gate is now cleared.
- `results/apmix_quota_status.json` still reports provider catalog drift/unprobed quota: provider-backed claims stay blocked (operational trace only).
- sp2027 appendix carries no pytest totals line (pre-existing source design); the 1,715-test figure lives in `paper/sections/appendix.tex` (main manuscript) and README/PROJECT_STATUS.
- The single `T1/ptm/m/scit` font-shape substitution warning is benign and pre-existing; zero overfull boxes.

## Provenance statement

PDFs are byte-reproducible from the current dirty worktree with: `cd paper && pdflatex -interaction=nonstopmode -halt-on-error main.tex` (×2) and `… sp2027.tex` (×2), TeX Live 2023/Debian with `texlive-science` added 2026-10-08; git baseline commit `f01a4a98d8fc0cdbf1f031d915385294675e3b1b` (branch `main`), dirty worktree preserved as-is.
