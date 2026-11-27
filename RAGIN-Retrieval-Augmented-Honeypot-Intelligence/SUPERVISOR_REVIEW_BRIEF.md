# Supervisor Review Brief — The Intelligence Ladder (v3, 2026-09-24)

**Paper:** `paper/main.pdf` — 20 pages, IEEEtran journal format
**Also at:** `https://github.com/0xzodiac/The-Intelligence-Ladder` (paper + full artifact tree)
**Requested by:** Anonymous — review before any submission decision.
**Reviewed copy:** commit `60f1c9a`, PDF SHA-256 starts `c05cc089d6625093`.

---

## What changed since v2 (2026-09-23)

The v2 draft was reviewed against a supervisor critique along four axes
(storytelling, figures, balance, structure). All six work items landed; this
version is the post-rework paper:

1. **Fresh opening (was: self-reuse).** The introduction no longer opens by
   quoting the ESWA submission's abstract; it opens with a concrete
   serving decision and earns the ladder framing from it.
2. **The reject path is walked, not asserted.** §III now follows one session
   through identity-pin rejection, the retry contradiction, and the
   deterministic fallback, with the fiction state byte-identical across the
   swap — the failure story reviewers asked for.
3. **Five figures (was: two tables and no figures).** New: the ladder itself
   (Fig. 1), the fold-down evidence funnel for RQ4 (Fig. 5), and the paired
   grounding effect with CIs (Fig. 4); the architecture (Fig. 2) and results
   (Fig. 3) figures kept.
4. **Headlines now match their evidence.** The RQ4 claim is stated at the
   benchmark's resolution ("no measurable advantage over a deterministic
   decision floor"); the abstract and introduction carry the same softening.
5. **§III slimmed; formal material split out.** New §IV "Formal Properties
   and Adversarial Analysis" holds the serving-path consistency invariant
   (with proof sketch), the loop algorithm block, and the attack analysis
   moved verbatim out of the design section.
6. **Figures are audited like the numbers.** New Appendix F + a replayable
   auditor (`scripts/audit_figure_geometry.py`): every figure is re-rendered
   in isolation and scanned for ink crossing node interiors; the version of
   record passes with zero crossings (73 long runs inventoried, all
   resolving to declared geometry). Artifact:
   `results/figure_geometry_audit.json`.

## Page map (verified against the reviewed PDF)

| Pages | Content |
|---|---|
| 1–2 | Abstract, Introduction (fresh opening scene, RQ1–4, contributions) |
| 3–4 | Background, threat model, design goals G1–G5 |
| 5–7 | §III The verified deception loop; ladder (Fig. 1, p6); architecture (Fig. 2, p7); reject-path walkthrough |
| 8 | §IV Formal properties (consistency invariant + proof sketch, algorithm) and adversarial analysis |
| 9 | §V Implementation |
| 10–13 | §VI Evaluation: RQ1 grounding (Fig. 4, p11; +0.154 composite), RQ2 campaign (Fig. 3, p10), judge audit, RQ3 consensus, RQ4 pricing + census funnel (Fig. 5, p13), stability |
| 14 | §VII Discussion: pricing, deployment guidance, limitations |
| 15–16 | §VIII Related work; §X Conclusion (+ repo URL); author bio |
| 17 | References; Appendix A (artifacts) |
| 18–19 | Appendices B (reproduction), C (rubrics + judge protocol), D (scenarios), E (audit records) |
| 20 | Appendix F (figure geometry audit) |

## Decisions requested from the supervisor

1. **Framing sign-off.** The ladder/certifiability device remains the
   contribution; the rework sharpened it rather than changing it. Confirm.
2. **Venue.** TDSC was the working target; the paper is now 20 pages with
   appendices A–F (v2 was 18). The likely trim candidates for a camera-ready
   are Appendices C–D (rubric anchors, scenario suite) and parts of E;
   Appendix F is short and defends the figures. T-IFS remains the
   alternative. Recommend one.
3. **The honest-null stance.** Unchanged from v2: the dwell-time null, the
   resolution bound on the fold-down, and the provider-refusal finding are
   reported as results. The RQ4 headline is now softer than v2 — confirm the
   weaker phrasing still reads as a contribution, not a retraction.
4. **Authorship/metadata.** Single author; repository history is unified to
   the owner identity (`youseefhamdi`). Confirm before submission.

## Open items (not blocking review)

- "Manuscript received XXX" footers need filling at submission time.
- Appendix B's reproduction sequence now ends with step 7, the figure
  geometry audit (`scripts/audit_figure_geometry.py`; needs pdflatex,
  pdftoppm, Pillow; no network).
- If TDSC: decide what moves to a supplementary package vs. stays inline.

## Reproducing the numbers

Every claim links to a persisted artifact; Appendix B lists the exact
command sequence. Deterministic batteries run offline; only the live
campaign needs provider quota. The figure audit is offline and deterministic
step 7 of the same listing.

— Prepared 2026-09-24; PDF hash of reviewed copy (SHA-256, first 16 hex):
`c05cc089d6625093` at commit `60f1c9a`.
