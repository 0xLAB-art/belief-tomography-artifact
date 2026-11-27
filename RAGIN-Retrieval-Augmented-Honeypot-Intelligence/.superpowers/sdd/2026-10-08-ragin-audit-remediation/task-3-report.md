# Task 3 Report: Repair the JEV hard-subset artifact and lock its interpretation

## Status

Complete. The contradictory resolution wording in `results/jev_hard_subset.json` is
repaired, and a minimal consistency assertion now locks the six/one/five
interpretation in the existing artifact-consistency test surface.

## Changed files

1. `tests/unit/test_artifact_consistency.py`
   - Added `test_jev_hard_subset_counts_and_resolution_consistent` (AC5 section banner,
     matching the file's existing AC1–AC4 section-banner convention).
   - Asserts: `ceiling.base_incorrect_informative == 6`, `len(informative_rows) == 6`,
     `jev_arm.assessed == 1`, `jev_arm.unavailable == 5`, `jev_arm.rescued == 1`, and
     `"stratum is empty" not in resolution_statement`.

2. `results/jev_hard_subset.json`
   - Replaced only the `resolution_statement` string. New wording: the informative
     stratum contains six rows, one Jev-arm row was assessed and rescued, five
     Jev-arm rows were unavailable/refused under the recorded provider-refusal
     policy, and the single rescued row must not be extrapolated into full coverage.
   - Counts, informative rows, breakdown, provider note, and retry measurement
     left untouched. The bounded refusal/availability caveat from the original is
     preserved (folded into the new statement referencing the recorded policy and
     the conditional nature of the rescued row).

## Verification summary

- TDD observed failure: `pytest tests/unit/test_artifact_consistency.py -k jev`
  failed at line 187 (`"stratum is empty" not in doc["resolution_statement"]`)
  before the JSON fix — expected failure confirmed.
- After JSON edit: `pytest tests/unit/test_artifact_consistency.py tests/unit/test_supported_claims.py -q`
  → 44 passed.
- Full suite: `pytest -q` → 9 failed, 1585 passed, 116 skipped (222s).
  All 9 failures are `tests/unit/test_don.py` VectorStore/ThreatRAGEngine cases
  failing on a corrupted/missing `safetensors` file in
  `~/.cache/huggingface/.../model.safetensors` — a pre-existing local cache/dependency
  issue unrelated to this task (no don-engine code or artifact was modified).

## Concerns

- The 9 `test_don.py` safetensors failures predate this change; flagging for a
  later task rather than fixing here (out of scope).
- The artifact's retry measurement (`recovered: 0`, `still_unavailable: 5`,
  "effectively unreachable through the free route") coexists with the bounded
  "1 rescued live" interpretation. The statement now explicitly conditions the
  rescue on availability, so the two remain compatible; provider README / paper
  sections remain for their later synchronization tasks.
- No README, paper, provider artifact, or other result file was modified.
