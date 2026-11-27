# APMIX WRITER PROVENANCE AUDIT — 2026-10-23

Status: **RESOLVED — the writer is identified, scheduled, and behaving as designed.**

This audit answers the question raised at the end of the transcript-contract phase:
who is rewriting `results/apmix_probe_history.jsonl` and
`results/apmix_quota_status.json`, and is anything else affected.

**Correction to the previous phase's record.** The transcript-contract change
manifest states *"14 synthetic rows appended 2026-10-23T09:01Z"*. That was wrong.
Exactly **one** row was appended during that window, at
`2026-10-23T06:01:00Z` (= 09:01 local EEST). The 15 uncommitted rows visible in
`git diff` (Oct 16 → Oct 23) were appended by the same scheduled job in its
normal twice-daily runs; they are genuine historical probes, not synthetic
backfill. The word "unattributed" was an artifact of not knowing the writer's
identity at the time. The rows themselves were never fabricated, and nothing
that depended on them changed.

## 1. The writer

| Attribute | Value | Evidence |
|---|---|---|
| Script | `scripts/check_apmix_catalog.py` | `HISTORY`/`STATUS` at lines 37–38; append at line 158; `STATUS.write_text` at line 160 |
| Scheduling | systemd **user** timer `ragin-apmix-watch.timer` | `systemctl --user list-timers ragin-apmix-watch.timer` → NEXT Fri 2026-10-23 21:01:07 EEST; LAST Fri 2026-10-23 09:00:59 EEST |
| Unit files | `~/.config/systemd/user/ragin-apmix-watch.{service,timer}` | `systemctl --user cat`; service unit dated Sep 23 16:32, timer Sep 22 13:58 |
| Installed by | `scripts/install_apmix_watch.sh` (verbatim heredoc of the same units) | script body matches installed units |
| Calendar | `OnCalendar=*-*-* 09,21:00:00`, `RandomizedDelaySec=300`, `Persistent=true` | timer unit |
| Working directory | project root | `WorkingDirectory=` in service unit |
| Python | `.venv/bin/python` | `ExecStart=` in service unit |
| Environment | `.env` via `EnvironmentFile=` | service unit; script also calls `load_dotenv(ROOT/".env")` |
| Active since | 2026-10-22 14:23:22 EEST (current boot); the job has run since 2026-09-22 | `systemctl --user status`; history file first row `2026-09-22T10:58:02Z` |
| Current state | timer **active (waiting)**; last service run **failed, exit 1** | `systemctl --user status ragin-apmix-watch.service` |

Run at 09:01 local today, from the journal:

```
Oct 23 09:00:59 zodiac systemd[1643]: Starting ragin-apmix-watch.service ...
Oct 23 09:01:00 zodiac python[1315976]: [apmix-watch] network error: <urlopen error [Errno 111] Connection refused>
Oct 23 09:01:00 zodiac python[1315976]: [apmix-watch] catalog unreachable: HTTP 0
Oct 23 09:01:00 zodiac systemd[1643]: ragin-apmix-watch.service: Main process exited, code=exited, status=1/FAILURE
```

## 2. Why it fails

`.env` sets `RAGIN_LLM_BASE_URL=http://127.0.0.1:8731/v1` — a **local** endpoint,
not the apmix.ai provider. Nothing is listening on port 8731 (`ss -ltnp` finds no
listener), so every probe returns `catalog_http: 0 / unreachable`,
`quota_status: not_probed`, `audit_pipeline: skipped`, and exit 1. This is a
deliberate fail-safe shape: on an unreachable catalog the script never probes
quota and never runs the reseed step (both gated on `catalog_status`), so the
only side effect is one appended JSON line plus the overwritten latest-status
file.

## 3. What it writes

Only two files, both documented in the script's own docstring:

- `results/apmix_probe_history.jsonl` — append-only, one JSON line per run
- `results/apmix_quota_status.json` — latest probe, overwritten each run

History content by day: 72 rows, exactly 2 per day (09:0x and 21:0x local) since
2026-09-22, 1 row on days the machine was asleep at the other slot. Status
counter over all rows: 32 `drift`/`not_probed`, 32 `unreachable`/`not_probed`,
3 `ok`/`live`, 2 `ok`/`exhausted`, 2 `drift`, 1 `ok`/`network_error`. The last
reachable probe was 2026-10-08T18:03:22Z, when the audit reseed ran and
reported `ok — nothing to do`.

Two side-effect paths exist but are **gated off** while the catalog is
unreachable, so neither has fired since Oct 8:

- quota probe: `POST /v1/chat/completions`, `max_tokens=1`, only when
  `catalog_status == "ok"` (i.e. 1 token, twice a day at most)
- audit reseed: `scripts/reseed_audit_pipeline.py`, offline, only when the
  catalog is reachable. Its write targets are the judge-audited
  `results/live_benchmark_*_judgescored.json` artifacts (mtime: Sep 24–25,
  i.e. not touched recently)

## 4. Other paths and processes

- No other cron entry, `/etc/cron.d` file, or systemd unit in this repo's scope
  writes to `results/`. The only user crontab entries are two disabled
  `ACTS-Attack` lines from an unrelated project.
- Three sibling services run from this repo and are active
  (`ragin-chrollo`, `ragin-don`, `ragin-hisoka`, ports 8081–8083, started
  2026-10-22 14:23:22 EEST, `EnvironmentFile=.env.ragin-stack`). A 24-hour
  `find` over the repo (excluding venvs, `.git`, `graphify-out`, caches)
  shows **no** file they wrote; only my own phase artifacts, the apmix files,
  and pytest cache changed.
- The timer is still **active**; the next write will occur at
  2026-10-23 21:01:07 EEST (±300 s), and twice daily thereafter.

## 5. Consequences for claims

- `results/` is **not** byte-frozen for `results/apmix_probe_history.jsonl`
  and `results/apmix_quota_status.json`. The frozen inventory in the change
  manifests must name these two paths as scheduled writers' territory.
- No experiment artifact, session log, benchmark run, or paper file is touched
  by this writer. Nothing measured in the manuscript depends on these two
  files; the only consumer found is `scripts/render_validation_section.py`,
  which renders the provider-quota snapshot line.
- The rows are honest probe records: they document an unreachable local
  endpoint, not fabricated liveness.

## 6. Safe remediation proposal (no action taken)

The writer is correct and useful; the mismatch is that `.env` points the probe
at a local port that is not running. Options, in order of preference:

1. **Leave it running and document** (recommended for this phase). The probe is
   offline-safe by construction, costs zero tokens while unreachable, and its
   history is the provenance record for provider availability. Update any
   "frozen" claims to exclude these two paths.
2. **Point it at a real endpoint** only when the provider base URL is actually
   served locally (e.g. the loopback trace server) or the apmux bridge is up.
   Changing `RAGIN_LLM_BASE_URL` affects every other consumer of `.env`, so
   this must not be done casually and is out of scope for this phase.
3. **Mask the two paths in frozen inventories** — already done in the manifest
   via `frozen_inventory.changed_since_baseline`.

Do **not** delete or rewrite the history: it is the audit trail that explains
the mtime drift which triggered this investigation, and truncating it would
destroy the evidence that the writer behaves as designed.

Explicitly not done: no `systemctl stop`/`disable`, no file deletion, no
truncation, no restore-from-git. The timer will fire again at 21:01 local.
