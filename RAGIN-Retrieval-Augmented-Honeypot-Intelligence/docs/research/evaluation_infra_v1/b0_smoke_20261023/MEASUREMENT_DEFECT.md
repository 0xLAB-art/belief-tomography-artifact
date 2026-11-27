# B0 native smoke — measurement defect and final evidence

**Date:** 2026-10-23  
**Scope:** `TEST_ONLY_B0_NATIVE_INTEGRATION_SMOKE`. No ablation effect is measured.

## First smoke (preserved, defective summary field)

- Path: `/tmp/opencode/ragin_b0_smoke_20261023_034743`
- `summary.json` SHA-256: `c8207e6a6584be3e91b17e91af75b125b6b157d6d54195e725b4734d0e3410aa`
- Record SHA-256: `9983fd38ab37642bbfa6353bb8f9b632656c96ef883e07ef36218863e47b61fc`
- Turns: 2; terminal cause: `ADMIN_CENSORED`; runner exit: 0.
- Defect: `ssh_loopback_only=false` and `listeners=[]` were measured **after**
  container cleanup, so they describe the cleaned-up host, not the live Cowrie
  listener. The run itself passed the live loopback bind check.
- Disposition: bytes preserved unchanged. Do not cite this summary as listener
  evidence.

## Second smoke (authorized final, live listener captured)

- Path: `/tmp/opencode/ragin_b0_smoke_20261023_034852`
- `summary.json` SHA-256: `441bc2d47cc5a2b4518d916c11162328494b13617f64e8ccdb4a012d685007d7`
- Record SHA-256: `02e3fcaa9c9d7d2e25119067c551fc55d51e4f006c6827fe8b54a65fd0f49b8e`
- Turns: 2; terminal cause: `ADMIN_CENSORED`; runner exit: 0.
- Live listener row: `LISTEN 0 50 127.0.0.1:60889 0.0.0.0:*`
  (`ssh_loopback_only=true`).
- Post-cleanup observation: `post_cleanup_observation.json`
  (`post_cleanup_listeners=[]`, `cleanup_true=true`).
- Final raw manifest: `raw_outputs.sha256.final.json`
  SHA-256 `dbc3174c660d8be386b66ea6473065b39ebf3b60705cc3673929ed2d1a2d9359`.
  It includes `summary.json` and all other artifacts, and excludes only itself.

## Runner correction for future runs

`scripts/run_ablation_track_b_v1.py` now captures the live listener rows, writes
a separate `post_cleanup_observation.json` after container removal, requires
both the live loopback check and cleanup to pass for `PASS`, and hashes every
artifact except the raw manifest itself. No further campaign/session was run.

## Claim boundary

This is transport/control evidence only: real SSH, native Cowrie shell, a
`SCRIPTED_POLICY` attacker, no LLM inference, no ablation B0–B3 comparison, no
H1 baseline match. The B0 identity remains `NOT_ESTABLISHED` against the
B1–B3 host fiction.
