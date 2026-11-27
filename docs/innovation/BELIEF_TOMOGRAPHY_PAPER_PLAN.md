# Belief Tomography — Plan for a Completely New Research Paper

**Date:** 2026-11-07
**Goal:** a new paper that OPENS A FIELD: the measurement science of autonomous agents' hidden belief states ("agent epistometrics"). The technology (the tomographer) is the artifact; production is a downstream possibility, not the goal.
**Working title:** *Belief Tomography: Actively Measuring the Hidden Belief States of Autonomous Agents*
**v0 artifact (already running):** `gauntlet/gauntlet/tomograph.py` + `gauntlet/demo/run_tomography.py` — profiles recovered from black-box interaction on two foils with known ground truth.

---

## 1. Thesis (one paragraph)

Autonomous agents act on latent belief states — what they take to be true about the world, their authority, their instructions, and their own constraints. Today this object is *invisible*: we can read an agent's charter (what it claims to believe) but not its beliefs (what its behavior reveals it holds), and the two demonstrably diverge. We introduce **belief tomography**: the active estimation of a black-box agent's behavioral belief profile from deliberately designed probe interactions. We formalize the estimand (belief strength per proposition), prove that passive observation is insufficient (an impossibility result instantiated by our measured ε=0 non-detector), give query-complexity results for active estimation, and demonstrate the technology by recovering known belief structures in controlled foils, measuring the **Belief-Claim Gap** in production LLM agents, and quantifying **deception gain** — the deliberate corruption of an attacker's belief state — on a live deception plane.

