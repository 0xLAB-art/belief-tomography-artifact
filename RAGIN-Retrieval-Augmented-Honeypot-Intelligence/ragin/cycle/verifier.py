"""FictionConsistencyVerifier — machine verification before serve.

C2 of the TDSC novelty plan: no deception response reaches the attacker
until it passes machine verification. Single invariant source shared with
the fiction graph (C1) so "verification" and "consistency" enforce the
same facts.

Checks (each failure is a hard fail — the response must NOT be served):
  D1  danger signals        — honeypot tells, refusal/chat phrasing, real secrets
  D2  fiction contradictions — reply facts contradict the session's fiction graph
  D3  identity pinning       — whoami/id answers must match the pinned identity
  D4  empty/degenerate       — empty or single-character output

On failure the LangGraph verify node decrements ``retries_left`` and loops
back to ``generate`` with the issues as feedback; the final fallback is the
deterministic identity-bound template (fail-safe default).

Deterministic, dependency-free, and thread-safe (no shared mutable state).
"""

from __future__ import annotations

import os
import re
from typing import Any

from ragin.cycle.strict_research import (
    LEGACY_PROFILE_NAME,
    PROFILE_NAME,
    VALID_PROFILES,
    evaluate_strict_research,
)
from ragin.graph.fiction import FictionGraph
from ragin.hisoka.deception import identity_for


