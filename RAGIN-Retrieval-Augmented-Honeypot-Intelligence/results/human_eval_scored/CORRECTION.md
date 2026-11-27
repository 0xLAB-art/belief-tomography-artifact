# Correction — results/human_eval_scored/ (2026-10-24)

This correction was recorded by the 2026-10-24 full verification audit. No
numeric data was altered anywhere; only provenance metadata and labels.

## What is wrong in this directory

1. **`consensus.json` does not derive from the sibling evaluator files.** Its
   former note claimed "Rebuilt from per-evaluator JSON files", but its embedded
   per-scenario scores match `evaluator-{alpha,beta,gamma}.json` in 0 of 14
   comparable rows (10 of 24 evaluator pairs could not be compared at all
   because they contain parse errors / timeouts). The note was false and has
   been replaced with a correction note plus a `superseded_by` pointer.
2. **Model mismatch.** `consensus.json` meta declares `openai/gpt-4o-mini`
   while the evaluator files in this directory record `qwen--qwen38-27b`.
3. **This directory is superseded.** The authoritative LLM-judge consensus is
   `results/human_eval_scored_20260922_180637_consensus/consensus.json`
   (mean 3.86/5, agreement 0.750, 8/8 scenarios ≥ 3; its embedded scores match
   its evaluator files 24/24). Do not cite this directory.

## Scope note on the whole evaluation chain

- **All evaluators in the entire chain are LLM personas, not humans.** This
  directory's evaluators are `qwen--qwen38-27b` (three labels, one model); the
  authoritative 2026-09-22 run's evaluators are `grok-4.7-free` (three
  personas, one model). No human rater scored any scenario anywhere in this
  repository.
- The blind human discrimination packets (`results/human_blind/packet_r1..r5.json`,
  real-Linux vs RAGIN vs Cowrie transcripts) were prepared and delivered but
  **never answered**: `human_returns/` contains no rater data as of 2026-10-24.
- Any document calling these numbers a "human eval" has been relabelled to
  "LLM-judge evaluation" by the same audit pass.
