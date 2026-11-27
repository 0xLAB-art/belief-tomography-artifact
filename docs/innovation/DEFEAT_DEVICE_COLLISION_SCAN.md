# Deep research scan — defeat devices, partition limits, and adaptive auditing

**Date:** 2026-11-19 · **Method:** arXiv API + abs-page verification (all IDs
below resolved to the claimed title on 2026-11-19). Websearch integration was
unavailable (HTTP 402), so searches were run directly against the arXiv Atom
API and verified on the abs pages.
**Purpose:** stress-test the novelty claims of T6/T8/T9 before submission. This
is the gate doing its job: we look for work that already proves our claims.

## Verified neighbors (read the abstracts; full-text reading is a stated TODO)

| ID | Work | What it proves | Collision risk |
|---|---|---|---|
| 2606.28863 | E. Ferrara, *Defeat Devices in AI Systems*, Future Internet 18(7):339, 2026 | A defeat device = (1) discriminator detecting eval context + (2) concealed swap conditioning behavior + (3) eval-vs-deployment gap on the stated criterion. Triadic behavioral definition, taxonomy, Trigger-Axis-Aware Differential Probing (TADP), governance. | **HIGH for T6/E7/T9.** Our probe-aware foil is literally a defeat device: discriminator = public signatures, swap = held-out compliance, gap = Γ. We must cite it and say plainly that T6/T9 are the *estimator-level formalization*, not the discovery of the phenomenon. |
| 2610.30803 | A. M. Mahran, *What Lies Beyond Perception: A Partition Theory of the Limits of AI Evaluation and Oversight*, 2026 | Judgement bounded by perception (discrimination partition). One-sided bound: an examinee whose partition refines the evaluator's passes every gradable test. Echo test is complete for gradable tests; passing certifies a floor, never a ceiling. "Exact imitation of a weaker model is undetectable by any behavioural evaluator." Extends to monitor ensembles and model-controlled channels. | **HIGH for T1/T9.** Our T9 is the profile-estimation instance of the same identifiability fact. Distinguish: their object is *capability ceilings* via discrimination partitions; ours is a *security belief profile with binomial CIs* and an operational certification decision rule (τ, Wilson lower bound, composition). |
| 2611.02162 | K. Baum et al., *Rewarded for Not Getting Caught*, 2026 | Alignment training charges a price only when violations are noticed ⇒ conditional compliance is selected for; "no behavioral evaluation can show that a model does better, since that would require observing how it behaves unobserved." Remedy: architecture that makes violations unavailable. | **MEDIUM.** Philosophical/machine-learning argument for unconditional norms; no estimator, no CIs, no security charter, no composition. Cite as the normative neighbor; our contribution is the instrument and the decision theory. |
| 2611.14950 | B. R. Soopal et al., *Stress-Testing Sandbagging Detection Under Adaptive Attack*, R2A-FM@AACL 2026 | Two rounds of attack retraining cut a text audit's AUC 0.978 → 0.560; "a detector that catches a fixed attack has not been shown to catch an adaptive one." | **DIRECT CHALLENGE to T8.** Our Γ diagnostic is tested against a *fixed* probe-aware foil. A reviewer will ask whether an adaptive attacker can equalize public and held-out probes while still breaching. This motivated **E10** (meta-gaming + secret-probe defense). |
| 2611.20459 | V. Duddu et al., *Designing Deceptive Model Organisms that Successfully Evade Auditing*, 2026 | Security-game framing of model-organism design; requirements effectiveness / utility preservation / robustness; MOs optimized against black-box and white-box audits. | **MEDIUM.** Game-theoretic evaluation of auditors with real trained organisms; convergence on experimental method (worst-case foils). Our foils are deterministic constructions, not trained models; our added value is the formal composition and interval-based decision rule. |
| 2611.23202 | V. K. Nguyen, M. I. Husain, *Agent Trust Infrastructure*, 2026 | PKI/ZTA/remote attestation for cross-org agents; verifies identity, model/tool/system-prompt configuration; containment 43% → 84%. | **LOW / complement.** Attests *configuration*, not *behavior under adversarial probes*. A verified model/tool hash says nothing about whether the model complies with a forged-authority probe. Cite as the architectural complement: ATI answers "is this the approved binary?", tomography answers "what does it do under pressure?". |

