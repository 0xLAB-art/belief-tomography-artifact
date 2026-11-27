# Evidence Judge Filtering Post-Hoc Engineering Analysis

Status: `POST_HOC_ENGINEERING_ANALYSIS`

This report replays the frozen 120-case artifacts. It does not rerun Don retrieval, regenerate Judge labels, execute captured commands, or evaluate accuracy.

## Replay

Replay feasible: **YES**. All 120 cases retain candidate IDs, complete frozen Judge traces, sufficiency states, provenance flags, and retrieval traces. Arm A replay matched the frozen Gate output for 120/120 cases; unfiltered Arm B replay also matched 120/120.

## Impact

- Total retrieved candidates: **947**
- Originally relevant candidates: **523**
- Non-supporting candidates originally relevant: **0**
- Candidates actually excluded by the new filter: **0**
- Retained supporting candidates: **523**
- Changed policy-visible evidence sets: **0/120**
- Changed Gate decisions: **0/120**
- Cases with no supporting evidence remaining: **2**
- Fail-closed cases: **2**
- Provenance violations: **0**
- Missing or ambiguous traces: **0**

The 231 non-supporting Judge labels were outside the original `relevant_doc_ids` set. The new filter therefore made no additional exclusions on this frozen study. This is an engineering replay result, not an accuracy result.

## Safety

Excluded IDs reached Policy: **NO**. Unsupported evidence promotion: **NO**. Original documents, provenance, and Judge traces were preserved. Baseline mode remains disabled by default. Invalid and conflicting bundles remain fail-safe. Policy V2 was inactive and no attacker command was executed.

## Classification

`FILTERING_ENGINEERING_IMPACT_ESTABLISHED`

The implementation impact is identifiable as zero additional candidate exclusions and zero Gate changes on these frozen inputs. Real-world accuracy: **NOT EVALUATED**.
