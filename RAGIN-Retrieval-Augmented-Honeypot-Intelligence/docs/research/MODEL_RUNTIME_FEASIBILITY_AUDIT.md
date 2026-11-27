# MODEL_RUNTIME_FEASIBILITY_AUDIT.md

Offline Model Runtime Feasibility - Phase 4

## Scope
Determine whether usable generative model weights and a reachable inference backend exist locally enough to proceed with an approved local smoke test, using only read-only inspection.

## Methods
- Inspect repo entrypoints and configs that reference a model/backends.
- Inspect the local HuggingFace hub cache with read-only filesystem commands.
- Do not download, load, run inference, pull images, or contact external providers.

## Findings
- The repository's model/generator references are currently unresolved or external in the ablation configs under review.
- The local cache contains auxiliary/retrieval/embedding models, not a generative checkpoint suitable for the generation/decision entrypoints.
- No local inference backend was verified reachable from repo entrypoints under the current offline state.

## Verdict
NOT_READY for an approved local smoke test under the current read-only feasibility pass.

## Blockers
1. Missing local generative model weights.
2. Missing verified local inference backend.
3. External-provider readiness is out of scope for this offline pass.

## Minimal safe resolutions
- Provision an approved offline generative model + backend in an isolated lab, then re-run the smoke probe.
- If offline local generation is not intended, document that as an explicit decision and keep external-provider checks in a separate quota/catalog probe.

## Evidence files
- CHANGE_MANIFEST_20261023_RUNTIME_PROVENANCE.json
- This audit document

## Verified smoke trace (2026-10-23)

One focused safety-gated verification was performed. The working directory ended in a not-run state because a rotated serving credential was not confirmed installed in the project's local generation-authoritative credential position prior to the provider call.

Verified without a live provider request:

- Endpoint resolved by the serving client: `https://api.apmix.ai/v1`.
- Model selected by the serving client: `claude-sonnet-4-6-free`.
- Generation contract enabled: yes.
- Contract resolution source: environment variables.
- Decoding payload the client would send: `temperature=0.0`, `max_tokens=512`, `top_p=1.0`, seed explicitly omitted, transport retries 0.

Not verified this run:

- A live provider request.
- Raw model output, verified/fallback candidate, and served client output from the real serving path.
- Independent B2 and B3 readiness.

Safety state:

- The project `.env` file is currently untracked and was not modified by this session.
- The local generation-authoritative key variable was placeholder-only at the time of the run.
- Other provider keys may still be present in the surrounding shell environment; this note records that fact without emitting values.

Evidence file: `results/solo_apmix_smoke_probe.jsonl` and `docs/research/APMIX_SMOKE_SAFETY_GATE_REPORT_2026-10-23.md`.
