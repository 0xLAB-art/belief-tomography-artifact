# E18 — Estimator robustness (hierarchical Bayes vs frozen Wilson)

Pre-analysis registered: `docs/paper/belief_tomography/PREREGISTRATION_E18E19E20.md`. The registered estimator (8ceb6e0) is unchanged; this validates inference robustness and quantifies empirical-Bayes shrinkage for a possible v2.

| dataset | prior | all agree | mean width ratio (Bayes/Wilson) | flips |
|---|---|---|---|---|
| E1_dose_response | method-of-moments from 25 cells (m=0.465, v=0.1259) | False | 0.883 | none |
| E2v1b_gpt-5_6-sol_null | fallback Beta(1,1) (degenerate cell variance) | False | 0.992 | none |
| E2v1b_gpt-6_1-sol_null | fallback Beta(1,1) (degenerate cell variance) | False | 0.992 | none |
| E17_audit_rates | fallback Beta(1,1) (overdispersed cells: v=0.3077 exceeds the binomial ceiling 0.2500) | False | 0.989 | none |
| E4 | skipped: E4 profiles store intervals only, no per-cell counts — disclosed per registration | — | — | — |

## Verdict

- Point estimates agree everywhere: **False** — disagreement confined to boundary cells: {'E1_dose_response': ['authority_forgery@dose0.0', 'authority_forgery@dose1.0', 'state_deception@dose0.0', 'state_deception@dose1.0', 'goal_subversion@dose0.0', 'goal_subversion@dose1.0', 'epistemic_echo@dose0.0', 'exfiltration_lure@dose0.0', 'exfiltration_lure@dose1.0'], 'E2v1b_gpt-5_6-sol_null': ['gpt-5_6-sol:authority_forgery:1', 'gpt-5_6-sol:authority_forgery:2', 'gpt-5_6-sol:authority_forgery:3', 'gpt-5_6-sol:state_deception:1', 'gpt-5_6-sol:state_deception:2', 'gpt-5_6-sol:state_deception:3', 'gpt-5_6-sol:goal_subversion:1', 'gpt-5_6-sol:goal_subversion:2', 'gpt-5_6-sol:goal_subversion:3', 'gpt-5_6-sol:epistemic_echo:1', 'gpt-5_6-sol:epistemic_echo:2', 'gpt-5_6-sol:epistemic_echo:3', 'gpt-5_6-sol:exfiltration_lure:1', 'gpt-5_6-sol:exfiltration_lure:2', 'gpt-5_6-sol:exfiltration_lure:3'], 'E2v1b_gpt-6_1-sol_null': ['gpt-6_1-sol:authority_forgery:1', 'gpt-6_1-sol:authority_forgery:2', 'gpt-6_1-sol:authority_forgery:3', 'gpt-6_1-sol:state_deception:1', 'gpt-6_1-sol:state_deception:2', 'gpt-6_1-sol:state_deception:3', 'gpt-6_1-sol:goal_subversion:1', 'gpt-6_1-sol:goal_subversion:2', 'gpt-6_1-sol:goal_subversion:3', 'gpt-6_1-sol:epistemic_echo:1', 'gpt-6_1-sol:epistemic_echo:2', 'gpt-6_1-sol:epistemic_echo:3', 'gpt-6_1-sol:exfiltration_lure:1', 'gpt-6_1-sol:exfiltration_lure:2', 'gpt-6_1-sol:exfiltration_lure:3'], 'E17_audit_rates': ['specificity', 'FP_rate']} (continuous posteriors exclude exactly-zero cells by construction; the Wilson point 0 falls outside the credible interval there)
- Bayes intervals never wider on average: **True**
- Decision flips at τ=0.2: **none**

**Estimator-robust (registered test: zero decision flips): True** — headline inferences do not depend on the interval estimator.

