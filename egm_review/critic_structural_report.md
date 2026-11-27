# Structural Review — RAGIN paper (EGM, Structural Goldfish)

- **TargetFile**: `/home/elaref/Documents/research/ragin/paper/main.tex` (2,144 lines)
- **FeatureRange under review**: lines 1..1124 (preamble/frontmatter, Section 1 Introduction, Section 2 Related Work, Section 3 System Architecture, Section 4 Experimental Setup). Whole-file outline inspected for context; out-of-range items are labeled as such.
- **Stated venue**: IEEE S&P 2027 submission.
- **Verification performed**: full label/ref cross-check (132 refs, 73 labels), cite/bibliography cross-check (47 bibitems), compile-log inspection, figure-file existence check, section-length balance analysis.

Priority legend: 🔴 Blocker · 🟡 Major · 🟢 Nit

---

## 1. Structural Map (extracted outline)

| Section | Lines | Length | Subsections |
|---|---|---|---|
| Frontmatter + Nomenclature | 1–109 | 109 | — |
| 1 Introduction | 111–317 | 207 | 7 sub (+2 subsub under "What This Paper Argues") |
| 2 Related Work | 318–527 | 210 | 6 sub (incl. Threat Model, Gap Summary) |
| 3 System Architecture | 528–1006 | 479 | 6 sub |
| 4 Experimental Setup | 1007–1124 | 118 | 4 sub, 4 subsub |
| 5 Implementation Details (out of range) | 1125–1239 | 115 | 5 sub, 4 subsub |
| 6 Results and Analysis (out of range) | 1240–1737 | 498 | 8 sub |
| 7 Discussion (out of range) | 1738–1932 | 195 | 6 sub |
| 8 Future Research Directions (out of range) | 1933–1957 | 25 | 0 |
| 9 Conclusion (out of range) | 1958–1981 | 24 | 0 |
| Backmatter (out of range) | 1983–2144 | — | CRediT, GenAI declaration, Competing Interest, Data Availability, Funding, Acknowledgments, Ethical Statement, 47-item thebibliography |

Numbering of figures (7) and tables (16) is sequential in source order; all `\includegraphics` targets exist (`figure1_pipeline.png`, `figure2_latency.png`, `figure4_audit.png`, `figure5_kpis.png`, `figure6_ttp_density.png`, `figure7_techniques.png`; the Figure-3 slot is the inline TikZ `fig:dataflow`, so the file-name numbering is internally consistent).

---

## 2. Findings — In-Range (lines 1..1124)

### F1. 🔴 Document class and backmatter do not match the target venue (IEEE S&P)
- **Scope**: line 1 (`\documentclass[preprint,12pt]{elsarticle}`), lines 26–76 (frontmatter), 1983–2044 (out-of-range backmatter).
- **Description**: The paper is typeset in Elsevier's `elsarticle` journal format (single column, 12 pt preprint, `\nonumnote`, `\begin{keyword}...\sep`, CRediT statement, Declaration of Competing Interest). IEEE S&P requires the IEEE conference two-column template (`IEEEtran`), with its own length limits, no CRediT/Competing-Interest blocks, and frontmatter via `\maketitle`/`\author{\IEEEauthorblockN{...}}`. Every Elsevier-specific construct will have to be rebuilt. This is the single largest structural item: it affects page budget for every section (a 2,144-line single-column preprint will not map 1:1 into the S&P 13-page + refs format), not just the preamble.

### F2. 🔴 Ethics material present but structurally misplaced for S&P
- **Scope**: lines 2036–2044 (out-of-range starred `\section*{Ethical Statement}` after Acknowledgments), and line 480–483 (in-range `\paragraph{Jurisdictional note}` buried at the end of the Threat Model subsection of Related Work).
- **Description**: The paper runs a live internet-exposed honeypot engaging real third-party attackers plus a blind red-team exercise — exactly the class of work S&P expects a visible, prominent ethics discussion for. The content is adequate (own infrastructure, no initiation of contact, IP hashing, authorization for the red team), but its placement — an unnumbered section after Acknowledgments, with a jurisdictional footnote-paragraph buried inside §2.5's threat model — is weak. For S&P this should be a numbered, clearly findable section (e.g., "Ethical Considerations" before or after the threat model) rather than end-matter. Structural finding: the element exists, its location does not.

### F3. 🟡 Threat Model is a subsection of Related Work
- **Scope**: line 436 (`\subsection{Threat Model}`, label `sec:threat`), line 485 (`\subsection{Gap Summary and Positioning of RAGIN}`).
- **Description**: The hierarchy reads §2.5 "Threat Model" and §2.6 "Gap Summary" under "Related Work". A threat model is forward-looking scoping, not prior-art survey content; S&P convention places it as a standalone top-level section (typically after the Introduction) or inside the System section. Under the current hierarchy it is easy to miss and it sits below a level that reviewers scan for. Same applies to the Gap Summary: it is positioning/meta-content, arguably belonging to the Introduction or end of Related Work as a distinct unit.

