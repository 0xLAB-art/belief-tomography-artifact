# Field Ops Log — S&P 2027 three-arm study

**PRIVATE — never commit real values to git.** This file lives in the private
ops store (password manager / encrypted note / private repo outside the paper
repo). The template below is the committed shape; fill it per endpoint at
provision time.

## Endpoint records (one block per VPS)

```
### arm=<cowrie|vanilla|ragin>
provider:            (Hetzner | DO | Lightsail)
region/location:     (must differ across arms — separate IP prefixes)
instance type:       (e.g. CX22, 2 vCPU / 4 GB / 40 GB)
public IPv4:         ___________        (prefix check: not in same /16 as other arms)
public IPv6:         ___________
ssh fingerprint:     ___________        (record at first boot)
tailscale hostname:  ___________        (management; public SSH must be OFF)
abuse contact:       ___________        (provider abuse URL/email — actionable in hours)
provisioned:         (date, by whom)
field_provision.sh:  (date + iptables -L DOCKER-USER -n output hash)
.env.field sha256:   ___________        (config provenance; file itself stays local)
```

## Dated precondition evidence (Sep 29–30, 2026)

| # | Item | Result | Evidence |
|---|---|---|---|
| 1 | Secret scan, tracked tree (413 code/config files) | CLEAN | all 4 regex hits = placeholders/official examples (`sk-REPLACED_*`, `AKIAIOSFODNN7EXAMPLE`) |
| 2 | Secret scan, tracked results/docs/data (5,084 files) | CLEAN w/ provenance | `AKIANZNIDYVHPF56D6JK` = `_CANARY_AWS_ACCESS_KEY` (deception.py:1322, deterministic from internal seed) — registered honeytoken bait, by design; masked `sk-…000…` = placeholders |
| 3 | Secret scan, `gateway.tar` (tracked docker image archive, 19 members) | CLEAN | pattern scan over all layers: no hits; config Env = PATH only |
| 4 | Secret scan, untracked strays (`.env.bak`, `.env.ragin-stack`, `audit_*.json`) | CLEAN | no credential shapes; all gitignored + dockerignored |
| 5 | Gateway authed probe (`GET /v1/models`, Bearer key) | 200 OK | 2026-09-28, apmix; note: completion calls were 429 same day — free-tier rate limits EXPECTED in field, fallback path is by design |
| 6 | Allowlist resolution (`api.apmix.ai`) | attacker-1f01ec5b6130 | re-resolve AT provision time on the VPS (field_provision.sh does this; provider IPs rotate) |
| 7 | Provider order | pending user | order spec in FIELD_LAUNCH_CHECKLIST §0 |
| 8 | Tailscale auth keys | pending user | 3 single-use keys, admin console → Settings → Keys |
| 9 | RAGIN image decision | (a) build on VPS | Dockerfile.python (slim, aiohttp runtime, models/ + corpus/ baked); GHCR push not published |

## Findings that changed the plan (2026-09-28)

1. **SSH substrate gap (blocking for arms B/C) — CLOSED same day:**
   `docker-compose.field.yml` mapped public 22→2222 on vanilla/ragin but
   nothing in those images spoke SSH. Rebuilt + validated 2026-09-28 per
   FIELD_LAUNCH_CHECKLIST §0.5: native cowrie LLM backend (stock image,
   `COWRIE_*` env config), shared `cowrie-llm` frontend, `bare-llm` +
   `ragin-server` backends, server_v2 `/v1/chat/completions` bridge.
   Remaining: per-arm VPS smoke tests (needs live hosts).
2. Docker `internal: true` bridge + DOCKER-USER allowlist coexist; container
   DNS is resolved by the host-side daemon, so the provision-time IP
   allowlist works. Tell-check: if the provider rotates IPs, the allowlist
   stales → serves fall back to templates → `TEMPLATE_FALLBACK_VERIFIED`
   share jumps. That jump is the monitoring tell, not a silent failure.
3. `deploy_field.sh` is the legacy Azure flow (domain/Grafana/SSL) — not the
   field path. Field path = git/rsync + compose + `field_provision.sh`.
