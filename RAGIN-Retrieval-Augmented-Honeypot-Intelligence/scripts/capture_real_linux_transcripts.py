#!/usr/bin/env python3
"""Capture REAL-Linux transcripts for the human blind eval (real_linux arm).

Honesty note (docs/FIELD_ETHICS.md §4): the repo's cowrie captures are
honeypot logs with no command output, so the real_linux arm must be built
from GENUINE command runs on a real Linux machine. This script executes a
fixed, read-only command set in the local shell, captures the real output,
and de-identifies it:

  * current user        -> ``sysadmin``  (home -> /home/sysadmin)
  * real hostname       -> ``srv-01``
  * IPv4 addresses      -> ``10.0.0.1``
  * non-system users in /etc/passwd -> dropped or mapped to sysadmin
  * shadow              -> real "Permission denied" error (non-root, honest)
  * ps lines            -> allowlist of generic server processes
  * ss lines            -> allowlist of generic listening ports
  * env output          -> generic-variable whitelist
  * listings            -> hidden files dropped (they fingerprint the box)
  * environment-specific file contents (/tmp artifacts, crontabs, /mnt
    mounts) -> commands replaced with generic equivalents

Prompt lines use the canonical ``user@host:cwd$`` shape so the transcript
looks like a normal interactive session. The packet builder
(scripts/human_blind_eval.py normalize_transcript) applies a SECOND,
arm-agnostic sanitization pass at build time; tokens chosen here (srv-01,
sysadmin) deliberately do not collide with its replacement map.

Everything captured is real output of the real commands on this machine —
no fabrication. Output schema: JSON array of {"transcript": "<session>"}.

Usage:
  python scripts/capture_real_linux_transcripts.py [--out data/real_linux_transcripts.json]
"""

from __future__ import annotations

import argparse
import getpass
import json
import re
import socket
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CANON_USER = "sysadmin"
CANON_HOST = "srv-01"
CANON_HOME = f"/home/{CANON_USER}"

# --- de-identification tables ------------------------------------------------

# Accounts that are safe (generic) to show in /etc/passwd.
SYSTEM_USERS = {
    "root", "daemon", "bin", "sys", "sync", "games", "man", "lp", "mail",
    "news", "uucp", "proxy", "www-data", "backup", "list", "irc", "gnats",
    "nobody", "systemd-network", "systemd-resolve", "messagebus", "sshd",
    "syslog", "uuidd", "tcpdump", "tss", "landscape", "pollinate", "lxd",
}

# Supplemental groups kept in `id` output (anything else, e.g. per-tool
# groups, is dropped).
GROUP_KEEP = {"adm", "cdrom", "sudo", "dip", "plugdev", "users", "lpadmin",
              "docker", "input"}

# Lines containing any of these tokens are dropped entirely (they fingerprint
# the capture environment rather than a generic Linux box). Matching is
# case-insensitive substring; be careful adding short tokens (e.g. "tor"
# matches "monitor"). When in doubt, over-dropping is the safe direction.
DENYLIST_TOKENS = [
    "codebuff", "graphify", "ragin", "claude", "cursor", "vscode",
    "playwright", "chrome", "workspaces", ".venv", "chatgpt", "codex",
    "openclaude", "crashpad", "ollama", "tailscale", "opencode",
    "acts_", "boot_rearm", "model_proxy", "sp2027",
]

# ps: keep only processes a generic server would plausibly show. Everything
# else (desktop apps, agent tooling, anything environment-specific) is dropped.
PS_ALLOW = re.compile(
    r"systemd|sshd|dbus|cron|getty|login|snapd|polkit|networkd|resolved|"
    r"journald|udevd|rsyslog|dockerd|containerd|auditd|nginx|postgres|"
    r"wpa_supplicant|NetworkManager|acpid|atd",
    re.IGNORECASE,
)

# ss: generic listening ports only.
SS_PORTS = {"22", "53", "80", "443", "5432", "631", "5353"}

# df: mount points a generic server would show.
DF_MOUNTS = {"/", "/run", "/dev/shm", "/run/lock", "/sys/firmware/efi/efivars",
             "/run/qemu", "/boot/efi", "/run/user/1000", "/run/user/0"}

# ls /: standard FHS entries only.
ROOT_NAMES = {
    "bin", "boot", "dev", "etc", "home", "lib", "lib32", "lib64", "libx32",
    "media", "mnt", "opt", "proc", "root", "run", "sbin", "snap", "srv",
    "sys", "tmp", "usr", "var",
}

# Environment variables safe to expose.
ENV_WHITELIST = ["HOME", "SHELL", "LANG", "TERM", "USER", "LOGNAME", "PATH", "HOSTNAME"]

PATH_ALLOW = {
    "/usr/local/sbin", "/usr/local/bin", "/usr/sbin", "/usr/bin",
    "/sbin", "/bin", "/snap/bin",
}


# --- generic sanitizers -------------------------------------------------------

