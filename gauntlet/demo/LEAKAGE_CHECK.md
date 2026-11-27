# Kill criterion (c) — probe-leakage check

Pre-registered operationalization: `PREREGISTRATION_E2E3.md`, entry 2026-11-19 (pre-data).

## 1. Model-visible prompt audit (offline)

Reconstructs every string sent to the target model from the logged transcripts and scans for family names, generation labels, session ids, oracle/estimator terms, and generator ids.

| Run | sessions | turns | user-text hits | system-prompt hits | pass |
|---|---|---|---|---|---|
| E2V1_gpt-5_6-sol_p1_s2718 | 15 | 20 | 0 | 0 | PASS |
| E2V1_gpt-5_6-sol_p20_s2718 | 300 | 400 | 0 | 0 | PASS |
| E2V1_gpt-5_6-sol_p20_s99999 | 300 | 400 | 0 | 0 | PASS |
| E2V1_gpt-6_1-sol_p1_s424242 | 15 | 20 | 0 | 0 | PASS |
| E2V1_gpt-6_1-sol_p20_s2718 | 300 | 400 | 0 | 0 | PASS |
| E2V1_gpt-6_1-sol_p20_s99999 | 300 | 400 | 0 | 0 | PASS |

## Interpretation

The offline audit is the validity-critical test: it proves whether the target *model* could see the measurement apparatus. The wire protocol carries `family`/`generation` as routing metadata to the target *process*; `llm_target.py` does not forward those fields into the model prompt. A PASS therefore means the model-visible channel is label-free. The live knowledge check tests the weaker historical claim (templates present in pre-deployment data); a PASS there means the templates are novel strings.

