# source_bytes/ moved out of the git tree (2026-10-26)

`source_bytes/` (the frozen byte-exact source copy from the 2026-10-23T04:29Z
recovery freeze) was moved out of the repository working tree per
`docs/MASTER_PLAN_2026-10-24.md` Phase 4 ("Move evidence snapshots out of the
tree"):

    ../evidence_snapshots_archive/docs/research/recovery_final_20261023T042900Z/source_bytes/

(path relative to the repository root; the archive sits next to the repo at
the project root). All 130 snapshot files across the three moved directories
were relocated with content intact (same filesystem rename; file count
verified equal before/after). The bytes also remain in git history at commit
`57be3c1c` and earlier.

Prose in `../../PERSONA_ALIGNMENT_ERRATUM_20261023.md` and any other records
that cite `recovery_final_20261023T042900Z/source_bytes/...` refer to this
archived copy.
