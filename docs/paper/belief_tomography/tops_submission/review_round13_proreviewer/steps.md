# Investigation steps

Each step records which log entries it targeted, why they were picked at that moment, what was read or computed, and the log operations that resulted. The reading order is driven by the log — unsettled claims and open questions decide where to read next.

**5 steps.**

---

## Step 1 — C1-C6, Q1-Q3, N1

**Why now.** First iteration: extracted central claims from abstract and contributions; four parallel child reviewers now gathering per-chunk evidence

**Action.** Read paper.md lines 1-90 (title, abstract, ACM ref, Section 1, 1.1 RQs, 1.2 contributions, start of Section 2); logged 6 central claims, 3 questions, 1 note

**Found.** Front matter carries: charter/belief-gap framing; six RQs each mapped to sections; five contributions with numbers; 'program in three layers' paragraph. Abstract states both self-caught errors and the spectrum result. Fig 1 caption carries per-family gap deltas and pooled 0.933 vs 0.600.

**Log operations.**

- `add_claim x6`
- `add_question x3`
- `add_note x1`

---

## Step 2 — C1,C2,C3,C4

**Why now.** Abstract/intro empirical claims need verification against instrument (Sec 5) and field (Sec 6) sections

**Action.** Read paper.md lines 369-407 (Sec 5.3-5.6), 505-520 (Sec 6.2), 476-504 (open-weight panels + Table 5), 578-600 (E21/E7/E8); grepped for 986/949/960/0-25/060/143/700/5-60/0-60/200-token; computed Wilson upper for 0/60

**Found.** All abstract validity and field numbers exact-match the body; [0,0.060] is exactly the two-sided 95% Wilson upper for 0/60 (300 sessions = 60/family); third error instance (E30 200-token cap) exists in body, making 'two' class-level counting

**Log operations.**

- `C1->supported`
- `C2->supported(caveat)`
- `C3->supported`
- `C4->supported`

---

## Step 3 — C5,C6,C7,C8,Q1,Q4

**Why now.** Theory pointer ranges, layer summary, and version desync needed verification; tex read for exact wording

**Action.** Grepped all Theorem/Proposition/Corollary 4.x-8.x references in paper.md and mapped to actual objects (Thm 7.4 line 606, Cor 7.5 line 610); diffed paper.md intro against introduction.tex (adversary sentence, Table 1, contribution 4 framing); grepped references.tex for situational/secret/sleeper; web-searched LLM Agent Honeypot 8.1M figure

**Found.** 'Propositions 7.3-7.8' and 'Theorems 7.4/7.5' mislabel object types; paper.md layer summary leaves 9 experiment IDs unplaced and lacks the tex Table 1; paper.md intro omits adversary sentence that tex has; cited honeypot paper says 'eight million SSH interactions' not sessions

**Log operations.**

- `C5->weak`
- `C6->weak`
- `C7 added->invalid`
- `C8 added->invalid`
- `Q1->resolved`
- `Q4 added->resolved`

---

## Step 4 — C1-C6, Q1-Q3 + per-chunk defect consolidation

**Why now.** Four parallel specialist reviewers reported; consolidate their findings, verify each critical defect against current tex (PDF was stale - tex already fixes several front findings)

**Action.** Grepped current sources for each critical finding: Cor 7.1 'complies' (limitscert:82 - present), discussion 'registered field breaches' (discussion:42 - present), 7.1 lower-bound rule (limitscert:28 - present), Thm 4.7(iii) flipped inequality (appendix:111 - present), Hoeffding misattribution (appendix:121 - present), E27 60-vs-30 (field:341 - present), v0 contradiction (field:69 vs 99 - present), 301 processes (field:95), 1230 corpus (field:269, instrument:29), resp. 11-22 (field:244), 8.1M sessions (related:117), most-cited (related:13), Theorems-vs-corollary labels (related:121, introduction:116), Treason Bricken + Binkyte (references:547,108).

**Found.** All flagged defects confirmed live in sources except those the newer tex already fixed (adversary sentence, four-layer table, contribution-4 retitle). Logged 7 new claims (C7-C13) with statuses from evidence; resolved C1-C6, Q1-Q3.

**Log operations.**

- `update_claim x12`
- `add_claim x6`
- `add_note x2`
- `resolve_question x3`
- `step x1`

---

## Step 5 — C7-C15

**Why now.** Straighten statuses after ID collision with child-written entries; each defect verified directly in current tex

**Action.** Greps across sections/*.tex and references.tex as recorded per claim

**Found.** All defects confirmed: cross-ref types, three-layer summary (already fixed in tex), Cor 7.1 'complies', Sec 9 'field breaches', Sec 7.1 rule, Table 3, E27 n, Sec 5.1 verbatim, bibliography. Statuses and reasons now aligned.

**Log operations.**

- `update_claim x9`

---
