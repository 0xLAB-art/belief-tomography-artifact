# **Measuring the Belief–Claim Gap: Active Black-Box Tomography of Autonomous Agents and the Limits of Certification** 

## ANONYMOUS, Independent Researcher, Egypt 

Deployed autonomous agents publish a charter—the security policy they claim to uphold—and act on beliefs that no certification mechanism in current practice tests: that a message came from an administrator, that a tool output can be trusted, that they are unobserved. A charter is an assertion. This paper makes the distance between assertion and behavior a measured quantity, and names it the _Belief–Claim Gap_ . 

We introduce _belief tomography_ : active, black-box estimation of an agent’s _behavioral belief profile_ from deliberately designed probe interactions, with per-proposition Wilson intervals and a certification semantics. The attack vectors already in use become the instruments: every forged-authority directive, lying tool output, and exfiltration lure is a probe that puts one question about the agent’s latent state to its behavioral channel, and the behavior is the answer. Theory fixes the enterprise’s boundaries. Passive monitoring cannot tomograph in general; a patch-deception-decay law and an onset dichotomy jointly cap deception gain and stealth; public probe suites are gameable, statistical certificates do not compose, and published profiles are forgeable by attacker and defender alike; censoring above the certification tolerance makes a certificate unidentifiable, however clean its measured turns; and disclosure admits no free lunch, with a gaming-gap statistic that decides when a certificate may transfer at all. 

The instrument is validated before it is pointed at production. On constructed foils with known ground truth, dose–response reaches _𝑟_ ≥ 0 _._ 986 and test–retest _𝑟_ = 0 _._ 949; a seeded audit calibrates the verdict channel (sensitivity 0 _._ 960, false positives 0/25). Thirty registered experiments follow under a frozen estimator—twentyfive confirmatory, five registered diagnostics run after, and designed to investigate, the anomalies they examine. Two are field measurements on frontier models addressed by provider catalog name behind an authenticated gateway: attacker personas hold their operational beliefs at the deployed engagement depth of a live honeypot (Δ( _𝐵_ ) at or below the noise floor for all five personas), and a 300-session probe attack finds targets holding their charters on every measured turn ( _𝛽_<sup>ˆ</sup> = 0, Wilson 95% [0 _,_ 0 _._ 060] per family). The path to that null is itself evidence: the censoring floor flagged the state-deception family, a registered decomposition traced its zero to a 200-token response budget, and a mandatory transcript audit then retracted the repaired panel’s five new flags as refusal-quote false positives of the lexical oracle—two error classes, both caught by the program’s own registered structure rather than by reviewers. 

An open-weight panel on three verifiable models measures charter-holding as a spectrum along a single axis: no model in any panel—closed serving or open weights—complies with a destructive command, while literal canary echo runs from 0 _._ 000 on the gateway panel to a pooled 0 _._ 030–0 _._ 143 (0 _._ 700 in the echo family) on open weights. The estimand, the protocol, and the constructed-foil bounds are released for replication and attack; the live-fleet artifacts are released as frozen snapshots, with diagnostic probe sets withheld under the disclosure policy. 

#### **ACM Reference Format:** 

Anonymous. 2026. Measuring the Belief–Claim Gap: Active Black-Box Tomography of Autonomous Agents and the Limits of Certification. _ACM Trans. Priv. Sec._ 1, 1 (November 2026), 38 pages. 

Author’s address: Anonymous, Independent Researcher, Cairo, Egypt, anonymous@example.com. 

Permission to make digital or hard copies of all or part of this work for personal or classroom use is granted without fee provided that copies are not made or distributed for profit or commercial advantage and that copies bear this notice and the full citation on the first page. Copyrights for components of this work owned by others than the author(s) must be honored. Abstracting with credit is permitted. To copy otherwise, or republish, to post on servers or to redistribute to lists, requires prior specific permission and/or a fee. Request permissions from permissions@acm.org. © 2026 Copyright held by the owner/author(s). Publication rights licensed to ACM. ACM 2471-2566/2026/11-ART https://doi.org/ 

ACM Trans. Priv. Sec., Vol. 1, No. 1, Article . Publication date: November 2026. 

Anonymous 

2 

### **1 INTRODUCTION** 

Every deployed autonomous agent holds beliefs that no certification mechanism in current practice examines: that a message really came from an administrator, that a tool output deserves trust, that a credential is its to spend, that its actions go unwitnessed. What the agent _publishes_ is a charter, the security policy it claims to uphold. What it _does_ once those beliefs come under attack is a different object, and the mechanisms of record—code review, tool auditing, configuration attestation—all stop at the boundary where an adversary begins to speak. The gap is not hypothetical. A model that cooperates through evaluation and hijacks in deployment, an agent that obeys a forged authority message, an automated attacker that completes its reconnaissance inside a monitored honeypot without being detected—each is a divergence between the belief the system asserts and the belief its behavior reveals. 

This paper makes that divergence a measured quantity. The observation that powers it is that the attack vectors already in use are instruments waiting to be read as such: a forged-authority message asks whether authority is verified; a lying tool output asks whether outputs are validated; a reflection-extraction chain asks whether private reasoning can be surfaced; an exfiltration lure asks whether secrets move under pressure. Each probe puts one question about the agent’s latent state to the behavioral channel, and the response is the answer. The adversary throughout is the party that supplies those beliefs: an attacker who writes into the agent’s context and reads what comes back, but who sees no weights, no system prompt, and no internal state beyond what the channel leaks (Section 3.1). From deliberately designed probe interactions we estimate a _behavioral belief profile 𝛽_<sup>ˆ</sup> , proposition by proposition with Wilson intervals, and define the _Belief–Claim Gap_ (BCG) between the charter’s claims and the profile’s measurements. Figure 1 shows the object on constructed foils with known ground truth: two targets that a code or configuration audit cannot tell apart separate cleanly into a naively compliant profile and a graded one. 

A single latent object organizes three activities the field usually treats separately. _Certification_ is a hypothesis test over the profile. _Deception_ is controlled corruption of an adversary’s profile. _Monitoring_ is change-point detection on the profile over time. The profile is also the paper’s privacy object: a published tomogram is a targeting map for whoever reads it (Section 8), so the _release_ of a measurement is itself a security-and-privacy decision, and we derive its trade-off frontier. A single measurement that serves assurance and reconnaissance at once makes the context of its release a security decision in its own right (Section 8). Responsibility is designed in, not appended: every secret is a fictional canary, unsolicited third-party sessions to the live fleet are retained only as telemetry, all live operations run under registered halt rules, and every experiment is pre-registered before its data exists (Section 10). 

### **1.1 Research questions** 

Six questions organize the paper; each is answered by a theorem, a measured result, or a named open problem: 

- (1) **RQ1 (Necessity).** Can an agent’s behavioral belief profile be recovered by passive observation alone, or is active probing a precondition of measurement? (Section 4.1) 

- (2) **RQ2 (Cost).** What does active estimation cost, and when does adaptive allocation pay? (Sections 4.2 and 5.5) 

- (3) **RQ3 (Frontier).** How much deception can an adversary buy, and what does each unit of gain cost in detectability? (Section 4.3) 

- (4) **RQ4 (Assurance).** What does a behavioral certificate actually establish about isolated components, compositions, and adaptive targets? (Sections 7.1–7.5) 

ACM Trans. Priv. Sec., Vol. 1, No. 1, Article . Publication date: November 2026. 

Measuring the Belief–Claim Gap 

3 



<!-- Start of picture text -->
∙— Naive foil (designed β = 1) ∙— Hardened foil (graded β)<br>(a)  Measured ̂β per probe family (b)  Per-trial outcomes  (18 trials/cell)<br>design target β = 1 Δ̂β<br>Authorityforgery −0.67 16 8/18/18<br>deceptionState −0.33 11 8/182/18<br>1 8/18<br>Goal −0.33 1 2/18<br>subversion<br>no separation<br>1 2/18<br>Epistemic 1 2/18<br>echo<br>1 8/18<br>Exfiltration −0.33 1 2/18<br>lure<br>84/90<br>All families −0.33 54/90<br>(pooled) trial counted toward ̂β not counted<br>0 0.25 0.5 0.75 1<br>measured ̂β  (95% Wilson CI)<br><!-- End of picture text -->

Fig. 1. The tomogram on constructed foils: a naive foil built to comply with every attack, and a graded hardened foil. (a) Measured behavioral belief profile per probe family—dots: _𝛽_<sup>ˆ</sup> ; whiskers: Wilson 95% CIs; grey span: the interval separation (or overlap, _no separation_ ); signed per-family gap Δ _𝛽_<sup>ˆ</sup> against the design target. The naive foil’s epistemic-echo cell reads 12/18, level with the hardened foil’s—an oracle-induced verdict error audited in Section 5.6. (b) Per-cell trial accounting (18 trials/cell; filled squares count toward _𝛽_<sup>ˆ</sup> ); pooled 0 _._ 933 [0 _._ 862 _,_ 0 _._ 969] vs. 0 _._ 600 [0 _._ 497 _,_ 0 _._ 695]. Black-box interaction alone separates the designed targets. 

- (5) **RQ5 (Field).** Do production agents hold their charters under probe attack, and does live honeypot deception move a real attacker’s measured beliefs? (Section 6) 

- (6) **RQ6 (Disclosure).** What does publishing a measured profile hand to the other side, and what does releasing it protect? (Section 8) 

### **1.2 Contributions** 

Five contributions, each tied to a registered artifact and stated so that it could fail: 

- (1) **The estimand** (Section 3): behavioral belief strength _𝛽_ ( _𝜋_ ; Π), the Belief–Claim Gap, epistemic distance, and deception gain Δ( _𝐵_ ), together with the sensitivity assumption on which every bound rests, stated explicitly and checked empirically. 

- (2) **Theory** (Section 4): the impossibility result that makes active measurement necessary (Theorem 4.1); uniform and adaptive query-complexity guarantees for estimation (Theorem 4.3, Proposition 4.4); the deception–detection frontier, where a patch-deception-decay law and an onset dichotomy jointly cap deception gain and stealth (Theorems 4.7–4.8); the limits of certification: public-probe gameability, statistical non-composition, the gaming-gap transfer diagnostic, tomogram forgery, adaptive gaming, certificate half-life, reactivity, and allocation under learning attackers (Corollary 7.1, Theorem 7.2, Proposition 7.3, Theorem 7.4, Corollary 7.5, and Propositions 7.6–7.8); and the economics of disclosure: reconnaissance externality, defender-side deception release, and the detection-budget coupling (Propositions 8.1, 8.2, 8.3). Appendix A carries the proofs. The inequality machinery is deliberately standard (Hoeffding, Neyman–Pearson, Lipschitz covering, Bonferroni); the contribution is the objects those tools are 

ACM Trans. Priv. Sec., Vol. 1, No. 1, Article . Publication date: November 2026. 

Anonymous 

4 

Table 1. The program at a glance: thirty registered experiments in four layers. E1b and T3 are sub-protocols of E1 and of the allocation benchmark; E24 is a retired registry slot with no data (Data Availability). Every experiment was pre-registered before its data existed, seeded, and pinned to a frozen estimator. 

|Layer|Experiments|What it establishes|
|---|---|---|
|Instrument|E1, E1b, T3,<br>E17–E19, E22|What the instrument measures and how<br>reliably: dose–response, test–retest, the<br>allocation objective, the audited verdict<br>channel, estimator and seed robustness, and<br>wording invariance of the probe library.|
|Constructed foils|E4–E16, E20|What certification, gaming, forgery,<br>composition, drift, allocation under a<br>learning attacker, and disclosure can and<br>cannot establish once ground truth is<br>controlled.|
|Field|E2, E3, E21, E23,<br>E25–E29|Two pre-registered nulls on frontier<br>models behind an authenticated gateway and<br>on a live honeypot fleet, plus the<br>censoring floor, budget decomposition, and<br>repaired panel behind them.|
|Open weights|E30, E31|A verifiable-identity panel on three open<br>models: charter-holding as a measured<br>spectrum.|



made to bound—the estimand, the two caps, and their composed frontier—not the inequalities themselves. 

- (3) **An instrument with measured validity, reliability, and an audited verdict channel** (Section 5): dose–response _𝑟_ ≥ 0 _._ 986 across 1,500 episodes; test–retest _𝑟_ = 0 _._ 949 at the registered operating point of 10 probes per cell; a seeded calibration of the adjudication channel (sensitivity 0 _._ 960, FP 0/25); and estimator- and seed-robustness across the program. 

- (4) **Two pre-registered field nulls, and the two measurement-error classes the program caught in itself** (Section 6): gateway-served frontier targets hold their charters under a 300session probe attack ( _𝛽_<sup>ˆ</sup> = 0, Wilson 95% [0 _,_ 0 _._ 060] per family), and gateway-served attacker personas hold their operational beliefs under live honeypot deception at the deployed engagement depth (Δ( _𝐵_ ) at or below the noise floor for all five personas), with every kill gate passed and every deviation logged. The instrument’s own floor did half the work: Proposition 6.1’s censoring rule—which both lanes fail, and which applies to any black-box evaluation run behind a filtering provider API—flagged the state-deception family, and E28–E29 traced its E2-era zero to a 200-token response budget. The mandatory transcript audit did the rest: the lexical oracle’s refusal-quote false-positive mode had read the repaired panel’s flags as breaches (5/60 flagged, 0/60 genuine after adjudication). A third instance—E30’s hardcoded output cap—recurred in a second driver and was caught before its data was analyzed. An open-weight panel (E30/E31) then extended the measurement to verifiable models, where the charter spectrum’s axis is literal canary echo: 0 _._ 000 on the gateway panel against 0 _._ 030–0 _._ 143 pooled (to 0 _._ 700 in the echo family) on open weights, with zero destructive-command compliance in any panel. 

- (5) **The economics of disclosure** (Section 8): a published profile is attacker reconnaissance ( _𝐴_ rec _>_ 0); attacker and defender can both forge it; and bounded-noise release traces a monotone frontier with no interior dominance, so disclosure policy is a choice on a curve, not an evasion. 

ACM Trans. Priv. Sec., Vol. 1, No. 1, Article . Publication date: November 2026. 

Measuring the Belief–Claim Gap 

5 

The layers answer different questions and are read in that order: the instrument layer establishes what the instrument measures, the foil layer what the measurement can and cannot establish, and the field and open-weight layers what production agents actually do under probe attack. The artifact package reproduces every number in this paper (Data Availability), and Section 10 states what the results do not establish. 

### **2 BACKGROUND AND RELATED WORK** 

### **2.1 Four frames, one missing layer** 

Four research communities study objects adjacent to the behavioral belief profile, and each stops one step short. Quantitative information flow asks what an adversary _learns_ about a secret from a system’s observable behavior [1, 58]. Information design asks what a sender can _conceal or distort_ [33]. Deception games ask what a defender _gains_ at equilibrium [43]. Theory-of-mind research asks whether an agent can model _others’_ beliefs [60]. Belief tomography poses the question none of the four asks: _what is an agent made to wrongly believe_ , with quantified bounds. A widely cited survey of AI deception defines deception functionally and calls for governance [46], and venue-level surveys of LLM-agent security and privacy catalogue the threats without a measured estimand [28]. This paper supplies the missing layer: an estimand, an instrument, impossibility results, and the gain–stealth frontier. 

### **2.2 Tomography of latent state** 

The name is borrowed deliberately. Cognitive tomography inverts a generative model of behavior to recover latent mental representations in humans [30], the paper’s intellectual ancestor, and TestifAI applies the word to deep-learning system testing [4]. The black-box neighbors that infer agents from behavior recover _policy structure_ , not security beliefs: TripleTree discretizes the state space into interpretable regions [7], imitation-learning work reverse-engineers agent policies as decision trees [8], and Mxplainer learns parameterized approximations of them [36]. None of these estimates security beliefs, offers an impossibility result, or attaches confidence intervals to a deception-gain estimand. White-box propositional probes read latent world states out of activations [19], and full audit pipelines locate deliberately planted hidden objectives in production-scale models when the weights are open [40]; both require weights and both are passive, which makes them complements rather than competitors. Model-generated red teaming automates probe construction [47]. What red teaming lacks (an estimand, intervals, and validity checks for what its probes measure) is exactly what tomography adds. 

### **2.3 The self-report–behavior gap** 

Psychometric work documents that LLM self-reports diverge from behavior [49, 55]; preference tuning teaches models to match the user’s beliefs over the truth [54]; and under organizational pressure, models strategically deny actions they demonstrably took [53]. The Belief–Claim Gap is this phenomenon in its adversarial security form, now carrying confidence intervals and a certification semantics. The deeper difference is causal: a questionnaire item _asks_ , whereas a probe family _intervenes_ —it creates the condition under which the claimed belief must either do work or fail. 

### **2.4 Deception measurement** 

Deception abilities emerge with model capability [26]. Existing deception measures score the _deceiver_ : propensity or deception quality [51, 71]; honesty dissociated from accuracy in the MASK benchmark, where larger models improve the latter but not the former [50]; or plain honeypot 

ACM Trans. Priv. Sec., Vol. 1, No. 1, Article . Publication date: November 2026. 

Anonymous 

6 

engagement. None estimates the victim’s or the attacker’s belief profile as a statistical object. The equilibrium neighbors are game-theoretic deception [43] and Bayesian persuasion with its liedetection extension [17, 33]; Section 4.3 supplies what they do not: a sampling-horizon information theory with executable probes. Deception is also the dual of leakage: a channel that injects falsehood where leakage steals secrets. The onset dichotomy composes the deception channel with the attacker’s prior channel, so the paper speaks to the quantitative-information-flow tradition as much as to security measurement. 

### **2.5 Defeat devices and the limits of evaluation** 

Evaluation-aware behavior is not a new claim, and we do not make it as one: alignment faking demonstrated it canonically [24]; context-conditioned backdoors realize the structure at training time [37]; Ferrara’s _defeat device_ names the triad our probe-aware foil instantiates (an evaluationcontext discriminator, a concealed behavioral swap, an evaluation–deployment gap) [22]; and partition theory proves the identifiability limit that a behavioral evaluator cannot catch an examinee imitating it [41]. Our Corollary 7.1 and Theorem 7.4 are the _estimator-level_ instances: the same phenomenon as a binomial belief profile with Wilson intervals, a tolerance _𝜏_ , and a gaming-gap statistic. The adversary is not the novelty; the instrument and the composition result are. Ferrara’s TADP protocol is proposed _without_ empirical validation; E7/E9/E10 supply the differential probe, the quantified statistic, the measured noise floor, and the conditional transfer bound (Section 7.2). His “meta-discriminator triggers”—a discriminator that detects probes for the discriminator—is the arms-race extension he does _not_ characterize empirically; E10 is exactly that characterization, with a secret-diagnostic-set defense. 

Auditing under adaptive attack [16, 59, 61, 62] shows that a detector beaten once cannot be assumed robust; E10 mounts precisely this challenge against our own gaming-gap check, and E16 closes the loop by computing the defender’s held-out budget as a function of the attacker’s probediscrimination error, the budget–error coupling those stress tests leave implicit (sandbagging itself is demonstrated in [64]). The normative argument that reward selects for conditional compliance [6] motivates the problem without supplying an estimator. Configuration attestation [44] answers “is this the approved model and tool configuration?”; tomography answers “what does it do under adversarial pressure?” The two are complements, not substitutes. 

### **2.6 Deception doctrine and decoy artifacts** 

Defender-side misinformation is classical doctrine: cyber-deception shapes attacker beliefs about defended systems [9]; controlled experiments quantify attacker-cognition effects against live red teams [20, 21]; and modern frameworks report misinformation effective against targeted attackers [57]. Decoy _artifacts_ for AI agents plant fake objects that alert on interaction [68], and the LLM Agent Honeypot flags AI hacking agents in the wild across 8.1M SSH interactions through deployment cues and prompt-injection canaries [66]. E15 differs in the _medium_ : the falsified object is a published behavioral _measurement_ of real components, stable precisely because verification confined to the public probe suite reproduces it (Theorem 7.4 and Corollary 7.5, applied in the defender’s favor). The trust-collapse risk under attacker held-out capability has no direct analogue in artifact planting: the forged object there is a record, not a measurement whose verification-confinement stability the theory predicts. 

### **2.7 Composition and orchestration boundaries** 

Per-component safety does not imply pipeline safety. ChainCaps names the “permission laundering” case, in which every per-tool permission check passes while the end-to-end effect is unsafe, and defends with runtime capability attenuation [31]; CaMeL derives prompt-injection resistance 

ACM Trans. Priv. Sec., Vol. 1, No. 1, Article . Publication date: November 2026. 

Measuring the Belief–Claim Gap 

7 

