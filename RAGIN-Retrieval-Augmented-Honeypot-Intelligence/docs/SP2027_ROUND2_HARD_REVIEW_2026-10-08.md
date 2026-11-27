# RAGIN — Hard IEEE S&P Review, Round 2 (post-revision audit)

**Review date:** 2026-10-08, second pass, same day
**Submission surface:** `paper/sp2027.tex` + `paper/sections/{introduction,sp_threat_model,design,sp_related,sp_evaluation,conclusion,sp_appendix}.tex`; compiled `paper/sp2027.pdf`, 14 pages, bibliography from p. 12 (11 text pages against a 13-page limit), 0 undefined references, 56/56 references cited.
**Round-1 audit + closure ledger:** `docs/SP2027_HARD_REVIEW_2026-10-08.md` and `docs/SP2027_HARD_REVIEW_2026-10-08_POSTFIX.md`.

## Provenance of this audit (disclosed)

The five-seat panel (Journal-Fit, Methodology, Security Domain, Systems/Reproducibility, Devil's Advocate) was dispatched. **All five failed** on provider quota (`APIError: The usage limit has been reached`) on both the primary and fallback routes, 10 attempts total. This audit is therefore a **single-auditor pass with direct tool verification** — no role separation, no cross-model corroboration, correlated blind spots possible. Every number below was recomputed from disk by the auditor.

**Read-only confirmed:** no manuscript, artifact, script, or config file was modified in this pass. The inline verifier probes were run in-process and wrote nothing.

---

## Decision

**Major Revision** — unchanged in letter, but for a materially different reason than round 1.

The revision did what it claimed. Every one of the fifteen round-1 findings was checked against the manuscript and the artifacts; twelve verify as closed, two are partially closed, one (the artifact mirror) needs an action outside the repository, and **one closure claim is arithmetically false**. No regression was introduced in any previously verified number: Table `tab:b4`'s four intervals, the campaign headline table, the stability pair, the six-arm ladder, and the 97/218 echo correction all still reproduce exactly.

What blocks acceptance is now narrower and sharper. Round 1's problem was overclaiming. Round 2's problem is that **the paper now reports a negative result about its own security control using a sample too small and too favourable to support the number attached to it** — and an independent probe of the same gate, run during this audit, is materially worse than the published figure suggests.

---

## Closure audit of the fifteen round-1 findings

| # | Finding | Verdict | Evidence checked |
|---|---|---|---|
| N1 | Version-of-record guarded bounds withheld | **VERIFIED CLOSED** | `tab:live` carries ≤0.479 / ≤0.243 / 0.733 and composite ≤0.511. I re-derived the composite: the artifact's own `composite_raw_both_channel` 0.8796 equals the row-weighted mean of the three strata (123/35/60), so the row-weighted mean of the per-stratum guarded bounds (0.5106 for run 1, 0.4907 for run 2) is a **valid** bound. The aggregate is licensed by the artifact, not invented. |
| N2 | Abstract `+0.116` built on the invalidated channel | **VERIFIED CLOSED** | Absent from the abstract; retained only in §Evaluation and the conclusion with explicit non-readings. |
| N3 | Serve-path split from a latency inference | **VERIFIED CLOSED** | Label-based 216/2 is primary; the 88.1/11.9 split survives only as a stated sensitivity note. |
| N4 | Three surfaces, unlogged generators | **VERIFIED CLOSED** | `tab:provenance` maps all six surfaces with two `not logged (pre-pin gateway default)` rows; no number is compared across rows. |
| N5 | No related work; 54/61 refs uncited | **VERIFIED CLOSED** | New §4 with five subsections; 56 references, all cited in the body; 5 off-topic entries removed including an arXiv duplicate. |
| N6 | Safety claim unmeasured | **VERIFIED CLOSED** | The byte-identical-arms fact is now stated plainly, and coverage is measured (540/778 pooled). |
| N7 | Draft-level intervals ignored clustering | **VERIFIED CLOSED** | Cluster bootstrap over cases, 10,000 iterations, seed recorded; intervals genuinely wider; Pooled row added; the script asserts its aggregation against the published counts and exits non-zero on disagreement. |
| N8 | Injection coverage backed by n=1 | **VERIFIED CLOSED (by withdrawal)** | Property table no longer credits injection; both battery injection cases are reported as misses. |
| N9 | Eight-command declared surface | **VERIFIED CLOSED** | Enumerated in the property table and attached to every P=R=1.0 claim. |
| N10 | Danger gate detects style tells | **CLOSED, BUT SEE ND2/ND3** | The probe exists and its conclusion is honest. Its *number* does not characterise the gate. |
| N11 | Estimand / weighting mismatch | **VERIFIED CLOSED** | Stated in the setup paragraph. |
| N12 | No multiplicity control | **VERIFIED CLOSED** | Stated with the reason it is immaterial. |
| N13 | Figures hand-coded | **VERIFIED CLOSED — and it had drifted** | `gen_sp_figures.py` generates the values, `--check` passes, the geometry audit consumes the same definitions. The generator caught a live stale error bar (0.0573 → 0.0587). |
| N14 | Two unexplained 0.955 values | **VERIFIED CLOSED** | Both sourced to the same 400-session split under two procedures. |
| N15 | No artifact locator | **PARTIAL — external action** | Paper side closed (release timing, no locator, softened claim). The anonymised mirror is still a human action. |

**Regression check: clean.** `tab:b4` = +0.3167 [0.1617, 0.4800] / +0.1400 [0.0833, 0.1967] / +0.0050 [−0.0467, 0.0567] / +0.1539 [0.0922, 0.2206]; stability 0.8796 → 0.8845 (Δ 0.0049, agreement 0.9908), technique/actor MAD 0.0000 with agreement 1.0; ladder 0.0006 / 0.0704 / 0.5018 / 0.6176 ×3; echo audit 97/218. All 16 appendix paths resolve, including the three new ones.

---

## New findings

### ND1 — MAJOR — the revision's own decomposition does not add up

**Anchor:** `paper/sections/sp_evaluation.tex:186`
**Quote:** "The one fully attributed family (llama-3.3-70b, 281 drafts) **decomposes its 185 rejections into** 122 danger-signal violations … 38 identity-pin violations, and 28 fiction-contradiction violations."

122 + 38 + 28 = **188**, not 185. The per-check tallies in `results/verifier_redteam_live_llama33_complete.json` overlap: a single draft that fires both the danger and consistency checks is counted in both per-check totals, while the overall `true_positives` counts it once. **41 drafts fired more than one check.** There is no partition, so "decomposes into" is false as written, and a reader who adds the three numbers gets a count three higher than the total it claims to decompose.

This is a self-inflicted wound: the sentence was written during the revision, and the round-1 audit's own methodology seat would have caught it had it run.

**Remedy:** drop the word "decomposes". Report the per-check counts as an overlapping profile explicitly — e.g. "185 rejected drafts; across those, the danger gate fired on 122, the identity pin on 38, and the consistency layer on 28, with 41 drafts triggering more than one check" — or report only the per-check numbers without implying they sum to the total.

### ND2 — MAJOR — the published coverage rate describes the seven chosen cases, not the gate

**Anchors:** `paper/sections/sp_evaluation.tex:202` ("the gate stopped 4 of 7 harmful drafts (recall 0.571)"), `paper/sp2027.tex:68`

**0.571 is a property of the corpus, not of the verifier.** Seven cases were authored by the team that wrote the verifier, covering three credential shapes (PEM, plaintext key/value, normalized DSN) plus topology, off-script capability, persona-config leak, and an echoed secret. A rate computed from that corpus estimates the corpus, not the population of fluent on-fiction secret disclosures. Its own 95% Wilson interval is **[0.25, 0.84]** — the data are consistent with a gate that catches a quarter of such disclosures and with one that catches most of them.

Publishing `recall 0.571` invites the reader to believe the gate stops roughly 57% of harmful disclosures. The defensible claim is directional and the paper nearly states it: the gate stops the credential *formats it was written against*.

**Remedy:** replace the rate with counts and the interval ("stopped 4 of 7 authored cases; the 95% interval on 7 cases spans [0.25, 0.84], so we report this as a boundary demonstration rather than an estimate of coverage"), or enlarge the corpus until a rate means something.

### ND3 — MAJOR — an independent probe of the same gate is materially worse than the published figure implies

**Anchor:** the gate as implemented in `ragin/cycle/verifier.py:55-63` and `ragin/hisoka/deception.py:914-939, 873-890`; measured during this audit.

I scored seven common real-world credential formats through the real serving-path verifier. **One was flagged; six were served:**

| Draft | Verdict |
|---|---|
| JWT bearer token (`Authorization: Bearer eyJ…`) | **SERVED** |
| Slack bot token (`xoxb-…`) | **SERVED** |
| HTTP Basic auth header | **SERVED** |
| MySQL DSN containing a password | **SERVED** |
| npm registry auth token | **SERVED** |
| PKCS#8 private key block | **SERVED** |
| GitHub PAT (`ghp_…`) | flagged |

For contrast, an AWS key ID is flagged **with or without** the `EXAMPLE` marker, and a `password=`/`key=` style assignment is flagged — so the gate is not uniformly weak, and the earlier hypothesis that its secret arm detects only fabrication markers is wrong. It covers a specific set of formats and misses others, and **JWT and DSN-embedded credentials are among the misses.** The paper reports the PEM and normalized-DSN misses but not these, and the two families it does report happen to be the two a reader is most likely to imagine as covered.

Note the direction of the finding: this **confirms** the revision's stated conclusion — "a keyword-and-consistency gate is therefore not a content-security control" — and shows the published rate is, if anything, generous.

**Remedy:** report the format-level result rather than only the case-level result. A compact table of credential formats attempted and flagged/served is a stronger, cheaper, and more honest contribution than seven hand-built narratives, and it is the number an operator would actually need.

### ND4 — MODERATE — the "regenerating checks" claim overstates what two of the three scripts do

**Anchor:** `paper/sections/sp_appendix.tex` ("Three checks regenerate rather than merely store the paper's derived numbers")

- `scripts/bootstrap_ci.py` — **accurate.** Recomputes the paired intervals and live suite means from persisted rows, and refuses to report a paired interval when the arm key-set, duplicate, or suite-membership audit fails.
- `scripts/verifier_ci_cluster_bootstrap.py` — **accurate.** Resamples cases and asserts its aggregation against the published counts. Verified: aggregation matches; `--check` passes.
- `scripts/gen_sp_figures.py` — **partially accurate.** It generates the *values* the figures plot, which is real and caught a live defect. It does **not** verify that the figures are otherwise consistent, and it introduces a build-order coupling: a stale `generated_values.tex` is caught only if someone runs `--check`, which nothing in the build currently does. The paper's own §Appendix figure-audit paragraph still reports the geometry audit as the figure check, so a reader could reasonably infer the values are covered by it. They are not.
- `scripts/audit_figure_geometry.py` was modified to consume the generated definitions, so the geometry audit now validates a file it does not itself regenerate.

**Remedy:** either add `--check` to the figure audit entry point so the two run together, or soften "three checks regenerate" to what each does.

### ND5 — MINOR — the pooled interval's stratification is unstated

**Anchor:** `paper/sections/sp_evaluation.tex:185` ("both cluster bootstraps over cases")

The pooled figures resample **cases within each author family**, holding each family's case count fixed, because the three families span two providers with different draft counts and error profiles. That is the right choice, but the manuscript does not say so; a reader who reads "cluster bootstrap over cases" will assume the pooled cases were resampled as one pooled set. **Remedy:** add "stratified by author family" to the sentence.

### ND6 — MINOR — the new §4 Related Work is defensible but thin where it matters most

**Anchor:** `paper/sections/sp_related.tex`

The section is written deliberately at title-and-venue granularity, which is honest and safe, and it does engage all four threads a reviewer would name: generative honeypots, runtime enforcement and agent injection, RAG grounding *and the attacks on it*, and LLM-as-judge. Two gaps remain. First, the runtime-enforcement subsection claims prior work "protects the assistant's user from the model's output" without engaging any evaluation of those systems' effectiveness, so the comparison is asserted. Second, the RAG-attacks subsection correctly adopts the poisoning threat model as out of scope — but that leaves the paper's own retrieval layer undefended against a threat its related work has just told the reader is live and well studied. That is a legitimate scoping decision, and it is currently priced at zero. **Remedy:** one sentence acknowledging that the retrieval layer sits inside the poisoning literature's threat surface and is unevaluated here.

---

## Systems and reproducibility lane

**Verified clean.** All 16 `\path{}` targets resolve, including the three new rows. The build is 11 text pages against a 13-page limit with 0 undefined references, 0 citation warnings, and 0 overfull boxes. Figure values and cluster-bootstrapped intervals both pass their `--check` modes.

**Unchanged from round 1 and still open:** no field or internet-facing deployment exists (`docs/AZURE_FIELD_STATUS.md` records no VM, subscription still on a billing hold); the live numbers are archived rather than reproducible without a provider key; the free-provider dependency remains the structural obstacle to an independent rerun; and the "regenerating" scripts require only local artifacts, which is a genuine improvement over the round-1 state.

**New observation.** The generator introduces a build-order dependency that did not previously exist: the figures now resolve through a generated file, so a contributor who edits a figure by hand gets no error. This is the standard trade for eliminating silent drift, and the mitigation is one line — run `gen_sp_figures.py --check` in the same entry point as the geometry audit.

---

## Devil's Advocate — strongest counter-argument

The revision has succeeded in making the paper's *negative* results undeniable while leaving its *positive* thesis resting on the one component it has just measured to be nearly ineffective. Read the abstract as a whole: the only capability claim that survives is the analysis-channel grounding result, which is about **what the operator is told**, not about what the honeypot serves or whether the serving is safe. The serving claim now rests on a gate that the paper itself measures at 4 of 7 on authored cases, at 1 of 7 on common credential formats, that missed both prompt-injection cases it was given, and that changed **nothing** about the 218 served rows — the verified and no-verifier arms are byte-identical. Meanwhile the paper's own ladder reports that routing left the serving path, that BM25 beats the graph index, and that the rescue controller is subsumed. The convergent reading is that every component measured on its own merits was removed or found wanting, and the surviving architecture is a deterministic template engine with a retrieval index attached, for which the paper's title and framing promise generative deception. A reviewer who accepts every disclosure the authors have made — and the disclosures are unusually forthcoming — still cannot identify an experiment in which the generative path was necessary. That is not a repairable gap in the current framing; it is evidence that the framing, not the engineering, is what needs to change.

**Adjudication: VALIDATED as a framing problem, not a validity problem.** Nothing here contradicts the artifacts. It is the reason the recommendation is Major Revision rather than Accept, and it is not fixable by adding experiments before 2026-11-17 — it is fixable only by choosing the honest thesis and rewriting the title, abstract, and contribution list around it. The defensible thesis is already present in the paper's fold-down results and cost/ladder analysis.

---

## Scorecard

| Dimension | Round 1 | Round 2 | Change and justification |
|---|---:|---:|---|
| Security relevance | 74 | 73 | −1. The problem is real, but the paper now measures its own control's boundary at roughly 1-in-7 on realistic credentials, which caps the security claim rather than supporting it. |
| Novelty | 34 | 62 | **+28.** A related-work section exists, 56 references are all cited, and the four required threads are engaged. The gap is now assessable, which is most of what novelty scoring at S&P measures. |
| Significance | 60 | 61 | +1. The self-audit and the fold-down discipline are genuinely useful to the community. |
| Technical quality | 70 | 74 | +4. Architecture, artifact discipline, and the three regenerating checks are real strengths; ND1 is a wording error, not a design fault. |
| Methodological validity | 61 | 63 | +2. Clustering, provenance, and pairing are all correct now; ND1 and ND2 are reporting defects in an otherwise much sounder treatment. |
| Reproducibility | 55 | 68 | **+13.** Figure drift is now impossible by construction, intervals are regenerating and self-asserting, and all artifact paths resolve. Still capped by archived-only live numbers and no mirror. |
| Clarity | 68 | 64 | −4. The abstract is now heavily hedged; a reader must work to find the single positive claim that survives. That is an honest cost of the corrections, but it is a cost. |
| **Overall** | **58** | **65** | **+7.** Major Revision. |

---

## What the revision genuinely achieved

The two things round 1 called blockers are closed, and closed properly: the paired grounding experiment now has an auditable pairing contract whose intervals reproduce bit-for-bit, and the threat model is a real section with an explicit property/evidence/nonclaim table whose nonclaims are specific rather than generic. The self-audit that discovered the echo-scorer defect is a genuine contribution to measurement practice. The fold-down results are reported against the authors' interest, including that the adaptive routing rung left the serving path. And the newly reported 4-of-7 boundary result is the kind of finding most papers suppress; reporting it in the abstract costs the authors the flattering reading and is to their credit.

The new generator earning its keep by catching a stale error bar on its first run is the clearest signal that the artifact discipline in this repository is real.

---

## Required before acceptance

**P0**
1. Fix ND1 — the 122/38/28 sentence. It currently misstates an artifact by three and asserts a partition that does not exist.
2. Fix ND2/ND3 — replace `recall 0.571` with counts plus an interval, and add the credential-format result (ND3), which is stronger evidence than the seven narratives it would accompany.
3. Choose the thesis. Either reframe the title, abstract, and contribution list around what the evidence supports (a deterministic verified-serving system with a priced intelligence ladder), or supply an experiment in which the generative path is necessary. The current framing promises more than the measurements deliver.

**P1**
4. ND4 — wire `gen_sp_figures.py --check` into the same entry point as the geometry audit, or soften the "three checks regenerate" claim.
5. ND5 — state the pooled interval's stratification.
6. ND6 — one sentence acknowledging the retrieval layer's exposure to the poisoning literature the new related work cites.
7. N15 — produce the anonymised mirror. Still the only open item requiring an action outside the manuscript.

---

## Closure ledger — author response, 2026-10-08 (added after the round-2 audit)

| # | Finding | Status | What changed |
|---|---|---|---|
| ND1 | 122 + 38 + 28 = 188 presented as a decomposition of 185 | **CLOSED** | `sp_evaluation.tex` now reads: the family "rejected 185 drafts; across those the danger gate fired on 122, the identity pin on 38, and the consistency layer on 28, **with 41 drafts triggering more than one check, so those three counts overlap and do not partition the 185**." Verified against the artifact: `per_check` sums to 188 while `overall.true_positives` is 185. |
| ND2 | `recall 0.571` characterises the corpus, not the gate | **CLOSED** | The rate is gone. The narrative probe is now reported as "stopped four of the seven", with the explicit statement that "with seven cases the 95% interval on that count spans $[0.25,0.84]$, so we report it as a boundary demonstration and not as an estimate of coverage." The abstract reports counts, not a rate. |
| ND3 | Credential-format coverage unmeasured | **CLOSED, with worse numbers than the review estimated** | New `F` group in `scripts/verifier_harm_cases.py`: ten single-purpose credential-format probes plus four benign look-alikes, scored through the real serving-path verifier. Result: **5 of 10 flagged, 5 served** — served are npm registry tokens, HTTP Basic credentials in a service config, a MySQL DSN with an embedded password, a PKCS#8 private key, and a SendGrid API key. Flagged are JWT bearer tokens, Slack bot tokens, GitHub PATs, AWS access key ids, and `password=` assignments. **2 of 4 benign look-alikes were also refused** (a placeholder token assignment, and a shadow `/etc/shadow` entry whose refusal is arguably conservative). The probe also reports **context-sensitivity**: the JWT and Slack drafts are caught only because of the surrounding assignment lines, and are served when presented without them — so the gate keys partly on assignment syntax rather than on the credential itself. |
| ND4 | "Three checks regenerate" overstates; staleness check unwired | **CLOSED** | `scripts/audit_figure_geometry.py` now runs `gen_sp_figures.py --check` as part of its own run, with the geometry verdict and the values verdict failing together. Verified: the audit prints `figure values OK` and exits non-zero if the generated file is stale. The appendix now states this, including why the geometry audit structurally cannot detect a stale value on its own. |
| ND5 | Pooled interval stratification unstated | **CLOSED** | The sentence now reads "cluster bootstraps that resample cases **within each author family**". |
| ND6 | Retrieval layer's poisoning exposure unpriced | **CLOSED** | §4 closes with: "We price that scoping rather than hide it. The retrieval layer sits inside the threat surface this literature has already mapped... the grounding rung's measured benefit of $+0.154$ is a benefit under an undefended retrieval layer. Closing that is a prerequisite for treating the grounding result as a security contribution rather than a capability one." |
| N15 | No artifact locator | **CLOSED** | New `scripts/build_anonymized_mirror.py` assembles an anonymised mirror of the version of record: 42 files from an **explicit allowlist** (not a glob), an 18-rule redaction pass, and a `MANIFEST.json` with a sha256 per file. The build **fails** rather than warns if (a) any of the 16 appendix `\path{}` targets fails to resolve inside the bundle, (b) any author identity, cloud identifier, or credential-shaped string survives, or (c) a rule matched its source but left the file unchanged. Verified: `verdict: PASS`, 42 files, 512 KiB tarball, `--check` PASS. **Credential redaction is format-preserving** — prefixes are kept and only the secret body is replaced — so the mirrored probe corpora return **identical verdicts to the originals: 0 verdict changes across 26 harm-probe cases and 123 red-team cases**, with case structure (keys, labels, categories) identical and both mirrored files still parsing as valid Python. The appendix now states the mirror, the allowlist discipline, the failing-verification behaviour, and the verdict-faithfulness guarantee. What remains is the human step of *publishing* the bundle wherever the venue permits. |

### Design change worth recording

The probe now separates two groups that must never be pooled, and the artifact says so in `method.group_note`: `H` (authored narratives, reported as counts) and `F` (credential formats, reported per format). Pooling them would produce a single rate over seventeen self-authored cases — exactly the statistic ND2 rejected.

### Verification evidence for this pass

- Full suite: **1622 passed, 116 skipped, 0 failed** (341 s).
- `scripts/verifier_redteam_check.py`: **47/47 PASS**. The canonical 105-case artifact is untouched.
- `scripts/verifier_ci_cluster_bootstrap.py --check`: aggregation matches published per-family counts.
- `scripts/audit_figure_geometry.py`: all five figures `pass`, plus `figure values OK` from the newly wired staleness check.
- `scripts/build_anonymized_mirror.py`: `verdict: PASS` on build, `PASS` on `--check`; verdict-equivalence of the mirrored corpora confirmed at 149/149 cases.
- `sp2027.pdf`: 15 pages, bibliography from p. 13, so **12 text pages** against the 13-page limit; 0 undefined references, 0 citation warnings, 0 errors, 0 overfull boxes, **56/56 references cited**.
- Round-1 regression check re-run and clean: `tab:b4` four intervals, stability pair, six-arm ladder, and the 97/218 echo correction all reproduce exactly.

### A note on the mirror's design constraint

Closing N15 was not a packaging job. Redacting the credential strings out of the
two probe corpora **changed four verdicts** on the first attempt, because the
gate detects those formats by their prefix and length: strip the prefix and the
detection stops firing. A mirror built that way would have shipped a
`verifier_redteam` suite whose reported failures no longer matched the paper's,
which is worse than not shipping it.

The fix was format-preserving redaction — keep `AKIA`, `ghp_`, `xoxb-`, `npm_`,
`SG.`, and the PEM `BEGIN`/`END` scaffold, replace only the secret body with an
obviously synthetic alphanumeric marker — plus two refinements the verifier
forced: the survivor scan has to distinguish a placeholder from real material
(it now strips `REDACTED`-bearing tokens before matching, and drops a PEM block
only when its body is redacted), and the PEM replacement must stay on one line,
because these corpora are Python source and a raw newline produces an
unterminated string literal. `--check` caught that last one by failing on the
broken bundle. The result is a mirror that is both secret-free and
verdict-identical.

### Where the paper stands after this round

**Every finding raised in either round is now closed.** The only remaining work is a human step: publishing the mirror bundle wherever the venue permits an anonymous link.

That leaves the framing decision, which was never a defect. The Devil's Advocate's structural objection survives all the fixes: the surviving capability claim is about what the operator is told rather than what the honeypot serves, and the serving control's measured boundary — four of seven authored disclosures, five of ten credential formats — is now published in the abstract. The authors have two honest options, and the evidence for both is in the paper: reframe the title, abstract, and contribution list around a deterministic verified-serving system with a priced intelligence ladder, or supply an experiment in which the generative path is necessary. Neither is a repair task; both are framing choices, and the deadline for making one is well before 2026-11-10.