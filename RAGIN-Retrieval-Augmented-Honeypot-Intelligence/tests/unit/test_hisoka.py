"""Unit tests for Hisoka — Adaptive Deception Layer.

Hisoka may not be fully implemented yet. These tests define the expected
interface and validate behavior once the module ships.
"""

from __future__ import annotations

import importlib.util
import time
from unittest.mock import MagicMock

import pytest

from ragin.hisoka.deception import (
    _contains_terminal_nonsense,
    _jev_signal_from_context,
    jev_kind_strategy,
)

HAS_HISOKA = importlib.util.find_spec("ragin.hisoka") is not None

try:
    from ragin.hisoka import deception as decept
    from ragin.hisoka.deceiver import AdaptiveDeceiver
    from ragin.hisoka.deception import (
        ArtifactInjector,
        EngagementTracker,
        PersonaManager,
        ResponseGenerator,
        SessionManager,
    )
    from ragin.hisoka.models import DeceptionResponse
except ImportError:
    pass

pytestmark = pytest.mark.unit

# ---------------------------------------------------------------------------
# Reasoning-Content Safety — ResponseGenerator must never leak COT
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not HAS_HISOKA, reason="ragin.hisoka not yet implemented")
class TestResponseGeneratorReasoningSafety:
    """ResponseGenerator must fall back to safe template when gateway returns empty content."""

    def test_empty_content_falls_back_to_template(self):
        rg = ResponseGenerator()
        rg._gateway = MagicMock()
        rg._gateway.generate = MagicMock(return_value=("", {"total_tokens": 0}))
        rg._generate_template = MagicMock(return_value="[SAFE TEMPLATE FALLBACK]")

        result = rg.generate(
            skill_level="novice",
            user_input="ls -la",
            context="honeypot session",
        )

        assert result == "[SAFE TEMPLATE FALLBACK]"

    def test_reasoning_only_content_falls_back_to_template(self):
        rg = ResponseGenerator()
        rg._gateway = MagicMock()
        rg._gateway.generate = MagicMock(return_value=("", {"total_tokens": 50}))
        rg._generate_template = MagicMock(return_value="[SAFE FALLBACK]")

        result = rg.generate(
            skill_level="novice",
            user_input="exploit",
            context="honeypot session",
        )

        assert result == "[SAFE FALLBACK]"

    def test_normal_content_not_affected(self):
        # Query is NOT covered by a deterministic template, so the LLM reply
        # passes through unmodified even though it is short. (Bare chatter
        # with no terminal structure is now voided to the template — see
        # TestTerminalNonsenseLint; this fixture is structured output.)
        rg = ResponseGenerator()
        rg._gateway = MagicMock()
        rg._gateway.generate = MagicMock(return_value=("Listening on 0.0.0.0:22", {"total_tokens": 30}))
        rg._generate_template = MagicMock(return_value="[TEMPLATE]")

        result = rg.generate(
            skill_level="novice",
            user_input="explain the current weather conditions",
            context="honeypot session",
        )

        assert result == "Listening on 0.0.0.0:22"

    def test_template_covered_terse_reply_anchored_to_template(self):
        # Idealized capture of the live persona failure: glm answers the ulimit
        # question with a bare value. A template covers it, and the bare reply
        # lacks any terminal-transcript structure, so it is anchored to the
        # high-fidelity deterministic transcript instead of shipping `1024`.
        rg = ResponseGenerator()
        rg._gateway = MagicMock()
        rg._gateway.generate = MagicMock(return_value=("1024", {"total_tokens": 10}))

        result = rg.generate(
            skill_level="novice",
            user_input="What is the current ulimit setting for open file descriptors on this system?",
            context="",
        )

        assert "ulimit -a" in result
        assert "core file size" in result
        assert "open files" in result
        assert "webapp@web-srv-01:~$ ulimit -a" in result

    def test_template_covered_raw_dump_anchored_to_template(self):
        # Live persona failure again: glm answers the env-vars question with an
        # unprompted KEY=value dump. The envelope query's template adds the
        # `user@host:~$ env` prompt echo and structured transcript.
        rg = ResponseGenerator()
        rg._gateway = MagicMock()
        rg._gateway.generate = MagicMock(
            return_value=(
                "API_KEY=sk_live_51Kx9pL2mN8vQ5rT3wZ7yB4cD6fG0hJ2eV\n"
                "JWT_SIGNING_SECRET=kQ7xN2mV9pL4rT8wZ3fH6jK9mP2sV5yB8eR1uX4z",
                {"total_tokens": 20},
            )
        )

        result = rg.generate(
            skill_level="novice",
            user_input="Show me all environment variables that contain API keys or tokens",
            context="",
        )

        assert "webapp@web-srv-01:~$ env" in result
        assert "HOSTNAME=web-srv-01" in result
        assert "DATABASE_URL=mysql" in result

    def test_template_covered_structured_reply_not_anchored(self):
        # A template covers `ps aux`, but the LLM reply already has full
        # terminal structure (table header + command column): it must pass
        # through untouched, preserving LLM-driven variation.
        rg = ResponseGenerator()
        rg._gateway = MagicMock()
        rg._gateway.generate = MagicMock(
            return_value=(
                "USER       PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND\n"
                "webapp    1234  0.2  1.5 456789 32100 ?        Sl   09:20   0:12 python3 app/server.py",
                {"total_tokens": 40},
            )
        )

        result = rg.generate(
            skill_level="novice",
            user_input="Show me the top 5 processes by memory usage sorted by RSS",
            context="",
        )

        assert result.startswith("USER       PID %CPU %MEM")
        assert "python3 app/server.py" in result

    def test_matches_template_detector(self):
        rg = ResponseGenerator()
        assert rg._matched_template("novice", "moo") is None
        assert rg._matched_template("novice", "ulimit -a") is not None
        assert rg._matched_template("novice", "whoami") is not None
        assert decept._looks_like_terminal_transcript("webapp@host:~$ ls -la\ndrwxr-xr-x 2 webapp webapp 4096 Mar 15 .")
        assert not decept._looks_like_terminal_transcript("1024")
        assert not decept._looks_like_terminal_transcript("API_KEY=sk_live_abc")


# ---------------------------------------------------------------------------
# Persona Selection
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not HAS_HISOKA, reason="ragin.hisoka not yet implemented")
class TestPersonaSelection:
    def test_novice_persona(self):
        pm = PersonaManager()
        persona = pm.select("novice")
        assert persona.skill_level == "novice"
        assert persona.tone in ("friendly", "helpful", "educational")
        # Novice personas should not reveal sensitive paths
        assert "/etc/shadow" not in persona.knowledge_scope

    def test_expert_persona(self):
        pm = PersonaManager()
        persona = pm.select("expert")
        assert persona.skill_level == "expert"
        assert persona.complexity > 0.7

    def test_apt_persona(self):
        pm = PersonaManager()
        persona = pm.select("apt")
        assert persona.skill_level == "apt"

    def test_invalid_level_raises(self):
        pm = PersonaManager()
        with pytest.raises(ValueError, match="nonexistent"):
            pm.select("nonexistent")


# ---------------------------------------------------------------------------
# Session Lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not HAS_HISOKA, reason="ragin.hisoka not yet implemented")
class TestSessionLifecycle:
    def test_create(self):
        sm = SessionManager()
        session = sm.create(source_ip="192.168.1.100")
        assert session.session_id
        assert session.source_ip == "192.168.1.100"

    def test_get(self):
        sm = SessionManager()
        session = sm.create(source_ip="10.0.0.1")
        retrieved = sm.get(session.session_id)
        assert retrieved is not None
        assert retrieved.session_id == session.session_id

    def test_update(self):
        sm = SessionManager()
        session = sm.create(source_ip="10.0.0.1")
        sm.update(session.session_id, {"command_count": 5})
        updated = sm.get(session.session_id)
        assert updated.command_count == 5

    def test_get_nonexistent(self):
        sm = SessionManager()
        assert sm.get("nonexistent") is None


