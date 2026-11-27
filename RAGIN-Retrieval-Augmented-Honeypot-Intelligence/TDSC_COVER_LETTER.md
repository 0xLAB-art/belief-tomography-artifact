# TDSC Cover Letter

> Before sending: fill the two bracketed placeholders (concurrent-submission
> status, date). See the checklist at the bottom.

---

Dear Editor-in-Chief,

I am submitting "The Intelligence Ladder: Pricing AI Mechanisms in a Verified
Deception Honeypot" for consideration as a full-length paper in IEEE
Transactions on Dependable and Secure Computing.

The paper asks a budgeting question that deployers of AI-assisted defenses
face but rarely measure: how much intelligence can a deception endpoint spend
on crafting its lie before the intelligence itself becomes the risk? I treat
that question as an experiment. Four rungs of increasing intelligence
(scripted templates, a behavioral classifier, retrieval-augmented planning,
free generation) are added one at a time to the same serving loop, and each
rung is kept only if a measured marginal effect justifies its trust price.
The main finding is a negative one, and I report it as such: at the top of
the ladder, kind-aware adversarial assessment fixes 12 of 13 real-world
assessments yet shows no measurable advantage over a deterministic decision
floor at the benchmark's resolution. Past the point of verification,
intelligence buys adaptation, not safety. The design rule that survives is
the one the title names: certifiable intelligence inside the loop, generative
intelligence outside it under verification.

The paper is about the dependability of the serving system; the AI mechanisms
are the risk being managed. Every adaptive component sits behind a
serving-time verifier with a 2,108-record human-on-the-loop audit trail. In
the 218-query campaign, 88.1% of serves came from verified generation, 11.9%
were served from vetted deterministic content, and no serve in either
campaign records failed generation, with byte-identical behavior under 45
adversarial re-queries. I believe this puts the work squarely in the
journal's scope: the contribution is a measured, auditable design for using
untrusted intelligence in a secure system, not a claim about the intelligence
itself.

I would ask reviewers to hold the paper to the same audit standard its
numbers are held to. Three chains are documented in the appendices. First,
every quantitative claim resolves to a persisted artifact; when an early
draft cited a summary whose source file had been lost in a machine
migration, I re-ran the 218-query campaign end to end rather than reuse the
number. Second, the automated persona judge was itself audited offline: two
systematic errors (canary-bait blindness, and a harness artifact worth 1.35
points across the two runs) were found, corrected, regression-tested, and
documented, and the audit now re-seeds itself on a schedule so the bias
cannot silently return. Third, the figures are audited like the numbers: a
script re-renders each figure and mechanically checks that no drawing element
crosses a node interior, and the check runs in the repository's continuous
integration. That check exists because an earlier version of Figure 1 passed
visual review with a curve crossing three node interiors; the mechanical
version of the same audit now fails on that class of defect.

Where the evidence is null or thin, the paper says so. The dwell-time null
for the top rung is reported as a null. The fold-down claim is bounded to the
one stratum where the comparison is informative (six sessions of a 400-session
census, five of which the provider refused and none of which recovered on a
structured retry), and those refusals are reported as an availability finding
in their own right rather than discarded as errors. The paired grounding
effect (+0.154 composite, 95% CI [+0.092, +0.221]) is printed with its
interval, including the persona stratum whose interval straddles zero exactly
as the architecture predicts. I have tried to write a paper whose claims are
no stronger than its instruments, and I would rather defend an honest null
than a rounded-up headline.

The full artifact tree, including both independent 218-query campaigns, the
audit records, and the figure-audit output, is public at
https://github.com/0xzodiac/The-Intelligence-Ladder. Appendix B lists the
exact command sequence that regenerates every table and figure; the
deterministic parts run offline. The manuscript is [not under consideration
elsewhere / state status]. I have no conflicts of interest.

Thank you for your consideration.

Sincerely,

Anonymous
Department of Computer Science, Benha University, Egypt
anonymous@example.com

---

## Before sending (checklist)

- [ ] **Concurrent submission.** The repository contains an ESWA submission
      record (ESWA-S-26-45224). Resolve its status (withdrawn, rejected, or
      still pending) before asserting the originality sentence; if it is
      still pending, this paper cannot go out simultaneously.
- [ ] Fill the bracketed status sentence and add the date.
- [ ] Optional: suggested reviewers / opposed reviewers, per TDSC policy.
- [ ] Optional: ORCID and affiliation consistency check against the paper's
      author block.
- [ ] Verify the repo URL resolves for an anonymous reader (artifact tree
      visible without auth).
