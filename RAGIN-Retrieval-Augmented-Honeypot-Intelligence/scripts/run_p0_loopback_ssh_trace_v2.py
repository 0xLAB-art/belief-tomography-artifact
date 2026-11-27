#!/usr/bin/env python3
"""P0 loopback SSH trace v2: 3 canonical positive turns + 1 negative session.

This runner extends v1 without modifying the frozen v1 source. It proves the
same positive transport/serving/verification/cardinality invariants, then opens
one separate SSH session with a predeclared negative command (default:
`cat /etc/sudoers`) and records the OBSERVED Cowrie/front-end behaviour on the
server's fail-closed 503. It does not assume that 503: the observation and the
absence of a fabricated claim are explicit checks.

It does NOT establish LLM inference, attacker engagement, dense retrieval, or an
arm effect. The final joint trace is intentionally pending until the generator
and eval streams are stable.

Boundary decisions
------------------
* Every listener is bound to ``127.0.0.1`` (server via ``RAGIN_BIND_HOST``,
  Cowrie via ``listen_endpoints=tcp:<port>:interface=127.0.0.1``).
* The Cowrie container is started from the local image **ID**, not a mutable
  tag, with ``--pull=never``.
* The runner writes a pre-launch manifest (git dirty state, source/config
  hashes, ports, image, environment policy) before starting the server.
* Exactly three expected commands must match three ``attacker_input``,
  ``system_response``, ``verification``, and ``metric`` events. Candidate,
  verified, and served SHA-256 values must agree, and each served text must
  occur after its corresponding terminal echo at a distinct offset.
* A failure leaves a fresh timestamped artifact directory with the failed
  summary; nothing is overwritten.

Egress limitation
-----------------
The container uses Docker host networking because the server is loopback-only.
Hard network-namespace egress blocking is NOT applied. An application-level
policy disables the provider, points every inference endpoint at a closed
loopback port, clears proxy variables, and uses the deterministic runtime. This
is not a network sandbox. A shared ``--network none`` namespace was assessed but
not used: the local ``ragin-python`` image has no SSH client/sshpass, and the
Cowrie image has neither ``/bin/sh`` nor paramiko. Injecting host binaries would
require loader/library mounts; host firewall changes were out of bounds.

Usage:
    .venv/bin/python scripts/run_p0_loopback_ssh_trace_v2.py [--out DIR] [--keep] [--negative-command CMD]
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import platform
import re
import signal
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
API_KEY = "p0-loopback-local-key"
COWRIE_IMAGE = "cowrie/cowrie:latest"
POSITIVE_COMMANDS = ["whoami", "id", "uname -a"]
NEGATIVE_COMMAND = "cat /etc/sudoers"
EXPECTED_COMMANDS = POSITIVE_COMMANDS
PROMPT_RE = re.compile(r"^[A-Za-z0-9_.-]+@[A-Za-z0-9_.-]+:[^$#]*[$#]\s?")
SECRET_ENV_RE = re.compile(r"(KEY|TOKEN|SECRET|PASSWORD|AUTH|CREDENTIAL|PROVIDER)", re.IGNORECASE)
SOURCE_FILES = [
    "scripts/run_p0_loopback_ssh_trace_v1.py",
    "scripts/run_p0_loopback_ssh_trace_v2.py",
    "ragin/server_v2.py",
    "ragin/cycle/harness.py",
    "ragin/cycle/sandbox.py",
    "ragin/cycle/adapters.py",
    "ragin/cycle/classification.py",
    "ragin/cycle/session.py",
    "ragin/cycle/verifier.py",
    "ragin/cycle/strict_research.py",
    "ragin/cycle/verification_deadline.py",
    "ragin/cycle/provider_transport.py",
    "ragin/gateway/generation.py",
    "ragin/gateway/client.py",
    "ragin/hisoka/deceiver.py",
    "ragin/hisoka/deception.py",
    "ragin/graph/host_fiction.py",
    "ragin/don/rag_engine.py",
    "ragin/don/vector_store.py",
    "ragin/don/intel_corpus.py",
    "ragin/decision_fusion_v4/evidence_export.py",
    "ragin/capture_v4/privacy.py",
    "configs/ablation/manifest_v1.json",
    "docs/research/CAUSAL_ABLATION_PROTOCOL.md",
]


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha_file(path: Path) -> str | None:
    try:
        return sha_bytes(path.read_bytes())
    except OSError:
        return None


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def free_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def two_free_loopback_ports() -> tuple[int, int]:
    first = free_loopback_port()
    second = free_loopback_port()
    while second == first:
        second = free_loopback_port()
    return first, second


def run_capture(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(args, capture_output=True, **kwargs)


def redact_env(env_map: dict[str, str]) -> dict[str, str]:
    return {
        key: ("[REDACTED]" if SECRET_ENV_RE.search(key) else value)
        for key, value in sorted(env_map.items())
    }


def safe_env(out: Path) -> dict[str, str]:
    """Build the server environment from an allow-list, not os.environ.copy().

    Inherited provider keys, cloud credentials, proxy settings, and RAGIN
    overrides are deliberately absent. The deterministic trace must not be
    able to spend money or reach an external endpoint through an inherited
    variable.
    """
    home = out / "home"
    tmp = out / "tmp"
    home.mkdir(parents=True, exist_ok=True)
    tmp.mkdir(parents=True, exist_ok=True)
    env: dict[str, str] = {}
    for key in ("PATH", "LANG", "LC_ALL", "TERM", "USER", "LOGNAME", "SHELL"):
        if key in os.environ:
            env[key] = os.environ[key]
    env.update(
        {
            "HOME": str(home),
            "TMPDIR": str(tmp),
            "PYTHONNOUSERSITE": "1",
            "PYTHONUNBUFFERED": "1",
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "RAGIN_BIND_HOST": "127.0.0.1",
            "RAGIN_REQUIRE_AUTH": "1",
            "API_KEY": API_KEY,
            "RAGIN_RAG_MODE": "none",
            "RAGIN_RUNTIME_MODE": "RAGIN_V4_SUBSTANTIVE_DETERMINISTIC",
            "RAGIN_PROVIDER_ENABLED": "0",
            "RAGIN_REQUIRE_PROVIDER": "0",
            "RAGIN_JEVI_ENABLED": "0",
            "RAGIN_LLM_BASE_URL": "http://127.0.0.1:9",
            "GATEWAY_URL": "http://127.0.0.1:9",
            "RAGIN_HISOKA_GATEWAY_URL": "http://127.0.0.1:9",
            "RAGIN_SESSION_DIR": str(out / "sessions"),
            "RAGIN_FIELD_EXPORT_DIR": str(out / "field_export"),
            "RAGIN_HOST_FICTION_PATH": str(out / "host_fiction.json"),
            "RAGIN_VERIFIER_PROFILE": "research_strict_v1",
            "RAGIN_VERIFIER_DEADLINE_S": "1.0",
            "RAGIN_LAYA_ENABLED": "0",
            "RAGIN_LAYA_EVAL_REQUIRE_REAL_MODEL": "0",
            "RAGIN_DON_RETRIEVAL_VERSION": "",
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "HTTP_PROXY": "",
            "HTTPS_PROXY": "",
            "ALL_PROXY": "",
            "http_proxy": "",
            "https_proxy": "",
            "all_proxy": "",
            "NO_PROXY": "127.0.0.1,localhost",
            "no_proxy": "127.0.0.1,localhost",
        }
    )
    # Defensive check: no allow-listed or explicitly set key may carry an
    # external provider/cloud credential.
    forbidden = ("OPENROUTER", "OPENAI", "ANTHROPIC", "AWS_", "AZURE_", "GOOGLE_", "HF_TOKEN")
    for key in list(env):
        if key.upper().startswith(forbidden):
            env.pop(key, None)
    return env


def listeners_on(port: int) -> list[str]:
    proc = run_capture(["ss", "-ltn"], check=False)
    rows = []
    for line in proc.stdout.decode(errors="replace").splitlines():
        if f":{port} " in line or line.rstrip().endswith(f":{port}"):
            rows.append(line.strip())
    return rows


def is_loopback_only(rows: list[str], port: int) -> bool:
    if not rows:
        return False
    for row in rows:
        fields = row.split()
        if len(fields) < 4:
            return False
        local = fields[3]
        if not local.startswith(("127.0.0.1:", "[::1]:")):
            return False
        if not local.endswith(f":{port}"):
            return False
    return True


def classify_frames(raw: bytes, commands: list[str]) -> list[dict[str, Any]]:
    """Tag terminal lines without discarding bytes."""
    frames: list[dict[str, Any]] = []
    for index, line in enumerate(raw.split(b"\n")):
        stripped = line.rstrip(b"\r")
        text = stripped.decode("utf-8", errors="replace")
        lowered = text.strip().lower()
        if not text.strip():
            kind = "blank"
        elif lowered in {command.lower() for command in commands}:
            kind = "echo"
        elif PROMPT_RE.match(text.strip()):
            kind = "prompt_echo" if any(text.strip().endswith(command) for command in commands) else "prompt"
        elif "password:" in lowered or "login as" in lowered:
            kind = "auth"
        else:
            kind = "answer"
        frames.append(
            {
                "line_index": index,
                "kind": kind,
                "bytes": len(line),
                "sha256": sha_bytes(line),
                "text": text,
            }
        )
    return frames


def _find_first(raw: bytes, variants: list[bytes], start: int, end: int | None = None) -> tuple[int, bytes]:
    limit = len(raw) if end is None else min(end, len(raw))
    for variant in variants:
        offset = raw.find(variant, start, limit)
        if offset >= 0:
            return offset, variant
    return -1, b""


def match_turns(raw: bytes, commands: list[str], responses: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Match each served text to its echo and answer, never to an echo alone.

    Echo offsets are located first so each answer search is bounded by the next
    echo. The answer must start strictly after the full echoed command and must
    match the complete served text, not a command substring.
    """
    echo_offsets: list[int] = []
    cursor = 0
    for command in commands:
        command_bytes = command.encode()
        offset, pattern = _find_first(raw, [command_bytes + b"\r\n", command_bytes + b"\n", command_bytes], cursor)
        if offset < 0:
            raise RuntimeError(f"terminal echo missing for command {command!r}")
        echo_offsets.append(offset)
        cursor = offset + len(pattern)

    matches: list[dict[str, Any]] = []
    for index, (command, response) in enumerate(zip(commands, responses, strict=True)):
        text = str(response.get("text", ""))
        if not text:
            raise RuntimeError(f"empty served text for command {command!r}")
        if text.strip() == command.strip():
            raise RuntimeError(f"served text for command {command!r} is indistinguishable from its echo")
        start = echo_offsets[index] + len(command)
        next_echo = echo_offsets[index + 1] if index + 1 < len(echo_offsets) else None
        variants = [text.replace("\n", "\r\n").encode(), text.encode()]
        answer_offset, pattern = _find_first(raw, variants, start, next_echo)
        if answer_offset < 0:
            raise RuntimeError(f"served text for command {command!r} not observed after its echo")
        if answer_offset <= echo_offsets[index]:
            raise RuntimeError(f"answer offset for command {command!r} is not after its echo")
        matches.append(
            {
                "turn": index,
                "command": command,
                "echo_offset": echo_offsets[index],
                "echo_end": echo_offsets[index] + len(command),
                "answer_offset": answer_offset,
                "answer_end": answer_offset + len(pattern),
                "served_text_sha256": sha_bytes(text.encode()),
                "wire_sha256": sha_bytes(pattern),
                "wire_framing": "crlf" if b"\r\n" in pattern else "lf",
                "observed_after_echo": answer_offset > echo_offsets[index],
            }
        )
    return matches


