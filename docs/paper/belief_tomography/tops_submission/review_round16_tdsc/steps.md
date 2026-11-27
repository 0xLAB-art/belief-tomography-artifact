# Investigation steps

Each step records which log entries it targeted, why they were picked at that moment, what was read or computed, and the log operations that resulted. The reading order is driven by the log — unsettled claims and open questions decide where to read next.

**8 steps.**

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

## Step 3 — Q1,Q2,Q4,C3

**Why now.** Page-2 survival, claim-calibration and figure audit drive the upgrade pass

**Action.** Read abstract+p1-2 PDF text; grepped marketing adjectives and throat-clearing; enumerated figure envs vs refs

**Found.** Ethics signal absent from p1-2; claims fully calibrated; 3/5 figures unreferenced; captions otherwise strong

**Log operations.**

- `resolve Q1,Q2,Q4`
- `support C3`

---

## Step 4 — paper-wide structural diff

**Why now.** Manuscript changed after round-15 review; needed the precise upgrade map before any claim verification

**Action.** diffed round-15 paper.md vs fresh init conversion of paper/tops/main.tex; read all 1399 diff lines against the round-15 findings checklist

**Found.** Every round-15 defect has an apparent text fix: Thm 4.8 restated with Delta_beta_d=1.84 rho_0 and M* closed form; E5 reframed as falsified-registration + post-hoc reading; honest registration ledger paragraph with per-experiment offsets and post-hoc-edit disclosure; (A3) axiom for Prop 7.3; Table 6 pools + censoring disclosed; canned-string disclosure; ethics rescoped to three environments; ledger+manifest promised by filename; bibliography repaired; appendix proofs rewritten with corrected power analysis

**Log operations.**

- `add_claim C1-C18`
- `add_question Q1-Q16`
- `add_note N1`

---

## Step 5 — C2,C3,C4,C5,Q14,Q15

**Why now.** Theory layer was rewritten for round-16; the theorem arm carries the paper's central falsifiable claims, so it needed from-scratch re-derivation plus E5-artifact verification

**Action.** Dispatched independent theory referee: re-derived power algebra, M* closed form, exact binomial UMP power at both middle cells, Table 2 columns, rem:sens identity, (A3) proof; located gate code in run_e5_onset.py; verified e5_onset.json values point-by-point; checked registration git precedence (8ceb6e0 vs c75bdcc)

**Found.** Restated theory substantially sound: all printed constants recompute; direction fixes correct; E5 chain verified. Two substantive defects (M*-finiteness iff false at vbar>p(1-p); 'exact UMP 0.85' is 0.8074 at (40,0.2), misprinted as 0.85 twice); one frozen-record misquote (birth delta=0.2 0.431-0.529 printed as 0.501-0.529); stale intro 'checked empirically' sentence; Remark 4.3 compile collision; z-notation contradiction; dangling §4.4 quantification promise

**Log operations.**

- `update_claim C2 supported`
- `C4 weak`
- `C5 supported`
- `C3 weak`
- `resolve Q14`
- `resolve Q15`
- `add_note N2`

---

## Step 6 — C7,C9,C10,C12,C13,C14,C15,C16,Q1,Q2,Q3,Q5,Q6,Q9,Q12

**Why now.** The upgrade vouches specific deposit files by name and prints new counts/bounds; a TDSC review must verify reproducibility claims against the actual deposit before accepting them

**Action.** Dispatched forensic ledger ref: sha256 verification of all manifest entries, blocked-turn recount across 11 panels, 230-flag recount from raw verdict JSONLs, canary-verbatim regex, Table 6 cell recount, E4/E26 artifact checks, EPK json checks, git-history re-verification of every registration offset quoted in the limitations paragraph

**Found.** Ledger+manifest REAL and hash-verified 382/382 (round-15 reject-grade defect 4 resolved); canned-turn counts recount exactly; Table 6 and E17 numbers verified; EPK verified except detector 2/2 understated (gen-1 4/4); registration ledger honest except: E22 clean-list placement unsupported (single same-commit as data, future-dated header undisclosed), E15/E16/E26 disclosed only in ledger not paper, E14 same-commit overstated, stale artifact typo '89 of 700' unfixed

**Log operations.**

- `update_claim C7,C9,C10,C12,C13,C14,C15,C16`
- `resolve Q1,Q2,Q3,Q5,Q6,Q9,Q12`
- `add_note N3`

---

## Step 7 — C1,C6,C8,C11,C18,Q4,Q7,Q8,Q10,Q11,Q16

**Why now.** Fresh-eyes line audit of the upgraded manuscript text was required after the theory/ledger panels — the upgrade fixed the round-15 big four but needed an independent read for what it broke or left dangling

**Action.** Dispatched fresh-eyes referee: line-audited all sections + cover letter + references (residual-claim greps per experiment, figure captions vs descriptions, numbers cross-occurrence table 25+ values, ethics scoping); cross-checked against the two forensic panels' artifact findings

**Found.** 24/6 split consistent; E18, Fig 3, fig3 collision, platform appendix, E3 ledger mapping, prompt-hygiene 1200/1600, TV preamble all fixed. Fresh defects: Fig 2 birth-onset range misquote vs frozen artifact and its own Description; E17 reverse-containment claim; intro/Table-1 layer-registration scope contradicts the paper's own ledger (E20/E21/E22-entry, E15/E16); E15/E16/E26 silent in the paper though ledger-disclosed; E23 'before data' unsupported; [0,5.7%] CI mislabel; discussion.tex 'author owns' residue; no TOU/banner text; cover letter describes the OLD paper (title/v5/null framing); Mahran-Marks sort error; my own arXiv verification shows the Rewoor fix mismatched the source metadata

**Log operations.**

- `update_claim C1,C6,C8,C11,C18+C19,C20,C21,C22`
- `resolve Q4,Q7,Q8,Q10,Q11,Q16`

---

## Step 8 — C17,C19,C20,C21,C22

**Why now.** Exit-condition sweep: settle the last unsettled claims and verify the two remaining unverified numbers (6.0% censoring denominator, bibliography source match)

**Action.** Recounted E31 MiniMax transcripts (400 turns, 24 blocked = 6.0%); fetched arxiv.org/abs/2410.13919 to settle the Rewoor/Reworr question; chair's read of abstract + conclusion for coherence

**Found.** 6.0% exact; abstract/conclusion coherent with the upgraded body; arXiv lists 'Reworr' — the fix introduced the metadata mismatch; all claims now carry final statuses

**Log operations.**

- `update_claim C17,C19,C20,C21,C22`

---
