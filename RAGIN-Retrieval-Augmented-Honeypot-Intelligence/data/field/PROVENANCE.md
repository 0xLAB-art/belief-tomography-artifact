# `data/field/` provenance — LOCAL SELF-PLAY ONLY

Nothing in this directory is field-endpoint traffic. Do not cite it as field
data in the paper.

| Path | What it is | Dates |
|---|---|---|
| `ragin/` (194 `ses-*.jsonl`) | Session exports written by the **local** compose arm-C `ragin-server` (`RAGIN_FIELD_EXPORT_DIR=/field-export` volume bind) during local field-stack runs | 2026-09-28 (local arm exercises) + 2026-10-26 (Phase 3 arm-C workload, 15 sessions) |
| `cowrie/`, `cowrie-llm/`, `bare-llm/` | Empty export mounts of the local compose arms | — |

Real field-endpoint data (EDGE `REDACTED_FLEET_HOST` cowrie.json, CORE sessions)
lives on the AWS hosts and is collected only via
`scripts/collect_field_data.py` over SSM after reauthentication; it lands in
`evidence/field/` and `run/field_export/` (both currently empty — see
`docs/FIELD_ETHICS_REVIEW_2026-10-26.md` §B).

The Phase 3 arm comparison for the paper comes from
`results/field_attack/sessions_armA_cowrie.jsonl` /
`sessions_armC_ragin.jsonl` + `arm_comparison.json`, which carry their own
local-self-play caveats.
