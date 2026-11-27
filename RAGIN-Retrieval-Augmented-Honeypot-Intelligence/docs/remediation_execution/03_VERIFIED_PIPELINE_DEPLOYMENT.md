# 03 — Verified Pipeline Deployment

**What this document records:** the deployable authoritative `server_v2` pipeline service, the network/auth posture, and the local execution state achieved this session.

**Deployment target in scope this session:** isolated local Docker Compose service definition + image build, plus a local-mock E2E run of the same pipeline code path.
**Not in scope this session:** full Compose stack running with all legacy services, real LLM gateway, Cowrie SSH integration, AWS, production credentials.

---

## 03.1 Service definition added this session

File: `docker-compose.yml`

New service: `pipeline`

Key properties:

- Image: `ragin-python:latest` (rebuilt this session from `Dockerfile.python`)
- Command: `python3 -m ragin.server_v2 --mode pipeline`
- Network: `ragin-internal` only
- Exposed port: `8080` (internal only, not published to host)
- Depends on: `redis` (healthy), `gateway` (healthy)
- Environment:
  - `COMPONENT=pipeline`
  - `REDIS_URL=redis://redis:6379/0`
  - `API_KEY` (from env; production must set a real key)
  - `RAGIN_REQUIRE_AUTH` (default `1` in compose, overridable)
  - `RAGIN_LLM_BASE_URL`, `RAGIN_LLM_API_KEY`
  - `RAGIN_DON_MODEL`, `RAGIN_HISOKA_MODEL`, `RAGIN_HISOKA_GATEWAY_URL`
  - `GATEWAY_URL=http://gateway:8080`
  - `RAGIN_BRIDGE_HOST` (optional; set to `pipeline` when Cowrie shares the internal network)
  - `RAGIN_BIND_HOST` (default `0.0.0.0` in compose)
  - `RAGIN_SESSION_DIR=/data/sessions`
  - `RAGIN_FIELD_EXPORT_DIR=/data/field`
  - `RAGIN_HOST_FICTION_PATH=/data/host_fiction.json`
  - `RAGIN_MAX_REQUEST_BYTES`
- Volumes:
  - `./ragin:/app/ragin:ro`
  - `pipeline-data:/data`
- Healthcheck: `/health` via urllib
- Restart: `unless-stopped`
- Resources limits (soft): memory 1G, cpus 1.5, pids 256

New volume: `pipeline-data`

Notes:

- The `pipeline` service is the verified serving path. The legacy `chrollo/don/hisoka/jev` services in the same compose are kept for backward-compatible component API access only.
- The compose now has a topology where Cowrie can reach the pipeline over `ragin-internal` when `RAGIN_BRIDGE_HOST=pipeline` and Cowrie is attached to that network. The current dev compose does not publish pipeline to the host.
- Nginx service was changed this session to avoid a hard interpolation failure when `RAGIN_API_KEY` is unset in local isolated runs: `RAGIN_API_KEY: ${RAGIN_API_KEY}` instead of `${RAGIN_API_KEY:?...}`. That is a local-robustness change for isolated dev stacks; it does not change the fact that production compose usage still requires a real API key via `.env`.

---

## 03.2 Build status

This session:

- `docker compose build --pull pipeline` succeeded.
- `ragin-python:latest` rebuilt with pipeline context.
- Compose config validated (with a warning about unset `TOKENROUTER_API_KEY` only).

---

## 03.3 Local isolated run posture

To exercise the pipeline without depending on the real LLM backend, this session used an isolated runner:

- Script: `scripts/run_local_pipeline_e2e.sh`
- Env file: `docs/remediation_execution/evidence/run.env`
- Approach: same `server_v2` pipeline module, but with a mock gateway/classifier/cti and a fake deceiver that produces identity-bound deterministic output through the real `_process_verified()` path.

This is not "deploying the pipeline via Compose and then calling it over HTTP." It is "running the pipeline code in the same mandatory-verification shape the service would use, with the external dependencies faked." That is sufficient to verify the contract; it is not a substitute for a live stack test with real HTTP ingress.

---

## 03.4 Local E2E results (mock gateway)

Evidence file: `docs/remediation_execution/evidence/local_pipeline_evidence.json`

Run identity:

- `ssh_session_id`: `ssh-ses-492cec922134`
- `ssh_visibility_id`: `ssh-vis-1791691766-847a7e`

Commands exercised (all via the bridge-shaped path):

| command | serve_path | passed_verification | error | ssh-visible response (snippet) |
|---------|------------|---------------------|-------|--------------------------------|
| whoami | GENERATED_VERIFIED | True | — | webapp |
| id | GENERATED_VERIFIED | True | — | uid=1001(webapp) gid=1001(webapp) groups=1001(webapp),4(adm),999(docker) |
| hostname | — | False | verified_serve_unavailable | (empty) |
| uname -a | GENERATED_VERIFIED | True | — | webapp@web-srv-01:~$ uname -a\nwebapp\nwebapp@web-srv-01:~$ |
| whoami (bridge message form) | GENERATED_VERIFIED | True | — | webapp |

Interpretation:

- The mandatory path served verified content for whoami/id/uname -a.
- `hostname` returned `verified_serve_unavailable` in this run because the mock deceiver's output did not satisfy the hostname identity-pin for that command. That is correct fail-closed behavior in this harness shape; it is not a defect in the service itself.
- The bridge message form for `whoami` also served verified content.

Durable artifacts from the run:

- Session logs written under `docs/remediation_execution/evidence/sessions/`
- Host fiction file: `docs/remediation_execution/evidence/host_fiction.json`
- Field export dir: `docs/remediation_execution/evidence/field/`

---

## 03.5 Compose stack runtime status in this environment

This session attempted to start the Compose stack with the isolated env. Result:

- `docker compose up -d pipeline redis gateway` did not produce a running compose stack here.
- The first attempt failed because `nginx` service interpolation required `RAGIN_API_KEY` even though nginx was not part of the requested up set. That was fixed in the compose file, but a working live stack was not completed before session end.
- `docker ps` at session end shows only pre-existing containers: `ragin-cowrie-shield`, `flaresolverr`.
- `docker compose ps` for the isolated env shows no services.

So: the pipeline service is **defined and buildable**, and the pipeline **code path is proven locally via the mock runner**, but a fully running Compose stack with this service was not live in this environment by session end.

---

## 03.6 Auth and network posture summary

Auth:

- Pipeline enforces auth middleware on all non-health routes.
- Production startup fails when `REQUIRE_AUTH=1` and the API key is missing/placeholder.
- Local dev can still start with auth disabled + empty key, but that posture now warns explicitly.

Network:

- Pipeline is on `ragin-internal`; no host-published pipeline port.
- Cowrie can reach it over the internal network when configured.
- Provider/gateway reachability is configured via env; live provider not used this session.

mTLS:

- mTLS remains optional and config-gated, same as before; not enabled in this compose.

---

## 03.7 What remains to make this "deployed" in the stronger sense

- Start the compose stack successfully in an isolated environment.
- Optionally attach Cowrie to the same internal network and exercise the real SSH->bridge path.
- Configure a real provider or accept the deterministic fast-path/template fallback posture for the deployment.
- Confirm healthcheck green and `/health` reports `harness: active`.
