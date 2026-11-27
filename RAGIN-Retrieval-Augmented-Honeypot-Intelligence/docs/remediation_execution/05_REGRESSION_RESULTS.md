# 05 — Regression Results

**Session:** RAGIN remediation execution
**Environment:** `.venv` Python 3.12.3
**Repo head:** `f0c4042c0eb2ee25854796b770ea440f0b5851b2`
**Worktree at session end:** dirty (2383 short-status lines; 2544 untracked; ~25 modified tracked files among them including `server_v2.py`, `docker-compose.yml`, `hisoka/deception.py` unchanged except read)

---

## 05.1 Fresh collection baseline (this session)

Command: `pytest --collect-only -q`

- Collected: **1837 tests** in 2.25s
- Test files: 80
- Top-level directory item sums:
  - `tests/unit`: 1557
  - `tests/security`: 60
  - `tests/integration`: 114
  - top-level `tests/`: 106 (e2e_comprehensive 62, performance_benchmark 17, security_validation 27)

Note: `benchmark_traditional.py` lives at repo top level and is not discovered by default pytest collection in `tests/`.

---

## 05.2 Suites executed this session

1. **Security task2 verified serving**
   - Command: `pytest tests/security/test_task2_verified_serving.py -q`
   - Result: **16 passed**
   - Includes the three P0-B regression tests added this session.

2. **Server v2 unit**
   - Command: `pytest tests/unit/test_server_v2.py -q`
   - Result: **24 passed**

3. **Verifier + fiction + hisoka + artifact consistency**
   - Command: `pytest tests/unit/test_verifier.py tests/unit/test_fiction_graph.py tests/unit/test_hisoka.py tests/unit/test_artifact_consistency.py -q`
   - Result: **239 passed**

4. **Cycle + don + chrollo + hitl + host fiction**
   - Command: `pytest tests/unit/test_cycle.py tests/unit/test_don.py tests/unit/test_chrollo.py tests/unit/test_hitl.py tests/unit/test_host_fiction.py -q`
   - Result: **230 passed**

5. **Combined focused regression (this session's final sweep)**
   - Command: `pytest tests/unit/test_server_v2.py tests/security/test_task2_verified_serving.py tests/unit/test_verifier.py tests/unit/test_fiction_graph.py tests/unit/test_hisoka.py tests/unit/test_artifact_consistency.py tests/unit/test_cycle.py -q`
   - Result: **279 passed** in 2.64s

---

## 05.3 Counts reconciliation

| Source | Count | Notes |
|--------|-------|-------|
| Fresh collection, all tests | 1837 | current baseline |
| Focused regression executed this session | 279 | server_v2 + task2 + verifier/hisoka/cycle selection |
| Prior audit suite table sum | 511 | 47+11+13+186+24+230 |
| Prior audit headline "executed this audit" | 471 | does not match either 511 or current suites exactly |
| Prior audit "464" referenced in prompt | n/a | not found in audit artifacts; appears to be a prompt-side figure |

So the prior "471 vs 464" discrepancy is not reproducible as written; the current reproducible number is 1837 collected, with 279 in the focused regression sweep.

---

## 05.4 Failures and skips

- No test failures in the executed suites this session.
- No skips reported in the focused regression output.
- Full suite (1837) was **not** executed this session because it includes LLM-backend-dependent and AWS-dependent tests. That remains a later milestone.

---

## 05.5 Warnings observed

- Pytest unknown-mark warnings for `e2e` and `slow` marks in some files when collected. These are registration warnings, not failures.

---

## 05.6 Exit status and runtime

- Combined focused regression exit code: 0
- Runtime: ~2.6s for the 279-test combined sweep.

---

## 05.7 What changed under test

- `ragin/server_v2.py`: added `_is_production_auth_disabled()`, `_production_auth_is_enforced()`, warning in `_validate_security_config()`.
- `tests/security/test_task2_verified_serving.py`: added 3 P0-B regression tests.
- `docker-compose.yml`: added `pipeline` service, `pipeline-data` volume, gateway healthcheck curl, nginx interpolation softening.
- `ragin/hisoka/deception.py`: not modified this session (fully read).

All modified-under-test files passed the focused regression.
