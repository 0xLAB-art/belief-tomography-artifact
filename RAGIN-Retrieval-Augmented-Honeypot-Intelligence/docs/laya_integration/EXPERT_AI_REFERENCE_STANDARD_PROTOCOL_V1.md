# Expert AI Reference Standard Protocol V1

## Status and scope

This is the preregistration protocol for the EXPERT AI REFERENCE PANEL V1.
It records a resource-management decision made before annotation outcomes
exist. The previous frontier-model proposal was not used for annotation and is
replaced by the cost-aware assignment below.

The panel will classify the 120 frozen V3 cases in three independent AI
annotation sessions. This panel is not a human panel and must never be
described as human ground truth.

## Panel assignment

| session | assigned model | reasoning effort |
| --- | --- | --- |
| `expert_ai_01` | `GPT-6-Luna` | `MEDIUM` |
| `expert_ai_02` | `GPT-5.6-Sol` | `MEDIUM` |
| `expert_ai_03` | `GPT-5.6-Terra` | `MEDIUM` |

The sessions remain distinct model configurations. The panel retains one
stronger Sol-class anchor and uses lower-cost models for the other independent
annotation sessions. This does not claim that the lower-cost models are
equivalent in capability to the previous frontier-model proposal.

The recorded resource policy is:

```text
resource_constraint_reason = "Preserve remaining model-usage quota while maintaining model diversity."
```

This assignment is not outcome-driven model selection. It was fixed before
annotation and before any panel outcomes were available.

## Preserved V3 controls

The following scientific rules are unchanged:

- 120 frozen V3 cases.
- Three separate sessions with separate contexts.
- A separate shuffled packet order for each session.
- No repository access.
- No web search.
- No communication between annotators.
- The existing V3 taxonomy and semantic instructions.
- The existing aggregation policy.

The panel type is `MULTI_MODEL_INDEPENDENT_AI_SESSIONS`. Existing packets,
taxonomy, aggregation rules, and frozen V3 semantics are outside the scope of
this assignment update and must not be edited as part of this freeze.

## Model identity verification and invalidity rule

Before annotation begins in each session, the operator must verify and record
the observed model identity and its provenance. The observed model must match
the session's `assigned_model` exactly.

If the observed model differs from the assigned model:

```text
model_assignment_violation = true
run validity = INVALID_MODEL_ASSIGNMENT
```

The model must not be silently substituted. A session with an assignment
violation is invalid regardless of its labels or apparent quality.

If model identity cannot be verified, the session must not be treated as
validly annotated; record the identity as unknown and resolve the issue before
using the run.

## Annotation boundary

This protocol update does not run annotation and does not access prior
case-level annotations, Chrollo predictions, Laya predictions, frozen
predictions, or ground truth. Those materials remain outside this
pre-annotation freeze.