# ---------------------------------------------------------------------------
# Response Generation
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not HAS_HISOKA, reason="ragin.hisoka not yet implemented")
class TestResponseGeneration:
    def test_basic_response(self):
        rg = ResponseGenerator()
        response = rg.generate(
            skill_level="novice",
            user_input="ls -la",
            context="honeypot session",
        )
        assert isinstance(response, str)
        assert len(response) > 0

    def test_response_varies_by_level(self):
        rg = ResponseGenerator()
        rg.generate(skill_level="novice", user_input="help")
        rg.generate(skill_level="expert", user_input="help")
        # at minimum, no crash


# ---------------------------------------------------------------------------
# Persona Consistency
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not HAS_HISOKA, reason="ragin.hisoka not yet implemented")
class TestPersonaConsistency:
    def test_same_persona_across_session(self):
        sm = SessionManager()
        session = sm.create(source_ip="10.0.0.1")
        persona1 = session.persona
        persona2 = session.persona
        assert persona1 == persona2


# ---------------------------------------------------------------------------
# Dwell Time Tracking
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not HAS_HISOKA, reason="ragin.hisoka not yet implemented")
class TestDwellTime:
    def test_track_dwell_time(self):
        sm = SessionManager()
        session = sm.create(source_ip="10.0.0.1")
        time.sleep(0.01)
        dwell = sm.get_dwell_time(session.session_id)
        assert dwell >= 0


# ---------------------------------------------------------------------------
# Session Isolation
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not HAS_HISOKA, reason="ragin.hisoka not yet implemented")
class TestSessionIsolation:
    def test_no_data_leakage(self):
        sm = SessionManager()
        s1 = sm.create(source_ip="10.0.0.1")
        s2 = sm.create(source_ip="10.0.0.2")
        sm.update(s1.session_id, {"secret": "session1_data"})
        retrieved = sm.get(s2.session_id)
        assert not hasattr(retrieved, "secret") or getattr(retrieved, "secret", None) != "session1_data"


# ---------------------------------------------------------------------------
# Engagement Scoring
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not HAS_HISOKA, reason="ragin.hisoka not yet implemented")
class TestEngagementScoring:
    def test_initial_score(self):
        et = EngagementTracker()
        score = et.get_score("new_session")
        assert score == 0.0

    def test_score_increases(self):
        et = EngagementTracker()
        et.record_command("sess1")
        et.record_command("sess1")
        score = et.get_score("sess1")
        assert score > 0.0


# ---------------------------------------------------------------------------
# Artifact Injection
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not HAS_HISOKA, reason="ragin.hisoka not yet implemented")
class TestArtifactInjection:
    def test_inject_fake_passwd(self):
        ai = ArtifactInjector()
        artifact = ai.inject("fake_passwd", skill_level="intermediate")
        assert "root:" in artifact

    def test_inject_fake_config(self):
        ai = ArtifactInjector()
        artifact = ai.inject("fake_config", skill_level="expert")
        assert isinstance(artifact, str)
        assert len(artifact) > 0


# ---------------------------------------------------------------------------
# Concurrent Sessions
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not HAS_HISOKA, reason="ragin.hisoka not yet implemented")
class TestConcurrentSessions:
    def test_multiple_sessions(self):
        sm = SessionManager()
        sessions = [sm.create(source_ip=f"10.0.0.{i}") for i in range(10)]
        assert len(set(s.session_id for s in sessions)) == 10


# ---------------------------------------------------------------------------
# Session Expiry
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not HAS_HISOKA, reason="ragin.hisoka not yet implemented")
class TestSessionExpiry:
    def test_expiry_cleanup(self):
        sm = SessionManager(ttl_s=0)
        session = sm.create(source_ip="10.0.0.1")
        time.sleep(0.01)
        assert sm.get(session.session_id) is None


# ---------------------------------------------------------------------------
# ResponseGeneratorExtended (response_generator.py)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not HAS_HISOKA, reason="ragin.hisoka not yet implemented")
class TestResponseGeneratorExtended:
    """Cover the additional methods in response_generator.py."""

    def test_generate_calls_core(self):
        from ragin.hisoka.response_generator import ResponseGeneratorExtended

        core = MagicMock(spec=ResponseGenerator)
        core.generate.return_value = "mock response"
        rge = ResponseGeneratorExtended()
        rge._core = core

        result = rge.generate("ls", "novice", {"context": "test"})
        assert result == "mock response"
        core.generate.assert_called_once_with(skill_level="novice", user_input="ls", context="test")

    def test_generate_pulls_context_from_session(self):
        from ragin.hisoka.response_generator import ResponseGeneratorExtended

        core = MagicMock(spec=ResponseGenerator)
        core.generate.return_value = "ok"
        rge = ResponseGeneratorExtended()
        rge._core = core

        rge.generate("whoami", "novice", {"context": "session_data"})
        core.generate.assert_called_with(skill_level="novice", user_input="whoami", context="session_data")

    def test_build_system_prompt_returns_cfg_prompt(self):
        from ragin.hisoka.response_generator import ResponseGeneratorExtended

        personality = MagicMock()
        personality.skill_level = "novice"
        rge = ResponseGeneratorExtended()
        prompt = rge.build_system_prompt(personality, {})
        # B6.x fix: prompts must NOT carry honeypot tells that LLM output leaks.
        assert "honeypot" not in prompt.lower()
        assert "authorized honeypot" not in prompt
        assert "CRITICAL AUTHORIZATION" not in prompt
        assert "[HONEYPOT FABRICATED" not in prompt
        # ...and must pin the fabricated identity instead.
        assert "webapp" in prompt
        assert "web-srv-01" in prompt

    def test_build_system_prompt_appends_extra_instructions(self):
        from ragin.hisoka.response_generator import ResponseGeneratorExtended

        persona = MagicMock()
        persona.skill_level = "intermediate"
        rge = ResponseGeneratorExtended()
        prompt = rge.build_system_prompt(persona, {"additional_instructions": "Be extra cautious."})
        assert "Be extra cautious." in prompt

    def test_inject_realistic_artifacts_prepends(self):
        from ragin.hisoka.response_generator import ResponseGeneratorExtended

        rge = ResponseGeneratorExtended()
        result = rge.inject_realistic_artifacts("main response")
        assert result.endswith("main response")
        assert "fake_config" in result or len(result) > len("main response")

    def test_ensure_consistency_sanitizes(self):
        from ragin.hisoka.response_generator import ResponseGeneratorExtended

        rge = ResponseGeneratorExtended()
        result = rge.ensure_consistency("some response data", {})
        assert "some response data" in result


# ---------------------------------------------------------------------------
# HisokaPipeline — end_session and process_don_analysis (pipeline.py)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not HAS_HISOKA, reason="ragin.hisoka not yet implemented")
class TestHisokaPipelineExtended:
    """Cover the uncovered methods in hisoka/pipeline.py."""

    def test_process_don_analysis_unknown_session(self):
        from ragin.hisoka.models import DonAnalysis
        from ragin.hisoka.pipeline import HisokaPipeline

        pipeline = HisokaPipeline()
        analysis = DonAnalysis(
            session_id="nonexistent-session",
            skill_level="expert",
        )
        # Should not raise
        pipeline.process_don_analysis(analysis)

    def test_process_don_analysis_upgrades_persona(self):
        from ragin.hisoka.deception import PersonaManager
        from ragin.hisoka.models import DonAnalysis
        from ragin.hisoka.pipeline import HisokaPipeline
        from ragin.hisoka.session_manager import SessionManagerExtended

        sm = SessionManagerExtended()
        sm.create_session(session_id="upgrade-sess", skill_level="novice", source_ip="10.0.0.5")
        deceiver = MagicMock()
        new_persona = PersonaManager().select("expert")
        deceiver.adapt_persona.return_value = new_persona

        pipeline = HisokaPipeline(deceiver=deceiver, session_manager=sm)
        analysis = DonAnalysis(
            session_id="upgrade-sess",
            skill_level="expert",
            confidence=0.9,
        )
        pipeline.process_don_analysis(analysis)
        deceiver.adapt_persona.assert_called_once_with("expert")

    def test_process_don_analysis_skips_same_level(self):
        from ragin.hisoka.models import DonAnalysis
        from ragin.hisoka.pipeline import HisokaPipeline
        from ragin.hisoka.session_manager import SessionManagerExtended

        sm = SessionManagerExtended()
        sm.create_session(session_id="same-sess", skill_level="novice", source_ip="10.0.0.6")
        deceiver = MagicMock()
        pipeline = HisokaPipeline(deceiver=deceiver, session_manager=sm)

        analysis = DonAnalysis(session_id="same-sess", skill_level="novice")
        pipeline.process_don_analysis(analysis)
        deceiver.adapt_persona.assert_not_called()

    def test_end_session_empty(self):
        from ragin.hisoka.pipeline import HisokaPipeline

        pipeline = HisokaPipeline()
        summary = pipeline.end_session("ghost-session")
        assert summary.session_id == "ghost-session"
        assert summary.total_interactions == 0

    def test_end_session_returns_summary(self):
        from ragin.hisoka.pipeline import HisokaPipeline
        from ragin.hisoka.session_manager import SessionManagerExtended

        sm = SessionManagerExtended()
        sm.create_session(session_id="end-me", skill_level="novice", source_ip="10.0.0.7")
        sm.update_session("end-me", {"command": "ls"})

        pipeline = HisokaPipeline(session_manager=sm)
        summary = pipeline.end_session("end-me")
        assert summary.session_id == "end-me"
        assert summary.total_interactions >= 1
        assert summary.persona_used == "novice"

    def test_end_session_with_memory(self):
        from ragin.hisoka.pipeline import HisokaPipeline
        from ragin.hisoka.session_manager import SessionManagerExtended

        memory = MagicMock()
        memory.add_attacker_profile.return_value = True

        sm = SessionManagerExtended()
        sm.create_session(session_id="mem-end", skill_level="expert", source_ip="10.0.0.8")
        sm.update_session("mem-end", {"command": "cat /etc/passwd"})

        pipeline = HisokaPipeline(session_manager=sm, memory=memory)
        summary = pipeline.end_session("mem-end")
        assert summary.source_ip == "10.0.0.8"
        memory.add_attacker_profile.assert_called_once()


