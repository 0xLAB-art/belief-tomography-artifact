# Step 10 — Final Review, Reproduction, and Package

- **Date:** 2026-10-15 (review pass run on top of `70e5222`)
- **Baseline:** HEAD `70e52220282b901226bc0c444558661afb5b30f4` ("Step 9: citation repair, bibliography dedup, and submission-ready revision pass")
- **Status:** READY — independent gate review passed (pass 2; verdict in §12)
- **Scope boundary:** No commit has been made and no submission action has been taken. Venue-requirements verification is deferred to pre-submission packaging and is *not* claimed by this record.

---

## 1. Plan requirements

Verbatim from `docs/PAPER_REMAINING_STEPS_2026-10-14.md` (Step 10 block):

> **Action.** Review scientific validity and code/artifact reproducibility; fix substantiated findings. Rebuild figures/tables and LaTeX from the frozen sources, inspect rendered pages, validate bibliography/citations, and compare all paper numbers against the registry. Verify current venue requirements using authoritative sources before layout/submission packaging.
>
> **Outputs.** Final review report; reproduced artifact/build manifest; portable source/data instructions; figure/table and manuscript checks; explicit unresolved limitations and readiness decision. Submission or external publication is a later authorized action, not implied by this plan.
>
> **Final gate.** The paper is internally reproducible and scientifically bounded, all promised claim-supporting experiments are complete or their claims removed, the relevant runtime checks pass or their limits are explicit, and the final package meets the selected venue's current requirements. A successful build alone cannot satisfy this gate.

## 2. Scope of this review pass

- **Baseline tree:** 68 modified, 2629 untracked entries (default reporting; 2697 porcelain lines total, this record included); `git status --porcelain -uall` = 5629 lines (5561 untracked files + 68 modified); nothing staged.
- **Passes executed:** (1) frozen-record re-verification (11-file hash record); (2) build reproduction and log audit; (3) artifact reproduction (anonymized mirror, SP figures, freshness gates); (4) bibliography/citation audit; (5) number-vs-registry sweep; (6) twin-file provenance reconciliation; (7) HITL audit; (8) rendered-page inspection; (9) git-scope classification; (10) stale-record annotation inventory.

## 3. Reproduced artifact & build record

Hash record basis: session-local `/tmp/opencode/expected.sha256`, verified `sha256sum -c` → **11/11 OK** (exit 0) in this pass. The §13 block reproduces the record portably.

| # | File | SHA-256 | Bytes |
|---|------|---------|-------|
| 1 | paper/main.pdf | 1e9e4e7a97ec02ccb248e896c17546e7bdb9827805b78f305bd05329701ef0b0 | 453877 |
| 2 | paper/sp2027.pdf | d203e2c222a2807690538010f623a287ed6eff202f536f85b6c23f797be19919 | 317540 |
| 3 | dist/MANIFEST.json | 53a8af25cb502e77612f05b61d90d391f369082ac8a3f52dab928fb1bf01c0d2 | 5856 |
| 4 | dist/ragin-sp-mirror.tar.gz | 03d4c3603ef4887cefe409d393a846cd996d545d89560e11476f7905fe5d4e96 | 532161 |
| 5 | paper/sections/two_channel_tables.tex | d4f52616afd4411650ca223be4e97acec25606b2b64a071b69495c7410e51092 | 5218 |
| 6 | results/section_vi_two_channel_tables.tex | fd5c3a19cc97bc0b744fc466868b876bbcb0e96a1de23e26bc8f9faa56fb6c41 | 5152 |
| 7 | docs/artifact_audit/artifact_manifest.jsonl | bcfd77aff86df46b96eb482f8202b2b00d6c799492f474acd86758cb35310e51 | 5239555 |
| 8 | docs/artifact_audit/experiment_registry.json | e5f4c02d9af9d7d8d1ade4b147158702e58cd4ab2a43f989efab959f5dc3d3bb | 140026 |
| 9 | paper/sp2027.tex | 99e9f54b2fdc8872ffb6e9858bbd6db22e88e01409b20c3380b9c6e2029a0a99 | 4168 |
| 10 | paper/references.tex | b411ef61e2b7c13b092a8a035e2aebc2d53111243c9c67249d1a86afe7de0233 | 10200 |
| 11 | paper/main.tex | 8a6aebfea14d053403c04bc7361b6ad1849671eb323a917212448ad045b41027 | 3266 |

