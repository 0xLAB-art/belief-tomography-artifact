"""JevAssessor — builds Jev System One states + question sets from RAGIN data.

Turns RAGIN session / attacker context into the ``state`` + ``questions``
payload Jev expects, and runs the standard decision set:

  - ``attack``      noul: is this evidence of an attack?
  - ``severity``    score (0-3): how severe?
  - ``attack_kind`` choice: which attack class (bruteforce/scanning/exploit/...)?

The caller stays in control of enabling/disabling this additive signal;
a Jev failure never crashes the pipeline (returns None / raises JevError
that orchestration code catches and downgrades).
"""

from __future__ import annotations

import logging
import os
from typing import Any

from ragin.jev.client import JevClient
from ragin.jev.models import (
    JevAssessment,
    JevQuestion,
    choice_question,
    noul_question,
    score_question,
)

logger = logging.getLogger(__name__)

# Score criteria bins (0..3), indexed so bin i == severity i.
_SEVERITY_CRITERIA = ["benign", "low concern", "suspicious", "confirmed attack"]
_ATTACK_KIND_OPTIONS = ["bruteforce", "scanning", "exploit", "persistence", "lateral", "unknown"]


class JevError(Exception):
    """Raised when a Jev assessment cannot be produced."""


class JevAssessor:
    """Builds and submits Jev System One assessments from RAGIN inputs.

    Args:
        client: Optional :class:`JevClient`; created lazily from env when
            omitted so the class is cheap to instantiate.
        enabled: ``None`` honours ``RAGIN_JEVI_ENABLED`` (default on).
            Pass False to hard-disable (tests / offline deployments).
    """

    def __init__(self, client: JevClient | None = None, enabled: bool | None = None) -> None:
        self._client = client
        self._enabled = (
            enabled
            if enabled is not None
            else os.environ.get("RAGIN_JEVI_ENABLED", "1").strip().lower() not in ("0", "false", "off", "no")
        )

    @property
    def enabled(self) -> bool:
        return self._enabled

    # ── State builders ────────────────────────────────────────────────────

    @staticmethod
    def state_from_session_log(session_log: Any) -> str:
        """Render a SessionLog (or anything with the same attrs) as Jev state.

        Focuses on the observable behavior: commands with exit codes and
        output sizes, file operations, network activity, and any raw log.
        """
        lines: list[str] = []
        for entry in getattr(session_log, "commands", []) or []:
            command = getattr(entry, "command", "") or ""
            user = getattr(entry, "user", "") or ""
            desc = command
            if user:
                desc = f"{user}$ {command}"
            if getattr(entry, "exit_code", None) is not None:
                desc = f"{desc} -> exit {entry.exit_code}"
            if getattr(entry, "output_length", 0):
                desc = f"{desc} (output {entry.output_length} bytes)"
            lines.append(desc)
        for op in getattr(session_log, "file_operations", []) or []:
            lines.append(f"{getattr(op, 'operation', '')} {getattr(op, 'path', '')} ({getattr(op, 'size', 0)} bytes)")
        for net in getattr(session_log, "network_activity", []) or []:
            lines.append(
                f"net {getattr(net, 'protocol', '')} "
                f"{getattr(net, 'source_ip', '')}->{getattr(net, 'destination_ip', '')}:"
                f"{getattr(net, 'destination_port', 0)} "
                f"sent {getattr(net, 'bytes_sent', 0)} recv {getattr(net, 'bytes_received', 0)}"
            )
        raw = getattr(session_log, "raw_log", "") or ""
        if raw and not lines:
            lines = raw.splitlines()
        header = f"session {getattr(session_log, 'session_id', 'unknown')}"
        return "\n".join([header, *lines])

    @staticmethod
    def state_from_commands(attacker_inputs: list[str], *, context: str = "") -> str:
        """Render attacker command strings + optional context as Jev state."""
        lines = [] if not context else [context]
        lines.extend(attacker_inputs)
        return "\n".join(str(x) for x in lines if x is not None and str(x).strip())

    @staticmethod
    def default_questions() -> dict[str, JevQuestion]:
        """The standard RAGIN decision set (attack? severity? kind?)."""
        return {
            "attack": noul_question(
                "Is this session evidence of a malicious or suspicious attack?",
                true_criteria=(
                    "The state shows attack behavior: credential guessing, "
                    "exploitation, persistence, pivoting, or malicious tooling."
                ),
                false_criteria=(
                    "The state shows benign or routine activity: normal commands, "
                    "config inspection, or harmless output."
                ),
            ),
            "severity": score_question(
                "How severe is the suspicious/malicious activity in this state?",
                minimum=0,
                maximum=3,
                criteria=_SEVERITY_CRITERIA,
            ),
            "attack_kind": choice_question(
                "Which attack class does this state most resemble?",
                options=_ATTACK_KIND_OPTIONS,
                criteria={
                    "bruteforce": ("repeated login/credential attempts, password guessing, or wordlist auth attempts"),
                    "scanning": ("port scans, service fingerprinting, directory busting, or passive recon"),
                    "exploit": (
                        "known CVE exploitation, injection attempts, remote code "
                        "execution, or payload delivery/execution"
                    ),
                    "persistence": (
                        "backdoors, scheduled tasks, cron, ssh keys, or service installation for regaining access"
                    ),
                    "lateral": ("movement to other hosts, credential dumping, kerberos attacks, or network pivoting"),
                    "unknown": "no clear attack pattern is evident",
                },
                allow_multi=True,
            ),
        }

    # ── Assessment ─────────────────────────────────────────────────────────

    def assess_session(self, session_log: Any) -> JevAssessment:
        """Assess a SessionLog['s events against the default question set."""
        if not self._enabled:
            raise JevError("Jev assessment is disabled (RAGIN_JEVI_ENABLED=0)")
        client = self._client or JevClient()
        return client.assess(
            session_id=getattr(session_log, "session_id", "unknown"),
            state=self.state_from_session_log(session_log),
            questions=self.default_questions(),
        )

    def assess_commands(
        self,
        attacker_inputs: list[str],
        *,
        session_id: str = "unknown",
        context: str = "",
        questions: dict[str, JevQuestion] | None = None,
    ) -> JevAssessment:
        """Assess attacker command strings against (default) questions."""
        if not self._enabled:
            raise JevError("Jev assessment is disabled (RAGIN_JEVI_ENABLED=0)")
        client = self._client or JevClient()
        return client.assess(
            session_id=session_id,
            state=self.state_from_commands(attacker_inputs, context=context),
            questions=questions or self.default_questions(),
        )

    def assess_context(self, context: dict[str, Any]) -> JevAssessment | None:
        """Best-effort assessment from a generic map (harness context dict).

        Accepts keys seen across the orchestrator: ``attacker_inputs`` /
        ``commands`` (list) or ``state`` (raw text). Returns None when the
        context holds nothing Jev can evaluate, without raising.
        """
        state = context.get("state")
        if not state:
            inputs = context.get("attacker_inputs") or context.get("commands") or []
            if isinstance(inputs, list) and inputs:
                state = self.state_from_commands([str(x) for x in inputs])
        if not state:
            return None
        try:
            return self.assess_commands(
                [str(state)] if isinstance(state, str) else [],
                session_id=str(context.get("session_id", "unknown")),
                context="" if isinstance(state, str) else "",
            )
        except Exception:
            logger.warning("Jev context assessment failed — continuing without it", exc_info=True)
            return None
