# Investigation steps

Each step records which log entries it targeted, why they were picked at that moment, what was read or computed, and the log operations that resulted. The reading order is driven by the log — unsettled claims and open questions decide where to read next.

**2 steps.**

---

## Step 1 — central claims intake

**Why now.** First iteration: log the paper's central empirical claims before evidence gathering

**Action.** Read abstract+contributions of paper.md; logged C1-C7 and Q1-Q2

**Found.** Claims stated in §1 contributions list tied to section refs

---

## Step 2 — C1-C7, Q1, Q2

**Why now.** All logged entries settled: artifact verification of instrument + field + disclosure numbers, then structural verification of theorem wiring and proof coverage

**Action.** Grepped/loaded dose_response.json, e17_audit_calibration.json, e5_onset.json, E2_RESULTS_V1.md, E3_DECEPTION_GAIN.md, E18/E20 MDs; pdftotext pass over main.pdf for theorem numbers and appendix subsections

**Found.** Every claimed number present in the frozen artifacts; theorem references all resolve; no dangling open-problem refs; Spearman 1.00 confirmed

---
