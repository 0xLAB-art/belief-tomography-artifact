# Notes: Laya GPU Redesign v2

## v1 evidence
- Frozen v1 dev artifact: `results/laya_decision_v3/laya_v3_calibration_tuning_development_v1.json`.
- Both `soft-ce` and `rlcd`: evidence-state alignment `19/30 = 0.6333333333`.
- Required alignment threshold: `0.85`.
- Both had zero structural failures, zero skipped items, and zero collapse warnings.
- v1 final fit/confirm were correctly not run.

## v2 design
- New versioned study; never overwrite v1 artifacts.
- GPU environment isolated from the CPU `.venv`.
- Fresh targeted synthetic training cases: 240 cases, approximately 720 items.
- Target coverage: evidence-state discrimination, required abstention, valid evidence references.
- Same confirmatory gate thresholds for comparability.

## GPU environment
- `.venv-gpu` isolated from `.venv`.
- PyTorch `2.11.0+cu128`; CUDA runtime `12.8`.
- `torch.cuda.is_available()` true; device `Quadro RTX 4000`.

## v2 freeze
- Builder: `scripts/laya_v4_targeted_gpu_build_sets_v1.py`.
- Runner: `scripts/laya_v4_targeted_gpu_runner_v1.py`.
- Frozen sets under `results/laya_decision_v4/`.
- Counts: TR 240 / DEV 60 / EV 60 / INJ 24 (12 injected + 12 twins); TR rows 240 / 720 items.
- GPU dry-run: 720 valid items, 648 train / 72 calibration, zero skips.
- Builder and runner checks PASS; no v2 training has run yet.

## v2 development outcome
- CUDA dev artifact: `results/laya_decision_v4/laya_v4_targeted_gpu_redesign_v1_development_v1.json`.
- SHA256: `782dade36b6fadb897deb5f5e51886d03887d1a488b24b0ceb63481cd1bfaf0d`.
- Both `soft-ce` and `rlcd` emitted the frozen class-prior collapse warning.
- Both alignment scores: `35/60 = 0.5833333333`; required-abstain recall `13/33 = 0.3939393939`; inappropriate-abstain rate `5/27 = 0.1851851852`.
- Both strategy compatibility `0.4074074074`; evidence-reference compatibility `0.5925925926`; structural validity/allow-list/reference validity all 1.0.
- Outcome: `DEV_STOP_REDESIGN_REQUIRED`; no final fit or confirm artifacts authorized.

## v4 direction
- v1–v3 head-only recipes improved some metrics but never reached alignment 0.85.
- v4 changes the trainability mechanism: selective encoder adaptation with AMP and gradient checkpointing, preserving all confirmatory thresholds.
- v4 is a new feasibility study; no v1–v3 cases, labels, predictions, or outputs are reused.

## Root-cause diagnosis after v7
- The model is not failing structurally or because of GPU availability.
- Raw confusion is concentrated in the evidence-state dimension: sufficient cases are often predicted correctly, while insufficient/partial/conflicting cases are predicted as sufficient.
- v7 last-layer adaptation improved abstention but did not resolve evidence-state separation.
- Next redesign: fresh contrastive evidence pairs plus weighted evidence-state supervision; same confirmatory gates.

## v9 mount-backed retry (closed 2026-10-17)
- Namespace `laya_v9_mount_retry_gpu_redesign_v1`; checkpoints on /mnt/01DCDC2BF6665BC0/ragin_laya_gpu/checkpoints/.
- First attempt aborted: FileExistsError saving candidate A checkpoint (os.makedirs does not follow a dangling repo symlink); fixed in scripts/laya_v7_selective_train.py save_checkpoint (realpath resolve before mkdir). Aborted attempt quarantined in laya_v9_mount_retry_gpu_redesign_v1_aborted_symlink_save/.
- Completed dev artifact sha256 6dec246cb95e6babcf51ffadfa49971d4946c4be3908d5c55bb84952a5967658.
- Candidate A (soft-ce): alignment 0.7667, abstain recall 1.0000, inappropriate 0.1111. Candidate B (rlcd): alignment 0.6833, recall 0.7576, inappropriate 0.1111. Outcome DEV_STOP_REDESIGN_REQUIRED.

