# RAGIN — EXECUTION CLOSE: SSH WIRE PROOF +AWS E2E — 2026-10-09

This document is the required execution output for the next-stage closure. It
updates existing next-stage files rather than creating another large report
collection.

Repository root: `/home/elaref/Documents/research/ragin/RAGIN-Retrieval-Augmented-Honeypot-Intelligence`
Updated files in this run:
- `docs/next_stage/EXECUTION_CLOSE_SSH_WIRE_AND_AWS_E2E_2026-10-09.md`
- `docs/next_stage/LAYA_REAL_INFERENCE_STATUS.md`
- `ragin/server_v2.py` (bridge bind patch)
- `results/external_baseline_cowrie_guarded_rerun_cowrie.json` (probe artifact)
- `scripts/_tmp_full_proof*.sh/.err/.out` (raw chain artifacts, best-effort)
- `scripts/_tmp_launch_proxy_and_probe.*` (raw proxy artifacts, best-effort)
- `scripts/_tmp_run_completion*.sh/.err/.out` (raw completion artifacts, best-effort)
- `/tmp/sv2_direct_final*.json`, `/tmp/sv2_corr_final*.json` (temporary evidence)
- `/tmp/ssh_wire_final*.txt`, `/tmp/ssh_stderr_final*.txt`, `/tmp/ssh_exit_final*.txt`

---

## 1. LOCAL SSH WIRE — FAIL (this run)

### Result
- **Verdict:** FAIL
- **Reason:** No non-empty verifier-accepted content reached the SSH wire through
  Cowrie in this laptop execution. Several independent causes contributed, and the
  wire was not faked.

### Environment used
- Cowrie container: `ragin-cowrie-shield`
- Cowrie network: `ragin-cowrie-net` (bridge, gateway `172.19.0.1`)
- Cowrie IP on bridge: `172.19.0.2`
- Cowrie SSH port: `2222`
- Cowrie auth: password `OVERTESTONLY`, user `5mXbKp9`
- SSH binary used: `/usr/bin/ssh` with `sshpass`
- Local sv2 target: `http://127.0.0.1:8083/v1/chat/completions`
- Test API key used for this wire run:
  `RAGIN_LLM_API_KEY=ragin-cowrie-test-wire-proof-2026-10-09`
- Cowrie backend configuration in this run: bridge proxy to sv2 on `172.19.0.1:8083`
  (base64-wrapped prompt lines)

### Raw SSH transcript — attempt
- `/tmp/ssh_wire_final*.txt` (stdout) and `/tmp/ssh_stderr_final*.txt` (stderr)
  were captured across multiple attempts. The SSH session established the
  Cowrie shell and accepted the password, but the command channel did not return
  non-empty verifier-accepted content on the wire for the tested commands:
  `id`, `uname -a`, `echo LAYACORE_LIVE`, `ls -la /home`.

### Raw artifacts preserved
- sv2 direct post capture: `/tmp/sv2_direct_final*.json`
- sv2 correlation probe capture: `/tmp/sv2_corr_final*.json`
- sv2 log: `/tmp/sv2_final*.log`
- cowrie log tail captured from `docker logs ragin-cowrie-shield --tail 90`

### What the artifacts show
1. Cowrie reached the configured proxy path and sent prompts toward sv2 in the
   bridge topology used for this run.
2. The sv2 bridge proxy forwarding was reachable from the Cowrie bridge side
   **only after** the server_v2 bind patch landed. Before the patch, the stock
   CLI bound `127.0.0.1` and the bridge topology could not close the loop.
3. Even after the bind patch, the default Cowrie `llm` backend persona/prompt path
   did not produce non-empty verifier-accepted content for the tested command set
   on this execution. That is a real logic gap, not an assumed one: verifier
   acceptance depends on content, and the default path did not yield accepted
   content under these test conditions.
4. The SSH-visible output on the wire was therefore not a non-empty verified
   response generated through the pipeline for these commands.

### What this means for the milestone
- The next success milestone is:
  **a real, non-empty, verifier-accepted SSH response with wire-level provenance.**
- That milestone was **not reached in this run**. The failure is in the
  verifier/prompt path and in the bridge bind path, both of which are real and
  were evidenced, not assumed.

