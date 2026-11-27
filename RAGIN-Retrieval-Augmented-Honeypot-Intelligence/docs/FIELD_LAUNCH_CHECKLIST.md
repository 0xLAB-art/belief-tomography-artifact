# Field Launch Checklist — Oct-3 VPS Pivot (hard gate: live by Oct 10)

**Created:** 2026-09-28 | **Target live:** 2026-10-03 → **hard gate 2026-10-10**
**Why the pivot:** Azure subscription writes remain blocked (ReadOnlyDisabledSubscription;
manual portal re-enable is the only unblock and is not in our control). The plan's
W1 decision (Q3) already pre-authorized 2–3 cheap VPSes as the alternative.
**UPDATE 2026-09-28 evening — user decision: NO VPS purchase; deploy on Azure
free services.** Provisioning package built + locally validated:
`scripts/provision_azure_field.sh` (per-arm Standard_B1s, billing-guard probe,
distinct-location enforcement, NSG port-22-only) + `scripts/cloudinit_field.yaml`
(secret-free bootstrap) + `scripts/field_smoke_ssh.py` (§0.5 per-arm smoke gate).
Free-tier math: 3× B1s = $0 compute (750 free hrs/mo each, 12-month allowance);
3× Standard public IP ≈ $11/mo total. **Human gates: (1) portal reactivation of
the disabled subscription (Cost Management → Reactivate), (2) 3 Tailscale
single-use keys.** The Hetzner spec below is retained as the fallback path.
**Budget (Azure):** ≈ $11/mo (public IPs only).

Local dry-run validations completed 2026-09-28 (recorded here so the launch day
only exercises *remote* unknowns):

- `bash -n` PASS on `field_provision.sh`, `deploy_field.sh`, `azure_healthcheck.sh`
- `docker compose -f docker-compose.field.yml config` PASS with env from
  `.env.field.example` (services: cowrie / vanilla-llm / ragin; network:
  honeypot-internal). Compose parses `version:` as obsolete — cosmetic warning only.
- `collect_field_data.py` (export/logs/metrics/analyze/archive/full), `field_health_check.py`
  (one-shot/continuous/json), `backup_field_data.py` CLI surfaces verified.
- Cowrie log parser re-verified against `data/cowrie_logs` (51 command entries) —
  the W1 "cowrie log parse failed" warning occurs only when field log dirs are
  empty pre-launch, not a parser defect.

---

## 0. Preconditions (do BEFORE VPS order — Sep 29–30)

Status 2026-09-28 (evidence in `docs/ops/OPS_LOG_TEMPLATE.md`): secret scan
**CLEAN** (tracked code/configs, tracked results/data, `gateway.tar` image
layers, untracked strays — the only format-valid AWS token found is the
pipeline's own registered canary `_CANARY_AWS_ACCESS_KEY`, provenance
verified); gateway authed probe **200 OK**; allowlist IP for
`api.apmix.ai` resolved (re-resolve on the VPS at provision time);
`RAGIN_IMAGE` decision = **(a) build on the VPS** from `Dockerfile.python`.
SSH substrate for arms B/C (§0.5) **built + locally validated** same day.
Still open: provider order, Tailscale auth keys (user actions below), and
the VPS-side §0.5 smoke tests.

- [x] **Secret scan** (`docs/FIELD_ETHICS.md` §2 hard gate): confirm no real
  credentials anywhere in the deploy payload; `.env.field` will hold ONLY
  synthetic/decoy credentials and the LLM API key (acceptable: the key is
  billing-contained and rotates). **DONE 2026-09-28 — CLEAN, evidence in ops log.**
