# Style Goldfish — Copy-Editing Review (EGM Stage: FeatureRange)

**TargetFile:** `/home/elaref/Documents/research/ragin/paper/main.tex`
**Scope:** lines 1–1124 (frontmatter, abstract, nomenclature, Introduction, Related Work, Architecture, Experimental Setup through Eq. (2))
**Reviewer persona:** Technical Copy Editor (clarity, precision, brevity, objectivity)

---

## 1. Overall Assessment

The draft is unusually candid for a systems-security paper: the scope re-statement (l. 245–253), the capability-table note (l. 521–525), and the "What is novel" paragraph (l. 255–273) are well-calibrated and should be **kept**. The dominant style problems are (a) an **internal-consistency cluster** — the same facts are stated with different values in different sections (corpus size, tree count, tier count, RAM, RAGIN's own expansion), which a copy edit alone cannot fix but which copy editing surfaces; (b) a **self-praise lexicon** ("candid", "honest", "more honest", "inflated") that editorializes about the paper's own virtue instead of letting the numbers speak; and (c) **sentence-length overload** in the architecture and validation sections, where 50–65-word sentences bury the load-bearing claim. The rhetorical voice of the Introduction ("Picture an SSH banner at 03:14", "silent witnesses", "not decoration") is a house-style choice; it is flagged where it shades into ungrounded or self-congratulatory, not on taste grounds.

---

## 2. Findings

### A. Internal inconsistency / uncalibrated claims (facts stated differently in different places)

**A1. 🔴 Attacker-tier taxonomy is stated three incompatible ways.**
- *Evidence:* l. 226–227 "selects one of **five personas**"; Table `tab:tiers` (l. 790–804) defines **three** tiers (Novice / Intermediate / Expert-APT); l. 587–588 trains on "500 per tier" of 2,000 sessions = **four** classes, confirmed by l. 597–599 ("novice↔intermediate and expert↔apt … per-class recalls of 0.91/0.89/0.85/0.90" — four values); l. 1043 red-team personas are "novice, intermediate, **advanced**".
- *Rationale:* Same concept, four names/counts. A reader cannot map "persona" to "tier" to "class" without guessing. This also undermines the headline ablation claims that depend on tier structure.
- *Action:* Pick one taxonomy (recommend the 4-class training taxonomy: novice / intermediate / expert / APT), state it once, and if the persona layer instantiates five distinct personas over four tiers, say so in one sentence at first use. Replace "advanced" with "expert" at l. 1043.

**A2. 🔴 Random Forest tree count contradicts itself.**
- *Evidence:* l. 594 "500 trees, depth 16" (shipped ensemble); l. 665 "The **200-tree** Random Forest"; l. 681 Algorithm 1 "Random Forest, **200 trees**"; l. 1003 "O(200·10)".
- *Rationale:* Either the ensemble was retrained (500 trees) and the algorithm/caption are stale, or vice versa. A reviewer will read this as carelessness about the artifact of record.
- *Action:* Reconcile against the released `benchmark_report.json` and use one number everywhere.

**A3. 🔴 Corpus size drifts across six spellings.**
- *Evidence:* l. 53 "more than 780,000"; l. 152 "780,000-document"; l. 219 "780,000+ documents"; l. 259 "780,600-document"; l. 364 "780,000+ documents"; l. 539 "780,000-document"; l. 704 and Table `tab:kb` (l. 738) "780,600".
- *Rationale:* The precise figure (780,600) appears in the table and the Don section; the abstract and intro round it inconsistently. Pick the exact figure everywhere; "more than 780,000" and "780,000+" are also two different roundings of the same fact.
- *Action:* Use "780,600" at every occurrence (abstract included); delete the roundings.

**A4. 🔴 Chrollo's output schema is described two contradictory ways.**
- *Evidence:* l. 582–584 "produces a **skill-level classification** with confidence s ∈ [0,1]"; l. 670–675 I/O contract "classification label y ∈ {malicious, benign, reject}" (Algorithm 1, l. 680–698, matches the latter).
- *Rationale:* A skill-tier classifier and a malicious/benign/reject gate are different artifacts. Section 2.3 (l. 384–387) further says Chrollo escalates "sessions exceeding a confidence threshold of 0.85", which fits neither schema cleanly. The pipeline narrative ("skill stratification drives personas") and the algorithm narrative ("malicious/benign routing") never meet.
- *Action:* State the two-stage decision explicitly: (i) malicious/benign/reject gate at τ=0.85 with reject band, then (ii) skill-tier assignment among escalated sessions. Rewrite the I/O contract and l. 582–584 to match.

**A5. 🔴 "Top-15 feature importances" for a 10-feature model.**
- *Evidence:* l. 811–812 "anchored empirically in Chrollo's **top-15** feature importances (`results/benchmark_report.json`)" vs. the 10-feature vector (l. 582, Table `tab:chrollo-feat`, l. 642–663).
- *Rationale:* Impossible on its face; likely a leftover from the prototype feature families (l. 620–637 add 8 phase + 32 n-gram features = 50). If the anchor uses the prototype features, say which model version.
- *Action:* "anchored empirically in Chrollo's feature importances (`results/benchmark_report.json`)" — or name the correct count and model.

**A6. 🟡 RAGIN's expansion differs between title and body.**
- *Evidence:* l. 28 title "Retrieval-Augmented Honeypot Intelligence"; l. 199 "RAGIN (Retrieval-Augmented Honeypot Intelligence **Network**)".
- *Rationale:* The acronym's own definition is inconsistent; the N silently appears and disappears.
- *Action:* Use the title's expansion everywhere, or add "Network" to the title.

**A7. 🟡 "Eight design bets" are never enumerated.**
- *Evidence:* l. 214 "a story of eight design bets and a steady accumulation of capability."
- *Rationale:* The paper then presents three contributions and four primitives. "Eight" is an unanchored count — the reader searches for a list that does not exist in scope.
- *Action:* Either enumerate the eight bets (one sentence each, or a table) or write "a sequence of design bets".

**A8. 🟡 Unqualified absolute claims in Related Work.**
- *Evidence:* l. 360 "A critical limitation shared across **all** prior RAG-for-security systems"; l. 361–363 "**No existing system** combines RAG with live honeypot session data…"; l. 489–490 "**No prior system** simultaneously combines…".
- *Rationale:* l. 148 hedges the same claim ("To our knowledge, no system has run RAG against a live attacker session"); l. 360–363 and l. 489–492 drop the hedge. Universal negatives over an entire literature are unprovable.
- *Action:* Restore "to our knowledge" at l. 360 and l. 489, or scope the claim ("no system we surveyed (Section 2.1–2.5)").

**A9. 🟡 "Live production stack" vs. "not a deployed system".**
- *Evidence:* l. 1013 "deployed as a **live production stack** on a single public AWS EC2 instance" vs. l. 251–252 "not as a deployed system that has held external attackers" and l. 522–523 (external ✓ "should not be read as 'deceived an external attacker in production'").
- *Rationale:* "Production" is precisely the word the scope re-statement disclaims. The internal tension is resolvable ("live public-cloud deployment") but the current wording lets a skim-reader overclaim on the authors' behalf.
- *Action:* l. 1013 → "deployed as a live public-cloud stack".

**A10. 🟡 "Substantially larger" has no comparator.**
- *Evidence:* l. 717–719 "Unlike prior RAG deployments in CTI, Don's corpus is **substantially larger** and tailored to live honeypot-session grounding."
- *Rationale:* Larger than which system, by what measure? Prior-work corpus sizes are not given anywhere in scope, so the comparative is unverifiable.
- *Action:* Either cite the comparison corpus size or drop "substantially larger" and keep "tailored to live honeypot-session grounding".

**A11. 🟢 Metric-name drift in the "fidelity" family and the composite.**
- *Evidence:* "lexical content fidelity" (l. 58), "content fidelity" (l. 286), "deployment fidelity" (l. 826, 899, 989), "live fidelity" (l. 67); "composite effectiveness (lexical)" (l. 205, 243, 287, 295) is forward-referenced as "detailed in Section results" (l. 1116) and its relationship to the formally defined IQS (l. 1070–1080, same 0.697 headline value at l. 1095) is never stated.
- *Rationale:* Four names for one latency-bounded-fidelity concept, and two metric names that appear to denote the same number.
- *Action:* Define once: "deployment fidelity (fraction of live queries returning grounded, non-refusal content within the 90 s budget)" and state whether composite effectiveness = IQS.

### B. Self-referential praise / subjective judgments of the paper's own work

**B1. 🔴 The paper repeatedly grades its own honesty.**
- *Evidence:* "candidly bounding" (l. 67), "a candid gap" (l. 207), "honest-negative accounting" (l. 265), "the live deployment metric is **more honest**" (l. 288), "an honest boundary we characterize rather than overstate" (l. 434), "rather than a single **inflated** mean" (l. 303).
- *Rationale:* Candor is demonstrated by the reported numbers (10.1% grounded, 86.7% timeouts, the falsified red-team claim); labeling it is marketing. "More honest" and "inflated" additionally take unargued swipes at unspecified alternative reporting practices.
- *Action (top-5 rewrite, see §3, R4):* Delete the self-assessments; keep the numbers and the hedges.

**B2. 🟡 Verdict adjectives where numbers suffice.**
- *Evidence:* "operationally sound, conservative choice" (l. 618); "comprehensive" in Table `tab:kb` (l. 738); "scores strongly" (l. 286); "richly instrumented environments" (l. 46); "stubbornly non-adaptive" (l. 47); "high-fidelity recorder" (l. 119); "The RAG layer is not decoration; it is the intelligence source" (l. 156–157).
- *Rationale:* Each is either supported by adjacent numbers (l. 614–617 give the ECE and escalated-population accuracy — the verdict clause adds nothing) or is unmeasurable ("comprehensive", "richly").
- *Action:* l. 618 → end the sentence at "…zero cross-tier errors." l. 738 → "Mixed" (drop "comprehensive"). l. 156–157 → "The RAG layer supplies the TTP signal: removing it removes all detected TTPs (Section 6)."

**B3. 🟡 Novelty claim at l. 259 lacks the "to our knowledge" hedge used elsewhere.**
- *Evidence:* l. 257–260 "First, *grounding at interaction time*: prior RAG-for-security systems retrieve from static reports…; RAGIN retrieves from a 780,600-document corpus at the moment an attacker types a command."
- *Rationale:* The same claim is correctly hedged at l. 148. Inside a paragraph titled "What is novel" the unhedged form reads as a proven universal.
- *Action:* "To our knowledge, RAGIN is the first to retrieve … at the moment an attacker types a command."

**B4. 🟡 "First" attributed to a cited work without attribution of the claim.**
- *Evidence:* l. 394–396 "The 'LLM Agent Honeypot' deployment [reworr2024] represents **the first empirical study** of AI hacking agents in the wild."
- *Rationale:* The "first" is the cited paper's framing; asserting it in the survey voice makes it the authors' claim to defend.
- *Action:* "…described by its authors as the first empirical study of AI hacking agents in the wild."

### C. Sentence length / overload (sentences > ~40 words)

**C1. 🔴 (worst-5, R1) l. 587–592 (~55 words, passive chain).**
"The shipped ensemble was retrained on a corpus of 2,000 labelled sessions (500 per tier) synthesized from tier-profiled command banks grounded in the extractor's own pattern families (…) and per-tier pacing profiles; per-session category mixes are Dirichlet-jittered and inter-command delays are lognormal, so adjacent-tier boundaries overlap rather than being artificially separable."
- *Rationale:* Four passive constructions ("was retrained", "synthesized", "grounded", "are Dirichlet-jittered") plus a nine-item parenthetical; the methodological point (synthetic data, overlapping tiers) is buried.

**C2. 🟡 l. 593–599 (~50 words).** The em-dash-embedded hyperparameter sweep inside the accuracy sentence duplicates information that belongs in the artifact manifest.

**C3. 🟡 l. 705–716 (~60 words).** The corrective-RAG state machine sentence chains decompose → retrieve → grade → check → rewrite → retry → fallback in one breath; the degradation sentence (l. 711–716) is a second independent claim stapled to it.

**C4. 🟡 l. 247–253 (~60 words).** The scope re-statement's single sentence carries the evaluation result, the red-team finding, its root cause, and the reading instruction. The content is exemplary (KEEP the caveat itself — it names a concrete decision: read as baseline, not deployed); the packaging is not.

**C5. 🟡 Table `tab:latency` caption, l. 871–877 (~65 words).** Captions should state what the table shows; the 158× explanation belongs in the body text, where it is already repeated.

**C6. 🟢 l. 288–290 (~45 words), l. 490–492 (~45 words), l. 807–812 (~50 words), l. 440–454 threat-model paragraphs** — same pattern at lower severity.

### D. Passive-voice clusters

**D1. 🟡 l. 587–592** — "was retrained … synthesized … grounded … are Dirichlet-jittered … are lognormal" (four passives in two clauses). Covered by R1.

**D2. 🟡 l. 221–222, l. 231–232** — "per-benchmark accuracy **is reported** in Section…"; "figures **are reported** only where they have a corresponding measurement section". Both are author-decisions recast as events. → "Section 6 reports per-benchmark accuracy"; "We report per-component figures only where a measurement section exists."

**D3. 🟡 l. 1013–1015** — "RAGIN **was deployed** as a live production stack on a single public AWS EC2 instance … **fronted by** an nginx reverse proxy." One active subject recovers both clauses: "We deployed RAGIN on a single public AWS EC2 instance (2 vCPU, 3.7 GB RAM, 40 GB EBS, Ubuntu LTS) behind an nginx reverse proxy."

**D4. 🟢 l. 288–289** — "10.1% of responses **were delivered** as grounded … content" — acceptable (the deliverer is the system, and the agent is clear from context); flagged for pattern awareness only.

### E. Undefined-at-first-use notation and terms

**E1. 🟡 Chrollo / Don / Hisoka used before definition.** l. 176 (body first use: "invokes Chrollo for classification, Don for RAG enrichment, and Hisoka for adaptive response") precedes the l. 218–232 contribution list and Section 3.2–3.4 definitions. → On first use: "Chrollo (the classifier; Section 3.2), Don (the RAG engine; Section 3.3), and Hisoka (the deception generator; Section 3.4)".

**E2. 🟡 "Arm-C" (l. 226).** "the no-RAG ablation narrows retrieval from a full 5-vs-0 signal to a prompt-controlled 3-vs-0 signal (Arm-C: neutral prompt + unrelated filler)" — the arm lettering scheme is not introduced; Arms A/B never appear in scope. → Name it "a prompt-controlled arm (neutral prompt + unrelated filler)" or introduce the arm scheme where defined.

**E3. 🟡 "composite effectiveness (lexical)" used in the abstract and l. 205 before any definition** — forward reference to Section 6 only (l. 1116). Abstracts may name a metric, but the parenthetical "(lexical)" is unexplained until late. → "a composite effectiveness score over lexical content fidelity".

**E4. 🟡 "ECE" (l. 614), "OOF" (l. 594 "out-of-fold", then bare "OOF-to-test collapse" l. 635), "CV" in Table `tab:chrollo-feat` (l. 658), "n.s." (l. 633).** None are in the Nomenclature (l. 79–107); ECE and CV are ambiguous to non-ML security readers. → Expand at first use ("expected calibration error (ECE)", "coefficient of variation (CV)") and add to the Nomenclature table.

**E5. 🟡 "honeytokens" (l. 296).** Domain term, undefined, absent from Nomenclature; the Cowrie comparison ("Cowrie 3.0.x has no honeytoken engine") depends on it. → One clause: "30 honeytokens (canary credentials, files, and endpoints planted for exfiltration detection)".

**E6. 🟢 "in distribution" (l. 633).** ML jargon standing alone ("helps marginally in distribution"); → "in-distribution" (hyphenated, or "on the original split").

**E7. 🟢 l. 1022 "all source is public at RAGIN."** Reads as "public at [the system]"; the referent is the GitHub repository. → "all source is public in the RAGIN repository."

### F. Copy-editing defects (typos / spacing)

**F1. 🟢 Missing spaces (five instances):** l. 253 "steprequired" → "step required"; l. 633 "but\emph{degrades}" → "but \emph{degrades}"; l. 705 "tab:kb}).Upon" → "}). Upon"; l. 811 "regimes,and" → "regimes, and"; l. 633 also "(+1.0pp, n.s.) but\emph" (same instance as above).

**F2. 🟢 l. 665–666 "The 200-tree Random Forest"** — apart from the A2 contradiction, the article usage here conflicts with "The shipped ensemble" (l. 594) and "a Random Forest ensemble" (l. 582); standardize on "the Random Forest ensemble".

**F3. 🟢 Decimal-precision inconsistency, l. 606–610.** "0.887 ± 0.007 … 0.885 ± 0.004 … 0.8865 ± 0.003" — the third figure carries an extra significant digit for no stated reason. → Round uniformly to three decimals.

**F4. 🟢 RAM figure:** ~4 GB in the abstract (l. 65) and l. 241, 553 vs. 3.7 GB at l. 1014. Acceptable rounding, but the abstract could say "under 4 GB" once and the setup keeps 3.7 GB.

**F5. 🟢 Complexity notation, l. 1001–1005.** "O(T·d) = O(200·10) per session, constant in N" — O(200·10) is a constant, not a class; and "the BM25 sparse branch at O(N) but capped at k_s = 3 candidates" conflates scan cost with candidate count. → "Chrollo's RF inference is O(T·d) — 200 trees × 10 features — constant in N; the BM25 branch scans the full index at O(N) but returns at most k_s = 3 candidates."

**F6. 🟢 Redundancy between text and caption.** l. 1083–1088 ("robustly specified for the headline comparison") and Table `tab:sensitivity` caption l. 1094–1096 repeat the identical claim twice on the same page. Keep it in one place (recommend the caption, since the table is what a skimmer reads).

**F7. 🟢 Synonym redundancy, l. 298–299.** "applies 7 evaluation role descriptions (scoring lenses, not separate judge models [paul2025]) as scoring lenses" — "scoring lenses" twice in one sentence. Drop the second occurrence.

**F8. 🟢 Circular cross-reference, l. 744–747.** "HNSW graphs give O(log N) …; this matches the O(log N) bound cited in the complexity analysis of Section 4.6" — the bound is stated here and stated again there; "this matches" adds no information. Delete the second clause.

### G. Defensive-caveat calibration (DROP | CALIBRATE | RELOCATE | KEEP)

| Location | Caveat | Verdict |
|---|---|---|
| l. 245–253 Scope re-statement ("internally validated, externally pending"; "not as a deployed system that has held external attackers") | Names the concrete reader decision (how to cite the work) and is backed by the red-team result | **KEEP** — exemplary |
| l. 521–525 Table note ("external ✓ … should not be read as 'deceived an external attacker in production'") | Prevents exactly the over-reading a capability table invites | **KEEP** |
| l. 239–243 ("We do not claim that any single primitive is novel on its own…") | Calibrated scoping of the contribution claim | **KEEP** |
| l. 431–434 ("an honest boundary we characterize rather than overstate") | The hedge is fine; the self-praise is not | **CALIBRATE** — keep the quantitative contrast, drop "honest … rather than overstate" |
| l. 67, 207, 265, 288, 303 ("candidly", "candid gap", "honest-negative accounting", "more honest", "inflated") | No reader decision; pure self-assessment | **DROP** |
| l. 859–866 ("to bring end-to-end latency below one second **without accuracy degradation**") | Future-work promise asserting an untested property | **CALIBRATE** — "targeting sub-second end-to-end latency; accuracy impact to be evaluated" |
| l. 1036–1037 session-length parenthetical ("this is the attacker-side session-level figure, not the per-query LLM inference latency") | Pre-empts a real unit-confusion a reader would hit in Section 6 | **KEEP** |

---

## 3. Worst-Five Findings with Concrete Rewrites

**R1 (A1 + C1) — Tier taxonomy contradiction, l. 226–227 / 587–599 / 790–804 / 1043. 🔴**
*Rewrite (l. 226–227):*
> "A Random Forest ensemble over 10 hand-engineered behavioural features assigns each session to one of four skill tiers (novice, intermediate, expert, APT); the persona layer maps each tier to a response strategy (Table 5)."

*Rewrite (l. 587–592), active voice, split:*
> "The shipped ensemble was retrained on 2,000 synthetic sessions (500 per tier). The generator draws commands from tier-profiled banks built on the extractor's own pattern families, jitters per-session category mixes with a Dirichlet prior, and samples inter-command delays from a lognormal distribution; adjacent tiers therefore overlap instead of separating artificially."

**R2 (A2) — Tree-count contradiction, l. 594 vs. 665/681/1003. 🔴**
*Rewrite (l. 665–666, assuming 500 is correct per the shipped-config text):*
> "Algorithm 1 details the classification pipeline. The Random Forest ensemble (500 trees) outputs a probability estimate for the predicted skill class; sessions crossing the 0.85 threshold are escalated to Don (C2) and Hisoka (C3)."
Update Algorithm 1's \Require line and l. 1003 to the same figure. If 200 is correct, fix l. 594 instead — but only one number may survive.

**R3 (A4) — Chrollo output schema, l. 582–584 vs. 670–675. 🔴**
*Rewrite (l. 582–584):*
> "Chrollo is a Random Forest ensemble that extracts 10 behavioural features from raw honeypot sessions and routes each session with a confidence score s ∈ [0,1]: s ≥ 0.85 → escalate as malicious to Don and Hisoka; s ≤ 0.75 → log as benign; the reject band (0.75, 0.85) is held for human review. Escalated sessions receive a skill-tier assignment (novice, intermediate, expert, APT) that drives persona selection (Section 3.4)."
Then reconcile the I/O contract (l. 670–675) to output `{escalate | benign | reject, s, X, tier}`.

**R4 (B1) — Self-praise cluster. 🔴**
*Rewrite (l. 288–290):*
> "…but the deployment-fidelity audit is stricter: 10.1% of live queries returned grounded, non-empty, non-refusal content within the 90 s latency budget, and 86.7% hit the OpenRouter SDK read-timeout before a complete turn (Section 6)."
*Rewrite (l. 433–434):* end at "…while its marginal gain for actor attribution is modest (Section 6)."
*Rewrite (l. 303):* "We report per-dimension scores rather than a single mean."
Delete "candidly" (l. 67), "candid gap" (l. 207), and "honest-negative accounting" (l. 265) — the surrounding numbers carry the point.

**R5 (A3) — Corpus-size drift. 🔴**
*Rewrite (l. 53, abstract):* "…a hybrid dense/sparse RAG engine grounds each response in a 780,600-document threat-intelligence corpus;"
*Rewrite (l. 152):* "…from a 780,600-document blended corpus of Exploit-DB, MITRE ATT&CK, OSINT, and dark-web telemetry,"
*Rewrite (l. 219, 364, 539):* replace "780,000+"/"780,000-document" with "780,600-document". One figure, every occurrence.

---

## 4. Priority Counts

| Priority | Count | Highlights |
|---|---|---|
| 🔴 Blocker | 7 | A1 (tier taxonomy), A2 (tree count), A3 (corpus size), A4 (Chrollo schema), A5 (top-15 vs 10 features), B1 (self-praise cluster), C1 (55-word passive sentence l. 587–592) |
| 🟡 Major | 14 | A6–A10, B2–B4, C2–C5, D1–D3, E1–E5 |
| 🟢 Nit | 12 | A11, C6, D4, E6–E7, F1–F8 |

Total findings reported: 33 (some composite; each with line evidence above).

**Verdict on caveats:** 3 KEEP verdicts issued (scope re-statement, table note, unit-disambiguation parenthetical) — none should be touched. All flagged DROP/CALIBRATE items concern self-assessment language or untested future-work properties, not substantive scoping.

---

## 5. Recommended Edit Order

1. Fix the five factual-consistency items (A1–A5) against `results/benchmark_report.json` — these require data verification, not just prose.
2. Apply R4's deletions (self-praise lexicon) — mechanical, high yield.
3. Split the six >40-word sentences (C1–C5) and convert D1–D3 to active voice.
4. Sweep terminology: corpus size (R5), "fidelity" family (A11), tier names (R1).
5. Add the five undefined terms to the Nomenclature table (E4–E5) and fix the F1 spacing typos.
