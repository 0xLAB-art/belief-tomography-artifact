# Task 2: Security Regression Results

## Commands and outcomes

| Command | Result |
|---|---:|
| `.venv/bin/pytest -q tests/security/test_task2_verified_serving.py -p no:cacheprovider` | 11 passed in 3.27 s before the final transport-error tightening |
| `.venv/bin/pytest -q tests/security/test_task2_verified_serving.py tests/unit/test_server_v2.py -p no:cacheprovider` | 36 passed in 4.38 s after transport-error tightening |
| `.venv/bin/pytest -q tests/security/test_task2_verified_serving.py tests/unit/test_server_v2.py tests/unit/test_harness_threat_modeling.py tests/unit/test_cycle_graph.py tests/unit/test_verifier.py tests/unit/test_verifier_redteam.py tests/unit/test_supported_claims.py tests/unit/test_fiction_graph.py tests/unit/test_host_fiction.py tests/unit/test_host_fiction_wiring.py tests/unit/test_hitl.py tests/unit/test_jevi.py tests/unit/test_artifact_consistency.py -p no:cacheprovider` | 298 passed in 17.13 s after all current fixes |
| `.venv/bin/pytest -q -p no:cacheprovider` | 1639 passed, 116 skipped, 34 warnings in 339.71 s |
| `.venv/bin/python -m py_compile ragin/cycle/harness.py ragin/cycle/sandbox.py ragin/cycle/verifier.py ragin/cycle/graph.py ragin/graph/fiction.py ragin/graph/host_fiction.py ragin/server.py ragin/server_v2.py` | passed |

The first broad run before the final assertion correction was 296 passed and 1 failed because the new metrics-auth behavior had an old test expectation. No application failure remained after the correction.

## Covered invariants

`tests/security/test_task2_verified_serving.py` independently exercises no verifier, false decisions, verifier exceptions, retry exhaustion, invalid fallback, HITL REQUIRE without approval, persistence failure, concurrent commands, authenticated local ingress, unauthorized session access, and disabled legacy generation. The local ingress test reaches `aiohttp` -> `server_v2` -> `Sandbox` -> mandatory Harness and returns only the accepted candidate.

`tests/unit/test_cycle_graph.py`, `test_host_fiction.py`, and `test_host_fiction_wiring.py` cover staged graph/fallback behavior and explicit accepted-state promotion. Existing verifier, supported-claim, HITL, JEV, and artifact tests were run without changing historical result files.

## Not claimed

No external model call, Laya call, AWS action, Rust build/authentication test, public-port test, or 218-query campaign rerun was performed. Editor LSP reports missing imports for packages that are available to the `.venv` test runner; these are environment configuration diagnostics, not test failures.
