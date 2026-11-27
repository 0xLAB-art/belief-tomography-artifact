# Fleet Census — 2026-11-18 (after 2-week soak, Nov 7→18)

**Access:** AWS SSM start-session (runCommand output capture broken on all instances — sessions used; plugin 1.2.835.0). Account REDACTED_ACCOUNT, eu-north-1.

## Fleet state

| Instance | IP | Container | Uptime | Disk |
|---|---|---|---|---|
| RAGIN-CORE (m7i-flex.large) | REDACTED_FLEET_HOST | ragin-core-staging **Up 11d** | host 41d | 5.2G/38G (14%) |
| RAGIN-EDGE (t3.micro) | REDACTED_FLEET_HOST | ragin-cowrie-staging **Up 12d** | — | — |
| RAGIN-INTEL (t3.micro) | REDACTED_FLEET_HOST | (no containers; intel+iv services on :8765/:8000 since Oct 25) | — | idle, 0 recent data |

EDGE listeners: socat `0.0.0.0:2222` → Cowrie (deception front), **sshd real-arm `0.0.0.0:2223`**, socat bridge-helper `172.29.0.1:18083`.

## The 2-week yield (Nov 7→18)

- **CORE deception plane: 3,413 served sessions** (mirrored `data/sessions` + `data/field/ragin`, 3,413 each; field plane total 3,692 incl. earlier days). Sessions carry **verification_passed + serve_path=TEMPLATE_FALLBACK_VERIFIED** and **per-session honeytoken deployment** (credential_0011+ seen). This is live deception serving — vs **0 deception-plane sessions** at the Nov-5 fleet check.
- **EDGE Cowrie: daily ambient 8–708 lines** (Nov 3–6 elevated 256–708; Nov 7–15 ambient 8–160; Nov 17: 263; today so far: 67) + **one burst: Nov 16 = 59,202 lines, 9,883 connects / 9,861 login.success**.
- CORE served-session days: Oct-25: 268, Nov-05: 145, Nov-06: 170, **Nov-16: 3,098** — i.e. the entire window's yield concentrates on Nov 16 (ratio served/connects ≈ 0.31).
- **All traffic arrives at Cowrie via the docker bridge (src 172.29.0.1)** — NAT'd; the pre-NAT source (real internet vs. a local driver like drive_cowrie.py / docker-compose.ab) is NOT yet attributed. **Nov-16 provenance is the open question for data validity.**
- Last activity: served sessions Nov 16 09:25; cowrie log last write Nov 16 23:56. **Nov 17–18: ambient only.**
- INTEL: services up since Oct 25, zero intel-plane data in the window.

## Reading

The soak proves the deception pipeline works end-to-end in the field (connect → serve → verify → honeytoken), but the 2-week window's dataset is dominated by one day (Nov 16) of unattributed provenance. Ambient internet scanning is present (Nov 3–6, 7–18 tail) but thin (tens-to-hundreds of lines/day).

## Nov-16 ATTRIBUTION VERDICT (same-session follow-up)

**Classification: scheduled machine prober (stress-test pattern), NOT organic attacker engagement, NOT our paramiko driver.**

Evidence chain (all from EDGE cowrie.json.2026-11-16 + CORE session files):
- Inter-connect gaps quantized at **exactly 60s** (35/40 sampled; one 120s) → minute-scheduler fingerprint, not network arrivals.
- Activity confined to **06:00–10:00 UTC** (3,764/22,732/22,712/9,815 per hour) then back to 5–10/h ambient.
- Client fingerprint: **9,837/9,876 connects = single `SSH-2.0-Go`** (our driver is paramiko; no local driver logs on Nov 16; no containers started on EDGE/CORE that day; CORE crons = e2scrub only; EDGE has our `ragin-field-census` cron only).
- **0 login failures** across 9,876 attempts (username root); **0 `cowrie.command.input`** events (exec-only, no interactive shell).
- CORE: **3,390/3,692 sessions byte-identical** (same `served_response_sha256` f745ca4cad8d…, `command_count:1`, `TEMPLATE_FALLBACK_VERIFIED` — the fiction replies "command not found" to an `echo -e` hex probe).

**Net reading:** a Go-SSH prober on a minute-cron (root login + one fingerprint command per connect) ran 4 hours. Candidate origin: external automated census scanner, OR a Go-based tool on the user's side (nuclei has an SSH protocol module and `~/nuclei-templates` was recently touched — **user to confirm**). It is nonetheless a genuine **durability result**: the deception pipeline sustained ~9.9k connects / 3.4k verified serves with per-session honeytokens for 4h at ~6/min without degradation.

**Paper consequence:** the 3,390 uniform sessions must NOT be used as real-attacker-diversity evidence; usable as load/durability evidence. Real-external evidence in the window remains scanner-grade ambient (8–708 lines/day) + ~302 heterogeneous historical sessions.

**Structural fix (required before the next soak):** all sources arrive NAT'd via the docker bridge (172.29.0.1) and socat keeps no connection logs (its 384k journal lines are a watchdog's "Address already in use" spam — a separate finding: something retries socat binds every ~2s indefinitely; locate and quiet it). Deploy **PROXY protocol** (socat/nginx stream → cowrie `proxy = yes`) so cowrie records true pre-NAT client IPs; optionally re-enable ufw LOG for 2222 to get kernel-level source evidence.

## Immediate continuations (decision needed)

1. **Attribute Nov-16** (driver vs internet): EDGE journalctl/socat logs for that window + CORE session template-duplication analysis. Determines whether the 3.4k sessions are field data or simulation — before anything touches the paper.
2. **Pull + analyze locally**: export CORE 3,413 sessions + EDGE cowrie daily logs → local corpus for deception-plane effectiveness vs scanner-grade ambient.
3. **Program continuation** (local): v11 deployed (20ed8994); optional gen-4, IND paper draft, or S&P/TDSC track — note response-letter files carry uncommitted edits and the Nov-17 submission gate has passed (user action; status unconfirmed).
