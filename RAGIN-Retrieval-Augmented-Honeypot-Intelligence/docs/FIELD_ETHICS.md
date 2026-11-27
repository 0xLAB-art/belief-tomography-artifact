# RAGIN S&P 2027 Field Study — Ethics & Operations

**Status:** DRAFT — complete before any public endpoint goes live.
**Governing venues:** IEEE S&P 2027 Research Ethics Committee (mandatory HotCRP
Ethics Considerations field) + the Generative-AI Usage Considerations field.

## 1. What this study is (and explicitly is not)

A passive measurement of **opportunistic Internet background adversarial
traffic** against three honeypot arms (vanilla Cowrie / bare LLM honeypot /
RAGIN verified loop). We claim NO APT engagement, NO targeting of real
attacker infrastructure, and NO active deception of humans beyond the
protocol-standard honeypot interaction.

## 2. Containment requirements (hard gates — verify per endpoint)

| Requirement | Mechanism | Verify |
|---|---|---|
| No outbound attack capability | `field_provision.sh` DOCKER-USER egress drop (NEW outbound from honeypot nets) | `iptables -L DOCKER-USER -n` |
| LLM egress allowlist only (RAGIN/vanilla arms) | :443 to resolved provider IPs only | same |
| No production credentials anywhere | `.env.field` holds ONLY synthetic/decoy credentials; generated secrets never overlap real ones | secret scan before deploy |
| Malware never executed | medium/low-interaction emulation; no real shell, no payload download-and-run | design review |
| No abuse of third parties | attacker-supplied C2 addresses are logged, never contacted | egress drop enforces |
| Management plane isolated | tailscale0 only; no public SSH for admin | `ss -tlnp` |

## 3. Data minimization & privacy

- Source IPs are **hashed at pipeline ingestion** (`ragin/chrollo/models.py`
  `source_ip` field validator → `ragin/utils.hash_ip`, SHA-256 keyed by
  `RAGIN_IP_SALT`); collection exports (`collect_field_data.py export`)
  carry only the hashed values. Raw IPs never leave the endpoint host and
  are never published. (Corrected 2026-10-26 per
  `FIELD_ETHICS_REVIEW_2026-10-26.md` F1: hashing is NOT done by the
  collector script itself.)
- Published artifacts contain: hashed source prefixes, timestamps truncated
  to the hour, command transcripts, and system metrics. Sessions are the
  unit of analysis; identity reconstruction is out of scope and mitigated by
  hashing + truncation.
- Retention: raw logs on endpoint 30 days; hashed exports retained for the
  analysis period + publication. Backups encrypted at rest.
- Disclosure in paper: lawful-intercept style monitoring of ONLY traffic that
  voluntarily connected to our honeypot listeners.

## 4. Human evaluation (separate protocol, also mandatory ethics field)

Blind expert "real or honeypot?" rating:
- Recruit ≥3 independent security practitioners (not authors).
- Consent form covers: purpose, data recorded (ratings + free text), duration,
  voluntary withdrawal, no compensation contingent on answers.
- IRB/ethics determination: file for a waiver determination BEFORE the first
  rating session (institution rules vary — do not collect first).
- Ratings are anonymized; the paper reports aggregate agreement statistics.

## 5. Disclosure obligations for the S&P submission

- **Ethics Considerations field:** summarize §§1–3, state the IRB/waiver
  determination, and the reasoning that the study risks are bounded by
  containment + data minimization.
- **GenAI Usage Considerations field:** declare LLMs as the *object and
  mechanism under study* (generator, attacker stand-ins in benchmarks,
  judge panels) and any use in manuscript preparation per the S&P policy.

## 6. Operational runbook (per endpoint)

1. `sudo bash scripts/field_provision.sh <arm>` (idempotent).
2. `docker compose -f docker-compose.field.yml --env-file .env.field up -d <arm-service>`.
3. Verify: `ufw status`, `iptables -L DOCKER-USER -n`, external probe that the
   listener answers, internal probe that egress drop holds (`curl -m 5 https://example.com` from inside the container must FAIL).
4. Daily (installed 2026-10-28): `/etc/cron.d/ragin-field-census` on EDGE runs
   `field_census.py --log-dir /opt/ragin/cowrie-var/log/cowrie --out-dir
   /var/lib/ragin/census` at 03:17 UTC. Output is aggregates plus salted
   hashes only; raw `src_ip` never leaves the host. The previous line
   (`collect_field_data.py export --days 1`) had never run: the script lives on
   CORE, not EDGE, reads Redis rather than the cowrie log, and the flag was on
   the wrong level (review F3). The two paths are separate: session export via
   `collect_field_data.py` on CORE, cowrie census via `field_census.py` on EDGE.
5. Weekly: `field_health_check.py` + restore-free backup of `data/field/`.
6. Teardown at study end: `docker compose ... down -v`, `ufw --force reset`,
   rotate logs, delete raw logs after final export.
