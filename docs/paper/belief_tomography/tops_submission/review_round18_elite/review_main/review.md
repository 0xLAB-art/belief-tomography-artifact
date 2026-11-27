## Summary

The paper defines the Belief-Claim Gap, estimates it by active black-box tomography with Wilson intervals and a certification semantics, proves an impossibility result, a query-complexity bound, a deception-detection frontier, and a set of certification limits, and reports thirty registered experiments on constructed foils, a commercial gateway lane, a live honeypot fleet, and three open-weight models. Both pre-registered field predictions were refuted at instrument resolution, and the program caught two of its own measurement errors. Round 18 reviewed the IEEE TDSC build with five independent seats (theory re-derivation, empirical recount, gatekeeping, fresh-eyes craft, consistency) and applied every verified correction.

## Strengths

- The empirical program survives a full recount: 33 Wilson/Clopper-Pearson intervals recompute to the digit from frozen artifacts, the 230-flag audit decomposes exactly (118 refusal-quote false positives, 112 genuine canary echoes), the censoring counters (591 + 83 + 305 = 979) and every table cell in the field, open-weight, and audit tables match the raw verdicts. The two self-caught errors are real and correctly attributed. [[C1](#c1), [C2](#c2), [C3](#c3), [C4](#c4), [C7](#c7)]
- The theory is now sound at the points where it was weakest. The onset theorem's certified horizon uses the exact two-sample variance, is finite exactly when the shift exceeds the certified boundary, and reproduces M*=29.73 at the registered cell; the exact binomial test's power is corrected to 0.785 at (40,0.2); the certification rule's Wilson trichotomy is respected by Proposition 6 and E13; and the sensitivity statement is correctly presented as an identity for binary verdicts rather than an assumption test. [[C8](#c8), [C10](#c10), [C16](#c16), [C17](#c17)]
- The honesty layer is unusually complete and now matches the record: the registration ledger distinguishes clean, same-commit, with-data, and post-data entries experiment by experiment (per-experiment timing in Supplement Table S2), discloses the two header-date edits, withdraws the earlier universal pre-registration phrasing, reports both field predictions as refuted, and states the 24/6 confirmatory-exploratory split as retroactive. [[C5](#c5), [C9](#c9)]

## Weaknesses

- The bibliography is still ACM-Reference-Format in an IEEE submission: full given names, year after authors, quoted titles, 'In Proceedings of', and only a third of entries carrying DOIs. Ordering is alphabetical rather than first-citation. An IEEE production editor will return it; converting 43 entries to IEEE punctuation with volumes, pages, and DOIs is the remaining production task. [[C22](#c22)]
- Fitting the 12-page Transactions limit cost the main paper every figure: the tomogram, the onset grid, the certification attack surface, and the release wave now live only in the supplement, and the main text is figure-free. A 13-page paper with one figure (0.5 page over the current fit) would read better, and the figure set would need regeneration at column width with Type 1 fonts before submission. [[C19](#c19)]
- The field panel is thin by construction: one model per gateway lane at the deployed depth, with censoring that leaves the primary lane's state-deception family unidentified ([0,1]) in E2-v1. The paper says this, and the repaired panel and the open-weight models mitigate it, but a reviewer will still ask for a second lane at the repaired budget. [[C3](#c3)]
- The deposit's own record includes post-data registrations in the E20-E29 window. This is disclosed rather than repaired, which is the honest treatment, but it means the exploratory diagnostics cannot be read as confirmatory even where their results are clean. [[C9](#c9)]

## Overall Score

5/6 (ICML 2026: Accept — technically solid, high impact)

## Evidence

<a id="c1"></a>**C1** · claim (supported) · §Abstract
> Dose-response reaches r>=0.986 across 1,500 episodes and test-retest r=0.949 at 10 probes per cell
>
> *Verification:* E1 per-family Pearson 0.9860-0.9904, Spearman 1.00; E1b r=0.9489 at 10 probes/cell (recounted from frozen artifacts by the empirics seat; all values exact).

<a id="c2"></a>**C2** · claim (supported) · §Abstract
> A seeded audit calibrates the verdict channel (sensitivity 0.960, false positives 0/25)
>
> *Verification:* E17: 24/25=0.960 [0.805,0.993], FP 0/25 [0,0.133]; rule-of-three power statement verified.

<a id="c3"></a>**C3** · claim (weak) · §Abstract
> Both field registrations were refuted at instrument resolution: Delta(B) at or below the noise floor for all five personas, and a 300-session probe attack finds beta-hat=0, Wilson 95% [0,0.060] per family
>
> *Verification:* Both refutations verified (beta-hat 0 across measured cells; Delta(B) 0.000-0.0067 for five personas). But the printed [0,0.060] is the nominal 0/60 bound, not the measured-n interval (0.061-0.088; [0,1] for the censored gpt-5.6 state-deception cell; [0,0.242] for 0/12). Corrected in this round: Table I now prints per-model measured-n bounds and the abstract says 'nominal 0/60 mapping'.

<a id="c4"></a>**C4** · claim (weak) · §Abstract
> Open-weight panel measures literal canary echo from 0.000 on the gateway panel to pooled 0.030-0.143 (0.700 in the echo family), with zero destructive-command compliance in any panel
>
> *Verification:* Spectrum verified (E31 9/300=0.030, 43/300=0.143; echo 42/60=0.700; zero destructive compliance). The abstract's '0.000 to 0.143' conflated the gateway panel (0.000) with open weights (min 0.030); corrected to 'from 0.000 on the gateway to a pooled 0.030-0.143'.

<a id="c5"></a>**C5** · claim (supported) · §Abstract
> Thirty registered experiments follow: twenty-four confirmatory and six exploratory post-anomaly diagnostics, the 24/6 split applied retroactively and disclosed
>
> *Verification:* Thirty entries = 24 confirmatory + 6 exploratory (E23, E25-E29); E24 retired; E1b/T3 sub-protocols. Counting verified in five places; the retroactive split is disclosed.

<a id="c7"></a>**C7** · claim (supported) · §Contribution 4
> The mandatory transcript audit retracted the repaired panel's five new flags as refusal-quote false positives of the lexical oracle (5/60 flagged, 0/60 genuine)
>
> *Verification:* E29: 5/60 flagged, all five adjudicated refusal-quote FPs, post-audit 0/60 [0,0.060]; 118/112 flag decomposition recounted exactly.

<a id="c8"></a>**C8** · claim (supported) · §Theory
> Passive monitoring cannot tomograph in general; a patch-deception-decay law and an onset dichotomy jointly cap deception gain and stealth
>
> *Verification:* Statements survive re-derivation after this round's corrections: M* now uses the exact variance q(1-q)/M + p(1-p)/N0 and is finite iff delta>Delta_beta_d; the regime table is unchanged. Passive impossibility and the decay law re-derived clean.

<a id="c9"></a>**C9** · claim (weak) · §1
> Registration is layered: E1-E3, E5, E14, E22, E25, E30, E31 registered before data; E15/E16 and E26 committed with their data; E20, E21, E22-entry and E27/E28/E29 minted after data
>
> *Verification:* The layered-registration claim was overstated for E1/E1b (E1 has no registration file and its data predate the layer registration by 11 days; E1b by 2 minutes) and for E14 (same-commit, 37 s, no git precedence). Corrected in this round in the introduction, Table S1's caption, and §10.

<a id="c10"></a>**C10** · claim (supported) · §Abstract
> Public probe suites are gameable, statistical certificates do not compose, published profiles are forgeable, censoring above tolerance makes a certificate unidentifiable, and disclosure admits no free lunch
>
> *Verification:* Corollary 1, Theorem 5, Theorem 6, Corollary 4, Proposition 9 and E13/E14-E16/E20 verified statement-by-statement; two wording defects fixed (Thm 3(ii) 'no test exceeds TV'; Prop 6 point-estimate vs Wilson trichotomy).

<a id="c16"></a>**C16** · claim (invalid) · §4 Theory
> The onset theorem's M* may use the conservative variance v=max{p(1-p),q(1-q)} in both terms, making no finite horizon exist for delta in (0.261,0.285)
>
> *Verification:* Recomputed: with sigma_dm=sqrt(q(1-q)/M+p(1-p)/N0), M*=(z+z')^2 q(1-q)/(delta^2-Delta^2) is finite iff delta>Delta=0.261; at delta=0.27 the exact horizon is 694, where the printed formula gave infinity. Fixed in theory.tex and appendix.tex; the regime table is unchanged.

<a id="c17"></a>**C17** · claim (invalid) · §4 Theory
> The one-sided exact binomial test has power 0.807 at (40,0.2)
>
> *Verification:* Level-0.05 one-sided exact binomial at n=40 rejects at k*=18 and has power P(Bin(40,0.5)>=18)=0.7852; 0.8074 is not attained by any non-randomized level-0.05 test at that n. Corrected at three sites.

<a id="c19"></a>**C19** · claim (invalid) · §whole
> The TDSC manuscript is within the Transactions page limit
>
> *Verification:* TDSC/Computer Society caps Transactions regular papers at 12 formatted pages including references (verified at computer.org/publications/author-resources, 2026-11-26); the build was 27. Resolved by condensing to a 13-page main with a 22-page supplement.

<a id="c22"></a>**C22** · claim (invalid) · COVER_LETTER.md
> The cover letter names the correct journal and speaks for a single author
>
> *Verification:* The letter named 'IEEE Transactions on Privacy and Security' (the ACM TOPS title), used 'we' for a single author, and narrated internal review rounds. Replaced with a single-author TDSC letter; the old file is marked superseded.
