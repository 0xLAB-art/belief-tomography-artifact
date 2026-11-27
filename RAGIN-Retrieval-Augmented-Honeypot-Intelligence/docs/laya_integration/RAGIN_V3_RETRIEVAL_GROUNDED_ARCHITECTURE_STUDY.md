# RAGIN V3 Retrieval-Grounded Laya Decision Layer

Status: design-only architecture study. No code, V2/V2a/V2b artifact, prediction, or holdout was modified or created by this study.

## Scope and motivation

The prior independent Laya placement is motivation for a redesign, not evidence that a retrieval-grounded design will work. The authoritative prior finding is: V2b attack/non-attack balanced accuracy `0.493382`, workflow primary delta `0`, strategy reached generator `169/169`, candidate changed `162/169`, and mean added end-to-end latency approximately `1.98 s`. The 169-case primary holdout is explicitly excluded from this study and remains untouched.

The target architecture is:

```text
input/session
  -> Chrollo behavioral context
  -> Don retrieval and analysis
  -> immutable evidence bundle
  -> Laya bounded evidence-grounded policy selection
  -> existing plan/HITL gate
  -> Hisoka/ResponseGenerator
  -> mandatory deterministic verifier
  -> accepted-only state commit
  -> serve
```

Laya is advisory policy selection only. It is not a CTI source, verifier, serving component, or state owner.

## Current executable interfaces

### ChrolloAdapter

`ChrolloAdapter.classify(attacker_input, session_context) -> dict` converts the current inputs into a `SessionLog`, calls the native classifier, and returns `skill_level`, `confidence`, `session_id`, `features_used`, `feature_values`, and `error` (`ragin/cycle/adapters.py:141-237`). The adapter also currently initializes and invokes Laya during classification when enabled (`ragin/cycle/adapters.py:154-173,214-227`). That is the V2 pre-Don/independent placement and must not be the V3 decision seam.

Chrollo's useful V3 contribution is behavioral context: the bounded feature values, skill level, confidence, observed command/session history, and any explicit classifier error. Chrollo does not provide CTI truth.

### DonAdapter and Don retrieval engine

`DonAdapter.analyze(attacker_input, session_context) -> dict` maps Chrollo's skill level to a Don `ClassificationLabel`, constructs an `AnalysisRequest`, builds a session log, extracts deterministic command evidence, and invokes `ThreatRAGEngine.analyze` (`ragin/cycle/adapters.py:302-355`). Its current returned dictionary contains analysis ID, severity, classification, confidence, sophistication, recommendations, tactics, candidate actors, local evidence categories, IOCs, observed TTPs, actor repertoire metadata, and error (`ragin/cycle/adapters.py:357-418`).

`ThreatRAGEngine.analyze` builds a query, performs hybrid vector/BM25 retrieval, stores a private context string, maps tactics/IOCs/actors, derives severity, and returns a `ThreatAnalysis` (`ragin/don/rag_engine.py:202-249`). The retrieval seam is `hybrid_search`, which fuses dense and keyword results and returns hit dictionaries with the source hit fields plus `hybrid_score` (`ragin/don/rag_engine.py:367-430`). The corrective graph additionally has `relevant_docs`, grades, sub-query coverage, and a trace, but those are not exposed by the current `DonAdapter` contract (`ragin/don/graph.py:120-220`).

The current adapter therefore performs Don retrieval but does not export a retrieval evidence bundle to a downstream decision component. This is the principal V3 interface change.

### Don result and provenance fields

The native `IntelDocument` schema can represent `doc_id`, `title`, `content`, `source`, `published_date`, `tags`, `mitre_tactics`, `threat_actors`, and `score` (`ragin/don/models.py:112-131`). `ThreatAnalysis` can carry `intel_documents` (`ragin/don/models.py:133-151`). However, `_hit_to_intel_doc` currently populates only ID, title, truncated content, source, and score (`ragin/don/rag_engine.py:548-558`), and `DonAdapter` currently omits `intel_documents` entirely (`ragin/cycle/adapters.py:357-397`).

Consequences for the proposed contract:

