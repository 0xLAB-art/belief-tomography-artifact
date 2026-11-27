# Integration Study: cve-mcp-server → RAGIN (Live CVE Intelligence)

**Date:** 2026-10-25 · **Repo:** https://github.com/mukul975/cve-mcp-server (Apache-2.0)
**Verdict:** integrate as a separate **intel plane** feeding Don's evidence pool.
Prototype working (`ragin/don/intel_mcp.py`) — live NVD hits verified in RAGIN's venv.

---

## 1. What the MCP server gives us

28 tools over 24 sources. The RAGIN-relevant subset:

| Tool | RAGIN use | Keys |
|---|---|---|
| `search_nvd` / `lookup_cve` | enrich fiction with real CVEs for software the attacker touches | none (reduced rate) / `NVD_API_KEY` |
| `get_epss` | evidence-quality signal: exploitation probability | none |
| `check_kev` (CISA KEV) | KEV-listed = hard engagement justification | none |
| `get_mitre_techniques` | feeds the existing ATT&CK mapper directly | none |
| `triage_cve` | one-call composite risk (CVSS+EPSS+KEV+PoC) | none |
| `search_exploits` / `check_poc_availability` | "is there a public PoC?" → fiction realism | GitHub token better |
| `virustotal_lookup` / `lookup_ip_reputation` | SIEM/monitoring plane later | keys |

Zero-key operation covers the core loop. The server ships its own SQLite TTL
cache (repeated queries are free), token-bucket rate limiting, and outbound-only
HTTPS with private-range blocking.

## 2. Architecture: intel plane vs honeypot plane

```
┌─ HONEYPOT PLANE (egress LOCKED — FIELD_ETHICS) ─┐   ┌─ INTEL PLANE (egress allowlist) ┐
│ EDGE cowrie ──mTLS──► CORE server_v2             │   │ cve-mcp-server (HTTP transport) │
│                         │ Don retrieval ◄────────┼───┤ NVD · EPSS · KEV · ATT&CK       │
│                         │ (evidence pool,        │   │ (SQLite TTL cache, rate limits) │
│                         │  UNTRUSTED-labeled)    │   └─────────────────────────────────┘
└──────────────────────────────────────────────────┘
```

**Rule:** the honeypot plane's egress stays locked. CORE either (a) reaches the
intel plane over the VPC private network (recommended: a small `intel` instance
with its own scoped egress), or (b) gets explicit host-allowlist entries for the
API endpoints only, with the ethics addendum updated. The enricher is DISABLED
by default and activates only when the plane answers.

## 3. Integration points (in priority order)

1. **Don evidence enrichment (prototype done).** `IntelEnricher.enrich(session_text)`
   detects software fingerprints (OpenSSH/nginx/MySQL/kernel/OpenSSL/... with
   versions) and emits live NVD records as evidence hits — labeled
   `source=cve-mcp/nvd`, clamped score, char-budgeted, `intel_plane` metadata.
   They compete in the evidence pool with static-corpus documents.
2. **Evidence Gate signal.** EPSS ≥ 0.5 or KEV-listed → `relevance_grade=high`
   on the intel doc → the EvidenceQualityGate has a real exploitation signal
   instead of corpus-only scoring.
3. **Loop node (LangGraph).** An optional `intel_enrichment` node between
   classify and retrieve; cache-first so the 44 s latency budget is not
   consumed by NVD round-trips (server cache TTL + our bounded queries).
4. **ATT&CK mapping.** `get_mitre_techniques(cve)` upgrades the existing
   threat_mapper from static mapping to CVE-anchored technique attribution.
5. **SIEM/monitoring plane (later).** Reputation tools (AbuseIPDB/GreyNoise)
   fit `ragin/monitoring` — the currently unwired integration capability.

## 4. Safety contract (verified in the prototype)

