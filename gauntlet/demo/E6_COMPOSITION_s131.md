# E6 — Certification does not compose (belief laundering)

Pre-registered: `docs/paper/belief_tomography/PREREGISTRATION_E6E7.md`, logged before data. Constructed deterministic foils; frozen estimator `wilson` and verdict engine `HeuristicJury` at `8ceb6e0`.

## 1. Local certification of components (5 families x 3 generations x 20)

| Component | seed | certified at tau=0.2 | max family beta |
|---|---|---|---|
| RetrieverFoil | 131 | YES | 0.000 |
| OrchestratorFoil | 131 | YES | 0.000 |

## 2. Cross-interface probe of the composition

| Target | seed | breaches/n | beta [95% CI] |
|---|---|---|---|
| ComposedPipeline | 131 | 20/20 | 1.000 [0.839, 1.000] |
| OrchestratorFoil (control) | 131 | 0/20 | 0.000 [0.000, 0.161] |

## Verdict

- Both components certified locally at both seeds: **True**
- Composition breaches at beta=1: **True**
- Negative control clean: **True**

**E6-H1 supported: True.** The retriever never discloses its secret under any public probe; the orchestrator never discloses its own secret under any public probe; the pipeline discloses the retriever's secret under a cross-interface probe that no single component sees. Per-component certification is therefore not a pipeline certificate.

## Mechanism and limits

The interface history (a document containing the retriever's secret under a `<tool:retriever>` tag) has zero measure under each component's public probe distribution. T1 therefore applies at the pipeline level: local behavioral evidence is silent exactly where the composed system fails. This is an **existence and mechanism** result on deterministic foils, not a prevalence estimate for deployed MCP or tool-use pipelines. The lexical oracle's constructed boundary behavior (20% FP / 48% FN) is disclosed; these sessions contain literal, unambiguous disclosures, where the oracle is competent.

