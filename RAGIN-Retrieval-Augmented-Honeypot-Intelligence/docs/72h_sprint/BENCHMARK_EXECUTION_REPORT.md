# Benchmark Execution Report

No new effectiveness benchmark was run in this checkpoint. The new evidence is a controlled deployment smoke test, mTLS boundary validation, and Cowrie-to-CORE serving trace. It must not be presented as a population study, field effectiveness result, or provider-backed generation benchmark.

## Available evidence

- Direct EDGE-to-CORE authenticated session, command, replay, verifier, and provenance records.
- Cowrie `whoami` request with synthetic output and CORE response status.
- Negative mTLS/API-authentication boundary cases.
- Existing repository test results: 1,645 passed, 116 skipped, 34 warnings.
- Focused mTLS/serving regression run: 42 passed.

## Next controlled experiment namespace

New measurements should use a timestamped namespace such as `results/overnight_20261008/`, with input/configuration hashes, provider/model identity, request IDs, verifier outcomes, fallback transitions, and explicit exclusions. Historical JEV/OpenCode results remain unchanged and separately labeled.
