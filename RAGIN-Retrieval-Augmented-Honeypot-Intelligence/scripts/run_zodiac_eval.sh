#!/usr/bin/env bash
# =============================================================================
# run_zodiac_eval.sh — one-command live human-eval re-run on the zodiac stack
#
# Pre-flight gates (fail fast, spend nothing on failure):
#   1. zodiac services  — hisoka/chrollo/don health (tailnet IP)
#   2. redis            — native service ping
#   3. .env keys        — RAGIN_LLM_* present, model names set
#   4. model catalog    — RAGIN_LLM_MODEL & EVAL_MODEL exist on the provider
#   5. quota probe      — 1-token chat; refuses on 429/402 (allowance spent)
#
# Modes:
#   ./scripts/run_zodiac_eval.sh            # full: 8 scenarios + scoring
#   ./scripts/run_zodiac_eval.sh --smoke    # 1 scenario + scoring (quota discipline)
# =============================================================================
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"
PY="${REPO}/.venv/bin/python"
[ -x "$PY" ] || PY=python3

TS_IP="${RAGIN_TS_IP:-REDACTED_OPERATOR_HOST}"
API_KEY="${RAGIN_API_KEY:-$(grep -E '^RAGIN_API_KEY=' .env | cut -d= -f2-)}"
STAMP="$(date +%Y%m%d_%H%M%S)"
SMOKE=0
[ "${1:-}" = "--smoke" ] && SMOKE=1

say()  { printf '\n\033[1;36m== %s\033[0m\n' "$*"; }
ok()   { printf '  \033[0;32m✔ %s\033[0m\n' "$*"; }
warn() { printf '  \033[0;33m⚠ %s\033[0m\n' "$*"; }
die()  { printf '  \033[0;31m✘ %s\033[0m\n' "$*"; exit 1; }

# ── load .env ────────────────────────────────────────────────────────────────
set -a; # shellcheck disable=SC1091
. ./.env; set +a
[ -n "${RAGIN_LLM_API_KEY:-}" ] || die ".env missing RAGIN_LLM_API_KEY"
[ -n "${RAGIN_LLM_BASE_URL:-}" ] || die ".env missing RAGIN_LLM_BASE_URL"
ok "keys present (apmix: ${RAGIN_LLM_BASE_URL})"

# ── gate 1: zodiac services ──────────────────────────────────────────────────
say "Gate 1/5 — zodiac stack ($TS_IP)"
curl -sf --max-time 5 "http://$TS_IP:8083/health" >/dev/null || die "hisoka :8083 not healthy — systemctl --user restart ragin-hisoka"
ok "hisoka :8083"
curl -sf --max-time 5 -H "X-API-Key: $API_KEY" "http://$TS_IP:8081/health" >/dev/null \
  || die "chrollo :8081 not healthy — systemctl --user restart ragin-chrollo"
ok "chrollo :8081 (auth)"
curl -sf --max-time 5 -H "X-API-Key: $API_KEY" "http://$TS_IP:8082/health" >/dev/null \
  || die "don :8082 not healthy — systemctl --user restart ragin-don"
ok "don :8082 (auth)"

# ── gate 2: redis ────────────────────────────────────────────────────────────
redis-cli ping 2>/dev/null | grep -q PONG || die "redis not answering — systemctl start redis"
ok "redis PONG"

# ── gate 4: model catalog (before burning the quota probe) ───────────────────
say "Gate 4/5 — model catalog on provider"
CATALOG="$(curl -sf --max-time 15 "$RAGIN_LLM_BASE_URL/models" -H "Authorization: Bearer $RAGIN_LLM_API_KEY")" \
  || die "cannot reach $RAGIN_LLM_BASE_URL/models — provider down or key invalid"
for m in "${RAGIN_LLM_MODEL:-}" "${RAGIN_DON_MODEL:-}" "${EVAL_MODEL:-}" "${RAGIN_HISOKA_MODEL:-}"; do
  [ -n "$m" ] || continue
  echo "$CATALOG" | grep -q "\"$m\"" || die "model '$m' not in provider catalog — update .env (catalog: $(echo "$CATALOG" | grep -oE '"[^"]*free[^"]*"' | tr -d '"' | tr '\n' ' '))"
  ok "$m in catalog"
done

# ── gate 5: quota probe (1 token) ────────────────────────────────────────────
say "Gate 5/5 — apmix quota probe (1 token)"
HTTP="$(curl -sS -o /tmp/ragin_quota_probe.json -w '%{http_code}' --max-time 30 \
  "$RAGIN_LLM_BASE_URL/chat/completions" \
  -H "Authorization: Bearer $RAGIN_LLM_API_KEY" -H "Content-Type: application/json" \
  -d "{\"model\":\"$RAGIN_LLM_MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"ok\"}],\"max_tokens\":1}")" || die "provider unreachable"
