# Field Ethics & Hardening Review — 2026-10-26

**Scope (plan Phase 1):** review pass over `FIELD_ETHICS.md` (hard gates §2,
data minimization §3, human-eval §4) and `SECURITY_HARDENING.md` against live
state, verify stale `DEPLOYMENT_STATE_MATRIX` APPROVAL_REQUIRED items, and
record the findings. Method: live external probes + code/doc cross-check +
**host-internal SSM probes (completed 2026-10-26T15:54Z, AWS session
reauthenticated)**. Full probe transcript + field collection:
`evidence/field/exit_evidence_2026-10-26.md`.

## A. Hard-gate status (FIELD_ETHICS §2)

| Gate | Mechanism claimed | Status 2026-10-26 | Evidence |
|---|---|---|---|
| No public SSH for admin (mgmt isolated) | SSM-only management | **PASS (external)** | admin SSH closed on both hosts; matrix §3 EIC path exists; FIELD_REVIVAL table row "Public admin SSH (22) → closed" |
| Sole public listener `:2222` | ufw default-deny + socat | **PASS (external)** | external SSH handshake to REDACTED_FLEET_HOST:2222 returns cowrie host key + password prompt (FIELD_REVIVAL verification evidence); external scan shows :2222 the only public listener, CORE 8443/443 filtered from outside |
| LLM/core plane unreachable externally | SG + mTLS + ufw | **PASS (external)** | CORE :8443 answers only from EDGE /32 (matrix §4); external probe filtered |
| Egress allowlist (no outbound attack) | `RAGIN-EGRESS` iptables/ufw on EDGE+CORE | **PASS (SSM, both hosts)** | `iptables -S OUTPUT` = `-j RAGIN-EGRESS` on both (63k/64k pkts traversed), terminal `-j DROP`; **negative controls time out** (root→:80, root→:8080, EDGE uid1000→:443 all exit 124). The only passing probes are root→:443, the **explicit allowlist** `--uid-owner 0 --dport 443` rule (+uid1000→:443 on CORE). `DOCKER-USER` empty but `FORWARD` policy = DROP (default-deny container egress). §2 probe *command* in the old doc used https:443 as root — always allowed; corrected to negative controls. See exit_evidence §A. |
| No production credentials in `.env.field` | secret scan before deploy | **PASS + residual live-cred** | **No `.env.field` exists.** EDGE secret surface = `/etc/ragin/api.key` (64-char, mode 600, not placeholder). CORE `/etc/ragin/server.env` — all 21 keys SET, **0 placeholders**; `API_KEY == RAGIN_API_KEY` (sha8 `939ab70e`, identical to EDGE). **New:** `RAGIN_LLM_API_KEY` is a **live third-party credential** (len 49) — required for inference, host is mTLS+SG-isolated, but **no rotation policy documented** (residual exposure, APPROVAL_REQUIRED). See exit_evidence §C. |
| Malware never executed | design (emulation only) | PASS (design review) | medium/low-interaction cowrie emulation; no shell/payload path in compose arm |
| No abuse of third parties | egress drop logs-only C2 | **PASS (SSM)** | Egress DROP verified by negative controls on both hosts (exit_evidence §A); no non-allowlisted outbound path observed. |

## B. SSM collection (COMPLETED 2026-10-26)

AWS session reauthenticated; all five §B items executed via SSM on EDGE
(`i-05bc6aab0bd4260a7`) + CORE (`i-062a400b300f4f9e4`). Full transcript:
`evidence/field/exit_evidence_2026-10-26.md`. Summary:

1. ✅ Egress + mgmt-plane probes → §A table regraded **PASS** (both gates).
2. ✅ `ss -tlnp` inside both hosts → mgmt/LLM isolation confirmed from inside
   (EDGE public listener = :2222 only; CORE :8443 bound to private iface
   `172.31.17.217` only, never 0.0.0.0).
3. ✅ Secret scan → no `.env.field`; EDGE `api.key` + CORE `server.env` clean
   (no placeholders), **except** live `RAGIN_LLM_API_KEY` (§C finding below).
