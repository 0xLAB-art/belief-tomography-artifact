# RAGIN V4 Evidence-Grounded Decision Architecture

## Scope

This document designs, but does not implement, the replacement for the retired Laya decision role. The replacement subsystem is named `EVIDENCE_GROUNDED_DECISION_FUSION`. The Laya 0.4.2 checkpoint remains historical negative-ablation evidence only and is not a V4 policy candidate.

No V2/V3 artifact was modified. No exploratory 120 case, primary 169 case, prior label, prediction, baseline/treatment output, or effectiveness result was used. No serving path or V4 prediction was created.

## Current executable boundary

The current path is materially more structured than the former Laya seam, but its export boundary is incomplete:

`ChrolloAdapter.classify()` exports skill level, confidence, selected features, and feature values. `DonAdapter.analyze()` constructs an `AnalysisRequest`, calls `ThreatRAGEngine.analyze()`, and exports classification, severity, confidence, tactics, IOCs, observed TTPs, and derived evidence fields. It does not export the native `ThreatAnalysis.intel_documents` list or raw retrieval metadata.

`ThreatRAGEngine.hybrid_search()` produces backend-dependent hits with document identifiers, title/content, source, raw score, and, on the native hybrid path, an RRF `hybrid_score`. The numeric scales are not comparable across dense, BM25, LightRAG, and fallback paths. The corrective graph merges hits by document ID, records `graph_score`, `sub_query_hits`, grades, coverage, relevant documents, and a bounded trace, then returns a `GraphResult`. `DonAdapter` does not currently expose that result.

The corrective graph's `sufficient` decision is an internal Don retrieval decision. It is useful provenance, but it is not a newly validated V4 evidence gate. V4 must expose the graph's bounded facts and apply a separate deterministic gate at the policy boundary.

Don's `IntelDocument` validator applies `_sanitize_for_llm()` to content, but no explicit sanitization status is emitted. Source strings are present, but no source registry or authenticity status is enforced. Retrieval exceptions in the graph can become empty hits, while the adapter's generic `error` field conflates retrieval and other analysis failures.

The current serving graph is `classify -> analyze -> plan -> approval -> generate -> verify -> finalize`. `HisokaAdapter` calls `AdaptiveDeceiver`, which is the effective response-generation boundary. `FictionConsistencyVerifier` is deterministic and fail-closed for response acceptance. `finalize_node` stages fiction updates and only replaces the live graph after a passed verification and conflict-free staged observation. HITL is authoritative through `ApprovalGateway`, but the current executable placement is pre-generation approval; the exact V4 ordering requested below requires a future graph seam after the Hisoka draft if approval is to inspect the proposed response.

## V4 architecture

The smallest clean V4 architecture is:

`Session -> Chrollo behavioral context -> Don corrective retrieval -> Evidence Quality Gate -> EVIDENCE_GROUNDED_DECISION_FUSION -> Hisoka -> HITL -> deterministic verifier -> accepted-only commit -> serve`

The decision subsystem is a bounded policy component. It does not retrieve, grade, classify evidence sufficiency, serve bytes, commit fiction state, alter verifier outcomes, decide HITL approval, or become CTI truth. Don remains the source of retrieval and CTI evidence; the deterministic gate is the authority over whether that evidence may reach policy selection.

## EVIDENCE GATE

The gate output is one of:

`VALID_EVIDENCE`, `NO_EVIDENCE`, `LOW_RELEVANCE`, `INVALID_PROVENANCE`, `UNRESOLVED_CONFLICT`, or `RETRIEVAL_FAILURE`.

Only `VALID_EVIDENCE` reaches a policy engine. Every other state deterministically selects `baseline`. A policy engine cannot override the gate.

The gate uses document identity, explicit retrieval status, Don-declared relevant document IDs, bounded query-coverage metadata, provenance status, sanitization status, duplicate checks, and conflict status. Scores are retained for traceability and ranking diagnostics; a learned score threshold is not introduced.

The minimal new Don export is a bounded evidence bundle containing:

- existing Chrollo and Don structured fields;
- retrieved documents and relevant document IDs already computed internally;
- backend, query/sub-query summary, counts, rounds, degraded state, and bounded trace;
- deterministic `retrieval_status`, `provenance_status`, `sanitization_status`, and `conflict_status` fields.

The four status fields are export/contract requirements, not new generative models. Provenance validity must come from a deterministic source/corpus registry or equivalent immutable manifest. A non-empty source string alone is not provenance proof.

## POLICY TASK

After the gate, the policy selector receives only the vetted evidence bundle: current input, Chrollo structured context, Don structured analysis, and sanitized documents selected by the gate. It chooses exactly one label from the seven bounded strategy labels:

`baseline`, `maximize_recon_surface`, `fake_success_and_return_visits`, `steer_to_honeytoken_credentials`, `expose_decoy_internal_topology`, `contain_in_fiction_and_instrument`, or `low_intensity_administration`.

It does not decide whether evidence is sufficient, whether retrieval should run, whether verification passes, whether HITL approves, or whether state commits. A malformed, timed-out, exception, or out-of-vocabulary result becomes `baseline` at the caller boundary.

The proposed policy output is:

```json
{
  "schema": "ragin.decision_fusion_v4.policy_decision.v1",
  "policy_engine_id": "...",
  "selected_response_strategy": "one allow-listed label",
  "supporting_evidence_refs": ["only supplied vetted doc_id values"],
  "policy_reason_code": "bounded enum",
  "input_digest": "sha256"
}
```