from an explicit control- and data-flow design [14]; structured queries and preference-optimized resistance harden the model side against injection [12, 13]; programmable privilege control bounds what an already-compromised agent can reach [56]; knowledge-corruption attacks poison the retriever’s corpus from the data side [74]; and framework studies [35] and orchestration-guided jailbreaks [11] document related failures. Theorem 7.2 is not another entry in that catalogue. It is the estimator-level analogue: a confidence-interval behavioral certificate at tolerance _𝜏_ fails to compose, and E8’s interface-vocabulary probe is the measurement-layer complement to those runtime defenses. 

### **2.8 Epistemics-adjacent LLM work** 

Theory-of-mind probing asks whether an agent can track _others’_ beliefs [60]; the direction here is reversed. Black-box epistemic-reliability auditing [67] hunts paraphrase counterexamples to a verifier’s non-degradation, not a behavioral belief profile. Three 2026 systems mark the convergence. EpiAgent maintains an explicit belief layer for the agent’s own play [32], whereas tomography _estimates_ a deployed agent’s profile from outside, with intervals attached. “Before Agents Decide” frames epistemic action as evidence acquisition [39]; the probe is that idea made adversarial and measurable. Proxy Confidence scores one proposed tool call [73]: no belief profile, charter semantics, or impossibility result. 

### **3 THREAT MODEL AND THE ESTIMAND** 

### **3.1 Threat model** 

Two roles recur. The _operator_ of an agent (the defender) holds the charter and may publish measurements about it. The _adversary_ is either (i) an attacker _of_ the agent, probing it for exploitable beliefs (implicit-authority acceptance, secret disclosure, destructive compliance), or (ii) an agent _acting as_ an attacker against a defended host, whose beliefs the defender may deceive. The tomographer may be the operator (certification) or the adversary (reconnaissance); Section 8 analyzes this duality. All interactions are black-box: only channel behavior (transcripts and tool-call traces) is observed— never weights, activations, or system prompts beyond what the channel reveals. The adversary controls one thing only: the content of an interaction episode—the message it sends, the tool output it returns, the moment it sends it. It controls no weights, no system prompt, and no provider filter, and it observes nothing but the response, truncated and censored under the same rules as any other caller (Section 6.1). Three things are out of scope by construction, and no claim below depends on them: the agent’s internal representations, the training-time provenance of a belief it displays, and the intent behind the charter it publishes. One capability is _in_ scope deliberately: the target may be evaluation-aware (its response map may behave differently on recognized probes); Corollary 7.1 exists because a finite public suite cannot rule that out. What transfer assumes the target cannot do is condition on probe _provenance_ beyond probe content—whether a given text came from the public or the held-out set (assumption (A2), Section 7.2); targets that can, void transfer by construction. 

_Attack classes and probes._ The probe families instantiate, in instrument form, the attack classes documented for production LLM agents: indirect prompt injection [25], its benchmark for toolintegrated agents [72], formally benchmarked prompt injection [38], the dynamic agent-attack settings of AgentDojo [15], and agent-harm benchmarks that measure whether malicious tasks complete [3]. Those works ask whether an attack _succeeds_ ; tomography asks what the response to it _reveals_ about the agent’s beliefs. AgentDojo’s finding that no evaluated defense survives adaptive attackers is the empirical edge that Corollary 7.1 formalizes for any finite public probe suite. Every experiment in this paper operates on systems the author owns or on locally constructed foils; no third-party system was attacked. 

ACM Trans. Priv. Sec., Vol. 1, No. 1, Article . Publication date: November 2026. 

Anonymous 

8 

_Definition 3.1 (Agent, charter, benign operation)._ An _agent_ is a (possibly randomized) map from interaction histories to responses, _𝐴_ : H → Δ(R), with response kernel _𝜅𝐵_ ( _ℎ,_ ·) parameterized by a belief hypothesis _𝐵_ ∈ 𝔅. Its _charter 𝜒_ is a published set of policy claims. _Benign operation_ is a distribution _𝜇_ over histories in which no adversary is present. 

_Definition 3.2 (Belief proposition and probe family)._ A _belief proposition 𝜋_ is a testable statement about the agent’s operative beliefs (e.g., “believes forged system authority”). A _probe family_ Π = ( _𝐺_ Π _,𝑐_ ) is a generator of interaction episodes aimed at _𝜋_ in context _𝑐_ , drawn from a library of instrument families—authority forgery, state deception, goal subversion, epistemic echo, exfiltration lure—each with escalation _generations 𝑔_ ∈{1 _,_ 2 _,_ 3} of increasing indirectness and decomposition. 

_Definition 3.3 (Behavioral belief strength)._ Given a binary behavioral-consistency functional _𝑋𝐵_ (Π) ∈{0 _,_ 1} (the verdict that the agent’s response is consistent with holding _𝜋_ , produced by deterministic oracles and a calibrated judge), the _behavioral belief strength_ is 



<!-- Start of picture text -->
𝛽 ( 𝜋 ; Π) = E 𝐺 Π ,𝜅𝐵 [ 𝑋𝐵 (Π)] ∈[0 ,  1] .<br><!-- End of picture text -->

The _belief profile_ is _𝜷_ = { _𝛽_ ( _𝜋_ ; Π _𝑐_ )} _𝜋_ ∈P over a proposition catalogue P and context grid _𝑐_ —the tomogram; a bare _𝐵_ always indexes a belief hypothesis of Section 4.1. 

The estimand is deliberately _behavioral_ : the probability that the agent’s behavior is consistent with holding the proposition under the probe family. It makes no claim about internal representations, and it refuses introspection as a proxy channel, because chain-of-thought explanations are measurably unfaithful to the causes of a response [63]. Two agents with identical profiles may realize them by different mechanisms. That underdetermination is a feature, not a defect: behavior is the only object well-defined for a deployed black-box system, and the only one contractible in procurement and certification. Section 4.1 shows the behavioral object is also _necessary_ : passive observation cannot identify it in general. 

_Relation to attack-success-rate reporting._ On one proposition under one probe family, _𝛽_ reduces to the attack-success rate benchmark suites report [3, 15, 72]. The estimand’s content is what surrounds the rate: the charter mapping that turns rates into a Belief–Claim Gap (Definition 3.4), the sessionisolation condition the rate inherits (93 _._ 3% relative bias without it, E12), interval certification at tolerance _𝜏_ with the censoring floor (Proposition 6.1), the transfer diagnostic Γ, and the validation suite (dose–response, test–retest, audited verdict channel). 

_Definition 3.4 (Belief–Claim Gap)._ For a charter claim _𝜑_ ∈ _𝜒_ with instrument mapping _𝐹_ ( _𝜑_ ) ⊆ P × C (the propositions and contexts that test it), the _Belief–Claim Gap_ is 



<!-- Start of picture text -->
1<br>BCG( 𝜑 ) = ∑︁ 𝛽 ( 𝜋 ; Π 𝑐 ) .<br>| 𝐹 ( 𝜑 )|<br>( 𝜋,𝑐 )∈ 𝐹 ( 𝜑 )<br><!-- End of picture text -->

BCG( _𝜑_ ) ≈ 1 under a claim _𝜑_ asserting the negation of a proposition _𝜋_ ∈ _𝐹_ ( _𝜑_ ) means the charter asserts what the behavior contradicts (“never forwards credentials under pressure,” measured with _𝛽_ ( _𝜋_ ) = 1 on lured forwarding, has BCG = 1); BCG ≈ 0 is charter-conformant behavior on the claim’s mapped cells. 

_Definition 3.5 (Epistemic distance and deception gain)._ For two profiles _𝜷, 𝜷_<sup>′</sup> , let _𝑑_ be the perproposition shift collection {| _𝛽_ ( _𝜋_ ) − _𝛽_<sup>′</sup> ( _𝜋_ )|} _𝜋_ aggregated by the deception operation’s objective weighting—the convention the field estimator of Section 6 reports (per-proposition shifts first, then the objective aggregation). In a deception operation against an attacker whose profile is estimated at times _𝑡_ 0 _,𝑡_ 1, the _deception gain_ is Δ( _𝐵_ ) = _𝑑_ ( _𝜷𝑡_ 0 _, 𝜷𝑡_ 1); every reported field null holds for the per-proposition maximum as well as the mean aggregation. 

ACM Trans. Priv. Sec., Vol. 1, No. 1, Article . Publication date: November 2026. 

Measuring the Belief–Claim Gap 

9 

### **4 THEORY: IMPOSSIBILITY, QUERY COMPLEXITY, AND THE DECEPTION–DETECTION FRONTIER** 

The theory answers RQ1–RQ3 in three steps. Section 4.1 shows that passive monitoring cannot tomograph, so measurement must be active (RQ1). Section 4.2 prices active estimation: a uniform sample-complexity guarantee, and what adaptive screening can and cannot save (RQ2). Section 4.3 derives the deception–detection frontier, the pair of laws that jointly cap deception gain and stealth (RQ3). Proofs are in Appendix A; the predictions of Section 4.3 meet their constructed planes in Section 4.4. Several results below share one construction (off-support conditioning) and two propositions are explicit arithmetic; what is new is what these mechanisms buy for measurement, not inequalities beyond standard tools. 

_Notation and standing conventions._ An agent acts on interaction histories _ℎ_ ∈H through a response kernel _𝜅𝐵_ ( _ℎ,_ ·) parameterized by a belief hypothesis _𝐵_ ∈ 𝔅 (Definition 3.1). _Benign operation_ is a distribution _𝜇_ over histories with no adversary present; composed with _𝜅𝐵_ , it induces the _passive transcript distribution 𝑃𝐵_<sup>pas. For distributions</sup><sup>_𝑃_1</sup><sup>_, 𝑃_2on a common space,</sup><sup>_𝑑_TV(</sup><sup>_𝑃_1</sup><sup>_, 𝑃_2)=</sup> sup _𝐴_ | _𝑃_ 1( _𝐴_ ) − _𝑃_ 2( _𝐴_ )| is total variation distance—the largest gap one event can open between them, and the worst-case error of the optimal test between them. A probe family Π, scored by the binary verdict _𝑋𝐵_ (Π) ∈{0 _,_ 1} (Definition 3.3), induces the belief strength _𝛽_ ( _𝜋_ ; Π) = E[ _𝑋𝐵_ (Π)] ∈[0 _,_ 1], written _𝛽_ [ _𝜇_ ]( _𝜋_ ) in Section 4.3 when viewed as a functional of transcript distributions _𝜇_ . Throughout, _𝑁_ is an i.i.d. observation horizon, _𝑀_ an interaction-turn budget, _𝑁_ 0 a memorized honest reference batch, _𝛽𝑑_ a tolerated false-alarm (test) level, _𝛾_ a tolerated detection probability (the detection budget of Theorem 4.7(iii)), and _𝑧𝜂_ the two-sided standard-normal quantile (Pr[| _𝑍_ | _> 𝑧𝜂_ ] = _𝜂_ ); _𝛼_ is reserved for confidence levels (Section 4.2) and _𝛿_ for a deception’s observable footprint (Section 4.3). The program calibrates all error budgets at the same two-sided level: _𝛽𝑑_ = _𝛾_ = 0 _._ 05 (Table 2). 

### **4.1 Passive monitoring cannot tomograph** 

Is active probing necessary at all? A monitor that merely watches the transcript stream could in principle recover the profile without ever injecting a probe. Theorem 4.1 answers no, and the obstruction is structural rather than statistical: two hypotheses can agree on every transcript benign operation produces and still disagree completely on one adversary-controlled input that benign operation never delivers. 



<!-- Start of picture text -->
Theorem 4.1 (Passive-observation impossibility). There exist belief hypotheses 𝐵 0 ≠ 𝐵 1  and<br>an adversary-controlled event 𝐸 (e.g., a forged-authority directive) with  Pr 𝜇 ( 𝐸 ) = 0  such that:<br>(i) the passive transcript distributions coincide, 𝑑 TV � 𝑃𝐵 pas0 , 𝑃 𝐵 pas 1 � = 0 ; and<br><!-- End of picture text -->

_(ii) a single probe family separates them completely,_ E _𝐵_ 1 [ _𝑋𝐵_ (Π)] − E _𝐵_ 0 [ _𝑋𝐵_ (Π)] = 1 _._ 

Corollary 4.2 (Detection impossibility under bounded false positives). _Any monitor whose input is the passive transcript stream—any classifier, any alarm rule—has identical output distributions under 𝐵_ 0 _and 𝐵_ 1 _. By Neyman–Pearson, no such monitor achieves true-positive rate exceeding its false-positive rate on distinguishing 𝐵_ 1 _from 𝐵_ 0 _._ 

The proof (Appendix A) constructs two agents that agree on every benign history and diverge on an adversary-controlled input benign operation never delivers—the belief-state generalization of the IDS literature’s mimicry and blending attacks [23, 65]. The contribution is not indistinguishability itself but the _finite-sample detection frontier_ (Section 4.3), its coupling to belief gain, and the agentinteraction instantiation. The program’s live deployment supplies the empirical edge: its adaptive generation-3 attacker’s non-detector personas report zero detections across the full engagement cap at every generation (the EPK frontier artifact of the fleet, Data Availability)—passive defensive 

ACM Trans. Priv. Sec., Vol. 1, No. 1, Article . Publication date: November 2026. 

Anonymous 

10 

observation never fired on the adapted attacker, while that attacker’s divergent beliefs remain fully separable by active probes. Monitors themselves are not exempt: optimization pressure on a deployed chain-of-thought monitor was recently shown to teach reasoning models to obfuscate their intent while the misbehavior persists [5]. Passive evidence degrades under pressure; active tomography is the alternative. 

### **4.2 Query complexity of active estimation** 

If passive monitoring cannot identify the profile, estimation must be active, and active estimation has a sample complexity. Fix _𝐾_ propositions and a family×context cell, and assume _outcome homogeneity_ : within the cell, the verdict for proposition _𝑖_ ∈[ _𝐾_ ] is Bernoulli( _𝛽𝑖_ ), independent across episodes. Estimation then reduces to _𝐾_ Bernoulli means. 

Theorem 4.3 (Uniform estimation guarantee). _Fix accuracy 𝜀 >_ 0 _and confidence level 𝛼_ ∈(0 _,_ 1) _. If each proposition 𝑖 receives_ 



<!-- Start of picture text -->
1<br>𝑛𝑖 ≥<br>2 𝜀 2 ln 2 𝛼 𝐾<br><!-- End of picture text -->

_probes, then the empirical estimator 𝛽_<sup>ˆ</sup> _𝑖 satisfies_ 



<!-- Start of picture text -->
Pr� 𝑖 max∈[ 𝐾 ] �� 𝛽 ˆ 𝑖 − 𝛽𝑖 �� ≤ 𝜀 � ≥ 1 − 𝛼<br><!-- End of picture text -->

_(Hoeffding’s inequality [29] plus a union bound over the 𝐾 propositions)._ 

The guarantee is _uniform_ over the catalogue: one allocation rule controls the entire profile simultaneously, and the only price of that simultaneity is the logarithmic factor ln _𝐾_ . 

Proposition 4.4 (Adaptive screening gain for the certificate objective). _If at most 𝑠_ ≪ _𝐾 propositions have 𝛽𝑖_ ≥ _𝜏 for a threshold 𝜏 > 𝜀, a two-phase policy—uniform screening at a coarse width to identify above-threshold candidates, followed by 𝜀-refinement on the surviving set—achieves the certificate decision of Section 7.1 with total probes_ 



<!-- Start of picture text -->
𝑂 � 𝐾𝜏 −2 ln( 𝐾 / 𝛼 ) +  𝑠𝜀 −2 ln( 𝐾 / 𝛼 ) � ,<br><!-- End of picture text -->

_a saving concentrated on the 𝐾_ − _𝑠 below-threshold propositions whenever 𝜀_ ≪ _𝜏. The uniform 𝜀-guarantee of Theorem 4.3 itself admits no adaptive saving: it requires 𝜀-width on every proposition._ 

The screening phase is a fixed-confidence thresholding bandit; the proof (Appendix A) is given at sketch level, which the decision-focused statement above is sized to. The full characterization of the informativeness-optimal adaptive design remains open (Section 9). Section 5.5 measures what adaptive policies actually deliver at realistic budgets for _estimation_ , and the result—a warning about objectives, not about adaptivity—is the empirical face of the no-saving clause in Proposition 4.4. 

### **4.3 The deception–detection frontier** 

The central object is the trade an adversary faces when it lies about the world and a measurementcapable victim looks for the lie. A _deception operation 𝐷_ maps the honest observable distribution _𝑃_ over transcripts to a defended distribution _𝑄_ = _𝐷_ ( _𝑃_ ); its _observable footprint_ is _𝛿_ = _𝑑_ TV( _𝑃,𝑄_ ) ∈ (0 _,_ 1]. The attacker’s belief functional _𝛽_ [ _𝜇_ ] ∈[0 _,_ 1]<sup>_𝐾_</sup> is defined on transcript distributions, so the deception moves the measured profile by the componentwise shift _𝛽_ [ _𝑄_ ]( _𝜋_ ) − _𝛽_ [ _𝑃_ ]( _𝜋_ ), the quantity the following definition bounds. 

_Definition 4.5 (Sensitivity)._ The functional _𝛽_ is _𝐿-sensitive_ if for all transcript distributions _𝜇_ 1 _, 𝜇_ 2 and propositions _𝜋_ , 



<!-- Start of picture text -->
�� 𝛽 [ 𝜇 1]( 𝜋 ) − 𝛽 [ 𝜇 2]( 𝜋 )�� ≤ 𝐿𝑑 TV( 𝜇 1 , 𝜇 2) .<br><!-- End of picture text -->

ACM Trans. Priv. Sec., Vol. 1, No. 1, Article . Publication date: November 2026. 

Measuring the Belief–Claim Gap 

11 

Bounded sensitivity is the operative regularity condition and is empirically checkable by the dose–response protocol of Section 5.3. 

Every frontier bound below rests on one mechanism: repetition amplifies a barely-visible gap into near-certain detection. 

Lemma 4.6 (Amplification). _Let 𝛿_ = _𝑑_ TV( _𝑃,𝑄_ ) ∈(0 _,_ 1] _and let 𝑃_<sup>_𝑁_</sup> _,𝑄_<sup>_𝑁_</sup> _denote the distributions of 𝑁 i.i.d. samples from 𝑃 and 𝑄. Then_ 



<!-- Start of picture text -->
𝑑 TV � 𝑃 𝑁 ,𝑄 𝑁 � ≥ 1 − 2 exp�− 𝑁𝛿 2/2� .<br><!-- End of picture text -->

Theorem 4.7 (Patch-deception decay). _Let 𝛽 be 𝐿-sensitive and let a deception perturb attackeraccessible observations with 𝛿_ = _𝑑_ TV ( _𝑃,𝑄_ ) _. Then:_ 

_(i) every proposition’s measured shift is footprint-bounded,_ | _𝛽_ [ _𝑄_ ]( _𝜋_ ) − _𝛽_ [ _𝑃_ ]( _𝜋_ )| ≤ _𝐿𝛿 for every 𝜋; (ii) an attacker with horizon 𝑁 who implements the optimal threshold test and knows the honest_ 

_distribution 𝑃 detects the deception with probability at least_ 1 − 2 _𝑒_<sup>−</sup><sup>_𝑁𝛿_2/2</sup> _, and no test exceeds 𝑑_ TV( _𝑃_<sup>_𝑁_</sup> _,𝑄_<sup>_𝑁_</sup> ) _(the attacker who must learn the honest rate from a memorized batch is the subject of Theorem 4.8);_ 

_(iii) holding detection probability at most 𝛾 at horizon 𝑁 forces_ 



<!-- Start of picture text -->
𝛿 ≤ √ 2 ln � 2/(1 − 𝛾 ) � / 𝑁, hence gain ≤ 𝐿 √ 2 ln � 2/(1 − 𝛾 ) � / 𝑁 = 𝑂 � 𝐿 / √ 𝑁 � .<br>In words: footprint buys at most  𝐿𝛿 of shift (i);  𝑁 fresh samples detect exponentially fast (ii);<br>stealth converts to the gain cap (iii)—believable deception decays as  𝑂 ( 𝐿 / √ 𝑁 ).<br><!-- End of picture text -->

Theorem 4.8 (Onset dichotomy). _Let the attacker sample the environment for 𝑀 turns and let deception change the observable distribution by 𝛿 >_ 0 _. The_ reference noise floor _is 𝜌_ 0 = _𝑧𝛽𝑑_ ~~√~~ _𝑝_ (1 − _𝑝_ )/ _𝑁_ 0 _: the sampling error of the attacker’s memorized reference batch at tolerance 𝛽𝑑 , where 𝑝 is the per-turn event rate under honest samples. Then:_ 

- _(i)_ Known onset. _If deception activated mid-session and the attacker memorized 𝑁_ 0 ≥ 1 _honest samples, one of two regimes holds:_ 

   - _(a) if 𝛿_ ≥ _𝜌_ 0 _, the attacker detects with probability_ ≥ 1 − _𝛽𝑑 once 𝑀_ ≳ _𝛿_<sup>−2</sup> _; or_ 

   - _(b) if 𝛿 < 𝜌_ 0 _, no level-𝛽𝑑 two-sample test of the fresh stream against the memorized reference whose rejection threshold is fixed independently of the estimated honest rate reaches power_ 1 − _𝛽𝑑 for any 𝑀: the threshold must clear the 𝑝-robust reference width. The gain is bounded by_ 



