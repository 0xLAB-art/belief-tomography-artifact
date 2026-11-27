# Investigation steps

Each step records which log entries it targeted, why they were picked at that moment, what was read or computed, and the log operations that resulted. The reading order is driven by the log — unsettled claims and open questions decide where to read next.

**2 steps.**

---

## Step 1 — C1,C2,C4

**Why now.** Gatekeeper novelty/title/churn attacks on the pitch

**Action.** Read abstract, §1, §2, §9, §11 plus §5.6/§6.1/§7.1/§8 spot reads; grepped ASR/spectrum/certification; recomputed Fig 1b Wilson bounds and Table 6 pooled intervals

**Found.** Rebranding attack fails (line 186 delta statement); churn story disclosed (E2-v1b line 513); certification instantiated on production in Table 5. Statistics recompute exactly

**Log operations.**

- `C1 supported`
- `C2 supported`
- `C4 supported`

---

## Step 2 — C6,C7,N2,N3

**Why now.** Artifact-driven integrity checks - the gatekeeper's most decisive evidence

**Action.** Read E2_RESULTS_V1.md, E29_REPAIRED_PANEL.md, E29_E30_ORACLE_AUDIT.md, E17 audit artifacts, PREREGISTRATION list; cross-checked paper text disclosure of each

**Found.** Registered >=6 vs executed 2 panel undisclosed in text (C6); final adjudications author-side non-blind per artifact, qualifier absent from text (C7); all Wilson intervals recompute; E17 FP bound pre-printed

**Log operations.**

- `C6 weak`
- `C7 weak`
- `N2 recorded`
- `N3 recorded`
- `N4 recorded`

---
