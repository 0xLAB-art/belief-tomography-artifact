#!/usr/bin/env python3
"""Bounded Cowrie persona alignment proof (exactly two SSH sessions).

Question
--------
The P0 strict trace shows an outer Cowrie prompt ``root@svr04:/#`` while the
RAGIN arm answers as ``webapp@web-srv-01:~$``. This runner localises the
contradiction with the smallest supported experiment:

* one session against **native** Cowrie (``backend = shell``), configured only
  through Cowrie v3.1.1's documented knobs and a derived ``fs.pickle`` that
  adds ``/home/webapp``;
* one session against the **RAGIN** arm (``backend = llm``) with
  ``research_strict_v1`` verification still enabled and the provider disabled;
* the same five strict-profile commands in both sessions.

It records the full raw frontend bytes, the observed prompts/answers, and the
candidate/served hashes from the session log. It does not modify peer-owned
source, does not call a provider, and does not claim model inference.

Bounded sequence: 2 SSH sessions x 5 commands (limit: 2 sessions / 6 commands).

Usage:
    .venv/bin/python scripts/prove_cowrie_persona_alignment_v1.py \
        [--out DIR] [--keep]
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import pickle
import platform
import re
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from run_p0_loopback_ssh_trace_v2 import (  # noqa: E402
    _all_session_events,
    free_loopback_port,
    is_loopback_only,
    listeners_on,
    redact_env,
    safe_env,
    sha_bytes,
    sha_file,
    write_json,
)

IMAGE_ID = "sha256:710f1e4601a663ac8591f58a42b44e4cd3b7ea170c7e6cdb9e54c430a30cd459"
IMAGE_SHORT = "cowrie/cowrie:latest"
LOCAL_API_KEY = "p0-loopback-local-key"
IMAGE_PICKLE_PATH = "/cowrie/cowrie-git/src/cowrie/data/fs.pickle"
BASE_PICKLE_SHA256 = "c54b9d6d550db961fb003cd94760918e2dce36d87632b3cfcb1205665731f941"
PERSONA_DIR = ROOT / "configs/ablation/persona_lab_v1"
HOST_FICTION_SOURCE = ROOT / "data/host_fiction.json"
PYTHON_IN_IMAGE = "/cowrie/cowrie-env/bin/python3"
CONTAINER_PREFIX = "ragin-persona-lab"

COMMANDS = ["whoami", "id", "uname -a", "hostname", "cat /etc/os-release"]
MAX_SESSIONS = 2
MAX_COMMANDS = 6

PERSONA: dict[str, Any] = json.loads((PERSONA_DIR / "persona.json").read_text(encoding="utf-8"))
USER = str(PERSONA["user"])
HOST = str(PERSONA["host"])
UID = int(PERSONA["uid"])
GID = int(PERSONA["gid"])
HOMEDIR = str(PERSONA["home"])
KERNEL = str(PERSONA["kernel"])
OS_RELEASE_LINES = [
    'PRETTY_NAME="Ubuntu 22.04.3 LTS"',
    'NAME="Ubuntu"',
    'VERSION_ID="22.04"',
    'VERSION="22.04.3 LTS (Jammy Jellyfish)"',
    "ID=ubuntu",
]
AUX = ",".join(f"{g['gid']}({g['name']})" for g in PERSONA["aux_groups"])
DECLARED_ID_LINE = f"uid={UID}({USER}) gid={GID}({USER}) groups={GID}({USER}),{AUX}"
NATIVE_ID_LINE = f"uid={UID}({USER}) gid={GID}({USER}) groups={GID}({USER})"
FULL_UNAME = f"Linux {HOST} {KERNEL} #167-Ubuntu SMP x86_64 GNU/Linux"
NATIVE_PROMPT = f"{USER}@{HOST}:~$ "
RAGIN_PROMPT = f"{USER}@{HOST}:/$ "

EXPECTED: dict[str, dict[str, list[str]]] = {
    "native": {
        "whoami": [USER],
        "id": [NATIVE_ID_LINE],
        "uname -a": [FULL_UNAME],
        "hostname": [HOST],
        "cat /etc/os-release": list(OS_RELEASE_LINES),
    },
    "ragin": {
        "whoami": [USER],
        "id": [DECLARED_ID_LINE],
        "uname -a": [FULL_UNAME],
        # Strict verification is expected to fail closed on both of these;
        # the observation (not this expectation) is authoritative.
        "hostname": [],
        "cat /etc/os-release": [],
    },
}

PROMPT_RE = re.compile(
    r"^(?P<prefix>[A-Za-z0-9_.-]+@[A-Za-z0-9_.-]+:[^$#]*[$#] ?)(?P<cmd>.*)$"
)
ANSI_CSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


def normalize_terminal_line(raw: bytes) -> str:
    """Remove PTY presentation controls while retaining raw bytes on disk."""
    text = raw.rstrip(b"\r").decode("utf-8", errors="replace")
    return ANSI_CSI_RE.sub("", text)


# ── Fixture build ────────────────────────────────────────────────────────────


def extract_base_pickle(out: Path) -> bytes:
    """Read the bundled fs.pickle from the pinned image, never from a tag."""
    proc = subprocess.run(
        [
            "docker", "run", "--rm", "--pull=never", "--entrypoint", PYTHON_IN_IMAGE,
            IMAGE_ID, "-c",
            f"import sys;sys.stdout.buffer.write(open({IMAGE_PICKLE_PATH!r},'rb').read())",
        ],
        capture_output=True,
        timeout=120,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"could not read base fs.pickle: {proc.stderr.decode(errors='replace')[:400]}")
    data = proc.stdout
    (out / "fs.base.pickle").write_bytes(data)
    if sha_bytes(data) != BASE_PICKLE_SHA256:
        raise RuntimeError(
            f"base fs.pickle sha256 mismatch: {sha_bytes(data)} != {BASE_PICKLE_SHA256}"
        )
    return data


def _find_node(tree: list[Any], path: str) -> list[Any] | None:
    node = tree
    for part in [p for p in path.split("/") if p]:
        if node[1] != 1:
            return None
        match = [child for child in node[7] if child[0] == part]
        if not match:
            return None
        node = match[0]
    return node


def build_derived_pickle(base_bytes: bytes) -> bytes:
    """Add /home/webapp and drop /home/phil; no handler or source change."""
    tree = pickle.loads(base_bytes)  # noqa: S301 - trusted, hash-pinned image data
    home = _find_node(tree, "/home")
    if home is None or home[1] != 1:
        raise RuntimeError("/home is not a directory in the pinned fs.pickle")
    home[7] = [child for child in home[7] if child[0] != "phil"]
    if not any(child[0] == "webapp" for child in home[7]):
        home[7].append(["webapp", 1, UID, GID, 4096, 16877, 1706476800, [], None, None])
    webapp = _find_node(tree, HOMEDIR)
    if webapp is None or webapp[1] != 1:
        raise RuntimeError(f"derived fs.pickle is missing {HOMEDIR}")
    return pickle.dumps(tree, protocol=4)


def build_bundle(out: Path) -> dict[str, Any]:
    bundle = out / "bundle"
    etc = bundle / "etc"
    honeyfs = bundle / "honeyfs"
    if bundle.exists():
        shutil.rmtree(bundle)
    etc.mkdir(parents=True)
    shutil.copytree(PERSONA_DIR / "cowrie/honeyfs", honeyfs)
    shutil.copyfile(PERSONA_DIR / "cowrie/etc/cowrie.cfg", etc / "cowrie.cfg")
    shutil.copyfile(PERSONA_DIR / "cowrie/etc/userdb.txt", etc / "userdb.txt")
    base = extract_base_pickle(out)
    derived = build_derived_pickle(base)
    (bundle / "fs.pickle").write_bytes(derived)
    shutil.copyfile(HOST_FICTION_SOURCE, out / "host_fiction.json")
    files = {
        str(path.relative_to(out)): sha_bytes(path.read_bytes())
        for path in sorted(bundle.rglob("*"))
        if path.is_file()
    }
    files["host_fiction.preflight.json"] = sha_bytes((out / "host_fiction.json").read_bytes())
    return {
        "bundle": str(bundle),
        "files_sha256": files,
        "base_pickle_sha256": sha_bytes(base),
        "derived_pickle_sha256": sha_bytes(derived),
    }


# ── Container orchestration ─────────────────────────────────────────────────


def start_container(
    name: str,
    bundle: Path,
    ssh_port: int,
    telnet_port: int,
    backend: str,
    extra_env: dict[str, str],
) -> str:
    # Docker interprets a relative ``-v`` source as a named volume.  Proof
    # artifacts are intentionally allowed to be requested with a relative
    # --out path, so resolve the fixture before crossing the Docker boundary.
    bundle = bundle.resolve()
    args = [
        "docker", "run", "-d", "--pull=never", "--name", name, "--network", "host",
        "-v", f"{bundle}:/cowrie-persona:ro",
        "-v", f"{bundle / 'etc'}:/cowrie/cowrie-git/etc:ro",
        "-e", f"COWRIE_HONEYPOT_BACKEND={backend}",
        "-e", f"COWRIE_SSH_LISTEN_ENDPOINTS=tcp:{ssh_port}:interface=127.0.0.1",
        "-e", f"COWRIE_TELNET_LISTEN_ENDPOINTS=tcp:{telnet_port}:interface=127.0.0.1",
        "-e", "HTTP_PROXY=", "-e", "HTTPS_PROXY=", "-e", "ALL_PROXY=",
        "-e", "http_proxy=", "-e", "https_proxy=", "-e", "all_proxy=",
    ]
    for key, value in extra_env.items():
        args.extend(["-e", f"{key}={value}"])
    args.append(IMAGE_ID)
    proc = subprocess.run(args, capture_output=True, timeout=60, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"docker run {name} failed: {proc.stderr.decode(errors='replace')[:600]}")
    return proc.stdout.decode().strip()


def wait_for_listener(port: int, attempts: int = 120) -> bool:
    for _ in range(attempts):
        if is_loopback_only(listeners_on(port), port):
            return True
        time.sleep(0.25)
    return False


def run_ssh_session(port: int, commands: list[str], out: Path, label: str) -> dict[str, Any]:
    """One PTY session as the declared user; preserve every byte."""
    ssh_cmd = [
        "sshpass", "-p", "x",
        "ssh", "-tt",
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        "-o", "PreferredAuthentications=password",
        "-o", "PubkeyAuthentication=no",
        "-o", "NumberOfPasswordPrompts=1",
        "-o", "ConnectTimeout=10",
        "-p", str(port), f"{USER}@127.0.0.1",
    ]
    client = subprocess.Popen(
        ssh_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
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
    time.sleep(0.5)
    with contextlib.suppress(BrokenPipeError):
        client.stdin.close()
    try:
        client.wait(timeout=60)
    except subprocess.TimeoutExpired:
        client.kill()
        client.wait(timeout=10)
    stdout = client.stdout.read()
    stderr = client.stderr.read()
    (out / f"ssh_client.{label}.stdout").write_bytes(stdout)
    (out / f"ssh_client.{label}.stderr").write_bytes(stderr)
    (out / f"ssh_client.{label}.exit_code").write_text(str(client.returncode) + "\n", encoding="utf-8")
    return {
        "command": ssh_cmd,
        "exit_code": int(client.returncode),
        "stdout_sha256": sha_bytes(stdout),
        "stdout_bytes": len(stdout),
        "stderr_sha256": sha_bytes(stderr),
        "stderr_bytes": len(stderr),
    }


# ── Raw terminal parsing (primary observation) ──────────────────────────────


def parse_terminal(raw: bytes, commands: list[str]) -> dict[str, Any]:
    lines = [
        {"index": index, "text": normalize_terminal_line(line)}
        for index, line in enumerate(raw.split(b"\n"))
    ]
    prompts = []
    for line in lines:
        match = PROMPT_RE.match(line["text"])
        if match:
            prompts.append(
                {
                    "index": line["index"],
                    "prefix": match.group("prefix"),
                    "cmd": match.group("cmd"),
                    "line": line["text"],
                }
            )
    if not prompts:
        raise RuntimeError("no shell prompt observed in raw frontend bytes")

    turns = []
    cursor = 0
    for command in commands:
        found = None
        for position in range(cursor, len(prompts)):
            if prompts[position]["cmd"].strip() == command:
                found = position
                break
        if found is None:
            raise RuntimeError(f"prompt/echo for command {command!r} not observed")
        prompt = prompts[found]
        stop = prompts[found + 1]["index"] if found + 1 < len(prompts) else len(lines)
        answers = [
            lines[index]["text"]
            for index in range(prompt["index"] + 1, stop)
            if lines[index]["text"].strip() and not PROMPT_RE.match(lines[index]["text"])
        ]
        turns.append(
            {
                "command": command,
                "prompt_line": prompt["line"],
                "prompt_prefix": prompt["prefix"],
                "prompt_index": prompt["index"],
                "answer_lines": answers,
                "answer_span": [prompt["index"] + 1, stop],
            }
        )
        cursor = found + 1

    first_prompt = prompts[0]["index"]
    banners = [lines[i]["text"] for i in range(first_prompt) if lines[i]["text"].strip()]
    return {
        "banners": banners,
        "outer_prompts": [turn["prompt_prefix"] for turn in turns],
        "turns": turns,
        "line_count": len(lines),
        "stdout_sha256": sha_bytes(raw),
    }


def compare(arm: str, parsed: dict[str, Any]) -> tuple[list[dict[str, Any]], bool]:
    rows = []
    ok = True
    for turn in parsed["turns"]:
        expected = EXPECTED[arm][turn["command"]]
        matched = turn["answer_lines"] == expected
        ok = ok and matched
        rows.append(
            {
                "arm": arm,
                "command": turn["command"],
                "outer_prompt": turn["prompt_prefix"],
                "echo_line": turn["prompt_line"],
                "observed_answer_lines": turn["answer_lines"],
                "expected_answer_lines": expected,
                "matches_expectation": matched,
            }
        )
    return rows, ok


# ── Session-log cross-check (secondary) ─────────────────────────────────────


def crosscheck_events(session_dir: Path) -> dict[str, Any]:
    events, parse_errors, file_count = _all_session_events(session_dir)
    by_command: dict[str, dict[str, Any]] = {}
    current: str | None = None
    for event in events:
        kind = str(event.get("event_type"))
        data = event.get("data", {}) if isinstance(event.get("data"), dict) else {}
        if kind == "attacker_input":
            current = str(data.get("command") or "")
            by_command.setdefault(current, {})
        elif current is None:
            continue
        elif kind == "system_response":
            by_command[current]["served_text"] = data.get("text")
        elif kind == "verification":
            by_command[current]["verification"] = data
        elif kind == "response_generate":
            by_command[current]["response_generate"] = data
    rows = []
    for command, record in by_command.items():
        served = record.get("served_text")
        verification = record.get("verification", {})
        trace = record.get("response_generate", {}).get("serving_trace", {})
        trace = trace if isinstance(trace, dict) else {}
        rows.append(
            {
                "command": command,
                "served_text_sha256": sha_bytes(served.encode()) if isinstance(served, str) else None,
                "candidate_sha256": verification.get("candidate_sha256"),
                "verification_served_sha256": verification.get("served_response_sha256"),
                "trace_served_sha256": trace.get("served_response_sha256"),
                "candidate_equals_served": (
                    isinstance(served, str)
                    and verification.get("candidate_sha256") == sha_bytes(served.encode())
                    and trace.get("served_response_sha256") == sha_bytes(served.encode())
                ),
                "passed": verification.get("passed"),
                "strict_verdict": verification.get("strict_verdict"),
                "strict_reason": verification.get("strict_reason"),
                "commit_event": trace.get("commit_event"),
                "commit_reason": trace.get("commit_reason"),
            }
        )
    return {
        "session_files": file_count,
        "event_count": len(events),
        "parse_errors": parse_errors,
        "rows": rows,
    }


# ── Main ────────────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    parser.add_argument(
        "--out", type=Path, default=ROOT / f"docs/research/persona_alignment_{stamp}"
    )
    parser.add_argument("--keep", action="store_true", help="keep the two owned containers")
    parser.add_argument(
        "--native-evidence", type=Path,
        help="reuse a prior native-arm artifact and run only the remaining RAGIN SSH session",
    )
    args = parser.parse_args()

    out: Path = args.out
    if out.exists():
        print(f"refusing to overwrite existing artifact dir: {out}", file=sys.stderr)
        return 2
    out.mkdir(parents=True)
    (out / "sessions").mkdir()

    run_id = f"{stamp}-{os.getpid()}"
    server_port, native_port, ragin_port, native_telnet, ragin_telnet = _five_free_ports()
    native_name = f"{CONTAINER_PREFIX}-native-{run_id}"
    ragin_name = f"{CONTAINER_PREFIX}-ragin-{run_id}"

    git_status = subprocess.run(
        ["git", "status", "--porcelain=v1"], cwd=ROOT, capture_output=True, check=False
    )
    status_text = git_status.stdout.decode(errors="replace")
    (out / "git_status.txt").write_text(status_text, encoding="utf-8")

    image = subprocess.run(
        ["docker", "image", "inspect", IMAGE_ID, "--format", "{{json .Config}}"],
        capture_output=True, check=False,
    )
    if image.returncode != 0:
        print("pinned image ID not present locally; refusing to pull", file=sys.stderr)
        return 2
    image_config = json.loads(image.stdout.decode())

    bundle_info: dict[str, Any] = {}
    error: str | None = None
    server = None
    server_handle = None
    containers: list[str] = []
    logs: dict[str, bytes] = {}
    native_run: dict[str, Any] | None = None
    ragin_run: dict[str, Any] | None = None
    native_parsed: dict[str, Any] | None = None
    ragin_parsed: dict[str, Any] | None = None
    native_rows: list[dict[str, Any]] = []
    ragin_rows: list[dict[str, Any]] = []
    native_ok = False
    ragin_ok = False

    prelaunch: dict[str, Any] = {
        "schema": "ragin.persona_alignment.proof.v1",
        "run_id": run_id,
        "created_utc": stamp,
        "script_sha256": sha_file(Path(__file__).resolve()),
        "python": sys.version,
        "platform": platform.platform(),
        "git": {
            "head": subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, check=False
            ).stdout.decode().strip(),
            "dirty": bool(status_text.strip()),
            "status_sha256": sha_bytes(git_status.stdout),
            "status_line_count": len(status_text.splitlines()),
        },
        "image": {
            "name": IMAGE_SHORT,
            "id": IMAGE_ID,
            "labels": image_config.get("Labels", {}),
            "user": image_config.get("User"),
            "entrypoint": image_config.get("Entrypoint"),
            "cmd": image_config.get("Cmd"),
        },
        "fixtures": {
            "persona_json_sha256": sha_file(PERSONA_DIR / "persona.json"),
            "cowrie_cfg_sha256": sha_file(PERSONA_DIR / "cowrie/etc/cowrie.cfg"),
            "userdb_sha256": sha_file(PERSONA_DIR / "cowrie/etc/userdb.txt"),
            "honeyfs": {
                str(path.relative_to(PERSONA_DIR)): sha_bytes(path.read_bytes())
                for path in sorted((PERSONA_DIR / "cowrie/honeyfs").rglob("*"))
                if path.is_file()
            },
        },
        "bounded_sequence": {
            "sessions": MAX_SESSIONS,
            "commands_per_session": len(COMMANDS),
            "command_limit_per_session": MAX_COMMANDS,
            "commands": COMMANDS,
        },
        "ports": {
            "server": server_port,
            "native_ssh": native_port,
            "ragin_ssh": ragin_port,
            "native_telnet": native_telnet,
            "ragin_telnet": ragin_telnet,
        },
        "verification_policy": {
            "ragin_profile": "research_strict_v1",
            "native_profile": "none (native shell, no RAGIN verifier)",
        },
        "provenance": {
            "transport": "REAL_SSH_LOOPBACK",
            "native": "COWRIE_V3_1_1_UNMODIFIED_HANDLERS",
            "ragin": "DETERMINISTIC_STRATEGY_RUNTIME_STRICT_VERIFIER",
            "provider_backed": False,
            "llm_inference": "NOT_ESTABLISHED",
            "note": "Deterministic output is not a model result.",
        },
    }

    try:
        bundle_info = build_bundle(out)
        prelaunch["fixtures"]["built_bundle"] = bundle_info
        env = safe_env(out)
        write_json(out / "run_manifest.prelaunch.json", prelaunch)

        # Native arm first: it needs no server.  ``--native-evidence`` is a
        # bounded continuation after an interrupted proof; it avoids opening
        # a third SSH session while retaining the original raw bytes.
        if args.native_evidence:
            prior = args.native_evidence.resolve()
            if not (prior / "ssh_client.native.stdout").is_file():
                raise RuntimeError(f"native evidence missing raw stdout: {prior}")
            for name in ("ssh_client.native.stdout", "ssh_client.native.stderr", "ssh_client.native.exit_code"):
                source = prior / name
                if source.is_file():
                    shutil.copyfile(source, out / name)
            prior_summary = prior / "summary.json"
            if prior_summary.is_file():
                prior_data = json.loads(prior_summary.read_text(encoding="utf-8"))
                native_run = prior_data.get("outcome", {}).get("native_session")
            prelaunch["bounded_sequence"]["native_evidence_reused"] = str(prior)
        else:
            start_container(
                native_name, Path(bundle_info["bundle"]), native_port, native_telnet,
                "shell", {},
            )
            containers.append(native_name)
            if not wait_for_listener(native_port):
                raise RuntimeError(f"native Cowrie did not bind 127.0.0.1:{native_port}")
            native_run = run_ssh_session(native_port, COMMANDS, out, "native")
        native_parsed = parse_terminal(
            (out / "ssh_client.native.stdout").read_bytes(), COMMANDS
        )
        write_json(out / "raw_terminal.native.json", native_parsed)
        native_rows, native_ok = compare("native", native_parsed)

        # RAGIN arm: deterministic server, strict verification, provider off.
        server_log = out / "ragin_server.log"
        server_handle = server_log.open("wb")
        server = subprocess.Popen(
            [
                str(ROOT / ".venv/bin/python"), "-m", "ragin.server_v2",
                "--mode", "pipeline", "--port", str(server_port),
            ],
            cwd=ROOT, env=env, stdout=server_handle, stderr=subprocess.STDOUT,
        )
        healthy = False
        for _ in range(240):
            if server.poll() is not None:
                raise RuntimeError(f"RAGIN server exited early: {server.returncode}")
            probe = subprocess.run(
                ["curl", "-sf", f"http://127.0.0.1:{server_port}/health"],
                capture_output=True, timeout=3, check=False,
            )
            if probe.returncode == 0:
                healthy = True
                break
            time.sleep(0.25)
        if not healthy:
            raise RuntimeError("RAGIN health check timed out")

        start_container(
            ragin_name, Path(bundle_info["bundle"]), ragin_port, ragin_telnet,
            "llm",
            {
                "COWRIE_LLM_HOST": f"http://127.0.0.1:{server_port}",
                "COWRIE_LLM_PATH": "/v1/chat/completions",
                # Must match the loopback-only API_KEY installed by safe_env;
                # a different fixture key produces a deterministic 401 and
                # an empty shell response even though the listener is live.
                "COWRIE_LLM_API_KEY": LOCAL_API_KEY,
                "COWRIE_LLM_MODEL": "ragin-local",
                "COWRIE_LLM_MAX_TOKENS": "120",
                "COWRIE_LLM_TEMPERATURE": "0",
                "COWRIE_LLM_DEBUG": "true",
            },
        )
        containers.append(ragin_name)
        if not wait_for_listener(ragin_port):
            raise RuntimeError(f"RAGIN Cowrie did not bind 127.0.0.1:{ragin_port}")
        ragin_run = run_ssh_session(ragin_port, COMMANDS, out, "ragin")
        ragin_parsed = parse_terminal(
            (out / "ssh_client.ragin.stdout").read_bytes(), COMMANDS
        )
        write_json(out / "raw_terminal.ragin.json", ragin_parsed)
        ragin_rows, ragin_ok = compare("ragin", ragin_parsed)
    except Exception as exc:  # noqa: BLE001 - failed attempt must be preserved
        error = f"{type(exc).__name__}: {exc}"
    finally:
        for name in containers:
            proc = subprocess.run(
                ["docker", "logs", name], capture_output=True, timeout=30, check=False
            )
            logs[name] = proc.stdout + proc.stderr
            (out / f"cowrie.{'native' if name == native_name else 'ragin'}.log").write_bytes(logs[name])
        if not args.keep:
            for name in containers:
                subprocess.run(
                    ["docker", "rm", "-f", name], stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL, check=False,
                )
        if server is not None:
            server.send_signal(signal.SIGTERM)
            try:
                server.wait(timeout=20)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=5)
        if server_handle is not None:
            server_handle.close()

    # ── Observed result ────────────────────────────────────────────────────
    match_table = native_rows + ragin_rows
    write_json(out / "match_table.json", match_table)

    json_crosscheck = crosscheck_events(out / "sessions")
    write_json(out / "json_crosscheck.json", json_crosscheck)

    native_prompts = native_parsed["outer_prompts"] if native_parsed else []
    ragin_prompts = ragin_parsed["outer_prompts"] if ragin_parsed else []
    native_prompt_ok = bool(native_prompts) and all(p == NATIVE_PROMPT for p in native_prompts)
    ragin_prompt_ok = bool(ragin_prompts) and all(p == RAGIN_PROMPT for p in ragin_prompts)

    blockers: list[dict[str, Any]] = []
    if native_parsed and ragin_parsed:
        if native_prompts != ragin_prompts:
            blockers.append(
                {
                    "id": "prompt_cwd",
                    "native": native_prompts[0] if native_prompts else None,
                    "ragin": ragin_prompts[0] if ragin_prompts else None,
                    "cause": (
                        "cowrie/llm/protocol.py hardcodes self.cwd = '/' (line 104) while "
                        "cowrie/shell/honeypot.py derives cwd from the passwd home and "
                        "renders '~' when cwd == home (lines 1115-1120)."
                    ),
                    "owner": "shared RAGIN/Cowrie LLM protocol (peer-owned)",
                }
            )
        native_id = next(
            (t["answer_lines"] for t in native_parsed["turns"] if t["command"] == "id"), []
        )
        ragin_id = next(
            (t["answer_lines"] for t in ragin_parsed["turns"] if t["command"] == "id"), []
        )
        if native_id != ragin_id:
            blockers.append(
                {
                    "id": "id_supplementary_groups",
                    "native": native_id,
                    "ragin": ragin_id,
                    "cause": (
                        "cowrie/commands/base.py Command_id prints only the primary gid; "
                        "the declared persona and RAGIN _id_line include 4(adm),999(docker)."
                    ),
                    "owner": "native Cowrie handler (would require a handler change)",
                }
            )
        for command in COMMANDS:
            native_turn = next(t for t in native_parsed["turns"] if t["command"] == command)
            ragin_turn = next(t for t in ragin_parsed["turns"] if t["command"] == command)
            if native_turn["answer_lines"] != ragin_turn["answer_lines"] and command not in {"id"}:
                blockers.append(
                        {
                            "id": f"answer:{command}",
                            "native": native_turn["answer_lines"],
                            "ragin": ragin_turn["answer_lines"],
                            "cause": (
                                "native serves the supported command; the RAGIN deterministic "
                                "generator has no strict-verifiable transcript for it (or, for "
                                "os-release, its template adds a second prompt echo and uname -r)."
                            ),
                            "owner": "RAGIN deterministic generator/template (peer-owned)",
                        }
                    )

    status = "FAIL"
    if (
        error is None
        and native_ok
        and ragin_ok
        and native_prompt_ok
        and ragin_prompt_ok
    ):
        status = "PARTIAL_ALIGNMENT" if blockers else "PASS"

    summary = {
        "schema": "ragin.persona_alignment.result.v1",
        "status": status,
        "run_id": run_id,
        "error": error,
        "bounded_sequence": {
            "sessions": 2 if (native_parsed and ragin_parsed) else (1 if native_parsed else 0),
            "session_limit": MAX_SESSIONS,
            "commands_per_session": len(COMMANDS),
            "command_limit": MAX_COMMANDS,
        },
        "outcome": {
            "native_session": native_run,
            "ragin_session": ragin_run,
            "native_prompt_ok": native_prompt_ok,
            "ragin_prompt_ok": ragin_prompt_ok,
            "native_answers_match_expected": native_ok,
            "ragin_answers_match_expected": ragin_ok,
            "native_outer_prompts": native_prompts,
            "ragin_outer_prompts": ragin_prompts,
            "native_banners": native_parsed["banners"] if native_parsed else [],
            "ragin_banners": ragin_parsed["banners"] if ragin_parsed else [],
        },
        "blockers": blockers,
        "json_crosscheck": json_crosscheck,
        "artifacts": {
            "native_raw_stdout": "ssh_client.native.stdout",
            "ragin_raw_stdout": "ssh_client.ragin.stdout",
            "native_terminal": "raw_terminal.native.json",
            "ragin_terminal": "raw_terminal.ragin.json",
            "match_table": "match_table.json",
            "crosscheck": "json_crosscheck.json",
        },
        "provenance": prelaunch["provenance"],
        "environment_policy": {
            "provider_enabled": False,
            "gateway": "http://127.0.0.1:9 (closed loopback)",
            "proxy_vars": "cleared",
            "env_keys": sorted(safe_env(out)),
            "env_redacted": redact_env(safe_env(out)),
        },
    }
    write_json(out / "summary.json", summary)

    manifest = {
        "schema": "ragin.persona_alignment.manifest.v1",
        "status": "FROZEN",
        "run_id": run_id,
        "files": {
            str(path.relative_to(out)): sha_bytes(path.read_bytes())
            for path in sorted(out.rglob("*"))
            if path.is_file() and path.name != "trace_manifest.json"
        },
    }
    write_json(out / "trace_manifest.json", manifest)
    print(json.dumps({"status": status, "out": str(out), "blockers": blockers}, indent=2))
    return 0 if status in {"PASS", "PARTIAL_ALIGNMENT"} else 1


def _five_free_ports() -> tuple[int, int, int, int, int]:
    ports: list[int] = []
    while len(ports) < 5:
        port = free_loopback_port()
        if port not in ports:
            ports.append(port)
    return tuple(ports)  # type: ignore[return-value]


if __name__ == "__main__":
    raise SystemExit(main())
