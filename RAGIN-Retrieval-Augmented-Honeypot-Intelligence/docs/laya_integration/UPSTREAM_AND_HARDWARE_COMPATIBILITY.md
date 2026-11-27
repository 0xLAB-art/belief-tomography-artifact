# Laya Upstream and Hardware Compatibility (RAGIN)

Date: 2026-10-12. Scope: Phase A/B of the Laya integration plan. This document records
what was verified, not planned.

## Upstream package

- Package: `laya==0.4.2` (official PyPI release; README documents 0.4.2 — version confirmed
  post-install, not assumed).
- Install location: RAGIN's existing `.venv` (Python 3.12.3), installed with
  `pip install --no-deps laya==0.4.2` so RAGIN's pinned torch/transformers stack was not
  touched. Laya's own deps were already satisfied in the venv.
- `import laya` is torch-free (lazy imports); `Router` is the main entry point.
- APIs used (verified in installed source): `Router.predict(state, questions, model=...)`,
  `Router(device, revisions, max_loaded, preload)`, question schema
  `{type, instructions, criteria}` with types `choice`/`score`/`noul`.
- Jev compatibility: Laya's question schema differs from Jev's wire format
  (`question`→`instructions`; choice options live in `criteria`, not a separate `options`
  field). Mapping implemented in `ragin/decision/laya_runtime.py`.

## Checkpoints

Three checkpoints live in one bundle repo (`convaiinnovations/laya`) plus standalone repos:

| name | repo | subfolder | encoder |
|---|---|---|---|
| english | convaiinnovations/laya | (root) | ModernBERT-large, 512 tokens |
| multilingual | convaiinnovations/laya | multilingual | mmBERT-base, 1024 tokens |
| typed-decisions | convaiinnovations/laya | typed-decisions | ModernBERT-large, 1024 tokens |

`laya.revisions.PINNED_REVISIONS` pins:

- english: `55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851`
- multilingual: `e4e9ddf21a7b1903b7acffd8814ad4307bf63a67`
- typed-decisions: `1a793eb568e6718f15941d08f85432581df534e3`

Selected for RAGIN: **english** — RAGIN analyzes English-language SSH/Cowrie sessions;
upstream's own benchmark shows the english checkpoint wins on English suites and collapses
on non-English input, which does not matter here.

Only the english weights were downloaded. The snapshot also fetched the small
config/tokenizer files of the other two subfolders (~few MB, unavoidable at snapshot
level); their large weight files were explicitly excluded by pattern.

Weight integrity: `model.safetensors` (803 MiB) sha256 =
`891102d372688fc2a094dac56a384bc537b87c63f21f9f3dac0be2b7cbc8d86c`
(matches the blob filename HF assigned at download time).

Local location: `~/.cache/huggingface/hub/models--convaiinnovations--laya/` (outside
all Git-tracked trees). Nothing was written into the repository except small result JSONs.

## Hardware findings

- GPU: NVIDIA driver present but **NVML is broken on this workstation right now**
  (`Failed to initialize NVML: Driver/library version mismatch`, NVML 595.99).
- PyTorch in the venv: `2.14.0+cpu` (CPU-only build). `torch.cuda.is_available()` → False.
- Decision: **CPU inference**, as mandated by the plan when CUDA is unavailable.
- RAM: 16 GB total, ~7 GB available before load. Model RSS after load ≈ 2.1 GB.
- Disk: 23 GB free at /home; downloaded weights 0.8 GiB (+ pre-existing 352 MB cache).
  Well under budget; no further downloads needed this session.

## Licensing note

Checkpoint repos are on the public HF hub under the upstream project's own licensing; the
ibresearch use here is evaluation only, no redistribution of weights into the repo, no
serving endpoint.

## Known upstream caveat (observed, not hypothetical)

laya 0.4.2 emits at Router load:

> this checkpoint ships invalid temperatures or values outside [0.5, 5]; using
> choice:11+=0.10058280825614929 -> 0.5. Treat confidence from the affected entries as
> uncalibrated.

Consequence taken seriously downstream: Jev thresholds are NOT transferred; pilot metrics
report Brier/ECE explicitly and mark probabilities uncalibrated.
