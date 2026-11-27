"""Supported-claim surface for the fail-closed verifier.

The base FictionConsistencyVerifier is CONTRADICTION-only: a draft passes
when it asserts nothing false. The S&P property statement needs the other
half — COMPLETENESS on a declared claim surface: for commands whose real-
Linux output is deterministic given the pinned machine identity (whoami,
id, uname, hostname, uptime, date, echo, two os-release file reads), the
draft must contain the right answer; hedging, echoing the query back, or
omitting the answer is a finding, not a pass. Commands outside the surface
return no handler requirements, so the verifier stays silent there — this
is what makes fail-closed SAFE to enable (recall does not collapse).

Supported-claim contract (property P1 becomes unconditional over this
surface):
  1. a supported command MUST be answered in the draft;
  2. the answer MUST match the machine identity (exact equality for
     identity facts, shape+consistency for parametric output);
  3. hedging (can't determine / unable to / not available / it depends),
     query echo (the transcript-echo class the CTI audit exposed), and
     identity contradiction each fail the draft;
  4. deterministic extraction only — no LLM, no fuzzy matching on the
     answer rules themselves.

Fail-closed semantics: when the surface module itself cannot answer
"supported or not" (malformed input), the command is treated as
UNSUPPORTED (no requirement) — the contradiction layer still guards it.
"""

from __future__ import annotations

import contextlib
import re
from collections.abc import Callable
from typing import Any

# ---------------------------------------------------------------------------
# Draft-level failure classes
# ---------------------------------------------------------------------------

# Hedge/refusal markers: the draft declines to answer. Real deterministic
# commands have exactly one output; "unable to determine" is a verifier
# finding, not a persona choice. (Deliberate-refusal personas are a
# deception-strategy concern and are represented on the bait/strategy
# surface, not by breaking P1 on the claim surface.)
_HEDGE_RE = re.compile(
    r"unable to determine|cannot determine|can't determine|not available|"
    r"no output returned|i cannot|i can't|it depends|\bunknown\b",
    re.IGNORECASE,
)

# Echo markers: the deterministic fallback echo class from the 2026-09-28
# CTI audit (`bash: <query>: command not found`, "(no output)"). A draft
# that echoes the command back has NOT answered it.
_ECHO_RE = re.compile(r"command not found|\(no output\)|not found\. try", re.IGNORECASE)


def _strip_echo_lines(text: str) -> str:
    """Drop transcript echo lines (prompt + command) so answer rules judge
    only what the machine PRINTED (mirrors verifier._answer_lines)."""
    prompt_shape = re.compile(
        r"^(?:[A-Za-z0-9_.\-]+@[A-Za-z0-9._\-]+[:#]|\[[A-Za-z0-9_.\-]+@[A-Za-z0-9._\-]+[~ ][^\]]*\])",
        re.MULTILINE,
    )
    return "\n".join(line for line in text.splitlines() if not prompt_shape.search(line))


def _is_echo(text: str) -> bool:
    return bool(_ECHO_RE.search(text))


def _is_hedge(text: str) -> bool:
    return bool(_HEDGE_RE.search(text))


# ---------------------------------------------------------------------------
# Command derivation (multi-command drafts answer their FIRST supported
# command; compound wrappers map to the inner deterministic command)
# ---------------------------------------------------------------------------

_WRAPPER_RE = re.compile(
    r"\b(?:sudo|doas|env|nohup|nice|command|builtin|time|timeout\s+\d+|"
    r"xargs|sh\s+-c|bash\s+-c|echo\s+\|)\b",
    re.IGNORECASE,
)


def derive_command(user_input: str) -> str:
    """Reduce a raw attacker input to the deterministic command it asks about.

    Handles: env prefixes (sudo/env/...), pipe wrappers, base64/hex-encoded
    payloads of a known command, composite wrappers ({ ...; whoami; }),
    and multi-command inputs (first supported command wins).
    """
    raw = (user_input or "").strip()
    if not raw:
        return ""
    # Decode single-stage base64/hex payloads: `echo <b64> | base64 -d`
    # The payload is captured by the SAME search that gated the branch: a
    # narrower second regex would raise AttributeError into the bare except
    # below and fail open to raw text.
    m = re.search(r"echo\s+([A-Za-z0-9+/=]{8,})\s*\|\s*base64\s+-d", raw, re.IGNORECASE)
    if m:
        import base64

        try:
            b64 = m.group(1)
            raw = base64.b64decode(b64 + "=" * (-len(b64) % 4)).decode("utf-8", "replace")
        except Exception:  # noqa: BLE001 — decode failure => treat as raw
            pass
    else:
        m = re.search(r"printf\s+([0-9a-fA-F]+)\s*\|\s?(?:xxd|printf)\s+-r\s+-p\s*%?", raw)
        if m:
            with contextlib.suppress(ValueError):
                raw = bytes.fromhex(m.group(1)).decode("utf-8", "replace")
    # Strip wrapper vocabulary for the LAST segment only (compound commands
    # split first, so each segment is judged on its own wrapper prefix).
    candidates: list[str] = []
    for segment in re.split(r"[;]|&&|\|\|", raw):
        seg = segment.strip()
        # pipe chains: the last stage decides the output
        if "|" in seg and "base64" not in seg:
            seg = seg.split("|")[-1].strip()
        seg = _WRAPPER_RE.sub(" ", seg).strip()
        if seg:
            candidates.append(seg)
    for seg in candidates:
        first = seg.split()[0].lower() if seg.split() else ""
        if first in _HANDLERS:
            return first
    return candidates[0].split()[0].lower() if candidates and candidates[0].split() else ""