* Document ID, title, content excerpt, source, and a score are available in the Don retrieval path, but are not currently exported through `DonAdapter` as a stable downstream contract.
* ATT&CK tactic IDs/techniques are available in `MITRETactic` and in the analysis result, but the adapter's tactic projection currently exports only tactic ID, name, and confidence. Document-level ATT&CK metadata is not currently exported.
* CVE identifiers are not represented in `IntelDocument`, `ThreatAnalysis`, or the adapter projection observed here. `cve_ids` is therefore a `NEW_REQUIRED_FIELD`, not an assumed field.
* Retrieval rank, exact retrieval query, retrieval mode, corpus revision, per-document relevance grade, document hash, and retrieval timestamp are not current adapter contract fields. They are `NEW_REQUIRED_FIELD`s for reproducible V3 provenance.

### LayaRuntime.infer

`LayaRuntime.infer(state: str) -> dict` calls `laya.Router.predict` with one state value under the `session` key and three typed questions: attack, stage, and severity (`ragin/decision/laya_runtime.py:264-330`). The runtime is local, revision-pinned, bounded to one model, and reports model/checkpoint provenance through `manifest()` (`ragin/decision/laya_runtime.py:141-264`). The current state input is a bounded serialized session string; there is no native evidence-bundle parameter or retrieval citation channel.

### LayaDecisionPolicy

`LayaDecisionPolicy.evaluate` maps an independent normalized attack signal to `baseline`, `low_intensity_administration`, or a stage-derived attack strategy (`ragin/decision/laya_decision.py:137-163`). `LayaDecisionAdapter` adds timeout, malformed-output, model provenance, input hashing, and fail-safe `BASELINE_NO_SIGNAL` behavior (`ragin/decision/laya_decision.py:165-260`). It has no access to fiction state, authorization, HITL, serving, or commit APIs.

For V3, this policy must be replaced or versioned as a new evidence-grounded policy contract. Reusing its attack probability as a gate would repeat the V2 seam and is prohibited.

### HisokaAdapter and effective ResponseGenerator

`HisokaAdapter.generate_response(attacker_input, session_context) -> dict` delegates to `AdaptiveDeceiver`, preserves response metadata and fallback provenance, and returns response text, persona, artifacts, engagement, honeytoken, metadata, and error (`ragin/cycle/adapters.py:421-486`). The effective generator path is `HisokaAdapter -> AdaptiveDeceiver -> ResponseGenerator` as documented in the adapter (`ragin/cycle/adapters.py:489-507`).

The existing graph places strategy context into the plan and then into Hisoka's generation context (`ragin/cycle/graph.py:260-319`). V3 should add one bounded `laya_policy` object to that context. Hisoka may use it as guidance, but it remains responsible for generating the draft and must not treat Laya as a verifier or truth source.

### Deterministic verifier boundary

The graph calls the configured verifier after every generated response (`ragin/cycle/graph.py:321-354`). `FictionConsistencyVerifier.verify` returns `passed`, `issues`, `confidence`, verifier identity, and `deterministic: true` (`ragin/cycle/verifier.py:202-246`). Failed drafts retry; after retry exhaustion the graph attempts an identity-bound deterministic fallback and serves nothing if that fallback cannot pass (`ragin/cycle/graph.py:354-404`). V3 must leave this authority unchanged. Laya cannot alter verifier outcomes or bypass this node.

### HITL

The approval gateway computes risk from classification, extracted techniques, and planned artifacts. It supports AUTO, NOTIFY, and REQUIRE, records the request/decision, and can block when approval is required without an approver (`ragin/cycle/hitl.py:38-81,192-325`). V3 policy output may contribute bounded strategy context and evidence references to the approval request, but cannot approve itself or bypass the existing gate.

### Accepted-only state commit

`finalize_node` stages observations and promotes them only after final verification passes; contradictions invalidate the staged update, and failed turns promote nothing (`ragin/cycle/graph.py:406-425`). The graph order is classify -> analyze -> plan -> approval -> generate -> verify -> retry/finalize (`ragin/cycle/graph.py:460-480`). V3 must preserve this order and must not let Laya directly commit, serve, or mutate fiction state.

## Candidate V3 seams

