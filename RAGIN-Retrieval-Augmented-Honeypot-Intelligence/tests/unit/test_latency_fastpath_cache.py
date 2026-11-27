"""Phase 4 latency features: common-command fast-path + session-scoped LLM cache.

MASTER_PLAN_2026-10-24 Phase 4: "deterministic fast-paths for common commands +
LLM response cache (44 s/command kills field sessions)". Two features, one
provenance contract under test:

* a fast-path serve is deterministic pinned-fiction bytes and must NEVER be
  counted as an LLM draft (serve_path TEMPLATE_FALLBACK_VERIFIED, never
  GENERATED_VERIFIED — the 2026-09-28 audit class);
* a cache hit must declare that NO provider request happened this turn and
  must never cross a session boundary (byte-identical answers to different
  source IPs are a cache-fingerprinting tell);
* both features are forced off under RAGIN_REQUIRE_MODEL_EXPOSURE, which
  exists to measure a model call per turn.
"""

from __future__ import annotations

import time
from typing import Any
from unittest.mock import MagicMock

import pytest

from ragin.cycle.graph import DeceptionGraph
from ragin.hisoka.deception import (
    LatencyFeatureConfigError,
    ResponseGenerator,
    _common_command_input,
    fastpath_common_enabled,
    identity_for,
    llm_cache_enabled,
    provider_path_enabled,
)
from ragin.hisoka.deceiver import AdaptiveDeceiver, _LLMResponseCache, _model_draft_generation

# Structured, terminal-shaped, danger-free draft: long enough (and path-bearing
# enough) to clear _contains_terminal_nonsense, so a test asserting the call
# count is not silently doubled by a strict retry.
_SAFE_DRAFT = (
    "drwxr-xr-x 2 deploy deploy 4096 Jun 13 08:42 .\n"
    "drwxr-xr-x 5 root   root   4096 Mar 15 09:23 ..\n"
    "-rw-r--r-- 1 deploy deploy  220 Jan 10 14:00 .bashrc\n"
    "drwxr-xr-x 2 deploy deploy 4096 Jun 13 08:42 /opt/app/cache\n"
)


class _FakeGateway:
    """Minimal GatewayClient stand-in: counts calls, returns a fixed draft."""

    def __init__(self, draft: str = _SAFE_DRAFT) -> None:
        self.draft = draft
        self.calls: list[dict[str, Any]] = []

    def generate(self, **kwargs: Any) -> tuple[str, dict[str, int]]:
        self.calls.append(dict(kwargs))
        observation = kwargs.get("observation")
        if isinstance(observation, dict):
            observation.update({"invocation_succeeded": True, "model_response_received": True})
        return self.draft, {"prompt_tokens": 10, "completion_tokens": 20}


def _gen() -> tuple[ResponseGenerator, _FakeGateway]:
    gen = ResponseGenerator(gateway_url=None)
    fake = _FakeGateway()
    gen._gateway = fake
    return gen, fake


def _deceiver_with_gateway() -> tuple[AdaptiveDeceiver, _FakeGateway]:
    dec = AdaptiveDeceiver()
    fake = _FakeGateway()
    dec._response_generator._gateway = fake
    return dec, fake


def _ctx(session_id: str, **extra: Any) -> dict[str, Any]:
    ctx: dict[str, Any] = {
        "session_id": session_id,
        "classification": {"skill_level": "novice"},
    }
    ctx.update(extra)
    return ctx


# ── eligibility helpers ─────────────────────────────────────────────────────


def test_command_shape_gate_matches_bin_heads_only():
    assert _common_command_input("whoami") is True
    assert _common_command_input("  /bin/ls -la /var/www") is True
    assert _common_command_input("cat /etc/os-release") is True
    assert _common_command_input("show me the firewall rules") is False
    assert _common_command_input("") is False
    assert _common_command_input("exploit.py --payload x") is False


def test_unknown_toggle_values_refuse_rather_than_guess():
    with pytest.raises(LatencyFeatureConfigError):
        fastpath_common_enabled(environ={"RAGIN_FASTPATH_COMMON": "yes"})
    with pytest.raises(LatencyFeatureConfigError):
        llm_cache_enabled(environ={"RAGIN_LLM_CACHE": "1"})


def test_toggles_default_enabled_and_honor_disabled():
    assert fastpath_common_enabled(environ={}) is True
    assert llm_cache_enabled(environ={}) is True
    assert fastpath_common_enabled(environ={"RAGIN_FASTPATH_COMMON": "disabled"}) is False
    assert llm_cache_enabled(environ={"RAGIN_LLM_CACHE": "disabled"}) is False


# ── common-command fast-path ────────────────────────────────────────────────


