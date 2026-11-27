# Evidence Judge Filtering V1 Trace Contract

Filtering is opt-in through `RAGIN_EVIDENCE_JUDGE_FILTERING_ENABLED=1`. The default is disabled. Don V2 retrieval and ranking are unchanged.

The bundle retains the original `retrieval.documents`, the original retrieval trace, and the complete `evidence_judge.candidate_judgments`. The filter adds `evidence_judge_filter` with:

- `original_relevant_doc_ids`: the pre-filter relevance references.
- `filtered_relevant_doc_ids`: only original relevant IDs with `SUPPORTED` judgments and valid document provenance.
- `excluded_doc_ids`: original relevant IDs excluded from policy visibility.
- `partial_doc_ids`, `contradictory_doc_ids`, `unknown_doc_ids`: typed exclusion subsets.
- `filtered_sufficiency`: `SUFFICIENT`, `INSUFFICIENT`, `CONFLICTING`, or `UNKNOWN`.
- `policy_visible_evidence_ids`: the filtered evidence IDs intended for Gate and Policy.
- `rationale_codes`: deterministic reason codes.

The Gate requires the filtering contract version, requires filtered IDs to equal `retrieval.relevant_doc_ids`, rejects conflicts, and rejects non-sufficient filtered bundles. It continues to enforce its existing provenance, sanitization, coverage, and retrieval checks. Policy receives only the Gate `valid_doc_ids`.

No probabilities or confidence scores are generated. External and Laya adapters remain disabled.
