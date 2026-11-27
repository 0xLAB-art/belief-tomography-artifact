# Evidence Judge V1 independent annotation guide

## Scope

This package is a blank independent review instrument for the 120 frozen cases. Reviewers must use only the observed command, available context, retrieved candidates, source references, and the stated behavioral claim. Do not use system Gate decisions, Judge decisions, or prior model outputs.

## Candidate review

For each candidate, select exactly one label:

- `DIRECT_SUPPORT`: the document directly and substantively supports the stated behavioral claim for the observed command and context.
- `PARTIAL`: the document is related and supports only part of the claim, or lacks enough detail for direct support.
- `IRRELEVANT`: the document does not materially relate to the command or claim.
- `CONTRADICTORY`: the document conflicts with the claim or supplies evidence against it.
- `UNKNOWN`: provenance, context, document content, or command meaning is insufficient to decide.

Record a short justification and cite the candidate `doc_id`, source URL or source reference, and the relevant document passage or locator.

## Bundle review

After reviewing all candidates, select exactly one bundle label:

- `SUFFICIENT`: the reviewed evidence supports the specific policy-relevant behavioral claim.
- `INSUFFICIENT`: evidence is relevant or partial but does not support the claim at the required specificity.
- `CONFLICTING`: material evidence supports incompatible interpretations or contains unresolved contradiction.
- `UNKNOWN`: command meaning, context, provenance, or evidence content prevents a reliable decision.

The command may be benign or ambiguous. Relevance alone is not sufficiency. State the exact evidence citations supporting the bundle decision.

## Review procedure

1. Read the observed command and all available context.
2. Read the precise behavioral claim.
3. Review each candidate independently and assign one candidate label.
4. Cite sources and passages for every non-`UNKNOWN` decision.
5. Assign one bundle label and explain why the cited evidence does or does not support the claim.
6. Leave any uncertain item as `UNKNOWN`; do not infer missing provenance.

The template contains two blank reviewer slots. The second slot is optional and must be completed independently without seeing the first review.
