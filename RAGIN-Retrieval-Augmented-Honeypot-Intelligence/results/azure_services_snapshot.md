# RAGIN Azure Services — Snapshot

- **Snapshot time:** 2026-09-22 18:00 UTC
- **Resource group:** `ragin-honeypot-rg`

## Container Apps

| Service | Provisioning | Replicas | FQDN |
|---|---|---|---|
| redis | Failed | 0 | — |
| chrollo | Failed | 0 | — |
| don | Failed | 0 | — |
| hisoka | Failed | 0 | — |

## Virtual Machines (free-tier Plan A)

| VM | Size | State | Public IP |
|---|---|---|---|

## ACI

| Name | Provisioning |
|---|---|
| ragin-cowrie-hp | Succeeded |

## /health probes

## Zodiac-native stack (Plan B, zero-cost, tailnet-only)

- chrollo: HEALTHY at http://REDACTED_OPERATOR_HOST:8081 (systemd --user, tailnet-only)
- don: HEALTHY at http://REDACTED_OPERATOR_HOST:8082 (systemd --user, tailnet-only)
- hisoka: HEALTHY at http://REDACTED_OPERATOR_HOST:8083 (systemd --user, tailnet-only)

## Compute-plane billing signal
```
ERROR: (ReadOnlyDisabledSubscription) The subscription '8110178a-4797-4682-88b1-3aa5db08b521' is disabled and therefore marked as read only. You cannot perform any write actions on this subscription until it is re-enabled.
Code: ReadOnlyDisabledSubscription
Message: The subscription '8110178a-4797-4682-88b1-3aa5db08b521' is disabled and therefore marked as read only. You cannot perform any write actions on this subscription until it is re-enabled.
>>> SUBSCRIPTION COMPUTE SUSPENDED — fix billing
```
## TDSC validation artifacts

Numbers are rendered directly from the artifact JSONs by
`scripts/render_validation_section.py` — refresh via `scripts/azure_healthcheck.sh`.

### C1 — fiction-graph consistency (`graph_consistency_bench.json`)

| Proof | Metric | Value | Status |
|---|---|---|---|
| C1_contradiction_rate_zero | contradictions per re-query turn (graph-full) | 0.0 (target 0.0) | ✅ |
| C1_determinism | byte-identical replay rate (graph-full) | 1.0 (target 1.0) | ✅ |
| C1_identity_pin | pinned-host violations across re-query (graph-full) | 0 (target 0) | ✅ |
| C1_verify_before_serve | responses served after a FAILED verification (graph-full) — must be 0 | 0 (target 0) | ✅ |
| C1_mechanism_checks | graph/verifier mechanism probes | 5 (target 5) | ✅ |
| C1_baseline_gap | graph-full vs no-enforcement on enforced guarantees | verifier coverage full=45/45 turns vs none=0 | ✅ |

### §5 — ablation battery (`ablation_battery.json`)

| Ablation | Target metric | Result |
|---|---|---|
| A1_no-fiction | fiction facts seeded into plan (C1) | ✅ DEGRADES-AS-EXPECTED |
| A2_no-bait-steer | strategy/steer context seeded into plan (C3) | ✅ DEGRADES-AS-EXPECTED |
| A3_no-verify | responses served with no verification verdict (C2) | ✅ DEGRADES-AS-EXPECTED |
| A4_no-approval | REQUIRE-level gating capability (C4) | ✅ DEGRADES-AS-EXPECTED |
| A5_no-graph | battery completes via linear fallback (equivalence, not degradation) | ✅ EQUIVALENT |

### C3 — MITRE predictive baiting (`mtp_steering_eval.json`)

Next-TTP accuracy: top-1 0.5 · top-3 0.9 · MRR 0.6667 over 10 predictions

| Proof | Claim | Value | Status |
|---|---|---|---|
| C3_next_ttp_top3 | graph-informed prediction puts a next-turn technique in top-3 | 0.9 (target >= 0.80) | ✅ |
| C3_next_ttp_top1 | the top-ranked suggestion matches the actual next technique | 0.5 (target >= 0.40 (kill-chain prior, not oracle)) | ✅ |
| C3_steering_reaches_plan | steer IDs + bait for the next move are attached to the plan | 0.9 (target >= 0.80) | ✅ |
| C3_ablation_gap | removing bait steering (A2) collapses the bait signal | 0.4 (target >= 0.4 - 0.05) | ✅ |

### Statistical intervals (`bootstrap_ci.json`)

Disk-provable 218-row composite: **0.8796 [0.8572, 0.9]** (95%).

| Proof | Detail | Status |
|---|---|---|
| CI_c1_contradiction_upper_below_10pct | 0 contradictions over 45 turns; 95% CI upper 0.079 < 0.10 | ✅ |
| CI_c1_determinism_lower_above_90pct | byte-identical replay 45/45; 95% CI lower 0.921 > 0.90 | ✅ |
| CI_c3_top3_lower_above_50pct | top-3 9/10; 95% CI lower 0.596 > 0.50 (majority precision) | ✅ |
| CI_technique_pass_lower_above_80pct | technique pass 123/123; 95% CI lower 0.970 > 0.80 | ✅ |
| CI_actor_pass_lower_above_80pct | actor pass 35/35; 95% CI lower 0.901 > 0.80 | ✅ |
| CI_b4_paired_diff_computed | B4 paired RAG−no-RAG overall diff +0.154 [+0.092, +0.221] | ✅ |

✅ 0.855 provenance **resolved**: superseded by the persisted `live_benchmark_zodiac_20260922.json` run —
cite that artifact's composite instead.

### Live-LLM re-run readiness (apmix)

- ✅ quota **live** (probed 2026-09-22T15:06:40Z, model `deepseek-v4-flash-free`, HTTP 200)
- Wiring: generator/don `deepseek-v4-flash-free`, judge `grok-4.7-free` (independent judge)
- One command at reset: `./scripts/run_zodiac_eval.sh --smoke` → full run if clean

