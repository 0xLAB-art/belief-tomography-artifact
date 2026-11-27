# Reviewer Report — IEEE Transactions on Information Forensics and Security (T-IFS)

**Manuscript:** "The Intelligence Ladder: Pricing AI Mechanisms in a Verified Deception Honeypot" (RAGIN; single author)
**Date of report:** 2026-09-25
**Recommendation: MAJOR REVISION** (acceptance contingent on new experiments; if induced-adversary testing and independent evaluation cannot be added, reject and resubmit after a full evaluation cycle)

---

## 1. Summary of the manuscript

The paper presents RAGIN, an LLM-backed honeypot organized as a "verified deception loop": behavioral classification routes sessions; hybrid RAG over curated CTI grounds a per-session deception plan; a per-session "fiction graph" binds all projected host facts; every LLM draft passes four serving-time decision-procedure checks (danger scan, identity pin, consistency, terminal sanity) before serving, with a human-in-the-loop gate for high-stakes content and a deterministic vetted fallback. The evaluation is framed as an "intelligence ladder" (R0 templates → R1 classifier → R2 grounded planning → R3 generation-under-verification), each rung "priced" by marginal effect, with a fold-down case study in which an LLM kind-assessment rung (Jev) was removed after deterministic mechanisms reproduced its benefit. Claims include: +0.154 composite grounding effect (paired 90-row ablation), 35 vs. 0 TTPs, zero contradictions/zero unverified serves/zero false-positive alerts, 3.86/5 LLM-judge consensus on deception quality, run-to-run stability Δ+0.005, and 12/13 kind-assessment fixes with +125% bait exposure.

The problem is important and genuinely under-examined; the transparency of the write-up is unusually good. However, the headline claims rest on circular instrumentation, the safety machinery is never tested against the failure mode it exists to catch, there is no external baseline and no human evaluation, and the bibliography contains duplicates, uncited padding, claim–citation mismatches, and at least two references the reviewer could not verify.

---

## 2. Strengths

1. **Real and well-motivated problem.** The three failure forms of generative honeypots (inconsistency, over-disclosure, unavailability) and the catch-22 framing (§II-A) are crisp and correct.
2. **Sensible architecture.** Post-hoc verification against a closed, session-scoped world model is defensible where constrained decoding is not (§III-A), and the deterministic fallback as a deception property (G4) rather than mere reliability is a nice inversion.
3. **Rare methodological honesty.** The paper reports a predicted null (persona stratum), a null dwell-time result, a post-hoc judge audit with corrections released alongside raw numbers, a lost artifact honestly disclosed, and provider fragility (catalog churn, 403 refusals) reported *as results* (§V, §VII, App. A).
4. **Ablation discipline.** The requirement that "each removed mechanism costs the system the property it was added to provide" (Table III), plus using a null stratum as evidence the ablation discriminates, is sound design.
5. **Artifact traceability.** The per-claim artifact index (App. A, Table VIII) and reproduction listing (App. B) are exemplary practice.
6. **The fold-down methodology** (re-price intelligent rungs against certifiable equivalents; §III-A, §V-E) is a genuinely useful contribution.

---

## 3. Major concerns

### A. Experimental validity

**M1. The headline grounding claim is partially circular.** The starkest number — "35 TTPs detected vs. 0 without grounding" — is presented as the "mechanism claim" (§V-B, Fig. 4). But TTP extraction is performed by the threat mapper operating on *retrieved* documents (§IV-B). Removing retrieval therefore zeroes detection *by construction*; 35-vs-0 measures the pipeline's structural dependence on retrieval, not a deception or intelligence gain. Similarly, "CTI-technique" queries are "scored on grounded technique coverage" (§V-A) with the rubric never defined; if coverage counts techniques that retrieval supplies, the +0.317 is near-tautological. Required: (a) define the scoring rubrics operationally, (b) report a grounding-effect measure independent of retrieval-dependent extraction, (c) restate 35-vs-0 as a dependence result, not a benefit result.

