#!/usr/bin/env bash
# =============================================================================
# install_apmix_watch.sh — schedule the apmix catalog+quota probe
#
# Installs a systemd --user service+timer that runs
# scripts/check_apmix_catalog.py twice daily (09:00 / 21:00 local):
#   - catalog drift (provider removed a wired model)  -> exit 2, ON FAILURE
#   - quota live (allowance reset)                    -> exit 0 + Journal note
#   - quota exhausted / payment_required              -> exit 0 (expected)
#   - audit pipeline reseeded after a new run, audited stability
#     verdict is ``review``                            -> exit 3, ON FAILURE
#     (surfaces loudly; see scripts/reseed_audit_pipeline.py)
#   - the probe also reseeds the judge-panel audit + audited stability
#     offline whenever a new campaign run lands (exit 0 if verdict stable)
#
# History:  results/apmix_probe_history.jsonl (append-only, git-tracked dir)
# Latest:   results/apmix_quota_status.json  (rendered by the snapshot doc)
#
# Ops:
#   systemctl --user status ragin-apmix-watch.timer
#   systemctl --user list-timers ragin-apmix-watch.timer
#   journalctl --user -u ragin-apmix-watch.service -f
#   systemctl --user start ragin-apmix-watch.service   # probe now
# =============================================================================
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$PROJECT_DIR/.venv/bin/python"
[ -x "$VENV" ] || VENV="$(command -v python3)"
UNIT_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"

mkdir -p "$UNIT_DIR"

cat > "$UNIT_DIR/ragin-apmix-watch.service" <<EOF
[Unit]
Description=RAGIN apmix catalog+quota probe (appends probe history)

[Service]
Type=oneshot
WorkingDirectory=$PROJECT_DIR
EnvironmentFile=$PROJECT_DIR/.env
ExecStart=$VENV $PROJECT_DIR/scripts/check_apmix_catalog.py
# exit 2 = catalog drift (important!), exit 3 = stability review (important!)
# exit 1 = probe failure
SuccessExitStatus=0 2
EOF

cat > "$UNIT_DIR/ragin-apmix-watch.timer" <<EOF
[Unit]
Description=Run the apmix catalog+quota probe twice daily

[Timer]
OnCalendar=*-*-* 09,21:00:00
RandomizedDelaySec=300
Persistent=true

[Install]
WantedBy=timers.target
EOF

systemctl --user daemon-reload
systemctl --user enable --now ragin-apmix-watch.timer

# --- first probe now (so history has a fresh entry immediately) -------------
echo "[install] running the first probe..."
systemctl --user start ragin-apmix-watch.service || true

echo
echo "[install] done. Timer:"
systemctl --user list-timers ragin-apmix-watch.timer --no-pager | head -4
echo
echo "[install] history: $PROJECT_DIR/results/apmix_probe_history.jsonl"
tail -1 "$PROJECT_DIR/results/apmix_probe_history.jsonl" 2>/dev/null || true
