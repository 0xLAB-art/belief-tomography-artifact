# RAGIN Threat Model and Claim Boundaries — 2026-10-08

Scope: this document freezes the security framing required by Workstream A of
`docs/superpowers/plans/2026-10-08-sp-hard-blocker-closure.md` and responds to
finding F1 of `docs/SP2027_HARD_REVIEW_2026-10-08.md`. It is a claim-boundary
artifact: every property row states what is trusted, what the adversary may
do, which artifact supports the property, and what the evidence does **not**
establish (nonclaim). Wording in the paper must not exceed the "Allowed wording" column.

System under model (from `README.md`, `docs/ARCHITECTURE.md`, `paper/`):

- The **serving path** is Profile → Retrieve → Fiction Graph → Draft → Verify
  → Serve, with deterministic fallback (R0) and an HITL gate.
- Components: LLM Gateway (Rust/Axum), Chrollo (R1 classifier), Don (R2 RAG),
  Hisoka (R3 deception layer), Jev (folded-down top rung), Redis /
  Prometheus / Grafana.
- Jev (adaptive kind-aware routing) is **off the serving path**: its measured
  Δ = 0.0 at benchmark ceiling was compiled down to a deterministic floor.

## 1. Trusted computing base (trusted components)

| Trusted component | Why trusted | Failure mode if wrong |
|---|---|---|
| Deterministic verifier (danger / identity / consistency / degenerate / supported-claim checks) | It is the fail-closed gate; its rules are the safety contract | Attacker-adaptive drafts that satisfy the closed rule set are served |
| Fiction-graph session state store | Verifier binds every host fact to one per-session graph | Cross-session contamination; stale facts served as current |
| Canary secret registry | Bait is registered secrets only; any canary in egress is attributed to bait interaction by construction | Real secrets exposed or bait not attributable |
| Deterministic fallback transcripts (R0) | Vetted offline; used when generation or verification fails | Unvetted content served on failure paths |
| LLM Gateway auth + provider routing | Owns provider keys, retries, cost tracking | Key compromise changes the provider trust assumption (historical pentest record was redacted/rotated — see README security note) |
| Append-only audit log (`results/hitl_audit_bench.jsonl`) | All accept/reject/HITL decisions persist for audit | Tampering invalidates the accountability trail |
| Human HITL gate | Last-resort human approval before serve | Operator error is outside the mechanized property |

## 2. Attacker capabilities (explicit, not assumed away)

| ID | Capability | Relevant property |
|---|---|---|
| ATK-1 | Observe and respond to served transcripts; re-query the same session or fresh sessions | P1 consistency, P3 no unverified serves |
| ATK-2 | Inject instructions into attacker-controlled input (prompt injection against Don/Hisoka/Jev) | P4 supported-claim / injection robustness |
| ATK-3 | Supply or influence CTI content attempts (poisoning, stale data, adversarial corpus rows) | P5 quarantine/screening, not open-world correctness |
| ATK-4 | Cross-session interaction: attempt to carry state across sessions or tenants | P2 isolation by fiction-graph binding |
| ATK-5 | Malformed outputs: trigger degenerate, empty, or non-shell responses | P1 degenerate-check fail-closed |
| ATK-6 | Retry / resource abuse: high-rate queries, large payloads, retry amplification | P6 availability via fallback, cost/latency bounds (not yet measured at scale) |
| ATK-7 | Adaptation against the verifier's closed rule set over many rounds | Limits of P1/P4 — no open-world guarantee |
| ATK-8 | Provider-side compromise or provider refusal/availability failure | Availability property degrades to fallback; provider trust is out of scope |
| ATK-9 | Operator / HITL failure (rubber-stamping approvals) | Human failure is outside the mechanized property |
| ATK-10 | Local host compromise of the RAGIN host itself | Out of scope for the in-system verifier properties (deployment hardening is a prerequisite) |

## 3. Property / evidence / nonclaim matrix (canonical table)

