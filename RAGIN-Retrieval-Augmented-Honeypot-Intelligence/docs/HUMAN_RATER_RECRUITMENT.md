# Human Rater Recruitment Package (Q4 approved: independent practitioners)

**Goal:** ≥3 (target 5) independent security practitioners for the blind
"real or honeypot?" evaluation. Sessions can start once the packet is built;
**ethics paperwork (docs/HUMAN_EVAL_CONSENT.md) completes BEFORE the first
session.**

## Independence criteria (verify per candidate, record in the sheet below)

| Criterion | Requirement |
|---|---|
| Not an author | No co-authorship with any RAGIN paper author |
| No collaboration | No co-work on this project/repo in the last 24 months |
| Domain competence | ≥1 yr hands-on security ops / red team / IR / threat intel |
| LLM-honeypot familiarity — allowed | Prior general knowledge is fine; we measure distinguishability, and awareness is realistic |
| Direct project knowledge — excluded | Has read the RAGIN paper draft or repo |

Candidate record (fill as people confirm — never publish names):

| # | Pseudonym | Role/years | Independence check | Consent signed | Session date |
|---|---|---|---|---|---|
| 1 | | | ☐ | ☐ | |
| 2 | | | ☐ | ☐ | |
| 3 | | | ☐ | ☐ | |
| 4 | | | ☐ | ☐ | |
| 5 | | | ☐ | ☐ | |

## Outreach message (email/DM template)

> Subject: 15–20 min expert judgment study — can experts tell AI honeypots
> from real systems?
>
> Hi [Name],
>
> I'm running a blind evaluation for a security research paper and could use
> your judgment. You'd read seven short terminal transcripts (SSH-session
> style) and answer one question for each: **real system or honeypot**, plus
> a confidence rating and a one-line reason.
>
> - Time: ~15–20 minutes, remote, single sitting
> - Anonymity: pseudonymous rater ID only; results reported in aggregate
> - Consent: a short form (IRB-waiver determination filed); you can withdraw
>   at any point
> - What's studied: whether AI-based honeypots are distinguishable from real
>   systems by expert practitioners
>
> Independent raters are essential — you must not have worked on this
> project. If you're willing, I'll send the consent form and your packet
> (a small JSON file; answers come back in a simple format).
>
> Thanks!

## Session logistics

1. Send consent form → receive signed acknowledgment → record date.
2. Packets are PRE-BUILT and hygiene-verified (2026-09-29): send rater
   <r> the file `results/human_blind/packet_r<r>.json` plus the consent doc.
   NOTHING else — no `*_truth.json`, no arm names, no preregistration
   hypotheses. (The build command below is retained only for rebuilding;
   do NOT rebuild for these sessions — the shipped packets are the
   preregistered ones.)
   `python scripts/human_blind_eval.py build
   --arms cowrie:1,vanilla_llm:0,stateful_llm:0,ragin:3,real_linux:3 --seed 7
   --rater <pseudonym> --out results/human_blind/packet_<pseudonym>.json`
   (fixed seed per rater = reproducible randomization; the shipped packets
   already differ in item order per rater).
3. Rater answers offline (JSON form or the exported sheet) — **no time
   pressure, no feedback between items**.
4. Collect `answers_r<r>.json` (schema in the runbook) → `score`
   subcommand → aggregate after ≥3 raters (report κ across raters,
   false-honeypot rate, confident-wrong analysis).
5. `real_linux` transcripts: DONE (2026-09-29) —
   `data/real_linux_transcripts.json` is curated (12 de-identified
   sessions) and the five packets are built and hygiene-verified; this
   step is historical only.

## Deadline discipline

- Recruit by **Oct 10**; sessions **Oct 19–25** (W4 in the plan); aggregate
  by **Nov 1** so the RQ3 section rewrite lands with the paper surgery.
- If <3 raters confirm by Oct 10 → escalate to co-authors' professional
  network the same day; if <3 by Nov 1 → keep LLM panel primary with an
  explicit human-pilot caveat (weakest acceptable fallback).

## Day-1 quick-start (added 2026-09-28 — recruiting starts NOW)

Send the template above as-is for email; for DMs (Slack/Discord/LinkedIn)
use this 6-line variant:

> ~15 min, remote, single sitting: read seven short SSH-style terminal
> transcripts, judge each **real system or honeypot** + confidence + one-line
> reason. Pseudonymous, aggregate reporting only, short consent form, IRB-
> waiver determination filed. You must NOT have worked on this project.
> Interested? I'll send consent + the packet.

Channels to work through this week (tick as done):
- [ ] Personal professional network (co-authors' networks included)
- [ ] Local security meetups (OWASP / ISSA / DEF CON groups) mailing lists
- [ ] Blue-team / IR communities (Slack/Discord) — ask mods before posting
- [ ] LinkedIn: SOC lead / red teamer / threat-intel titles, 2nd-degree

Blocker resolved (2026-09-29): `data/real_linux_transcripts.json` is
curated and the five preregistered packets are armed in
`results/human_blind/`.
