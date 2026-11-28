# PREREGISTRATION — E33: Human Blind Adjudication of the 230-Flag Audit Sample

**Registered:** 2026-11-28, before any human recruitment or payment. This
file is a **launch-ready protocol**: it executes only when the author
commits a recruitment channel (decision explicitly reserved to the author —
see §7). Nothing in the paper currently depends on it; it is the
pre-committed answer to the one remaining open item (the κ = 0.96/1.00
re-adjudication is LLM-only).

## Registered question

Do independent human coders, blind to panel, model, session, and author
label, reproduce the author's adjudication of the oracle flags at the same
agreement level the three-LLM panel achieved (45/46, κ = 0.96 full-sample;
39/39, κ = 1.00 own-panel-excluded)?

## Design (frozen before recruitment)

- **Item set:** the existing 46-item 20% stratified blind sample
  (`docs/paper/belief_tomography/independent_reaudit/sample_blind.jsonl`) —
  identical items to the LLM round, so human vs LLM vs author agreement is
  directly comparable on identical data. Sheets are already blinded; the
  label key is a separate file coders never see.
- **Rubric:** the frozen E17 rubric (case-insensitive canary rule;
  refusal-that-names-the-action = safe) plus a one-page plain-language
  guide written for lay coders.
- **Coders:** n = 5 adult human coders, recruited without knowledge of the
  author, the panels, or the hypothesis. Qualification: three practice
  items with known labels; failure on ≥ 2 disqualifies before scoring.
- **Independence:** coders work separately; no discussion; one attempt.
- **Compensation:** flat, not performance-contingent.

## Endpoints (registered)

1. **Primary:** per-coder raw agreement and Cohen's κ with the author's
   frozen labels (46 items; exact 95% CI disclosed — at n = 46 the κ CI is
   ±~0.15, stated as a power limit up front).
2. **Secondary:** human majority label vs author (and vs each LLM coder);
   human–human pairwise agreement; per-flag disagreement table with the
   reply text quoted, published regardless of direction.
3. **Disclosed asymmetry:** humans read the same replies the LLMs read; the
   comparison tests whether the *adjudication step* is human-consistent,
   not whether human judgment of model behavior differs in kind.

## Kill gates

- A recruitment channel that cannot guarantee coder independence (shared
  accounts, discussion) → halt, report as instrument failure.
- Any coder accessing the label key → that coder's rows void, disclosed.

## Budget and channels (for the author's go decision)

| Channel | Est. cost | Notes |
|---|---|---|
| Prolific (n = 5, ~10 min each incl. guide) | ≈ $60–130 with platform fees | fastest; researcher-account region rules apply |
| Local university coders (n = 5, supervised) | ≈ $0–50 (vouchers) | author's institution; supervision must not breach blinding |
| Author-run peer volunteers | $0 | weakest independence; disclosed as such |

Total exposure is bounded by the item count: 46 blind items × 5 coders.

## Status

Registered and stamped before recruitment. Execution is the author's
decision alone; non-execution changes nothing already printed in the paper.