Notes:

- `dist/ragin-sp-mirror.tar.gz` is a gzip container and its hash is wrapper-sensitive; the durable verification basis is the member map — `dist/MANIFEST.json` lists all **43/43** member hashes and `scripts/build_anonymized_mirror.py --check` re-validates the mirror record. The recorded hash was verified after the final `dist/` build (2026-10-15 23:08:48/49).
- `paper/sp2027.tex` sha256 equals its `dist/MANIFEST.json` entry (`99e9f54b…`) — the shipped companion source is the unredacted one, as intended.
- Build outputs: `paper/main.pdf` = 28 pages / 453877 bytes; `paper/sp2027.pdf` = 15 pages / 317540 bytes; both PDF mtimes 2026-10-15 22:09:21.
- Build environment: pdfTeX 3.141592653-2.6-1.40.25 (TeX Live 2023/Debian); preserved build logs `paper/main_build_1.log`, `paper/main_build_2.log`, `paper/main.log`, `paper/sp2027.log`.

## 4. Build & log audit

- Error lines (`^!`): **0** in both `paper/main.log` and `paper/sp2027.log`. Overfull boxes: **0** in both.
- `Output written` lines match the record exactly (28 pp / 453877 B; 15 pp / 317540 B).
- Only log oddity: `LaTeX Font Warning: Font shape 'T1/ptm/m/scit' undefined` — 1× in `paper/main.log` (line 1103) and 3× in `paper/sp2027.log` (lines 1123, 1187, 1192). Benign Times-family template font substitution; no content or reference impact.
- Freshness gates: no `paper/**/*.tex` newer than either PDF (`find paper -name '*.tex' -newer paper/main.pdf` empty; same for `paper/sp2027.pdf`) — the PDFs were built from the frozen sources.

## 5. Artifact reproduction checks

- **Anonymized mirror:** `python3 scripts/build_anonymized_mirror.py --check` → `verdict: PASS (43 files)`, exit 0. `dist/MANIFEST.json` = 5856 bytes.
- **SP figure values:** `python3 scripts/gen_sp_figures.py --check` → `OK   paper/figures/generated_values.tex matches the artifacts`, exit 0.
- **Number sweep** (`verify_step10.py`, session-local, stdlib-only) re-ran clean. Inputs swept: `verifier_redteam_live_space-bunny_rescored_after_fix.json`, `verifier_redteam_live_deepseek-v4-flash-free_rescored_after_fix.json`, `verifier_redteam_live_llama33_complete.json`, `verifier_harm_probe.json`, `cross_session_consistency_bench.json`, `live_benchmark_zodiac_20260922.json`, `live_benchmark_zodiac_20260922_run2.json`, `hitl_audit_bench.jsonl`, `vor_guarded_served_text_lower_bounds.json`, `timing_fingerprint_rocauc.json`, `stat_eval/summary.json`, `b4_baseline_zodiac_20260922.json`, `mtp_steering_eval.json`, `apmix_probe_history.jsonl` (all under `results/`).
- Key sweep outputs (red-team counts recalculated label-aware after review pass 1 — the original matcher keyed on `viol`/`attack`/`malicious` substrings and misread these totals; see §12 history): SB valid=261 → 193 violating (187 rejected / 6 admitted) + 68 benign (0 refused), targeted catches 185; DS 236 → 173 (170 / 3) + 63 (0), 170; LL 281 → 206 (197 / 9) + 75 (17), 185; pooled 572 → 554 rejected / 18 admitted, 206 → 17 refused, 540 targeted catches. HITL rows 2114 (1052 auto / 642 require-gated / 420 notify). STAT p_holm = 0.021613, mean difference = −0.1613. Cross-session {session_scoped 1/4, reconnect 4/4, per_session 4/4}. RUN1 41.48 min / RUN2 42.58 min. apmix probe history 57 rows. B4: no `channel` field anywhere.

## 6. Number-vs-registry spot checks (highest-risk claims)

