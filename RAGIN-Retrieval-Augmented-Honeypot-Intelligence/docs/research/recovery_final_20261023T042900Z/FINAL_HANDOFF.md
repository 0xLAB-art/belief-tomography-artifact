# Recovery final handoff — 2026-10-23

This package records the final local validation boundary. It does not claim a completed B1–B3 study, hypothesis support, human collection, or model inference.

## Completed gates

- Current source/config/test byte archive: `SOURCE_MANIFEST.json`; 66/66 entries verified before and after the final trace, with no changed or missing paths. The manifest SHA-256 is `a0d703373041e6426829be20d7b1f6c242be03f084e3b3dd7c7ab10eeeecd433`.
- Focused regression: 86 tests passed (`tests/unit/test_generation_contract_v1.py`, preflight, and eight ablation v1 suites), exit 0.
- Scoped Ruff over owned evaluation, preflight, persona, freeze, and ablation files: clean.
- Graphify: one `graphify update .`, AST extraction only, exit 0; log is `recovery_final_graphify_20261023T042800Z.log`.
- Final strict loopback trace: `p0_final_trace/trace_summary.json`, PASS. It exercised three positive and one negative SSH command, strict profile, loopback listeners, candidate/served correspondence, actual HTTP 503, no accepted negative commit, no fabricated claim, and cleanup.
- Supervisor combined evidence (489 tests / 25 files, independently run): copied byte-for-byte under `supervisor_combined_evidence/`; it is preserved evidence and is not added to the 86-test count.
- Baseline comparison: all 5,352 tracked `data/`, `results/`, and `paper/` records match `docs/research/baseline/tracked_sha256_20261022T184958Z.jsonl`. The 13 changed records in the full 5,866-record inventory are the already-owned runtime/test changes listed in `baseline_compare.json`.

## Persona boundary

`docs/research/persona_alignment_20261023T042600Z/` is the valid bounded proof: exactly two real loopback SSH sessions with five commands each, provider disabled. Native Cowrie matched the declared `webapp@web-srv-01:~$` persona. The RAGIN arm exposed `webapp@web-srv-01:/$` and failed closed for unsupported command responses. The raw frontend bytes are preserved. This remains an explicit persona/outer-frontend mismatch blocker; no verifier or candidate checks were relaxed.

## External approval boundary

The preflight packet remains draft and unexecuted: `docs/research/generation_contract_v1/external_preflight_v1/APPROVAL_PACKET.md` and `REQUEST_MANIFEST.json` (packet digest `795a28bd70b92220cecece2b4eb3f38d7baa207d7d9cb37a1c69048e566a9893`). It requests at most four synthetic generation POSTs, zero retries, one free alias, and expected cost `$0` without billing attestation. No provider endpoint, bridge, AWS, JEV, download, install, training, or public deployment was used. Approval is still required before any external traffic; the packet cannot establish scientific B1–B3 decoding or model identity.

## Remaining blockers

The B1–B3 runner, model exposure/identity and decoding attestation, datasets/splits/resource enforcement, higher-level statistics, human ratings, and B5/JEV remain `NOT_READY` or `NOT_ESTABLISHED`. The final local trace demonstrates deterministic runtime mechanics and fail-closed observability only.