---

## 2. AWS EDGE → CORE — unable to prove from this laptop

### Result
- **Verdict:** NOT PROVEN FROM THIS LAPTOP
- **Reason:** The app-layer request must be made from inside the AWS EDGE
  instance using its existing authorized mTLS client identity and API
  authentication. The laptop does not hold that identity and was not used to
  fabricate or export anything.

### What is known from prior verified state
- AWS CORE/EDGE are running and accessible through SSM.
- AWS CORE serves privately with mandatory mTLS.
- The private application path exists between EDGE and CORE.

### What could not be done from this laptop
- I could not run the application-level request from the laptop because the EDGE
  mTLS client identity and API auth live inside AWS, not on this host.
- I did not export EDGE private keys to the laptop or CORE.
- I did not fabricate a new trusted certificate.
- I did not disable mTLS.
- I did not relax SAN identity authorization.
- I did not open public ports.
- I did not enable insecure SSH forwarding.

### Current labeling
- **Outcome label from this laptop:** UNAVAILABLE (unproven here)
- This is accurate: the path is reachable-and-live per prior verified state, but
  the app-layer proof was not executed from the current host, so it is not labeled
  GENERATED_VERIFIED or FALLBACK_VERIFIED from this laptop.
- If AWS CORE is still fallback-only in the AWS-internal view, that should be
  reported explicitly there; it is not asserted here as GENERATED on AWS.

### AWS COWRIE OUTPUT
- **Label from this laptop:** NOT DETERMINED HERE
- If Cowrie is already configured on AWS EDGE, the controlled localhost SSH
  interaction and its wire transcript must be captured from inside EDGE. That was
  not executed from this laptop.

---

## 3. GENERATOR TRANSPORT — DEPLOYED (partial), with a real remaining blocker

### Result
- **Status:** DEPLOYED for the local bridge path, with the remaining blocker below.

### What was deployed this run
- The bridge bind gap in `server_v2.py` was fixed so bridge/pipeline mode can
  bind to `RAGIN_BRIDGE_HOST` (default `0.0.0.0`) instead of forcing
  `127.0.0.1` when bridge mode is active. This makes sv2 reachable from the
  internal Cowrie bridge in the topology used for this run.
- The provider path was validated directly:
  - Reachable provider probed directly from this laptop:
    `api.apmix.ai`
  - Model id that works today: `claude-sonnet-4-6-free`
  - Real `finish_reason: stop` completions were observed from the provider.
  - The old `opencode/space-bunny-free` model id is a hard 404 from the provider,
    so `RAGIN_LLM_BASE_URL=http://127.0.0.1:8731/v1` is no longer a working
    default without a provider-side model id change.
- The local OpenCode proxy remained functional and reachable.

### What is still blocked
- The local flow is now structurally able to reach sv2 from the Cowrie bridge, but
  the verifier/prompt path still did not produce non-empty verifier-accepted SSH
  content for the tested command set this run. That is the remaining blocker for
  the wire proof milestone.
- AWS CORE still lacks a proven permanent provider-backed path from this laptop's
  view. The smallest secure authorized path that avoids new recurring charges was
  investigated, but the laptop-side boundary prevented completing the AWS-proof
  portion here.

### Hard constraints preserved
- No public proxy exposure.
- No EICE inference network transport use.
- Provider credentials stay on the trusted side.
- Cowrie stays separated from model-control interfaces.
- Mutual authentication and authorization remain mandatory.
- Service allowlisting remains strict.
- Request/response sizes and timeouts remain bounded.
- Fail-closed generation and verified fallback remain the posture.

---

## 4. TEST RESULTS — actual executed counts

### Focused integration
- Command:
  ```
  .venv/bin/python -m pytest tests/integration/test_readiness.py tests/integration/test_pipeline.py -q
  ```
- Exit code: 0
- Result: **86 passed**, 3 warnings, 2.64s
- Captured to: `/tmp/pytest_int_final4.out`

### Unit / security
- Command:
  ```
  .venv/bin/python -m pytest tests/unit tests/security -q
  ```
- Exit code: 0
- Result: **1553 passed**, 28 warnings, 142.42s
- Captured to: `/tmp/pytest_unit_security_final4.out`

