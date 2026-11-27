# Laya V3 Policy Capability Probe

Status: capability and contract probe only. This is not a V3 implementation, accuracy evaluation, or effectiveness study.

## Scope and isolation

The probe used only the installed pinned `laya 0.4.2` package and the verified English checkpoint `english@55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851` with checkpoint SHA-256 `891102d372688fc2a094dac56a384bc537b87c63f21f9f3dac0be2b7cbc8d86c`. It used eight newly constructed synthetic evidence cases, three repeated calls per case, and no case IDs, labels, predictions, or artifacts from the exploratory 120 or primary 169.

The probe called `laya.Router.predict` directly for custom questions. RAGIN's current `LayaRuntime.infer` remains a different boundary: it constructs the fixed attack/stage/severity questions and calls `Router.predict` with those questions. Therefore, a successful custom-question API call must not be described as proof that the current RAGIN Laya task is already a policy model.

## API inspection

The installed API signature is:

```text
Router.predict(
    state: str | dict | list,
    questions: dict,
    model: str | None = None,
    task: str | None = None,
    ...,
    max_len: int | None = None,
    head_max_len: int | None = None,
    min_confidence: float | None = None
) -> dict
```

The implementation validates each question as a dictionary with a nonempty `instructions` field and one of `choice`, `score`, or `noul` types. `choice` accepts a dictionary of scalar labels to descriptions or a list of labels. `score` accepts a list of levels. `noul` accepts optional `true`/`false` criteria. The output includes an answer, probabilities, confidence, and `answer_confidence` for the choice questions used here (`.venv/lib/python3.12/site-packages/laya/agent.py:967-1087,1888-1907`).

The state parameter accepts a string, dictionary, or list. Dictionaries/lists are JSON-serialized by the package before tokenization (`.venv/lib/python3.12/site-packages/laya/common.py:95-110`). This supports serializing multiple evidence fields, but it is text serialization rather than a typed evidence contract. The state is bounded by the model token budget and can be truncated (`.venv/lib/python3.12/site-packages/laya/common.py:156-170`).

The package documentation confirms that finite choices and answer probabilities are supported, but also warns that confidence depends on option count and that thresholds require validation on held-out data (`.venv/lib/python3.12/site-packages/laya-0.4.2.dist-info/METADATA:825-829`). Custom `instructions` change the rendered question text. The documentation does not guarantee that arbitrary question wording creates a calibrated new task or preserves semantic grounding.

During the real CPU probe, the package also emitted an invalid-temperature warning and fell back to a bounded temperature. Confidence values for affected entries must therefore be treated as uncalibrated diagnostics, not deployment thresholds.

## API CAPABILITY

custom questions supported:
YES

categorical finite choice supported:
YES

structured evidence input supported:
YES, mechanically. The API serializes dict/list state to text; it does not enforce the proposed Don evidence schema.

multiple contextual evidence fields safely serializable:
YES, subject to token-budget truncation and caller-side bounding.

probabilities and confidence exposed:
YES. Choice answers expose `probabilities`, `confidence`, and `answer_confidence`.

custom question text changes model semantics in a documented/calibrated way:
NO. It changes the rendered question, but the package documents mechanics and output shape, not semantic validity for a new policy task.

The underlying API is expressive enough to pose the contract question. That is an API capability result, not a model suitability result.

## Synthetic probe contract

Each normal case contained:

- current session input;
- skill level, behavior confidence, and observed techniques;
- Don-style severity, tactics, observed TTPs, and IOCs;
- two or three synthetic retrieval documents with `doc_id`, title, excerpt, source, and retrieval score.

The eight cases were:

1. clear recon;
2. credential access;
3. persistence;
4. conflicting retrieval;
5. weak/irrelevant retrieval;
6. benign administration;
7. malformed/missing retrieval evidence;
8. contradictory behavior and retrieval.

The question bundle had three finite-choice questions:

```text
status: SELECT | ABSTAIN
strategy: the seven allow-listed V3 strategies
evidence_ref: D1..D4 | NONE
```

The caller converted `NONE` to an empty `evidence_refs` array. No free-form strategy output was accepted. A returned document reference was valid only when it was one of the IDs in that case's supplied bundle.

## PROBE

synthetic cases:
8

runs:
24 total, 3 repeated inference calls per case

