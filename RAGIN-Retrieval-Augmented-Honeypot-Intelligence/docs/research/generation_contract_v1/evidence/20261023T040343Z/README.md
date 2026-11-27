# Preflight generation-contract evidence — 2026-10-23T04:03:43Z

Offline verification of `scripts/preflight_generation_contract_v1.py` and the
approval packet in `../external_preflight_v1/`. **No external provider was
contacted, no bridge was started, and no LLM inference occurred.** The runner
tests use a loopback fixture only.

Environment for every captured command:

- fresh interpreter (`.venv/bin/python`, Python 3.12.3)
- unique `RAGIN_SESSION_DIR` and `RAGIN_HOST_FICTION_PATH` under `/tmp/opencode`
- `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`
- provider credentials and HTTP(S)/ALL proxy variables unset
- `NO_PROXY`/`no_proxy=127.0.0.1,localhost,::1`

## Captured results

| File | Purpose | Exit |
|---|---|---|
| `pytest_generation_contract.log` | raw pytest stdout, 54 passed | 0 |
| `pytest_generation_contract.exit` | pytest exit status | 0 |
| `dry_run.log` | raw preflight dry-run stdout | 0 |
| `dry_run.exit` | dry-run exit status | 0 |
| `ruff.log` | scoped ruff on runner + new test | 0 |
| `ruff.exit` | ruff exit status | 0 |

Tests: `tests/unit/test_preflight_generation_contract_v1.py` (16) plus
`tests/unit/test_generation_contract_v1.py` (38) = 54 passed.

Packet digest: `795a28bd70b92220cecece2b4eb3f38d7baa207d7d9cb37a1c69048e566a9893`.

## Files

- `PACKET_DIGEST.txt` — recorded canonical approval digest.
- `SOURCE_HASHES.sha256` — runner, bridge, safe config, and focused test hashes.
- `PACKET_ARTIFACTS.sha256` — manifest, approval packet, and four payload hashes.
- `EVIDENCE_MANIFEST.sha256` — hashes of the raw evidence files above.

These hashes describe local verification evidence only. A passing test or dry
run is **not** model exposure and must not be reported as a scientific result.
The evidence manifest intentionally excludes peer-modified shared runtime files.
