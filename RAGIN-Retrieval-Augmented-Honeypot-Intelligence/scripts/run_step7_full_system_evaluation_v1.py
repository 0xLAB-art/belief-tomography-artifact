from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FREEZE_DIR = ROOT / "results" / "step6_matched_evaluation_protocol_v1"
DEFAULT_OUT = ROOT / "results" / "step7_full_system_evaluation_v1"
EXPERIMENT_ID = "ragin.step7.full_system_evaluation.v1"
API_KEY = "step7-local-auth-key-20261015"
PORT = 18080


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha_file(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def post(base: str, path: str, payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    request_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    request = urllib.request.Request(
        base + path,
        data=request_bytes,
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            response_bytes = response.read()
            status = response.status
            response_headers = dict(response.headers)
    except urllib.error.HTTPError as error:
        response_bytes = error.read()
        status = error.code
        response_headers = dict(error.headers)
    try:
        parsed = json.loads(response_bytes.decode("utf-8"))
    except Exception:
        parsed = None
    return {
        "request_bytes": request_bytes.decode("utf-8"),
        "request_sha256": sha_bytes(request_bytes),
        "response_bytes": response_bytes.decode("utf-8", "replace"),
        "response_sha256": sha_bytes(response_bytes),
        "response_status": status,
        "response_headers": {key.lower(): value for key, value in response_headers.items() if key.lower() in {"x-session-id", "x-session-token", "x-response-time"}},
        "parsed": parsed,
    }


def wait_health(base: str, process: subprocess.Popen[str]) -> None:
    deadline = time.time() + 90
    while time.time() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"server exited before health check: {process.returncode}")
        try:
            with urllib.request.urlopen(base + "/health", timeout=2) as response:
                if response.status == 200:
                    return
        except Exception:
            time.sleep(0.25)
    raise RuntimeError("server health check timed out")


def server_environment(out: Path, arm: str) -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "RAGIN_BIND_HOST": "127.0.0.1",
            "RAGIN_REQUIRE_AUTH": "1",
            "API_KEY": API_KEY,
            "RAGIN_RAG_MODE": "offline",
            "RAGIN_RUNTIME_MODE": "RAGIN_V4_SUBSTANTIVE_DETERMINISTIC",
            "RAGIN_EVIDENCE_JUDGE_ENABLED": "1" if arm == "B_judge_on" else "0",
            "RAGIN_EVIDENCE_JUDGE_FILTERING_ENABLED": "1" if arm == "B_judge_on" else "0",
            "RAGIN_PROVIDER_ENABLED": "0",
            "RAGIN_LLM_BASE_URL": "http://127.0.0.1:9",
            "GATEWAY_URL": "http://127.0.0.1:9",
            "RAGIN_SESSION_DIR": str(out / "sessions" / arm),
            "RAGIN_FIELD_EXPORT_DIR": str(out / "field_export" / arm),
            "RAGIN_HOST_FICTION_PATH": str(out / "host_fiction" / f"{arm}.json"),
            "PYTHONUNBUFFERED": "1",
        }
    )
    return env


def run_arm(arm: str, cases: list[dict[str, Any]], out: Path) -> dict[str, Any]:
    arm_dir = out / arm
    arm_dir.mkdir(parents=True, exist_ok=True)
    log_path = arm_dir / "server.log"
    log_handle = log_path.open("w", encoding="utf-8")
    process = subprocess.Popen(
        [str(ROOT / ".venv/bin/python"), "-m", "ragin.server_v2", "--mode", "pipeline", "--port", str(PORT)],
        cwd=ROOT,
        env=server_environment(out, arm),
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        text=True,
    )
    base = f"http://127.0.0.1:{PORT}"
    raw_calls: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    try:
        wait_health(base, process)
        for case in cases:
            case_started = time.time()
            created = post(base, "/api/session/create", {"source_ip": "127.0.0.1", "max_commands": 1000}, {"X-API-Key": API_KEY})
            raw_calls.append({"case_id": case["case_id"], "arm": arm, "stage": "create", **created})
            if created["response_status"] != 200 or not isinstance(created["parsed"], dict):
                records.append({"case_id": case["case_id"], "arm": arm, "status": "FAILED_CREATE", "create": created})
                continue
            session_id = created["parsed"]["session_id"]
            session_token = created["parsed"]["session_token"]
            turns = []
            commands = [*case["preceding_commands"], case["selected_input"]]
            for turn_index, command in enumerate(commands, start=1):
                result = post(
                    base,
                    "/api/session/command",
                    {"session_id": session_id, "command": command},
                    {"X-API-Key": API_KEY, "X-Session-Token": session_token},
                )
                raw_calls.append({"case_id": case["case_id"], "arm": arm, "stage": "command", "turn_index": turn_index, **result})
                turns.append({"turn_index": turn_index, "command": command, "result": result["parsed"], "status": result["response_status"], "response_sha256": result["response_sha256"]})
            final = turns[-1] if turns else None
            records.append(
                {
                    "experiment_id": EXPERIMENT_ID,
                    "case_id": case["case_id"],
                    "arm": arm,
                    "session_id": session_id,
                    "input_sha256": case["identity_keys"]["final_input_sha256_bytes"],
                    "case_started_at": case_started,
                    "turn_count": len(turns),
                    "turns": turns,
                    "final_response_sha256": final["response_sha256"] if final else None,
                    "final_status": final["status"] if final else None,
                    "final_response_text": ((final.get("result") or {}).get("response_text") if final else None),
                    "session_path": str(out / "sessions" / arm / f"{session_id}.jsonl"),
                    "status": "COMPLETE" if final and final["status"] == 200 and isinstance(final["result"], dict) and not final["result"].get("error") else "FAILED_FINAL",
                }
            )
    finally:
        process.send_signal(signal.SIGTERM)
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        log_handle.close()
    return {"arm": arm, "records": records, "raw_calls": raw_calls, "server_exit_code": process.returncode}


