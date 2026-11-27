import json
import re
import subprocess
from collections.abc import Callable

import scripts.opencode_proxy as proxy


def exception_message(callback: Callable[[], object]) -> str:
    try:
        callback()
    except ValueError as exc:
        return str(exc)
    raise AssertionError("expected ValueError")


def test_build_prompt_allows_free_model_and_bounds_tokens():
    payload = proxy.build_prompt(
        {
            "model": "opencode/ling-3.1-flash-free",
            "messages": [{"role": "user", "content": "hello"}],
            "max_tokens": 99999,
        },
        ("opencode/ling-3.1-flash-free",),
    )

    assert payload["model"] == "opencode/ling-3.1-flash-free"
    assert payload["max_tokens"] == 4096
    assert "[USER]\nhello" in payload["prompt"]
    assert "Do not call tools" in payload["prompt"]


def test_default_allowlist_prioritizes_validated_space_bunny_model():
    assert proxy.configured_models()[0] == "opencode/space-bunny-free"


def test_build_prompt_rejects_non_allowlisted_model():
    message = exception_message(
        lambda: proxy.build_prompt(
            {"model": "opencode/claude-opus-5-5", "messages": [{"role": "user", "content": "hello"}]},
            ("opencode/ling-3.1-flash-free",),
        )
    )
    assert re.search("allowlist", message)


def test_build_prompt_rejects_oversized_message():
    message = exception_message(
        lambda: proxy.build_prompt(
            {"model": "opencode/ling-3.1-flash-free", "messages": [{"role": "user", "content": "x" * 32001}]},
            ("opencode/ling-3.1-flash-free",),
        )
    )
    assert re.search("bounded request size", message)


def test_extract_assistant_text_supports_json_event_shapes():
    stdout = "\n".join(
        [
            json.dumps({"type": "text", "part": {"text": "first "}}),
            json.dumps({"type": "message.part.updated", "properties": {"part": {"type": "text", "text": "second"}}}),
        ]
    )

    assert proxy.extract_assistant_text(stdout) == "first second"


def test_opencode_command_uses_safe_agent_and_no_auto_mode():
    command = proxy.opencode_command("opencode/ling-3.1-flash-free", "prompt", "/tmp/work")

    assert command[:2] == [proxy.DEFAULT_OPENCODE, "run"]
    assert "--pure" in command
    assert "--format" in command
    assert "--agent" in command
    assert command[command.index("--agent") + 1] == "ragin-safe"
    assert "--auto" not in command


def test_run_cli_completion_uses_safe_config_and_drops_legacy_credentials(monkeypatch):
    captured_command: list[str] = []
    captured_env: dict[str, str] = {}
    captured_stdin: object = None

    class Completed:
        returncode = 0
        stdout = json.dumps({"type": "text", "part": {"text": "generated"}})
        stderr = ""

    def fake_run(command, **kwargs):
        nonlocal captured_command, captured_env, captured_stdin
        captured_command = command
        captured_env = kwargs["env"]
        captured_stdin = kwargs["stdin"]
        return Completed()

    monkeypatch.setenv("OPENCODE_BIN", "/bin/true")
    monkeypatch.setenv("RAGIN_LLM_API_KEY", "legacy-secret-not-forwarded")
    monkeypatch.setenv("OPENROUTER_API_KEY", "provider-secret-not-forwarded")
    monkeypatch.setattr(subprocess, "run", fake_run)

    text, elapsed_ms = proxy.run_cli_completion(
        {"model": "opencode/ling-3.1-flash-free", "prompt": "hello", "max_tokens": 10}
    )

    assert text == "generated"
    assert elapsed_ms >= 0
    assert "RAGIN_LLM_API_KEY" not in captured_env
    assert "OPENROUTER_API_KEY" not in captured_env
    assert captured_env["OPENCODE_CONFIG"] == str(proxy.SAFE_CONFIG)
    assert captured_stdin is subprocess.DEVNULL
    assert captured_command[captured_command.index("--agent") + 1] == "ragin-safe"


def test_extract_assistant_text_rejects_empty_output():
    message = exception_message(lambda: proxy.extract_assistant_text("{\"type\":\"step-start\"}\n"))
    assert re.search("no assistant text", message)
