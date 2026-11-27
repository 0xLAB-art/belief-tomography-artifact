# V4 Real Capture Privacy Policy

## Scope

This policy applies to prospective V4 capture artifacts and derived canonical records. Raw captures remain access-controlled research evidence; registry and evaluation artifacts are minimized metadata.

## Retention and minimization

- Raw source IPs are never written to the prospective registry, canonical evaluation record, public artifact, or annotator material.
- Source/network correlation uses a keyed HMAC-SHA256 identifier. The study secret is external to evaluation artifacts and is not published.
- Credential, token, password, authorization, and API-key values are redacted by default. A keyed hash may be retained only when required for duplicate/correlation analysis; raw secret material is never retained in derived study artifacts.
- Command and event text is retained only in access-controlled raw evidence and the minimum sanitized canonical context needed for the preregistered evaluation input.
- Operator/admin transcripts are limited to the controlled session and are checked for unrelated personal identifiers before derivation.

## Safety and ethics boundary

Collection is limited to the approved controlled honeypot, documented natural-field sources where separately authorized, and isolated real Linux administration sessions. No production credentials, private-network pivot, cloud metadata access, or uncontrolled outbound action is permitted. Source provenance and consent/ethics/containment approvals remain deployment gates outside the capture library.

## Failure behavior

Missing provenance, failed hash checks, unrecognized source classes, raw-secret exposure, malformed timestamps, replay, synthetic, or fixture flags make a record ineligible. The collector fails closed and does not infer provenance from realism, UUIDs, or transcript shape.