- [ ] **Provider choice + order** (3 accounts or 1 account 3 regions — separate
  IP prefixes per arm; never co-locate arms on one IP).
  **Research-verified order spec (2026-09-28):**
  - **Primary: Hetzner Cloud** — CX22 (2 vCPU / 4 GB / 40 GB, ~€4.5/mo after
    the Jun-2026 adjustment); 3 instances ≈ €14/mo total, well under budget;
    hourly billing enables cheap pilot tests. Sizing note: CX22's 4 GB covers
    the ragin arm's headroom need with margin. Locations: pick 3 distinct
    locations (e.g. HEL1 / FSN1 / NBG4) for separate IP prefixes; verify the
    assigned IPv4s are not in the same /16 and record them in the ops log.
  - **Alternates (if Hetzner ToS/signup friction):** DigitalOcean
    s-1vcpu-2gb (~$12/mo, 3 regions) or AWS Lightsail 2 GB (~$10/mo).
    Either satisfies separate-prefix + hourly-billing requirements.
  - **User action:** create account, order 3 instances (Ubuntu 22.04), file
    each provider abuse contact in the ops log BEFORE first boot goes public.
- [ ] **DNS/none required** — attackers find raw IPs; no domain needed. Record
  the three IPs in the private ops log (NOT in the repo).
- [ ] **Tailscale** account + auth keys ready (management plane is tailnet-only).
  **Setup spec (verified 2026-09-28):** Personal plan (free, 3 users / 100
  devices) covers 3 VPSes + laptop. Admin console → Settings → Keys →
  generate **3 single-use, reusable=false, 90-day** auth keys (one per VPS,
  tagged `tag:field-<arm>`). `tailscale up --ssh` per node; then verify
  public `ss -tlnp` shows NO sshd on 0.0.0.0:22 before the honeypot listener
  goes public.
- [x] **RAGIN image**: decide `RAGIN_IMAGE` source. **DECIDED 2026-09-28: (a)**
  build on the ragin VPS from the repo (`docker build -f Dockerfile.python -t
  the-intelligence-ladder:field .`); compose default (GHCR, unpublished) is
  overridden by `.env.field` (`RAGIN_IMAGE=the-intelligence-ladder:field`).
- [ ] **Gateway reachability from VPS**: the ragin + vanilla arms call the LLM
  gateway (`RAGIN_LLM_BASE_URL`). Verified locally 2026-09-28 (authed
  `/v1/models` → 200); **must be re-verified from the VPS** at provision:
  `curl -sS -o /dev/null -w '%{http_code}\n' $RAGIN_LLM_BASE_URL/models -H "Authorization: Bearer $RAGIN_LLM_API_KEY"`
  Free-tier rate limits under continuous background traffic are EXPECTED — the
  fallback path is by design (and now correctly labeled `TEMPLATE_FALLBACK_VERIFIED`
  per the 2026-09-28 provenance fix). Also budget-check the completions path
  (model listing ≠ completion quota; completions were 429 on 2026-09-28).

### 0.5 SSH substrate for arms B/C — BLOCKING, decided 2026-09-28

Recon finding: arms B/C as composed have **no SSH attack surface** — nothing
in their images listens on 2222 (the compose maps public 22→2222),
`server_v2` is HTTP-only, and the ESWA-era cowrie-LLM plugin survived only on
the destroyed VPS. Decision: rebuild the **cowrie + LLM-backend adapter**
pattern — cowrie speaks SSH, its LLM backend calls the RAGIN backends.

**BUILT + VALIDATED 2026-09-28** (local; a previous session died mid-write
and NUL-corrupted two files, which were rebuilt from the surviving
contracts):

- [x] **Cowrie LLM backend is NATIVE upstream** — no plugin vendoring needed.
  Verified against docs.cowrie.org (`[honeypot] backend = llm` + `[llm]`
  section: `host`, `path`, `api_key`, `model`, `max_tokens`, `temperature`,
  `debug`; conversation history of last 10 commands kept by cowrie itself).
  The stock `cowrie/cowrie` image also accepts `COWRIE_<SECTION>_<KEY>` env
  vars (env beats file), so **no custom cfg mount is required at all** —
  the `cowrie.cfg.ragin` / `cowrie.cfg.bare` files in `docker/cowrie/` are
  the human-readable spec of the wiring (and the fallback if env templating
  is not desired); compose sets the same values via env vars.
