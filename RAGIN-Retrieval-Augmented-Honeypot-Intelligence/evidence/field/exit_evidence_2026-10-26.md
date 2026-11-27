# Field Exit Evidence — 2026-10-26 (SSM collection)

Method: all figures computed **on the EDGE host** via SSM and exported only as
aggregates / hashed values. Raw cowrie `src_ip` values never left the endpoint
(FIELD_ETHICS §3). IP hashing = SHA-256 with salt `ragin-ip-v1` (same salt as
`ragin/utils.hash_ip`), truncated to 12 hex chars for display.

Hosts probed:
- **RAGIN-EDGE** `i-05bc6aab0bd4260a7` (public `REDACTED_FLEET_HOST`, priv `172.31.35.203`)
- **RAGIN-CORE** `i-062a400b300f4f9e4` (no public IP, priv `172.31.17.217`)
- (`RAGIN-INTEL` `i-0c0bd6b6a824b80b9` running; out of review scope. `0xzodiac` stopped.)

## A. §2 Hard-gate probes (SSM, both hosts, 2026-10-26T15:54Z)

| Probe | EDGE | CORE |
|---|---|---|
| `iptables -S OUTPUT` contains `-j RAGIN-EGRESS` | **YES** (63,436 pkts / 11M traversed) | **YES** (64,071 pkts / 11M traversed) |
| `iptables -L DOCKER-USER -n` | empty (0 rules) | empty (0 rules) |
| `FORWARD` policy | **DROP** (default-deny container egress via DOCKER-FORWARD/ufw-reject) | **DROP** |
| `RAGIN-EGRESS` terminal rule | `-j DROP` | `-j DROP` |
| **Neg control** root → `http://example.com:80` (not allowlisted) | **FAIL** (curl exit 124 = timeout/drop) | **FAIL** (exit 124) |
| **Neg control** root → `example.com:8080` | **FAIL** (exit 124) | **FAIL** (exit 124) |
| **Neg control** uid1000 → `https://example.com:443` | **FAIL** (exit 124) | **PASS** (200 — see exception) |
| root → `https://example.com:443` | PASS (200 — allowlisted `--uid-owner 0 --dport 443`) | PASS (200 — same) |

**Verdict — Egress allowlist gate: PASS.** The chain is genuinely attached to
OUTPUT and DROPs non-allowlisted egress (proven by the negative controls, which
time out). The earlier "must-fail" probe returning 200 was root→:443, which is
the **explicitly allowlisted** `--uid-owner 0 --dport 443` rule (the documented
"root:443 preserved" exception). CORE additionally allowlists
`--uid-owner 1000 --dport 443` (its service user), so uid1000→:443 succeeds
there by design.

Documented allowlist exceptions (host-layer, Oct 25 revival):
- EDGE: `lo`, RELATED/ESTABLISHED, `172.29.0.0/16`, `172.31.17.217:8443` (CORE),
  DNS 53, NTP 123, IMDS `169.254.169.254:80`, root→443, then DROP.
- CORE: `lo`, RELATED/ESTABLISHED, DNS/NTP/IMDS, `172.31.35.203/32` (EDGE),
  `172.31.16.167:8765` (INTEL), root→443, uid1000→443, then DROP.
- IPv6: DOCKER-USER empty on both; ufw default deny-in / allow-out.
- SG-layer egress still `all -> 0.0.0.0/0` (host-layer allowlist only) — an
  APPROVAL_REQUIRED item, unchanged.

## B. mgmt-plane isolation (inside view, `ss -tulnp`)

- **EDGE** listeners: `:2222` (socat → cowrie, the sole public honeypot
  listener), `172.29.0.1:18083` (socat → CORE mTLS staging), `:22` sshd bound
  0.0.0.0 but **ufw restricts :22 to operator IP `REDACTED_OPERATOR_HOST` only**. No LLM /
  core plane listener on a public interface. Matches external scan.
- **CORE** listeners: `172.31.17.217:8443` (python3 server, **bound to the
  private interface only** — not 0.0.0.0), `:22` sshd (ufw: operator IP +
  `172.31.61.22` EIC private mgmt). No public bind. Matches external scan
  (CORE :8443 filtered from outside).
- **Verdict — mgmt/LLM-plane isolation: PASS** (confirmed from inside).

## C. Secret scan (values never printed; len + sha256[:8] only)