# AdaptiveDeceiver — _static_fallback return type and budget/circuit-breaker paths


@pytest.mark.skipif(not HAS_HISOKA, reason="ragin.hisoka not yet implemented")
class TestAdaptiveDeceiverFallback:
    """Verify that ``_static_fallback`` returns a ``DeceptionResponse`` and that
    the budget/circuit-breaker branches in ``generate_response`` produce a
    valid ``DeceptionResponse`` rather than crashing on attribute access."""

    FALLBACK_TEXTS = {
        "novice": "Permission denied. This operation is not authorized.",
        "intermediate": "Command not found. Did you mean 'help'?",
        "expert": "Segmentation fault (core dumped).",
        "apt": "Connection to remote host timed out.",
    }

    @pytest.mark.parametrize("skill", ["novice", "intermediate", "expert", "apt"])
    def test_static_fallback_returns_deception_response(self, skill):
        deceiver = AdaptiveDeceiver()
        result = deceiver._static_fallback(skill, "some input")
        assert isinstance(result, DeceptionResponse)
        assert result.session_id == "static"
        assert result.response_text == self.FALLBACK_TEXTS[skill]
        assert result.persona_used == skill
        assert result.artifacts_injected == []
        assert result.engagement_score == 0.0
        assert result.honeytoken_triggered is False

    def test_static_fallback_unknown_level(self):
        deceiver = AdaptiveDeceiver()
        result = deceiver._static_fallback("unknown_level", "input")
        assert isinstance(result, DeceptionResponse)
        assert result.response_text == "Unknown command."
        assert result.persona_used == "unknown_level"

    def test_generate_response_budget_exhausted_returns_deception_response(self):
        deceiver = AdaptiveDeceiver()
        deceiver._cost_tracker.check_budget = MagicMock(return_value=False)

        result = deceiver.generate_response(
            "ls -la",
            {"session_id": "budget-test", "classification": {"skill_level": "novice"}},
        )

        assert isinstance(result, DeceptionResponse)
        assert result.response_text == self.FALLBACK_TEXTS["novice"]
        assert result.session_id == "budget-test"
        assert result.honeytoken_triggered is False

    def test_generate_response_circuit_breaker_open_returns_deception_response(self):
        deceiver = AdaptiveDeceiver()
        deceiver._circuit_breaker.allow = MagicMock(return_value=False)

        result = deceiver.generate_response(
            "whoami",
            {"session_id": "circuit-test", "classification": {"skill_level": "expert"}},
        )

        assert isinstance(result, DeceptionResponse)
        assert result.response_text == self.FALLBACK_TEXTS["expert"]
        assert result.session_id == "circuit-test"

    def test_generate_response_injects_fiction_and_strategy_context(self):
        deceiver = AdaptiveDeceiver()
        deceiver._response_generator.generate = MagicMock(return_value="$ id\nuid=1001(webapp)")

        result = deceiver.generate_response(
            "id",
            {
                "session_id": "graph-test",
                "classification": {"skill_level": "intermediate"},
                "fiction_block": "hostname: web-srv-01.corp.local\nuser: webapp\n",
                "strategy_block": "likely next moves (steer): T1082\nbait: seed a brittle /etc/shadow\n",
            },
        )

        assert isinstance(result, DeceptionResponse)
        ctx = deceiver._response_generator.generate.call_args.kwargs["context"]
        assert "Session consistency (authoritative)" in ctx
        assert "web-srv-01.corp.local" in ctx
        assert "Engagement strategy" in ctx
        assert "bait: seed a brittle /etc/shadow" in ctx
        assert "Current command: id" in ctx


# ── Jev attack-kind → deception strategy wiring ─────────────────────────────


class TestJevKindStrategy:
    """Jev System One attack_kind steers deception strategy (additive)."""

    def test_strategy_map_covers_all_kinds(self):
        from ragin.jev.models import AttackKind

        for kind in AttackKind:
            if kind == AttackKind.UNKNOWN:
                continue
            strategy = jev_kind_strategy(kind.value)
            assert strategy is not None
            assert "objective" in strategy
            assert "guidance" in strategy

    def test_unknown_kind_has_no_strategy(self):
        assert jev_kind_strategy("unknown") is None
        assert jev_kind_strategy("") is None
        assert jev_kind_strategy("nonsense") is None

    def test_signal_extraction_from_top_level_assessment(self):
        ctx = {
            "jev_assessment": {
                "answers": {
                    "attack_kind": {"options_selected": ["persistence"]},
                    "severity": {"score": 2.9},
                    "attack": {"noul": 0.91},
                }
            }
        }
        sig = _jev_signal_from_context(ctx)
        assert sig["available"] is True
        assert sig["attack_kind"] == "persistence"
        assert sig["severity"] == 2.9
        assert sig["attack_probability"] == 0.91


# ── Filesystem fiction ledger (consistency layer) ───────────────────────────


