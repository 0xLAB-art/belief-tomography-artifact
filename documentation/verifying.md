# Verification

Two SHA-256 manifests cover the repository, both rooted at the repository root:

| Manifest | Scope |
|---|---|
| `docs/paper/belief_tomography/ARTIFACT_MANIFEST.sha256` | The **381 frozen experiment artifacts** — registrations hashed *as frozen, post-hoc edits included* |
| `SUPPLEMENTARY_ASSETS.sha256` | Every other deposit file (**46,469** entries; excludes the manifests and policy documents themselves) |

## Run the checks

```bash
./verify.sh                    # → 381 frozen + 46,469 supplementary files OK
```

or the raw commands:

```bash
sha256sum -c docs/paper/belief_tomography/ARTIFACT_MANIFEST.sha256
sha256sum -c SUPPLEMENTARY_ASSETS.sha256
```

`verify.sh` exits non-zero on any mismatch and prints the failing paths.

## What is pinned

- **The frozen scope** covers `gauntlet/demo/` (recursive), the day-0
  registration files under `docs/paper/belief_tomography/`, `data/field/`, and
  `docs/paper/belief_tomography/independent_reaudit/`. The original 395-entry
  scope also pinned `paper/tops/figs/figdata/*.dat`; those 20 figure-data
  files were released from the deposit on 2026-11-27 together with the
  manuscript builds (manifest header documents the reduction).
- **The supplementary scope** covers everything else: manuscripts, platform
  mirror, live-fleet VPS export, review records, figure sources, producer
  scripts.

## Structural checks

```bash
bash checks/quick_counts.sh
```

asserts, straight from the frozen artifacts:

- the 230-flag decomposition: **118** `unauthorized_action` refusal-quote
  false positives + **112** genuine `secret_leak` canary echoes;
- the blocked-turn table: E30 Flash 9 · V4-Pro 79 · MiniMax 305 ·
  E31 Flash 0 · V4-Pro 59 · MiniMax 24.
