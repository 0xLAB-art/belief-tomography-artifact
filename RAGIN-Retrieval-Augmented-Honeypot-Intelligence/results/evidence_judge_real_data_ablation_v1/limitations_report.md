# Real-data Evidence Judge V1 ablation limitations

The preferred separate prospective Cowrie/SSH corpus was unavailable. This ablation therefore uses 120 same-source retrospective HF-2024 source-group command families, selected after excluding prior source groups and normalized command families.

No genuine independent reviewer labels were available. The blinded packet contains empty candidate and bundle review fields, and no Judge, Gate, or prior model output was used as reference truth. Accuracy, precision, recall, false admissions, false rejections, confidence intervals, and paired agreement are therefore not evaluated.

The two arms share the frozen command/context inputs, Don V2 retrieval configuration, retrieved evidence, corpus, and existing gate. No policy, generator, verifier, HITL, or commit path was run.
