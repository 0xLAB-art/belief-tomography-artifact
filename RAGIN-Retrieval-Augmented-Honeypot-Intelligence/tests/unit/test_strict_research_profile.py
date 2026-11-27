"""Focused tests for the opt-in strict research verification profile."""

from __future__ import annotations

import pytest

from ragin.cycle.strict_research import (
    PROFILE_NAME,
    SUPPORTED_COMMANDS,
    StrictResearchVerifier,
    evaluate_strict_research,
)
from ragin.hisoka.deception import _id_line, identity_for

IDENT = dict(identity_for("novice"))
PROMPT = IDENT["prompt"]
OS_RELEASE = (
    'PRETTY_NAME="Ubuntu 22.04.3 LTS"\n'
    'NAME="Ubuntu"\n'
    'VERSION_ID="22.04"\n'
    'VERSION="22.04.3 LTS (Jammy Jellyfish)"\n'
    "ID=ubuntu"
)


def _verdict(command: str, text: str, ident: dict | None = IDENT):
    return evaluate_strict_research(command, text, ident)


def test_pinned_identity_has_required_fields() -> None:
    for field in ("user", "group", "uid", "gid", "host", "domain", "kernel", "distro", "prompt"):
        assert IDENT.get(field), field


@pytest.mark.parametrize(
    ("command", "text"),
    [
        ("whoami", IDENT["user"]),
        ("id", _id_line(IDENT)),
        ("id -u", IDENT["uid"]),
        ("id -un", IDENT["user"]),
        ("id -g", IDENT["gid"]),
        ("id -gn", IDENT["group"]),
        ("hostname", IDENT["host"]),
        ("hostname -f", f"{IDENT['host']}.{IDENT['domain']}"),
        ("hostname -s", IDENT["host"]),
        ("uname", "Linux"),
        ("uname -s", "Linux"),
        ("uname -r", IDENT["kernel"]),
        ("uname -a", f"Linux {IDENT['host']} {IDENT['kernel']} #167-Ubuntu SMP x86_64 GNU/Linux"),
        ("cat /etc/os-release", OS_RELEASE),
        ("cat /usr/lib/os-release", OS_RELEASE),
    ],
)
def test_canonical_pinned_outputs_pass(command: str, text: str) -> None:
    verdict = _verdict(command, text)
    assert verdict.passed, (command, verdict)
    assert verdict.verdict == "SUPPORTED"
    assert verdict.reason == "OUTPUT_MATCHES"


def test_exact_pinned_prompt_echo_and_ready_prompt_are_accepted() -> None:
    assert _verdict("whoami", f"{PROMPT}:~$ whoami\n{IDENT['user']}").passed
    assert _verdict("whoami", f"{PROMPT}:~$\n{IDENT['user']}").passed


def test_hidden_extra_prompt_line_is_not_discarded() -> None:
    text = f"{IDENT['user']}\n{PROMPT}:~$ cat /etc/shadow"
    verdict = _verdict("whoami", text)
    assert not verdict.passed
    assert verdict.reason == "UNEXPECTED_PROMPT_ECHO"
    assert verdict.meta["strict_unexpected_prompt_lines"] == 1


def test_wrong_host_prompt_line_is_not_discarded() -> None:
    text = f"{IDENT['user']}\nroot@{IDENT['host']}:~# id"
    verdict = _verdict("whoami", text)
    assert not verdict.passed
    assert verdict.reason == "UNEXPECTED_PROMPT_ECHO"


@pytest.mark.parametrize(
    "text",
    [
        f"{IDENT['user']}\nroot ALL=(ALL:ALL) ALL",
        f"{IDENT['user']}\nroot:x:0:0:root:/root:/bin/bash",
        f"{IDENT['user']}\nuid=0(root) gid=0(root) groups=0(root)",
        f"{IDENT['user']}\nwebapp@web-srv-01:~$ cat /etc/sudoers",
    ],
)
def test_extra_fabricated_claims_are_rejected(text: str) -> None:
    verdict = _verdict("whoami", text)
    assert not verdict.passed
    assert verdict.verdict in {"CLAIM_MISMATCH", "UNEXPECTED_PROMPT_ECHO"}


