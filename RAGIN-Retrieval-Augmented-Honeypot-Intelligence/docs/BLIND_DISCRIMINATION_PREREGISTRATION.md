# PREREGISTRATION — Blind Real-vs-Honeypot Discrimination Study

**Registered:** 2026-09-29, before any rater contact. Committed before data
collection begins; any amendment after collection starts must be logged in the
Amendments section with a timestamp.

## Design

Binary blind discrimination. Each rater independently labels transcripts as
REAL (a genuine Linux session) or HONEYPOT (a deception system's output),
without knowing the arm inventory, the systems compared, or the mixture ratio.
Raters see only transcript text; hostnames/usernames are normalized to a
canonical shape by the packet builder so naming style cannot fingerprint an
arm; session counts and provenance metadata are absent by construction.

## Arms and materials

| Arm | Source | Items per packet |
|---|---|---|
| real_linux | `data/real_linux_transcripts.json` — 12 genuine sessions recorded by `scripts/capture_real_linux_transcripts.py` on a real Linux host; read-only commands; de-identified (allowlist-based ps/ss/df/env filters, honest permission errors, hidden files dropped) | 3 |
| ragin | `results/human_eval_full.json` raw_pipeline_outputs — verified-loop serves from the 8 ground-truth scenarios | 3 |
| cowrie | scripted Cowrie session shape from the captured corpus | 1 |

7 items per packet (3 real / 4 honeypot), order shuffled per rater with a
fixed seed (seed 7, rater-keyed) for reproducible randomization.

## Hypotheses (pre-registered)

- **H1 (primary):** raters cannot distinguish real from honeypot above chance
  across the mixed packet. Operationalized as: per-rater accuracy's 95%
  binomial (Clopper–Pearson) interval includes 0.5, and pooled accuracy's CI
  lower bound is below 0.65.
- **H2 (secondary):** honeypot-armed items are judged REAL at ≥ 50%
  (false-"real" rate ≥ 0.5 on honeypot items) — the deception-direction
  metric: a honeypot that is *believed* scores high here.
- **H3 (secondary):** real-Linux items are correctly judged REAL at ≥ 70%
  (low false-"honeypot" rate on genuine sessions) — the safety-direction
  metric: the system does not teach raters that everything is fake.

H1 failure (detection significantly above chance) does not invalidate the
system: per-arm breakdown is pre-declared so that a failure attributable to
the scripted cowrie arm (static, no outputs) does not mask verified-generation
performance. All arms are reported; no arm is dropped post hoc.

## Sample and power

Target 5 raters × 7 items = 35 judgments (21 honeypot, 14 real pooled).
Exact binomial power at n=35, α=0.05, true accuracy 0.70: ≈ 0.72; at 0.75:
≈ 0.86. This is a small pilot-scale study; we pre-declare it as such and
report CIs rather than point-claim significance. If fewer than 4 raters
complete, the study reports per-rater intervals only and is labeled
underpowered.

## Metrics

- Per-rater accuracy with exact binomial 95% CI.
- Pooled accuracy with exact binomial 95% CI.
- False-"real" rate on honeypot items (deception direction).
- False-"honeypot" rate on real items (safety direction).
- Per-arm breakdown (real_linux / ragin / cowrie).
- Cohen's κ across raters on the binary verdict (pooling items; κ is
  computed pairwise and averaged).
- Mean confidence per arm; correlation between confidence and correctness
  (pre-declared as exploratory).

## Procedure

1. Raters receive only `packet_<rater>.json` (no truth file, no arm names).
2. Raters answer every item: verdict, confidence 1–5, free-text reason.
3. Answers returned as JSON matching the `score` subcommand's schema
   (`{"verdicts": [{"id", "verdict": "real"|"honeypot", "confidence": 1-5,
   "reason": "..."}]}`).
4. Scoring exclusively via `scripts/human_blind_eval.py score`.
5. Raters do not see other raters' answers until all packets are in.

## Analysis plan

Primary analysis: pooled + per-rater accuracy with exact CIs; per-arm
breakdown; κ. All computed by the released scorer; no manual aggregation.
No post-hoc items, arms, or metrics will be added after unblinding.

## Ethics

Raters are domain-adjacent volunteers (security students/practitioners);
participation per `docs/HUMAN_EVAL_CONSENT.md`; no compensation beyond
acknowledgment; no personal data collected beyond a self-chosen rater alias;
answers stored in `results/human_blind/` with the blinding key discipline of
the CTI audit (researcher-held truth files, never distributed).

## Amendments

(none yet — must be timestamped if used)
