#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ragin.capture_v4.cowrie import CowrieCaptureFinalizer, parse_jsonl


def now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def list_container_files(container, log_dir):
    code = "import glob; print(*sorted(glob.glob(%r)), sep=\"\\n\")" % (log_dir.rstrip("/") + "/*.json*")
    completed = subprocess.run(
        ["docker", "exec", container, "/cowrie/cowrie-env/bin/python3", "-c", code],
        check=True, capture_output=True, text=True,
    )
    return [line for line in completed.stdout.splitlines() if line.strip()]


def copy_container_file(container, source, destination):
    subprocess.run(["docker", "cp", f"{container}:{source}", str(destination)], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--container", required=True)
    parser.add_argument("--log-dir", default="/cowrie/cowrie-git/var/log/cowrie")
    parser.add_argument("--root", default="data/prospective_v4/cowrie")
    parser.add_argument("--deployment-id", default="current-cowrie-container")
    parser.add_argument("--environment-id", default="current-cowrie-container")
    parser.add_argument("--cowrie-version", default="cowrie/cowrie:latest")
    parser.add_argument("--collector-sha256", required=True)
    parser.add_argument("--study-secret")
    parser.add_argument("--interval", type=float, default=30.0)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    root = Path(args.root)
    root.mkdir(parents=True, exist_ok=True)
    boundary = now()
    state_path = root / "watcher_state.json"
    state = {"schema": "ragin.cowrie.watcher_state.v1", "started_at_utc": boundary,
             "container": args.container, "log_dir": args.log_dir, "polls": 0,
             "finalized_native_sessions": []}
    finalizer = CowrieCaptureFinalizer(
        root=root, collector_name="v4_cowrie_capture_watch.py", collector_version="v1",
        collector_sha256=args.collector_sha256, deployment_id=args.deployment_id,
        environment_id=args.environment_id, cowrie_version=args.cowrie_version,
        study_secret=args.study_secret,
    )
    with tempfile.TemporaryDirectory(prefix="v4-cowrie-watch-") as staging:
        while True:
            state["polls"] += 1
            files = list_container_files(args.container, args.log_dir)
            local_files = []
            for source in files:
                local = Path(staging) / (hashlib.sha256(source.encode()).hexdigest() + ".json")
                copy_container_file(args.container, source, local)
                local_files.append(local)
            sessions = parse_jsonl(local_files)
            boundary_dt = datetime.fromisoformat(boundary.replace("Z", "+00:00"))
            for session in sessions.values():
                if session.start < boundary_dt or not session.close_seen:
                    continue
                source_network_id = next((event.event.get("src_ip") or event.event.get("source_ip") for event in session.events if event.event.get("src_ip") or event.event.get("source_ip")), None)
                result = finalizer.finalize(session, source_network_id=source_network_id)
                if result.get("status") in {"RECOVERED_VALID_CAPTURE", "ALREADY_FINALIZED"}:
                    if session.native_session_id not in state["finalized_native_sessions"]:
                        state["finalized_native_sessions"].append(session.native_session_id)
            state_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")
            if args.once:
                break
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
