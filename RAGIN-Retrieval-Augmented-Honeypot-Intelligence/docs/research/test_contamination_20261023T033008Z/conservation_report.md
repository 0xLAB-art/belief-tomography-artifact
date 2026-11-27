# Test-contamination conservation report — 2026-10-23T03:30:08Z

## Incident

A broad `pytest tests/unit tests/integration` run appended test events at `2026-10-23T03:23:25Z` to five tracked `data/sessions/sup-*.jsonl` files. The append occurred because these tests constructed `Session("sup-*")` without an explicit `session_dir`; `ragin/cycle/session.py` binds its default at import time, so setting `RAGIN_SESSION_DIR` after import would not help. No Git history was used to reconstruct the files.

## Preservation before restoration

Full contaminated bytes, the exact appended suffix, and post-restore copies are under `docs/research/test_contamination_20261023T033008Z`. The original dirty-work prefix was accepted only after an exact size + SHA-256 match against `docs/research/baseline/tracked_sha256_20261022T184958Z.jsonl`.

| file | frozen size | frozen SHA-256 | contaminated size | contaminated SHA-256 | suffix bytes | suffix SHA-256 | prefix match |
|---|---:|---|---:|---|---:|---|---|
| `data/sessions/sup-1.jsonl` | 308080 | `584788fa391d3720aff6c08738e41dd76868ab998010b55d4ddeecbeefb15b9f` | 309077 | `218e61821c9d4e2fb8bc14ccd50f598e5969a98b44b320d41b0407a4a04a0da2` | 997 | `ce181fc7dc240d1f3cf5da01e7492a1fe950e14a20740c098e89263d7dd1f260` | YES |
| `data/sessions/sup-ctx.jsonl` | 304340 | `76bbeaa35448103e05fb978caf699f975312ce88bfc96fe28ca3f14b6ae25d55` | 305337 | `16dd4920ace2b226016a39f673e1c56b5ecb27654ff53b714b73c77e7168fd3f` | 997 | `1893d76e0af77d800bd4bc64b3febd6175ad158d1fcd13835b3d41bdcde31a25` | YES |
| `data/sessions/sup-expert.jsonl` | 304340 | `db38ffc5affdb045f10edf584345077c4cf49cbeea43a5f3554557a0825aa268` | 305337 | `6ddc2c2a6b891b956e27245a4ef0886a46645252a5310c5a393a31282e49732d` | 997 | `cc223af980d5612546fcab5773053fe707a2dad59b074ba3b9b11dfb50063882` | YES |
| `data/sessions/sup-rev.jsonl` | 188136 | `1b77bb3738c44bc90a48f8bd4c768f211f779fbeb7e61df5e86419b14af2e436` | 188734 | `4f023c1730fe477f7f7ad210eb6a90d247febdc4991dcd05e9222034aae558bf` | 598 | `d5cd55c26f6e6bd4510acae50e9e0e1bcf208ecd9f903488f737eeef8451c20c` | YES |
| `data/sessions/sup-vote.jsonl` | 307283 | `e97f1b8faef0cc26aa2a111c8db086959997c34d0b563b4c65540cb7a2272149` | 308289 | `d0f7e56392655e70a8195f525e0ecd3cce709dc9659c28ad673985052123f32c` | 1006 | `45d2f47f565822c5ab0bb3f97b0075c3b405f6b06b103eae12cb09515eee2293` | YES |

## Restored state

Only the verified original prefix was written back. No other tracked file was modified by this correction.

| file | restored size | restored SHA-256 | matches frozen |
|---|---:|---|---|
| `data/sessions/sup-1.jsonl` | 308080 | `584788fa391d3720aff6c08738e41dd76868ab998010b55d4ddeecbeefb15b9f` | YES |
| `data/sessions/sup-ctx.jsonl` | 304340 | `76bbeaa35448103e05fb978caf699f975312ce88bfc96fe28ca3f14b6ae25d55` | YES |
| `data/sessions/sup-expert.jsonl` | 304340 | `db38ffc5affdb045f10edf584345077c4cf49cbeea43a5f3554557a0825aa268` | YES |
| `data/sessions/sup-rev.jsonl` | 188136 | `1b77bb3738c44bc90a48f8bd4c768f211f779fbeb7e61df5e86419b14af2e436` | YES |
| `data/sessions/sup-vote.jsonl` | 307283 | `e97f1b8faef0cc26aa2a111c8db086959997c34d0b563b4c65540cb7a2272149` | YES |