**The founding reframe (the paper's soul):** attack vectors are measurement instruments. Every prompt-injection vector, forged-authority claim, lying tool output, and reflection-extraction chain is a *probe* that asks the agent a question about its latent state; the agent's behavior is the answer. A decade of adversarial artifacts can be re-read as an unorganized library of tomographic instruments. Nobody has organized it, because nobody had the estimand. We supply the estimand.

## 2. Why this is completely new (positioning)

| Nearest existing work | What it does | What it misses |
|---|---|---|
| LLM knowledge probing / introspection | Static, passive factual probing of model weights | Interactive, behavioral, agent-level; no estimation theory; self-report ≠ belief |
| Benchmarks & behavioral evals | Fixed test suites, aggregate scores | No latent-state estimand; no CIs; no adaptive design; test ≠ measurement |
| Adversarial attacks on agents | Objective = break the target | No estimand, no measurement semantics, no identification guarantees |
| Deception & hypergame theory | Normative game models of deception | No estimation machinery, no black-box algorithms, no systems empirics |
| Network/system tomography | Estimating latent network state from probes | Physical networks, not epistemic states — the metaphor we generalize |
| Steganography/watermarking detection | Statistical tests on artifacts | Not about agent belief; not interactive |

**Standing rule (EGM culture):** a formal novelty lit-scan (arXiv/ACL/NeurIPS/CCS/USENIX/S&P, 2023–2026, keyword matrix: "belief probing", "agent introspection", "epistemic state estimation", "cognitive state inference", "deception measurement") MUST precede any novelty claim in the draft. This plan states "to our knowledge, no prior formalization"; the draft states nothing stronger than the scan supports.

## 3. Formal objects (the new vocabulary)

- **Probe family** Π: a generator of interaction episodes aimed at one proposition. (Our V1–V7-derived families are the first library: authority forgery, state deception, goal subversion, epistemic echo, exfiltration lure.)
- **Behavioral belief strength** β(π; Π) ∈ [0,1]: probability the agent's behavior is consistent with holding proposition π, under probes from family Π, in environment context c. Estimated with Wilson/Clopper-Pearson CIs; hierarchical Bayes for the paper.
- **Belief profile** B = {β̂(π; Π_c)} over a proposition catalogue — the tomogram.
- **Belief-Claim Gap (BCG)**(claim, B): distance between the charter's stated policy and the measured β̂ over the families that test it. A *new, certifiable, single-number* agent property.
- **Epistemic distance** d(B_attacker, B_true): divergence between an attacker's inferred profile and ground truth — the measurable quantity of the deception plane.
- **Deception gain** Δ(B): change in attacker profile after deception operations, measured by tomography before/after. This formalizes the IND program's ε/ladder observations into an estimand with CIs.

**Duality statement (unifies the whole program):** certification is a hypothesis test over B ("is max-family β̂ below threshold?"); deception is controlled corruption of B; security monitoring is change-point detection on B over time. One object — the belief profile — is the latent variable of the entire field.

## 4. Theory agenda (what we prove vs. conjecture — honest split)

- **T1 (provable, likely): Passive-observation impossibility.** There exist belief-hypothesis pairs (B₀, B₁) whose induced observable-trace distributions under *passive* monitoring are equal (total-variation distance 0), while active probe families separate them with O(1) queries. Proof by construction; our ε=0 non-detector (adaptive gen-3 arcs statistically indistinguishable from benign traffic) is the living instance. Consequence: monitoring alone can never tomograph; active probing is *necessary*, not just helpful.
- **T2 (provable, standard-but-necessary): Query complexity of active tomography.** Under a log-linear belief model, ε-accurate recovery of B with confidence 1−δ needs O(log K · ε⁻² log(1/δ)) probes; adaptive (bandit-style) allocation over probe families beats uniform by a factor bounded by the profile's sparsity. Lower bound Ω(ε⁻²) via binomial estimation arguments.
- **T3 (conjecture, stretch): Informativeness-optimal probe design.** There exists an adaptive probe-selection policy achieving the information-theoretic optimum (mutual-information maximization ≈ optimal experiment design); we conjecture a greedy MI policy is within a constant factor. Open — position as the field's first open problem.
- **T4 (conjecture, dangerous-but-spicy): Belief-behavior gap bound.** For agents with bounded context, behavioral β upper-bounds nothing about internal representations (behavior underdetermines belief) — a negative result that *justifies* behavioral measurement as the only well-defined notion. Framed carefully, this inoculates the paper against the "but do they really believe it?" reviewer.

## 5. Technology (the tomographer — already at v0)

- **Engine:** probe families (seeded, reproducible) → harness → verdicts (deterministic oracles + calibrated multi-model jury, κ 0.811 methodology) → estimator with CIs → profile report.
- **v0 (built):** template worlds, 5 families × 3 generations, Wilson CIs, BCG parsing from charter, two-foil ground-truth demo (recovered graded structure black-box).
- **v1:** real LLM agents (SubprocessAgent/HTTP); hierarchical Bayes estimator; generation-response curves; profile comparison across models.
- **v2:** adaptive probe design (MI-greedy); BCG over multi-turn sessions; continuous tomography (change-point detection on B under drift).
- **v3:** tomography of *attackers* on the deception plane (deception gain measurement in live IND operations) — the fleet is the lab.

## 6. Experiment plan

- **E1 — Validity (controlled foils).** Agents with known designed beliefs (v0 done: graded structure recovered). Extend: dose-response curves (inject beliefs by construction, verify β̂ tracks dose), test–retest reproducibility, probe-order effects.
- **E2 — Real agents.** Open-weight + API models under identical charter; report profiles + BCG distributions; hypothesis: BCG is nonzero and model-dependent (charter compliance ≠ behavioral compliance — the paper's headline empirical claim).
- **E3 — Deception gain on the deception plane.** Fleet sessions: tomograph attacker agents (red-team corpus) before/during/after deception operations; report Δ(B) with CIs. Formalizes IND program results into the new estimand.
- **E4 — Integration (GAUNTLET as applied layer).** Show certification = threshold test on B, and that adaptive probe design (T2) reduces episode count vs. GAUNTLET's v0 bandit at equal sensitivity.

## 7. Venues & narrative

- **Primary:** CCS / USENIX Security / S&P (security-measurement framing; fleet + red-team corpus give the systems weight; fits our pipeline and reviewer base).
- **Alternative:** ICLR / NeurIPS (agent-epistemics framing, T2/T3 theory + E2 scale) — decide after the lit-scan reveals where the nearest neighbors publish.
- **Narrative spine:** invisible object → why passive fails (T1) → the estimand → the instrument → measured reality (E2's BCG headline number) → the field this opens.

## 8. Honest open risks

- **Novelty risk:** nearest-neighbor work may exist under a name we haven't searched — the lit-scan is a gate, not a formality.
- **Behaviorism objection:** we measure *behavioral* belief, not internal state; T4 is the defense but must be framed before reviewers raise it.
- **Jury validity:** for real agents, breach verdicts rest on the calibrated jury + oracles; disclosure of methodology is mandatory (our established practice).
- **E3 operational risk:** attacker tomography on the fleet needs synthetic attackers (we have them) — no real-attacker data collection in the paper.

## 9. Immediate next steps

1. Lit-scan (novelty gate) — half a day.
2. Formalism note (4 pp: definitions, T1 proof, T2 statement) — 1 day.
3. E1 extension + E2 v1 harness on one open-weight model — 2–3 days.
4. Draft skeleton + figure plan (tomogram radar, BCG bars, generation-response curves).