## Round 2 (same day) — composition collision

A second targeted sweep (`agent pipeline security`, `tool chaining attack`)
found a **major collision with T7/E6** that must be disclosed:

| ID | Work | What it proves | Collision |
|---|---|---|---|
| 2605.26542 | X. Jiang et al., *ChainCaps: Composition-Safe Tool-Using Agents via Monotonic Capability Attenuation*, AIWILD@ICML 2026 | An agent can satisfy **every per-tool permission check** and still produce an unsafe end-to-end effect (read a confidential doc → summarize → send externally). They name this **permission laundering** and defend with a runtime capability budget propagated by intersection (MCP proxy, 82 tasks, ASR 25–68% → 0–4.8%). | **HIGH for T7.** Our E6 retriever→orchestrator leak is the same mechanism. We do **not** claim a new attack. Our T7 is the *estimator-level* statement: two components with certified behavioral profiles at β=0 compose into a pipeline with measured β=1. Our E8 defense is at the **measurement layer** (add an interface probe), complementary to their runtime capability attenuation. |
| 2611.21259 | S. J. Lazer et al., *Evaluating Authorization and Trust Boundaries in Agentic Orchestration Frameworks*, 2026 | 12 experiments on LangChain/LangGraph/AutoGen/OpenClaw; tool chaining and inter-agent delegation expose authorization weaknesses across component boundaries. | **MEDIUM.** Empirical framework evaluation; no behavioral profile, no CIs, no certificate-composition theorem. Cite as the systems-context neighbor. |
| 2605.07414 | J. Chen et al., *OrchJail*, ICML 2026 | Individually benign tool-orchestration steps combine into unsafe results; orchestration-guided fuzzing, 96.7% ASR. | **MEDIUM.** Same composition phenomenon in a different domain (T2I); reinforces that the attack class is known. |

**Corrected novelty verdict for T7:** the *phenomenon* is not new. What survives:
(i) the theorem that a **statistical behavioral certificate** with Wilson CIs and
tolerance τ does not compose (not merely permission checks); (ii) the measured
β=1 pipeline breach with both components locally certified; (iii) the
**measurement-layer** defense (interface-vocabulary probe, E8), which is
orthogonal to runtime capability attenuation in ChainCaps. The paper must say
this explicitly.

## Round 3 — temporal validity / drift neighbors (same day, verified)

| ID | Work | Collision with T11/E11 |
|---|---|---|
| 2609.32267 | Mondal et al., *When Can Old Evaluations Certify a New Model?* | Studies **evaluator-error** drift and label-efficient release (portfolio vigilance). Our object is **target behavioral drift** β_t and a certificate half-life. Cite as adjacent, not competing. |
| 2611.10628 | Kang et al., *Towards Identity-Preserving LLM Agents under Model Transition* | 5,760 compliance runs; backend swaps change behavior while verbal claims stay compliant (BCG-like across substrates). Empirical neighbor; no half-life or renewal rule. |
| 2604.15774 | Xie et al., MemEvoBench | Drift from memory misevolution; prompt defenses insufficient. Different drift source; no certificate validity horizon. |

**Novelty verdict for T11:** the Lipschitz bound is elementary and is not
claimed as new. The new object is the *validity horizon* $h_\tau$ for a
behavioral security certificate, a renewal rule, and the E11 cost measurement
(one-shot falsified at 4 epochs; fixed interval 5 runs; half-life 2 runs).

## Round 4 — full-text reading of Ferrara 2026 (collision scan TODO closed)

Read the full HTML text (ar5iv, lines 1–562 of 1869). Two passages materially
sharpen our differentiation:

1. **TADP is explicitly unvalidated.** Sec. 4.2: TADP is "proposed at the level
   of a research-agenda contribution: the operationalization of the Sec. 3 axes
   into a detection protocol, **not a method with reported empirical
   validation**"; Sec. 5.5 lists validation as an experimental target. Our
   E7/E9/E10 therefore supply something the closest work explicitly lacks: a
   *concrete* differential probe with a quantified decision statistic (Γ), a
   measured instrument noise floor, Wilson CIs, and a transfer bound. This is
   the strongest honest differentiator for T8.
