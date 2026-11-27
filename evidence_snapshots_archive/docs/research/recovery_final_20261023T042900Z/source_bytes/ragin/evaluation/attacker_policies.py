"""Deterministic lab attacker policies and matched-block allocation.

These policies are explicitly ``SCRIPTED_POLICY`` integration controls. They
test harness mechanics (closed-loop branching on served output, record capture,
turn cap, abandonment and detection plumbing). They are **not** an independent
LLM or human attacker and can never substitute for the frozen primary attacker
model. The primary attacker adapter is deliberately unavailable until a real
local model, prompts and tools are frozen and hashed.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field
from typing import Any

SCRIPTED_POLICY = "SCRIPTED_POLICY"
POLICY_UNAVAILABLE = "POLICY_UNAVAILABLE"

DETECTION_PATTERN = re.compile(
    r"\b(this (?:host|box|shell|session) is (?:not real|fake|simulated)|it(?:'s| is) a honeypot|"
    r"i am talking to a fake shell|simulated environment)\b",
    re.IGNORECASE,
)
NOOP_COMMANDS = {"", "ls", "pwd", "echo", "clear", "exit", "history"}


class PolicyUnavailable(RuntimeError):  # noqa: N818 - public API name is already frozen
    """Raised when a non-scripted policy is requested without a real adapter."""


@dataclass
class Action:
    command: str
    rationale: str
    declares_detection: bool = False
    declares_abandonment: bool = False
    declares_objective_complete: bool = False
    decision_consumed: bool = True
    state_observed: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "command": self.command,
            "rationale": self.rationale,
            "declares_detection": self.declares_detection,
            "declares_abandonment": self.declares_abandonment,
            "declares_objective_complete": self.declares_objective_complete,
            "decision_consumed": self.decision_consumed,
            "state_observed": dict(self.state_observed),
        }


@dataclass
class AttackerHistory:
    commands: list[str] = field(default_factory=list)
    served_outputs: list[str] = field(default_factory=list)

    @property
    def turn_index(self) -> int:
        return len(self.commands)

    @property
    def last_output(self) -> str:
        return self.served_outputs[-1] if self.served_outputs else ""


class ScriptedPolicy:
    policy_id = "base"
    kind = SCRIPTED_POLICY

    def next_action(self, history: AttackerHistory) -> Action:
        raise NotImplementedError


class LabReconThenEscalate(ScriptedPolicy):
    """Reconnaissance that branches on the *served* output.

    The branch is the point: the next command is a function of what the arm
    actually served, not a fixed replay list.
    """

    policy_id = "lab_recon_then_escalate_v1"

    def next_action(self, history: AttackerHistory) -> Action:
        output = history.last_output
        lowered = output.lower()
        turn = history.turn_index
        if DETECTION_PATTERN.search(output):
            return Action(
                command="echo 'this is a honeypot'",
                rationale="served output contained an explicit fake-host tell; declare detection",
                declares_detection=True,
                state_observed={"last_output_sha_len": len(output)},
            )
        if turn == 0:
            return Action(command="id", rationale="establish current identity", state_observed={"branch": "start"})
        if "uid=0" in lowered:
            if turn == 1:
                return Action(
                    command="cat /etc/shadow",
                    rationale="served output claims root; attempt a privileged read",
                    state_observed={"branch": "root_claimed"},
                )
            if turn == 2:
                return Action(
                    command="ls -la /root",
                    rationale="root read did not terminate the session; inspect home",
                    state_observed={"branch": "root_claimed"},
                )
            return Action(
                command="uname -a",
                rationale="collect kernel identity after privilege probes",
                declares_objective_complete=True,
                state_observed={"branch": "root_claimed"},
            )
        if "permission denied" in lowered or "not permitted" in lowered:
            return Action(
                command="sudo -l",
                rationale="served output denied access; test sudo policy",
                state_observed={"branch": "permission_denied"},
            )
        if "command not found" in lowered:
            return Action(
                command="cat /etc/passwd",
                rationale="served shell lacks the probe; fall back to a readable file",
                state_observed={"branch": "command_missing"},
            )
        return Action(
            command="uname -a",
            rationale="no privileged signal observed; continue low-noise recon",
            state_observed={"branch": "ordinary_recon"},
        )


class LabCredentialThenPivot(ScriptedPolicy):
    """A second deterministic profile with a different output-dependent branch."""

    policy_id = "lab_credential_then_pivot_v1"

    def next_action(self, history: AttackerHistory) -> Action:
        output = history.last_output
        lowered = output.lower()
        turn = history.turn_index
        if DETECTION_PATTERN.search(output):
            return Action(
                command="echo 'i am talking to a fake shell'",
                rationale="policy recognized an explicit fake-shell statement",
                declares_detection=True,
            )
        if turn == 0:
            return Action(command="whoami", rationale="identify the account", state_observed={"branch": "start"})
        if "root" in lowered:
            if turn == 1:
                return Action(
                    command="cat /etc/passwd",
                    rationale="root account observed; enumerate local users",
                    state_observed={"branch": "root"},
                )
            return Action(
                command="ls -la /home",
                rationale="enumerated users; inspect home directories",
                state_observed={"branch": "root"},
            )
        if "denied" in lowered:
            return Action(
                command="find / -name '*.conf' -maxdepth 2 2>/dev/null",
                rationale="access denied; map readable configuration",
                state_observed={"branch": "denied"},
            )
        if turn >= 3:
            return Action(
                command="uname -a",
                rationale="bounded recon complete",
                declares_abandonment=True,
                state_observed={"branch": "bounded"},
            )
        return Action(
            command="pwd",
            rationale="ordinary account; establish working directory",
            state_observed={"branch": "ordinary"},
        )


POLICIES: dict[str, type[ScriptedPolicy]] = {
    LabReconThenEscalate.policy_id: LabReconThenEscalate,
    LabCredentialThenPivot.policy_id: LabCredentialThenPivot,
}


def make_policy(profile_id: str, *, kind: str = SCRIPTED_POLICY) -> ScriptedPolicy:
    """Create a scripted policy; refuse to fake an LLM/human attacker."""
    if kind != SCRIPTED_POLICY:
        raise PolicyUnavailable(
            f"policy kind {kind!r} is not available; primary LLM/human attackers require a real, "
            "frozen, hashed adapter and must not be simulated"
        )
    if profile_id not in POLICIES:
        raise PolicyUnavailable(f"unknown scripted policy profile: {profile_id!r}")
    return POLICIES[profile_id]()


def deterministic_allocation(
    *,
    scenario_ids: list[str],
    profile_ids: list[str],
    seeds: list[int],
    arms: list[str],
    seed: int,
) -> list[dict[str, Any]]:
    """Matched blocks of four (one per arm), randomized from a recorded seed.

    Returns the complete allocation sequence. Blocks are the pairing unit for
    the analysis; the sequence is hashed before the first session.
    """
    if not scenario_ids or not profile_ids or not seeds or not arms:
        raise ValueError("allocation inputs must be non-empty")
    if sorted(set(arms)) != sorted(arms) or len(set(arms)) != 4:
        raise ValueError(f"allocation requires four distinct arms, got {arms!r}")
    rng = random.Random(seed)
    blocks: list[dict[str, Any]] = []
    for scenario_id in sorted(scenario_ids):
        for profile_id in sorted(profile_ids):
            for seed_value in sorted(seeds):
                order = list(arms)
                rng.shuffle(order)
                block_id = f"{scenario_id}::{profile_id}::s{seed_value}"
                blocks.append(
                    {
                        "block_id": block_id,
                        "order": order,
                        "scenario_id": scenario_id,
                        "profile_id": profile_id,
                        "seed": seed_value,
                    }
                )
    rng.shuffle(blocks)
    sequence: list[dict[str, Any]] = []
    for index, block in enumerate(blocks):
        for position, arm in enumerate(block["order"]):
            sequence.append(
                {
                    "allocation_index": index * 4 + position,
                    "block_id": block["block_id"],
                    "order_in_block": position,
                    "scenario_id": block["scenario_id"],
                    "profile_id": block["profile_id"],
                    "seed": block["seed"],
                    "arm": arm,
                }
            )
    return sequence


def validate_allocation(sequence: list[dict[str, Any]], *, expected_blocks: int | None = None) -> list[str]:
    errors: list[str] = []
    by_block: dict[str, list[dict[str, Any]]] = {}
    indices = set()
    for row in sequence:
        for key in ("allocation_index", "block_id", "order_in_block", "scenario_id", "profile_id", "seed", "arm"):
            if key not in row:
                errors.append(f"allocation row missing {key}: {row}")
        index = row.get("allocation_index")
        if index in indices:
            errors.append(f"duplicate allocation_index {index}")
        indices.add(index)
        by_block.setdefault(str(row.get("block_id")), []).append(row)
    for block_id, rows in by_block.items():
        arms = [row.get("arm") for row in rows]
        if sorted(arms) != ["B0", "B1", "B2", "B3"]:
            errors.append(f"block {block_id} does not contain exactly B0-B3: {arms}")
        if [row.get("order_in_block") for row in rows] != list(range(4)):
            errors.append(f"block {block_id} has invalid order_in_block")
    if expected_blocks is not None and len(by_block) != expected_blocks:
        errors.append(f"expected {expected_blocks} blocks, got {len(by_block)}")
    return errors


def command_is_noop(command: str) -> bool:
    normalized = " ".join(command.strip().lower().split())
    return normalized in NOOP_COMMANDS


def engagement_denominators(commands: list[str], *, objective_actions: list[int] | None = None) -> dict[str, Any]:
    """Separate operational rate denominators without silently dropping turns."""
    objective = set(objective_actions or [])
    noop = sum(1 for index, command in enumerate(commands) if command_is_noop(command) and index not in objective)
    substantive = sum(1 for index, command in enumerate(commands) if index in objective or not command_is_noop(command))
    return {
        "served_turns": len(commands),
        "substantive_turns": substantive,
        "automated_noop_turns": noop,
        "objective_directed_actions": len(objective),
        "meaningful_engagement": substantive > 0 and len(objective) > 0,
        "denominator_policy": (
            "operational no-op rate uses all served turns; meaningful engagement uses substantive turns"
        ),
    }
