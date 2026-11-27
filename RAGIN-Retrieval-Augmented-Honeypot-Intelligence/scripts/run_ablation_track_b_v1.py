#!/usr/bin/env python3
"""Track B closed-loop runner (B0 native Cowrie development smoke).

The runner launches a real, cached Cowrie container on 127.0.0.1, opens a real
SSH session and lets a deterministic ``SCRIPTED_POLICY`` choose each next
command from the *served output* of the previous turn. It is explicitly a
``TEST_ONLY`` integration control:

* it is not an ablation, not a B0-B3 comparison, and not LLM inference;
* it never pulls an image, never binds a public interface, never starts a
  provider or a full campaign;
* it writes a fresh unique artifact directory and refuses to overwrite it.

B1-B3 are refused until the run contract is execution-ready. Use
``--dry-run`` to inspect the wiring without starting Docker.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import re
import select
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ragin.evaluation.ablation_contract import (  # noqa: E402
    DESIGN_INVALID,
    ContractRefusal,
    assert_execution_ready,
    load_contract,
    sha256_file,
    validate_design,
)
from ragin.evaluation.attacker_policies import PolicyUnavailable, make_policy  # noqa: E402
from ragin.evaluation.closed_loop import SessionMeta, TransportError, run_session  # noqa: E402
from ragin.evaluation.records import validate_record  # noqa: E402

PROMPT_RE = re.compile(rb"[\w.-]+@[\w.-]+:[^\r\n]*[#$] ")
ANSI_RE = re.compile(rb"\x1b\[[0-9;?]*[A-Za-z]")


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def write_json(path: Path, value: Any) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def free_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def listeners_on(port: int) -> list[str]:
    proc = subprocess.run(["ss", "-ltn"], capture_output=True, text=True, check=False)
    return [
        line.strip()
        for line in proc.stdout.splitlines()
        if f":{port} " in line or line.rstrip().endswith(f":{port}")
    ]


def loopback_only(rows: list[str], port: int) -> bool:
    if not rows:
        return False
    for row in rows:
        fields = row.split()
        if len(fields) < 4:
            return False
        local = fields[3]
        if not local.startswith(("127.0.0.1:", "[::1]:")) or not local.endswith(f":{port}"):
            return False
    return True


class SshCowrieTransport:
    """Drive a real SSH PTY and return only the served text for each command."""

    def __init__(self, *, port: int, timeout: float = 20.0) -> None:
        self.port = port
        self.timeout = timeout
        self.process: subprocess.Popen[bytes] | None = None
        self.raw = bytearray()

    def start(self) -> None:
        command = [
            "sshpass",
            "-p",
            "x",
            "ssh",
            "-tt",
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "UserKnownHostsFile=/dev/null",
            "-o",
            "PreferredAuthentications=password",
            "-o",
            "PubkeyAuthentication=no",
            "-o",
            "NumberOfPasswordPrompts=1",
            "-o",
            "ConnectTimeout=10",
            "-p",
            str(self.port),
            "root@127.0.0.1",
        ]
        self.process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if self.process.stderr is not None:
            os.set_blocking(self.process.stderr.fileno(), False)
        self._read_until_prompt(timeout=self.timeout)

    def _drain_stderr(self, limit: int = 4096) -> bytes:
        if self.process is None or self.process.stderr is None:
            return b""
        fd = self.process.stderr.fileno()
        chunks: list[bytes] = []
        remaining = limit
        while remaining > 0:
            ready, _, _ = select.select([fd], [], [], 0)
            if not ready:
                break
            try:
                chunk = os.read(fd, min(1024, remaining))
            except (BlockingIOError, OSError):
                break
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        return b"".join(chunks)

    def _terminate(self) -> None:
        if self.process is None or self.process.poll() is not None:
            return
        try:
            self.process.terminate()
            self.process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            self.process.kill()
            with contextlib.suppress(subprocess.TimeoutExpired):
                self.process.wait(timeout=2)

    def _read_until_prompt(self, *, timeout: float) -> bytes:
        if self.process is None or self.process.stdout is None:
            raise TransportError("SSH process is not running")
        deadline = time.monotonic() + timeout
        buffer = bytearray()
        while time.monotonic() < deadline:
            remaining = max(0.0, deadline - time.monotonic())
            ready, _, _ = select.select([self.process.stdout], [], [], min(0.25, remaining))
            if not ready:
                if self.process.poll() is not None:
                    break
                continue
            chunk = os.read(self.process.stdout.fileno(), 4096)
            if not chunk:
                break
            self.raw.extend(chunk)
            buffer.extend(chunk)
            cleaned = ANSI_RE.sub(b"", bytes(buffer))
            if PROMPT_RE.search(cleaned):
                return bytes(buffer)
        stderr = self._drain_stderr()
        self._terminate()
        raise TransportError(
            f"timed out waiting for SSH prompt after {timeout}s ({len(buffer)} bytes, stderr={stderr[:120]!r})"
        )

    def execute(self, command: str) -> dict[str, Any]:
        if self.process is None or self.process.stdin is None:
            raise TransportError("SSH process is not running")
        started = time.monotonic()
        self.process.stdin.write((command + "\n").encode())
        self.process.stdin.flush()
        chunk = self._read_until_prompt(timeout=self.timeout)
        latency_ms = (time.monotonic() - started) * 1000.0
        cleaned = ANSI_RE.sub(b"", chunk).decode("utf-8", "replace").replace("\r\n", "\n").replace("\r", "")
        position = cleaned.find(command)
        if position < 0:
            served = cleaned
        else:
            newline = cleaned.find("\n", position)
            served = cleaned[newline + 1 :] if newline >= 0 else cleaned[position + len(command) :]
        served = PROMPT_RE.sub(b"", served.encode()).decode("utf-8", "replace").strip("\n")
        # A legitimate native command may produce no output (true, mkdir, a
        # redirect). Preserve it as an explicit EMPTY serve; never drop the turn
        # and never convert absence of output into a transport failure.
        empty = not bool(served.strip())
        return {
            "served_text": served,
            "serve_status": "EMPTY" if empty else "SERVED",
            "failure_reason": "native command produced no output (legitimate empty result)" if empty else None,
            "generation_kind": "NATIVE_SHELL",
            "decision_consumed": False,
            "arm_exposure": "OBSERVED",
            "model_exposure": {"observed": False},
            "verification": {"profile": "NATIVE_TRANSPORT_ONLY", "passed": True},
            "latency_ms": {"availability": "MEASURED", "value": latency_ms},
            "tokens_in": {"availability": "UNAVAILABLE"},
            "tokens_out": {"availability": "UNAVAILABLE"},
            "cost_usd": {"availability": "UNAVAILABLE"},
        }

    def close(self) -> None:
        if self.process is None:
            return
        if self.process.stdin is not None:
            with contextlib.suppress(OSError):
                self.process.stdin.close()
        try:
            self.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=5)


def _docker(args: list[str], *, timeout: int = 60) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["docker", *args], capture_output=True, text=True, check=False, timeout=timeout)


BASELINE_PROBES = (
    "id",
    "uname -a",
    "pwd",
    "hostname",
    "cat /etc/os-release 2>/dev/null | head -5",
    "getent passwd webapp 2>/dev/null || true",
)


def observe_b0_baseline(transport: Any) -> dict[str, Any]:
    """Observe the served native baseline instead of assuming JSON equality.

    This is a transport-only observation. It does not alter Cowrie, does not
    rewrite native commands and does not claim that default Cowrie identity
    matches the B1-B3 host fiction.
    """
    observed: dict[str, Any] = {}
    errors: list[str] = []
    for command in BASELINE_PROBES:
        try:
            response = transport.execute(command)
            text = str(response.get("served_text") or "")
            observed[command] = {
                "served_text": text[:1200],
                "served_sha256": sha_bytes(text.encode("utf-8")),
            }
        except Exception as exc:  # noqa: BLE001 - observation failure is evidence, not a reason to invent a value
            errors.append(f"{command}: {type(exc).__name__}: {exc}")
    return {
        "schema": "ragin.ablation.b0_baseline_observation.v1",
        "observed": observed,
        "errors": errors,
        "matched_to_b1_b3": False,
        "match_status": "NOT_ESTABLISHED",
        "reference": (
            "data/host_fiction.json (webapp uid 1001, web-srv-01, Ubuntu 22.04.3 LTS, "
            "kernel 5.15.0-91-generic)"
        ),
        "claim": "transport/control observation only; not a matched pilot and not H1 evidence",
        "note": (
            "Default Cowrie root/OS/kernel may differ from the pinned Hisoka webapp/Ubuntu host. "
            "Matching requires supported Cowrie persona/config fixtures and an explicit observed comparison."
        ),
    }


def check_b0_environment(contract: dict[str, Any], container: str) -> tuple[str, list[str]]:
    errors: list[str] = []
    image_id = contract["b0_native"]["image_id"]
    inspect = _docker(["image", "inspect", image_id, "--format", "{{.Id}}"])
    if inspect.returncode != 0 or inspect.stdout.strip() != image_id:
        errors.append(f"cached B0 image ID unavailable: {image_id}; refusing to pull")
    if _docker(["ps", "-a", "--filter", f"name=^{container}$", "--format", "{{.Names}}"]).stdout.strip():
        errors.append(f"container name already exists: {container}")
    return image_id, errors


def main() -> int:
    parser = argparse.ArgumentParser()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    parser.add_argument("--contract", type=Path, default=ROOT / "configs/ablation/eval_v1/run_contract_v1.json")
    parser.add_argument("--arm", default="B0", choices=["B0", "B1", "B2", "B3"])
    parser.add_argument("--scenario", default="dev-lab-recon-01")
    parser.add_argument("--profile", default="lab_recon_then_escalate_v1")
    parser.add_argument("--max-turns", type=int, default=4)
    parser.add_argument("--out", type=Path, default=Path(f"/tmp/opencode/ragin_ablation_track_b_{stamp}_{os.getpid()}"))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--i-understand-test-only", action="store_true")
    args = parser.parse_args()

    if args.max_turns < 1 or args.max_turns > 4:
        print("this development runner is bounded to <=4 turns", file=sys.stderr)
        return 2
    contract = load_contract(args.contract, repo_root=ROOT)
    design = validate_design(contract)
    if design.status == DESIGN_INVALID:
        print(json.dumps(design.to_dict(), indent=2), file=sys.stderr)
        return 3

    scenarios = json.loads(
        (ROOT / "configs/ablation/eval_v1/track_b_scenarios_v1.json").read_text(encoding="utf-8")
    )
    if args.scenario not in {item["scenario_id"] for item in scenarios["scenarios"]}:
        print(f"unknown development scenario: {args.scenario}", file=sys.stderr)
        return 2
    scenario_row = next(item for item in scenarios["scenarios"] if item["scenario_id"] == args.scenario)
    objective_turns = {
        int(turn) - 1
        for turn in set(scenario_row.get("objective_turns") or [])
        if int(turn) >= 1
    }
    try:
        policy = make_policy(args.profile)
    except PolicyUnavailable as exc:
        print(f"policy unavailable: {exc}", file=sys.stderr)
        return 2

    if args.arm != "B0":
        try:
            assert_execution_ready(contract, repo_root=ROOT)
        except ContractRefusal as exc:
            print(json.dumps(exc.report.to_dict(), indent=2, sort_keys=True), file=sys.stderr)
            return 2
        print("B1-B3 execution is not implemented in this development runner", file=sys.stderr)
        return 2

    if not args.i_understand_test_only and not args.dry_run:
        print(
            "refusing to run: this B0 native smoke is TEST_ONLY integration mechanics, not an ablation. "
            "Pass --i-understand-test-only.",
            file=sys.stderr,
        )
        return 2

    container = f"ragin-b0-trackb-{os.getpid()}-{stamp}"
    image_id, errors = check_b0_environment(contract, container)
    if args.dry_run:
        print(
            json.dumps(
                {
                    "mode": "DRY_RUN",
                    "arm": "B0",
                    "scenario": args.scenario,
                    "profile": args.profile,
                    "max_turns": args.max_turns,
                    "image_id": image_id,
                    "environment_errors": errors,
                    "claim": "TEST_ONLY_B0_NATIVE_INTEGRATION_SMOKE; not an ablation",
                },
                indent=2,
            )
        )
        return 0 if not errors else 2
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 2
    if args.out.exists():
        print(f"refusing to overwrite existing artifact directory: {args.out}", file=sys.stderr)
        return 2
    args.out.mkdir(parents=True)

    git_status = subprocess.run(
        ["git", "status", "--porcelain=v1"], cwd=ROOT, capture_output=True, text=True, check=False
    ).stdout
    ssh_port = free_loopback_port()
    prelaunch = {
        "schema": "ragin.ablation.track_b.prelaunch.v1",
        "created_utc": stamp,
        "runner_sha256": sha256_file(Path(__file__).resolve()),
        "contract_sha256": contract["_contract_sha256"],
        "scenario_file_sha256": sha256_file(ROOT / "configs/ablation/eval_v1/track_b_scenarios_v1.json"),
        "git": {
            "head": subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=False
            ).stdout.strip(),
            "dirty": bool(git_status.strip()),
            "status_sha256": sha_bytes(git_status.encode()),
        },
        "image": {"id": image_id, "pull": "never"},
        "b0_baseline": contract.get("b0_native", {}).get("baseline_identity", {}),
        "container": {"name": container, "network": "host"},
        "port": {"ssh": ssh_port, "host": "127.0.0.1"},
        "policy": {"profile_id": policy.policy_id, "kind": policy.kind},
        "provenance": {
            "transport": "REAL_SSH_NATIVE_COWRIE",
            "generator": "NATIVE_COWRIE_SHELL",
            "llm_inference": "NOT_ESTABLISHED",
            "retrieval": "NOT_APPLICABLE",
            "verification": "NATIVE_TRANSPORT_ONLY",
            "claim": "TEST_ONLY_B0_NATIVE_INTEGRATION_SMOKE",
        },
        "environment_policy": {
            "inherited_provider_credentials": "not passed to the container",
            "proxy_vars": "cleared in container",
            "public_listener": False,
        },
    }
    write_json(args.out / "run_manifest.prelaunch.json", prelaunch)

    container_started = False
    transport: SshCowrieTransport | None = None
    error: str | None = None
    record: dict[str, Any] | None = None
    baseline_observation: dict[str, Any] | None = None
    observed_listeners: list[str] = []
    post_cleanup_listeners: list[str] = []
    cleanup_true = False
    try:
        docker = _docker(
            [
                "run",
                "-d",
                "--pull=never",
                "--name",
                container,
                "--network",
                "host",
                "-e",
                f"COWRIE_SSH_LISTEN_ENDPOINTS=tcp:{ssh_port}:interface=127.0.0.1",
                "-e",
                "HTTP_PROXY=",
                "-e",
                "HTTPS_PROXY=",
                "-e",
                "ALL_PROXY=",
                "-e",
                "http_proxy=",
                "-e",
                "https_proxy=",
                "-e",
                "all_proxy=",
                image_id,
            ]
        )
        if docker.returncode != 0:
            raise RuntimeError(f"docker run failed: {docker.stderr[:400]}")
        container_started = True
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline and not loopback_only(listeners_on(ssh_port), ssh_port):
            time.sleep(0.25)
        if not loopback_only(listeners_on(ssh_port), ssh_port):
            raise RuntimeError(f"Cowrie did not bind 127.0.0.1:{ssh_port}")
        observed_listeners = listeners_on(ssh_port)

        transport = SshCowrieTransport(port=ssh_port)
        transport.start()
        baseline_observation = observe_b0_baseline(transport)
        write_json(args.out / "b0_baseline_observation.json", baseline_observation)
        meta = SessionMeta(
            record_id=f"TESTONLY-B0-{stamp}-{os.getpid()}",
            track="B",
            split="development",
            block_id="TESTONLY-B0-NATIVE",
            allocation_index=0,
            arm="B0",
            scenario_id=args.scenario,
            profile_id=args.profile,
            seed=0,
            test_only=True,
            test_label="TEST_ONLY_B0_NATIVE_INTEGRATION_SMOKE",
            provenance=prelaunch["provenance"],
            verification_profile="NATIVE_TRANSPORT_ONLY",
        )
        record = run_session(
            meta,
            policy,
            transport,
            max_turns=args.max_turns,
            objective_turns=objective_turns,
        )
        validation = validate_record(record)
        if validation:
            raise RuntimeError(f"record contract failed: {validation}")
    except Exception as exc:  # noqa: BLE001 - preserve failure
        error = f"{type(exc).__name__}: {exc}"
    finally:
        if transport is not None:
            transport.close()
            (args.out / "ssh_client.raw").write_bytes(bytes(transport.raw))
        if container_started:
            logs = _docker(["logs", container])
            (args.out / "cowrie.log").write_text(logs.stdout + logs.stderr, encoding="utf-8")
            _docker(["rm", "-f", container])
        remaining = _docker(
            ["ps", "-a", "--filter", f"name=^{container}$", "--format", "{{.Names}}"]
        ).stdout.strip()
        post_cleanup_listeners = listeners_on(ssh_port)
        cleanup_true = not remaining and not post_cleanup_listeners
    if record is not None:
        (args.out / "record.jsonl").write_text(
            json.dumps(record, sort_keys=True) + "\n", encoding="utf-8"
        )
    cleanup_observation = {
        "schema": "ragin.ablation.track_b.cleanup_observation.v1",
        "container": container,
        "container_removed": not bool(
            _docker(["ps", "-a", "--filter", f"name=^{container}$", "--format", "{{.Names}}"]).stdout.strip()
        ),
        "ssh_port": ssh_port,
        "post_cleanup_listeners": post_cleanup_listeners,
        "cleanup_true": cleanup_true,
        "claim": "measured after container removal; empty listener rows are the expected cleanup state",
    }
    write_json(args.out / "post_cleanup_observation.json", cleanup_observation)
    summary = {
        "schema": "ragin.ablation.track_b.smoke_summary.v1",
        "status": (
            "PASS"
            if error is None
            and record is not None
            and loopback_only(observed_listeners, ssh_port)
            and cleanup_true
            else "FAIL"
        ),
        "error": error,
        "test_only": True,
        "claim": "TEST_ONLY_B0_NATIVE_INTEGRATION_SMOKE; not an ablation and not model inference",
        "arm": "B0",
        "scenario": args.scenario,
        "profile": args.profile,
        "turns": len(record.get("turns") or []) if record else 0,
        "terminal_cause": record.get("terminal_cause") if record else None,
        "b0_baseline_match_status": (
            baseline_observation.get("match_status") if baseline_observation else "NOT_OBSERVED"
        ),
        "b0_baseline_matched_to_b1_b3": (
            baseline_observation.get("matched_to_b1_b3") if baseline_observation else False
        ),
        "h1_claim": "BLOCKED_UNMATCHED_BASELINE_AND_NO_SHARED_VERIFIER",
        "ssh_loopback_only": loopback_only(observed_listeners, ssh_port),
        "listeners": observed_listeners,
        "post_cleanup_listeners": post_cleanup_listeners,
        "cleanup_true": cleanup_true,
        "record_sha256": (
            sha_bytes((args.out / "record.jsonl").read_bytes())
            if (args.out / "record.jsonl").exists()
            else None
        ),
    }
    write_json(args.out / "summary.json", summary)
    raw_files = [
        path for path in args.out.iterdir() if path.name != "raw_outputs.sha256.json"
    ]
    hashes = {path.name: sha256_file(path) for path in sorted(raw_files)}
    write_json(args.out / "raw_outputs.sha256.json", hashes)
    for path in raw_files:
        os.chmod(path, 0o444)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