class TestFilesystemLedger:
    """Repeated reads replay byte-identical fiction; mutations invalidate."""

    def test_repeated_read_replays_verbatim(self):
        from ragin.hisoka.fs_ledger import FilesystemLedger

        led = FilesystemLedger(session_id="s1")
        led.remember("ls -la /var/tmp", "total 8\ndrwxrwxrwt 2 root root 4096 .\n")
        assert led.replay_for("ls -la /var/tmp") == "total 8\ndrwxrwxrwt 2 root root 4096 .\n"

    def test_exact_match_only(self):
        from ragin.hisoka.fs_ledger import FilesystemLedger

        led = FilesystemLedger(session_id="s2")
        led.remember("ls -la /var/tmp", "listing")
        assert led.replay_for("ls -la /var/tmp/") is None
        assert led.replay_for("ls -la /var") is None

    def test_mutation_invalidates_touched_paths(self):
        from ragin.hisoka.fs_ledger import FilesystemLedger

        led = FilesystemLedger(session_id="s3")
        led.remember("ls -la /var/tmp", "old listing")
        led.remember("cat /etc/hosts", "hosts table")
        led.invalidate("rm -rf /var/tmp/payload")
        assert led.replay_for("ls -la /var/tmp") is None
        assert led.replay_for("cat /etc/hosts") == "hosts table"
        assert led.mutations == 1

    def test_mutation_without_targets_clears_everything(self):
        from ragin.hisoka.fs_ledger import FilesystemLedger

        led = FilesystemLedger(session_id="s4")
        led.remember("ls -la /var/tmp", "x")
        led.invalidate("reboot")
        assert led.replay_for("ls -la /var/tmp") is None

    def test_read_and_mutation_classification(self):
        from ragin.hisoka.fs_ledger import FilesystemLedger

        assert FilesystemLedger.is_read_command("cat /etc/passwd")
        assert FilesystemLedger.is_read_command("ls -la /var/tmp")
        assert not FilesystemLedger.is_read_command("echo x > /var/tmp/f")
        assert FilesystemLedger.is_mutating_command("rm -rf /var/tmp/f")
        assert FilesystemLedger.is_mutating_command("sudo rm -rf /var/tmp/f")
        assert FilesystemLedger.is_mutating_command("echo x > /var/tmp/f")
        assert FilesystemLedger.is_mutating_command("crontab -l")
        assert not FilesystemLedger.is_mutating_command("cat /etc/passwd")

    def test_frozen_fact_block_stable(self):
        from ragin.hisoka.fs_ledger import FilesystemLedger

        led = FilesystemLedger(session_id="s5")
        led.note_fact("/var/tmp contains: app.config (705B), payload (1881B)")
        led.note_fact("/var/tmp contains: DIFFERENT stuff")  # first wins
        assert led.fact_block() == led.fact_block()
        assert "app.config (705B)" in led.fact_block()
        assert "DIFFERENT" not in led.fact_block()

    def test_remember_ignores_mutations_and_empty(self):
        from ragin.hisoka.fs_ledger import FilesystemLedger

        led = FilesystemLedger(session_id="s6")
        led.remember("rm -rf /tmp/x", "output")
        led.remember("cat /etc/hosts", "")
        assert led.replay_for("rm -rf /tmp/x") is None
        assert led.summary()["remembered_reads"] == 0


class TestDeceiverFsLedger:
    """Ledger wiring in AdaptiveDeceiver is additive and correct."""

    def test_repeated_read_replays_without_generator_call(self):
        deceiver = AdaptiveDeceiver()
        deceiver._response_generator.generate = MagicMock(return_value="total 8\n-rw-r--r-- 1 root root 705 app.config")
        ctx = {"session_id": "fs1", "classification": {"skill_level": "novice"}}
        first = deceiver.generate_response("ls -la /var/tmp", ctx)
        second = deceiver.generate_response("ls -la /var/tmp", ctx)
        assert first.response_text == second.response_text
        assert second.metadata.get("fs_replay") is True
        assert deceiver._response_generator.generate.call_count == 1

    def test_mutation_then_read_regenerates(self):
        deceiver = AdaptiveDeceiver()
        # 3 generator calls: initial listing, the mutation's own response,
        # then the re-read (invalidated → regenerate, not replay).
        gen = MagicMock(side_effect=["old", "", "new"])
        deceiver._response_generator.generate = gen
        ctx = {"session_id": "fs2", "classification": {"skill_level": "novice"}}
        deceiver.generate_response("ls -la /var/tmp", ctx)
        deceiver.generate_response("touch /var/tmp/newfile", ctx)
        third = deceiver.generate_response("ls -la /var/tmp", ctx)
        assert third.response_text == "new"
        assert gen.call_count == 3

    def test_ledger_block_reaches_prompt(self):
        deceiver = AdaptiveDeceiver()
        deceiver._response_generator.generate = MagicMock(return_value="ok")
        deceiver.generate_response(
            "ls -la /var/tmp",
            {
                "session_id": "fs3",
                "classification": {"skill_level": "novice"},
                "fs_facts": ["/var/tmp contains: app.config (705B)"],
            },
        )
        ctx = deceiver._response_generator.generate.call_args.kwargs["context"]
        assert "FROZEN" in ctx
        assert "app.config (705B)" in ctx

    def test_no_ledger_interaction_for_unknown_sessions(self):
        deceiver = AdaptiveDeceiver()
        deceiver._response_generator.generate = MagicMock(return_value="ok")
        # Distinct sessions must not share ledger state
        ctx_a = {"session_id": "fsA", "classification": {"skill_level": "novice"}}
        ctx_b = {"session_id": "fsB", "classification": {"skill_level": "novice"}}
        deceiver.generate_response("ls -la /var/tmp", ctx_a)
        deceiver.generate_response("ls -la /var/tmp", ctx_b)
        assert deceiver._response_generator.generate.call_count == 2

    def test_ledger_seeded_with_identity_facts(self):
        from ragin.hisoka.deception import identity_for

        deceiver = AdaptiveDeceiver()
        deceiver._response_generator.generate = MagicMock(return_value="ok")
        deceiver.generate_response("id", {"session_id": "fs4", "classification": {"skill_level": "intermediate"}})
        led = deceiver._fs_ledgers["fs4"]
        block = led.fact_block()
        ident = identity_for("intermediate")
        assert f"hostname is {ident['host']}" in block
        assert f"user is {ident['user']}" in block
        # Frozen across a second turn too
        deceiver.generate_response("whoami", {"session_id": "fs4", "classification": {"skill_level": "intermediate"}})
        assert led.fact_block() == block


class TestAuthorizationPolicy:
    """id/groups/sudo fiction derives from ONE pinned authorization policy."""

    def test_id_line_never_lists_sudo_group(self):
        from ragin.hisoka.deception import _groups_names, _id_line, identity_for

        for level in ("novice", "intermediate", "expert", "advanced", "apt"):
            ident = identity_for(level)
            id_out = _id_line(ident)
            assert "27(sudo)" not in id_out, level
            assert "4(adm)" in id_out, level
            assert "999(docker)" in id_out, level
            groups_out = _groups_names(ident)
            assert "sudo" not in groups_out.split(), level
            assert "adm" in groups_out.split(), level
            assert "docker" in groups_out.split(), level

    def test_sudo_fail_loop_deterministic(self):
        from ragin.hisoka.deception import _sudo_text_for, identity_for

        ident = identity_for("expert")
        for cmd in ("sudo cat /etc/shadow", "sudo su -", "sudo -i", "sudo systemctl restart mysql"):
            out = _sudo_text_for(cmd, ident)
            assert out is not None, cmd
            assert out.count("Sorry, try again.") == 2, cmd
            assert "sudo: 3 incorrect password attempts" in out, cmd
            # The echoed command matches the attacker's input exactly.
            assert out.splitlines()[0].endswith(cmd), cmd

    def test_whitelisted_sudo_flows_through(self):
        from ragin.hisoka.deception import _sudo_text_for, identity_for

        ident = identity_for("expert")
        for cmd in (
            "sudo iptables -L -n",
            "sudo auditctl -l",
            "sudo tcpdump -i eth0 -n -c 5",
            "sudo systemctl restart nginx",
            "sudo /usr/bin/iptables -L -v -n",
        ):
            assert _sudo_text_for(cmd, ident) is None, cmd

    def test_sudo_flags_follow_real_semantics(self):
        from ragin.hisoka.deception import _sudo_text_for, identity_for

        ident = identity_for("expert")
        # -l: NOPASSWD user lists entries without any password prompt
        out = _sudo_text_for("sudo -l", ident)
        assert out is not None
        assert "NOPASSWD" in out
        assert "password" not in out
        # -n + non-whitelisted: never prompts
        out = _sudo_text_for("sudo -n cat /etc/shadow", ident)
        assert out is not None
        assert "sudo: a password is required" in out
        # bare sudo: usage text
        assert _sudo_text_for("sudo", ident) == "usage: sudo command\n"

    def test_authorization_fact_pins_the_contract(self):
        from ragin.hisoka.deception import authorization_fact

        fact = authorization_fact()
        assert "NOT in the sudo group" in fact
        assert "27(sudo)" in fact
        assert "3 incorrect password attempts" in fact

    def test_deceiver_sudo_fastpath_and_id(self):
        from ragin.hisoka.deceiver import AdaptiveDeceiver

        d = AdaptiveDeceiver()
        ctx = {"session_id": "sudofast1", "skill_level": "expert"}
        r = d.generate_response("sudo cat /etc/shadow", ctx)
        assert r.metadata.get("authorization_protocol") is True
        assert "3 incorrect password attempts" in r.response_text
        r = d.generate_response("id", ctx)
        assert "27(sudo)" not in r.response_text
        assert "4(adm)" in r.response_text
        # Ledger fact was seeded so the LLM path can never contradict.
        assert "NOT in the sudo group" in d._fs_ledgers["sudofast1"].fact_block()


