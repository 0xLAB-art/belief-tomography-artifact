# GAUNTLET — Adversarial World Engine (AWE) v0

Closed-loop adaptive adversarial certification for AI systems.
**The test is not fixed — the test is a living adversary.**

Spec: `docs/innovation/AWE_SPEC.md`

```
gauntlet/
  gauntlet/
    world.py         # Episode/Phase data model
    generator.py     # 5 families x 3 generations template worlds (seeded)
    harness.py       # closed loop: probe pass -> adaptive reallocation (UCB-lite)
    verdict.py       # oracles + heuristic jury (v0); calibrated multi-jury lane = v1
    certificate.py   # certificate + failure taxonomy (markdown + JSON)
  demo/
    target_dummy.py  # deliberately naive foil target
    run_certification.py
```

Run the demo:

```bash
cd gauntlet
python3 demo/run_certification.py
```

Outputs `demo/CERTIFICATE.md` + `demo/results.json`.

v0 honesty: template worlds + heuristic jury prove the pipeline. Unbounded
novelty (LLM-authored worlds) and the calibrated multi-model jury arrive in v1/v2.
