# SSH-wire E2E evidence — status and requirements

## Objective

Close the remaining evidence gap for Priority 0:

- a real, non-empty SSH-visible generated response,
- delivered by SSH to an isolated Cowrie instance,
- with a captured transcript,
- correlated to an accepted serving record,
- with explicit verification that no unaccepted candidate is transmitted.

## Current status

- **Session-record evidence:** present in prior sprint records.
- **Live SSH-wire captured transcript for a `GENERATED_VERIFIED` canary:** not completed from this host at this moment.

This gap is not closed by asserting a file exists. It is closed only when a controlled end-to-end run produces machine-readable evidence of live SSH delivery that matches an accepted candidate digest.

```
BLOCKER_EXPLICIT: ssh-wire-e2e-proof-pending
State: blocked_until_live_cowrie_and_live_generation_path_reachable_from_this_host
Local_evidence_available: unit_contracts_exist; local_opencode_bridge_exists; session_record_evidence_exists
Live_ssh_wire_captured: false
Correlation_gating: blocked_on_live_path
```

## Required test sequence

### 1. Start the approved local generation backend

- Use the OpenCode CLI bridge path that is already locally validated.
- Use the safe agent configuration that denies all tool categories.
- Use the approved free-model allowlist and the primary validated model.

### 2. Use a controlled canary command with a unique test identifier

- Pick a command that is expected to produce non-empty terminal output.
- Tie the run to a unique session/canary identifier.
- Record the identifier in the evidence bundle.

### 3. Generate a response through Hisoka

- Route the request through the authoritative pipeline, not through a bypass.
- Record intermediate artifacts:
  - classification,
  - Don retrieval state if enabled,
  - generation input/output references,
  - candidate digest.

### 4. Pass the candidate through the authoritative verifier

- Verification must be mandatory, not advisory.
- Record the verification decision and any issues.
- Do not serve a candidate that fails verification.

### 5. Capture the accepted candidate digest

- Record the exact accepted candidate before any wire transmission.
- Compute and store the digest used for later correlation.
- Store the raw accepted response text in the evidence bundle.

### 6. Execute the command using a real SSH client connected to isolated Cowrie

- Connect to the isolated Cowrie/EDGE endpoint used for internal testing only.
- Run the canary command from a real SSH client.
- Capture the raw SSH-visible output.

### 7. Capture the raw SSH-visible command output

- Capture terminal output, not just the shell prompt.
- Preserve framing/prompt differences explicitly so correlation is not based on fuzzy matching alone.

### 8. Verify the returned content matches the accepted serving record

- Correlate the SSH-visible output to the accepted candidate digest.
- Account explicitly for terminal framing and prompts.
- Show the match decision in machine-readable form.

### 9. Preserve complete request/session correlation

- Store session id, request id, candidate digest, verification outcome, and served output together.
- Make the mapping reproducible from the stored evidence.

### 10. Verify that no unaccepted candidate is transmitted

- Confirm that only the accepted candidate reaches SSH output.
- This is the security-critical assertion, not just a functional one.

## Pass criteria

- The test produces **non-empty command output**, not merely a shell prompt.
- The SSH-visible output is **correlated** to an **accepted** serving record.
- The evidence shows **no unaccepted candidate** was transmitted.
- Raw evidence and the machine-readable correlation are both preserved.

## Blocking condition in this host moment

The live SSH-wire proof requires:

- an isolated Cowrie/EDGE instance reachable from this host, and
- a live generation path (local bridge or authenticated CORE path) reachable from this host.

Both are needed. If either is unavailable, the proof cannot be executed from this host and must remain a documented blocker rather than a fabricated result.

## Evidence storage

When executed, store:

- `results/ssh_wire/<canary-id>.md` — human-readable evidence
- `results/ssh_wire/artifacts/<canary-id>.<json|txt>` — raw artifacts:
  - accepted candidate text
  - accepted candidate digest
  - verification record
  - raw SSH transcript
  - correlation report

## Namespace rule

This proof is a new next-stage evidence artifact. It must not be relabeled as historical JEV/OpenCode or manuscript headline evidence.

## Fallback behavior note

If a run produces a fallback response, that is **not** the same as a successful generative SSH-wire proof. The test must distinguish `GENERATED_VERIFIED` from `TEMPLATE_FALLBACK_VERIFIED` explicitly.