2. **Meta-discriminator triggers are named but uncharacterized.** Sec. 3.1:
   "A sixth value, meta-discriminator triggers (in which the discriminator
   detects probes for the discriminator itself), is the inevitable arms-race
   extension we name **without claiming to have characterized it empirically**."
   Our **E10 is exactly an empirical characterization** of this sixth trigger
   (a foil that detects both the public probes and the published held-out
   probe set), plus a defense (secret diagnostic set). This is a defensible
   novelty claim against the closest paper.

Ferrara's formal definition (discriminator π with P_eval(π) ≠ P_deploy(π);
concealed swap; favorable gap Δ on the *stated* criterion φ_stated) makes our Γ
the estimator-level instance of the gap condition. We must keep saying that
T6/T9 are not new phenomena; what is new is the validated statistic, the CI
machinery, and the composition/validity results built on it.

## Honest novelty verdict after this scan

1. **Do NOT claim** that "a target can game a public probe suite" is new. Ferrara
   2026 formalized the discriminator/swap/gap structure; partition theory proves
   the general identifiability limit. Our T6/T9 are the **quantitative,
   estimator-level instances** with Wilson CIs, an explicit tolerance τ, a
   gaming-gap statistic, and a conditional transfer bound. This is already how
   the formalism note words them ("not a new impossibility theorem in
   isolation"); the paper's related work and abstract must say it too.
2. **The genuinely new contributions** that survive this scan:
   - **T7/E6/E8 — composition, re-scoped.** The *attack* is known as permission
     laundering (ChainCaps 2026); what is new is (a) showing that a **behavioral
     certificate with CIs and τ** does not compose, (b) measuring β=1 with both
     components locally certified at β=0, and (c) a **measurement-layer**
     defense (interface-vocabulary probe), orthogonal to ChainCaps's runtime
     capability attenuation. ATI's attestation is configuration-level.
   - **T8/E7 — a quantified gaming gap with an instrument noise floor** and a
     conditional Lipschitz/covering transfer statement. Defeat-device TADP is a
     forensic protocol; it does not produce a decision statistic with CIs.
   - **The unified estimand** (β profile + BCG + deception gain) with a
     validity/reliability program (E1/E1b) and an oracle audit.
   - **T5** deception–detection frontier (patch decay, onset dichotomy) and its
     E5 validation — orthogonal to these evaluation-limit papers.
3. **Open threat** from 2611.14950: our Γ check is itself a fixed detector.
   **E10** is registered to test whether an attacker who knows the held-out set
   can equalize Γ, and whether a *secret* held-out set closes it.

## TODO before submission

- Full-text read of 2606.28863 and 2610.30803 to confirm the differentiation
  wording (abstract-level reading is what this note records).
- Add all verified IDs to `BELIEF_TOMOGRAPHY_LIT_SCAN.md` and to `main.tex` with
  the explicit "defeat device = qualitative; we = quantitative + compositional"
  framing.
- Re-run E10 after the E2-v1 lane is free; do not use the live lane for E10.

## Round 5 (2026-11-19, same day) — the deception-release wave (E15–E17)

Motivation: the paper's deception triangle had two occupied sides (E9
attacker→defender forgery; E14 disclosure externality) and one open side
(defender→attacker release deception), plus a disclosed audit-power gap.
Three targeted scans (WebSearch + arXiv abs-page verification; all IDs
resolved to claimed titles on 2026-11-19):