- **EDGE** has **no `.env.field`** (the review's assumed path does not exist).
  Secret surface: `/etc/ragin/api.key` (mode 600, root) — **len 64,
  sha8 `939ab70e`, not a placeholder**; `/etc/ragin/cowrie.cfg` (root:journal,
  640) with `api_key` + `max_tokens`; `/etc/ragin/tls/` (ca.crt, edge.crt,
  edge.key mode 600) and `/opt/ragin/pki-v2/` (fresh PKI, mtime Oct 25 03:57).
- **CORE** `/etc/ragin/server.env` (mode 600, root) — **all 21 keys SET, 0
  placeholder lines**. `API_KEY == RAGIN_API_KEY` (both len 64, sha8
  `939ab70e` — **identical to EDGE `api.key`**, i.e. one shared deployment
  secret). `RAGIN_MTLS_*` point at the same `pki-v2` material.
- **New finding (residual exposure):** `RAGIN_LLM_API_KEY` on CORE is a **live
  third-party credential** (len 49, sha8 `812dbd6a`, not a placeholder). It is
  required for the inference path, and the host is mTLS-only + SG-restricted,
  but there is **no documented rotation policy** for it. Not a §2 gate violation
  (the gate is "no *staging/placeholder* creds shipped"; none were), but record
  it as live-cred exposure pending a rotation decision (APPROVAL_REQUIRED).

## D. Field collection — cowrie capture (EDGE, all rotated logs)

`cowrie.json` rotates **daily** (`cowrie.json.YYYY-MM-DD`). Aggregated across
`cowrie.json` + all rotations:

| UTC date | total events | session.connect |
|---|---|---|
| 2026-10-08 | 101 | 6 |
| 2026-10-09 | 227 | 11 |
| 2026-10-11 | 3 | 1 |
| 2026-10-25 | 634 | 68 |
| 2026-10-26 | 31 | 11 |
| **total** | **996** | **97** |

- **Unique hashed sources: 2** (e.g. `f28b4a8076cf` …). Field traffic is from a
  handful of scanners, not a crowd.
- **Interactive events: 368** = 305 `cowrie.command.input`, 60
  `cowrie.login.success`, 3 `cowrie.login.failed`.
- **Login.success is cowrie accept-all emulation, not real auth.** Spray
  usernames: root×29, test×17, admin×3, then single hits (bogususer, ubuntu,
  oracle, pi, deploy, webapp, postgres, mysql, svc_backup, user, guest) —
  classic default-cred spraying absorbed by the emulated shell.
- **Top recon commands:** `whoami` (17), `uname -a` (12), `cat /etc/passwd` (9),
  `cat /etc/os-release` (6), `ls -la /root` (4), banner checks
  (`nginx/1.18.0`, `OpenSSH_8.9p1`). Automated-scanner behavior.
- **LLM refusal strings appear as `cowrie.command.input`** ("I cannot help with
  that request", "I can't help with credential hunting…", …) — evidence the
  deception-LLM plane engages and its refusals land in the command log.
- **file / download / honeytoken events: 0.** No attacker retrieved files.
- **Honeytoken census: 0 deployed.** No `*honey*` files under
  `/opt/ragin/cowrie-var`, and `/etc/ragin/cowrie.cfg` has no honeytoken
  section. → **Honeytoken detection is not exercised in the live field
  config** (capability exists in RAGIN code, not enabled here). Honest limit on
  any field claim about honeytoken efficacy.

**Verdict:** real attacker interaction captured (97 sessions, 60 emulated
logins, 305 commands, 2 sources, Oct 8–26), but **handshake + emulated-shell
only** — no file retrieval, no honeytokens, and the "logins" are accept-all
spray, not compromise.

## E. F2 / F3 closure — live daily export

- `cowrie_pipeline_bridge.py` and `collect_field_data.py` are present on
  **CORE** (`/opt/ragin/scripts/`), **not on EDGE**.
- **No crontab** for root or ubuntu on either host → the §6 "daily export" is
  **not scheduled** and has **never run**.
- `RAGIN_FIELD_EXPORT_DIR=/app/data/field/ragin` on CORE is **empty** (only
  `.` / `..`). → No records — and therefore **no raw source IPs** — have ever
  been written or exported. F2's raw-IP risk is **latent, not realized** (the
  bridge's `source_ip`/`src_ip` fields would carry raw IPs *if* it were
  activated; strip them at export or keep the on-host-only invariant explicit
  before enabling). F3 confirmed: the §6 runbook command was invalid *and* no
  cron exists to run it.

## F. New operational finding (not a security gate)

`socat-ragin.service` (EDGE→CORE mTLS forwarder) is in a **systemd crash-loop**
(`NRestarts=57738`, `SubState=running` via a stale instance): the unit's
`ExecStart` keeps exiting `status=1` because **pid 1431 already holds
`172.29.0.1:18083`**. The listener is functionally up (pid 1431 LISTEN), so the
forwarder works, but the unit cannot manage its own socket — drift to reconcile
(a `systemctl restart` that kills the stale pid, or `ReusePort`) before relying
on the unit for HA. Operational, not a FIELD_ETHICS §2 gate.

## G. 2026-10-28 re-check — census v1 + collection plumbing

Collected over SSM from EDGE `i-05bc6aab0bd4260a7` with
`scripts/field_census.py` (aggregates + salted hashes only, SHA-256 of
`ip + ragin-ip-v1`, 12 hex chars). Artifact: `evidence/field/census_2026-10-28.json`.

| Metric | Value |
|---|---|
| events | 1,081 |
| unique sessions connected | 124 |
| `cowrie.command.input` | 305, of which **88 are model refusal strings** |
| login.success / login.failed | 62 / 3 |
| file downloads | 0 |
| unique hashed sources | 2 |
| interactive events | 370 |

Per-day `session.connect`: Oct 8: 6 · Oct 9: 11 · Oct 11: 1 · Oct 25: 68 ·
Oct 26: 14 · Oct 27: 23 · Oct 28: 1.

**Correction to §D.** The "honeytoken census: 0 deployed" line measured
cowrie's *native* honeytoken feature. The planted bait used by the paper
(`.dbpass`, `.env` with AWS-shaped keys) is served by the RAGIN fiction layer
on CORE, so that census does not cover it. Consequence: the §5.6 transcript
counts are **what the surface returns**, and the §D line must not be read as
"no bait exists". The paper now labels those counts as surface descriptions,
and the per-arm artifact `arm_stats_bootstrap_v1.json` keeps them out of the
controlled contrast.

**New finding (logging).** 88 of 305 `command.input` records are the deception
model's refusal text ("I cannot help with that request." etc.), not attacker
keystrokes. Two consequences: (a) attacker-issued commands = 217, not 305;
(b) the refusal path reaches the SSH channel in a way cowrie logs as input,
which needs a transport review before the number is quoted again.

**Collection plumbing installed.** `/opt/ragin/field_census.py` on EDGE and
`/etc/cron.d/ragin-field-census` (03:17 UTC daily, `--out-dir
/var/lib/ragin/census`). Verified by writing `2026-10-28.json` on the host.
An earlier attempt with `$(date +\%F)` in the cron line expanded at install
time and would have overwritten one filename forever — the script now names
its own output, which is also why the original runbook entry never worked.

## H. The 300-second ceiling (2026-10-28)

Cowrie closes an interactive session at `[honeypot] interactive_timeout`, whose
fallback is **300 s** (`cowrie/ssh/transport.py`). The field posture never
overrode it, so every field session is capped at five minutes of wall clock,
and the 67–335 s dwell range in §D/§G is a *transport* bound, not attacker
persistence. This matters for how §5.6 reads: the live sessions end because the
emulator closes them, and the v1 local A/B had the same ceiling on top of its
14-turn cap. The v2 study raises it to 3600 s for the local arms only; the field
default stays 300 s, so any field dwell number must be labelled as capped.

## I. First successful export + census snapshot (2026-10-29)

- **Census** `evidence/field/census_2026-10-29.json` (pulled via SSM from EDGE
  `/var/lib/ragin/census/2026-10-29.json`): 1,087 events, 127 sessions, 305
  commands, 62 login.success / 3 failed, **0 file downloads**, 2 unique hashed
  sources. Daily breakdown confirms **zero new attacker commands after
  2026-10-25** (batch-1 campaign day) — ambient traffic is scanner-grade and
  does not reach the deception plane. Field numbers in the paper remain
  consistent with the 2026-10-28 census.
- **First CORE export** (`results/field_export/`, 279 `ses-*.jsonl`): the
  ragin-server per-session JSONLs written 2026-10-25 inside the
  `ragin-core-staging` container (`/app/data/field/ragin`, bind dir empty on
  host — mount gap noted). Transferred as gzip+base64 over SSM RunCommand.
- **Redaction audit on the export**: no public-IP-shaped strings (only
  fiction/infra loopback + RFC1918 values: 127.0.0.1, 0.0.0.0, 10.0.0.5,
  10.0.1.66); exactly one distinct AKIA-shaped key, matching the registered
  canary in `results/cti_audit_packets.md`. No live credentials left the host.
- Follow-ups (not blockers): (a) wire the host bind dir for `/app/data/field/ragin`
  so future exports need no docker-cp; (b) refusal-transport review from §G
  still open.
