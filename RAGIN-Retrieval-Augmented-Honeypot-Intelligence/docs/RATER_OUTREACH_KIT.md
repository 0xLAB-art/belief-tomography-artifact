# Rater Outreach Kit — ready-to-send (2026-09-29)

Preregistered study: `docs/BLIND_DISCRIMINATION_PREREGISTRATION.md`.
Operator checklist: `docs/BLIND_DISCRIMINATION_RUNBOOK.md`.
Ethics: `docs/HUMAN_EVAL_CONSENT.md` (updated to the 7-item / 15–20 min reality).
**All five packets are armed in `results/human_blind/` — no build step needed.**

## Before sending anything (one-time)

1. Fill the independence table in `docs/HUMAN_RATER_RECRUITMENT.md` per candidate
   (no co-authorship, no project collaboration in 24 months, ≥1 yr security ops,
   has NOT read the draft/repo). Record the check, not the identity.
2. Move `results/cti_audit_blinding_key.json` out of the repo tree into the
   private ops store BEFORE any rater has the repo path (owner: USER).
3. Send each packet from a channel that timestamps arrival (email is fine) and
   log the send/receive times in the ops log — the score aggregate needs the
   "no cross-rater discussion" attestation with times.
4. Stagger sends within a 24–48 h window so no rater can compare notes first;
   collect independently (runbook §Collection).

## The five send-ready emails

Each rater gets: the email below + `packet_r<r>.json` + `HUMAN_EVAL_CONSENT.md`.
NEVER attach: `*_truth.json`, arm names, the preregistration hypotheses.

### r1 — [Name 1]

> Subject: 15–20 min expert judgment — can you tell an AI honeypot from a real box?
>
> Hi [Name],
>
> I'm running a blind evaluation for a security research paper and could use
> your judgment. You'd read seven short terminal transcripts (SSH-session
> style) and answer one question for each: **real system or honeypot**, plus a
> confidence rating (1–5) and a one-line reason.
>
> - Time: ~15–20 minutes, remote, single sitting
> - Anonymity: pseudonymous rater ID only; results reported in aggregate
> - Consent: short form attached (IRB-waiver determination filed); withdraw anytime
> - What's studied: whether AI-based honeypots are distinguishable from real
>   systems by expert practitioners
>
> Two ground rules from the study design: please don't discuss the items with
> anyone before sending your answers, and answer in one sitting if you can.
>
> Independent raters are essential — you must not have worked on this project.
> If you're in, I'll send the consent form and your packet (a small JSON file;
> answers come back in a simple JSON format I'll include).
>
> Thanks!

### r2 — [Name 2]
Use the r1 text verbatim, replacing name/number. Personalization beyond the
greeting is intentionally excluded so no rater can infer a different protocol.

### r3 — [Name 3]
Same template. (If a candidate asks about the AI-honeypot literature, answer
AFTER their answers arrive; log the exchange.)

### r4 — [Name 4]
Same template.

### r5 — [Name 5]
Same template.

### DM variant (Slack/Discord/LinkedIn — ask mods before posting)

> ~15 min, remote, single sitting: read seven short SSH-style terminal
> transcripts, judge each **real system or honeypot** + confidence + one-line
> reason. Pseudonymous, aggregate reporting only, short consent form, IRB-
> waiver determination filed. You must NOT have worked on this project.
> Interested? I'll send consent + the packet.

## Tracking table (mirror into the recruitment doc as raters confirm)

| Rater | Packet | Independence ✓ | Consent sent | Consent back | Packet sent | Answers received | Answers file |
|---|---|---|---|---|---|---|---|
| r1 | packet_r1.json | ☐ | ☐ | ☐ | ☐ | ☐ | answers_r1.json |
| r2 | packet_r2.json | ☐ | ☐ | ☐ | ☐ | ☐ | answers_r2.json |
| r3 | packet_r3.json | ☐ | ☐ | ☐ | ☐ | ☐ | answers_r3.json |
| r4 | packet_r4.json | ☐ | ☐ | ☐ | ☐ | ☐ | answers_r4.json |
| r5 | packet_r5.json | ☐ | ☐ | ☐ | ☐ | ☐ | answers_r5.json |

## Answers format to include in every packet email

> Reply with a JSON file named `answers_r<r>.json`:
>
> ```json
> {"verdicts": [
>   {"id": "<item id>", "verdict": "real" | "honeypot",
>    "confidence": 1, "reason": "<one line>"}
> ]}
> ```
>
> One entry per transcript, `id` copied from the item header. Confidence 1–5.
> Please don't rename items or reorder entries.

## After collection (mechanical, no judgment)

```bash
for r in 1 2 3 4 5; do
  .venv/bin/python scripts/human_blind_eval.py score \
    --packet results/human_blind/packet_r$r.json \
    --answers results/human_blind/answers_r$r.json
done
```

Aggregate per the preregistration: H1 exact binomial, H2/H3 rates, pooled κ.
Report the underpowered path exactly as pre-declared if <5 raters land.

## Status snapshot

- Packets armed: 5 × 7 items (3 real_linux / 3 ragin / 1 cowrie), hygiene-verified.
- Consent doc: synced to the shipped protocol (7 items, 15–20 min).
- Outreach: READY — nothing sent yet (waiting on independence checks + consent copy).
- Blocker removed this pass: recruitment doc previously promised a 40-item,
  45–60 min session with rating fields that the shipped packets and scorer do
  not implement; everything now matches the preregistered protocol exactly.