# ---------------------------------------------------------------------------
# Handlers: (user_input, text, ident, graph) -> list[str] findings
# ident: the machine identity (pinned host-fiction identity when present,
# else identity_for(skill)); graph: the session FictionGraph (may be None).
# Return [] when the draft satisfies the claim.
# ---------------------------------------------------------------------------

HandlerT = Callable[[str, str, dict[str, Any], Any], list[str]]


def _need_answer(text: str, what: str) -> list[str]:
    findings: list[str] = []
    if not text.strip():
        findings.append(f"supported-claim: empty reply for '{what}'")
    else:
        if _is_echo(text):
            findings.append(f"supported-claim: '{what}' echoed, not answered")
        if _is_hedge(text):
            findings.append(f"supported-claim: '{what}' hedged instead of answered")
    return findings


def _handle_whoami(user_input: str, text: str, ident: dict[str, Any], graph: Any) -> list[str]:
    findings = _need_answer(text, "whoami")
    if findings:
        return findings
    answer = _strip_echo_lines(text)
    if re.search(rf"\b{re.escape(str(ident['user']))}\b", answer) is None:
        findings.append(f"supported-claim: whoami must be '{ident['user']}'")
    return findings


def _handle_id(user_input: str, text: str, ident: dict[str, Any], graph: Any) -> list[str]:
    findings = _need_answer(text, "id")
    if findings:
        return findings
    answer = _strip_echo_lines(text)
    # Full `id` prints the canonical triple; flag variants (-un/-u/-g) may
    # print the name or numeric id alone (V17 contract).
    is_variant = bool(re.search(r"\bid\s+-[a-zA-Z]+\b", user_input.lower()))
    canonical = f"uid={ident['uid']}({ident['user']})"
    if is_variant:
        if not re.search(rf"\b(?:{re.escape(str(ident['user']))}|{re.escape(str(ident['uid']))})\b", answer):
            findings.append(f"supported-claim: id variant must report '{ident['user']}'")
    elif canonical not in answer.replace(" ", ""):
        findings.append(f"supported-claim: id must report {canonical}")
    return findings


def _handle_hostname(user_input: str, text: str, ident: dict[str, Any], graph: Any) -> list[str]:
    findings = _need_answer(text, "hostname")
    if findings:
        return findings
    answer = _strip_echo_lines(text)
    host = str(ident.get("host", ""))
    if host and host not in answer and f"{host}." not in answer:
        findings.append(f"supported-claim: hostname must resolve to '{host}'")
    return findings


def _handle_uname(user_input: str, text: str, ident: dict[str, Any], graph: Any) -> list[str]:
    findings = _need_answer(text, "uname")
    if findings:
        return findings
    answer = _strip_echo_lines(text)
    lower = user_input.lower().strip()
    kernel = str(ident.get("kernel", ""))
    # uname -r: the kernel release; plain uname: s/gen-one-line; uname -a: all.
    if re.search(r"\buname\s+-r\b", lower):
        if kernel and kernel not in answer:
            findings.append(f"supported-claim: uname -r must report '{kernel}'")
    else:
        # Plain/-a/-s answers must at least carry the kernel release OR the
        # distro name — both are pinned facts of the same machine.
        distro = str(ident.get("distro", ""))
        if kernel and kernel not in answer and distro and distro.split()[0].lower() not in answer.lower():
            findings.append("supported-claim: uname must report pinned kernel or distro")
    return findings


def _handle_echo(user_input: str, text: str, ident: dict[str, Any], graph: Any) -> list[str]:
    findings = _need_answer(text, "echo")
    if findings:
        return findings
    # `echo <arg>` must print the argument back (deterministic POSIX).
    m = re.search(r"\becho\s+(.+)$", user_input.strip(), re.IGNORECASE)
    if m:
        arg = m.group(1).strip().strip("\"'").replace("$?", "0")
        if arg and arg.lower() not in _strip_echo_lines(text).lower():
            findings.append("supported-claim: echo must print its argument")
    return findings


