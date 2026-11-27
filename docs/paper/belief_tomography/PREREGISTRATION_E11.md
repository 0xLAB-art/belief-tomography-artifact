# Pre-registration — E11 and T11 (certificate half-life under behavioral drift)

**Logged:** 2026-11-19, **before any E11 data was generated or inspected.**
**Estimator:** frozen `wilson` at `8ceb6e0`, imported directly.
**Lane:** fully offline deterministic foils.

## Adjacent work and the gap (internet research, verified 2026-11-19)

- *When Can Old Evaluations Certify a New Model?* (arXiv:2609.32267) studies
  **evaluator-error drift** and label-efficient release decisions (portfolio
  vigilance). Its target of inference is the *evaluator*, not the agent.
- *Towards Identity-Preserving LLM Agents under Model Transition*
  (arXiv:2611.10628) measures behavioral drift when the **backend model is
  swapped**, with 5,760 compliance runs; verbal claims stay compliant while
  decisions diverge (a BCG-like phenomenon across substrates).
- MemEvoBench (arXiv:2604.15774) measures drift from **memory misevolution**.

None of these defines or measures a **validity horizon for a security
certificate**: given a measured $\hat\beta$ with upper confidence bound $U$ and
a known drift rate bound $v$, for how long may the certificate $\beta\le\tau$ be
trusted, and how often must it be renewed? That is the object registered here.

## 1. T11 — Certificate half-life (proof obligation before data)

Assume the target's belief strength is $v$-Lipschitz in time:
$|\beta_{t+h}-\beta_t|\le v h$ for all $t,h\ge0$. Let a measurement at $t_0$
produce Wilson upper bound $U_0=\hat\beta_0+\varepsilon$ for a family-level
estimate. Then
\[
\beta_t \le U_0 + v(t-t_0)\quad\text{for all }t\ge t_0,
\]
so the certificate $\beta_t\le\tau$ is valid for
$h_\tau=(τ-U_0)/v$ when $U_0<\tau$, and invalid immediately otherwise.

**Proof obligation:** triangle inequality; $\beta_t\le\beta_{t_0}+v\Delta
\le U_0+v\Delta$. For $k$ sequential renewals, a Bonferroni-adjusted per-check
level $\alpha/k$ gives simultaneous validity $\ge1-\alpha$; this is a standard
union bound and is attributed as such. The **new object** is $h_\tau$ as a
certificate-validity horizon and the resulting renewal rule.

**Claim boundary:** this is a basic Lipschitz consequence; we do not claim a
new mathematical inequality. The contribution is applying it to behavioral
security certificates and measuring the cost of ignoring it.

## 2. E11 — Drift experiment (registered design)

**Foil `DriftFoil(v)`:** deterministic. Its per-cell breach fraction at epoch
$e$ is $\min(1, v e)$: within each 20-probe cell, the first $20 v e$ probes
produce a literal disclosure, the rest refuse. `set_epoch(e)` is called by the
experiment before each tomography run. Ground truth at epoch $e$ is
$\beta_e=\min(1, v e)$.

**Registered parameters:** $v=0.02$/epoch, $\tau=0.2$, epochs $e=0,\dots,12$
(so true $\beta$ crosses $\tau$ at $e=10$), batch 20 probes/cell, seeds
$\{2718,99001\}$. Wilson upper bound $U_e$ computed from the frozen estimator.

**Policies compared (registered):**
1. **One-shot:** certify at $e=0$, assume valid for all 12 epochs.
2. **Fixed interval:** set $\Delta=\lfloor h_0\rfloor$ from the initial
   half-life $h_0=(\tau-U_0)/v$, re-certify every $\Delta$ epochs.
3. **Drift-aware:** after each measurement, compute $h_e=(\tau-U_e)/v$ and
   re-certify at $t_e+h_e$ (clamped to remaining epochs). Use a fixed
   per-check level of 0.05; report the Bonferroni-adjusted variant as a
   secondary statistic.

**Endpoints (registered):**
- **False certifications:** number of epochs $e$ where a policy reports
  "certified" while true $\beta_e>\tau$.
- **Measurement cost:** total tomography runs (probes) used by each policy.
- **Half-life sequence** $h_e$ and whether $h_e$ shrinks as $\beta$ grows.

**Registered success:** one-shot has ≥1 false certification; fixed interval
has ≥1 false certification (because $h_e$ shrinks below $\Delta$); drift-aware
has 0 false certifications at both seeds and uses fewer probes than a policy
that re-certifies every epoch. Otherwise report as inconclusive.

**Kill criterion E11:** report the observed table; do not claim the half-life
result unless all three conditions hold at both seeds.

## 3. Disclosures fixed before data

- Constructed deterministic foil with an *assumed* drift-rate bound $v$ known
  to the certifier. In deployment $v$ must itself be estimated or bounded by
  policy (e.g., model-change events); we do not claim to solve that problem.
- The Wilson intervals are per-family; the experiment reports the max family
  $\hat\beta$ and its upper bound, matching the certification rule of E4.
- The lexical oracle's 20% FP / 48% FN boundary behavior is disclosed; breach
  replies are literal disclosures.
- No E11 number is transferred to E2-v1 or to production models.
- Failed controls, if any, retained with a dated entry before any re-run.

## 4. Pre-data amendment (logged before any E11 data exists)

The originally registered $v=0.02$/epoch over 12 epochs gives an initial
Wilson upper bound $U_0\approx0.06$ and hence $h_0=(0.2-0.06)/0.02=7$ epochs;
the fixed-interval policy ($\Delta=\lfloor h_0\rfloor=7$) and the drift-aware
policy would then renew at the same epoch, making the cost comparison
uninformative. **Amendment, before any E11 artifact exists:** use
$v=0.05$/epoch over epochs $e=0,\dots,8$ (true $\beta$ crosses $\tau=0.2$ at
$e=4$). Then $h_0=(0.2-0.06)/0.05\approx2.8$, $\lfloor h_0\rfloor=2$, and the
half-life shrinks within the horizon as $\hat\beta$ rises, so the three
policies are distinguishable. All endpoints, decision rules, seeds, batch,
estimator, and disclosures are unchanged. This amendment is logged before the
first E11 run so no data-dependent choice is made.
