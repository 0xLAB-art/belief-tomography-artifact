# Expert AI Session Assignment

Session: `expert_ai_03`

Assigned model: `GPT-5.6-Terra`

Reasoning effort: `MEDIUM`

Before any annotation, verify that the observed model is exactly
`GPT-5.6-Terra` and record the observed identity and provenance in
`RUN_METADATA_TEMPLATE.json`. If it differs, set
`model_assignment_violation = true`, set run validity to
`INVALID_MODEL_ASSIGNMENT`, and stop. Do not silently substitute a model.

Use the frozen V3 packet and existing V3 semantic instructions supplied by the
controller. Keep the session independent: use a separate context and this
session's separate shuffled packet order; do not access the repository or web;
do not communicate with other annotators; and do not use prior annotations,
predictions, or ground truth.

This is an AI annotation session in
`MULTI_MODEL_INDEPENDENT_AI_SESSIONS`, not a human panel and not human ground
truth. The assignment was fixed before annotation outcomes for resource
management and model diversity.