def _handle_uptime(user_input: str, text: str, ident: dict[str, Any], graph: Any) -> list[str]:
    findings = _need_answer(text, "uptime")
    if findings:
        return findings
    answer = _strip_echo_lines(text)
    # Real uptime always carries: load averages + up duration + users count.
    shape_ok = (
        re.search(r"load average", answer, re.IGNORECASE)
        and re.search(r"\bup\b", answer, re.IGNORECASE)
        and re.search(r"\d+\s+users?\b", answer, re.IGNORECASE)
    )
    if not shape_ok:
        findings.append("supported-claim: uptime output lacks real-command shape")
    return findings


def _handle_date(user_input: str, text: str, ident: dict[str, Any], graph: Any) -> list[str]:
    findings = _need_answer(text, "date")
    if findings:
        return findings
    answer = _strip_echo_lines(text)
    # A real `date` prints a weekday; a fabricated prose answer usually
    # doesn't. Timezone/fact pinning is NOT required (clock legitimately
    # advances) — only the output SHAPE is deterministic.
    if not re.search(r"\b(mon|tue|wed|thu|fri|sat|sun)[a-z]*\b", answer, re.IGNORECASE):
        findings.append("supported-claim: date output lacks weekday shape")
    return findings


def _handle_os_release(user_input: str, text: str, ident: dict[str, Any], graph: Any) -> list[str]:
    """`cat /etc/os-release` (and the sourced variant): deterministic content
    from the pinned distro."""
    findings = _need_answer(text, "os-release")
    if findings:
        return findings
    answer = _strip_echo_lines(text)
    distro = str(ident.get("distro", ""))
    name_word = distro.split()[0] if distro else ""
    # PRETTY_NAME must carry the distro; VERSION_ID its major version.
    pretty_ok = bool(re.search(r"PRETTY_NAME", answer, re.IGNORECASE)) and name_word.lower() in answer.lower()
    major = distro.split()[1].split(".")[0] if distro and len(distro.split()) > 1 else ""
    version_ok = True
    if major and re.search(r"VERSION_ID", answer, re.IGNORECASE):
        version_ok = bool(re.search(rf"VERSION_ID\s*=\s*\"?{re.escape(major)}\b", answer, re.IGNORECASE))
    if not pretty_ok or not version_ok:
        findings.append(f"supported-claim: os-release must describe pinned distro '{distro}'")
    return findings


# The declared surface. Keys are the command word (first token) a real
# attacker would type. Anything not listed => no completeness requirement.
_HANDLERS: dict[str, HandlerT] = {
    "whoami": _handle_whoami,
    "id": _handle_id,
    "hostname": _handle_hostname,
    "uname": _handle_uname,
    "echo": _handle_echo,
    "uptime": _handle_uptime,
    "date": _handle_date,
    "cat": _handle_os_release,  # narrowed inside: only /etc/os-release paths
}

# `cat` is only supported for the os-release files — everything else (cat
# /etc/passwd, cat ~/.ssh/...) has NO deterministic content contract.
_OS_RELEASE_PATH_RE = re.compile(r"^cat\s+(/etc/os-release|/usr/lib/os-release)\b", re.IGNORECASE)


def supported_command(user_input: str) -> str | None:
    """The supported command this input asks about, or None when the input
    lies outside the declared surface (=> no completeness requirement)."""
    cmd = derive_command(user_input)
    if not cmd or cmd not in _HANDLERS:
        return None
    if cmd == "cat" and not _OS_RELEASE_PATH_RE.match((user_input or "").strip()):
        return None
    return cmd


def check_supported_claim(
    user_input: str,
    text: str,
    ident: dict[str, Any],
    graph: Any = None,
) -> list[str]:
    """Fail-closed completeness check for one attacker input.

    Returns a list of findings (empty = the claim is satisfied). Inputs
    outside the declared surface return [] without inspection — the
    contradiction layer (FictionConsistencyVerifier) still guards those.
    """
    cmd = supported_command(user_input)
    if cmd is None:
        return []
    handler = _HANDLERS[cmd]
    try:
        return handler(user_input or "", text or "", ident or {}, graph)
    except Exception:  # noqa: BLE001 — the surface must never crash the verifier
        # Fail-closed direction: an internal error yields a finding, not a
        # silent pass (a false REJECT is safe; a false PASS is the failure
        # mode this module exists to prevent).
        return [f"supported-claim: internal check error on '{cmd}'"]


def declared_surface() -> list[str]:
    """The command surface covered by the fail-closed contract (for the
    paper's Property-1 statement and the verifier benchmark)."""
    return sorted(_HANDLERS)
