# Hidden-Layers Checklist — full sweep 2026-10-29

Complete inventory of everything found in the hidden / uncommitted / historical
layers of the repo (three sweeps: historical experiments, hidden dot/ignored
files, git history). Each item carries a status and an action.

## A. Git layer

- [x] Working tree clean — zero uncommitted changes (last commits: `51ec7566` paper, `c66b5435` field)
- [x] No stashes; 157 commits; single branch
- [x] Only ONE deleted result artifact in history: `results/human_eval_scored/test-alpha.json` (d5528131, consolidation) — accounted for
- [x] `evidence_snapshots_archive` (130 files, 2.2 MB) — moved OUT of tree to `../evidence_snapshots_archive/` (c61b5427), sha256-verified, pointer note `docs/research/recovery_final_20261023T042900Z/MOVED_SOURCE_SNAPSHOTS.md` — **intact, no action**
- [x] `results/laya_research/expert_ai_workspaces/` was a resolution failure, not data loss — real store at `../ragin_expert_panel_v1/` — **intact**

## B. Ignored / dot directories

- [x] `.mimosa/` (587 MB) — 12 security-scan runs 2026-10-24→10-29; **latest scan INCOMPLETE** (hook: `scanner_enobufs`)
  - [ ] ACTION (pre-submission): run full Mimosa scan to completion
- [x] `data/field/` (4.6 MB) — 194 local self-play session exports, own `PROVENANCE.md` (LOCAL SELF-PLAY ONLY) — **recorded, no action**
- [x] `.omo/` — 3 hidden review records:
  - [x] `ROLE_G_EXPERIMENTAL_DESIGN_REVIEW_20261013.json` → full report at `docs/laya_integration/CODEX_EXPERIMENTAL_DESIGN_REVIEW.md` (independent design review; verdict: preserve frozen design; taxonomy-precedence concerns deferred to v2) — **SUPPORTS the paper**
    - [ ] ACTION: cite one line in supplement as independent design review of the label lane
  - [x] `codex_r1-integrity-*.json`, `role-b-case-quality-conflict-*.json` — invocation-integrity evidence, no contradictions
- [x] `.archify/`, `.superpowers/`, `.qwen/`, `.zcode/`, `.freebuff/`, `.persona_build_tmp/` — tool state only
- [x] `.venv-gpu/` (6.9 GB) — CUDA env for the GPU redesign experiments — env, not results
- [x] `gateway.tar` (96 MB), `imc_vpn.pdf`, `dist/` — build artifacts
- [x] `ESWA-S-26-45224/` — empty dir (submission was via tracked response letter)
- [x] Backup files in tree: `ragin/cycle/harness.py.bak20261010`, `nginx-canary.conf.bak_ips`, `run.env.bak` — inert
- [x] Env files with live keys present locally: `.env`, `.env.bak*`, `.env.field`, `.env.field.local`, `.env.ragin-stack` — gitignored correctly
  - [ ] ACTION: rotate the agentrouter key (it was pasted in an old chat) after the last run
- [x] `results/cti_audit_blinding_key.json` — unblinding key, correctly untracked

## C. ⚠️ Missing / lost items found by the sweep

- [ ] `results/azure_field_endpoints.jsonl` + `results/azure_field_prefixes/` — gitignored AND absent from the working tree: Azure deployment artifacts appear **deleted locally**. ACTION: check git history / document as lost
- [x] `ragLegendre/` referenced in `docs/full_project_audit/09_TECHNICAL_DEBT.md` — does not exist; stale doc reference, harmless
- [x] `/tmp` artifacts cited in docs (`tmp/ragin_live_bench_final_v5.json`, opencode captures) — transient, superseded by tracked copies

## D. Out-of-repo experiment stores (documented + verified)

