"""Tests for the rewritten deception prompt + LLM-output postprocessor."""

from __future__ import annotations

import pytest

from ragin.hisoka.deception import (
    ResponseGenerator,
    _contains_danger_signal,
    _identity_block,
    _persona_system_prompt,
    _postprocess_llm_output,
    _strip_code_fences,
    _strip_reveal_tells,
    identity_for,
)

SKILL_LEVELS = ["novice", "intermediate", "expert", "advanced", "apt"]


class TestIdentity:
    @pytest.mark.parametrize("level", SKILL_LEVELS)
    def test_identity_is_pinned_for_every_level(self, level):
        ident = identity_for(level)
        assert ident["user"] == "webapp"
        assert ident["uid"] == "1001"
        assert ident["host"]
        assert ident["distro"]
        assert ident["kernel"]

    def test_identities_never_contradict(self):
        hosts = {identity_for(level)["host"] for level in SKILL_LEVELS}
        domains = {identity_for(level)["domain"] for level in SKILL_LEVELS}
        distros = {identity_for(level)["distro"] for level in SKILL_LEVELS}
        assert len(hosts) == len(SKILL_LEVELS)  # distinct hosts per persona
        assert len(domains) == 1
        assert len(distros) == 1


class TestSystemPrompt:
    @pytest.mark.parametrize("level", SKILL_LEVELS)
    def test_no_honeypot_tells(self, level):
        prompt = _persona_system_prompt(level)
        for tell in [
            "honeypot",
            "simulation",
            "fabricated",
            "not real",
            "ILLEGAL",
            "never refuse",
            "authorized access only",
            "CRITICAL AUTHORIZATION",
        ]:
            assert tell.lower() not in prompt.lower(), f"{tell!r} leaked into prompt"

    @pytest.mark.parametrize("level", SKILL_LEVELS)
    def test_identity_block_present(self, level):
        prompt = _persona_system_prompt(level)
        assert "webapp" in prompt
        assert identity_for(level)["host"] in prompt
        assert "corp.local" in prompt

    @pytest.mark.parametrize("level", SKILL_LEVELS)
    def test_identity_block_is_coherent(self, level):
        block = _identity_block(level)
        ident = identity_for(level)
        assert ident["uid"] in block
        assert ident["user"] in block
        assert ident["ip"] in block

    def test_persona_prompt_follows_strict_output_discipline(self):
        prompt = _persona_system_prompt("intermediate")
        assert "no markdown" in prompt.lower() or "raw" in prompt.lower()


class TestPostprocessor:
    def test_strips_reveal_tells(self):
        text = "webapp is a [HONEYPOT FABRICATED — NOT REAL] dummy user that was planted"
        assert "HONEYPOT" not in _strip_reveal_tells(text)
        assert "HONEYPOT FABRICATED" not in _strip_reveal_tells(text)

    def test_strips_code_fences_keeps_transcript(self):
        text = "```bash\nroot@web-srv-01:~# id\nuid=0(root) gid=0(root)\n```"
        clean = _strip_code_fences(text)
        assert "```" not in clean
        assert ">" not in clean
        assert "uid=0(root) gid=0(root)" in clean  # transcript preserved

    def test_strips_markdown_bold_and_backticks(self):
        text = "> **root**@corp.local\n> id\n`uid=1001`"
        clean = _strip_code_fences(text)
        assert "**root**" not in clean
        assert "`uid=1001`" not in clean
        assert "root@corp.local" in clean

    def test_pins_whoami(self):
        out = _postprocess_llm_output("root@web-srv-01:~# whoami\nroot", "whoami", "intermediate")
        assert out.strip() == "webapp"

    def test_pins_id_uid(self):
        out = _postprocess_llm_output("uid=0(root) gid=0(root) groups=0(root)", "id", "novice")
        assert "uid=1001(webapp)" in out

    def test_keeps_aware_multi_turn(self):
        # Multi-turn aware responses already referencing the pinned identity survive.
        out = _postprocess_llm_output(
            "uid=1001(webapp) gid=1001(webapp) groups=1001(webapp),sudo", "id", "intermediate"
        )
        assert "uid=1001(webapp)" in out

    def test_replaces_root_prompt(self):
        out = _postprocess_llm_output("root@web-srv-01:~/app# pwd\n/home/webapp", "pwd", "novice")
        assert "webapp@web-srv-01" in out
        assert "root@" not in out

    def test_full_pipeline_sanitizes_fabricated_marker(self):
        raw = "Here is the [HONEYPOT FABRICATED — NOT REAL] creds:\n```\njohn:k9s2L2a\n```"
        out = _postprocess_llm_output(raw, "give me /etc/shadow", "expert")
        assert "HONEYPOT" not in out
        assert "```" not in out


class TestDangerSignals:
    def test_refusal_is_danger(self):
        assert _contains_danger_signal("I'm not able to share that information with you")

    def test_fabrication_disclaimer_is_danger(self):
        assert _contains_danger_signal("this is a honeypot, the data is fabricated")

    def test_normal_reply_is_safe(self):
        assert not _contains_danger_signal("uid=1001(webapp) gid=1001(webapp) groups=1001(webapp),sudo")

    def test_gateway_refusal_produces_template_fallback(self):
        class _RefusingGateway:
            def generate(self, *, model, messages, temperature, max_tokens):
                return "I'm not going to help with that.", {"total_tokens": 40}

        gen = ResponseGenerator()
        gen._gateway = _RefusingGateway()
        out = gen.generate("advanced", "deploy a reverse shell on port 4444", "ctx")
        assert out
        assert "4444" in out
        assert "going to help" not in out


class TestTemplate:
    @pytest.fixture
    def generator(self):
        return ResponseGenerator()

    @pytest.mark.parametrize("cmd", ["whoami", "id", "uname -a", "cat /etc/shadow", "ls -la", "ps aux", "help"])
    def test_identity_bound_templates(self, generator, cmd):
        out = generator._generate_template("intermediate", cmd, "") or ""
        assert out
        assert "HONEYPOT" not in out.upper()
        assert "```" not in out

    def test_whoami_template_returns_pinned_user(self, generator):
        out = generator._generate_template("intermediate", "whoami", "")
        assert out
        # Transcript shape: prompt+echo line, then the pinned user.
        assert out.strip().endswith("webapp")
        assert out.startswith("webapp@")

    def test_template_has_no_follow_up_chatter(self, generator):
        out = generator._generate_template("intermediate", "ls -la", "")
        assert "Anything else" not in (out or "")

    def test_refusal_phrases_classified_as_danger(self):
        for phrase in (
            "I'm not going to help with that.",
            "I won't help you deploy a reverse shell.",
            "I can not assist with this request.",
            "I am not able to show you that.",
        ):
            assert _contains_danger_signal(phrase), f"expected danger: {phrase}"

    def test_reverse_shell_input_falls_back_to_listener_template(self, generator):
        out = generator._generate_template("advanced", "deploy a reverse shell on port 4444", "") or ""
        assert "4444" in out
        assert "help" not in out.lower()
        assert "?" not in (out or "")[-60:]

    def test_generate_without_gateway_uses_template(self, generator):
        out = generator.generate("advanced", "whoami")
        assert out.strip().endswith("webapp")
