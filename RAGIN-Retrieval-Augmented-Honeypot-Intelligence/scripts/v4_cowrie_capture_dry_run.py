#!/usr/bin/env python3
import json
import tempfile
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ragin.capture_v4.cowrie import CowrieCaptureFinalizer, CowrieEvent, CowrieSession


def main():
    events = [
        {"eventid": "cowrie.session.connect", "session": "dry-run-session", "timestamp": "2026-10-14T00:00:00Z"},
        {"eventid": "cowrie.login.success", "session": "dry-run-session", "timestamp": "2026-10-14T00:00:01Z", "username": "root", "password": "fixture-secret"},
        {"eventid": "cowrie.command.input", "session": "dry-run-session", "timestamp": "2026-10-14T00:00:02Z", "input": "id"},
        {"eventid": "cowrie.session.closed", "session": "dry-run-session", "timestamp": "2026-10-14T00:00:03Z"},
    ]
    session = CowrieSession("dry-run-session", [CowrieEvent("fixture-cowrie.json", index + 1, event) for index, event in enumerate(events)])
    with tempfile.TemporaryDirectory(prefix="v4-cowrie-dry-run-") as directory:
        result = CowrieCaptureFinalizer(
            root=directory, collector_name="v4_cowrie_capture_dry_run.py", collector_version="v1",
            collector_sha256="f" * 64, deployment_id="dry-run", environment_id="dry-run",
            cowrie_version="fixture", test_fixture=True,
        ).finalize(session)
        result.update({"test_fixture": True, "eligible_real_sessions": 0, "network_access": False,
                       "v4_policy_execution": 0, "reference_annotations": 0})
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
