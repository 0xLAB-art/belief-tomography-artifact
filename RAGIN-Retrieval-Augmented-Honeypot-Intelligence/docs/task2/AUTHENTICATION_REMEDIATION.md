# Task 2: Authentication Remediation

## Implemented controls

- `server_v2` rejects missing, empty, and known placeholder production credentials at application creation and startup (`ragin/server_v2.py:41-128,668-697`).
- Authenticated requests require exact `X-API-Key` or Bearer credentials; health and readiness are the only public exceptions (`server_v2.py:113-157`).
- Session creation returns a random session capability. Command, wake, context, and replay endpoints require the matching `X-Session-Token`; a guessed session ID alone is rejected (`server_v2.py:131-148,172-305`).
- The Cowrie bridge applies the same service authentication and validates explicit session ownership; transcript continuity is a bounded local mapping, not an authorization credential (`server_v2.py:331-379`).
- The legacy Python server validates credentials in `create_app` and startup, protects metrics, and disables generative deception routes with HTTP 410 (`ragin/server.py:249-282,719-727`).
- Field Compose requires `BACKEND_API_KEY` and routes Cowrie to the verified `ragin-server`; the unverified `bare-llm` is a named baseline profile rather than the default service (`docker-compose.field.yml:65-130`).
- The main Compose Rust gateway no longer publishes a host port (`docker-compose.yml:1-13`).

## Rust gateway disposition

`llm-gateway/src/main.rs` and `llm-gateway/config.toml` do not provide demonstrated request authentication middleware. This task therefore does not claim that gateway auth is fixed. Host exposure was disabled in Compose, so the gateway is not an active public route. It must remain internal-only and cannot be used as a deployment dependency until authenticated service identity, authorization, and regression tests are added.

## Remaining blockers

The application controls do not establish AWS private networking, security groups, NACLs, IMDS protection, provider egress allowlisting, or emergency shutdown. The proposed CORE may still have a public IP. These are P0 deployment blockers from Task 1 and belong to the AWS hardening task. The current result is not authorization to deploy publicly.
