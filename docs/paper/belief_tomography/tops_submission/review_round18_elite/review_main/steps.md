# Investigation steps

Each step records which log entries it targeted, why they were picked at that moment, what was read or computed, and the log operations that resulted. The reading order is driven by the log — unsettled claims and open questions decide where to read next.

**3 steps.**

---

## Step 1 — central claims (C1-C10)

**Why now.** first iteration: log the paper's own assertions before any section is read for evidence

**Action.** Read main.tex abstract, sections/introduction.tex (full), sections/limitations.tex (full), sections/conclusion.tex (full), sections/field.tex L140-220 and L270-390

**Found.** Ten load-bearing claims logged; two candidate inconsistencies observed: (i) Table tab:openweight caption promises 'its row is reported with session-level worst case [0,0.387]' but the E30 V4-Pro row prints [0.099,0.176] and 0.387 is a theory-table constant (theory.tex L486-488), not a censoring bound derivable from 224/300 measured; (ii) Table tab:censor caption says c=103/300 and 66/300 while the row set gives 197/300 and 234/300 fully measured, internally consistent, but the E2 lane's 103/300 session-censored vs 117/400 turn-censored pair needs a units sentence in the same paragraph.

**Log operations.**

- `add_claim C1-C10`

---

## Step 2 — C11, Table 6 censoring cells

**Why now.** caption printed a bound that did not match its own stated denominator; verify against raw transcripts before accepting

**Action.** Counted blocked turns/sessions in E30/E31 transcripts.jsonl; recomputed per-family c

**Found.** E30 V4-Pro: 76/300 sessions censored (0.253), not 0.387; E31 MiniMax state-dec 12/60=0.200 verified exactly; E31 V4-Pro authority 27/60=0.450 verified; E30 MiniMax 305/400=76.25% verified; E31 MiniMax 24/400=6.0% verified.

**Log operations.**

- `add_claim C11`
- `update_claim C11 invalid`

---

## Step 3 — C12-C15

**Why now.** humanizer seat returned four presentation/integrity findings; each is cheap to settle against the class file, a recomputation, or a count

**Action.** grep IEEEtran.cls for secnumdepth/theparagraphdis; pdftotext pp.5,20; counted abstract words; recomputed Wilson-Holm bound with scipy

**Found.** All four confirmed: 38 lettered-and-doubled run-in heads; 0.1135 should be 0.1136 (0.113594); 'reproduces every number' contradicted by two disclosed manuscript-side computations; abstract 500 words vs the 250-word IEEE norm.

**Log operations.**

- `add_claim C12-C15`
- `update_claim C12 invalid`
- `C13 invalid`
- `C14 weak`
- `C15 invalid`

---
