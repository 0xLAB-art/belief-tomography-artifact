"""Focused contract checks for the bounded Cowrie persona proof."""

from __future__ import annotations

import sys
import tempfile
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import persona_prompt_patch as prompt_patch  # noqa: E402
import prove_cowrie_persona_alignment_v1 as proof  # noqa: E402

# Structural stand-in for the pinned image's llm/protocol.py: the two anchors
# the patch rewrites, at the same indentation, with the same surrounding code.
FIXTURE_PROTOCOL = '''class CowrieConfig:
    home = ""

    @classmethod
    def get(cls, section, option, *, fallback=""):
        if (section, option) == ("llm", "home"):
            return cls.home or fallback
        return fallback


class Protocol:
    def __init__(self, avatar):
        self.user = avatar
        self.environ = avatar.environ
        self.hostname: str = self.user.server.hostname
        self.cwd = "/"
        self.data = None
        self.password_input = False

    def getProtoTransport(self):
        return None

    def _show_prompt(self):
        # Build a realistic prompt
        if self.user.username == "root":
            prompt = f"{self.user.username}@{self.hostname}:{self.cwd}# "
        else:
            prompt = f"{self.user.username}@{self.hostname}:{self.cwd}$ "

        self.terminal.write(prompt.encode("utf-8"))
'''


def _avatar(username: str, home: str) -> types.SimpleNamespace:
    avatar = types.SimpleNamespace(
        username=username,
        environ={},
        server=types.SimpleNamespace(hostname="web-srv-01"),
    )
    if home:
        avatar.home = home
    return avatar


def _patched_namespace(source: str = FIXTURE_PROTOCOL) -> dict[str, object]:
    patched = prompt_patch.patch_protocol_source(source)
    namespace: dict[str, object] = {}
    exec(compile(patched, "<fixture-protocol>", "exec"), namespace)  # noqa: S102
    return namespace


def _prompt_for(
    username: str, home: str, cwd: str | None = None, config_home: str = ""
) -> tuple[str, str]:
    namespace = _patched_namespace()
    namespace["CowrieConfig"].home = config_home  # type: ignore[attr-defined]
    writes: list[bytes] = []
    instance = namespace["Protocol"](_avatar(username, home))  # type: ignore[operator]
    instance.terminal = types.SimpleNamespace(write=writes.append)
    if cwd is not None:
        instance.cwd = cwd
    initial_cwd = instance.cwd
    instance._show_prompt()
    return writes[-1].decode(), initial_cwd


def test_terminal_parser_removes_pty_controls_but_keeps_observed_fields() -> None:
    raw = (
        b"Welcome to web-srv-01\r\n"
        b"\x1b[4hwebapp@web-srv-01:~$ whoami\r\n"
        b"\x1b[4lwebapp\r\n"
        b"\x1b[4hwebapp@web-srv-01:~$ "
    )
    parsed = proof.parse_terminal(raw, ["whoami"])
    assert parsed["banners"] == ["Welcome to web-srv-01"]
    assert parsed["turns"][0]["prompt_prefix"] == "webapp@web-srv-01:~$ "
    assert parsed["turns"][0]["answer_lines"] == ["webapp"]


def test_strict_transcript_prompt_echo_is_recorded_not_mistaken_for_a_turn() -> None:
    # RAGIN's strict transcript starts with its own `prompt$ command` line, so
    # the frontend echoes the command twice. The parser must still attribute
    # only `webapp` to the turn and record the duplicate.
    raw = (
        b"Welcome to web-srv-01\r\n"
        b"webapp@web-srv-01:~$ whoami\r\n"
        b"webapp@web-srv-01:~$ whoami\r\n"
        b"webapp\r\n"
        b"webapp@web-srv-01:~$ "
    )
    parsed = proof.parse_terminal(raw, ["whoami"])
    turn = parsed["turns"][0]
    assert turn["answer_lines"] == ["webapp"]
    assert turn["served_echo_lines"] == ["webapp@web-srv-01:~$ whoami"]
    assert parsed["outer_prompts"] == ["webapp@web-srv-01:~$ "]


