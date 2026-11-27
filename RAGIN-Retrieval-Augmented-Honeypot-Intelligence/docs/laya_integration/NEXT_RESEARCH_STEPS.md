# Next Research Steps

Ordered by research value per unit of work (smallest first). Nothing below has been
executed yet in this session.

## 1. Historical Cowrie evaluation set with independent labels (highest priority)

- Use the repository's existing archived Cowrie session artifacts
  (e.g. `results/jev_real_logs_eval.json` provenance: 13 real sessions with manually
  supplied severity labels) as a starting lot; audit provenance first, then extend.
- Target 100+ sessions with binary malicious/benign plus stage labels assigned by a
  human pass, not by any model.
- Freeze hashes/splits/license notes in a dataset manifest under `results/laya_research/`.

## 2. Threshold and calibration fitting on a dev split

- Split: dev (threshold selection) / held-out (reporting), no leakage.
- Fit temperature scaling for the noul head on cybersecurity data (laya exposes
  `laya.calibrate.fit_temperatures`); recompute Brier/ECE on held-out.
- Re-run the B/D comparison with the fitted threshold before any claims of improvement
  over the 0.5 threshold pilot numbers.

## 3. Full A/B run through the live pipeline (Chrollo → Hisoka → verifier)

- Config A (`RAGIN_LAYA_ENABLED=0`) vs B (`=1`) on the same session population through
  `server_v2` / cycle harness locally: measure verifier acceptance/rejection deltas,
  deception-policy selection deltas, and whether Laya's signal adds information beyond
  Chrollo's RF features (agreement/disagreement matrix).
- Hisoka integration point for policy selection should only be touched after step 2 shows
  the noul head is calibrated on this domain.

## 4. typed-decisions checkpoint trial (optional)

- Only if step 1 labels support it: `typed-decisions` ships a `security_incidents`
  workflow (credential_compromise, severity, true_positive, urgency, disposition) that
  maps naturally onto RAGIN's questions. One additional checkpoint download (~0.8 GB) is
  within the disk budget; measure against `english` on the same held-out split.

## 5. Latency budget integration

- If Laya is promoted toward default-on, the 1.3 s CPU assessment per session must be
  amortized (batching, persistent worker) or gated to sessions Chrollo is uncertain
  about (only-call-on-disagreement policy). Measure the conditional-call version first.

## Hard blockers worth recording now

- NVML/driver mismatch on this workstation currently blocks any GPU plan; CPU-only torch
  is installed. If GPU is wanted later, fix driver/library mismatch first and reinstall
  a CUDA-enabled torch build in an isolated env (not the RAGIN `.venv`).
- The free-tier Jev endpoint was not contacted this session; config C (Jev baseline on
  the new dataset) remains unmeasured.
