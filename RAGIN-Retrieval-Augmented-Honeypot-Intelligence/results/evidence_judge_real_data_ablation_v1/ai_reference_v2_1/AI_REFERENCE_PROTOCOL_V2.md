# AI-Derived Evidence-Support Reference Protocol V2.1

Status: frozen before the V2.1 annotation calls.

## Objective and claim boundary

Create an AI-derived evidence-support reference for the existing retrospective 120-case Evidence Judge ablation. It is not human ground truth, a gold standard, or independent consensus. The two distinct model families can still have correlated errors. Report their exact agreement as AI-panel agreement only. Results are descriptive for this frozen retrospective cohort and cannot establish fresh confirmatory performance, deployment benefit, or field effectiveness.

Human delivery returns are empty. The V1 NVIDIA Ultra requests produced provider-overload envelopes and one uncaptured request. V2's Nano/Inkling requests were a format/access pilot: provider errors, a response with non-JSON preamble, and an interrupted request. No V1/V2 review labels were accepted or used. Their raw attempts remain preserved in their own directories. V2.1 starts a clean annotation run with frozen JSON-capable primary identities.

## Frozen source and blindness

- Blinded source: `results/evidence_judge_real_data_ablation_v1/blinded_reference_packet.json`
- Packet SHA256: `975f24fca75b0deb8d930252294ddf729eff850d715f87dc8bcac0706c4aacb5`
- Source protocol SHA256: `fa5a7908b8d131b3db2a32b0330ab1713beda10008aa6760e50843804837d5b4`
- Cohort: 120 unique cases and 947 candidates.
- Each model receives only case ID, observed command, available context, behavioral claim, and frozen candidate ID/source/title/content/version/provenance hash.
- Calls exclude source-group IDs, input/context hashes, empty review slots, Judge labels, Gate outcomes, arm results, policy outputs, and analysis summaries.
- The coordinator has seen aggregate descriptive summaries. The annotation calls receive none of those summaries or any system outputs.

## Fixed primary identities

| Rater | Model ID | Family | Structured JSON |
|---|---|---|---|
| P1 | `nvidia/nemotron-3-super-120b-a12b:free` | NVIDIA Nemotron Super | OpenRouter `json_object` mode |
| P2 | `dots-studio/dots-3-note-preview:free` | Dots | OpenRouter `json_object` mode |

The model catalog snapshot records both IDs, zero prompt/completion price, context limits, supported parameters, and successful no-data JSON probes. Requests use exact IDs, `temperature=0`, `max_tokens=12000`, `response_format={"type":"json_object"}`, and provider fallback disabled. The exact model/provider, generation ID, token usage/cost, timestamp, response hash, and errors are retained. No substitutions are allowed.

## Annotation schedule and instrument

Each primary reviews all 120 cases once in six consecutive packet-order batches of 20. Both receive identical frozen batch content and prompts. Candidate labels are `DIRECT_SUPPORT`, `PARTIAL`, `IRRELEVANT`, `CONTRADICTORY`, and `UNKNOWN`; bundle labels are `SUFFICIENT`, `INSUFFICIENT`, `CONFLICTING`, and `UNKNOWN`.

Responses identify candidates by zero-based packet order index. Deterministic ingestion maps each index back to the exact source `doc_id` and `source`, validates the 1-based paragraph locator against frozen candidate content, and emits complete per-rater files with source/document citations. A non-`UNKNOWN` candidate requires a valid locator and a short paraphrased rationale. Missing, invalid, or uncited decisions become `UNKNOWN`. Responses must parse as one JSON object under the frozen structured-output API mode; no free-form prefix extraction or repair prompt is permitted.

Each API request allows at most two exact retries for transport/provider failure. A successful malformed/partial response is preserved; affected records become `UNKNOWN`. Stop immediately if any call reports nonzero cost or a different model identity.

## Agreement, disagreement, and adjudication rule

Exact P1/P2 label agreement is retained, including shared `UNKNOWN`. Every differing candidate or bundle label is recorded with both rationales and citations and resolved as `UNKNOWN`. The AI-only fallback does not use an adjudicator, human adjudication, or model-generated tie breaking. This conservative rule prevents an unresolved panel disagreement from being turned into a confident reference label.

Report P1/P2 exact agreement and Cohen/Fleiss kappa separately for candidate and bundle labels; report all disagreement records, schema/citation validity, per-rater labels, reference-evaluable coverage, and every `UNKNOWN`. Agreement is not human reliability or ground truth.

## Locked analysis after reference freeze

Do not read `matched_arm_results.json` or downstream paired outcomes until `reference_freeze_v2_1.json` and its hash manifest exist and validate. Then compare deterministic candidate labels to the AI-derived reference: unsupported `SUPPORTED` admissions, false rejection of `DIRECT_SUPPORT`, bundle sufficiency, and an error taxonomy. Separately describe paired Arm A/Arm B gate outcomes and retained-candidate changes. Exclude reference `UNKNOWN` from label metrics but report its counts. Cluster candidate uncertainty by case/source group, never treat candidates as independent. Separate execution availability, reference-evaluable cases, and candidate denominators.