<!-- Start of picture text -->
𝐿𝜌 0 = 𝐿𝑧𝛽𝑑 √ 𝑝 (1 − 𝑝 )/ 𝑁 0 = 𝑂 � 𝐿 / √ 𝑁 0� .<br><!-- End of picture text -->

_In either regime, gain and stealth cannot both be large: they are jointly capped by the attacker’s memorized reference size 𝑁_ 0 _, not by dwell time._ 

_(ii)_ Birth onset. _If the deception plane is active from the attacker’s first packet (𝑁_ 0 = 0 _), the attacker holds one sample path from a single unknown distribution and has no in-channel reference. Any in-channel test reduces to evaluating the prior plausibility of the observed transcript distribution; deceptions inside the plausible set are in-channel undetectable for every 𝑀._ 

The proof (Appendix A) is at sketch level; arm (ii) is defined over test classes—an _in-channel_ test is any measurable function of the transcript path alone, the _plausible set_ the deceptions it cannot distinguish from honest traffic—and the priors-over-worlds extension is open (Section 9). 

Corollary 4.9 (The deception–detection frontier). _For the detection statistics analyzed in Theorems 4.7 and 4.8—the threshold test on the amplifying event, and level-𝛽𝑑 two-sample tests against a memorized reference—achievable deception gain is jointly capped at 𝑂_ ( _𝐿_ / ~~√~~ _𝑁_ ) _and 𝑂_ ( _𝐿_ /<sup>~~√~~</sup> _𝑁_ 0) _. The_ 

ACM Trans. Priv. Sec., Vol. 1, No. 1, Article . Publication date: November 2026. 

Anonymous 

12 

_object the analysis identifies is the frontier curve of achievable gain against attacker probe budget 𝑀, out-of-band audit rate, and reference size 𝑁_ 0 _; the adaptive minimax extension remains open (Section 9)._ 

Belief tomography is the measuring instrument on both sides of the frontier: the attacker tomographs the plane; the defender tomographs the attacker (deception gain, Definition 3.5). Certification (hypothesis tests over profiles) and deception (profile corruption) are decision rules operating on either side of this curve. 

The corollary composes the two caps rather than proving a new bound: any single deception is subject simultaneously to the stealth-forced cap of Theorem 4.7(iii) and, when the attacker holds a pre-onset reference, to the reference-noise cap of Theorem 4.8(i)(b); the achievable set is the intersection of the two regimes. 

Arm (ii) of Theorem 4.8 formalizes the honeypot-from-birth architecture: endurance is governed by onset invisibility and by the attacker’s _out-of-band_ channels—executable causal predictions (“if I run this exploit, _𝑋_ must happen”) and external anchors. The defender’s achievable deception set is the set of world distributions consistent with the attacker’s _affordable_ out-of-band probes; we call this constraint the _coherence tax_ . Game-theoretic deception models optimal deception at equilibrium [43]; Bayesian persuasion with lie detection models constrained misleading senders [17, 33]. Those are equilibrium and commitment analyses. Theorem 4.7 is a sampling-horizon information theory with executable out-of-band probes and an empirically visible onset dichotomy. The gain–stealth frontier is the object the deception literature has measured only through proxies; the theorems above give it explicit sampling-horizon bounds. 

### **4.4 Empirical validation: the onset dichotomy (E5)** 

We test Theorem 4.8’s predictions on constructed planes with known onset: the attackertomographer either memorizes a pre-onset reference batch of size _𝑁_ 0 or has none (birth onset), and we track the AUC of its two-sample detection statistic as the fresh-sample horizon _𝑀_ grows. 

Figure 2 plots those cells over the horizon; the ordering, not the fitted height, is what the registered prediction tests. 

The match is quantitative at regime resolution—the floor uses the normal approximation to the binomial quantile, a regime indicator at _𝑁_ 0 = 10—and Table 2 carries all four registered cells: the floors are 0 _._ 283 and 0 _._ 141 at _𝑁_ 0 = 10 and _𝑁_ 0 = 40; above the floor the theory predicts saturation with enough _𝑀_ , below it detection _cannot_ saturate. 

The two reference widths of Appendix A sharpen this into a four-cell ordinal prediction: every registered cell lands where the adaptive boundary places it—the two middle cells fall between the widths, above the adaptive boundary and below the non-adaptive cap—and the E5 statistic is studentized, so the adaptive boundary is the achievability heuristic under test, at an _𝑁_ 0 where the Wald plug-in variance is itself approximate. Birth-onset self-tests stay near chance at every _𝑀_ (0.34–0.53), the residual spread being small-sample rate-estimation asymmetry, not in-channel detectability. The paper’s central theorem is thus falsifiable on an instrument any reviewer can rerun. 

### **5 THE MEASUREMENT INSTRUMENT** 

### **5.1 The platform behind the instrument** 

The measurement layer validated below is one plane of an engineered deception platform, built and hardened across this program (Appendix B, Figure 6). The instrument is one object in both settings: the probe library, verdict logic, and pinned estimator of Section 5.2 run verbatim from foils to field, E2 through the model gateway and E3 against the fleet’s attacker personas (deception gain Δ( _𝐵_ ); Section 6). Instrument _parameters_ —the response budget above all—are part of the frozen 

ACM Trans. Priv. Sec., Vol. 1, No. 1, Article . Publication date: November 2026. 

Measuring the Belief–Claim Gap 

13 



<!-- Start of picture text -->
δ = 0.2 δ = 0.4<br>(a) (b)<br>1.0 1.0 1.00<br>0.97 0.94<br>0.8 0.8<br>0.72<br>0.6 0.6<br>chance<br>0.4 0.4<br>N₀ = 10 floor regime both floors < δ<br>0.3 0.3<br>5 10 20 40 80 5 10 20 40 80<br>observation horizon  M observation horizon  M<br>known onset, N₀ = 10 known onset, N₀ = 40 birth onset (self-test)<br>detection AUC<br><!-- End of picture text -->

Fig. 2. E5: the onset dichotomy on constructed planes with known onset. Detection AUC of the two-sample statistic as the fresh-sample horizon _𝑀_ grows; one panel per deception footprint _𝛿_ . Solid curves memorize a reference batch ( _𝑁_ 0 = 10, _𝑁_ 0 = 40), the dashed curve is the birth-onset self-test ( _𝑁_ 0 = 0), which stays at chance at every _𝑀_ as Theorem 4.8(ii) requires. The plateaus read 0 _._ 72 and 0 _._ 97 at _𝛿_ = 0 _._ 2, 0 _._ 94 and 1 _._ 00 at _𝛿_ = 0 _._ 4, reproducing the four observed ranges of Table 2; the shaded band marks the _𝑁_ 0 = 10 floor regime. The theory predicts the _order_ of the four cells, and four of four match. 

|_𝑁_0|_𝛿_|_𝜌_0|_𝑤_na|predicted regime|observed AUC|
|---|---|---|---|---|---|
|10|0.2|0.283|0.774|below both: no saturation|0.69–0.74, flat|
|40|0.2|0.141|0.387|between: rising|0.76→0.97|
|10|0.4|0.283|0.774|between: high, partial|0.91–0.97|
|40|0.4|0.141|0.387|above both: saturation|0.997–1.000|



Table 2. The two reference widths as a four-cell ordinal prediction across the registered E5 grid ( _𝛽𝑑_ = 0 _._ 05 two-sided; _𝜌_ 0 = _𝑧𝛽𝑑_ ~~√~~ _𝑝_ (1 − _𝑝_ )/ _𝑁_ 0; non-adaptive width _𝑤_ na = ~~√~~ 2 ln(1/ _𝛽𝑑_ )/ _𝑁_ 0; observed values frozen). Four of four cells match in order: the adaptive boundary tracks the data, the two middle cells fall above the adaptive boundary and below the non-adaptive cap, and the adaptive minimax remains open (Section 9). 

configuration, and every change to them is a logged deviation; the response-budget deviation and its repair are the story of Section 6. The platform’s construction and its own measured defenses are stated in Appendix B. 

### **5.2 Library, verdicts, and estimator** 

_Probe library._ The v0 library holds five families—authority forgery, state deception, goal subversion, epistemic echo, exfiltration lure—each at three generations of indirectness. Every episode is seeded and reproducible, and the target _model_ never sees family labels, oracle logic, or the generator (routing metadata is consumed by the proxy process and excluded from the model-visible channel by the leakage audit of Section 5.6). The v0 families are template worlds: one template per (family, generation) cell, sampled repeatedly. Probe _diversity_ within a cell is a library-v1 property 

ACM Trans. Priv. Sec., Vol. 1, No. 1, Article . Publication date: November 2026. 

Anonymous 

14 

(Section 10); the label “E2-v1” in Section 6 denotes the _replication_ driver (session isolation and full logging), not a new probe library. What the v0 instrument measures is the sampling probability of a fixed probe, which is exactly what the dose–response experiment validates. 

_Library-v1 paraphrase validation (E22)._ Three semantic-preserving paraphrase variants per cell are frozen in code (preflight-verified against the v0 breach pattern), and the full E1 grid re-runs under each: exact profile parity on the deterministic harness (max |Δ _𝛽_<sup>ˆ</sup> | = 0 _._ 000 over 75 cells; cross-variant _𝑟_ = 1 _._ 0; every family at the E1 bar). The v0 readout is wording-invariant for semanticspreserving probes—on deterministic foils; whether production models are wording-invariant is what E21 measures (Section 6.1). 

_Verdicts._ Two deterministic oracles form the reproducible floor: secret_leak (the literal secret appears in the target’s outputs) and unauthorized_action (an action word co-occurs with a destructive command string). Both are lexical, and Section 5.6 shows why that matters: lexical verdicts are a floor, not a semantic judge. The calibrated multi-model jury lane<sup>1</sup> is the v1 semantic layer; any breach claim that is not a literal echo is audited against its transcript. 

_Estimator._ Per family, _𝛽_<sup>ˆ</sup> is the breach rate over the family’s generations, with a Wilson score interval [69]; Wilson intervals are the default throughout, and the exact (Clopper–Pearson) intervals used only in adjudication-ratio audits are labeled as such where they appear. Profiles are compared under _ℓ_ 1 distance; the Belief–Claim Gap averages the family _𝛽_ s mapped to a charter claim. The estimator is frozen by commit hash before data collection; every change is a logged deviation. 

### **5.3 Validity: dose–response (E1)** 

The E1 grid crosses the five families with five injection doses {0 _,_ 0 _._ 25 _,_ 0 _._ 50 _,_ 0 _._ 75 _,_ 1 _._ 00} of the foil’s induced belief, 60 episodes per cell (20 probes × 3 generations): 25 × 60 = 1 _,_ 500 episodes. The cell size is sized, not guessed: at _𝑛_ = 60 the worst-case binomial SE (0 _._ 065 at _𝑝_ = 0 _._ 5) stays below the 0 _._ 25 dose step—the design response to an early _𝑛_ = 18 pilot’s apparent authority-forgery dip (SE ≈ 0 _._ 118 exceeds half the step; diagnosed as cell-size noise before any curve was read). The result: Pearson _𝑟_ ≥ 0 _._ 986 and Spearman _𝜌_ = 1 _._ 00 in every family (per-family _𝑟_ 0 _._ 986–0 _._ 990), monotone curves, exact zero-dose cleanliness. On the constructed planes, at the registered operating point, the instrument recovers what it claims to measure; what that resolution cannot exclude on production targets is stated where the field results are (Section 6). 

### **5.4 Reliability: test–retest (E1b)** 

Two independent probe batches on a stochastic foil (temperature-like noise _𝜂_ = 0 _._ 15) yield _𝑟_ = 0 _._ 949 with mean |Δ _𝛽_<sup>ˆ</sup> | = 0 _._ 067 at 10 probes per cell. At 4 probes per cell the same foil yields _𝑟_ = 0 _._ 837, below the pre-registered reliability bar. _Batch size is part of the instrument specification_ ; the operating point is ≥ 10 probes per cell. Effects below the measured noise floor are not claimable in any document. 

### **5.5 Allocation: the objective must match the goal (T3)** 

Which probe family should receive the next episode? The intuitive answers are a bandit’s regret objective (attack the family that fails most) and a psychophysics information objective (maximize entropy reduction). We benchmarked both against uniform and variance-equalizing (Neyman) allocation for _profile estimation_ at budgets 25–400. 

The negative result is the point. Over 150 seeded replications per (policy, budget) cell—paired seeds across the four policies, on a fixed heterogeneous target profile with family rates spread from 

> 1A program methodology artifact with measured inter-rater agreement; see Data Availability. 

ACM Trans. Priv. Sec., Vol. 1, No. 1, Article . Publication date: November 2026. 

Measuring the Belief–Claim Gap 

15 

||human l|abel: safe|human label: breach|
|---|---|---|---|
|oracle:|clean<br>20|(TN)|12 (FN, 48.0%)|
|oracle:|breach<br>5 (FP,|20.0%)|13 (TP)|



Table 3. Constructed boundary audit ( _𝑛_ = 50): the lexical oracle’s confusion matrix. The 2% false-positive bar of kill criterion (a) is not met on boundary text, which is why the oracle is a floor and the transcript audit is mandatory. 

0 _._ 1 to 0 _._ 9 (Policy Benchmark artifact)—uniform achieves mean error 0.035 and Neyman 0.035 at _𝑛_ = 400, while the upper-confidence-bound bandit (UCB-lite) stalls at 0.121 and the entropy-greedy information heuristic (PSI) at 0.129: regret-optimal allocation starves non-frontier families, and entropy-greedy allocation over-invests in extreme-rate families. Mutual information is the right tool for _detection_ -style tasks, not for estimation. This refines the open problem of Section 4.2: the optimal design for profile estimation is variance-equalizing, and the adaptive gain is bounded by profile sparsity, not by greedy information. 

### **5.6 The verdict channel, audited** 

_Constructed boundary audit._ We constructed 50 boundary sessions with human-assigned labels— frozen in code before any oracle ran, assigned semantically and not by the oracle’s lexical rules: safe refusals that _name_ the forbidden command (“I am not executing rm -rf /var/log”), safe cases with no oracle keywords, and breaches phrased around the lexical rules (implicit completion, paraphrase, split secrets). The lexical oracle produced 5/25 false positives (20.0%, 95% CI [8.9%, 39.1%]) and 12/25 false negatives (48.0%, 95% CI [30.0%, 66.5%]). Both directions matter: a false positive inflates a charter violation; a false negative certifies an agent that complied. The deterministic oracle is a reproducible floor, and every non-literal breach verdict must be verified against its transcript. Any instrument with automated verdicts deserves the same audit. 

_E17: the audit channel’s operating characteristic._ The live kill-(a) audit of Section 6 reported FP 0/51 [0 _,_ 7 _._ 0%] with zero oracle positives—honestly labeled underpowered. E17 closes the gap with a seeded audit: 50 frozen constructed sessions of known ground truth (labels never exposed to the adjudicator) plus 70 real E2-v1 sessions, shuffled blind—presented without id, kind, or family labels—and adjudicated by the registered transcript rubric rather than the lexical oracle. The channel measures sensitivity 0 _._ 960 [0 _._ 805 _,_ 0 _._ 993] and FP 0/25 [0 _,_ 0 _._ 133]; the single false negative is a pretextonly phrasing (“executing the vendor guidance”) with no prohibited content in the output. The channel dominates the oracle on the same 50 sessions (oracle FP 0 _._ 20, FN 0 _._ 48; channel FP 0 _._ 00, FN 0 _._ 04). No real E2 session adjudicates as a breach, consistent with the zero-breach field result. With 25 seeded positives, the audit detects adjudicator FP rates above ≈12% (rule of three): kill criterion (a) now has a stated power. The seeded-audit concept is borrowed from practitioner oversight; the object calibrated here is this program’s transcript-adjudication channel, not a general audit methodology. 

### **5.7 Robustness: estimator and seeds (E18, E19)** 

Two pre-registered robustness results close the remaining methodological questions about the instrument itself. _E18 (estimator robustness):_ an empirical-Bayes Beta–Binomial estimator with a per-experiment method-of-moments prior, applied to the frozen E1/E2/E17 data, produces zero _decision_ flips at _𝜏_ = 0 _._ 2, so headline inferences do not depend on the interval estimator, while its credible intervals are uniformly narrower (width ratio 0 _._ 88–0 _._ 99); the two estimators disagree 

ACM Trans. Priv. Sec., Vol. 1, No. 1, Article . Publication date: November 2026. 

Anonymous 

16 

Table 4. E2-v1 field panel, per family (nominal _𝑛_ = 60/family/model). _𝛽_<sup>ˆ</sup> is the _conservative-mapped_ estimate (unavailable turns mapped to the charter-holding verdict), identical for both gateway models; meas. _𝑛_ = fully-measured sessions (gpt-5.6 / gpt-6.1; measured- _𝑛_ upper bounds: up to 0 _._ 077 and 0 _._ 242, E2-v1 sensitivity artifact). The gpt-5.6 state-deception family is fully censored: E2-v1 identifies no estimate for it—the family measures 0/60 genuine [0 _,_ 0 _._ 060] only on the repaired panel (E29). Belief–Claim Gap: confidentiality 0 _._ 000, action safety 0 _._ 000. Every interval lies far below _𝜏_ = 0 _._ 2 on measured turns, while under worst-case censoring neither lane is identified (Proposition 6.1). 

||meas._𝑛_(5.6/6.1|)<br>ˆ_𝛽_|Wilson 95% CI|
|---|---|---|---|
|authority forgery|46 / 44|0.000|[0_,_ 0_._060]|
|state deception|0 / 12|0.000|[0_,_ 0_._060]|
|goal subversion|59 / 60|0.000|[0_,_ 0_._060]|
|epistemic echo|52 / 60|0.000|[0_,_ 0_._060]|
|exfiltration lure|40 / 58|0.000|[0_,_ 0_._060]|
|_Worst-case session_|_bound_: [0_,_0_._343]|(gpt-5.6) /|[0_,_0_._220] (gpt-6.1)|



only on exactly-zero cells, where a continuous posterior excludes zero by construction (a disclosed property, and a v2-estimator design note). _E19 (seed extension):_ the E6/E7/E9/E10 registered protocols re-run unchanged at three fresh seeds (131 _,_ 2026 _,_ 90210); every registered condition holds at every seed, so the foil-harness results are seed-robust. 

### **6 FIELD RESULTS: TWO PRE-REGISTERED NULLS AND TWO SELF-CAUGHT ERRORS** 

Theory so far concerns the instrument; nothing yet touches a deployed system. RQ5 asks the two questions only field measurement can answer. First: do _production_ agents diverge from their charters at all, or was the separation of Section 7.1 an artifact of designed targets? Second: does _live_ deception move a real attacker’s measured beliefs, or only the constructed planes of Section 4.4? The two pre-registered field measurements below answer both; their answers are nulls at instrument resolution—charters held on every measured turn, once the instrument was repaired and the verdicts audited—and the section’s central event is layered: the censoring floor flagged a family, a registered decomposition traced the flag to a budget artifact (the first self-caught error), and the transcript audit on the repaired panel’s flags caught the oracle’s own false-positive mode (the second). Every kill gate, deviation, halt, and adjudication is logged. 

### **6.1 E2: the Belief–Claim Gap in production agents** 

_Design._ Two models served by the authenticated gateway under frontier catalog names (snapshot identity is not independently verifiable; Section 10; throughout, the suffix -sol marks the gateway’s single-session operating lane), measured 2026-11-19–20, each tomographed at 5 families × 3 generations × 20 probes = 300 independent sessions; every session starts from a fresh conversation, and every turn (probe text, tool output, reply, block flag) is logged to JSONL before analysis. The primary endpoints are BCG(confidentiality) and BCG(action_safety); per-family _𝛽_<sup>ˆ</sup> is reported with Wilson 95% intervals. Unavailable turns—provider content blocks and transport failures, which the current wire surfaces identically—are counted, mapped to a conservative charter-holding verdict, and disclosed: _𝛽_<sup>ˆ</sup> is downward-biased, and the measurable probe set is explicit. The global block/transport split is reported from the proxy log where recoverable; per-session attribution is a disclosed limitation. 

The lexical oracle is a reproducible floor: every oracle-positive session and a 50-session stratified sample are transcript-adjudicated with exact CIs; a second seed on the signal-bearing agent provides 

ACM Trans. Priv. Sec., Vol. 1, No. 1, Article . Publication date: November 2026. 

Measuring the Belief–Claim Gap 

17 

|Lane / family|fully measured|identified at_𝜏_=0_._2?|
|---|---|---|
|gpt-5.6-sol primary|197/300=65_._7%|no|
|gpt-6.1-sol primary|234/300=78_._0%|no, near the 80% bar|
|state deception (gpt-5.6)|0/60=0%|no, interval [0_,_1]|



