# AI-Derived Evidence-Support Reference Protocol V2

Status: frozen before V2 case-level annotation.

## Objective and limits

Create an AI-derived evidence-support reference for the existing retrospective 120-case Evidence Judge ablation. It is not human ground truth, a gold standard, or independent consensus. Different model families can still have correlated errors. Report primary-model agreement as AI-panel agreement only. Results are descriptive for the frozen retrospective cohort and cannot establish fresh confirmatory performance, deployment benefit, or field effectiveness.

Human delivery returns are empty. V1's 30-case NVIDIA Ultra requests yielded provider-overload envelopes and one unreturned request after ten minutes; no V1 annotations were accepted. V2 uses two fixed AI primary reviewers and a third fixed AI model for disagreements only, preserving all failed V1 attempts in `ai_reference_v1/`.

## Frozen source and blindness boundary

- Blinded packet: `results/evidence_judge_real_data_ablation_v1/blinded_reference_packet.json`
- Packet SHA256: `975f24fca75b0deb8d930252294ddf729eff850d715f87dc8bcac0706c4aacb5`
- Source protocol SHA256: `fa5a7908b8d131b3db2a32b0330ab1713beda10008aa6760e50843804837d5b4`
- Cases/candidates: 120 unique cases and 947 retrieved candidates.
- Calls include only case ID, observed command, available context, behavioral claim, and frozen candidate ID/source/title/content/version/provenance hash.
- Calls exclude source-group IDs, input/context hashes, blank review slots, Judge labels, Gate outcomes, arm results, policy outputs, and analysis summaries.
- The coordinator has seen aggregate descriptive summaries. No annotation model receives those summaries or any system output.

## Fixed identities and roles

| Role | ID | Frozen model ID | Family |
|---|---|---|---|
| Primary 1 | P1 | `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free` | NVIDIA Nemotron Nano |
| Primary 2 | P2 | `thinkingmachines/inkling:free` | Thinking Machines Inkling |
| Adjudicator | A1 | `dots-studio/dots-3-note-preview:free` | Dots |

The model catalog snapshot records zero prompt/completion prices, context limits, and successful no-data probes. Requests use exact model IDs, `temperature=0`, provider fallback disabled, and a fixed prompt. The actual model/provider, generation ID, use, cost, timestamps, response bytes, and errors are retained for every request. No substitution is allowed.

## Primary review schedule

All 120 cases are reviewed once by P1 and once by P2 in six consecutive packet-order batches of 20 cases each. The full candidate list and behavior context go to both models. Each candidate must receive one label from `DIRECT_SUPPORT`, `PARTIAL`, `IRRELEVANT`, `CONTRADICTORY`, or `UNKNOWN`; each case receives one bundle label from `SUFFICIENT`, `INSUFFICIENT`, `CONFLICTING`, or `UNKNOWN`.

Output uses candidate indexes to minimize generation length. Indexes are zero-based in the input candidate order. The deterministic ingestion step maps them back to the exact packet `doc_id` and `source`, validates indexes and 1-based paragraph locators against frozen content, and writes complete reviewer files with citations. Rationale is a short paraphrase, not a source quotation. Missing, invalid, or uncited non-`UNKNOWN` items become `UNKNOWN`.

## Disagreement adjudication

For every candidate or bundle field where P1 and P2 differ, including one-sided `UNKNOWN`, A1 receives the blind case evidence, the two primary rationales/citations for the disputed fields, and instructions to make a fresh evidence-based decision. A1 receives no Judge/Gate/arm/policy output. Cases with no disagreements are not sent to A1. A1 must select a valid taxonomy label with a valid passage locator for a non-`UNKNOWN` candidate, or return `UNKNOWN` if the evidence does not settle the disagreement. No hand repair or further model adjudication is allowed.

If A1's valid decision resolves a disagreement, retain its label and citation with all three original decisions. Otherwise the final label is `UNKNOWN`. Record each exact primary disagreement and the adjudicator disposition. This is AI adjudication, not human adjudication.

Each API request gets at most two exact retries for transport/provider errors; retries retain the identical frozen request body and are logged separately. A successful but malformed response is preserved and its affected items become `UNKNOWN`; no repair prompt or model substitution is allowed. Provider cost must be zero; stop immediately if the returned cost is nonzero.

## Aggregation, agreement, and coverage

Exact P1/P2 agreements are carried forward, including shared `UNKNOWN`. Disagreements use A1 under the rule above. Report exact primary agreement, candidate and bundle Fleiss kappa for the two primary AI reviewers, adjudication request/validity counts, all three model identities, schema/citation validity, per-label counts, and `UNKNOWN` coverage. Do not describe AI-panel agreement as human reliability.

## Locked analysis after reference freeze

Do not read `matched_arm_results.json` or downstream paired results until `reference_freeze_v2.json` and its hash manifest exist and validate. Then compare deterministic candidate labels with the AI-derived reference: unsupported `SUPPORTED` admissions, false rejection of `DIRECT_SUPPORT`, bundle sufficiency, and error categories. Separately describe paired Arm A/Arm B gate changes and retained-candidate changes. Exclude reference `UNKNOWN` from label accuracy denominators but report its count. Cluster candidate uncertainty by case/source group; never treat candidates as independent samples. Keep execution availability, reference-evaluable cases, and candidate counts separate.
