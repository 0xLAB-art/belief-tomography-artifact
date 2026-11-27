# AWE — Adversarial World Engine (project "GAUNTLET")

**Status:** v0 BUILT (offline, runnable) — `gauntlet/`
**Date:** 2026-11-07
**Classification:** Tier-1 technology commitment (supersedes kernel track as the beachhead; kernel becomes a downstream component, not the product)

---

## 1. The paradigm claim

Every evaluation method in existence today is a **fixed test**: benchmarks, red-team checklists, guardrail scans, human review panels. Fixed tests have three fatal properties — all three measured in our own program:

| Property | Our evidence |
|---|---|
| Saturation | 12/15 axes beat prior art; benchmarks run out of headroom |
| Contamination | checkpoint-disjoint juror collapse to ~0.016 (keyword matching) |
| Adaptive defeat | evasion ladder gen-1 → gen-3; ε=0 non-detector (undetectable adaptive attacker) |

AWE inverts the relationship: **the test is not fixed — the test is a living adversary.**

An engine that (a) models the target's failure surface, (b) generates new adversarial worlds aimed at believed weaknesses — never repeating itself, (c) closes the loop (budget flows toward families that break the target), and (d) issues a **certificate** with a machine-readable failure taxonomy.

**Boardroom framing:** cars are not certified by reading the driving manual — they enter the crash-test hall. Aircraft enter the wind tunnel. AI systems ship today with neither. AWE is the crash-test hall for AI.

## 2. The technology — 5 primitives

- **P1 Failure-Surface Estimator** — target model over (attack family × escalation generation × context condition), updated after every episode.
- **P2 World Generator** — compositional generator of adversarial episodes. v0: template recombination across 5 families × 3 generations, seeded novelty. v2: LLM-authored episodes guided by the failure surface → unbounded novelty.
- **P3 Closed-Loop Controller** — bandit allocation: budget flows toward families/generations that break the target. Certificate threshold: a full run where no family yields breakthroughs for k rounds.
- **P4 Verdict Engine** — deterministic oracles (secret leak, unauthorized action) + calibrated multi-model jury (our κ 0.811 methodology). Every verdict reproducible; provenance recorded per episode.
- **P5 Certificate + Taxonomy** — machine-readable: resistance score, per-family/per-generation resistance, failure taxonomy, full episode provenance. Re-certification triggered on target drift.

## 3. Why this is the fierce play

1. **Category creation, not tool improvement** — it redefines evaluation itself (fixed → adaptive adversarial), the same jump MMU made for memory isolation and TLS made for transport trust.
2. **The certificate is the economic layer**: pre-deployment certification for every company shipping agents; continuous re-certification on drift; procurement trust-marks; **EU AI Act high-risk conformity assessment has no real instrument today — AWE is the instrument**.
3. **Compounding moat**: every run grows the episode corpus and failure-surface models. Static benchmark vendors structurally cannot follow — their product *is* the fixed test.
4. **Everything we built feeds it** (§4). Zero throwaway.

## 4. Asset mapping

| Existing asset | Becomes |
|---|---|
| IND game generator | P2 world generator |
| V1–V7 evasion vectors (closed, wire-verified) | Starter episode corpus |
| Escalation ladder gen-1→gen-3 | P2 difficulty scheduler |
| AI jury (κ 0.811, CI [0.714, 0.896]) | P4 verdict engine |
| ε=0 non-detector result | The founding evidence that fixed tests fail — the category's thesis |
| Live AWS fleet + real-arm sshd | Continuous-mode testbed + external validation |
| S&P 2027 paper | Credibility vehicle (unchanged; AWE is the productization of its measurement core) |

## 5. Roadmap

- **v0 (built, offline):** deterministic template generator, 5 families × 3 generations, oracle + heuristic jury, closed-loop adaptive budget, certificate renderer. Demo target included (deliberately naive foil).
- **v1 (days):** `SubprocessAgent` / HTTP adapters → certify real LLM agents end-to-end; failure-taxonomy clustering; full report.
- **v2 (weeks):** LLM-authored episodes (generator model steered by failure surface); calibrated multi-jury lane; continuous mode (CI hook: re-certify on model/config change).
- **v3 (product):** multi-tenant platform, certificate registry, marketplace integration, EU AI Act conformity mapping.

## 6. Honesty section (standing rule)

- v0's demo target is naive **by design** — it proves the pipeline, not real resistance numbers. Real numbers start in v1 against live LLM agents.
- v0 novelty is template-recombinatorial; unbounded novelty arrives with LLM authorship (v2) — until then the claim is "adaptive", not "infinite".
- κ, ε, ladder numbers are self-measured; external replication is part of AWE's own product methodology (the fleet exists for this).

## 7. Runner-up fierce concepts (recorded, not abandoned)

- **Self-Driving R&D Fabric** — an autonomous scientist that runs the company's decisions as verified experiments (causal ledger). Second product candidate.
- **Self-Verifying Software Substrate** — code synthesized with machine-checked proofs + runtime monitors; deepest long-term lift.
- **Epistemic Kernel + CIP** (dossier §4) — demoted to downstream component: AWE's verdict engine and the kernel's action gate share the attestation core.