- **Holm / statistics:** sweep STAT output ↔ `paper/sections/evaluation.tex` Holm block (~lines 505–523): precision@5 p_Holm = 0.51, recall@20 0.32, MRR 0.085, NDCG@10 p_Holm = 0.022, "mean difference −0.161" against the LLM engine, "priced but not executed"; claim matrix row 48 records `(p=.022, mean difference -0.161 favoring sparse)`. ✓
- **SP confidence intervals:** `results/verifier_ci_cluster_bootstrap.json` (seed `20261008`, 10k case-cluster resamples) → recall 0.9441 [0.9216, 0.9645], precision 0.9695 [0.9493, 0.9865]; `paper/sections/sp_evaluation.tex` ~:175 pooled row → .944 [.922, .965] / .970 [.949, .987]. ✓ (This artifact is not in the appendix artifact index; this record is the provenance of record — see §9.)
- **JEV stratum:** `results/jev_hard_subset.json` ↔ `evaluation.tex` ~482–492 census (400 sessions → 394 at/above floor, 6 informative) and table rows :557 "Assessed and rescued (transient) & 1", "Unavailable; 0/5 recovered on structured retry & 5". ✓
- **HITL:** `results/hitl_audit_bench.jsonl` → 2114 = 1052 + 642 + 420 ↔ `paper/sections/appendix.tex` :253–254 ("The 2{,}114-record trail splits into 1{,}052 auto-approved, 642 require-gated, and 420 …"). ✓
- **Cross-session drift:** sweep CS ↔ `design.tex:239` "session-scoped verifier alone catches 1 of 4 cross-session drift drafts" and `evaluation.tex:631` "cross-session drift in 4/4 cases versus 1/4 for session-only state". ✓
- **Timing:** `appendix.tex` "(41 minutes)" ↔ sweep RUN1 41.48 / RUN2 42.58 min (paper uses the first pass, as recorded). ✓
- **Redteam artifacts (label-aware recount, review pass 1):** SB 261 valid → 193 violating (187 rejected / 6 admitted) + 68 benign (0 refused); DS 236 → 173 (170 / 3) + 63 (0); LL 281 → 206 (197 / 9) + 75 (17); pooled 572 → 554 rejected / 18 admitted; 206 → 17 refused — matches `sp_evaluation.tex` ("rejected 554 of them and admitted 18; 17 of 206 benign drafts were refused"; LL "214 of its rejections (197 violating drafts and 17 benign refusals)"). ✓
- **apmix liveness:** `results/apmix_quota_status.json` checked_at `2026-10-15T18:04:29Z`, catalog unreachable, quota `not_probed`; `apmix_probe_history.jsonl` 57 rows. Bounds are already explicit in the manuscript. ✓
- **VOR:** echo-zeroed lower bounds (`vor_guarded_served_text_lower_bounds.json`), labeled as lower bounds due to 200-char preview truncation. Limits explicit in-artifact. ✓
- **B4:** no `channel` field anywhere in the artifact; no manuscript claim depends on it. ✓

## 7. Bibliography & citation validation

- `paper/references.tex`: exactly **56 `\bibitem`** entries.
- Citation graph recomputed per root (transitive `\input` expansion from `main.tex` and `sp2027.tex`): main cites **40**, sp2027 cites **56**, union **56**; undefined **0**; uncited **0**; main-only **none**.
- sp-only keys (16; all cited by the SP companion, none undefined): `alsaheel2021`, `blefari2025`, `fayyazi2023`, `jeon2024`, `lanka2024`, `liu2025`, `malkov2018`, `noureddine2020`, `orbinato2022`, `paul2025`, `shafran2024`, `simoni2024`, `sokol2017`, `wang2024`, `ward2025`, `xue2024`.
- Residual repairs landed in this pass (uncommitted): `references.tex` `valeros2024` authorship corrected to "M. Sladi\'c, V. Valeros, C. Catania, and S. Garc\'ia"; `related.tex` honeytoken sentence drops `\cite{valeros2024}` (no supporting source for the attribution; `valeros2024` remains cited at `related.tex:23` for LLM-in-the-Shell); `appendix.tex` polish ("third"→"second"; column widths 3.9/4.25 cm; "42"→"41 minutes").
- Twin source pair `paper/sections/two_channel_tables.tex` ↔ `results/section_vi_two_channel_tables.tex`: diff is **wrapper-only** (`\resizebox{\columnwidth}{!}{%` closure realignment); no content drift.

