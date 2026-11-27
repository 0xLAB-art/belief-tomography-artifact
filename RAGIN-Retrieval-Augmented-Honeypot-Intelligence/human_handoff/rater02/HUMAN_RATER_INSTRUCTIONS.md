# Independent Offline Cybersecurity Behavior Classification

This packet contains 120 cases. Complete every case independently and do
not discuss cases with other raters before your initial file is frozen.

For each case, select exactly one label from the nine labels below and add
a short evidence-based note:

- `BENIGN`
- `RECON`
- `SUSPICIOUS`
- `EXPLOITATION`
- `PRIVILEGE_ESCALATION`
- `DATA_ACCESS`
- `PERSISTENCE`
- `OTHER_ATTACK`
- `UNCERTAIN`

Label observed behavior, not presumed intent. Do not infer source,
honeypot status, or authorization from formatting. Natural-language
discussion of a technique is not execution. A standard Linux command alone
is not automatically malicious. Do not balance categories or use expected
prevalence. Use `UNCERTAIN` when the supplied evidence is genuinely
insufficient.

Keep each note short and tied to the evidence shown in the case. Do not
add fields, change case IDs, reorder the frozen text inside a case, or omit
a case. The completed output for each case is:

```json
{"case_id": "...", "label": "...", "note": "short evidence-based reason"}
```

Return all 120 completed items under the required output schema. The
coordinator will freeze the file before any discussion or later review.