The five restored files remain modified relative to Git `HEAD`, which is expected: the frozen manifest records pre-existing dirty work, not `HEAD` bytes.

## Appended test events (metadata only)

`sup-1.jsonl.append`:
- `attacker_input` at `2026-10-23T03:23:25.799657+00:00` source=`harness`
- `classification` at `2026-10-23T03:23:25.809177+00:00` source=`supervisor`
- `system_response` at `2026-10-23T03:23:25.811708+00:00` source=`harness`
`sup-ctx.jsonl.append`:
- `attacker_input` at `2026-10-23T03:23:25.819762+00:00` source=`harness`
- `classification` at `2026-10-23T03:23:25.839261+00:00` source=`supervisor`
- `system_response` at `2026-10-23T03:23:25.842697+00:00` source=`harness`
`sup-expert.jsonl.append`:
- `attacker_input` at `2026-10-23T03:23:25.871904+00:00` source=`harness`
- `classification` at `2026-10-23T03:23:25.879845+00:00` source=`supervisor`
- `system_response` at `2026-10-23T03:23:25.882504+00:00` source=`harness`
`sup-rev.jsonl.append`:
- `attacker_input` at `2026-10-23T03:23:25.887123+00:00` source=`harness`
- `error` at `2026-10-23T03:23:25.895775+00:00` source=`supervisor`
- `error` at `2026-10-23T03:23:25.899693+00:00` source=`harness`
`sup-vote.jsonl.append`:
- `attacker_input` at `2026-10-23T03:23:25.854486+00:00` source=`harness`
- `classification` at `2026-10-23T03:23:25.863973+00:00` source=`supervisor`
- `system_response` at `2026-10-23T03:23:25.867116+00:00` source=`harness`

Raw command/text values from the test events are preserved only in the suffix artifacts and are not reproduced here.

## Session directory audit

- Current `data/sessions` file count: **7659**.
- Files present now but absent from the frozen 2026-10-22 untracked inventory: **4955**. These were left untouched; they are not deleted or reclassified. Fifteen have mtimes at/after 2026-10-23T03:20Z, including the five restored files and ten `ses-*` test artifacts.
- Full current inventory with sizes, SHA-256, and mtimes: `session_inventory_after.jsonl`.
- Delta inventory: `not_in_20261022T184958Z_inventory.jsonl`.

## Isolated rerun evidence

The focused rerun used unique paths and set the environment before interpreter import:

```bash
RAGIN_SESSION_DIR=/tmp/opencode/ragin_envcheck_20261023T033500Z/sessions \
RAGIN_HOST_FICTION_PATH=/tmp/opencode/ragin_envcheck_20261023T033500Z/host/host_fiction.json \
.venv/bin/python -m pytest <focused tests> -q
```

Result: **289 passed**, raw exit **0**. The aggregate SHA-256 of the `data/sessions` inventory was identical before and after (`0dcb647984b7134ccc7f0a5a557db5f37dacc4e8facdf1d0d4297d61ce4b9328`), so the isolated run did not append to the default session directory.

Targeted isolation fixes were made so the same contamination cannot recur from these tests:

- `tests/unit/test_coordination.py`: all five `Session("sup-*")` constructions now receive `session_dir=str(tmp_path)`.
- `tests/security/test_task2_verified_serving.py`: both default `Sandbox(harness=...)` constructions now pass `SandboxConfig(session_dir=str(tmp_path / "sessions"))`.

## Boundary

This is a correction of unintended test appends and a preservation record, not a deletion of evidence. The raw appended bytes remain recoverable. No destructive Git command was used. No full-plan or readiness claim is made here.

