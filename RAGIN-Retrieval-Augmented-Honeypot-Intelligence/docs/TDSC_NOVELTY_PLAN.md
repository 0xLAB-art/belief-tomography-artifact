# RAGIN → IEEE TDSC Retarget: Novelty Plan

**Status:** Working draft (Phase A/B implemented; scoring re-run pending)
**Intended venue:** IEEE Transactions on Dependable and Secure Computing (TDSC)
**Prior submission:** ESWA-S-26-45224 (Major Revision) — the five panel complaints are listed in `REVIEWER_FIXES_SUMMARY.md`.

This document argues why the *current* system — not the ESWA version — clears
TDSC's novelty bar, and what experiments turn each claim into an artifact the
reviewers can reproduce.

---

## 1. Positioning statement

TDSC accepts work that *changes threat/defense outcomes under adversarial
pressure*. The ESWA submission described a static GPT-based honeypot.
This revision describes a **cyber-deception closed loop** whose defensive
value the paper can now *measure* on three axes TDSC reviewers accept as
primary:

1. **Verifiability** — every deception response is machine-verified before it
   is served, and every high-risk action is gated by a man-in-the-loop approval
   with a queryable audit trail.
2. **Adversarial consistency** — the honeypot cannot be contradicted *by
   itself* (fiction-graph invariants), closing the classic
   "ask twice, get two answers" fingerprinting attack.
3. **Predictive baiting** — the environment does not respond reactively;
   it steers the attacker toward predicted next techniques (MITRE chain in the
   loop), which is measurable as a *downstream* drop in time-to-first-action
   and a rise in capture/honeytoken rate.

Each item is a **graph-injected, checkpointed, human-auditable loop** — none of
it existed in the ESWA artifact, and none of it has a published analogue at the
confluence of LLM honeypots and deception graphs.

---

## 2. Novelty claims and prior-art gap

### C1 — Fiction-graph consistency enforcement (novel)

Prior art (HoneyGPT, ENTICE, DeceptiveHoneynet, review: "LLM honeypots 2024–25")
pins identity in a *system prompt*. Every one of them is vulnerable to the
**re-query fingerprint**: ask `hostname`, then `cat /etc/hostname`, then
`uname -a`, and the LLM drifts (different FQDN, kernel release, users,
`/etc/passwd` vs `whoami` uid).

We replace prompt-only pinning with a **fictional-world knowledge graph**
(`ragin/graph/fiction.py`):

- Stable predicates (`os`, `kernel`, `hostname`, `domain`, `user`) are
  **assert-once**: a contradicting re-assertion is recorded as a
  *contradiction*, not silently overwritten.
- Every LLM reply is parsed (`observe()`), and any new fact enters the graph.
- The fact block is fed back into the next prompt as authoritative context,
  so later answers are *forced* to agree with earlier ones.

**Why TDSC:** internal-consistency is a falsifiable defense property. The paper
reports *contradiction rate vs re-query count* for RAGIN vs system-prompt-only
baselines (HoneyGPT-style). An attacker who fingerprint-checks the honeypot
takes strictly longer to disbelieve it.

### C2 — Verification-before-serve with retry (verifiable deception)

Every generated response is checked by a `verify` stage before it reaches the
attacker; on failure the graph **retries generation with state feedback**
(`max_retries`), then falls back to a deterministic, identity-bound template.
The verifier checks the same predicates the fiction graph enforces, so
"verification" and "consistency" share a single invariant source.

**Why TDSC:** serving *verified* content is the machine-learning analogue of
"fail-safe default." Reviewers get a head-to-head metric: % of responses served
after passing verification, and *time-to-first-inconsistent-answer*.

### C3 — MITRE-steering predictive bait (offense-aware defense)

`ragin/graph/mitre.py` ranks the most probable next techniques from the
techniques observed so far (`_TECHNIQUE_EDGES`, tactic-chained traversal), and
seeds the *environment* with matching bait artifacts:

- `T1003*` (ingest shadow hashes) → brittle `/etc/shadow` (locked hashes) +
  stale `.bash_history` re-using a service account;