Hisoka may consume the bounded strategy as planning context, but the policy output does not directly generate or serve a response. HITL, deterministic verification, accepted-only commit, and serving remain outside policy authority.

## CANDIDATES

### Deterministic policy

This is mandatory and remains the primary baseline. It uses explicit precedence rules over Chrollo skill/confidence/features, Don classification/severity/tactics/TTPs, and vetted document metadata. It has no model dependency, predictable latency, and strong reproducibility. Its risks are rule incompleteness and manual maintenance, not hidden confidence behavior.

### Lightweight learned policy

The candidate family is a small structured classifier over the same frozen feature map: multinomial logistic regression, gradient-boosted trees, or a shallow MLP. `scikit-learn` is already a project dependency, so logistic regression and tree candidates are locally compatible in principle. The exact algorithm, preprocessing, seed, and hyperparameters must be frozen before validation; selection cannot be made by unrestricted final-validation probing. A learned policy may advance only if it passes every contract gate and is not materially worse than the deterministic baseline.

### Local instruction policy

The candidate is a local instruction-following model consuming only the vetted bundle and returning one finite strategy label. The repository already contains local-model configuration seams, including an OpenAI-compatible local endpoint and Ollama-compatible benchmark plumbing, but the exact model, quantization, context limit, and hardware availability are not verified by this design study. Those facts must be inventoried and frozen before validation. No specific local model is assumed or selected here.

## DON -> GATE CONTRACT

The full contract is recorded in [evidence_gate_contract_v1.json](../../results/decision_fusion_v4/evidence_gate_contract_v1.json). Its central rule is:

`VALID_EVIDENCE -> policy selector`; every other gate state -> `baseline`.

The contract deliberately separates raw score fields from provenance and quality statuses. It forbids free-form retrieval prose outside the bounded document objects and requires unique document IDs, sanitized content, valid provenance, and an explicit conflict state.

## SAFETY AUTHORITY

Authority is ordered as follows:

1. Don retrieval and the deterministic Evidence Quality Gate decide whether evidence can reach policy.
2. The bounded policy selector chooses only a strategy label.
3. Hisoka drafts the response.
4. HITL can block or deny according to the existing approval authority.
5. The deterministic verifier can reject, retry, or force the fail-safe template; policy cannot alter its result.
6. Accepted-only commit stages and commits fiction state only after verification passes and staged observation has no contradiction.
7. Only the existing serve boundary returns the accepted response.

This preserves verifier independence, prevents policy from becoming CTI truth, and prevents an invalid retrieval result from being rescued by a model's confidence.

## RECOMMENDED BENCHMARK

Use new synthetic corpora with no overlap with the Laya V3 adaptation cases. A recommended design is 72 development cases and 96 validation cases, each stratified across valid recon, credential access, persistence, exploitation, data access, benign administration, multiple supporting documents, high-score irrelevant documents, low-score relevant documents, weak/missing evidence, retrieval failure, invalid provenance, duplicates, unresolved conflict, query-coverage failure, and sanitization failure.

Every case must freeze its contract oracle before inference: expected gate state, allowed strategies if valid, supporting document IDs, forbidden strategies where meaningful, and whether baseline is required. The previous Laya V3 validation set may be cited as historical failure evidence only; it is not a V4 selection corpus.

Report gate and policy metrics separately. Gate metrics are gate-state alignment, fail-safe recall, and invalid-evidence pass-through. Policy metrics are strategy compatibility on valid evidence, catastrophic incompatible strategy rate, schema/allow-list compliance, repeatability, and latency.

## ADVANCEMENT CRITERIA

Freeze before untouched validation:

- gate fail-safe recall >= 95%;
- invalid/insufficient evidence pass-through <= 5%;
- policy strategy compatibility >= 80% on `VALID_EVIDENCE` cases;
- catastrophic incompatible strategy rate <= 5%;
- schema/allow-list compliance = 100%;
- any learned or instruction candidate not materially worse than deterministic baseline.

For this study, materially worse is preregistered as more than 5 percentage points lower strategy compatibility or more than 2 percentage points higher catastrophic rate on the same valid-evidence cases. A candidate that does not pass is classified `PROMISING_BUT_NOT_VALIDATED` or `REJECT_FOR_POLICY_ROLE`; it is not promoted by subjective interpretation.

## LAYA STATUS

current checkpoint: `RETIRED_FROM_DECISION_ROLE`

historical evidence preserved: `YES`

The Laya checkpoint is not included in the V4 candidate pool.

## NEXT STEP

full prototype now: `NO`

synthetic candidate benchmark first: `YES`

old 169 reusable: `NO`

The next authorized step is to construct and freeze the new V4 synthetic development corpus, inventory local instruction-model availability without selecting on validation, implement only the benchmark harness/contracts, and then freeze candidate configurations before the untouched synthetic validation phase. No real effectiveness claim is possible until a new untouched real holdout is registered.

RAGIN V4 DECISION-ENGINE REPLACEMENT STUDY DESIGNED.
THE FAILED LAYA CHECKPOINT IS RETIRED FROM THE DECISION ROLE.
THE POST-RETRIEVAL ARCHITECTURE IS PRESERVED, BUT THE DECISION SUBSYSTEM IS NOW MODEL-AGNOSTIC.
A NEW UNTOUCHED HOLDOUT WILL BE REQUIRED BEFORE ANY REAL EFFECTIVENESS CLAIM.