def test_fastpath_serves_common_command_with_zero_gateway_calls():
    """`uname -a` is pinned fiction: the ~44 s gateway round-trip must be
    skipped entirely and the turn labelled as a deterministic fast-path."""
    gen, fake = _gen()
    meta: dict[str, Any] = {}
    text = gen.generate(skill_level="expert", user_input="uname -a", meta=meta)

    assert fake.calls == []
    assert meta["common_command_fastpath"] is True
    assert meta["template_fallback_reason"] == "fastpath_common_command"
    ident = identity_for("expert")
    assert ident["host"] in text and "GNU/Linux" in text
    # Provenance: never a model draft, never cacheable as one.
    assert _model_draft_generation(meta) is False


def test_fastpath_covers_exact_common_commands_but_not_novel_input():
    gen, fake = _gen()
    meta: dict[str, Any] = {}
    gen.generate(skill_level="novice", user_input="ls -la", meta=meta)
    assert fake.calls == [] and meta.get("common_command_fastpath") is True

    # A bin head whose command has NO transcript (novel content) still buys
    # the model call: the fast-path is template-hit-gated, not bin-gated.
    meta2: dict[str, Any] = {}
    gen.generate(skill_level="novice", user_input="tail -n 40 /opt/app/release/notes.txt", meta=meta2)
    assert len(fake.calls) == 1
    assert meta2.get("common_command_fastpath") is None

    # Prose never matches a binary head, so it keeps its LLM adaptation.
    gen.generate(skill_level="novice", user_input="show me the firewall rules", meta={})
    assert len(fake.calls) == 2


