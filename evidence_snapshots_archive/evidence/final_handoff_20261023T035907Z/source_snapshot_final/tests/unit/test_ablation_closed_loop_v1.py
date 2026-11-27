"""Closed-loop session tests: declarations, transport failures, and EMPTY.

The interpreter must be started with unique RAGIN_SESSION_DIR and
RAGIN_HOST_FICTION_PATH values; these assignments are a defensive fallback and
never point at the repository's historical/default session directory.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

os.environ.setdefault("RAGIN_SESSION_DIR", tempfile.mkdtemp(prefix="ragin-ablation-loop-session-"))
os.environ.setdefault(
    "RAGIN_HOST_FICTION_PATH",
    str(Path(tempfile.mkdtemp(prefix="ragin-ablation-loop-fiction-")) / "host_fiction.json"),
)

from ragin.evaluation.attacker_policies import Action  # noqa: E402
from ragin.evaluation.closed_loop import (  # noqa: E402
    SessionMeta,
    TransportError,
    run_session,
)
from ragin.evaluation.records import validate_record  # noqa: E402


class DeclaringPolicy:
    """Returns one fixed action and records that it was produced first."""

    policy_id = "unit_declaring_policy"
    kind = "SCRIPTED_POLICY"

    def __init__(self, action: Action) -> None:
        self.action = action
        self.calls = 0
        self.declared_before_execute = False

    def next_action(self, history) -> Action:
        self.calls += 1
        assert self.calls == 1
        self.declared_before_execute = True
        return self.action


class ExplodingTransport:
    """Fails the outgoing command after the declaration has been produced."""

    def __init__(self, policy: DeclaringPolicy, message: str = "outgoing command transport failed") -> None:
        self.policy = policy
        self.message = message
        self.executed = False

    def execute(self, command: str) -> dict:
        self.executed = True
        assert self.policy.declared_before_execute is True
        raise TransportError(self.message)

    def close(self) -> None:
        return None


class FixedResponseTransport:
    """Returns a fixed response after the declaration has been produced."""

    def __init__(self, policy: DeclaringPolicy, response: dict) -> None:
        self.policy = policy
        self.response = response
        self.executed = False

    def execute(self, command: str) -> dict:
        self.executed = True
        assert self.policy.declared_before_execute is True
        return dict(self.response)

    def close(self) -> None:
        return None


def meta(**overrides) -> SessionMeta:
    values = {
        "record_id": "TESTSESSION-1",
        "track": "B",
        "split": "development",
        "block_id": "scenario::profile::s1",
        "allocation_index": 0,
        "arm": "B0",
        "scenario_id": "scenario",
        "profile_id": "profile",
        "seed": 1,
        "test_only": True,
        "test_label": "TEST_ONLY_UNIT_SESSION",
        "provenance": {
            "transport": "UNIT_FAKE",
            "generator": "NONE",
            "llm_inference": "NOT_ESTABLISHED",
            "mock": False,
        },
        "verification_profile": "NATIVE_TRANSPORT_ONLY",
        "model_exposure": {"observed": False},
    }
    values.update(overrides)
    return SessionMeta(**values)


def detection_action() -> Action:
    return Action(
        command="echo 'this is a honeypot'",
        rationale="the served banner and filesystem are synthetic; declaring detection",
        declares_detection=True,
    )


def assert_detection_preserved_after_failure(record: dict, policy: DeclaringPolicy, transport) -> None:
    assert policy.declared_before_execute is True
    assert transport.executed is True
    assert record["terminal_cause"] == "DETECTION"
    assert record["detection_turn"] == 1
    assert record["event_turn"] == 1
    assert record["technical_reason"]
    assert len(record["turns"]) == 1

    turn = record["turns"][0]
    assert turn["serve_status"] == "FAILED"
    assert turn["served_text"] == ""
    assert turn["failure_reason"]
    assert turn["transport_failure"] == record["technical_reason"]
    assert turn["attacker_declares_detection"] is True
    assert turn["attacker_rationale"] == policy.action.rationale
    assert turn["attacker_suspicion_statement"] == policy.action.rationale
    assert record["attacker_actions"] == [
        {"turn": 1, **policy.action.to_dict()},
    ]
    assert validate_record(record) == []


def test_declaration_is_observed_before_execute_and_survives_transport_failure() -> None:
    policy = DeclaringPolicy(detection_action())
    transport = ExplodingTransport(policy)

    record = run_session(meta(), policy, transport, max_turns=12)

    assert "TransportError" in record["technical_reason"]
    assert "outgoing command transport failed" in record["technical_reason"]
    assert_detection_preserved_after_failure(record, policy, transport)


def test_declaration_survives_response_conversion_failure() -> None:
    policy = DeclaringPolicy(detection_action())
    # A non-string served_text cannot be converted into a valid turn.
    transport = FixedResponseTransport(policy, {"served_text": 123, "serve_status": "SERVED"})

    record = run_session(meta(), policy, transport, max_turns=12)

    assert "TransportError" in record["technical_reason"]
    assert "non-string served_text" in record["technical_reason"]
    assert_detection_preserved_after_failure(record, policy, transport)


def test_failure_without_declaration_becomes_technical_failure() -> None:
    action = Action(command="id", rationale="establish current identity", declares_detection=False)
    policy = DeclaringPolicy(action)
    transport = ExplodingTransport(policy)

    record = run_session(meta(), policy, transport, max_turns=12)

    assert record["terminal_cause"] == "TECHNICAL_FAILURE"
    assert record["event_turn"] == 1
    assert record["detection_turn"] is None
    assert "TransportError" in record["technical_reason"]
    turn = record["turns"][0]
    assert turn["serve_status"] == "FAILED"
    assert turn["transport_failure"] == record["technical_reason"]
    assert turn["attacker_rationale"] == action.rationale
    assert turn["attacker_suspicion_statement"] is None
    assert turn["attacker_declares_detection"] is False
    assert record["attacker_actions"][0]["rationale"] == action.rationale
    assert validate_record(record) == []


def test_empty_native_output_remains_empty_and_valid() -> None:
    action = Action(command="true", rationale="probe the shell", declares_detection=False)
    policy = DeclaringPolicy(action)
    transport = FixedResponseTransport(
        policy,
        {
            "served_text": "",
            "serve_status": "EMPTY",
            "generation_kind": "NATIVE_SHELL",
            "verification": {"passed": False},
        },
    )

    record = run_session(meta(), policy, transport, max_turns=1)

    assert record["terminal_cause"] == "ADMIN_CENSORED"
    assert record["event_turn"] == 1
    assert record["detection_turn"] is None
    assert record["technical_reason"] is None
    assert len(record["turns"]) == 1
    turn = record["turns"][0]
    assert turn["serve_status"] == "EMPTY"
    assert turn["served_text"] == ""
    assert turn["generation_kind"] == "NATIVE_SHELL"
    assert turn["failure_reason"]
    assert "transport_failure" not in turn
    assert turn["attacker_suspicion_statement"] is None
    assert validate_record(record) == []
