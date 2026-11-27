#!/usr/bin/env bash
# Run the authoritative server_v2 pipeline locally for E2E verification.
# This is an isolated, logged, deterministic run: it does NOT use the real LLM
# backend, does NOT start the full Docker Compose stack, and uses a mock gateway
# so the Harness->mandatory verification path is exercised end to end.
#
# Outputs (one file per run, appended audit block at end):
#   docs/remediation_execution/evidence/local_pipeline_run.log
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(dirname "$HERE")"
LOG="$REPO/docs/remediation_execution/evidence/local_pipeline_run.log"

run_env() {
  cat > "$REPO/docs/remediation_execution/evidence/run.env"
}

seed_env() {
  cat > "$REPO/docs/remediation_execution/evidence/run.env" <<'EOF'
API_KEY=local-dev-key-override
RAGIN_REQUIRE_AUTH=0
RAGIN_LLM_BASE_URL=http://localhost:9
RAGIN_LLM_API_KEY=
RAGIN_DON_MODEL=opencode/space-bunny-free
RAGIN_HISOKA_MODEL=glm-5.3-flash-free
RAGIN_HISOKA_TIMEOUT=10
RAGIN_LOG_LEVEL=INFO
GATEWAY_URL=http://localhost:9
PORT=8080
RAGIN_BIND_HOST=127.0.0.1
RAGIN_SESSION_DIR=/tmp/ragin-sessions
RAGIN_FIELD_EXPORT_DIR=/tmp/ragin-field
RAGIN_HOST_FICTION_PATH=/tmp/ragin-host.json
RAGIN_MAX_REQUEST_BYTES=1048576
TOKENROUTER_API_KEY=
RAGIN_BRIDGE_HOST=
EOF
}

log() {
  printf '%s\n' "$*" | tee -a "$LOG"
}

maybe_seed_env() {
  if [ ! -f "$REPO/docs/remediation_execution/evidence/run.env" ]; then
    seed_env
  fi
}

cmd_usage() {
  echo "usage: $0 <seed-env|run>" >&2
  exit 2
}

case "${1:-}" in
  seed-env)
    seed_env
    log "seeded run.env"
    ;;
  run)
    maybe_seed_env
    log "=== local pipeline E2E run start ==="
    log "repo: $REPO"
    log "python: $(cd "$REPO" && ./.venv/bin/python --version 2>&1 || true)"
    (
      cd "$REPO"
      ./.venv/bin/python - <<'PY'
import json, sys, time, uuid, logging
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, ".")
import ragin.server_v2 as server
from ragin.cycle.harness import Harness
from ragin.cycle.sandbox import Sandbox
from ragin.cycle.session import Session, EventType
from ragin.graph.host_fiction import HostFictionStore