### F4. 🟡 Section length asymmetry (in-range)
- **Scope**: Section 3 = 479 lines (528–1006) vs. Section 4 = 118 lines (1007–1124); Section 1 = 207 lines; within §3, subsection §3.2 (Chrollo) = ~121 lines vs. §3.1 (Overview) = ~47 lines.
- **Description**: System Architecture is ~4× Experimental Setup and ~2.3× Related Work, and §3.2 alone is nearly the size of §2.5–2.6 combined. Within §3 the per-component subsections are otherwise well balanced (Don 77, Hisoka 77, Latency 83, Invariants 66) — Chrollo is the outlier because two blocks of *experimental* material were appended to it (see F5). In the whole file (context), Results (498) vs. Future Directions (25) and Conclusion (24) is also wildly uneven, though short closing sections are conventional.

### F5. 🟡 Empirical-results content embedded in architecture and setup sections
- **Scope**: lines 606–637 (learning-curve, calibration ECE, n-gram feature-family experiments inside §3.2); lines 1082–1109 (`\paragraph{Weight-sensitivity analysis}` + Table `tab:sensitivity` in §4.4).
- **Description**: Measured outcomes (Δ+6.0pp with CIs, McNemar p-values, ECE 0.071, escalated-population accuracy) are reported in the architecture narrative, and a full results table (IQS weight sensitivity) lives in the metrics subsection of Experimental Setup. This blurs the Architecture/Results boundary the Paper Organization (§1.9, line 306) promises, and it is the mechanical cause of the §3.2 asymmetry in F4. Recommend moving to Results (or a labeled "design-space study" subsection) with a forward pointer retained in place.

### F6. 🟡 Figure cross-reference order violates figure numbering order
- **Scope**: line 861 cites `Figure~\ref{fig:dataflow}`; line 862 cites `Figure~\ref{fig:latency}`; float source order: `fig:latency` at 893–902 (becomes Figure 2), `fig:dataflow` at 904–938 (becomes Figure 3).
- **Description**: The running text references Figure 3 before Figure 2. With `[htbp]` floats LaTeX will number by source order regardless of first-citation order, producing out-of-sequence first mentions. Swap the two float environments or reorder the first citations so each figure's first reference is monotonically increasing.

### F7. 🟡 Duplicate bibliography entries for the same paper
- **Scope**: `\bibitem{sladic2025}` (line 2120) and `\bibitem{valeros2024}` (line 2122), both titled "LLM in the Shell: Generative Honeypots" (arXiv preprint vs. IEEE EuroS&PW 2024). Both cited jointly at line 392 (`~\cite{valeros2024,sladic2025}`).
- **Description**: One work appears twice under two keys and is cited as if it were two independent references ("Recent literature documents a structural shift toward LLM-powered deception~\cite{valeros2024,sladic2025}"), which inflates the related-work claim. Merge into one entry (the peer-reviewed EuroS&PW 2024 version) and deduplicate all joint citations. (Found during whole-file cite/bib cross-check; the citation site is in-range.)

### F8. 🟡 Missing-space typos (multiple, mechanical hygiene)
- **Scope / evidence**:
  - Line 253: `the engineering steprequired to convert` → "step required".
  - Line 705: `(Table~\ref{tab:kb}).Upon escalation` → missing space after period.
  - Line 811: `separates those two regimes,and its boundaries` → "regimes, and".
  - Line 633: `helps marginally in distribution (+1.0pp, n.s.) but\emph{degrades}` → missing space before `\emph`.
- **Description**: Four spacing defects in the first 1,124 lines; each is trivial but they will print as run-together words in the PDF.

### F9. 🟡 Title contains a doubled colon construction
- **Scope**: line 28: `RAGIN: Retrieval-Augmented Honeypot Intelligence: Measuring Adaptive Deception Against Real and Simulated Adversaries`.
- **Description**: "Name: expansion: subtitle" reads as two stacked titles. Restructure (e.g., "RAGIN: Retrieval-Augmented Honeypot Intelligence — Measuring ...", or drop the expansion into a subtitle line).

### F10. 🟢 Hierarchy semantics of Introduction subsubsections
- **Scope**: lines 275 (`\subsubsection{Headline Results on the Live Deployment}`) and 306 (`\subsubsection{Paper Organization}`) nested under `\subsection{What This Paper Argues}` (211).
- **Description**: "Paper Organization" logically scopes to the whole Introduction (or the paper), not to the "What This Paper Argues" subsection it is nested under. No level is skipped (§1 → §1.x → §1.x.y is legal), so this is not a violation, but the nesting is semantically wrong; consider promoting both to top-level unnumbered blocks or restructuring.

