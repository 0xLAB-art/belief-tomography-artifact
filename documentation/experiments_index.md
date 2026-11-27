# Experiment index — the E1–E31 registry

The manuscript numbers experiments by **registry slot, not chronology**: E24
was retired void before registration or data (hence the gap), E1b and T3 are
sub-protocols inside the E1 and allocation-benchmark slots, and E2-v0 is the
superseded run that E2-v1 replaced after the session-isolation fix. The
full table — all thirty slots with layer, registration status, and outcome —
is **Supplement Table S1** of the submitted manuscript, with
per-experiment registration timing in Supplement Table S2.

## Layers at a glance

| Layer | Slots | What it establishes |
|---|---|---|
| Instrument validity | E1, E1b, E4 | Dose–response linearity (Pearson r ≥ 0.986 per family), test–retest reliability (r = 0.949), the graded-foil target |
| Reliability & robustness | E6–E13, E18–E19 | Composition, gaming, forgery, adaptivity, halflife, reactivity, allocation, seed-robustness, estimator robustness |
| Deception gain on the live fleet | E3, E23, E25 | Δ(B) of attacker beliefs under deception operations |
| Field measurement | E2-v1/v1b, E20–E22, E26–E28 | β̂ of real agents; disclosure externality; library; L-sensitivity; scale-up; budget decomposition |
| Repaired field panel | E29 | The repaired gateway panel (seed 2718, identical instances) |
| Open-weight spectrum | E30, E31 | Three open-weight models under identical probes, 200 → 1024 token budgets |
| Blinded audit | E17 + Round-19 re-audit | Rubric channel calibration; blinded re-adjudication (κ = 0.96) |

## Where each layer's artifacts live

- **E1–E22, E25–E29**: `gauntlet/demo/` (result JSON, transcripts, verdicts,
  run logs, registrations E21–E29)
- **E30/E31**: `gauntlet/demo/E30_*` and `E31_*` panels + `PREREGISTRATION_E30_OPENWEIGHT_PANEL.md`,
  `PREREGISTRATION_E31_OPENWEIGHT_REPAIRED.md`
- **Live-fleet raw records**: `vps-export/2026-11-27/` (served sessions, field
  records, pre-NAT connection log, Cowrie history)
- **Audit**: `gauntlet/demo/E29_E30_ORACLE_AUDIT.md` +
  `docs/paper/belief_tomography/independent_reaudit/`

Every slot's outcome is mapped claim-by-claim in
[CLAIMS_EVIDENCE_LEDGER.md](https://github.com/0xLAB-art/belief-tomography-artifact/blob/main/docs/paper/belief_tomography/CLAIMS_EVIDENCE_LEDGER.md).
