# S&P 2027 rescue artifacts

This directory contains new rescue work kept separate from the frozen
version-of-record campaign artifacts.

## Valid artifact

`behavior_trajectory_benchmark.json` is a provider-free replay of 400 held-out
sessions from `data/training/test.jsonl` at eight command prefixes. Its
independent result is the Chrollo skill-classification learning curve. The
risk-floor comparison is explicitly a self-consistency diagnostic because its
reference rule is also implemented by the Supervisor; it is not an
independent effectiveness claim.

## Excluded provider pilot

The `hostfiction_provider_*` artifacts are retained as an operational trace,
not experimental evidence. They served deterministic fallback content after
the configured model returned HTTP 404 (`Unknown model`). A read-only catalog
request then returned an empty model list. No provider-generated quality or
security result is inferred from those files.

## 2026-10-08 provider recheck (Task 8)

`python3 scripts/check_apmix_catalog.py` was re-run 2026-10-08T06:03:31Z
(exit 2, catalog drift). Provider catalog HTTP 200 lists only
`claude-sonnet-4-6-free`; the wired models `deepseek-v4-flash-free` and
`grok-4.7-free` remain absent, and the quota probe was not run
(`quota_http: 0`, `quota_status: not_probed`) because the catalog gate is
`drift`. Provider-backed reruns remain **blocked**; this rescue benchmark
retains its status as provider-free, held-out, fallback-only evidence and no
provider comparison claim is available.
