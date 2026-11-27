### Task 3: Repair the JEV hard-subset artifact and lock its interpretation

**Files:**
- Modify: `results/jev_hard_subset.json`
- Modify if needed: `tests/unit/test_artifact_consistency.py`, `tests/unit/test_supported_claims.py`
- Synchronize later: `README.md`, `paper/sections/evaluation.tex`, `paper/sections/appendix.tex`, `results/sp2027_rescue/README.md`

**Interfaces:**
- Consumes: current JEV counts and the manuscript’s bounded six-row interpretation.
- Produces: one internally consistent artifact whose counts, resolution statement, tests, and paper prose all describe the same six informative rows.

- [ ] **Step 1: Write a failing consistency assertion if none exists.** Assert `base_incorrect_informative == 6`, `len(informative_rows) == 6`, `jev_arm.assessed == 1`, `jev_arm.unavailable == 5`, and `jev_arm.rescued == 1` for the current corpus, while also asserting that the resolution text does not say the stratum is empty.
- [ ] **Step 2: Replace only the contradictory resolution wording.** State that the informative stratum contains six rows, one Jev-arm row was assessed and rescued, and five Jev-arm rows were unavailable/refused under the recorded policy; preserve the bounded refusal/availability caveat.
- [ ] **Step 3: Run the artifact and supported-claim tests.** Confirm the JSON and all claim extractors agree with the six-row interpretation.
- [ ] **Step 4: Compare the artifact against the manuscript.** Confirm no section implies six successful Jev rescues, full provider coverage, or an empty hard subset.

**Pass condition:** The artifact, tests, README, and paper use the same six/one/five counts and explicitly avoid extrapolating from the single assessed row.

