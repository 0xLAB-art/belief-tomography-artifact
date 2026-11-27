#!/usr/bin/env python3
"""Field SSH smoke gate — the §0.5 per-arm test, runnable against any host.

Drives a scripted SSH login + command through the PUBLIC honeypot port and
asserts the full chain, per arm:

  cowrie arm   : banner + credential behavior + session lands in the
                 container's cowrie.json log (manual on-host step printed)
  vanilla arm  : cowrie-llm -> bare-llm backend SERVED (a real `whoami`
                 answer comes back, NOT the query-echo class)
  ragin arm    : cowrie-llm -> ragin-server bridge SERVED through the
                 verified pipeline (real identity answer; export JSONL
                 grows on the endpoint — printed as a manual check)

Exit 0 = the arm passes its smoke gate; nonzero = do NOT consider the arm
live (go/no-go criterion (a) in FIELD_LAUNCH_CHECKLIST §4).

The smoke gate uses the SYSTEM `ssh` client (no paramiko dependency — it
is not in requirements-runtime.txt and the smoke runs from the operator
laptop, not the image). Banner gating happens client-side without a
password prompt: cowrie accepts ANY password by design (userdbAny).

Usage:
    python scripts/field_smoke_ssh.py --host <public-ip> --arm vanilla
    python scripts/field_smoke_ssh.py --host <ip> --arm ragin --user root --password toor
"""

from __future__ import annotations

import argparse
import subprocess
import sys

# The single SSH client binary used for every probe (kept configurable for
# testing; override with --ssh-binary).
_SSH = "ssh"


def grab_banner(host: str, port: int, timeout: float) -> str:
    """Read the pre-auth SSH banner (client-side gate: no auth needed)."""
    import socket

    with socket.create_connection((host, port), timeout=timeout) as s:
        s.settimeout(timeout)
        data = b""
        while b"\n" not in data and len(data) < 256:
            chunk = s.recv(64)
            if not chunk:
                break
            data += chunk
    return data.decode("utf-8", "replace").strip()


def ssh_run(
    host: str,
    port: int,
    user: str,
    password: str,
    command: str,
    ssh_binary: str,
    timeout: float,
) -> tuple[int, str, str]:
    """Run one command over SSH with a password, non-interactively.

    Uses sshpass when available (apt/brew install sshpass); otherwise fails
    with an explicit instruction rather than hanging on a password prompt.
    """
    cmd = [
        ssh_binary,
        "-p",
        str(port),
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "UserKnownHostsFile=/dev/null",
        "-o",
        "LogLevel=ERROR",
        "-o",
        "ConnectTimeout=10",
        "-o",
        "PreferredAuthentications=password",
        "-o",
        "PubkeyAuthentication=no",
        f"{user}@{host}",
        command,
    ]
    if _has_sshpass():
        wrapped = ["sshpass", "-p", password, *cmd]
    else:
        print(
            "HINT: install sshpass for the automated path "
            "(apt install sshpass / brew install esolitos/ipa/sshpass), "
            "or run the printed command manually and paste output.",
            file=sys.stderr,
        )
        return 2, "", "sshpass-missing"
    proc = subprocess.run(wrapped, capture_output=True, text=True, timeout=timeout)
    return proc.returncode, proc.stdout, proc.stderr


def _has_sshpass() -> bool:
    from shutil import which

    return which("sshpass") is not None


def _is_echo_class(response: str) -> bool:
    """The deterministic-fallback echo class the CTI audit exposed."""
    low = response.lower()
    return "command not found" in low or "(no output)" in low or "not found. try" in low


def check_arm(arm: str, response: str) -> list[str]:
    """Per-arm assertions on the served text. Empty list = pass."""
    problems: list[str] = []
    response_stripped = response.strip()
    if not response_stripped:
        return ["empty serve — backend did not answer"]
    if _is_echo_class(response_stripped):
        return ["echo-class serve — the backend did NOT answer (template echo)"]

    if arm == "ragin":
        # The verified pipeline pins webapp@web-srv-01 for the novice persona;
        # a whoami serve must name the pinned user.
        if "webapp" not in response_stripped:
            problems.append("ragin arm: whoami serve lacks pinned user 'webapp' — check persona/fiction wiring")
    elif arm == "vanilla":
        # Bare generator: no pinned contract, but a `whoami` serve must at
        # least look like a username (single short token), not prose/refusal.
        if len(response_stripped.split()) > 3 or len(response_stripped) > 64:
            problems.append(f"vanilla arm: serve does not look like a whoami answer: {response_stripped[:60]!r}")
    elif arm == "cowrie":
        # Stock cowrie emulates a root-ish shell; any non-empty output passes.
        pass
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description="Per-arm SSH smoke gate (§0.5)")
    ap.add_argument("--host", required=True, help="public IP/hostname of the endpoint")
    ap.add_argument("--port", type=int, default=22)
    ap.add_argument("--arm", required=True, choices=["cowrie", "vanilla", "ragin"])
    ap.add_argument("--user", default="root")
    ap.add_argument("--password", default="toor", help="any password is accepted by all arms (userdbAny)")
    ap.add_argument("--command", default="whoami")
    ap.add_argument("--timeout", type=float, default=30.0, help="seconds to wait for the serve")
    ap.add_argument("--ssh-binary", default=_SSH)
    ap.add_argument("--banner-timeout", type=float, default=8.0)
    args = ap.parse_args()

    print(f"[1/3] banner: {args.host}:{args.port}")
    try:
        banner = grab_banner(args.host, args.port, args.banner_timeout)
    except OSError as e:
        print(f"FAIL: no banner ({e}) — port not reachable / listener down", file=sys.stderr)
        return 1
    if not banner.startswith("SSH-2.0-"):
        print(f"FAIL: not an SSH-2.0 banner: {banner!r}", file=sys.stderr)
        return 1
    print(f"      {banner}")

    print(f"[2/3] ssh {args.user}@{args.host} '{args.command}' (arm={args.arm})")
    code, out, err = ssh_run(
        args.host,
        args.port,
        args.user,
        args.password,
        args.command,
        args.ssh_binary,
        args.timeout,
    )
    if code == 2 and err == "sshpass-missing":
        print("\n  Run manually, then re-check the output against step 3:")
        print(
            f"    sshpass -p {args.password} ssh -p {args.port} -o StrictHostKeyChecking=no "
            f"-o PreferredAuthentications=password -o PubkeyAuthentication=no "
            f"{args.user}@{args.host} '{args.command}'"
        )
        return 2
    served = (out or err).strip()
    print(f"      served: {served[:200]!r}")

    print("[3/3] per-arm assertions")
    problems = check_arm(args.arm, served)
    if problems:
        for p in problems:
            print(f"  FAIL: {p}", file=sys.stderr)
        return 1

    print(f"  PASS: {args.arm} arm served a real answer (not echo-class)")
    print(
        "\nMANUAL follow-ups on the endpoint (needed for the go/no-go record):\n"
        "  cowrie/vanilla/ragin: docker logs field-cowrie-llm --tail 20   # session logged\n"
        + (
            "  ragin: docker exec field-ragin-server ls -la /field-export  # export JSONL grew\n"
            if args.arm == "ragin"
            else ""
        )
        + "  sudo iptables -L DOCKER-USER -n | head   # egress gate verified"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
