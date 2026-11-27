# Belief Tomography — Novelty Lit-Scan (Gate Report)

**Date:** 2026-11-07
**Status:** GATE PASSED — proceed, with a mandatory differentiation table (below). The single-word novelty claim is dead; the synthesis + estimand + theory claim survives.
**Rule:** every entry below MUST be cited and differentiated in the paper. Nothing here is optional.

> **⚠️ ROUND 5 CORRECTION (2026-11-19, citation verification).** Two citations in
> the original table were wrong and are corrected here. (1) **N2 is retracted**:
> arXiv:2405.16331 is *"Confirming the Null: Remarks on Equivalence Testing and
> the Topology of Confirmation"* (R. Dale, math.ST), not "Learning Interpretable
> Models for Black-Box Agents". No paper with that title was found in the arXiv
> index. The verified methodological neighbors for black-box agent
> interpretation are **TripleTree** (Bewley & Lawry, arXiv:2009.04743) and
> **Modelling Agent Policies with Interpretable Imitation Learning** (Bewley,
> Lawry & Richards, arXiv:2006.11309), plus **Mxplainer** (arXiv:2506.14246).
> (2) **N5's ValueBench ID is wrong**: ValueBench is **arXiv:2406.04214**, not
> 2506.21961 (which is PapersPlease). The value–action gap paper is **"Mind the
> Value-Action Gap"**, Shen, Clark & Mitra, **arXiv:2501.15463** (EMNLP 2025).
> The novelty verdict is unchanged — none of the verified neighbors estimates a
> security belief profile, and none has an impossibility theorem — but the paper
> may cite only the corrected entries. This is the gate doing its job: an
> unverified ID is treated as a fabrication until checked.
>
> **⚠️ ROUND 6 CORRECTION (2026-11-19, second verification pass, arXiv API).**
> Three IDs in N9 were re-checked against the arXiv Atom API. `2610.40227`
> (EpiAgent) and `2610.03894` (Proxy Confidence) resolve correctly.
> `2601.05869` does **not**: it is *"Non-conservation of a generalized helicity
> in the Euler equations"*, a fluid-dynamics paper. "Before Agents Decide:
> Epistemic Action in LLM-Based Systems" is **arXiv:2610.00511**. N9 is corrected
> and its differentiation sharpened (EpiAgent maintains a belief layer; Proxy
> Confidence scores a single action; neither estimates a belief profile). Rule
> extended: no arXiv ID enters a draft or a lit scan until it resolves to the
> claimed title through the API. **All 12 arXiv IDs now cited in `main.tex` /
> `formalism_note.tex` were re-checked against the API; `2601.05869` was the
> only remaining bad ID, and it is removed from the draft. The corrected
> `2610.00511` is cited instead.** Verified: 2009.04743 (TripleTree),
> 2006.11309 (Bewley imitation), 2506.14246 (Mxplainer), 2406.19501
> (propositional probes), 2608.18900 (TestifAI), 2609.32361 (ER-Audit),
> 2610.07967 (DecepEval), 2406.04214 (ValueBench), 2501.15463 (value--action
> gap), 2610.40227 (EpiAgent), 2610.03894 (Proxy Confidence),
> 2610.00511 (Before Agents Decide).

---

## 1. Query matrix executed

 belief-state probing LLM black-box · self-report vs behavior gap · prompt injection as measurement · deception measurement epistemic games · epistemic state estimation interactive black-box · attacker belief modeling honeypot · "model tomography"/"cognitive tomography" · (incomplete matrix: "agent introspection evals" still to run before drafting)

## 2. Nearest neighbors (mandatory citations + differentiation)