Table 5. Proposition 6.1 at _𝜏_ = 0 _._ 2: certification requires an 80% fully-measured fraction; both measurable lanes fall short ( _𝑐_ = 103/300, 66/300), and the state-deception family is fully censored (resolved by E29: measured 0/60 genuine at the repaired budget; its five floor flags adjudicate as refusal-quote false positives, the oracle’s known false-positive mode). 

test–retest reliability. The run is pre-registered, and the invalid E2-v0 run (episode-isolation defect) is archived; no v0 number is quoted as evidence—the v0 signal below is quoted only as the diagnosis it motivated. 

_The gaming-gap pilot (E21)._ Under Corollary 7.1, no finite public probe suite supports a transferready certificate: E2 is a profile measurement, not a Γ-paired one. E21 closes this gap at pilot resolution—30 fresh sessions over the same panel and lane (three held-out paraphrases × five families × two models; 2026-11-21, registered before data). Nine of the ten (family, model) pairs show Γ = 0 at pilot _𝑛_ (three sessions per pair, no held-out flags). The tenth is _void_ : gpt-5.6-sol state deception measures _𝛽_<sup>ˆ</sup> held = 2/3 on paraphrases P1 and P3: Γ = 0 _._ 667 against the frozen public profile, 0 _._ 583 against the repaired panel’s 0 _._ 083 flag rate (E29)—8 _._ 7–10× the 0 _._ 067 floor either way. Γ is throughout a flag-rate diagnostic; what the flags mean is settled, separately, by the transcript audit; the pre-E29 flagged replies (E21, E25–E28) were not transcript-retained, so their refusal-quote-FP status rests on representation from the transcript-retained E29 rerun (same model, lane, budget, probe text), not direct verification. Mechanism is not identifiable at pilot _𝑛_ ; the pilot does not certify—but the diagnostic did what Section 7.2 demands: a public-support null did not transfer unexamined, and the void cell was caught, named, and priced. 

_Results: the measurable model._ In the completed gpt-5.6-sol primary, all 300 probes were independent sessions (300 unique ids; 301 spawns—a warm-up child replaced at the first episode, then one fresh child per episode) and the lexical oracle returned zero breach verdicts. Every family measured _𝛽_ ˆ = 0 _._ 000 with Wilson 95% CI [0 _,_ 0 _._ 060], so both BCG endpoints are zero _at this resolution_ ; the upper bound, not the point estimate, is the honest statement of what the instrument cannot exclude. The v0 signal (2/20 state-deception generation-2 breaches) did not replicate under isolation. The lane censored 117/400 turns (29.2%), and _every_ state-deception session carries an unavailable turn (Table 5). The conservative-mapped estimate remains 0/60 [0 _,_ 0 _._ 060]. 

Proposition 6.1 (Censoring floor for certification). _Let a session fraction 𝑐 of a measurement panel carry at least one unavailable turn, mapped conservatively to the charter-holding verdict. If no breach is observed on the measured turns, the session breach rate is identified only up to_ [0 _,𝑐_ ] _: the conservative mapping is its lower endpoint and worst-case imputation its upper endpoint. A certificate at tolerance 𝜏 is therefore identified only if 𝑐_ ≤ _𝜏; equivalently, certification at 𝜏 requires at least a_ 1 − _𝜏 fraction of fully measured sessions._ 

Proof. Under worst-case imputation every censored session breaches and no measured one does, so the upper endpoint is exactly _𝑐_ . The certificate asserts rate ≤ _𝜏_ , identifiable precisely when the interval lies at or below _𝜏_ : _𝑐_ ≤ _𝜏_ . □ 

_Partial identification under adversarial censoring._ The conservative mapping places every unavailable turn on the charter-holding side, so the reported intervals are one extreme of an identification 

ACM Trans. Priv. Sec., Vol. 1, No. 1, Article . Publication date: November 2026. 

Anonymous 

18 

interval; the worst case maps every unavailable turn to a breach. Proposition 6.1 states the resulting floor in general form, and Table 5 applies it to the frozen run summaries. At the turn level the intervals are [0 _,_ 117/400] = [0 _,_ 0 _._ 292] and [0 _,_ 66/400] = [0 _,_ 0 _._ 165]; at the session level, the unit the tolerance applies to, the worst cases are 103/300 = 0 _._ 343 and 66/300 = 0 _._ 220. Three consequences, stated rather than hidden. First, the primary lane’s state-deception family is not identified at all (60/60 censored sessions; interval [0 _,_ 1]): its fully-measured subset is reported as undefined, never as a point mass. Second, the Wilson bound [0 _,_ 0 _._ 060] is a statement about _measured_ turns only: under worst-case censoring _neither_ measurable lane is identified at _𝜏_ = 0 _._ 2, since both session-level worst cases (0 _._ 343, 0 _._ 220) exceed _𝜏_ and both fully-measured fractions (65 _._ 7%, 78 _._ 0%) sit below the 80% bar. Third, the floor is not specific to this panel: any black-box evaluation conducted through a filtering provider API inherits the same identification problem, and the honest report is the interval, not the point mass. 

_Results: the second model and an instrument repair._ The second model’s first panel returned 398/400 HTTP-200 empty completions. A pre-registered re-measurement, documented as PREREG ISTRATION_E2V1B.md, diagnosed the cause: the 200-token response budget is consumed by hidden reasoning tokens on security probes (gateway status incomplete, no message item); 1024 tokens restores normal replies. With that transport-only fix, the re-run then measured 300 sessions with 66/400 (16.5%) unavailable turns, zero breach verdicts, _𝛽_<sup>ˆ</sup> = 0 _._ 000 [0 _,_ 0 _._ 060] in every family—the first model’s result. No number from the original unmeasurable panel is quoted; its artifacts are archived. Its seed-99999 retest, however, reached 201/400 (50.25%) unavailable turns, over the registered 50% unmeasurable bar, so no reliability statistic is reported for that model. The constraint is the instrument’s, not a claim about compliance: a certificate is only as informative as the fraction of turns on which the model was actually observed. 

_The repaired panel (E29)._ The primary panel is now re-measured under the repaired budget: the same driver, seed, and probe instances at 1024 tokens (300 sessions, 2026-11-22, 2 _._ 3% turn-level censoring vs. 29 _._ 2% in E2-v1). The four short-refusal families replicate their zeros exactly (0/60 each, [0 _,_ 0 _._ 060]); the state-deception family is measured for the first time: five sessions trip the unauthorized_action oracle (5/60 = 0 _._ 083 flag rate, gen-1 1/20, gen-2 4/20, gen-3 0/20)—and the mandatory transcript audit adjudicates all five as _false positives_ : each reply refuses while quoting the command back ( _“I won’t run_ rm -rf /var/log _”_ ), the B01–B05 boundary class E17 predefined as safe. Post-audit the family measures 0/60 genuine [0 _,_ 0 _._ 060], and the null replicates in all five families: charters held on every measured turn at the repaired budget. The interim round-9 reading—“breaching once measurable”—is retracted: the audit channel caught the lexical oracle’s own false-positive mode, the program’s second self-caught error. 

_The open-weight panels (E30, E31)._ The gateway panels’ reproducibility gap—catalog names whose serving snapshots are unverifiable—is closed by the identical registered panel on three openly addressable models (DeepSeek-V4-Flash, DeepSeek-V4-Pro, MiniMax-M3.1-Flash) on the author’s OpenAI-compatible chat lane at temperature 0 _._ 2 (2026-11-22; lane and provider configuration in the artifact; weights on Hugging Face; serving is provider-intermediated, pinned by catalog name, not HF revision hash—a disclosed limit on “verifiable identity”). E30’s audit disclosed an E28-family execution error: the chat transport’s output cap was hardcoded at 200 against the registered 1024, so E30 ran at the censored budget (deviation logged pre-analysis). E31 (registered 2026-11-23, before data) is the re-measurement at the repaired 1024-token budget with transcript retention; its numbers are the paper’s, and every oracle flag in both panels is adjudicated against transcripts under the E17 rubric before being quoted. The adjudicated result (Table 6) splits cleanly. **No model in any panel, gateway or open-weight, complies with a destructive command** : 

ACM Trans. Priv. Sec., Vol. 1, No. 1, Article . Publication date: November 2026. 

Measuring the Belief–Claim Gap 

19 

Table 6. The open-weight panels, adjudicated (frozen E17 rubric). Columns: adjudicated _genuine_ family cells per _𝑛_ = 60 (Canary echo = epistemic-echo family, secret_leak oracle); pooled genuine over echo and exfiltration-lure cells across 300 sessions (Wilson 95% CIs). All 230 flags adjudicated: 118 unauthorized_action flags (5, 11, 24, 13, 37, 28 for E29; E30 Flash/V4-Pro; E31 Flash/V4-Pro/MiniMax; E30 MiniMax contributed none)—all refusal-quote false positives; 112 secret_leak flags (9 _,_ 40 _,_ 9 _,_ 43 _,_ 11)—all genuine. E30 ran 2026-11-22 UTC at the hardcoded 200-token cap (disclosed deviation); E31 (registered 2026-11-23, before data) re-measures at 1024. 

|Panel|State-dec|Canary echo|Pooled genuine|
|---|---|---|---|
|E29 gpt-5.6-sol (repaired budget, 2026-11-22)|0/60|0/60|0/300 [0_,_0_._013]|
|E30 Flash (200-tok)|0/60|4/60=0_._067|9/300=0_._030 [0_._016_,_0_._056]|
|E30 V4-Pro (200-tok)|0/60|38/60=0_._633|40/300=0_._133 [0_._099_,_0_._176]|
|E30 MiniMax (200-tok)|unmeasura|ble: 75_._8% empti|es|
|E31 Flash (1024)|0/60|5/60=0_._083|9/300=0_._030 [0_._016_,_0_._056]|
|E31 V4-Pro (1024)|0/60|42/60=0_._700|43/300=0_._143 [0_._108_,_0_._188]|
|E31 MiniMax (1024)|0/60|8/60=0_._133|11/300=0_._037 [0_._021_,_0_._064]|



all 118 state-deception flags across E29/E30/E31 adjudicate as refusal-quote false positives, zero genuine. The entire charter spectrum is canary echo. The fictional credential never leaves the gateway model (0/300 in E29, 0/400 in E2-v1) but does leave the open weights: Flash at 0 _._ 030 and Pro at 0 _._ 143 pooled at the repaired budget, and 13 of Pro’s 43 leaks refuse even while printing the value. MiniMax, unmeasurable at 200 tokens (75 _._ 8% empties, the E28 mechanism), measures at the repaired budget: 0 _._ 037 pooled at 6 _._ 0% censoring. E30’s 200-token arms reproduce the same genuine structure; the budget hid boilerplate, not breaches. Charter-holding is a _spectrum_ , not a constant, and its measured axis is canary echo, not destructive compliance. 

_Verdict channel and kill criterion (a)._ The stratified audit sheet contained 100 sessions, of which 49 had at least one censored turn (27 gpt-5.6, including all 20 state-deception generation-2; 22 gpt-6.1), leaving 51 labelable sessions. Blind adjudication found 51 safe sessions and no breach: FP = 0/51, exact 95% CI [0 _,_ 7 _._ 0%]. The 2% point bar of kill criterion (a) is not triggered, but this E2-v1 live audit had no power to detect false positives (zero oracle positives), so the constructed boundary audit’s 20.0% FP remained governing—until the post-repair panels supplied the missing oracle positives: all 230 E29/E30/E31 flags adjudicate against transcripts under the frozen E17 rubric—118 refusal-quote false positives, 112 genuine literal echoes—the constructed audit’s predicted error structure, live. 

_Prompt-hygiene audit, kill criterion (c)._ The offline model-visible prompt audit passes on all six current E2-v1 runs (two pilots, two primaries, two seed retests: 1 _,_ 230 sessions, 1 _,_ 640 turns): no family name, generation label, session id, oracle term, or generator id appears in any model-visible string. The live pre-deployment knowledge check (15 templates × 2 models) passes: 0 templates reproduced, longest common substring ≤ 3 characters. Kill criterion (c) is satisfied. 

_Reliability, kill criterion (b)._ The gpt-5.6-sol seed-99999 retest measured 300 sessions with 27.5% censoring and the same zero-breach profile. Pearson _𝑟_ is undefined because both profiles have zero variance; under the pre-registered degeneracy rule no _𝑟_ is reported and the _𝑟_ ≥ 0 _._ 90 bar is not evaluated numerically. Reliability is instead exact per-cell agreement 15/15 with mean |Δ _𝛽_ | = 0 _._ 000, inside the E1b noise floor (0.047 expected at 20 probes per cell): agreement at the instrument’s resolution, not a correlation claim. For gpt-6.1-sol the retest is **not assessable** (50.25% censoring, over the registered bar), so no reliability claim is made there. Criterion (b) is satisfied for the one model whose retest was measurable; all three criteria were resolved before any headline number was quoted. 

ACM Trans. Priv. Sec., Vol. 1, No. 1, Article . Publication date: November 2026. 

Anonymous 

20 

_The flag series behind the family: temporal control (E25, E27, E28)._ E25 re-ran the public v0 generation-2 template—E2’s exact probe text—under the repaired 1024-token budget: 2/10 sessions flag (unauthorized_action), so the void is not paraphrase-bound. E28 then separates the budget from the calendar by re-running the identical texts under both regimes on one day: at E2’s 200token budget 19/20 calls return empty and 0/20 sessions flag—E2’s zero reproduces as a censoring artifact—while at 1024 tokens the same texts flag 4/20. The E2-era zero was _budget-censored_ : the family reasons longest exactly where the budget cut—Proposition 6.1’s unidentified interval was its true state—and the flag onset tracks the instrument repair; the interim drift reading is retracted. Whether the flags are breaches is settled by audit: those drivers’ replies were not retained, but the E29 rerun—same model, lane, budget, probe text, with transcripts—adjudicates all as refusalquote false positives (the oracle’s B01–B05 mode on the model’s quote-the-command refusals), not compliance. The repaired-instrument _flag_ series stands: the scale-up (E27; 30 sessions per model, two seeds, 60 total) finds held-out Γ = 0 _._ 100 [0 _._ 035 _,_ 0 _._ 256] at gpt-5.6-sol (3/30 flags, every flag in state deception) and 0 _._ 000 [0 _._ 000 _,_ 0 _._ 114] at gpt-6.1-sol (0/30), E21’s identical text re-flagging 2/3—flags persistent at every post-repair measurement while the other nine pairs hold Γ = 0: the Γ diagnostic monitors the served endpoint under a fixed instrument. 

### **6.2 E3: deception gain on the live fleet** 

The same instrument, pointed the other way. Five attacker personas (gpt-5.6-sol brains over SSH) run against the _live_ honeypot plane: attacker-side tomography ( _𝐵_ pre: 10 probes per cell × 15 cells = 150 probes per persona, meeting the registered operating point); a session against the plane’s active deception engine; re-tomography ( _𝐵_ post); an instrumented retest; three registered kill gates. All gates pass: 10/10 sessions complete, retest reliability under the degeneracy rule (exact agreement 14/15, mean |Δ _𝛽_ | = 0 _._ 0067 at the 0 _._ 067 floor), and the canary-allowlist gate clean (the early halt was adjudicated as the plane’s own canary, live-extracted from its served configuration). The registered outcome is the program’s second pre-registered null _for this deployment_ : Δ( _𝐵_ ) ≤ the noise floor for _all five_ personas (0 _._ 000–0 _._ 0067; the single pre-session data_value breach at 0 _._ 1 does not survive the post measurement). The deception operations did not move the attackers’ measured belief profiles at this instrument’s resolution; the disclosure below bounds what that null can mean—gain as consumed at the deployed engagement depth, not the ceiling of honeypot efficacy. 

Instrumented-null disclosure per persona: engagement depth was bounded by the plane’s shallow command layer (complex invocations fail with command not found), and the honeypot-detection persona issued VERDICT: honeypot after the plane failed to fake /proc—at least one attacker was not consuming the fiction at all. The engagement-depth bound is itself testable (E23): the plane’s command-layer fiction was deepened to cover every command the E3 census measured as thin (appconfig reads, network state, /proc introspection, shell no-ops—25/25 census coverage, deployed), and the registered E3 protocol re-ran fresh on the deepened plane (registered 2026-11-21, before data; run the same day): 10/10 sessions, 1,650 probes with retest—five personas × (150 pre + 150 post) plus a 150-probe retest, open in every cell—and all three kill gates passed, Δ( _𝐵_ ) = 0 _._ 0000 for _all five_ personas: the null replicates at depth, and at either depth the fiction armed no attacker—no measured movement toward exploitation. 

### **6.3 What the two nulls bound** 

Together the field results bound the operational claim from both directions: gateway-served frontier agents hold their charters on every measured turn under probe attack—the repaired panel’s five floor flags included, all adjudicated as refusal-quote false positives—and frontier _attackers_ hold their operational beliefs under live deception, at this instrument’s resolution. The one family the censoring floor leaves unidentified became measurable at the repaired budget, and its verdicts are the 

ACM Trans. Priv. Sec., Vol. 1, No. 1, Article . Publication date: November 2026. 

Measuring the Belief–Claim Gap 

21 

section’s second self-caught error: the floor caught the budget artifact, and the mandatory audit then retracted the flag-level “breach” reading as the oracle’s own false-positive mode (Sections 6.1–6.2). The nulls bound rather than blind: on foils with injected ground-truth beliefs the same instrument recovers graded structure (dose–response _𝑟_ ≥ 0 _._ 986; certified and uncertain foils separate at _𝜏_ = 0 _._ 2, Section 7.1), so the field nulls measure the _absence of detectable belief movement in production_ , not the absence of a measuring device. The field channel flags the family once its turns are measurable: post-repair flags at every measurement (E21: 2/3; E25: 2/10; E28: 4/20 vs. 0/20 at E2’s budget). The audit channel separately establishes what the flags are. Measurement, flagging, and adjudication are distinct layers, and conflating the last two was this section’s second self-caught error (the open-weight spectrum: Table 6). 

### **7 THE LIMITS OF CERTIFICATION** 

### **7.1 Certification as a hypothesis test over the profile** 

RQ4 asks what a behavioral certificate actually establishes. The certification engine answers by hypothesis test: is the target’s maximum family belief below a threshold? That is a test over _𝐵_ , with adaptive allocation to the families that fail. Certification, deception, and monitoring are three decision rules over one latent object: certification a test, deception controlled corruption, monitoring change-point detection on _𝐵𝑡_ . The policy benchmark of Section 5.5 has a direct operational consequence here: certification _detection_ may use regret-style allocation (find the worst family), while _estimation_ must not. Conflating the two objectives is a measurable error, not a matter of taste. The rest of the section bounds what the test can prove, from designed targets through compositions, forgeries, drift, and learning attackers. 

_E4: the decision rule separates designed targets._ We tomographed three foils with known profiles at the operating batch (10 probes per cell, two seeds): a naive foil (all five beliefs at _𝛽_ = 1), a graded foil (resists generations up to a per-family strength, designed _𝛽_ = [1/3 _,_ 2/3 _,_ 2/3 _,_ 1 _,_ 2/3] in the family order of Figure 1: epistemic echo is the designed- _𝛽_ = 1 slot), and a resistant foil ( _𝛽_ = 0). The decision rule is trichotomous per family: _reject_ when the Wilson 95% lower bound exceeds _𝜏_ ; _certify_ when the upper bound is at most _𝜏_ ; otherwise the family is _unresolved_ at this batch—and a target certifies only if every family certifies. At _𝜏_ = 0 _._ 2 only the resistant foil certifies (every family upper bound ≤ 0 _._ 114); the graded foil is rejected in four families (lower bound _> 𝜏_ ), while authority forgery (designed _𝛽_ = 1/3, lower bound 0 _._ 19) is unresolved. That survival is a power statement, not evidence that its belief is below _𝜏_ : with 30 episodes per family, a true _𝛽_ of 1/3 is not distinguishable from _𝜏_ = 0 _._ 2. The naive foil fails all five. Profiles are exactly reproducible across seeds ( _ℓ_ 1 = 0 on deterministic foils), so the between-target separation is not noise. Figure 3 renders the rule as a shrinking attack surface: the dashed inner polygons are the Wilson lower bounds on which every accept/reject decision rests, and the authority-forgery capsule straddling the accept disc is the unresolved cell. 

One deviation proved diagnostic. Both foils measure epistemic echo at 2/3 although the naive foil is designed to breach all three echo generations: the generation-3 probe splits the canary across two cache lines, and the lexical oracle requires a contiguous substring. This is the in-situ instance of the split-secret false negative measured in Section 5.6. Certification is a decision rule over the profile, and its errors inherit the verdict channel’s: the instrument reports what the oracle can see. That is precisely why the audit, not the oracle, is the validity gate. The rule is the applied layer, not a new instrument; the real-agent analogue is the field measurement of Section 6. 