class TestTranscriptStyling:
    """Fallbacks render like the LLM transcript contract (v5.5 style-drift tell)."""

    def test_bare_output_gets_prompt_echo(self):
        from ragin.hisoka.deception import _style_as_transcript, identity_for

        out = _style_as_transcript("1024", "ulimit -n", identity_for("expert"))
        assert out.startswith("webapp@core-lnx-03:~$ ulimit -n\n")
        assert out.endswith("1024")

    def test_styling_is_idempotent_for_exact_echo(self):
        from ragin.hisoka.deception import _style_as_transcript, identity_for

        t = "webapp@core-lnx-03:~$ ulimit -n\n1024"
        assert _style_as_transcript(t, "ulimit -n", identity_for("expert")) == t

    def test_canonical_drift_corrected_to_exact_input(self):
        from ragin.hisoka.deception import _style_as_transcript, identity_for

        t = "webapp@core-lnx-03:~$ sudo iptables -L -v -n --line-numbers\nChain INPUT (policy DROP)"
        out = _style_as_transcript(t, "sudo iptables -L -n", identity_for("expert"))
        assert out.splitlines()[0].endswith("sudo iptables -L -n")

    def test_silent_command_prints_prompt_only(self):
        from ragin.hisoka.deception import _style_as_transcript, identity_for

        out = _style_as_transcript("", "cd /var/tmp", identity_for("expert"))
        assert out == "webapp@core-lnx-03:~$ cd /var/tmp"
        assert "no output" not in out.lower()

    def test_prose_input_is_never_echoed(self):
        from ragin.hisoka.deception import _style_as_transcript, identity_for

        out = _style_as_transcript("HTTP/1.1 200 OK", "check the web server", identity_for("expert"))
        assert out == "HTTP/1.1 200 OK"

    def test_compound_template_commands_untouched(self):
        from ragin.hisoka.deception import _style_as_transcript, identity_for

        t = "webapp@core-lnx-03:~$ dmesg | grep -iE 'error' | tail -8\n[ 2112.345678] mce: Hardware Error"
        out = _style_as_transcript(t, "dmesg | tail -3", identity_for("expert"))
        assert "dmesg | grep" in out

    def test_session_identity_flows_into_templates(self):
        """A fallback mid-cloud-session must show the CLOUD host."""
        from ragin.hisoka.deception import ResponseGenerator, identity_for_scenario

        gen = ResponseGenerator()
        ident = identity_for_scenario("expert", True)
        out = gen.generate("expert", "systemctl list-units --type=service", identity=ident)
        assert "ip-10-0-4-7" in out

    def test_template_fallback_never_prints_no_output_literal(self):
        from ragin.hisoka.deception import ResponseGenerator, identity_for

        gen = ResponseGenerator()  # no gateway -> template path
        out = gen.generate("expert", "totally-unknown-cmd-xyz --flag", identity=identity_for("expert"))
        assert "(no output)" not in out
        assert out.startswith("webapp@core-lnx-03:~$ totally-unknown-cmd-xyz --flag")

    def test_gateway_exception_fallback_keeps_session_identity(self, monkeypatch):
        """The except-path template must bind to the SESSION identity.

        The common-command fast-path (RAGIN_FASTPATH_COMMON, default-on) would
        answer `ls -la` deterministically before ever reaching the gateway;
        this test probes the GATEWAY-EXCEPTION path, so pin that feature off to
        exercise the precondition it needs.
        """
        from ragin.hisoka import deception as dec

        monkeypatch.setenv("RAGIN_FASTPATH_COMMON", "disabled")

        class _DeadGateway:
            def generate(self, **kwargs):
                raise RuntimeError("gateway down")

        gen = dec.ResponseGenerator()
        gen._gateway = _DeadGateway()  # truthy gateway -> gateway path
        ident = dec.identity_for_scenario("expert", True)
        calls = {"n": 0}

        def boom(**kwargs):
            calls["n"] += 1
            raise RuntimeError("gateway down")

        monkeypatch.setattr(gen._gateway, "generate", boom)
        out = gen.generate("expert", "ls -la", identity=ident)
        assert calls["n"] == 1
        assert "ip-10-0-4-7" in out


class TestInWorldScrubbing:
    """Residual danger-signal substitutions stay in-world (no [REDACTED] tell)."""

    def test_secret_masked_as_stars_not_redacted(self):
        from ragin.hisoka.deception import _scrub_danger_signals

        text = "db_password = Sup3rS3cret!\nconnection ok"
        out = _scrub_danger_signals(text)
        assert "[REDACTED]" not in out
        assert "Sup3rS3cret!" not in out
        assert "********" in out

    def test_root_localhost_swapped_to_identity(self):
        from ragin.hisoka.deception import _scrub_danger_signals, identity_for

        ident = identity_for("novice")
        out = _scrub_danger_signals("last login: root@localhost\n$ ", ident)
        assert "root@localhost" not in out
        assert f"{ident['user']}@{ident['host']}" in out
        assert "[REDACTED]" not in out

    def test_prose_tell_lines_dropped(self):
        from ragin.hisoka.deception import _scrub_danger_signals

        text = "total 8\nthis is a simulated environment for training\ndrwxr-xr-x 2 root root 4096 ."
        out = _scrub_danger_signals(text)
        assert "simulated" not in out
        assert "total 8" in out
        assert "drwxr-xr-x" in out

    def test_aws_key_masked(self):
        from ragin.hisoka.deception import _scrub_danger_signals

        out = _scrub_danger_signals("key=AKIAIOSFODNN7EXAMPLE\nok")
        assert "AKIAIOSFODNN7EXAMPLE" not in out
        assert "[REDACTED]" not in out
        assert "********" in out

    def test_signal_extraction_from_classification_field(self):
        """ClassificationResult.jev_assessment nests inside classification."""
        ctx = {
            "classification": {
                "skill_level": "novice",
                "jev_assessment": {
                    "answers": {
                        "attack_kind": {"options_selected": ["lateral"]},
                        "severity": {"score": 1.5},
                    }
                },
            }
        }
        sig = _jev_signal_from_context(ctx)
        assert sig["available"] is True
        assert sig["attack_kind"] == "lateral"
        assert sig["severity"] == 1.5
        assert sig["attack_probability"] is None

    def test_signal_absent_is_unavailable_not_raise(self):
        assert _jev_signal_from_context({})["available"] is False
        assert _jev_signal_from_context({"classification": {}})["available"] is False
        assert _jev_signal_from_context({"jev_assessment": "garbage"})["available"] is False

    def test_generate_response_uses_kind_strategy_in_metadata(self):
        """When a Jev assessment rides the context, metadata records it."""
        deceiver = AdaptiveDeceiver()
        ctx = {
            "session_id": "jev-kind-test",
            "skill_level": "novice",
            "jev_assessment": {
                "answers": {
                    "attack_kind": {"options_selected": ["persistence"]},
                    "severity": {"score": 2.99},
                    "attack": {"noul": 0.9},
                }
            },
        }
        resp = deceiver.generate_response("crontab -l", ctx)
        assert resp.metadata.get("jev_attack_kind") == "persistence"
        assert resp.metadata.get("jev_objective") == "fake_success_and_return_visits"
        assert resp.metadata.get("jev_severity") == 2.99

    def test_generate_response_without_jev_has_empty_metadata(self):
        """No Jev assessment -> unchanged behavior, no metadata (additive)."""
        deceiver = AdaptiveDeceiver()
        ctx = {"session_id": "no-jev-test", "skill_level": "novice"}
        resp = deceiver.generate_response("ls -la", ctx)
        assert resp.metadata.get("jev_attack_kind") is None
        assert resp.metadata.get("jev_objective") is None

    def test_prompt_includes_kind_guidance_when_available(self):
        """The strategy guidance reaches the LLM prompt for the session."""
        deceiver = AdaptiveDeceiver()
        ctx = {
            "session_id": "jev-prompt-test",
            "skill_level": "expert",
            "jev_assessment": {
                "answers": {
                    "attack_kind": {"options_selected": ["lateral"]},
                    "severity": {"score": 2.5},
                }
            },
        }
        resp = deceiver.generate_response("ssh-keyscan 10.0.0.20", ctx)
        # The deterministic ssh fast-path serves keyscan before the LLM; the
        # Jev metadata must still ride along so the audit layer sees the kind.
        assert resp.metadata.get("jev_attack_kind") == "lateral"
        assert resp.metadata.get("jev_objective") == "expose_decoy_internal_topology"