| # | Work | What it does | What it misses (our differentiation) |
|---|------|--------------|--------------------------------------|
| N1 | **Cognitive Tomography** — Houlsby, Huszár, Ghassemi, Orbán, Wolpert & Lengyel, *Current Biology* 2013 (DOI:10.1016/j.cub.2013.09.012) | Inverts a generative model of behavior to estimate latent mental representations in humans; coins the "tomography of the mind" frame | Humans + psychophysics; passive observation; no adversarial probes, no security propositions, no impossibility theory, no deployed systems. **We cite as intellectual ancestor — it legitimizes the name and shows the transfer (humans→deployed agents) is the new contribution** |
| N2 | ~~Learning Interpretable Models for Black-Box Agents — arXiv:2405.16331~~ **RETRACTED (wrong ID)** | The ID is a statistics paper on equivalence testing. **Replaced by verified neighbors:** TripleTree (arXiv:2009.04743) and Interpretable Imitation Learning (arXiv:2006.11309) — behaviourist, decision-tree models of black-box agent policies; Mxplainer (arXiv:2506.14246) — parameterized search approximations of agent policies | These estimate *policy/state structure* for explanation, not security belief propositions; no adversarial probes, no impossibility result, no CIs/estimation theory, no deception gain, no BCG. The differentiation is unchanged; the citation is now real |
| N3 | **TestifAI: Tomography-Based Testing for Deep Learning** — arXiv:2608.18900 | "Partial model tomography" for test prioritization | Testing/debugging objective; no latent belief estimand, no adversarial security probes, no theory |
| N4 | **Monitoring Latent World States in LMs with Diagnostic Classification** — Feng, arXiv:2406.19501 | White-box probes on internal activations extract latent world states; more faithful than outputs under prompt injection | Requires weights (not deployed black-box agents); passive classification, not active adversarial estimation. **Complement, not competitor** |
| N5 | **Value-Action Gap line** — "Mind the Value-Action Gap" (Shen, Clark & Mitra, **arXiv:2501.15463**, EMNLP 2025), **ValueBench** (**arXiv:2406.04214**, ACL 2024), psychometric self-report–behavior gap | Documents that LLM self-reports diverge from behavior (values/personality) | Psychometric constructs via static questionnaires; no security propositions, no adversarial probe families, no estimation theory. **BCG = the adversarial, security instantiation of their documented phenomenon — cite, don't claim the phenomenon as new** |
| N6 | **ER-Audit** — arXiv:2609.32361 | Black-box auditing of "epistemic reliability" in multi-agent systems | Audits reliability of knowledge claims; no behavioral belief profile, no probe-family theory, no deception setting |
| N7 | **Deception measurement line** — Rowe 2006 (honeypot counter-deception metrics), Savage 2025 (attacker belief/motivation profiling), DecepEval (arXiv:2610.07967), ParliamentBench, "Hidden in Plain Text" (deception quality=detectability), "The Structure of Deception" (Shi 2026) | Measures deception propensity/quality of the *deceiver*, or honeypot engagement metrics | **All measure the deceiver or engagement; none estimates the victim's/attacker's belief profile as a statistical object with CIs.** Deception gain Δ(B) is our estimand |
| N8 | **ProbeCourt** (2026), garak/augustus probe tools | Cross-examination / injection probes as *defenses* or scanners | Binary classify-and-block; no estimand, no profile, no theory |
| N9 | **EpiAgent: Epistemic Self-Play for LLM Agents** (arXiv:2610.40227), **Before Agents Decide: Epistemic Action in LLM-Based Systems** (arXiv:2610.00511), **Proxy Confidence: Auditing Black-Box LLM Agents with a Surrogate's Log-Probabilities** (arXiv:2610.03894) | Epistemic vocabulary entering agent research: a *learned* belief layer over others' private information (EpiAgent), epistemic action as evidence acquisition, and auditing a single proposed tool call with a surrogate's log-probabilities (Proxy Confidence) | EpiAgent *maintains* a belief layer for the agent's own play; we *estimate* the deployed agent's belief profile from outside, with CIs, and test a security charter. Proxy Confidence scores one action's correctness; it does not estimate a belief profile and has no impossibility result or charter semantics. Timing evidence, not collision |

## 3. Verdict

**Occupied:** the *words* (tomography-for-behavior: humans N1, testing N3; active interrogation: N2; self-report gap: N5; deception metrics: N7). The field is converging on agent epistemics (N9) — the window is open but closing.