### Failure policy
- No failures were hidden.
- The verifier/prompt gap is a real logic gap and is reflected in the SSH-wire
  verdict above, not papered over by test counts.

---

## 5. LAYA — real inference / fixture-only / blocked

### Current status
- See `docs/next_stage/LAYA_REAL_INFERENCE_STATUS.md`
- This run did not complete live Laya inference from this host.
- The adapter contract is present and locally validated without the full app
  dependency set.
- Local unit-style checks for the adapter contract passed for fixture signals and
  failure paths.
- Real inference from this host was not completed and is not asserted as completed.

### Label
- **OPTIONAL_ASSESSMENT_STATUS:** in_progress
- **Local_adapter_contract:** verified_without_app_deps
- **Local_unit_style_checks:** passed_for_fixture_signals_and_failure_paths
- **Real_inference_from_this_host:** not_completed
- **Real_inference_gating:** reachability_timeout_credentials_approval

---

## 6. COST — actual changes and known exposure

### Actual changes
- One code patch landed in `ragin/server_v2.py` for bridge bind behavior.
- One git commit landed:
  ```
  fe09635 fix(server_v2): bind pipeline/bridge mode to RAGIN_BRIDGE_HOST ...
  ```
- No new billed AWS resource was created from this laptop.
- No public exposure was added.
- No EC2/EBS migration was performed.

### Known exposure
- The free-pool provider path was validated directly from this laptop for
  completeness. That validation does not change project defaults in this run, but
  it is the reachable path if the project defaults are updated later with approval.
- The remaining blocker is not a cost blocker; it is an architectural/validation
  blocker for the wire proof milestone.

---

## 7. NEXT ACTION — concrete executable next step

### Highest-priority next action
Fix the two real blockers to close the LOCAL SSH WIRE milestone:

1. **Make the Cowrie-facing / verifier prompt non-empty on the default persona path**
   so the verifier can actually accept generated content for real commands. The
   current default path can yield empty `response_text`, which causes verifier
   rejection. That must be fixed at the source of the prompt/response path, not by
   pretending the wire produced output.

2. **Keep sv2 reachable from the internal bridge Cowrie is on** using the
   bridge-bind patch already landed, then restart sv2 and re-run the full chain:
   - restart sv2 fresh
   - password-ssh to `172.19.0.2:2222`
   - run `id; uname -a; echo LAYACORE_LIVE; ls -la /home`
   - capture SSH transcript + sv2 log correlation
   - verify the accepted final response matches the SSH-visible output
   - do not count a shell prompt alone as command output

### Secondary next action
If you want the AWS EDGE→CORE app request proven, it must be run from inside
EDGE/CORE via the existing authorized SSM channel with the EDGE-side mTLS identity
and API auth. That cannot be done from this laptop without violating the stated
constraints, and I will not fabricate or export anything to get around that.

### Independent work
After the SSH-wire proof exists, continue with:
- Laya real-inference feasibility and bounded setup
- Protected audit persistence
- Final container egress restrictions
- Private encrypted CORE cutover cost and approval packet
- Reproducible controlled research workloads

Those are not declared complete from contract tests alone.

---

## Raw evidence index

- sv2 direct completion captures: `/tmp/sv2_direct_final*.json`
- sv2 correlation probe captures: `/tmp/sv2_corr_final*.json`
- SSH transcript captures: `/tmp/ssh_wire_final*.txt`
- SSH stderr captures: `/tmp/ssh_stderr_final*.txt`
- SSH exit captures: `/tmp/ssh_exit_final*.txt`
- sv2 logs: `/tmp/sv2_final*.log`
- integration test capture: `/tmp/pytest_int_final4.out`
- unit/security test capture: `/tmp/pytest_unit_security_final4.out`
- repository commit: `fe09635` in `ragin/server_v2.py`

---

## Closing statement

This execution closed as far as the current environment allows. The local bridge
bind blocker is fixed and committed. The verifier/prompt blocker is evidenced and
remains open. The AWS EDGE→CORE app-layer proof is reachable-but-unproven-from-this-
laptop and is labeled accordingly. The next milestone is a real, non-empty,
verifier-accepted SSH response with wire-level provenance.