4. ✅ Field collection → `evidence/field/exit_evidence_2026-10-26.md` §D
   (per-day counts, hashed-source census, honeytoken census). Aggregated
   on-host; raw `src_ip` never exported (§3 honored).
5. ✅ Live daily export confirmed **empty / never run** → F2, F3 CLOSED (§C).

Local note (unchanged): `data/field/` (gitignored) holds ONLY local self-play
arm exports — 194 `ragin/` session files (2026-09-28 + 2026-10-26 arm-C),
labeled in `data/field/PROVENANCE.md`; never mixed with the endpoint
collection.

## C. Findings — doc-vs-code drift (fix docs or code, then re-verify)

**F1 — §3 attributes IP hashing to the wrong mechanism.**
`FIELD_ETHICS.md §3` says "Source IPs are **hashed at collection time**
(`collect_field_data.py`)". `scripts/collect_field_data.py` contains **no
hashing at all** (grep for `hash` → 0 hits): it verbatim-dumps Redis sessions
(`export`) and repo `logs/{gateway,chrollo,don,hisoka}.log` (`logs`). Actual
hashing happens at pipeline ingestion:
`ragin/chrollo/models.py:92-98` `field_validator("source_ip")` →
`ragin/utils.hash_ip` (SHA-256, salt `RAGIN_IP_SALT`, default `ragin-ip-v1`).
Also `export_logs` reads component logs, **not** cowrie logs — the §3 claim
does not describe this script's behavior. → Correct §3 to name the real
mechanism and its location.

**F2 — standalone bridge persists RAW source IPs alongside the hashed forms. [CLOSED — latent]**
`scripts/cowrie_pipeline_bridge.py` hashes into the session id + `hashed_ip`
but also writes `"source_ip": src_ip` (line 142) and `"src_ip": src_ip`
(line 161) into its records. **Live check (2026-10-26):** the bridge +
`collect_field_data.py` exist on **CORE** (`/opt/ragin/scripts/`), **not on
EDGE**; **no crontab** on either host; `RAGIN_FIELD_EXPORT_DIR=/app/data/field/ragin`
is **empty**. → The bridge has **never run**; no records and therefore **no raw
IPs** have been written or exported. §3's "raw IPs never leave the endpoint"
holds in practice. The raw fields remain a **latent** risk: strip them at
export (or state the on-host-only invariant explicitly) **before** enabling the
bridge. No code change made (would alter a deployed pipeline without approval).
See exit_evidence §E.

**F3 — §6 runbook step 4 command is invalid. [CLOSED — confirmed no cron]**
`collect_field_data.py --days 1` fails: `--days` belongs to subcommands
(`export|logs|metrics|analyze|archive|full`); bare invocation errors with
`invalid choice: '1'`. **Live check (2026-10-26):** moreover there is **no
crontab** on EDGE or CORE — the daily export is not scheduled at all, and the
real EDGE cowrie capture is a **daily-rotating** `cowrie.json[.YYYY-MM-DD]`
under `/opt/ragin/cowrie-var/log/cowrie/` that the collector never reads. →
Fix the doc command (e.g. `collect_field_data.py export --days 1`) **and** wire
a real cron against the cowrie path if daily export is wanted. Doc-only fix;
no cron installed (would alter deployed scheduling without approval).

**F4 — matrix rows are stale vs `FIELD_REVIVAL_2026-10-25.md`.**
`DEPLOYMENT_STATE_MATRIX.md` still says "Public Cowrie exposure … BLOCKED,
no public listener" (§6) and "Egress containment … not implemented" (§4),
and describes pre-revival mTLS ("staged staging CA, short validity"). The
Oct-25 revival opened `:2222` as sole public listener, applied RAGIN-EGRESS on
both hosts, and installed fresh PKI (10y CA / 90d leafs, expiring ~2027-01-23).
→ Mark superseded rows; keep APPROVAL_REQUIRED rows as pending decisions.

**F5 — live `RAGIN_LLM_API_KEY` is a real third-party credential on CORE
(new, residual exposure).** `/etc/ragin/server.env` has `RAGIN_LLM_API_KEY`
(len 49, sha8 `812dbd6a`, **not** a placeholder). Required for the inference
path; host is mTLS-only + SG-restricted, so blast radius is contained, but
**no rotation policy is documented** → add to APPROVAL_REQUIRED (rotation or
Secrets-Manager migration decision), not a §2 gate violation.