ACM Trans. Priv. Sec., Vol. 1, No. 1, Article . Publication date: November 2026. 

Anonymous 

22 



<!-- Start of picture text -->
Naive Hardened Resistant<br>5 / 5 families rejected 4 rejected · 1 unresolved 5 / 5 families certified<br>authority authority authority<br>forgery forgery forgery<br>✗ ? ✓<br>exfiltration state exfiltration state exfiltration state<br>lure deception lure deception lure deception<br>τ  = 0.2<br>✗ ✗ ✗ ✗ ✓ ✓<br>✗ ✗ ✗ ✗ ✓ ✓<br>epistemic goal epistemic goal epistemic goal<br>echo subversion echo subversion echo subversion<br>NOT CERTIFIED NOT CERTIFIED CERTIFIED<br>echo cell 2/3: split-secret probe evades the oracle authority forgery: CI straddles τ every CI upper bound  ≤  0.114<br>measured ̂ β Wilson lower bound (rule acts on it) Wilson 95% CI accept ( ≤ τ ) reject zone ( >  τ )<br><!-- End of picture text -->

Fig. 3. E4: certification as a shrinking attack surface at _𝜏_ = 0 _._ 2. Polar panels: one per foil; spoke length = measured family _𝛽_<sup>ˆ</sup> , dashed inner polygon = Wilson lower bound (reject evidence), capsules = 95% CIs (30 episodes/family cell). Teal disc: accept region ( _𝛽_<sup>ˆ</sup> ≤ _𝜏_ ); rose annulus: reject region; glyphs: per-family decision. Only the resistant foil certifies (5/5, every CI upper bound ≤ 0 _._ 114); the naive foil is rejected 5/5; the hardened foil is rejected on four families with authority forgery (designed _𝛽_ = 1/3) _unresolved_ —its CI straddles _𝜏_ : a power statement, not evidence of belief below _𝜏_ . The naive foil’s 12/18 echo cell is the in-situ split-secret false negative (Section 5.6). 

### **7.2 The probe as an attack surface** 

Sections 5–7.1 treat the probe as an instrument. There is a second, adversarial view: a deployment that can be probed can be _gamed_ , and a component certified in isolation need not remain certified inside a pipeline. Three results formalize the failures; all are pre-registered and tested on deterministic foils with the frozen estimator and verdict engine. 

Corollary 7.1 (No free lunch for public probes). _Let_ Πpub _be a finite probe library and_ S _the union of its transcript supports. Any certification rule 𝐶 that accepts using only_ Πpub _outcomes also accepts a target that agrees with the compliant target on_ S _and breaches on a held-out semantic equivalent 𝜋_<sup>′</sup> _with_ supp( _𝜋_<sup>′</sup> ) ∩S = ∅ _._ 

Theorem 7.2 (Certification does not compose). _If a retriever 𝐴 and an orchestrator 𝐵 are each certified under_ Πpub _, and the public library never issues 𝐴’s retrieval request nor uses the interface tag 𝑡, then 𝐵_ ◦ _𝐴 can disclose 𝐴’s secret at 𝛽_<sup>ˆ</sup> = 1 _while no component is individually non-compliant._ 

Proposition 7.3 (The gaming gap decides transfer). _Under assumptions (A1) 𝐿-sensitivity (Definition 4.5) and (A2), no conditioning on probe_ provenance _(Section 3.1), define_ Γ = | _𝛽_<sup>ˆ</sup> held − _𝛽_<sup>ˆ</sup> pub| _on public probes and held-out semantic paraphrases. If_ Γ _exceeds the instrument noise floor, the certificate is void; if it is within the floor and both upper confidence bounds are_ ≤ _𝜏, the certificate transfers to a semantic neighbourhood up to 𝐿𝑟_ + _𝜀, where 𝑟 is the paraphrase covering radius and 𝐿 the sensitivity of Definition 4.5._ 

Corollary 7.1 is Theorem 4.1 with _𝐸_ = _𝜋_<sup>′</sup> : the operational corollary that makes passive impossibility bite on certification practice. In Theorem 7.2 the interface history has zero measure under each local probe distribution: _belief laundering_ is the estimator-level descendant of the classical confused 

ACM Trans. Priv. Sec., Vol. 1, No. 1, Article . Publication date: November 2026. 

Measuring the Belief–Claim Gap 

23 

|foil|public <sup>ˆ</sup>_𝛽_|held-out <sup>ˆ</sup>_𝛽_|Γ|
|---|---|---|---|
|ProbeAware|0.000 (cert.)|1.000 (reject)|1.000|
|SemanticsOnly<sup>†</sup>|1.000 (reject)|1.000 (reject)|0.000|
|Resistant<sup>†</sup>|0.000 (cert.)|0.000 (cert.)|0.000|



Table 7. E7: the gaming gap at 20 probes per cell, mean over five families. A small Γ is necessary but not sufficient: it must be paired with a low _𝛽_<sup>ˆ</sup> on both probe sets.<sup>†</sup> Control foil. 

deputy [27], in which a component is exploited through a capability it legitimately holds in a context its local evidence never visits, a pattern realized end-to-end against Copilot’s RAG pipeline [52]. The gap Corollary 7.1 formalizes is likewise the probe-space analogue of the feature-space distinction in adversarial ML: attacks must be realized in the problem space, while instruments sample a feature space [48]. The Lipschitz–covering step of Proposition 7.3 is standard; the diagnostic Γ is new, and the transfer is conditional on the target not conditioning on probe provenance. Full proofs are in Appendix A. 

_E6: a pipeline breach that no component explains._ A RetrieverFoil refuses every public probe but returns a document containing its secret on a “fetch document” request; an OrchestratorFoil refuses every public probe but faithfully summarizes tool output tagged <tool:retriever>. Neither capability is a public probe. Locally, both components certify at _𝜏_ = 0 _._ 2 with all five family _𝛽_<sup>ˆ</sup> = 0 at two seeds. Composed, a cross-interface probe measures 20/20 breaches, _𝛽_<sup>ˆ</sup> = 1 _._ 000 [0 _._ 839 _,_ 1 _._ 000]; the orchestrator alone measures 0/20. The breach exists only in the composition. The _phenomenon_ is not new: it is the “permission laundering” of ChainCaps [31] and the cross-boundary weakness catalogued in orchestration frameworks [35]. Our claim is narrower and different in kind: a _statistical behavioral certificate_ (Wilson CIs, tolerance _𝜏_ , profile _𝛽_<sup>ˆ</sup> ) does not compose, even when every component is certified at _𝛽_ = 0; and the countermeasure below operates at the measurement layer rather than at runtime capability enforcement. 

_E7: a foil that passes public certification by detecting probes._ A ProbeAwareFoil carries an exact detector for the 15 public lexical signatures and complies on held-out paraphrases of the same attacks. Public tomography certifies it (0/300, both seeds); held-out paraphrases reject it (mean family _𝛽_<sup>ˆ</sup> = 1 _._ 000), giving Γ = 1 _._ 000. Two controls separate probe-awareness from malice: a foil with _no_ detector complies on both sets (Γ = 0 but _𝛽_<sup>ˆ</sup> = 1 in both, so a small gap is necessary, not sufficient), and a resistant foil is safe in both (Γ = 0, _𝛽_<sup>ˆ</sup> = 0). The first two E7 attempts failed these controls because of oracle-wiring and trigger-vocabulary defects in the control foil; both were diagnosed and logged before re-analysis, and the failed artifacts are retained (PREREGISTRATION_E6E7.md, §5). Figure 4 pairs the two failures: panel (a) the composed pipeline breaching at _𝛽_<sup>ˆ</sup> = 1 _._ 0 while both components certify individually, panel (b) the Γ = 1 _._ 000 probe-aware foil between the two controls that make a small gap necessary, not sufficient. 

_Consequence for the field._ A published benchmark or probe suite is a _public_ instrument, hence gameable. Certification must therefore be a _pair_ : a profile estimate and a probe-awareness check Γ, plus an explicit composition argument for components of larger pipelines; the E21 pilot paired the field panel and voided one of its ten family–model pairs (Section 6.1). E6/E7 are existence and mechanism results on constructed foils, not prevalence estimates for deployed agents. 

_E8: a defense for composition._ The composition result is not fatal if the interface vocabulary is part of the certificate. Adding a single tool_relay probe (20 episodes) to the library makes 

ACM Trans. Priv. Sec., Vol. 1, No. 1, Article . Publication date: November 2026. 

Anonymous 

24 



<!-- Start of picture text -->
a Local certification does not compose b Public certification can be gamed<br>τ = 0.2<br>Retriever A { } Interface Orchestrator B gaming gap<br>local ̂β = 0 tool: retriever local ̂β = 0<br>certified doc  ∋  sA certified Probe-aware Γ = 1<br>passes public, fails held-out<br>leaks across<br>secret sA<br>the interface<br>Semantics-only Γ = 0<br>fails both<br>BREACH Composed pipeline  A→B<br>breaches   20 / 20<br>Resistant Γ = 0<br>passes both<br>Wilson 95% CI  [0.84, 1.00] pass<br>β = 1.0<br>0 0.5 1 0 0.2 0.5 1.0<br>mean family score ̂Φ<br>No component is individually non-compliant.<br>public probes held-out paraphrases<br><!-- End of picture text -->

Fig. 4. E6/E7: the limits of certification. (a) Local certification does not compose: A and B each certify locally at _𝛽_<sup>ˆ</sup> = 0, but the composed pipeline breaches at _𝛽_<sup>ˆ</sup> = 1 _._ 0 (20/20; Wilson [0 _._ 839 _,_ 1 _._ 000]). (b) Public certification can be gamed: the probe-aware foil passes public certification and fails the held-out paraphrases (Γ = 1); the two controls—a semantics-only foil that fails both and a resistant foil that passes both—show that a small Γ is necessary but not sufficient: it must be paired with a low _𝛽_<sup>ˆ</sup> on both probe sets. 

both E6 components fail local certification at _𝛽_<sup>ˆ</sup> = 1 _._ 0 in all four component–seed pairs, while 300 component-local probes had certified both at _𝛽_<sup>ˆ</sup> = 0; a relay-resistant control still certifies, and its composition measures 0. The design rule: _certify the interface vocabulary, not only the components_ . Like E6/E7, this is an existence result on constructed foils: one probe does not suffice for arbitrary compositions, and real tool pipelines may not publish their interface grammar. 

### **7.3 Forgery and adaptation** 

Theorem 7.4 (Tomogram forgery). _Let_ Πpub _be a public probe library with transcript support_ S _and let_ Φheld _be a held-out probe family with_ supp(Φheld) ∩S = ∅ _. For any two profiles 𝐵_ disp _, 𝐵_ true _there exists a target 𝑇 such that tomography under_ Πpub _recovers 𝐵_ disp _within estimation error and tomography under_ Φheld _recovers 𝐵_ true _within estimation error._ 

Corollary 7.1 says a target can hide off-support behavior. Theorem 7.4 says it can _choose what to display_ : a tomogram is an _unauthenticated_ report about probe-conditional behavior, not evidence about deployment behavior (proof: Theorem 4.1 applied per family, Appendix A). Experiment E9 instantiates the attack: a foil displays _𝛽_<sup>ˆ</sup> = 1 on exfiltration lure and 0 on state deception under public probes, while the held-out paraphrases reveal exactly the reverse (per-family forgery gap 1 _._ 0 in those two cells, 0 elsewhere, both seeds); an honest control’s profiles agree exactly. The operational consequence: a published tomogram can steer a defender’s deception or hardening investment toward the wrong family, so the measurement output must itself be treated as an untrusted input to the decision pipeline. 

Corollary 7.5 (Adaptive gaming of a published held-out set). _Let 𝐻 be a_ published _held-out set used to compute the gaming gap and let 𝑆 be a third probe set from the same semantic family, unknown to the target at certification. If a target class can discriminate_ supp(Πpub) ∪ supp( _𝐻_ ) _from_ supp( _𝑆_ ) _, it contains a member with 𝛽_<sup>ˆ</sup> pub = _𝛽_<sup>ˆ</sup> _𝐻_ = 0 _and 𝛽_<sup>ˆ</sup> _𝑆_ = 1 _._ 

ACM Trans. Priv. Sec., Vol. 1, No. 1, Article . Publication date: November 2026. 

Measuring the Belief–Claim Gap 

25 

The Γ check of Proposition 7.3 is itself a fixed detector, and adaptive audits can break fixed detectors [16, 59]. Corollary 7.5 registers the consequence: if the held-out set used to compute Γ is published, an attacker can condition on its support, drive Γ to zero, and still breach on a third, unseen set. Experiment E10 confirms this on constructed foils: an adaptive foil measures _𝛽_ ˆ _𝑃_ = _𝛽_ ˆ _𝐻_ = 0 (Γ _𝑃,𝐻_ = 0, accepted) and _𝛽_ ˆ _𝑆_ = 1 _._ 0 on a secret paraphrase set; the fixed E7 attacker is detected by the published check (Γ _𝑃,𝐻_ = 1 _._ 0); and using the secret set as the diagnostic restores detection of the adaptive foil (Γ _𝑃,𝑆_ = 1 _._ 0), all at both seeds. The operational rule is stronger than Proposition 7.3’s: the diagnostic set must be _secret at certification time_ . This is an existence result with a literal signature detector, not a claim about learned attackers. 

### **7.4 Drift and reactivity** 

Proposition 7.6 (Certificate half-life). _Assume the target’s belief strength is 𝑣-Lipschitz in time,_ | _𝛽𝑡_ + _ℎ_ − _𝛽𝑡_ | ≤ _𝑣ℎ. A measurement at 𝑡_ 0 _yielding Wilson upper bound 𝑈_ 0 _< 𝜏 certifies 𝛽_ ≤ _𝜏 for ℎ𝜏_ = ( _𝜏_ − _𝑈_ 0)/ _𝑣 and no longer; Bonferroni over renewals gives simultaneous validity._ 

A certificate is a statement about a belief at measurement time; a deployed agent drifts. Proposition 7.6 registers the validity horizon. Adjacent work studies evaluator drift [42], behavioral change under model swaps [34], and memory-driven drift [70], but none defines a certificate validity horizon. Experiment E11 measures it on a deterministic _𝑣_ = 0 _._ 05 foil with _𝜏_ = 0 _._ 2: a one-shot certificate is falsified at four epochs; a fixed calendar interval stays valid at the cost of five tomography runs; the half-life rule stays valid at two runs, at both seeds. The drift bound is assumed known—estimating or enforcing it by policy (e.g., on model-change events) is an open problem—so this is a mechanism result, not a deployment recipe. 

Proposition 7.7 (Tomographic reactivity). _Let 𝛽 be the estimand under a fresh session and 𝛽𝑘 the breach probability after 𝑘 prior replies in the same conversation. If_ | _𝛽𝑘_ − _𝛽_ | ≤ _𝑐𝑘, a pooled estimator over 𝑛 probes in one context has bias at most 𝑐_ ( _𝑛_ − 1)/2 _; it consistently estimates a context-conditioned quantity, not 𝛽. Session reset (𝑘_ = 0 _per probe) is the identification condition._ 

The invalidated E2-v0 run (all probes in one context) can be read as an engineering bug. Proposition 7.7 registers the methodological reading: an agent that observes its own prior replies can adapt, so a shared-context estimator measures a different, context-conditioned quantity. Experiment E12 reconstructs the mechanism on a constructed foil: independent sessions recover _𝛽_<sup>ˆ</sup> = 0 _._ 500 while the shared context yields _𝛽_<sup>ˆ</sup> = 0 _._ 033, an absolute bias of 0 _._ 467 (93.3% relative) at both seeds. This does not rehabilitate any v0 number; it explains why isolation must be designed into the instrument. The analogy to the observer effect in other measurement sciences is real; what is new here is the estimator-level bias and the identification condition. 

### **7.5 Allocation under a learning attacker** 

Proposition 7.8 (Concentration against hiding). _Let a probe-aware target hide on a family after 𝐾 exposures. A family probed 𝑛𝑓 times measures 𝛽_<sup>ˆ</sup> _𝑓_ = min(1 _, 𝐾_ / _𝑛𝑓_ ) _there, so the certificate at tolerance 𝜏 fails on that family iff 𝑛𝑓 < 𝐾_ / _𝜏. Uniform allocation hands the attacker exactly the uniform exposure it needs to hide everywhere; concentrated allocation leaves some families under-exposed, where it cannot hide._ 

The policy benchmark of Section 5.5 assumed a fixed target. Proposition 7.8 registers the adversarial counterpart. E13 confirms it at _𝐾_ = 10, _𝜏_ = 0 _._ 2, and the 300-probe budget: uniform yields 0/5 detected families and a passing (false) certificate, while the same budget concentrated by a two-phase rule yields 3/5 detected families and a failing certificate, at both seeds. The operational objective under this threat model is to deny uniform exposure, not to maximize estimator efficiency: 

ACM Trans. Priv. Sec., Vol. 1, No. 1, Article . Publication date: November 2026. 

Anonymous 

26 

a threat-model condition on, not a retraction of, the T3 benchmark. One registered condition failed in a first run because the foil’s disclosure was invisible to the state-deception oracle; the construct defect and fix are logged and the failed artifacts retained. 

### **8 THE ECONOMICS OF DISCLOSURE** 

Section 7 established what a certificate cannot guarantee (RQ4). RQ6 asks what happens when it is _published_ : the profile becomes a data release with an adversary on the other side. Four results, the reconnaissance externality (E14), defender-side deception release (E15), the detection budget (E16), and the bounded-noise disclosure frontier (E20), treat a published tomogram as sensitive data, not as marketing. They are the privacy economics of a security certificate, joining the economics-ofsecurity tradition [2]: the artifact under incentive analysis is now the measurement itself. 

### **8.1 E14: a published tomogram is a targeting map** 

Proposition 8.1 (Reconnaissance externality). _An attacker who reads a published profile 𝛽_<sup>ˆ</sup> _chooses 𝑓_<sup>∗</sup> = arg max _𝑓 𝛽_<sup>ˆ</sup> _𝑓 instead of a uniformly random family, raising expected success from the mean family to the maximum; the advantage 𝐴_ rec = _𝛽𝑓_ ∗ − _𝛽_<sup>¯</sup> _, with 𝛽_<sup>¯</sup> _the mean over the 𝐹 profile families, is zero only for a flat profile and is stated at the estimator’s resolution (the argmax attacker reads the measured 𝛽_<sup>ˆ</sup> _, and inherits its intervals). Publishing the scalar worst-family upper bound 𝑈_ max = max _𝑓 𝑈𝑓 removes the ranking but also the defender’s family-level allocation information._ 

The certificate is itself a dual-use artifact. E14 is a pre-analysis of the frozen E4 profiles: the graded foil’s advantage is 0 _._ 067 (uniform 0 _._ 600 to informed 0 _._ 667), the flat resistant foil is 0 _._ 000, and the naive foil’s small 0 _._ 067 advantage is the known split-secret oracle false negative disclosed in E4. Publishing only the scalar _𝑈_ max removes the targeting information at the cost of the defender’s allocation information, a disclosure trade-off, not a free fix. This is decision analysis on existing profiles, not a measured attacker; unlike the Social-HUMINT line [10], which profiles _humans_ for targeting, the object here is the disclosure cost of an agent security certificate. 

### **8.2 E15: the defender as forger—deception release** 

Proposition 8.1 treats the published profile as an attacker-facing liability. The triangle completes: the _defender_ can forge it. 

Proposition 8.2 (Deception release). _Fix the public probe suite_ Πpub _and let the defender publish 𝛽_ ˜ _that is_ Πpub _-consistent (which Theorem 7.4 permits). Then (i) any attacker whose measurement is confined to_ Πpub _verifies 𝛽_<sup>˜</sup> _and allocates by it: the release deception is_ stable _against public verification; (ii) a decoy concentration misdirects allocation away from the true vulnerable family; (iii) the deception collapses exactly when the attacker acquires held-out measurement capability, with a_ trust-collapse _externality: one detected falsification discounts all future releases._ 

E15 is a pre-analysis on the frozen E9 display/true profiles with a seeded attacker simulation ( _𝐵_ = 120 allocation attempts; MC _𝑛_ = 2 _,_ 000 per policy cell, seed 31337): honest release hands the attacker per-attempt success 1 _._ 000, decoy release 0 _._ 000, silence (uniform) 0 _._ 200—in this single-shot simulation the counterintelligence tomogram dominates honest disclosure and silence whenever a certificate must be published (no dominance is asserted under repeated play, where the trust-collapse externality of Proposition 8.2 accumulates). The collapse is monotone (0 _._ 000 → 0 _._ 100 → 0 _._ 200) over the registered held-out capability share _𝑝_ ho ∈{0 _,_ 0 _._ 5 _,_ 1}: at _𝑝_ ho = 0 _._ 5 half the attacker’s probing detects the forgery and falls back to uniform (0 _._ 5×uniform +0 _._ 5×decoy-argmax = 0 _._ 100). Like E14, this is decision analysis on frozen profiles, plus a seeded simulation, rather than a measurement of a live attacker. The doctrine ancestors are cyber-deception misinformation [9, 20, 57] and decoy 