**Unoccupied (the paper's claim):** *the first tomographic theory and instrument library for the security belief state of deployed black-box agents* — specifically the union of: (a) adversarial probe families as calibrated measurement instruments; (b) behavioral belief estimand with CIs; (c) **T1 passive-observation impossibility theorem** (no prior work states or proves it; N4 needs weights, monitors are passive); (d) **deception gain on the attacker's belief profile** (N7 measures the wrong side); (e) **Belief-Claim Gap for security charters** (N5's phenomenon, our adversarial instantiation).

**Positioning sentence for the abstract:** "Cognitive tomography measured the human mind from behavior (N1); we measure the security mind of deployed agents — actively, adversarially, and with guarantees."

## 5. Deep investigation round 2 (2026-11-18) — T5 positioning

| Neighbor | What it has | T5 differentiation |
|---|---|---|
| **Nguyen et al. Stackelberg deception line** (IJCAI'19 imitative attacker deception; finitely repeated security games; AAAI'22 defender deception) | Game-theoretic equilibrium models of optimal deception + detection in repeated play | Payoff/utility models — no sampling-detectability bounds, no amplification lemma, no onset dichotomy; our T5 is information-theoretic (TV budgets, sample complexity), complementary not competing. **Cite as the game-theoretic neighbor** |
| **Park, Goldstein, O'Gara, Chen, Hendrycks — "AI deception" survey (Patterns 2024, ~790 cites)** | Functional definition of deception ("systematic induction of false beliefs"), risk taxonomy, regulatory solutions | Defines WHAT deception is, provides NO measurement theory, estimand, bounds, or instrument. **Our Δ(B) + T5 are the quantitative layer that survey explicitly lacks — position the paper as supplying it.** Their functional definition = our deception gain's philosophical ancestor |
| **ToM / false-belief line** (Strachan Nature HB 2024; Kosinski 2024; Lu 2025 belief-state tracking; epistemic agency 2410.16270) | Whether LLMs can track/infer OTHERS' beliefs | Direction reversal: ToM = agent modeling others; Belief Tomography = the agent's OWN operative beliefs under adversarial interaction. **Cite as the epistemics-adjacent field with reversed direction** |
| Two-sample testing literature (C2ST Lopez-Paz; contamination models Milhaud 2023) | Generic statistical machinery | Our tools (Hahn set + Hoeffding amplification) are standard — a credibility asset; the NEW object is deception-gain-vs-detectability as a bounded quantity |
| White-box lying probes (Azaria line) | Internal-state deception detection | Requires weights; our black-box behavioral channel complements (same N4 relationship as Feng) |

**Verdict after round 2:** T5 remains unoccupied. The strongest positioning sentence now: *"The most-cited deception survey (Park et al., Patterns 2024) defines deception functionally and calls for governance — without a measurement theory. We supply the missing layer: an estimand, an instrument, impossibility results, and the deception–detection frontier."*

## 6. Deep investigation round 3 (2026-11-18) — T1 lineage + T3 methodology

| Neighbor | Relationship to our theory |
|---|---|
| **Mimicry attacks** (Wagner & Soto 2002, ~1151 cites) + **Polymorphic Blending Attacks** (Fogla et al., USENIX Sec 2006) + countermeasure Anagram (Wang & Stolfo 2006) | **T1's IDS-era ancestors**: PBA explicitly constructs attacks "statistically indistinguishable from benign traffic" — same structure as our ε=0 non-detector. Honest differentiation: they *construct* indistinguishability; our Lemma A quantifies the **finite-N detection frontier** (1−2e^(−Nδ²/2)), couples it to **deception gain via sensitivity L**, and adds the **onset dichotomy** — none of which exist in that line. The amplification inequality itself is standard-style (Tsybakov-type) — **the contribution is its role in the gain/stealth coupling, not the inequality**. Cite as the direct ancestors |
| **Psychophysics adaptive estimation**: QUEST (Watson & Pelli 1983), PSI (Kontsevich & Tyler 1999; Prins 2013), QUEST+ (Watson 2017, expected-entropy-minimization design), Treutwein 1995 / Leek 2001 reviews | **T3's methodological ancestor**: mature Bayesian optimal probe-placement machinery, 60 years old. Our move: transplant to adversarial belief estimation of agents (the attacker's probe design and OUR probe design are the same mathematics — dual-use symmetry again). T3 upgrades from "open problem" to "imported + first policy benchmark" |

**Draft consequences:** (1) T1 section must open by crediting the mimicry/blending lineage; (2) T3 section imports PSI-style expected-entropy minimization and benchmarks it against uniform/UCB allocation (first policy benchmark for belief tomography); (3) amplification lemma attributed as standard-technique-with-new-role.

## 3b. Deep research round 7 (2026-11-19) — collision gate on evaluation limits

See `DEFEAT_DEVICE_COLLISION_SCAN.md` for the full analysis and verified IDs.
Summary: **Ferrara 2026** (arXiv:2606.28863, defeat devices: discriminator +
concealed swap + eval/deployment gap) and **Mahran 2026** (arXiv:2610.30803,
partition theory: passing certifies a floor, never a ceiling; exact imitation
undetectable) already establish the *qualitative* content of our T6/T9.
Differentiation: our β profile with Wilson CIs, tolerance τ, gaming gap Γ, and
composition theorem T7 are **estimator- and decision-level**, not a new
phenomenon or a new impossibility theorem. Additional neighbors:
**Soopal 2026** (arXiv:2611.14950, adaptive attacks break fixed sandbagging
detectors — motivates E10), **Duddu 2026** (arXiv:2611.20459, worst-case
deceptive model organisms as a security game), **Baum 2026**
(arXiv:2611.02162, normative argument for conditional compliance), and
**Nguyen & Husain 2026** (arXiv:2611.23202, ATI configuration attestation —
complement, attests config not behavior). All six IDs verified on abs pages.

## 4. Consequences for the draft

1. BCG reframed: "adversarial value-action gap for security charters" (N5 cited in the same sentence).
2. T1 is the theory centerpiece — nobody in N1–N9 has it.
3. N2 must be read in full before the formalism note is frozen.
4. Remaining scan before drafting: "agent introspection evaluations", "theory of mind probing adversarial", "context poisoning detection estimation".

## 7. Deep investigation round 4 (2026-11-18) — theoretical anchors

| Framework | Relationship |
|---|---|
| **Quantitative Information Flow** — Smith 2009 (min-entropy leakage, 786 cites), g-leakage (Alvim et al. CSF 2012, gain functions), "The Science of QIF" (Springer 2020) | QIF measures what an adversary LEARNS about a secret from observing a system (vulnerability/gain functions, channel capacity). **Deception is the dual: a channel that injects falsehood.** Draft agenda item T6 "Deception as negative leakage": formulate deception operations D as QIF channels with an inverse gain function; deception gain = g-misinformation; the detection budget = leakage about D itself; onset dichotomy = prior-channel composition. This anchors the paper in a rigorous CS-theory community (CSF/TIFS) beyond security venues |
| **Information design / Bayesian persuasion** — Kamenica & Gentzkow 2011 (~4300 cites); **Bayesian Persuasion with Lie Detection (NBER WP 30065)**; Ichihashi 2019 (limited sender information); Nguyen 2021 (costly messages); Bergemann-Morris 2016 (BCE); Verbalized Bayesian Persuasion 2025 (LLM settings) | **Closest economic-theory neighbor of T5**: lie-detection constraints limiting a misleading sender = the coherence tax's persuasion-frame. Differentiation: persuasion models are equilibrium/commitment analyses with type spaces; T5 is sampling-horizon information theory with executable out-of-band probes and onset visibility. Cite the lie-detection paper prominently — it legitimizes "constrained misleading" as a studied object |
| **Positioning upgrade (3 theory frames)**: QIF (what the adversary learns), information design (what the sender conceals/distorts), deception games (what the defender gains) — **Belief Tomography measures what the adversary is made to wrongly believe, with bounds — the missing fourth frame** | |

**Draft consequences:** (1) new §"Deception as negative leakage" agenda (T6) in the formalism note's roadmap; (2) related-work reorganized into the four-frame structure; (3) the NBER lie-detection paper is mandatory reading before finalizing T5's positioning sentence.
