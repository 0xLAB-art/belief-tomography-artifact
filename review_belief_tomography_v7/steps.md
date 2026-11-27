# Investigation steps

Each step records which log entries it targeted, why they were picked at that moment, what was read or computed, and the log operations that resulted. The reading order is driven by the log — unsettled claims and open questions decide where to read next.

**2 steps.**

---

## Step 1 — round-14 setup

**Why now.** Second-pass adversarial review requested by the author on the upgraded manuscript

**Action.** Fresh init on the round-13-upgraded PDF; seeded 7 load-bearing claims + 1 question + context note; spawned four adversarial reviewers (theory hawk, stats skeptic, rigor/ethics auditor, journal gatekeeper) with reject-by-default mandates

**Found.** PDF converts cleanly; all round-13 fixes visible in the converted text

**Log operations.**

- `add_claim x7`
- `add_question x1`
- `add_note x1`
- `step x1`

---

## Step 2 — Whole paper v7 under the four-reviewer adversarial panel (gatekeeper, theory hawk, stats skeptic, rigor auditor), reject-by-default rules of engagement, round-13 fixed points excluded

**Why now.** User asked for the harshest possible adversarial re-review of the upgraded v7 manuscript

**Action.** Four parallel specialist child reviewers reviewed their chunks against the frozen artifacts; the review consolidator then independently re-verified every reject-grade and major finding from the primary sources

**Found.** Panel: 2 Reject (theory 4/5, stats 5/5), 1 Borderline→Accept (gatekeeper 4/5), 1 Accept-conditional (rigor 4/5). All four confirm the statistics reproduce exactly; the surviving defects are theory misprints (T1/T2), preregistration provenance (P1/W1), estimand/disclosure hygiene (P2/P4/P5/G1/G2/W4), and the absent claims ledger (W2)

**Log operations.**

- `update C1=weak,C2=weak,C3=invalid,C4=supported,C5=weak,C6=supported,C7=invalid`
- `add_claim C8-C10`

---