### F11. 🟢 Unused labels and unreferenced equations
- **Scope**: verified via cross-check. Never-`\ref`'d labels: `sec:intro, sec:headline, sec:organization, sec:gap, sec:overview, sec:chrollo, sec:env, sec:data, sec:baselines, sec:metrics, sec:impl-chrollo, sec:impl-don, sec:benchmark, sec:reliability, sec:opimplications, sec:breaker, sec:generalizability`, and — more notable — **both equations**: `eq:iqs` (1074) and `eq:delta` (1122).
- **Description**: Section labels are harmless placeholders. But Eq. (2) "Comparative Improvement" (`eq:delta`) is defined in §4.4 and never referenced or computed anywhere — dead metric definition in a paper whose whole §4 is metrics; either use it in Results or cut it.

### F12. 🟢 Caption/paragraph-formatting hygiene
- **Scope**: lines 868–878 — the caption of `tab:latency` is a seven-line argumentative paragraph containing `\ref{sec:results}`; line 888 — table cell reads `--- --- OpenRouter / safety-paced` (doubled em dash, malformed punctuation); lines 962–967 — `\begin{sloppypar}` inside an itemize item (overfull workaround leaking into the source).
- **Description**: Captions should be self-contained identifiers, not analysis paragraphs with cross-references; move the 158×-multiplier narrative into body text. The `--- ---` cell should be a single rule or plain text.

### F13. 🟢 Heading-naming inconsistency between the two component sections
- **Scope**: §3.2 "Component 1: Chrollo --- Behavioral Session Classifier" (579) vs. §5.1 "Chrollo: Behavioral Classifier" (1128, out of range); likewise Don and Hisoka pairs.
- **Description**: The architecture section uses "Component N: Name --- Role", the implementation section uses "Name: Role". Parallel sections describing the same components should use parallel titling.

### F14. 🟢 DOI rendered with `\url{}` in the frontmatter note
- **Scope**: line 30: `Zenodo): \url{https://doi.org/10.5281/zenodo.21808407}`.
- **Description**: Cosmetic; use `\doi{10.5281/zenodo.21808407}` (or the venue's badge mechanism). Also note the GitHub repository is repeated verbatim three times (lines 30, 601, 1023/2015) — a single macro would enforce consistency.

---

## 3. Findings — Whole-file context (out of range, outline-level only)

### F15. 🟡 Forward references reach across half the paper
- **Scope**: e.g., line 478 (`Section~\ref{sec:deflayer}` → Discussion, 1832), line 936 (`Section~\ref{sec:mem0}` → 1205), line 1096 (caption forward-ref to `tab:cowrie`, 1495), plus routine Intro→Results/Discussion/RedTeam/Future refs.
- **Description**: Intro forward references are conventional and fine. The notable ones are (a) a *caption* forward-referencing a table 400 lines ahead (tab:sensitivity caption → tab:cowrie), and (b) the Threat Model pointing into the Discussion for mitigations (`sec:deflayer`). Both are resolvable by reordering or restating, and both mildly degrade first-read linear comprehension.

### F16. 🟢 Bibliography is self-contained and consistent
- **Positive finding / Nit**: 47 `\bibitem`s, all cited at least once; every `\cite` key resolves; no undefined-reference or multiply-defined-label warnings in `main.log`; only one overfull hbox (2.61 pt); hyperref "Token not allowed in a PDF string" warnings are benign elsarticle frontmatter artifacts. Remaining item for the venue switch: S&P uses `IEEEtran` bibliography style; the current numbered `thebibliography` with mixed arXiv/proceedings styling will need reformatting.

### F17. 🟢 Missing S&P-conventional elements checklist
- Artifact availability: present (frontmatter note line 30, Data Availability 2012–2024, footnotes) — adequate content, will need reformatting for IEEE.
- Ethics: present but misplaced (see F2).
- Responsible-disclosure statement: **absent** as such; partially covered by the Ethical Statement. Consider an explicit line on coordinated disclosure for any live findings.
- Appendix: none; not required.
- Acknowledgments / Funding / GenAI-use declaration: present (Elsevier-style; must be adapted or dropped per S&P rules).

---

## 4. Summary Counts

| Priority | Count | Items |
|---|---|---|
| 🔴 Blocker | 2 | F1 (venue/template mismatch), F2 (ethics placement) |
| 🟡 Major | 8 | F3 (threat-model hierarchy), F4 (section asymmetry), F5 (results in arch/setup), F6 (figure cite order), F7 (duplicate bib entry), F8 (spacing typos), F9 (title colons), F15 (long-range forward refs, context) |
| 🟢 Nit | 7 | F10 (subsubsection nesting), F11 (unused labels/eqs), F12 (caption hygiene), F13 (heading naming), F14 (DOI macro), F16 (bib style note), F17 (S&P element checklist) |

**Verified clean (no findings)**: no duplicate `\label`s; no undefined `\ref` (132/132 resolve); no skipped heading levels anywhere in the outline; all float environments closed; all figure files present; tables and figures numbered strictly in source order; section/subsection/subsubsection depth never exceeds 3; every cited key has a bibitem and vice versa.
