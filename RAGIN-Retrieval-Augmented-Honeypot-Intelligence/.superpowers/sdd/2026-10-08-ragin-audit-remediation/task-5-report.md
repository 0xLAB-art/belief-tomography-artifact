# Task 5 Report — Canonical Manuscript Surface Decision

Date: 2026-10-08. Operator: Sisyphus (implementation worker for Task 5 only).

## Step 1 — Source scope comparison

Compared `paper/main.tex` and `paper/sp2027.tex` by their preamble input lists
and shared section files (both: IEEEtran conference/compsoc, anonymous
submission, same abstract thesis, same headline numbers from the Oct-8
ledger).

| Surface | Sections / inputs | Figures/artifacts | Result coverage |
|---|---|---|---|
| `paper/main.tex` (full audit) | `sections/introduction`, `background`, `design`, `formal`, `implementation`, `evaluation`, `discussion`, `related`, `conclusion`, `references`, `sections/appendix` | Full figure set via `paper/figures/` + `../figures/`; two_channel tables; appendix artifact index | Full evaluation narrative incl. two-channel/echo-guard audit, cross-family verifier stress, stability, JEV fold-down census, sp2027 rescue benchmark context |
| `paper/sp2027.tex` (shorter rescue) | `sections/introduction`, `design`, `sp_evaluation`, `conclusion`, `references`, `sections/sp_appendix` | Subset of figures; `sp_*` tables | Condensed evaluation: paired grounding delta, model-coherent ladder, live campaign totals, verifier deterministic suite + cross-family stress, stability; rescue benchmark bounded and provider pilots excluded |

Results present in `main.tex` but absent from `sp2027.tex`: the standalone
`background`, `formal`, `implementation`, `discussion`, `related` sections and
the full-length `evaluation`/`appendix` apparatus (e.g. two_channel_tables,
extended artifact index). Results in `sp2027.tex` are a strict subset of the
ledger's canonical evidence rows; no result exists only in `sp2027.tex`.

## Step 2 — Canonical release target (decision)

Per the task instruction, the decision recorded is:

- **Canonical next release/submission surface: `paper/sp2027.tex`** (shorter
  rescue manuscript). Build output `paper/sp2027.pdf` is the release candidate.
- **`paper/main.tex` is the full audit / extended companion.** Build output
  `paper/main.pdf` is its generated artifact. The two surfaces are
  intentionally **not merged**; shared headline numbers are kept artifact-linked
  per `docs/RAGIN_RESULTS_LEDGER_2026-10-08.md`.

Direct source comparison did **not** contradict this choice: `sp2027.tex`
inputs the shared `introduction`/`design`/`conclusion`/`references` plus its
own condensed `sp_evaluation`/`sp_appendix`, so it is maintainable standalone.

## Step 3 — Status language updated

- `README.md`: replaced the stale "Full reproducible companion to the paper —
  paper/main.pdf" line with the dated canonical-surface statement, the
  companion label for `main.pdf`, and the explicit fresh-build + evidence gate
  (neither PDF submission-ready). Left the "1,466 tests" badge/count untouched
  (Task 6 owns counts).
