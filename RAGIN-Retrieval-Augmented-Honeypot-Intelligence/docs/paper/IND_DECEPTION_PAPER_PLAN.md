# Paper Plan: "IND-Deception: Measuring and Widening the Indistinguishability
# Frontier of Interactive Deception Systems"

**Target:** IEEE S&P 2027 cycle 1 (abstract ~June 4, paper ~June 11, 2027 — confirm
against sp2027 CFP when published). Template: `\documentclass[conference,compsoc]{IEEEtran}`,
US letter, 13pp body + 5pp refs/appendix, double-blind, GenAI-disclosure field.

**Status:** artifacts complete through gen-2 final + gen-3 partial (escalation ladder
V1→V7 measured); gen-3 completion + optional gen-4 slot into §VI. All numbers below
resolve to committed artifacts (see docs/IND_DECEPTION_SPEC.md §8 and results/).

---

## Story spine (one paragraph)

Everyone believes an intelligent attacker eventually detects a fake; the field
therefore builds content, not security properties. We define IND-DEF — the first
computational indistinguishability game for interactive deception — and build the
Epistemic Deception Kernel: a serving path that tracks what the attacker can INFER
(runtime closure over a synthetic fact graph), refuses any response that lets the
attacker infer a contradiction or an out-of-world fact, extends the world only along
closure-preserving transactions, and repairs discovered cracks with plausible
operational drift. Over three attacker generations on a live public deployment
(16+9+4 sessions, five personas, budgets logged per session), the measured frontier
holds ε=0.0 for every non-detector persona (including two full 30-turn APT arcs and
a 36-minute credential campaign), while the purpose-built detector persona is forced
to escalate through a measured ladder of ever-deeper probes (filesystem depth →
coreutils presence → inode coherence → time coherence) as each rung is closed.
Detection of an adaptive attacker is not defeated — it is PRICED, per generation,
as an escalation requirement.

## Section map

§I Introduction — the impossibility narrative; IND-DEF game in 10 lines; the
  three results: (R1) definition+kernel, (R2) frontier methodology (swarm as
  distinguisher), (R3) the measured escalation ladder (gen-1→gen-3).
  Numbers: 16 gen-1 sessions ε=0.0 (APT 30/30 turns ×2, cred_hunter 36 min);
  escalation: V1-V4 closed → attacker at V5(inode)/V6(time) → V6b closed → …

§II Background & threat model — deception as a control problem; attacker classes
  (scripted, LLM-driven, purpose-built detector); the observation model (public
  channel ⇒ PAL fragment, P-complete, per-turn feasible); what is NOT claimed
  (unbounded attackers; physical; control-plane).

§III The IND-DEF game — formal definition (spec §2); resource classes Q×D×S;
  the distinguisher swarm protocol (personas as adversary class; VERDICT as the
  distinguisher output; budget logging per session).

§IV The Epistemic Deception Kernel — fig: architecture; EPK-EPI closure tracker
  (first published runtime attacker-knowledge tracker); EPK-SCHED epistemic
  firewall (Δ+/Δ− profile; upgrades lexical verification to inferred
  verification); EPK-SYNTH constrained self-extension; systree (deterministic
  fs oracle: mtime-ordered inodes, dpkg↔tree coherence, /proc coherence);
  drift/self-repair (slot supersede semantics).
  Theorems: T1 inference isolation; T2 consistency-under-inference (with
  property-test pointers); T3 monotone deception (conditional).

§V Implementation — the RAGIN deployment: fiction graph + verifier + HITL +
  fallback (prior work) as the kernel's substrate; wire path (cowrie→bridge→
  kernel→pipeline); the deployed identity (web-srv-01 / Ubuntu 22.04.3 /
  kernel 5.15.0-91); live since 2026-10-25; deployment gotchas as
  operational contributions (SSM, socket-activation ssh, distroless).

§VI Evaluation — the frontier experiments:
  A. Calibration (W1 gate): attacker inference ≈ Datalog closure on 170
     sessions (results/epk_calibration_v1.json).
  B. Gen-1 baseline frontier: 16 sessions/5 personas; ε=0.0 non-detector
     (Table: persona × detection × budget); APT arcs 30/30; cred_hunter 36 min.
  C. Escalation measurement (gen-1→gen-2): vectors V1-V4 catalogued → closed →
     attacker escalation to V5 (inode)/V6 (time) — the ladder table.
  D. Gen-3 vs v9/v10: V6b closure; remaining rungs honest-reported.
  E. Coherence properties: T1/T2 property tests; cross-query suite
     (dpkg↔tree, proc↔uptime, inode↔mtime ordering — zero violations).
  F. Cost: systree answers at zero provider cost; latency fingerprinting
     discussed as the residual channel (priced, not hidden).

§VII Related work — Jafarian (planning-time placement logic; archived PDF);
  Biskup (inference-proof filtering inverted); DEL misdirection (non-computational);
  LLM honeypots (shelLM/HoneyGPT/LLMHoney/GenPot/LLM-SSHH); AgentTrap; Honeyquest;
  SoK honeypots+LLM endgame; swarm-as-benchmark novelty.

§VIII Discussion — what the frontier does NOT claim; the honest boundaries
  (evasion persona still detects; latency channel open; free-tier provider);
  dual-use: publishing detection vectors educates both sides — our stance.

§IX Ethics — live honeypot; canary-only secrets; no real-attacker logs
  committed; HMAC IP hashing; LLM-judge disclosure; red-team authorization;
  the dev-account lockdown (owner-match iptables, locked between windows).

Appendices: artifact index (every number ↔ file); reproduction sequence;
rubrics; verifier red-team detail; figure-geometry audit.

## Evidence inventory (all committed)
- docs/IND_DECEPTION_SPEC.md — the formal anchor
- results/epk_calibration_v1.json — W1 gate
- results/epk_frontier_gen1.json — 16-session baseline frontier
- results/epk_frontier_gen2.json — escalation measurement (V5/V6)
- results/field_attack/sessions_epk_gen*.jsonl — raw transcripts (Q/D/S budgets)
- results/epk_screens.jsonl (on CORE; export before freeze) — kernel-side screens
- docs/prior_art_jafarian_hicss2020.pdf — prior-art differentiation source
- tests/unit/test_epk_*.py — T1/T2 + coherence property tests (31)

## Remaining to write (mechanical once gen-3 lands)
1. gen-3 final numbers (recon/apt in flight) + optional gen-4 against V4b/V7 fixes
2. §III/§IV prose from the spec (6-8 pp)
3. §VI tables from artifacts (2-3 pp)
4. T1/T2 proof write-up (0.5 p)
5. Figure set: kernel architecture, escalation-ladder table, frontier curve
   (detection rate vs generation × persona), knowledge-ledger sample transcript

## Known honest limitations to state
- ε measured against free-tier LLM attackers (the swarm), not human experts
- synthetic-arm slice complete; dual-arm (real-host pairing) requires driver
  PTY support (OpenSSH 10.2p1 exec quirk) — in progress
- latency homogenization open (the one channel the kernel does not close —
  priced in the threat model)
- V5/V6 closed; V7-class cross-directory checks closed by the ordering table;
  deeper rungs (proc cross-checks beyond uptime/version, package-db epochs)
  remain open by design — the ladder is the contribution