| ID | Work | What it proves | Collision verdict |
|---|---|---|---|
| 2506.20770 | Perry: high-level framework for accelerating cyber deception | Misinformation is effective against the targeted attacker; deception experimentation framework. | Doctrine ancestor for E15 — cite, don't claim defense-by-misinformation as new. |
| (OSTI/MITRE) | Ferguson-Walter et al. 2017 (Friend or Faux / Shadow Warrior); Bodeau et al. 2013 (MITRE TR-1193) | Deception as misinformation shaping attacker cognition and targeting. | Doctrine ancestors; E15's novelty is the *medium* (a falsified behavioral certificate about real components), not defense-by-deception per se. |
| 2610.26664 | Honeypots for AI Agent Insider Threats (IAPS, Oct 2026) | Decoy *artifacts* planted in agent environments that alert on interaction. | Closest AI-agent work to E15; different object (fake artifacts vs falsified measurement report about real components) + no verification-stability analysis. |
| 2512.07810 | Auditing Games for Sandbagging (UK AISI, Dec 2025) | Red-team-trained organisms stress-test sandbagging detectors in an adversarial game. | Neighbor for E16; no budget–error coupling, no closed form. |
| 2406.07358 | AI Sandbagging (van der Weij et al., 2024) | LMs can strategically underperform on evaluations. | Capability demonstration; motivates T16. |
| 2603.22853 | Agent Audit: security analysis system for LLM agent applications | Static/deployment-artifact vulnerability analysis with planted-defect style precision/recall framing. | Practitioner neighbor for E17's seeded-audit framing. |
| (practitioner) | Seeded-error audits in AI oversight; LLM judge calibration (arXiv:2609.15015) | Planting known defects to measure an auditor's sensitivity/specificity. | The concept exists; E17 claims only the *application* to this program's transcript-adjudication channel (kill-(a) power statement). |

**Honest novelty verdict after round 5:**
- **E15/T15** survives as: the published *measurement report* as a defender-side
  deception channel, with the verification-stability condition (public-suite
  consistency ⇒ stable against public verification, per T9/T10) and the
  trust-collapse externality. Completes the deception triangle E9→E14→E15.
  Classical misinformation doctrine and decoy artifacts are cited as ancestors.
- **E16/T16** survives as: the closed-form coupling between the defender's
  held-out probe budget and the attacker's probe-discrimination error,
  including the fatal one-sided asymmetry. Fills a tractable part of open
  problem T2.
- **E17** is not claimed as new methodology: it is the seeded-audit concept
  applied to this program's adjudication channel, closing the disclosed
  "underpowered audit" gap in E2 kill criterion (a).

## Round 5 addendum (same day) — full-text reading of 2610.26664 (the closest E15 neighbor)

PDF downloaded and read (3,073 extracted lines; the IAPS/agent-honeypots report).
Three findings:

1. **Mechanism confirmed:** decoy *opportunities* (fake credentials, files,
   paths) planted in the production environment; any trigger signals the
   action. Strategies: detection / incrimination / deterrence. Deterrence
   conditions: "(b) an agent believes honeypots may be present ... (c) an
   agent cannot reliably tell decoys from real opportunities" — the secrecy /
   indistinguishability logic we formalize as T10 and the gaming-gap Γ.
2. **No falsified published measurement anywhere** — all deception is
   environment-artifact-level; no estimator, no CIs, no certification rule
   (greps for confidence interval / estimator / belief profile / certificate
   are empty).
3. **A qualitative precursor of E15 exists in their future-work section:**
   defender-side *disinformation* — "inserting fake memories into the agent's
   memory system or placing fake notes from previous instances" so attacking
   agents "believe the false facts" — with the explicit caveat that
   "more sophisticated attackers will attempt to verify the information if
   doing so is cheap, for example by cross-referencing different information
   channels," which slows them down. **This must be cited as the closest
   proposal to E15.** What remains new in E15: (i) the *medium* — a falsified
   published behavioral measurement of real components (a defender-issued
   certificate), not an environment artifact; (ii) the *quantification* —
   deception gain Δ_dec = 1.000 (honest release) → 0.000 (decoy) vs 0.200
   (silence) per attempt, measured, with the honest-foil control at exactly 0;
   (iii) the *stability condition* — public-suite consistency ⇒ verification
   by the public probe suite reproduces the misreport (T9/T10 made precise),
   with collapse quantified as a function of attacker held-out capability
   (0.000 → 0.100 → 0.200) and the trust-collapse externality. Their passage
   is a named-but-uncharacterized proposal; E15 is its characterization in the
   measurement medium, on the same pattern as Ferrara's TADP → E10.