- `PROJECT_STATUS.md`: header note (2026-09-23 block) previously claimed "The
  paper is written and compiled (17 pp, `paper/main.pdf`, 'The Intelligence
  Ladder')" — replaced with the dated Task-5 designation and the
  not-submission-ready gate; marked the old 17 pp/title wording historical.
  §7 TDSC row: replaced stale 17 pp "The Intelligence Ladder" canonical claim
  with the 2026-10-08 canonical/companion split. T5 row noted as superseded.
- `docs/SP2027_AUDIT_2026-10-03.md`: was stale (claimed both LaTeX builds
  compile; pytest counts presented as current). Added a dated 2026-10-08
  addendum: canonical designation, the stale build claim (fresh `main.tex`
  build blocked on missing `algorithm.sty`; `sp2027.tex` loads the same
  package so it is gated identically), stale PDFs, and that its test counts
  are historical / Task 6-owned. Historical content preserved.

## Step 4 — Source-of-truth note

Added §7.1 "Manuscript source-of-truth (2026-10-08, Task 5)" to
`PROJECT_STATUS.md`: `paper/sp2027.tex` controls the release PDF;
`paper/main.tex` is the full audit companion; PDFs and `*.aux/*.log/*.out/*.bbl/*.blg`
are generated (never hand-edit); companion maintenance rule (shared headline
numbers stay artifact-linked, content not merged); and the blocking
fresh-build/evidence gate.

## Step 5 — Consistency search classification

Searched: "submission-ready", page counts ("17 pp", "27 pages", "11 pages",
"13 text pages"), test counts (1323 / 1412 / 1466 / 1593 / 1709), "The
Intelligence Ladder", `paper/main` / `paper/sp2027` references.

| Occurrence | Classification |
|---|---|
| `docs/RAGIN_RESULTS_LEDGER_2026-10-08.md` (neither submission-ready; main.tex blocked on algorithm.sty; PDFs stale) | current — matches ledger of record |
| `docs/RAGIN_RELEASE_MANIFEST_2026-10-08.md` (same gating; sp2027 = shorter rescue/submission surface "until a release decision changes the designation") | current — Task 5's decision now ratifies the sp2027 designation; wording remains accurate as descriptive |
| `docs/SP2027_AUDIT_2026-10-03.md` "both LaTeX builds compile", pytest 1,709/41-pass | stale — corrected by Task 5 addendum (historical, preserved) |
| `docs/SP2027_AUDIT_2026-10-03.md` "sp2027 11 pages; main 27 pages, not the upload variant" | current/historical — consistent with sp2027-as-submission decision; left |
| `docs/SP2027_SUBMISSION_PLAN.md` 27-pp/1412/1593 pass counts, "paper/tdsc/..." paths | historical era log — not a status surface; left (Task 6 territory for counts) |
| `PROJECT_STATUS.md` 17 pp / "The Intelligence Ladder" as current paper | stale — updated by Task 5 |
| `PROJECT_STATUS.md` 1323 passed (2026-09-22), 116 skipped, and "TDSC retarget ✅ 17 pp" row | historical/dated — updated row wording; dated test-count history left as era record |
| `README.md` "1,466 tests (41 unit modules)" | Task 6 scope — untouched |
| `README.md` "Full reproducible companion — paper/main.pdf" | stale surface — updated by Task 5 |
| `.superpowers/sdd/.../task-*.md`, `progress.md`, plan file | task/plan narrative — left |
| `SUPERVISOR_REVIEW_BRIEF.md`, `TDSC_COVER_LETTER.md`, `VENUE_DECISION_NOTE.md`, `CODE_AUDIT.md`, `graphify-out/` | historical artifacts (v3 review brief, frozen TDSC cover letter, stale graphify output) — left; not status surfaces |
| "submission-ready" in plan/manifest/ledger/progress | current as a **negative** gate — all consistent |

No occurrence of an affirmative "paper is submission-ready" claim remains.

## Verification

- `git diff --stat` confirms only `README.md` and `PROJECT_STATUS.md` edited
  (tracked); `docs/SP2027_AUDIT_2026-10-03.md` is untracked and carries the
  addendum (verified via `tail`).
- No result JSONs, paper section content (`paper/sections/*`, `paper/*.tex`),
  PDFs, tests, provider files, or counts/claim wording changed.
- Topology check: `which latexmk` → absent; `kpsewhich algorithm.sty` →
  absent; `pdflatex` present. Fresh-build gate on `main.tex` confirmed still
  blocked; `sp2027.tex` loads `\usepackage{algorithm}` and is gated the same.
- Per brief: neither manuscript is submission-ready until fresh builds and
  evidence gates pass — stated in README, PROJECT_STATUS, SP2027_AUDIT addendum,
  and here.

## Concerns

1. `sp2027.tex`'s preamble also requires the missing `algorithm.sty`, so the
   fresh rebuild of the canonical surface currently fails too; the release
   package cannot be cut until that dependency is resolved or the preamble is
   trimmed (out of Task 5 scope — flagged for the fresh-build task).
2. `docs/SP2027_AUDIT_2026-10-03.md` and `docs/SP2027_SUBMISSION_PLAN.md`
   remain untracked/era docs with stale build and pytest claims; I annotated
   the first, left the second as history. Consider formalizing their status in
   Task 6/7.
3. `graphify-out/` (2026-09-28) references the old "Intelligence Ladder"
   surface and is stale; ledger already classifies it operational-trace.
