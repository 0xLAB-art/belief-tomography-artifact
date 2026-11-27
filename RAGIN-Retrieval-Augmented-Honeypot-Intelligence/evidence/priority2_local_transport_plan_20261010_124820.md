# Priority 2 — local permanent generation transport (implementation plan)

## Goal
Smallest authenticated, loopback-only local transport between the trusted generator and AWS CORE, with tests and failure classification, without exposing public inference or the OpenCode proxy.

## Found so far
- server_v2 (8731) is the verified serving core; keep it private.
- OpenCode proxy (127.0.0.1:41155) still listening; live probe returned  for a tiny completion, so genuine local model inference availability is NOT confirmed this session.
- Proposing a bounded local generator gateway shim plus config plus tests before any AWS-facing wiring.

## Local transport requirements
- Bind 127.0.0.1 only; no public inference listener.
- Explicit bearer auth; no credential logging.
- Bounded request bytes, response tokens, timeout, retries.
- Provider unavailable => deterministic verifier fallback or TEMPLATE_FALLBACK_VERIFIED, never unverified generation.
- Keep EDGE from being an unrestricted model proxy.

## Do NOT claim
DEPLOYED until a genuine authenticated live connection has been tested end-to-end.
No unapproved material network-trust changes.
No misuse of EIC as permanent inference transport.

## Next implementation slice
Implement local generator gateway shim + config + negative tests first; separate AWS CORE wiring for a later approved step.

artifact generated: evidence/priority2_local_transport_plan_20261010_124820.md