- [x] `/mnt/01DCDC2BF6665BC0/ragin_laya_gpu/` — 1.6 GB Laya v12 final checkpoint (evidence of the frozen negative result; 9.5 GB→1.6 GB pruning executed) — **intact**
- [x] `../ragin_expert_panel_v1/` — expert-AI panel authoritative workspaces (expert_ai_01..03 + adjudicator_01) — **intact**
- [x] AWS field hosts: EDGE runs a full copy of the repo at `/opt/ragin/repo/`; cowrie logs `/opt/ragin/cowrie-var/log/cowrie/`; intel services `:8000/:8765` — **host-side only**; collection via SSM verified working (census 2026-10-29 + 279-session export pulled 2026-10-29)

## E. Historical experiments NOT in the paper (from the 82-item historical sweep)

Priority-1 (measure exactly what the paper claims — integrate):

- [x] **Decision Fusion V4** (integrated 2026-10-29: supplement `app:floorvalidation` + evidence map) — deterministic policy layer: locked validation N=96, fail-safe recall 1.0 (42/42), contract alignment 1.0 (96/96), latency 0.027 ms; HF2024 retrospective N=720 family-disjoint (`results/decision_fusion_v4/`). → one sentence in §5.5/supplement
- [x] **Provider content-filter campaign (2026-10-27)** — agentrouter blocks 72/174 (41%) of real field commands; stability 216/216; serve-rate under framing 0.24 (`results/provider_content_filter_*.json`). (integrated 2026-10-29: §5.5 availability paragraph)
- [x] **Evidence Judge synthetic validation** (integrated: supplement `app:floorvalidation`) — without judge: 32 false admissions; with: 0/0 (`results/evidence_judge_paired_validation_v1/`). (integrated)
- [x] **Aug-2026 live VPS campaign** (integrated: §5.7 field paragraph) — 30 sessions, **2 genuinely external attackers** (`results/ALL_RESULTS_VS_ESWA_PAPER.md` axis 15). (integrated)
- [x] **ROLE_G independent design review** (integrated: supplement `app:floorvalidation`)

Priority-2 (context, keep in artifact mirror):

- [x] Dwell-replay fiction ladder v1→v7 (integrated: supplement Supporting Studies) (0/14 → 12/12; tells: key prefix, fallback echo, AWS-doc-credentials trap)
- [x] CTI manual audit (integrated: §5.8 + supplement; strict-vs-family added in elite pass)
- [x] 72h-sprint mTLS matrix; fast-path/cache 4.7×; determinism sweep 1.0 (integrated: supplement Supporting Studies)

## F. Frozen-but-unexecuted experiment contracts (hidden in plain sight)

- [ ] **Causal ablation program B0–B5** — `configs/ablation/eval_v1/run_contract_v1.json`: DESIGN_VALIDATED_EXECUTION_NOT_READY, execution_lock INCOMPLETE, provider_calls=0, 0/32 sessions, H1–H5 NOT_ESTABLISHED. The largest designed-but-unrun experiment. → post-submission decision
- [ ] Laya v13 redesign blueprint (`docs/laya_integration/LAYA_V13_REDESIGN_BLUEPRINT.md`) — unexecuted, Laya frozen negative
- [ ] SSH-wire E2E proof — `BLOCKED: ssh-wire-e2e-proof-pending` (`docs/next_stage/`)
- [ ] Guarded Table VII rerun — blocked on provider quota (`docs/GUARDED_TABLE_VII_RERUN.md`)

## G. Already integrated (verified in paper)

- [x] Grounding ablation + VoR campaign + stability + echo-guard
- [x] Verifier battery + cross-family + harm probe + hardening waves
- [x] A/B v1 + v2 (pre-registered nulls + exploratory surface yield)
- [x] AI jury + deterministic oracle + protocol sensitivity (κ 0.811 → 0.790/0.663)
- [x] JEV fold-down + Laya v12 gates + Evidence Judge prospective null
- [x] Timing side-channel (AUC 0.983 unpadded / 0.551 padded), profiler 0.8875/0.9550, host-fiction drift 4/4, steering top-3 0.9
- [x] Claims→evidence map: 16 rows, every claim has a sha-pinned artifact

---
Sweep date: 2026-10-29 · Method: 3 Explore agents (historical 82-item inventory; hidden/ignored/dot/git layers; paper coverage diff) · No secrets printed; key rotation pending.
