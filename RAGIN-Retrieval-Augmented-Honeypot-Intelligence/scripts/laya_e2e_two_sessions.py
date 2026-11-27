"""Two local e2e runs: ChrolloAdapter → Sandbox → Harness (mandatory verification ON).

Identical benign synthetic inputs; RAGIN_LAYA_ENABLED=0 vs =1 (separate processes,
same checkpoint). Evidence: per-run session event log replay showing the
CLASSIFICATION event with/without a laya_assessment block, plus trace IDs.
Raw evidence: results/laya_research/e2e_sessions.json
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RESULTS_DIR = REPO / "results" / "laya_research"
OUT = RESULTS_DIR / "e2e_sessions.json"
INPUTS = ["ls -la /var/www", "uptime\nwho\nw"]


def session_log_path(session_id: str, session_dir: str) -> Path:
    return Path(session_dir) / f"{session_id}.jsonl"


def replay_classification(session_id: str, session_dir: str) -> tuple[list[str], list]:
    """Replay the JSONL event log; return (event types, laya blocks from CLASSIFICATION)."""
    log = session_log_path(session_id, session_dir)
    etypes = []
    blocks = []
    with open(log) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            et = d.get("event_type")
            etypes.append(et)
            if et == "classification":
                blocks.append(d.get("data", {}).get("laya_assessment"))
    return etypes, blocks


CHILD = r"""
import json, sys, uuid

mode = sys.argv[1]
session_dir = sys.argv[2]
import os
os.environ["RAGIN_REQUIRE_AUTH"] = "0"
os.environ["RAGIN_SESSION_DIR"] = session_dir
os.environ["RAGIN_LAYA_ENABLED"] = {"OFF": "0", "ON": "1"}[mode]
from ragin.cycle.adapters import ChrolloAdapter, DonAdapter, HisokaAdapter
from ragin.cycle.harness import Harness
from ragin.cycle.sandbox import Sandbox, SandboxConfig
from ragin.graph.host_fiction import HostFictionStore

trace_id = str(uuid.uuid4())
host_path = sys.argv[3]
host_store = HostFictionStore(host_key=f"e2e-laya-{mode.lower()}", policy="per_session")
host_store.save(host_path)

harness = Harness(
    classifier=ChrolloAdapter(),
    cti_engine=DonAdapter(gateway_url="http://localhost:8080", api_key=""),
    deceiver=HisokaAdapter(gateway_url="http://localhost:8080"),
    mandatory_verification=True,
    host_store=host_store,
)
sandbox = Sandbox(harness=harness)
cfg = SandboxConfig(source_ip="127.0.0.1", session_dir=session_dir)

# First command creates the session and returns its id.
first = sandbox.handle_command("127.0.0.1", INPUT := sys.argv[4])
session_id = first.session_id
responses = [ Responses := {"command": sys.argv[4], "responded": bool(first.response_text), "status": first.status, "error": (first.error or "")[:80]} ]
for cmd in sys.argv[5:]:
    r = sandbox.handle_command("127.0.0.1", cmd, session_id=session_id)
    responses.append({"command": cmd, "responded": bool(r.response_text), "status": r.status, "error": (r.error or "")[:80]})

print(json.dumps({"trace_id": trace_id, "session_id": session_id, "responses": responses}))
"""


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    child_path = RESULTS_DIR / "_e2e_child.py"
    child_path.write_text(CHILD)
    runs = {}
    for mode in ("OFF", "ON"):
        sdir = RESULTS_DIR / f"sessions_{mode}"
        if sdir.exists():
            for old in sdir.glob("*.jsonl"):
                old.unlink()
        host_path = RESULTS_DIR / f"host_fiction_{mode}.json"
        if host_path.exists():
            host_path.unlink()
        cmd_inputs = [INPUTS[0], *INPUTS[1:]]
        argv = [
            str(REPO / ".venv" / "bin" / "python"),
            str(child_path),
            mode,
            str(sdir),
            str(host_path),
            *cmd_inputs,
        ]
        t0 = time.time()
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=600, cwd=str(REPO))
        wall_s = round(time.time() - t0, 1)
        if proc.returncode != 0:
            runs[mode] = {"error": proc.stderr[-800:], "exit_code": proc.returncode}
            continue
        summary = json.loads(proc.stdout.strip().splitlines()[-1])
        etypes, blocks = replay_classification(summary["session_id"], str(sdir))
        runs[mode] = {
            "trace_id": summary["trace_id"],
            "session_id": summary["session_id"],
            "laya_enabled_env": {"OFF": "0", "ON": "1"}[mode],
            "responses": summary["responses"],
            "classification_events": sum(1 for e in etypes if e == "classification"),
            "laya_assessment_in_events": blocks,
            "event_types": etypes,
            "wall_s": wall_s,
        }
    out = {"generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "runs": runs}
    OUT.write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps(out, indent=1, default=str)[:4000])
    child_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