**F6 — field-capture reality check (honest-limit finding for the S&P ethics
field).** Aggregated across all daily cowrie rotations (2026-10-08→26):
**97 sessions, 60 `login.success`, 3 `login.failed`, 305 `command.input`,
2 unique hashed sources**; bulk on revival day (Oct 25: 634 events). BUT:
(a) the 60 "logins" are **cowrie accept-all emulation**, not real auth — the
spray usernames (root×29, test×17, admin×3, oracle/pi/postgres/mysql… 1 each)
are default-cred guessing absorbed by the emulated shell; (b) **0
file/download events**; (c) **0 honeytokens deployed** — no `*honey*` files and
no honeytoken section in `/etc/ragin/cowrie.cfg`, so **honeytoken detection is
not exercised in the live config** (capability exists in code, not enabled).
→ Any field claim about honeytoken efficacy or "attackers compromised the
box" must be scoped to handshake + emulated-shell interaction only. LLM
refusal strings ("I cannot help with that request", …) appear as
`command.input`, showing the deception-LLM plane engages. See exit_evidence §D.

**F7 — `socat-ragin.service` (EDGE→CORE mTLS forwarder) crash-looping
(operational, not a gate).** Unit `ExecStart` exits `status=1` with
`NRestarts=57738` because **pid 1431 already holds `172.29.0.1:18083`**; the
listener is functionally up (stale instance LISTEN) so the forwarder works, but
the unit cannot manage its own socket. Reconcile drift (restart that reaps the
stale pid, or `ReusePort`) before relying on the unit for HA. See exit_evidence
§F.

## D. APPROVAL_REQUIRED inventory (surfaced, NOT executed)

None of these are FIELD_ETHICS §2 hard gates; each needs explicit approval
before any change (matrix legend: "not an approval to deploy"):

- Private CORE placement (private subnet, no public IP) + private inference
  path + no-public-IP SSM/recovery proof
- Restrictive NACL (default is allow-all)
- Encrypted CORE/EDGE root EBS; snapshot/AMI migration
- Egress containment at the **SG** layer (host-layer allowlist applied Oct 25;
  SG still `all -> 0.0.0.0/0`)
- Audit durability, Flow Logs, cowrie container isolation,
  deception/admin plane split, Laya optional inference
- **[new, F5]** Rotate / vault the live `RAGIN_LLM_API_KEY` on CORE
- **[new, F7]** Reconcile `socat-ragin.service` socket drift (stale pid holds
  :18083)

## E. Ethics §4 (human evaluation)

IRB/ethics **waiver determination not filed** — must be filed BEFORE the first
rating session (recruit ≥3 non-author practitioners; consent form per §4).
No ratings collected yet, so no violation; gate remains open.

## F. Verdict

- External-observable hard gates: **PASS**.
- **Host-internal gates (SSM, 2026-10-26): egress allowlist PASS, mgmt/LLM
  isolation PASS, secret scan PASS (with F5 residual live-cred).** All three
  formerly-`PENDING` gates now have probe evidence in
  `evidence/field/exit_evidence_2026-10-26.md`.
- **Field collection complete** (exit_evidence §D): 97 sessions / 60 emulated
  logins / 305 commands / 2 sources / Oct 8–26 — handshake + emulated-shell
  only; **no honeytokens deployed**, no file retrieval. Scope paper claims to
  match (F6).
- **F2, F3 CLOSED** (live export empty / never scheduled; raw-IP risk latent).
  F1, F4 remain doc-drift fixes (§3 attribution; stale matrix rows). F5, F6, F7
  are new (live-cred rotation, field-claim scoping, socat drift).
- IRB/ethics §E waiver still **not filed** — must precede any human rating
  session (no ratings collected yet).
- APPROVAL_REQUIRED items stay frozen pending explicit go/no-go (matrix legend:
  "not an approval to deploy").
- **Overall: the review is now probe-complete.** Submission-facing ethics
  claims may cite PASS on all §2 hard gates, with the F5/F6 caveats stated.