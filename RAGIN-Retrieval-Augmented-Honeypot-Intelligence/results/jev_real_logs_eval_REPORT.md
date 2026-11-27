# Jev on REAL Traffic — The Decisive Evaluation

**Question:** هل Jev يستحق بعد ما النظام بقى 100% على الـ synthetic benchmark؟

**Answer: نعم — وبقوة. على الحركة الحقيقية الوضع معكوس تماماً: الـ baseline (بكل إصلاحاتنا) فاشل 13/13، وJev صحّح 12/13.**

## Setup

- **Data:** 13 real Cowrie honeypot sessions (`data/cowrie_logs/`), 46 commands total — captured live traffic, not generated.
- **Ground truth:** expert severity labels per session family (enumeration bot=medium, shadow-read/SSRF/lateral=high, exfil+implant/persistence=critical).
- **Baseline:** Chrollo(ngram) → Supervisor.route() **including** all our fixes (apt map, weighted behavior floor, confident-apt floor).
- **With Jev:** same + `JevRoutingSignal.adjust_risk()`.
- **Endpoint:** Vercel AI Gateway `typesafe/v1/systemone` (`typesafe-ai/jev`) — zen free tier was exhausted (7.2h Retry-After); same System One protocol.

## Results

| Path | at/above expert severity |
|---|---|
| Baseline (all fixes, no Jev) | **0/13** |
| Baseline + Jev | **12/13** |

Every single real session was improved or held by Jev; 11/13 were corrected outright.

### Why the baseline collapsed on real traffic (domain shift)

1. **Chrollo:** trained on synthetic templates → labels **all 13 real sessions `novice`** (conf 0.51–0.92). The RF never saw real command distributions.
2. **Behavior floor:** real attackers here are subtle — the enumeration bot (`whoami/id/uname/cat /etc/passwd/ls/ps`) matches **zero** hostile patterns → no floor; shadow-read sessions have one heavyweight signal → medium (truth: high). Short sessions = few signals = weak floor.

### Jev's severity on real traffic is well-calibrated and monotonic with expert labels

| Family (truth) | Jev severity | Jev kind |
|---|---|---|
| network scanning (medium) | 0.74 | scanning |
| enumeration bot (medium) | 0.93–0.99 | scanning |
| cloud-metadata SSRF (high) | 1.66 | scanning |
| shadow read (high) | 1.97–1.99 | scanning |
| exfil + implant (critical) | 2.98 | exploit |
| persistence implant (critical) | 2.99 | persistence |

The only remaining miss: **lateral movement pivot** (truth high, Jev medium — `ssh`+`scp`+`ssh-keyscan` treated as recon-grade). One 1-level underestimate, vs baseline's 1–2 level misses on every session.

## The two evaluations together tell the real story

| Eval | Baseline alone | Baseline + Jev | Jev delta |
|---|---|---|---|
| Synthetic 200 (patterns tuned on it) | 100% | (n/a — quota) | ≈0 |
| **Real Cowrie 13 (no tuning)** | **0%** | **92%** | **+92pp** |

The synthetic 100% is partly **circular**: the behavior-floor patterns were designed after seeing what that generator produces. On traffic the patterns never saw, they fail completely — and Jev (a learned model) carries the system. This is exactly the generalization gap a honeypot faces in production.

## Verdict

**Jev يستحق — على البيانات الحقيقية هو الفرق بين 0% و92%.** الخلاصة المحدّثة للدور:

- **Production traffic:** Jev is the *primary* severity signal, not a safety net. Keep `RAGIN_JEVI_ENABLED=1`.
- **Resilience:** zen free tier limits ~40–50 calls/burst; the Vercel AI Gateway route works with a paid key and survived this full run. The client fails fast and degrades to baseline — no availability risk.
- **Recommended next:** feed Jev's `attack_kind` (scanning/exploit/persistence/...) into Hisoka persona selection, and extend the behavior floor with the two families it missed (cloud-metadata probing, lateral pivoting) — but the generalization lesson stands: patterns freeze, models adapt.

## Reproduce

```bash
RAGIN_JEVI_BASE_URL=https://ai-gateway.vercel.sh/typesafe/v1 \
RAGIN_JEVI_API_KEY=<vck key> RAGIN_JEVI_MODEL=typesafe-ai/jev \
.venv/bin/python scripts/jev_real_logs_eval.py
# -> results/jev_real_logs_eval.json (per-session rows)
```

---

## Update: attack_kind wired into Hisoka persona strategy

Jev's `attack_kind` classification now steers Hisoka's deception strategy (additive — no Jev signal means unchanged behavior):

| Jev kind | Engagement objective | Deception posture |
|---|---|---|
| `scanning` | maximize recon surface | convincingly reveal broad-but-shallow surface, mild misconfigurations |
| `bruteforce` | steer to honeytoken credentials | realistic auth failures; make planted tokens attractive |
| `exploit` | contain in fiction | let exploits "succeed" against sandboxed fiction, keep chain alive |
| `persistence` | fake success, return visits | implants appear installed; attacker returns to a box they "own" |
| `lateral` | expose decoy topology | believable 10.x hosts, fake db/backup services, token-pointing creds |

**Wiring paths (all supported):**
- top-level `session_context["jev_assessment"]` (e.g. `/api/assess` output posted to `/api/deceive`)
- `classification.jev_assessment` (Chrollo `process_with_jev` output riding the harness context)
- `/api/deceive` accepts an optional `jev_assessment` JSON field and passes it through

**Response metadata:** `DeceptionResponse.metadata` now carries `jev_attack_kind`, `jev_severity`, `jev_attack_probability`, `jev_objective` when a signal is present — giving the SIEM/audit layer the behavioral classification that shaped the deception.

Persona selection remains skill-matched (Chrollo); the kind signal changes *how* the persona engages, not *who* it is. Tests: `tests/unit/test_hisoka.py::TestJevKindStrategy` (8 tests).
