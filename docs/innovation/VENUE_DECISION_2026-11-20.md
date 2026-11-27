# Venue decision research — Belief Tomography (2026-11-20)

**Question:** which top journal suits "Belief Tomography: Measuring What
Autonomous Agents Are Made to Wrongly Believe" (13 pp, agent-security
measurement + impossibility/frontier theory + preregistered field experiments
+ certification-limit theorems + audit calibration)?
**Method:** venue-scope verification, comparable-work placement, impact
metrics, timeline verification. All claims sourced below; contradictions
disclosed.

## FINAL DECISION (2026-11-20, author's call): ACM TAISAP

The author selected **ACM Transactions on AI Security and Privacy (TAISAP)**
as the primary target — a deliberate founding-window bet: the journal's scope
is verbatim the paper's thesis, the first issue (Vol 1, Issue 1, March 2027)
is an Issue-in-Progress already publishing LLM-security papers (November
2026), agent-security is exploding (every neighbor found in the collision
scan is 2025-2026), and early TAISAP papers become the citable foundation of
the field's journal record. EICs: Murat Kantarcıoğlu, Patrick McDaniel,
Sagar Samtani. Submission: ScholarOne (mc.manuscriptcentral.com/taisap), ACM
open access — **$0 for the author** (Egypt = 100% APC waiver, verified on
ACM's waiver-countries list).

**Known tradeoff (recorded honestly):** TAISAP has no IF/quartile yet
(possibly not yet Scopus-indexed); most ACM Transactions earn Q1-Q2 within
1-2 years, but that is an expectation, not a guarantee. If a certified
quartile is ever required, IEEE TDSC (SJR Q1, JIF ≈ 6.8-7.5, free in
traditional mode) remains the fallback target for a future paper, and TOPS
(SJR Q1, JIF 4.0, $0 via the Egypt waiver) is the in-ACM prestige fallback.

**Submission logistics:** ACM acmart format (acmsmall, review/anonymous for
review); conversion started in `docs/paper/belief_tomography/taisap_submission/`;
rolling submissions (no deadline); the original 13-page draft is preserved
untouched as the working manuscript.

---

## The research below (pre-decision)

**Primary journal target: IEEE TDSC — Special Issue "Trust, Privacy, and
Security in Intelligent and Agentic Systems", submission deadline
15 January 2027.**

Why it is the best fit (verified from the CFP):
- The SI's own topic list names what the paper is: *Frontier AI Safety,
  Assurance, and Governance — alignment, auditing, red-teaming; conformance
  with NIST AI RMF / EU AI Act*; *Agentic and Multi-Agent AI — tool-use
  isolation, MCP protocol security, memory/context integrity*; *Foundation
  Models and LLMs — trust, safety, resilience; prompt injection*. The paper's
  certification semantics + audit-channel calibration (E17) + gaming-gap
  diagnostics (E7/E10/E16) are exactly "auditing and assurance for agentic
  systems".
- Verified timeline (from the CFP): submit 15 Jan 2027 → first reviews
  15 Apr 2027 → revised 15 Jun 2027 → notification 31 Aug 2027 → final
  15 Oct 2027 → **publication early 2028**. A defined path, no rolling
  uncertainty.
- Journal prestige: TDSC is CCF Rank A, Q1 (SJR top-20 CS), JIF ≈ 6.8–7.5.
- Format: a 13-page draft + 10-page formalism note fits a journal naturally —
  no two-column page squeeze, and the appendix-style formalism note can be an
  appendix or a second companion submission.
- Guest editors: Hongxin Hu (Buffalo, lead), Elena Ferrari (Insubria),
  Heiko Ludwig (IBM Research) — access control / security / agentic-systems
  coverage, matching the paper's positioning.
- Rule check: original work only, no surveys/case studies — the paper is
  original research; the E2-v0 invalidation story is disclosed as instrument
  archaeology, not a case study.

## The alternatives, with evidence

| venue | fit | prestige | timeline | verdict |
|---|---|---|---|---|
| **ACM TOPS** | high (security+privacy flagship; LLM content appearing, Vol 29(2) 2026 has an LLM+model-checking paper) | top-tier security journal (TISSEC lineage) | slower, no fixed dates | strong second; submit after TDSC SI verdict (early 2028) |
| **ACM TAISAP** (new, 2025, EIC Patrick McDaniel) | perfect scope — "methods for assessing the security of AI models/systems/environments" | brand-new: no IF yet, not yet "top" | rolling, open access, **no fees** | best-scope hedge; ideal if speed-to-first-journal-publication matters more than prestige |
| **IEEE TIFS** | medium-high (QIF's home community; adversarial-ML coverage) | highest IF of the group (~8–9.3) | standard IEEE | viable; scope skews forensics/adversarial-ML more than assurance |
| **Computers & Security** (Elsevier, IFIP TC11) | broad fit | Q1, JIF ≈ 6.8 | faster | backup, lower prestige ceiling |
| **Nature Machine Intelligence** | field-opening framing ("Governing AI safety through independent audits" is its own anchor paper) | JIF 29.8 | median ~255 days to acceptance, very selective | high-risk/high-reward; requires a major cross-disciplinary reframe; try as a *second* act only if TDSC/USENIX verdicts land fast |

## The conference reality check (the program's stated primary)

- **USENIX Security '27, cycle 2: registration 19 Jan 2027, papers due
  26 Jan 2027** — eleven days after the TDSC SI deadline; the paper is
  submission-ready now.
- **CCS 2027: abstract 8 Jan 2027, paper 12 Jan 2027.**
- **NDSS 2027 and S&P 2027 cycle 1: closed.** (S&P 2027 cycle 2 was
  10/17 Nov 2026 — the RAGIN honeypot paper's cycle.)
- Community reality: the neighboring work in this space landed at
  **ICLR 2025 main conference** (AI Sandbagging, poster), AISI's
  auditing-games report, and **arXiv/workshops** — the LLM Agent Honeypot
  (Palisade, arXiv:2410.13919) is still an unreviewed preprint. **Nobody has
  yet placed this class of agent-security measurement in a top journal** —
  the journal lane is open, and a journal venue here differentiates the
  portfolio from the RAGIN conference paper.

## Recommendation (decision-ready)

1. **January 2027 = one shot, choose deliberately:**
   - **Journal answer:** TDSC SI, submit by **15 Jan 2027**. Best scope match,
     verified timeline, CCF-A/Q1, journal-length formatting, and the
     four-frame/QIF positioning reads well to a TDSC audience.
   - **Conference answer (if community prestige is the priority):** USENIX
     Security '27 cycle 2, **26 Jan 2027**, with CCS 2027 (12 Jan) as the
     alternative. More competitive; artifact evaluation favors our fully
     seeded, pinned, reproducible pipeline.
2. **Do not submit to both in January** (concurrent-submission rules). Default
   recommendation: **TDSC SI first** (journal was the ask; fit is exceptional;
   the defined SI timeline de-risks the wait), then route the next paper
   (e.g., E3 deception-gain results or the GAUNTLET/AWE certification paper)
   to USENIX/CCS.
3. **Keep TOPS as the post-verdict fallback** for the same manuscript; keep
   TAISAP as the fast-scope option if a delay is unacceptable; treat NMI as a
   2028 possibility once a citable, peer-reviewed version exists (Nature
   venues prefer work with standing).

## What each venue would change in the manuscript

- **TDSC:** IEEE two-column format; fold `formalism_note` into an appendix;
  emphasize the certification/assurance semantics (SI's governance topic);
  artifact link (all seeded/pinned — a differentiator).
- **TOPS:** same, plus sharpen the privacy-adjacent framing (tomograms as
  sensitive evaluation data; E14's disclosure-externality).
- **TAISAP:** submit nearly as-is (scope is the paper's thesis).
- **NMI:** major reframe to cross-field significance (measurement science for
  AI assurance), compress theorems to one section, expand the governance
  implications (EU AI Act/NIST AI RMF mapping already in §8/§11).

## Sources

- TDSC SI CFP (verified directly): computer.org/digital-library/journals/tq/cfp-trust-privacy-security-agentic-systems
- ACM TAISAP launch (Jun 2025): acm.org/media-center/2025/june/taisap-launch
- AI Sandbagging venue: OpenReview — ICLR 2025 poster
- LLM Agent Honeypot: arXiv:2410.13919 (still preprint as of 2026-11-20)
- Nature MI metrics + audit-governance anchor: nature.com (Nature MI journal
  metrics page; "Governing AI safety through independent audits")
- Deadlines: USENIX Sec '27 CFP (usenix.org), CCS 2027 (sigsac.org),
  NDSS 2027 CFP, S&P 2027 CFP (sp2027.ieee-security.org), sec-deadlines.org
  tracker
- IFs: JCR/SJR aggregates as reported 2025-2026 (TDSC ≈ 6.8–7.5; TIFS ≈
  8–9.3; C&S ≈ 6.8; Nature MI 29.8)
