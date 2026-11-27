# T3 Policy Benchmark — probe-allocation efficiency

Profile: {authority_forgery:0.9, state_deception:0.5, goal_subversion:0.3, epistemic_echo:0.7, exfiltration_lure:0.1}; 150 trials per cell.

**Finding (negative result, policy-objective mismatch):** both intuitive adaptive policies LOSE to uniform at profile estimation — UCB-lite optimizes REGRET (find-the-worst-arm) and starves other families; PSI entropy-greedy optimizes information-about-theta, which misallocates effort across extreme-rate families. The estimation-correct criterion is variance equalization (Neyman).

| Budget | uniform | Neyman | UCB-lite | PSI |
|---|---|---|---|---|
| 25 | 0.1240 | 0.1258 | 0.1677 | 0.1458 |
| 50 | 0.0931 | 0.0954 | 0.1497 | 0.1298 |
| 100 | 0.0710 | 0.0656 | 0.1332 | 0.1204 |
| 200 | 0.0508 | 0.0459 | 0.1265 | 0.1214 |
| 400 | 0.0349 | 0.0353 | 0.1206 | 0.1288 |

## VERDICT: uniform error=0.0349 vs best adaptive=0.0353 at n=400 → uniform is the strong baseline; objective-mismatch quantified for UCB and PSI

*Field-level content for T3: probe-design objectives must MATCH the estimation goal. Regret-optimal (bandit) and information-optimal (psychophysics PSI) criteria are both misallocations for profile estimation; variance-equalizing (Neyman) is the correct criterion, and uniform is a strong baseline. This refines the open problem: MI-optimal design is the right tool for DETECTION-style tasks, not estimation.*
