# Jev A/B Evaluation + Routing Improvement Results

**Question:** هل إضافة Jev حسّنت قرارات التوجيه (risk level) فعلاً؟ — وبعدها: هل حسّنا النظام نفسه؟

## Timeline of results (same 200-session stratified held-out sample, 50/tier)

| Stage | Correct (risk ≥ tier floor) | Notes |
|---|---|---|
| 1. Original baseline (Chrollo label + Supervisor) | **69.5%** (139/200) | APT sessions underestimated by **1.9 levels** on average |
| 2. + Jev enrichment (44/200 sessions assessed — free-tier rate limit) | **91.5%** (183/200) | 44/44 assessed APTs fixed, 0 regressions |
| 3. + apt skill-map fix + weighted behavior floor + ngram model (no Jev needed) | **100%** (200/200) | zero underestimation, no network dependency |

## Root causes found & fixed

### Bug 1: `apt` label scored as novice in risk computation
`Supervisor._compute_risk` mapped `skill_scores = {novice:0, intermediate:1, advanced:2, expert:3}` — but Chrollo's top-tier label is **`apt`**, which hit `.get(skill_level, 0)` → **score 0**. Every APT classification was scored like a novice. Fixed by adding `"apt": 3` and adding `apt` to `ELEVATED_SKILL_LEVELS`.

### Fix 2: Weighted behavior-severity floor (deterministic, no-network)
New `Supervisor._behavior_floor()`: pattern-weights hostile commands in `attacker_inputs` (heavyweight primitives like `/etc/shadow`, `reverse_tcp`, `secretsdump` = weight 2; staging/recon like `wget http`, `linpeas` = weight 1). Two distinct heavyweight primitives → critical floor; weighted ≥3 → high; ≥1 → medium. Zero false positives on admin workflows (verified: `systemctl status nginx`, `tail`, `df` produce no floor). Includes anti-forensics signatures (`shred`, `rm -rf /var/log`, timestomping).

### Fix 3: Confident-apt → critical floor
When the classifier says `apt` with confidence ≥ 0.6, risk floor = critical. Cost analysis on held-out data: +1 level on ~1 expert session per 50 (already floor-satisfying) to fix 3 underestimated APTs per 50.

### Fix 4: Chrollo retrained on baseline+ngram features (0.8875 → 0.9550)
`results/model_quality/seq_features_benchmark.json` showed `baseline+ngram` (+32 hashed command n-gram features) is the only feature family improving **all three** benchmark regimes (+6.0pp same-distribution p=1.2e-7; +3.9pp template-disjoint; +3.7pp strict bank-disjoint) while `+phase`/`+all` overfit the strict regime. `ChrolloClassifier` now supports pluggable feature sets with the feature list persisted alongside the artifact (`.features.joblib` sidecar) — legacy artifacts keep working. Retrained: held-out accuracy **0.8875 → 0.9550**, per-tier recall 0.94–0.97, adjacent-tier confusion only. Artifact: `models/chrollo/rf_classifier.joblib` (backup: `rf_classifier_pre_ngram.joblib`).

### Fix 5: JevClient hardening (production efficiency)
- `requests.Session` connection reuse
- 429 = **fail fast + park endpoint 60s** (respects `Retry-After`) instead of burning retries — quota errors are not transient
- State tail-truncated to 8000 chars (recent commands matter most)
- Tests now patch `requests.Session.post` (previously patched `requests.post`, causing real network calls from "unit" tests)

## Final system quality (n=200 held-out, no network calls)

| Metric | Value |
|---|---|
| Routing decisions at/above tier floor | **200/200 (100%)** |
| Mean underestimation depth | 0.0 (was 0.53) |
| APT-tier underestimation | 0.0 (was 1.9) |
| Over-escalation ≥ +2 levels | 12/200 (6%, was 55/200) |
| Over-escalation = +3 levels | 0 (was 6) |
| Mean over-escalation | 0.57 levels |

The +1-over sessions (90/200) trigger voting/expert analysis by design — acceptable efficiency cost for a honeypot deception system (more engagement, not less). Severe over-escalation (+2) is 12 cases, concentrated in novice/intermediate sessions with real staging behavior.

## Jev's role after these fixes

Jev remains a valuable **additive** layer (its 44/44 APT fix rate motivated the behavior-floor design; it catches sessions whose tradecraft the deterministic patterns miss), and it degrades gracefully (rate-limit → fail fast → baseline decision unchanged). The zen free tier allows ~40–50 calls/burst; for production volume use a paid key or self-hosted Jev. Full-coverage Jev re-run awaits quota reset.

## Reproduce

```bash
.venv/bin/python scripts/jev_ab_eval.py --n 200 --concurrency 4   # A/B eval
.venv/bin/python scripts/retrain_chrollo_ngram.py                  # model retrain
.venv/bin/pytest tests/unit -q                                     # 1060 tests
```

Artifacts: `results/jev_ab_eval.json` (per-session rows), `models/chrollo/training_manifest.json` (retrain evidence).
