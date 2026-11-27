# RAGIN — Hard IEEE S&P Review, Round 3 (post-closure audit)

**Review date:** 2026-10-08, third pass, same day
**Submission surface:** `paper/sp2027.tex` + `paper/sections/{introduction,sp_threat_model,design,sp_related,sp_evaluation,conclusion,sp_appendix}.tex`; compiled `paper/sp2027.pdf`, 15 pages, bibliography from p. 13 (**12 text pages** against the 13-page limit), 0 undefined references, 0 citation warnings, 0 overfull boxes, 56/56 references cited.
**Prior rounds:** `docs/SP2027_HARD_REVIEW_2026-10-08.md` (round 1, findings N1–N15) and `docs/SP2027_ROUND2_HARD_REVIEW_2026-10-08.md` (round 2, findings ND1–ND6 plus the N15 closure).

## Provenance of this audit (disclosed)

The five-seat panel was **not** dispatched this round. Delegation has failed **12 times out of 12** across two previous rounds on provider quota (`APIError: The usage limit has been reached`, both the primary `openai/gpt-6-astra` route and the `openai/gpt-5.6-sol` fallback). Continuing to spend dispatches on a known-dead path would waste the session, so this is a **single-auditor pass with direct tool verification** — no role separation, no cross-model corroboration, correlated blind spots possible.

**Disclosure — one non-source file was written.** To test whether the anonymised mirror was current, I re-ran `scripts/build_anonymized_mirror.py`, which deletes and regenerates `dist/`. `dist/` is a gitignored build output, so no tracked file changed, and this is disclosed rather than hidden: the audit changed the on-disk state it was measuring. It left the bundle in its **correct fail-closed state**, which is where it belongs given R3-2 below.

---

## Decision

**Major Revision** — unchanged in letter for the third consecutive round, but the *reason* has inverted twice and inverted again here.

Round 1 found overclaiming. Round 2 found reporting defects, one of them an arithmetic error I had introduced. Round 3 finds **two defects in the closure work itself**: an unsupported claim added while fixing ND2, and a promise in the appendix that the artifact does not keep. No round-3 finding concerns the science.

That pattern is itself the most important result of this round, and it is the basis for the recommendation below.

## Regression check: clean

Every previously verified claim still reproduces. No round-1 or round-2 closure was undone.

- `tab:b4`: +0.3167 [0.1617, 0.4800] / +0.1400 [0.0833, 0.1967] / +0.0050 [−0.0467, 0.0567] / +0.1539 [0.0922, 0.2206].
- Stability: 0.8796 → 0.8845 (Δ 0.0049), agreement 0.9908; technique and actor MAD 0.0000 with agreement 1.0.
- Ladder: 0.0006 / 0.0704 / 0.5018 / 0.6176 ×3.
- Echo audit: 97/218 rows corrected; technique 0.5236 → 0.0569; actor 0.6800 → 0.0000.
- ND1's corrected sentence: 122 + 38 + 28 with 41 drafts firing more than one check — matches the artifact.
- ND3's format table: served = npm token, HTTP Basic, MySQL DSN, PKCS#8, SendGrid; flagged = JWT, Slack, GitHub PAT, AWS key id, `password=` assignment; 2 of 4 benign look-alikes refused (`F-benign-masked-password`, `F-benign-token-placeholder`). All match `results/verifier_harm_probe.json` exactly.
- H group: 4 of 7 caught, 0 false positives on 5 benign, Wilson [0.25, 0.842]. F group: 5 of 10 caught, 2 false positives on 4 benign, Wilson [0.237, 0.763]. Both fail-closed readings identical.
- Canonical 105-case suite still perfect; 1622 tests pass.

---

## New findings

### R3-1 — MAJOR — the context-dependence claim has no artifact behind it

**Anchor:** `paper/sections/sp_evaluation.tex:225`
**Quote:** "Coverage is also context-dependent: the same JWT and Slack token appear among the served drafts when presented without the surrounding assignment lines they were caught alongside, so the gate keys partly on assignment syntax and not only on the credential itself."

The claim is, as far as I can determine, **true** — that is how I found it during the round-2 audit, by scoring JWT and Slack drafts in isolation and watching them pass. But it was an ad-hoc inline probe. It was never added to the corpus, and `results/verifier_harm_probe.json` contains **no minimal-context variant**: 26 harm rows and 14 format rows, and no case key carrying a bare or context-free form of the JWT or Slack drafts.

So the paper's measurement paragraph now contains a causal claim about mechanism — that the gate keys on assignment syntax — with nothing in the release that a reader can execute. This is precisely the standard the appendix commits to ("every headline number resolves to a persisted result file") and the standard the round-1 audit held the paper to when it rejected the unguarded `+0.116`.

**Remedy:** add the two minimal-context variants to `scripts/verifier_harm_cases.py` and re-run the probe, so the artifact carries the contrast; or delete the sentence. The first is better — it converts the paragraph's most interesting observation into a reproducible one, and it costs two cases.

### R3-2 — MAJOR — the anonymised mirror fails its own verification, on a path the appendix promises

