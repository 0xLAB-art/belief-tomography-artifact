# CORE Deployment Results

## Result

PASS for controlled staging only. The selected `server_v2 -> Sandbox -> Harness -> mandatory verifier -> commit/serve` path started on the existing CORE host and returned an accepted response or verified fallback through authenticated requests. This is not proof of private production placement.

## Observed startup

- Image: `ragin-staging:20261008`.
- Chrollo model loaded with 42 features.
- Don indexed 25,397 documents, 15 tactics, 174 actors, and 19,250 BM25 terms.
- Pipeline initialized Chrollo -> Don -> Hisoka.
- HTTPS listener bound to private `172.31.17.217:8443`.
- Container uses non-root UID, read-only root filesystem, dropped capabilities, no-new-privileges, bounded memory/CPU/PIDs, and restricted data/TLS mounts.

## Serving evidence

The controlled `whoami` request produced:

- Chrollo: novice, confidence `0.9749`.
- Don: medium severity, TTP `T1033`.
- Verifier: `FictionConsistencyVerifier`, deterministic, passed, confidence `1.0`.
- Final path: `GENERATED_VERIFIED` in the direct EDGE-to-CORE evidence; the Cowrie run used the configured unavailable provider and observed a verified deterministic fallback.
- Served synthetic response: `webapp@web-srv-01:~$ whoami` followed by `webapp`.

Evidence files:

- `evidence/edge_to_core_verified_provenance.json`
- `evidence/edge_to_core_e2e_summary.json`
- `evidence/cowrie_to_core_e2e.json`

The staging environment deliberately does not claim live paid/provider-backed Hisoka generation. No provider completion request was issued.
