"""Versioned transcript contract: which layer owns the command echo.

An attacker-visible SSH turn has one mandatory echo: the PTY echoes the bytes the
attacker typed. Cowrie writes that echo itself, before RAGIN's response is
written. A transcript that *also* begins with ``user@host:~$ <command>`` makes the
same command appear twice on the wire, and RAGIN's own generator added that
second copy (``hisoka/deception.py::_style_as_transcript``) only when its
shell-command heuristic accepted the input, so the duplication was not even
consistent across commands in one session.

Two contracts are defined. Both are explicit, both are recorded in every serving
trace, and neither is inferred from the other:

``v1`` (legacy)
    The server prepends a ``prompt + command`` echo line to bare output. This is
    the behaviour historical artifacts were produced under. It is reproducible,
    but on a real Cowrie frontend it duplicates the PTY echo.

``v2`` (current for new experiments)
    The frontend owns the echo. The server serves command output only: it never
    prepends an echo and it strips a leading echo line that exactly repeats the
    command (a model draft may still contain one).

The default is ``v1`` so that historical runs stay reproducible byte-for-byte.
Any new experiment must set ``RAGIN_TRANSCRIPT_CONTRACT=v2`` explicitly, and the
version is persisted next to the served bytes. An unrecognised value raises
instead of silently falling back: a contract that is guessed is not a contract.
"""

from __future__ import annotations

import os
from typing import Any

CONTRACT_ENV = "RAGIN_TRANSCRIPT_CONTRACT"

LEGACY_CONTRACT = "v1"
CURRENT_CONTRACT = "v2"

_CONTRACTS: dict[str, dict[str, str]] = {
    LEGACY_CONTRACT: {
        "echo_owner": "server",
        "description": (
            "Server prepends 'prompt$ command' when a body carries no echo. "
            "Faithful to the v5.5 fallback-shape work; duplicates the PTY echo "
            "on a real frontend."
        ),
    },
    CURRENT_CONTRACT: {
        "echo_owner": "frontend",
        "description": (
            "Frontend owns the echo (Cowrie PTY). Server serves command output "
            "only, and strips a leading echo line that exactly repeats the "
            "attacker's command."
        ),
    },
}


def resolve(version: str | None = None) -> str:
    """Return the active contract version.

    ``version`` wins; otherwise ``RAGIN_TRANSCRIPT_CONTRACT``; otherwise the
    legacy contract. An unknown version raises ``ValueError``.
    """
    raw = version if version is not None else os.environ.get(CONTRACT_ENV, LEGACY_CONTRACT)
    value = str(raw or "").strip().lower()
    if value not in _CONTRACTS:
        raise ValueError(
            f"unknown transcript contract {raw!r}; expected one of {sorted(_CONTRACTS)}"
        )
    return value


def echo_owner(version: str | None = None) -> str:
    """Return ``"server"`` or ``"frontend"`` for the contract in force."""
    return _CONTRACTS[resolve(version)]["echo_owner"]


def describe(version: str | None = None) -> dict[str, Any]:
    """Provenance record for a serving trace or manifest."""
    resolved = resolve(version)
    contract = _CONTRACTS[resolved]
    return {
        "version": resolved,
        "echo_owner": contract["echo_owner"],
        "description": contract["description"],
        "source": "argument" if version is not None else f"env:{CONTRACT_ENV}",
        "default": resolved == LEGACY_CONTRACT and CONTRACT_ENV not in os.environ,
        "current_for_new_experiments": CURRENT_CONTRACT,
    }