**Anchor:** `paper/sections/sp_appendix.tex:8`
**Quote:** the appendix names `\path{scripts/build_anonymized_mirror.py}` as the thing that builds the mirror of the version of record.

Re-running the builder against the current appendix returns:

```
verdict: FAIL
  FAIL appendix path unresolved: scripts/build_anonymized_mirror.py (absent from bundle)
```

The mirror's `SCRIPT_FILES` allowlist does not include its own builder. So the bundle omits the script the appendix names, and the verification that was added specifically to catch this class of defect catches it — **but only when it is run**, which it was not.

The practical consequence for a reviewer: read the appendix, open the bundle, and the first `\path{}` reference dangles. That is the same reviewer friction round 1 flagged as F10 and that round 2 closed, reintroduced one round later by the closure itself.

**Remedy:** add `scripts/build_anonymized_mirror.py` to `SCRIPT_FILES`. The verification then passes with no other change, since the builder carries no identity or credential material.

### R3-3 — MODERATE — nothing in the repository runs the mirror's verification

**Anchors:** `scripts/audit_figure_geometry.py:333-336`; no reference to `build_anonymized_mirror` anywhere in `tests/` or any other script.

The round-2 response to ND4 wired `gen_sp_figures.py --check` into the figure geometry audit, so a stale figure file now fails one command that a contributor already runs. **The mirror received no equivalent wiring.** `build_anonymized_mirror.py --check` exists and works, but nothing invokes it.

This is the identical defect class twice: a generated artifact whose verification is correct, available, and never executed. Round 2's ND4 was this bug in the figures; R3-2 and R3-3 are the same bug in the mirror, one level up.

**Remedy:** run the mirror's `--check` from the same place as the figure check, or add a test that asserts every `\path{}` target in the shipped appendix resolves inside the bundle. The second is stronger, because it fails on the *cause* rather than on the instance.

### R3-4 — MINOR — the bundle's last recorded PASS is now false

**Anchors:** `dist/MANIFEST.json`, `results/figure_geometry_audit.json`

Until this audit re-ran the build, the on-disk manifest recorded `verdict: PASS` for a bundle that did not satisfy its own contract. Any downstream reader of that artifact — including the authors' own future self — would have taken a stale PASS at face value. The failure mode is mild only because the bundle is regenerated wholesale rather than consumed; if a mirror is ever published from a manifest, this is how a broken artifact ships with a green check beside it.

**Remedy:** none beyond R3-2/R3-3; recorded because the *shape* of the risk matters more than this instance of it.

---

## What did not get worse

The paper's negative results are now stated with unusual precision, and I re-verified every one of them against disk. "Four of seven" with a [0.25, 0.84] interval attached, a format table naming exactly what was served, the statement that the exposure of a deployment to a real credential is bounded by canary-registry discipline rather than by the verifier, and the threat-model row that withdraws injection coverage — none of this overstates. The related-work section still engages all four required threads. The generator still cannot let a figure drift from its artifact. The pairing contract still reproduces bit-for-bit.

If the *science* were the thing under review today, the remaining substantive gap would still be the one identified in round 2 and not yet addressed by the authors: the framing decision. But the science is not what this round found anything wrong with.

---

## Scorecard

| Dimension | Round 2 | Round 3 | Change and justification |
|---|---:|---:|---|
| Security relevance | 73 | 73 | No change. The measured boundary stands as reported. |
| Novelty | 62 | 62 | No change; related work unchanged since round 2. |
| Significance | 61 | 61 | No change. |
| Technical quality | 74 | 71 | **−3.** The mirror's own verification fails, and R3-3 leaves a correct check unwired. Both are process defects in work that was added to *raise* rigor. |
| Methodological validity | 63 | 60 | **−3.** R3-1 is a mechanism claim with no executable support, in the paragraph whose purpose is measurement. |
| Reproducibility | 68 | 64 | **−4.** The version of record as published does not currently satisfy its own appendix contract. |
| Clarity | 64 | 64 | No change. |
| **Overall** | **65** | **61** | **−4.** Major Revision. |

---

## The finding that matters more than the four above

Rounds 1 and 2 found defects in the paper. Round 3 found **two defects in the act of fixing them** — an unsupported claim introduced while closing ND2, and a broken appendix promise introduced while closing N15. Both were caught by re-running verification rather than by reading the diff.

That is a signal about process, not about the manuscript. Three edit-and-audit cycles have now produced roughly one new defect per cycle in the closure work itself, while the underlying science has been stable since the round-1 fixes. Continuing to cycle is how a paper acquires a green build and a broken promise.

The recommendation is therefore procedural as much as editorial:

1. **Freeze the manuscript.** No further prose edits until the framing decision is made. R3-1 and R3-2 are the only open defects and neither requires a structural change.
2. **Close R3-1 and R3-2** as two small, mechanical edits — two corpus cases, one allowlist line.
3. **Close R3-3** by making the appendix contract executable, so this class cannot recur.
4. **Then make the framing decision**, which remains the only substantive question left and has been open since round 2: reframe around a deterministic verified-serving system with a priced intelligence ladder, or produce an experiment in which the generative path is necessary.
5. **Re-run the full verification set once**, as a single gate, rather than per-cycle: 1622 tests, the 47-check artifact audit, the cluster-bootstrap check, the figure geometry plus values check, and the mirror check.