def sanitize(text: str, real_user: str, real_home: str, real_host: str) -> str:
    out = text
    out = re.sub(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", "10.0.0.1", out)
    if real_host:
        out = re.sub(rf"\b{re.escape(real_host)}(?:\.\S+)?\b", CANON_HOST, out)
    if real_user:
        out = re.sub(rf"\b{re.escape(real_user)}\b", CANON_USER, out)
    if real_home:
        out = out.replace(real_home, CANON_HOME)
    for tok in DENYLIST_TOKENS:
        out = re.sub(rf"^.*{re.escape(tok)}.*$", "", out, flags=re.MULTILINE | re.IGNORECASE)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.rstrip("\n")


def sanitize_passwd(raw: str, real_user: str) -> str:
    lines = []
    for line in raw.splitlines():
        f = line.split(":")
        if len(f) < 7:
            continue
        name = f[0]
        if name == real_user:
            f[0], f[5] = CANON_USER, CANON_HOME
            lines.append(":".join(f))
        elif name in SYSTEM_USERS:
            if f[5].startswith("/home/"):
                f[5] = "/nonexistent"  # keep structure, avoid a duplicate sysadmin
            lines.append(":".join(f))
        # anything else (local tool/service accounts) is dropped
    return "\n".join(lines)


def sanitize_os_release(raw: str) -> str:
    """Capitalize lowercase 'ubuntu' values/URLs. The packet builder's
    normalize_transcript() replaces lowercase 'ubuntu' with a canonical USER
    name — without this, ID=ubuntu and ubuntu.com URLs would be mangled into
    'ID=deploy' / 'deploy.com' in the rater-facing packet."""
    return re.sub(r"(?<![A-Za-z])ubuntu", "Ubuntu", raw)


def sanitize_id(raw: str, real_user: str) -> str:
    m = re.match(r"uid=\d+\(([^)]+)\) gid=\d+\(([^)]+)\) groups=(.*)", raw.strip())
    if not m:
        return raw
    uid_name, gid_name, groups = m.groups()
    kept = []
    for g in groups.split(","):
        g = g.strip()
        gm = re.match(r"\d+\(([^)]+)\)", g)
        if gm and (gm.group(1) in GROUP_KEEP or g == f"1000({uid_name})"):
            kept.append(re.sub(rf"\({re.escape(uid_name)}\)", f"({CANON_USER})", g))
    text = f"uid=1000({CANON_USER}) gid=1000({CANON_USER}) groups={','.join(kept)}"
    if uid_name == "root":  # root session: keep the real (generic) ids
        text = raw.strip()
    return text


def sanitize_ps(raw: str, real_user: str) -> str:
    out_lines = []
    for i, line in enumerate(raw.splitlines()):
        if i == 0:  # header
            out_lines.append(line)
            continue
        if not line.strip():
            continue
        if PS_ALLOW.search(line):
            out_lines.append(line)
    text = "\n".join(out_lines)
    # user column: map the real (non-root) user to the canonical one
    if real_user and real_user != "root":
        text = re.sub(rf"(^|\n){re.escape(real_user)}\s", rf"\1{CANON_USER} ", text)
    return text


def sanitize_ss(raw: str) -> str:
    out_lines = []
    for i, line in enumerate(raw.splitlines()):
        if i == 0:  # header
            out_lines.append(line)
            continue
        if "users:" in line:  # per-socket process reveals local tooling
            continue
        if re.search(r"(?i)fd7a:|tailscale", line):
            continue
        cols = line.split()
        if len(cols) < 5:
            continue
        local = cols[4]
        port = local.rsplit(":", 1)[-1]
        if port in SS_PORTS:
            out_lines.append(line)
    return "\n".join(out_lines)


def sanitize_df(raw: str) -> str:
    out_lines = []
    for i, line in enumerate(raw.splitlines()):
        if i == 0 or line.startswith("Filesystem"):
            out_lines.append(line)
            continue
        mount = line.split()[-1] if line.split() else ""
        if mount in DF_MOUNTS:
            out_lines.append(line)
    return "\n".join(out_lines)


def sanitize_env(raw: str) -> str:
    lines = []
    for line in raw.splitlines():
        key = line.split("=", 1)[0]
        if key not in ENV_WHITELIST:
            continue
        if key == "PATH":
            parts = [p for p in line.split("=", 1)[1].split(":") if p in PATH_ALLOW]
            seen, uniq = set(), []
            for p in parts:
                if p not in seen:
                    seen.add(p)
                    uniq.append(p)
            line = "PATH=" + ":".join(uniq)
        lines.append(line)
    return "\n".join(lines)


_LS_ENTRY = re.compile(
    r"^[dl-][rwx-]{9}[.+]?\s+\d+\s+\S+\s+\S+\s+\S+\s+\w{3}\s+\d{1,2}\s+"
    r"(?:\d{1,2}:\d{2}|\d{4})\s+(.+)$"
)


def sanitize_ls_generic(raw: str) -> str:
    """Keep `ls -la` total lines, '.'/'..' (non-identifying, keep realism) and
    non-hidden entries (dotfiles and odd entries fingerprint the box)."""
    keep = []
    for line in raw.splitlines():
        if line.startswith("total "):
            keep.append(line)
            continue
        m = _LS_ENTRY.match(line)
        if m and (m.group(1) in (".", "..") or not m.group(1).startswith(".")):
            keep.append(line)
    return "\n".join(keep[:30])


def _entry_name(text: str) -> str:
    """Trailing ls field: 'name' or symlink 'name -> target'."""
    left = text.split(" -> ", 1)[0]
    return left


def sanitize_ls_root(raw: str) -> str:
    """`ls -la /`: keep '.', '..', standard FHS entries and their
    merged-usr symlinks (a real Ubuntu / always shows bin -> usr/bin)."""
    keep = []
    for line in raw.splitlines():
        if line.startswith("total "):
            keep.append(line)
            continue
        m = _LS_ENTRY.match(line)
        if not m:
            continue
        name = _entry_name(m.group(1))
        if name in (".", "..") or name in ROOT_NAMES:
            keep.append(line)
    return "\n".join(keep)


def sanitize_ls_varlog(raw: str) -> str:
    """Bare `ls /var/log | head` names: drop hidden/denylisted names."""
    keep = []
    for line in raw.splitlines():
        name = line.strip()
        if not name or name.startswith("."):
            continue
        if any(tok.lower() in name.lower() for tok in DENYLIST_TOKENS):
            continue
        keep.append(name)
    return "\n".join(keep)


# --- command execution --------------------------------------------------------

def run_cmd(cmd: str, timeout: int = 15) -> str:
    try:
        p = subprocess.run(
            cmd, shell=True, text=True, capture_output=True, timeout=timeout
        )
        out = (p.stdout or "") + (p.stderr or "")
        return out if out.strip() else ""
    except subprocess.TimeoutExpired:
        return "[command timed out]"


# Session plans. Commands are real and read-only; the same recon command
# families used in the scripted cowrie corpus, bounded so nothing runs away.
# (Full-filesystem `find /` is deliberately replaced by a bounded /etc scan.)
SESSION_PLANS: list[list[str]] = [
    ["whoami", "id", "uname -a"],
    ["uptime", "date -u"],
    ["cat /etc/os-release", "free -m"],
    ["ls -la /"],
    ["df -h"],
    ["ps aux"],
    ["cat /etc/passwd", "cat /etc/shadow"],
    ["echo $HOME", "env | sort"],
    ["ss -tupln"],
    ["ls /var/log | head -n 20", "ls -la /etc/ssh"],
    ["whoami", "hostname", "uname -r"],
    ["find /etc -name '*.conf' 2>/dev/null | head -n 20", "cat /proc/version"],
]


def capture_sessions() -> list[str]:
    real_user = getpass.getuser()
    real_home = run_cmd("printf %s \"$HOME\"") or f"/home/{real_user}"
    real_host = socket.gethostname()

    def san(text: str) -> str:
        return sanitize(text, real_user, real_home, real_host)

    cwd_disp = "~"
    transcripts = []
    for plan in SESSION_PLANS:
        parts = []
        for cmd in plan:
            out = run_cmd(cmd)
            prompt = f"{CANON_USER}@{CANON_HOST}:{cwd_disp}$ {cmd}"
            if not out.strip():
                parts.append(prompt)
                continue
            # Per-command post-processing on top of the generic sanitizer.
            if cmd.startswith("cat /etc/os-release"):
                out = sanitize_os_release(out)
            elif cmd.startswith("cat /etc/passwd"):
                out = sanitize_passwd(out, real_user)
            elif cmd.startswith("cat /etc/shadow"):
                pass  # non-root: keep the honest "Permission denied" error
            elif cmd == "id":
                out = sanitize_id(out, real_user)
            elif cmd.startswith("ps aux"):
                out = sanitize_ps(out, real_user)
            elif cmd.startswith("ss "):
                out = sanitize_ss(out)
            elif cmd.startswith("df -h"):
                out = sanitize_df(out)
            elif cmd.startswith("env"):
                out = sanitize_env(out)
            elif cmd == "ls -la /":
                out = sanitize_ls_root(out)
            elif cmd.startswith("ls /var/log"):
                out = sanitize_ls_varlog(out)
            elif cmd.startswith("ls -la"):
                out = sanitize_ls_generic(out)
            out = san(out)
            if not out.strip():
                parts.append(prompt)
                continue
            parts.append(f"{prompt}\n{out}")
        transcripts.append("\n".join(parts))
    return transcripts


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--out",
        default=str(ROOT / "data" / "real_linux_transcripts.json"),
        help="output path (default: data/real_linux_transcripts.json)",
    )
    args = ap.parse_args()

    transcripts = capture_sessions()
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # Schema consumed by scripts/human_blind_eval.py load_transcripts("real_linux"):
    out_path.write_text(json.dumps([{"transcript": t} for t in transcripts], indent=2) + "\n")

    print(f"[ok] wrote {len(transcripts)} real-Linux transcripts -> {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