schema-valid:
24/24

allow-list valid:
24/24

valid evidence refs:
24/24

malformed-output rate:
0/24

ABSTAIN behavior:
3/24 runs abstained. All three were the malformed/missing-evidence case and returned `ABSTAIN`, `baseline`, and no evidence reference. The weak/irrelevant, conflicting-retrieval, and behavior/retrieval-contradiction cases all selected a strategy in all three repeats. Therefore the probe demonstrates a missing-input abstain pattern, not robust insufficiency/contradiction detection.

input sensitivity:
5 unique `(status, strategy, evidence_refs)` signatures across the eight inputs. This is nonzero sensitivity, but it is not an accuracy measure and does not establish evidence grounding.

repeated-run stability:
All eight cases were stable across their three repeated calls. Stability was high but some stable outputs were semantically unsupported: clear recon and credential-access cases both selected `expose_decoy_internal_topology` with `D2`, while weak/irrelevant evidence selected rather than abstained.

latency:
Minimum `2740.06 ms`, mean `7343.15 ms`, median `7582.27 ms`, maximum `12329.28 ms`, on CPU. The first model load was included in the measured run set.

Representative outputs:

| Case | Status | Strategy | Evidence ref | Observation |
|---|---|---|---|---|
| clear recon | SELECT | expose_decoy_internal_topology | D2 | structurally valid but not supported by the strongest recon document |
| credential access | SELECT | expose_decoy_internal_topology | D2 | same strategy/reference as recon despite different evidence |
| persistence | SELECT | fake_success_and_return_visits | D1 | finite-choice output, but low strategy confidence |
| conflicting retrieval | SELECT | low_intensity_administration | D2 | did not abstain on conflict |
| weak/irrelevant | SELECT | contain_in_fiction_and_instrument | D2 | did not abstain on irrelevant evidence |
| benign administration | SELECT | low_intensity_administration | D2 | selected despite a competing benign document being stronger |
| malformed/missing | ABSTAIN | baseline | none | only case family with consistent abstention |
| behavior/retrieval contradiction | SELECT | low_intensity_administration | D2 | did not abstain on contradiction |

These are contract observations, not invented ground truth labels. No claim is made that a strategy is objectively correct for any synthetic case.

## SUITABILITY

classification:
TASK_ADAPTATION_UNVALIDATED

reason:

The API supports a custom finite-choice question and returns a schema-valid bounded answer with probabilities/confidence. However, the current checkpoint's behavior was not sufficiently grounded for the proposed task: it selected on weak, conflicting, and contradictory evidence, and the clear recon/credential cases shared a strategy and evidence reference that did not track the supplied evidence. Repeated stability makes the behavior reproducible, not trustworthy.

The current native RAGIN task remains attack/stage/severity assessment. It is not `NATIVE_TASK_COMPATIBLE`. A task adaptation is required, including an explicit evidence-conditioned question contract, caller-side evidence-reference validation, abstention policy, and a new scientific evaluation. This probe does not establish that a new checkpoint is necessary, but it also does not justify proceeding as if the current checkpoint were a policy model.

## RECOMMENDATION

Proceed with full POST_RETRIEVAL_POLICY_FUSION implementation:
NO

task adaptation required:
YES

new model/task required:
YES, because a new task is required. A new model is not established as necessary by this probe.

The immediate next step, if authorized, is a separately versioned task-adaptation study with frozen question wording, evidence serialization, option ordering, abstention thresholds, and contract checks. It must remain synthetic or use a newly defined evaluation set and must not alter V2 artifacts.

## SCIENTIFIC BOUNDARY

old 169 reused:
NO

effectiveness claim made:
NO

No reference labels, prior predictions, exploratory 120 cases, or primary 169 cases were used. The probe measures API expressiveness, output-contract compliance, sensitivity, stability, abstention behavior, and latency only.

LAYA V3 POLICY CAPABILITY PROBE COMPLETE.
NO PRIOR HOLDOUT OR EFFECTIVENESS ARTIFACT WAS USED.
THE CURRENT LAYA MODEL WAS EVALUATED ONLY FOR CONTRACT/TASK SUITABILITY.
FULL V3 IMPLEMENTATION REMAINS BLOCKED UNTIL THIS CAPABILITY DECISION IS MADE.