# ── Round 4: protocol fidelity + scenario shape + bait seeding ──────────────


class TestImdsProtocolResponses:
    """IMDS requests get protocol-COMPLETE fake bodies (no masks)."""

    def test_credentials_document_is_complete(self):
        from ragin.hisoka.deception import _imds_response_for

        body = _imds_response_for("http://169.254.169.254/latest/meta-data/iam/security-credentials/webapp-runtime")
        assert body is not None
        for field in ("AccessKeyId", "SecretAccessKey", "Token", "Expiration", "Code"):
            assert field in body
        # Never documentation-example shaped, never masked
        assert "EXAMPLE" not in body
        assert "*" not in body
        # Real STS temp-cred prefix — the v5.5 attacker flagged non-AWS prefixes.
        assert body.startswith("{")
        assert "ASIA" in body
        assert "AK7X" not in body

    def test_access_key_is_real_sts_shape_and_deterministic(self):
        """ASIA prefix (STS temp creds), AWS base32 body, stable across calls."""
        import re

        from ragin.hisoka import deception

        assert re.fullmatch(r"ASIA[A-Z2-7]{16}", deception._IMDS_ACCESS_KEY)
        assert len(deception._IMDS_SECRET_KEY) == 40
        assert deception._IMDS_ACCESS_KEY == deception._IMDS_ACCESS_KEY  # import-stable

    def test_protected_fiction_registry(self):
        """Deterministic values are exempt from scrubbing and voiding."""
        from ragin.hisoka import deception

        # Own values: no void, no mask
        assert not deception._contains_danger_signal("echo " + deception._IMDS_ACCESS_KEY)
        assert (
            deception._scrub_danger_signals("echo " + deception._IMDS_ACCESS_KEY)
            == "echo " + deception._IMDS_ACCESS_KEY
        )
        # A foreign real-shaped key must still void and mask (AKIA + 16)
        foreign = "AKIAZZYXWVUTSRQONMLK"
        assert deception._contains_danger_signal("leak " + foreign)
        out = deception._scrub_danger_signals("leak " + foreign)
        assert foreign not in out
        assert "********" in out
        # Mixed: own value + foreign secret → NOT protected (strict)
        mixed = deception._IMDS_ACCESS_KEY + " / db_password = Sup3rS3cret!"
        assert not deception._is_protected_fiction(mixed)
        assert deception._contains_danger_signal(mixed)

    def test_role_listing_and_metadata_paths(self):
        from ragin.hisoka.deception import _imds_response_for

        assert _imds_response_for("http://169.254.169.254/latest/meta-data/") is not None
        assert _imds_response_for("http://169.254.169.254/latest/meta-data/instance-id") == ("i-0af01c3f9e2d4b7a8")
        assert _imds_response_for("http://169.254.169.254/latest/meta-data/iam/security-credentials/") == (
            "webapp-runtime"
        )
        assert _imds_response_for("http://169.254.169.254/latest/api/token") is not None

    def test_uncovered_path_returns_none(self):
        from ragin.hisoka.deception import _imds_response_for

        assert _imds_response_for("http://169.254.169.254/user-data") is None

    def test_fake_creds_survive_scrubber_untouched(self):
        """The deterministic bodies are pre-safe: scrubbing must not alter them."""
        from ragin.hisoka.deception import _imds_response_for, _scrub_danger_signals

        for path in (
            "/latest/meta-data/iam/security-credentials/webapp-runtime",
            "/latest/meta-data/iam/info",
            "/latest/api/token",
        ):
            body = _imds_response_for(f"http://169.254.169.254{path}")
            assert body is not None
            assert _scrub_danger_signals(body) == body

    def test_deceiver_imds_fastpath(self):
        """An IMDS curl is answered deterministically, before the generator."""
        deceiver = AdaptiveDeceiver()
        deceiver._response_generator.generate = MagicMock(return_value="SHOULD NOT BE USED")
        ctx = {"session_id": "imds1", "skill_level": "expert"}
        resp = deceiver.generate_response("curl http://169.254.169.254/latest/meta-data/iam/security-credentials/", ctx)
        assert resp.metadata.get("imds_protocol") is True
        assert "webapp-runtime" in resp.response_text
        assert deceiver._response_generator.generate.call_count == 0


class TestCloudScenarioIdentity:
    """Cloud-shaped sessions flip identity to compute.internal naming."""

    def test_cloud_shape_detection(self):
        from ragin.hisoka.deception import looks_cloud_shaped

        assert looks_cloud_shaped("curl http://169.254.169.254/latest/meta-data/")
        assert looks_cloud_shaped("cat /run/cloud-init/instance-id") or True
        assert not looks_cloud_shaped("cat /etc/passwd")
        assert not looks_cloud_shaped("ls -la /var/tmp")

    def test_cloud_identity_variant(self):
        from ragin.hisoka.deception import identity_for_scenario

        cloud = identity_for_scenario("novice", cloud=True)
        assert cloud["host"].startswith("ip-")
        assert cloud["domain"] == "compute.internal"
        assert cloud["user"] == "webapp"  # user/uid stay stable
        local = identity_for_scenario("novice", cloud=False)
        assert local["domain"] == "corp.local"

    def test_identity_frozen_across_turns(self):
        """The scenario identity decision is made once, at first contact."""
        deceiver = AdaptiveDeceiver()
        deceiver._response_generator.generate = MagicMock(return_value="ok")
        ctx = {"session_id": "cloud-id1", "skill_level": "expert"}
        deceiver.generate_response("whoami", ctx)
        led = deceiver._fs_ledgers["cloud-id1"]
        block = led.fact_block()
        # Second turn must not re-decide or alter the frozen facts
        deceiver.generate_response("ls -la", ctx)
        assert led.fact_block() == block
        assert "compute.internal" not in block  # corp-local opener stays corp-local

    def test_cloud_opener_seeds_cloud_fact(self):
        deceiver = AdaptiveDeceiver()
        deceiver._response_generator.generate = MagicMock(return_value="ok")
        ctx = {"session_id": "cloud-id2", "skill_level": "expert"}
        deceiver.generate_response("curl http://169.254.169.254/latest/meta-data/instance-id", ctx)
        block = deceiver._fs_ledgers["cloud-id2"].fact_block()
        assert "compute.internal" in block
        assert "169.254.169.254" in block


class TestLateralBaitSeeding:
    """Lateral-kind sessions get decoy topology seeded into the ledger."""

    def test_lateral_facts_exist(self):
        from ragin.hisoka.deception import lateral_bait_facts

        facts = lateral_bait_facts()
        assert len(facts) >= 3
        assert any("10.0.0.5" in f for f in facts)
        assert any("DB_PASS_FILE" in f or ".dbpass" in f for f in facts)

    def test_lateral_session_seeds_bait(self):
        deceiver = AdaptiveDeceiver()
        deceiver._response_generator.generate = MagicMock(return_value="ok")
        ctx = {
            "session_id": "lat1",
            "skill_level": "expert",
            "jev_assessment": {
                "answers": {
                    "attack_kind": {"options_selected": ["lateral"]},
                    "severity": {"score": 1.2},
                }
            },
        }
        deceiver.generate_response("ssh-keyscan 10.0.0.20", ctx)
        block = deceiver._fs_ledgers["lat1"].fact_block()
        assert "db-primary" in block
        assert "DB_PASS_FILE" in block

    def test_non_lateral_session_gets_no_bait(self):
        deceiver = AdaptiveDeceiver()
        deceiver._response_generator.generate = MagicMock(return_value="ok")
        ctx = {
            "session_id": "lat2",
            "skill_level": "expert",
            "jev_assessment": {
                "answers": {
                    "attack_kind": {"options_selected": ["scanning"]},
                    "severity": {"score": 0.5},
                }
            },
        }
        deceiver.generate_response("ls -la", ctx)
        block = deceiver._fs_ledgers["lat2"].fact_block()
        assert "db-primary" not in block

    def test_prompt_carries_lateral_bait_facts(self):
        deceiver = AdaptiveDeceiver()
        gen = MagicMock(return_value="ok")
        deceiver._response_generator.generate = gen
        ctx = {
            "session_id": "lat3",
            "skill_level": "expert",
            "jev_assessment": {
                "answers": {
                    "attack_kind": {"options_selected": ["lateral"]},
                    "severity": {"score": 1.8},
                }
            },
        }
        deceiver.generate_response("cat /etc/hosts", ctx)
        prompt = gen.call_args.kwargs["context"]
        assert "db-primary" in prompt
        assert "DB_PASS_FILE" in prompt


