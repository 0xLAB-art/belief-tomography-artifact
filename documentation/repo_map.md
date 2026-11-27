# Repository map

Five layers. Paths are relative to the repository root.

## 1 · Paper evidence layer

| Path | Contents |
|---|---|
| `gauntlet/demo/` | Frozen experiment deposit: E1–E31 results, transcripts, verdicts, run logs, E21–E31 registrations, E3 grids, drivers |
| `gauntlet/gauntlet/` | Frozen instrument/estimator code (`tomograph.py`, `verdict.py`, generator, world, policies, certificate, harness) — the `8ceb6e0` estimator pin |
| `docs/paper/belief_tomography/CLAIMS_EVIDENCE_LEDGER.md` | Claim → artifact map with the registration-integrity status note |
| `docs/paper/belief_tomography/ARTIFACT_MANIFEST.sha256` | 375-entry frozen manifest |
| `docs/paper/belief_tomography/PREREGISTRATION_*.md` | Day-0 registrations (E10–E20) · `RESEARCH_PROGRAM_V2.md` |
| `docs/paper/belief_tomography/independent_reaudit/` | Blinded re-adjudication: 3 coders, 46-item stratified sample, κ = 0.96 |
| `docs/paper/belief_tomography/figures/` | F1–F9 sources + `anthro/` plates + `make_figures.py` |
| `docs/paper/belief_tomography/formalism_note.{tex,pdf}` | Formal definitions/proofs note |
| `docs/innovation/` | Program record: execution log, lit-scan, paper plan, collision scan, venue decision |
| `data/field/ragin/`, `data/sessions/` | Frozen live-field snapshot (13 + 11 records) |

## 2 · Manuscript

The manuscript and its build artifacts are **not hosted in this repository** —
reviewers receive the paper through IEEE. Validation does not require it: the
ledger quotes every claim verbatim. The figure data
(`paper/tops/figs/figdata/`, 20 manifest-pinned files) was released from the
deposit together with the manuscript on 2026-11-27; the frozen-manifest header
documents the scope reduction.

## 3 · The platform (complete mirror)

| Path | Contents |
|---|---|
| `RAGIN-Retrieval-Augmented-Honeypot-Intelligence/` | Full honeypot/RAG platform minus `.venv`, model weights, caches: deception engine (`ragin/`), Rust LLM gateway (`llm-gateway/`), ablation configs, tests, docs, dist mirrors |
| `…/results/` | Field-attack campaign (EPK frontier gen-1–3, arm A/C, bootstrap stats) · jury lane (`panel_v3/`, `ai_jury_*`) · fleet census (redacted) · verifier red-team · complete product-evaluation record |
| `…/data/` | Session store (7,759 seeded sessions), field exports, corpora, benchmarks — **`data/field/` is local self-play** per its own `PROVENANCE.md` |
| `…/scripts/` | Producers for every cited artifact (field drivers, stats, jury scripts, proxies) |
| `results/`, `scripts/`, `ragin/` | Root-level mirrors for the ledger's bare-path citations |

## 4 · Live-fleet VPS export (2026-11-27)

| Path | Contents |
|---|---|
| `vps-export/2026-11-27/CORE/` | 15,409 cumulative served-session logs · 15,404 field records · `host_fiction.json` |
| `vps-export/2026-11-27/EDGE/` | 42,076 pre-NAT connection records · full Cowrie log history (2026-10-08 → 11-27) |

Pulled over AWS SSM the same day as the freeze; see
`vps-export/2026-11-27/EXPORT_MANIFEST.md`.

## 5 · Review and audit record

| Path | Contents |
|---|---|
| `egm_review/` | Seven-reviewer audit (151 findings, disposition) |
| `review_belief_tomography_v6/`, `v7/`, `review_main/`, `review_rebuild_2026-11-21/` | Adversarial review rounds that shaped the manuscript |

## Infrastructure

| File | Purpose |
|---|---|
| `verify.sh` | Checks both manifests |
| `checks/quick_counts.sh` | Asserts the 230-flag decomposition and blocked-turn table |
| `REDACTIONS.md` | Every substitution with original/public hashes |
| `CITATION.cff` | Citation metadata (paper author; anonymous commit identity) |
| `mkdocs.yml` + `documentation/` | Source of this documentation site |
