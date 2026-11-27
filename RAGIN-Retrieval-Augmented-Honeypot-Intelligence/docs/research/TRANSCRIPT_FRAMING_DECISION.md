# TRANSCRIPT FRAMING DECISION — 2026-10-23

Decision: **keep transcript contract `v1` as the default; `v2` stays opt-in.**
No serving behavior changed in this phase.

## Why

`v1` (server prepends the echo) is the contract historical artifacts were
produced under; `v2` (frontend owns the echo) is the one a real Cowrie
frontend actually delivers. The evidence runs already separate the two
(`persona_alignment_20261023T052609Z` under v1, `…054559Z` under v2), so the
duplicate echo is documented, measured, and reproducible rather than silently
"fixed". Changing the default now would break byte-for-byte reproduction of
every frozen run for no measurement gain — the framing itself does not alter
model output, only the echo the attacker already receives from the PTY.

## What this phase added

Regression tests, not behavior:

- `tests/integration/test_served_output_integrity_v1.py`
  - closed loop: the served-response hash in the interaction trace, the
    `SYSTEM_RESPONSE` event, and the bytes returned to the caller are the same
    bytes (real Harness/Sandbox/Session; generator and verifier faked);
  - the bounded `served_text` projection may truncate, and the primary hash
    must not — the echo-aware diagnostic stays separate from the primary
    attacker-facing record;
  - failed verification serves empty and records empty;
  - frozen evidence: under `v2` every command appears **exactly once** on the
    captured SSH wire and no served payload carries an echo line; under `v1`
    the duplicate is still present in the evidence and is **not** rewritten.

## Acceptance criteria for making `v2` the default (not met yet)

1. Every experiment artifact records `transcript_contract` per serving trace
   (done in code; must be true for every arm run).
2. The closed-loop harness asserts framing+payload end-to-end, not just the
   payload (see gap below).
3. All frozen runs that will be cited remain reproducible under their recorded
   contract version, and any cross-contract comparison is labelled.
4. The 14 assertions that encode the v5.5 transcript shape
   (`test_hisoka.py`, `test_credential_baits.py`) are re-owned under v2 with
   an explicit contract change, not edited in place.

## Remaining gap (honest)

The framing+payload concatenation is asserted end-to-end only by the persona
proof over real SSH bytes (one run, five commands, one persona). The
closed-loop harness asserts the payload hash and the returned bytes, but the
PTY framing layer does not exist inside it, so a per-arm assertion of
"attacker-visible bytes == framing + payload" still requires the loopback
persona-style run. Until that is wired into the arm runner, any arm-level
claim about attacker-visible text must cite the serving-boundary hash and
label the framing layer as observed-by-sampling, not asserted-per-turn.