- [x] `docker-compose.field.yml` rewritten: shared `cowrie-llm` frontend
  service (backend=llm via COWRIE_* env) + `bare-llm` backend (:8084, arm B)
  + `ragin-server` backend (:8083, arm C). Vanilla arm A's broken
  `cowrie-etc:/etc/cowrie` mount fixed to the real image path
  `/cowrie/cowrie-git/etc` (named volume so `cowrie.cfg.dist`/`userdb.txt`
  are NOT shadowed). Only the honeypot listener is published; backends bind
  0.0.0.0 **inside the `internal: true` bridge only**; backend auth via
  `BACKEND_API_KEY` (Bearer, generated per endpoint; see .env.field.example).
- [x] Arm B backend: `scripts/bare_llm_backend.py` — OpenAI-compatible
  `/v1/chat/completions` wrapper over `GatewayClient`; persona prompt is
  byte-identical to the external-baseline `llm_unverified` arm; no CTI,
  no graph, no verifier, no fail-closed fallback (that is the measured
  baseline); empty-generation serves a minimal shell-error line so a dead
  gateway never hangs the attacker session.
- [x] Arm C backend: `ragin/server_v2.py` gained the cowrie bridge —
  `POST /v1/chat/completions` (pipeline mode) maps the conversation onto the
  sandbox (`X-Session-Id` header wins; otherwise transcript-prefix matching
  reconstructs per-SSH-session continuity, since stock cowrie re-sends the
  full growing history and echoes no header) and returns the VERIFIED
  response. Fail-safe on pipeline error: a generic `bash: input/output
  error` is served, never an unverified draft. Session interactions export
  as JSONL to `RAGIN_FIELD_EXPORT_DIR` (compose: `/field-export` bind mount)
  for `collect_field_data.py`. Auth middleware now accepts Bearer as well as
  X-API-Key; `GATEWAY_URL`/`OPENROUTER_API_KEY` are mapped from the
  `RAGIN_LLM_*` env names inside the container (silent-wiring-bug guard).
- [x] `Dockerfile.python` now copies `scripts/` so the bare backend ships in
  the image.
- [x] Regression locks: 7 bridge tests in `tests/unit/test_server_v2.py`
  (serve, transcript-prefix continuity, fresh-session on divergent
  transcript, explicit-header-wins, fail-safe-on-error, 400s, auth);
  full suite **1389 passed** + 38 lightrag, ruff clean.
- [ ] **Per-arm SSH smoke test on the VPS (still open — needs live hosts):**
  scripted SSH login + command over the public port; verify the session lands
  in cowrie logs AND the backend served (arm B: generator text; arm C: serve
  carries the verified pipeline surface and the export JSONL grows in
  `/field-export`).
- [ ] **Egress check after wiring (VPS):** the LLM-backend call is
  container→container on the internal net; only the ragin/bare backends
  egress to the allowlisted provider :443 (DOCKER-USER).

---

## 1. Per-endpoint provision (repeat ×3; ~30 min each)

- [ ] `apt update && apt -y upgrade && apt -y install docker.io docker-compose-v2`
- [ ] Add non-root deploy user; install Tailscale; `tailscale up --ssh`;
  verify public `ss -tlnp` shows NO sshd on 0.0.0.0:22 (management tailnet-only).
