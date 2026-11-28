# SPLIT-ROBUSTNESS NOTE — the 24/6 confirmatory/exploratory split under the strictest timing rule

**Written:** 2026-11-28 (post-hoc, exploratory; designed after an external
audit asked how we know the retroactive split was not drawn to flatter the
results).
**Inputs:** the frozen registration-timing table (Supplement Table S2) and
the paper's declared split (confirmatory = E1–E22 and E30–E31; exploratory =
E23 and E25–E29; E24 retired).

## 1. The strictest rule

Reclassify every entry by the frozen record alone: **confirmatory only if
registration strictly precedes data** (clean git precedence, or prereg
mtime before first data write). Same-commit counts only if the prereg
mtime precedes the data.

## 2. Result: exactly six demotions

Under the strict rule, six of the 24 confirmatory entries demote:

| Entry | Frozen evidence | Why demoted |
|---|---|---|
| E1 | no registration file; data 2026-11-07 | unregistered |
| E1b | data precedes layer registration | unregistered |
| E15 | committed together with its data | not strictly before |
| E16 | committed together with its data | not strictly before |
| E20 | committed after computation | post-data |
| E21 | prereg mtime after session data | post-data |

Everything else in the confirmatory set survives (E2/E3/E5/E14/E22 clean or
same-commit-preceding; E17–E19, E30, E31 clean; E4/E6–E13 covered by the
layer registration the ledger pins). No entry is promoted by any plausible
alternative rule — the split only ever moves experiments toward exploratory.

## 3. What rests on the demoted six

- **The headline claims do not.** The paper's central results are
  refutations: the two registered field predictions rest on E2/E3 (clean
  git precedence) and the E5 lineage (clean), and the open-weight spectrum
  rests on E30/E31 (clean, the only field layer with genuine git
  precedence). A refutation does not gain strength from confirmatory
  status; multiplicity corrections guard positive claims, and demotion
  makes them strictly harder, not easier.
- **E16 is analytic.** Its support is a divergence derivation verified on
  the harness ("evasion budget diverges as held-out recognition error → 1"),
  not a sampled test — split-invariant by nature.
- **E15 and E20 (disclosure economics) are the only sampled positive claims
  on demoted entries.** Under the strict rule they carry exploratory
  labels; their in-sample orderings (decoy release dominating honest
  release and silence; no bounded-noise release dominating both corners)
  are reported descriptively in their frozen results files, and any
  inferential restatement in a revision should carry a multiplicity
  adjustment across the full registry.
- **E1/E1b are calibration**, already excluded from the cleanly
  pre-registered list since Round 18; no headline claim rests on them.
- **E21's void cell is a detection, not a certification** — demotion does
  not change its (already void-and-unadjudicated) status.

## 4. Bottom line

The retroactive split is conservative in the only direction that matters
for this paper: under the strictest defensible rule the confirmatory set
shrinks by six, no headline claim loses confirmatory support, and no claim
gains status under any alternative split. The residual exposure is exactly
E15/E20's descriptive orderings, flagged here rather than defended.
