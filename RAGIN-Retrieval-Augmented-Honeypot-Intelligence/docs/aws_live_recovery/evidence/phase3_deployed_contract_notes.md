# RAGIN Phase 3 — Deployed Application Contract Discovery

Source: `docs/aws_live_recovery/evidence/phase3_core_route_discovery_script_out_20261011T162211Z.json`
Parsed handler inventory: `docs/aws_live_recovery/evidence/phase3_route_handler_list.txt`

Runtime source file on CORE:
- `/opt/ragin/ragin/server_v2.py`
- sha256: `4bceee674f50b3d3a9dce8683725c46c35a737308699d363a1dc4fb9a8a6ca50`

Runtime mode:
- `python3 -m ragin.server_v2 --mode pipeline`
- `create_app(mode="pipeline")` registers the route set below.

Registered handlers (line: name):
- 201 `session_create`
- 226 `session_command`
- 272 `session_wake`
- 303 `session_context`
- 320 `session_replay`
- 350 `openai_chat_completions`
- 602 `health`
- 616 `ready`
- 620 `metrics`
- 692 `create_app`
- 729 `main`

Middleware (order in create_app):
- mtls_middleware
- auth_middleware
- timing_middleware

Key contract facts from source:
- Pipeline mode registers:
  - `POST /api/session/create`
  - `POST /api/session/command`
  - `POST /api/session/wake`
  - `POST /api/session/replay`
  - `GET /api/session/{session_id}/context`
  - `POST /v1/chat/completions`
  - `GET /health`, `GET /ready`, `GET /metrics`
- mTLS paths bypassed by middleware: `/health`, `/ready`
- Auth: `Authorization: Bearer <API_KEY>`
- mTLS allowed identities read from `RAGIN_MTLS_ALLOWED_IDENTITIES`
- Session ownership via `X-Session-Token`
- `openai_chat_completions` is the Cowrie bridge handler used for the staged LLM-backend topology
- `session_command` is the full harness pipeline command handler

Incorrect endpoint used earlier:
- `POST /ragin/v1/command` returned 404
- Correct registered command endpoint is `POST /api/session/command`
- Correct chat-completions endpoint is `POST /v1/chat/completions`

Environment used by deployed CORE:
- `RAGIN_MTLS_REQUIRED=1`
- `RAGIN_MTLS_ALLOWED_IDENTITIES=spiffe://ragin/edge`
- `RAGIN_BIND_HOST=172.31.17.217`
- `PORT=8443`
- `RAGIN_REQUIRE_AUTH=1`
- `RAGIN_MAX_REQUEST_BYTES=1048576`
