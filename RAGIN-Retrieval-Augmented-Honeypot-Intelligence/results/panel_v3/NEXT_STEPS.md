# Fresh-rerun program — state and next steps (2026-10-31 ~23:59 UTC)

## What is running right now
`python3 scripts/run_baseline_comparison.py --limit 30 --json --report results/b4_fresh_rerun_20261031.json` (PID 651178, detached, log /tmp/b4_full.log).
- Fresh 90-scenario paired grounding ablation on the LIVE agentrouter-backed stack — removes the paper's "fresh provider-backed reruns are currently unavailable" caveat.
- Runner patched to dump **full response texts** to `results/b4_fresh_responses.jsonl` (harness_bridge now carries `response_full` in details).
- When it completes: `results/b4_fresh_rerun_20261031.json` = fresh paired delta (the paper's headline +0.154 test on fresh models).

## After it completes (in order)
1. **Disjoint-juror re-score** (J1/J4/J5's decisive ask):
   - Score `results/b4_fresh_responses.jsonl` with kimi-k3 and/or gemini (apinex, free, ~1.5 s/call — 180 rows ≈ 10 min)
   - Blind to arm: juror scores each response against the scenario's expected technique/actor
   - Compute the paired delta under the independent labeler; bootstrap CI
   - Report in §5.1: "a family-disjoint labeler re-scores the fresh paired ablation: Δ = X [CI] — the +0.154 headline survives de-correlation" (or shrinkage honestly reported)
2. **Compare fresh vs archived**: does the +0.154 replicate on fresh models? Update §5.1 "Fresh provider-backed reruns are currently unavailable" → now available and reported.
3. **v3 decomposition control** (J3's decisive ask, next in queue): 10 sessions against a bait-only deterministic surface.
4. **Re-run the 5-judge panel** on the final text.
5. Register abstract Nov 10, submit Nov 17.

## Gotchas
- Dump appends; clear `results/b4_fresh_responses.jsonl` before any rerun.
- harness_bridge `response_full` addition is additive (manifest_hash unchanged — per_row unchanged).
- If the run dies: delete the partial report json, clear the dump, relaunch with `--limit 30`.
- beatapi key: credit exhausted (402) — beatapi-dependent jobs (claude brain/juror) blocked until top-up.
- apinex key: working, fast (~1.5-2 s/call), x-ratelimit headers for adaptive pacing; kimi-k3 most cooperative on red-team framing, gemini refuses in-session sometimes but was fine for the v3 run.
