# source_snapshot/ + source_snapshot_final/ moved out of the git tree (2026-10-26)

The two source-snapshot directories of this handoff were moved out of the
repository working tree per `docs/MASTER_PLAN_2026-10-24.md` Phase 4
("Move evidence snapshots out of the tree"):

    ../../../../../evidence_snapshots_archive/evidence/final_handoff_20261023T035907Z/source_snapshot/
    ../../../../../evidence_snapshots_archive/evidence/final_handoff_20261023T035907Z/source_snapshot_final/

(paths relative to this directory; the archive sits next to the repository at
the project root). Content is byte-identical (same-filesystem rename, 130
files total across the three moved directories, count verified before/after),
so each `SNAPSHOT_SHA256.json` still validates against its files when rooted
at the archive location. The bytes also remain in git history at commit
`57be3c1c` and earlier.

`FINAL_HANDOFF_REPORT.md` and `release_manifest_final.stdout.txt` in this
directory cite the old in-repo paths; they describe this archived copy.
