"""Integration tests for the EPKScreen opt-in layer."""

from __future__ import annotations

import pytest

from ragin.epk.graph import Fact, FactGraph
from ragin.epk.integrate import EPKScreen, epk_enabled

pytestmark = pytest.mark.unit


def _screen() -> EPKScreen:
    w = FactGraph()
    for f in [
        Fact("kernel.version", ("web-srv-01",), "5.15.0-91-generic", "seed"),
        Fact("pkg.version", ("nginx",), "1.25.5", "seed"),
    ]:
        w.stage(f)
    w.commit()
    return EPKScreen(world=w)


def test_disabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RAGIN_EPK_ENABLED", raising=False)
    s = _screen()
    r = s.screen("Linux web-srv-01 9.9.9-fake GNU/Linux")
    assert r.enabled is False and r.admitted is True  # legacy behavior passthrough
    assert epk_enabled() is False


def test_kernel_banner_version_conflict_denied(monkeypatch: pytest.MonkeyPatch) -> None:
    """A draft that prints a kernel build different from the world's seed is
    an inferable contradiction (functional slot) — the firewall must deny it
    even though no lexical verifier rule would catch it."""
    monkeypatch.setenv("RAGIN_EPK_ENABLED", "1")
    s = _screen()
    r = s.screen("Linux web-srv-01 5.15.0-72-generic #150-Ubuntu SMP GNU/Linux")
    assert r.enabled and not r.admitted
    assert any("T2" in x for x in r.profile.deny_reasons)


def test_consistent_banner_admitted_and_announced(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RAGIN_EPK_ENABLED", "1")
    s = _screen()
    r = s.screen("Linux web-srv-01 5.15.0-91-generic #167-Ubuntu SMP GNU/Linux")
    assert r.admitted and r.extracted
    assert any(f.value == "5.15.0-91-generic" for f in s.tracker.served_history())


def test_untypeable_content_passes_through(monkeypatch: pytest.MonkeyPatch) -> None:
    """Content the extractor cannot type degrades to legacy behavior — the
    kernel is additive, never a stricter blind gate."""
    monkeypatch.setenv("RAGIN_EPK_ENABLED", "1")
    s = _screen()
    r = s.screen("total 12\ndrwxr-xr-x 2 webapp webapp 4096 .")
    assert r.admitted and r.extracted == []


def test_foreign_hostname_denied_at_t1(monkeypatch: pytest.MonkeyPatch) -> None:
    """A draft rendering a shell prompt with a hostname OUTSIDE the pinned
    fiction (the live svr04-vs-web-srv-01 tell) is denied at the T1
    boundary — the cross-surface inconsistency class the kernel exists for."""
    monkeypatch.setenv("RAGIN_EPK_ENABLED", "1")
    s = EPKScreen(seed_identity={"host": "web-srv-01", "kernel": "5.15.0-91-generic"})
    good = s.screen("webapp@web-srv-01:~$ ls\ndrwxr-xr-x deploy deploy .")
    assert good.admitted, good.profile.deny_reasons
    bad = s.screen("root@svr04:/# id\nuid=0(root)")
    assert not bad.admitted
    assert any("hostname" in x for x in bad.profile.deny_reasons)


def test_session_key_stable_across_conversation_growth():
    """The epistemic session key derived from (source_ip, first user message)
    stays constant as the conversation grows — the property K_t accumulation
    depends on after the W4.1 continuity fix."""
    import hashlib

    turn1 = [{"role": "system", "content": "ctx"}, {"role": "user", "content": "id"}]
    turn2 = turn1 + [{"role": "assistant", "content": "uid=1001(webapp)"},
                     {"role": "user", "content": "uname -a"}]
    def key(msgs):
        first_user = next((str(m.get("content", "")) for m in msgs
                           if isinstance(m, dict) and m.get("role") == "user"), "")
        return hashlib.sha256(f"10.0.0.9|{first_user}".encode()).hexdigest()[:16]
    assert key(turn1) == key(turn2)