| Seam | Scientific clarity | Complexity/latency | Provenance and verifier independence | A/B testability | V2 failure risk |
|---|---|---|---|---|---|
| A. POST_RETRIEVAL_POLICY_FUSION | Highest: Don retrieves first; Laya's estimand is incremental policy value conditional on the same evidence | Moderate; one bounded Laya call after existing Don work; adds Laya latency but no extra retrieval loop | Strong: evidence is frozen before Laya; verifier remains downstream and independent | Highest: baseline and treatment can share Chrollo, Don bundle, Hisoka, verifier, HITL, and holdout | Lowest, provided treatment is compared against baseline policy and abstain is fail-safe |
| B. RETRIEVAL_RERANKING_PLUS_POLICY | Mixed: retrieval quality and policy quality are confounded unless separately instrumented | High: reranking changes Don's evidence and can require additional model work | Weaker: Laya can distort CTI evidence ordering; provenance must record both original and reranked lists | Moderate to low: hard to attribute gains/losses to retrieval vs policy | Medium/high: repeats a decision model influencing upstream evidence and can recreate no-benefit behavior |
| C. PRE_RETRIEVAL_QUERY_ROUTING | Lowest for the intended claim: Laya affects what Don knows before policy selection | High and potentially variable; adds a model call before retrieval and query branching | Weakest: query routing can suppress or redirect evidence and create selection bias | Low: retrieval changes make matched A/B attribution difficult | Highest: independent attack uncertainty can suppress useful CTI and reproduce the V2 placement failure |

### Recommendation

Choose A, POST_RETRIEVAL_POLICY_FUSION. The treatment is a conditional policy component: it sees the same behavioral context and a Don-produced evidence bundle, then proposes one member of a finite strategy vocabulary or abstains. Don remains the CTI authority; the baseline policy remains the deterministic fallback; Hisoka, HITL, verification, commit, and serving stay outside Laya.

The V3 causal comparison should be baseline policy versus the same pipeline with only this post-retrieval Laya policy enabled. It must not compare different retrieval corpora, thresholds, verifier rules, or holdout membership in the same contrast.

## Proposed evidence bundle: Don -> Laya

The bundle is immutable after Don emits it and is the only input boundary for V3 Laya policy selection. The exact JSON contract is also recorded in `results/laya_decision_v3/v3_architecture_design.json`.

```json
{
  "schema": "ragin.laya_v3.evidence_bundle.v1",
  "session": {
    "session_id": "<current session id>",
    "turn_id": "<NEW_REQUIRED_FIELD>",
    "attacker_input": "<current input>",
    "attacker_inputs": ["<bounded prior inputs>"],
    "system_responses": ["<bounded prior responses>"]
  },
  "behavior": {
    "skill_level": "<Chrollo output>",
    "classification_confidence": 0.0,
    "features_used": [],
    "feature_values": {},
    "observed_techniques": [],
    "evasion_techniques": {},
    "tools_used": {},
    "credential_access": {}
  },
  "don_analysis": {
    "analysis_id": "<Don analysis_id>",
    "classification": "<Don classification>",
    "severity": "<Don severity>",
    "confidence": 0.0,
    "sophistication_score": 0.0,
    "tactics": [],
    "observed_ttps": [],
    "iocs": [],
    "candidate_actors": [],
    "recommendations": [],
    "error": ""
  },
  "retrieval": {
    "query": "<NEW_REQUIRED_FIELD>",
    "mode": "<NEW_REQUIRED_FIELD>",
    "documents": [
      {
        "doc_id": "<Don hit doc_id>",
        "rank": "<NEW_REQUIRED_FIELD>",
        "title": "<Don hit title>",
        "content_excerpt": "<bounded Don content/text>",
        "source": "<Don source if present>",
        "published_date": "<Don published_date if present>",
        "retrieval_score": "<Don score/hybrid_score; stable name NEW_REQUIRED_FIELD>",
        "relevance_grade": "<NEW_REQUIRED_FIELD>",
        "attack_mapping": "<NEW_REQUIRED_FIELD: document-level ATT&CK mapping>",
        "cve_ids": "<NEW_REQUIRED_FIELD>",
        "document_sha256": "<NEW_REQUIRED_FIELD>"
      }
    ],
    "trace": "<NEW_REQUIRED_FIELD>",
    "corpus_revision": "<NEW_REQUIRED_FIELD>",
    "retrieved_at": "<NEW_REQUIRED_FIELD>"
  },
  "bundle_sha256": "<NEW_REQUIRED_FIELD>"
}
```

