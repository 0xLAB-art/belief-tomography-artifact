# Task Plan: Laya GPU Redesign v2

## Goal
Complete a new, versioned Laya calibration/tuning study that addresses v1's failed alignment and abstention behavior without modifying v1 artifacts.

## Phases
- [x] Phase 1: GPU environment feasibility and isolated setup
- [x] Phase 2: Design and freeze 240 fresh targeted training cases
- [ ] Phase 3: GPU architecture-feasibility development — v4 running
- [ ] Phase 4: Final fit, protocol freeze, and single confirmation
- [ ] Phase 5: Independent recomputation, one gate review, and final study report

## Decisions Made
- GPU runtime, separate virtual environment, slow-download timeout.
- Targeted contract redesign; fresh 240-case training set (~720 items).
- Head-only fine-tuning; no LoRA/full encoder tuning.
- Preserve G1–G8 and I1–I3 thresholds unchanged.
- Keep v1 immutable; new versioned artifacts only.
- No commit without explicit user authorization.

## Errors Encountered
- v1 CPU dev run had infrastructure interruptions; partial outputs were quarantined.
- v1 completed with `DEV_STOP_REDESIGN_REQUIRED`: both recipes had alignment 0.6333 < 0.85.

## Status
**Currently in Phase 3** — v8 root-cause redesign targets the measured sufficient/insufficient/conflicting confusion with fresh contrastive cases and weighted evidence-state supervision.

## 2026-10-17 progress
- v9 (mount-backed retry) and v10 (state-only supervision) both closed DEV_STOP_REDESIGN_REQUIRED; artifacts + digests recorded in notes.md.
- v11 launched: matched-coverage corpus (all required archetypes x all 9 scenarios, DEV-proportioned class mix), evidence-state-only supervision, 16 epochs; DEV/EV/INJ unchanged and byte-reused; checkpoints on /mnt.
- Phase 3 dev gate running; no user asks mid-phase.