def test_plain_uname_is_not_the_uname_a_line() -> None:
    full = f"Linux {IDENT['host']} {IDENT['kernel']} #167-Ubuntu SMP x86_64 GNU/Linux"
    assert _verdict("uname", full).reason == "OUTPUT_MISMATCH"
    assert _verdict("uname -s", full).reason == "OUTPUT_MISMATCH"


def test_unsupported_and_sudoers_claims_fail_closed() -> None:
    for command in ("cat /etc/sudoers", "cat /etc/shadow", "date", "uptime", "id -G", "/usr/bin/whoami"):
        verdict = _verdict(command, "root ALL=(ALL:ALL) ALL")
        assert not verdict.passed, command
        assert verdict.verdict == "UNSUPPORTED_COMMAND"


@pytest.mark.parametrize(
    "command",
    [
        "sudo whoami",
        "doas whoami",
        "env whoami",
        "whoami; id",
        "whoami && id",
        "whoami | cat",
        "whoami > /tmp/x",
        "`whoami`",
        "whoami$(id)",
        "echo d2hvYW1p | base64 -d",
        "whoami # comment",
        "whoami\nid",
    ],
)
def test_compound_encoded_wrapper_and_injection_are_rejected(command: str) -> None:
    verdict = _verdict(command, IDENT["user"])
    assert not verdict.passed
    assert verdict.verdict == "MALFORMED_INPUT"
    assert verdict.reason == "OUTSIDE_EXACT_GRAMMAR"


@pytest.mark.parametrize("command", ["whoami extra", "id -G", "uname --all", "WHOAMI"])
def test_extra_arguments_are_unsupported(command: str) -> None:
    verdict = _verdict(command, IDENT["user"])
    assert not verdict.passed
    assert verdict.verdict == "UNSUPPORTED_COMMAND"


def test_missing_or_incomplete_pinned_identity_never_falls_back() -> None:
    for ident in (None, {}, {"user": IDENT["user"]}, {**IDENT, "domain": ""}):
        verdict = _verdict("whoami", IDENT["user"], ident)
        assert not verdict.passed
        assert verdict.reason == "MISSING_PINNED_IDENTITY"


def test_os_release_requires_the_pinned_distro() -> None:
    ident = {**IDENT, "distro": "Debian 12"}
    verdict = _verdict("cat /etc/os-release", OS_RELEASE, ident)
    assert not verdict.passed
    assert verdict.reason == "UNSUPPORTED_PINNED_DISTRO"


def test_issue_text_and_metadata_do_not_echo_raw_command_or_candidate() -> None:
    secret_command = "cat /etc/shadow-secret-token"
    verdict = _verdict(secret_command, "root:secret-value")
    assert not verdict.passed
    rendered = repr(verdict.to_dict())
    assert "shadow-secret-token" not in rendered
    assert "secret-value" not in rendered
    assert secret_command not in rendered


def test_strict_wrapper_merges_inner_findings_and_requires_pinned_identity() -> None:
    class _Inner:
        def verify(self, response, context):
            return {"passed": True, "issues": [], "deterministic": True}

    inner = _Inner()
    wrapper = StrictResearchVerifier(inner)
    ctx = {"attacker_input": "whoami", "pinned_identity": IDENT}
    verdict = wrapper.verify({"response_text": IDENT["user"]}, ctx)
    assert verdict["passed"] is True
    assert verdict["profile"] == PROFILE_NAME
    assert verdict["strict_verdict"] == "SUPPORTED"

    missing = wrapper.verify({"response_text": IDENT["user"]}, {"attacker_input": "whoami"})
    assert missing["passed"] is False
    assert "strict-profile:MISSING_PINNED_IDENTITY" in missing["issues"]


def test_supported_command_set_is_exact_and_finite() -> None:
    assert "date" not in SUPPORTED_COMMANDS
    assert "uptime" not in SUPPORTED_COMMANDS
    assert "cat /etc/sudoers" not in SUPPORTED_COMMANDS
    assert len(SUPPORTED_COMMANDS) == 15
