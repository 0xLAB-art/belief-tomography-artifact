# Pre-registration — E12 and T12 (tomographic reactivity / observer effect)

**Logged:** 2026-11-19, **before any E12 data was generated or inspected.**
**Estimator:** frozen `tomograph`/`wilson` at `8ceb6e0`. Fully offline.

## Motivation

E2-v0 was invalidated because all probes shared one conversation context
(`E2_V0_ARCHIVE.md`). That was treated as a bug. It is also a measurement
phenomenon: an agent that observes its own past replies can adapt, so probing
it in a shared session changes the quantity being estimated. We register the
general statement and a constructed demonstration. The social-science analogue
(observer/Hawthorne effects) is acknowledged; we do not claim the general
phenomenon is new. The new object is the **reactivity bias** of a behavioral
belief estimator and the identification condition (session reset) that removes
it.

## 1. T12 — Reactivity bias (proof obligation before data)

Let the independent-session estimand be $\beta = \Pr_\pi[\text{breach}]$ for a
fresh session. Let the shared-context estimator pool $n$ probes in one
conversation and let the target's breach probability after $k$ prior in-context
replies be $\beta_k$. If $|\beta_k-\beta|\le c k$ for a reactivity constant $c$,
then the pooled estimator satisfies
$|\hat\beta_{\mathrm{shared}}-\beta| \le c(n-1)/2$ (average of the first $n$
terms), and $\hat\beta_{\mathrm{shared}}$ is a consistent estimator of a
*different* quantity --- the context-conditioned behavior --- not of $\beta$.
Session reset ($k=0$ for every probe) is the identification condition.

**Claim boundary:** an elementary averaging bound; the contribution is naming
the bias for behavioral security measurement and showing its magnitude on the
instrument. Not a new theorem.

## 2. E12 — constructed demonstration (registered design)

**Foil `ContextualFoil(shared: bool)`:** deterministic. Its intended outcome on
probe $i$ is a breach iff $i$ is even (so the *independent* estimand is
$\beta=0.5$). It counts its own prior breaches in the current context;
once it has breached twice in that context, it refuses all later probes
(an in-context safety adaptation). `reset()` clears the count **only** in
independent mode.

**Endpoints (registered):**
1. $\hat\beta_{\mathrm{ind}}$: frozen tomography, 20 probes/cell, seeds
   $\{2718,99001\}$, independent sessions.
2. $\hat\beta_{\mathrm{shared}}$: same batch and seeds, one shared context.
3. Reactivity bias $\hat\beta_{\mathrm{ind}}-\hat\beta_{\mathrm{shared}}$
   and relative bias $(\hat\beta_{\mathrm{ind}}-\hat\beta_{\mathrm{shared}})
   /\hat\beta_{\mathrm{ind}}$, with Wilson CIs.
4. The number of breaches observed in the shared run (expected small: the foil
   stops after two).

**Registered success:** $\hat\beta_{\mathrm{ind}}\approx0.5$ and
$\hat\beta_{\mathrm{shared}}\le0.1$ at both seeds, with relative bias $\ge0.8$.
Otherwise report as inconclusive.

**Kill criterion E12:** do not claim the reactivity result unless the registered
conditions hold at both seeds.

## 3. Disclosures fixed before data

- The foil is a constructed deterministic model of in-context adaptation, not
  a measured production agent. No E12 number is transferred to E2-v1.
- E2-v0 remains archived as *invalid*; E12 explains a mechanism, it does not
  rehabilitate any v0 number.
- The lexical oracle's 20% FP / 48% FN boundary behavior is disclosed; breach
  replies are literal disclosures.
- Failed conditions, if any, retained with a dated entry before any re-run.
