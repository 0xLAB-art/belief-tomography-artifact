### Task 9: Verify rescue-benchmark validity and limitations

**Files:**
- Verify: `results/sp2027_rescue/behavior_trajectory_benchmark.json`, `results/sp2027_rescue/README.md`, `scripts/sp2027_rescue_behavior_benchmark.py`
- Modify if needed: rescue README, paper rescue sections, supported-claim tests

**Interfaces:**
- Consumes: `docs/RAGIN_RESULTS_LEDGER_2026-10-08.md`, provider status from Task 8, and the provider-free rescue corpus/artifacts.
- Produces: an independently reproducible rescue result with explicit split and interpretation limits.

**Required work:**
1. Recompute split integrity: verify 400 held-out test sessions, zero train/test ID overlap, session-level grouping, and the recorded prefix schedule.
2. Recompute learning-curve values: confirm skill-only prefix accuracy and behavior-floor coverage from the source script and artifact.
3. Verify the self-consistency boundary: confirm Supervisor and evaluation use the same risk-floor rule where applicable; label the comparison as self-consistency, not independent effectiveness.
4. Verify no provider contamination: confirm provider pilot artifacts are not required for the rescue result and fallback/provider traces are not counted as independent model evidence.
5. Synchronize rescue wording: state that this is benchmark-rescue/learning-curve evidence, not field validation or proof of adaptive-agent superiority.

**Constraints:**
- Work only on Task 9; preserve unrelated user changes.
- Do not run provider calls, alter provider pilot classifications, or invent adaptive-superiority/field-validation claims.
- Do not dispatch further agents.
- Create `.superpowers/sdd/2026-10-08-ragin-audit-remediation/task-9-report.md` with commands, exact outputs, hashes/timestamps, files changed, and residual limitations.

**Pass condition:** The rescue benchmark is reproducible from provider-free inputs and its claims are limited to held-out classification/behavior-floor evidence.