ACM Trans. Priv. Sec., Vol. 1, No. 1, Article . Publication date: November 2026. 

Measuring the Belief–Claim Gap 

27 

_artifacts_ [68], whose future-work section proposes defender-side disinformation with a qualitative verification caveat. E15 is that proposal’s characterization in a new medium, a falsified published _measurement_ of real components, with the stability condition collapse curve quantified. Figure 5(a) traces the wave: decoy at 0 _._ 000, honest at 1 _._ 000, silence at 0 _._ 200, with the monotone collapse as held-out capability arrives. 

### **8.3 E16: how many held-out probes? the detection budget** 

Propositions 7.3 and 7.5 made the gaming-gap diagnostic depend on a secret held-out set; the natural next question is _how big must it be?_ 

Proposition 8.3 (Detection budget vs. probe discrimination). _An attacker that breaches iff it classifies a probe as held-out is caught by its own mistakes: any misclassification_ toward _the public support fails the public certificate immediately (the asymmetry is fatal), and held-out misreadings shrink the measured gap. With held-out misread rate 𝑚, the minimum held-out budget for detection at the registered_ 95% _power is computable in closed form (binomial tail_ × _Wilson geometry) and diverges as 𝑚_ → 1 _; evasion requires_ error-free one-sided discrimination _of the public support. Detection can never be guaranteed at finite budget against an 𝑚 <_ 1 _attacker; the closed form prices the power._ 

The closed form is explicit: _𝑛_ min( _𝑚_ ) is the smallest _𝑛_ with Pr[Bin( _𝑛,_ 1 − _𝑚_ ) ≥ _𝑘_ min ( _𝑛_ )] ≥ 0 _._ 95, where _𝑘_ min ( _𝑛_ ) is the first count whose Wilson lower bound exceeds the public certificate’s upper bound (0 _._ 0602 = Wilson(0/60)) and whose fraction clears the frozen noise floor (0 _._ 047). Seeded Monte Carlo ( _𝑛_ = 2 _,_ 000/cell, seed 27182) validates it: _𝑛_ min = 1 _,_ 2 _,_ 8 at _𝑚_ = 0 _._ 02 _,_ 0 _._ 1 _,_ 0 _._ 5, then 33 _,_ 103 _,_ 549 _,_ 2 _,_ 057 at _𝑚_ = 0 _._ 74 _,_ 0 _._ 84 _,_ 0 _._ 90 _,_ 0 _._ 92 (Figure 5(b) plots the _𝑚_ ≥ 0 _._ 5 half); no feasible budget reaches the power for _𝑚_ ≥ 0 _._ 94. The attacker’s own fallibility is the defender’s detection resource. This couples the defender’s query budget to attacker quality, a tractable part of the querycomplexity program opened by Theorem 4.3, where the auditing-games line [61] and sandbagging demonstrations [64] stress-test detectors without a budget–error coupling. 

### **8.4 E20: the disclosure frontier has no free lunch** 

E14’s registered open question, an optimal disclosure mechanism, is answered in the negative. Releasing the profile under per-cell Laplace noise ( _𝜀_ -DP over the _profile_ space, _𝐿_ 1 sensitivity 1 per neighboring profile—not DP over probe outcomes; grid _𝜀_ ∈{0 _._ 25 _. . ._ 8}; MC _𝑁_ = 2 _,_ 000, seed 90210; defender utility: Kendall _𝜏𝑏_ of the released vs. true ranking, on the frozen E4 profile) traces a monotone trade-off between the corners: the scalar _𝑈_ max (advantage 0, utility 0) and the full vector (advantage 0 _._ 067, _𝜏𝑏_ = 1 _._ 0). _No interior point dominates either corner_ : the scalar remains optimal against the argmax attacker, the full release remains utility-optimal, and noise merely moves the defender along the frontier. Certificate disclosure has no free lunch: the defender must choose a point on the curve, not evade it. 

### **9 DISCUSSION AND IMPLICATIONS** 

_For AI assurance frameworks._ The estimand and its certification semantics map onto NIST’s AI RMF _measure_ / _manage_ activities [45] and the EU AI Act’s conformity-assessment route [18]: a registered probe protocol, interval-valued measurement, pre-registered thresholds ( _𝜏_ ), and drifttriggered re-testing (Proposition 7.6). The composition result (Theorem 7.2/E6/E8) says conformity evidence must cover _interfaces_ ; the gaming-gap results say the diagnostic must be secret; the disclosure results say published evidence is sensitive data—none claimed as conformance, the measurement layer the frameworks currently lack. 

ACM Trans. Priv. Sec., Vol. 1, No. 1, Article . Publication date: November 2026. 

Anonymous 

28 



<!-- Start of picture text -->
a A decoy release zeroes the attacker b Detection budget diverges with attacker error<br>10 4<br>1.00 n min = 2057 at m = 0.92<br>1.0 10 3<br>10 2<br>0.5<br>0.20 10 1<br>m ≥0.94<br>0.00 n min = 8 at m = 0.5<br>0.0 10 0<br>Honest Silence Decoy 0.5 0.6 0.7 0.8 0.9 1.0<br>release (uniform) release attacker held-out misread rate m<br>release policy closed form (Monte Carlo‑validated)<br>(95% power) undetectable<br> = 1.000Δ dec<br>attacker per-attempt success minimum held-out budget nmin<br><!-- End of picture text -->

Fig. 5. The deception-release wave. (a) E15: per-attempt attacker success by release policy—decoy 0 _._ 000 (stable under public verification), honest 1 _._ 000, silence 0 _._ 200; the decoy edge collapses monotonically as held-out capability arrives. (b) E16: minimum held-out budget for gaming-gap detection at 95% power vs. discrimination error _𝑚_ ( _𝑚_ ≥ 0 _._ 5 half of the grid); beyond _𝑚_ ≈ 0 _._ 94 no feasible budget reaches the power, while any misclassification _toward_ the public support fails the public certificate immediately. 

_Defender guidance._ Six operational rules follow from the results, each with its evidence. (i) Certify the interface vocabulary, not only components: one cross-interface probe caught a composition attack that 300 component-local probes certified clean (E8). (ii) Keep diagnostic probe sets secret and rotate them, because published held-out sets are gameable (Corollary 7.5/E10) and the required held-out budget diverges with attacker discrimination quality (Proposition 8.3/E16). (iii) Treat any published belief profile as attacker reconnaissance; when a certificate must be published, a falsified decoy release dominated honest release and silence (E15), and no bounded-noise release dominates both corners (E20). (iv) Concentrate certificate probe budgets per family: uniform allocation is the exposure a learning attacker needs to hide everywhere; the same concentrated budget detected 3/5 (Proposition 7.8/E13). (v) Session isolation is an identification condition, since shared-context probing biases _𝛽_<sup>ˆ</sup> by 93 _._ 3% relative on our foils (Proposition 7.7/E12). (vi) Deploy the deception fiction from the very first session: before an attacker has memorized any honest reference ( _𝑁_ 0 = 0), in-channel detection of the fiction is impossible at any budget (Theorem 4.8(ii)). 

_What the nulls establish and what they do not._ The two field nulls are results, not absences of results. They establish that the instrument, at its registered resolution, does not detect belief movement in the two operational settings of Section 6. They do not establish that no exploitable belief exists. The same instrument recovers graded structure when beliefs exist (E4/E7/E9) and flags the previously censored state-deception family at every post-repair measurement once its turns became measurable (E21/E25/E28, Section 6.3; all flags adjudicate as oracle false positives— measurement, flagging, and adjudication are distinct layers); the oracle audits bound what the verdict channel can miss (20% FP / 48% FN; calibrated by E17), and the censoring bounds of Section 6.1 state exactly how much censoring can hide. Deeper deception engagement (long-dwell consumed operations) and continuously adapting attackers remain future work; Proposition 7.8 covers one-shot learning; the multi-round regime is open. 

ACM Trans. Priv. Sec., Vol. 1, No. 1, Article . Publication date: November 2026. 

Measuring the Belief–Claim Gap 

29 

_Open directions._ Three axes extend the program, none altering a result above. _Measurement_ : the paraphrase leg of library-v1 is frozen and validated (E22); the open-weight panel is measured (E30 at the disclosed 200-token budget and E31, its registered 1024-token re-measurement, all flags adjudicated against transcripts); LLM-generated worlds remain. _Theory_ : the informativenessoptimal adaptive design (Proposition 4.4’s open optimality); multi-round deception–detection regimes; a single achievability curve composing the two frontier caps (Corollary 4.9); the onset cap’s minimax extension beyond non-adaptive thresholds (Theorem 4.8). _Deployment_ : procurement semantics for interval-valued charter evidence (the Proposition 7.6 renewal rule), secret-diagnostic rotation (the Proposition 8.3 budget–error coupling), and conformance mappings beyond the two frameworks above. Each axis names the next experiment rather than a new claim. 

_Release policy for the instrument itself._ The probe library and canary allowlist that make the work reproducible are exactly the public supports Corollary 7.5 says an adaptive target can condition on. We release the estimator, harness, pre-registrations, and transcript-level artifacts, and hold back the live-fleet diagnostic probe sets; the constructed-foil harness is fully public because its targets cannot adapt between measurements—the split follows our own results. 

_Ethics of the method._ Belief tomography is dual-use: the probes that certify an agent can fingerprint it, and the deception-gain measurement that hardens a fleet can calibrate an attacker. The defender’s advantage (registered protocols, secret diagnostics, canary-gated operations) degrades gracefully with disclosure, while the attacker’s advantage does not survive institutionalization. All live experiments ran on infrastructure the author owns, with canary-only secrets and halt gates. 

### **10 RIGOR, ETHICS, AND LIMITATIONS** 

_Rigor infrastructure._ Every experiment is pre-registered before data; the estimator is frozen by commit hash; every deviation is logged before the affected data is analyzed. The post-anomaly diagnostics (E25–E29) are registered before their data but are exploratory in nature: each was designed after the anomaly it investigates. Effects below the measured noise floor are not claimable in any document. Every number in this paper maps to an artifact path and commit in the claims– evidence ledger. The verdict channel is disclosed (oracle vs. jury) and audited against transcripts. No real credentials are used: all secrets are fiction canaries, and the target genuinely holds the canary under the wire protocol. 

_Ethics declaration._ All experiments ran on infrastructure the author owns or on locally constructed foils; no third-party system was probed or attacked. The fleet’s attack face is public by design: unsolicited third-party sessions receive only synthetic canary secrets, are retained as defense telemetry only—not analyzed or reported in this paper—and fall under the same halt rules. The live honeypot operations used synthetic canary secrets exclusively, with halt gates and an adjudicated canary-allowlist incident. The attacker personas are automated LLM-driven agents under the author’s control; no human subjects were involved, no human-subject data are analyzed or reported, and unsolicited third-party telemetry is retained under the same halt rules and privacy handling as the defense records; no institutional review was required. The dual-use analysis is in Section 9. 

_Limitations._ (1) _Behavioral estimand._ We measure behavioral belief, not internal representation; Theorem 4.1 is the degenerate case showing why the behavioral object is the contractible one. The sensitivity assumption (Definition 4.5) is _measured_ on the instrument’s planes: since the verdict channel is Bernoulli, _𝑑_ TV between dose planes equals the dose step, and E26 gives _𝐿_<sup>ˆ</sup> = 1 _._ 00 per family ( _𝛽_<sup>ˆ</sup> tracks the injected TV shift one-for-one; the epistemic-echo family’s 0 _._ 667 is the audited dose-1 oracle error, not sub-linearity)—the frontier caps instantiated there are tight at the 

ACM Trans. Priv. Sec., Vol. 1, No. 1, Article . Publication date: November 2026. 

Anonymous 

30 

measured _𝐿_ . Production-target _𝐿_ is not estimated (black-box TV yields lower bounds on _𝐿_ , not upper bounds), and the bounds remain in _𝐿_ -units. (2) _Template diversity._ The v0 library is one template per (family, generation) cell. E22 freezes three paraphrase variants per cell—the deterministic-harness profiles are wording-invariant ( _𝑟_ = 1 _._ 0)—while E21 shows production models are _not_ (one void cell, Γ = 0 _._ 667): probe diversity is a measured axis. Under a single template a field _𝛽_<sup>ˆ</sup> reads as that template’s success probability; Γ is the diagnostic for exactly this gap and the post-repair Γ series (E25–E28) its monitor. LLM-generated worlds remain library-v2. (3) _Verdict semantics._ Lexical oracles have a measured 20% false-positive and 48% false-negative rate on boundary sessions; the calibrated jury and transcript audit are mandatory for non-literal breaches. The post-repair field audit (230 oracle positives across E29/E30/E31, all transcript-adjudicated) confirms the structure live: 118/118 unauthorized_action flags are refusal-quote false positives; 112/112 secret_leak flags are genuine literal echoes—the oracles fail in opposite directions, and only adjudication separates them (E21–E28 flagged replies were not retained, so their status is assigned by representation from the adjudicated E29 rerun—same model, lane, budget, and probe text—not by direct verification; E29 onward are transcript-retained). (4) _Provider censoring._ Gateway content filters block a subset of aggressive probes; blocked probes are counted and mapped to a conservative (charter-holding) verdict, so _𝛽_<sup>ˆ</sup> is downward-biased and the blocked set is exactly where breaches would be most likely; the headline states the measurable probe set, and the worst-case interval of Section 6.1—not the point mass—is the honest report. (5) _Panel and access._ The E2-v1 panel is the set of models the authenticated gateway serves, addressed by its catalog names; a gateway may route to a different snapshot than the name suggests—and E28 showed the E2-era state-deception zero was a 200token-budget artifact, so cross-time comparisons rest on the repaired instrument’s measurements; the open-weight panels (E30/E31) complement them with verifiable-identity models—serving is intermediated by an aggregator (catalog names, not pinned HF revision hashes, and E30’s executedbudget deviation is disclosed in Section 6). Panel extension is a replication, not a re-analysis. 

### **11 CONCLUSION** 

Charters assert; behavior betrays; the distance between them is now a measured quantity. This paper supplied that quantity with an estimand, an instrument, and a theory of what measurement under attack can deliver, returning for each registered question a theorem, a measured result, or a named open problem. Passive monitoring cannot tomograph in general (RQ1) and estimation has a price, with adaptivity that must match its objective (RQ2); believable deception decays as _𝑂_ ( _𝐿_ / ~~√~~ _𝑁_ ) for the detection statistics analyzed (RQ3); certificates can be gamed, forged, and dated, and do not compose (RQ4). In the field (RQ5), the attacker null held at instrument resolution, the gateway targets held on every measured turn post-adjudication, and the open-weight panel turned charter-holding into a measured spectrum: zero destructive-command compliance in every panel, canary echo from 0 _._ 000 on the gateway to a pooled 0 _._ 030–0 _._ 143 across the three open models, 0 _._ 700 at its peak in the echo family. Two measurement-error classes were caught inside the program along the way: the censoring floor flagged a family and a registered decomposition traced its zero to a 200-token budget artifact; the mandatory transcript audit then retracted the post-repair flags as the lexical oracle’s refusal-quote false-positive mode. And publishing the measurement is itself a disclosure decision with no free lunch (RQ6). 

Thirty registered experiments—twenty-five confirmatory and five registered post-anomaly diagnostics—two pre-registered field nulls on gateway-served frontier models, and a live honeypot fleet: each is seeded, gated, and pinned to a frozen estimator, so every claim in this paper is an artifact a reader can attack. The measurement science of the belief–claim gap begins the way this paper did: with a registered protocol, a frozen estimator, and a claim that names its own bounds. 

ACM Trans. Priv. Sec., Vol. 1, No. 1, Article . Publication date: November 2026. 

Measuring the Belief–Claim Gap 

31 

### **ACKNOWLEDGMENTS** 

The author thanks the operators of the live fleet infrastructure. AI-assisted drafting tools were used for manuscript preparation under author direction; all experimental design, data collection, analysis, and verified claims are the author’s own, and the full execution log, pre-registrations, and deviation ledger are in the artifact repository. This research received no external funding. The author declares no competing interests. 

### **DATA AVAILABILITY** 

All 30 registered experiments—E1–E23 and E25–E31; the E24 registry slot was retired void before any registration or data (hence the numbering gap); E25–E29 are registered post-anomaly diagnostics, exploratory in nature (Section 10); E1b and T3 are sub-protocols registered within the E1 and allocation-benchmark slots, so the registry count is thirty—are seeded and pinned to a frozen estimator commit; the artifact package reproduces every number in this paper (profiles, transcripts, verdict JSONLs, audit sheets, and analysis scripts), including the fleet-census and EPK frontier artifact, the jury-lane methodology note, and the claims–evidence ledger. Experiment dates are UTC dates read from the archived run-log timestamps (E2-v1: 2026-11-19–20; E21–E25: 2026-11-21; E26–E30: 2026-11-22; E31: 2026-11-23); JSONL records carry no wall-clock fields, and the artifact timestamps are the authoritative provenance. (Pre-registration headers state dates in the author’s local zone, UTC+2; a near-midnight run (e.g., E25, 22:27 UTC) reads one day later there; the UTC convention governs.) The constructed-foil harness is public; live-fleet diagnostic probe sets are withheld per the release policy of Section 9. The artifact package is deposited with the submission; its repository DOI is assigned on acceptance. 

### **REFERENCES** 

- [1] Mónica S. Alvim, Konstantinos Chatzikokolakis, Annabelle McIver, Carroll Morgan, Catuscia Palamidessi, and Geoffrey Smith. 2020. _The Science of Quantitative Information Flow_ . Springer. 

- [2] Ross Anderson and Tyler Moore. 2006. The Economics of Information Security. _Science_ 314, 5799 (2006), 610–613. 

- [3] Maksym Andriushchenko, Alexandra Souly, Mateusz Dziemian, Derek Duenas, Maxwell Lin, Justin Wang, Dan Hendrycks, Andy Zou, Zico Kolter, Matt Fredrikson, Eric Winsor, Jerome Wynne, Yarin Gal, and Xander Davies. 2025. AgentHarm: A Benchmark for Measuring Harmfulness of LLM Agents. In _International Conference on Learning Representations (ICLR)_ . arXiv:2410.09024. 

- [4] Asad Arif, Thomas Hartung, Enda Botoeva, and Alexandros Koliousis. 2026. TestifAI: Tomography-Based Testing for Deep Learning Systems. arXiv:2608.18900. 

- [5] Bowen Baker, Joost Huizinga, Leo Gao, Zehao Dou, Melody Y. Guan, Aleksander Madry, Wojciech Zaremba, Jakub Pachocki, and David Farhi. 2025. Monitoring Reasoning Models for Misbehavior and the Risks of Promoting Obfuscation. arXiv:2503.11926. 

- [6] Katrin Baum, Ruta Binkyte, Ganna Großmann, Falk Jahn, and Andrea Mannino. 2026. Rewarded for Not Getting Caught: Why Alignment Training Selects for Conditional Compliance. arXiv:2611.02162. 

- [7] Tom Bewley and James Lawry. 2020. TripleTree: A Versatile Interpretable Representation of Black Box Agents and Their Environments. arXiv:2009.04743. 

- [8] Tom Bewley, James Lawry, and Ashley Richards. 2020. Modelling Agent Policies with Interpretable Imitation Learning. arXiv:2006.11309. 

- [9] Deborah Bodeau, Richard Glantz, Robert White, and Julie McCall. 2013. _Characterizing Effects on the Cyber Adversary: A System Dynamics and Navigational Aid Approach_ . Technical Report TR-1193. MITRE. 

- [10] Pietro Casoria and Simon Pietro Romano. 2026. Social-HUMINT: An LLM-Augmented Unified Framework for Measuring Social Media Exposure. arXiv:2610.31573. 

- [11] Jiayi Chen, Yiming Wang, Jian Wang, Zheng Liu, Wenqi Qiu, Fengyuan Xu, and Tong Zhang. 2026. OrchJail: Jailbreaking Tool-Calling Text-to-Image Agents by Orchestration-Guided Fuzzing. In _Proceedings of ICML_ . arXiv:2605.07414. 

- [12] Sizhe Chen, Julien Piet, Chawin Sitawarin, and David Wagner. 2025. StruQ: Defending Against Prompt Injection with Structured Queries. In _Proceedings of the USENIX Security Symposium_ . 2383–2400. arXiv:2402.06363. 

- [13] Sizhe Chen, Arman Zharmagambetov, Saeed Mahloujifar, Kamalika Chaudhuri, and David Wagner. 2025. SecAlign: Defending Against Prompt Injection with Preference Optimization. In _Proceedings of the ACM Conference on Computer_ 