`attack_mapping` above is intentionally marked `NEW_REQUIRED_FIELD`; the implementation name should be finalized only after a concrete code contract is chosen. The study does not claim that current Don can provide a CVE mapping, rank, grade, corpus revision, or cryptographic document identity. A V3 implementation must fail closed to baseline when required provenance is absent rather than fabricate it.

The evidence bundle is evidence, not an instruction prompt. Retrieved text must retain Don's existing sanitization boundary before it reaches any model. Laya may cite document IDs from the bundle, but it cannot create new CTI facts, promote candidate actors to truth, or treat an actor repertoire as observed behavior.

## Proposed bounded policy output: Laya -> Hisoka

The output is a proposal consumed by the graph's plan/generation context. It is not a response, approval, verification result, state mutation, or serve command.

```json
{
  "schema": "ragin.laya_v3.policy_decision.v1",
  "session_id": "<session id>",
  "status": "SELECT | ABSTAIN",
  "selected_response_strategy": "baseline | maximize_recon_surface | fake_success_and_return_visits | steer_to_honeytoken_credentials | expose_decoy_internal_topology | contain_in_fiction_and_instrument | low_intensity_administration",
  "evidence_refs": ["<doc_id>"],
  "decision_reason": "<bounded enum or short reason>",
  "decision_confidence": "<NEW_REQUIRED_FIELD>",
  "policy_version": "LAYA_DECISION_POLICY_V3",
  "policy_hash": "<implementation artifact hash>",
  "laya_provenance": {
    "model": "<current Laya model identity>",
    "revision": "<current Laya revision>",
    "model_hash": "<current Laya model hash>",
    "input_sha256": "<Laya input hash>",
    "evidence_bundle_sha256": "<NEW_REQUIRED_FIELD>",
    "latency_ms": 0.0
  },
  "abstain_reason": "<required when status=ABSTAIN>"
}
```

The strategy vocabulary is finite and must be allow-listed by the receiving plan/generation boundary. Unknown values, missing evidence references for a selected non-baseline strategy, malformed output, timeout, model identity failure, or policy-contract failure become `ABSTAIN`, not a best-effort free-form strategy.

Hisoka receives this object as `session_context["laya_policy"]` or an equivalent explicitly versioned plan field. It may use `selected_response_strategy` as bounded guidance. It must continue to generate through the existing `AdaptiveDeceiver`/`ResponseGenerator` path and return its ordinary response object and metadata.

## Native Laya model/task suitability

The current native model/task is not semantically appropriate for V3 evidence-conditioned policy selection without a task change. The runtime is configured for three generic typed questions over a session string: maliciousness, attack stage, and severity (`ragin/decision/laya_runtime.py:264-330`). The current adapter normalizes those answers into an independent attack signal and uses attack probability/stage to select strategy (`ragin/decision/laya_decision.py:88-163`).

Appending retrieved evidence to the serialized `state` could technically make the current runtime read evidence, but that would be an unvalidated prompt/input change and would not establish an evidence-grounded policy task. A defensible V3 implementation needs a new explicitly specified task contract, question set and calibration/evaluation plan, and likely a model or prompt/task adaptation. If the current Laya checkpoint cannot reliably answer policy questions conditioned on cited Don evidence, it must remain an abstaining component; silently calling the old classifier a policy model is not acceptable.

## V3 safety and control invariants

1. Don runs before Laya for every treatment decision. Laya cannot bypass, suppress, reroute, or selectively omit Don retrieval.
2. Don owns CTI truth. Laya can select among bounded response strategies only and must cite the evidence IDs it used.
3. Laya cannot directly serve. Only Hisoka/ResponseGenerator produces a draft.
4. Laya cannot directly commit state. Only the existing accepted-only finalize path can promote fiction state.
5. Laya cannot alter verifier outcomes. Verification is mandatory and deterministic at the existing boundary.
6. HITL remains authoritative for required approvals. Laya cannot auto-approve.
7. Missing or insufficient evidence maps deterministically to the baseline policy.
8. All Laya outputs, including abstentions, carry model/policy/input/evidence provenance and are observable for A/B analysis.

## Implementation changes required

Design-only list; none of these changes were made in this study.