- [ ] Copy repo (git clone from the private remote or rsync), then:
  `cp .env.field.example .env.field` and set:
  - `RAGIN_FIELD_ARM` (cowrie | vanilla | ragin — one per VPS)
  - `RAGIN_LLM_BASE_URL` / `RAGIN_LLM_API_KEY` / `RAGIN_LLM_MODEL` (vanilla+ragin)
  - `RAGIN_LLM_PROVIDER_HOST` (hostname — provision script resolves it to IPs
    for the egress allowlist)
  - `RAGIN_IMAGE` if not building locally
  - `BACKEND_API_KEY` (generate per endpoint; must equal the cowrie-llm
    frontend's key on arms B/C — see `.env.field.example`)
  - `COWRIE_LLM_HOST` (vanilla endpoint: `http://bare-llm:8084`; ragin
    endpoint: `http://ragin-server:8083`)
- [ ] Bring up the arm (services per §0.5 wiring):
  `docker compose -f docker-compose.field.yml --env-file .env.field up -d <services>`
  (cowrie arm: `cowrie` · vanilla arm: `cowrie-llm bare-llm` · ragin arm: `cowrie-llm ragin-server`)
- [ ] `sudo bash scripts/field_provision.sh <arm>` — idempotent; applies the
  DOCKER-USER egress drop + LLM-provider allowlist + log dir perms + cron line.
- [ ] **Ethics gates (§2 of FIELD_ETHICS.md) — verify, don't assume:**
  - `iptables -L DOCKER-USER -n` shows NEW outbound DROP from honeypot nets
  - allowlist: only `:443` to resolved provider IPs (vanilla/ragin), none for cowrie
  - `ss -tlnp`: only the honeypot listener(s) public

## 2. Post-launch verification (launch day +48 h)

- [ ] **Inbound traffic lands:** cowrie arm → `docker logs field-cowrie` shows
  sessions; ragin/vanilla arms → the arm's session store/log grows.
- [ ] `field_health_check.py --json` green on all three endpoints (disk, log
  freshness, service liveness).
- [ ] `collect_field_data.py logs --dest results/field/<arm>/` pulls real rows;
  verify source-IP hashing at collection (raw IPs stay on the endpoint).
- [ ] `backup_field_data.py -o /var/backups/field` + cron verified; restore drill:
  untar one archive locally and re-run the analyzer against it.
- [ ] **First-hours tell check (audit carry-over):** skim served transcripts —
  template-fallback serves must now be counted under
  `TEMPLATE_FALLBACK_VERIFIED`, not `GENERATED_VERIFIED`; if the
  `GENERATED_VERIFIED` fraction looks implausibly high under gateway errors,
  re-check `metadata` marks before drawing any RQ4 conclusion.

## 3. Study calendar (backwards from the Nov 8 freeze)

| Date | Milestone |
|---|---|
| Sep 29–30 | Preconditions: provider order, tailscale, image decision |
| Oct 1–2 | Provision cowrie + vanilla VPS; SSH substrate **already built (§0.5, 2026-09-28)** — run the per-arm VPS smoke tests; collect first traffic |
| **Oct 3** | **Pivot target: all three arms live** |
| Oct 4–9 | Stability watch; fix whatever launch shook out; daily collect cron verified |
| **Oct 10** | **HARD GATE: stack live with first real sessions in logs.** If not met, Q1 falls back to option B (ladder demoted to design insight) per the locked decision rule |
| Oct 10 → Nov 8 | Passive accrual (~29 days at gate, ≥25 days at freeze = defensible minimum) |
| Weekly | `backup_field_data.py` restore drill; ethics §2 re-verification per endpoint |

## 4. Go/No-Go criteria (Oct 3 and Oct 10)

GO = all of: (a) three arms up with correct serve-path labels flowing into the
collectors, (b) egress gates verified by command output, (c) management plane
tailnet-only verified, (d) collectors + backups demonstrated with a restore drill,
(e) ethics preconditions signed off (secret scan, retention config).
NO-GO on any (a)–(e) failure → fix and re-gate; do NOT let the calendar push a
half-contained endpoint public.

## 5. Kill switches (documented before launch, exercised never)

- Per endpoint: `docker compose -f docker-compose.field.yml down` (stops listeners).
- Provider-level: destroy the instance (fastest containment if something is wrong).
- Abuse contact: file the provider's abuse-report contact in the ops log so a
  complaint is actionable within hours, not days.
