#!/usr/bin/env python3
"""Track A fixed-trace response-evaluation runner.

By default this is a dry run: it validates the frozen command file and the run
contract without sending anything. With ``--base-url`` it drives an already
running loopback ``server_v2`` through ``/api/session/create`` and
``/api/session/command`` using the exact frozen commands.

Track A is *not* closed-loop engagement and cannot establish detection,
suspicion or time-to-suspicion. Any executed run here is ``TEST_ONLY`` until a
real frozen generator is available, and its records must never be pooled with
Track B.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ragin.evaluation.ablation_contract import load_contract, sha256_file, validate_design  # noqa: E402
from ragin.evaluation.attacker_policies import engagement_denominators  # noqa: E402
from ragin.evaluation.records import validate_record  # noqa: E402


def sha_text(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def post(base: str, path: str, payload: dict[str, Any], headers: dict[str, str]) -> tuple[int, dict[str, Any]]:
    request = urllib.request.Request(
        base + path,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            body = response.read()
            status = response.status
    except urllib.error.HTTPError as error:
        body = error.read()
        status = error.code
    try:
        parsed = json.loads(body.decode("utf-8", "replace"))
    except json.JSONDecodeError:
        parsed = {"raw": body.decode("utf-8", "replace")[:2000]}
    return status, parsed


def check_loopback(url: str) -> None:
    parsed = urllib.parse.urlparse(url)
    if parsed.hostname not in {"127.0.0.1", "::1", "localhost"}:
        raise ValueError(f"refusing non-loopback base URL: {url}")
    if parsed.scheme != "http":
        raise ValueError("only plain HTTP loopback is accepted")


def get_health(base: str, *, timeout: float = 15.0) -> dict[str, Any]:
    request = urllib.request.Request(base + "/health", method="GET")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if response.status != 200:
            raise RuntimeError(f"/health returned HTTP {response.status}")
        return json.loads(response.read().decode("utf-8", "replace"))


def check_test_only_health(base: str) -> dict[str, Any]:
    """Refuse to command a server whose inference path is not established.

    A loopback URL proves *transport* locality, not local-weight inference. On
    this host a loopback Ollama endpoint can still be a cloud alias. Until an
    approved bounded plan exists, Track A may only drive a server whose health
    payload explicitly reports no configured provider and a non-provider runtime.
    """
    health = get_health(base)
    problems = []
    if health.get("status") != "healthy":
        problems.append(f"status={health.get('status')!r}")
    provider = health.get("provider")
    if not isinstance(provider, dict):
        problems.append("provider state is absent")
    else:
        if provider.get("configured") is not False:
            problems.append(f"provider.configured={provider.get('configured')!r}; external inference is not excluded")
        if provider.get("api_key_configured") is True:
            problems.append("provider api key is configured")
    runtime_mode = health.get("runtime_mode")
    if runtime_mode not in {"RAGIN_BASELINE", "RAGIN_V4_SUBSTANTIVE_DETERMINISTIC"}:
        problems.append(f"runtime_mode={runtime_mode!r} is not an established non-provider mode")
    result = {
        "schema": "ragin.ablation.track_a.health_gate.v1",
        "status": "PASS" if not problems else "REFUSED",
        "problems": problems,
        "health": health,
        "claim": "server health is a precondition only; it is not proof of local generative inference",
    }
    if problems:
        raise RuntimeError("TEST_ONLY health gate refused: " + "; ".join(problems))
    return result


def write_failure(
    out: Path,
    *,
    records: list[dict[str, Any]],
    failure: dict[str, Any],
    health: dict[str, Any] | None = None,
) -> None:
    """Persist the failed allocation and any partial turns before exiting."""
    (out / "records.jsonl").write_text(
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in records), encoding="utf-8"
    )
    payload = {
        "schema": "ragin.ablation.track_a.failure.v1",
        "status": "FAIL",
        "test_only": True,
        "claim": "TEST_ONLY Track A failure; no measured arm effect",
        "failure": failure,
        "health": health,
        "records": len(records),
    }
    (out / "failure.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / "summary.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    parser.add_argument("--contract", type=Path, default=ROOT / "configs/ablation/eval_v1/run_contract_v1.json")
    parser.add_argument("--trace", type=Path, default=ROOT / "configs/ablation/eval_v1/track_a_frozen_v1.json")
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--allow-test-only", action="store_true")
    parser.add_argument("--out", type=Path, default=Path(f"/tmp/opencode/ragin_ablation_track_a_{stamp}"))
    args = parser.parse_args()

    contract = load_contract(args.contract, repo_root=ROOT)
    design = validate_design(contract)
    if design.status != "DESIGN_VALID":
        print(json.dumps(design.to_dict(), indent=2), file=sys.stderr)
        return 3
    trace = json.loads(args.trace.read_text(encoding="utf-8"))
    expected_hash = (contract.get("bundle") or {}).get("track_a", {}).get("sha256")
    if expected_hash != sha256_file(args.trace):
        print("frozen Track A trace hash does not match the run contract", file=sys.stderr)
        return 3

    if not args.base_url:
        print(
            json.dumps(
                {
                    "mode": "DRY_RUN",
                    "trace_sha256": expected_hash,
                    "scenarios": [
                        {"scenario_id": item["scenario_id"], "commands": item["commands"]}
                        for item in trace["scenarios"]
                    ],
                    "claim": "Track A cannot establish engagement, detection or suspicion",
                },
                indent=2,
            )
        )
        return 0
    if not args.allow_test_only:
        print("refusing to execute without --allow-test-only: no frozen generator is available", file=sys.stderr)
        return 2
    if not args.api_key:
        print("--api-key is required for the loopback server", file=sys.stderr)
        return 2
    check_loopback(args.base_url)
    if args.out.exists():
        print(f"refusing to overwrite: {args.out}", file=sys.stderr)
        return 2
    args.out.mkdir(parents=True)

    records: list[dict[str, Any]] = []
    health: dict[str, Any] | None = None
    try:
        health = check_test_only_health(args.base_url)
    except Exception as exc:  # noqa: BLE001 - refused health is persisted, never hidden
        write_failure(
            args.out,
            records=records,
            failure={"stage": "HEALTH_GATE", "error": f"{type(exc).__name__}: {exc}"},
        )
        print(f"health gate failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    def base_record(
        scenario: dict[str, Any],
        turns: list[dict[str, Any]],
        *,
        cause: str,
        event_turn: int,
    ) -> dict[str, Any]:
        commands = [turn["command"] for turn in turns if turn.get("serve_status") in {"SERVED", "EMPTY"}]
        return {
            "schema": "ragin.ablation.session_record.v1",
            "record_id": f"TESTONLY-TRACKA-{scenario['scenario_id']}-{stamp}",
            "track": "A",
            "test_only": True,
            "test_label": "TEST_ONLY_TRACK_A_DETERMINISTIC_RESPONSE_SMOKE",
            "split": "development",
            "block_id": f"TRACKA::{scenario['scenario_id']}",
            "allocation_index": 0,
            "arm": "B1",
            "scenario_id": scenario["scenario_id"],
            "profile_id": "FIXED_TRACE",
            "seed": 0,
            "provenance": {
                "transport": "LOOPBACK_HTTP_SERVER_V2",
                "generator": "UNOBSERVED_DETERMINISTIC_RUNTIME",
                "llm_inference": "NOT_ESTABLISHED",
                "mock": False,
            },
            "turns": turns,
            "terminal_cause": cause,
            "detection_turn": None,
            "event_turn": event_turn,
            "objective_action_indices": [],
            "operational": engagement_denominators(commands),
            "verification": {"profile": "TEST_ONLY_SERVER_REPORTED", "passed": bool(turns) and all(
                turn.get("verification", {}).get("passed") is True for turn in turns
            )},
            "analysis_eligible": False,
        }

    for scenario in trace["scenarios"]:
        status, created = post(
            args.base_url,
            "/api/session/create",
            {"source_ip": "127.0.0.1", "max_commands": len(scenario["commands"]) + 4},
            {"X-API-Key": args.api_key},
        )
        if status != 200 or not created.get("session_id"):
            record = base_record(scenario, [], cause="UNAVAILABLE", event_turn=0)
            records.append(record)
            write_failure(
                args.out,
                records=records,
                failure={
                    "stage": "SESSION_CREATE",
                    "scenario_id": scenario["scenario_id"],
                    "http_status": status,
                    "response": created if isinstance(created, dict) else str(created),
                },
                health=health,
            )
            print(f"session create failed: HTTP {status} {created}", file=sys.stderr)
            return 1
        session_id = created["session_id"]
        headers = {"X-API-Key": args.api_key, "X-Session-Token": created.get("session_token", "")}
        turns: list[dict[str, Any]] = []
        failed = False
        for index, command in enumerate(scenario["commands"], start=1):
            started = time.perf_counter()
            status, parsed = post(
                args.base_url,
                "/api/session/command",
                {"session_id": session_id, "command": command},
                headers,
            )
            latency_ms = (time.perf_counter() - started) * 1000.0
            if status != 200:
                turns.append(
                    {
                        "turn": index,
                        "command": command,
                        "input_redacted": command,
                        "raw_input_sha256": sha_text(command),
                        "serve_status": "FAILED",
                        "failure_reason": f"HTTP {status}: {str(parsed)[:300]}",
                        "served_text": "",
                        "served_text_sha256": sha_text(""),
                        "served_raw_sha256": None,
                        "served_sha256": None,
                        "served_availability": "UNAVAILABLE",
                        "candidate_sha256": None,
                        "verified_sha256": None,
                        "generation_kind": "UNAVAILABLE",
                        "decision_consumed": False,
                        "arm_exposure": "UNAVAILABLE",
                        "model_exposure": {"observed": False},
                        "verification": {"profile": "TEST_ONLY_SERVER_REPORTED", "passed": False},
                        "latency_ms": {"availability": "MEASURED", "value": latency_ms},
                        "tokens_in": {"availability": "UNAVAILABLE"},
                        "tokens_out": {"availability": "UNAVAILABLE"},
                        "cost_usd": {"availability": "UNAVAILABLE"},
                    }
                )
                failed = True
                break
            served = parsed.get("response_text") or ""
            empty = not bool(str(served).strip())
            candidate = parsed.get("candidate_sha256")
            verified = parsed.get("served_response_sha256")
            turns.append(
                {
                    "turn": index,
                    "command": command,
                    "input_redacted": command,
                    "raw_input_sha256": sha_text(command),
                    "serve_status": "EMPTY" if empty else "SERVED",
                    "failure_reason": "server returned a legitimate empty response" if empty else None,
                    "served_text": served,
                    "served_text_sha256": sha_text(served),
                    "served_raw_sha256": sha_text(served) if not empty else None,
                    "served_sha256": sha_text(served) if not empty else None,
                    "served_availability": "UNAVAILABLE" if empty else "RAW",
                    "candidate_sha256": candidate,
                    "verified_sha256": verified,
                    "generation_kind": "TEMPLATE" if not candidate else "GENERATED",
                    "decision_consumed": bool(parsed.get("decision_consumed", False)),
                    "arm_exposure": "OBSERVED",
                    "model_exposure": {"observed": False},
                    "verification": {
                        "profile": "TEST_ONLY_SERVER_REPORTED",
                        "passed": bool((parsed.get("verification") or {}).get("passed")),
                    },
                    "latency_ms": {"availability": "MEASURED", "value": latency_ms},
                    "tokens_in": {"availability": "UNAVAILABLE"},
                    "tokens_out": {"availability": "UNAVAILABLE"},
                    "cost_usd": {"availability": "UNAVAILABLE"},
                }
            )
        record = base_record(
            scenario,
            turns,
            cause="TECHNICAL_FAILURE" if failed else "OBJECTIVE_COMPLETION",
            event_turn=len(turns) if turns else 0,
        )
        if failed:
            record["technical_reason"] = "loopback command failed; partial turns preserved above"
        errors = validate_record(record)
        records.append(record)
        if errors:
            write_failure(
                args.out,
                records=records,
                failure={
                    "stage": "RECORD_VALIDATION",
                    "scenario_id": scenario["scenario_id"],
                    "errors": errors,
                },
                health=health,
            )
            print(json.dumps({"record_id": record["record_id"], "errors": errors}, indent=2), file=sys.stderr)
            return 1
        if failed:
            write_failure(
                args.out,
                records=records,
                failure={
                    "stage": "SESSION_COMMAND",
                    "scenario_id": scenario["scenario_id"],
                    "partial_turns": len(turns),
                },
                health=health,
            )
            return 1
    (args.out / "records.jsonl").write_text(
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in records), encoding="utf-8"
    )
    summary = {
        "schema": "ragin.ablation.track_a.smoke_summary.v1",
        "status": "PASS",
        "test_only": True,
        "claim": "TEST_ONLY Track A response mechanics; not engagement and not a measured arm effect",
        "records": len(records),
        "trace_sha256": expected_hash,
        "health_gate": health.get("status") if health else "NOT_RUN",
        "record_sha256": hashlib.sha256((args.out / "records.jsonl").read_bytes()).hexdigest(),
    }
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
