# New Controlled Measurements

Status: LIMITED CONTROLLED EVIDENCE, not a broad effectiveness benchmark.

## Measurements recorded

- One provider-backed generation through isolated Cowrie, mTLS, CORE serving, and the mandatory verifier.
- One restored fallback flow with corrected `TEMPLATE_FALLBACK_VERIFIED` provenance.
- Positive mTLS and service-authentication path, with invalid/missing identity cases rejected in prior controlled tests.
- Container reachability checks: approved forwarder reachable; host SSH, metadata, and external connectivity test blocked from the Cowrie container.
- Optional assessment contract: fixture-backed typed signal, provider failure, and timeout all passed; no real Laya runtime was invoked.
- Earlier provider probe latency: 4570.7 ms; 22 total tokens. Latest provider readback after the fresh bounded request: 13,300 used, 2,986,700 remaining, top-up 0.
- Scorer audit: echoed CTI technique and actor queries scored 0.0 on served text; the reported 0.850 values came from the separate internal CTI-analysis channel combined by `max()`. The persona 0.800 score came from deterministic structured nginx text. See `evidence/scorer_audit_20261009.json`.

## Fallback benchmark run

Existing command: `.venv/bin/python scripts/run_live_benchmark.py --limit 1 --engine graph` with the gateway forced to `http://127.0.0.1:9`. The run completed in 12.11 seconds with three sessions and no pipeline errors. All three records carried `TEMPLATE_FALLBACK_VERIFIED`. Reported scores were CTI technique `0.850`, CTI actor `0.850`, and persona realism `0.800`; one unique TTP was detected, three artifacts were deployed, and zero artifacts were accessed.

The retrieval initializer accessed the existing `all-MiniLM-L6-v2` dependency through Hugging Face during setup. No paid generation provider or external attack target was contacted. The run is a fallback-path regression/measurement, not evidence of live generation quality or field behavior.

## OpenCode provider-backed benchmark run

The bounded follow-up used the selected local OpenCode replacement profile:

`.venv/bin/python scripts/run_live_benchmark.py --limit 1 --engine graph --report results/overnight_20261009/opencode_provider_limit1.json`

The loopback bridge invoked `opencode/space-bunny-free` through the installed OpenCode CLI with the deny-all tool profile. The 90.36-second run produced three sessions and zero pipeline errors. The CTI-technique and CTI-actor cases were `GENERATED_VERIFIED` (one passed case each, scores 0.850); the persona case was explicitly `TEMPLATE_FALLBACK_VERIFIED` (score 0.800), so it is not evidence of model generation. Average response time was 30,114 ms. This is a bounded local provider-backed benchmark, not an AWS deployment or a field study.

The redacted provenance envelope is `evidence/opencode_provider_benchmark_20261009.json`; the raw report is `results/overnight_20261009/opencode_provider_limit1.json`. The temporary bridge was stopped after completion. No public listener, paid model, or AWS resource was created.

## Evidence boundary

The namespace is staging-only and does not support claims about attacker behavior, human labels, broad model quality, or field effectiveness. No public observations were collected. Historical JEV/OpenCode measurements remain separate. Future runs must preserve input hashes, source revision, provider/model version, verifier outcomes, request IDs, and scorer version; attacker-supplied text must not be treated as independent labels merely because it is echoed.

Evidence files: `evidence/real_generation_provider_probe.json`, `evidence/real_generation_provider_probe_20261009.json`, `evidence/real_generation_e2e.json`, `evidence/cowrie_container_isolation.json`, `evidence/controlled_benchmark_fallback_20261009.json`, and `evidence/scorer_audit_20261009.json`.