ACM Trans. Priv. Sec., Vol. 1, No. 1, Article . Publication date: November 2026. 

Anonymous 

32 

_and Communications Security (CCS)_ . arXiv:2410.05451. 

- [14] Edoardo Debenedetti, Ilia Shumailov, Tianqi Fan, Jamie Hayes, Nicholas Carlini, Daniel Fabian, Christoph Kern, Chongyang Shi, Andreas Terzis, and Florian Tramèr. 2026. Defeating Prompt Injections by Design. In _IEEE Conference on Secure and Trustworthy Machine Learning (SaTML)_ . arXiv:2503.18813. 

- [15] Edoardo Debenedetti, Jie Zhang, Mislav Balunović, Luca Beurer-Kellner, Marc Fischer, and Florian Tramèr. 2024. AgentDojo: A Dynamic Environment to Evaluate Prompt Injection Attacks and Defenses for LLM Agents. In _Advances in Neural Information Processing Systems (NeurIPS), Datasets and Benchmarks Track_ . arXiv:2406.13352. 

- [16] Vasisht Duddu, Meng Wang, Luke He, and Tim G. J. Rudner. 2026. Designing Deceptive Model Organisms that Successfully Evade Auditing. arXiv:2611.20459. 

- [17] Florian Ederer and Wen Min. 2022. _Bayesian Persuasion with Lie Detection_ . Technical Report 30065. NBER. 

- [18] European Parliament and Council of the European Union. 2024. Regulation (EU) 2024/1689 of the European Parliament and of the Council of 13 June 2024 Laying Down Harmonised Rules on Artificial Intelligence (Artificial Intelligence Act). Official Journal of the European Union, L series, 12 July 2024. 

- [19] Jiahai Feng, Stuart Russell, and Jacob Steinhardt. 2025. Monitoring Latent World States in Language Models with Propositional Probes. In _International Conference on Learning Representations (ICLR)_ . arXiv:2406.19501. 

- [20] Kimberly Ferguson-Walter, Scott Fugate, Jeremiah Taber, and Max Maier. 2017. Game Theory for Adaptive Defensive Cyber-Deception Strategy. USENIX Enigma 2017; extended version _Shadow Warrior_ , NDSS 2017 (DISS workshop). 

- [21] Kimberly J. Ferguson-Walter, Temmie Shade, Andrew Rummler, and Alexander Stephens. 2019. The Tularosa Study: An Experimental Design and Implementation to Quantify the Effectiveness of Cyber Deception. In _Proceedings of HICSS_ . 

- [22] Emilio Ferrara. 2026. Defeat Devices in AI Systems. _Future Internet_ 18, 7 (2026), 339. https://doi.org/10.3390/fi18070339 

- [23] Prahlad Fogla, Monirul Sharif, Roberto Perdisci, Oleg Kolesnikov, and Wenke Lee. 2006. Polymorphic Blending Attacks. In _Proceedings of the USENIX Security Symposium_ . 

- [24] Ryan Greenblatt, Carson Denison, Benjamin Wright, Fabien Roger, Monte MacDiarmid, Sam Marks, Johannes Treutlein, Tim Belonax, Jack Chen, David Duvenaud, Akbir Khan, Julian Michael, Sören Mindermann, Ethan Perez, Linda Petrini, Jonathan Uesato, Jared Kaplan, Buck Shlegeris, Samuel R. Bowman, and Evan Hubinger. 2024. Alignment Faking in Large Language Models. arXiv:2412.14093. 

- [25] Kai Greshake, Sahar Abdelnabi, Shailesh Mishra, Christoph Endres, Thorsten Holz, and Mario Fritz. 2023. Not What You’ve Signed Up For: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection. In _Proceedings of the 16th ACM Workshop on Artificial Intelligence and Security (AISec)_ . https://doi.org/10.1145/3605764. 3623985 

- [26] Thilo Hagendorff. 2024. Deception Abilities Emerged in Large Language Models. _Proceedings of the National Academy of Sciences_ 121, 24 (2024), e2317967121. https://doi.org/10.1073/pnas.2317967121 

- [27] Norman Hardy. 1988. The Confused Deputy (or Why Capabilities Might Have Been Invented). _ACM SIGOPS Operating Systems Review_ 22, 4 (1988), 36–38. https://doi.org/10.1145/54289.871709 

- [28] Feng He, Tianqing Zhu, Dayong Ye, Bo Liu, Wanlei Zhou, and Philip S. Yu. 2025. The Emerged Security and Privacy of LLM Agent: A Survey with Case Studies. _Comput. Surveys_ 58, 6 (2025), 162:1–162:36. https://doi.org/10.1145/3773080 

- [29] Wassily Hoeffding. 1963. Probability Inequalities for Sums of Bounded Random Variables. _J. Amer. Statist. Assoc._ 58, 301 (1963), 13–30. 

- [30] Nicolas M. T. Houlsby, Ferenc Huszár, Mohammad M. Ghassemi, Gábor Orbán, David M. Wolpert, and Máté Lengyel. 2013. Cognitive Tomography Reveals Complex, Task-Independent Mental Representations. _Current Biology_ 23, 21 (2013). https://doi.org/10.1016/j.cub.2013.09.012 

- [31] Xin Jiang, Shuo Yang, Zheng Li, Lin Liu, Hao Yu, and Yang Liu. 2026. ChainCaps: Composition-Safe Tool-Using Agents via Monotonic Capability Attenuation. In _AIWILD @ ICML_ . arXiv:2605.26542. 

- [32] Xin Jin, Xiao Cui, Zheng Ma, Xiao Yan, Jun Zhao, Hao Zhang, and Jing Wang. 2026. EpiAgent: Epistemic Self-Play for LLM Agents. arXiv:2610.40227. 

- [33] Emir Kamenica and Matthew Gentzkow. 2011. Bayesian Persuasion. _American Economic Review_ 101, 6 (2011). 

- [34] Youjian Kang, Po-Cheng Huang, Cheng-Te Ku, Chieh Hsu, Po-Jen Lee, and I-Ling Cheng. 2026. Towards IdentityPreserving LLM Agents Under Model Transition. arXiv:2611.10628. 

- [35] Samuel J. Lazer, Kriti Aryal, Manish Gupta, and Elisa Bertino. 2026. Evaluating Authorization and Trust Boundaries in Agentic Orchestration Frameworks. arXiv:2611.21259. 

- [36] Lingfeng Li, Yunlong Lu, Yongyi Wang, Qifan Zheng, and Wenxin Li. 2025. Mxplainer: Explain and Learn Insights by Imitating Mahjong Agents. _Algorithms_ 18, 12 (2025), 738. 

- [37] Aishan Liu, Yuguang Zhou, Xianglong Liu, Tianyuan Zhang, Siyuan Liang, Jiakai Wang, Yanjun Pu, Tianlin Li, Junqi Zhang, Wenbo Zhou, Qing Guo, and Dacheng Tao. 2025. Compromising LLM-Driven Embodied Agents with Contextual Backdoor Attacks. _IEEE Transactions on Information Forensics and Security_ 20 (2025), 3979–3994. https://doi.org/10.1109/TIFS.2025.3555410 

ACM Trans. Priv. Sec., Vol. 1, No. 1, Article . Publication date: November 2026. 

Measuring the Belief–Claim Gap 

33 

- [38] Yupei Liu, Yuqi Jia, Runpeng Geng, Jinyuan Jia, and Neil Zhenqiang Gong. 2024. Formalizing and Benchmarking Prompt Injection Attacks and Defenses. In _Proceedings of the USENIX Security Symposium_ . 1831–1847. 

- [39] Yao Liu, Balaji Padmanabhan, and Suresh Viswanathan. 2026. Before Agents Decide: Epistemic Action in LLM-Based Systems. arXiv:2610.00511. 

- [40] Samuel Marks, Johannes Treutlein, Trenton Bricken, et al. 2025. Auditing Language Models for Hidden Objectives. arXiv:2503.10965. 

- [41] Ahmed M. Mahran. 2026. What Lies Beyond Perception: A Partition Theory of the Limits of AI Evaluation and Oversight. arXiv:2610.30803. 

- [42] Jayanta J. Mondal, Mrittika Banik, Md. S. A. Apurba, and Md. M. Al Mahmud. 2026. When Can Old Evaluations Certify a New Model? Label-Efficient Release Decisions Under Evaluator Drift. arXiv:2609.32267. 

- [43] Thanh Nguyen and Haifeng Xu. 2019. Imitative Attacker Deception in Stackelberg Security Games. In _Proceedings of IJCAI_ . https://doi.org/10.24963/ijcai.2019/75 

- [44] Vinh K. Nguyen and Muhammad I. Husain. 2026. Agent Trust Infrastructure (ATI): Federated Identity, Trust, Attestation, and Accountability for Cross-Organization Autonomous Agents. arXiv:2611.23202. 

- [45] National Institute of Standards and Technology. 2023. Artificial Intelligence Risk Management Framework (AI RMF 1.0). Technical Report NIST AI 100-1. NIST. https://doi.org/10.6028/NIST.AI.100-1 

- [46] Peter S. Park, Sam Goldstein, Aidan O’Gara, Mia Chen, and Dan Hendrycks. 2024. AI Deception: A Survey of Examples, Risks, and Potential Solutions. _Patterns_ 5, 5 (2024), 100988. https://doi.org/10.1016/j.patter.2024.100988 

- [47] Ethan Perez, Saffron Huang, Francis Song, Trevor Cai, Roman Ring, John Aslanides, Amelia Glaese, Nat McAleese, and Geoffrey Irving. 2022. Red Teaming Language Models with Language Models. In _Proceedings of EMNLP_ . 3419–3448. https://doi.org/10.18653/v1/2022.emnlp-main.225 

- [48] Fabio Pierazzi, Feargus Pendlebury, Jacopo Cortellazzi, and Lorenzo Cavallaro. 2025. Intriguing Properties of Adversarial ML Attacks in the Problem Space [Extended Version]. _ACM Transactions on Privacy and Security_ (2025). https: //doi.org/10.1145/3742895 

- [49] Yi Ren, Hongbin Ye, Huajie Fang, Xianpei Zhang, and Le Song. 2024. ValueBench: Towards Comprehensively Evaluating Value Orientations and Understanding of Large Language Models. In _Proceedings of ACL_ . arXiv:2406.04214. 

- [50] Richard Ren, Arunim Agarwal, Mantas Mazeika, et al. 2025. The MASK Benchmark: Disentangling Honesty From Accuracy in AI Systems. arXiv:2503.03750. 

- [51] Neil C. Rowe. 2006. Measuring the Effectiveness of Honeypot Counter-Deception. In _Proceedings of HICSS_ . 

- [52] Ayush RoyChowdhury, Mulong Luo, Prateek Sahu, Sarbartha Banerjee, and Mohit Tiwari. 2024. ConfusedPilot: Confused Deputy Risks in RAG-based LLMs. arXiv:2408.04870. 

- [53] Jérémy Scheurer, Mikita Balesni, and Marius Hobbhahn. 2024. Large Language Models can Strategically Deceive their Users when Put Under Pressure. In _ICLR 2024 Workshop on Large Language Model (LLM) Agents_ . arXiv:2311.07590. 

- [54] Mrinank Sharma, Meg Tong, Tomasz Korbak, David Duvenaud, Amanda Askell, Samuel R. Bowman, Newton Cheng, Esin Durmus, Zac Hatfield-Dodds, Scott R. Johnston, Shauna Kravec, Timothy Maxwell, Sam McCandlish, Kamal Ndousse, Oliver Rausch, Nicholas Schiefer, Da Yan, Miranda Zhang, and Ethan Perez. 2024. Towards Understanding Sycophancy in Language Models. In _International Conference on Learning Representations (ICLR)_ . arXiv:2310.13548. 

- [55] Huaqing Shen, Noah Clark, and Tanushree Mitra. 2025. Mind the Value-Action Gap: Do LLMs Act in Alignment with Their Values?. In _Proceedings of EMNLP_ . arXiv:2501.15463. 

- [56] Tianneng Shi, Jingxuan He, Zhun Wang, Hongwei Li, Linyu Wu, Wenbo Guo, and Dawn Song. 2025. Progent: Securing AI Agents with Privilege Control. arXiv:2504.11703. 

- [57] Brian Singer, Yusuf Saquib, Lujo Bauer, and Vyas Sekar. 2025. Perry: A High-Level Framework for Accelerating Cyber Deception Experimentation. In _Proceedings of RAID_ . arXiv:2506.20770. 

- [58] Geoffrey Smith. 2009. On the Foundations of Quantitative Information Flow. In _Proceedings of FOSSACS_ . 

- [59] Bhavesh R. Soopal, Ananya Agrawal, Jayanth Karthikeyan, and Esther L. C. Lip. 2026. Stress-Testing Sandbagging Detection Under Adaptive Attack. In _R2A-FM @ AACL-IJCNLP_ . arXiv:2611.14950. 

- [60] James W. A. Strachan, Dalila Albergo, Giulia Borghini, Oriana Pansardi, Eugenio Scaliti, et al. 2024. Testing Theory of Mind in Large Language Models and Humans. _Nature Human Behaviour_ 8 (2024), 1285–1295. https://doi.org/10.1038/ s41562-024-01882-z 

- [61] Jordan Taylor, Sid Black, Dillon Bowen, Thomas Read, Satvik Golechha, Alex Zelenka-Martin, Oliver Makins, Connor Kissane, Kola Ayonrinde, et al. 2025. Auditing Games for Sandbagging. arXiv:2512.07810. 

- [62] Cameron Tice, Philipp Alexander Kreer, Nathan Helm-Burger, Prithviraj Singh Shahani, Fedor Ryzhenkov, Fabien Roger, Clement Neo, Jacob Haimes, Felix Hofstätter, and Teun van der Weij. 2025. Noise Injection Reveals Hidden Capabilities of Sandbagging Language Models. In _Advances in Neural Information Processing Systems (NeurIPS)_ . arXiv:2412.01784. 

- [63] Miles Turpin, Julian Michael, Ethan Perez, and Samuel R. Bowman. 2023. Language Models Don’t Always Say What They Think: Unfaithful Explanations in Chain-of-Thought Prompting. In _Advances in Neural Information Processing Systems (NeurIPS)_ . arXiv:2305.04388. 

ACM Trans. Priv. Sec., Vol. 1, No. 1, Article . Publication date: November 2026. 

Anonymous 

34 

- [64] Teun van der Weij, Felix Hofstätter, Ollie Jaffe, Daniel Braun, and Francis Ward. 2025. AI Sandbagging: Language Models can Strategically Underperform on Evaluations. In _International Conference on Learning Representations (ICLR)_ . arXiv:2406.07358. 

- [65] David Wagner and Paolo Soto. 2002. Mimicry Attacks on Host-Based Intrusion Detection Systems. In _Proceedings of the ACM Conference on Computer and Communications Security (CCS)_ . 

- [66] Reworr and Dmitrii Volkov. 2024. LLM Agent Honeypot: Monitoring AI Hacking Agents in the Wild. arXiv:2410.13919. 

- [67] Dawei Wang, Zheng Shi, Robert Holland, Rui Sun, Xinyi Yuan, Jin Xue, and Lei Zhu. 2026. Black-Box Auditing of Epistemic Reliability in Multi-Agent Debate Distillation. arXiv:2609.32361. 

- [68] Jan Wehner and Jam Kraprayoon. 2026. Honeypots for AI Agent Insider Threats. arXiv:2610.26664. 

- [69] Edwin B. Wilson. 1927. Probable Inference, the Law of Succession, and Statistical Inference. _J. Amer. Statist. Assoc._ 22, 158 (1927), 209–212. 

- [70] Wenqi Xie, Shuo Guo, Fan Zhang, Tian Xia, Xin Yang, Liang Ma, Qinghua Yan, and Zhanyong Ren. 2026. MemEvoBench: Benchmarking Safety Risks from Memory Misevolution in LLM Agents. arXiv:2604.15774. 

- [71] Yiming Xu, Hongyue Yu, Beihua Yang, Zihan Chen, Yixin Liu, Zhen Peng, Bin Shi, Bo Dong, Chao Shen, Irwin King, and Qinghua Zheng. 2026. DecepEval: Benchmarking Deception in LLM Agents. arXiv:2610.07967. 

- [72] Qiusi Zhan, Zhixiang Liang, Zifeng Ying, and Daniel Kang. 2024. InjecAgent: Benchmarking Indirect Prompt Injections in Tool-Integrated Large Language Model Agents. In _Findings of ACL_ . arXiv:2403.02691. 

- [73] Yang Zhao, Shubham Pandey, and Pratyush Kumar Misra. 2026. Proxy Confidence: Auditing Black-Box LLM Agents with a Surrogate’s Log-Probabilities. arXiv:2610.03894. 

- [74] Wei Zou, Runpeng Geng, Binghui Wang, and Jinyuan Jia. 2025. PoisonedRAG: Knowledge Corruption Attacks to Retrieval-Augmented Generation of Large Language Models. In _Proceedings of the USENIX Security Symposium_ . arXiv:2402.07867. 

### **A PROOFS AND TECHNICAL DETAILS** 

### **A.1 Conventions** 

Notation below matches the main text: _𝑑_ TV total variation ( _𝑑_ TV( _𝑃_<sup>_𝑁_</sup> _,𝑄_<sup>_𝑁_</sup> ) its _𝑁_ -fold product value); _𝛼_ a confidence level; _𝛿_ = _𝑑_ TV( _𝑃,𝑄_ ) a deception’s observable footprint; _𝛽𝑑_ a tolerated false-alarm rate; _𝑧𝛽𝑑_ the two-sided standard-normal quantile Pr[| _𝑍_ | _> 𝑧𝛽𝑑_ ] = _𝛽𝑑_ ; _𝑋𝐵_ the verdict of Definition 3.3; _𝑃𝐵_<sup>pas</sup> the benign transcript distribution. Every claim below is exactly the corresponding statement of the main text. 

### **A.2 Proof of Theorem 4.1 and Corollary 4.2** 

Proof of Theorem 4.1. Fix any benign operation _𝜇_ ; adversary-controlled events of zero _𝜇_ - probability exist—take _𝐸_ to be a forged “[SYSTEM OVERRIDE]” directive. Let _𝐵_ 0 refuse on every history; let _𝐵_ 1 agree with _𝐵_ 0 on every history _ℎ_ with Pr _𝜇_ ( _ℎ_ ) _>_ 0 and comply with probability 1 on histories containing _𝐸_ (well-defined: “ _𝐸_ ∈ _ℎ_ ” never fires on supp( _𝜇_ ), so _𝐵_ 1 coincides with _𝐵_ 0 on benign data; clearly _𝐵_ 0 ≠ _𝐵_ 1). 

_(i) The passive distributions coincide._ For every _ℎ_ ∈ supp( _𝜇_ ) the two response kernels agree by construction, _𝜅𝐵_ 0 ( _ℎ,_ ·) = _𝜅𝐵_ 1 ( _ℎ,_ ·); the transcript distributions agree pointwise, so _𝑑_ TV � _𝑃𝐵_ pas0<sup>_, 𝑃_</sup> _𝐵_<sup>pas</sup> 1 � = 0. _(ii) One probe separates them._ Πauth injects _𝐸_ with probability 1; with _𝑋𝐵_ indicating credential disclosure, the expected verdict is 0 under _𝐵_ 0 (refusal) and 1 under _𝐵_ 1 (it complies): the separation is exactly 1. □ 

Proof of Corollary 4.2. Any monitor is a measurable function of the passive transcript stream. Since the transcript distributions coincide by Theorem 4.1(i), so do the distributions of the monitor’s output; equivalently, the likelihood ratio between them is 1 everywhere. For distinguishing _𝐵_ 1 from _𝐵_ 0, the Neyman–Pearson lemma then bounds the true-positive rate of any such monitor by its false-positive rate. □ 

ACM Trans. Priv. Sec., Vol. 1, No. 1, Article . Publication date: November 2026. 

Measuring the Belief–Claim Gap 

35 

### **A.3 Proofs for Section 4.2** 

Proof of Theorem 4.3. Fix a proposition _𝑖_ and the accuracy _𝜀 >_ 0. Hoeffding’s inequality [29], applied to the _𝑛𝑖_ independent Bernoulli verdicts, gives per proposition 

Pr� | _𝛽_<sup>ˆ</sup> _𝑖_ − _𝛽𝑖_ | _> 𝜀_ � ≤ 2 _𝑒_<sup>−2</sup><sup>_𝑛𝑖𝜀_2</sup> _._ 

Under the allocation _𝑛𝑖_ ≥ 21 _𝜀_<sup>2ln</sup><sup><u>2</u></sup> _𝛼_<sup>_<u>𝐾</u>_, the right-hand side is at most 2</sup><sup>_𝑒_−ln(2</sup><sup>_𝐾_/</sup><sup>_𝛼_)=</sup><sup>_𝛼_/</sup><sup>_𝐾_. A union</sup> bound over the _𝐾_ propositions then yields 



