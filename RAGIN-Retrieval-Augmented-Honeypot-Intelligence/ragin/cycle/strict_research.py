"""Strict, opt-in research verification profile (``research_strict_v1``).

The legacy ``FictionConsistencyVerifier`` is contradiction-only: a reply
passes when it asserts nothing the pinned fiction contradicts. That is a
coverage boundary, not grounding — a plausible ungrounded ``cat /etc/sudoers``
reply can pass because no deterministic evidence contract covers it.

This module adds an explicit, versioned profile over a **predeclared finite
shell-command contract**:

* only the exact commands in ``SUPPORTED_COMMANDS`` are in scope;
* wrappers, compound commands, pipes, redirections, substitutions, encoded
  payloads, comments, and extra arguments are outside the grammar and are
  rejected (they are never reduced to a supported first command);
* a supported reply must contain exactly the canonical output derived from
  the authoritative pinned host identity — extra fabricated lines are a
  mismatch, and arbitrary prompt-shaped lines are not silently discarded;
* unsupported commands produce an explicit ``UNSUPPORTED_COMMAND`` verdict,
  never a silent pass;
* verification uses only the declared host identity/fiction facts, never the
  retrieval or CTI layer (B1 has no retrieval by design).

The profile is intentionally a *bounded* claim: rejecting unsupported commands
has a measured availability cost. It does not assert general Linux correctness
and it does not replace the legacy contradiction checks, which still run.
``date``/``uptime`` are excluded in v1 because shape alone is not evidence;
only commands with a pinned canonical output (plus identity-derived facts)
are in scope.

Version history:
  research_strict_v1 — initial finite contract (2026-10-23).
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any

from ragin.hisoka.deception import _id_line

PROFILE_NAME = "research_strict_v1"
LEGACY_PROFILE_NAME = "legacy"
VALID_PROFILES: frozenset[str] = frozenset({LEGACY_PROFILE_NAME, PROFILE_NAME})

# Exact command strings accepted by the profile. No prefixes, suffixes,
# flags outside this set, paths, quoting, whitespace variants, or clock-shaped
# commands whose values are not pinned.
SUPPORTED_COMMANDS: frozenset[str] = frozenset(
    {
        "whoami",
        "id",
        "id -u",
        "id -un",
        "id -g",
        "id -gn",
        "hostname",
        "hostname -f",
        "hostname -s",
        "uname",
        "uname -a",
        "uname -r",
        "uname -s",
        "cat /etc/os-release",
        "cat /usr/lib/os-release",
    }
)

_REQUIRED_IDENTITY_FIELDS: tuple[str, ...] = (
    "user",
    "group",
    "uid",
    "gid",
    "host",
    "domain",
    "kernel",
    "distro",
)

# Shell metacharacters that put an input outside the exact grammar. Exact
# set membership already rejects these; naming them yields a clearer verdict.
_SHELL_METACHAR_RE = re.compile(r"[;&|<>(){}`$#\\\n\r\t]|\$\(")
_WRAPPER_RE = re.compile(
    r"^\s*(?:sudo|doas|env|nohup|nice|command|builtin|time|timeout|xargs|sh|bash|zsh)\b",
    re.IGNORECASE,
)
_ENCODED_RE = re.compile(
    r"\b(?:base64|xxd|rev|tr|eval|exec)\b|\bprintf\s+['\"]?[0-9a-fA-F]{8,}",
    re.IGNORECASE,
)

# Any prompt-like line. Only the exact pinned prompt echo for THIS command
# (or its exact empty ready prompt) is accepted; everything else is rejected.
_PROMPT_RE = re.compile(
    r"^(?:\[)?[A-Za-z0-9_.\-]+@[A-Za-z0-9_.\-]+(?::|~| )[^\n]*[$#](?:\s|$)",
)

# Error text a shell prints when a command did not produce the claimed output.
_SHELL_ERROR_RE = re.compile(
    r"command not found|no such file or directory|permission denied|"
    r"operation not permitted|could not resolve|not found\b",
    re.IGNORECASE,
)

# Pinned os-release body. Mirrors ResponseGenerator._lookup_template's
# deterministic content without that template's trailing prompt/uname lines.
_OS_RELEASE_LINES: tuple[str, ...] = (
    'PRETTY_NAME="Ubuntu 22.04.3 LTS"',
    'NAME="Ubuntu"',
    'VERSION_ID="22.04"',
    'VERSION="22.04.3 LTS (Jammy Jellyfish)"',
    "ID=ubuntu",
)
_PINNED_DISTRO_PREFIX = "Ubuntu 22.04"


@dataclass(frozen=True)
class StrictVerdict:
    """Outcome of one strict-profile evaluation.

    Issue text is a stable reason code. Diagnostic metadata carries only
    counts and SHA-256 digests — never raw attacker input or candidate lines.
    """

    verdict: str
    reason: str
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.verdict == "SUPPORTED"

    @property
    def issue(self) -> str | None:
        if self.passed:
            return None
        return f"strict-profile:{self.reason}"

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "profile": PROFILE_NAME,
            "strict_verdict": self.verdict,
            "strict_reason": self.reason,
        }
        payload.update(self.meta)
        return payload


def _fail(verdict: str, reason: str, **meta: Any) -> StrictVerdict:
    return StrictVerdict(verdict=verdict, reason=reason, meta=meta)


def _identity_ok(ident: dict[str, Any] | None) -> bool:
    if not isinstance(ident, dict):
        return False
    return all(str(ident.get(field) or "").strip() for field in _REQUIRED_IDENTITY_FIELDS)


def _line_identity(ident: dict[str, Any]) -> str:
    """Canonical ``id`` line, reusing the pinned authorization policy."""
    return _id_line({key: str(value) for key, value in ident.items()})


def _full_uname(ident: dict[str, Any]) -> str:
    # Same pinned line the deterministic generator serves.
    return f"Linux {ident['host']} {ident['kernel']} #167-Ubuntu SMP x86_64 GNU/Linux"


def _expected_output(command: str, ident: dict[str, Any]) -> tuple[str, ...]:
    user = str(ident["user"])
    if command == "whoami":
        return (user,)
    if command == "id":
        return (_line_identity(ident),)
    if command == "id -u":
        return (str(ident["uid"]),)
    if command == "id -un":
        return (user,)
    if command == "id -g":
        return (str(ident["gid"]),)
    if command == "id -gn":
        return (str(ident["group"]),)
    if command == "hostname":
        return (str(ident["host"]),)
    if command == "hostname -f":
        return (f"{ident['host']}.{ident['domain']}",)
    if command == "hostname -s":
        return (str(ident["host"]).split(".")[0],)
    if command in {"uname", "uname -s"}:
        # Plain `uname`/`uname -s` print the kernel name only; they do not
        # print the `uname -a` line.
        return ("Linux",)
    if command == "uname -a":
        return (_full_uname(ident),)
    if command == "uname -r":
        return (str(ident["kernel"]),)
    if command in {"cat /etc/os-release", "cat /usr/lib/os-release"}:
        return _OS_RELEASE_LINES
    raise ValueError(f"no strict contract for {command!r}")


def _digest_lines(lines: list[str]) -> str:
    return hashlib.sha256("\n".join(lines).encode()).hexdigest()


def _answer_lines(text: str, command: str, ident: dict[str, Any]) -> tuple[list[str], int]:
    """Return (answer lines, unexpected prompt-line count).

    Accepted transcript lines are only:

    * the exact pinned prompt echo of THIS command, e.g.
      ``webapp@web-srv-01:~$ whoami``;
    * the exact empty ready prompt, e.g. ``webapp@web-srv-01:~$``.

    Any other prompt-shaped line is counted as unexpected (and therefore a
    mismatch) rather than discarded. Bare command echoes are not accepted.
    """
    prompt = str(ident.get("prompt") or f"{ident['user']}@{ident['host']}")
    accepted_prompt_echoes = {f"{prompt}:~$ {command}", f"{prompt}:~$"}
    lines: list[str] = []
    unexpected_prompts = 0
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line in accepted_prompt_echoes:
            continue
        if _PROMPT_RE.search(line):
            unexpected_prompts += 1
            continue
        lines.append(line)
    return lines, unexpected_prompts


def evaluate_strict_research(
    user_input: str,
    text: str,
    ident: dict[str, Any] | None,
) -> StrictVerdict:
    """Evaluate one attacker input against the finite strict contract.

    ``ident`` must be the authoritative pinned identity snapshot injected by
    the harness (graph/host store). There is no skill-based fallback: missing
    or incomplete identity is a fail-closed verdict.
    """
    raw = user_input or ""
    command = raw.strip()
    if not command:
        return _fail("MALFORMED_INPUT", "MISSING_ATTACKER_INPUT")
    if command not in SUPPORTED_COMMANDS:
        if _SHELL_METACHAR_RE.search(raw) or _WRAPPER_RE.search(raw) or _ENCODED_RE.search(raw):
            return _fail("MALFORMED_INPUT", "OUTSIDE_EXACT_GRAMMAR")
        return _fail("UNSUPPORTED_COMMAND", "UNSUPPORTED_COMMAND")

    if not _identity_ok(ident):
        return _fail(
            "MISSING_EVIDENCE",
            "MISSING_PINNED_IDENTITY",
            strict_identity_fields_required=len(_REQUIRED_IDENTITY_FIELDS),
        )
    assert ident is not None  # narrowed by _identity_ok

    if command in {"cat /etc/os-release", "cat /usr/lib/os-release"} and not str(
        ident["distro"]
    ).startswith(_PINNED_DISTRO_PREFIX):
        return _fail("UNSUPPORTED_COMMAND", "UNSUPPORTED_PINNED_DISTRO")

    body = (text or "").strip()
    if not body:
        return _fail("MISSING_EVIDENCE", "EMPTY_REPLY", strict_observed_line_count=0)

    lines, unexpected_prompts = _answer_lines(text or "", command, ident)
    if unexpected_prompts:
        return _fail(
            "CLAIM_MISMATCH",
            "UNEXPECTED_PROMPT_ECHO",
            strict_unexpected_prompt_lines=unexpected_prompts,
        )
    if not lines:
        return _fail(
            "MISSING_EVIDENCE",
            "NO_ANSWER_LINES",
            strict_observed_line_count=0,
        )
    if any(_SHELL_ERROR_RE.search(line) for line in lines):
        return _fail("MISSING_EVIDENCE", "SHELL_ERROR_TEXT", strict_observed_line_count=len(lines))

    try:
        expected = list(_expected_output(command, ident))
    except (KeyError, ValueError):
        return _fail("UNSUPPORTED_COMMAND", "UNSUPPORTED_COMMAND")

    if lines != expected:
        return _fail(
            "CLAIM_MISMATCH",
            "OUTPUT_MISMATCH",
            strict_expected_line_count=len(expected),
            strict_observed_line_count=len(lines),
            strict_expected_sha256=_digest_lines(expected),
            strict_observed_sha256=_digest_lines(lines),
        )
    return StrictVerdict("SUPPORTED", "OUTPUT_MATCHES", {"strict_observed_line_count": len(lines)})


class StrictResearchVerifier:
    """Wrap any verifier and add the strict research profile checks.

    The wrapper runs the inner verifier first (legacy contradiction/identity
    checks still apply), then the finite strict contract. Both must pass.
    The pinned identity is taken only from ``pinned_identity`` in the context;
    the harness injects it from the session graph / host store.
    """

    profile = PROFILE_NAME

    def __init__(self, inner: Any) -> None:
        self._inner = inner

    def verify(self, response: dict[str, Any] | str, session_context: dict[str, Any] | None = None) -> dict[str, Any]:
        ctx = session_context or {}
        result = self._inner.verify(response, ctx)
        if not isinstance(result, dict):
            result = {
                "passed": False,
                "issues": ["verifier_malformed_result"],
                "deterministic": True,
            }
        text = (response.get("response_text") or "") if isinstance(response, dict) else str(response or "")
        user_input = str(ctx.get("attacker_input") or ctx.get("query") or "")
        pinned = ctx.get("pinned_identity")
        strict = evaluate_strict_research(
            user_input,
            text,
            pinned if isinstance(pinned, dict) else None,
        )
        merged = dict(result)
        issues = list(merged.get("issues") or [])
        if strict.issue:
            issues.append(strict.issue)
        merged["issues"] = issues
        merged["passed"] = bool(merged.get("passed") is True and strict.passed)
        merged.update(strict.to_dict())
        merged.setdefault("deterministic", True)
        merged.setdefault("verifier", type(self._inner).__name__)
        return merged


__all__ = [
    "LEGACY_PROFILE_NAME",
    "PROFILE_NAME",
    "SUPPORTED_COMMANDS",
    "StrictResearchVerifier",
    "StrictVerdict",
    "VALID_PROFILES",
    "evaluate_strict_research",
]
