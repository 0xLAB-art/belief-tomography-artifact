# V3 AI Label Status

Status: exploratory annotation-reliability evidence only.

The three valid V3 agent runs (`v3_agent_run_01`, `v3_agent_run_03`, and
`v3_agent_run_04`) are exploratory annotation-reliability evidence. They
are not human raters and they are not a reference standard. AI majority
vote is prohibited as confirmatory truth. Their labels must not influence
human raters or adjudicators. The poor agreement result is preserved as a
scientific result and is not repaired by rerunning annotators.

Future Chrollo-vs-Laya confirmatory analysis requires independently
collected human labels.

## Frozen aggregate reliability statistics

These are aggregate values only; no case-level labels are included here.

- Valid runs: 3; invalid run excluded: `v3_agent_run_02`.
- Invalid-run reason: `PREDECLARED_BLINDNESS_BOUNDARY_VIOLATION`.
- Multiclass: N=120; observed agreement=0.341667; Fleiss kappa=0.077003.
- Multiclass pairwise exact agreement range: 0.083333–0.475000.
- Binary: eligible N=112; excluded N=8 for unresolved `UNCERTAIN` values;
  observed agreement=0.505952; Fleiss kappa=-0.022925.
- Binary pairwise agreement range: 0.258929–0.655462.

The binary projection and all confirmatory analyses are separately frozen
in the human protocol. No AI label is used as human-reference evidence.