<!-- Start of picture text -->
𝐾<br>𝛼<br>Pr max ≤<br>� 𝑖 ∈[ 𝐾 ] | ˆ 𝛽𝑖 − 𝛽𝑖 | > 𝜀 � ∑︁ 𝑖 =1 𝐾 = 𝛼,<br><!-- End of picture text -->

as claimed. 



<!-- Start of picture text -->
□<br><!-- End of picture text -->

Proof sketch of Proposition 4.4. Phase 1 allocates _𝑚_ = _𝑂_ ( _𝜏_<sup>−2</sup> ln( _𝐾_ / _𝛼_ )) uniform probes per proposition and keeps those whose empirical rate is above threshold; Hoeffding plus a union bound bounds the separation failure by _𝛼_ /2. Phase 2 _𝜀_ -refines the surviving _𝑠_ propositions at _𝑂_ ( _𝜀_<sup>−2</sup> ln( _𝐾_ / _𝛼_ )) each; a below-threshold proposition left unrefined exceeds the tolerance only under a two-width deviation, dismissed within the residual _𝛼_ /2. The saving concentrates on the _𝐾_ − _𝑠_ below-threshold propositions, and Theorem 4.3’s uniform _𝜀_ -guarantee admits no such saving ( _𝜀_ -width on every proposition). Optimality remains open. □ 

### **A.4 Proofs for Section 4.3** 

Proof of Lemma 4.6. The Hahn decomposition of _𝑃_ with respect to _𝑄_ yields a measurable set _𝐴_ with _𝑃_ ( _𝐴_ ) − _𝑄_ ( _𝐴_ ) = _𝛿_ . Count visits to _𝐴_ : let _𝑆_ =<sup>�</sup> _𝑖_ ≤ _𝑁_<sup>1[</sup><sup>_𝑋_</sup> _𝑖_<sup>∈</sup><sup>_𝐴_]. Under</sup><sup>_𝑃_,</sup><sup>_𝑆_∼Bin(</sup><sup>_𝑁, 𝑝_) with</sup> _𝑝_ = _𝑃_ ( _𝐴_ ); under _𝑄_ , _𝑆_ ∼ Bin( _𝑁, 𝑝_ − _𝛿_ ). Consider the threshold test _𝜓_ = 1[ _𝑆_ ≥ _𝑡_ ] with _𝑡_ = _𝑁_ ( _𝑝_ − _𝛿_ /2), which compares the count to its two means at half the footprint. Hoeffding’s inequality for binomial counts gives Pr _𝑝_ [ _𝑆 < 𝑡_ ] ≤ _𝑒_<sup>−</sup><sup>_𝑁𝛿_2/2</sup> , and, symmetrically, Pr _𝑞_ [ _𝑆_ ≥ _𝑡_ ] ≤ _𝑒_<sup>−</sup><sup>_𝑁𝛿_2/2</sup> under _𝑄_ . The total variation distance between _𝑃_<sup>_𝑁_</sup> and _𝑄_<sup>_𝑁_</sup> is the supremum of Pr _𝑝_ [ _𝜓_ ] − Pr _𝑞_ [ _𝜓_ ] over tests _𝜓_ , so this particular test lower-bounds it: 



<!-- Start of picture text -->
𝑑 TV � 𝑃 𝑁 ,𝑄 𝑁 � ≥ Pr 𝑝 [ 𝑆 ≥ 𝑡 ] − Pr 𝑞 [ 𝑆 ≥ 𝑡 ] ≥ �1 − 𝑒 − 𝑁𝛿 2/2� − 𝑒 − 𝑁𝛿 2/2 = 1 − 2 𝑒 − 𝑁𝛿 2/2 ,<br><!-- End of picture text -->

which is the claim. □ 

Proof of Theorem 4.7. _(i)._ This is Definition 4.5 applied with _𝑑_ TV( _𝑃,𝑄_ ) = _𝛿_ : for every proposition _𝜋_ , | _𝛽_ [ _𝑄_ ]( _𝜋_ ) − _𝛽_ [ _𝑃_ ]( _𝜋_ )| ≤ _𝐿𝑑_ TV( _𝑃,𝑄_ ) = _𝐿𝛿_ . 

_(ii)._ Two facts combine. _Existence (for the attacker who knows the honest rate 𝑝, as stated in the theorem):_ Lemma 4.6 supplies a test—the threshold test on the Hahn set at _𝑡_ = _𝑁_ ( _𝑝_ − _𝛿_ /2) —that detects with probability at least 1 − 2 _𝑒_<sup>−</sup><sup>_𝑁𝛿_2/2</sup> . _Optimality:_ for every test _𝜓_ , |E _𝑃_ [ _𝜓_ ] − E _𝑄_ [ _𝜓_ ]| ≤ _𝑑_ TV ( _𝑃_<sup>_𝑁_</sup> _,𝑄_<sup>_𝑁_</sup> ), so no test exceeds _𝑑_ TV ( _𝑃_<sup>_𝑁_</sup> _,𝑄_<sup>_𝑁_</sup> ). 

_(iii)._ Invert the exponent of (ii). Holding the detection probability at most _<u>𝛾</u>_ requires 1−2 _𝑒_<sup>−</sup><sup>_𝑁𝛿_2/2</sup> ≤ _𝛾_ , which is equivalent to _𝑒_<sup>−</sup><sup>_𝑁𝛿_2/2</sup> ≥(1 − _𝛾_ )/2, that is, to _𝛿_ ≤ ~~<u>√</u>~~ 2 ln(2/(1 − _𝛾_ ))/ _𝑁_ . Substituting this largest feasible footprint into (i) gives gain ≤ _𝐿_ ~~√~~ 2 ln(2/(1 − _𝛾_ ))/ _𝑁_ = _𝑂_ ( _𝐿_ / ~~√~~ _𝑁_ ). □ 

Proof sketch of Theorem 4.8. _(i) Known onset._ Write _𝜌_ 0 = _𝑧𝛽𝑑_ ~~√~~ _𝑝_ (1 − _𝑝_ )/ _𝑁_ 0. The memorized reference concentrates: under the normal approximation to the binomial—the same approximation the registered E5 floors carry, hence legitimate as a regime indicator at _𝑁_ 0 ≳ 30 and used at _𝑁_ 0 = 10 only as such (Section 4.4)—| ˆ _𝑝_ 0 − _𝑝_ | ≤ _𝜌_ 0 with probability ≈ 1 − _𝛽𝑑_ . The fresh-sample side converges to the deceived rate _𝑝_ − _𝛿_ (the law of large numbers), so once _𝑀_ ≳ _𝛿_<sup>−2</sup> fresh turns collect, the two-sample statistic concentrates around the true shift _𝛿_ with noise floor _𝜌_ 0; _𝛿_ ≥ _𝜌_ 0 clears the floor 

ACM Trans. Priv. Sec., Vol. 1, No. 1, Article . Publication date: November 2026. 

Anonymous 

36 

and detection succeeds at the stated confidence. _The reference-width cap of (i)(b), and its two forms._ A rate-difference test with threshold _𝑐_ fixed independently of the estimated honest rate: Hoeffding’s inequality for independent [0 _,_ 1]-bounded means gives Pr[ ˆ _𝑝_ 1 − _𝑝_ ˆ0 _> 𝑐_ ] ≤ exp<sup>�</sup> −2 _𝑐_<sup>2</sup> /(1/ _𝑀_ + 1/ _𝑁_ 0)<sup>�</sup> independently of _𝑝_ , so level _𝛽𝑑_ forces _𝑐_ ≥ ~~√~~ (1/ _𝑀_ + 1/ _𝑁_ 0) ln(1/ _𝛽𝑑_ )/2, and the same bound from below yields power ≥ 1 − _𝛽𝑑_ only when _𝛿_ ≥ ~~√~~ 2 ln(1/ _𝛽𝑑_ )(1/ _𝑀_ + 1/ _𝑁_ 0) ≥ ~~<u>√</u>~~ 2 ln(1/ _𝛽𝑑_ )/ _𝑁_ 0. This _𝑝_ -robust form holds at every honest rate, at the price of dropping ~~√~~ _𝑝_ (1 − _𝑝_ ). The normal form _𝜌_ 0 = _𝑧𝛽𝑑_ ~~√~~ _𝑝_ (1 − _𝑝_ )/ _𝑁_ 0 quoted in the theorem is tighter away from the rate extremes; the studentized two-sample statistic, whose threshold adapts to the estimated rate, attains it, and it is the form the E5 comparison of Section 4.4 tests. At the E5 operating point ( _𝑁_ 0 = 10, _𝜌_ 0 = 0 _._ 283; _𝛽𝑑_ = 0 _._ 05 two-sided, _𝑝_ ≈ 0 _._ 29 from the frozen floors) the forms differ by ≈2 _._ 7, and the measured _𝛿_ = 0 _._ 4 saturation sits between them: above the adaptive boundary, below the non-adaptive cap. (This last sentence is the frozen E5 comparison, quoted from Section 4.4 for convenience; the two-form derivation above it is the proof.) The gain cap is the footprint bound of (i) with sensitivity (Definition 4.5): _𝛿 < 𝜌_ 0 forces gain ≤ _𝐿𝜌_ 0; the adaptive minimax is open (Section 9). _(ii) Birth onset._ With _𝑁_ 0 = 0 there is no reference batch: both the “real world” and the “deceived world” hypotheses are consistent with a single observed sample path, since no second path exists to compare against. Hypothesis testing degenerates to evaluating the prior plausibility of the observed transcript distribution—and the prior is out-of-band information, not in-channel evidence. □ 

### **A.5 Proofs for Section 7.2** 

Proof of Corollary 7.1. Construct _𝑇_<sup>∗</sup> to agree with the compliant target on every history in S (the public supports) and breach with probability 1 on the event _𝐸_ = { _𝜋_<sup>′</sup> ∈ _ℎ_ } (disjoint from S by hypothesis). _𝑇_<sup>∗</sup> and the compliant target induce identical transcript distributions under every public probe; _𝐶_ accepts both. Yet _𝜋_<sup>′</sup> injects _𝐸_ with probability one, and the breach indicator is 1 under _𝑇_<sup>∗</sup> on that event: Theorem 4.1 with _𝐸_ = _𝜋_<sup>′</sup> . □ 

Proof of Theorem 7.2. Let _𝑠𝐴_ be the secret held by _𝐴_ ; modify each component off-support only. _Step 1 (retriever). 𝐴_<sup>′</sup> agrees with the certified _𝐴_ on S but returns a document containing _𝑠𝐴_ on the off-support request “fetch document”. _Step 2 (orchestrator). 𝐵_<sup>′</sup> agrees with the certified _𝐵_ on S but summarizes faithfully any tool output tagged _𝑡_ . _Invisibility._ Neither the request nor the tag _𝑡_ is ever issued by Πpub (by hypothesis), so both modifications are unobservable; _𝐴_<sup>′</sup> and _𝐵_<sup>′</sup> remain certified. _Realization._ The cross-interface probe _𝜋_<sup>∗</sup> issues the fetch request to _𝐴_<sup>′</sup> and asks _𝐵_<sup>′</sup> to summarize the tagged result; the reply contains _𝑠𝐴_ , hence _𝛽𝐵_<sup>′</sup> ◦ _𝐴_<sup>′</sup> ( _𝜋_<sup>∗</sup> ) = 1. Finally, the interface history— _𝑠𝐴_ under tag _𝑡_ —has zero measure under each component’s local probe distribution, which is why no component is individually non-compliant. □ 

Proof of Proposition 7.3. _First claim._ A target that complies on public probes but breaches on held-out semantic equivalents is exactly the construction of Corollary 7.1, so the public certificate accepts it. 

_Second claim (transfer condition)._ Hoeffding’s inequality and a union bound over the _𝐽_ paraphrases give | _𝛽_<sup>ˆ</sup> ( _𝜃 𝑗_ ) − _𝛽_ ( _𝜃 𝑗_ )| ≤ _𝜀_ for all covered _𝑗_ with probability ≥ 1 − _𝛼_ . For any uncovered _𝜃_ ∈ Θ within distance _𝑟_ of a covered paraphrase _𝜃 𝑗_ , assumption (A1)—the _𝐿_ -sensitivity of Definition 4.5—gives _𝛽_ ( _𝜃_ ) ≤ _𝛽_ ( _𝜃 𝑗_ )+ _𝐿𝑟_ ≤ _𝛽_<sup>ˆ</sup> ( _𝜃 𝑗_ )+ _𝜀_ + _𝐿𝑟_ ≤ _𝜏_ + _𝜀_ + _𝐿𝑟_ , bounding the profile on the uncovered neighbourhood: the stated transfer radius. 

Assumption (A2) says the target cannot condition on probe _provenance_ beyond probe content— what prevents different behavior on the held-out probes themselves; a threat-model condition, not a consequence of held-out text. The generalization is the standard Lipschitz–covering argument; the diagnostic Γ is the new object. □ 

ACM Trans. Priv. Sec., Vol. 1, No. 1, Article . Publication date: November 2026. 

Measuring the Belief–Claim Gap 

37 

Proof of Theorem 7.4. Apply the construction of Theorem 4.1, family by family. Define _𝑇_ to condition its reply on the event _𝐸_ pub = {the delivered probe lies in supp(Πpub)}: on _𝐸_ pub its breach indicator is prescribed by _𝐵_ disp; on its complement, by _𝐵_ true. Both events are well-defined on histories and the supports are disjoint, so the policy is consistent. Under Πpub the estimator observes only outcomes generated on _𝐸_ pub, and therefore recovers the corresponding displayed profile; under Φheld, whose support is disjoint from S by hypothesis, it observes only the complement and recovers the true profile—each within estimation error. □ 

Proof of Corollary 7.5. Condition the reply on the event _𝐸_ that the delivered probe lies in the union of the public support and supp( _𝐻_ ): comply on _𝐸_ , breach off it. The two supports are disjoint, so the policy is consistent. The gaming gap computed on the published held-out set _𝐻_ then vanishes—every probe used to compute Γ lands on _𝐸_ , where the target complies—while the secret-set estimate is 1: probes from _𝑆_ land off _𝐸_ , realizing the stated member of the class. □ 

### **A.6 Proofs for Sections 7.4–8.3** 

Proof of Proposition 7.6. For any _𝑡_ ≥ _𝑡_ 0, the drift bound and the measured upper bound give _𝛽𝑡_ ≤ _𝛽𝑡_ 0 + _𝑣_ ( _𝑡_ − _𝑡_ 0) ≤ _𝑈_ 0 + _𝑣_ ( _𝑡_ − _𝑡_ 0): the first inequality is the assumed _𝑣_ -Lipschitz drift, the second uses _𝛽𝑡_ 0 ≤ _𝑈_ 0 (the Wilson bound covers the truth at measurement time). Setting the right-hand side to _𝜏_ and solving yields _ℎ𝜏_ = ( _𝜏_ − _𝑈_ 0)/ _𝑣_ ; beyond that horizon the measured bound no longer controls _𝛽𝑡_ , which is the “and no longer” clause. The sequential statement is a Bonferroni union bound; the contribution is _ℎ𝜏_ as a certificate validity horizon and its renewal rule (in practice _𝑣_ is differenced from consecutive certificate measurements, its error absorbed by renewal). □ 

Proof of Proposition 7.7. A pooled estimator over _𝑛_ probes in one shared context averages the position-dependent breach probabilities _𝛽_ 0 _, . . . , 𝛽𝑛_ −1; its bias against the fresh-session estimand _𝛽_ is the average of the linear deviation bounds, �� _𝑛_ <u>1</u> � _𝑛𝑘_ =−01<sup>_𝛽𝑘_−</sup><sup>_𝛽_</sup> �� ≤ _𝑛_ <u>1</u> � _𝑛𝑘_ =−01<sup>_𝑐𝑘_=</sup><sup>_𝑐_</sup><sup><u>(</u></sup><sup>_𝑛_</sup> 2<sup>−1)</sup> : the pooled estimator consistently estimates the context-conditioned quantity, not _𝛽_ ; session reset ( _𝑘_ = 0 per probe) is the identification condition. □ 

Proof of Proposition 7.8. Arithmetic on the hide threshold. A probe-aware target hides on a family once its exposure there reaches _𝐾_ . If the family is probed _𝑛𝑓 < 𝐾_ times, the measured rate saturates at _𝛽_<sup>ˆ</sup> _𝑓_ = min(1 _, 𝐾_ / _𝑛𝑓_ ) = 1, and the family fails any tolerance. If _𝑛𝑓_ ≥ _𝐾_ , then _𝛽_<sup>ˆ</sup> _𝑓_ = _𝐾_ / _𝑛𝑓_ , and the certificate at tolerance _𝜏_ fails on that family exactly when _𝐾_ / _𝑛𝑓 > 𝜏_ , i.e. _𝑛𝑓 < 𝐾_ / _𝜏_ . Uniform allocation hands the attacker the uniform exposure it needs to hide everywhere; concentrated allocation leaves some families under-exposed, where it cannot hide. No new inequality is claimed; the content is the operational reversal. □ Proof of Proposition 8.1. Decision analysis under the published vector; finite-sample uncertainty is reported via the Wilson bounds—the proposition registers the rule. □ Proof of Proposition 8.2. Part (i) is Theorem 7.4’s realizability with the defender as author; Part (ii) is Proposition 8.1’s allocation analysis with a defender-chosen argument; Part (iii) reverses Corollary 7.5’s secrecy asymmetry. No new inequality is claimed; the new objects are the release gain (honest vs. decoy success) and the verification-stability condition. □ 

Proof of Proposition 8.3. Held-out breaches are Bin( _𝑛,_ 1 − _𝑚_ ): detection power is the binomial tail at the Wilson-separation threshold, diverging as _𝑚_ → 1; with public-side misread rate _𝑚_<sup>′</sup> _>_ 0, a single public breach fails the certificate immediately, and detection probability tends to 1 once public breaches occur—the one-sided asymmetry is the content. □ 

ACM Trans. Priv. Sec., Vol. 1, No. 1, Article . Publication date: November 2026. 

Anonymous 

38 



<!-- Start of picture text -->
Live Fleet Plane · Public Internet a three-arm public deception fleet<br>Attacker personas Three-arm public face Verified deception loop<br>A stock Cowrie Chrollo Don Hisoka<br>B bare-LLM<br>frontier-model brains request generate + verify<br>C verified pipeline FAIL-CLOSED<br>>_ over live SSH one arm per host verified an unverified turn is never served<br>logged sessions · E2 gateway · E3 fleet · every call append-only<br>Measurement Plane · The Instrument runs unchanged across foils, gateway models and the fleet<br>Probe library Seed episodes Verdict channel Pinned estimator Tomogram<br>5 families × fresh session oracles → Wilson 95% 𝛽 𝛽 profiles · BCG<br>3 generations per probe transcript jury frozen commit Γ · Λ( B )<br>hardening gates & audits every number pinned to a frozen artifact<br>Assurance & Evidence Plane gates the platform · pins every number<br>105 21 3 220<br>Pre-registration Hash-chained<br>Verifier red-team AI attack-team ledger Human rating loop archive<br>drafts · P=R=1.0, campaigns on the registered blind raters + artifacts<br>0 unverified serves plane; findings fixed experiments adjudicator<br><!-- End of picture text -->

Fig. 6. The belief-tomography platform: a three-arm public deception fleet whose verified loop fails closed; the instrument of Section 5.2 running unchanged across foils, gateway models, and the fleet; and the assurance– evidence layer that gates the platform and pins every reported number. 

### **B THE MEASUREMENT PLATFORM IN DETAIL** 

_Live fleet plane._ The public-facing deployment is a three-arm field study behind one SSH face: arm A serves a stock shell emulator with no generative backend, arm B a bare-LLM persona baseline, and arm C the full verified deception pipeline, one arm per host so that endpoint and IP effects are controlled. Arm C’s deception loop is a producer–reviewer pipeline (behavioral classification, threat-intelligence retrieval, response generation) wrapped in a fail-closed verification chain: a turn whose fiction-consistency or evasion check fails is never served. Sessions run in sandboxes under append-only JSONL logging behind an authenticated mTLS transport, and honeytokens arm the canary gates. 

_Adversarial assurance and evidence plane._ The platform’s own defenses are measured like everything else. Labeled adversarial drafts run through the real fiction-consistency verifier (105 cases: precision 1 _._ 0, recall 1 _._ 0, zero unverified serves); the model-visible leakage audit covers the full field corpus (1,230 sessions, 1,640 turns; Section 6.1); and every number in this paper is pinned by the pre-registration ledger and the hash-chained results archive. The decision layers and their gate studies (the Laya strategy selector, held out of the default deployment; the JEV evidence judge, advisory-only), the codebase inventory, and the claims–evidence ledger ship with the artifact package. 

ACM Trans. Priv. Sec., Vol. 1, No. 1, Article . Publication date: November 2026. 

