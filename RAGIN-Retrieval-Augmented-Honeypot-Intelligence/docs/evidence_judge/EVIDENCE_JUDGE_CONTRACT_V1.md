# Don V2 Evidence Judge Contract V1

Status: `EVIDENCE_JUDGE_CONTRACT_READY` when the focused synthetic test suite and freeze generator pass.

## Scope

This stage is an opt-in, separately versioned evidence assessment between Don V2 retrieval and the existing Evidence Gate. The default is disabled with `RAGIN_EVIDENCE_JUDGE_ENABLED=0`. The stage performs string and provenance checks only. It does not execute commands, load a local model, download data, call a paid API, change AWS, or access historical HF-2024 holdouts.

The existing gate version and thresholds are unchanged. A bundle without `evidence_judge` follows the existing gate path byte-for-byte at the decision level.

## Pipeline

`Don V2 Retrieval -> EvidenceJudge per candidate -> Bundle Sufficiency -> Existing Evidence Gate -> Policy V2 -> Substantive Generator -> Verifier/HITL/Commit`

When enabled, `SUFFICIENT` permits the existing gate to continue. `INSUFFICIENT` and `UNKNOWN` produce a low-relevance gate result; `CONFLICTING` produces an unresolved-conflict result. The judge cannot make a malformed, unproven, or unsafe bundle valid, and it does not replace mandatory verification, approval, or commit checks.

## Typed candidate questions

`CandidateJudgment` records:

1. `relates_to_command`: relation to the observed command and multi-command context.
2. `substantively_supports_behavior`: direct behavioral support rather than topical similarity.
3. `support_kind`: `SUPPORTED`, `PARTIAL`, `IRRELEVANT`, `CONTRADICTORY`, or `UNKNOWN`.
4. `provenance_sufficient`: valid document identifier, non-empty source, and `provenance_status=VALID`.
5. `context_status`: `PRESENT`, `MISSING`, or `AMBIGUOUS`.

The candidate `label` is the typed evidence classification. Missing provenance is `UNKNOWN` even if text overlaps. An adjacent document can be related while remaining `PARTIAL` or `IRRELEVANT`.

## Bundle sufficiency

`BundleSufficiency.label` is one of `SUFFICIENT`, `INSUFFICIENT`, `CONFLICTING`, or `UNKNOWN`.

Relevance alone never produces `SUFFICIENT`. The deterministic judge requires at least one provenance-valid direct behavior match, and it abstains for ambiguous commands, contradictory evidence, provenance failure, partial-only support, and empty candidates. The trace preserves supporting and contradictory document IDs and rationale codes.

## Adapter contract

`EvidenceScoringAdapter` is an optional future seam. `ExternalScoringAdapter` and `LayaScoringAdapter` are present as disabled contracts and contain no client, checkpoint, or inference path. They cannot provide probabilities in their current state.

`EvidenceJudgeTrace.probabilities` is therefore always empty for the implementation in this freeze. Future probabilistic scoring requires calibration and independently labeled evidence before it can affect a decision.

## Freeze boundary

The freeze contains only fresh synthetic cases and full JSON decision traces. It is not an evaluation of historical frozen evaluations and makes no policy correctness or effectiveness claim. The SHA256 manifest covers the contract implementation, gate integration, tests, specification, and freeze generator.