**M2. The verifier is never exercised against the failure it exists for.** Across 2×218 live queries there are zero verifier rejections, zero fallback serves, zero contradictions. The safety apparatus has zero observed interventions in the headline data; the "nothing unverified is served" claim holds *vacuously* if the generator simply never errs on this workload. The only described rejections are a staged illustration (§III-G) and a development-time false positive. The 45 "adversarial re-queries" (C1) re-query committed facts; they do not *induce* drafts that hallucinate. Required: an adversarial harness that actively induces inconsistent/unsafe/dangerous drafts (prompt injection is already conceded in scope, §II-B), reporting rejection counts, verifier precision/recall, and retry/fallback behavior.

**M3. No external baseline.** Every comparison is RAGIN vs. ablated-RAGIN. No comparison against vanilla Cowrie, against the cited LLM honeypots (kouremetis2024, valeros2024, reworr2024), or any non-RAG generation baseline on a shared metric. At minimum, a plain-LLM honeypot (generator, no graph/verifier/fallback) scored on the same suites is needed.

**M4. "Deception Quality Against Human Evaluators" (§V-D) involves no humans.** Three prompted personas of one LLM judge model sharing a provider with the generator. The within-model caveat is conceded in places but the heading and prose imply human validation. Post-hoc rubric patching (bait floor 0.85, applied after penalties) improved the persona means (0.733→0.756; 0.750→0.762); the corrections are disclosed but need validation on a held-out judge/model.

**M5. Statistical power and metric switching in RQ4.** The fold-down "design rule" rests on 13 real-log sessions, a 200-session A/B at ceiling, six informative sessions (one assessed), five closed-loop pairs, and n=10 steering predictions with no CI. "Adds no measurable dwell time" is a power statement, not effect absence; "dwell time" is actually turn count. The abstract's closing generalization is not licensed by this evidence; the hedge must be propagated to the abstract. Metric switches between accuracy (0.8875→0.9550) and floor-pass (100%) without a consistent definition.

**M6. Serve-path provenance is a latency heuristic, contradicting the paper's own auditability thesis (G5).** The 88.1%/11.9% split is inferred from a latency threshold despite the system logging every verdict; error under threshold misspecification is unquantified; and the method itself demonstrates the latency fingerprinting channel that §II-B disclaims.

**M7. The actor stratum has zero discriminant validity yet enters the composite.** All 35 actor rows score identically; a constant stratum contributes a constant to the composite (0.880) and to the ablation differential (+0.140).

**M8. Unverified "zero false positives" and unaudited detections.** Ground truth for the 132 detections is unstated; if detection and verification share machinery, FP=0 is by construction. No manual audit sample; no per-class precision/recall or confusion matrix for the classifier; label provenance for the 200/400 sessions unstated.

**M9. Workload inconsistencies.** 30-per-suite ablation subsets vs. 123/35/60 campaign — provenance unstated; persona ablation arm 0.833 vs. campaign 0.733 unexplained; Table II caption "180 paired rows" vs. "90 pairs" text; bootstrap method unspecified; 123/218 "live campaign" rows are CTI Q&A, not attacker interactions.

### B. Formal content and threat model

**M10. Property 1 is conditional on an unstated extractor assumption.** The invariant quantifies over E(σ_t), the host facts a draft emits, established by an extraction layer whose recall is never specified; normalization is "tuned." Restate conditional on extractor soundness/recall; fix notation (¬⋔ undefined; σ double-duty).

**M11. The zero-contradiction claim is within-session; the threat model licenses cross-session probing.** Class-conditional policies and fresh fictions per session create observable cross-session divergence. Scope the claim explicitly.

**M12. Latency.** Mean session ≈44 s on a shell; claims scoped to "response content alone" but deception claims (dwell, believability) judged by models that do not experience timing. Caveat belongs in the abstract.

### C. Internal consistency and reporting integrity

**M13. Direct contradictions and dangling references.** (a) gradient-boosted (§III-B) vs. random forest (§IV-A); (b) three attacker classes (§III-B) vs. four tiers (§IV-A); (c) "rewritten or withheld" mechanism nonexistent in §III-E/Alg. 1; (d) "34 credential deployments" cited to app:audit but absent there; (e) "approval-latency analysis" promised from §V, never reported; (f) 86.7% quota figure with no artifact, violating the paper's own provenance rule; (g) "1.35 points" scale unstated; (h) audited composites not reconciled; (i) footnote "link omitted for review" vs. URL in conclusion.