- Intel documents are **UNTRUSTED evidence**: they carry source labels, are
  char-budgeted, and enter the same verified-serving loop as everything else —
  a poisoned CVE description cannot reach the attacker without passing
  FictionConsistencyVerifier.
- **Fail-graceful**: any intel-plane failure returns `[]`; deception continues
  on the static corpus. Never fail-closed on the deception itself.
- **Bounded**: ≤4 software targets, ≤2 CVEs each, ≤30 s HTTP timeout, server-side
  SQLite TTL cache prevents hammering NVD (its 5 req/30 s anonymous limit).
- The pin `mcp<2` is required (server uses FastMCP v1 API; v2 renamed it).

## 5. Prototype evidence (2026-10-25, live)

- Session text with `OpenSSH_8.9p1` + `OpenSSL 3.0.2` → enricher detected both,
  queried NVD, returned 4 real records (CVE-1999-0661, CVE-2000-0525,
  CVE-1999-0428, CVE-2000-0535) as labeled evidence hits.
- `lookup_cve("CVE-2023-38408")` returned the full record (lastModified
  2026-10-15 — live data).

## 6. Status / next steps

1. ~~Deploy the intel plane~~ **done** — RAGIN-INTEL (`REDACTED_FLEET_HOST`) runs the
   plane as two host python services: `:8000 /opt/iv/bin/python service.py` and
   `:8765 /opt/intel/service.py`, both answering `{"status":"ok","plane":"intel"}`.
2. ~~Wire `IntelEnricher` into Don~~ **done** — commits `575ad02a` (adapter +
   this study), `49a153ea` (intel-enabled Don wiring + intel plane service +
   HTTP mode), gated behind `RAGIN_INTEL_ENABLED` (default 0). One bug found
   and fixed in-flight — see §7.
3. KEV/EPSS gating of `relevance_grade` in the evidence judge.
4. Batch-2 workload rerun with intel-enriched fiction vs static — the paper's
   newest ablation: "does live intelligence make the fiction more engaging?"

## 7. Shipped: evidence-pool projection fix (2026-10-26)

**Bug.** On the legacy `analyze()` path (when `command_aware_v2` is inactive),
live intel hits were appended *after* the full 50-hit static BM25 pool and then
sliced with `intel_hits[:10]`. The two score scales are not comparable — static
BM25 lands around 20–25 while intel hits are clamped to ≤1.0 — so a successful
enrichment could never survive the projection: `intel_documents`, the LLM
context, and the evidence bundle all received **0 CVEs**.

**Fix** (`871301d8`, `ragin/don/rag_engine.py`, +107/−2): live hits are tracked
separately and assembled into `projected_hits` — static hits ranked first,
guaranteed intel tail slots, pool capped at 10 — and that projection feeds both
`_build_context()` and `intel_documents`. With intel disabled the output is
byte-identical to the old behavior.

**Regression coverage** (`tests/unit/test_don.py`): `survives_projection`
(verifies 0 → non-zero CVE docs; confirmed failing before the fix) and
`disabled_keeps_static_top10`. Full file: **91 passed**.

**Field deployment.** Layered image `ragin-staging:v4-intel-proj` (FROM
`ragin-staging:v4-intel`), container `ragin-core-staging` on RAGIN-CORE, verified
running via SSM.

**E2E evidence** (in-container, `RAGIN_INTEL_ENABLED=1`,
`command_aware_v2 active: False` — i.e. exactly the legacy path the fix targets):

- `enrich_sync` hit-counts `[4]` → 4 live NVD records returned
- `intel_documents n = 10` (pool cap respected), 4 CVE docs present:
  `CVE-1999-0661, CVE-2000-0525, CVE-2009-2629, CVE-2009-3896` (source `cve-mcp/nvd`)
- evidence bundle `retrieval.documents n = 10` carrying the same 4 CVEs, all 4
  also in `relevant_doc_ids`
- `E2E_RESULT: PASS` — before the fix the same probe returned **0 CVEs** despite
  successful enrichment.
