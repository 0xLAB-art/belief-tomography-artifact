# Task 2: Verified Serving Contract

## Required order

The authoritative `Harness._process_verified` sequence is:

1. `server_v2` authenticates the service request and validates the request shape (`ragin/server_v2.py:113-157,197-212,331-371`).
2. `Sandbox` loads or creates the session, increments the command counter, and calls the Harness (`ragin/cycle/sandbox.py:118-165`).
3. Harness emits the attacker input and builds pre-request context before classification and CTI analysis (`ragin/cycle/harness.py:327-340`).
4. A candidate is generated with fiction and host identity context. Generator exceptions become failed candidates, not serveable text (`harness.py:222-241`).
5. The configured verifier must return a dictionary with exactly `passed is True` for acceptance. Missing, malformed, false, or exception-raising decisions fail closed (`harness.py:243-259`).
6. A failed candidate is rejected without state commit. Retries are bounded by `max_retries` (`harness.py:340-370`).
7. The `ApprovalGateway` is evaluated after verification and before commit. `REQUIRE` without an approval returns no serveable candidate (`harness.py:261-275,344-360`).
8. After retry exhaustion, the deterministic template is treated as another candidate and must pass the same verifier and HITL gate (`harness.py:372-394`).
9. `_strict_commit` observes a clone, rejects contradictions, then commits the graph and host facts, persists host state, and records the accepted verification decision before the system-response event (`harness.py:277-325`).
10. Only the accepted candidate or verified fallback is placed in `PipelineResult.deception_response` and emitted as `SYSTEM_RESPONSE`.
11. If no candidate is accepted, the result contains no response text and `verified_serve_unavailable`; HTTP adapters return a 503 safe transport error (`harness.py:395-406`; `server_v2.py:216-231,380-421`).

## Response and provenance contract

An accepted result has `verification.passed=true`, `accepted=true`, `serve_path` (`GENERATED_VERIFIED` or `FALLBACK_VERIFIED`), bounded `attempt`, deterministic decision fields, and a SHA-256 digest of the served candidate. The session event log receives a verification event and then a system-response event. Rejections receive verification/error events but no candidate system-response event.

Transport errors are intentionally not deception responses. A generator outage, verifier exception, persistence failure, or rejected fallback produces an explicit 503 with `verified_serve_unavailable`; internal logs retain the failure class without exposing raw exception details to the attacker. The old generic shell-error response was removed because it was not verifier-approved content.

## Trust boundaries

Attacker input, transcript history, CTI/retrieved text, and provider output remain untrusted. They can influence classification, prompts, or candidate text, but cannot authorize a serve or state mutation. The deterministic verifier and post-verification staged commit are the authorization boundary. Provider/JEV/Laya availability never bypasses this boundary.

## Authentication boundary

Production defaults require a non-placeholder `API_KEY`; requests accept exact `X-API-Key` or Bearer credentials. Session endpoints additionally require the session capability token returned by session creation; possession of an arbitrary session ID is insufficient (`server_v2.py:113-148,172-194,197-305`). Health/readiness are the only unauthenticated routes. Metrics, context, replay, wake, generation, and operator-adjacent APIs are not public exceptions.