Steps 1–3 are an afternoon. Step 4 is the real work, and it is not a task anyone can do for the authors.

---

## Closure ledger — author response, 2026-10-08 (added after the round-3 audit)

| # | Finding | Status | What changed |
|---|---|---|---|
| R3-1 | Context-dependence claim had no artifact behind it | **CLOSED — and the claim was half wrong** | Two minimal-context variants added to `scripts/verifier_harm_cases.py` as a new `X` group (`X-jwt-bearer-bare`, `X-slack-bot-token-bare`), each carrying the *same* credential string as its `F` counterpart with the surrounding lines removed, so a verdict difference isolates the surrounding text. `verifier_harm_probe.py` now reports a `context_contrast` block pairing each `X` case with its `F` counterpart. **Result: the JWT is caught in both forms; only the Slack bot token is served bare and caught embedded.** The paper's sentence was wrong and has been rewritten to say exactly that, and to conclude that the gate matches assignment syntax rather than the credential for that format — which is the argument for reporting per-format results instead of one coverage figure. The `X` group is deliberately excluded from the format-coverage count, and the module docstring records why. Headline numbers are unchanged: H 4/7, F 5/10. |
| R3-2 | Mirror failed its own verification on a path the appendix names | **CLOSED** | `scripts/build_anonymized_mirror.py` added to its own `SCRIPT_FILES` allowlist. Bundle is now 43 files, `verdict: PASS`, and `--check` returns `PASS`. |
| R3-3 | Nothing ran the mirror's verification | **CLOSED** | New `tests/unit/test_anonymized_mirror.py` (5 tests) asserts the *cause* rather than the instance: every `\path{}` target the shipped appendix names must be in the mirror allowlist; the builder must be in its own version of record; no allowlisted path may be excluded by policy or missing on disk; the unblinding key must never be shipped. Runs in ~1 s with no build. |
| R3-4 | Bundle's last recorded PASS was false | **CLOSED by R3-2/R3-3** | Bundle regenerated and passing; the contract is now enforced by a test in the default suite, so a stale bundle fails `pytest` rather than waiting for a human to run `--check`. |

### Two defects the closure itself introduced, and what they say

Closing R3-1 surfaced a **false positive in the mirror's own verifier**: the builder exempts itself from the "rule matched source but output unchanged" check, because its source necessarily contains its own replacement literals (`SG.REDACTEDREDACTED.REDACTEDREDACTED` matches the sendgrid pattern). The exemption was initially written against the wrong value and matched nothing; the survivor scan still covers that file, so the check is not weakened, only the no-op guard is scoped.

Closing R3-2/R3-3 exposed a **real performance defect**: `verify_existing()` re-read and re-normalised the 7.7 MB trajectory artifact once per rule — fifteen times — making the gate take **75 seconds**. That is not a gate anyone runs often, which is the same failure R3-3 was about. Normalising each file once cut it to **20 seconds**.

Both are the same shape as the finding that prompted the round: a verification mechanism that existed, was correct, and was not exercised on the path anyone actually took.

### Verification evidence for this pass

- Full suite: **1627 passed, 116 skipped, 0 failed** (365 s), including the 5 new mirror-contract tests.
- `scripts/verifier_redteam_check.py`: **47/47 PASS**; canonical 105-case artifact untouched.
- `scripts/verifier_ci_cluster_bootstrap.py --check`: aggregation matches published per-family counts.
- `scripts/gen_sp_figures.py --check`: figure values match the artifacts; figure geometry audit **5/5 pass, zero defects**.
- `scripts/build_anonymized_mirror.py`: `PASS` on build (43 files, 518 KiB) and `PASS` on `--check` (20 s).
- Mirror verdict-faithfulness re-verified after adding the `X` group: **0 verdict changes** across 28 harm-probe cases and 123 red-team cases.
- `sp2027.pdf`: 15 pages, bibliography from p. 13, **12 text pages** against the 13-page limit; 0 undefined references, 0 citation warnings, 0 errors, 0 overfull boxes.
- Round-1 and round-2 regression: `tab:b4`, stability, ladder, echo audit, ND1's overlap sentence, and ND3's format table all still reproduce exactly.

### Where the paper stands

Every finding raised across all three rounds is now closed. The round-3 audit's own recommendation — freeze prose, close the mechanical items, make the contract executable, then decide the framing — has been followed for the first three steps.

**What remains is the framing decision, and it is not a repair.** The surviving capability claim is about what the operator is told rather than what the honeypot serves; the serving control's measured boundary is four of seven authored disclosures and five of ten credential formats, correctly reported with intervals; and the ladder's fold-down results point at a different, arguably more valuable paper. Either reframe around a deterministic verified-serving system with a priced intelligence ladder, or produce an experiment in which the generative path is necessary. Both are honest. Neither can be executed by a reviewer, and the choice is cheaper to make before 2026-11-10 than after.