**M14. Reference list problems.**
- Duplicate: valeros2024 (EuroS&PW 2024) and sladic2025 (arXiv:2309.00155, dated 2025; actually 2023) are the same work.
- Claim–citation mismatches: valeros2024 for multi-sensor platforms; sladic2025 for containerized honeynets; liang2025 (SafeRAG, a RAG security benchmark) cited as a grounded-generation system.
- ≥16 uncited entries padding a manual thebibliography (blefari2025, farasat2024a, fayyazi2023, lanka2024, malkov2018, liu2025, orbinato2022, paul2025, shafran2024, simoni2024, sokol2017, ward2025, xue2024, alsaheel2021, noureddine2020, wang2024).
- Unverifiable: bera2024 ("Engagement-Yield Modeling for Adaptive Cyber Deception," T-IFS 19:9123–9138) and liska2024 ("Cognitive-Load-Aware Deception," RAID 2024) could not be located in any index; both carry argumentative weight. DOIs required.
- Minor: zheng2024 is NeurIPS 2023.

### D. Ethics and release

**M15. Missing related work.** GALAH (LLM-generated honeypots), 2026 SoK on honeypots & LLMs, foundational honeytoken literature, guardrails/generate-then-check and RAG-faithfulness verification literature, prompt-injection defenses.

**M16.** (a) 13 replayed real Cowrie logs: provenance/licensing unstated. (b) Dual-use of releasing defense internals (verifier surface) alongside scenario sets. (c) HITL pause: what does the attacker observe during the gate pause?

---

## 4. Minor issues

1. Typos: "attackerhas," "froman" (twice), spacing.
2. RQ3 parenthetical lists four dimensions; metrics/Table V use five.
3. "Acceptance bar" never defined.
4. Abstract conflates +0.154 composite with technique detection (+0.317); packs campaign numbers and 45-query numbers into one clause.
5. Abstract "byte-identical determinism" is a ledger/fallback property, not generation's (persona MAD 0.096).
6. Fictional-character component names (Chrollo, Hisoka, Don, Jev) — rename or justify.
7. Reproduction ran on a 12-vCPU workstation, not the 2-vCPU deployed stack; soften "production deployment" framing.
8. Figure 1 top rung "(assessed, removed)" unexplained on first viewing.
9. Prose compressible ~15–20%; App. F (figure-geometry audit) consumes space.
10. Bootstrap method (percentile/BCa, B) unstated; "row-weighted mean" weighting unshown.
11. Keywords omit "verification," "honeytokens/canary tokens."

---

## 5. Questions for the authors

1. Define the CTI-technique and CTI-actor scoring rubrics operationally. Does the technique score depend on retrieval by construction?
2. How many drafts failed verification across all experiments? Can you run an induced-failure red-team suite for the verifier?
3. Can the audit trail directly attribute each serve to a path? If so, why was provenance estimated by latency?
4. Per-class confusion matrices for Chrollo? How were the 200/400 labels established?
5. Who labeled the 13 real-log sessions, and against what annotation protocol?
6. Supply DOIs for bera2024 and liska2024.
7. Was the 0.85 bait floor validated on any run other than the one that motivated it?
8. What does the attacker observe during an HITL pause, and what is its latency distribution?

---

## 6. Overall evaluation

A paper the reviewer wanted to accept: the problem matters, the architecture is sensible, and the candor is a model for the field. But the manuscript claims more than its instruments support: the flagship detection effect is partially circular, the safety machinery is untested against its target failure mode, the "human evaluation" is one LLM judge, the ladder's design rule rests on n≤13 fragments, and the reference list needs serious repair. M1–M4 and M14 require real additional work, not just prose.

**Recommendation: Major revision.**
**Reviewer confidence:** 4/5 (expert in deception/CTI systems; reviewed the released artifact list as described in the manuscript).
