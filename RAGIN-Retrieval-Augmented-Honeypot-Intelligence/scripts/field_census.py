#!/usr/bin/env python3
"""Aggregate-only census of the field cowrie logs.

Runs **on the endpoint** (EDGE) and prints one JSON document with counts and
hashed source identifiers only. Raw `src_ip` values are hashed in-process with
the pipeline's own salt/format (`ragin.utils.hash_ip`) and never emitted, so
the census can be collected over SSM without moving raw addresses off the host
(FIELD_ETHICS §3).

Stdlib only: the endpoint has no project venv.

Usage:
  python3 scripts/field_census.py --log-dir /opt/ragin/cowrie-var/log/cowrie
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REFUSAL = re.compile(r"(i cannot help|i can't help|i'm unable|cannot assist|as an ai)", re.I)


def hash_ip(value: str, length: int = 12) -> str:
    """HMAC-SHA256 keyed with RAGIN_IP_SALT — matches ragin.utils.hash_ip.

    Endpoint scripts replicate this derivation in-place (stdlib only, no project
    venv on the host); tests/unit/test_ip_hashing.py asserts the two agree.
    Requires RAGIN_IP_SALT to be set; refuses to hash with a committed default.
    """
    if not value or value in ("unknown", "_", "0.0.0.0", "::"):
        return value
    salt = os.environ.get("RAGIN_IP_SALT")
    if not salt:
        raise RuntimeError(
            "RAGIN_IP_SALT is not set: refusing to hash source IPs with a "
            "default key (set RAGIN_IP_SALT or run inside the pipeline)."
        )
    return hmac.new(salt.encode(), value.encode(), hashlib.sha256).hexdigest()[:length]


def iter_events(log_dir: Path):
    for path in sorted(log_dir.glob("cowrie.json*")):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            yield path, event


def census(log_dir: Path) -> dict:
    by_day: dict[str, dict[str, int]] = {}
    event_ids: Counter[str] = Counter()
    commands: Counter[str] = Counter()
    sources: set[str] = set()
    sessions: set[str] = set()
    refusals = 0
    malformed = 0
    total = 0

    for path, event in iter_events(log_dir):
        total += 1
        event_id = str(event.get("eventid", "?"))
        event_ids[event_id] += 1
        day = str(event.get("timestamp", ""))[:10] or "unknown"
        bucket = by_day.setdefault(day, {"events": 0, "session_connect": 0, "commands": 0})
        bucket["events"] += 1
        if event_id == "cowrie.session.connect":
            bucket["session_connect"] += 1
            if event.get("session"):
                sessions.add(str(event["session"]))
        if event_id == "cowrie.command.input":
            bucket["commands"] += 1
            command = str(event.get("input", "")).strip()
            if command:
                commands[command.split("\n")[0][:80]] += 1
            if REFUSAL.search(command):
                refusals += 1
        if event.get("src_ip"):
            sources.add(hash_ip(str(event["src_ip"])))

    return {
        "schema": "ragin.field.cowrie_census.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generated_on": _hostname(),
        "log_dir": str(log_dir),
        "log_files": [
            {"name": p.name, "bytes": p.stat().st_size}
            for p in sorted(log_dir.glob("cowrie.json*"))
            if p.is_file()
        ],
        "totals": {
            "events": total,
            "malformed_lines": malformed,
            "sessions_connected": len(sessions),
            "unique_hashed_sources": len(sources),
            "commands": event_ids.get("cowrie.command.input", 0),
            "login_success": event_ids.get("cowrie.login.success", 0),
            "login_failed": event_ids.get("cowrie.login.failed", 0),
            "file_downloads": event_ids.get("cowrie.session.file_download", 0),
            "refusal_shaped_commands": refusals,
            "interactive_events": (
                event_ids.get("cowrie.command.input", 0)
                + event_ids.get("cowrie.login.success", 0)
                + event_ids.get("cowrie.login.failed", 0)
            ),
        },
        "by_day": dict(sorted(by_day.items())),
        "event_ids": dict(event_ids.most_common()),
        "top_commands": [{"command": c, "count": n} for c, n in commands.most_common(15)],
        "hashed_sources": sorted(sources),
        "ip_hash": {
            "algorithm": "hmac-sha256(key=RAGIN_IP_SALT)",
            "truncated_hex": 12,
        },  # the key itself is never emitted
    }


def _hostname() -> str:
    try:
        return Path("/etc/hostname").read_text(encoding="utf-8").strip()
    except OSError:
        return "unknown"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--log-dir",
        type=Path,
        default=Path("/opt/ragin/cowrie-var/log/cowrie"),
    )
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="write <UTC date>.json here (cron-safe: no shell date substitution)",
    )
    args = parser.parse_args(argv[1:])
    payload = census(args.log_dir)
    text = json.dumps(payload, indent=2)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    if args.out_dir:
        args.out_dir.mkdir(parents=True, exist_ok=True)
        day = payload["generated_at"][:10]
        (args.out_dir / f"{day}.json").write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
