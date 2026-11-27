# Controlled Evaluation Manifest

Status: arms frozen for controlled follow-up; only fallback and one provider-backed staging case are currently executed.

| Arm | Definition | Status | Evidence boundary |
|---|---|---|---|
| A | Verified deterministic fallback, mandatory verifier, normal retrieval path | EXECUTED | Three sessions; all `TEMPLATE_FALLBACK_VERIFIED`; no generation claim |
| B | Catalog-listed free provider, mandatory verifier, same private staging boundary | EXECUTED, separate workload | One Cowrie session `ses-46a0642581094765`; `GENERATED_VERIFIED`; not matched to Arm A's exact query |
| C | Provider-backed generator with retrieval ablation | NOT EXECUTED | Requires a new controlled run and explicit ablation manifest |
| D | Provider-backed generator with optional assessment disabled | NOT EXECUTED | The adapter contract is tested, but no provider-backed matched arm was run |
| E | Provider unavailable or timeout with mandatory fallback | EXECUTED | Three fallback sessions plus provider-unavailable local benchmark; no bypass observed |

## Frozen workload and scoring rules

The existing `scripts/run_live_benchmark.py --limit 1 --engine graph` workload is retained for the fallback diagnostic. Its CTI technique and actor rows declare `served_text+cti_analysis_max`; persona rows use served text. The echo guard gives query echoes zero served-text credit. This channel split is mandatory in future reports.

Source hashes and direct scorer checks are in `evidence/scorer_audit_20261009.json`. The benchmark report is `evidence/controlled_benchmark_fallback_20261009.json`. Results must preserve provider/model identity, serve path, verification result, input query, response digest, and the distinction between internal CTI analysis and attacker-visible text.

No arm is a field-study result. No sample-size or significance claim is supported by the current runs.