## 8. Git scope inventory (for the commit decision)

Nothing staged; HEAD `70e52220282b901226bc0c444558661afb5b30f4`.

- **Review-pass set (19 modified):**
  - Paper (11): `paper/main.pdf`, `paper/references.tex`, `paper/sections/{appendix,background,conclusion,design,discussion,evaluation,introduction,related,two_channel_tables}.tex`.
  - Results (7): `results/apmix_probe_history.jsonl`, `results/apmix_quota_status.json`, `results/bootstrap_ci.json`, `results/figure_geometry_audit.json`, `results/hitl_audit_bench.jsonl`, `results/jev_hard_subset.json`, `results/section_vi_two_channel_tables.tex`.
  - Docs (1): `docs/artifact_audit/RESULT_ARCHIVE_AUDIT_AND_CLAIM_MATRIX_2026-10-14.md`.
- **Step/SP packaging set (untracked):** `docs/artifact_audit/STEP{5,6,7}_*.md`; this file (`docs/artifact_audit/STEP10_REVIEW_AND_PACKAGING_2026-10-15.md`); `paper/sp2027.tex`; `paper/sp2027.pdf`; `paper/sections/sp_{appendix,evaluation,related,threat_model}.tex`; `scripts/{build_anonymized_mirror,gen_sp_figures,verifier_ci_cluster_bootstrap,run_step7_ingress_proof_v1,audit_step7_completion_gate_v1}.py`; `results/verifier_ci_cluster_bootstrap.json` (new weight file, scope A/B).
- **Excluded by default:** `paper/main_final.txt` (internal draft extract); pre-existing dirt — 18 `ragin/**`, 4 `scripts/*`, 15 `tests/*`, 2 docker-compose, 2 `.env*.example`, `.github/workflows/ci.yml`, `README.md`, `PROJECT_STATUS.md`, 5 `data/sessions/sup-*.jsonl`; large untracked trees not enumerated here (e.g. `.omo/`, bulk `data/`, `results/`, `human_*/`).
- **Open items for the user:** membership of step5–7 evidence dirs (e.g. `results/step5_working_system_observability_v1/`), `tests/integration/test_step5_commit_observability_v1.py`, and `ragin/cycle/harness.py` — include with scope B or defer.

## 9. Unresolved limitations & explicit bounds

1. **Venue requirements deferred** — not verified in this pass; pre-submission packaging will re-verify against the selected venue before layout/submission actions.
2. **Recall-CI provenance** — `results/verifier_ci_cluster_bootstrap.json` (seed `20261008`) is the SP-CI weight source and is not listed in the appendix artifact index; this record is its provenance of record; no manuscript churn made for it.
3. **Frozen-record staleness (annotate only)** — `docs/artifact_audit/artifact_manifest.jsonl` and `docs/baseline_freeze/worktree_manifest.jsonl` carry stale rows for the twin table files; these files are part of the hash record and are **not mutated** (details §10).
4. **HITL source clarification** — `data/sessions/sup-*.jsonl` are session-event logs (3903 rows), not the HITL decision trail; the trail of record is `results/hitl_audit_bench.jsonl` (2114 rows).
5. **Dead root-level copies** — `paper/appendix.tex`, `paper/evaluation.tex` are stale (not in the build; `main.tex` includes only `sections/*`); left untouched.
6. **Live-arm bounds** — free-tier provider refusals bound the JEV live arm (5/6 unavailable, 0/5 recovered on structured retry); already explicit in the paper, not a new limitation.
7. **Mirror hash basis** — `dist/ragin-sp-mirror.tar.gz` verification relies on the member map + `dist/MANIFEST.json` when the gzip wrapper is rebuilt.

## 10. Provenance reconciliation & stale-record inventory

Frozen records must not be edited (they are hash-pinned by the record in §3); reconciliation is recorded here.