def _event_lists(events: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    for event in events:
        result.setdefault(str(event.get("event_type")), []).append(event)
    return result


def _session_event_file(session_dir: Path) -> Path | None:
    files = [path for path in sorted(session_dir.glob("*.jsonl")) if path.stat().st_size > 0]
    if not files:
        return None
    return max(files, key=lambda path: path.stat().st_size)


def run_ssh_session(ssh_port: int, commands: list[str], out: Path, label: str) -> tuple[bytes, bytes, int]:
    """Open one PTY SSH session, send commands, and preserve raw bytes.

    No assumption is made about what Cowrie prints when the backend returns a
    fail-closed transport error. The caller records the bytes and classifies
    them; a missing/short read is itself evidence.
    """
    ssh_cmd = [
        "sshpass", "-p", "x",
        "ssh", "-tt",
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        "-o", "PreferredAuthentications=password",
        "-o", "PubkeyAuthentication=no",
        "-o", "NumberOfPasswordPrompts=1",
        "-o", "ConnectTimeout=10",
        "-p", str(ssh_port), "root@127.0.0.1",
    ]
    client = subprocess.Popen(ssh_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert client.stdin is not None
    assert client.stdout is not None
    assert client.stderr is not None
    for command in commands:
        try:
            client.stdin.write((command + "\n").encode())
            client.stdin.flush()
        except BrokenPipeError:
            break
        time.sleep(4)
    # Close the PTY by EOF rather than typing ``exit``. ``exit`` would be
    # forwarded to the backend and produce an extra command/event.
    time.sleep(0.5)
    with contextlib.suppress(BrokenPipeError):
        client.stdin.close()
    try:
        client.wait(timeout=45)
    except subprocess.TimeoutExpired:
        client.kill()
        client.wait(timeout=10)
    stdout = client.stdout.read()
    stderr = client.stderr.read()
    (out / f"ssh_client.{label}.stdout").write_bytes(stdout)
    (out / f"ssh_client.{label}.stderr").write_bytes(stderr)
    (out / f"ssh_client.{label}.exit_code").write_text(str(client.returncode) + "\n", encoding="utf-8")
    return stdout, stderr, int(client.returncode)


def _all_session_events(session_dir: Path) -> tuple[list[dict[str, Any]], list[str], int]:
    """Load every session log, chronologically, without dropping a session.

    Positives and the negative session may land in one resumed file or in
    separate files. Sorting by the durable event timestamp makes the summary
    independent of that layout.
    """
    files = [path for path in sorted(session_dir.glob("*.jsonl")) if path.stat().st_size > 0]
    events: list[dict[str, Any]] = []
    parse_errors: list[str] = []
    for path in files:
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                parse_errors.append(f"{path.name}:{line_number}: {exc}")
                continue
            event["_session_file"] = path.name
            events.append(event)
    events.sort(key=lambda event: (str(event.get("timestamp") or ""), str(event.get("event_id") or "")))
    return events, parse_errors, len(files)


def main() -> int:
    parser = argparse.ArgumentParser()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    parser.add_argument("--out", type=Path, default=Path(f"/tmp/opencode/ragin_p0_loopback_trace_v1_{stamp}"))
    parser.add_argument("--keep", action="store_true", help="keep the Cowrie container for inspection")
    parser.add_argument(
        "--negative-command",
        default=NEGATIVE_COMMAND,
        help="one negative command in a separate SSH session",
    )
    args = parser.parse_args()

    out = args.out
    if out.exists():
        print(f"refusing to overwrite existing artifact dir: {out}", file=sys.stderr)
        return 2
    out.mkdir(parents=True)
    session_dir = out / "sessions"
    field_dir = out / "field_export"
    session_dir.mkdir()
    field_dir.mkdir()

    image = run_capture(["docker", "image", "inspect", COWRIE_IMAGE, "--format", "{{.Id}}"], check=False)
    if image.returncode != 0:
        print(f"image {COWRIE_IMAGE} not present locally; refusing to pull", file=sys.stderr)
        print(image.stderr.decode(errors="replace"), file=sys.stderr)
        return 2
    image_id = image.stdout.decode().strip()

    server_port, ssh_port = two_free_loopback_ports()
    container = f"ragin-p0-loopback-{os.getpid()}-{stamp}"
    run_id = f"{stamp}-{os.getpid()}"

    status = run_capture(["git", "status", "--porcelain=v1"], cwd=ROOT, check=False)
    status_text = status.stdout.decode(errors="replace")
    (out / "git_status.txt").write_text(status_text, encoding="utf-8")
    env = safe_env(out)

    prelaunch = {
        "schema": "ragin.p0.loopback_trace.prelaunch.v2",
        "run_id": run_id,
        "created_utc": stamp,
        "script_sha256": sha_file(Path(__file__).resolve()),
        "python": sys.version,
        "platform": platform.platform(),
        "git": {
            "head": run_capture(["git", "rev-parse", "HEAD"], cwd=ROOT, check=False).stdout.decode().strip(),
            "dirty": bool(status_text.strip()),
            "status_sha256": sha_bytes(status.stdout),
            "status_line_count": len(status_text.splitlines()),
            "status_file": "git_status.txt",
        },
        "source_hashes": {
            path: {
                "sha256": sha_file(ROOT / path),
                "bytes": (ROOT / path).stat().st_size if (ROOT / path).exists() else None,
            }
            for path in SOURCE_FILES
        },
        "image": {"name": COWRIE_IMAGE, "id": image_id},
        "ports": {"server": server_port, "ssh": ssh_port},
        "container": {"name": container, "network": "host"},
        "commands": EXPECTED_COMMANDS,
        "negative_command": args.negative_command,
        "verification_policy": {
            "profile": "research_strict_v1",
            "deadline_s": 1.0,
            "source": "env",
            "strict_contract": "exact finite command/claim allow-list",
        },
        "environment_policy": {
            "base": "allow-list, not os.environ.copy()",
            "inherited_credentials": "removed/never copied",
            "provider_enabled": False,
            "runtime_mode": "RAGIN_V4_SUBSTANTIVE_DETERMINISTIC",
            "rag_mode": "none",
            "laya_enabled": False,
            "proxy_vars": "cleared",
            "env_keys": sorted(env),
            "env_redacted": redact_env(env),
        },
        "derived_from": {
            "path": "scripts/run_p0_loopback_ssh_trace_v1.py",
            "sha256": sha_file(ROOT / "scripts/run_p0_loopback_ssh_trace_v1.py"),
        },
        "provenance": {
            "transport": "REAL_SSH_COWRIE_TO_SERVER_V2",
            "serving": "REAL_SANDBOX_HARNESS_VERIFIER",
            "generator": "DETERMINISTIC_STRATEGY_RUNTIME",
            "provider_backed": False,
            "llm_inference": "NOT_ESTABLISHED",
            "retrieval": "RAGIN_RAG_MODE=none (no dense/sparse index)",
            "note": "Deterministic runtime output is not a model result and does not establish LLM inference.",
        },
        "egress": {
            "host_network": True,
            "network_namespace_egress_block": False,
            "limitation": (
                "Docker host networking is used for loopback-only listeners; hard egress blocking "
                "would require host firewall/namespace work and is not claimed."
            ),
            "netns_attempt": "NOT_USED; exact blocker in trace_summary.isolation.netns",
        },
    }
    write_json(out / "run_manifest.prelaunch.json", prelaunch)

    server_log = out / "ragin_server.log"
    server_handle = server_log.open("wb")
    server = subprocess.Popen(
        [str(ROOT / ".venv/bin/python"), "-m", "ragin.server_v2", "--mode", "pipeline", "--port", str(server_port)],
        cwd=ROOT,
        env=env,
        stdout=server_handle,
        stderr=subprocess.STDOUT,
    )

    container_started = False
    container_id: str | None = None
    cowrie_logs: bytes = b""
    client_stdout = b""
    client_stderr = b""
    positive_exit_code: int | None = None
    negative_stdout = b""
    negative_stderr = b""
    negative_exit_code: int | None = None
    error: str | None = None
    result: dict[str, Any] = {
        "schema": "ragin.p0.loopback_ssh_trace.v2",
        "status": "FAIL",
        "run_id": run_id,
        "started_utc": stamp,
        "ports": {"server": server_port, "ssh": ssh_port},
        "container": {"name": container, "image": COWRIE_IMAGE, "image_id": image_id, "network": "host"},
        "isolation": {},
        "provenance": prelaunch["provenance"],
        "verification_policy": prelaunch["verification_policy"],
        "egress": prelaunch["egress"],
    }

    try:
        healthy = False
        for _ in range(160):
            if server.poll() is not None:
                raise RuntimeError(f"RAGIN server exited early: {server.returncode}")
            health = run_capture(["curl", "-sf", f"http://127.0.0.1:{server_port}/health"], timeout=3, check=False)
            if health.returncode == 0:
                healthy = True
                break
            time.sleep(0.25)
        if not healthy:
            raise RuntimeError("RAGIN health check timed out")

        docker_args = [
            "docker", "run", "-d", "--pull=never", "--name", container, "--network", "host",
            "-e", "COWRIE_HONEYPOT_BACKEND=llm",
            "-e", f"COWRIE_SSH_LISTEN_ENDPOINTS=tcp:{ssh_port}:interface=127.0.0.1",
            "-e", f"COWRIE_LLM_HOST=http://127.0.0.1:{server_port}",
            "-e", "COWRIE_LLM_PATH=/v1/chat/completions",
            "-e", f"COWRIE_LLM_API_KEY={API_KEY}",
            "-e", "COWRIE_LLM_MODEL=ragin-local",
            "-e", "COWRIE_LLM_MAX_TOKENS=120",
            "-e", "COWRIE_LLM_TEMPERATURE=0",
            "-e", "COWRIE_LLM_DEBUG=true",
            "-e", "HTTP_PROXY=", "-e", "HTTPS_PROXY=", "-e", "ALL_PROXY=",
            "-e", "http_proxy=", "-e", "https_proxy=", "-e", "all_proxy=",
            image_id,
        ]
        docker = run_capture(docker_args, check=False, timeout=60)
        if docker.returncode != 0:
            raise RuntimeError(f"docker run failed: {docker.stderr.decode(errors='replace')[:500]}")
        container_started = True
        container_id = docker.stdout.decode().strip()
        result["container"]["id"] = container_id

        ssh_up = False
        for _ in range(80):
            if is_loopback_only(listeners_on(ssh_port), ssh_port):
                ssh_up = True
                break
            time.sleep(0.25)
        if not ssh_up:
            raise RuntimeError(f"Cowrie did not bind 127.0.0.1:{ssh_port}")

        inspect = run_capture(["docker", "inspect", container, "--format", "{{json .Config.Env}}"], check=False)
        raw_env = json.loads(inspect.stdout.decode() or "[]")
        env_pairs = {}
        for item in raw_env:
            key, _, value = item.partition("=")
            env_pairs[key] = value
        result["container"]["runtime_env_redacted"] = redact_env(env_pairs)
        result["container"]["listen_endpoints"] = env_pairs.get("COWRIE_SSH_LISTEN_ENDPOINTS")
        result["isolation"] = {
            "server_bind": "127.0.0.1",
            "server_listeners": listeners_on(server_port),
            "server_loopback_only": is_loopback_only(listeners_on(server_port), server_port),
            "ssh_listeners": listeners_on(ssh_port),
            "ssh_loopback_only": is_loopback_only(listeners_on(ssh_port), ssh_port),
            "egress_policy": {
                "provider_enabled": False,
                "inference_endpoint": "http://127.0.0.1:9 (closed loopback port)",
                "runtime_mode": "RAGIN_V4_SUBSTANTIVE_DETERMINISTIC",
                "container_proxy_env": "cleared",
                "network_namespace_egress_block": False,
                "limitation": prelaunch["egress"]["limitation"],
            },
            "netns": {
                "used": False,
                "blocker": (
                    "ragin-python image lacks SSH/sshpass; Cowrie image has no /bin/sh or paramiko. "
                    "A shared --network none namespace would require injecting host binaries plus "
                    "loader/library mounts; host firewall changes were out of bounds."
                ),
            },
        }

        client_stdout, client_stderr, positive_exit_code = run_ssh_session(
            ssh_port, EXPECTED_COMMANDS, out, "positive"
        )
        frames = classify_frames(client_stdout, EXPECTED_COMMANDS)
        write_json(out / "terminal_frames.json", frames)

        # One separate SSH session with a predeclared command that has no
        # strict evidence contract. The server should fail closed (503); the
        # runner records what Cowrie/front-end actually does instead of
        # assuming the status or a synthetic shell error.
        negative_stdout, negative_stderr, negative_exit_code = run_ssh_session(
            ssh_port, [args.negative_command], out, "negative"
        )
        negative_frames = classify_frames(negative_stdout, [args.negative_command])
        write_json(out / "terminal_frames.negative.json", negative_frames)

        logs = run_capture(["docker", "logs", container], check=False, timeout=30)
        cowrie_logs = logs.stdout + logs.stderr
        (out / "cowrie.log").write_bytes(cowrie_logs)
    except Exception as exc:  # noqa: BLE001 - a failed attempt must be preserved
        error = f"{type(exc).__name__}: {exc}"
    finally:
        if container_started and not args.keep:
            if not cowrie_logs:
                logs = run_capture(["docker", "logs", container], check=False, timeout=30)
                cowrie_logs = logs.stdout + logs.stderr
                (out / "cowrie.log").write_bytes(cowrie_logs)
            subprocess.run(
                ["docker", "rm", "-f", container],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        server.send_signal(signal.SIGTERM)
        try:
            server.wait(timeout=20)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=5)
        server_handle.close()

    if error:
        result["error"] = error

    # ── Post-run evidence ──────────────────────────────────────────────────
    events, parse_errors, session_file_count = _all_session_events(session_dir)
    lists = _event_lists(events)
    inputs = lists.get("attacker_input", [])
    responses = lists.get("system_response", [])
    verifications = [event.get("data", {}) for event in lists.get("verification", [])]
    metrics = [event.get("data", {}) for event in lists.get("metric", [])]
    strategy_events = lists.get("strategy_update", [])
    response_generate_events = lists.get("response_generate", [])
    serving = [event.get("data", {}).get("serving_trace", {}) for event in response_generate_events]
    server_text = server_log.read_text(encoding="utf-8", errors="replace") if server_log.exists() else ""
    frames = (
        json.loads((out / "terminal_frames.json").read_text(encoding="utf-8"))
        if (out / "terminal_frames.json").exists()
        else []
    )
    negative_frames = (
        json.loads((out / "terminal_frames.negative.json").read_text(encoding="utf-8"))
        if (out / "terminal_frames.negative.json").exists()
        else []
    )
    client_stdout = (
        (out / "ssh_client.positive.stdout").read_bytes()
        if (out / "ssh_client.positive.stdout").exists()
        else b""
    )
    client_stderr = (
        (out / "ssh_client.positive.stderr").read_bytes()
        if (out / "ssh_client.positive.stderr").exists()
        else b""
    )
    negative_stdout = (
        (out / "ssh_client.negative.stdout").read_bytes()
        if (out / "ssh_client.negative.stdout").exists()
        else b""
    )
    negative_stderr = (
        (out / "ssh_client.negative.stderr").read_bytes()
        if (out / "ssh_client.negative.stderr").exists()
        else b""
    )
    positive_count = len(EXPECTED_COMMANDS)
    positive_inputs = inputs[:positive_count]
    positive_responses = responses[:positive_count]
    positive_verifications = verifications[:positive_count]
    positive_metrics = metrics[:positive_count]
    positive_strategy_events = strategy_events[:positive_count]
    positive_response_generates = response_generate_events[:positive_count]
    negative_inputs = inputs[positive_count:]
    negative_responses = responses[positive_count:]
    negative_verifications = verifications[positive_count:]
    negative_metrics = metrics[positive_count:]
    negative_response_generates = response_generate_events[positive_count:]

    terminal_matches: list[dict[str, Any]] = []
    terminal_error: str | None = None
    try:
        if len(positive_responses) == len(EXPECTED_COMMANDS):
            terminal_matches = match_turns(
                client_stdout,
                EXPECTED_COMMANDS,
                [event.get("data", {}) for event in positive_responses],
            )
    except Exception as exc:  # noqa: BLE001
        terminal_error = f"{type(exc).__name__}: {exc}"

    turn_checks: list[dict[str, Any]] = []
    if (
        len(positive_inputs)
        == len(positive_responses)
        == len(positive_verifications)
        == len(positive_metrics)
        == len(EXPECTED_COMMANDS)
    ):
        for index, expected in enumerate(EXPECTED_COMMANDS):
            input_data = positive_inputs[index].get("data", {})
            response_data = positive_responses[index].get("data", {})
            verification = positive_verifications[index]
            metric = positive_metrics[index]
            trace = metric.get("trace", {}) if isinstance(metric.get("trace"), dict) else {}
            served_text = response_data.get("text", "")
            served_sha = sha_bytes(str(served_text).encode())
            match = terminal_matches[index] if index < len(terminal_matches) else {}
            decision = trace.get("decision", {}) if isinstance(trace.get("decision"), dict) else {}
            strategy_event = (
                positive_strategy_events[index]
                if index < len(positive_strategy_events)
                else {}
            )
            checks = {
                "command_matches": input_data.get("command") == expected,
                "response_has_text": bool(served_text),
                "verification_passed": verification.get("passed") is True,
                "candidate_hash_agrees": (
                    verification.get("candidate_sha256") == trace.get("candidate_sha256")
                    and response_data.get("candidate_sha256") == verification.get("candidate_sha256")
                ),
                "served_hash_agrees": (
                    response_data.get("served_response_sha256") == served_sha
                    and verification.get("served_response_sha256") == served_sha
                    and trace.get("served_response_sha256") == served_sha
                    and trace.get("served_text_availability") == "REDACTED_MINIMIZED"
                ),
                "terminal_after_echo": match.get("observed_after_echo") is True,
                "terminal_text_hash_agrees": match.get("served_text_sha256") == served_sha,
                "decision_event_ref": (
                    bool(strategy_event)
                    and decision.get("event_id") == strategy_event.get("event_id")
                    and decision.get("availability") == "OBSERVED_EVENT_REFERENCE"
                ),
                "verification_profile_matches": (
                    verification.get("verification_policy", {}).get("profile")
                    == "research_strict_v1"
                ),
                "strict_verdict_supported": verification.get("strict_verdict") == "SUPPORTED",
                "deadline_enforced": verification.get("deadline_enforced") is True,
            }
            turn_checks.append(
                {
                    "turn": index,
                    "command": expected,
                    "checks": checks,
                    "event_ids": {
                        "input": positive_inputs[index].get("event_id"),
                        "response": positive_responses[index].get("event_id"),
                        "verification": (
                            positive_verifications[index].get("_event_id")
                            if index < len(positive_verifications)
                            and positive_verifications[index].get("_event_id")
                            else None
                        ),
                        "metric": (
                            positive_metrics[index].get("_event_id")
                            if index < len(positive_metrics)
                            and positive_metrics[index].get("_event_id")
                            else None
                        ),
                        "response_generate": (
                            positive_response_generates[index].get("event_id")
                            if index < len(positive_response_generates)
                            else None
                        ),
                        "strategy_update": strategy_event.get("event_id"),
                    },
                    "hashes": {
                        "candidate": verification.get("candidate_sha256"),
                        "served": served_sha,
                        "terminal_wire": match.get("wire_sha256"),
                    },
                    "terminal_offsets": {
                        "echo": match.get("echo_offset"),
                        "echo_end": match.get("echo_end"),
                        "answer": match.get("answer_offset"),
                        "answer_end": match.get("answer_end"),
                    },
                }
            )

    http_200_count = sum(
        1
        for line in server_text.splitlines()
        if "POST /v1/chat/completions" in line and " 200 " in line
    )
    http_503_count = sum(
        1
        for line in server_text.splitlines()
        if "POST /v1/chat/completions" in line and " 503 " in line
    )
    export_files = sorted(field_dir.glob("*.jsonl"))
    export_rows = [
        json.loads(line)
        for path in export_files
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    answer_texts = [frame["text"] for frame in frames if frame["kind"] == "answer"]
    negative_answer_texts = [
        frame["text"] for frame in negative_frames if frame["kind"] == "answer"
    ]
    negative_served_texts = [
        str(event.get("data", {}).get("text", "")) for event in negative_responses
    ]
    negative_fabricated_claim_texts = [
        text
        for text in negative_answer_texts + negative_served_texts
        if "root ALL" in text
        or "Defaults env_reset" in text
    ]
    negative_serving_traces = [
        event.get("data", {}).get("serving_trace", {})
        for event in negative_response_generates
        if isinstance(event.get("data", {}).get("serving_trace"), dict)
    ]
    negative_verifier_verdicts = [
        trace.get("verifier_verdict")
        for trace in negative_serving_traces
        if isinstance(trace.get("verifier_verdict"), dict)
    ]
    negative_strict_verdicts = [
        verdict.get("strict_verdict") for verdict in negative_verifier_verdicts
    ]
    negative_commit_events = [
        trace.get("commit_event") for trace in negative_serving_traces
    ]
    negative_commit_reasons = [
        trace.get("commit_reason") for trace in negative_serving_traces
    ]
    negative_input_commands = [
        event.get("data", {}).get("command") for event in negative_inputs
    ]
    negative_fail_closed = (
        len(negative_inputs) == 1
        and not negative_responses
        and bool(negative_verifier_verdicts)
        and len(negative_verifier_verdicts) == len(negative_serving_traces)
        and all(verdict.get("passed") is False for verdict in negative_verifier_verdicts)
        and any(
            verdict in {"UNSUPPORTED_COMMAND", "MALFORMED_INPUT"}
            for verdict in negative_strict_verdicts
        )
        and "accepted" not in negative_commit_events
    )
    result["terminal"] = {
        "stdout_sha256": sha_bytes(client_stdout),
        "stderr_sha256": sha_bytes(client_stderr),
        "stdout_bytes": len(client_stdout),
        "exit_code": positive_exit_code,
        "frame_counts": {
            kind: sum(1 for frame in frames if frame["kind"] == kind)
            for kind in {frame["kind"] for frame in frames}
        },
        "echo_frames": [frame for frame in frames if frame["kind"] in {"echo", "prompt_echo"}],
        "prompt_frames": [frame for frame in frames if frame["kind"] in {"prompt", "prompt_echo"}],
        "answer_frames": [frame for frame in frames if frame["kind"] == "answer"],
        "answer_texts": answer_texts,
        "turn_matches": terminal_matches,
        "match_error": terminal_error,
    }
    positive_verification_event_ids = [
        event.get("event_id") for event in lists.get("verification", [])[:positive_count]
    ]
    positive_metric_event_ids = [
        event.get("event_id") for event in lists.get("metric", [])[:positive_count]
    ]
    for index, check in enumerate(turn_checks):
        check["event_ids"]["verification"] = (
            positive_verification_event_ids[index]
            if index < len(positive_verification_event_ids)
            else None
        )
        check["event_ids"]["metric"] = (
            positive_metric_event_ids[index]
            if index < len(positive_metric_event_ids)
            else None
        )
    result["session"] = {
        "session_files": session_file_count,
        "parse_errors": parse_errors,
        "event_types": sorted(event_type for event_type in lists if event_type),
        "event_count": len(events),
        "attacker_input_count": len(inputs),
        "system_response_count": len(responses),
        "verification_count": len(verifications),
        "metric_count": len(metrics),
        "response_generate_count": len(lists.get("response_generate", [])),
        "strategy_update_count": len(strategy_events),
        "positive": {
            "attacker_input_count": len(positive_inputs),
            "system_response_count": len(positive_responses),
            "verification_count": len(positive_verifications),
            "metric_count": len(positive_metrics),
            "turn_checks": turn_checks,
        },
        "negative": {
            "input_count": len(negative_inputs),
            "input_commands": negative_input_commands,
            "system_response_count": len(negative_responses),
            "verification_count": len(negative_verifications),
            "strict_verdicts": negative_strict_verdicts,
            "metric_count": len(negative_metrics),
            "response_generate_count": len(negative_response_generates),
            "verification_passed_values": [
                verdict.get("passed") for verdict in negative_verifier_verdicts
            ],
            "commit_events": negative_commit_events,
            "commit_reasons": negative_commit_reasons,
            "serving_traces": negative_serving_traces,
        },
        "turn_checks": turn_checks,
        "latest_trace": positive_metrics[-1].get("trace") if positive_metrics else None,
        "serving_trace_sha256": sha_bytes(json.dumps(serving, sort_keys=True).encode()) if serving else None,
    }
    result["terminal"]["negative"] = {
        "command": args.negative_command,
        "stdout_sha256": sha_bytes(negative_stdout),
        "stderr_sha256": sha_bytes(negative_stderr),
        "stdout_bytes": len(negative_stdout),
        "stderr_bytes": len(negative_stderr),
        "exit_code": negative_exit_code,
        "frame_counts": {
            kind: sum(1 for frame in negative_frames if frame["kind"] == kind)
            for kind in {frame["kind"] for frame in negative_frames}
        },
        "answer_texts": negative_answer_texts,
        "served_texts": negative_served_texts,
        "fabricated_claim_texts": negative_fabricated_claim_texts,
        "observed": bool(negative_stdout or negative_stderr or negative_frames),
    }
    result["negative"] = {
        "command": args.negative_command,
        "http_503_count": http_503_count,
        "http_503_observed": http_503_count >= 1,
        "fail_closed": negative_fail_closed,
        "no_fabricated_claim": not negative_fabricated_claim_texts,
        "strict_verdicts": negative_strict_verdicts,
        "commit_events": negative_commit_events,
        "commit_reasons": negative_commit_reasons,
        "no_accepted_commit": "accepted" not in negative_commit_events,
        "terminal_bytes_observed": bool(negative_stdout or negative_stderr),
    }
    result["bridge"] = {
        "http_200_count": http_200_count,
        "http_200_observed": http_200_count >= len(EXPECTED_COMMANDS),
        "http_503_count": http_503_count,
        "http_503_observed": http_503_count >= 1,
        "export_rows": len(export_rows),
        "export_sha256": sha_bytes(json.dumps(export_rows, sort_keys=True).encode()) if export_rows else None,
    }

    turn_checks_ok = bool(turn_checks) and all(all(check["checks"].values()) for check in turn_checks)
    offsets = [
        (check["terminal_offsets"]["echo"], check["terminal_offsets"]["answer"])
        for check in turn_checks
        if check["terminal_offsets"]["echo"] is not None and check["terminal_offsets"]["answer"] is not None
    ]
    offsets_distinct = len(offsets) == len(EXPECTED_COMMANDS) and all(
        echo < answer for echo, answer in offsets
    ) and len({echo for echo, _ in offsets}) == len(offsets) and len({answer for _, answer in offsets}) == len(offsets)
    checks = {
        "no_runner_error": error is None,
        "cowrie_container_ran": container_started,
        "server_loopback_only": bool(result["isolation"].get("server_loopback_only")),
        "ssh_loopback_only": bool(result["isolation"].get("ssh_loopback_only")),
        "exact_three_positive_inputs": len(positive_inputs) == 3,
        "exact_three_positive_responses": len(positive_responses) == 3,
        "exact_three_positive_verifications": len(positive_verifications) == 3,
        "exact_three_positive_metrics": len(positive_metrics) == 3,
        "exact_three_positive_generations": len(positive_response_generates) == 3,
        "exact_three_positive_decisions": len(positive_strategy_events) == 3,
        "exact_one_negative_input": (
            len(negative_inputs) == 1
            and negative_input_commands == [args.negative_command]
        ),
        "negative_fail_closed": negative_fail_closed,
        "negative_no_accepted_commit": "accepted" not in negative_commit_events,
        "negative_http_503_observed": http_503_count >= 1,
        "negative_terminal_observed": bool(negative_stdout or negative_stderr or negative_frames),
        "negative_no_fabricated_claim": not negative_fabricated_claim_texts,
        "all_turns_consistent": turn_checks_ok,
        "strict_profile_observed": all(
            check["checks"].get("verification_profile_matches") is True
            and check["checks"].get("strict_verdict_supported") is True
            and check["checks"].get("deadline_enforced") is True
            for check in turn_checks
        ),
        "terminal_offsets_distinct_after_echo": offsets_distinct,
        "terminal_has_echo": any(frame["kind"] in {"echo", "prompt_echo"} for frame in frames),
        "terminal_has_prompt": any(frame["kind"] == "prompt" for frame in frames),
        "terminal_has_answers": bool(answer_texts),
        "bridge_http_200": result["bridge"]["http_200_observed"],
        "required_event_types": {
            "attacker_input",
            "classification",
            "verification",
            "system_response",
            "response_generate",
            "strategy_update",
            "metric",
        }.issubset(set(lists)),
    }
    result["checks"] = checks
    result["status"] = "PASS" if all(checks.values()) else "FAIL"
    result["finished_utc"] = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    write_json(out / "trace_summary.json", result)

    trace_manifest = {
        "schema": "ragin.p0.loopback_trace_manifest.v2",
        "status": "FROZEN",
        "run_id": run_id,
        "prelaunch_manifest": "run_manifest.prelaunch.json",
        "files": {
            str(path.relative_to(out)): sha_bytes(path.read_bytes())
            for path in sorted(out.rglob("*"))
            if path.is_file() and path.name != "trace_manifest.json"
        },
    }
    write_json(out / "trace_manifest.json", trace_manifest)
    print(json.dumps({"status": result["status"], "out": str(out), "checks": checks}, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
