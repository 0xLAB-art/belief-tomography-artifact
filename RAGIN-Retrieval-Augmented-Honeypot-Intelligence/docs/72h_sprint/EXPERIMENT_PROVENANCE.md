# Experiment Provenance

This sprint produced engineering and security evidence, not new effectiveness claims.

## Evidence classes

| Class | Contents | Treatment |
|---|---|---|
| Historical | JEV/OpenCode, prior live campaigns, prior Cowrie results | Retain and label historical; never relabel as Laya or new field evidence |
| Provider-free canonical | Existing rescue benchmark, ablations, verifier tests | Refer to `docs/RAGIN_RESULTS_LEDGER_2026-10-08.md`; do not overwrite |
| New controlled | mTLS server code, local socket matrix, regression tests, AWS subnet readback, provider-backed staging, fallback benchmark | New sprint evidence; no effectiveness extrapolation |
| Public field | None | No ambient traffic collected; no pilot claim |

Every new security result is tied to source code, test command, timestamp, and a redacted outcome in `E2E_TEST_RESULTS.md`. No raw credential, private key, provider token, or unredacted source address is stored here.

The configured DeepSeek model was absent from the observed catalog. The active local staging selector is now `opencode/space-bunny-free` through a loopback bridge around the installed OpenCode CLI. The bounded report `results/overnight_20261009/opencode_provider_limit1.json` contains two `GENERATED_VERIFIED` cases and one `TEMPLATE_FALLBACK_VERIFIED` case; the redacted provider/configuration envelope is `evidence/opencode_provider_benchmark_20261009.json`. The earlier controlled benchmark deliberately forced an unavailable local gateway and remains fallback-only; it must not be described as a provider evaluation.
