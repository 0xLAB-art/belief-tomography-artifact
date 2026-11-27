# AI-Derived Evidence-Support Reference Protocol V2.2

Status: frozen before V2.2 annotation calls.

## Objective and limits

This is a single-reviewer AI-derived assessment of the existing retrospective 120-case Evidence Judge ablation. It is neither human ground truth nor independent consensus. A single fixed model can make correlated or systematic errors. Findings are descriptive for this already-used cohort and cannot support fresh confirmatory performance, deployment benefit, or field-effectiveness claims.

Human return directories remain empty. V1, V2, and V2.1 attempted external multi-model routes; those attempts and their errors are preserved under their original directories. V2.1 accepted no annotation payloads. Its all-UNKNOWN output is an execution-failure record, not a reference. V2.2 uses the authenticated local Codex CLI with strict JSON Schema output as a new, separately frozen route.

## Source and blindness

- Source packet: `results/evidence_judge_real_data_ablation_v1/blinded_reference_packet.json`
- Frozen packet SHA256: `975f24fca75b0deb8d930252294ddf729eff850d715f87dc8bcac0706c4aacb5`
- Cohort: 120 cases and 947 retrieved candidates.
- Each request contains only case ID, observed command, available context, behavioral claim, and frozen candidate ID/source/title/content/version/provenance hash.
- Judge decisions, gate outputs, arm/policy outputs, analysis summaries, source-group IDs, and context hashes are excluded.
- The coordinator has previously seen aggregate outcome summaries. Neither the requested Codex reviewer nor its prompts receive those summaries or any system output.

## Fixed reviewer and instrument

One primary reviewer is assigned to all six consecutive packet-order batches of 20:

| Rater | Fixed model identity | Interface |
|---|---|---|
| C1 | `gpt-5.6-luna` | Codex CLI `0.162.1`, `codex exec --ephemeral`, strict `--output-schema` |

The model is selected explicitly on every call. The invocation runs from `/tmp`, not the RAGIN repository, and receives the blinded batch over standard input. The exact command, CLI event stream, final message, usage, exit status, and hashes are preserved. No model substitution or free-form JSON extraction is allowed. Each batch receives one call; a failed, incomplete, malformed, or citation-invalid output becomes UNKNOWN for affected fields.

Candidate labels are `DIRECT_SUPPORT`, `PARTIAL`, `IRRELEVANT`, `CONTRADICTORY`, and `UNKNOWN`. Bundle labels are `SUFFICIENT`, `INSUFFICIENT`, `CONFLICTING`, and `UNKNOWN`. Non-UNKNOWN candidate labels require a valid 1-based paragraph locator into the cited candidate. UNKNOWN requires no locator. The frozen V2 primary prompt defines the semantics and output fields.

## Aggregation and reporting

There is no adjudicator and no inter-rater agreement statistic for a single reviewer. Preserve the reviewer output exactly, map candidate indexes to frozen document IDs, and set malformed, missing, duplicate, out-of-range, or uncited decisions to UNKNOWN. Report coverage, exact label counts, citation validity, model identity, execution usage, and all unknowns. Do not describe the output as ground truth, human consensus, or independent model agreement.

## Locked analysis

Only after the reference and its hash manifest are frozen may the locked evaluator read the matched arm output and downstream paired comparison. Compare candidate/bundle labels only over reference-evaluable fields and report UNKNOWN coverage. Report gate/retention changes descriptively, preserving the original cohort and protocol limitations. Cluster uncertainty by case/source-family only where the original sampling design supports it. Do not use this cohort for confirmatory model selection.