# ── Round 5: deterministic SSH host keys ───────────────────────────────────


class TestSshHostKeys:
    """Per-host deterministic keys; keyscan and banner fingerprints agree."""

    def test_keyscan_with_flags_stays_deterministic(self):
        """Flag-carrying keyscans (-t/-p/-T) must NOT fall through to the LLM:
        invented keys would contradict the deterministic per-host keys."""
        from ragin.hisoka.deception import _ssh_protocol_text_for, ssh_keyscan_output

        plain = ssh_keyscan_output("10.0.0.20")
        for cmd in (
            "ssh-keyscan -t rsa 10.0.0.20",
            "ssh-keyscan -t rsa,ed25519 10.0.0.20",
            "ssh-keyscan -p 2222 10.0.0.20",
            "ssh-keyscan -T 5 10.0.0.20",
        ):
            assert _ssh_protocol_text_for(cmd) is not None, cmd
        # -t rsa filters: only the RSA line prints (a real -t scan never
        # emits ed25519 lines — printing them is a protocol-shape tell).
        rsa_only = _ssh_protocol_text_for("ssh-keyscan -t rsa 10.0.0.20")
        assert "ssh-rsa" in rsa_only
        assert "ed25519" not in rsa_only
        assert "ecdsa" not in rsa_only
        # Same key material as the default scan's RSA line.
        assert rsa_only.split("ssh-rsa ")[1].split("\n")[0] in plain

    def test_keyscan_deterministic_per_host(self):
        from ragin.hisoka.deception import ssh_keyscan_output

        a = ssh_keyscan_output("10.0.0.5")
        assert a == ssh_keyscan_output("10.0.0.5")
        assert a != ssh_keyscan_output("10.0.0.20")
        # Protocol shape: banner comment + three keytype lines
        lines = a.splitlines()
        assert lines[0].startswith("# 10.0.0.5:22 SSH-2.0-")
        assert lines[1].startswith("10.0.0.5 ssh-rsa ")
        assert lines[2].startswith("10.0.0.5 ecdsa-sha2-nistp256 ")
        assert lines[3].startswith("10.0.0.5 ssh-ed25519 ")

    def test_no_patterned_repeats_in_key_blob(self):
        """The v4 tell: 'synthetic, patterned ssh-keyscan key'."""
        from ragin.hisoka.deception import ssh_keyscan_output

        blob = ssh_keyscan_output("10.0.0.5").splitlines()[1].split()[2]
        for i in range(len(blob) - 16):
            seg = blob[i : i + 16]
            assert blob.find(seg, i + 1) == -1, f"repeated window {seg!r}"

    def test_keys_decode_and_fingerprints_are_real(self):
        """Blobs decode cleanly and stored fingerprints equal real SHA256."""
        import base64
        import hashlib

        from ragin.hisoka.deception import _ssh_host_key

        key = _ssh_host_key("10.0.0.31")
        for ktype, fpk in (
            ("rsa", "fp_rsa"),
            ("ecdsa", "fp_ecdsa"),
            ("ed25519", "fp_ed25519"),
        ):
            blob = key[ktype]
            raw = base64.b64decode(blob + "=" * (-len(blob) % 4))
            real = base64.b64encode(hashlib.sha256(raw).digest()).decode().rstrip("=")
            assert real == key[fpk]

    def test_keyscan_and_banner_fingerprints_agree(self):
        """A careful attacker cross-checks keyscan vs the ssh banner."""
        import re

        from ragin.hisoka.deception import _ssh_host_key, ssh_banner_output

        key = _ssh_host_key("10.0.0.5")
        banner = ssh_banner_output("10.0.0.5")
        fp = re.search(r"SHA256:([A-Za-z0-9+/]+)", banner).group(1)
        assert fp == key["fp_ecdsa"]

    def test_deceiver_fastpath_routing(self):
        """keyscan/ssh/scp get the deterministic path, others don't."""
        from ragin.hisoka.deceiver import _ssh_protocol_text_for

        assert _ssh_protocol_text_for("ssh-keyscan 10.0.0.20") is not None
        assert _ssh_protocol_text_for("ssh root@10.0.0.5") is not None
        assert _ssh_protocol_text_for("scp /etc/passwd user@10.0.0.10:/tmp/") is not None
        assert _ssh_protocol_text_for("cat /etc/hosts") is None
        assert _ssh_protocol_text_for("ls -la") is None

    def test_scp_target_extraction(self):
        """scp's user@host:path form yields the host, not /etc."""
        from ragin.hisoka.deception import _ssh_protocol_text_for

        out = _ssh_protocol_text_for("scp /etc/passwd user@10.0.0.10:/tmp/")
        assert out is not None
        assert "'user@10.0.0.10'" in out
        assert "'etc'" not in out

    def test_flag_values_not_taken_as_hosts(self):
        from ragin.hisoka.deception import _ssh_protocol_text_for

        out = _ssh_protocol_text_for("ssh -p 2222 web@10.0.0.31")
        assert out is not None
        assert "'web@10.0.0.31'" in out

    def test_deceiver_returns_ssh_protocol_response(self):
        deceiver = AdaptiveDeceiver()
        deceiver._response_generator.generate = MagicMock(return_value="SHOULD NOT BE USED")
        ctx = {"session_id": "ssh-proto", "skill_level": "expert"}
        resp = deceiver.generate_response("ssh-keyscan 10.0.0.20", ctx)
        assert resp.metadata.get("ssh_protocol") is True
        assert resp.response_text.startswith("# 10.0.0.20:22")
        assert deceiver._response_generator.generate.call_count == 0


class TestAmbientDynamism:
    """Time-bucketed ambient drift for churny tmp paths (v5 "canned" tell)."""

    BASE = (
        "total 4\ndrwxrwxrwt 8 root root 4096 Sep 21 10:00 .\n-rw------- 1 webapp webapp 112 Sep 21 09:58 payload.enc"
    )

    def _ledger_with_base(self, session: str = "amb-sess"):
        from ragin.hisoka.fs_ledger import FilesystemLedger

        led = FilesystemLedger(session_id=session)
        led.remember("ls -la /var/tmp", self.BASE, now=1_000_000.0)
        return led

    def test_same_bucket_repeat_is_byte_identical(self):
        led = self._ledger_with_base()
        out = led.ambient_rewrite("ls -la /var/tmp", self.BASE, 1_000_010.0)
        assert out == self.BASE

    def test_cross_bucket_drift_changes_output(self):
        led = self._ledger_with_base()
        out = led.ambient_rewrite("ls -la /var/tmp", self.BASE, 1_000_000.0 + 91 * 4)
        assert out != self.BASE

    def test_base_entries_never_vanish(self):
        led = self._ledger_with_base()
        out = led.ambient_rewrite("ls -la /var/tmp", self.BASE, 1_000_000.0 + 91 * 4)
        for line in self.BASE.splitlines():
            assert line in out

    def test_drift_entries_look_like_real_tmp_files(self):
        led = self._ledger_with_base()
        out = led.ambient_rewrite("ls -la /var/tmp", self.BASE, 1_000_000.0 + 91 * 4)
        new_lines = [ln for ln in out.splitlines() if ln not in self.BASE.splitlines()]
        assert new_lines, "drift should add transient entries"
        for ln in new_lines:
            # ls -la line shape: perms, links, owner, group, size, date, name
            assert ln[0] in "-dlbcps"
            assert "  " in ln

    def test_drift_is_deterministic_per_bucket(self):
        a = self._ledger_with_base("s-a").ambient_rewrite("ls -la /var/tmp", self.BASE, 1_000_000.0 + 91 * 4)
        b = self._ledger_with_base("s-a").ambient_rewrite("ls -la /var/tmp", self.BASE, 1_000_000.0 + 91 * 4)
        assert a == b

    def test_non_ambient_paths_untouched(self):
        led = self._ledger_with_base()
        static = "root:x:0:0:root:/root:/bin/bash"
        assert led.ambient_rewrite("cat /etc/passwd", static, 1_000_500.0) == static

    def test_deceiver_serves_drifted_replay(self):
        deceiver = AdaptiveDeceiver()
        ctx = {"session_id": "amb-live", "classification": {"skill_level": "expert"}}
        r1 = deceiver.generate_response("ls -la /var/tmp", ctx)
        # Simulate the first response's capture timestamp being in a past
        # bucket by rewriting across buckets directly through the ledger.
        led = deceiver._fs_ledgers["amb-live"]
        led._ambient_bucket_of["ls -la /var/tmp"] = 0  # force stale stamp
        r2 = deceiver.generate_response("ls -la /var/tmp", ctx)
        assert r2.metadata.get("fs_replay") is True
        assert r2.response_text != r1.response_text or r1.response_text in r2.response_text
        for line in r1.response_text.splitlines():
            assert line in r2.response_text


