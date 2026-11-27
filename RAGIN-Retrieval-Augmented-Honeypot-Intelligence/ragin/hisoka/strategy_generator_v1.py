from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any

from ragin.decision_fusion_v4.benchmark import ALLOWED_STRATEGIES
from ragin.hisoka.deception import ResponseGenerator

STRATEGY_GENERATOR_VERSION = "V1_SUBSTANTIVE_STRATEGY_GENERATOR"
_NON_BASELINE = set(ALLOWED_STRATEGIES) - {"baseline"}
_SIMULATED_ACTIONS = {
    "cat", "configure", "credentials", "deploy", "discover", "find", "help",
    "history", "hostname", "id", "inspect", "list", "network", "operations",
    "ps", "services", "status", "topology", "visit",
}
_COMMAND_RE = re.compile(r"[A-Za-z0-9_./:@=+,-]+")


@dataclass(frozen=True)
class FictionalState:
    session_id: str
    seed: int
    visits: int = 0
    discovered_paths: tuple[str, ...] = ()
    discovered_services: tuple[str, ...] = ()
    completed_operations: tuple[str, ...] = ()
    decoy_credentials: tuple[str, ...] = ()
    topology_hosts: tuple[str, ...] = ()
    topology_services: tuple[str, ...] = ()
    contained_resources: tuple[str, ...] = ()
    telemetry_events: tuple[str, ...] = ()


@dataclass(frozen=True)
class StrategyCandidate:
    response_text: str
    proposed_state: FictionalState
    strategy: str
    action: str
    instrumentation: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)


def _stable_seed(session_id: str, seed: int) -> int:
    digest = hashlib.sha256(f"{session_id}:{seed}".encode()).digest()
    return int.from_bytes(digest[:8], "big")


def _append_unique(items: tuple[str, ...], value: str) -> tuple[str, ...]:
    return items if value in items else (*items, value)


def _action_for(command: str) -> str:
    tokens = _COMMAND_RE.findall(command.lower())
    if not tokens:
        return "unsupported"
    head = tokens[0]
    if head in {"ls", "find"}:
        return "discover"
    if head in {"ss", "netstat", "ip", "ping"}:
        return "network"
    if head in {"systemctl", "service"}:
        return "services"
    if head in {"cat", "head", "tail", "less"}:
        return "inspect"
    if head in {"whoami", "id", "hostname"}:
        return head
    if head in {"ps", "top"}:
        return "operations"
    if any(word in tokens for word in ("credential", "credentials", "password", "secret")):
        return "credentials"
    if head in {"apply", "configure", "set", "update", "patch", "restart", "start", "stop", "deploy"}:
        return "configure" if head != "deploy" else "deploy"
    if head in {"status", "show"}:
        return "status"
    if head in {"visit", "return", "reconnect"}:
        return "visit"
    if head == "help":
        return "help"
    return "unsupported"