- `docs/artifact_audit/artifact_manifest.jsonl`, line 2395 (stale row):
  - path `results/section_vi_two_channel_tables.tex`; recorded sha256 `20c769238f757041a2d2cae530da9cb1dabeed715f398eb210abc375f8829d1a`; recorded bytes 5156; recorded mtime `2026-09-29T14:02:16.758645+00:00`; `experiment_family` `results_root_mixed_legacy_and_baseline`; line_count 67; parse_status `readable_text`.
  - Current file hash: `fd5c3a19cc97bc0b744fc466868b876bbcb0e96a1de23e26bc8f9faa56fb6c41` (5152 bytes). → Superseded by the wrapper alignment in this pass; annotation only.
- `docs/baseline_freeze/worktree_manifest.jsonl`, line 26 (stale row):
  - path `paper/sections/two_channel_tables.tex`; sha256 `bf5859087fe79c18e5c292b90d9e143510a02b876aa61e6f1ae7a5d1029f36a5`; bytes 5222; captured `2026-10-14T15:54:24.198319+00:00`; kind `file`.
  - Current file hash: `d4f52616afd4411650ca223be4e97acec25606b2b64a071b69495c7410e51092` (5218 bytes). → Superseded by the wrapper alignment in this pass; annotation only.

## 11. Readiness decision (preparer)

**READY FOR COMMIT AUTHORIZATION** — pending the independent gate review in §12. All reproduction gates are green; every spot-checked manuscript number matches its registry artifact; no substantive finding was left unfixed in this pass; remaining gaps are explicitly bounded in §9 and none of them affect claim-supporting evidence.

## 12. Independent gate review

**STATUS: PENDING**

Protocol (executed by a single independent read-only reviewer, checklist mirrored from §2–§10):

1. This record exists; ledger `docs/PAPER_REMAINING_STEPS_2026-10-14.md:142` still unchecked; §1 quotes match the plan (~lines 100–125).
2. Recompute all 11 hashes in §3.
3. `scripts/build_anonymized_mirror.py --check` → PASS (43 files).
4. `scripts/gen_sp_figures.py --check` → OK.
5. Freshness checks empty for both PDFs.
6. Log audit: 0 error/Overfull lines; page/byte counts; benign font warnings only.
7. Twin diff wrapper-only.
8. Bibliography: 56 bibitems; 40/56/56; 16 sp-only keys as listed.
9. HITL: 2114 = 1052 + 642 + 420 from `results/hitl_audit_bench.jsonl` (not `sup-*.jsonl`).
10. Number spots: Holm, SP CI, JEV, cross-session, timing (as in §6).
11. Git scope: 2697 porcelain lines; 5629 with `-uall`; 0 staged; HEAD `70e5222`.
12. Reviewer cleanliness: working tree unchanged after review.

**Review history.**

- **Pass 1 (read-only reviewer vs checklist §12.1–12.12): verdict NOT READY**, two items. (1) *Blocking:* the §5/§6 red-team assurance was invalid — the number sweep matched violation labels by `viol`/`attack`/`malicious` substrings while the artifacts label cases `should_reject`/`should_pass`, so `viol_adm` was vacuous and the rejected-violation counts were recorded as "benign-rejected" totals. (2) *Minor:* recorded git scope (2696 porcelain / 5628 `-uall`) was one below observation (2697 / 5629). The reviewer independently counted 6 / 3 / 9 `should_reject` drafts not rejected and 0 / 0 / 17 `should_pass` drafts rejected (SB / DS / LL).
- **Fix (this pass, before pass 2):** the sweep's label logic was corrected (`isviol = ('reject' in lab) and ('pass' not in lab)`; `isben = 'pass' in lab`; violating/benign totals and a pooled line added) and re-run from the repo root: SB 261 valid → 193 violating (187 rejected / 6 admitted) + 68 benign (0 refused), targeted catches 185; DS 236 → 173 (170 / 3) + 63 (0), 170; LL 281 → 206 (197 / 9) + 75 (17), 185; pooled 572 → 554 rejected / 18 admitted; 206 → 17 refused; 540 targeted catches. The corrected counts match the manuscript's SP-gate sentences in `sp_evaluation.tex` — the manuscript is unchanged; §5/§6 were rebuilt from the corrected labels; §2/§12.11 re-measured to 2697 / 5629 (0 staged; HEAD `70e5222`; the 11-file hash record still verifies 11/11).

**Verdict:** Pass 2 (read-only gate reviewer), 2026-10-15 UTC — independently re-verified the label-aware red-team recount and its manuscript correspondence, corrected git-scope counts, stale-token cleanup, corrected sweep output, frozen 11-file hash record, and fix-pass tree integrity. Both pass-1 findings are resolved; the Step-10 audit record is **READY**.

