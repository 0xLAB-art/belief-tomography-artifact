# Blind Real-vs-Honeypot Eval — Operator Runbook

Everything except human raters is ready. This checklist moves the study from
"armed" to "done".

## State (all pre-flight done 2026-09-29)

- [x] Packet builder: `scripts/human_blind_eval.py` (double de-identification:
      capture-side canonical naming + arm-agnostic normalization at build)
- [x] Real-Linux arm: `data/real_linux_transcripts.json` (12 genuine
      de-identified sessions; `scripts/capture_real_linux_transcripts.py`)
- [x] RAGIN arm: `results/human_eval_full.json` raw_pipeline_outputs (8
      verified-loop serves)
- [x] Cowrie arm: scripted corpus loader (`_load_cowrie_command_corpus`)
- [x] 5 packets built + hygiene-verified: `results/human_blind/packet_r{1..5}.json`
      (7 items each = real_linux 3 / ragin 3 / cowrie 1; zero identifying-token
      leaks; per-rater order differs; truth in separate `*_truth.json` files)
- [x] Preregistration committed BEFORE rater contact:
      `docs/BLIND_DISCRIMINATION_PREREGISTRATION.md`
- [x] Score path verified: `human_blind_eval.py score` (accuracy, false-real /
      false-honeypot rates, kappa)

## Recruitment

1. Targets: 5 raters (minimum 4 — below that the study is reported as
   underpowered per the preregistration).
2. Outreach template: `docs/HUMAN_RATER_RECRUITMENT.md` (day-1 quick-start
   section). Point raters at `docs/HUMAN_EVAL_CONSENT.md` first.
3. Each rater gets: their packet JSON + the consent doc. NOTHING else —
   no truth files, no arm names, no the preregistration hypotheses.

## Collection

- Answers format per rater: `results/human_blind/answers_r<r>.json` with
  schema `{"verdicts": [{"id": "<packet id>", "verdict": "real"|"honeypot",
  "confidence": 1-5, "reason": "<free text>"}]}`.
- Collect through a channel that timestamps arrival (email is fine); record
  arrival order in the ops log — needed for the "no cross-rater discussion"
  attestation.

## Scoring (after all packets in)

```bash
for r in 1 2 3 4 5; do
  .venv/bin/python scripts/human_blind_eval.py score \
    --packet results/human_blind/packet_r$r.json \
    --answers results/human_blind/answers_r$r.json
done
```

Then aggregate per the preregistration (pooled exact binomial CI, per-arm
breakdown, kappa). Write results to `results/human_blind/study_results.json`
and reference it from the paper's RQ3 as the discrimination study.

## Paper integration (after scoring)

- RQ3 subsection gains a "Blind discrimination study" paragraph: design
  pointer to the preregistration, pooled detection rate with CI, false-real
  rate on honeypot items, per-arm breakdown.
- The intro contribution bullet on deception quality gains the detection-rate
  number.
- If H1 holds (no above-chance detection): state it as the paper's first
  human-grounded deception evidence, with the pilot-scale caveat.
- If H1 fails: report the failure with the per-arm breakdown honestly — the
  preregistration pre-declares that a cowrie-attributable failure does not
  mask verified-generation performance.

## Known scope limits (documented, not hidden)

- `stateful_llm` and `llm_unverified` packets are deferred: their checkpoints
  predate full-transcript persistence (scores only, no served text). Building
  their packets requires live re-runs under a healthy gateway window; the
  current study compares real Linux vs RAGIN (verified generation) vs cowrie
  (scripted). This is stated in the paper paragraph.
- Pilot scale (5×7). CIs reported, not point claims; underpowered path is
  pre-declared.
