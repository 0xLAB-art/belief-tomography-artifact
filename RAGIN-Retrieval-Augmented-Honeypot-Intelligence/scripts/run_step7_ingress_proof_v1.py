from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import signal
import subprocess
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "results" / "step7_full_system_evaluation_v1" / "ingress_proof_v1"
API_KEY = "step7-local-auth-key-20261015"
PORT = 18087
CONTAINER = "step7-cowrie-ingress-proof"


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_capture(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    out = args.out
    if out.exists():
        raise RuntimeError(f"refusing to overwrite existing ingress artifact: {out}")
    out.mkdir(parents=True)
    session_dir = out / "sessions"
    field_dir = out / "field_export"
    session_dir.mkdir()
    field_dir.mkdir()
    env = os.environ.copy()
    env.update(
        {
            "RAGIN_BIND_HOST": "127.0.0.1",
            "RAGIN_REQUIRE_AUTH": "1",
            "API_KEY": API_KEY,
            "RAGIN_RAG_MODE": "offline",
            "RAGIN_RUNTIME_MODE": "RAGIN_V4_SUBSTANTIVE_DETERMINISTIC",
            "RAGIN_PROVIDER_ENABLED": "0",
            "RAGIN_LLM_BASE_URL": "http://127.0.0.1:9",
            "GATEWAY_URL": "http://127.0.0.1:9",
            "RAGIN_SESSION_DIR": str(session_dir),
            "RAGIN_FIELD_EXPORT_DIR": str(field_dir),
            "RAGIN_HOST_FICTION_PATH": str(out / "host_fiction.json"),
            "PYTHONUNBUFFERED": "1",
        }
    )
    server_log = out / "ragin_server.log"
    server_handle = server_log.open("wb")
    server = subprocess.Popen(
        [str(ROOT / ".venv/bin/python"), "-m", "ragin.server_v2", "--mode", "pipeline", "--port", str(PORT)],
        cwd=ROOT,
        env=env,
        stdout=server_handle,
        stderr=subprocess.STDOUT,
    )
    container_started = False
    try:
        for _ in range(100):
            if server.poll() is not None:
                raise RuntimeError(f"RAGIN server exited: {server.returncode}")
            try:
                if run_capture(["curl", "-sf", f"http://127.0.0.1:{PORT}/health"], timeout=3).returncode == 0:
                    break
            except subprocess.TimeoutExpired:
                pass
            time.sleep(0.25)
        else:
            raise RuntimeError("RAGIN health check timed out")

        docker_args = [
            "docker", "run", "-d", "--name", CONTAINER, "--network", "host",
            "-e", "COWRIE_HONEYPOT_BACKEND=llm",
            "-e", f"COWRIE_LLM_HOST=http://127.0.0.1:{PORT}",
            "-e", "COWRIE_LLM_PATH=/v1/chat/completions",
            "-e", f"COWRIE_LLM_API_KEY={API_KEY}",
            "-e", "COWRIE_LLM_MODEL=ragin-local",
            "-e", "COWRIE_LLM_MAX_TOKENS=80",
            "-e", "COWRIE_LLM_TEMPERATURE=0",
            "-e", "COWRIE_LLM_DEBUG=true",
            "-e", "HTTP_PROXY=", "-e", "HTTPS_PROXY=", "-e", "ALL_PROXY=",
            "-e", "http_proxy=", "-e", "https_proxy=", "-e", "all_proxy=",
            "cowrie/cowrie:latest",
        ]
        docker = run_capture(docker_args, check=True, timeout=30)
        container_started = True
        container_id = docker.stdout.decode().strip()
        time.sleep(6)

        client = subprocess.Popen(
            [
                "ssh", "-tt", "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null",
                "-o", "PreferredAuthentications=password", "-o", "PubkeyAuthentication=no",
                "-p", "2222", "root@127.0.0.1",
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        assert client.stdin and client.stdout and client.stderr
        client.stdin.write(b"whoami\n")
        client.stdin.flush()
        time.sleep(10)
        client.stdin.write(b"exit\n")
        client.stdin.flush()
        client_stdout, client_stderr = client.communicate(timeout=30)
        (out / "ssh_client.stdout").write_bytes(client_stdout)
        (out / "ssh_client.stderr").write_bytes(client_stderr)

        logs = run_capture(["docker", "logs", CONTAINER], check=True, timeout=30)
        (out / "cowrie.log").write_bytes(logs.stdout + logs.stderr)
        image = run_capture(["docker", "image", "inspect", "cowrie/cowrie:latest"], check=True, timeout=30)
        image_info = json.loads(image.stdout.decode())[0]
        write_json(out / "container_image.json", {"repo_digests": image_info.get("RepoDigests", []), "id": image_info.get("Id"), "created": image_info.get("Created")})
    finally:
        if container_started:
            subprocess.run(["docker", "rm", "-f", CONTAINER], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        server.send_signal(signal.SIGTERM)
        try:
            server.wait(timeout=20)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=5)
        server_handle.close()

    export_files = sorted(field_dir.glob("*.jsonl"))
    export_rows = [json.loads(line) for path in export_files for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    session_files = sorted(session_dir.glob("*.jsonl"))
    events = [json.loads(line) for path in session_files for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    event_types = {event.get("event_type") for event in events}
    responses = [event for event in events if event.get("event_type") == "system_response"]
    served_text = responses[0].get("data", {}).get("text", "") if responses else ""
    verification = next((event.get("data", {}) for event in events if event.get("event_type") == "verification"), {})
    policy = next((event.get("data", {}) for event in events if event.get("event_type") == "strategy_update"), {})
    serving = next((event.get("data", {}).get("serving_trace", {}) for event in events if event.get("event_type") == "response_generate"), {})
    server_text = server_log.read_text(encoding="utf-8", errors="replace")
    client_stdout = (out / "ssh_client.stdout").read_bytes()
    served_digest = sha_bytes(served_text.encode()) if served_text else None
    served_wire = served_text.replace("\n", "\r\n").encode() if served_text else b""
    proof = {
        "schema": "ragin.step7.ingress_proof.v1",
        "status": "PASS" if all([
            client_stdout,
            served_text,
            served_wire in client_stdout,
            served_digest == verification.get("candidate_sha256"),
            'POST /v1/chat/completions' in server_text and '" 200 ' in server_text,
            export_rows and not export_rows[-1].get("error"),
            {"classification", "cti_lookup", "strategy_update", "verification", "system_response", "response_generate", "metric"}.issubset(event_types),
            verification.get("passed") is True and verification.get("accepted") is True,
            verification.get("commit_event") == "accepted",
            serving.get("served_response_sha256") == served_digest,
        ]) else "FAIL",
        "container": {"name": CONTAINER, "id": locals().get("container_id"), "network": "host", "image": "cowrie/cowrie:latest"},
        "client": {"ssh_port": 2222, "stdout_sha256": sha_bytes(client_stdout), "stderr_sha256": sha_bytes((out / "ssh_client.stderr").read_bytes()), "served_text_substring": served_wire in client_stdout},
        "bridge": {"http_200_observed": 'POST /v1/chat/completions' in server_text and '" 200 ' in server_text, "export_rows": len(export_rows), "export_sha256": sha_bytes(json.dumps(export_rows, sort_keys=True).encode()) if export_rows else None},
        "session": {"session_files": [str(path.relative_to(out)) for path in session_files], "event_types": sorted(event_types), "event_count": len(events)},
        "served": {"response_text_sha256": served_digest, "candidate_sha256": verification.get("candidate_sha256"), "serve_path": verification.get("serve_path"), "verifier": verification.get("verifier"), "approval": verification.get("accepted"), "commit_event": verification.get("commit_event"), "policy_hash": policy.get("policy_hash"), "strategy": policy.get("selected_response_strategy"), "serving_trace_sha256": sha_bytes(json.dumps(serving, sort_keys=True).encode()) if serving else None},
        "model_identity": {"mode": "RAGIN_V4_SUBSTANTIVE_DETERMINISTIC", "provider_backed": False, "model": "ragin-local"},
    }
    write_json(out / "ingress_proof.json", proof)
    manifest_files = {}
    for path in sorted(out.rglob("*")):
        if path.is_file() and path.name != "ingress_manifest.json":
            manifest_files[str(path.relative_to(out))] = sha_bytes(path.read_bytes())
    write_json(out / "ingress_manifest.json", {"schema": "ragin.step7.ingress_manifest.v1", "status": "FROZEN", "proof_sha256": sha_bytes((out / "ingress_proof.json").read_bytes()), "files": manifest_files})
    print(json.dumps(proof, indent=2, sort_keys=True))
    return 0 if proof["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