def test_fastpath_can_be_disabled(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("RAGIN_FASTPATH_COMMON", "disabled")
    gen, fake = _gen()
    gen.generate(skill_level="expert", user_input="whoami", meta={})
    assert len(fake.calls) == 1


def test_fastpath_forced_off_under_model_exposure(monkeypatch: pytest.MonkeyPatch):
    """Model-exposure mode measures a model call per turn: no deterministic
    substitution may happen there, even for identity commands."""
    monkeypatch.setenv("RAGIN_REQUIRE_MODEL_EXPOSURE", "1")
    gen = ResponseGenerator(gateway_url=None)
    fake = _FakeGateway()
    gen._gateway = fake
    gen.generate(skill_level="expert", user_input="whoami", meta={})
    assert len(fake.calls) == 1


def test_fastpath_turn_is_never_cached_or_mislabelled():
    """A fast-path response must not enter the model-draft cache, and must
    carry no llm_cache claim."""
    dec, fake = _deceiver_with_gateway()
    resp = dec.generate_response("hostname", _ctx("fastpath-cache"))
    assert fake.calls == []
    assert resp.metadata["common_command_fastpath"] is True
    assert resp.metadata.get("llm_cache") is None
    assert len(dec._llm_response_cache) == 0


def test_generate_node_labels_fastpath_as_template_fallback():
    """serve_path provenance: a deliberate deterministic serve is a verified
    template, never a GENERATED_VERIFIED LLM draft."""
    deceiver = MagicMock()
    deceiver.generate_response.return_value = {
        "response_text": "webapp",
        "persona_used": "novice",
        "metadata": {"common_command_fastpath": True, "template_fallback_reason": "fastpath_common_command"},
    }
    graph = DeceptionGraph(classifier=_classifier(), analyzer=_analyzer(), deceiver=deceiver)
    state = {
        "session_id": "s1",
        "attacker_input": "whoami",
        "context": {},
        "classification": {"skill_level": "novice"},
    }
    out = graph.generate_node(state)["deception_response"]
    assert out["serve_path"] == "TEMPLATE_FALLBACK_VERIFIED"


# ── session-scoped LLM response cache ───────────────────────────────────────


def test_cache_second_identical_turn_skips_gateway():
    dec, fake = _deceiver_with_gateway()
    first = dec.generate_response("mkdir -p /opt/app/cache", _ctx("cache-sess"))
    second = dec.generate_response("mkdir -p /opt/app/cache", _ctx("cache-sess"))

    assert len(fake.calls) == 1  # the second 44 s round-trip never happened
    assert second.response_text == first.response_text
    assert second.metadata["llm_cache"] == "hit"
    # Legacy mode carries no generator source label (contract fields appear
    # only under a generation contract) — the key exists and holds the
    # origin's label whenever one was emitted; this turn's label is the hit.
    assert "llm_cache_origin_generation_source" in second.metadata
    # Honest per-turn accounting: no provider request THIS turn, no usage.
    assert second.metadata["model_invocation_attempted"] is False
    assert second.metadata["model_invocation_succeeded"] is False
    assert second.metadata["usage_scope"] == "NO_PROVIDER_REQUEST"
    assert second.metadata["final_generation_source"] == "LLM_CACHE_HIT"


def test_cache_never_crosses_sessions():
    """Byte-identical answers to different sessions (source IPs) are the
    cache-fingerprinting tell the legacy server disabled caching for."""
    dec, fake = _deceiver_with_gateway()
    dec.generate_response("mkdir -p /opt/app/cache", _ctx("session-a"))
    other = dec.generate_response("mkdir -p /opt/app/cache", _ctx("session-b"))
    assert len(fake.calls) == 2
    assert other.metadata.get("llm_cache") is None


def test_cache_misses_when_prompt_context_changes():
    """The key hashes the assembled prompt: a changed fiction block (or a
    verification-retry feedback turn) must never be served a stale draft."""
    dec, fake = _deceiver_with_gateway()
    dec.generate_response("mkdir -p /opt/app/cache", _ctx("ctx-sess"))
    dec.generate_response(
        "mkdir -p /opt/app/cache",
        _ctx("ctx-sess", fiction_block="Session consistency: host db-int-04"),
    )
    assert len(fake.calls) == 2


def test_cache_can_be_disabled(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("RAGIN_LLM_CACHE", "disabled")
    dec, fake = _deceiver_with_gateway()
    dec.generate_response("mkdir -p /opt/app/cache", _ctx("cache-off"))
    resp = dec.generate_response("mkdir -p /opt/app/cache", _ctx("cache-off"))
    assert len(fake.calls) == 2
    assert resp.metadata.get("llm_cache") is None


def test_cache_forced_off_under_model_exposure(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("RAGIN_REQUIRE_MODEL_EXPOSURE", "1")
    dec, fake = _deceiver_with_gateway()
    dec.generate_response("mkdir -p /opt/app/cache", _ctx("exposure-sess"))
    resp = dec.generate_response("mkdir -p /opt/app/cache", _ctx("exposure-sess"))
    assert len(fake.calls) == 2
    assert resp.metadata.get("llm_cache") is None


def test_cache_stores_only_model_drafts():
    """Template/anchored/fallback bytes have their own deterministic serving
    paths and their own marks — they must never be stored as model drafts."""
    assert _model_draft_generation({}) is True
    assert _model_draft_generation({"final_generation_source": "MODEL_POSTPROCESSED"}) is True
    for mark in ("common_command_fastpath", "gateway_fallback", "template_anchored", "static_fallback"):
        assert _model_draft_generation({mark: True}) is False
    assert _model_draft_generation({"template_fallback_reason": "no_gateway"}) is False
    assert _model_draft_generation({"final_generation_source": "TEMPLATE_FALLBACK"}) is False
    assert _model_draft_generation({"final_generation_source": "LLM_CACHE_HIT"}) is False


def test_cache_evicts_beyond_maxsize_and_expires_after_ttl():
    cache = _LLMResponseCache(maxsize=2, ttl_s=0.05)
    for i in range(3):
        cache.put(("s", "novice", "", f"prompt-{i}"), f"text-{i}", {"final_generation_source": "MODEL_POSTPROCESSED"})
    assert len(cache) == 2  # LRU bound
    cache.put(("s", "novice", "", "prompt-x"), "x", {})
    cache.put(("s", "novice", "", "prompt-y"), "y", {})
    time.sleep(0.06)
    assert cache.get(("s", "novice", "", "prompt-x")) is None  # TTL expiry


def test_cache_hit_and_fresh_generation_share_bytes():
    """A cached serve must be byte-identical to the fresh one — within a
    session that identity is the consistency contract, not a tell."""
    dec, fake = _deceiver_with_gateway()
    first = dec.generate_response("mkdir -p /opt/app/cache", _ctx("bytes-sess"))
    for _ in range(3):
        repeat = dec.generate_response("mkdir -p /opt/app/cache", _ctx("bytes-sess"))
        assert repeat.response_text == first.response_text
    assert len(fake.calls) == 1


# ── provider path defers both latency features ─────────────────────────────
#
# WS1 acceptance contract: with the provider path enabled, EVERY generation
# turn must be INVOKED against the provider (the mock request log is the
# evidence). A fast-path serve or a cache hit that skipped the provider would
# silently break request-log provenance, so both features defer.


def test_provider_path_enabled_matches_server_v2_allowlist():
    # Same read server_v2 uses to decide it wires ProviderTransport — an
    # unknown value means "not the provider path", never a serving error.
    assert provider_path_enabled(environ={"RAGIN_PROVIDER_ENABLED": "1"}) is True
    assert provider_path_enabled(environ={"RAGIN_PROVIDER_ENABLED": "true"}) is True
    assert provider_path_enabled(environ={"RAGIN_PROVIDER_ENABLED": "YES"}) is True
    assert provider_path_enabled(environ={}) is False
    assert provider_path_enabled(environ={"RAGIN_PROVIDER_ENABLED": ""}) is False
    assert provider_path_enabled(environ={"RAGIN_PROVIDER_ENABLED": "nope"}) is False


def test_fastpath_defers_when_provider_path_enabled(monkeypatch: pytest.MonkeyPatch):
    """`whoami` is fast-path-eligible — but with the provider enabled the
    gateway must still be reached (acceptance asserts the provider log)."""
    monkeypatch.setenv("RAGIN_PROVIDER_ENABLED", "1")
    gen, fake = _gen()
    meta: dict[str, Any] = {}
    gen.generate(skill_level="expert", user_input="whoami", meta=meta)
    assert len(fake.calls) == 1
    assert meta.get("common_command_fastpath") is None


def test_provider_transport_in_gateway_slot_defers_fastpath(monkeypatch: pytest.MonkeyPatch):
    """The isinstance signal: even without the env flag, a ProviderTransport in
    the gateway slot means the provider must be reached every turn."""
    monkeypatch.delenv("RAGIN_PROVIDER_ENABLED", raising=False)
    from ragin.cycle.provider_transport import ProviderTransport

    gen = ResponseGenerator(gateway_url=None)
    transport = ProviderTransport()
    calls = {"n": 0}

    def stub(**kwargs: Any):
        calls["n"] += 1
        observation = kwargs.get("observation")
        if isinstance(observation, dict):
            observation.update({"invocation_succeeded": True, "model_response_received": True})
        return _SAFE_DRAFT, {"prompt_tokens": 10, "completion_tokens": 20}

    monkeypatch.setattr(transport, "generate", stub)
    gen._gateway = transport
    assert gen.provider_backed() is True

    meta: dict[str, Any] = {}
    gen.generate(skill_level="expert", user_input="whoami", meta=meta)
    assert calls["n"] == 1  # reached the provider transport, no fast-path
    assert meta.get("common_command_fastpath") is None


def test_cache_defers_when_provider_path_enabled(monkeypatch: pytest.MonkeyPatch):
    """A repeat of the same prompt must still reach the provider — no silent
    in-session replay while the provider path is enabled."""
    monkeypatch.setenv("RAGIN_PROVIDER_ENABLED", "1")
    dec, fake = _deceiver_with_gateway()
    dec.generate_response("mkdir -p /opt/app/cache", _ctx("prov-cache"))
    resp = dec.generate_response("mkdir -p /opt/app/cache", _ctx("prov-cache"))
    assert len(fake.calls) == 2
    assert resp.metadata.get("llm_cache") is None


# ── reads are ledger-owned: never cached ────────────────────────────────────


def test_cache_never_caches_read_commands():
    """The ledger owns read-command repeats (remember → replay → invalidate on
    mutation). A read must never enter the cache, so a mutation can never find
    pre-mutation bytes there after the ledger invalidated its own entry."""
    dec, fake = _deceiver_with_gateway()
    cmd = "tail -n 40 /opt/app/release/notes.txt"  # readable, no transcript
    first = dec.generate_response(cmd, _ctx("read-cache"))
    second = dec.generate_response(cmd, _ctx("read-cache"))

    assert len(fake.calls) == 1          # the repeat was served by the ledger
    assert len(dec._llm_response_cache) == 0  # reads never enter the cache
    assert first.metadata.get("fs_replay") is None
    assert second.metadata.get("fs_replay") is True
    assert second.metadata.get("llm_cache") is None


def test_read_after_mutation_regenerates_never_cached_bytes():
    """mutation → the ledger invalidates → the next read must GENERATE (not
    replay, not serve cached bytes from before the mutation)."""
    dec, fake = _deceiver_with_gateway()
    cmd = "tail -n 40 /opt/app/release/notes.txt"
    dec.generate_response(cmd, _ctx("mut-read"))
    dec.generate_response("touch /opt/app/release/notes.txt", _ctx("mut-read"))
    third = dec.generate_response(cmd, _ctx("mut-read"))

    assert len(fake.calls) == 3  # generate, mutation turn, regenerate — no skips
    assert third.metadata.get("fs_replay") is None  # ledger entry was invalidated
    assert third.metadata.get("llm_cache") is None


# ── graph mocks (local copies of the test_cycle_graph helpers) ──────────────


def _classifier(skill: str = "intermediate", confidence: float = 0.8) -> MagicMock:
    c = MagicMock()
    c.classify.return_value = {"skill_level": skill, "confidence": confidence}
    return c


def _analyzer() -> MagicMock:
    a = MagicMock()
    a.analyze.return_value = {
        "threat_summary": "SSH brute force then credential hunt",
        "recommendations": ["deploy honeytoken"],
        "extracted_techniques": ["T1552"],
    }
    return a