| ID | Security property | Trusted components | Attack surface | Evidence artifact / command | Nonclaim (explicit) | Allowed wording |
|---|---|---|---|---|---|---|
| P1 | Verifier rejects identity violations, contradictions with the session fiction graph, unsupported command answers, and malformed shell responses | Verifier, fiction graph, fallback | ATK-1, ATK-5, ATK-7 | `results/verifier_redteam.json` (105 cases, P=R=1.000 on the declared suite); `results/verifier_redteam_cross_family.json`; `scripts/verifier_redteam_check.py` | Not open-world resistance; closed declared surface only; does not certify realism | "Passed the declared deterministic test suites and failed closed on the evaluated cases." |
| P2 | Session/host facts are bound to a single fiction graph; no cross-session contamination in the evaluated suite | Fiction graph store | ATK-4 | `results/graph_consistency_bench.json` (0 contradictions / 45 re-queries, byte-identical replay); `results/cross_session_consistency_bench.json` | Closed workload only; not a guarantee under arbitrary tenant pressure | "Zero observed in the 45 re-query and recorded audited workload; not an open-world guarantee." |
| P3 | No unverified serves; any generation/verification failure falls back to vetted deterministic transcripts | Verifier, R0 fallback, HITL gate | ATK-1, ATK-5, ATK-6, ATK-8 | `results/live_benchmark_zodiac_20260922.json` (218-row campaign, 0 unverified serves); `results/ablation_battery.json` (removal of the verifier costs the property) | Bounded by the recorded campaign; not a live-field guarantee | "Zero unverified serves in the recorded audited workload." |
| P4 | Supported-claim check grounds served answers in the curated corpus; prompt injection gets no extra privilege | Verifier supported-claim check, Don retrieval | ATK-2 | `results/verifier_redteam_supported_claims.json` (123 cases); cross-family artifact exposes transfer limits | Closed-surface recall only; open-ended recall untouched | "Supported-claim screening holds on the evaluated case families." |
| P5 | CTI pipeline screens/quarantines suspect corpus content | Don ingestion path, CTI curation | ATK-3 | `scripts/cti_manual_audit.py` workflow artifacts (`results/cti_manual_audit*.json`) | Implementation-level screening; no live poisoning attack evaluation yet | "Screening/quarantine mechanisms exist; poisoning resistance is not yet evaluated adversarially." |
| P6 | Availability under failure: fallback keeps the session coherent; cost/latency pressure degrades to deterministic service | R0 fallback, gateway retries, cost tracking | ATK-6, ATK-8 | `results/ablation_battery.json`; fallback path in the serving loop; no dedicated field campaign yet | No measured field availability under real attacker load | "Deterministic fallback covers failure paths in the offline battery; field availability is not yet measured." |
| P7 | Bait is attributable: registered canaries appear only as deployed bait | Canary registry | ATK-1 | `results/human_eval_scored_20260922_180637_consensus/` rubric (canaries scored as bait); README safety guarantee | Attribution assumes the registry is complete and the host is not compromised | "Canary hits are attributable to bait interaction by construction." |
| P8 | Bounded intelligence spend: mechanisms past the certifiable point (Jev routing) compile down; no adaptive-security benefit is claimed | Jev fold-down artifacts, fusion/benchmark ceiling | ATK-7 | `results/jev_ab_eval.json` (Δ = 0.0 at ceiling), `results/jev_hard_subset.json` (6 informative sessions, 1 rescued, 5 provider refusals), `results/sp2027_rescue/behavior_trajectory_benchmark.json` (self-consistency only) | Rescue controller benchmark is self-referential against its own floor; not independent effectiveness evidence | "Exploratory controller validation; provider-free self-consistency audit." |
| P9 | Auditability: every accept/reject/HITL decision persists | Append-only log | ATK-9 | `results/hitl_audit_bench.jsonl`; `results/stability_run1_vs_run2.json` | Log integrity is assumed (append-only property not adversarially tested) | "Decisions are persisted to an append-only log; integrity under attack is future work." |
| P10 | Grounding lift (+.154 composite, CI [+0.092, +0.221]) is an archived, model-coherent analysis-channel comparison | Don vs no-RAG arms, bootstrap | — | `results/b4_baseline_zodiac_20260922.json`; `results/bootstrap_ci.json`; `scripts/bootstrap_ci.py` | Pairing contract under-specified (no canonical IDs/hashes yet); not a clean served-text result; echo-guarded offline rescore changes the served-text picture | "Archived model-coherent analysis-channel comparison reports +.154; independent causal reproduction remains to be completed." |

## 4. Deployment boundary and non-scope

- The deployment is tailnet-only/private-access first; there is no
  multi-tenant isolation evidence and no ambient-attacker traffic sample.
  The field protocol (Workstream F) remains `READY-FOR-VPS`/`BLOCKED-EXTERNAL`.
- Provider/quota availability blocks fresh provider-backed reruns
  (`results/apmix_quota_status.json`); all live numbers are archived evidence.
- Host escape, container escape, and operator collusion are outside the
  in-system properties; they are handled by deployment hardening
  (`docs/SECURITY_HARDENING.md`, `docs/DEPLOYMENT_CHECKLIST.md`), not by the
  verifier matrix.
- The rescue benchmark's risk floor is derived from its own controller; it
  is self-consistency evidence only (`docs/RAGIN_RESULTS_LEDGER_2026-10-08.md`).

## 5. Held-out verifier stress backlog (Workstream A follow-up)

Cases listed in the plan must be independently constructed (not derived from
the verifier's rules) before any stronger wording is used: prompt injection,
CTI poisoning, cross-session contamination, malformed output, retry/resource
abuse, and verifier adaptation. Until they are run and archived, the P1–P4
rows keep their closed-surface wording.

## 6. Traceability

| Source | How this doc uses it |
|---|---|
| `docs/SP2027_HARD_REVIEW_2026-10-08.md` F1, F8, claim-boundary audit | Property rows mirror its "Allowed wording now" column verbatim |
| `docs/superpowers/plans/2026-10-08-sp-hard-blocker-closure.md` §A | Scope, stress-case list, closed-surface boundary rule |
| `docs/RAGIN_RESULTS_LEDGER_2026-10-08.md`, `docs/RAGIN_RELEASE_MANIFEST_2026-10-08.md` | Artifact inventory and classification |
| `scripts/validate_release_artifacts.py` (new) | Enforces that every canonical appendix reference resolves from the repo root with an explicit prefix |