class FictionConsistencyVerifier:
    """Verify a deception response against the session fiction graph + danger rules.

    ``profile`` selects the claim contract:

    * ``legacy`` (default) — contradiction/identity checks plus the optional
      ``RAGIN_FAIL_CLOSED`` supported subset; byte-identical to prior behavior.
    * ``research_strict_v1`` — additionally applies the finite exact-grammar
      contract in :mod:`ragin.cycle.strict_research`, which rejects
      unsupported/compound/encoded inputs and extra fabricated claim lines.

    The profile can be supplied explicitly (used by tests and the harness
    policy) or via ``RAGIN_VERIFIER_PROFILE``. Invalid profiles raise rather
    than silently falling back.
    """

    def __init__(self, fictions: dict[str, FictionGraph] | None = None, *, profile: str | None = None) -> None:
        # Optional per-session fiction-graph registry (session_id -> graph).
        # When provided, contradiction checks run against the SAME graph the
        # generation node seeded; standalone callers get a fresh identity-
        # seeded graph so verification still has authoritative facts.
        self._fictions = fictions
        raw_profile = profile if profile is not None else os.environ.get("RAGIN_VERIFIER_PROFILE", LEGACY_PROFILE_NAME)
        self._profile = str(raw_profile).strip().lower()
        if self._profile not in VALID_PROFILES:
            raise ValueError(
                f"invalid RAGIN_VERIFIER_PROFILE={raw_profile!r}; expected one of {sorted(VALID_PROFILES)}"
            )
        # Fail-closed completeness (S&P P1 upgrade, opt-in): on the declared
        # supported-claim surface (whoami/id/hostname/uname/echo/uptime/date/
        # os-release), a draft must CONTAIN the deterministic answer — hedging,
        # query echo, or omission is a finding, not a pass. Default OFF keeps
        # byte-identical legacy behavior; the contradiction checks above are
        # unchanged either way.
        self._fail_closed = os.environ.get("RAGIN_FAIL_CLOSED", "").strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )

    @property
    def profile(self) -> str:
        """The active claim-contract profile (see module docstring)."""
        return self._profile

    # ── checks ─────────────────────────────────────────────────────────────

    def _check_danger_signals(self, text: str) -> list[str]:
        from ragin.hisoka.deception import _contains_danger_signal

        issues: list[str] = []
        if _contains_danger_signal(text):
            issues.append("danger-signal: response contains honeypot tells, refusal phrasing, or real secrets")
        if re.search(r"\b(?:as an? (?:ai|assistant|language model)|i cannot assist)\b", text, re.IGNORECASE):
            issues.append("danger-signal: explicit AI/refusal self-reference")
        return issues

    def _check_fiction_contradictions(self, session_id: str, skill_level: str, text: str) -> list[str]:
        fiction = self._fictions.get(session_id) if self._fictions else None
        if fiction is None:
            fiction = FictionGraph(session_id=session_id, identity=identity_for(skill_level))
        result = fiction.clone(session_id=fiction.session_id).observe(text, source="verifier")
        if result.contradictions:
            preview = "; ".join(
                f"{c.get('predicate')}: {c.get('before')} -> {c.get('after')}" for c in result.contradictions[:3]
            )
            return [f"fiction-contradiction: {preview}"]
        return []

    def _check_identity_pin(
        self, user_input: str, text: str, skill_level: str, ident: dict[str, Any] | None = None
    ) -> list[str]:
        issues: list[str] = []
        ident = ident or identity_for(skill_level)
        lower = user_input.lower().strip()
        # V16 (live red-team): drafts sometimes omit ctx attacker_input; the
        # transcript's own echo line still names the command — derive it from
        # there so the whoami/id answer rules fire on the reply's intent
        # rather than the metadata field.
        if not lower:
            m = re.search(
                r"(?:^|\n)\[?[A-Za-z0-9_.\-]+@[A-Za-z0-9._\-]+[^\n]*\]?[:#$][^a-z\n]*(.*)$",
                text,
                re.MULTILINE,
            )
            if m:
                # V16b (live round 5): drafts invoke the absolute path
                # (/usr/bin/whoami) — the basename is the command. V23b
                # (live round 7, second author model): composite wrappers
                # too — { printf ...; whoami; }, `command whoami`, env-prefix
                # forms. Word-boundary search over the whole echo tail: the
                # identity answer rules check whoami/id directly, so wrapper
                # noise is harmless.
                tail = m.group(1).strip().lower()
                for cmd in ("whoami", "id"):
                    if re.search(rf"\b{cmd}\b", tail):
                        if cmd == "id":
                            # Preserve flag variants (`id -un`) when deriving the
                            # command from the transcript echo — flattening to
                            # bare `id` routed correct variant answers into the
                            # strict uid=() branch, false-rejecting them (V17
                            # contract violation; caught by the 2026-09-27
                            # cross-family rescore: space-bunny v1/v3 + deepseek
                            # v3 drafts answering `id -un` with the correct name).
                            fm = re.search(r"\bid\s+(-[a-zA-Z]+\b)", tail)
                            lower = f"id {fm.group(1)}" if fm else "id"
                        else:
                            lower = cmd
                        break
        # Red-team finding V5: the old `ident["user"] not in text` substring
        # test matched the pinned user ANYWHERE in the reply — including the
        # echoed prompt line `webapp@web-srv-01:~$ whoami` — so a wrong answer
        # on the answer line passed verification. Compare the ANSWER lines
        # (post-prompt, post-command) instead.
        answer_lines = self._answer_lines(text)
        answer_text = "\n".join(answer_lines)
        if (
            (lower in ("whoami", "who am i") or lower.startswith("whoami"))
            and text.strip()
            and answer_text.strip()
            and ident["user"] not in answer_text
        ):
            issues.append(f"identity-pin: whoami must be '{ident['user']}'")
        if (lower == "id" or lower.startswith("id ")) and text.strip() and answer_text.strip():
            # V17 (live red-team): `id -un`/`id -u` legitimately print ONLY the
            # name (or numeric uid) — demanding the canonical uid=() string
            # false-rejected correct variant answers. Full `id` keeps the
            # strict shape; flag variants accept user, uid, or group name.
            is_variant = lower != "id"
            if is_variant:
                uid_word = re.search(rf"\b(?:{re.escape(ident['user'])}|{re.escape(str(ident['uid']))})\b", answer_text)
                if not uid_word:
                    issues.append(f"identity-pin: id variant must report '{ident['user']}'")
            elif f"uid={ident['uid']}({ident['user']})" not in answer_text:
                issues.append(f"identity-pin: id must report uid={ident['uid']}({ident['user']})")
        # A root shell prompt in any reply is a hard identity violation.
        if re.search(r"root@[A-Za-z0-9._\-]+[:#]", text):
            issues.append("identity-pin: root shell prompt leaked")
        # Red-team finding V3 (coverage, not precision): the fiction extractor
        # observes dotted hostnames only, so a draft answering `hostname` with
        # a DIFFERENT BARE SHORTNAME (app-db-02 vs pinned web-srv-01) plants a
        # silent drift. When the attacker asked for the host's own name, the
        # pinned hostname must appear in the reply's answer lines — presence
        # is required (the fiction uses short or FQDN forms), not absence of
        # alternatives, so FQDN replies keep passing.
        pinned_host = str(ident.get("host", "") or "")
        if (
            pinned_host
            and answer_text.strip()
            and re.fullmatch(r"hostname(?:\s+-[a-zA-Z]+)?", lower)
            and pinned_host not in answer_text
            and f"{pinned_host}." not in answer_text
        ):
            issues.append(f"identity-pin: hostname must resolve to '{pinned_host}'")
        return issues

    @staticmethod
    def _answer_lines(text: str) -> list[str]:
        """Reply lines a real command prints: drop prompt/command echoes.

        A line is an echo when it contains the pinned prompt shape
        (`user@host`) or the command word itself; answer lines are what
        remains. Best-effort by design — when nothing remains (e.g. the
        reply IS just `webapp`), the caller's ``answer_text.strip()`` guard
        keeps the check inert rather than inventing a violation.
        """
        # Live red-team finding V9: bracket-style prompts (`[user@host ~]$`,
        # common on RHEL-family fiction) are echo lines too — the old shape
        # only matched classic `user@host:~$`, so a draft serving `attacker`
        # under a bracket prompt passed the identity pin.
        prompt_shape = re.compile(
            r"^(?:[A-Za-z0-9_.\-]+@[A-Za-z0-9._\-]+[:#]|\[[A-Za-z0-9_.\-]+@[A-Za-z0-9._\-]+[~ ][^\]]*\])",
            re.MULTILINE,
        )
        lines: list[str] = []
        for line in text.splitlines():
            # V9b (live): real transcripts echo MULTIPLE prompts (trailing
            # shell ready-line, multi-command chains) — every echo line is
            # dropped, not just the first.
            if prompt_shape.search(line):
                continue
            lines.append(line)
        # Drop the first non-prompt line too when it echoes the command.
        if lines and lines[0].strip().split(" ")[0].strip("$") in {"whoami", "id"}:
            lines = lines[1:]
        return lines

    def _check_degenerate(self, text: str) -> list[str]:
        if len(text.strip()) <= 1:
            return ["degenerate: response is empty or single-character"]
        return []

    # ── protocol entry point ───────────────────────────────────────────────

    def verify(self, response: dict[str, Any] | str, session_context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Verify a deception response. Protocol-compatible with ResponseVerifier.

        Returns ``{"passed": bool, "issues": [...], "confidence": float}``.
        """
        ctx = session_context or {}
        if isinstance(response, str):
            response = {"response_text": response}
        text = (response.get("response_text") or "") if isinstance(response, dict) else ""
        session_id = (
            ctx.get("session_id") or (response.get("session_id") if isinstance(response, dict) else "") or "unknown"
        )
        skill = (
            (ctx.get("classification") or {}).get("skill_level")
            or ctx.get("skill_level")
            or (response.get("persona_used") if isinstance(response, dict) else "")
            or "novice"
        )
        user_input = str(ctx.get("attacker_input") or ctx.get("query") or "")

        issues: list[str] = []
        # Identity invariant source: when the session's fiction graph is
        # registered, ITS pinned identity is authoritative. Host-fiction
        # provisioning (HostFictionStore) may seed a session with the machine
        # pinned at first contact rather than the per-skill identity — the
        # box the attacker has been facing all along is the one verification
        # must enforce. Standalone callers keep the classification-derived
        # identity (previous behavior, byte-identical).
        session_graph = self._fictions.get(session_id) if self._fictions else None
        pinned_ident = getattr(session_graph, "identity", None) or identity_for(skill)
        issues += self._check_degenerate(text)
        issues += self._check_danger_signals(text)
        issues += self._check_identity_pin(user_input, text, skill, ident=pinned_ident)
        issues += self._check_fiction_contradictions(session_id, skill, text)
        strict_meta: dict[str, Any] = {}
        if self._profile == PROFILE_NAME:
            # The strict profile requires an authoritative pinned identity
            # snapshot from the harness. It never falls back to a
            # classification-derived identity.
            strict_ident = ctx.get("pinned_identity")
            strict = evaluate_strict_research(
                user_input,
                text,
                strict_ident if isinstance(strict_ident, dict) else None,
            )
            if strict.issue:
                issues.append(strict.issue)
            strict_meta = strict.to_dict()
        elif self._fail_closed:
            from ragin.cycle.supported_claims import check_supported_claim

            issues += check_supported_claim(user_input, text, pinned_ident, session_graph)

        verdict: dict[str, Any] = {
            "passed": not issues,
            "issues": issues,
            "confidence": 1.0 if not issues else 0.3,
            "verifier": "FictionConsistencyVerifier",
            # Declared so serve-path accounting can distinguish a verified
            # serve from a baseline pass-through (deterministic: False).
            "deterministic": True,
        }
        verdict.update(strict_meta)
        return verdict


__all__ = ["FictionConsistencyVerifier"]
