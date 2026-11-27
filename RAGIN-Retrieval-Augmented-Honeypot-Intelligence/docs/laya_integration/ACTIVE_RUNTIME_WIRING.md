# Active Runtime Wiring (server_v2 → Sandbox → Harness → Chrollo)

Date: 2026-10-12. Continues RAGIN_INTEGRATION_STATUS.md; same checkpoint
(`english@55cf4c4…`), same `LayaAssessmentAdapter`, same `ragin/decision/laya_runtime.py`.

## Execution path traced

```
server_v2._init_pipeline()
  → ChrolloAdapter / DonAdapter / HisokaAdapter
  → Harness(mandatory_verification=True, host_store=…)
  → Sandbox(harness=harness)
  → Sandbox.handle_command() → Harness.process() → _process_verified()
      ├─ _run_classification → ChrolloAdapter.classify  ← Laya wired here (advisory)
      ├─ _run_cti_lookup → Don
      ├─ fiction(session) / strict candidate → FictionConsistencyVerifier + HostFictionVerifier
      ├─ ApprovalGateway (HITL)
      └─ strict commit (accepted-only state commit)
```

The wire point is inside `ChrolloAdapter.classify`: when
`RAGIN_LAYA_ENABLED=1`, a `laya_assessment` block is attached to the returned
classification dict. `Harness._run_classification` then emits it verbatim in the
`classification` session event (`source="chrollo"`), giving a durable trace ID'd
event-log record per command. No new serving path, no new endpoint, no change to
generation or verification.

## Files changed this phase

| file | change |
|---|---|
| `ragin/cycle/adapters.py` | NEW module function `laya_assessment_mapper(payload, session_id, attacker_input)` (env-gated, bounded state, timeout→NO_SIGNAL); `ChrolloAdapter.__init__` resolves the adapter once when enabled; payload gets `laya_assessment` attached after a successful native classify |
| `scripts/laya_e2e_two_sessions.py` | NEW — OFF/ON e2e runner, separate processes, replays event logs |
| `scripts/laya_paired_comparison.py` | NEW — runtime-behavior vs classification-quality separation |
| `docs/laya_integration/ACTIVE_RUNTIME_WIRING.md` | NEW — this file |

`ragin/server_v2.py`, `ragin/cycle/harness.py`, `ragin/cycle/sandbox.py`: **unchanged**
(this phase attaches at the adapter seam the harness already calls).

## Behavior contract verified

- Default `RAGIN_LAYA_ENABLED=0`: adapter resolves nothing; classification payload has
  no `laya_assessment` key; OFF-run event logs show `classification → laya_assessment: null`.
- Enabled: real forward pass per command; `provider="laya"`, `status="SIGNAL"`,
  latency, noul P(true), stage choice, severity recorded.
- Failure path: adapter try/except wraps the mapper → NO_SIGNAL recorded; classify
  itself cannot fail from the advisory path.
- Timeout: `RAGIN_LAYA_TIMEOUT_S` (default 30) enforced by the existing adapter's
  ThreadPoolExecutor contract.

## ON/OFF e2e evidence (raw: results/laya_research/e2e_sessions.json)

| run | trace_id | session_id | laya in events | responses ok | verification events |
|---|---|---|---|---|---|
| OFF | `bd95c9c6-308e…` | `ses-d1565a0dce144929` | 0 (null) | yes | 2 (passed) |
| ON | `424b5504-786c…` | `ses-5e59cee22b78417f` | 2, `provider=laya`, SIGNAL | yes | 2 (passed) |

ON-run laya latencies: 23.1 s (first call incl. load) and 3.5 s (warm).
Identical benign inputs, identical verified system responses in both runs —
Hisoka output and accepted-only commit behavior unchanged by the advisory signal.

Paired summary: `results/laya_research/paired_comparison.json`
(runtime proof: `behavior_identical_when_disabled: true`, `laya_execution_proven: true`).

## Test results

- `tests/unit/test_optional_assessment.py` + `tests/integration/test_laya_real_model.py`: 7 passed.
- Affected subset (`-k "harness or adapters or sandbox or session or verifier or fiction or host_fiction"`):
  **347 passed, 1 failed** — the pre-existing, previously-diagnosed
  `test_verifier_redteam_security_oracle::test_oracle_validate_passes` oracle-fixture gap
  (fails on the clean tree too; not caused by Laya).
- `tests/security`: **66 passed** (mTLS transport, verified-serving security).

## Data-class distinction and claims discipline

- Runtime behavior (OFF vs ON) is deterministic, trace-ID-proven from session logs.
- Classification quality (0.778 acc / 0.60 recall / Brier 0.151) is measured ONLY on the
  45-case synthetic set with by-construction labels — that is NOT independent evaluation
  data, and no statistically demonstrated improvement over baseline instrumentation is
  claimed. The only permitted comparison is against trivial baselines
  (always-benign 0.556; seeded random ≈0.5).
- An independently labeled Cowrie-derived evaluation set remains the prerequisite for
  any effectiveness claim (see NEXT_RESEARCH_STEPS.md step 1).

## Remaining limitations

- Two e2e sessions run once each — deterministic proof, not a statistical comparison.
- `server_v2.py` itself untouched: the toggle lives on the adapter; surfacing it in the
  server's own config surface is still possible follow-up (not required: the adapter is
  the seam server_v2 constructs through).
- Laya ON adds 3.5–23 s CPU assessment latency on this workstation; conditional calling
  (only when Chrollo is uncertain) is the next cost optimization if ON becomes default.