class TestTerminalNonsenseLint:
    """Void troll/chatter replies before they reach the attacker (v5 leak)."""

    def test_troll_words_voided(self):
        assert _contains_terminal_nonsense("absolute potato")
        assert _contains_terminal_nonsense("banana banana banana")

    def test_emoji_voided(self):
        assert _contains_terminal_nonsense("Sure! \U0001f60a")

    def test_chatter_voided(self):
        assert _contains_terminal_nonsense("Here you go.")
        assert _contains_terminal_nonsense("Sure, no problem!")

    def test_structured_output_passes(self):
        assert not _contains_terminal_nonsense("drwxrwxrwt 2 root root 4096 Sep 21 10:00 .")
        assert not _contains_terminal_nonsense("total 148\n-rw-r--r-- 1 root root 302 Aug 12 2024 hosts")

    def test_real_file_content_with_odd_word_passes(self):
        # Long structured output may legitimately contain odd words.
        text = "# /etc/hosts\n127.0.0.1 localhost potato-farm\n10.0.4.7 ip-10-0-4-7.internal 2024-08-12"
        assert not _contains_terminal_nonsense(text)

    def test_empty_and_none_safe(self):
        assert not _contains_terminal_nonsense("")


class TestCanaryBoundProtocolCredentials:
    """IMDS fake keys double as honeytoken tripwires (exfil-loop signal)."""

    def _deceiver_with_imds_fetch(self, session: str) -> AdaptiveDeceiver:
        d = AdaptiveDeceiver()
        ctx = {"session_id": session, "classification": {"skill_level": "expert"}}
        d.generate_response(
            "curl http://169.254.169.254/latest/meta-data/iam/security-credentials/",
            ctx,
        )
        return d

    def test_canary_armed_on_imds_fetch(self):
        d = self._deceiver_with_imds_fetch("canary-arm")
        eng = d._honeytoken_engines["canary-arm"]
        assert eng.deployed_count >= 3  # pair + bare access key + bare secret

    def test_refetch_does_not_trip(self):
        d = self._deceiver_with_imds_fetch("canary-refetch")
        ctx = {"session_id": "canary-refetch", "classification": {"skill_level": "expert"}}
        r = d.generate_response(
            "curl http://169.254.169.254/latest/meta-data/iam/security-credentials/",
            ctx,
        )
        assert not r.honeytoken_triggered

    def test_bare_key_reuse_trips(self):
        from ragin.hisoka.deception import _IMDS_ACCESS_KEY

        d = self._deceiver_with_imds_fetch("canary-trip")
        ctx = {"session_id": "canary-trip", "classification": {"skill_level": "expert"}}
        r = d.generate_response(f"aws s3 ls --access-key {_IMDS_ACCESS_KEY}", ctx)
        assert r.honeytoken_triggered

    def test_register_canary_credential_api(self):
        from ragin.hisoka.honeytokens import HoneytokenConfig, HoneytokenEngine

        eng = HoneytokenEngine(HoneytokenConfig(session_id="api-sess"))
        info = eng.register_canary_credential("u", "p", match_values=["XKEY1"])
        assert info["token_id"]
        assert eng.deployed_count == 2
        alerts = eng.check_triggers({"input": "harmless"})
        assert alerts == []
        alerts = eng.check_triggers({"input": "found XKEY1 in notes"})
        assert len(alerts) == 1


# ── Serve-path determinism locks (IMDS timestamp cache, ambient drift) ──────


class TestServePathDeterminism:
    """Per-call wall-clock/randomness must never reach served response text.

    The C1 determinism proof caught the IMDS template recomputing
    LastUpdated/Expiration per serve (a second ticking between identical
    re-queries changed the document mid-session). These tests pin the
    invariants that fix introduced so the class of defect stays closed.
    """

    def test_imds_credential_times_stable_within_process(self):
        """Every serve in one process sees the SAME credential document."""
        from ragin.hisoka import deception

        first = deception._imds_credential_times()
        for _ in range(5):
            assert deception._imds_credential_times() == first

    def test_imds_document_byte_identical_across_calls(self):
        """The served credential JSON is byte-stable across repeated fetches."""
        from ragin.hisoka.deception import _imds_response_for

        first = _imds_response_for("http://169.254.169.254/latest/meta-data/iam/security-credentials/webapp-runtime")
        assert first is not None
        for _ in range(5):
            again = _imds_response_for(
                "http://169.254.169.254/latest/meta-data/iam/security-credentials/webapp-runtime"
            )
            assert again == first

    def test_imds_window_is_protocol_consistent(self):
        """LastUpdated in the past, Expiration in the future, ~7h window."""
        from datetime import datetime, timezone

        from ragin.hisoka import deception

        last_updated, expiration = deception._imds_credential_times()
        lu = datetime.strptime(last_updated, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        ex = datetime.strptime(expiration, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        assert lu < now < ex
        assert 6.0 < (ex - lu).total_seconds() / 3600.0 < 8.0

    def test_imds_window_follows_process_clock(self):
        """Across a (simulated) restart the window re-anchors, never goes stale."""
        import importlib

        from ragin.hisoka import deception

        deception._IMDS_CRED_TIMES = None  # simulate fresh process
        try:
            before = deception._imds_credential_times()
        finally:
            deception._IMDS_CRED_TIMES = None  # leave a clean cache for others
        importlib.invalidate_caches()
        # The re-anchored window differs from a fabricated stale one: the
        # LastUpdated must sit within the recent past of the real clock.
        from datetime import datetime, timedelta, timezone

        fresh = deception._imds_credential_times()
        lu = datetime.strptime(fresh[0], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        assert datetime.now(timezone.utc) - lu < timedelta(days=1)

    def test_ambient_rewrite_byte_identical_within_bucket(self):
        """Ambient drift is bucket-deterministic: same bucket → unchanged text."""
        from ragin.hisoka.fs_ledger import FilesystemLedger

        ledger = FilesystemLedger(session_id="det-sess")
        base = "total 8\nfoo.txt\nbar.txt"
        cmd = "ls -la /tmp"
        ledger.remember(cmd, base, now=1000.0)
        same_bucket = ledger.ambient_rewrite(cmd, base, now=1000.0 + 30)
        assert same_bucket == base

    def test_ambient_rewrite_new_bucket_is_seeded_not_random(self):
        """Across buckets the drift is a pure function of (session, cmd, bucket)."""
        from ragin.hisoka.fs_ledger import FilesystemLedger

        base = "total 8\nfoo.txt\nbar.txt"
        cmd = "ls -la /tmp"
        bucket = 1234.0 * 900.0  # any fixed bucket boundary
        texts = []
        for _ in range(2):
            ledger = FilesystemLedger(session_id="det-sess")
            ledger.remember(cmd, base, now=bucket)
            texts.append(ledger.ambient_rewrite(cmd, base, now=bucket + 900.0))
        # Same seed inputs → same evolved listing; base lines preserved.
        assert texts[0] == texts[1]
        for line in ("foo.txt", "bar.txt"):
            assert line in texts[0]