1. Add a Don post-retrieval export that returns a stable evidence bundle, including retrieval query, rank, score name, corpus/retrieval provenance, and bounded document excerpts.
2. Preserve/export document-level ATT&CK mappings where available; add `cve_ids` only if Don's corpus and loader can source them, otherwise omit the field and make the policy aware that CVE evidence is unavailable. Do not synthesize CVEs.
3. Add a stable document identity/hash and bundle hash. Define whether the production source is `ThreatRAGEngine.analyze` or `analyze_graph`; do not mix their provenance silently.
4. Move the Laya call from the Chrollo classification seam to a post-Don policy node. Chrollo output remains behavioral context only.
5. Implement `LayaDecisionPolicyV3` as an allow-listed evidence-conditioned selector with explicit `SELECT` and `ABSTAIN` states. Keep V2 policy and artifacts unchanged.
6. Thread the bounded policy object through `plan_node` and `generate_node` into Hisoka; reject unknown strategies at the boundary.
7. Keep the existing approval, generation, retry, deterministic verification, fallback, accepted-only commit, and serve-path provenance logic authoritative.
8. Add contract tests for missing evidence, bad provenance, unsupported strategy, timeout, malformed model output, verifier rejection, HITL REQUIRE, and no-commit-on-failure. These are future implementation tests, not run here.

## RECOMMENDED V3 ARCHITECTURE

POST_RETRIEVAL_POLICY_FUSION: Chrollo supplies behavioral context; Don retrieves and remains the CTI authority; an immutable, provenance-carrying Don evidence bundle is passed to a new bounded Laya V3 policy task; Laya selects an allow-listed strategy or abstains; the baseline RAGIN policy is used on abstention; Hisoka generates; HITL and mandatory deterministic verification remain outside Laya; only verified output reaches accepted-only commit and serve.

## DON -> LAYA CONTRACT

`ragin.laya_v3.evidence_bundle.v1` as defined above. Current Don-supported values must be exported without reinterpretation. Retrieval rank, query/mode, relevance grade, document-level ATT&CK mapping, CVE IDs, document/bundle hashes, corpus revision, retrieval timestamp, and turn ID are `NEW_REQUIRED_FIELD`s unless a future implementation supplies them. Missing required provenance forces `ABSTAIN` and baseline fallback.

## LAYA -> HISOKA CONTRACT

`ragin.laya_v3.policy_decision.v1` as defined above. The only actionable field is an allow-listed `selected_response_strategy`; `status=ABSTAIN` selects `baseline`. Evidence references and provenance are audit fields and cannot authorize serving, HITL approval, verification, or state commit.

## ABSTAIN PATH

Any timeout, malformed output, unavailable/identity-unverified model, missing or insufficient Don evidence, unsupported strategy, missing evidence reference, or provenance mismatch produces `status=ABSTAIN`, `selected_response_strategy=baseline`, and an explicit `abstain_reason`. The graph continues through the baseline RAGIN policy, Hisoka, HITL, deterministic verification, accepted-only commit, and serve rules. Laya never suppresses Don retrieval because of an attack probability.

## SAFETY AUTHORITY

Don owns CTI evidence and retrieval provenance. The bounded V3 policy owns only conditional strategy selection. HITL owns required human approval. The deterministic verifier owns response acceptance. The existing finalize path owns accepted-only fiction/state commit. Hisoka owns response generation. No Laya output can override any of these authorities.

## IMPLEMENTATION CHANGES REQUIRED

The required changes are limited to the new Don evidence export, the post-retrieval Laya policy node and V3 contract, the plan-to-Hisoka context thread, provenance/fail-closed validation, and focused contract/A-B instrumentation. V2/V2a/V2b code and artifacts must remain unchanged; the V3 implementation should be a separate versioned path.

## NEW EVALUATION REQUIRED

YES

old 169 reusable:
NO

new untouched holdout required:
YES

The new evaluation must freeze a V3 protocol, evidence-bundle schema, policy vocabulary, model identity, abstain rule, verifier/HITL configuration, and analysis plan before testing. It must report conditional policy success, abstain/insufficient-evidence rate, Don retrieval coverage, strategy reach, verifier pass/fallback/retry rates, HITL rates, accepted-only commit rate, end-to-end latency, and primary workflow outcomes separately. Any future A/B must preserve the untouched holdout requirement and must not reuse the 169-case primary holdout.