- `T1552*` (unsecured credentials) → env/config file with a re-usable credential;
- `T1046`/`T1571` → a half-open non-standard-port service as a pivot lure;
- `T1021*`/`T1550`/`T1078` → credential/alternate-auth material greasing
  lateral movement.

This is **proactive deceptiveness**: the honeypot invites the exact technique
the attacker is about to use, which maximizes downstream sensor
(honeytoken/capture) yield.

**Why TDSC:** next-technique prediction accuracy is a concrete,
benchmark-able contribution, and it connects to MITRE ATT&CK grounding the
reviewers already asked for in ESWA (issue M7).

### C4 — Human-in-the-middle approval + audit (man-in-the-loop, operational truth)

`ragin/cycle/hitl.py` computes a risk score from attacker skill, requested
technique (e.g., `T1003` credential harvest, listener/beacon spawn), and
response size, then enforces an approval policy (`AUTO` / `NOTIFY` / `REQUIRE`).
`REQUIRE` blocks the serve until a human approves; every decision is appended
to a JSONL audit trail. The LangGraph orchestrator pauses-and-resumes via
checkpointing (no state loss), so a blocked action can be reviewed *later*
while the session stays consistent.

**Why TDSC:** operationally honest deception. The paper reports (a) how much
traffic real deployments can keep in AUTO vs REQUIRE, (b) audit-trail
completeness, (c) whether human gating measurably cuts *legal/ethical
blast radius* — the argument TDSC reviewers use to justify allowing
deception research at all.

### C5 — Checkpointed, replayable orchestration (reproducibility)

The full loop (`classify → analyze → plan → approval → generate → verify →
finalize`, conditional retry, HITL resume) runs on a **checkpointed graph**
(`ragin/cycle/graph.py`). Any session can be:
- resumed after a human pause with identical prior state;
- replayed deterministically for forensics / red-team reproduction of a
  contested event.

**Why TDSC:** the reviewers' deep-dive question ("what exactly did the
honeypot serve, and can we re-run it?") has a one-command answer.

---

## 3. What is *not* novel (and must not be oversold)

- LLM-based open-domain shell emulation — prior art exists (HoneyGPT et al.).
- A knowledge graph per se, or MITRE ATT&CK as a taxonomy — mature.
- Honeytoken engines, engagement profiling — inherited from the ESWA build.

The paper's contribution is the *integrated, verified, human-gated
deception loop with predictive baiting*, and the *benchmark* that measures it.
Overselling components individually would invite the "incremental" verdict.

---

## 4. Validation plan (maps claim → artifact)

| # | Claim | Experiment | Metric | Artifact |
|---|-------|-----------|--------|----------|
| C1 | Consistency enforced | Re-query battery: `hostname`, `cat /etc/hostname`, `uname -a`, `id`, `cat /etc/passwd`, `cat /etc/shadow`, IMDS, repeated 20× per session | contradiction rate 0 vs system-prompt baseline | `graph_consistency_bench.json` |
| C1 | Drift detectable | Adversarial re-query with *false* facts injected in prompt | contradiction *recorded* (not silent) | `fiction.contradictions` |
| C2 | Verification works | Inject verify-failing responses (reveal tells, contradictions) | % blocked, % retried, % served; no failed response served | verifier log |
| C3 | BAIT = right bait | Drive attacker sessions with known next-technique ground truth | next-TTP top-1/top-3 accuracy; bait-hit rate | `mtp_steering_eval.json` |
| C3 | Proactive > reactive | Same attacker corpus vs reactive-only honeypot | time-to-capture, honeytoken trigger rate | head-to-head |
| C4 | Gating effective | Skill × technique matrix | fraction AUTO/NOTIFY/REQUIRE; audit completeness 100% | `hitl_audit_eval.json` |
| C4 | Oracle honest | Human reviewer reads audit trail vs actual served responses | mismatch = 0 | audit review |
| C5 | Replay works | Pause → resume → replay contested session | identical state transition trace | checkpoint diff |
| S | Overall > ESWA | Full 8-scenario human eval re-run with current pipeline | mean ≥ 3.0/5 (vs stale 1.91) | `results/human_eval_scored/consensus.json` |

Legend: S = superiority re-benchmark (see §6).

---

