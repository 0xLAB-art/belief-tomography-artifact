# RAGIN — Project State Report (2026-10-24, end of day)

**One line:** Engineering and security posture at their all-time best (suite 2088/0 green, 11
pen-test findings fixed, git secured in 5 clean commits); research-realism gaps remain open
(no human raters, no field data) and are the focus of the remaining plan (see
`MASTER_PLAN_2026-10-24.md`).

---

## 1. System (what is actually running, verified from code)

- **Serving:** `ragin/server_v2.py` (aiohttp) — Harness + Session + Sandbox architecture.
  Mandatory verification: every draft passes FictionConsistencyVerifier (wrapped in
  StrictResearch + Deadline + HostFiction layers) → HITL approval → commit before any text
  reaches the attacker. Fail-closed everywhere (verified by live pentest probes).
- **Pipeline:** Chrollo (RF skill classifier) → Don (ThreatRAG: BM25/hybrid + command_aware_v2 +
  MITRE + LightRAG adapter + Evidence Judge) → Hisoka (adaptive deception, personas, dwell).
- **Decisions:** deterministic decision_fusion_v4 (EvidenceQualityGate + PolicySelector) is the
  authority; JEV and Laya are additive signals, default OFF.
- **LLM transport:** `GatewayClient` (Python, the live path) → apmix `claude-sonnet-4-6-free`
  (verified live 2026-10-24). Rust llm-gateway exists but is not the active serving path.
- **Multi-agent coordination:** Supervisor / VotingSystem / ExpertPool / DelegationChain inside
  the harness; HITL gate with honest semantics (human only at REQUIRE; AUTO/NOTIFY programmatic).

## 2. AI components status