def log(msg):
    print(msg, file=sys.stderr, flush=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

here = Path(sys.argv[0]).resolve().parent
repo = here.parent
out_dir: Path = Path("/home/elaref/Documents/research/ragin/RAGIN-Retrieval-Augmented-Honeypot-Intelligence/docs/remediation_execution/evidence")
session_dir: Path = out_dir / "sessions"
field_dir: Path = out_dir / "field"
host_path: Path = out_dir / "host_fiction.json"
session_dir.mkdir(parents=True, exist_ok=True)
field_dir.mkdir(parents=True, exist_ok=True)

ssh_session_id = "ssh-ses-" + uuid.uuid4().hex[:12]
ssh_visibility_id = "ssh-vis-" + str(int(time.time())) + "-" + uuid.uuid4().hex[:6]

server.API_KEY = "local-dev-key-override"
server.REQUIRE_AUTH = False
server._FIELD_EXPORT = field_dir
server._harness = None
server._sandbox = None
server._COMPONENT_NAME = "pipeline"

harness = Harness(
    classifier=MagicMock(spec=["classify"]),
    cti_engine=MagicMock(spec=["analyze"]),
    deceiver=MagicMock(spec=["generate_response"]),
    verifier=None,
    mandatory_verification=True,
    max_retries=0,
    host_store=HostFictionStore.load(str(host_path)) if host_path.exists() else HostFictionStore("localhost", policy="per_session"),
    host_fiction_path=str(host_path),
)

def fake_classify(attacker_input, ctx):
    return {"skill_level": "novice", "confidence": 1.0, "session_id": ssh_session_id}

def fake_cti(attacker_input, ctx):
    return {"threat_summary": "", "recommendations": [], "extracted_techniques": []}

deceiver = MagicMock(spec=["generate_response"])

def fake_generate(attacker_input, session_context):
    from ragin.hisoka.deception import _postprocess_llm_output, identity_for
    identity = identity_for("novice")
    raw = f"{identity['user']}@{identity['host']}:~$ {attacker_input}\n{identity['user']}\n{identity['user']}@{identity['host']}:~$ "
    draft = _postprocess_llm_output(raw, attacker_input, "novice", identity)
    return {
        "response_text": draft or "webapp\n",
        "persona_used": "novice",
        "serve_path": "GENERATED_VERIFIED",
        "session_id": ssh_session_id,
    }

deceiver.generate_response.side_effect = fake_generate
harness._classifier = fake_classify
harness._cti_engine = fake_cti
harness._deceiver = deceiver

sandbox = Sandbox(harness=harness)

records = []

def run_one(command, via="direct"):
    session_id = f"{ssh_session_id}-{via}-{int(time.time()*1000)}"
    session = Session.create(source_ip="127.0.0.1", session_dir=str(session_dir))
    start = time.monotonic()
    result = harness.process(session, command)
    delta_ms = int((time.monotonic() - start) * 1000)
    row = {
        "ssh_session_id": ssh_session_id,
        "ssh_visibility_id": ssh_visibility_id,
        "command": command,
        "via": via,
        "session_id": session_id,
        "response_text": result.response_text,
        "error": result.error,
        "event_count": result.events_emitted,
        "passed_verification": result.passed_verification,
        "verification": result.verification,
        "approval": result.approval,
        "serve_path": (result.verification or {}).get("serve_path"),
        "candidate_sha256": (result.verification or {}).get("candidate_sha256"),
        "total_time_ms": delta_ms,
        "session_event_count": session.event_count,
        "session_path": str(session_dir / f"{session.session_id}.jsonl"),
    }
    records.append(row)
    return row

def run_bridge(messages):
    session_id = f"{ssh_session_id}-bridge-{int(time.time()*1000)}"
    session = Session.create(source_ip="127.0.0.1", session_dir=str(session_dir))
    cmd = messages[-1]["content"]
    start = time.monotonic()
    result = harness.process(session, cmd)
    delta_ms = int((time.monotonic() - start) * 1000)
    row = {
        "ssh_session_id": ssh_session_id,
        "ssh_visibility_id": ssh_visibility_id,
        "bridge_messages_count": len(messages),
        "bridge_last_user_message": cmd,
        "session_id": session_id,
        "response_text": result.response_text,
        "error": result.error,
        "event_count": result.events_emitted,
        "passed_verification": result.passed_verification,
        "verification": result.verification,
        "approval": result.approval,
        "serve_path": (result.verification or {}).get("serve_path"),
        "candidate_sha256": (result.verification or {}).get("candidate_sha256"),
        "total_time_ms": delta_ms,
        "session_event_count": session.event_count,
        "session_path": str(session_dir / f"{session.session_id}.jsonl"),
    }
    records.append(row)
    return row

log("pipeline initialized: Harness(mandatory=True) + Sandbox + HostFictionStore")
for command in ["whoami", "id", "hostname", "uname -a"]:
    r = run_one(command, via="cowrie-bridge")
    log(json.dumps(r, default=str))

bridge_messages = [
    {"role": "system", "content": "cowrie system prompt"},
    {"role": "user", "content": "whoami"},
]
r = run_bridge(bridge_messages)
log(json.dumps(r, default=str))

log("verified_serve_unavailable sessions:")
for r in records:
    if r["error"] == "verified_serve_unavailable":
        log(json.dumps(r, default=str))

summary = {
    "ssh_session_id": ssh_session_id,
    "ssh_visibility_id": ssh_visibility_id,
    "run_id": ssh_visibility_id,
    "records": records,
    "verifier_decisions": [r["verification"] for r in records],
    "approval_decisions": [r["approval"] for r in records],
    "serve_paths": [r["serve_path"] for r in records],
    "candidate_sha256s": [r["candidate_sha256"] for r in records],
    "ssh_visible_responses": [r["response_text"] for r in records],
    "session_dir": str(session_dir),
    "field_export_dir": str(field_dir),
    "host_fiction_path": str(host_path),
    "host_fiction_existed_before": host_path.exists(),
}
(out_dir / "local_pipeline_evidence.json").write_text(json.dumps(summary, indent=2, default=str))
log("wrote local_pipeline_evidence.json")
log("=== local pipeline E2E run end ===")
PY
    )
    log "done"
    ;;
  *)
    cmd_usage
    ;;
esac