case "$HTTP" in
  200) QUOTA_STATUS="live"; ok "quota live — GO" ;;
  429|402)
    QUOTA_STATUS="exhausted"
    grep -oE '"message":"[^"]*"' /tmp/ragin_quota_probe.json | head -1
    ;;
  404) QUOTA_STATUS="model_not_found" ;;
  *)   QUOTA_STATUS="provider_error_$HTTP" ;;
esac
# Persist the probe outcome so the snapshot doc renders live quota truth
# (results/azure_services_snapshot.md reads this file on every refresh).
# Atomic (tmp + mv): an interruption must never leave the 0-byte file that
# breaks every consumer that json.loads()s this path. Schema-compatible with
# the canonical watch probe (scripts/check_apmix_catalog.py): the rich keys
# plus audit_pipeline {"status": "skipped"} so the watch's test contract
# (tests/unit/test_watch_audit_pipeline) survives an eval run landing
# between scheduled watches. Legacy status/http_code/model keys stay for
# render_validation_section.py's dual-schema read.
STATUS_JSON="results/apmix_quota_status.json"
STATUS_TMP="${STATUS_JSON}.tmp"
STATUS_HTTP="${HTTP:-0}" STATUS_QUOTA="$QUOTA_STATUS" STATUS_MODEL="${RAGIN_LLM_MODEL:-}" \
  STATUS_CATALOG="$CATALOG" \
  "$PY" - "$STATUS_TMP" <<'PYEOF'
import json, os, sys, time

out = sys.argv[1]
http = int(os.environ.get("STATUS_HTTP") or 0)
quota = os.environ["STATUS_QUOTA"]
model = os.environ.get("STATUS_MODEL") or ""
try:
    data = json.loads(os.environ.get("STATUS_CATALOG") or "{}").get("data", [])
    catalog = {m.get("id") for m in data if isinstance(m, dict)}
except (json.JSONDecodeError, AttributeError):
    catalog = set()

probe = {
    "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "models_wired": [m for m in (model, os.environ.get("RAGIN_DON_MODEL"),
                                  os.environ.get("EVAL_MODEL"),
                                  os.environ.get("RAGIN_HISOKA_MODEL")) if m],
    # gate 4 verified every wired model is listed before this probe ran
    "catalog_http": 200,
    "catalog_models": sorted(catalog),
    "catalog_status": "ok",
    "quota_http": http,
    "quota_status": quota,
    # legacy keys (old flat schema) kept for the snapshot renderer
    "status": quota,
    "http_code": http,
    "model": model,
    # this script never runs the reseed stage — the scheduled watch owns it
    "audit_pipeline": {"status": "skipped",
                       "detail": "zodiac eval gate-5 probe; reseed owned by check_apmix_catalog.py"},
}
with open(out, "w") as f:
    f.write(json.dumps(probe, indent=2) + "\n")
PYEOF
mv -f "$STATUS_TMP" "$STATUS_JSON"
case "$HTTP" in
  200) : ;;
  429|402) die "allowance still exhausted — wait for the monthly reset, then re-run this script" ;;
  404) die "model rejected at chat endpoint — catalog mismatch, check .env" ;;
  *)   die "unexpected HTTP $HTTP — see /tmp/ragin_quota_probe.json" ;;
esac

# ── run ──────────────────────────────────────────────────────────────────────
OUT="results/human_eval_zodiac_${STAMP}.json"
if [ "$SMOKE" -eq 1 ]; then
  say "RUN (smoke) — 1 scenario"
  $PY scripts/run_human_eval.py --output "$OUT" --limit 1
else
  say "RUN (full) — 8 scenarios"
  $PY scripts/run_human_eval.py --output "$OUT"
fi

say "SCORE — evaluator: ${EVAL_MODEL:-} (independent judge)"
$PY scripts/score_human_eval.py --input "$OUT" --output-dir "results/human_eval_scored_${STAMP}"

say "DONE"
if [ "$SMOKE" -eq 1 ]; then
  echo "Smoke passed. Fire the full run:  ./scripts/run_zodiac_eval.sh"
else
  echo "Results:  $OUT"
  echo "Scored:   results/human_eval_scored_${STAMP}/"
  echo "Compare vs baseline 2.83/5 (M5 honest) — target ≥ 3.14"
fi
