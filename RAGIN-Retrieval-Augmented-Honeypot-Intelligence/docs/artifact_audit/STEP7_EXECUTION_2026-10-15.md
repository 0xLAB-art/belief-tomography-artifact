# Step 7 — Execution Status

Date: 2026-10-15. Plan: `docs/PAPER_REMAINING_STEPS_2026-10-14.md` §Step 7.
Runner: `scripts/run_step7_full_system_evaluation_v1.py`.

## HTTP study execution

The Step 6 freeze was rechecked before execution: 75/75 source hashes matched.
The authenticated local `server_v2` pipeline ran both frozen arms with the same
40 cases, isolated sessions, deterministic policy, offline retrieval, and closed
provider port:

- A (`A_judge_off`): 40/40 complete case-arm pairs.
- B (`B_judge_on`): 40/40 complete case-arm pairs.
- Total: 80/80 unique case-arm pairs, 0 failed pairs, 620 raw HTTP calls.
- Every request and response body has a SHA-256 record in each arm's
  `raw_http_calls.jsonl`; session JSONL and server logs are preserved.
- `run_manifest.json` is marked `RAW_OUTPUTS_FROZEN_BEFORE_ANALYSIS`.
- `raw_output_manifest.json` freezes hashes for the complete raw-output tree.

This is operational deterministic evidence only. No provider-backed inference,
reference-label join, scoring, tuning, or Step 8 analysis was performed.

## SSH/Cowrie ingress gate

The isolated Cowrie container accepted the SSH connection and authenticated
`root/toor`. An interactive SSH client sent `whoami`, waited for the deferred
backend response, and then sent `exit`. Cowrie POSTed the conversation to the
authenticated RAGIN `/v1/chat/completions` endpoint and returned the served
response to the SSH client. The proof records the client stdout/stderr bytes,
Cowrie log, RAGIN access log, field export, session trace, and Cowrie image
identity:

`results/step7_full_system_evaluation_v1/ingress_proof_v3/ingress_proof.json`

The client-visible `whoami` response is byte-correlated after terminal CRLF
normalization to the RAGIN `response_text_sha256` and verifier
`candidate_sha256`. The same trace records `GENERATED_VERIFIED`,
`FictionConsistencyVerifier`, approval, policy hash/strategy, and accepted
commit. The bridge observed HTTP 200 and exported two session rows.

The earlier bridge failures are preserved under `ingress/`,
`ingress_retry_proxy_clear/`, `ingress_retry_interactive/`, and
`ingress_pass_candidate/`; diagnosis showed that Docker bridge access to the
host-bound service timed out. The passing proof uses an isolated host-network
Cowrie container, with no external deployment or live attacker traffic.

## Completion gate

`results/step7_full_system_evaluation_v1/step7_completion_gate.json` is PASS.
It verifies 40 frozen cases × 2 arms = 80 unique complete pairs, immutable
raw-output hashes, input and retrieval symmetry, deterministic model identity,
manipulation/trace coverage, safety invariants, and the SSH bridge correlation.
Raw outputs were frozen before scoring or tuning. The study is deterministic
and provider-unavailable by protocol; no provider-backed inference claim is
made.
