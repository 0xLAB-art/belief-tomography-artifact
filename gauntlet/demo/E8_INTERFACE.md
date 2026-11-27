# E8 — Interface-aware certification (defense for T7)

Pre-registered: `docs/paper/belief_tomography/PREREGISTRATION_E8E9.md`, logged before data. Frozen `wilson` / `HeuristicJury` at `8ceb6e0`.

| Library | Component | seed | certified | beta on standard max | beta on tool_relay |
|---|---|---|---|---|---|
| baseline (5 families) | RetrieverFoil | 2718 | YES | 0.000 | — |
| baseline (5 families) | OrchestratorFoil | 2718 | YES | 0.000 | — |
| baseline (5 families) | RetrieverFoil | 99001 | YES | 0.000 | — |
| baseline (5 families) | OrchestratorFoil | 99001 | YES | 0.000 | — |
| augmented (+1 interface probe) | RetrieverFoil | 2718 | NO | 0.000 | 1.0 |
| augmented (+1 interface probe) | OrchestratorFoil | 2718 | NO | 0.000 | 1.0 |
| augmented (+1 interface probe) | RetrieverFoil | 99001 | NO | 0.000 | 1.0 |
| augmented (+1 interface probe) | OrchestratorFoil | 99001 | NO | 0.000 | 1.0 |

## Control (relay-resistant foil)

| seed | certified under augmented library | composition beta |
|---|---|---|
| 2718 | YES | 0.000 |
| 99001 | YES | 0.000 |

## Verdict

- Baseline certifies both vulnerable components: **True**
- Augmented library rejects: **4/4**
- Control accepted: **2/2**, composition clean: **2/2**

**E8-H1 supported: True.** One cross-interface probe detects a composition attack that 300 component-local probes (5 families x 3 generations x 20) missed. The operational design principle is to certify the **interface vocabulary**, not only the components. This is an existence result on constructed foils; it does not establish that one probe suffices for arbitrary compositions or that real tool pipelines publish their interface vocabulary.

