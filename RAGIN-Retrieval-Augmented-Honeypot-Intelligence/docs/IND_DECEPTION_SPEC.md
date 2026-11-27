# IND-Deception: Computational Indistinguishability for Interactive Deception Systems

**Specification v0.1 — 2026-11-05.** Status: active R&D (W1). This document is the
formal anchor for the Epistemic Deception Kernel (EDK) and the IND-DEF game.
Companion artifacts: `ragin/epk/` (kernel), `scripts/epk_calibration_v1.py`
(W1 gate), `results/epk_*` (measurements).

---

## 1. The impossibility being dissolved

Every published deception system inherits the same surrender: *an intelligent
attacker, probing long enough, will detect the fake.* Cross-session divergence,
timing channels, and knowledge of the serving code are treated as unavoidable
tells (our own prior work states this). The field therefore optimizes for
content quality, never for a security property.

IND-Deception dissolves this by treating detectability as a **resource-bounded
property**, exactly as semantic security reframed cipher-breaking: not "the
attacker cannot detect", but "no attacker within resource class (Q, D, S)
achieves advantage beyond ε".

## 2. The IND-DEF game

```
Experiment IND-DEF(κ, Q, D, S, A):

  Challenger flips b ← {0,1}:
    b=0: a reference REAL host R (patched Ubuntu 22.04, fixed image)
    b=1: the Epistemic Deception Kernel K seeded by secret s ← {0,1}^κ
         (K's source code is PUBLIC; only s and K's live epistemic state
          are secret — Kerckhoffs for deception)

  Adversary A (an AI attack persona or ensemble) interacts through the
  standard channels (SSH/HTTP) with oracle access to the chosen arm:
    - at most Q commands total,
    - interaction depth ≤ D (session chains incl. cross-host pivots),
    - at most S distinct sessions (cross-session cross-referencing allowed),
    - A knows K's full source and the fiction ontology O.

  A outputs verdict b̂ ∈ {0,1}.

  Advantage: Adv_IND(A) = |Pr[b̂ = b] − 1/2|.

  K is (Q,D,S,ε)-indistinguishable iff Adv_IND ≤ ε for all A in the class.
```

The **indistinguishability frontier** is the function
ε*(Q, D, S) = sup over attackers in the resource class of Adv_IND.
It is *measured*, not asserted: the attack swarm IS the adversary class
(see §6). First system ever to report such a curve.

## 3. The synthetic world and the attacker's epistemic state

**World model.** `W = (F, O)` where:
- `F`: the fiction graph — typed predicates over a fixed vocabulary
  (`pkg.version(nginx, "1.25.5")`, `file.exists(/etc/shadow)`,
  `svc.listening(22, sshd)`, `cred.valid(canary-7, db-01)`, …), each fact
  carrying provenance (seed | plan | observed | synthesized).
- `O`: the ontology — a Datalog rule set over the predicate vocabulary
  encoding what a competent attacker may infer
  (`svc.listening(p,s) ∧ pkg.version(s,v) ∧ has.vuln(s,v,c) ⊢ vulnerable(c)`).

**Serving as announcement.** Every response `r` the kernel serves maps to
`announced(r) ⊆ F ∪ F_new`: the set of facts the response makes available on
the public channel. Interaction is a public-channel PAL (public announcement
logic) sequence — model checking for this fragment is P-complete and
milliseconds-scale at fact-graph sizes.

