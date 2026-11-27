# Matched Ablation Results (RAGIN × Laya, pilot)

Date: 2026-10-12. All numbers come from raw evidence in `results/laya_research/`:
`real_inference_cpu_pilot.jsonl` (raw per-case model outputs and latencies) and
`matched_ablation_analysis.json` (derived metrics, recomputable via
`scripts/laya_ablation_analysis.py`).

## Experimental design (pilot scale)

- Population: 45 synthetic SSH sessions, by-construction labels (25 benign / 20 malicious).
- Identical inputs and evaluator logic across configurations; matched comparison.
- Reproduction: `.venv/bin/python scripts/laya_real_inference_pilot.py` then
  `.venv/bin/python scripts/laya_ablation_analysis.py`.

## Configurations actually measured

| config | measured | how |
|---|---|---|
| A — baseline (Laya disabled) | yes | env gate returns no provider; classification unchanged (unit-tested); no assessment metrics apply |
| B — Laya enabled | yes | real weights, real forward pass, 45/45 scored |
| B0 — always-benign baseline | yes | derived from the same cases |
| R0 — random coin baseline | yes | seeded (20261012), 1000 draws |
| C — Jev assessment | not measured | remote free-tier endpoint was not contacted this session (rate-limited free quota; not adding external calls) |
| D — Laya alone | yes | same 45 cases, isolated classifier-quality view = config B numbers themselves |

## Assessment quality (binary malicious verdict, noul P(true) ≥ 0.5)

| config | acc | bal-acc | precision | recall | F1 |
|---|---|---|---|---|---|
| B / D — Laya | 0.778 | 0.760 | 0.857 | 0.60 | 0.706 |
| B0 always-benign | 0.556 | 0.500 | — | 0.0 | — |
| R0 random | ≈0.5 ± 0.07 | ≈0.5 ± 0.07 | — | — | — |

Laya exceeds both trivial baselines on every reported metric. Brier 0.151; 10-bin ECE
0.151 (probabilities are miscalibrated — the checkpoint itself ships an invalid
temperature; laya emits a runtime warning saying so).

## Cost

| metric | value |
|---|---|
| Warm p50 / p95 | 1.30 s / 1.41 s per assessment (CPU) |
| Cold first assessment | 6.6 s (route + weights load) |
| Resident cost | ≈ 2.1 GB RSS while enabled |
| NO_SIGNAL rate | 0 / 45 |
| Total 45-case runtime | 59.6 s |

## Paired per-case differences

Per-case paired records (y, prediction, P(true), latency) are in the raw JSONL for every
case under both trivial baselines; because configs A/B differ only in whether an
advisory dict is attached, A-vs-B produces no classification delta by construction —
the pipeline seam is additive. Downstream policy selection was NOT exercised in this
pilot; no claim of improved deception is made.

## Statistical limitations (explicit)

- n=45 with 20 positives: binomial 95% CI on 0.778 accuracy is roughly ±0.12; treat the
  point estimate as pilot-signal only.
- Labels are by-construction on synthetic transcripts; they are independent of the model
  (not model-generated), but they are not historical Cowrie ground truth.
- Threshold 0.5 was fixed a priori, not tuned; no dev/held-out split was performed —
  threshold fitting must precede any larger matched experiment.
- ECE at this n is indicative only.
- laya's own calibration warning means confidence values must not be compared to Jev's
  confidence semantics.

## Conclusion scale

At pilot cost (1 extra CPU process, ~1.3 s assessment latency, ~2.1 GB RSS), Laya adds a
usable independent signal on synthetic sessions (0.778 vs 0.556 always-benign), with a
recall (0.60) that must improve before it could justify promotion into anything
decision-adjacent. This justifies extending the experiment, not production adoption.