| Component | Status | Evidence |
|---|---|---|
| **JEV** | ✅ WIRED LIVE + verified | beatapi Decisions API (`api.beatapi.io/v1/systemone`, `jev-1.14-free`); project client returns typed answers (live: p(recon)=0.97 on a scan session). Wire key is `instructions`; free tier 1 req/min (client has 60s cool-off). Gate study not yet run — that is the next research step. |
| **Laya** | 🧊 FROZEN as negative result | v12 final verdict `TUNING_FAIL_REDESIGN_REQUIRED` (2026-10-17): G4 0.786/0.9, G5 0.125/0.10, G7 0.281 vs 0.8 threshold (control itself 0.344 → contract problem, not model), G8 0.719/0.9, I2 fail. In-sample train report (acc 0.595→0.944) is calibration fit, not held-out. Server default OFF is the correct posture. 10 checkpoints (9.5 GB) on `/mnt/01DCDC2BF6665BC0/ragin_laya_gpu` — keep v12_final + reports, prune the rest. |
| **LLM chain** | ✅ LIVE (single model) | apmix key in gitignored `.env`; probe shows catalog ok / quota live / 1 model (`claude-sonnet-4-6-free`). Known gaps: no tested fallback model, no fast-path latency (measured ~44 s/command full path), Rust gateway vs Python client duality unresolved. |
| **Intelligence ladder** | ✅ measured (paper's core) | 4 rungs on the same loop; the fold-down result (kind-aware routing Δ=0 at benchmark resolution) is a headline finding, not a bug. |

## 3. Engineering health

- **Git:** working tree clean. Chain today:
  `705ba098` consolidation snapshot (3,088 files — v4 subsystem finally tracked) →
  `d3b87230` post-audit fix pass → `020c49aa` adversarial hardening (11 findings) →
  `a1aad28c` untrack .mimosa tooling state.
- **Tests:** `pytest tests/unit -q` → **2088 passed / 9 skipped / 0 failed** (first fully green
  run in project history; grew from 1992 by +96 hardening tests).
- **Don retrieval:** root cause fixed (BM25 raw-score clamp into IntelDocument.score; v2
  activation allowed in bm25 mode + provenance stamp). 10/10 test_don_v2.
- **Integrity:** `audit_integrity.py` restored (had been truncated to 0 bytes) + two latent bugs
  fixed (sign/verify canonical mismatch — no row could ever verify; seal annotation). Decoys
  http/ssh/telnet replaced with honest stubs (content never existed). Dead
  `_bridge_verifier_artifact` removed.
- **Knowledge graph:** `graphify-out/` refreshed (AST-only, per CLAUDE.md): 14,368 nodes /
  34,381 edges / 626 communities; god nodes Harness(163), Session(107), LightRAGAdapter(87).

## 4. Security posture (red-team wave 1, 2026-10-24)

Attack surfaces probed: serving layer (live HTTP repros), verification gate (payload battery).
**Fixed (all verified by regression tests):**
- Cross-attacker session takeover via transcript-prefix matching (owner token minting) — closed.
- Whole-honeypot freeze: global RLock + superlinear danger-regex (20 KB command = 110 s) —
  per-session lock sharding + compiled alternations.
- `/health` fingerprint dump unauthenticated — now `{"ok":true}` only.
- `_TRANSCRIPT_MAP` 16.8 GB pin — byte-budgeted; session-creation rate limit; closed-session
  500s → fail-closed 503; session_id traversal validation; mTLS boot-order gap; constant-time
  key compare; 413 for oversize bodies.
- **Verification gate:** 12/15 real secret shapes used to bypass `_contains_danger_signal`
  (ghp_/xoxb-/PEM/JWT/real-AKIA/zero-width/homoglyph/base64/hex). Now 0/11 attack payloads
  bypass: real-shape battery (exact-36 GitHub PATs, github_pat_, xox[baprs]-, PEM any-type,
  JWT eyJ…, exact-length AKIA/ASIA), hardened NFKC+zero-width view for the whole battery,
  command-shaped transports (base64-decode pipe, hex printf) in the pre-exemption hardened
  lane. Deception-fiction behavior unchanged (mysql scatter, authored fakes still behave
  identically); verifier red-team suite still 47/47 (precision 0.994 / recall 0.942).
**Held under attack:** API-key auth, mTLS layering (fail-closed boot, independent layering),
path normalization tricks, fail-closed serving discipline (no unverified text served in any probe).

## 5. Research evidence status (honest labels)

| Claim | Real status |
|---|---|
| Composite 0.880 [0.857, 0.900] | Reproduces exactly (bootstrap verified) — but it is a **serving-contract score**: 11/18 metrics definitional, actor rows fixed at 0.85 floor, honeytoken/artifact access structurally zero. Must be labeled as such in the paper. |
| "Human eval 3.86/5" | **Relabeled**: LLM-judge consensus (grok-4.7-free ×3 personas, agreement 0.750, 24/24 embedded match). No human rater anywhere in the chain. Old `human_eval_scored/consensus.json` had false provenance — corrected with `CORRECTION.md` + `superseded_by`. |
| Blind human packets r1–r5 | Prepared and delivered, **never answered** (`human_returns/` empty). Running them with 3–5 real raters is the cheapest realism upgrade available. |
| External baselines (cowrie 0.0006 → ragin 0.8474) | Reproducible from stored rows; order stable; but scoring channels were not uniform across arms and cowrie is structurally zero on a command-shaped workload. Frame as capability-comparison, not head-to-head. |
| Laya v12 gates | Verified reproducible from saved predictions (state_correct 35/60 and 51/60 recompute G6 exactly). Verdict stands on frozen absolute thresholds. |
| Verifier red-team | Real and strong: 47/47 artifact checks, precision 0.994 / recall 0.942 over 80 live cases. The project's crown jewel. Known honest boundary: 4/7 disclosures, 5/10 credential formats — report per-format, not one coverage figure. |

## 6. Field deployment (AWS eu-north-1)

- **CORE** `i-062a400b300f4f9e4` (m7i-flex.large): server_v2 pipeline mode, mTLS required,
  running since Oct 9. **EDGE** `i-05bc6aab0bd4260a7` (t3.micro): Cowrie + socat mTLS chain.
- **Audit result (live SSM, 2026-10-24): both ran 16 days EMPTY.** Zero sessions (EDGE log file
  does not exist), zero field exports, load 0.00. Causes: :2222 never exposed in any security
  group; mTLS certs (CA + EDGE) expired 2026-10-11 20:13 UTC (renewal was PREPARED, never
  executed); CORE LLM path deliberately blackholed (`127.0.0.1:9`).
- **Cost: $0.00 across the whole period** (credits cover it) — stopping them saves nothing.
- **Revival checklist (pending go/no-go):** renew certs → hardening/ethics review
  (`SECURITY_HARDENING.md`, `FIELD_ETHICS.md`; APPROVAL_REQUIRED items) → open :2222 → enable
  apmix path on CORE → external end-to-end probe → collect 12–14 days of real attacker data.

## 7. Docs corrected today (integrity pass, no numbers altered)

- PROJECT_STATUS.md / BENCHMARK_REPORT.md / README.md: "human eval" → "LLM-judge evaluation
  (grok-4.7-free ×3 personas — not human raters)".
- `docs/RAGIN_RESULTS_LEDGER_2026-10-08.md`: dated addendum — new bootstrap_ci sha, deception
  stability is 0.7433→0.7621 (not "unchanged"), live session counts (7,659), provider unblocked,
  bootstrap_ci holds 6 proofs (not "5/5").
- `results/human_eval_scored/consensus.json`: false provenance note corrected + superseded_by.
- `.env.example`: beatapi JEV endpoint documented (placeholder key only).