def test_native_expectations_are_fixture_derived() -> None:
    assert proof.EXPECTED["native"]["hostname"] == ["web-srv-01"]
    assert proof.NATIVE_PROMPT == "webapp@web-srv-01:~$ "
    assert proof.IMAGE_ID.endswith("a30cd459")


def test_prompt_patch_anchors_are_exact_and_single_use() -> None:
    patched = prompt_patch.patch_protocol_source(FIXTURE_PROTOCOL)
    assert 'self.cwd = self._initial_cwd()' in patched
    assert 'self.cwd = "/"' not in patched
    assert 'cwd = "~" + cwd[len(home) :]' in patched
    with pytest.raises(prompt_patch.PatchError):
        prompt_patch.patch_protocol_source(FIXTURE_PROTOCOL.replace('self.cwd = "/"\n', ""))
    with pytest.raises(prompt_patch.PatchError):
        prompt_patch.patch_protocol_source(FIXTURE_PROTOCOL + FIXTURE_PROTOCOL)


def test_prompt_starts_in_home_and_renders_tilde_like_the_native_shell() -> None:
    prompt, initial_cwd = _prompt_for("webapp", "/home/webapp")
    assert initial_cwd == "/home/webapp"
    assert prompt == "webapp@web-srv-01:~$ "
    assert prompt == proof.NATIVE_PROMPT
    assert prompt == proof.RAGIN_PROMPT


def test_prompt_renders_home_subdirectories_and_absolute_paths() -> None:
    nested, _ = _prompt_for("webapp", "/home/webapp", "/home/webapp/app")
    assert nested == "webapp@web-srv-01:~/app$ "
    absolute, _ = _prompt_for("webapp", "/home/webapp", "/var/log")
    assert absolute == "webapp@web-srv-01:/var/log$ "
    root, _ = _prompt_for("root", "/root")
    assert root == "root@web-srv-01:~# "


def test_prompt_uses_configured_home_when_the_avatar_has_none() -> None:
    # The LLM avatar carries no passwd entry, so the persona home is config.
    prompt, initial_cwd = _prompt_for("webapp", "", config_home="/home/webapp")
    assert initial_cwd == "/home/webapp"
    assert prompt == "webapp@web-srv-01:~$ "


def test_prompt_without_a_declared_or_configured_home_falls_back_to_root() -> None:
    prompt, initial_cwd = _prompt_for("webapp", "")
    assert initial_cwd == "/"
    assert prompt == "webapp@web-srv-01:/$ "


def test_llm_arm_reachability_separates_auth_failure_from_generation() -> None:
    denied = (
        b"LLM request: {...}\n"
        b"LLM API error (status 401): {\"error\": \"unauthorized\"}\n"
        b"LLM request: {...}\n"
        b"LLM API error (status 401): {\"error\": \"unauthorized\"}\n"
    )
    verdict = proof.llm_arm_reachability(denied)
    assert verdict == {
        "llm_requests": 2,
        "unauthorized_401": 2,
        "other_api_errors": 0,
        "authenticated": False,
    }
    served = b"LLM request: {...}\nLLM response received\n"
    assert proof.llm_arm_reachability(served)["authenticated"] is True
    assert proof.llm_arm_reachability(b"")["authenticated"] is False


def test_loopback_proof_keeps_strict_verification_and_provider_off() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        env = proof.safe_env(Path(temp_dir))
        assert env["RAGIN_VERIFIER_PROFILE"] == "research_strict_v1"
        assert env["RAGIN_PROVIDER_ENABLED"] == "0"
    source = (ROOT / "scripts/prove_cowrie_persona_alignment_v1.py").read_text()
    assert '"COWRIE_LLM_API_KEY": LOCAL_API_KEY' in source
    # The RAGIN arm must mount the prompt patch; the native arm must not.
    assert "mounts=[(patch_info[\"patched_path\"], PROTOCOL_PATH_IN_IMAGE)]" in source
    assert "COWRIE_HONEYPOT_BACKEND={backend}" in source
