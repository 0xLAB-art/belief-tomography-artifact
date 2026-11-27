# Step 6 — Matched Evaluation Protocol Freeze

Date: 2026-10-15. Plan: `docs/PAPER_REMAINING_STEPS_2026-10-14.md` §Step 6.
Evidence root: `results/step6_matched_evaluation_protocol_v1/`.
Freeze script: `scripts/freeze_step6_evaluation_protocol_v1.py` (`run` / `verify`).

## Decision and frozen design

Step 4 binds this evaluation to two arms only. Arm A is baseline Don retrieval plus
the existing evidence gate. Arm B uses the identical Don evidence with the frozen
deterministic Evidence Judge/filter and the same gate. Policy, generator, verifier,
HITL, state initialization, deterministic closed-port serving mode, and corpus are
held identical within the contrast. The Laya scorer is excluded because its Step 4
feasibility gate failed; no arm C is defined.

The prospective controlled-real-admin registry contains 40 eligible captures. All
40 passed the preselection checks, have non-empty selected inputs, and have a
canonical-record digest matching the registry. Selection is deterministic by
`capture_id` and does not read judge, reference, gate, or arm outputs. The frozen
selection is recorded in `selected_cases_v1.json` with `N=40`.

The untouched boundary is explicit in `holdout_freeze_v1.json`: all 40 selected
case IDs, the registry hash, selection hash, and preselection summary are locked
before any arm outcome. The pre-arm reference inputs are frozen separately in
`reference_input_freeze_v1.json`, and deterministic Don retrieval candidates and
traces are frozen in `retrieval_evidence_freeze_v1.json`. Retrieval score and
relevance labels are stripped from the reference-facing candidates.

The Cowrie prospective directory produced no usable attacker sessions and is not
silently merged into the cohort. The study therefore freezes the controlled-admin
source only, with the Cowrie limitation retained for Step 7 reporting.

## Disjointness and sample size gates

The disjointness audit compared final-input byte/JSON digests, normalized family,
sequence, preceding context, exposed normalized text, and group/case identifiers
against every declared used cohort. Result: `PASS`, zero overlap hits across all
comparisons. The old HF-2024, judge, fixture, Laya, V4 holdout, and development
cohorts remain comparison-only exclusions and are not reused as Step 6 cases.

The preregistered paired design uses delta*=0.15, central paired-difference
sigma=0.25, alpha=0.05, and 80% target power. The central required sample is
N=24; the frozen N=40 full eligible cohort exceeds that requirement. Sensitivity
values and precision calculations are preserved in `power_analysis_v1.json`.

## Integrity verification

The protocol, selection, exclusions, disjointness audit, power analysis, freeze
manifest, blinded input packet, retrieval packet, and output hash manifest were
regenerated after repairing the capture schema binding. `python
scripts/freeze_step6_evaluation_protocol_v1.py verify` returned `PASS` with 95
checks and no failures. The freeze manifest locks 75 source
hash entries, including all selected canonical files, declared cohorts, code
anchors, reference-protocol artifacts, and corpus metadata.

The initial failed run and the invalid intermediate N=0 result were not retained
as evidence: the final outputs were regenerated from the corrected schema and
their hashes were then verified. The reference labels themselves remain pending
the separately blinded annotation step. The declared reference identity is
`gpt-5.6-luna via Codex CLI`, explicitly AI-derived rather than human ground
truth or independent consensus. This freeze locks the complete pre-arm
input and retrieval packet, not labels. No confirmatory arm execution, model-provider
call, logistic-policy arm, or live deployment action is implied by this freeze.

## Remaining boundary

Step 6 is complete. Step 7 must still prove the actual HTTP/SSH ingress and execute
all frozen case/arm pairs, preserving raw outputs and provider failures before any
Step 8 analysis or outcome join. This protocol freeze does not establish model
availability, in-process stage timers, field effectiveness, or scientific
submission readiness.
