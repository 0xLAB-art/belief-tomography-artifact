# AI-Derived Evidence-Support Reference Protocol V1

Status: frozen before any case-level annotation calls.

## Purpose and claim boundary

This protocol creates an AI-derived evidence-support reference for the existing retrospective 120-case Evidence Judge ablation. It does not create human ground truth, a gold standard, or an independent-model consensus. The three model outputs are potentially correlated; agreement is reported as AI-panel agreement only. Findings are descriptive for this already-used cohort and cannot support a fresh confirmatory-performance or deployment-benefit claim.

Human reviewers were preferred, but the three prepared human return directories contain only instructions to return completed files and no annotations or metadata. The available fallback is a fixed-identity, three-family AI panel. No labels will be manually authored or repaired by the coordinator.

## Frozen source and blindness

- Source packet: `results/evidence_judge_real_data_ablation_v1/blinded_reference_packet.json`
- Source packet SHA256: `975f24fca75b0deb8d930252294ddf729eff850d715f87dc8bcac0706c4aacb5`
- Protocol SHA256: `fa5a7908b8d131b3db2a32b0330ab1713beda10008aa6760e50843804837d5b4`
- Cohort: 120 unique cases, 947 retrieved candidates.
- The packet has `decisions_omitted=true`, `judge_outputs_omitted=true`, and `gate_outputs_omitted=true`.
- Input construction retains case ID, observed command, available context, behavioral claim, and each frozen candidate's ID, source, title, content, source version, and provenance hash. It drops empty review slots, source group IDs, input/context hashes, and every other field.
- The annotation calls receive no matched-arm results, deterministic Judge labels, Gate outcomes, policy decisions, prior model outputs, or analysis summaries.
- The coordinator had read aggregate descriptive summaries before freezing this fallback protocol. This is disclosed; the three remote annotation calls are separate model sessions supplied only the blind packet fields listed above.

## Fixed AI identities and transport

Each model reviews every case exactly once, in the same four deterministic batches of 30 cases:

| Rater | Frozen OpenRouter model ID | Model family |
|---|---|---|
| AI-R1 | `nvidia/nemotron-3-ultra-550b-a55b:free` | NVIDIA Nemotron |
| AI-R2 | `thinkingmachines/inkling:free` | Thinking Machines Inkling |
| AI-R3 | `dots-studio/dots-3-note-preview:free` | Dots |

Transport is OpenRouter Chat Completions with the exact model ID, `temperature=0`, `max_tokens=32768`, and provider fallbacks disabled. The API key is read from `OPENROUTER_API_KEY`; it is never written to the run artifacts or logs. The model catalog reported zero input/output price for all three IDs at freeze time. Each model returned a zero-cost no-data preflight response before this protocol was frozen. Actual provider/model, generation ID, usage, cost, timestamps, response hashes, and errors are recorded per request. No provider/model substitution is allowed.

Four batches preserve packet order and contain cases 1–30, 31–60, 61–90, and 91–120. All three raters receive the same frozen prompt and the same corresponding batch JSON. The request schedule is 12 calls total. Calls are sequential per model and every request is stored before validation. At most two exact-request retries are allowed for a transport/provider failure; retries are separately recorded and do not replace the original failed attempt. Schema-invalid successful responses are preserved and the affected judgments become `UNKNOWN`; no repair prompt is allowed.

## Annotation instrument

The frozen prompt is `AI_ANNOTATION_PROMPT_V1.txt`. Candidate labels are `DIRECT_SUPPORT`, `PARTIAL`, `IRRELEVANT`, `CONTRADICTORY`, and `UNKNOWN`. Bundle labels are `SUFFICIENT`, `INSUFFICIENT`, `CONFLICTING`, and `UNKNOWN`. Every non-`UNKNOWN` candidate judgment must cite its exact frozen `doc_id`, exact frozen `source`, and at least one 1-based paragraph locator into that candidate's frozen content. Rationale is paraphrased, not quoted. Bundle judgments cite supporting and/or conflicting candidate IDs. Missing provenance, ambiguous behavior, invalid citations, or incomplete model output remain `UNKNOWN`.

## Aggregation and unresolved cases

Aggregation is field-wise majority vote across the three fixed model identities. A label is resolved only when at least two models return the same valid label. A 1-1-1 split, fewer than two valid reviews, or invalid/missing evidence citations produces `UNKNOWN`. Rationale and document citations are retained per rater; majority labels are not manually adjudicated. This is an AI-derived multi-family majority reference, not human adjudication or independent consensus.

Report exact per-rater completion, schema/citation validity, candidate and bundle panel agreement, and `UNKNOWN` coverage. Report Fleiss' kappa as descriptive model-panel agreement with no human-reliability interpretation. Do not discard uncertain cases silently.

## Locked post-freeze analysis

Only after the aggregate reference and source/output manifest are frozen may the locked analysis read `matched_arm_results.json` or the downstream paired-audit artifacts. It will compare deterministic candidate labels to the reference, specifically unsupported `SUPPORTED` admissions and false rejection of `DIRECT_SUPPORT`; compare bundle sufficiency labels; and describe paired Arm A/Arm B gate and retained-candidate changes. Reference `UNKNOWN` rows are excluded from point estimates but counted and reported. Candidate-level uncertainty is clustered by case/source group; no candidate is treated as an independent sample. Report cluster bootstrap intervals only where the frozen IDs support the grouping. Keep execution coverage, reference-evaluable coverage, and candidate counts separate.

The paper must identify this as AI-derived, multi-family but potentially correlated panel review of a retrospective cohort. No deployment, safety, field effectiveness, human-reference accuracy, or independent consensus claim follows from this analysis.