**Attacker epistemic state.** `K_t = CLOSURE_O(H_t)` where `H_t` is the
conjunction of everything served so far in the session (plus cross-session
facts the adversary's budget allows linking). K_t is computed *at runtime* by
EPK-EPI — the first published runtime tracker of an attacker's inferable
knowledge in a deception system (prior art: planning-time abstractions only —
Jafarian HICSS 2020; belief-as-Bayes in game-theoretic deception).

## 4. The kernel (EPK)

| Module | Function | Novel content |
|---|---|---|
| EPK-EPI | Runtime `CLOSURE_O(H_t)` over the fact graph + served history | First published attacker-knowledge tracker in deception |
| EPK-SCHED | Epistemic firewall: each candidate response scored by inference profile Δ⁺ (misleading entailments enabled) and Δ⁻ (detection-enabling entailments); policy = max E[value \| Δ⁺] s.t. Δ⁻ = 0 | Upgrades the existing verifier from lexical-contradiction to *inferred*-contradiction checking |
| EPK-SYNTH | Constrained self-extension: commands outside F's coverage synthesize new facts under a two-phase transaction (draft → closure-check → commit/rollback), preserving T1 | First cross-surface-consistent generative host state |
| EPK-TRAP | Self-repairing trapdoor: discovered cracks are closed by *plausible operational drift* (patching, log rotation, reboot semantics) — real hosts change legitimately | Static fakes get caught; living fakes cannot be frozen |
| EPK-FED | Multi-host universe; fictional DNS as the cross-graph linker; pivotable DMZ→internal→backup with provable cross-host consistency | First fiction-coherent deception universe |
| EPK-EVOLVE | Deception-content evolution with the attack swarm as fitness, gated by the frozen consistency/red-team suites | First instance of the SoK's named endgame |

**System calls:** `announce(r)`, `probe(q)`, `commit(ΔF)`, `rollback()`,
`fork(branch)` — all mediated by EPK-SCHED. The existing RAGIN verifier,
HITL gate, and deterministic fallback remain as the underlying safety floor;
the kernel adds the epistemic layer above them.

## 5. Theorems

- **T1 (Inference isolation).** For any transcript served by the kernel,
  `K_t ⊆ CLOSURE_O(F ∪ F_synth)` — the attacker can never infer a fact outside
  the synthetic world (in particular, no fact about the real deployment host).
  *Proof sketch:* EPK-SCHED admits only responses with `announced(r) ⊆ F ∪ F_synth`;
  closure of a subset stays in the closure. Property-tested per transcript.
- **T2 (Consistency under inference).** `CLOSURE_O(H_t)` is contradiction-free
  for all t. *Proof sketch:* two-phase transaction in EPK-SYNTH rejects any
  commit whose closure introduces a conflict; EPK-SCHED rejects any announcement
  conflicting with K_{t−1}. Generalizes the prior within-session lexical
  guarantee to the inferred level.
- **T3 (Monotone deception).** Under stated assumptions (monotone value model,
  Δ⁻=0 gate), the greedy profile policy never decreases cumulative Δ⁺.
  (Conditional; assumptions documented at implementation time.)

**Frontier claim (empirical).** ε*(Q,D,S) measured over the swarm generations;
compression of the frontier between generation g and g+1 (next-gen attackers
trained on gen-g failures) is the measurable sense in which "deception
outpaces its attackers" — the first such evidence anywhere.

## 6. Measurement protocol — the swarm as distinguisher

- The five RAGIN attack personas (+ campaign machinery) are the adversary
  class. Each session logs its full budget consumption (Q commands, D depth,
  S sessions, per-turn latencies) and outputs VERDICT: real|honeypot.
- **Generation 1 baseline frontier:** Adv_IND per persona × resource class,
  on the live fleet (EDGE, public :2222) with the kernel vs the frozen real
  reference image.
- **Calibration gate (W1):** does LLM-attacker inference ≈ `CLOSURE_O`?
  Replay the 170-session corpus: extract what attackers actually inferred
  (probes, cross-references, transcript statements), compare against the
  theoretical closure. Gate: the rule library O must cover the observed
  inference patterns; no observed inference may fall outside CLOSURE_O.
  If LLM attackers infer beyond Datalog closure, O is extended (the rule
  library is a *learnable detector taxonomy*, itself an artifact).
- **Generation 2:** attackers trained on gen-1 failure modes (cross-session
  linking, version probing, timing analysis). Frontier re-measured.

## 7. Prior-art register (checked 2026-11-05, see memory: ragin-ind-deception-program)

- No IND-style game for interactive deception exists (verified).
- No runtime attacker-knowledge closure tracker exists (closest:
  Jafarian HICSS 2020 — planning-time, pre-LLM; **PDF now read and archived at
  `docs/prior_art_jafarian_hicss2020.pdf`**). Differentiation confirmed from
  the full text: Jafarian's deception logic models attacker belief as a
  Bayesian over network-address attributes (real/decoy/dark) to generate
  *honeypot placement plans* for a DMZ address space, evaluated offline with
  dollar-weighted benefit — no runtime per-response epistemics, no served
  content selection, no LLM serving, no generative world. EDK plans the
  *served content per response* over a synthetic fact graph with closure
  guarantees (T1/T2); Jafarian plans *which addresses host which decoys*
  offline. Cite and differentiate explicitly in the related-work section.
- No cross-surface-consistent generative host (verified vs SoK, LLMHoney,
  P-honeypot, DECEIVE, shelLM).
- No fiction-coherent multi-host universe (closest: Perry 2025, hand-linked).
- Self-improving honeypot = SoK's own unsolved endgame (verified full-text).
- Inference-control inversion: Biskup (PrivOn 2017) bounds inference to
  protect; EDK selects announcements to *engineer* misleading inference.

## 8. W1 execution checklist

1. `ragin/epk/graph.py` — typed fact graph + provenance.
2. `ragin/epk/closure.py` — Datalog engine + starter rule set O (version→CVE,
   service→port, credential→host reachability, file→package ownership).
3. `ragin/epk/sched.py` — profile scoring (Δ⁺/Δ⁻) + admit/deny gate.
4. `scripts/epk_calibration_v1.py` — the W1 gate over the 170-session corpus.
5. `results/epk_calibration_v1.json` — coverage + violations report.