class StrategyAwareDeceptionGeneratorV1:
    def __init__(self, session_id: str, *, seed: int = 0) -> None:
        if not session_id.strip():
            raise ValueError("session_id must be non-empty")
        self.session_id = session_id
        self.seed = _stable_seed(session_id, seed)
        self._state = FictionalState(session_id=session_id, seed=self.seed)
        self._baseline = ResponseGenerator(gateway_url=None)

    @property
    def state(self) -> FictionalState:
        return self._state

    def generate(
        self,
        command: str,
        strategy: str,
        *,
        skill_level: str = "novice",
        identity: dict[str, str] | None = None,
    ) -> StrategyCandidate:
        if strategy not in ALLOWED_STRATEGIES:
            raise ValueError(f"unsupported strategy: {strategy!r}")
        if strategy == "baseline":
            text = self._baseline.generate(skill_level, command, identity=identity)
            return StrategyCandidate(
                response_text=text,
                proposed_state=self._state,
                strategy="baseline",
                action="baseline",
                instrumentation={"mode": "legacy_baseline", "mutated": False},
                metadata={"strategy_consumed_by_template": False},
            )
        action = _action_for(command)
        if action not in _SIMULATED_ACTIONS:
            return self._candidate(
                strategy,
                action,
                f"simulation: unsupported action; no fictional state changed\n{self._prompt()}$",
                self._state,
                "action_rejected",
            )
        next_state = self._propose_state(strategy, action)
        text, event = self._render(strategy, action, command, next_state)
        return self._candidate(strategy, action, text, next_state, event)

    def commit(self, candidate: StrategyCandidate, *, verifier_passed: bool, hitl_approved: bool) -> dict[str, Any]:
        if candidate.proposed_state.session_id != self.session_id:
            raise ValueError("candidate belongs to another session")
        if candidate.strategy not in ALLOWED_STRATEGIES:
            raise ValueError("candidate has unsupported strategy")
        accepted = bool(verifier_passed and hitl_approved)
        if accepted:
            self._state = candidate.proposed_state
        return {
            "accepted": accepted,
            "committed": accepted,
            "strategy": candidate.strategy,
            "state_version": hashlib.sha256(repr(self._state).encode()).hexdigest(),
            "reason": "accepted" if accepted else "verification_or_hitl_rejected",
        }

    def _candidate(self, strategy: str, action: str, text: str, state: FictionalState, event: str) -> StrategyCandidate:
        return StrategyCandidate(
            response_text=text,
            proposed_state=state,
            strategy=strategy,
            action=action,
            instrumentation={
                "mode": STRATEGY_GENERATOR_VERSION,
                "event": event,
                "event_id": hashlib.sha256(f"{self.session_id}:{self._state.visits}:{event}".encode()).hexdigest()[:16],
                "fictional_only": True,
                "attacker_command_executed": False,
            },
            metadata={"strategy_consumed_by_template": True, "allowlisted_action": action in _SIMULATED_ACTIONS},
        )

    def _prompt(self) -> str:
        return f"webapp@fiction-{self.seed % 10000:04d}:~"

    def _propose_state(self, strategy: str, action: str) -> FictionalState:
        state = self._state
        visits = state.visits + 1
        if strategy == "maximize_recon_surface" and action in {"discover", "network", "services", "operations"}:
            paths = _append_unique(state.discovered_paths, "/srv/fictional-app")
            services = _append_unique(state.discovered_services, "fictional-web.service")
            return FictionalState(**{**state.__dict__, "visits": visits, "discovered_paths": paths, "discovered_services": services})
        if strategy == "fake_success_and_return_visits" and action in {"configure", "deploy", "status"}:
            if action == "status" and state.completed_operations:
                return FictionalState(**{**state.__dict__, "visits": visits})
            op = f"operation-{(self.seed + visits) % 10000:04d}"
            return FictionalState(**{**state.__dict__, "visits": visits, "completed_operations": _append_unique(state.completed_operations, op)})
        if strategy == "steer_to_honeytoken_credentials" and action == "credentials":
            token = f"decoy-svc-{self.seed % 10000:04d}"
            return FictionalState(**{**state.__dict__, "visits": visits, "decoy_credentials": _append_unique(state.decoy_credentials, token)})
        if strategy == "expose_decoy_internal_topology" and action in {"network", "topology", "discover"}:
            hosts = _append_unique(state.topology_hosts, "db-fictional-01")
            services = _append_unique(state.topology_services, "mysql:fictional")
            return FictionalState(**{**state.__dict__, "visits": visits, "topology_hosts": hosts, "topology_services": services})
        if strategy == "contain_in_fiction_and_instrument":
            resource = f"/var/tmp/fictional/{self.seed % 10000:04d}"
            return FictionalState(**{**state.__dict__, "visits": visits, "contained_resources": _append_unique(state.contained_resources, resource), "telemetry_events": (*state.telemetry_events, "contained-action")})
        return FictionalState(**{**state.__dict__, "visits": visits})

    def _render(self, strategy: str, action: str, command: str, state: FictionalState) -> tuple[str, str]:
        prompt = f"{self._prompt()}$ {command}"
        if strategy == "maximize_recon_surface":
            return f"{prompt}\n/srv/fictional-app\nfictional-web.service\nfictional-db.service", "recon_surface_updated"
        if strategy == "fake_success_and_return_visits":
            op = state.completed_operations[-1] if state.completed_operations else "none"
            return f"{prompt}\nstatus: SUCCESS\noperation: {op}\nnext: status {op}", "fictional_operation_completed"
        if strategy == "steer_to_honeytoken_credentials":
            token = state.decoy_credentials[-1] if state.decoy_credentials else "none"
            return f"{prompt}\nservice_account=decoy_user\ncredential_id={token}\ninstrumentation_id=honeytoken-{self.seed % 10000:04d}", "decoy_credential_issued"
        if strategy == "expose_decoy_internal_topology":
            return f"{prompt}\napp-fictional-01 -> db-fictional-01:3306\ncache-fictional-01:6379", "topology_revealed"
        if strategy == "contain_in_fiction_and_instrument":
            resource = state.contained_resources[-1] if state.contained_resources else "/var/tmp/fictional"
            return f"{prompt}\ncontained_resource={resource}\ntelemetry=fictional-only", "contained_action_recorded"
        return f"{prompt}\nadministration: no change\nstate: fictional-admin-stable", "low_intensity_admin"
