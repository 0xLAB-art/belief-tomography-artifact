# RAGIN Release Report — 2026-10-08 (Task 10)

Gate evidence collected 2026-10-08, observed at `2026-10-08T06:16:35Z`–`2026-10-08T06:24:00Z`
(Africa/Cairo local; UTC timestamps below). Worker: direct execution by Sisyphus
(OpenCode), model `opencode/fledge-alpha-free`. No agents dispatched; no provider
campaigns run; no secrets handled; no files reset/cleaned/deleted; no PDFs hand-edited;
no historical/provider/fallback artifacts relabeled.

Git state at gate run: branch `main`, HEAD `f01a4a98d8fc0cdbf1f031d915385294675e3b1b`,
23 modified tracked paths, 1,989 untracked paths (baseline was 18 M / 1,986 ?? at Task 1;
delta attributable to Tasks 2–9 artifacts and this report's inputs).

## Gate table

| # | Gate | Command (exact) | Timestamp (UTC) | Duration | Result | Status |
|---|---|---|---|---|---|---|
| 1 | Diff/whitespace integrity | `git diff --check` | 2026-10-08T06:17Z | <1 s | exit 0, no output | PASS |
| 1b | Conflict-marker scan | `grep -rn '<<<<<<<\|>>>>>>>\|=======$'` over `ragin/ docs/ paper/ results/ scripts/ tests/` | 2026-10-08T06:17Z | <1 s | only `=` comment separators in `tests/unit/test_intelligence.py` (false positive) | PASS |
| 2 | Ruff (repo command) | `ruff check ragin/ tests/` | 2026-10-08T06:18Z | ~1 s | exit 1 — **1 error**: `PT001` `@pytest.fixture()` at `tests/unit/test_artifact_consistency.py:53` (changed file, Task 3 surface) | FAIL (changed-file lint) |
| 2 | Ruff on changed `.py` files | `git diff --name-only \| grep '\.py$' \| xargs ruff check` | 2026-10-08T06:19Z | ~1 s | same single PT001 error; exit 123 (xargs propagate) | FAIL (same root cause) |
| 2 | Ruff full tree (incl. scripts) | `ruff check ragin/ tests/ scripts/` | 2026-10-08T06:17Z | ~2 s | 67 pre-existing errors, almost all in unmodified `scripts/` (E501, N806, F841, I001, etc.) | PRE-EXISTING (not introduced by remediation) |
| 2 | mypy (repo command) | `mypy ragin/ --ignore-missing-imports` | 2026-10-08T06:20Z | ~40 s | exit 1 — **5 pre-existing errors**: `ragin/graph/fiction.py:393,400,403,414` (`Match[str] \| None` vs `Match[str]`), `ragin/cycle/supported_claims.py:103` (union-attr). Both files unmodified by this remediation. | PRE-EXISTING |
| 2 | mypy on changed engine | `mypy ragin/don/rag_engine.py --ignore-missing-imports` | 2026-10-08T06:21Z | ~15 s | `Success: no issues found in 1 source file` | PASS |
| 3 | Full test suite | `.venv/bin/pytest -q` | 2026-10-08T06:22Z | 115.57 s | **1599 passed, 116 skipped, 0 failed, 34 warnings** | PASS |
| 4 | Artifact-focused tests | `.venv/bin/pytest -q tests/unit/test_artifact_consistency.py tests/unit/test_supported_claims.py tests/unit/test_figure_geometry.py tests/unit/test_verifier_redteam.py tests/unit/test_two_channel_metrics.py` | 2026-10-08T06:23Z | 0.78 s (1.9 s wall) | **132 passed** | PASS |
| 5 | DON default hybrid | `.venv/bin/pytest -q tests/unit/test_don.py` (no env override) | 2026-10-08T06:24Z | 85.59 s | **89 passed, 6 warnings** | PASS (default hybrid) |
| 5 | DON explicit BM25/sparse | `RAGIN_RAG_MODE=bm25 .venv/bin/pytest -q tests/unit/test_don.py` | 2026-10-08T06:26Z | 67.18 s | **89 passed, 6 warnings** | PASS (sparse/BM25) |
| 6 | PDF hashes vs manifest | `sha256sum paper/main.pdf paper/sp2027.pdf` | 2026-10-08T06:27Z | <1 s | `main.pdf` = `03c1067e…708b22`, 27 pp, 442,777 B; `sp2027.pdf` = `26086903…b96079`, 11 pp, 285,769 B — both match Task 7 / manifest §5 | PASS |
| 6 | PDF metadata | `pdfinfo` | 2026-10-08T06:27Z | <1 s | Producer pdfTeX-1.40.25; creation 2026-10-08 08:53:38/08:53:51 EEST; pages 27/11 | PASS |
| 6 | LaTeX log hygiene | `grep -ciE 'undefined reference\|undefined citation\|duplicate label\|missing figure'` on `paper/main.log`, `paper/sp2027.log`; `grep -ci overfull` | 2026-10-08T06:28Z | <1 s | 0 undefined refs/citations, 0 duplicate labels, 0 missing figures, 0 overfull boxes in both logs; 10 generic `Warning` lines in main.log (benign font-shape substitution, per Task 7) | PASS |
| 6 | PDF text sentinels | `pdftotext … \| grep -c` | 2026-10-08T06:28Z | <1 s | main.pdf: `1,715`×1, `+0.154`×7; sp2027.pdf: `+0.154`×7, `105-case`×5 | PASS |
| 7 | Graph/provenance freshness | `graphify --help`, `graphify update --help`, `sha256sum graphify-out/graph.json` | 2026-10-08T06:23Z | <1 s | Installed `graphify` CLI (`~/.local/bin/graphify`) has **no `update` subcommand** — regeneration unsupported; `graphify-out/graph.json` unchanged (`sha256 818c4fb9…`, mtime 2026-10-03 06:47:04, 8.8 MB). Recorded **stale / operational-trace / excluded**; not deleted, not treated as current. | BLOCKED (stale; excluded from evidence) |

## Residual risks / non-clearing evidence

1. **Provider catalog drift remains.** Task 8 (2026-10-08T06:03:31Z,
   `scripts/check_apmix_catalog.py`, exit 2): catalog lists only
   `claude-sonnet-4-6-free`; wired `deepseek-v4-flash-free` and
   `grok-4.7-free` missing; quota `not_probed`. Provider-backed reruns stay
   blocked; `results/sp2027_rescue/hostfiction_provider_*` remain
   fallback-only/operational-trace.
2. **Echo-guarded served-text correction is an offline rescore**, not a live
   218-row pass; guarded technique/actor values (0.0569 / 0.0) require a live
   rerun for fresh campaign evidence.
3. **Two-channel served-text credit was substantially an echo artifact**
   (per the Sep-28 CTI audit and ledger §2); headline analysis-channel numbers
   remain the valid ones.
4. **Verifier paired delta is exactly 0** in the model-coherent baseline —
   quality parity plus safety boundary, not an independent causal claim.
5. **Rescue benchmark is provider-free / self-consistency bounded**: the
   behavior-floor comparison is a diagnostic against the Supervisor's own
   rule, not independent effectiveness or field validation.
6. **`results/benchmark_report.json` (158/158 failed)**, old `results/before_openrouter/`,
   superseded human-eval dirs, guarded-rerun Cowrie variant: historical/supporting only.
7. The Task 10 **Ruff PT001** at `tests/unit/test_artifact_consistency.py:53`
   was fixed narrowly during Task 11; the changed-file Ruff check now passes.
   Repository-wide Ruff still reports pre-existing script findings, and mypy
   still reports five errors in unmodified `ragin/graph/fiction.py` /
   `ragin/cycle/supported_claims.py`; these block a fully clean static-check gate.
8. **`graphify-out/` is stale** (2026-10-03, pre-dirty-worktree) and the
   installed CLI cannot regenerate it; it is excluded from the release surface.
9. **JEV fold-down evidence is bounded**: six informative rows, one assessed/rescued,
   five provider-unavailable — no general subsumption claim is supported.

## Final status

**AUDIT-DRAFT-ONLY**

Rationale: every offline evidence gate that can run locally passes
(1,599 passed / 116 skipped / 0 failed; 132 artifact tests; 89+89 DON mode
tests; PDFs match the manifest with clean logs), but the release cannot be
`READY` while (a) provider catalog drift keeps provider-backed claims blocked,
(b) repository-wide Ruff and mypy carry pre-existing findings, and (c)
`graphify-out/` is stale and not regenerable with the installed CLI. The
manuscript may circulate only as an explicitly labeled audit draft;
it is not submission-ready. Build/test success proves only the stated checks —
not scientific validity, causal identification, or venue readiness.

## Task 11 handoff addendum (2026-10-08)

- The one changed-file Ruff finding from the Task 10 gate was remediated
  narrowly: `@pytest.fixture()` -> `@pytest.fixture` in
  `tests/unit/test_artifact_consistency.py`. The focused file now passes
  `17 passed` and `.venv/bin/ruff check tests/unit/test_artifact_consistency.py`
  reports `All checks passed`.
- Repository-wide Ruff findings in `scripts/` and five mypy findings in
  unmodified files remain pre-existing; no unrelated lint/type cleanup was
  performed. The LSP environment still reports `pytest` unresolved for the
  test file, but the project `.venv` test and Ruff checks pass.
- `bash scripts/security_scan.sh` completed locally. Bandit produced a
  supporting `bandit-report.json` with 30 existing code-pattern findings (20
  low, 10 medium); dependency audit tools were unavailable. No secret/token
  value was copied into this report. The scan script exits 0 while reporting
  warnings, so this is not a clean security gate.
- Worktree review counted 23 modified tracked paths and 1,991 untracked paths;
  session transcripts, `.omo/`, plan/ledger/report files, rescue outputs, and
  `bandit-report.json` remain preserved and classified rather than deleted.

Final status remains **AUDIT-DRAFT-ONLY**: provider catalog drift, stale
unregenerable graph output, pre-existing mypy/repository Ruff findings, Bandit
warnings, and the evidence/venue-readiness boundary remain open.

## Hard-review closure addendum (2026-10-08)

The S&P hard-review remediation started after Task 11 and was verified locally
as follows:

| Workstream | Evidence | Status |
|---|---|---|
| Threat model | `docs/RAGIN_THREAT_MODEL_2026-10-08.md`; new `paper/sections/sp_threat_model.tex` and canonical-source integration | `CLOSED-LOCAL` for claim framing; held-out adaptive stress cases remain open |
| B4 paired provenance | `scripts/run_baseline_comparison.py`, `scripts/bootstrap_ci.py`, `tests/unit/test_b4_pairing_contract.py`; exact-set audit and `--audit` CLI | `CLOSED-LOCAL` for the contract; archived result still uses name fallback and needs a fresh provider rerun for canonical IDs |
| Artifact paths | `scripts/validate_release_artifacts.py`, `tests/unit/test_validate_release_artifacts.py`, corrected `paper/sections/sp_appendix.tex` | `CLOSED-LOCAL`; validator exit 0 |
| Claim boundaries | Canonical abstract, introduction, evaluation, and conclusion now distinguish analysis-channel, raw/guarded served-text, archived reruns, and human-validation limits | `CLOSED-LOCAL` for the short paper |
| Fresh canonical PDF | `paper/sp2027.pdf`, 12 pages, SHA256 `509974820f2443a7cb06216ac1531ea242df04525b5e44ddd0ebdde7fdd71ffc`; clean second-pass references and rendered inspection | `CLOSED-LOCAL` for the short-paper build |
| Focused remediation tests | `.venv/bin/pytest -q tests/unit/test_b4_pairing_contract.py tests/unit/test_validate_release_artifacts.py` -> 23 passed; Ruff and diff check pass | `CLOSED-LOCAL` |

The canonical PDF remains `AUDIT-DRAFT-ONLY`. Unresolved S&P blockers are
explicitly external or evidence-dependent: provider catalog/quota access,
independent human or judge-model quality validation, stronger direct baselines,
held-out adaptive attacks, and authorized VPS/ambient-traffic deployment. No
fresh provider campaign or external service was started in this addendum.

## Final local verification addendum (2026-10-08)

- Full suite: `.venv/bin/pytest -q` -> **1622 passed, 116 skipped, 0 failed,
  34 warnings** in 116.88 seconds.
- Pairing audit: `scripts/bootstrap_ci.py --audit results/b4_baseline_zodiac_20260922.json`
  -> exact 90/90 set and suite membership, no duplicates; key is legacy
  `name` because the archived artifact predates canonical `scenario_id`.
- Artifact-path audit: `scripts/validate_release_artifacts.py` -> **exit 0**;
  11 canonical references resolve from the repository root.
- Changed-file Ruff: **All checks passed**. `git diff --check`: clean.
- TeX second-pass logs: no undefined references/citations, duplicate labels,
  missing figures, or overfull boxes. The only remaining warning is the known
  font-shape substitution.
- Generated PDFs: `paper/main.pdf` 27 pages, SHA256
  `97173f48241e0b3f190a3b0b6df3a92d0565af90bfee70a0cfe4b85e8cdc523d`;
  `paper/sp2027.pdf` 12 pages, SHA256
  `509974820f2443a7cb06216ac1531ea242df04525b5e44ddd0ebdde7fdd71ffc`.

These results close the local software, artifact, and canonical-build gates.
They do not close provider availability, independent quality validation,
adaptive-attack coverage, direct-baseline completeness, or VPS/field
deployment evidence.

## Static-analysis closure addendum (2026-10-08T12:59Z)

The gate table above is a timestamped record of the run at 06:17–06:28Z and is
left unedited. Its rows 19, 20, and 22 recorded `FAIL` / `PRE-EXISTING` for the
static checks; those results are **superseded** by the re-runs below. Resolving
them was not a prerequisite for the paper, so they were carried as documented
debt until this pass.

| Gate | Command (exact) | Result | Status |
|---|---|---|---|
| Ruff (CI-gated) | `ruff check ragin/ tests/` | `All checks passed!` | **PASS** |
| Ruff format (CI-gated) | `ruff format --check ragin/ tests/` | `168 files already formatted` | **PASS** |
| mypy (CI-gated) | `mypy ragin/ --ignore-missing-imports` | `Success: no issues found in 97 source files` | **PASS** |
| Ruff on changed `.py` | `git diff --name-only \| grep '\.py$' \| xargs ruff check` | `All checks passed!` | **PASS** |
| Ruff format on changed `.py` | same file list, `ruff format --check` | `24 files already formatted` | **PASS** |
| Full suite | `.venv/bin/pytest -q` | **1627 passed, 116 skipped, 0 failed, 34 warnings** in 125.52 s | **PASS** |
| Bandit | `bandit -r ragin/ -c pyproject.toml` | 30 findings (20 low, 10 medium, **0 high**), all triaged false positive — see below | **PASS (triaged)** |
| Ruff incl. `scripts/` | `ruff check ragin/ tests/ scripts/` | 77 findings, all in `scripts/` | **PRE-EXISTING, outside CI** |

### What actually changed, and why it was not cosmetic

1. **mypy: 5 errors → 0**, from two root causes rather than five typos.
   - `ragin/cycle/supported_claims.py:103` re-searched with a *second, narrower*
     regex to extract the base64 payload, then called `.group(1)` on it. The
     outer regex that gated the branch already implied the inner one, so it was
     never `None` in practice — but if the two ever drifted, the resulting
     `AttributeError` was swallowed by a bare `except Exception` and the checker
     **failed open to raw text** on a verification path. The payload is now
     captured by the same search that gated the branch, so the dependency is
     gone rather than merely typed away.
   - `ragin/graph/fiction.py` reused one name `m` for `finditer` results
     (`Match[str]`) and `.search()` results (`Match[str] | None`), so mypy took
     the first binding as the declaration for the whole method. Fixed with a
     single declaration at the first binding; no `Any`, no `# type: ignore`.
2. **`ruff format --check` was never recorded as passing.** The CI workflow runs
   it, and it was red on 20 files — 18 pre-existing drift plus 2 introduced
   during this remediation. All 20 reformatted, plus 2 changed `scripts/` files
   found by the changed-file check. Formatting only; the suite count is
   unchanged at 1627.
3. **Bandit's 30 findings are not a security finding.** They were never triaged
   because CI runs bandit with `|| true`. Triaged by hand: `B608`
   (`deception.py:1649`) is attacker-supplied SQL text rendered into a fake
   `bash: SELECT: command not found` reply — the module contains no database and
   no `execute()`; `B310` (`mitre_cti_loader.py:44`) already enforces the
   `https://` scheme allowlist bandit asks for; `B108` sites are `/tmp` strings
   inside constants that generate fake directory-listing text, not real temp
   calls; `B104` is a honeypot binding `0.0.0.0` on purpose.

### Residual

- `scripts/` carries 77 lint findings and is **not** covered by CI, which gates
  `ragin/` and `tests/` only. Most are `N806`/`E501` argument-naming and
  long-line style in research scripts. Left as-is: a 77-finding mechanical
  refactor of files outside the CI contract is not a debt worth paying blind,
  and it would bury the uncommitted paper work in the diff.
- Of the three reasons this report gave for `AUDIT-DRAFT-ONLY`, static-check
  debt is now closed. **The status does not change** — provider catalog drift
  and the stale, unregenerable `graphify-out/` both remain open, as do the
  evidence and venue-readiness boundaries listed above.

### Canonical artifact state, and superseded figures above

Two figures recorded in the earlier addenda no longer describe the tree. Both
are noted here rather than edited in place, since those sections are timestamped
records of the run they measured.

| Artifact | Recorded earlier | Current (2026-10-08T12:59Z) |
|---|---|---|
| `paper/sp2027.pdf` | 12 pp, SHA256 `509974820f…` (lines 114, 138–139) | **15 pp, SHA256 `fa05345b3b3eabf3c408…`** |
| `paper/sp2027.pdf` text pages | — | **12** (bibliography begins p. 13; limit 13) |
| `paper/main.pdf` | 27 pp, SHA256 `97173f48241e0b3f190a…` | unchanged |
| Full suite | 1622 passed (line 125) | **1627 passed** |

The short paper was rebuilt during the three-round hard review: two new context
probes were added to the harm corpus, one mirror script was added to the
allowlist, and the R3-1 wording correction landed in `sp_evaluation.tex`. The
page count grew from 12 to 15 to accommodate the corrected evaluation text and
its supporting table; the text-page budget is unchanged at 12 of a 13-page
limit, with 0 undefined references, 0 citation warnings, and 0 overfull boxes.
The extended companion (`main.pdf`) was not touched.

Artifact gates re-run against the current tree, all passing: red-team artifact
consistency 47/47, cluster-bootstrap aggregation, figure values, figure geometry
5/5, harm probe (H 4/7, F 5/10, X 1/2), mirror build and `--check` at 43 files,
and mirror verdict-faithfulness with **0 verdict changes across 151 cases**.