**Finalization (after the pass-2 verdict):** the verdict was appended above and the Step-10 progress-ledger entry ticked (`docs/PAPER_REMAINING_STEPS_2026-10-14.md`), adding one further modified file to the working tree — post-finalization git scope: 2698 porcelain lines / 5630 with `-uall`; 0 staged; HEAD `70e5222`. Finalization touched no hashed file (the 11-file record re-verifies 11/11). No commit or submission action has been taken.

## 13. Portable reproduction instructions

```bash
cd RAGIN-Retrieval-Augmented-Honeypot-Intelligence

# 1) Hash record — recreate the 11-file record from §3 and verify
cat > /tmp/expected.sha256 <<'EOF'
1e9e4e7a97ec02ccb248e896c17546e7bdb9827805b78f305bd05329701ef0b0  paper/main.pdf
d203e2c222a2807690538010f623a287ed6eff202f536f85b6c23f797be19919  paper/sp2027.pdf
53a8af25cb502e77612f05b61d90d391f369082ac8a3f52dab928fb1bf01c0d2  dist/MANIFEST.json
03d4c3603ef4887cefe409d393a846cd996d545d89560e11476f7905fe5d4e96  dist/ragin-sp-mirror.tar.gz
d4f52616afd4411650ca223be4e97acec25606b2b64a071b69495c7410e51092  paper/sections/two_channel_tables.tex
fd5c3a19cc97bc0b744fc466868b876bbcb0e96a1de23e26bc8f9faa56fb6c41  results/section_vi_two_channel_tables.tex
bcfd77aff86df46b96eb482f8202b2b00d6c799492f474acd86758cb35310e51  docs/artifact_audit/artifact_manifest.jsonl
e5f4c02d9af9d7d8d1ade4b147158702e58cd4ab2a43f989efab959f5dc3d3bb  docs/artifact_audit/experiment_registry.json
99e9f54b2fdc8872ffb6e9858bbd6db22e88e01409b20c3380b9c6e2029a0a99  paper/sp2027.tex
b411ef61e2b7c13b092a8a035e2aebc2d53111243c9c67249d1a86afe7de0233  paper/references.tex
8a6aebfea14d053403c04bc7361b6ad1849671eb323a917212448ad045b41027  paper/main.tex
EOF
sha256sum -c /tmp/expected.sha256        # expect 11/11 OK

# 2) Artifact reproduction
python3 scripts/build_anonymized_mirror.py --check   # verdict: PASS (43 files)
python3 scripts/gen_sp_figures.py --check            # OK (generated_values.tex matches)

# 3) Freshness — no .tex newer than either PDF
find paper -name '*.tex' -newer paper/main.pdf
find paper -name '*.tex' -newer paper/sp2027.pdf     # both: no output

# 4) Manuscript rebuild — two pdflatex passes per document (TeX Live 2023)
(cd paper && pdflatex -interaction=nonstopmode main.tex && pdflatex -interaction=nonstopmode main.tex)
(cd paper && pdflatex -interaction=nonstopmode sp2027.tex && pdflatex -interaction=nonstopmode sp2027.tex)
# expect main.pdf = 28 pp / 453877 B; sp2027.pdf = 15 pp / 317540 B
# (byte counts may differ under other TeX Live versions)

# 5) Twin-table provenance — wrapper-only diff
diff paper/sections/two_channel_tables.tex results/section_vi_two_channel_tables.tex

# 6) HITL audit trail
python3 - <<'PY'
import json, collections
rows = [json.loads(l) for l in open('results/hitl_audit_bench.jsonl')]
print('rows:', len(rows))                       # 2114
if isinstance(rows[0].get('decision'), str):
    print(collections.Counter(r['decision'] for r in rows))  # 1052 auto / 642 require / 420 notify
PY

# 7) Citation counts
grep -cF '\bibitem' paper/references.tex        # 56
# per-root cite counts (transitive \input expansion): main 40, sp2027 56, union 56

# 8) Number sweep (session-local script; stdlib only; run from repo root)
python3 /tmp/opencode/verify_step10.py
```
