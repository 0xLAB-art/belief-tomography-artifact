# Test execution integrity

## Why prior reporting was contradictory

Bare pytest with no `|| true`, no shell pipes, and no documented wrapper reports
a non-zero shell exit code when tests fail.

In this session, the main unit suite (`python -m pytest tests/unit/ -q`) exits
non-zero because it has failures.

In contrast, some sub-suites genuinely pass and exit 0, for example the
optional-assessment plus security subset.

So two different statements can both be true:
- The full unit suite has failures and exits non-zero.
- A subset of the suite passes and exits 0.

Prior contradictory wording came from mixing suite-level and sub-suite-level
observations, possibly through a pipeline or wrapper that masked exit status.

## Exact evidence captured this session

Environment:
- python: `/usr/local/bin/python`
- python version: `Python 3.12.3`
- pytest: `pytest 9.1.1`

Commands and true shell exit codes:
- `python -m pytest tests/unit/ -q` → exit 1 (21 failed, 1542 passed, 31 warnings, 10 errors)
- `python -m pytest tests/unit/test_verifier_redteam_security_oracle.py -q` → exit 1 (1 failed, 7 passed)
- `python -m pytest tests/unit/test_optional_assessment.py tests/security/ -q` → exit 0 (69 passed)
- `python -m pytest tests/unit/test_hisoka_memory.py -q` → exit 1 (20 failed, 4 passed)
- `python -m pytest tests/unit/test_server_v2_laya_config.py tests/unit/test_server_v2_laya_runtime_no_second_path.py tests/unit/test_optional_assessment.py tests/security/ -q` → exit 0 (85 passed)

Artifact files:
- `/tmp/py_unit.out`
- `/tmp/py_oracle.out`
- `/tmp/py_opt.out`
- `/tmp/py_hisoka.out`

## Failure inventory classification

- `tests/unit/test_verifier_redteam_security_oracle.py::test_oracle_validate_passes`
  - classification: PRE_EXISTING_CONFIRMED
  - reason: stable fixture-level failure (missing `should_pass` cohort in oracle validate logic), unrelated to Laya.
- `tests/unit/test_hisoka_memory.py`
  - classification: ENVIRONMENT_DEPENDENT
  - reason: module imports cleanly in this environment, but the test suite fails at runtime; not fully diagnosed here.
- No NEW_REGRESSION claim is made without baseline evidence.
- UNKNOWN is reserved for the hisoka_memory failures pending deeper diagnosis.

## Boundary
- The unrelated verifier oracle failure is NOT fixed here just to obtain green output.