def load_freeze() -> tuple[dict[str, Any], dict[str, Any]]:
    manifest = read_json(FREEZE_DIR / "freeze_manifest_v1.json")
    for relative, expected in manifest["source_hashes"].items():
        actual = sha_file(ROOT / relative)
        if actual != expected:
            raise RuntimeError(f"freeze source hash mismatch before execution: {relative}")
    selection = read_json(FREEZE_DIR / "selected_cases_v1.json")
    protocol = read_json(FREEZE_DIR / "protocol_v1.json")
    if selection["status"] != "FROZEN_BEFORE_CONFIRMATORY_CALLS":
        raise RuntimeError("selection is not frozen before confirmatory calls")
    if protocol["status"] != "FROZEN_BEFORE_CONFIRMATORY_CALLS":
        raise RuntimeError("protocol is not frozen before confirmatory calls")
    return selection, manifest


def run_study(out: Path) -> int:
    selection, manifest = load_freeze()
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "execution_start.json", {"experiment_id": EXPERIMENT_ID, "freeze_manifest_sha256": sha_file(FREEZE_DIR / "freeze_manifest_v1.json"), "started_at": time.time(), "status": "RUNNING", "N": selection["N"], "arms": ["A_judge_off", "B_judge_on"]})
    results = []
    for arm in ("A_judge_off", "B_judge_on"):
        result = run_arm(arm, selection["cases"], out)
        results.append(result)
        write_jsonl(out / arm / "raw_http_calls.jsonl", result["raw_calls"])
        write_jsonl(out / arm / "case_arm_records.jsonl", result["records"])
    flat = [record for result in results for record in result["records"]]
    manifest_out = {
        "schema": "ragin.step7.execution_manifest.v1",
        "experiment_id": EXPERIMENT_ID,
        "status": "RAW_OUTPUTS_FROZEN_BEFORE_ANALYSIS",
        "freeze_manifest_sha256": sha_file(FREEZE_DIR / "freeze_manifest_v1.json"),
        "selection_manifest_sha256": sha_file(FREEZE_DIR / "selected_cases_v1.json"),
        "N_cases": selection["N"],
        "expected_case_arm_pairs": selection["N"] * 2,
        "observed_case_arm_pairs": len({(row["case_id"], row["arm"]) for row in flat}),
        "complete_case_arm_pairs": sum(row["status"] == "COMPLETE" for row in flat),
        "failed_case_arm_pairs": sum(row["status"] != "COMPLETE" for row in flat),
        "raw_http_call_count": sum(len(result["raw_calls"]) for result in results),
        "arms": {result["arm"]: {"server_exit_code": result["server_exit_code"], "case_count": len(result["records"])} for result in results},
        "limitations": ["deterministic provider-unavailable mode only", "SSH/Cowrie ingress proof is a separate gate", "no scoring, reference-label join, or tuning performed"],
    }
    write_json(out / "run_manifest.json", manifest_out)
    write_json(out / "execution_start.json", {"experiment_id": EXPERIMENT_ID, "freeze_manifest_sha256": sha_file(FREEZE_DIR / "freeze_manifest_v1.json"), "completed_at": time.time(), "status": "RAW_OUTPUTS_FROZEN_BEFORE_ANALYSIS", "N": selection["N"]})
    freeze_outputs(out)
    return 0 if manifest_out["observed_case_arm_pairs"] == manifest_out["expected_case_arm_pairs"] and manifest_out["failed_case_arm_pairs"] == 0 else 1


def freeze_outputs(out: Path) -> None:
    selection, freeze_manifest = load_freeze()
    run_manifest = read_json(out / "run_manifest.json")
    files = {}
    for path in sorted(out.rglob("*")):
        if path.is_file() and path.name != "raw_output_manifest.json":
            files[str(path.relative_to(out))] = sha_file(path)
    write_json(
        out / "raw_output_manifest.json",
        {
            "schema": "ragin.step7.raw_output_manifest.v1",
            "experiment_id": EXPERIMENT_ID,
            "status": "FROZEN_BEFORE_ANALYSIS",
            "freeze_manifest_sha256": sha_file(FREEZE_DIR / "freeze_manifest_v1.json"),
            "selection_manifest_sha256": sha_file(FREEZE_DIR / "selected_cases_v1.json"),
            "N": selection["N"],
            "run_manifest_sha256": sha_file(out / "run_manifest.json"),
            "source_hash_count": len(freeze_manifest["source_hashes"]),
            "files": files,
        },
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["preflight", "study", "freeze"])
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    if args.mode == "preflight":
        selection, manifest = load_freeze()
        print(json.dumps({"status": "PASS", "N": selection["N"], "freeze_source_hashes": len(manifest["source_hashes"]), "arms": ["A_judge_off", "B_judge_on"]}, indent=2))
        return 0
    if args.mode == "study":
        return run_study(args.out)
    freeze_outputs(args.out)
    print(json.dumps(read_json(args.out / "raw_output_manifest.json"), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