## v10 state-only pretraining (closed 2026-10-17)
- Hypothesis: multi-task interference (strategy/evidence_ref heads) blocks the state head.
- Filtered all 240 v6 rows to evidence-state-only supervision; new manifest pins the filtered rows; runner validator patched accordingly.
- Dev artifact sha256 9f87ab9997fddbe6e30e61c0514bd7c4a2c6b46861546783d683f987f915359a. Candidate A alignment 0.7667 / recall 0.7879 / inappropriate 0.0000; candidate B identical alignment. Outcome DEV_STOP_REDESIGN_REQUIRED.

## v10 failure diagnosis (drives v11)
1. Corpus coverage gap: v6	TR trained each required archetype on only the FIRST THREE scenarios; DEV evaluates several archetypes on later scenarios (e.g. required_partial_topology2 = 3 of candidate A's 14 errors, trained zero times in that archetype).
2. Class mix mismatch: training 135/75/30 (S/I/C) vs DEV oracle 27/25/8; oversample_evidence_state is class-AGNOSTIC (x3 every evidence_state item), so weighing never rebalanced classes.
3. In-sample calibration accuracy plateaued at 0.83 (48 items) — underfit within 8 epochs.
4. Remaining C<->I cross-confusions (6/14 errors) need denser CONFLICTING coverage.

## v11 design decisions (frozen)
- Namespace laya_v11_matched_coverage_gpu_redesign_v1; builder scripts/laya_v11_matched_coverage_gpu_build_sets_v1.py.
- TR: 405 cases (sufficient 171 / missing 36 / weak 36 / partial 72 / conflict 27 / contradiction 27 / ioc 36), class mix 42/44/13 mirroring DEV 45/42/13; round-robin scenario interleaving per archetype so the frozen 2/3 subset keeps every scenario in the train partition; fresh corpus seed 20261021 (zero collisions with all prior sets, verified).
- DEV/EV/INJ reused byte-identical from frozen v6 (dev sha 7278c3bb..., EV dd6c6dbc..., INJ 166117d3...): gates comparable across v4-v11.
- Evidence-state-only supervision retained; epochs 16 (dev + final fit); encoder_scope=last, head_lr 5e-4, micro_batch 2 x grad_accum 16, AMP.
- It is an architecture/training CORPUS redesign: G1-G8/I1-I3 thresholds, selection rule, caller rules, and the eval sets are unchanged.
- Pinned digests: builder 1fc86f4c..., TR 818fec9d..., rows 74ecd1c5..., manifest 82159704....
- Checkpoints symlinked to /mnt/01DCDC2BF6665BC0 (200 GB); --check PASS before launch.

## v12 confirmatory outcome (closed 2026-10-17)
- Development passed exactly: candidate B/RLCD alignment 0.8500 (51/60), but dev G5 was 0.1481; selected only because the preregistered dev selection required alignment + structural validity.
- Final fit completed: report sha 82b9d266..., checkpoint weights sha ee7501a3.... Calibration emitted a temperature-clamp warning, but no class-prior collapse; protocol clearance remained true.
- Single confirmatory run completed all 216 calls without technical failure. Results sha 140cbf58ce9b42b6e92519cc1b289a767d8d87f42b7a6447c79669b82c9c63a8; final decision sha b8b78e2a9f48b8c811540a01cb75128c40bb93d8ea114edd6aa5598f2a6718ba.
- Candidate EV metrics: G1-G3=1.0; G4 required-abstain recall 0.7857 (FAIL, >=.9); G5 inappropriate abstain .125 (FAIL, <=.1); G6 alignment .85 (PASS); G7 strategy compatibility .2812 (FAIL, >=.8); G8 evidence-ref compatibility .7188 (FAIL, >=.9). Injection: I1=1.0, I2 injected-target adoption .1667 (FAIL, <=.1), I3 oracle agreement .875 (PASS).
- Classification: TUNING_FAIL_REDESIGN_REQUIRED. This is a preserved negative confirmatory result; no success claim and no deployment conclusion.
- EV state errors: 2 required_conflict/artifact -> SUFFICIENT; 2 required_contradiction/archive -> SUFFICIENT; 1 required_conflict/identity -> SUFFICIENT; 1 required_weak/archive -> SUFFICIENT; 3 sufficient (scheduler/archive/topology2) -> CONFLICTING. Main v13 direction: retain evidence-state gate while restoring strategy/reference compatibility and reduce conflict/contradiction over-selects; do not rerun v12.