## 5. Ablation (to defend every component)

1. **No-fiction** (final prompt never seeded from fiction graph) → expect
   contradiction rate ↑.
2. **No-bait-steer** (strategy block empty) → expect bait-hit rate ↓.
3. **No-verify** (never gate) → expect a measurable % of bad responses served.
4. **No-approval** (everything AUTO) → expected REQUIRE-stage audit trail empty.
5. **No-graph** (linear hand-rolled orchestration, `_run_linear` path) →
   equivalently correct transitions, but checkpoint/replay/HITL-resume
   features go `N/A`; used to prove the loop logic does not secretly depend
   on LangGraph.

Ablations 1–4 must be *worse* on their target metric — not crash — which is
also the robustness test reviewers will run.

---

## 6. Re-benchmark vs the stale numbers

The ESWA consensus (`results/human_eval_scored/consensus.json`, mean 1.91/5,
deception ceiling 2.51/5) is **stale**: it predates the honest-identity
rewrite. Current proofs in `results/human_eval.json` (newer run) already show:

- TTP extraction populates correctly (pinned `id` → `uid=1001(webapp)`,
  GT-003 no longer a refusal);
- persona override honored per-ground-truth (was: every scenario ran as `apt`).

Open output leaks still visible in the newer raw logs, and their fixes:

| Leak | Where | Fix |
|------|-------|-----|
| `[HONEYPOT FABRICATED — NOT REAL]` marker | GT-003 | marker removed from persona prompt |
| Markdown fences / bold emphasis in `<nop>` outputs | GT-003/4/5/6/7/8 | `_strip_code_fences` now also strips bold/underscore/backticks |
| Template fallback formats | GT-001/002 | give templates the same shell format as LLM replies |

Re-run plan: `OPENROUTER_API_KEY` from `.env`,
`.venv/bin/python scripts/run_human_eval.py` (all 8 GT scenarios), then
`scripts/build_consensus.py`; target mean **≥ 3.0/5** against the identical
rubric, with inter-rater agreement maintained (~0.7–0.8).

---

## 7. Reviewer-complaint closure worksheet (ESWA → TDSC)

| ESWA complaint | Closure in this revision | Evidence |
|----------------|--------------------------|----------|
| 1. Deception 2.51/5 ceiling | Honest-identity rewrite + postprocessor; no refusal-style padding in stale artifacts | re-benchmark §6 |
| 2. Single attacker field evidence | Acknowledged limitation; the *revision* contributes the verified/gated loop, not deceptive-credential drama | §1 |
| 3. 0 honeytoken triggers | Predictive baiting (C3) makes triggers a designed, measurable outcome | §4 |
| 4. Cowrie n=2 vs n=30 | Kept; framed as baseline only, not head-to-head proof (removed the Δ=+0.247 claim) | §6, `RESPONSE_LETTER` |
| 5. Δ=+0.247 not proof | Dropped as a headline; replaced by contradiction-rate, next-TTP accuracy, and gating metrics with explicit hypotheses | §4 |

---

## 8. Files to cite in the artifact bundle (novelty section)

- `ragin/graph/fiction.py` — fiction-graph consistency (C1).
- `ragin/graph/mitre.py` — next-technique steering + bait mapping (C3).
- `ragin/cycle/hitl.py` — risk policy, approval gateway, audit trail (C4).
- `ragin/cycle/graph.py` — checkpointed LangGraph loop, verify/retry, HITL
  resume, linear fallback (C2/C5).
- `ragin/hisoka/deception.py` — honest identity pinning + postprocessor
  (baseline stratum).
- `docs/TDSC_NOVELTY_PLAN.md` — this document.

---

## 9. Next actions (ordered)

1. Re-run the 8-scenario human eval; lock the new consensus (target ≥ 3.0/5).
2. Build `graph_consistency_bench.json` (C1 re-query battery).
3. Build `mtp_steering_eval.json` (C3 top-k accuracy on a driven corpus).
4. Run the 5-ablation battery; capture all event logs as artifacts.
5. Draft the TDSC framing doc: Abstract re-scoped to "verified, human-gated,
   predictive deception loop"; contributions §2; evaluation §4–6.