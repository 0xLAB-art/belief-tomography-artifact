# Chrollo vs Laya — Paired Results Status

## Status

**PENDING HUMAN ANNOTATION.**

An independent candidate pool and blinded packet exist, but no human labels have
been supplied yet in this session. Therefore the paired Chrollo-vs-Laya
evaluation on independent ground truth is not yet executable in a scientifically
valid way.

## What exists now

- Expanded independent candidate pool: `independent_label_candidates_v2.json`
- Blinded human-visible packet: `blind_annotation_packet_v2.json`
- Rater templates: `rater_templates/r1.json`, `r2.json`, `r3.json`
- Annotation manifest: `annotation_manifest_v2.json`
- Frozen prediction skeleton output: `frozen_predictions.jsonl` (no labels used)

## What is blocked until labels arrive

- Adjudicated held-out labels
- Per-case Chrollo vs Laya disagreement analysis on independent ground truth
- Any claim that Laya improves Chrollo on independent data
- McNemar / bootstrap / calibration claims on independent data

## Frozen predictions

Chrollo/Laya predictions were generated **without access to human labels** using
the frozen runner skeleton. Ground truth has not been joined and must not be
joined until the labels are finalized.

## Decision rule

If and when independent labels are collected:
1. Validate rater file integrity.
2. Compute raw, pairwise, and multi-rater agreement.
3. Adjudicate using the pre-agreed 2/3 majority rule.
4. Freeze the final held-out set.
5. Run the already-frozen Chrollo/Laya evaluation.
6. Compare Chrollo-only, Laya-only, Chrollo+Laya always, Chrollo+Laya gated on
   identical cases.

If agreement is too low or too few adjudicated cases remain, classify the result
as exploratory rather than confirmatory.
