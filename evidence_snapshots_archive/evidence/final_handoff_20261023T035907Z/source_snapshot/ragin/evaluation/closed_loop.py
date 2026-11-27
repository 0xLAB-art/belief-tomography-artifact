"""Closed-loop Track B runner core.

Each next command is produced by the policy from the *served output of the
previous turn* (or, for turn 1, from the frozen scenario). A fixed replay list
is not a closed loop and is not accepted here. The transport is injected so the
same controller can drive a real native Cowrie SSH session (B0 development
smoke) or a future frozen-generator arm without changing the record contract.

This module never launches containers, opens listeners or calls a model. The
CLI runner owns those bounded, explicit operations.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from typing import Any, Protocol

from ragin.capture_v4.privacy import bounded_redacted_text
from ragin.evaluation.attacker_policies import (
    Action,
    AttackerHistory,
    ScriptedPolicy,
    engagement_denominators,
)
from ragin.evaluation.records import SCHEMA, sha256_text

TURN_CAP = 12


class TransportError(RuntimeError):
    """A transport failure is recorded, never replaced."""


class LoopTransport(Protocol):
    def execute(self, command: str) -> dict[str, Any]: ...

    def close(self) -> None: ...


@dataclass
class SessionMeta:
    record_id: str
    track: str
    split: str
    block_id: str
    allocation_index: int
    arm: str
    scenario_id: str
    profile_id: str
    seed: int
    test_only: bool
    test_label: str | None
    provenance: dict[str, Any]
    verification_profile: str
    model_exposure: dict[str, Any] = field(default_factory=dict)


def _measurement(value: Any) -> dict[str, Any]:
    if isinstance(value, dict) and value.get("availability") in {"MEASURED", "ESTIMATED", "UNAVAILABLE"}:
        payload = dict(value)
        candidate = payload.get("value")
        if payload.get("availability") != "UNAVAILABLE" and (
            isinstance(candidate, bool)
            or not isinstance(candidate, (int, float))
            or not math.isfinite(float(candidate))
            or float(candidate) < 0
        ):
            return {"availability": "UNAVAILABLE"}
        return payload
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)) or value < 0:
        return {"availability": "UNAVAILABLE"}
    return {"availability": "MEASURED", "value": float(value)}


def _turn_from_transport(
    *,
    index: int,
    command: str,
    response: dict[str, Any],
    meta: SessionMeta,
) -> dict[str, Any]:
    served_text = response.get("served_text")
    if not isinstance(served_text, str):
        raise TransportError("transport returned a non-string served_text")
    serve_status = str(response.get("serve_status", "SERVED"))
    if serve_status not in {"SERVED", "EMPTY", "REJECTED", "FAILED", "UNAVAILABLE"}:
        raise TransportError(f"transport returned an invalid serve_status: {serve_status!r}")
    if serve_status == "SERVED" and not served_text:
        raise TransportError("transport marked an empty response as SERVED")
    served_sha = sha256_text(served_text)
    reported = response.get("served_sha256")
    if reported is not None and reported != served_sha:
        raise TransportError("transport served hash does not match the served bytes")
    verified = response.get("verified_sha256")
    if verified is not None and verified != served_sha:
        raise TransportError("verified hash does not match the served bytes")
    kind = response.get("generation_kind", "NATIVE_SHELL")
    redacted = bounded_redacted_text(command, limit=400)
    verification = response.get("verification") or {}
    if not isinstance(verification, dict):
        verification = {}
    verification.setdefault("profile", meta.verification_profile)
    verification.setdefault("passed", bool(verification.get("passed")) if "passed" in verification else False)
    served = serve_status == "SERVED"
    raw_sha = served_sha if served else None
    failure_reason = response.get("failure_reason")
    if not served and not failure_reason:
        failure_reason = f"transport reported serve_status={serve_status}"
    return {
        "turn": index,
        "command": command,
        "command_redacted": redacted["text"],
        "input_redacted": redacted["text"],
        "raw_input_sha256": sha256_text(command),
        "serve_status": serve_status,
        "failure_reason": failure_reason,
        "served_text": served_text,
        "served_text_sha256": served_sha,
        "served_raw_sha256": raw_sha,
        "served_sha256": raw_sha,
        "served_availability": "RAW" if served else "UNAVAILABLE",
        "candidate_sha256": response.get("candidate_sha256") if served else None,
        "verified_sha256": verified if served else None,
        "generation_kind": kind,
        "decision_consumed": bool(response.get("decision_consumed")),
        "arm_exposure": response.get("arm_exposure", "OBSERVED"),
        "model_exposure": response.get("model_exposure") or meta.model_exposure or {"observed": False},
        "verification": verification,
        "latency_ms": _measurement(response.get("latency_ms")),
        "tokens_in": _measurement(response.get("tokens_in")),
        "tokens_out": _measurement(response.get("tokens_out")),
        "cost_usd": _measurement(response.get("cost_usd")),
        "transport_sha256": response.get("transport_sha256"),
        "redaction": {
            "input_method": "minimize_then_truncate",
            "served_text": "retained raw because it is the experimental stimulus",
        },
    }


def failed_turn(*, index: int, command: str, meta: SessionMeta, reason: str) -> dict[str, Any]:
    """Represent an attempted-but-failed turn instead of dropping it."""
    redacted = bounded_redacted_text(command, limit=400)
    empty_sha = hashlib.sha256(b"").hexdigest()
    return {
        "turn": index,
        "command": command,
        "command_redacted": redacted["text"],
        "input_redacted": redacted["text"],
        "raw_input_sha256": sha256_text(command),
        "serve_status": "FAILED",
        "failure_reason": reason[:500],
        "served_text": "",
        "served_text_sha256": empty_sha,
        "served_raw_sha256": None,
        "served_sha256": None,
        "served_availability": "UNAVAILABLE",
        "candidate_sha256": None,
        "verified_sha256": None,
        "generation_kind": "UNAVAILABLE",
        "decision_consumed": False,
        "arm_exposure": "UNAVAILABLE",
        "model_exposure": meta.model_exposure or {"observed": False},
        "verification": {"profile": meta.verification_profile, "passed": False},
        "latency_ms": {"availability": "UNAVAILABLE"},
        "tokens_in": {"availability": "UNAVAILABLE"},
        "tokens_out": {"availability": "UNAVAILABLE"},
        "cost_usd": {"availability": "UNAVAILABLE"},
        "redaction": {"input_method": "minimize_then_truncate", "served_text": "no bytes served"},
    }


def run_session(
    meta: SessionMeta,
    policy: ScriptedPolicy,
    transport: LoopTransport,
    *,
    max_turns: int = TURN_CAP,
    objective_turns: set[int] | None = None,
    on_event: Any | None = None,
) -> dict[str, Any]:
    """Drive one closed-loop session and return a validated-shape record."""
    if max_turns < 1 or max_turns > TURN_CAP:
        raise ValueError(f"max_turns must be 1..{TURN_CAP}")
    history = AttackerHistory()
    turns: list[dict[str, Any]] = []
    actions: list[Action] = []
    terminal_cause = "TURN_CAP" if max_turns == TURN_CAP else "ADMIN_CENSORED"
    event_turn: int | None = None
    technical_reason: str | None = None
    objectives = set(objective_turns or set())

    def declared_cause(action: Action) -> str | None:
        if action.declares_detection:
            return "DETECTION"
        if action.declares_abandonment:
            return "ABANDONMENT"
        if action.declares_objective_complete:
            return "OBJECTIVE_COMPLETION"
        return None

    for index in range(1, max_turns + 1):
        action = policy.next_action(history)
        actions.append(action)
        declaration = declared_cause(action)
        try:
            response = transport.execute(action.command)
            turn = _turn_from_transport(index=index, command=action.command, response=response, meta=meta)
        except Exception as exc:  # noqa: BLE001 - preserve execute AND conversion failures
            technical_reason = f"{type(exc).__name__}: {exc}"
            turn = failed_turn(index=index, command=action.command, meta=meta, reason=technical_reason)
            turn["transport_failure"] = technical_reason
        # Attacker-side evidence is observed before the transport attempt. It
        # survives a failed outgoing command and is never reconstructed later.
        turn["attacker_rationale"] = action.rationale
        turn["attacker_declares_detection"] = action.declares_detection
        turn["attacker_declares_abandonment"] = action.declares_abandonment
        turn["attacker_declares_objective_complete"] = action.declares_objective_complete
        turn["attacker_suspicion_statement"] = action.rationale if action.declares_detection else None
        turns.append(turn)
        history.commands.append(action.command)
        history.served_outputs.append(str(turn.get("served_text") or ""))
        if on_event is not None:
            on_event({"type": "turn", "turn": index, "action": action.to_dict(), "record_turn": turn})

        # An explicit attacker declaration is the event. A failed outgoing
        # command is recorded as a transport failure on that turn, but it does
        # not erase or relabel the declaration.
        if declaration is not None:
            terminal_cause = declaration
            event_turn = index
            break
        if turn.get("serve_status") in {"FAILED", "REJECTED", "UNAVAILABLE"}:
            terminal_cause = "TECHNICAL_FAILURE"
            event_turn = index
            break
    else:
        terminal_cause = "TURN_CAP" if max_turns == TURN_CAP else "ADMIN_CENSORED"
        event_turn = max_turns

    eligible = [
        (index, turn)
        for index, turn in enumerate(turns)
        if turn.get("serve_status") in {"SERVED", "EMPTY"}
    ]
    commands = [str(turn["command"]) for _, turn in eligible]
    index_map = {original: position for position, (original, _) in enumerate(eligible)}
    eligible_objectives = sorted(objectives & set(index_map))
    denominators = engagement_denominators(
        commands, objective_actions=[index_map[index] for index in eligible_objectives]
    )
    record: dict[str, Any] = {
        "schema": SCHEMA,
        "record_id": meta.record_id,
        "track": meta.track,
        "test_only": meta.test_only,
        "test_label": meta.test_label,
        "split": meta.split,
        "block_id": meta.block_id,
        "allocation_index": meta.allocation_index,
        "arm": meta.arm,
        "scenario_id": meta.scenario_id,
        "profile_id": meta.profile_id,
        "seed": meta.seed,
        "provenance": meta.provenance,
        "turns": turns,
        "terminal_cause": terminal_cause,
        "detection_turn": event_turn if terminal_cause == "DETECTION" else None,
        "event_turn": event_turn,
        "technical_reason": technical_reason,
        "objective_action_indices": eligible_objectives,
        "attacker_actions": [{"turn": index, **action.to_dict()} for index, action in enumerate(actions, start=1)],
        "operational": denominators,
        "verification": {"profile": meta.verification_profile, "passed": all(
            turn["verification"].get("passed") is True for turn in turns
        ) if turns else False},
        "policy": {"profile_id": policy.policy_id, "kind": policy.kind},
    }
    return record


class HttpLoopbackTransport:
    """Minimal read-only client for an already-running loopback server.

    The caller must validate the URL host is loopback before constructing this
    transport. This class does not start a server and does not retry.
    """

    def __init__(self, *, base_url: str, api_key: str, session_id: str, timeout: float = 120.0) -> None:
        from urllib.parse import urlparse

        parsed = urlparse(base_url)
        if parsed.hostname not in {"127.0.0.1", "::1", "localhost"}:
            raise ValueError("HttpLoopbackTransport only accepts loopback URLs")
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("unsupported URL scheme")
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.session_id = session_id
        self.timeout = timeout

    def execute(self, command: str) -> dict[str, Any]:
        import json
        import time
        import urllib.error
        import urllib.request

        payload = json.dumps({"session_id": self.session_id, "command": command}).encode()
        request = urllib.request.Request(
            self.base_url + "/api/session/command",
            data=payload,
            headers={"Content-Type": "application/json", "X-API-Key": self.api_key},
            method="POST",
        )
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = response.read()
                status = response.status
        except urllib.error.HTTPError as error:
            body = error.read()
            status = error.code
        latency_ms = (time.perf_counter() - started) * 1000.0
        parsed = json.loads(body.decode("utf-8", "replace"))
        if status != 200:
            raise TransportError(f"loopback serve failed with HTTP {status}: {parsed.get('error')!r}")
        return {
            "served_text": parsed.get("response_text", ""),
            "served_sha256": parsed.get("served_response_sha256"),
            "candidate_sha256": parsed.get("candidate_sha256"),
            "verified_sha256": parsed.get("verified_sha256"),
            "verification": parsed.get("verification") or {},
            "generation_kind": parsed.get("generation_kind", "GENERATED"),
            "decision_consumed": bool(parsed.get("decision_consumed", False)),
            "arm_exposure": parsed.get("arm_exposure", "OBSERVED"),
            "model_exposure": parsed.get("model_exposure") or {"observed": False},
            "latency_ms": {"availability": "MEASURED", "value": latency_ms},
        }

    def close(self) -> None:
        return None
